---
name: aws-networking-and-compute
description: Provides production AWS infrastructure-as-code blueprints for multi-AZ VPCs, VPC Endpoints/PrivateLink, Transit Gateways, EKS/ECS Fargate container platforms, Lambda/EventBridge serverless architectures, and S3/RDS/DynamoDB stateful storage across CDK, CloudFormation, Terraform, Pulumi, and Crossplane.
---

# AWS Networking, Compute, Containers, Serverless & Storage Blueprints

Use this skill whenever designing or authoring AWS VPC networking, EKS/ECS container platforms, EC2 Auto Scaling, serverless event topologies, or stateful storage in **any IaC engine** (`aws-cdk`, `aws-cloudformation`, `aws-terraform`, `aws-pulumi`, `aws-crossplane`).

## 1. Production VPC & Network Topology Standards

Every production VPC authored in IaC must enforce these architectural invariants (see [`references/vpc-multi-az.md`](references/vpc-multi-az.md) and [`references/vpc-endpoints.md`](references/vpc-endpoints.md)):

1. **Three-Tier Multi-AZ Subnetting (Minimum 3 AZs for Production)**:
   - **Public Subnets** (`/20` or `/24` per AZ): Only for internet-facing Application/Network Load Balancers and NAT Gateways (`map_public_ip_on_launch = false` by default).
   - **Private Application Subnets**: For EKS nodes, ECS Fargate tasks, Lambda VPC interfaces, and EC2 Auto Scaling groups; egress via AZ-local NAT Gateways.
   - **Isolated Data Subnets**: For RDS/Aurora, ElastiCache, OpenSearch, and Redshift (`SubnetGroup`); zero route to IGW or NAT Gateway.
2. **Gateway & Interface VPC Endpoints (Cost & Security)**:
   - Always provision free **Gateway VPC Endpoints** for `com.amazonaws.<region>.s3` and `com.amazonaws.<region>.dynamodb` attached to all private/isolated route tables to avoid $0.045/GB NAT Gateway data-processing charges.
   - For high-throughput or air-gapped private subnets, provision **Interface VPC Endpoints** (`ecr.api`, `ecr.dkr`, `logs`, `sts`, `secretsmanager`, `ssm`, `ssmmessages`, `ec2messages`) with Private DNS enabled.
3. **VPC Flow Logs & Default Security Group Hardening**:
   - Enable VPC Flow Logs (`ALL` or `REJECT` traffic) delivered to an encrypted S3 bucket or CloudWatch Log Group.
   - Restrict the VPC Default Security Group to zero ingress and zero egress rules (`restrict_default_security_group = true` in CDK / `aws_default_security_group` with empty rules in Terraform).

## 2. Container Platforms: Amazon EKS & Amazon ECS Fargate

See [`references/eks.md`](references/eks.md) and [`references/ecs.md`](references/ecs.md):
- **Amazon EKS**:
  - Use `authentication_mode = "API_AND_CONFIG_MAP"` (or `"API"`), disallow public-only API endpoints without CIDR restrictions (`endpoint_private_access = true`), and enable control-plane logs (`api`, `audit`, `authenticator`).
  - Use **EKS Pod Identity** (`aws_eks_pod_identity_association` / `AWS::EKS::PodIdentityAssociation`) or IRSA for workload IAM, and **Karpenter** or EKS Auto Mode / Managed Node Groups in private subnets.
- **Amazon ECS Fargate**:
  - Enable Container Insights (`enhanced`), set explicit `TaskRoleArn` (workload permissions) separate from `ExecutionRoleArn` (image pull/log push), run tasks in private subnets with `assignPublicIp: DISABLED`, and configure deployment circuit breakers with automatic rollback (`enable: true, rollback: true`).

## 3. Serverless & Event-Driven Compute

See [`references/serverless-architecture.md`](references/serverless-architecture.md):
- **AWS Lambda**: Prefer `arm64` (Graviton2) for 20% better price-performance, set explicit CloudWatch Log Group retention (`RetentionInDays: 30` or `90`), enable X-Ray active tracing (`TracingConfig: Active`), and configure Dead-Letter Queues (DLQ) or EventBridge Destinations on asynchronous invocations.
- **API Gateway / ALB**: Attach AWS WAFv2 WebACLs (`AWSManagedRulesCommonRuleSet`, rate-based rules) and enable access logging.

## 4. Stateful Storage & Database Guardrails

See [`references/s3-general-purpose-knowledge.md`](references/s3-general-purpose-knowledge.md) and [`references/ebs-knowledge.md`](references/ebs-knowledge.md):
- **Amazon S3**: Block all public access (`BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets`), enforce BucketOwnerEnforced object ownership (`ACLs disabled`), enable versioning + lifecycle rules to expire noncurrent versions and abort incomplete multipart uploads after 7 days.
- **Amazon RDS / Aurora**: Deploy in isolated DB subnet groups, enable `MultiAZ` for production, enable `StorageEncrypted` with KMS, enable `DeletionProtection`, set `ManageMasterUserPassword: true`, and configure automated backups (`BackupRetentionPeriod >= 7`).
- **Amazon EBS**: Always use `gp3` (or `io2` for extreme IOPS) instead of legacy `gp2`/`io1`, with encryption enabled.

## 5. Bundled Reference Guides

- **[`references/vpc-multi-az.md`](references/vpc-multi-az.md)**: Multi-AZ VPC CIDR math, route tables, NAT Gateway high availability, and Flow Logs.
- **[`references/vpc-endpoints.md`](references/vpc-endpoints.md)**: Gateway and Interface VPC Endpoints (PrivateLink) and endpoint policies.
- **[`references/transit-gateway.md`](references/transit-gateway.md)**: Multi-VPC hub-and-spoke Transit Gateway routing and RAM sharing.
- **[`references/eks.md`](references/eks.md)** & **[`references/ecs.md`](references/ecs.md)**: EKS and ECS Fargate production IaC patterns.
- **[`references/serverless-architecture.md`](references/serverless-architecture.md)**: Lambda, API Gateway, Step Functions, and EventBridge IaC patterns.
- **[`references/s3-general-purpose-knowledge.md`](references/s3-general-purpose-knowledge.md)** & **[`references/ebs-knowledge.md`](references/ebs-knowledge.md)**: Storage security, performance tiers, and lifecycle policies.
