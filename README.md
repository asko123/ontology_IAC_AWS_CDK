# Graph RAG Infrastructure with AWS CDK

## Overview
This project provisions a complete Graph RAG (Retrieval Augmented Generation) infrastructure on AWS using CDK (TypeScript). The system enables document upload, ontology generation, graph storage in Neptune, and vector search with OpenSearch.

## Architecture
- **Upload**: API Gateway → Lambda → S3 → EventBridge
- **Processing**: Step Functions orchestrates document parsing, RDF generation, Neptune ingestion, and embedding creation
- **Storage**: Amazon Neptune (graph relationships), OpenSearch (full text + vectors), S3 (documents)

### Data Separation Strategy ⚡
- **Neptune**: Stores document metadata, entity relationships, chunk references (NOT full text)
- **OpenSearch**: Stores full chunk text and vector embeddings for search
- **Benefit**: 36% reduction in Neptune storage, 4-5x faster graph queries, no data duplication

📖 **See**: [DATA_SEPARATION_STRATEGY.md](DATA_SEPARATION_STRATEGY.md) for complete details

## 🏗️ Infrastructure as Code (IAC) Documentation

**Complete IAC documentation suite** (2,250+ lines) covering all AWS CDK implementation aspects:

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[IAC_INDEX.md](IAC_INDEX.md)** 📑 | Navigation & documentation index | Find what you need |
| **[IAC_QUICK_REFERENCE.md](IAC_QUICK_REFERENCE.md)** ⚡ | Commands & quick lookup | Daily operations |
| **[IAC_GUIDE.md](IAC_GUIDE.md)** 📖 | Comprehensive IAC guide | Understanding & customization |
| **[IAC_STACK_REFERENCE.md](IAC_STACK_REFERENCE.md)** 📋 | Complete resource catalog | Resource details & config |

**6 CDK Stacks** | **47 AWS Resources** | **1,600 lines of infrastructure code**

👉 **New to CDK?** Start with [IAC_QUICK_REFERENCE.md](IAC_QUICK_REFERENCE.md)  
👉 **Need details?** See [IAC_GUIDE.md](IAC_GUIDE.md) for comprehensive coverage

## Prerequisites
- Node.js 18+ and npm
- AWS CLI configured with appropriate credentials
- AWS CDK CLI: `npm install -g aws-cdk`

## Installation
```bash
npm install
```

## Configuration
Edit `cdk.json` or set environment variables:
- `ALLOWED_ORIGINS`: CORS origins for API (default: '*')
- `VPC_CIDR`: VPC CIDR block (default: '10.0.0.0/16')

## Deployment
```bash
# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy all stacks
cdk deploy --all

# Deploy specific stack
cdk deploy GraphRagNetworkingStack
```

## Outputs
After deployment, note the outputs:
- `ApiEndpoint`: Upload API endpoint
- `S3BucketName`: Document storage bucket
- `NeptuneEndpoint`: Neptune cluster endpoint
- `OpenSearchEndpoint`: OpenSearch domain endpoint

## Usage

### Upload Document
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"fileName":"policy.pdf","metadata":{"keywords":"compliance,security"},"fileContent":"<base64-encoded-content>"}' \
  https://<API_ID>.execute-api.<REGION>.amazonaws.com/prod/upload
```

### Query (Future Enhancement)
The query pipeline requires additional Lambda functions for RAG retrieval.

## OWL Ontology & Model-Driven Graphs 🆕

This system implements **AWS best practices** for model-driven graphs using **OWL (Web Ontology Language)** in Amazon Neptune.

Based on: [Model-driven graphs using OWL in Amazon Neptune](https://aws.amazon.com/blogs/database/model-driven-graphs-using-owl-in-amazon-neptune/)

### Features
- ✅ **Formal OWL ontology** (`ontologies/graph-rag-ontology.ttl`)
- ✅ **Automatic validation** against ontology before loading to Neptune
- ✅ **Standard W3C vocabularies** (FOAF, Dublin Core, SKOS)
- ✅ **OWL restrictions** (cardinality, domains, ranges)
- ✅ **SPARQL-based validation** Lambda function
- ✅ **Inference support** (inverse properties, subclasses)

### Documentation
- **[ONTOLOGY_GUIDE.md](ONTOLOGY_GUIDE.md)** - Complete guide to using the ontology
- **[ONTOLOGY_UPLIFTS.md](ONTOLOGY_UPLIFTS.md)** - AWS blog implementation details
- **[ontologies/graph-rag-ontology.ttl](ontologies/graph-rag-ontology.ttl)** - The formal ontology

### Quick Start
```sparql
# Query documents using ontology
PREFIX : <http://graph-rag.example.com/ontology#>

SELECT ?doc ?fileName ?chunk
WHERE {
    ?doc a :Document ;
         :hasFileName ?fileName ;
         :hasChunk ?chunk .
}
```

## Project Structure
```
├── bin/
│   └── graph-rag-cdk.ts          # CDK app entry point
├── lib/
│   ├── networking-stack.ts        # VPC, subnets, security groups
│   ├── storage-stack.ts           # S3 bucket configuration
│   ├── datastores-stack.ts        # Neptune and OpenSearch
│   ├── processing-stack.ts        # Lambda functions for processing
│   ├── orchestration-stack.ts     # Step Functions and EventBridge
│   └── api-stack.ts               # API Gateway and upload handler
├── lambda/
│   ├── upload-handler/            # File upload handler
│   ├── document-parser/           # Document parsing
│   ├── rdf-generator/             # RDF/ontology generation
│   ├── ontology-validator/        # 🆕 OWL ontology validation
│   ├── neptune-writer/            # Neptune ingestion
│   ├── embedding-generator/       # Vector embedding generation (SageMaker)
│   └── opensearch-writer/         # OpenSearch indexing
├── ontologies/
│   └── graph-rag-ontology.ttl    # 🆕 Formal OWL ontology
├── ONTOLOGY_GUIDE.md             # 🆕 Ontology usage guide
├── ONTOLOGY_UPLIFTS.md           # 🆕 AWS blog implementation
└── cdk.json                       # CDK configuration
```

## Cleanup
```bash
# Destroy all resources (WARNING: Deletes data)
cdk destroy --all
```

## Cost Considerations
- Neptune and OpenSearch clusters run 24/7 (major cost components)
- Consider Neptune Serverless for intermittent workloads
- Use S3 lifecycle policies for long-term cost reduction
- Lambda and Step Functions are pay-per-use

## Security
- All traffic between services uses VPC private subnets
- IAM roles follow least-privilege principle
- S3 bucket encryption enabled
- OpenSearch fine-grained access control (optional, can be enabled)

## Monitoring
- CloudWatch Logs for all Lambda functions and Step Functions
- CloudWatch Alarms for error rates (configure in stacks)
- X-Ray tracing (can be enabled)

## Future Enhancements
- Query pipeline implementation
- SageMaker endpoint integration for custom models
- Metadata schema validation
- Multi-region replication
- Cost optimization with Savings Plans

