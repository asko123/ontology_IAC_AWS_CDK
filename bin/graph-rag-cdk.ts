#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { NetworkingStack } from '../lib/networking-stack';
import { StorageStack } from '../lib/storage-stack';
import { DataStoresStack } from '../lib/datastores-stack';
import { ProcessingStack } from '../lib/processing-stack';
import { OrchestrationStack } from '../lib/orchestration-stack';
import { ApiStack } from '../lib/api-stack';

/**
 * Main CDK Application Entry Point
 * 
 * This app orchestrates the deployment of a complete Graph RAG infrastructure
 * consisting of multiple interdependent stacks:
 * 
 * 1. NetworkingStack: VPC, subnets, security groups
 * 2. StorageStack: S3 bucket for document storage
 * 3. DataStoresStack: Neptune (graph DB) and OpenSearch (vector search)
 * 4. ProcessingStack: Lambda functions for data processing pipeline
 * 5. OrchestrationStack: Step Functions and EventBridge for workflow orchestration
 * 6. ApiStack: API Gateway and upload handler for user interactions
 */

const app = new cdk.App();

// Get environment configuration
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};

// Stack naming prefix
const stackPrefix = 'GraphRag';

/**
 * STEP 1: Create networking infrastructure (VPC, subnets, security groups)
 * Neptune and OpenSearch require VPC deployment
 */
const networkingStack = new NetworkingStack(app, `${stackPrefix}NetworkingStack`, {
  env,
  description: 'VPC and networking infrastructure for Graph RAG system',
});

/**
 * STEP 2: Create S3 bucket for document storage
 * Configured with versioning, lifecycle policies, and encryption
 */
const storageStack = new StorageStack(app, `${stackPrefix}StorageStack`, {
  env,
  description: 'S3 storage for uploaded documents and intermediate data',
});

/**
 * STEP 3: Create data stores (Neptune and OpenSearch)
 * These are deployed in the VPC created by NetworkingStack
 */
const dataStoresStack = new DataStoresStack(app, `${stackPrefix}DataStoresStack`, {
  env,
  vpc: networkingStack.vpc,
  neptuneSecurityGroup: networkingStack.neptuneSecurityGroup,
  openSearchSecurityGroup: networkingStack.openSearchSecurityGroup,
  description: 'Neptune graph database and OpenSearch vector store',
});

/**
 * STEP 4: Create Lambda functions for processing pipeline
 * Functions are deployed in VPC to access Neptune and OpenSearch
 */
const processingStack = new ProcessingStack(app, `${stackPrefix}ProcessingStack`, {
  env,
  vpc: networkingStack.vpc,
  documentBucket: storageStack.documentBucket,
  neptuneCluster: dataStoresStack.neptuneCluster,
  openSearchDomain: dataStoresStack.openSearchDomain,
  lambdaSecurityGroup: networkingStack.lambdaSecurityGroup,
  description: 'Lambda functions for document processing, RDF generation, and indexing',
});

/**
 * STEP 5: Create orchestration layer (Step Functions and EventBridge)
 * EventBridge listens to S3 events and triggers Step Functions workflow
 */
const orchestrationStack = new OrchestrationStack(app, `${stackPrefix}OrchestrationStack`, {
  env,
  documentBucket: storageStack.documentBucket,
  documentParserFunction: processingStack.documentParserFunction,
  rdfGeneratorFunction: processingStack.rdfGeneratorFunction,
  neptuneWriterFunction: processingStack.neptuneWriterFunction,
  embeddingGeneratorFunction: processingStack.embeddingGeneratorFunction,
  openSearchWriterFunction: processingStack.openSearchWriterFunction,
  description: 'Step Functions workflow and EventBridge rules for orchestration',
});

/**
 * STEP 6: Create API Gateway and upload handler
 * Provides HTTP endpoint for document uploads with metadata
 */
const apiStack = new ApiStack(app, `${stackPrefix}ApiStack`, {
  env,
  documentBucket: storageStack.documentBucket,
  description: 'API Gateway and Lambda for document upload endpoint',
});

// Add stack dependencies to ensure proper deployment order
storageStack.addDependency(networkingStack);
dataStoresStack.addDependency(networkingStack);
processingStack.addDependency(dataStoresStack);
processingStack.addDependency(storageStack);
orchestrationStack.addDependency(processingStack);
apiStack.addDependency(storageStack);

// Add tags to all stacks for resource tracking and cost allocation
cdk.Tags.of(app).add('Project', 'GraphRAG');
cdk.Tags.of(app).add('ManagedBy', 'CDK');
cdk.Tags.of(app).add('Environment', process.env.ENVIRONMENT || 'dev');

app.synth();

