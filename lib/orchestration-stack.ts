import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

/**
 * Props for OrchestrationStack
 */
export interface OrchestrationStackProps extends cdk.StackProps {
  documentBucket: s3.Bucket;
  documentParserFunction: lambda.Function;
  rdfGeneratorFunction: lambda.Function;
  neptuneWriterFunction: lambda.Function;
  embeddingGeneratorFunction: lambda.Function;
  openSearchWriterFunction: lambda.Function;
}

/**
 * OrchestrationStack
 * 
 * Creates event-driven orchestration layer:
 * - EventBridge rule to capture S3 upload events
 * - Step Functions state machine to orchestrate processing pipeline
 * - Dead Letter Queue for failed events
 * 
 * Flow:
 * S3 Upload → EventBridge → Step Functions → Lambda Functions (parallel/sequential)
 */
export class OrchestrationStack extends cdk.Stack {
  public readonly stateMachine: sfn.StateMachine;
  public readonly eventRule: events.Rule;

  constructor(scope: Construct, id: string, props: OrchestrationStackProps) {
    super(scope, id, props);

    const {
      documentBucket,
      documentParserFunction,
      rdfGeneratorFunction,
      neptuneWriterFunction,
      embeddingGeneratorFunction,
      openSearchWriterFunction,
    } = props;

    /**
     * ============================================================
     * DEAD LETTER QUEUE
     * ============================================================
     * 
     * Captures failed Step Functions executions for debugging and retry
     */
    const dlq = new sqs.Queue(this, 'ProcessingDlq', {
      queueName: 'graph-rag-processing-dlq',
      retentionPeriod: cdk.Duration.days(14), // Keep failed messages for 14 days
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    /**
     * ============================================================
     * STEP FUNCTIONS STATE MACHINE
     * ============================================================
     * 
     * Orchestrates the document processing pipeline with error handling.
     * 
     * Pipeline stages:
     * 1. Parse Document (extract text)
     * 2. Parallel Processing:
     *    a. Generate RDF → Write to Neptune
     *    b. Generate Embeddings → Write to OpenSearch
     * 
     * Rationale for parallelization:
     * - RDF generation and embedding generation are independent
     * - Reduces total processing time by ~50%
     * - Both branches use the same parsed text input
     */

    /**
     * STEP 1: Parse Document
     * Extract text and metadata from uploaded file
     */
    const parseDocumentTask = new tasks.LambdaInvoke(this, 'ParseDocument', {
      lambdaFunction: documentParserFunction,
      outputPath: '$.Payload', // Pass Lambda output to next state
      retryOnServiceExceptions: true,
      payload: sfn.TaskInput.fromObject({
        'bucket.$': '$.detail.bucket.name',
        'key.$': '$.detail.object.key',
        's3Event.$': '$.detail',
      }),
    });

    /**
     * Add retry logic for document parser
     * Retries with exponential backoff for transient failures
     */
    parseDocumentTask.addRetry({
      errors: ['States.TaskFailed', 'Lambda.ServiceException', 'Lambda.TooManyRequestsException'],
      interval: cdk.Duration.seconds(2),
      maxAttempts: 3,
      backoffRate: 2.0, // Exponential backoff
    });

    /**
     * Add catch for permanent failures
     * Log error details and move to failed state
     */
    const parseFailedState = new sfn.Fail(this, 'ParseDocumentFailed', {
      cause: 'Document parsing failed',
      error: 'ParseError',
    });

    parseDocumentTask.addCatch(parseFailedState, {
      errors: ['States.ALL'],
      resultPath: '$.errorInfo',
    });

    /**
     * BRANCH A: RDF Processing Chain
     * Generate RDF → Write to Neptune
     */

    // STEP 2a: Generate RDF triples and ontology
    const generateRdfTask = new tasks.LambdaInvoke(this, 'GenerateRdf', {
      lambdaFunction: rdfGeneratorFunction,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
      payload: sfn.TaskInput.fromJsonPathAt('$'), // Pass entire state to Lambda
    });

    generateRdfTask.addRetry({
      errors: ['States.TaskFailed', 'Lambda.ServiceException'],
      interval: cdk.Duration.seconds(3),
      maxAttempts: 2,
      backoffRate: 2.0,
    });

    // STEP 3a: Write RDF to Neptune
    const writeToNeptuneTask = new tasks.LambdaInvoke(this, 'WriteToNeptune', {
      lambdaFunction: neptuneWriterFunction,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
      payload: sfn.TaskInput.fromJsonPathAt('$'),
    });

    writeToNeptuneTask.addRetry({
      errors: ['States.TaskFailed', 'Lambda.ServiceException'],
      interval: cdk.Duration.seconds(5),
      maxAttempts: 3,
      backoffRate: 1.5,
    });

    // Chain RDF branch: Generate → Write
    const rdfBranch = generateRdfTask.next(writeToNeptuneTask);

    /**
     * BRANCH B: Embedding Processing Chain
     * Generate Embeddings → Write to OpenSearch
     */

    // STEP 2b: Generate embeddings using Bedrock
    const generateEmbeddingsTask = new tasks.LambdaInvoke(this, 'GenerateEmbeddings', {
      lambdaFunction: embeddingGeneratorFunction,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
      payload: sfn.TaskInput.fromJsonPathAt('$'),
    });

    generateEmbeddingsTask.addRetry({
      errors: ['States.TaskFailed', 'Lambda.ServiceException'],
      interval: cdk.Duration.seconds(3),
      maxAttempts: 2,
      backoffRate: 2.0,
    });

    // STEP 3b: Index embeddings in OpenSearch
    const writeToOpenSearchTask = new tasks.LambdaInvoke(this, 'WriteToOpenSearch', {
      lambdaFunction: openSearchWriterFunction,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
      payload: sfn.TaskInput.fromJsonPathAt('$'),
    });

    writeToOpenSearchTask.addRetry({
      errors: ['States.TaskFailed', 'Lambda.ServiceException'],
      interval: cdk.Duration.seconds(5),
      maxAttempts: 3,
      backoffRate: 1.5,
    });

    // Chain embedding branch: Generate → Write
    const embeddingBranch = generateEmbeddingsTask.next(writeToOpenSearchTask);

    /**
     * PARALLEL STATE: Execute RDF and Embedding branches concurrently
     * 
     * This reduces processing time by running independent operations in parallel.
     * Both branches must complete successfully for the workflow to succeed.
     */
    const parallelProcessing = new sfn.Parallel(this, 'ParallelProcessing', {
      resultPath: '$.parallelResults',
    });

    parallelProcessing.branch(rdfBranch);
    parallelProcessing.branch(embeddingBranch);

    /**
     * Add catch for parallel processing failures
     * If either branch fails, log details and move to failed state
     */
    const parallelFailedState = new sfn.Fail(this, 'ParallelProcessingFailed', {
      cause: 'One or more processing branches failed',
      error: 'ProcessingError',
    });

    parallelProcessing.addCatch(parallelFailedState, {
      errors: ['States.ALL'],
      resultPath: '$.errorInfo',
    });

    /**
     * SUCCESS STATE
     * All processing completed successfully
     */
    const successState = new sfn.Succeed(this, 'ProcessingComplete', {
      comment: 'Document successfully processed and indexed',
    });

    /**
     * CONSTRUCT WORKFLOW
     * Parse → Parallel(RDF + Embeddings) → Success
     */
    const definition = parseDocumentTask
      .next(parallelProcessing)
      .next(successState);

    /**
     * CREATE STATE MACHINE
     */
    this.stateMachine = new sfn.StateMachine(this, 'ProcessingStateMachine', {
      stateMachineName: 'graph-rag-processing',
      definitionBody: sfn.DefinitionBody.fromChainable(definition),
      timeout: cdk.Duration.minutes(30), // Maximum execution time
      tracingEnabled: true, // Enable X-Ray tracing for debugging
      
      /**
       * Logging configuration
       * Log all execution details to CloudWatch for debugging
       */
      logs: {
        destination: new cdk.aws_logs.LogGroup(this, 'StateMachineLogGroup', {
          logGroupName: '/aws/stepfunctions/graph-rag-processing',
          retention: cdk.aws_logs.RetentionDays.ONE_WEEK,
          removalPolicy: cdk.RemovalPolicy.DESTROY,
        }),
        level: sfn.LogLevel.ALL,
        includeExecutionData: true,
      },
    });

    /**
     * ============================================================
     * EVENTBRIDGE RULE
     * ============================================================
     * 
     * Triggers Step Functions when files are uploaded to S3.
     * 
     * Event pattern:
     * - Source: aws.s3
     * - Event type: Object Created
     * - Bucket: documentBucket
     * - Key prefix: Filter to specific folder if needed
     */
    this.eventRule = new events.Rule(this, 'S3UploadRule', {
      ruleName: 'graph-rag-s3-upload-trigger',
      description: 'Trigger processing pipeline when documents are uploaded to S3',
      
      /**
       * EventBridge event pattern for S3 object creation
       * Matches PutObject, CompleteMultipartUpload, and CopyObject events
       */
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Created'],
        detail: {
          bucket: {
            name: [documentBucket.bucketName],
          },
          // Optional: Filter by object key prefix (e.g., only process files in 'uploads/' folder)
          // object: {
          //   key: [{ prefix: 'uploads/' }],
          // },
          
          // Optional: Filter by file extension
          // object: {
          //   key: [
          //     { suffix: '.pdf' },
          //     { suffix: '.docx' },
          //     { suffix: '.csv' },
          //   ],
          // },
        },
      },
    });

    /**
     * Add Step Functions as target for EventBridge rule
     * Each S3 upload event triggers a new state machine execution
     */
    this.eventRule.addTarget(new targets.SfnStateMachine(this.stateMachine, {
      // Use document key as execution name for traceability
      input: events.RuleTargetInput.fromEventPath('$'),
      
      /**
       * Dead letter queue for failed rule invocations
       * If EventBridge fails to start the state machine, send event to DLQ
       */
      deadLetterQueue: dlq,
      
      /**
       * Retry policy for rule target
       */
      retryAttempts: 3,
      maxEventAge: cdk.Duration.hours(2),
    }));

    /**
     * Grant EventBridge permission to start state machine executions
     * This is automatically handled by addTarget(), but explicitly shown for clarity
     */
    this.stateMachine.grantStartExecution(new iam.ServicePrincipal('events.amazonaws.com'));

    /**
     * ============================================================
     * OPTIONAL: MANUAL TRIGGER LAMBDA
     * ============================================================
     * 
     * Allows manual triggering of the processing pipeline for existing S3 objects.
     * Useful for reprocessing documents or batch processing.
     * 
     * Uncomment to enable
     */
    // const manualTriggerFunction = new lambda.Function(this, 'ManualTriggerFunction', {
    //   functionName: 'graph-rag-manual-trigger',
    //   runtime: lambda.Runtime.PYTHON_3_12,
    //   handler: 'index.handler',
    //   code: lambda.Code.fromInline(`
    // import boto3
    // import json
    // 
    // sfn = boto3.client('stepfunctions')
    // 
    // def handler(event, context):
    //     bucket = event['bucket']
    //     key = event['key']
    //     
    //     response = sfn.start_execution(
    //         stateMachineArn='${this.stateMachine.stateMachineArn}',
    //         input=json.dumps({
    //             'detail': {
    //                 'bucket': {'name': bucket},
    //                 'object': {'key': key}
    //             }
    //         })
    //     )
    //     
    //     return {
    //         'statusCode': 200,
    //         'body': json.dumps({'executionArn': response['executionArn']})
    //     }
    //   `),
    //   environment: {
    //     STATE_MACHINE_ARN: this.stateMachine.stateMachineArn,
    //   },
    // });
    // 
    // this.stateMachine.grantStartExecution(manualTriggerFunction);

    /**
     * ============================================================
     * STACK OUTPUTS
     * ============================================================
     */
    new cdk.CfnOutput(this, 'StateMachineArn', {
      value: this.stateMachine.stateMachineArn,
      description: 'ARN of the processing Step Functions state machine',
      exportName: 'GraphRag-StateMachineArn',
    });

    new cdk.CfnOutput(this, 'StateMachineConsoleUrl', {
      value: `https://console.aws.amazon.com/states/home?region=${this.region}#/statemachines/view/${this.stateMachine.stateMachineArn}`,
      description: 'AWS Console URL for the state machine',
    });

    new cdk.CfnOutput(this, 'EventRuleName', {
      value: this.eventRule.ruleName,
      description: 'Name of the EventBridge rule triggering processing',
    });

    new cdk.CfnOutput(this, 'DlqUrl', {
      value: dlq.queueUrl,
      description: 'URL of the Dead Letter Queue for failed processing events',
    });
  }
}

