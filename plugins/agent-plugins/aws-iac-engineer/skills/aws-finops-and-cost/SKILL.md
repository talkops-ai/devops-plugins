---
name: aws-finops-and-cost
description: Computes pre-deployment AWS infrastructure cost estimates, monthly cost breakdowns, and architecture cost optimizations across Terraform, Terragrunt, CloudFormation, CDK, Pulumi, and Crossplane using Infracost, AWS Price List API (aws-mcp), and shift-left FinOps guardrails.
---

# Shift-Left AWS FinOps & Pre-Deployment Cost Estimation

Use this skill before deploying new infrastructure or major architectural changes, or whenever the user asks "how much will this stack/module cost?" or wants to optimize AWS spend in IaC.

## 1. Pre-Deployment Cost Estimation Matrix

Select the most accurate cost estimation path available in the workspace (adapted from `infracost/agent-skills` and [`references/shift-left-iac-estimation.md`](references/shift-left-iac-estimation.md)):

| Priority | Method | Supported IaC Engines | How to Execute |
|---|---|---|---|
| **1 (Preferred for TF/TG)** | **Infracost CLI** | Terraform, OpenTofu, Terragrunt, CloudFormation | Run `infracost breakdown --path . --format table` for baseline monthly cost, or `infracost diff --path .` against the base branch. |
| **2 (Live AWS Pricing)** | **AWS Price List API (`aws-mcp`)** | CDK, CloudFormation, Pulumi, Crossplane, Terraform | Query `aws pricing get-products --service-code <ServiceCode> --region us-east-1` via `aws-mcp` (`aws___call_aws`) using exact instance families, storage GB-months, and data-transfer assumptions (see [`references/pricing-lookup.md`](references/pricing-lookup.md)). |
| **3 (Synthesized Plan)** | **CDK / Pulumi / CFN Synthesis + Pricing Table** | AWS CDK (`cdk.out/*.template.json`), Pulumi (`pulumi preview --json`), Crossplane (`crossplane render`) | Extract all billable resources from the synthesized output and compute deterministic monthly fixed + usage-based costs (see [`references/deterministic-calculations.md`](references/deterministic-calculations.md)). |

## 2. High-Impact IaC Cost Traps to Flag Automatically

Whenever reviewing or authoring IaC, proactively audit and call out these six recurring AWS cost traps before deployment:

1. **Multi-AZ NAT Gateways & Data Processing ($32.85/mo fixed per AZ + $0.045/GB)**:
   - Always attach free **S3 and DynamoDB Gateway VPC Endpoints** to private route tables so S3/DynamoDB traffic bypasses NAT Gateways.
   - For `dev`/`staging` environments, parameterize NAT Gateway count (`single_nat_gateway = true` in non-prod vs. `one_nat_gateway_per_az = true` in prod).
2. **Legacy EBS & RDS Storage Tiers (`gp2` / `io1` vs. `gp3`)**:
   - Always default EBS volumes and RDS storage to **`gp3`** (20% lower base cost per GB-month than `gp2`, with 3,000 IOPS and 125 MB/s included free). See [`references/ebs-optimization.md`](references/ebs-optimization.md).
3. **Graviton (`arm64`) vs. `x86_64` Compute**:
   - Recommend Graviton3/Graviton4 (`m7g`/`c7g`/`r7g`, RDS `db.r7g`/`db.t4g`, ElastiCache `r7g`, Lambda `arm64`, Fargate `ARM64`) for up to 20–40% better price-performance unless x86-specific binaries are required. See [`references/ec2-rightsizing.md`](references/ec2-rightsizing.md) and [`references/rds-optimization.md`](references/rds-optimization.md).
4. **Unbounded CloudWatch Logs & S3 Storage**:
   - Never create `AWS::Logs::LogGroup` / `aws_cloudwatch_log_group` without an explicit `retention_in_days` (e.g., `14`, `30`, or `90` days) — infinite log retention silently compounds at $0.03/GB-month indefinitely.
   - Attach S3 Intelligent-Tiering or lifecycle transitions (`STANDARD_IA` / `GLACIER_IR`) and `AbortIncompleteMultipartUpload` (7 days) on high-volume buckets.
5. **Idle Interface VPC Endpoints ($7.30/mo per AZ per Endpoint)**:
   - Interface Endpoints across 3 AZs cost ~$21.90/mo each before data processing. Provision Interface Endpoints selectively for high-traffic services (`ecr.dkr`, `logs`, `sts`, `secretsmanager`) or air-gapped subnets.
6. **Provisioned vs. On-Demand Database Capacity**:
   - Default spiky or new workloads to DynamoDB `PAY_PER_REQUEST` (with optional max throughput caps) and Aurora Serverless v2 (`MinCapacity: 0.5` ACU in dev/test) until baseline traffic justifies provisioned capacity.

## 3. Standard Cost Breakdown Output Format

When presenting a pre-deployment cost estimate alongside a change set or plan, summarize:
- **Fixed Monthly Baseline (730 hours/month)**: Compute instances/tasks, RDS instances, NAT Gateways, Load Balancers, Interface VPC Endpoints, KMS keys ($1.00/key/month).
- **Variable / Usage-Driven Drivers**: Data transfer out/NAT processing ($/GB), CloudWatch log ingestion ($0.50/GB), Lambda requests/GB-seconds, DynamoDB RCU/WCU or on-demand requests.
- **Cost Delta (`+` / `-` $/month)** when modifying an existing stack.

## 4. Bundled Reference Guides

- **[`references/shift-left-iac-estimation.md`](references/shift-left-iac-estimation.md)**: Pre-deployment IaC cost estimation methodology across CloudFormation, CDK, and Terraform.
- **[`references/pricing-lookup.md`](references/pricing-lookup.md)**: Querying the AWS Price List API (`aws pricing get-products`) with exact service codes and attribute filters.
- **[`references/deterministic-calculations.md`](references/deterministic-calculations.md)**: Exact formulas for monthly hours (`730`), storage GB-months, and IOPS billing.
- **[`references/ec2-rightsizing.md`](references/ec2-rightsizing.md)**, **[`references/rds-optimization.md`](references/rds-optimization.md)**, **[`references/ebs-optimization.md`](references/ebs-optimization.md)**: Compute, database, and storage cost optimization rules.
