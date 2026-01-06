"""
Neptune Writer Lambda Function

Loads RDF data into Amazon Neptune graph database.

Two approaches:
1. Neptune Bulk Loader: For large datasets (recommended for >10K triples)
2. Direct SPARQL INSERT: For small datasets

This implementation uses the bulk loader approach.
"""

import json
import os
import boto3
import time
import urllib3
from typing import Dict, Any

s3_client = boto3.client('s3')

# Environment variables
BUCKET_NAME = os.environ['DOCUMENT_BUCKET_NAME']
NEPTUNE_ENDPOINT = os.environ['NEPTUNE_ENDPOINT']
NEPTUNE_PORT = os.environ.get('NEPTUNE_PORT', '8182')
NEPTUNE_LOAD_FROM_S3_ROLE_ARN = os.environ.get('NEPTUNE_LOAD_FROM_S3_ROLE_ARN', '')
NEPTUNE_STAGING_PREFIX = os.environ.get('NEPTUNE_STAGING_PREFIX', 'neptune-staging/')

# Neptune loader endpoint
NEPTUNE_LOADER_ENDPOINT = f'https://{NEPTUNE_ENDPOINT}:{NEPTUNE_PORT}/loader'

# HTTP client
http = urllib3.PoolManager()


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for Neptune loading.
    
    Input (from previous Step Functions task):
    {
        "documentId": "uuid",
        "rdfS3Key": "neptune-staging/uuid/data.ttl",
        "rdfBucket": "bucket-name",
        "tripleCount": 123,
        ...
    }
    
    Output:
    {
        "documentId": "uuid",
        "neptuneLoadId": "load-id",
        "neptuneLoadStatus": "LOAD_COMPLETED",
        "loadedTriples": 123,
        "success": true,
        ...
    }
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract parameters
        document_id = event.get('documentId')
        rdf_s3_key = event.get('rdfS3Key')
        rdf_bucket = event.get('rdfBucket', BUCKET_NAME)
        triple_count = event.get('tripleCount', 0)
        
        if not document_id or not rdf_s3_key:
            raise ValueError("documentId and rdfS3Key are required")
        
        print(f"Loading RDF from s3://{rdf_bucket}/{rdf_s3_key} into Neptune")
        
        # Construct S3 source URI
        s3_source_uri = f's3://{rdf_bucket}/{rdf_s3_key}'
        
        # Initiate Neptune bulk load
        load_id = initiate_neptune_bulk_load(
            source_uri=s3_source_uri,
            iam_role_arn=NEPTUNE_LOAD_FROM_S3_ROLE_ARN,
            format='turtle',
            region=os.environ.get('AWS_REGION', 'us-east-1'),
        )
        
        print(f"Initiated Neptune bulk load: {load_id}")
        
        # Poll load status
        load_status = poll_neptune_load_status(load_id, max_wait_seconds=300)
        
        print(f"Neptune load completed with status: {load_status['status']}")
        
        # Prepare result
        result = {
            **event,  # Pass through previous state data
            'neptuneLoadId': load_id,
            'neptuneLoadStatus': load_status['status'],
            'loadedTriples': load_status.get('totalRecords', triple_count),
            'neptuneEndpoint': NEPTUNE_ENDPOINT,
            'success': load_status['status'] == 'LOAD_COMPLETED',
        }
        
        return result
    
    except Exception as e:
        print(f"Error loading data to Neptune: {str(e)}")
        return {
            **event,
            'success': False,
            'error': str(e),
            'stage': 'neptune-write',
        }


def initiate_neptune_bulk_load(
    source_uri: str,
    iam_role_arn: str,
    format: str = 'turtle',
    region: str = 'us-east-1',
) -> str:
    """
    Initiate Neptune bulk load from S3.
    
    Neptune Bulk Loader API:
    POST https://<neptune-endpoint>:8182/loader
    
    Request body:
    {
        "source": "s3://bucket/path/to/data",
        "format": "turtle",
        "iamRoleArn": "arn:aws:iam::...",
        "region": "us-east-1",
        "failOnError": "FALSE",
        "parallelism": "MEDIUM",
        "parserConfiguration": {...}
    }
    
    Returns: Load ID
    """
    # Prepare request payload
    payload = {
        'source': source_uri,
        'format': format,
        'iamRoleArn': iam_role_arn,
        'region': region,
        'failOnError': 'FALSE',  # Continue loading even if some triples fail
        'parallelism': 'MEDIUM',  # OVERSUBSCRIBE, HIGH, MEDIUM, or LOW
    }
    
    print(f"Initiating Neptune bulk load with payload: {json.dumps(payload)}")
    
    try:
        # Make HTTP POST request to Neptune loader endpoint
        response = http.request(
            'POST',
            NEPTUNE_LOADER_ENDPOINT,
            body=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
            },
            timeout=30.0,
        )
        
        # Parse response
        response_data = json.loads(response.data.decode('utf-8'))
        
        if response.status != 200:
            raise Exception(f"Neptune loader API returned status {response.status}: {response_data}")
        
        # Extract load ID
        load_id = response_data.get('payload', {}).get('loadId')
        
        if not load_id:
            raise Exception(f"No loadId in Neptune response: {response_data}")
        
        return load_id
    
    except Exception as e:
        raise Exception(f"Failed to initiate Neptune bulk load: {str(e)}")


def poll_neptune_load_status(load_id: str, max_wait_seconds: int = 300) -> Dict[str, Any]:
    """
    Poll Neptune load status until completion or timeout.
    
    GET https://<neptune-endpoint>:8182/loader/<load-id>
    
    Response:
    {
        "status": "200 OK",
        "payload": {
            "feedCount": [...],
            "overallStatus": {
                "fullUri": "s3://...",
                "runNumber": 1,
                "retryNumber": 0,
                "status": "LOAD_COMPLETED",
                "totalTimeSpent": 5,
                "startTime": 1234567890,
                "totalRecords": 123,
                "totalDuplicates": 0,
                "parsingErrors": 0,
                "datatypeMismatchErrors": 0,
                "insertErrors": 0
            }
        }
    }
    """
    status_endpoint = f'{NEPTUNE_LOADER_ENDPOINT}/{load_id}'
    
    start_time = time.time()
    wait_interval = 5  # seconds
    
    while True:
        elapsed = time.time() - start_time
        
        if elapsed > max_wait_seconds:
            raise Exception(f"Neptune load timeout after {max_wait_seconds} seconds")
        
        try:
            # Query load status
            response = http.request(
                'GET',
                status_endpoint,
                headers={'Content-Type': 'application/json'},
                timeout=10.0,
            )
            
            response_data = json.loads(response.data.decode('utf-8'))
            
            if response.status != 200:
                raise Exception(f"Neptune status API returned {response.status}: {response_data}")
            
            # Extract status
            overall_status = response_data.get('payload', {}).get('overallStatus', {})
            status = overall_status.get('status')
            
            print(f"Neptune load status: {status}")
            
            # Check if load completed (success or failure)
            if status in ['LOAD_COMPLETED', 'LOAD_FAILED', 'LOAD_CANCELLED']:
                if status == 'LOAD_FAILED':
                    errors = overall_status.get('parsingErrors', 0) + overall_status.get('insertErrors', 0)
                    raise Exception(f"Neptune load failed with {errors} errors")
                
                return {
                    'status': status,
                    'totalRecords': overall_status.get('totalRecords', 0),
                    'totalDuplicates': overall_status.get('totalDuplicates', 0),
                    'parsingErrors': overall_status.get('parsingErrors', 0),
                    'insertErrors': overall_status.get('insertErrors', 0),
                    'totalTimeSpent': overall_status.get('totalTimeSpent', 0),
                }
            
            # Wait before next poll
            time.sleep(wait_interval)
        
        except Exception as e:
            print(f"Error polling Neptune load status: {str(e)}")
            # Retry after wait interval
            time.sleep(wait_interval)


def execute_sparql_insert(triples_ttl: str) -> Dict[str, Any]:
    """
    Alternative approach: Direct SPARQL INSERT for small datasets.
    
    Use this for quick inserts without S3 staging.
    Limited to ~10K triples due to payload size limits.
    
    SPARQL INSERT query:
    INSERT DATA {
        <subject1> <predicate1> <object1> .
        <subject2> <predicate2> <object2> .
    }
    """
    sparql_endpoint = f'https://{NEPTUNE_ENDPOINT}:{NEPTUNE_PORT}/sparql'
    
    # Construct SPARQL INSERT query
    sparql_query = f"""
    INSERT DATA {{
        {triples_ttl}
    }}
    """
    
    try:
        # Execute SPARQL update
        response = http.request(
            'POST',
            sparql_endpoint,
            body=sparql_query.encode('utf-8'),
            headers={
                'Content-Type': 'application/sparql-update',
            },
            timeout=60.0,
        )
        
        if response.status != 200:
            raise Exception(f"SPARQL INSERT failed with status {response.status}")
        
        return {
            'status': 'success',
            'method': 'sparql-insert',
        }
    
    except Exception as e:
        raise Exception(f"SPARQL INSERT failed: {str(e)}")

