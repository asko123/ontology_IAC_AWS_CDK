"""
Embedding Generator Lambda Function

Generates vector embeddings from document text using Amazon Bedrock.

Embedding model: amazon.titan-embed-text-v1
Dimensions: 1536

Alternative approaches:
- SageMaker endpoint with custom model
- Lambda with sentence-transformers (limited by memory)
"""

import json
import os
import boto3
from typing import Dict, Any, List

bedrock_runtime = boto3.client('bedrock-runtime')

# Environment variables
EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'amazon.titan-embed-text-v1')
EMBEDDING_DIMENSIONS = int(os.environ.get('EMBEDDING_DIMENSIONS', '1536'))
CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', '512'))  # Tokens
CHUNK_OVERLAP = int(os.environ.get('CHUNK_OVERLAP', '50'))  # Tokens


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for embedding generation.
    
    Input (from previous Step Functions task):
    {
        "documentId": "uuid",
        "textContent": "Full text...",
        "chunks": [
            {"chunkId": 0, "text": "..."},
            ...
        ],
        "metadata": {...},
        ...
    }
    
    Output:
    {
        "documentId": "uuid",
        "embeddings": [
            {
                "chunkId": 0,
                "embedding": [0.123, -0.456, ...],
                "text": "...",
                "metadata": {...}
            },
            ...
        ],
        "embeddingCount": 10,
        "embeddingModel": "amazon.titan-embed-text-v1",
        "embeddingDimensions": 1536,
        "success": true,
        ...
    }
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract parameters
        document_id = event.get('documentId')
        chunks = event.get('chunks', [])
        metadata = event.get('metadata', {})
        file_name = event.get('fileName', 'unknown')
        
        if not document_id:
            raise ValueError("documentId is required")
        
        if not chunks:
            raise ValueError("No text chunks to embed")
        
        print(f"Generating embeddings for {len(chunks)} chunks from document {document_id}")
        
        # Generate embeddings for all chunks
        embeddings = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = chunk.get('chunkId', i)
            chunk_text = chunk.get('text', '')
            
            if not chunk_text.strip():
                print(f"Skipping empty chunk {chunk_id}")
                continue
            
            # Generate embedding
            try:
                embedding_vector = generate_embedding_bedrock(chunk_text)
                
                embeddings.append({
                    'chunkId': chunk_id,
                    'embedding': embedding_vector,
                    'text': chunk_text,
                    'textLength': len(chunk_text),
                    'startPosition': chunk.get('startPosition', 0),
                    'endPosition': chunk.get('endPosition', len(chunk_text)),
                    'metadata': {
                        'documentId': document_id,
                        'fileName': file_name,
                        **metadata,
                    },
                })
                
                print(f"Generated embedding for chunk {chunk_id} (dimension: {len(embedding_vector)})")
            
            except Exception as e:
                print(f"Error generating embedding for chunk {chunk_id}: {str(e)}")
                # Continue with other chunks
                continue
        
        if not embeddings:
            raise Exception("Failed to generate any embeddings")
        
        print(f"Successfully generated {len(embeddings)} embeddings")
        
        # Prepare result
        result = {
            **event,  # Pass through previous state data
            'embeddings': embeddings,
            'embeddingCount': len(embeddings),
            'embeddingModel': EMBEDDING_MODEL,
            'embeddingDimensions': EMBEDDING_DIMENSIONS,
            'success': True,
        }
        
        return result
    
    except Exception as e:
        print(f"Error generating embeddings: {str(e)}")
        return {
            **event,
            'success': False,
            'error': str(e),
            'stage': 'embedding-generation',
        }


def generate_embedding_bedrock(text: str) -> List[float]:
    """
    Generate embedding using Amazon Bedrock Titan Embeddings model.
    
    Bedrock Titan Embeddings API:
    - Model: amazon.titan-embed-text-v1
    - Input: Text string (max ~8K tokens)
    - Output: 1536-dimensional vector
    
    Request body:
    {
        "inputText": "text to embed"
    }
    
    Response:
    {
        "embedding": [0.123, -0.456, ...],
        "inputTextTokenCount": 42
    }
    """
    try:
        # Truncate text if too long
        # Titan embeddings model supports up to ~8000 tokens
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = 8000 * 4
        if len(text) > max_chars:
            text = text[:max_chars]
            print(f"Truncated text to {max_chars} characters")
        
        # Prepare request
        request_body = {
            'inputText': text,
        }
        
        # Call Bedrock API
        response = bedrock_runtime.invoke_model(
            modelId=EMBEDDING_MODEL,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json',
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        embedding = response_body.get('embedding')
        
        if not embedding:
            raise Exception("No embedding in Bedrock response")
        
        if len(embedding) != EMBEDDING_DIMENSIONS:
            print(f"Warning: Expected {EMBEDDING_DIMENSIONS} dimensions, got {len(embedding)}")
        
        return embedding
    
    except Exception as e:
        raise Exception(f"Bedrock embedding generation failed: {str(e)}")


def generate_embedding_sagemaker(text: str, endpoint_name: str) -> List[float]:
    """
    Alternative: Generate embedding using SageMaker endpoint.
    
    Use this if you have a custom model deployed on SageMaker.
    
    Example for sentence-transformers model:
    - Deploy model to SageMaker endpoint
    - Send text to endpoint
    - Receive embedding vector
    """
    sagemaker_runtime = boto3.client('sagemaker-runtime')
    
    try:
        # Prepare request
        request_body = {
            'inputs': text,
        }
        
        # Invoke SageMaker endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps(request_body),
        )
        
        # Parse response
        response_body = json.loads(response['Body'].read())
        
        # Extract embedding (format depends on model)
        embedding = response_body.get('embedding') or response_body.get('vectors') or response_body[0]
        
        return embedding
    
    except Exception as e:
        raise Exception(f"SageMaker embedding generation failed: {str(e)}")


def generate_embedding_local(text: str) -> List[float]:
    """
    Alternative: Generate embedding locally using sentence-transformers.
    
    Note: This requires packaging the model with Lambda (increases deployment size).
    Limited by Lambda memory (up to 10GB).
    
    Example:
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embedding = model.encode(text)
    return embedding.tolist()
    """
    raise NotImplementedError("Local embedding generation not implemented")


def split_into_token_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split text into chunks based on token count.
    
    This is a simplified character-based approximation.
    For accurate token counting, use tokenizers library:
    
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained('model-name')
    tokens = tokenizer.encode(text)
    """
    # Rough estimate: 1 token ≈ 4 characters
    char_chunk_size = chunk_size * 4
    char_overlap = overlap * 4
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + char_chunk_size, len(text))
        chunk = text[start:end]
        
        if chunk.strip():
            chunks.append(chunk)
        
        start = end - char_overlap
        
        if end >= len(text):
            break
    
    return chunks


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Useful for comparing embeddings and finding similar documents.
    """
    import math
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

