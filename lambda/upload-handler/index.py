"""
Upload Handler Lambda Function

Handles document uploads via API Gateway.
Supports two modes:
1. Direct upload: Accepts base64-encoded file in request body
2. Presigned URL: Generates presigned S3 URL for client-side upload
"""

import json
import os
import base64
import uuid
import boto3
from datetime import datetime
from typing import Dict, Any

s3_client = boto3.client('s3')

# Environment variables
BUCKET_NAME = os.environ['DOCUMENT_BUCKET_NAME']
MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', '50'))
ALLOWED_FILE_TYPES = os.environ.get('ALLOWED_FILE_TYPES', 'pdf,docx,csv,txt').split(',')
PRESIGNED_URL_EXPIRY = int(os.environ.get('PRESIGNED_URL_EXPIRY_SECONDS', '3600'))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for upload requests.
    Routes to appropriate handler based on HTTP method and path.
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        if http_method == 'POST' and '/upload' in path:
            return handle_direct_upload(event)
        elif http_method == 'GET' and '/presigned-url' in path:
            return handle_presigned_url_request(event)
        else:
            return create_response(400, {'error': 'Invalid request'})
    
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})


def handle_direct_upload(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle direct file upload via API Gateway.
    
    Request body format:
    {
        "fileName": "document.pdf",
        "fileContent": "<base64-encoded-content>",
        "metadata": {
            "keywords": "compliance,security",
            "documentType": "policy"
        }
    }
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        file_name = body.get('fileName')
        file_content_base64 = body.get('fileContent')
        metadata = body.get('metadata', {})
        
        # Validate request
        if not file_name or not file_content_base64:
            return create_response(400, {'error': 'fileName and fileContent are required'})
        
        # Validate file type
        file_extension = file_name.split('.')[-1].lower()
        if file_extension not in ALLOWED_FILE_TYPES:
            return create_response(400, {
                'error': f'File type .{file_extension} not allowed. Allowed types: {ALLOWED_FILE_TYPES}'
            })
        
        # Decode file content
        try:
            file_content = base64.b64decode(file_content_base64)
        except Exception as e:
            return create_response(400, {'error': f'Invalid base64 content: {str(e)}'})
        
        # Validate file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return create_response(400, {
                'error': f'File size ({file_size_mb:.2f}MB) exceeds maximum allowed ({MAX_FILE_SIZE_MB}MB)'
            })
        
        # Generate unique document ID and S3 key
        document_id = str(uuid.uuid4())
        s3_key = f"documents/{document_id}/{file_name}"
        
        # Prepare S3 metadata and tags
        s3_metadata = {
            'document-id': document_id,
            'original-filename': file_name,
            'upload-timestamp': datetime.utcnow().isoformat(),
        }
        
        # Add custom metadata
        if metadata:
            for key, value in metadata.items():
                s3_metadata[f'custom-{key}'] = str(value)
        
        # Prepare tags
        tags = {
            'DocumentId': document_id,
            'FileName': file_name,
            'UploadDate': datetime.utcnow().strftime('%Y-%m-%d'),
        }
        
        if 'keywords' in metadata:
            tags['Keywords'] = metadata['keywords']
        if 'documentType' in metadata:
            tags['DocumentType'] = metadata['documentType']
        
        # Convert tags to S3 format
        tag_set = '&'.join([f'{k}={v}' for k, v in tags.items()])
        
        # Upload to S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            Metadata=s3_metadata,
            Tagging=tag_set,
            ServerSideEncryption='AES256',
        )
        
        print(f"Successfully uploaded document {document_id} to {s3_key}")
        
        return create_response(200, {
            'message': 'Upload successful',
            'documentId': document_id,
            's3Key': s3_key,
            'fileName': file_name,
            'fileSize': len(file_content),
            'metadata': metadata,
        })
    
    except Exception as e:
        print(f"Error in direct upload: {str(e)}")
        return create_response(500, {'error': f'Upload failed: {str(e)}'})


def handle_presigned_url_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate presigned S3 URL for client-side upload.
    
    This approach is better for large files (>10MB).
    Client uploads directly to S3 using the presigned URL.
    
    Query parameters:
    - fileName: Name of file to upload (required)
    - fileType: MIME type (optional)
    - metadata: JSON-encoded metadata (optional)
    """
    try:
        # Parse query parameters
        params = event.get('queryStringParameters', {}) or {}
        file_name = params.get('fileName')
        file_type = params.get('fileType', 'application/octet-stream')
        metadata_json = params.get('metadata', '{}')
        
        # Validate file name
        if not file_name:
            return create_response(400, {'error': 'fileName query parameter is required'})
        
        # Validate file type
        file_extension = file_name.split('.')[-1].lower()
        if file_extension not in ALLOWED_FILE_TYPES:
            return create_response(400, {
                'error': f'File type .{file_extension} not allowed. Allowed types: {ALLOWED_FILE_TYPES}'
            })
        
        # Parse metadata
        try:
            metadata = json.loads(metadata_json)
        except:
            metadata = {}
        
        # Generate unique document ID and S3 key
        document_id = str(uuid.uuid4())
        s3_key = f"documents/{document_id}/{file_name}"
        
        # Prepare S3 metadata
        s3_metadata = {
            'document-id': document_id,
            'original-filename': file_name,
            'upload-timestamp': datetime.utcnow().isoformat(),
        }
        
        # Add custom metadata
        if metadata:
            for key, value in metadata.items():
                s3_metadata[f'custom-{key}'] = str(value)
        
        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': s3_key,
                'ContentType': file_type,
                'Metadata': s3_metadata,
                'ServerSideEncryption': 'AES256',
            },
            ExpiresIn=PRESIGNED_URL_EXPIRY,
        )
        
        print(f"Generated presigned URL for document {document_id}")
        
        return create_response(200, {
            'uploadUrl': presigned_url,
            'documentId': document_id,
            's3Key': s3_key,
            'expiresIn': PRESIGNED_URL_EXPIRY,
            'method': 'PUT',
            'headers': {
                'Content-Type': file_type,
            },
            'instructions': 'Use PUT request to upload file to the uploadUrl',
        })
    
    except Exception as e:
        print(f"Error generating presigned URL: {str(e)}")
        return create_response(500, {'error': f'Failed to generate presigned URL: {str(e)}'})


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized API Gateway response with CORS headers.
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # Configure for specific origins in production
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        },
        'body': json.dumps(body),
    }

