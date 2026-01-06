import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

/**
 * Props for ApiStack
 */
export interface ApiStackProps extends cdk.StackProps {
  documentBucket: s3.Bucket;
}

/**
 * ApiStack
 * 
 * Creates API Gateway REST API for document uploads.
 * 
 * Endpoints:
 * - POST /upload: Upload document with metadata
 * - GET /presigned-url: Get presigned S3 URL for direct upload (alternative approach)
 * 
 * Features:
 * - CORS configuration for browser clients
 * - Request validation
 * - API key authentication (optional)
 * - CloudWatch logging
 * 
 * Two upload approaches:
 * 1. Direct upload via API Gateway (limited to 10MB)
 * 2. Presigned URL approach (supports larger files)
 */
export class ApiStack extends cdk.Stack {
  public readonly api: apigateway.RestApi;
  public readonly uploadHandler: lambda.Function;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    const { documentBucket } = props;

    /**
     * ============================================================
     * UPLOAD HANDLER LAMBDA
     * ============================================================
     * 
     * Handles document uploads with metadata.
     * 
     * Two modes:
     * 1. Direct upload: Receives base64-encoded file in request body
     * 2. Presigned URL: Generates presigned S3 URL for client-side upload
     * 
     * Process:
     * - Validate file type and size
     * - Extract metadata from request
     * - Upload to S3 with metadata as object tags
     * - Return upload confirmation
     */
    this.uploadHandler = new lambda.Function(this, 'UploadHandlerFunction', {
      functionName: 'graph-rag-upload-handler',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda/upload-handler'),
      timeout: cdk.Duration.seconds(30),
      memorySize: 512, // MB
      
      environment: {
        DOCUMENT_BUCKET_NAME: documentBucket.bucketName,
        MAX_FILE_SIZE_MB: '50',
        ALLOWED_FILE_TYPES: 'pdf,docx,csv,txt',
        PRESIGNED_URL_EXPIRY_SECONDS: '3600', // 1 hour
      },
      
      architecture: lambda.Architecture.ARM_64,
      
      description: 'Handles document uploads and generates presigned URLs',
    });

    /**
     * Grant S3 permissions to upload handler
     * - PutObject: Upload files
     * - PutObjectTagging: Add metadata as tags
     */
    documentBucket.grantPut(this.uploadHandler);
    documentBucket.grantPutAcl(this.uploadHandler);

    // Additional permission for presigned URLs
    this.uploadHandler.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        's3:PutObject',
        's3:PutObjectTagging',
      ],
      resources: [`${documentBucket.bucketArn}/*`],
    }));

    /**
     * ============================================================
     * API GATEWAY REST API
     * ============================================================
     * 
     * REST API with CORS support for browser clients.
     */
    this.api = new apigateway.RestApi(this, 'GraphRagApi', {
      restApiName: 'Graph RAG Upload API',
      description: 'API for uploading documents to Graph RAG system',
      
      /**
       * API Gateway deployment configuration
       */
      deployOptions: {
        stageName: 'prod',
        
        /**
         * Enable CloudWatch logging
         */
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,
        
        /**
         * Throttling configuration
         * Protect backend from excessive requests
         */
        throttlingBurstLimit: 100, // Burst capacity
        throttlingRateLimit: 50,   // Requests per second
      },
      
      /**
       * CORS configuration
       * Allow browser-based uploads from any origin
       * TODO: Restrict to specific domains in production
       */
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS, // Change to specific origins in production
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token',
        ],
        allowCredentials: true,
        maxAge: cdk.Duration.hours(1),
      },
      
      /**
       * Binary media types
       * Support for file uploads
       */
      binaryMediaTypes: [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/octet-stream',
        'multipart/form-data',
      ],
    });

    /**
     * ============================================================
     * API ENDPOINTS
     * ============================================================
     */

    /**
     * POST /upload
     * Direct file upload with metadata
     * 
     * Request body format (JSON):
     * {
     *   "fileName": "document.pdf",
     *   "fileContent": "<base64-encoded-content>",
     *   "metadata": {
     *     "keywords": "compliance,security",
     *     "documentType": "policy",
     *     "author": "John Doe"
     *   }
     * }
     * 
     * Response:
     * {
     *   "statusCode": 200,
     *   "message": "Upload successful",
     *   "documentId": "uuid",
     *   "s3Key": "documents/uuid/document.pdf"
     * }
     */
    const uploadResource = this.api.root.addResource('upload');
    
    /**
     * Request validator
     * Validates request body structure
     */
    const requestValidator = new apigateway.RequestValidator(this, 'UploadRequestValidator', {
      restApi: this.api,
      requestValidatorName: 'upload-request-validator',
      validateRequestBody: true,
      validateRequestParameters: false,
    });

    /**
     * Request model
     * Defines expected request body schema
     */
    const uploadRequestModel = new apigateway.Model(this, 'UploadRequestModel', {
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
            properties: {
              keywords: { type: apigateway.JsonSchemaType.STRING },
              documentType: { type: apigateway.JsonSchemaType.STRING },
              author: { type: apigateway.JsonSchemaType.STRING },
            },
          },
        },
      },
    });

    /**
     * Lambda integration for upload endpoint
     */
    const uploadIntegration = new apigateway.LambdaIntegration(this.uploadHandler, {
      proxy: true, // Lambda proxy integration
      allowTestInvoke: true,
    });

    uploadResource.addMethod('POST', uploadIntegration, {
      requestValidator: requestValidator,
      requestModels: {
        'application/json': uploadRequestModel,
      },
      apiKeyRequired: false, // Set to true to require API keys
    });

    /**
     * GET /presigned-url
     * Generate presigned URL for direct S3 upload
     * 
     * This approach is better for large files (>10MB) as it bypasses API Gateway limits.
     * Client uploads directly to S3 using the presigned URL.
     * 
     * Query parameters:
     * - fileName: Name of file to upload
     * - fileType: MIME type (optional)
     * - metadata: JSON-encoded metadata (optional)
     * 
     * Response:
     * {
     *   "uploadUrl": "https://s3.amazonaws.com/...",
     *   "documentId": "uuid",
     *   "expiresIn": 3600
     * }
     */
    const presignedUrlResource = this.api.root.addResource('presigned-url');
    
    const presignedUrlIntegration = new apigateway.LambdaIntegration(this.uploadHandler, {
      proxy: true,
    });

    presignedUrlResource.addMethod('GET', presignedUrlIntegration, {
      requestParameters: {
        'method.request.querystring.fileName': true,
        'method.request.querystring.fileType': false,
      },
      apiKeyRequired: false,
    });

    /**
     * Optional: API Key for authentication
     * Uncomment to enable API key requirement
     */
    // const apiKey = this.api.addApiKey('GraphRagApiKey', {
    //   apiKeyName: 'graph-rag-api-key',
    //   description: 'API key for Graph RAG upload endpoint',
    // });
    // 
    // const usagePlan = this.api.addUsagePlan('GraphRagUsagePlan', {
    //   name: 'graph-rag-usage-plan',
    //   throttle: {
    //     rateLimit: 100,
    //     burstLimit: 200,
    //   },
    //   quota: {
    //     limit: 10000,
    //     period: apigateway.Period.MONTH,
    //   },
    // });
    // 
    // usagePlan.addApiKey(apiKey);
    // usagePlan.addApiStage({
    //   stage: this.api.deploymentStage,
    // });

    /**
     * Optional: Custom domain
     * Uncomment and configure to use custom domain
     */
    // const certificate = acm.Certificate.fromCertificateArn(
    //   this,
    //   'Certificate',
    //   'arn:aws:acm:region:account:certificate/xxx'
    // );
    // 
    // const domainName = new apigateway.DomainName(this, 'CustomDomain', {
    //   domainName: 'api.yourdomain.com',
    //   certificate: certificate,
    //   endpointType: apigateway.EndpointType.REGIONAL,
    // });
    // 
    // domainName.addBasePathMapping(this.api, {
    //   basePath: 'v1',
    // });

    /**
     * ============================================================
     * STACK OUTPUTS
     * ============================================================
     */
    new cdk.CfnOutput(this, 'ApiEndpoint', {
      value: this.api.url,
      description: 'Graph RAG API Gateway endpoint URL',
      exportName: 'GraphRag-ApiEndpoint',
    });

    new cdk.CfnOutput(this, 'UploadEndpoint', {
      value: `${this.api.url}upload`,
      description: 'Direct upload endpoint',
    });

    new cdk.CfnOutput(this, 'PresignedUrlEndpoint', {
      value: `${this.api.url}presigned-url`,
      description: 'Presigned URL generation endpoint',
    });

    new cdk.CfnOutput(this, 'ApiId', {
      value: this.api.restApiId,
      description: 'API Gateway REST API ID',
    });

    /**
     * Example curl command for testing
     */
    new cdk.CfnOutput(this, 'ExampleCurlCommand', {
      value: `curl -X POST ${this.api.url}upload -H "Content-Type: application/json" -d '{"fileName":"test.pdf","fileContent":"<base64>","metadata":{"keywords":"test"}}'`,
      description: 'Example curl command for testing upload endpoint',
    });
  }
}

