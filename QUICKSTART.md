# Quick Start Guide - Graph RAG Infrastructure

## 🚀 Deploy in 5 Minutes

This guide gets you up and running quickly. For detailed information, see [DEPLOYMENT.md](DEPLOYMENT.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

## Prerequisites

- AWS Account with admin access
- AWS CLI configured (`aws configure`)
- Node.js 18+
- AWS CDK CLI (`npm install -g aws-cdk`)

## Quick Deploy

```bash
# 1. Install dependencies
npm install

# 2. Bootstrap CDK (first time only)
cdk bootstrap

# 3. Deploy all stacks
cdk deploy --all --require-approval never
```

⏱️ **Deployment time:** 20-40 minutes (Neptune and OpenSearch take time to provision)

## Test Your Deployment

After deployment completes, test the upload endpoint:

```bash
# Get your API endpoint from CDK outputs
API_ENDPOINT="<your-api-endpoint-from-outputs>"

# Create test document
echo "Graph RAG test document for ontology processing." > test.txt

# Convert to base64
if [[ "$OSTYPE" == "darwin"* ]]; then
  BASE64_CONTENT=$(base64 -i test.txt)
else
  BASE64_CONTENT=$(base64 -w 0 test.txt)
fi

# Upload document
curl -X POST "${API_ENDPOINT}upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"fileName\": \"test.txt\",
    \"fileContent\": \"$BASE64_CONTENT\",
    \"metadata\": {
      \"keywords\": \"graph,rag,test\",
      \"documentType\": \"demo\"
    }
  }"
```

Expected response:
```json
{
  "message": "Upload successful",
  "documentId": "550e8400-e29b-41d4-a716-446655440000",
  "s3Key": "documents/550e8400-e29b-41d4-a716-446655440000/test.txt"
}
```

## Monitor Processing

1. **Step Functions Console:**
   ```
   https://console.aws.amazon.com/states/home?region=us-east-1
   ```
   Look for "graph-rag-processing" state machine

2. **CloudWatch Logs:**
   ```bash
   # Watch document parser
   aws logs tail /aws/lambda/graph-rag-document-parser --follow
   ```

3. **Check Processing Status:**
   - Should complete in 1-2 minutes for small documents
   - Status: Parse → RDF Generation + Embedding Generation → Complete

## What Happens During Processing?

1. **Parse Document** (10-30 sec)
   - Extracts text from your document
   - Splits into chunks for processing

2. **Parallel Processing** (30-90 sec)
   - **RDF Branch:** Creates knowledge graph → Stores in Neptune
   - **Embedding Branch:** Generates vectors via Bedrock → Indexes in OpenSearch

3. **Complete**
   - Document searchable in both Neptune (graph) and OpenSearch (vector)

## Verify Data

### Check Neptune (Graph Database)

From a Lambda or bastion in VPC:
```python
import urllib3
http = urllib3.PoolManager()
response = http.request('GET', 
    f'https://{NEPTUNE_ENDPOINT}:8182/sparql',
    fields={'query': 'SELECT * WHERE { ?s ?p ?o } LIMIT 10'})
print(response.data)
```

### Check OpenSearch (Vector Search)

From within VPC:
```bash
curl -X GET "https://${OPENSEARCH_ENDPOINT}/document-embeddings/_count"
```

## Important Notes

### ⚠️ Enable Bedrock Access

Before using, enable Amazon Bedrock model access:

1. Go to [Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Click "Model access" in left menu
3. Request access to "Titan Embeddings G1 - Text"
4. Wait for approval (usually instant)

### 💰 Cost Awareness

This infrastructure runs 24/7 services:
- **Neptune:** ~$70/month
- **OpenSearch:** ~$60/month  
- **NAT Gateway:** ~$35/month
- **Total:** ~$175/month

**To save costs:**
- Delete infrastructure when not in use: `cdk destroy --all`
- Use Neptune Serverless (modify code)
- Reduce to 1 NAT Gateway (dev only)

### 🔒 Security

Default configuration:
- ✅ VPC isolation (private subnets)
- ✅ Encryption at rest (S3, Neptune, OpenSearch)
- ✅ HTTPS only
- ⚠️ CORS allows all origins (restrict in production)
- ⚠️ No API authentication (add in production)

## Common Issues

### Issue: Bedrock Access Denied

**Solution:**
```bash
# 1. Enable model access in Bedrock console
# 2. Verify Lambda role has permissions
aws iam get-role-policy --role-name GraphRagProcessingStack-EmbeddingGeneratorFunctionRole* --policy-name default
```

### Issue: Lambda Timeout in VPC

**Cause:** NAT Gateway still provisioning or route tables misconfigured

**Solution:** Wait 5 minutes after deployment completes, try again

### Issue: Neptune Connection Timeout

**Solution:** Ensure Lambda is in correct VPC and security groups allow port 8182

## Next Steps

### Implement Query Pipeline

Add RAG retrieval for answering questions:

1. Create query Lambda that:
   - Takes user question
   - Generates embedding via Bedrock
   - Searches similar chunks in OpenSearch
   - Queries related graph data in Neptune
   - Sends context to LLM for answer generation

2. Add to API Gateway as `POST /query` endpoint

### Add Authentication

Integrate AWS Cognito or API keys:

```typescript
// In api-stack.ts
const authorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'Authorizer', {
  cognitoUserPools: [userPool],
});

uploadResource.addMethod('POST', uploadIntegration, {
  authorizer: authorizer,
  authorizationType: apigateway.AuthorizationType.COGNITO,
});
```

### Custom Domain

Add your own domain:

```typescript
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as route53 from 'aws-cdk-lib/aws-route53';

const domainName = new apigateway.DomainName(this, 'CustomDomain', {
  domainName: 'api.yourdomain.com',
  certificate: certificate,
});
```

## Resources

- 📖 [Full Deployment Guide](DEPLOYMENT.md)
- 🏗️ [Architecture Documentation](ARCHITECTURE.md)  
- 🐛 [Troubleshooting](DEPLOYMENT.md#troubleshooting)
- 💻 [AWS CDK Docs](https://docs.aws.amazon.com/cdk/)
- 🔍 [Neptune Docs](https://docs.aws.amazon.com/neptune/)
- 🔎 [OpenSearch Docs](https://docs.aws.amazon.com/opensearch-service/)

## Cleanup

**⚠️ WARNING: This deletes all data!**

```bash
# Destroy all infrastructure
cdk destroy --all

# Manually delete S3 bucket (has retention policy)
aws s3 rb s3://$(aws s3 ls | grep graphragstoragestack | awk '{print $3}') --force
```

## Support

For issues:
1. Check CloudWatch Logs
2. Review Step Functions execution history
3. Verify VPC connectivity (security groups, route tables)
4. Check service quotas

Happy building! 🎉

