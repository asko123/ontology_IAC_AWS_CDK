"""
Document Parser Lambda Function

Extracts text content from uploaded documents.
Supports: PDF, DOCX, CSV, TXT

Libraries required (add to Lambda layer or deployment package):
- PyPDF2 or pdfplumber for PDF parsing
- python-docx for Word documents
- pandas for CSV
"""

import json
import os
import boto3
import re
from typing import Dict, Any, List
from io import BytesIO

s3_client = boto3.client('s3')

# Environment variables
BUCKET_NAME = os.environ['DOCUMENT_BUCKET_NAME']
MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', '50'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for document parsing.
    
    Input (from Step Functions or direct invocation):
    {
        "bucket": "bucket-name",
        "key": "documents/uuid/file.pdf",
        "s3Event": {...} (optional, contains metadata)
    }
    
    Output:
    {
        "documentId": "uuid",
        "bucket": "bucket-name",
        "key": "documents/uuid/file.pdf",
        "fileName": "file.pdf",
        "fileType": "pdf",
        "textContent": "Extracted text...",
        "metadata": {...},
        "chunks": [...],
        "success": true
    }
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract parameters
        bucket = event.get('bucket')
        key = event.get('key')
        
        if not bucket or not key:
            raise ValueError("bucket and key are required parameters")
        
        print(f"Processing document: s3://{bucket}/{key}")
        
        # Download file from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read()
        file_size = len(file_content)
        
        print(f"Downloaded file, size: {file_size} bytes")
        
        # Get metadata from S3 object
        s3_metadata = response.get('Metadata', {})
        
        # Get tags from S3 object
        try:
            tags_response = s3_client.get_object_tagging(Bucket=bucket, Key=key)
            tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagSet', [])}
        except Exception as e:
            print(f"Warning: Could not retrieve tags: {str(e)}")
            tags = {}
        
        # Extract document ID from key
        document_id = extract_document_id(key)
        
        # Determine file type
        file_name = key.split('/')[-1]
        file_extension = file_name.split('.')[-1].lower()
        
        # Parse document based on file type
        text_content, parsed_metadata = parse_document(file_content, file_extension)
        
        # Split text into chunks for embedding generation
        chunks = create_text_chunks(text_content, chunk_size=1000, overlap=100)
        
        # Combine metadata
        combined_metadata = {
            **s3_metadata,
            **tags,
            **parsed_metadata,
        }
        
        # Prepare output
        result = {
            'documentId': document_id,
            'bucket': bucket,
            'key': key,
            'fileName': file_name,
            'fileType': file_extension,
            'textContent': text_content,
            'textLength': len(text_content),
            'metadata': combined_metadata,
            'chunks': chunks,
            'chunkCount': len(chunks),
            'success': True,
            'timestamp': response['LastModified'].isoformat() if 'LastModified' in response else None,
        }
        
        print(f"Successfully parsed document. Extracted {len(text_content)} characters in {len(chunks)} chunks")
        
        return result
    
    except Exception as e:
        print(f"Error parsing document: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'documentId': extract_document_id(event.get('key', '')),
            'bucket': event.get('bucket'),
            'key': event.get('key'),
        }


def parse_document(file_content: bytes, file_extension: str) -> tuple:
    """
    Parse document based on file type.
    Returns (text_content, metadata)
    """
    if file_extension == 'pdf':
        return parse_pdf(file_content)
    elif file_extension in ['docx', 'doc']:
        return parse_docx(file_content)
    elif file_extension == 'csv':
        return parse_csv(file_content)
    elif file_extension == 'txt':
        return parse_txt(file_content)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")


def parse_pdf(file_content: bytes) -> tuple:
    """
    Parse PDF document.
    
    Note: This is a simplified implementation.
    For production, use pdfplumber or PyPDF2:
    
    import PyPDF2
    pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    """
    try:
        # For this example, we'll simulate PDF parsing
        # In production, install and use PyPDF2 or pdfplumber
        text = f"[PDF content placeholder - implement PDF parsing library]\n"
        text += f"File size: {len(file_content)} bytes\n"
        text += "Install PyPDF2 or pdfplumber for actual PDF parsing."
        
        metadata = {
            'pageCount': 'unknown',
            'parsingMethod': 'placeholder',
        }
        
        return text, metadata
    
    except Exception as e:
        raise Exception(f"PDF parsing failed: {str(e)}")


def parse_docx(file_content: bytes) -> tuple:
    """
    Parse DOCX document.
    
    Note: Requires python-docx library:
    
    from docx import Document
    doc = Document(BytesIO(file_content))
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    """
    try:
        # Placeholder implementation
        text = f"[DOCX content placeholder - implement python-docx library]\n"
        text += f"File size: {len(file_content)} bytes\n"
        text += "Install python-docx for actual DOCX parsing."
        
        metadata = {
            'paragraphCount': 'unknown',
            'parsingMethod': 'placeholder',
        }
        
        return text, metadata
    
    except Exception as e:
        raise Exception(f"DOCX parsing failed: {str(e)}")


def parse_csv(file_content: bytes) -> tuple:
    """
    Parse CSV document.
    
    Converts CSV to structured text format.
    """
    try:
        import csv
        from io import StringIO
        
        # Decode bytes to string
        text_content = file_content.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.reader(StringIO(text_content))
        rows = list(csv_reader)
        
        # Convert to text format
        text_lines = []
        for i, row in enumerate(rows):
            if i == 0:
                # Header row
                text_lines.append("Headers: " + ", ".join(row))
            else:
                # Data rows
                text_lines.append(f"Row {i}: " + " | ".join(row))
        
        text = "\n".join(text_lines)
        
        metadata = {
            'rowCount': len(rows),
            'columnCount': len(rows[0]) if rows else 0,
            'parsingMethod': 'csv',
        }
        
        return text, metadata
    
    except Exception as e:
        raise Exception(f"CSV parsing failed: {str(e)}")


def parse_txt(file_content: bytes) -> tuple:
    """
    Parse plain text document.
    """
    try:
        # Decode bytes to string
        text = file_content.decode('utf-8')
        
        metadata = {
            'characterCount': len(text),
            'lineCount': text.count('\n'),
            'parsingMethod': 'text',
        }
        
        return text, metadata
    
    except Exception as e:
        # Try alternative encodings
        try:
            text = file_content.decode('latin-1')
            metadata = {
                'characterCount': len(text),
                'lineCount': text.count('\n'),
                'parsingMethod': 'text',
                'encoding': 'latin-1',
            }
            return text, metadata
        except:
            raise Exception(f"Text parsing failed: {str(e)}")


def create_text_chunks(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks for embedding generation.
    
    Args:
        text: Full text content
        chunk_size: Maximum characters per chunk
        overlap: Number of overlapping characters between chunks
    
    Returns:
        List of chunks with metadata
    """
    chunks = []
    
    # Clean text
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) <= chunk_size:
        # Document fits in single chunk
        chunks.append({
            'chunkId': 0,
            'text': text,
            'startPosition': 0,
            'endPosition': len(text),
            'length': len(text),
        })
        return chunks
    
    # Split into chunks with overlap
    start = 0
    chunk_id = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence ending
            for punct in ['. ', '.\n', '! ', '?\n']:
                last_punct = text.rfind(punct, start, end)
                if last_punct != -1:
                    end = last_punct + 1
                    break
        
        chunk_text = text[start:end].strip()
        
        if chunk_text:
            chunks.append({
                'chunkId': chunk_id,
                'text': chunk_text,
                'startPosition': start,
                'endPosition': end,
                'length': len(chunk_text),
            })
            chunk_id += 1
        
        # Move to next chunk with overlap
        start = end - overlap if end < len(text) else len(text)
    
    return chunks


def extract_document_id(s3_key: str) -> str:
    """
    Extract document ID from S3 key.
    Assumes format: documents/<document-id>/filename
    """
    try:
        parts = s3_key.split('/')
        if len(parts) >= 2 and parts[0] == 'documents':
            return parts[1]
        return 'unknown'
    except:
        return 'unknown'

