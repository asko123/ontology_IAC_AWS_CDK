# Infrastructure as Code (IAC) - Documentation Index

## 📚 Complete IAC Documentation Suite

This project includes **comprehensive Infrastructure as Code documentation** covering all aspects of the AWS CDK implementation.

---

## 🎯 Start Here

### New to the Project?
👉 **[IAC_QUICK_REFERENCE.md](IAC_QUICK_REFERENCE.md)** - Essential commands, configs, and quick lookup tables

### Want Complete Details?
👉 **[IAC_GUIDE.md](IAC_GUIDE.md)** - Comprehensive guide covering all aspects

### Need Resource Details?
👉 **[IAC_STACK_REFERENCE.md](IAC_STACK_REFERENCE.md)** - Complete catalog of every AWS resource

---

## 📖 Documentation Structure

### 1. **IAC_QUICK_REFERENCE.md** (Quick Lookup)
**450 lines** | ⏱️ **5 min read**

**What's Inside:**
- ✅ Essential CDK commands
- ✅ Stack props and exports
- ✅ Resource configuration tables
- ✅ Cost breakdown
- ✅ Environment variables
- ✅ IAM roles quick reference
- ✅ Troubleshooting table

**Use When:**
- Need a quick command
- Looking up a configuration value
- Checking cost estimates
- Debugging common issues

### 2. **IAC_GUIDE.md** (Comprehensive Guide)
**800+ lines** | ⏱️ **30 min read**

**What's Inside:**
- ✅ Complete stack architecture
- ✅ Resource inventory with costs
- ✅ IAM roles and permissions detail
- ✅ Network architecture explained
- ✅ Configuration management
- ✅ Deployment procedures
- ✅ Infrastructure update patterns
- ✅ Cost optimization strategies
- ✅ CDK best practices
- ✅ CI/CD integration examples
- ✅ Troubleshooting guide

**Use When:**
- First-time deployment
- Understanding architecture decisions
- Making infrastructure changes
- Setting up CI/CD
- Implementing best practices

### 3. **IAC_STACK_REFERENCE.md** (Resource Catalog)
**1000+ lines** | ⏱️ **Reference**

**What's Inside:**
- ✅ Every CDK stack detailed
- ✅ Every AWS resource documented
- ✅ Complete configuration options
- ✅ Customization examples
- ✅ CloudFormation template snippets
- ✅ Resource ARN patterns
- ✅ Exports and imports

**Use When:**
- Need exact resource configuration
- Customizing a specific resource
- Understanding resource dependencies
- Writing infrastructure tests
- Troubleshooting specific resources

---

## 🏗️ CDK Code Files

### Core Infrastructure Code

| File | Purpose | Lines | Complexity |
|------|---------|-------|------------|
| **bin/graph-rag-cdk.ts** | App entry point | 120 | ⭐ Simple |
| **lib/networking-stack.ts** | VPC & Security | 150 | ⭐⭐ Medium |
| **lib/storage-stack.ts** | S3 configuration | 110 | ⭐ Simple |
| **lib/datastores-stack.ts** | Neptune & OpenSearch | 220 | ⭐⭐⭐ Complex |
| **lib/processing-stack.ts** | Lambda functions | 350 | ⭐⭐⭐ Complex |
| **lib/orchestration-stack.ts** | Step Functions | 280 | ⭐⭐⭐ Complex |
| **lib/api-stack.ts** | API Gateway | 370 | ⭐⭐ Medium |

**Total**: ~1,600 lines of TypeScript infrastructure code

### Configuration Files

| File | Purpose |
|------|---------|
| **package.json** | CDK and TypeScript dependencies |
| **cdk.json** | CDK app configuration, feature flags |
| **tsconfig.json** | TypeScript compiler options |
| **.gitignore** | Exclude node_modules, cdk.out |

---

## 🎓 Learning Path

### Beginner (Never used CDK)

1. Read **[QUICKSTART.md](QUICKSTART.md)** (5 min)
2. Skim **[IAC_QUICK_REFERENCE.md](IAC_QUICK_REFERENCE.md)** (10 min)
3. Deploy: `npm install && cdk bootstrap && cdk deploy --all`
4. Explore deployed resources in AWS Console

### Intermediate (Some CDK experience)

1. Read **[IAC_GUIDE.md](IAC_GUIDE.md)** sections 1-5 (20 min)
2. Review **[IAC_STACK_REFERENCE.md](IAC_STACK_REFERENCE.md)** for your use case
3. Make configuration changes
4. Deploy and test

### Advanced (Customizing infrastructure)

1. Read complete **[IAC_GUIDE.md](IAC_GUIDE.md)** (30 min)
2. Study **[IAC_STACK_REFERENCE.md](IAC_STACK_REFERENCE.md)** in depth
3. Review CDK code in `lib/*.ts`
4. Implement custom resources
5. Add tests in `test/`

---

## 📊 Documentation Statistics

### IAC Documentation

| Document | Lines | Topics | Diagrams |
|----------|-------|--------|----------|
| IAC_GUIDE.md | 800+ | 11 | 3 |
| IAC_STACK_REFERENCE.md | 1000+ | 6 stacks | Code snippets |
| IAC_QUICK_REFERENCE.md | 450+ | Quick lookup | Tables |
| **Total IAC Docs** | **2,250+** | | |

### Complete Project Documentation

| Category | Files | Lines | Purpose |
|----------|-------|-------|---------|
| **IAC** | 3 | 2,250+ | Infrastructure code docs |
| **Ontology** | 5 | 2,550+ | OWL ontology guides |
| **Architecture** | 3 | 1,800+ | System architecture |
| **Deployment** | 3 | 1,100+ | Setup and deployment |
| **Code** | 6 stacks + 6 Lambda | 2,500+ | TypeScript + Python |
| **TOTAL** | **26 files** | **10,200+ lines** | Production-ready |

---

## 🔍 Find What You Need

### By Task

| Task | Documentation |
|------|---------------|
| **First-time setup** | QUICKSTART.md → IAC_GUIDE.md (Setup) |
| **Deploy infrastructure** | IAC_GUIDE.md (Deployment) → IAC_QUICK_REFERENCE.md |
| **Understand architecture** | ARCHITECTURE.md → ARCHITECTURE_DIAGRAM.md |
| **Modify resources** | IAC_STACK_REFERENCE.md → lib/*.ts code |
| **Troubleshoot** | IAC_GUIDE.md (Troubleshooting) → DEPLOYMENT.md |
| **Optimize costs** | IAC_GUIDE.md (Cost) → IAC_STACK_REFERENCE.md |
| **Use ontology** | ONTOLOGY_GUIDE.md → ONTOLOGY_QUICK_REFERENCE.md |
| **Understand data flow** | DATA_SEPARATION_STRATEGY.md |

### By AWS Service

| Service | CDK Stack | Documentation | Config File |
|---------|-----------|---------------|-------------|
| **VPC** | NetworkingStack | IAC_GUIDE.md §6 | lib/networking-stack.ts |
| **S3** | StorageStack | IAC_STACK_REFERENCE.md | lib/storage-stack.ts |
| **Neptune** | DataStoresStack | IAC_STACK_REFERENCE.md | lib/datastores-stack.ts |
| **OpenSearch** | DataStoresStack | IAC_STACK_REFERENCE.md | lib/datastores-stack.ts |
| **Lambda** | ProcessingStack | IAC_STACK_REFERENCE.md | lib/processing-stack.ts |
| **Step Functions** | OrchestrationStack | IAC_GUIDE.md §1.5 | lib/orchestration-stack.ts |
| **API Gateway** | ApiStack | IAC_STACK_REFERENCE.md | lib/api-stack.ts |
| **SageMaker** | External | SAGEMAKER_SETUP.md | N/A (pre-deployed) |

### By Question

| Question | Answer Location |
|----------|-----------------|
| How do I deploy? | IAC_QUICK_REFERENCE.md → Essential Commands |
| What resources are created? | IAC_STACK_REFERENCE.md → Resource Catalog |
| How much does it cost? | IAC_QUICK_REFERENCE.md → Cost Breakdown |
| How do I customize X? | IAC_STACK_REFERENCE.md → {Stack} → Customization |
| What IAM roles exist? | IAC_GUIDE.md § 4 OR IAC_QUICK_REFERENCE.md |
| How are stacks connected? | IAC_GUIDE.md § 3 → Stack Dependencies |
| How do I update? | IAC_GUIDE.md § 8 → Infrastructure Updates |
| What if deployment fails? | IAC_GUIDE.md § 11 → Troubleshooting |
| How do I test? | IAC_GUIDE.md § 12 → Infrastructure Testing |
| Can I use CI/CD? | IAC_GUIDE.md § 13 → CI/CD Integration |

---

## 🎯 Common Workflows

### Workflow 1: Initial Deployment

```bash
# Step 1: Read quick reference
cat IAC_QUICK_REFERENCE.md

# Step 2: Deploy SageMaker
# See SAGEMAKER_SETUP.md

# Step 3: Configure and deploy
export SAGEMAKER_ENDPOINT_NAME=your-endpoint
npm install
cdk bootstrap
cdk deploy --all

# Step 4: Verify
# See DEPLOYMENT.md § Post-Deployment
```

### Workflow 2: Update Lambda Function

```bash
# Step 1: Modify code
vim lambda/document-parser/index.py

# Step 2: Check what changes
cdk diff GraphRagProcessingStack

# Step 3: Deploy
cdk deploy GraphRagProcessingStack

# Step 4: Test
# Upload test document
```

### Workflow 3: Scale Resources

```bash
# Step 1: Identify resource to scale
# See IAC_STACK_REFERENCE.md → DataStoresStack

# Step 2: Modify CDK code
vim lib/datastores-stack.ts
# Change: dataNodes: 2 → dataNodes: 3

# Step 3: Preview impact
cdk diff GraphRagDataStoresStack

# Step 4: Deploy (takes ~30 min for OpenSearch)
cdk deploy GraphRagDataStoresStack
```

### Workflow 4: Add Monitoring

```bash
# Step 1: Add CloudWatch alarm
vim lib/processing-stack.ts
# Add: new cloudwatch.Alarm(...)

# Step 2: Deploy
cdk deploy GraphRagProcessingStack

# Step 3: Verify
aws cloudwatch describe-alarms
```

---

## 📦 CDK Project Structure

```
graph-rag-cdk/
│
├── 🏗️  Infrastructure Code (TypeScript)
│   ├── bin/graph-rag-cdk.ts           # App entry point
│   ├── lib/                           # Stack definitions (6 files)
│   ├── cdk.json                       # CDK config
│   ├── package.json                   # Dependencies
│   └── tsconfig.json                  # TypeScript config
│
├── 📦  Application Code (Python)
│   └── lambda/*/index.py              # 6 Lambda handlers
│
├── 📋  Data & Config
│   └── ontologies/*.ttl               # OWL ontology
│
├── 📖  IAC Documentation (3 files)
│   ├── IAC_GUIDE.md                   # Comprehensive (800+ lines)
│   ├── IAC_STACK_REFERENCE.md         # Resource catalog (1000+ lines)
│   ├── IAC_QUICK_REFERENCE.md         # Quick lookup (450+ lines)
│   └── IAC_INDEX.md                   # This file
│
├── 📖  Other Documentation
│   ├── README.md                      # Project overview
│   ├── QUICKSTART.md                  # 5-min deploy
│   ├── DEPLOYMENT.md                  # Detailed deploy
│   ├── ARCHITECTURE.md                # System architecture
│   ├── ARCHITECTURE_DIAGRAM.md        # Mermaid diagrams
│   ├── ONTOLOGY_GUIDE.md              # OWL guide
│   ├── DATA_SEPARATION_STRATEGY.md    # Data design
│   └── SAGEMAKER_SETUP.md             # ML setup
│
└── 🧪  Tests (Future)
    └── test/graph-rag.test.ts         # Infrastructure tests
```

---

## 🎓 IAC Concepts Explained

### CDK Constructs

**L1 (CloudFormation)**:
```typescript
new neptune.CfnDBCluster(this, 'Cluster', {...})
// Direct mapping to CloudFormation resource
```

**L2 (AWS Construct Library)**:
```typescript
new lambda.Function(this, 'Func', {...})
// High-level, includes best practices, automatic IAM
```

**L3 (Patterns)**:
```typescript
new patterns.ApplicationLoadBalancedFargateService(...)
// Complete architectural patterns
```

### Stack vs Construct

**Stack**: Unit of deployment (maps to CloudFormation stack)
```typescript
export class NetworkingStack extends cdk.Stack {}
```

**Construct**: Reusable component (resource or group of resources)
```typescript
export class CustomVpc extends Construct {}
```

### Props Pattern

```typescript
// Define interface
export interface MyStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
}

// Use in constructor
constructor(scope: Construct, id: string, props: MyStackProps) {
  super(scope, id, props);
  const vpc = props.vpc;  // Type-safe!
}
```

### Tokens and References

```typescript
// Token (placeholder resolved at deploy)
const endpoint = neptuneCluster.attrEndpoint;  // Token

// Use in another resource
environment: {
  ENDPOINT: endpoint,  // Resolves at deploy time
}
```

---

## 🛠️ Maintenance Tasks

### Daily/Weekly

- ✅ Monitor CloudWatch Logs
- ✅ Check Step Functions executions
- ✅ Review API Gateway metrics
- ✅ Verify SageMaker endpoint health

### Monthly

- ✅ Review AWS costs (Cost Explorer)
- ✅ Check for CDK updates: `npm outdated`
- ✅ Review IAM policies (least privilege)
- ✅ Check resource utilization
- ✅ Review and rotate secrets

### Quarterly

- ✅ Update CDK version
- ✅ Review and update dependencies
- ✅ Conduct DR testing
- ✅ Review and optimize costs
- ✅ Security audit

---

## 🚀 Advanced Topics

### Multi-Region Deployment

```typescript
const regions = ['us-east-1', 'eu-west-1'];

regions.forEach(region => {
  new NetworkingStack(app, `GraphRag-${region}-Networking`, {
    env: { account, region },
  });
});
```

### Blue-Green Deployments

```typescript
// Deploy parallel stack
const blueStack = new ProcessingStack(app, 'ProcessingBlue', {...});
const greenStack = new ProcessingStack(app, 'ProcessingGreen', {...});

// Switch traffic via weighted alias
```

### Infrastructure Testing

```typescript
// Unit test
test('VPC has 2 AZs', () => {
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::EC2::VPC', {
    MaxAzs: 2,
  });
});

// Integration test
test('Neptune accessible', async () => {
  const endpoint = await getEndpoint();
  const result = await queryNeptune(endpoint);
  expect(result).toBeDefined();
});
```

### Custom Constructs

```typescript
export class GraphRagVpc extends Construct {
  public readonly vpc: ec2.Vpc;
  
  constructor(scope: Construct, id: string) {
    super(scope, id);
    
    this.vpc = new ec2.Vpc(this, 'Vpc', {
      // Custom VPC logic
    });
  }
}

// Use in stack
const graphRagVpc = new GraphRagVpc(this, 'CustomVpc');
```

---

## 📊 Infrastructure Metrics

### Resource Count by Category

| Category | Count | Examples |
|----------|-------|----------|
| Compute | 7 | Lambda × 6, Step Functions × 1 |
| Networking | 12 | VPC, Subnets × 6, NAT × 1, IGW × 1, SG × 3 |
| Storage | 1 | S3 Bucket |
| Database | 8 | Neptune cluster + instance, OpenSearch + 2 nodes |
| Integration | 3 | API Gateway, EventBridge, SQS |
| IAM | 8 | Execution roles |
| Monitoring | 8 | CloudWatch Log Groups |
| **TOTAL** | **~47** | |

### Code Statistics

| Metric | Count |
|--------|-------|
| CDK Stacks | 6 |
| TypeScript files | 7 |
| Python Lambda functions | 6 |
| Lines of infrastructure code | ~1,600 |
| Lines of application code | ~2,500 |
| Lines of documentation | ~10,200 |
| **Total lines** | **~14,300** |

---

## 🔗 External Resources

### AWS CDK

- **Documentation**: https://docs.aws.amazon.com/cdk/
- **API Reference**: https://docs.aws.amazon.com/cdk/api/v2/
- **Workshop**: https://cdkworkshop.com/
- **Patterns**: https://cdkpatterns.com/
- **Examples**: https://github.com/aws-samples/aws-cdk-examples

### AWS Services

- **Neptune**: https://docs.aws.amazon.com/neptune/
- **OpenSearch**: https://docs.aws.amazon.com/opensearch-service/
- **Step Functions**: https://docs.aws.amazon.com/step-functions/
- **Lambda**: https://docs.aws.amazon.com/lambda/
- **API Gateway**: https://docs.aws.amazon.com/apigateway/

### Community

- **CDK GitHub**: https://github.com/aws/aws-cdk
- **AWS Construct Hub**: https://constructs.dev/
- **CDK Day**: https://www.cdkday.com/

---

## 📝 Quick Command Reference

```bash
# Setup
npm install                    # Install dependencies
cdk bootstrap                  # Initialize CDK in AWS account

# Development
cdk list                       # List all stacks
cdk synth                      # Generate CloudFormation
cdk diff                       # Show pending changes
cdk deploy StackName           # Deploy single stack
cdk deploy --all               # Deploy all stacks
cdk watch StackName            # Auto-deploy on file changes

# Information
cdk doctor                     # Check CDK installation
cdk docs                       # Open CDK documentation
cdk metadata StackName         # Show stack metadata

# Cleanup
cdk destroy StackName          # Delete single stack
cdk destroy --all              # Delete all stacks

# Context
cdk context                    # Show cached context
cdk context --clear            # Clear context cache

# Asset Management
cdk deploy --all --build-exclude=... # Skip certain assets
cdk deploy --exclusively       # Deploy only specified stacks
```

---

## 💡 Pro Tips

### 1. Use CDK Watch for Development

```bash
cdk watch GraphRagProcessingStack
# Auto-deploys Lambda code changes
# Faster than full cdk deploy
```

### 2. Cache Stack Outputs

```bash
# Save outputs to file
cdk deploy --all --outputs-file outputs.json

# Use in scripts
NEPTUNE_ENDPOINT=$(jq -r '.GraphRagDataStoresStack.NeptuneClusterEndpoint' outputs.json)
```

### 3. Diff Before Deploy

```bash
# Always review changes
cdk diff --all
# Look for resource replacements (will cause downtime)
```

### 4. Use --exclusively Flag

```bash
# Deploy only specified stack (skip dependencies)
cdk deploy GraphRagApiStack --exclusively
# Faster if dependencies haven't changed
```

### 5. Parallel Deployments

```bash
# Deploy independent stacks in parallel
cdk deploy NetworkingStack &
cdk deploy StorageStack &
wait
# Then deploy dependent stacks
```

---

## 🎉 Summary

### IAC Documentation Coverage

✅ **Complete** - Every resource documented  
✅ **Comprehensive** - 2,250+ lines of IAC docs  
✅ **Practical** - Real examples and commands  
✅ **Searchable** - Multiple ways to find info  
✅ **Up-to-date** - Matches current implementation  

### Quick Navigation

- **Quick lookup** → [IAC_QUICK_REFERENCE.md](IAC_QUICK_REFERENCE.md)
- **Complete guide** → [IAC_GUIDE.md](IAC_GUIDE.md)
- **Resource details** → [IAC_STACK_REFERENCE.md](IAC_STACK_REFERENCE.md)
- **This index** → [IAC_INDEX.md](IAC_INDEX.md)

### Key Files

```
IAC Documentation:
├── IAC_INDEX.md              ← You are here
├── IAC_QUICK_REFERENCE.md    ← Start here for commands
├── IAC_GUIDE.md              ← Comprehensive guide
└── IAC_STACK_REFERENCE.md    ← Resource catalog

Infrastructure Code:
├── bin/graph-rag-cdk.ts      ← App entry point
└── lib/*.ts                  ← Stack definitions (6 files)
```

---

**This comprehensive IAC documentation suite covers every aspect of deploying, managing, and customizing your Graph RAG infrastructure with AWS CDK.**

