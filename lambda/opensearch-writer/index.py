"""
OpenSearch Writer Lambda Function

Indexes embeddings and metadata in Amazon OpenSearch for vector similarity search.

Uses OpenSearch k-NN (k-Nearest Neighbors) plugin for efficient vector search.
"""

import json
import os
import boto3
from typing import Dict, Any, List
import urllib3
from urllib3.util.retry import Retry

# Environment variables
OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
OPENSEARCH_INDEX_NAME = os.environ.get('OPENSEARCH_INDEX_NAME', 'document-embeddings')
KNN_DIMENSIONS = int(os.environ.get('KNN_DIMENSIONS', '1536'))
KNN_METHOD = os.environ.get('KNN_METHOD', 'hnsw')  # hnsw or ivf
KNN_SIMILARITY = os.environ.get('KNN_SIMILARITY', 'cosine')  # cosine, l2, or l1

# HTTP client with retries
http = urllib3.PoolManager(
    retries=Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for OpenSearch indexing.
    
    Input (from previous Step Functions task):
    {
        "documentId": "uuid",
        "embeddings": [
            {
                "chunkId": 0,
                "embedding": [0.123, ...],
                "text": "...",
                "metadata": {...}
            },
            ...
        ],
        "embeddingCount": 10,
        ...
    }
    
    Output:
    {
        "documentId": "uuid",
        "indexedCount": 10,
        "openSearchIndex": "document-embeddings",
        "success": true,
        ...
    }
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract parameters
        document_id = event.get('documentId')
        embeddings = event.get('embeddings', [])
        
        if not document_id:
            raise ValueError("documentId is required")
        
        if not embeddings:
            raise ValueError("No embeddings to index")
        
        print(f"Indexing {len(embeddings)} embeddings for document {document_id}")
        
        # Ensure OpenSearch index exists with proper k-NN configuration
        ensure_index_exists()
        
        # Index embeddings in bulk
        indexed_count = bulk_index_embeddings(document_id, embeddings)
        
        print(f"Successfully indexed {indexed_count} embeddings")
        
        # Prepare result
        result = {
            **event,  # Pass through previous state data
            'indexedCount': indexed_count,
            'openSearchIndex': OPENSEARCH_INDEX_NAME,
            'openSearchEndpoint': OPENSEARCH_ENDPOINT,
            'success': True,
        }
        
        return result
    
    except Exception as e:
        print(f"Error indexing to OpenSearch: {str(e)}")
        return {
            **event,
            'success': False,
            'error': str(e),
            'stage': 'opensearch-write',
        }


def ensure_index_exists():
    """
    Ensure OpenSearch index exists with proper k-NN configuration.
    
    Index mapping:
    {
        "settings": {
            "index.knn": true,
            "number_of_shards": 2,
            "number_of_replicas": 1
        },
        "mappings": {
            "properties": {
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "nmslib"
                    }
                },
                "text": { "type": "text" },
                "metadata": { "type": "object" },
                ...
            }
        }
    }
    """
    index_url = f'{OPENSEARCH_ENDPOINT}/{OPENSEARCH_INDEX_NAME}'
    
    try:
        # Check if index exists
        response = http.request(
            'HEAD',
            index_url,
            timeout=10.0,
        )
        
        if response.status == 200:
            print(f"Index {OPENSEARCH_INDEX_NAME} already exists")
            return
        
        # Create index with k-NN configuration
        index_config = {
            'settings': {
                'index.knn': True,  # Enable k-NN plugin
                'number_of_shards': 2,
                'number_of_replicas': 1,
                'refresh_interval': '30s',  # Optimize for bulk indexing
            },
            'mappings': {
                'properties': {
                    'documentId': {
                        'type': 'keyword',
                    },
                    'chunkId': {
                        'type': 'integer',
                    },
                    'embedding': {
                        'type': 'knn_vector',
                        'dimension': KNN_DIMENSIONS,
                        'method': {
                            'name': KNN_METHOD,  # hnsw (Hierarchical NSW) or ivf (Inverted File)
                            'space_type': map_similarity_to_space_type(KNN_SIMILARITY),
                            'engine': 'nmslib',  # nmslib or faiss
                            'parameters': {
                                'ef_construction': 128,  # HNSW: higher = better recall, slower indexing
                                'm': 16,  # HNSW: number of connections per layer
                            },
                        },
                    },
                    'text': {
                        'type': 'text',
                        'analyzer': 'standard',
                    },
                    'textLength': {
                        'type': 'integer',
                    },
                    'startPosition': {
                        'type': 'integer',
                    },
                    'endPosition': {
                        'type': 'integer',
                    },
                    'fileName': {
                        'type': 'keyword',
                    },
                    'metadata': {
                        'type': 'object',
                        'enabled': True,
                    },
                    'timestamp': {
                        'type': 'date',
                    },
                },
            },
        }
        
        # Create index
        response = http.request(
            'PUT',
            index_url,
            body=json.dumps(index_config).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            timeout=30.0,
        )
        
        if response.status not in [200, 201]:
            response_data = json.loads(response.data.decode('utf-8'))
            raise Exception(f"Failed to create index: {response_data}")
        
        print(f"Created index {OPENSEARCH_INDEX_NAME} with k-NN configuration")
    
    except Exception as e:
        print(f"Warning: Could not ensure index exists: {str(e)}")
        # Continue anyway - index might already exist


def bulk_index_embeddings(document_id: str, embeddings: List[Dict[str, Any]]) -> int:
    """
    Bulk index embeddings into OpenSearch.
    
    Uses OpenSearch Bulk API for efficient batch indexing:
    POST /_bulk
    
    Bulk format (newline-delimited JSON):
    { "index": { "_index": "index-name", "_id": "doc-id" } }
    { "field1": "value1", "field2": "value2" }
    { "index": { "_index": "index-name", "_id": "doc-id-2" } }
    { "field1": "value1", "field2": "value2" }
    """
    bulk_url = f'{OPENSEARCH_ENDPOINT}/_bulk'
    
    # Prepare bulk request body
    bulk_body_lines = []
    
    for embedding_doc in embeddings:
        # Document ID: documentId-chunkId
        doc_id = f"{document_id}-{embedding_doc.get('chunkId', 0)}"
        
        # Index action
        action = {
            'index': {
                '_index': OPENSEARCH_INDEX_NAME,
                '_id': doc_id,
            }
        }
        bulk_body_lines.append(json.dumps(action))
        
        # Document content
        doc = {
            'documentId': document_id,
            'chunkId': embedding_doc.get('chunkId', 0),
            'embedding': embedding_doc.get('embedding'),
            'text': embedding_doc.get('text', ''),
            'textLength': embedding_doc.get('textLength', 0),
            'startPosition': embedding_doc.get('startPosition', 0),
            'endPosition': embedding_doc.get('endPosition', 0),
            'fileName': embedding_doc.get('metadata', {}).get('fileName', ''),
            'metadata': embedding_doc.get('metadata', {}),
            'timestamp': get_current_timestamp(),
        }
        bulk_body_lines.append(json.dumps(doc))
    
    # Join with newlines and add trailing newline (required by bulk API)
    bulk_body = '\n'.join(bulk_body_lines) + '\n'
    
    # Send bulk request
    try:
        response = http.request(
            'POST',
            bulk_url,
            body=bulk_body.encode('utf-8'),
            headers={'Content-Type': 'application/x-ndjson'},
            timeout=60.0,
        )
        
        response_data = json.loads(response.data.decode('utf-8'))
        
        if response.status != 200:
            raise Exception(f"Bulk index failed: {response_data}")
        
        # Check for errors in bulk response
        if response_data.get('errors', False):
            error_count = 0
            for item in response_data.get('items', []):
                if 'error' in item.get('index', {}):
                    error_count += 1
                    print(f"Bulk index error: {item['index']['error']}")
            
            if error_count > 0:
                print(f"Warning: {error_count} documents failed to index")
        
        # Count successful indexes
        indexed_count = len([
            item for item in response_data.get('items', [])
            if item.get('index', {}).get('result') in ['created', 'updated']
        ])
        
        return indexed_count
    
    except Exception as e:
        raise Exception(f"Bulk indexing failed: {str(e)}")


def map_similarity_to_space_type(similarity: str) -> str:
    """
    Map similarity metric to OpenSearch space_type.
    
    Mappings:
    - cosine → cosinesimil
    - l2 → l2
    - l1 → l1
    """
    mapping = {
        'cosine': 'cosinesimil',
        'l2': 'l2',
        'l1': 'l1',
    }
    
    return mapping.get(similarity, 'cosinesimil')


def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO format.
    """
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'


def search_similar_embeddings(query_embedding: List[float], k: int = 10) -> List[Dict[str, Any]]:
    """
    Search for similar embeddings using k-NN.
    
    This function demonstrates how to query the indexed embeddings.
    Not used in the upload pipeline, but useful for RAG retrieval.
    
    Query format:
    {
        "size": 10,
        "query": {
            "knn": {
                "embedding": {
                    "vector": [0.123, ...],
                    "k": 10
                }
            }
        }
    }
    """
    search_url = f'{OPENSEARCH_ENDPOINT}/{OPENSEARCH_INDEX_NAME}/_search'
    
    query = {
        'size': k,
        'query': {
            'knn': {
                'embedding': {
                    'vector': query_embedding,
                    'k': k,
                }
            }
        },
        '_source': {
            'excludes': ['embedding'],  # Don't return embedding in results (save bandwidth)
        },
    }
    
    try:
        response = http.request(
            'POST',
            search_url,
            body=json.dumps(query).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            timeout=30.0,
        )
        
        response_data = json.loads(response.data.decode('utf-8'))
        
        if response.status != 200:
            raise Exception(f"Search failed: {response_data}")
        
        # Extract results
        hits = response_data.get('hits', {}).get('hits', [])
        
        results = []
        for hit in hits:
            results.append({
                'documentId': hit['_source']['documentId'],
                'chunkId': hit['_source']['chunkId'],
                'text': hit['_source']['text'],
                'score': hit['_score'],
                'metadata': hit['_source'].get('metadata', {}),
            })
        
        return results
    
    except Exception as e:
        raise Exception(f"Search failed: {str(e)}")


def delete_document_embeddings(document_id: str) -> int:
    """
    Delete all embeddings for a specific document.
    
    Useful for document updates or deletions.
    
    Delete by query:
    POST /index/_delete_by_query
    {
        "query": {
            "term": { "documentId": "uuid" }
        }
    }
    """
    delete_url = f'{OPENSEARCH_ENDPOINT}/{OPENSEARCH_INDEX_NAME}/_delete_by_query'
    
    query = {
        'query': {
            'term': {
                'documentId': document_id,
            }
        }
    }
    
    try:
        response = http.request(
            'POST',
            delete_url,
            body=json.dumps(query).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            timeout=30.0,
        )
        
        response_data = json.loads(response.data.decode('utf-8'))
        
        if response.status != 200:
            raise Exception(f"Delete failed: {response_data}")
        
        deleted_count = response_data.get('deleted', 0)
        
        print(f"Deleted {deleted_count} embeddings for document {document_id}")
        
        return deleted_count
    
    except Exception as e:
        raise Exception(f"Delete failed: {str(e)}")

