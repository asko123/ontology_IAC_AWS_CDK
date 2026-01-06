# Deployment Guide - Graph RAG Infrastructure

## Prerequisites

Before deploying this infrastructure, ensure you have:

1. **AWS Account** with appropriate permissions
   - IAM permissions to create VPC, Lambda, S3, Neptune, OpenSearch, etc.
   - Sufficient service quotas (especially for Neptune and OpenSearch)

2. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```

3. **Node.js** 18 or higher
   ```bash
   node --version  # Should be 18.x or higher
   ```

4. **AWS CDK CLI** installed globally
   ```bash
   npm install -g aws-cdk
   cdk --version
   ```

5. **Python 3.12** (for Lambda functions)
   ```bash
   python3 --version
   ```

## Initial Setup

### 1. Clone and Install Dependencies

```bash
cd /path/to/project
npm install
```

### 2. Bootstrap CDK (First Time Only)

Bootstrap CDK in your AWS account and region:

```bash
cdk bootstrap aws://ACCOUNT-NUMBER/REGION
```

Example:
```bash
cdk bootstrap aws://123456789012/us-east-1
```

### 3. Configure Environment Variables (Optional)

You can customize deployment by setting environment variables:

```bash
export ENVIRONMENT=dev
export AWS_REGION=us-east-1
```

## Deployment Steps

### Step 1: Synthesize CloudFormation Templates

Preview the CloudFormation templates that will be generated:

```bash
cdk synth
```

This creates templates in `cdk.out/` directory.

### Step 2: Review Changes (Recommended)

See what resources will be created/modified:

```bash
cdk diff
```

### Step 3: Deploy All Stacks

Deploy all stacks in dependency order:

```bash
cdk deploy --all --require-approval never
```

Or deploy interactively (prompts for approval):

```bash
cdk deploy --all
```

**Note:** Initial deployment takes 20-40 minutes due to Neptune and OpenSearch cluster provisioning.

### Step 4: Deploy Individual Stacks (Alternative)

You can deploy stacks individually:

```bash
# Deploy in order (respecting dependencies)
cdk deploy GraphRagNetworkingStack
cdk deploy GraphRagStorageStack
cdk deploy GraphRagDataStoresStack
cdk deploy GraphRagProcessingStack
cdk deploy GraphRagOrchestrationStack
cdk deploy GraphRagApiStack
```

## Post-Deployment Configuration

### 1. Note Stack Outputs

After deployment, CDK outputs important information:

```
Outputs:
GraphRagApiStack.ApiEndpoint = https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/
GraphRagDataStoresStack.NeptuneClusterEndpoint = xxx.cluster-xxx.us-east-1.neptune.amazonaws.com
GraphRagDataStoresStack.OpenSearchDomainEndpoint = https://xxx.us-east-1.es.amazonaws.com
GraphRagStorageStack.DocumentBucketName = graphragstoragestack-documentbucketxxx
GraphRagOrchestrationStack.StateMachineArn = arn:aws:states:us-east-1:xxx:stateMachine:xxx
```

Save these values for later use.

### 2. Install Lambda Dependencies (If Using Advanced Libraries)

If you uncommented advanced libraries in Lambda requirements.txt files:

```bash
# For each Lambda function directory
cd lambda/document-parser
pip install -r requirements.txt -t .
cd ../..
```

Then redeploy the processing stack:

```bash
cdk deploy GraphRagProcessingStack
```

### 3. Enable Bedrock Model Access

To use Bedrock for embeddings, enable model access in AWS Console:

1. Go to AWS Bedrock console
2. Navigate to "Model access"
3. Request access to "Titan Embeddings G1 - Text"
4. Wait for approval (usually instant)

### 4. Initialize OpenSearch Index (Optional)

The OpenSearch writer Lambda automatically creates the index on first use.
To pre-create it manually:

```bash
# Get OpenSearch endpoint from outputs
OPENSEARCH_ENDPOINT="https://xxx.us-east-1.es.amazonaws.com"

# Create index (from within VPC or use port forwarding)
curl -X PUT "$OPENSEARCH_ENDPOINT/document-embeddings" \
  -H "Content-Type: application/json" \
  -d @opensearch-index-config.json
```

## Testing the Deployment

### 1. Test Upload Endpoint

```bash
# Get API endpoint from outputs
API_ENDPOINT="https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/"

# Create a test file
echo "This is a test document for Graph RAG system." > test.txt
BASE64_CONTENT=$(base64 test.txt)

# Upload via API
curl -X POST "${API_ENDPOINT}upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"fileName\": \"test.txt\",
    \"fileContent\": \"$BASE64_CONTENT\",
    \"metadata\": {
      \"keywords\": \"test,demo\",
      \"documentType\": \"test\"
    }
  }"
```

Expected response:
```json
{
  "message": "Upload successful",
  "documentId": "uuid-here",
  "s3Key": "documents/uuid/test.txt",
  "fileName": "test.txt"
}
```

### 2. Monitor Step Functions Execution

1. Go to AWS Step Functions console
2. Find "graph-rag-processing" state machine
3. View recent executions
4. Monitor progress through workflow

### 3. Verify Data in Neptune

Connect to Neptune from a bastion host or Lambda:

```python
import boto3
from urllib3 import PoolManager

http = PoolManager()
response = http.request(
    'GET',
    f'https://{NEPTUNE_ENDPOINT}:8182/sparql',
    fields={'query': 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10'}
)
print(response.data.decode('utf-8'))
```

### 4. Verify Data in OpenSearch

Query OpenSearch from within VPC:

```bash
curl -X GET "$OPENSEARCH_ENDPOINT/document-embeddings/_search?size=5" \
  -H "Content-Type: application/json"
```

## Monitoring and Logs

### CloudWatch Logs

All Lambda functions and Step Functions log to CloudWatch:

```bash
# View logs for a specific Lambda
aws logs tail /aws/lambda/graph-rag-document-parser --follow

# View Step Functions logs
aws logs tail /aws/stepfunctions/graph-rag-processing --follow
```

### Step Functions Execution History

View execution details in AWS Console:
https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines

### Dead Letter Queue

Check for failed events:

```bash
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name graph-rag-processing-dlq --query 'QueueUrl' --output text)
```

## Cost Estimation

Estimated monthly costs (us-east-1 region):

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| Neptune | db.t3.medium, 1 instance | ~$70 |
| OpenSearch | t3.small.search, 2 nodes | ~$60 |
| VPC | NAT Gateway | ~$35 |
| S3 | 100GB storage, 1000 requests | ~$3 |
| Lambda | 1000 invocations/month | ~$5 |
| API Gateway | 1000 requests | ~$0.01 |
| **Total** | | **~$173/month** |

**Cost optimization tips:**
- Use Neptune Serverless for intermittent workloads
- Reduce NAT Gateway count to 1 (dev only)
- Enable S3 Intelligent-Tiering
- Use Lambda ARM architecture (already configured)

## Troubleshooting

### Issue: CDK Deploy Fails with Quota Error

**Solution:** Request service quota increases:
- Neptune instances
- OpenSearch domains
- VPC resources (Elastic IPs for NAT Gateway)

### Issue: Lambda Function Timeout

**Solution:** Increase timeout in `lib/processing-stack.ts`:
```typescript
timeout: cdk.Duration.minutes(15),  // Increase as needed
```

### Issue: Neptune Connection Timeout

**Cause:** Lambda not in correct VPC subnet or security group misconfigured.

**Solution:** Verify Lambda security group can access Neptune security group on port 8182.

### Issue: OpenSearch Index Creation Fails

**Cause:** k-NN plugin not enabled or incorrect index configuration.

**Solution:** Verify OpenSearch version 2.11+ and k-NN plugin enabled (default in managed OpenSearch).

### Issue: Bedrock Access Denied

**Cause:** Model access not enabled or Lambda role missing permissions.

**Solution:**
1. Enable Bedrock model access in AWS Console
2. Verify Lambda role has `bedrock:InvokeModel` permission

## Cleanup

To delete all resources:

```bash
# WARNING: This deletes all data!
cdk destroy --all
```

Or delete individual stacks in reverse order:

```bash
cdk destroy GraphRagApiStack
cdk destroy GraphRagOrchestrationStack
cdk destroy GraphRagProcessingStack
cdk destroy GraphRagDataStoresStack
cdk destroy GraphRagStorageStack
cdk destroy GraphRagNetworkingStack
```

**Note:** S3 bucket has `RETAIN` policy by default. Delete manually:

```bash
aws s3 rb s3://BUCKET-NAME --force
```

Neptune and OpenSearch also have retention policies. Verify deletion in console.

## Next Steps

After successful deployment:

1. **Implement Query Pipeline**: Add Lambda functions for RAG retrieval
2. **Add Authentication**: Integrate Cognito or API keys
3. **Custom Domain**: Configure Route 53 and ACM certificate
4. **Monitoring**: Set up CloudWatch dashboards and alarms
5. **Backup Strategy**: Configure automated backups for Neptune and OpenSearch
6. **CI/CD Pipeline**: Set up automated deployments with GitHub Actions or CodePipeline

## Support and Documentation

- AWS CDK Documentation: https://docs.aws.amazon.com/cdk/
- Neptune Documentation: https://docs.aws.amazon.com/neptune/
- OpenSearch Documentation: https://docs.aws.amazon.com/opensearch-service/
- Bedrock Documentation: https://docs.aws.amazon.com/bedrock/

For issues, check CloudWatch Logs and Step Functions execution history.

