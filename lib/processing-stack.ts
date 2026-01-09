import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as neptune from 'aws-cdk-lib/aws-neptune';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

/**
 * Props for ProcessingStack
 */
export interface ProcessingStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  documentBucket: s3.Bucket;
  neptuneCluster: neptune.CfnDBCluster;
  openSearchDomain: opensearch.Domain;
  lambdaSecurityGroup: ec2.SecurityGroup;
}

/**
 * ProcessingStack
 * 
 * Creates Lambda functions for the document processing pipeline.
 * 
 * Pipeline stages:
 * 1. Document Parser: Extract text from PDFs, DOCs, CSVs
 * 2. RDF Generator: Generate RDF triples and ontology from extracted text
 * 3. Neptune Writer: Bulk load RDF data into Neptune graph database
 * 4. Embedding Generator: Create vector embeddings using Bedrock or SageMaker
 * 5. OpenSearch Writer: Index embeddings and metadata in OpenSearch
 * 
 * All Lambda functions are deployed in VPC to access Neptune and OpenSearch.
 */
export class ProcessingStack extends cdk.Stack {
  public readonly documentParserFunction: lambda.Function;
  public readonly rdfGeneratorFunction: lambda.Function;
  public readonly neptuneWriterFunction: lambda.Function;
  public readonly embeddingGeneratorFunction: lambda.Function;
  public readonly openSearchWriterFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: ProcessingStackProps) {
    super(scope, id, props);

    const { vpc, documentBucket, neptuneCluster, openSearchDomain, lambdaSecurityGroup } = props;

    /**
     * Common Lambda environment variables
     */
    const commonEnvironment = {
      DOCUMENT_BUCKET_NAME: documentBucket.bucketName,
      NEPTUNE_ENDPOINT: neptuneCluster.attrEndpoint,
      NEPTUNE_PORT: neptuneCluster.attrPort || '8182',
      OPENSEARCH_ENDPOINT: `https://${openSearchDomain.domainEndpoint}`,
      AWS_REGION: this.region,
    };

    /**
     * ============================================================
     * 1. DOCUMENT PARSER LAMBDA
     * ============================================================
     * 
     * Extracts text and metadata from uploaded documents.
     * Supports: PDF, DOCX, CSV, TXT
     * 
     * Libraries used (in Lambda layer or deployment package):
     * - PyPDF2 or pdfplumber for PDFs
     * - python-docx for Word documents
     * - pandas for CSV
     */
    this.documentParserFunction = new lambda.Function(this, 'DocumentParserFunction', {
      functionName: 'graph-rag-document-parser',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda/document-parser'), // Lambda code directory
      timeout: cdk.Duration.minutes(5), // Allow time for large documents
      memorySize: 1024, // MB (increase for large PDFs)
      
      // VPC configuration (not required for this function as it only accesses S3)
      // But included for consistency and future flexibility
      vpc: vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      
      environment: {
        ...commonEnvironment,
        MAX_FILE_SIZE_MB: '50', // Maximum file size to process
      },
      
      // Use ARM architecture (Graviton2) for cost savings
      architecture: lambda.Architecture.ARM_64,
      
      description: 'Parses uploaded documents and extracts text content',
    });

    // Grant S3 read access
    documentBucket.grantRead(this.documentParserFunction);

    /**
     * ============================================================
     * 2. RDF GENERATOR LAMBDA
     * ============================================================
     * 
     * Generates RDF triples and ontology from parsed text.
     * 
     * Process:
     * - Receives parsed text from previous step
     * - Applies NLP to extract entities, relationships
     * - Constructs RDF triples following defined ontology schema
     * - Outputs RDF/Turtle or N-Triples format
     * 
     * Libraries:
     * - rdflib for RDF manipulation
     * - spaCy or similar for NLP (entity extraction)
     * - Custom ontology schema definitions
     */
    this.rdfGeneratorFunction = new lambda.Function(this, 'RdfGeneratorFunction', {
      functionName: 'graph-rag-rdf-generator',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda/rdf-generator'),
      timeout: cdk.Duration.minutes(10), // RDF generation can be time-consuming
      memorySize: 2048, // MB (increase for NLP models)
      
      vpc: vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      
      environment: {
        ...commonEnvironment,
        ONTOLOGY_SCHEMA_VERSION: '1.0',
        RDF_FORMAT: 'turtle', // turtle, n-triples, or rdf-xml
      },
      
      architecture: lambda.Architecture.ARM_64,
      
      description: 'Generates RDF triples and ontology from document content',
    });

    // Grant S3 read/write (for staging RDF files)
    documentBucket.grantReadWrite(this.rdfGeneratorFunction);

    /**
     * ============================================================
     * 3. NEPTUNE WRITER LAMBDA
     * ============================================================
     * 
     * Writes RDF data to Neptune graph database.
     * 
     * Two approaches:
     * 1. Bulk Loader: For large datasets, write RDF to S3 staging area
     *    and use Neptune bulk loader API (recommended for >10K triples)
     * 2. Direct Insert: For small datasets, use SPARQL INSERT queries
     *    via Neptune HTTP endpoint
     * 
     * This implementation uses Neptune's bulk loader for efficiency.
     */
    this.neptuneWriterFunction = new lambda.Function(this, 'NeptuneWriterFunction', {
      functionName: 'graph-rag-neptune-writer',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda/neptune-writer'),
      timeout: cdk.Duration.minutes(15), // Bulk loading can take time
      memorySize: 512, // MB
      
      // Must be in VPC to access Neptune
      vpc: vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      
      environment: {
        ...commonEnvironment,
        NEPTUNE_LOAD_FROM_S3_ROLE_ARN: '', // Set by IAM role below
        NEPTUNE_STAGING_PREFIX: 'neptune-staging/', // S3 prefix for RDF files
      },
      
      architecture: lambda.Architecture.ARM_64,
      
      description: 'Loads RDF data into Neptune graph database',
    });

    // Grant S3 access for staging area
    documentBucket.grantRead(this.neptuneWriterFunction, 'neptune-staging/*');

    /**
     * Grant Neptune access via IAM
     * Neptune IAM authentication requires neptune-db:* permissions
     */
    this.neptuneWriterFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'neptune-db:connect',
        'neptune-db:ReadDataViaQuery',
        'neptune-db:WriteDataViaQuery',
        'neptune-db:DeleteDataViaQuery',
      ],
      resources: [
        `arn:aws:neptune-db:${this.region}:${this.account}:${neptuneCluster.attrClusterResourceId}/*`,
      ],
    }));

    /**
     * Create IAM role for Neptune bulk loader
     * Neptune needs permission to read from S3 staging bucket
     */
    const neptuneBulkLoadRole = new iam.Role(this, 'NeptuneBulkLoadRole', {
      assumedBy: new iam.ServicePrincipal('rds.amazonaws.com'),
      description: 'Role for Neptune to read from S3 for bulk loading',
    });

    documentBucket.grantRead(neptuneBulkLoadRole, 'neptune-staging/*');

    // Add Neptune cluster resource ID to policy
    neptuneBulkLoadRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['s3:GetObject', 's3:ListBucket'],
      resources: [
        documentBucket.bucketArn,
        `${documentBucket.bucketArn}/neptune-staging/*`,
      ],
    }));

    // Update Lambda environment with bulk load role ARN
    this.neptuneWriterFunction.addEnvironment('NEPTUNE_LOAD_FROM_S3_ROLE_ARN', neptuneBulkLoadRole.roleArn);

    /**
     * ============================================================
     * 4. EMBEDDING GENERATOR LAMBDA
     * ============================================================
     * 
     * Generates vector embeddings from document text for similarity search.
     * 
     * Uses Amazon SageMaker endpoint with embedding model.
     * Recommended models:
     * - sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
     * - sentence-transformers/all-mpnet-base-v2 (768 dimensions)
     * - intfloat/e5-large-v2 (1024 dimensions)
     * - BAAI/bge-large-en-v1.5 (1024 dimensions)
     * 
     * Note: You must deploy a SageMaker endpoint before using this Lambda.
     * Set the endpoint name in the SAGEMAKER_ENDPOINT_NAME environment variable.
     */
    this.embeddingGeneratorFunction = new lambda.Function(this, 'EmbeddingGeneratorFunction', {
      functionName: 'graph-rag-embedding-generator',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda/embedding-generator'),
      timeout: cdk.Duration.minutes(5), // SageMaker endpoint calls can take longer
      memorySize: 512, // MB
      
      vpc: vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      
      environment: {
        ...commonEnvironment,
        // TODO: Update with your SageMaker endpoint name after deployment
        SAGEMAKER_ENDPOINT_NAME: process.env.SAGEMAKER_ENDPOINT_NAME || 'huggingface-embedding-endpoint',
        EMBEDDING_DIMENSIONS: process.env.EMBEDDING_DIMENSIONS || '768', // Update based on your model
        CHUNK_SIZE: '512', // Tokens per embedding chunk
        CHUNK_OVERLAP: '50', // Token overlap between chunks
        EMBEDDING_PROVIDER: 'sagemaker', // sagemaker (not bedrock)
      },
      
      architecture: lambda.Architecture.ARM_64,
      
      description: 'Generates vector embeddings from document text using SageMaker endpoint',
    });

    /**
     * Grant SageMaker endpoint access
     * 
     * Note: This grants access to all SageMaker endpoints in the region.
     * For production, restrict to specific endpoint ARN:
     * `arn:aws:sagemaker:${this.region}:${this.account}:endpoint/your-endpoint-name`
     */
    this.embeddingGeneratorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'sagemaker:InvokeEndpoint',
      ],
      resources: [
        `arn:aws:sagemaker:${this.region}:${this.account}:endpoint/*`,
        // For production, specify exact endpoint:
        // `arn:aws:sagemaker:${this.region}:${this.account}:endpoint/${process.env.SAGEMAKER_ENDPOINT_NAME || 'huggingface-embedding-endpoint'}`,
      ],
    }));

    /**
     * ============================================================
     * 5. OPENSEARCH WRITER LAMBDA
     * ============================================================
     * 
     * Indexes embeddings and metadata in OpenSearch for similarity search.
     * 
     * Process:
     * - Receives embeddings from previous step
     * - Constructs OpenSearch document with:
     *   - embedding vector (for k-NN search)
     *   - document metadata (keywords, title, etc.)
     *   - text chunks (for context retrieval)
     * - Indexes to OpenSearch using k-NN index
     */
    this.openSearchWriterFunction = new lambda.Function(this, 'OpenSearchWriterFunction', {
      functionName: 'graph-rag-opensearch-writer',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda/opensearch-writer'),
      timeout: cdk.Duration.minutes(5), // Batch indexing
      memorySize: 512, // MB
      
      // Must be in VPC to access OpenSearch
      vpc: vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [lambdaSecurityGroup],
      
      environment: {
        ...commonEnvironment,
        OPENSEARCH_INDEX_NAME: 'document-embeddings',
        KNN_DIMENSIONS: '1536', // Match embedding dimensions
        KNN_METHOD: 'hnsw', // Hierarchical Navigable Small World algorithm
        KNN_SIMILARITY: 'cosine', // cosine, l2, or l1
      },
      
      architecture: lambda.Architecture.ARM_64,
      
      description: 'Indexes embeddings and metadata in OpenSearch for vector search',
    });

    /**
     * Grant OpenSearch access
     * Lambda needs to write to OpenSearch domain
     */
    this.openSearchWriterFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'es:ESHttpPost',
        'es:ESHttpPut',
        'es:ESHttpGet',
      ],
      resources: [
        `${openSearchDomain.domainArn}/*`,
      ],
    }));

    /**
     * Optional: Create OpenSearch index initialization Lambda
     * This Lambda creates the k-NN index with proper mappings on first deployment
     * Uncomment to enable
     */
    // const initOpenSearchFunction = new lambda.Function(this, 'InitOpenSearchFunction', {
    //   functionName: 'graph-rag-init-opensearch',
    //   runtime: lambda.Runtime.PYTHON_3_12,
    //   handler: 'index.handler',
    //   code: lambda.Code.fromAsset('lambda/init-opensearch'),
    //   timeout: cdk.Duration.minutes(2),
    //   memorySize: 256,
    //   vpc: vpc,
    //   vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
    //   securityGroups: [lambdaSecurityGroup],
    //   environment: {
    //     OPENSEARCH_ENDPOINT: `https://${openSearchDomain.domainEndpoint}`,
    //     INDEX_NAME: 'document-embeddings',
    //     KNN_DIMENSIONS: '1536',
    //   },
    //   architecture: lambda.Architecture.ARM_64,
    // });
    // 
    // initOpenSearchFunction.addToRolePolicy(new iam.PolicyStatement({
    //   effect: iam.Effect.ALLOW,
    //   actions: ['es:ESHttpPut', 'es:ESHttpGet'],
    //   resources: [`${openSearchDomain.domainArn}/*`],
    // }));
    // 
    // // Use custom resource to trigger initialization on stack creation
    // const initProvider = new cr.Provider(this, 'InitOpenSearchProvider', {
    //   onEventHandler: initOpenSearchFunction,
    // });
    // 
    // new cdk.CustomResource(this, 'InitOpenSearchCustomResource', {
    //   serviceToken: initProvider.serviceToken,
    // });

    /**
     * ============================================================
     * CLOUDWATCH ALARMS FOR MONITORING
     * ============================================================
     */

    /**
     * Optional: Create CloudWatch alarms for Lambda errors
     * Uncomment to enable monitoring
     */
    // const allFunctions = [
    //   this.documentParserFunction,
    //   this.rdfGeneratorFunction,
    //   this.neptuneWriterFunction,
    //   this.embeddingGeneratorFunction,
    //   this.openSearchWriterFunction,
    // ];
    // 
    // allFunctions.forEach(fn => {
    //   new cloudwatch.Alarm(this, `${fn.functionName}-ErrorAlarm`, {
    //     metric: fn.metricErrors(),
    //     threshold: 5,
    //     evaluationPeriods: 1,
    //     alarmDescription: `Alarm when ${fn.functionName} has errors`,
    //   });
    // });

    /**
     * ============================================================
     * STACK OUTPUTS
     * ============================================================
     */
    new cdk.CfnOutput(this, 'DocumentParserFunctionArn', {
      value: this.documentParserFunction.functionArn,
      description: 'ARN of document parser Lambda function',
    });

    new cdk.CfnOutput(this, 'RdfGeneratorFunctionArn', {
      value: this.rdfGeneratorFunction.functionArn,
      description: 'ARN of RDF generator Lambda function',
    });

    new cdk.CfnOutput(this, 'NeptuneWriterFunctionArn', {
      value: this.neptuneWriterFunction.functionArn,
      description: 'ARN of Neptune writer Lambda function',
    });

    new cdk.CfnOutput(this, 'EmbeddingGeneratorFunctionArn', {
      value: this.embeddingGeneratorFunction.functionArn,
      description: 'ARN of embedding generator Lambda function',
    });

    new cdk.CfnOutput(this, 'OpenSearchWriterFunctionArn', {
      value: this.openSearchWriterFunction.functionArn,
      description: 'ARN of OpenSearch writer Lambda function',
    });
  }
}

