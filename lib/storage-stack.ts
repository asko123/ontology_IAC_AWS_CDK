import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import { Construct } from 'constructs';

/**
 * StorageStack
 * 
 * Creates S3 bucket infrastructure for document storage.
 * 
 * Features:
 * - Versioning enabled for document history tracking
 * - Lifecycle policies for cost optimization (Glacier transitions)
 * - Server-side encryption (SSE-S3)
 * - CORS configuration for browser uploads
 * - EventBridge notifications for object creation events
 * 
 * The bucket stores:
 * - Uploaded documents (PDFs, CSVs, DOCs)
 * - Intermediate processing artifacts
 * - RDF data for Neptune bulk loading (staging area)
 */
export class StorageStack extends cdk.Stack {
  public readonly documentBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    /**
     * Create S3 bucket for document storage
     * 
     * Configuration rationale:
     * - Versioning: Required by design doc to track document changes
     * - Encryption: Security best practice for data at rest
     * - Block public access: Prevent accidental exposure
     * - Auto-delete objects: Only for dev/test (DISABLE IN PRODUCTION)
     */
    this.documentBucket = new s3.Bucket(this, 'DocumentBucket', {
      bucketName: undefined, // Let CloudFormation generate unique name
      versioned: true, // Enable versioning as per requirements
      encryption: s3.BucketEncryption.S3_MANAGED, // SSE-S3 (can upgrade to KMS for more control)
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL, // Security: Block all public access
      removalPolicy: cdk.RemovalPolicy.RETAIN, // IMPORTANT: Retain bucket on stack deletion (change to DESTROY for dev only)
      autoDeleteObjects: false, // IMPORTANT: Must be false when removalPolicy is RETAIN
      
      /**
       * CORS configuration for browser-based uploads
       * Allows presigned URL uploads directly from client applications
       */
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.POST,
            s3.HttpMethods.PUT,
          ],
          allowedOrigins: ['*'], // TODO: Restrict to specific domains in production
          allowedHeaders: ['*'],
          exposedHeaders: ['ETag'],
          maxAge: 3000,
        },
      ],

      /**
       * Lifecycle rules for cost optimization
       * 
       * Strategy:
       * - Current versions: Keep in Standard storage for fast access
       * - Non-current versions (old): Transition to Glacier after 30 days
       * - Delete old versions after 90 days to manage costs
       * 
       * Adjust based on compliance and retention requirements
       */
      lifecycleRules: [
        {
          id: 'TransitionOldVersionsToGlacier',
          enabled: true,
          noncurrentVersionTransitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(30),
            },
          ],
          noncurrentVersionExpiration: cdk.Duration.days(90),
        },
        {
          id: 'DeleteIncompleteMultipartUploads',
          enabled: true,
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(7),
        },
      ],

      /**
       * EventBridge notifications
       * 
       * Enable EventBridge for all bucket events.
       * This allows EventBridge rules to filter and route S3 events
       * to Step Functions for processing.
       * 
       * More flexible than direct S3 event notifications to Lambda/SNS/SQS.
       */
      eventBridgeEnabled: true,
    });

    /**
     * Optional: S3 Object Tags for metadata propagation
     * 
     * The upload handler Lambda can add tags to uploaded objects
     * containing metadata (keywords, document type, etc.)
     * These tags are accessible in EventBridge events and can be
     * passed to the Step Functions workflow.
     */

    /**
     * Optional: S3 Inventory for auditing
     * Uncomment to enable daily inventory reports
     */
    // this.documentBucket.addInventory({
    //   destination: {
    //     bucketArn: inventoryBucket.bucketArn,
    //     prefix: 'inventory',
    //   },
    //   frequency: s3.InventoryFrequency.DAILY,
    //   includeObjectVersions: s3.InventoryObjectVersion.ALL,
    //   inventoryId: 'GraphRagDocumentInventory',
    // });

    /**
     * Create a separate prefix/folder for Neptune bulk loading staging
     * Lambda functions will write RDF files here before loading to Neptune
     */
    // Note: S3 doesn't have true folders, but we document the naming convention
    // Staging path: s3://<bucket>/neptune-staging/<document-id>/data.rdf

    /**
     * Stack Outputs
     */
    new cdk.CfnOutput(this, 'DocumentBucketName', {
      value: this.documentBucket.bucketName,
      description: 'S3 bucket name for document uploads',
      exportName: 'GraphRag-DocumentBucketName',
    });

    new cdk.CfnOutput(this, 'DocumentBucketArn', {
      value: this.documentBucket.bucketArn,
      description: 'S3 bucket ARN for IAM policies',
      exportName: 'GraphRag-DocumentBucketArn',
    });
  }
}

