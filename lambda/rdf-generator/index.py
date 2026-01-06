"""
RDF Generator Lambda Function

Generates RDF triples and ontology from parsed document text.
Constructs semantic graph representation for Neptune storage.

Libraries required:
- rdflib for RDF manipulation
- spaCy or similar for NLP (optional, for entity extraction)
"""

import json
import os
import boto3
from typing import Dict, Any, List
from datetime import datetime
from urllib.parse import quote

s3_client = boto3.client('s3')

# Environment variables
BUCKET_NAME = os.environ['DOCUMENT_BUCKET_NAME']
ONTOLOGY_SCHEMA_VERSION = os.environ.get('ONTOLOGY_SCHEMA_VERSION', '1.0')
RDF_FORMAT = os.environ.get('RDF_FORMAT', 'turtle')  # turtle, n-triples, or rdf-xml

# Namespace definitions for ontology
NAMESPACE_BASE = "http://graph-rag.example.com/"
NAMESPACE_DOC = f"{NAMESPACE_BASE}document/"
NAMESPACE_ENTITY = f"{NAMESPACE_BASE}entity/"
NAMESPACE_ONTO = f"{NAMESPACE_BASE}ontology/"


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for RDF generation.
    
    Input (from previous Step Functions task):
    {
        "documentId": "uuid",
        "textContent": "Extracted text...",
        "chunks": [...],
        "metadata": {...},
        ...
    }
    
    Output:
    {
        "documentId": "uuid",
        "rdfS3Key": "neptune-staging/uuid/data.ttl",
        "tripleCount": 123,
        "entityCount": 45,
        "success": true,
        ...
    }
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract parameters
        document_id = event.get('documentId')
        text_content = event.get('textContent', '')
        chunks = event.get('chunks', [])
        metadata = event.get('metadata', {})
        file_name = event.get('fileName', 'unknown')
        
        if not document_id:
            raise ValueError("documentId is required")
        
        print(f"Generating RDF for document {document_id}")
        
        # Generate RDF triples
        rdf_graph = generate_rdf_graph(
            document_id=document_id,
            text_content=text_content,
            chunks=chunks,
            metadata=metadata,
            file_name=file_name,
        )
        
        # Serialize RDF to string
        rdf_content = serialize_rdf(rdf_graph, format=RDF_FORMAT)
        
        # Count triples
        triple_count = len(rdf_graph)
        
        # Save RDF to S3 staging area for Neptune bulk loading
        staging_key = f"neptune-staging/{document_id}/data.ttl"
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=staging_key,
            Body=rdf_content.encode('utf-8'),
            ContentType='text/turtle',
            Metadata={
                'document-id': document_id,
                'triple-count': str(triple_count),
                'format': RDF_FORMAT,
                'schema-version': ONTOLOGY_SCHEMA_VERSION,
            },
        )
        
        print(f"Generated {triple_count} RDF triples, saved to {staging_key}")
        
        # Prepare result
        result = {
            **event,  # Pass through previous state data
            'rdfS3Key': staging_key,
            'rdfBucket': BUCKET_NAME,
            'tripleCount': triple_count,
            'rdfFormat': RDF_FORMAT,
            'ontologyVersion': ONTOLOGY_SCHEMA_VERSION,
            'success': True,
        }
        
        return result
    
    except Exception as e:
        print(f"Error generating RDF: {str(e)}")
        return {
            **event,
            'success': False,
            'error': str(e),
            'stage': 'rdf-generation',
        }


def generate_rdf_graph(
    document_id: str,
    text_content: str,
    chunks: List[Dict],
    metadata: Dict,
    file_name: str,
) -> List[Dict[str, str]]:
    """
    Generate RDF triples representing the document and its content.
    
    This is a simplified implementation. For production:
    - Use rdflib library for proper RDF handling
    - Implement NLP for entity extraction (spaCy, NLTK)
    - Define comprehensive ontology schema
    - Extract relationships and concepts
    
    Returns: List of triple dictionaries
    """
    triples = []
    
    # Document URI
    doc_uri = f"{NAMESPACE_DOC}{document_id}"
    
    # ===== Document-level triples =====
    
    # Document type
    triples.append({
        'subject': doc_uri,
        'predicate': 'rdf:type',
        'object': f'{NAMESPACE_ONTO}Document',
    })
    
    # Document properties
    triples.append({
        'subject': doc_uri,
        'predicate': f'{NAMESPACE_ONTO}hasId',
        'object': f'"{document_id}"',
    })
    
    triples.append({
        'subject': doc_uri,
        'predicate': f'{NAMESPACE_ONTO}hasFileName',
        'object': f'"{escape_literal(file_name)}"',
    })
    
    triples.append({
        'subject': doc_uri,
        'predicate': f'{NAMESPACE_ONTO}hasTextLength',
        'object': f'"{len(text_content)}"^^xsd:integer',
    })
    
    triples.append({
        'subject': doc_uri,
        'predicate': f'{NAMESPACE_ONTO}createdAt',
        'object': f'"{datetime.utcnow().isoformat()}"^^xsd:dateTime',
    })
    
    # ===== Metadata triples =====
    
    if metadata.get('keywords'):
        keywords = metadata['keywords'].split(',')
        for keyword in keywords:
            keyword = keyword.strip()
            keyword_uri = f"{NAMESPACE_ENTITY}{quote(keyword)}"
            
            # Keyword entity
            triples.append({
                'subject': keyword_uri,
                'predicate': 'rdf:type',
                'object': f'{NAMESPACE_ONTO}Keyword',
            })
            
            triples.append({
                'subject': keyword_uri,
                'predicate': f'{NAMESPACE_ONTO}hasValue',
                'object': f'"{escape_literal(keyword)}"',
            })
            
            # Document-Keyword relationship
            triples.append({
                'subject': doc_uri,
                'predicate': f'{NAMESPACE_ONTO}hasKeyword',
                'object': keyword_uri,
            })
    
    if metadata.get('documentType'):
        triples.append({
            'subject': doc_uri,
            'predicate': f'{NAMESPACE_ONTO}hasType',
            'object': f'"{escape_literal(metadata["documentType"])}"',
        })
    
    if metadata.get('author'):
        author_uri = f"{NAMESPACE_ENTITY}{quote(metadata['author'])}"
        
        triples.append({
            'subject': author_uri,
            'predicate': 'rdf:type',
            'object': f'{NAMESPACE_ONTO}Author',
        })
        
        triples.append({
            'subject': author_uri,
            'predicate': f'{NAMESPACE_ONTO}hasName',
            'object': f'"{escape_literal(metadata["author"])}"',
        })
        
        triples.append({
            'subject': doc_uri,
            'predicate': f'{NAMESPACE_ONTO}hasAuthor',
            'object': author_uri,
        })
    
    # ===== Chunk triples =====
    
    for chunk in chunks:
        chunk_id = chunk.get('chunkId', 0)
        chunk_text = chunk.get('text', '')
        
        chunk_uri = f"{doc_uri}/chunk/{chunk_id}"
        
        # Chunk entity
        triples.append({
            'subject': chunk_uri,
            'predicate': 'rdf:type',
            'object': f'{NAMESPACE_ONTO}TextChunk',
        })
        
        triples.append({
            'subject': chunk_uri,
            'predicate': f'{NAMESPACE_ONTO}hasChunkId',
            'object': f'"{chunk_id}"^^xsd:integer',
        })
        
        triples.append({
            'subject': chunk_uri,
            'predicate': f'{NAMESPACE_ONTO}hasText',
            'object': f'"{escape_literal(chunk_text[:500])}"',  # Truncate for RDF storage
        })
        
        triples.append({
            'subject': chunk_uri,
            'predicate': f'{NAMESPACE_ONTO}hasStartPosition',
            'object': f'"{chunk.get("startPosition", 0)}"^^xsd:integer',
        })
        
        triples.append({
            'subject': chunk_uri,
            'predicate': f'{NAMESPACE_ONTO}hasLength',
            'object': f'"{chunk.get("length", 0)}"^^xsd:integer',
        })
        
        # Chunk belongs to document
        triples.append({
            'subject': doc_uri,
            'predicate': f'{NAMESPACE_ONTO}hasChunk',
            'object': chunk_uri,
        })
        
        # Extract entities from chunk (simplified)
        # In production, use NLP library for entity recognition
        entities = extract_entities_simple(chunk_text)
        for entity_text, entity_type in entities:
            entity_uri = f"{NAMESPACE_ENTITY}{quote(entity_text)}"
            
            triples.append({
                'subject': entity_uri,
                'predicate': 'rdf:type',
                'object': f'{NAMESPACE_ONTO}{entity_type}',
            })
            
            triples.append({
                'subject': entity_uri,
                'predicate': f'{NAMESPACE_ONTO}hasValue',
                'object': f'"{escape_literal(entity_text)}"',
            })
            
            triples.append({
                'subject': chunk_uri,
                'predicate': f'{NAMESPACE_ONTO}mentions',
                'object': entity_uri,
            })
    
    return triples


def extract_entities_simple(text: str) -> List[tuple]:
    """
    Simple entity extraction (placeholder).
    
    In production, use:
    - spaCy for named entity recognition
    - Custom domain-specific entity extractors
    - Regular expressions for patterns
    
    Returns: List of (entity_text, entity_type) tuples
    """
    entities = []
    
    # Simple capitalized word detection (very basic)
    import re
    
    # Find capitalized words (potential entities)
    words = re.findall(r'\b[A-Z][a-z]+\b', text)
    
    # Take first 5 unique capitalized words as entities
    seen = set()
    for word in words:
        if word not in seen and len(word) > 3:
            entities.append((word, 'Entity'))
            seen.add(word)
            if len(entities) >= 5:
                break
    
    return entities


def serialize_rdf(triples: List[Dict[str, str]], format: str = 'turtle') -> str:
    """
    Serialize RDF triples to string format.
    
    In production, use rdflib:
    
    from rdflib import Graph, Namespace, Literal, URIRef
    g = Graph()
    for triple in triples:
        g.add((URIRef(triple['subject']), URIRef(triple['predicate']), ...))
    return g.serialize(format='turtle')
    """
    if format == 'turtle':
        return serialize_turtle(triples)
    elif format == 'n-triples':
        return serialize_ntriples(triples)
    else:
        raise ValueError(f"Unsupported RDF format: {format}")


def serialize_turtle(triples: List[Dict[str, str]]) -> str:
    """
    Serialize triples to Turtle format (simplified).
    """
    lines = []
    
    # Prefixes
    lines.append('@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .')
    lines.append('@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .')
    lines.append(f'@prefix doc: <{NAMESPACE_DOC}> .')
    lines.append(f'@prefix entity: <{NAMESPACE_ENTITY}> .')
    lines.append(f'@prefix onto: <{NAMESPACE_ONTO}> .')
    lines.append('')
    
    # Group triples by subject for better readability
    subject_triples = {}
    for triple in triples:
        subject = triple['subject']
        if subject not in subject_triples:
            subject_triples[subject] = []
        subject_triples[subject].append(triple)
    
    # Serialize grouped triples
    for subject, subject_triple_list in subject_triples.items():
        lines.append(f'<{subject}>')
        for i, triple in enumerate(subject_triple_list):
            predicate = triple['predicate']
            obj = triple['object']
            
            # Format predicate (use prefix if possible)
            predicate = format_uri(predicate)
            
            # Format object
            if obj.startswith('"'):
                # Literal
                obj_formatted = obj
            elif obj.startswith(NAMESPACE_BASE):
                # URI
                obj_formatted = f'<{obj}>'
            else:
                obj_formatted = format_uri(obj)
            
            # Add triple
            if i < len(subject_triple_list) - 1:
                lines.append(f'    {predicate} {obj_formatted} ;')
            else:
                lines.append(f'    {predicate} {obj_formatted} .')
        
        lines.append('')
    
    return '\n'.join(lines)


def serialize_ntriples(triples: List[Dict[str, str]]) -> str:
    """
    Serialize triples to N-Triples format.
    """
    lines = []
    
    for triple in triples:
        subject = f'<{triple["subject"]}>'
        
        predicate = triple['predicate']
        if not predicate.startswith('<'):
            predicate = format_uri_full(predicate)
        
        obj = triple['object']
        if not obj.startswith('"') and not obj.startswith('<'):
            obj = f'<{obj}>'
        
        lines.append(f'{subject} {predicate} {obj} .')
    
    return '\n'.join(lines)


def format_uri(uri: str) -> str:
    """
    Format URI with prefix if applicable.
    """
    if uri.startswith('rdf:') or uri.startswith('xsd:'):
        return uri
    elif uri.startswith(NAMESPACE_DOC):
        return uri.replace(NAMESPACE_DOC, 'doc:')
    elif uri.startswith(NAMESPACE_ENTITY):
        return uri.replace(NAMESPACE_ENTITY, 'entity:')
    elif uri.startswith(NAMESPACE_ONTO):
        return uri.replace(NAMESPACE_ONTO, 'onto:')
    else:
        return f'<{uri}>'


def format_uri_full(uri: str) -> str:
    """
    Format URI with full namespace (for N-Triples).
    """
    if uri.startswith('rdf:'):
        return f'<http://www.w3.org/1999/02/22-rdf-syntax-ns#{uri[4:]}>'
    elif uri.startswith('xsd:'):
        return f'<http://www.w3.org/2001/XMLSchema#{uri[4:]}>'
    elif uri.startswith('doc:'):
        return f'<{NAMESPACE_DOC}{uri[4:]}>'
    elif uri.startswith('entity:'):
        return f'<{NAMESPACE_ENTITY}{uri[7:]}>'
    elif uri.startswith('onto:'):
        return f'<{NAMESPACE_ONTO}{uri[5:]}>'
    else:
        return f'<{uri}>'


def escape_literal(text: str) -> str:
    """
    Escape special characters in RDF literals.
    """
    return (text
        .replace('\\', '\\\\')
        .replace('"', '\\"')
        .replace('\n', '\\n')
        .replace('\r', '\\r')
        .replace('\t', '\\t'))

