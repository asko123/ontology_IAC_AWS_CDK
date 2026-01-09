import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

/**
 * NetworkingStack
 * 
 * Creates VPC infrastructure required for Neptune and OpenSearch.
 * Both services require VPC deployment for security and network isolation.
 * 
 * Resources created:
 * - VPC with public and private subnets across 2 AZs
 * - Internet Gateway for public subnet access
 * - NAT Gateways for private subnet outbound access
 * - Security groups for Neptune, OpenSearch, and Lambda functions
 */
export class NetworkingStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly neptuneSecurityGroup: ec2.SecurityGroup;
  public readonly openSearchSecurityGroup: ec2.SecurityGroup;
  public readonly lambdaSecurityGroup: ec2.SecurityGroup;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    /**
     * Create VPC with public and private subnets
     * 
     * Configuration:
     * - 2 Availability Zones for high availability
     * - Public subnets: For NAT Gateways and potential bastion hosts
     * - Private subnets: For Neptune, OpenSearch, and Lambda functions
     * - Isolated subnets: Additional isolation tier (optional for future use)
     * 
     * Cost consideration: NAT Gateways incur hourly charges
     * Alternative: Use VPC endpoints for AWS services to reduce NAT usage
     */
    this.vpc = new ec2.Vpc(this, 'GraphRagVpc', {
      vpcName: 'graph-rag-vpc',
      ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
      maxAzs: 2, // Deploy across 2 AZs for high availability
      natGateways: 1, // Cost optimization: Use 1 NAT Gateway (increase for prod HA)
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
        {
          cidrMask: 28,
          name: 'Isolated',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        },
      ],
      // Enable DNS for internal service discovery
      enableDnsHostnames: true,
      enableDnsSupport: true,
    });

    /**
     * Security Group for Neptune Cluster
     * 
     * Allows inbound connections from Lambda functions on Neptune ports:
     * - Port 8182: Gremlin/SPARQL (default Neptune endpoint)
     */
    this.neptuneSecurityGroup = new ec2.SecurityGroup(this, 'NeptuneSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: 'neptune-sg',
      description: 'Security group for Neptune graph database cluster',
      allowAllOutbound: false, // Restrict outbound for security
    });

    /**
     * Security Group for OpenSearch Domain
     * 
     * Allows inbound HTTPS connections from Lambda functions:
     * - Port 443: OpenSearch API endpoint
     */
    this.openSearchSecurityGroup = new ec2.SecurityGroup(this, 'OpenSearchSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: 'opensearch-sg',
      description: 'Security group for OpenSearch vector search domain',
      allowAllOutbound: false,
    });

    /**
     * Security Group for Lambda Functions
     * 
     * Lambda functions need to:
     * - Connect to Neptune (port 8182)
     * - Connect to OpenSearch (port 443)
     * - Access internet for AWS API calls (via NAT Gateway)
     */
    this.lambdaSecurityGroup = new ec2.SecurityGroup(this, 'LambdaSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: 'lambda-sg',
      description: 'Security group for Lambda functions in processing pipeline',
      allowAllOutbound: true, // Allow outbound for AWS API calls and external dependencies
    });

    /**
     * Configure Security Group Rules
     * 
     * Allow Lambda → Neptune communication
     */
    this.neptuneSecurityGroup.addIngressRule(
      this.lambdaSecurityGroup,
      ec2.Port.tcp(8182),
      'Allow Lambda functions to connect to Neptune on port 8182'
    );

    /**
     * Allow Lambda → OpenSearch communication
     */
    this.openSearchSecurityGroup.addIngressRule(
      this.lambdaSecurityGroup,
      ec2.Port.tcp(443),
      'Allow Lambda functions to connect to OpenSearch on port 443'
    );

    /**
     * Allow Neptune internal cluster communication (required for replication)
     */
    this.neptuneSecurityGroup.addIngressRule(
      this.neptuneSecurityGroup,
      ec2.Port.tcp(8182),
      'Allow Neptune cluster instances to communicate with each other'
    );

    /**
     * Allow OpenSearch internal node communication (required for cluster operations)
     */
    this.openSearchSecurityGroup.addIngressRule(
      this.openSearchSecurityGroup,
      ec2.Port.allTcp(),
      'Allow OpenSearch nodes to communicate with each other'
    );

    /**
     * VPC Flow Logs (Optional but recommended for security auditing)
     * Uncomment to enable VPC traffic logging to CloudWatch
     */
    // const flowLogRole = new iam.Role(this, 'FlowLogRole', {
    //   assumedBy: new iam.ServicePrincipal('vpc-flow-logs.amazonaws.com'),
    // });
    // 
    // const logGroup = new logs.LogGroup(this, 'VpcFlowLogGroup', {
    //   retention: logs.RetentionDays.ONE_WEEK,
    // });
    // 
    // new ec2.FlowLog(this, 'VpcFlowLog', {
    //   resourceType: ec2.FlowLogResourceType.fromVpc(this.vpc),
    //   destination: ec2.FlowLogDestination.toCloudWatchLogs(logGroup, flowLogRole),
    // });

    /**
     * Stack Outputs
     */
    new cdk.CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId,
      description: 'VPC ID for Graph RAG infrastructure',
      exportName: 'GraphRag-VpcId',
    });

    new cdk.CfnOutput(this, 'PrivateSubnetIds', {
      value: this.vpc.privateSubnets.map(subnet => subnet.subnetId).join(','),
      description: 'Private subnet IDs where Neptune and OpenSearch are deployed',
      exportName: 'GraphRag-PrivateSubnetIds',
    });

    new cdk.CfnOutput(this, 'NeptuneSecurityGroupId', {
      value: this.neptuneSecurityGroup.securityGroupId,
      description: 'Security group ID for Neptune cluster',
      exportName: 'GraphRag-NeptuneSecurityGroupId',
    });

    new cdk.CfnOutput(this, 'OpenSearchSecurityGroupId', {
      value: this.openSearchSecurityGroup.securityGroupId,
      description: 'Security group ID for OpenSearch domain',
      exportName: 'GraphRag-OpenSearchSecurityGroupId',
    });
  }
}

