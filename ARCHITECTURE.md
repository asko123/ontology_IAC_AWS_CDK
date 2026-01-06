# Architecture Documentation - Graph RAG System

## Overview

This document provides detailed architecture documentation for the Graph RAG (Retrieval Augmented Generation) system built with AWS CDK.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              UPLOAD PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────┐       ┌─────────────┐       ┌──────────┐       ┌──────────────┐
│  Client  │──────▶│ API Gateway │──────▶│  Lambda  │──────▶│  S3 Bucket   │
│ (User)   │       │   (REST)    │       │ (Upload) │       │ (Documents)  │
└──────────┘       └─────────────┘       └──────────┘       └──────┬───────┘
                                                                     │
                                                                     │ PutObject
                                                                     │ Event
                                                                     ▼
                                                            ┌────────────────┐
                                                            │  EventBridge   │
                                                            │     Rule       │
                                                            └────────┬───────┘
                                                                     │
                                                                     │ Trigger
                                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PROCESSING PIPELINE                                 │
│                           (Step Functions)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 1: Parse Document                                              │  │
│  │  ┌────────────────────┐                                              │  │
│  │  │ Document Parser    │  Extract text from PDF/DOCX/CSV/TXT         │  │
│  │  │     Lambda         │  Split into chunks                           │  │
│  │  └─────────┬──────────┘                                              │  │
│  └────────────┼─────────────────────────────────────────────────────────┘  │
│               │                                                              │
│               ▼                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 2: Parallel Processing                                         │  │
│  │                                                                       │  │
│  │  ┌────────────────────────────┐  ┌────────────────────────────────┐ │  │
│  │  │   RDF Branch               │  │   Embedding Branch             │ │  │
│  │  │                            │  │                                │ │  │
│  │  │  ┌──────────────────┐     │  │  ┌──────────────────┐         │ │  │
│  │  │  │ RDF Generator    │     │  │  │ Embedding Gen    │         │ │  │
│  │  │  │    Lambda        │     │  │  │    Lambda        │         │ │  │
│  │  │  │                  │     │  │  │  (Bedrock)       │         │ │  │
│  │  │  └────────┬─────────┘     │  │  └────────┬─────────┘         │ │  │
│  │  │           │                │  │           │                   │ │  │
│  │  │           ▼                │  │           ▼                   │ │  │
│  │  │  ┌──────────────────┐     │  │  ┌──────────────────┐         │ │  │
│  │  │  │ Neptune Writer   │     │  │  │ OpenSearch       │         │ │  │
│  │  │  │    Lambda        │     │  │  │ Writer Lambda    │         │ │  │
│  │  │  │                  │     │  │  │                  │         │ │  │
│  │  │  └────────┬─────────┘     │  │  └────────┬─────────┘         │ │  │
│  │  └───────────┼────────────────┘  └───────────┼──────────────────┘ │  │
│  └──────────────┼───────────────────────────────┼────────────────────┘  │
│                 │                               │                        │
└─────────────────┼───────────────────────────────┼────────────────────────┘
                  │                               │
                  ▼                               ▼
        ┌───────────────────┐         ┌───────────────────┐
        │  Amazon Neptune   │         │  Amazon OpenSearch│
        │  (Graph Database) │         │  (Vector Search)  │
        │                   │         │                   │
        │  - RDF Triples    │         │  - Embeddings     │
        │  - Ontology       │         │  - k-NN Index     │
        │  - SPARQL         │         │  - Metadata       │
        └───────────────────┘         └───────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          QUERY PIPELINE (Future)                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────┐       ┌─────────────┐       ┌──────────────┐       ┌──────────┐
│  Client  │──────▶│ API Gateway │──────▶│ Query Lambda │──────▶│ Bedrock  │
│ (Query)  │       │             │       │              │       │(Embedding)│
└──────────┘       └─────────────┘       └──────┬───────┘       └──────────┘
      ▲                                          │
      │                                          ▼
      │                                  ┌───────────────┐
      │                                  │  OpenSearch   │
      │                                  │  k-NN Search  │
      │                                  └───────┬───────┘
      │                                          │
      │                                          ▼
      │                                  ┌───────────────┐
      │                                  │   Neptune     │
      │                                  │ Graph Query   │
      │                                  └───────┬───────┘
      │                                          │
      │                                          ▼
      │                                  ┌───────────────┐
      │                                  │     LLM       │
      │                                  │  (Bedrock)    │
      │                                  └───────┬───────┘
      │                                          │
      └──────────────────────────────────────────┘
```

## Component Details

### 1. API Layer

#### API Gateway
- **Type:** REST API
- **Endpoints:**
  - `POST /upload`: Direct file upload (≤10MB)
  - `GET /presigned-url`: Generate presigned S3 URL for large files
- **Features:**
  - CORS enabled
  - Request validation
  - CloudWatch logging
  - Throttling (50 req/sec, 100 burst)

#### Upload Handler Lambda
- **Runtime:** Python 3.12
- **Memory:** 512 MB
- **Timeout:** 30 seconds
- **Functions:**
  - Validate file type and size
  - Store file in S3 with metadata
  - Generate presigned URLs
  - Return upload confirmation

### 2. Storage Layer

#### S3 Bucket
- **Purpose:** Document storage and staging
- **Configuration:**
  - Versioning enabled
  - Server-side encryption (SSE-S3)
  - Lifecycle policies (Glacier transition after 30 days)
  - EventBridge notifications enabled
- **Structure:**
  ```
  documents/
    ├── {document-id}/
    │   └── {filename}
  neptune-staging/
    └── {document-id}/
        └── data.ttl
  ```

### 3. Event-Driven Orchestration

#### EventBridge Rule
- **Event Source:** S3 (Object Created)
- **Event Pattern:**
  ```json
  {
    "source": ["aws.s3"],
    "detail-type": ["Object Created"],
    "detail": {
      "bucket": {"name": ["document-bucket"]}
    }
  }
  ```
- **Target:** Step Functions state machine

#### Step Functions State Machine
- **Type:** Standard workflow
- **Timeout:** 30 minutes
- **Logging:** CloudWatch Logs (all events)
- **Tracing:** X-Ray enabled

**Workflow States:**
1. **Parse Document** (Lambda invoke)
   - Retry: 3 attempts with exponential backoff
   - Error handling: Move to Fail state
2. **Parallel Processing**
   - Branch A: RDF Generation → Neptune Write
   - Branch B: Embedding Generation → OpenSearch Write
   - Both branches must succeed
3. **Success** (terminal state)

### 4. Processing Functions

#### Document Parser Lambda
- **Runtime:** Python 3.12, ARM64
- **Memory:** 1024 MB
- **Timeout:** 5 minutes
- **VPC:** Deployed in private subnet
- **Functions:**
  - Extract text from PDF, DOCX, CSV, TXT
  - Split text into overlapping chunks
  - Extract metadata from S3 tags
- **Output:** Parsed text and chunks array

#### RDF Generator Lambda
- **Runtime:** Python 3.12, ARM64
- **Memory:** 2048 MB
- **Timeout:** 10 minutes
- **VPC:** Deployed in private subnet
- **Functions:**
  - Generate RDF triples from text
  - Construct ontology relationships
  - Extract entities and concepts
  - Serialize to Turtle format
- **Output:** RDF file in S3 staging area

#### Neptune Writer Lambda
- **Runtime:** Python 3.12, ARM64
- **Memory:** 512 MB
- **Timeout:** 15 minutes
- **VPC:** Deployed in private subnet
- **Functions:**
  - Initiate Neptune bulk loader
  - Poll load status
  - Handle load errors
- **Output:** Load status and triple count

#### Embedding Generator Lambda
- **Runtime:** Python 3.12, ARM64
- **Memory:** 512 MB
- **Timeout:** 3 minutes
- **VPC:** Deployed in private subnet
- **Functions:**
  - Generate embeddings via Bedrock
  - Use Titan Embeddings (1536 dimensions)
  - Process all text chunks
- **Output:** Array of embeddings with metadata

#### OpenSearch Writer Lambda
- **Runtime:** Python 3.12, ARM64
- **Memory:** 512 MB
- **Timeout:** 5 minutes
- **VPC:** Deployed in private subnet
- **Functions:**
  - Ensure k-NN index exists
  - Bulk index embeddings
  - Handle indexing errors
- **Output:** Index status and document count

### 5. Data Stores

#### Amazon Neptune
- **Engine:** Neptune 1.3
- **Instance Type:** db.t3.medium
- **Instances:** 1 primary (+ optional read replica)
- **Storage:** Auto-scaling
- **Backup:** 7-day retention
- **Encryption:** At rest and in transit
- **Authentication:** IAM enabled
- **Endpoints:**
  - Write: Cluster endpoint (port 8182)
  - Read: Read-only endpoint
- **Supported Queries:**
  - SPARQL (RDF/semantic queries)
  - Gremlin (property graph queries)

#### Amazon OpenSearch
- **Version:** OpenSearch 2.11
- **Instance Type:** t3.small.search
- **Nodes:** 2 data nodes
- **Storage:** 50 GB EBS (gp3) per node
- **Zone Awareness:** 2 AZs
- **Encryption:** At rest and in transit
- **Plugins:** k-NN enabled
- **Index Configuration:**
  - Vector field: 1536 dimensions
  - Algorithm: HNSW (Hierarchical NSW)
  - Similarity: Cosine
  - Engine: nmslib

### 6. Networking

#### VPC
- **CIDR:** 10.0.0.0/16
- **Availability Zones:** 2
- **Subnets:**
  - Public: 2 (for NAT Gateways)
  - Private: 2 (for Lambda, Neptune, OpenSearch)
  - Isolated: 2 (future use)

#### Security Groups
- **Neptune SG:**
  - Inbound: Port 8182 from Lambda SG
  - Inbound: Port 8182 from Neptune SG (cluster communication)
- **OpenSearch SG:**
  - Inbound: Port 443 from Lambda SG
  - Inbound: All TCP from OpenSearch SG (cluster communication)
- **Lambda SG:**
  - Outbound: All (for AWS API calls, Neptune, OpenSearch)

### 7. IAM Roles and Policies

#### Upload Lambda Role
- S3: PutObject, PutObjectTagging on document bucket
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents

#### Processing Lambda Roles
- S3: GetObject, PutObject on document bucket
- Neptune: neptune-db:* on cluster
- Bedrock: InvokeModel for Titan Embeddings
- OpenSearch: ESHttpPost, ESHttpPut, ESHttpGet
- CloudWatch Logs: Write permissions
- VPC: CreateNetworkInterface, DeleteNetworkInterface

#### Step Functions Role
- Lambda: InvokeFunction on all processing functions
- CloudWatch Logs: Write permissions

#### Neptune Bulk Load Role
- S3: GetObject, ListBucket on staging prefix
- Trust: rds.amazonaws.com

## Data Flow

### Upload Flow

1. **User uploads document via API Gateway**
   - Client sends POST request with base64-encoded file
   - API Gateway validates request schema
   - Routes to Upload Handler Lambda

2. **Upload Handler processes request**
   - Decodes base64 content
   - Validates file type and size
   - Generates unique document ID (UUID)
   - Stores file in S3: `documents/{id}/{filename}`
   - Adds metadata as S3 object tags
   - Returns confirmation to client

3. **S3 triggers EventBridge**
   - S3 emits "Object Created" event
   - EventBridge captures event via rule
   - Starts Step Functions execution

### Processing Flow

4. **Step Functions orchestrates pipeline**
   - **Stage 1: Parse Document**
     - Lambda downloads file from S3
     - Extracts text based on file type
     - Splits into overlapping chunks
     - Returns parsed data
   
   - **Stage 2: Parallel Processing**
     - **Branch A: RDF Path**
       - Generate RDF triples from text
       - Save RDF to S3 staging area
       - Initiate Neptune bulk loader
       - Poll until load complete
       - Store graph in Neptune
     
     - **Branch B: Embedding Path**
       - For each text chunk:
         - Call Bedrock to generate embedding
         - Collect 1536-dimensional vectors
       - Bulk index to OpenSearch
       - Create k-NN searchable index

5. **Completion**
   - Both branches must succeed
   - Step Functions transitions to Success state
   - Document is now queryable via both Neptune and OpenSearch

## Scalability Considerations

### Vertical Scaling
- **Lambda:** Increase memory allocation (up to 10 GB)
- **Neptune:** Upgrade to larger instance types (db.r6g.*)
- **OpenSearch:** Upgrade to larger instance types

### Horizontal Scaling
- **Lambda:** Auto-scales by default (1000 concurrent executions)
- **Neptune:** Add read replicas for read scaling
- **OpenSearch:** Add more data nodes

### Performance Optimization
- **S3:** Use S3 Transfer Acceleration for large files
- **Lambda:** Use Provisioned Concurrency for predictable latency
- **Neptune:** Use read endpoint for query distribution
- **OpenSearch:** Tune k-NN parameters (ef_search, m)
- **Step Functions:** Use Express Workflows for high-throughput scenarios

## Security Architecture

### Network Security
- **VPC Isolation:** Neptune and OpenSearch in private subnets
- **Security Groups:** Least-privilege access rules
- **No Public IPs:** All resources behind NAT Gateway

### Data Security
- **Encryption at Rest:**
  - S3: SSE-S3
  - Neptune: AWS-managed encryption
  - OpenSearch: AWS-managed encryption
- **Encryption in Transit:**
  - API Gateway: HTTPS only
  - Neptune: TLS
  - OpenSearch: HTTPS only

### Access Control
- **IAM Roles:** Least-privilege policies
- **Neptune IAM Auth:** Database access via IAM
- **API Gateway:** Optional API keys/Cognito auth

### Compliance
- **Audit Logging:** CloudWatch Logs for all operations
- **VPC Flow Logs:** Network traffic monitoring (optional)
- **AWS CloudTrail:** API call logging

## Monitoring and Observability

### Metrics
- **Lambda:** Invocations, duration, errors, throttles
- **Step Functions:** Execution status, duration
- **Neptune:** CPU, memory, connections, queries
- **OpenSearch:** Cluster health, indexing rate, search latency
- **API Gateway:** Requests, latency, 4xx/5xx errors

### Logging
- **CloudWatch Log Groups:**
  - `/aws/lambda/{function-name}`
  - `/aws/stepfunctions/graph-rag-processing`
  - `/aws/apigateway/graph-rag-api`

### Tracing
- **X-Ray:** Distributed tracing for Step Functions
- **Service Map:** Visual representation of service interactions

### Alarms (Recommended)
- Lambda error rate > 5%
- Step Functions failed executions
- Neptune CPU > 80%
- OpenSearch cluster status RED
- API Gateway 5xx error rate > 1%

## Cost Optimization

### Current Configuration
- **Neptune:** db.t3.medium = ~$70/month
- **OpenSearch:** 2× t3.small.search = ~$60/month
- **NAT Gateway:** ~$35/month
- **Other services:** ~$10/month
- **Total:** ~$175/month

### Optimization Strategies
1. **Neptune Serverless:** $2.50/hour when active (good for intermittent use)
2. **Reduce NAT Gateways:** Use 1 instead of 2 (dev only)
3. **Reserved Instances:** Save up to 40% for Neptune/OpenSearch
4. **S3 Intelligent-Tiering:** Automatic cost optimization
5. **Lambda ARM:** Already using (20% cost reduction)
6. **OpenSearch UltraWarm:** Archive old indices

## Future Enhancements

### Query Pipeline
- Implement RAG retrieval Lambda
- Combine vector search (OpenSearch) + graph traversal (Neptune)
- LLM integration for answer generation

### Advanced Features
- Multi-modal embeddings (text + images)
- Incremental updates (update existing documents)
- Batch processing for large document sets
- Real-time streaming ingestion
- Custom ontology management UI

### Operational Improvements
- Multi-region deployment
- Automated failover
- Blue-green deployments
- Canary releases
- Cost allocation tags

## References

- [AWS CDK Best Practices](https://docs.aws.amazon.com/cdk/latest/guide/best-practices.html)
- [Neptune Best Practices](https://docs.aws.amazon.com/neptune/latest/userguide/best-practices.html)
- [OpenSearch k-NN](https://opensearch.org/docs/latest/search-plugins/knn/index/)
- [Amazon Bedrock](https://docs.aws.amazon.com/bedrock/)
- [Step Functions Best Practices](https://docs.aws.amazon.com/step-functions/latest/dg/bp-express.html)

