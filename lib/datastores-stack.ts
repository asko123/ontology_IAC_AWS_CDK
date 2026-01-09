import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as neptune from 'aws-cdk-lib/aws-neptune';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

/**
 * Props for DataStoresStack
 */
export interface DataStoresStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  neptuneSecurityGroup: ec2.SecurityGroup;
  openSearchSecurityGroup: ec2.SecurityGroup;
}

/**
 * DataStoresStack
 * 
 * Creates data storage infrastructure:
 * - Amazon Neptune: Graph database for RDF/ontology storage
 * - Amazon OpenSearch: Vector database for embedding-based similarity search
 * 
 * Both services are deployed in private VPC subnets for security.
 * 
 * Cost considerations:
 * - Neptune: Provisioned instances run 24/7 (consider Serverless for intermittent workloads)
 * - OpenSearch: Provisioned instances run 24/7 (t3.small.search is minimum for production)
 * - Data transfer within VPC is free
 */
export class DataStoresStack extends cdk.Stack {
  public readonly neptuneCluster: neptune.CfnDBCluster;
  public readonly neptuneInstance: neptune.CfnDBInstance;
  public readonly openSearchDomain: opensearch.Domain;

  constructor(scope: Construct, id: string, props: DataStoresStackProps) {
    super(scope, id, props);

    const { vpc, neptuneSecurityGroup, openSearchSecurityGroup } = props;

    /**
     * ============================================================
     * AMAZON NEPTUNE CLUSTER
     * ============================================================
     * 
     * Neptune is a fully managed graph database supporting:
     * - Apache TinkerPop Gremlin (property graph queries)
     * - RDF/SPARQL (semantic web queries)
     * 
     * For this use case, we'll use RDF/SPARQL for ontology storage.
     */

    /**
     * Create Neptune Subnet Group
     * Neptune instances must be launched in a DB subnet group
     * spanning at least 2 AZs for high availability
     */
    const neptuneSubnetGroup = new neptune.CfnDBSubnetGroup(this, 'NeptuneSubnetGroup', {
      dbSubnetGroupName: 'graph-rag-neptune-subnet-group',
      dbSubnetGroupDescription: 'Subnet group for Neptune cluster in private subnets',
      subnetIds: vpc.privateSubnets.map(subnet => subnet.subnetId),
    });

    /**
     * Create Neptune Cluster Parameter Group
     * Configure Neptune-specific parameters
     */
    const neptuneClusterParameterGroup = new neptune.CfnDBClusterParameterGroup(this, 'NeptuneClusterParameterGroup', {
      family: 'neptune1.3', // Latest Neptune engine family (check AWS docs for updates)
      description: 'Custom parameter group for Graph RAG Neptune cluster',
      parameters: {
        // Enable audit logs for compliance (optional)
        neptune_enable_audit_log: '0', // Set to 1 to enable (incurs CloudWatch costs)
        // Query timeout (milliseconds)
        neptune_query_timeout: '120000', // 2 minutes
      },
      name: 'graph-rag-neptune-cluster-params',
    });

    /**
     * Create Neptune DB Cluster
     * 
     * Configuration:
     * - Engine: neptune (supports both Gremlin and SPARQL)
     * - Backup retention: 7 days (increase for production)
     * - Encryption at rest: Enabled
     * - IAM authentication: Enabled (more secure than DB credentials)
     */
    this.neptuneCluster = new neptune.CfnDBCluster(this, 'NeptuneCluster', {
      dbClusterIdentifier: 'graph-rag-neptune-cluster',
      dbSubnetGroupName: neptuneSubnetGroup.dbSubnetGroupName,
      vpcSecurityGroupIds: [neptuneSecurityGroup.securityGroupId],
      dbClusterParameterGroupName: neptuneClusterParameterGroup.name,
      
      // Backup and maintenance
      backupRetentionPeriod: 7, // Days (1-35, increase for production)
      preferredBackupWindow: '03:00-04:00', // UTC
      preferredMaintenanceWindow: 'sun:04:00-sun:05:00', // UTC
      
      // Security
      storageEncrypted: true, // Encryption at rest
      iamAuthEnabled: true, // Enable IAM database authentication
      
      // Engine version
      engineVersion: '1.3.1.0', // Check AWS docs for latest version
      
      // Optional: Enable CloudWatch logs export
      // enableCloudwatchLogsExports: ['audit'], // Uncomment to export audit logs
    });

    neptuneCluster.addDependency(neptuneSubnetGroup);
    neptuneCluster.addDependency(neptuneClusterParameterGroup);

    /**
     * Create Neptune DB Parameter Group (for instances)
     */
    const neptuneInstanceParameterGroup = new neptune.CfnDBParameterGroup(this, 'NeptuneInstanceParameterGroup', {
      family: 'neptune1.3',
      description: 'Custom parameter group for Neptune instances',
      parameters: {
        // Instance-level parameters can be added here
      },
      name: 'graph-rag-neptune-instance-params',
    });

    /**
     * Create Neptune DB Instance (Primary)
     * 
     * Instance types:
     * - db.t3.medium: Smallest production-capable instance (2 vCPU, 4 GB RAM)
     * - db.r6g.large: Better for memory-intensive workloads (2 vCPU, 16 GB RAM)
     * 
     * For dev/test, db.t3.medium is sufficient.
     * For production, consider db.r6g.large or larger based on data volume.
     */
    this.neptuneInstance = new neptune.CfnDBInstance(this, 'NeptuneInstance', {
      dbInstanceIdentifier: 'graph-rag-neptune-instance-1',
      dbClusterIdentifier: this.neptuneCluster.dbClusterIdentifier,
      dbInstanceClass: 'db.t3.medium', // Start small, scale up based on load
      dbParameterGroupName: neptuneInstanceParameterGroup.name,
    });

    this.neptuneInstance.addDependency(this.neptuneCluster);
    this.neptuneInstance.addDependency(neptuneInstanceParameterGroup);

    /**
     * Optional: Add read replica for high availability and read scaling
     * Uncomment to create a read replica in a different AZ
     */
    // const neptuneReadReplica = new neptune.CfnDBInstance(this, 'NeptuneReadReplica', {
    //   dbInstanceIdentifier: 'graph-rag-neptune-instance-2',
    //   dbClusterIdentifier: this.neptuneCluster.dbClusterIdentifier,
    //   dbInstanceClass: 'db.t3.medium',
    //   dbParameterGroupName: neptuneInstanceParameterGroup.name,
    // });
    // neptuneReadReplica.addDependency(this.neptuneInstance);

    /**
     * ============================================================
     * AMAZON OPENSEARCH DOMAIN
     * ============================================================
     * 
     * OpenSearch is used for vector similarity search using k-NN plugin.
     * Stores document embeddings with metadata for RAG retrieval.
     * 
     * Architecture:
     * - 2 data nodes for redundancy (minimum for production)
     * - t3.small.search instances (smallest production-capable)
     * - EBS storage with gp3 volumes
     */

    /**
     * Create IAM Service-Linked Role for OpenSearch
     * Required for OpenSearch to access VPC and other AWS resources
     * 
     * Note: This role may already exist in your account.
     * CDK will handle gracefully if it exists.
     */
    // const openSearchServiceRole = new iam.CfnServiceLinkedRole(this, 'OpenSearchServiceLinkedRole', {
    //   awsServiceName: 'es.amazonaws.com',
    // });

    /**
     * Create OpenSearch Domain
     * 
     * Configuration:
     * - VPC deployment for security
     * - 2 AZs with zone awareness for high availability
     * - EBS storage (gp3 for better price/performance)
     * - Encryption at rest and in transit
     * - Fine-grained access control (optional, can be enabled)
     */
    this.openSearchDomain = new opensearch.Domain(this, 'OpenSearchDomain', {
      domainName: 'graph-rag-opensearch',
      version: opensearch.EngineVersion.OPENSEARCH_2_11, // Latest version (check AWS docs)
      
      /**
       * Cluster configuration
       * 
       * Instance types:
       * - t3.small.search: Minimum for production (1 vCPU, 2 GB RAM, ~$30/month per instance)
       * - t3.medium.search: Better performance (2 vCPU, 4 GB RAM)
       * - r6g.large.search: Memory-optimized for large embedding datasets
       */
      capacity: {
        dataNodes: 2, // Minimum for zone awareness (high availability)
        dataNodeInstanceType: 't3.small.search', // Cost-effective for small-medium workloads
        multiAzWithStandbyEnabled: false, // Multi-AZ with standby (3 AZs) for even higher availability
      },
      
      /**
       * EBS storage configuration
       * Each data node gets its own EBS volume
       */
      ebs: {
        enabled: true,
        volumeSize: 50, // GB per node (start with 50 GB, scale up as needed)
        volumeType: ec2.EbsDeviceVolumeType.GP3, // gp3 offers better price/performance than gp2
        iops: 3000, // Baseline for gp3
        throughput: 125, // MiB/s
      },
      
      /**
       * Zone awareness for high availability
       * Distributes data nodes across 2 AZs
       */
      zoneAwareness: {
        enabled: true,
        availabilityZoneCount: 2,
      },
      
      /**
       * VPC configuration
       * Deploy in private subnets with security group
       */
      vpc: vpc,
      vpcSubnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
      securityGroups: [openSearchSecurityGroup],
      
      /**
       * Security configuration
       */
      encryptionAtRest: {
        enabled: true, // Encrypt data at rest (uses AWS-managed keys)
      },
      nodeToNodeEncryption: true, // Encrypt inter-node communication
      enforceHttps: true, // Require HTTPS for API calls
      
      /**
       * Access policy
       * Allow access from Lambda execution role (configured in ProcessingStack)
       * 
       * Note: Fine-grained access control can be enabled for more granular permissions
       * but requires additional configuration and master user credentials.
       */
      accessPolicies: [
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          principals: [new iam.AnyPrincipal()], // Will be restricted by security group
          actions: ['es:*'],
          resources: ['*'],
        }),
      ],
      
      /**
       * Advanced options
       * Enable k-NN plugin for vector similarity search
       */
      // Note: k-NN is enabled by default in OpenSearch 2.x
      // Additional configuration done via Lambda initialization function
      
      /**
       * Logging configuration (optional)
       * Uncomment to enable various log types
       */
      // logging: {
      //   slowSearchLogEnabled: true,
      //   appLogEnabled: true,
      //   slowIndexLogEnabled: true,
      // },
      
      /**
       * Automated snapshot hour (UTC)
       */
      automatedSnapshotStartHour: 2, // 2 AM UTC
      
      /**
       * Removal policy
       * RETAIN for production to prevent accidental data loss
       */
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    /**
     * ============================================================
     * STACK OUTPUTS
     * ============================================================
     */

    /**
     * Neptune Outputs
     */
    new cdk.CfnOutput(this, 'NeptuneClusterEndpoint', {
      value: this.neptuneCluster.attrEndpoint,
      description: 'Neptune cluster endpoint for SPARQL/Gremlin queries',
      exportName: 'GraphRag-NeptuneClusterEndpoint',
    });

    new cdk.CfnOutput(this, 'NeptuneClusterReadEndpoint', {
      value: this.neptuneCluster.attrReadEndpoint,
      description: 'Neptune cluster read-only endpoint for load distribution',
      exportName: 'GraphRag-NeptuneReadEndpoint',
    });

    new cdk.CfnOutput(this, 'NeptuneClusterPort', {
      value: this.neptuneCluster.attrPort || '8182',
      description: 'Neptune cluster port',
      exportName: 'GraphRag-NeptunePort',
    });

    new cdk.CfnOutput(this, 'NeptuneClusterResourceId', {
      value: this.neptuneCluster.attrClusterResourceId,
      description: 'Neptune cluster resource ID for IAM policies',
      exportName: 'GraphRag-NeptuneClusterResourceId',
    });

    /**
     * OpenSearch Outputs
     */
    new cdk.CfnOutput(this, 'OpenSearchDomainEndpoint', {
      value: this.openSearchDomain.domainEndpoint,
      description: 'OpenSearch domain endpoint (HTTPS)',
      exportName: 'GraphRag-OpenSearchDomainEndpoint',
    });

    new cdk.CfnOutput(this, 'OpenSearchDomainArn', {
      value: this.openSearchDomain.domainArn,
      description: 'OpenSearch domain ARN for IAM policies',
      exportName: 'GraphRag-OpenSearchDomainArn',
    });

    new cdk.CfnOutput(this, 'OpenSearchDashboardsUrl', {
      value: `https://${this.openSearchDomain.domainEndpoint}/_dashboards`,
      description: 'OpenSearch Dashboards URL for visualization and management',
    });
  }
}

