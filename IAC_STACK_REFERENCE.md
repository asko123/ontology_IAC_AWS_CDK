# CDK Stack Reference - Complete Resource Catalog

## Overview

This document provides a **complete reference** for every AWS resource provisioned by each CDK stack, including configurations, dependencies, and customization options.

---

## Table of Contents

1. [NetworkingStack](#networkingstack)
2. [StorageStack](#storagestack)
3. [DataStoresStack](#datastoresstack)
4. [ProcessingStack](#processingstack)
5. [OrchestrationStack](#orchestrationstack)
6. [ApiStack](#apistack)

---

## NetworkingStack

**File**: `lib/networking-stack.ts`  
**Purpose**: VPC and network security infrastructure

### Resources Created

#### 1. VPC (`AWS::EC2::VPC`)

**Construct**: `ec2.Vpc`  
**Logical ID**: `GraphRagVpc`

```typescript
new ec2.Vpc(this, 'GraphRagVpc', {
  vpcName: 'graph-rag-vpc',
  ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
  maxAzs: 2,
  natGateways: 1,
  subnetConfiguration: [...],
  enableDnsHostnames: true,
  enableDnsSupport: true,
})
```

**Configuration**:
- **CIDR**: 10.0.0.0/16 (65,536 IPs)
- **AZs**: 2 for high availability
- **DNS**: Enabled for service discovery
- **Cost**: Free (VPC itself)

**Customization**:
```typescript
// Change CIDR
ipAddresses: ec2.IpAddresses.cidr('172.16.0.0/16')

// Add more AZs
maxAzs: 3

// Add NAT Gateway per AZ (HA)
natGateways: 2  // $70/month vs $35/month for 1
```

#### 2. Subnets

**Public Subnets** (2):
- Type: `AWS::EC2::Subnet`
- CIDR: 10.0.0.0/24, 10.0.2.0/24
- Purpose: NAT Gateways, Internet Gateway
- Route: → Internet Gateway → Internet

**Private Subnets with Egress** (2):
- Type: `AWS::EC2::Subnet`
- CIDR: 10.0.1.0/24, 10.0.3.0/24
- Purpose: Lambda, Neptune, OpenSearch
- Route: → NAT Gateway → Internet

**Isolated Subnets** (2):
- Type: `AWS::EC2::Subnet`
- CIDR: 10.0.4.0/28, 10.0.5.0/28
- Purpose: Future use (no internet)
- Route: None

#### 3. Internet Gateway (`AWS::EC2::InternetGateway`)

**Automatically created by VPC construct**

**Purpose**: Public subnet internet access

#### 4. NAT Gateways (`AWS::EC2::NatGateway`)

**Count**: 1 (configurable to 2)  
**Location**: Public subnets  
**Elastic IPs**: 1 per NAT Gateway  
**Cost**: ~$35/month per gateway

**High Availability Option**:
```typescript
natGateways: 2  // One per AZ
```

#### 5. Route Tables

**Automatically created**:
- Public route table (1)
- Private route table (1-2, depends on NAT count)
- Isolated route table (1)

#### 6. Security Groups (3)

##### Neptune Security Group

**Type**: `AWS::EC2::SecurityGroup`  
**Construct**: `ec2.SecurityGroup`  
**Name**: `neptune-sg`

**Inbound Rules**:
```typescript
// From Lambda
Source: lambdaSecurityGroup
Port: 8182 (TCP)
Description: "Allow Lambda to connect to Neptune"

// From Neptune (self-reference)
Source: neptuneSecurityGroup
Port: 8182 (TCP)
Description: "Neptune cluster communication"
```

**Outbound Rules**: None (default deny)

##### OpenSearch Security Group

**Type**: `AWS::EC2::SecurityGroup`  
**Name**: `opensearch-sg`

**Inbound Rules**:
```typescript
// From Lambda
Source: lambdaSecurityGroup
Port: 443 (TCP)
Description: "Allow Lambda to connect to OpenSearch"

// From OpenSearch (self-reference)
Source: openSearchSecurityGroup
Port: All TCP
Description: "OpenSearch cluster communication"
```

**Outbound Rules**: None (default deny)

##### Lambda Security Group

**Type**: `AWS::EC2::SecurityGroup`  
**Name**: `lambda-sg`

**Inbound Rules**: None

**Outbound Rules**: All (allow Lambda to call AWS APIs, Neptune, OpenSearch)

### Exports

```yaml
Exports:
  GraphRag-VpcId: vpc-xxxxx
  GraphRag-PrivateSubnetIds: subnet-xxx,subnet-yyy
  GraphRag-NeptuneSecurityGroupId: sg-xxxxx
  GraphRag-OpenSearchSecurityGroupId: sg-yyyyy
```

### Customization Options

```typescript
// 1. Change VPC CIDR
ipAddresses: ec2.IpAddresses.cidr('172.16.0.0/16')

// 2. Add more AZs
maxAzs: 3

// 3. Enable VPC Flow Logs
const logGroup = new logs.LogGroup(this, 'VpcFlowLogGroup');
new ec2.FlowLog(this, 'VpcFlowLog', {
  resourceType: ec2.FlowLogResourceType.fromVpc(this.vpc),
  destination: ec2.FlowLogDestination.toCloudWatchLogs(logGroup),
});

// 4. Add VPC Endpoints (reduce NAT costs)
this.vpc.addInterfaceEndpoint('S3Endpoint', {
  service: ec2.InterfaceVpcEndpointAwsService.S3,
});
```

---

## StorageStack

**File**: `lib/storage-stack.ts`  
**Purpose**: Document storage bucket

### Resources Created

#### 1. S3 Bucket (`AWS::S3::Bucket`)

**Construct**: `s3.Bucket`  
**Logical ID**: `DocumentBucket`

```typescript
new s3.Bucket(this, 'DocumentBucket', {
  versioned: true,
  encryption: s3.BucketEncryption.S3_MANAGED,
  blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
  removalPolicy: cdk.RemovalPolicy.RETAIN,
  autoDeleteObjects: false,
  eventBridgeEnabled: true,
  cors: [...],
  lifecycleRules: [...],
})
```

**Configuration**:

**Versioning**:
- Enabled: ✅
- Purpose: Track document changes, rollback capability

**Encryption**:
- Type: SSE-S3 (AWS-managed keys)
- Alternative: SSE-KMS for customer-managed keys
```typescript
encryption: s3.BucketEncryption.KMS,
encryptionKey: kmsKey,
```

**Public Access**: Blocked (all 4 settings)
- BlockPublicAcls: true
- IgnorePublicAcls: true
- BlockPublicPolicy: true
- RestrictPublicBuckets: true

**EventBridge**: Enabled for S3 event notifications

**CORS Configuration**:
```typescript
cors: [{
  allowedMethods: [
    s3.HttpMethods.GET,
    s3.HttpMethods.POST,
    s3.HttpMethods.PUT,
  ],
  allowedOrigins: ['*'],  // TODO: Restrict in production
  allowedHeaders: ['*'],
  exposedHeaders: ['ETag'],
  maxAge: 3000,
}]
```

**Lifecycle Rules**:

Rule 1: Archive old versions
```typescript
{
  id: 'TransitionOldVersionsToGlacier',
  enabled: true,
  noncurrentVersionTransitions: [{
    storageClass: s3.StorageClass.GLACIER,
    transitionAfter: cdk.Duration.days(30),
  }],
  noncurrentVersionExpiration: cdk.Duration.days(90),
}
```

Rule 2: Cleanup incomplete uploads
```typescript
{
  id: 'DeleteIncompleteMultipartUploads',
  enabled: true,
  abortIncompleteMultipartUploadAfter: cdk.Duration.days(7),
}
```

### Bucket Structure

```
s3://bucket-name/
├── documents/              # Uploaded documents
│   └── {document-id}/
│       └── {filename}
├── neptune-staging/        # RDF files for bulk loading
│   └── {document-id}/
│       └── data.ttl
└── ontologies/             # OWL ontology files
    └── graph-rag-ontology.ttl
```

### Exports

```yaml
Exports:
  GraphRag-DocumentBucketName: graphragstoragestack-documentbucketxxxxx
  GraphRag-DocumentBucketArn: arn:aws:s3:::graphragstoragestack-documentbucketxxxxx
```

### Customization Options

```typescript
// 1. Use KMS encryption
const kmsKey = new kms.Key(this, 'BucketKey');
encryption: s3.BucketEncryption.KMS,
encryptionKey: kmsKey,

// 2. Add object lock (compliance)
objectLockEnabled: true,

// 3. Enable access logging
serverAccessLogsBucket: logBucket,
serverAccessLogsPrefix: 'access-logs/',

// 4. Intelligent tiering
lifecycleRules: [{
  transitions: [{
    storageClass: s3.StorageClass.INTELLIGENT_TIERING,
    transitionAfter: cdk.Duration.days(0),
  }],
}]

// 5. Replication (multi-region)
replicationConfiguration: {...}
```

---

## DataStoresStack

**File**: `lib/datastores-stack.ts`  
**Purpose**: Graph and vector databases

### Neptune Resources

#### 1. Neptune Subnet Group (`AWS::Neptune::DBSubnetGroup`)

```typescript
new neptune.CfnDBSubnetGroup(this, 'NeptuneSubnetGroup', {
  dbSubnetGroupName: 'graph-rag-neptune-subnet-group',
  subnetIds: vpc.privateSubnets.map(s => s.subnetId),
})
```

**Configuration**:
- Subnets: All private subnets (2)
- Purpose: Neptune instances must be in DB subnet group

#### 2. Neptune Cluster Parameter Group (`AWS::Neptune::DBClusterParameterGroup`)

```typescript
new neptune.CfnDBClusterParameterGroup(this, 'ClusterParamGroup', {
  family: 'neptune1.3',
  parameters: {
    neptune_enable_audit_log: '0',
    neptune_query_timeout: '120000',
  },
})
```

**Parameters**:
- `neptune_enable_audit_log`: 0 (disabled) or 1 (enabled, costs extra)
- `neptune_query_timeout`: 120000 ms (2 minutes)
- `neptune_enable_slow_query_log`: Optional

#### 3. Neptune DB Cluster (`AWS::Neptune::DBCluster`)

```typescript
new neptune.CfnDBCluster(this, 'NeptuneCluster', {
  dbClusterIdentifier: 'graph-rag-neptune-cluster',
  dbSubnetGroupName: neptuneSubnetGroup.dbSubnetGroupName,
  vpcSecurityGroupIds: [neptuneSecurityGroup.securityGroupId],
  backupRetentionPeriod: 7,
  preferredBackupWindow: '03:00-04:00',
  preferredMaintenanceWindow: 'sun:04:00-sun:05:00',
  storageEncrypted: true,
  iamAuthEnabled: true,
  engineVersion: '1.3.1.0',
})
```

**Configuration**:
- **Engine**: Neptune 1.3.1.0
- **Backup**: 7 days retention
- **Encryption**: Enabled (AWS-managed keys)
- **IAM Auth**: Enabled (more secure than passwords)
- **Multi-AZ**: Automatic with replicas

**Endpoints**:
- Cluster endpoint: Write operations
- Reader endpoint: Read operations (load balancing)

#### 4. Neptune Instance Parameter Group (`AWS::Neptune::DBParameterGroup`)

```typescript
new neptune.CfnDBParameterGroup(this, 'InstanceParamGroup', {
  family: 'neptune1.3',
  parameters: {},
})
```

#### 5. Neptune DB Instance (`AWS::Neptune::DBInstance`)

```typescript
new neptune.CfnDBInstance(this, 'NeptuneInstance', {
  dbInstanceIdentifier: 'graph-rag-neptune-instance-1',
  dbClusterIdentifier: neptuneCluster.dbClusterIdentifier,
  dbInstanceClass: 'db.t3.medium',
})
```

**Configuration**:
- **Instance Class**: db.t3.medium
  - vCPUs: 2
  - Memory: 4 GB
  - Network: Moderate
  - Cost: ~$70/month

**Instance Types**:
| Type | vCPUs | Memory | Cost/Month | Use Case |
|------|-------|--------|------------|----------|
| db.t3.medium | 2 | 4 GB | $70 | Dev/Small |
| db.r6g.large | 2 | 16 GB | $235 | Production |
| db.r6g.xlarge | 4 | 32 GB | $470 | Large scale |

**Add Read Replica**:
```typescript
const readReplica = new neptune.CfnDBInstance(this, 'ReadReplica', {
  dbInstanceIdentifier: 'graph-rag-neptune-instance-2',
  dbClusterIdentifier: this.neptuneCluster.dbClusterIdentifier,
  dbInstanceClass: 'db.t3.medium',
});
```

### OpenSearch Resources

#### 6. OpenSearch Domain (`AWS::OpenSearchService::Domain`)

```typescript
new opensearch.Domain(this, 'OpenSearchDomain', {
  domainName: 'graph-rag-opensearch',
  version: opensearch.EngineVersion.OPENSEARCH_2_11,
  capacity: {
    dataNodes: 2,
    dataNodeInstanceType: 't3.small.search',
    multiAzWithStandbyEnabled: false,
  },
  ebs: {
    enabled: true,
    volumeSize: 50,
    volumeType: ec2.EbsDeviceVolumeType.GP3,
    iops: 3000,
    throughput: 125,
  },
  zoneAwareness: {
    enabled: true,
    availabilityZoneCount: 2,
  },
  vpc: props.vpc,
  vpcSubnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
  securityGroups: [props.openSearchSecurityGroup],
  encryptionAtRest: { enabled: true },
  nodeToNodeEncryption: true,
  enforceHttps: true,
  automatedSnapshotStartHour: 2,
  removalPolicy: cdk.RemovalPolicy.RETAIN,
})
```

**Configuration**:

**Cluster**:
- **Version**: OpenSearch 2.11
- **Nodes**: 2 data nodes
- **Instance**: t3.small.search
  - vCPUs: 1
  - Memory: 2 GB
  - Cost: ~$30/month per node

**Storage**:
- **Type**: EBS gp3
- **Size**: 50 GB per node
- **IOPS**: 3000
- **Throughput**: 125 MiB/s

**High Availability**:
- **Zone Awareness**: 2 AZs
- **Replica**: Automatic (within cluster)

**Security**:
- **Encryption at Rest**: Enabled
- **Node-to-Node Encryption**: Enabled
- **HTTPS**: Enforced
- **Fine-grained Access Control**: Optional (not enabled)

**Instance Types**:
| Type | vCPUs | Memory | Cost/Node/Month | Use Case |
|------|-------|--------|-----------------|----------|
| t3.small.search | 1 | 2 GB | $30 | Dev/Small |
| t3.medium.search | 2 | 4 GB | $60 | Production |
| r6g.large.search | 2 | 16 GB | $145 | Memory-intensive |

**Scaling**:
```typescript
// Add more nodes
capacity: {
  dataNodes: 3,  // Increase nodes
}

// Larger instances
dataNodeInstanceType: 't3.medium.search',

// Multi-AZ with standby (3 AZs)
multiAzWithStandbyEnabled: true,
```

### Exports

```yaml
Exports:
  GraphRag-NeptuneClusterEndpoint: xxx.cluster-xxx.neptune.amazonaws.com
  GraphRag-NeptuneReadEndpoint: xxx.cluster-ro-xxx.neptune.amazonaws.com
  GraphRag-NeptunePort: 8182
  GraphRag-OpenSearchDomainEndpoint: https://xxx.us-east-1.es.amazonaws.com
  GraphRag-OpenSearchDomainArn: arn:aws:es:region:account:domain/graph-rag-opensearch
```

---

## ProcessingStack

**File**: `lib/processing-stack.ts`  
**Purpose**: Lambda processing functions

### Common Configuration

**All Lambda functions share**:

```typescript
const commonEnvironment = {
  DOCUMENT_BUCKET_NAME: documentBucket.bucketName,
  NEPTUNE_ENDPOINT: neptuneCluster.attrEndpoint,
  NEPTUNE_PORT: '8182',
  OPENSEARCH_ENDPOINT: `https://${openSearchDomain.domainEndpoint}`,
  AWS_REGION: this.region,
};
```

**VPC Configuration** (all functions):
```typescript
vpc: props.vpc,
vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
securityGroups: [props.lambdaSecurityGroup],
```

**Runtime**: Python 3.12 (all functions)  
**Architecture**: ARM64 (all functions, 20% cost savings)

### Lambda Functions

#### 1. Document Parser

**Resource**: `AWS::Lambda::Function`  
**Name**: `graph-rag-document-parser`

```typescript
new lambda.Function(this, 'DocumentParserFunction', {
  functionName: 'graph-rag-document-parser',
  runtime: lambda.Runtime.PYTHON_3_12,
  handler: 'index.handler',
  code: lambda.Code.fromAsset('lambda/document-parser'),
  timeout: cdk.Duration.minutes(5),
  memorySize: 1024,
  architecture: lambda.Architecture.ARM_64,
  environment: {
    ...commonEnvironment,
    MAX_FILE_SIZE_MB: '50',
  },
})
```

**IAM Permissions**:
- s3:GetObject on document bucket
- s3:GetObjectTagging

**Trigger**: Step Functions invoke

**Cost**: $0.0000133334 per GB-second (ARM)

#### 2. RDF Generator

**Name**: `graph-rag-rdf-generator`

```typescript
memorySize: 2048,
timeout: cdk.Duration.minutes(10),
environment: {
  ONTOLOGY_SCHEMA_VERSION: '1.0',
  RDF_FORMAT: 'turtle',
}
```

**IAM Permissions**:
- s3:GetObject (read source)
- s3:PutObject (write RDF to staging)

#### 3. Neptune Writer

**Name**: `graph-rag-neptune-writer`

```typescript
memorySize: 512,
timeout: cdk.Duration.minutes(15),
environment: {
  NEPTUNE_LOAD_FROM_S3_ROLE_ARN: neptuneBulkLoadRole.roleArn,
  NEPTUNE_STAGING_PREFIX: 'neptune-staging/',
}
```

**IAM Permissions**:
- neptune-db:connect
- neptune-db:ReadDataViaQuery
- neptune-db:WriteDataViaQuery
- s3:GetObject (staging area)

#### 4. Embedding Generator

**Name**: `graph-rag-embedding-generator`

```typescript
memorySize: 512,
timeout: cdk.Duration.minutes(5),
environment: {
  SAGEMAKER_ENDPOINT_NAME: process.env.SAGEMAKER_ENDPOINT_NAME || 'huggingface-embedding-endpoint',
  EMBEDDING_DIMENSIONS: process.env.EMBEDDING_DIMENSIONS || '768',
  CHUNK_SIZE: '512',
  CHUNK_OVERLAP: '50',
  EMBEDDING_PROVIDER: 'sagemaker',
}
```

**IAM Permissions**:
- sagemaker:InvokeEndpoint (all endpoints in region)

#### 5. OpenSearch Writer

**Name**: `graph-rag-opensearch-writer`

```typescript
memorySize: 512,
timeout: cdk.Duration.minutes(5),
environment: {
  OPENSEARCH_INDEX_NAME: 'document-embeddings',
  KNN_DIMENSIONS: '768',
  KNN_METHOD: 'hnsw',
  KNN_SIMILARITY: 'cosine',
}
```

**IAM Permissions**:
- es:ESHttpPost
- es:ESHttpPut
- es:ESHttpGet

### Additional Resources

#### Neptune Bulk Load Role

**Type**: `AWS::IAM::Role`

```typescript
const neptuneBulkLoadRole = new iam.Role(this, 'NeptuneBulkLoadRole', {
  assumedBy: new iam.ServicePrincipal('rds.amazonaws.com'),
});

documentBucket.grantRead(neptuneBulkLoadRole, 'neptune-staging/*');
```

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "rds.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

**Permissions**:
```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:ListBucket"],
  "Resource": [
    "arn:aws:s3:::bucket-name",
    "arn:aws:s3:::bucket-name/neptune-staging/*"
  ]
}
```

### Exports

```yaml
Outputs:
  DocumentParserFunctionArn: arn:aws:lambda:...
  RdfGeneratorFunctionArn: arn:aws:lambda:...
  NeptuneWriterFunctionArn: arn:aws:lambda:...
  EmbeddingGeneratorFunctionArn: arn:aws:lambda:...
  OpenSearchWriterFunctionArn: arn:aws:lambda:...
```

### Customization Options

```typescript
// 1. Adjust Lambda memory/timeout per function
this.documentParserFunction = new lambda.Function(this, 'DocParser', {
  memorySize: 2048,  // Increase for large PDFs
  timeout: cdk.Duration.minutes(10),  // Increase for complex docs
});

// 2. Add Lambda layers (for shared dependencies)
const rdfLibLayer = new lambda.LayerVersion(this, 'RdfLibLayer', {
  code: lambda.Code.fromAsset('layers/rdflib'),
  compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
});

this.rdfGeneratorFunction = new lambda.Function(this, 'RdfGen', {
  layers: [rdfLibLayer],
});

// 3. Add reserved concurrency (guarantee capacity)
reservedConcurrentExecutions: 10,

// 4. Add provisioned concurrency (reduce cold starts)
this.embeddingGeneratorFunction.addAlias('live', {
  provisionedConcurrentExecutions: 2,
});

// 5. Enable SnapStart (Java only, not Python)
// Not applicable for Python runtime
```

---

## OrchestrationStack

**File**: `lib/orchestration-stack.ts`  
**Purpose**: Workflow orchestration

### Resources Created

#### 1. SQS Dead Letter Queue (`AWS::SQS::Queue`)

```typescript
new sqs.Queue(this, 'ProcessingDlq', {
  queueName: 'graph-rag-processing-dlq',
  retentionPeriod: cdk.Duration.days(14),
  visibilityTimeout: cdk.Duration.seconds(300),
})
```

**Purpose**: Capture failed Step Functions executions

#### 2. CloudWatch Log Group (`AWS::Logs::LogGroup`)

```typescript
new logs.LogGroup(this, 'StateMachineLogGroup', {
  logGroupName: '/aws/stepfunctions/graph-rag-processing',
  retention: logs.RetentionDays.ONE_WEEK,
  removalPolicy: cdk.RemovalPolicy.DESTROY,
})
```

**Purpose**: Step Functions execution logs

#### 3. Step Functions State Machine (`AWS::StepFunctions::StateMachine`)

```typescript
new sfn.StateMachine(this, 'ProcessingStateMachine', {
  stateMachineName: 'graph-rag-processing',
  definitionBody: sfn.DefinitionBody.fromChainable(definition),
  timeout: cdk.Duration.minutes(30),
  tracingEnabled: true,
  logs: {
    destination: logGroup,
    level: sfn.LogLevel.ALL,
    includeExecutionData: true,
  },
})
```

**Workflow States**:

1. **Parse Document** (Task)
   - Type: Lambda invoke
   - Retries: 3 with exponential backoff
   - Catch: All errors → Fail state

2. **Parallel Processing** (Parallel)
   - Branch A: Generate RDF → Write to Neptune
   - Branch B: Generate Embeddings → Write to OpenSearch
   - Both must succeed

3. **Success** (Succeed terminal state)

4. **Failed** (Fail terminal state)

**State Machine Definition** (ASL - Amazon States Language):
```json
{
  "StartAt": "ParseDocument",
  "States": {
    "ParseDocument": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "graph-rag-document-parser",
        "Payload.$": "$"
      },
      "Retry": [{
        "ErrorEquals": ["States.TaskFailed"],
        "IntervalSeconds": 2,
        "MaxAttempts": 3,
        "BackoffRate": 2.0
      }],
      "Next": "ParallelProcessing"
    },
    "ParallelProcessing": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "GenerateRdf",
          "States": {...}
        },
        {
          "StartAt": "GenerateEmbeddings",
          "States": {...}
        }
      ],
      "Next": "ProcessingComplete"
    },
    "ProcessingComplete": {
      "Type": "Succeed"
    }
  }
}
```

#### 4. EventBridge Rule (`AWS::Events::Rule`)

```typescript
new events.Rule(this, 'S3UploadRule', {
  ruleName: 'graph-rag-s3-upload-trigger',
  eventPattern: {
    source: ['aws.s3'],
    detailType: ['Object Created'],
    detail: {
      bucket: {
        name: [documentBucket.bucketName],
      },
    },
  },
})
```

**Event Pattern**:
```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": {
      "name": ["graphragstoragestack-documentbucketxxxxx"]
    }
  }
}
```

**Target**: Step Functions state machine

**Target Configuration**:
```typescript
rule.addTarget(new targets.SfnStateMachine(this.stateMachine, {
  input: events.RuleTargetInput.fromEventPath('$'),
  deadLetterQueue: dlq,
  retryAttempts: 3,
  maxEventAge: cdk.Duration.hours(2),
}))
```

### Exports

```yaml
Outputs:
  StateMachineArn: arn:aws:states:region:account:stateMachine:graph-rag-processing
  StateMachineConsoleUrl: https://console.aws.amazon.com/states/...
  EventRuleName: graph-rag-s3-upload-trigger
  DlqUrl: https://sqs.region.amazonaws.com/account/graph-rag-processing-dlq
```

### Customization Options

```typescript
// 1. Add retry logic
parseDocumentTask.addRetry({
  errors: ['CustomError'],
  interval: cdk.Duration.seconds(5),
  maxAttempts: 5,
  backoffRate: 1.5,
});

// 2. Add catch for specific errors
parseDocumentTask.addCatch(customErrorHandler, {
  errors: ['CustomError'],
  resultPath: '$.errorInfo',
});

// 3. Add choice state for conditional logic
const choice = new sfn.Choice(this, 'CheckFileType');
choice
  .when(sfn.Condition.stringEquals('$.fileType', 'pdf'), pdfPath)
  .when(sfn.Condition.stringEquals('$.fileType', 'docx'), docxPath)
  .otherwise(defaultPath);

// 4. Add wait state
new sfn.Wait(this, 'Wait30Seconds', {
  time: sfn.WaitTime.duration(cdk.Duration.seconds(30)),
});

// 5. Change to Express workflow (high throughput)
stateMachineType: sfn.StateMachineType.EXPRESS,
```

---

## ApiStack

**File**: `lib/api-stack.ts`  
**Purpose**: HTTP API for uploads

### Resources Created

#### 1. Upload Handler Lambda (`AWS::Lambda::Function`)

```typescript
new lambda.Function(this, 'UploadHandlerFunction', {
  functionName: 'graph-rag-upload-handler',
  runtime: lambda.Runtime.PYTHON_3_12,
  handler: 'index.handler',
  code: lambda.Code.fromAsset('lambda/upload-handler'),
  timeout: cdk.Duration.seconds(30),
  memorySize: 512,
  architecture: lambda.Architecture.ARM_64,
  environment: {
    DOCUMENT_BUCKET_NAME: documentBucket.bucketName,
    MAX_FILE_SIZE_MB: '50',
    ALLOWED_FILE_TYPES: 'pdf,docx,csv,txt',
    PRESIGNED_URL_EXPIRY_SECONDS: '3600',
  },
})
```

**IAM Permissions**:
```typescript
documentBucket.grantPut(uploadHandler);
// Grants: s3:PutObject, s3:PutObjectAcl, s3:PutObjectTagging
```

#### 2. API Gateway REST API (`AWS::ApiGateway::RestApi`)

```typescript
new apigateway.RestApi(this, 'GraphRagApi', {
  restApiName: 'Graph RAG Upload API',
  deployOptions: {
    stageName: 'prod',
    loggingLevel: apigateway.MethodLoggingLevel.INFO,
    dataTraceEnabled: true,
    metricsEnabled: true,
    throttlingBurstLimit: 100,
    throttlingRateLimit: 50,
  },
  defaultCorsPreflightOptions: {
    allowOrigins: apigateway.Cors.ALL_ORIGINS,
    allowMethods: apigateway.Cors.ALL_METHODS,
    allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key'],
    allowCredentials: true,
    maxAge: cdk.Duration.hours(1),
  },
  binaryMediaTypes: [
    'application/pdf',
    'application/octet-stream',
    'multipart/form-data',
  ],
})
```

**Configuration**:
- **Stage**: prod
- **Throttling**: 50 req/sec, burst 100
- **Logging**: INFO level, includes data trace
- **CORS**: Enabled for all origins (restrict in production)
- **Binary support**: PDF, DOCX uploads

#### 3. API Resources

**POST /upload**:
```typescript
const uploadResource = this.api.root.addResource('upload');

const uploadIntegration = new apigateway.LambdaIntegration(uploadHandler, {
  proxy: true,
});

uploadResource.addMethod('POST', uploadIntegration, {
  requestValidator: requestValidator,
  requestModels: { 'application/json': uploadRequestModel },
  apiKeyRequired: false,
});
```

**GET /presigned-url**:
```typescript
const presignedUrlResource = this.api.root.addResource('presigned-url');

presignedUrlResource.addMethod('GET', integration, {
  requestParameters: {
    'method.request.querystring.fileName': true,
  },
});
```

#### 4. Request Validator (`AWS::ApiGateway::RequestValidator`)

```typescript
new apigateway.RequestValidator(this, 'UploadRequestValidator', {
  restApi: this.api,
  requestValidatorName: 'upload-request-validator',
  validateRequestBody: true,
  validateRequestParameters: false,
})
```

#### 5. Request Model (`AWS::ApiGateway::Model`)

```typescript
new apigateway.Model(this, 'UploadRequestModel', {
  restApi: this.api,
  contentType: 'application/json',
  modelName: 'UploadRequest',
  schema: {
    type: apigateway.JsonSchemaType.OBJECT,
    required: ['fileName', 'fileContent'],
    properties: {
      fileName: {
        type: apigateway.JsonSchemaType.STRING,
        minLength: 1,
        maxLength: 255,
      },
      fileContent: {
        type: apigateway.JsonSchemaType.STRING,
        description: 'Base64-encoded file content',
      },
      metadata: {
        type: apigateway.JsonSchemaType.OBJECT,
      },
    },
  },
})
```

### Exports

```yaml
Outputs:
  ApiEndpoint: https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/
  UploadEndpoint: https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/upload
  PresignedUrlEndpoint: https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/presigned-url
  ApiId: xxxxx
```

### Customization Options

```typescript
// 1. Add API key authentication
const apiKey = this.api.addApiKey('GraphRagApiKey');
const usagePlan = this.api.addUsagePlan('UsagePlan', {
  throttle: { rateLimit: 100, burstLimit: 200 },
  quota: { limit: 10000, period: apigateway.Period.MONTH },
});
usagePlan.addApiKey(apiKey);

uploadResource.addMethod('POST', integration, {
  apiKeyRequired: true,  // Require API key
});

// 2. Add Cognito authorizer
const authorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'Auth', {
  cognitoUserPools: [userPool],
});

uploadResource.addMethod('POST', integration, {
  authorizer: authorizer,
  authorizationType: apigateway.AuthorizationType.COGNITO,
});

// 3. Add custom domain
const domainName = new apigateway.DomainName(this, 'CustomDomain', {
  domainName: 'api.yourdomain.com',
  certificate: certificate,
});

// 4. Add WAF (Web Application Firewall)
const webAcl = new wafv2.CfnWebACL(this, 'ApiWaf', {
  scope: 'REGIONAL',
  defaultAction: { allow: {} },
  rules: [...],
});

new wafv2.CfnWebACLAssociation(this, 'WafAssociation', {
  resourceArn: this.api.deploymentStage.stageArn,
  webAclArn: webAcl.attrArn,
});
```

---

## Resource Tags

### Applied to All Resources

```typescript
// In bin/graph-rag-cdk.ts
cdk.Tags.of(app).add('Project', 'GraphRAG');
cdk.Tags.of(app).add('ManagedBy', 'CDK');
cdk.Tags.of(app).add('Environment', process.env.ENVIRONMENT || 'dev');
```

### Per-Stack Tags

```typescript
cdk.Tags.of(networkingStack).add('Layer', 'Networking');
cdk.Tags.of(dataStoresStack).add('Layer', 'Data');
```

### Cost Allocation Tags

```typescript
cdk.Tags.of(app).add('CostCenter', 'Engineering');
cdk.Tags.of(app).add('Owner', 'DataTeam');
```

---

## Complete Resource List by Type

### Compute
- 6× Lambda Functions (Python 3.12, ARM64)
- 1× Step Functions State Machine

### Networking
- 1× VPC (10.0.0.0/16)
- 6× Subnets (2 public, 2 private, 2 isolated)
- 1× Internet Gateway
- 1-2× NAT Gateways
- 3× Security Groups
- 4× Route Tables (auto-created)

### Storage
- 1× S3 Bucket (versioned, encrypted)

### Database
- 1× Neptune DB Cluster
- 1× Neptune DB Instance (primary)
- 1× Neptune Subnet Group
- 2× Neptune Parameter Groups
- 1× OpenSearch Domain (2 nodes, 2 AZs)

### Integration
- 1× API Gateway REST API
- 1× EventBridge Rule
- 1× SQS Queue (DLQ)

### IAM
- 6× Lambda Execution Roles (auto-created)
- 1× Neptune Bulk Load Role
- 1× Step Functions Execution Role (auto-created)
- 1× EventBridge Target Role (auto-created)

### Monitoring
- 8× CloudWatch Log Groups (auto-created)
- 1× Step Functions Log Group (explicit)

### **Total**: ~35 AWS resources

---

## Quick Reference Table

| Stack | Primary Resources | Dependencies | Deploy Time | Monthly Cost |
|-------|-------------------|--------------|-------------|--------------|
| NetworkingStack | VPC, Security Groups | None | ~10 min | $35 |
| StorageStack | S3 Bucket | None | ~2 min | $3-5 |
| DataStoresStack | Neptune, OpenSearch | NetworkingStack | ~25 min | $130 |
| ProcessingStack | 5× Lambda | All above | ~5 min | $5-10 |
| OrchestrationStack | Step Functions | ProcessingStack | ~3 min | $1-2 |
| ApiStack | API Gateway, Lambda | StorageStack | ~2 min | $0.50 |
| **TOTAL** | **~35 resources** | | **~50 min** | **~$175** |

*Plus SageMaker endpoint: $84/month (deployed separately)*

---

This IAC documentation provides complete reference for managing, deploying, and customizing your Graph RAG infrastructure using AWS CDK.

