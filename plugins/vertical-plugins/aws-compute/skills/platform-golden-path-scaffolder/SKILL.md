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

## Targeted 6-Capability Golden-Path Workflow (Call Only Requested MCP Tools)

> **Turn & Latency Budget Guardrail (Do NOT Over-Call Unrequested MCP Tools)**:
> - **Targeted MCP Invocation Only**: Execute ONLY the MCP tool(s) directly required by the user's prompt so you respond quickly and never time out:
>   - Call `aws-mcp` (`aws___run_script` — 1 combined script) **only** when the prompt asks to inspect live AWS resources (e.g., Service Catalog portfolios or EC2 Image Builder pipelines in the target region).
>   - Call `awspricing` (`get_pricing` — max 2–3 calls) **only** when the prompt asks for cost estimation, pricing tables, or dev vs. prod FinOps comparisons.
>   - Call `awsiac` (`validate_cloudformation_template` and `check_cloudformation_template_compliance`) **only** when the prompt explicitly asks to validate a CloudFormation template with `awsiac` / `cfn-guard`. Do **not** call `awsiac` when the user asks for a Backstage `template.yaml`, a Terraform module, a CDK construct, or an adversarial security/CI-CD review.
>   - Call `cloudwatch` (`get_recommended_metric_alarms` — max 1–2 calls) **only** when the prompt specifically asks for Day-2 CloudWatch alarm recommendations.
> - **Output Directly in Markdown**: Do **not** create temporary files on disk via `write_file`; include all Backstage YAML, Terraform, CDK, or CloudFormation code blocks directly in your final response.

### Step 1: Intent Classification, Service Quota Preflight & Environment Tiering

Classify the workload into one of five canonical AWS Golden Paths and determine the target environment tier (`dev`, `qa`/`staging`, or `prod`):

| Golden Path | Reference Architecture | Primary Skills Orchestrated |
|---|---|---|
| **1. Three-Tier Web/API Service (Containerized or EC2/ALB)** | Route 53 + CloudFront/WAFv2 + Multi-AZ ALB + **ECS Fargate / EKS / EC2 ASG** in Multi-AZ Private Subnets + **Multi-AZ Aurora/RDS** + **Multi-AZ ElastiCache** + Secrets Manager | `aws-containers`, `aws-compute`, `creating-production-vpc-multi-az`, `configuring-vpc-endpoints-for-private-aws-service-access` |
| **2. Serverless API & Event Microservice** | API Gateway (HTTP API v2 or REST API v1) + **AWS Lambda (`arm64` Graviton)** with X-Ray tracing + **DynamoDB (PITR + KMS)** + Step Functions | `aws-serverless`, `aws-messaging-and-streaming`, `aws-stateful-data-and-caching-platform` |
| **3. Asynchronous Queue Worker** | **Amazon SQS** (KMS-encrypted main queue + **Dead-Letter Queue** wired via `RedrivePolicy` `maxReceiveCount: 5`) + ECS/EC2/Lambda Worker + least-privilege IAM Role + DLQ CloudWatch Alarms | `aws-messaging-and-streaming`, `aws-containers`, `aws-compute` |
| **4. Scheduled Batch/Data Job** | EventBridge Scheduler + Step Functions / AWS Batch / ECS Fargate Task / EC2 Spot Fleet + S3 + KMS + CloudWatch failure notifications | `aws-serverless`, `aws-containers`, `aws-compute` |
| **5. Static SPA + Edge API (and Internal Zero-Trust Mesh)** | S3 (Private Bucket + `PublicAccessBlockConfiguration` + KMS) + **CloudFront Origin Access Control (OAC)** + `SecurityHeadersPolicy` + Route 53 + AWS WAFv2 (plus **VPC Lattice** / **ECS Service Connect** for internal service-to-service mesh) | `cloudfront`, `routing-traffic-with-route53-and-cloudfront`, `waf`, `aws-storage` |

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

### Step 2: Pre-Deployment FinOps Cost Estimation (When Cost / Pricing Is Requested)

When the user asks for cost estimation, pricing comparison, or dev vs. prod FinOps tables, query the `awspricing` MCP server (`get_pricing` — 1–3 focused calls) to estimate the monthly run rate of the proposed Golden Path. Present a clear Markdown table showing:
1. **Fixed hourly/monthly baseline costs** (e.g., NAT Gateways `$32.40/mo/AZ`, ALB `$16.20/mo`, EKS Control Plane `$73.00/mo`, VPC Interface Endpoints `$7.20/mo/AZ`, Route 53 Hosted Zone `$0.50/mo`).
2. **Variable / usage-based costs** (e.g., Fargate `arm64` vCPU/GB-hours, Lambda invocations/GB-s, Aurora ACU-hours, DynamoDB RCU/WCU, NAT data processing `$0.045/GB`, CloudWatch Logs ingestion `$0.50/GB`).
3. **Side-by-side Dev/QA vs. Prod monthly cost comparison** with concrete cost-saving alternatives.

---

### Step 3: Declarative IaC Generation (Never ClickOps)

Author the requested infrastructure directly in your Markdown response (do NOT write files to disk unless requested) as **Backstage Software Templates (`scaffolder.backstage.io/v1beta3` `template.yaml`)**, **AWS CDK (TypeScript/Python)**, **AWS CloudFormation YAML/JSON**, **AWS SAM (`template.yaml`)**, or **Terraform (`*.tf`)** matching the user's request:
- **Mandatory Cost & Governance Tagging**: Apply `Environment`, `Owner`, `CostCenter`, `Workload`, and `ManagedBy` tags at the stack/provider/template level so all child resources inherit them.
- **Zero Public Compute / Database Placement**: Never place application compute (EC2, ECS tasks, EKS nodes, Lambda functions) or stateful data stores (RDS, Aurora, ElastiCache, MSK, OpenSearch) in public subnets. Only Internet-facing ALBs, NLBs, and NAT Gateways belong in public subnets.
- **PrivateLink First**: Attach free S3 and DynamoDB Gateway Endpoints (`$0.00`) to every private route table and Interface Endpoints for ECR, CloudWatch Logs, SSM, and Secrets Manager where appropriate.
- **2026 Service Guardrail**: Never provision AWS App Runner (sunset April 30, 2026); use **Amazon ECS Express Mode** or standard ECS Fargate + ALB instead.

---

### Step 4: Static Validation & Security Compliance Gating (When CloudFormation Validation Is Requested)

When authoring a CloudFormation template and asked to validate it via `awsiac`, execute the `awsiac` MCP server tools:
1. **Syntax & Schema Validation**: Call `validate_cloudformation_template` (`cfn-lint`) on the CloudFormation template to verify resource properties, intrinsic functions, and regional schema compatibility.
2. **Proactive Compliance Checking**: Call `check_cloudformation_template_compliance` (`cfn-guard`) to verify compliance against AWS Control Tower proactive controls and Guard rules:
   - Storage and database encryption at rest enabled (`EBS`, `S3`, `RDS/Aurora`, `DynamoDB`, `EFS`, `SNS/SQS`).
   - S3 `PublicAccessBlockConfiguration` all four booleans set to `true` and TLS enforced (`aws:SecureTransport`).
   - Zero unrestricted `0.0.0.0/0` or `::/0` ingress on administrative (`22`, `3389`) or database (`3306`, `5432`, `6379`, `27017`) ports.
   - Explicit `RetentionInDays` configured on every `AWS::Logs::LogGroup`.
3. **Gate Rule**: Do not proceed to deployment until **zero blocking errors or compliance violations** remain. (Skip calling `awsiac` when the user asks for Terraform modules, CDK code, Backstage YAML, or security architecture reviews.)

---

### Step 5: Least-Privilege Identity Verification

Construct dedicated workload identities: EC2 Instance Profiles (`setting-up-ec2-instance-profiles` with IMDSv2 `HttpTokens: required` and `HttpPutResponseHopLimit: 2`), separate ECS `TaskRoleArn` and `ExecutionRoleArn`, **EKS Pod Identity** (`pods.eks.amazonaws.com`), or scoped Lambda Execution Roles:
- Include `aws:SourceArn` and `aws:SourceAccount` conditions on all cross-service resource policies (S3, SQS, SNS, KMS, EventBridge) to prevent confused-deputy attacks.

---

### Step 6: Day-2 Observability, Resilience & Alarm Wiring

When Day-2 observability or CloudWatch alarm guidance is requested, call `get_recommended_metric_alarms` on the `cloudwatch` MCP server (or include the canonical alarm specifications below) to bundle baseline operational alarms directly into the IaC stack:
- **Edge & Ingress**: ALB/API Gateway `5XXError` rate (`> 1%`), `TargetResponseTime` (`p95`/`p99`), HealthyHostCount (`< MinTasks`), WAF `BlockedRequests` spike.
- **Compute & Containers**: ECS/EKS CPU & Memory utilization (`> 80%`), ECS Deployment Circuit Breaker failure events, Lambda `Errors`, `Throttles`, and `Duration` (`> 80%` of timeout).
- **Messaging & Async**: SQS `ApproximateNumberOfMessagesVisible` on Dead-Letter Queues (`> 0` — immediate P1/P2 alert) and `ApproximateAgeOfOldestMessage`.
- **Stateful Data**: RDS/Aurora `DatabaseConnections`, `FreeableMemory`, `CPUUtilization`, `ReadLatency`/`WriteLatency`, and ElastiCache `SwapUsage` / `Evictions`.

## MCP-First Execution, Guardrails & `awsknowledge` Fallback

- **MCP-Only Execution (Zero Raw AWS CLI in Shell)**: When querying live AWS state, Service Quotas, CloudWatch recommended alarms, pricing (`awspricing`), or IaC template compliance (`awsiac` `validate_cloudformation_template` & `check_cloudformation_template_compliance`), always use connected MCP tools (`aws-mcp` `aws___run_script` / `aws___call_aws`, `cloudwatch`, `awspricing`, `awsiac`, `awsknowledge`) in strictly read-only mode. NEVER execute raw `aws`, `cdk`, or `terraform` CLI commands via `run_command` / `Bash`.
- **Platform Golden-Path Standards (Backstage, Service Catalog, OIDC CI/CD & Tagging)**:
  - **Backstage (`scaffolder.backstage.io/v1beta3` `template.yaml`) & AWS Service Catalog**: Enforce required input parameters (`environment`, `owner`, `cost_center`, `workload_name`) and automatically propagate mandatory cost-allocation tags (`Environment`/`env`, `Owner`/`owner`, `CostCenter`/`cost-center`, `Workload`, `ManagedBy`) at the CDK Stack / CloudFormation / Terraform provider level.
  - **Zero Static CI/CD IAM User Keys (Enforce OIDC Federation)**: Strictly reject creating IAM Users (`AWS::IAM::User` / `aws_iam_user`) or long-lived `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` secrets for GitHub Actions or GitLab CI. Always provision an **IAM OIDC Identity Provider** (`https://token.actions.githubusercontent.com` or GitLab URL) and a deployment IAM Role using `sts:AssumeRoleWithWebIdentity` with strict `StringEquals` on `:aud` (`sts.amazonaws.com`) and `StringEquals`/`StringLike` on `:sub` (`repo:<org>/<repo>:environment:production` or `repo:<org>/<repo>:ref:refs/heads/main`).
  - **Refuse Guardrail Bypasses**: Explicitly reject golden-path templates that allow public S3 buckets (`PublicAccessBlockConfiguration` disabled), unencrypted storage/databases, compute/databases in public subnets, or `0.0.0.0/0` SSH/DB ingress; enforce `cfn-guard` (`check_cloudformation_template_compliance`) / OPA policy-as-code gates in CI/CD.
- **Vague Workload Sizing & Cost Guard**: If the user asks to scaffold a golden path template or asks for a monthly AWS bill in dollars without specifying service requirements, refuse to generate a one-size-fits-all template or guess a single monthly dollar figure, ask clarifying questions covering the missing requirements (golden path archetype, IaC/IDP framework Terraform/CDK/CloudFormation/Backstage, dev vs prod tier, and database/storage needs), **and query the `awspricing` MCP server (`get_pricing` for the target region) to show illustrative dev vs prod baseline unit rates and monthly tier ranges** once assumptions are stated.
- **Read-Only & Secret Safety (`aws-mutation-gate.py`, `secret-safety.py`)**: Never run mutating commands (`cdk deploy`, `terraform apply`, `aws cloudformation create-stack`) or fetch plaintext secrets (`aws secretsmanager get-secret-value`); recommend `DescribeSecret` metadata checks and `{{resolve:secretsmanager:...}}`.
- **`awsknowledge` Edge-Case Fallback**: If **no** local section covers the user's specific edge-case question (e.g., AWS Proton migration to Backstage/Service Catalog + CodePipeline, or AWS Service Catalog Launch Constraints and TagOptions), immediately query the connected `awsknowledge` MCP server (`aws___search_documentation` and `aws___read_documentation` — 1–2 focused searches) and answer directly.
