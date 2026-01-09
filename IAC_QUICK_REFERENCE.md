# IAC Quick Reference - AWS CDK

## CDK Stack Locations

| Stack | File | Line Count |
|-------|------|------------|
| NetworkingStack | `lib/networking-stack.ts` | ~150 |
| StorageStack | `lib/storage-stack.ts` | ~110 |
| DataStoresStack | `lib/datastores-stack.ts` | ~220 |
| ProcessingStack | `lib/processing-stack.ts` | ~350 |
| OrchestrationStack | `lib/orchestration-stack.ts` | ~280 |
| ApiStack | `lib/api-stack.ts` | ~370 |
| **App Entry** | `bin/graph-rag-cdk.ts` | ~120 |

## Essential Commands

```bash
# Setup
npm install                           # Install dependencies
cdk bootstrap                         # First-time setup

# Development
cdk synth                            # Generate CloudFormation
cdk diff                             # Show changes
cdk deploy --all                     # Deploy all stacks
cdk watch StackName                  # Auto-deploy on changes

# Production
export ENVIRONMENT=prod              # Set environment
export SAGEMAKER_ENDPOINT_NAME=...   # Configure
cdk deploy --all --require-approval never  # Deploy

# Cleanup
cdk destroy --all                    # Delete all resources
```

## Stack Props & Exports

### NetworkingStack

**Props**: None (foundation stack)

**Exports**:
```typescript
vpc: ec2.Vpc
neptuneSecurityGroup: ec2.SecurityGroup
openSearchSecurityGroup: ec2.SecurityGroup
lambdaSecurityGroup: ec2.SecurityGroup
```

**CloudFormation Exports**:
- `GraphRag-VpcId`
- `GraphRag-PrivateSubnetIds`
- `GraphRag-NeptuneSecurityGroupId`
- `GraphRag-OpenSearchSecurityGroupId`

### StorageStack

**Props**: None

**Exports**:
```typescript
documentBucket: s3.Bucket
```

**CloudFormation Exports**:
- `GraphRag-DocumentBucketName`
- `GraphRag-DocumentBucketArn`

### DataStoresStack

**Props**:
```typescript
{
  vpc: ec2.Vpc,
  neptuneSecurityGroup: ec2.SecurityGroup,
  openSearchSecurityGroup: ec2.SecurityGroup,
}
```

**Exports**:
```typescript
neptuneCluster: neptune.CfnDBCluster
neptuneInstance: neptune.CfnDBInstance
openSearchDomain: opensearch.Domain
```

**CloudFormation Exports**:
- `GraphRag-NeptuneClusterEndpoint`
- `GraphRag-NeptuneReadEndpoint`
- `GraphRag-OpenSearchDomainEndpoint`

### ProcessingStack

**Props**:
```typescript
{
  vpc: ec2.Vpc,
  documentBucket: s3.Bucket,
  neptuneCluster: neptune.CfnDBCluster,
  openSearchDomain: opensearch.Domain,
  lambdaSecurityGroup: ec2.SecurityGroup,
}
```

**Exports**:
```typescript
documentParserFunction: lambda.Function
rdfGeneratorFunction: lambda.Function
neptuneWriterFunction: lambda.Function
embeddingGeneratorFunction: lambda.Function
openSearchWriterFunction: lambda.Function
```

### OrchestrationStack

**Props**:
```typescript
{
  documentBucket: s3.Bucket,
  documentParserFunction: lambda.Function,
  rdfGeneratorFunction: lambda.Function,
  neptuneWriterFunction: lambda.Function,
  embeddingGeneratorFunction: lambda.Function,
  openSearchWriterFunction: lambda.Function,
}
```

**Exports**:
```typescript
stateMachine: sfn.StateMachine
eventRule: events.Rule
```

### ApiStack

**Props**:
```typescript
{
  documentBucket: s3.Bucket,
}
```

**Exports**:
```typescript
api: apigateway.RestApi
uploadHandler: lambda.Function
```

## Resource Configuration Quick Lookup

### Lambda Functions

| Function | Memory | Timeout | VPC | Environment Variables |
|----------|--------|---------|-----|----------------------|
| Upload Handler | 512 MB | 30s | No | BUCKET, MAX_SIZE, ALLOWED_TYPES |
| Document Parser | 1024 MB | 5m | Yes | BUCKET, MAX_SIZE |
| RDF Generator | 2048 MB | 10m | Yes | BUCKET, ONTOLOGY_VERSION, RDF_FORMAT |
| Neptune Writer | 512 MB | 15m | Yes | BUCKET, NEPTUNE_ENDPOINT, ROLE_ARN |
| Embedding Generator | 512 MB | 5m | Yes | SAGEMAKER_ENDPOINT, DIMENSIONS |
| OpenSearch Writer | 512 MB | 5m | Yes | OPENSEARCH_ENDPOINT, INDEX_NAME |

### Database Instances

| Resource | Instance Type | Storage | Multi-AZ | Cost/Month |
|----------|--------------|---------|----------|------------|
| Neptune Primary | db.t3.medium | Auto-scaling | Yes (with replica) | $70 |
| OpenSearch Node 1 | t3.small.search | 50GB gp3 | Yes | $30 |
| OpenSearch Node 2 | t3.small.search | 50GB gp3 | Yes | $30 |

### Networking

| Resource | Configuration | Cost/Month |
|----------|--------------|------------|
| VPC | 10.0.0.0/16, 2 AZs | $0 |
| NAT Gateway | 1 gateway | $35 |
| Internet Gateway | 1 gateway | $0 |
| Security Groups | 3 groups | $0 |

## Environment Variables

### CDK Deployment

```bash
# Required
export SAGEMAKER_ENDPOINT_NAME=huggingface-embedding-endpoint
export EMBEDDING_DIMENSIONS=768

# Optional
export ENVIRONMENT=dev
export AWS_REGION=us-east-1
export CDK_DEFAULT_ACCOUNT=123456789012
export CDK_DEFAULT_REGION=us-east-1
```

### Lambda Runtime

**Automatically set by CDK**:
```bash
DOCUMENT_BUCKET_NAME=bucket-name
NEPTUNE_ENDPOINT=xxx.neptune.amazonaws.com
NEPTUNE_PORT=8182
OPENSEARCH_ENDPOINT=https://xxx.es.amazonaws.com
AWS_REGION=us-east-1
```

**Customizable per function**: See stack files

## IAM Role Quick Reference

### Lambda Execution Roles

**Base permissions** (all):
- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`

**VPC Lambda** (5 functions):
- `ec2:CreateNetworkInterface`
- `ec2:DescribeNetworkInterfaces`
- `ec2:DeleteNetworkInterface`

**Per function**:
| Function | Additional Permissions |
|----------|----------------------|
| Upload Handler | `s3:PutObject` |
| Document Parser | `s3:GetObject` |
| RDF Generator | `s3:GetObject`, `s3:PutObject` |
| Neptune Writer | `neptune-db:*`, `s3:GetObject` |
| Embedding Generator | `sagemaker:InvokeEndpoint` |
| OpenSearch Writer | `es:ESHttpPost`, `es:ESHttpPut`, `es:ESHttpGet` |

### Service Roles

| Role | Service | Permissions |
|------|---------|-------------|
| Neptune Bulk Load | rds.amazonaws.com | `s3:GetObject` on staging/ |
| Step Functions | states.amazonaws.com | `lambda:InvokeFunction` |
| EventBridge | events.amazonaws.com | `states:StartExecution` |

## Cost Breakdown (Monthly)

| Category | Resource | Cost |
|----------|----------|------|
| **Compute** | 6× Lambda (pay-per-use) | $5-10 |
| | SageMaker ml.m5.large (24/7) | $84 |
| **Database** | Neptune db.t3.medium | $70 |
| | OpenSearch 2× t3.small.search | $60 |
| **Networking** | NAT Gateway | $35 |
| **Storage** | S3 100GB | $3 |
| **Orchestration** | Step Functions | $1-2 |
| **API** | API Gateway | $0.50 |
| **TOTAL** | | **$258-264** |

## Deployment Order

```
1. NetworkingStack      (~10 min)  $35/month
2. StorageStack         (~2 min)   $3/month
   ├─▶ 3. DataStoresStack   (~25 min)  $130/month
   └─▶ 4. ProcessingStack   (~5 min)   $5/month
        └─▶ 5. OrchestrationStack (~3 min)  $1/month
6. ApiStack            (~2 min)   $0.50/month

Total: ~50 minutes    ~$175/month (+ $84 SageMaker)
```

## Common CDK Patterns Used

### Pattern 1: Grant Permissions

```typescript
// High-level grant methods
documentBucket.grantRead(lambdaFunction);
documentBucket.grantWrite(lambdaFunction);
documentBucket.grantReadWrite(lambdaFunction);

// Equivalent to:
lambdaFunction.addToRolePolicy(new iam.PolicyStatement({
  actions: ['s3:GetObject', 's3:ListBucket'],
  resources: [bucket.bucketArn, `${bucket.bucketArn}/*`],
}));
```

### Pattern 2: Cross-Stack References

```typescript
// Export from one stack
new cdk.CfnOutput(this, 'VpcId', {
  value: this.vpc.vpcId,
  exportName: 'GraphRag-VpcId',
});

// Import in another stack (automatic via props)
const vpc = props.vpc;  // Passed from parent

// Or manual import
const vpcId = cdk.Fn.importValue('GraphRag-VpcId');
```

### Pattern 3: Conditional Resources

```typescript
const isProd = process.env.ENVIRONMENT === 'prod';

if (isProd) {
  // Add read replica in production only
  new neptune.CfnDBInstance(this, 'ReadReplica', {...});
}

// Or inline
natGateways: isProd ? 2 : 1,
```

### Pattern 4: Resource Dependencies

```typescript
// Explicit dependency
neptuneInstance.addDependency(neptuneCluster);

// Implicit via references
const endpoint = neptuneCluster.attrEndpoint;  // Creates dependency
```

## Troubleshooting Guide

| Issue | Cause | Solution |
|-------|-------|----------|
| Bootstrap error | CDK not initialized | Run `cdk bootstrap` |
| Resource not found | Wrong deployment order | Check stack dependencies |
| Quota exceeded | AWS account limits | Request quota increase |
| VPC Lambda timeout | No NAT/routes | Check NAT Gateway, route tables |
| IAM permission denied | Missing policy | Check grantXxx() calls |
| Stack stuck | Failed update | Continue rollback in CloudFormation |

## CDK Context Values

**Stored in**: `cdk.json` → `"context"`

```json
{
  "@aws-cdk/aws-iam:minimizePolicies": true,
  "@aws-cdk/core:validateSnapshotRemovalPolicy": true,
  "@aws-cdk/aws-ec2:restrictDefaultSecurityGroup": true
}
```

**Purpose**: Enable/disable CDK feature flags

## Useful CDK Snippets

### Get Current Account/Region

```typescript
this.account  // Current AWS account
this.region   // Current AWS region
```

### Access Stack Name

```typescript
this.stackName  // CloudFormation stack name
this.stackId    // CloudFormation stack ID
```

### Add Dependencies

```typescript
stackB.addDependency(stackA);  // stackB waits for stackA
```

### Tag Resources

```typescript
cdk.Tags.of(resource).add('Key', 'Value');
```

### Remove Resource

```typescript
removalPolicy: cdk.RemovalPolicy.DESTROY  // Delete on stack destroy
removalPolicy: cdk.RemovalPolicy.RETAIN   // Keep on stack destroy
```

## File Structure Legend

```
📁 Project Root
│
├── 🏗️  bin/                   # CDK App
│   └── graph-rag-cdk.ts      # Entry point, stack instantiation
│
├── 🏗️  lib/                   # Stack Definitions
│   ├── networking-stack.ts   # VPC, SG (150 lines)
│   ├── storage-stack.ts      # S3 (110 lines)
│   ├── datastores-stack.ts   # Neptune, OpenSearch (220 lines)
│   ├── processing-stack.ts   # Lambda functions (350 lines)
│   ├── orchestration-stack.ts # Step Functions (280 lines)
│   └── api-stack.ts          # API Gateway (370 lines)
│
├── 📦  lambda/                # Application Code
│   └── */index.py            # Python Lambda handlers
│
├── 🏗️  cdk.json              # CDK Configuration
├── 🏗️  package.json          # NPM Dependencies
├── 🏗️  tsconfig.json         # TypeScript Config
│
├── 📖  IAC_GUIDE.md           # Comprehensive IAC guide
├── 📖  IAC_STACK_REFERENCE.md # This file
└── 📖  IAC_QUICK_REFERENCE.md # Quick reference

Legend:
🏗️  = Infrastructure code
📦  = Application code
📖  = Documentation
```

## CDK vs CloudFormation

| Feature | CDK | CloudFormation |
|---------|-----|----------------|
| Language | TypeScript/Python/Java | JSON/YAML |
| Abstraction | High-level (Constructs) | Low-level (Resources) |
| Reusability | Classes, inheritance | Nested stacks |
| Type Safety | Yes (TypeScript) | No |
| IDE Support | Full IntelliSense | Limited |
| Learning Curve | Moderate | Steep |
| Community | Growing | Mature |

## Resource Limits & Quotas

| Service | Default Limit | How to Increase |
|---------|--------------|-----------------|
| VPCs per region | 5 | Request increase |
| NAT Gateways | 5 per AZ | Request increase |
| Lambda concurrent | 1000 | Request increase |
| Neptune instances | 40 | Request increase |
| OpenSearch domains | 100 | Request increase |
| S3 buckets | 100 | Request increase |
| API Gateway APIs | 600 | Request increase |

**Check limits**:
```bash
aws service-quotas list-service-quotas \
  --service-code lambda \
  --query 'Quotas[?QuotaName==`Concurrent executions`]'
```

## CDK Asset Management

### Asset Locations

```bash
# Local staging
.cdk.staging/               # Temporary, deleted after deploy

# Synthesized templates
cdk.out/                    # CloudFormation templates
├── NetworkingStack.template.json
├── StorageStack.template.json
└── ...

# Bootstrap bucket (in AWS)
s3://cdk-hnb659fds-assets-{account}-{region}/
├── assets/               # Lambda code zips
└── templates/           # CloudFormation templates
```

### Asset Hash

CDK automatically versions assets:
```typescript
code: lambda.Code.fromAsset('lambda/parser')
// Creates: parser-a1b2c3d4.zip (hash-based name)
```

## Testing Infrastructure

### Unit Tests

**File**: `test/graph-rag.test.ts`

```typescript
import { Template } from 'aws-cdk-lib/assertions';

test('Resource Count', () => {
  const template = Template.fromStack(stack);
  template.resourceCountIs('AWS::Lambda::Function', 5);
});

test('Resource Properties', () => {
  template.hasResourceProperties('AWS::Lambda::Function', {
    Runtime: 'python3.12',
    Architectures: ['arm64'],
  });
});
```

**Run**:
```bash
npm test
```

## Updating Resources

### Zero-Downtime Updates

✅ **Safe** (no downtime):
- Lambda code updates
- Lambda environment variables
- Lambda memory/timeout increases
- Security group rule additions
- S3 bucket lifecycle rules
- API Gateway method additions

⚠️ **Requires restart** (brief downtime):
- Neptune instance class change
- OpenSearch instance type change
- OpenSearch storage increase

❌ **Requires replacement** (downtime/data loss):
- VPC CIDR change (create new VPC)
- Neptune encryption toggle
- OpenSearch zone awareness change

### Update Procedure

```bash
# 1. Make changes in code
vim lib/processing-stack.ts

# 2. Review changes
cdk diff GraphRagProcessingStack

# 3. Deploy
cdk deploy GraphRagProcessingStack

# 4. Monitor
aws cloudformation describe-stack-events \
  --stack-name GraphRagProcessingStack
```

## Rollback Procedure

### Manual Rollback

```bash
# CloudFormation console: Select stack → Actions → Roll back

# Or CLI:
aws cloudformation cancel-update-stack \
  --stack-name GraphRagProcessingStack
```

### Automated Rollback

```typescript
// CloudFormation rollback triggers
deployOptions: {
  rollbackConfiguration: {
    monitoringTimeInMinutes: 10,
    rollbackTriggers: [{
      arn: alarm.alarmArn,
      type: 'AWS::CloudWatch::Alarm',
    }],
  },
}
```

## Cost Tags

```typescript
// In bin/graph-rag-cdk.ts
cdk.Tags.of(app).add('Project', 'GraphRAG');
cdk.Tags.of(app).add('Environment', 'dev');
cdk.Tags.of(app).add('CostCenter', 'Engineering');
cdk.Tags.of(app).add('Owner', 'DataTeam');
cdk.Tags.of(app).add('ManagedBy', 'CDK');
```

**View costs by tag**:
```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=Project
```

## Stack State

### View Stack Status

```bash
# All stacks
aws cloudformation list-stacks \
  --query "StackSummaries[?contains(StackName, 'GraphRag')]"

# Specific stack
aws cloudformation describe-stacks \
  --stack-name GraphRagNetworkingStack

# Stack resources
aws cloudformation list-stack-resources \
  --stack-name GraphRagNetworkingStack
```

### Export Values

```bash
# List all exports
aws cloudformation list-exports \
  --query "Exports[?starts_with(Name, 'GraphRag')]"

# Get specific export
aws cloudformation list-exports \
  --query "Exports[?Name=='GraphRag-VpcId'].Value" \
  --output text
```

## CDK Constructs Used

### AWS Construct Library (L2)

| Construct | Import | Purpose |
|-----------|--------|---------|
| `Vpc` | `aws-cdk-lib/aws-ec2` | High-level VPC |
| `Bucket` | `aws-cdk-lib/aws-s3` | S3 with best practices |
| `Function` | `aws-cdk-lib/aws-lambda` | Lambda with IAM |
| `StateMachine` | `aws-cdk-lib/aws-stepfunctions` | Step Functions |
| `RestApi` | `aws-cdk-lib/aws-apigateway` | API Gateway |
| `Domain` | `aws-cdk-lib/aws-opensearchservice` | OpenSearch |
| `SecurityGroup` | `aws-cdk-lib/aws-ec2` | VPC security |

### CloudFormation Resources (L1)

| Construct | Import | Purpose |
|-----------|--------|---------|
| `CfnDBCluster` | `aws-cdk-lib/aws-neptune` | Neptune cluster |
| `CfnDBInstance` | `aws-cdk-lib/aws-neptune` | Neptune instance |
| `CfnDBSubnetGroup` | `aws-cdk-lib/aws-neptune` | Neptune subnets |

## Dependencies & Versions

**package.json**:
```json
{
  "dependencies": {
    "aws-cdk-lib": "2.130.0",
    "constructs": "^10.0.0"
  },
  "devDependencies": {
    "typescript": "~5.3.3",
    "aws-cdk": "2.130.0"
  }
}
```

**Node.js**: 18+ required  
**Python**: 3.12 (Lambda runtime)

## Outputs Summary

### After Deployment

```bash
# Networking
VpcId = vpc-xxxxx
PrivateSubnetIds = subnet-xxx,subnet-yyy

# Storage
DocumentBucketName = graphrag-bucket-xxxxx

# Data Stores
NeptuneClusterEndpoint = xxx.neptune.amazonaws.com
OpenSearchDomainEndpoint = https://xxx.es.amazonaws.com

# API
ApiEndpoint = https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/

# Orchestration
StateMachineArn = arn:aws:states:region:account:stateMachine:graph-rag-processing
```

**Get outputs**:
```bash
aws cloudformation describe-stacks \
  --stack-name GraphRagApiStack \
  --query 'Stacks[0].Outputs'
```

## Quick Debugging

```bash
# View Lambda logs
aws logs tail /aws/lambda/graph-rag-document-parser --follow

# View Step Functions executions
aws stepfunctions list-executions \
  --state-machine-arn <arn>

# Check Neptune status
aws neptune describe-db-clusters \
  --db-cluster-identifier graph-rag-neptune-cluster

# Check OpenSearch status
aws opensearch describe-domain \
  --domain-name graph-rag-opensearch

# Test API
curl -X POST https://api-endpoint/prod/upload \
  -d '{"fileName":"test.txt","fileContent":"dGVzdA=="}'
```

---

**For complete IAC documentation, see [IAC_GUIDE.md](IAC_GUIDE.md)**

