---
name: platform-golden-path-scaffolder
description: Translates high-level application developer or QA engineer requests (e.g., "deploy my web app", "spin up a staging environment", "set up a worker queue", "create an internal microservice") into production-ready, Well-Architected AWS Golden Path architectures with environment tiering, pre-deployment FinOps cost tables, cfn-lint/cfn-guard IaC validation, least-privilege IAM simulation, Service Quota checks, and Day-2 CloudWatch alarms.
metadata:
  version: "2.0"
---

# Platform Golden Path Scaffolder

## Purpose

Application developers and QA engineers focus on business logic, feature velocity, and test verification rather than VPC CIDR math, IAM trust policies, Karpenter node consolidation, or NAT Gateway data-processing charges. Activate this skill whenever a user requests a new environment, service deployment, or architectural setup without specifying low-level AWS resource configurations.

This skill operates as a **Cognitive Translation Layer**: it intercepts high-level workload intent and orchestrates infrastructure-as-code authoring, security compliance, identity simulation, observability wiring, and cost estimation transparently.

---

## Mandatory 6-Step Execution Workflow

### Step 1: Intent Classification, Service Quota Preflight & Environment Tiering

Classify the workload into one of five canonical AWS Golden Paths and determine the target environment tier (`dev`, `qa`/`staging`, or `prod`):

| Golden Path | Reference Architecture | Primary Skills Orchestrated |
|---|---|---|
| **1. Containerized Web / API Service** | Route 53 + CloudFront/WAFv2 + ALB + **ECS Fargate / ECS Express Mode** (or **EKS Auto Mode / Karpenter**) in Multi-AZ Private Subnets + ECR + Secrets Manager | `aws-containers`, `creating-production-vpc-multi-az`, `configuring-vpc-endpoints-for-private-aws-service-access`, `waf`, `route53` |
| **2. Event-Driven Serverless API / Worker** | API Gateway (HTTP API v2 or REST API v1) + **AWS Lambda (`arm64`)** + SQS (with DLQ) / SNS / EventBridge / Step Functions (or Lambda Durable Functions) + DynamoDB | `aws-serverless`, `aws-messaging-and-streaming`, `aws-stateful-data-and-caching-platform` |
| **3. Stateful Full-Stack Platform** | Multi-AZ VPC + ECS/EKS Compute + **Aurora PostgreSQL/MySQL (with RDS Proxy)** or DynamoDB + **ElastiCache (Valkey)** + Secrets Manager rotation + AWS Backup | `aws-stateful-data-and-caching-platform`, `aws-containers`, `creating-production-vpc-multi-az` |
| **4. Static / Edge SPA & Media Frontend** | S3 (Private Bucket + KMS/SSE-S3) + **CloudFront Origin Access Control (OAC)** + `SecurityHeadersPolicy` + Route 53 + AWS WAFv2 | `cloudfront`, `routing-traffic-with-route53-and-cloudfront`, `waf`, `aws-storage` |
| **5. Internal Zero-Trust Microservice Mesh** | Multi-VPC / Multi-Account **Amazon VPC Lattice** Service Network (or **ECS Service Connect**) with `AWS_IAM` SigV4 auth policies + Private Route 53 Profiles | `aws-landing-zone-and-platform-governance`, `aws-containers`, `aws-networking` |

#### Environment Tier Sizing Rules
- **`dev` and `qa`/`staging` Tiers (Cost-Optimized Defaults)**:
  - Default to burstable, Spot, or scale-to-zero compute (`FARGATE_SPOT` capacity provider, Graviton `t4g`/`m7g` Spot, Lambda `arm64`, Aurora Serverless v2 with `MinCapacity: 0` or `0.5` ACU, ElastiCache Serverless).
  - Replace expensive per-AZ NAT Gateways (`~$32.40/mo/AZ`) with free **S3/DynamoDB Gateway Endpoints (`$0.00`)**, targeted **Interface Endpoints** (`ecr.api`, `ecr.dkr`, `logs`, `secretsmanager`), or a single shared non-prod NAT Gateway / IPv6 Egress-Only Internet Gateway (`$0.00`).
  - Set CloudWatch Log Groups to `RetentionInDays: 7` or `14`.
- **`prod` Tier (Resilience & High-Availability Defaults)**:
  - Strictly enforce Multi-AZ redundancy across at least 2–3 Availability Zones (Multi-AZ NAT or centralized Transit Gateway egress, Multi-AZ ALB, Multi-AZ Aurora with RDS Proxy, Multi-AZ ElastiCache with Auto-Failover).
  - Mix On-Demand base capacity (`FARGATE` base `2`, `weight: 1`) with Spot burst capacity (`FARGATE_SPOT` `weight: 3`) or Karpenter multi-arch (`arm64`/`amd64`) `NodePool`s with `PodDisruptionBudget`s.
  - Enforce `DeletionPolicy: Retain` / `RemovalPolicy.RETAIN` and AWS Backup plans on all stateful storage and databases.
  - Check regional service quotas (`aws service-quotas list-service-quotas` via `aws-mcp`) for vCPUs, NAT Gateways, and Elastic IPs before deployment.

---

### Step 2: Pre-Deployment FinOps Cost Estimation

Before writing or deploying infrastructure, delegate to `aws-finops-and-cost-optimization` and query the `pricing` MCP server (`awslabs.aws-pricing-mcp-server`) to estimate the monthly run rate of the proposed Golden Path. Present a clear Markdown table showing:
1. **Fixed hourly/monthly baseline costs** (e.g., NAT Gateways `$32.40/mo/AZ`, ALB `$16.20/mo`, EKS Control Plane `$73.00/mo`, VPC Interface Endpoints `$7.20/mo/AZ`, Route 53 Hosted Zone `$0.50/mo`).
2. **Variable / usage-based costs** (e.g., Fargate `arm64` vCPU/GB-hours, Lambda invocations/GB-s, Aurora ACU-hours, DynamoDB RCU/WCU, NAT data processing `$0.045/GB`, CloudWatch Logs ingestion `$0.50/GB`).
3. **Side-by-side Dev/QA vs. Prod monthly cost comparison** with concrete cost-saving alternatives.

---

### Step 3: Declarative IaC Generation (Never ClickOps)

Delegate to `aws-iac-cloudformation-cdk` to author the infrastructure as **AWS CDK (TypeScript/Python)**, **AWS CloudFormation YAML/JSON**, **AWS SAM (`template.yaml`)**, or **Terraform (`*.tf`)** matching the repository's existing convention:
- **Mandatory Cost & Governance Tagging**: Apply `Environment`, `Owner`, `CostCenter`, `Workload`, and `ManagedBy: aws-platform-engineer-agent` tags at the stack/provider level so all child resources inherit them.
- **Zero Public Compute / Database Placement**: Never place application compute (EC2, ECS tasks, EKS nodes, Lambda functions) or stateful data stores (RDS, Aurora, ElastiCache, MSK, OpenSearch) in public subnets. Only Internet-facing ALBs, NLBs, and NAT Gateways belong in public subnets.
- **PrivateLink First**: Use `configuring-vpc-endpoints-for-private-aws-service-access` to attach free S3 and DynamoDB Gateway Endpoints (`$0.00`) to every private route table and Interface Endpoints for ECR, CloudWatch Logs, SSM, and Secrets Manager where appropriate.
- **2026 Service Guardrail**: Never provision AWS App Runner (sunset April 30, 2026); use **Amazon ECS Express Mode** or standard ECS Fargate + ALB instead.

---

### Step 4: Static Validation & Security Compliance Gating

Execute the `aws-iac` MCP server tools sequentially before proposing any deployment command:
1. **Syntax & Schema Validation**: Call `validate_cloudformation_template` (`cfn-lint`) on the authored or `cdk synth`-generated template to verify resource properties, intrinsic functions, and regional schema compatibility.
2. **Proactive Compliance Checking**: Call `check_cloudformation_template_compliance` (`cfn-guard`) to verify compliance against AWS Control Tower proactive controls and Guard rules:
   - Storage and database encryption at rest enabled (`EBS`, `S3`, `RDS/Aurora`, `DynamoDB`, `EFS`, `SNS/SQS`).
   - S3 `PublicAccessBlockConfiguration` all four booleans set to `true` and TLS enforced (`aws:SecureTransport`).
   - Zero unrestricted `0.0.0.0/0` or `::/0` ingress on administrative (`22`, `3389`) or database (`3306`, `5432`, `6379`, `27017`) ports.
   - Explicit `RetentionInDays` configured on every `AWS::Logs::LogGroup`.
3. **Gate Rule**: Do not proceed to deployment until **zero blocking errors or compliance violations** remain.

---

### Step 5: Least-Privilege Identity Verification

Delegate to `aws-iam-least-privilege-governance` and the `iam` MCP server:
- Construct dedicated workload identities: EC2 Instance Profiles (`setting-up-ec2-instance-profiles` with IMDSv2 `HttpTokens: required` and `HttpPutResponseHopLimit: 2`), separate ECS `TaskRoleArn` and `ExecutionRoleArn`, **EKS Pod Identity** (`pods.eks.amazonaws.com`), or scoped Lambda Execution Roles.
- Include `aws:SourceArn` and `aws:SourceAccount` conditions on all cross-service resource policies (S3, SQS, SNS, KMS, EventBridge) to prevent confused-deputy attacks.
- Validate policies using `simulate_principal_policy` on the `iam` MCP server to confirm the workload role can access only its specific S3 buckets, DynamoDB tables, SQS queues, or Secrets Manager ARNs—and is denied wildcard `*` actions.

---

### Step 6: Day-2 Observability, Resilience & Alarm Wiring

Delegate to `aws-observability-and-incident-triage` and call `get_recommended_metric_alarms` on the `cloudwatch` MCP server to bundle baseline operational alarms directly into the IaC stack:
- **Edge & Ingress**: ALB/API Gateway `5XXError` rate (`> 1%`), `TargetResponseTime` (`p95`/`p99`), HealthyHostCount (`< MinTasks`), WAF `BlockedRequests` spike.
- **Compute & Containers**: ECS/EKS CPU & Memory utilization (`> 80%`), ECS Deployment Circuit Breaker failure events, Lambda `Errors`, `Throttles`, and `Duration` (`> 80%` of timeout).
- **Messaging & Async**: SQS `ApproximateNumberOfMessagesVisible` on Dead-Letter Queues (`> 0` — immediate P1/P2 alert) and `ApproximateAgeOfOldestMessage`.
- **Stateful Data**: RDS/Aurora `DatabaseConnections`, `FreeableMemory`, `CPUUtilization`, `ReadLatency`/`WriteLatency`, and ElastiCache `SwapUsage` / `Evictions`.
