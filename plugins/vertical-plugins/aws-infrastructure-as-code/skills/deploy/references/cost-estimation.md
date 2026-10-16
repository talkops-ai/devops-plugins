# FinOps & Real-Time AWS Cost Estimation Patterns

Use the bound **`awspricing`** MCP server (`get_pricing`, `get_pricing_service_codes`, `get_pricing_service_attributes`, `get_pricing_attribute_values`, `analyze_cdk_project`, `analyze_terraform_project`, `generate_cost_report`) to calculate region-accurate monthly cost estimates **before** generating or executing any mutating deployment.

## 1. Mandatory Cost Estimation Workflow

1. **Scan Existing IaC (When Present):**
   - If the repository contains an AWS CDK project, run `awspricing` -> `analyze_cdk_project` to automatically inventory configured AWS services.
   - If the repository contains Terraform (`.tf`) files, run `awspricing` -> `analyze_terraform_project`.
2. **Query Live Regional Rates:**
   - Call `get_pricing` for the exact target `AWS_REGION` (never quote `us-east-1` prices for a workload deploying to `eu-west-1` or `ap-southeast-1`).
3. **Apply the Standard Monthly Baseline Formula:**
   - **Continuous Hourly Resources (EC2, Fargate, ALB, NAT Gateway, Aurora ACU, DocumentDB DCU, ElastiCache):**
     $$\text{Monthly Cost} = \text{Hourly Unit Rate} \times 730\text{ hours} \times \text{Instance/Unit Count}$$
   - **Consumption & Traffic Tiers (Lambda, API Gateway, DynamoDB, S3, CloudFront, Data Transfer):**
     Explicitly parameterize baseline traffic assumptions (e.g., `1M requests/month`, `50 GB storage`, `100 GB outbound data transfer`) and Peak/Spike sensitivity (`10x traffic burst`).
4. **Enforce the Approval Gate:**
   - Present the structured Markdown cost table below (and optionally persist a detailed report to `./reports/` via `generate_cost_report`) and **WAIT** for explicit user approval before provisioning.

## 2. Required Cost Breakdown Table Format

Always display this table structure to the user prior to deployment:

| Component | AWS Service & Sizing | Unit Rate (`<region>`) | Monthly Baseline (`730h` / Assumed Traffic) | Estimated Peak / Burst |
| --- | --- | --- | --- | --- |
| Compute | ECS Fargate (`0.5 vCPU, 1 GB`, ARM64, 1 task) | `$X.XXXX/vCPU-hr`, `$Y.YYYY/GB-hr` | `$XX.XX` | `$XX.XX` (at 4 tasks) |
| Ingress | Application Load Balancer + LCU | `$0.0225/hr` + LCU | `$18.00` | `$25.00` |
| Networking | NAT Gateway (1 AZ dev) + Data Processed | `$0.045/hr` + `$0.045/GB` | `$35.10` | `$45.00` |
| Database | Aurora PostgreSQL Serverless v2 (`0.5–2 ACU`) | `$0.12/ACU-hr` + `$0.10/GB-mo` | `$45.00` | `$175.00` |
| **Total** | **Environment: Dev (`<region>`)** | — | **`~$XXX.XX / month`** | **`~$XXX.XX / month`** |

## 3. AWS Pricing Service Codes & Key Cost Drivers

| Service | `awspricing` Service Code | Key Filters & Hidden Cost Drivers to Include |
| --- | --- | --- |
| **ECS Fargate** | `AmazonECS` | Filter `usagetype` for `Fargate-vCPU-Hours:perCPU` and `Fargate-GB-Hours` (or `Fargate-ARM-vCPU-Hours` for Graviton2). |
| **NAT Gateway** | `AmazonEC2` | Always include NAT Gateway hourly charge (`~$32.85/mo` per AZ) + per-GB data processing (`$0.045/GB`) when deploying private subnets without VPC endpoints! |
| **ALB** | `AWSELB` | Include fixed hourly rate (`~$16.43/mo`) plus LCU usage. |
| **Aurora Serverless v2** | `AmazonRDS` | Filter `databaseEngine` (`Aurora PostgreSQL` / `Aurora MySQL`) + `ServerlessV2Usage` (`ACU-Hr` * 730 * min ACUs) + storage (`GB-Mo`). |
| **DocumentDB Serverless** | `AmazonDocDB` | DCU-Hours (`0.5 DCU` min * 730) + storage (`GB-Mo`). |
| **AWS Lambda** | `AWSLambda` | Requests (`$0.20 / 1M`) + Duration (`GB-seconds` on `arm64` vs `x86_64`); note 1M requests + 400,000 GB-sec monthly free tier. |
| **API Gateway** | `AmazonApiGateway` | HTTP API (`~$1.00 / 1M requests`) vs. REST API (`~$3.50 / 1M requests`). |
| **DynamoDB** | `AmazonDynamoDB` | On-Demand Read Request Units (RRUs), Write Request Units (WRUs), storage (`$0.25/GB-mo`), and PITR (`$0.20/GB-mo`). |
| **Amplify Hosting** | `AWSAmplify` | Build minutes (`$0.01/min`), SSR compute GB-sec, and CDN storage/bandwidth. |
| **CloudWatch** | `AmazonCloudWatch` | Log ingestion (`$0.50/GB`), storage (`$0.03/GB-mo`), and custom metrics/alarms (`$0.10–$0.30/alarm`). |
| **Secrets Manager** | `AWSSecretsManager` | `$0.40 / secret / month` + `$0.05 / 10,000 API calls`. |
| **Elastic Beanstalk** | `AmazonEC2` + `AWSELB` | EB has no service fee; price the EC2 instances (`t3.small` / `t3.medium`), gp3 EBS volumes (`8 GB` per instance), and ALB. |

## 4. FinOps Optimization Levers to Recommend

- **Graviton (`arm64`) First:** Recommend `ARM64` on ECS Fargate, Lambda, and RDS/ElastiCache for up to 20–25% better price-performance.
- **Avoid Duplicate NAT Gateways in Dev:** Reuse brownfield VPCs discovered by `preflight-discovery` or add a free **S3/DynamoDB Gateway VPC Endpoint** so private subnet traffic to S3/DynamoDB bypasses per-GB NAT Gateway charges.
- **HTTP API over REST API:** Default to API Gateway HTTP API v2 unless REST API v1 features (WAF, Usage Plans, Private APIs) are required.
