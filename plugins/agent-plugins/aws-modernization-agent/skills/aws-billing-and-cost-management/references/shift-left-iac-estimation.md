# Shift-Left IaC Cost Estimation & Remediation Validation (`infracost`, `awspricing`, `bcm-pricing-calc`, `awsiac`)

Use this reference whenever estimating the monthly cost of a Terraform/OpenTofu module, AWS CDK app, CloudFormation template, or pull request diff **before deployment**, or when authoring and validating IaC remediation patches for FinOps findings.

---

## 1. Multi-Engine Shift-Left Estimation Workflow

Select the estimation engine based on the IaC artifacts in the workspace:

### Engine A: Infracost CLI (Preferred for Terraform / OpenTofu Directories & PR Diffs)
1. Check if `infracost` is installed locally via `Bash`:
   ```bash
   command -v infracost
   ```
2. Run `infracost breakdown` or `infracost diff` with `--llm` (compresses verbose JSON output by ~84% while keeping all SKU rates and resource totals):
   ```bash
   # Baseline cost breakdown of a Terraform directory
   infracost breakdown --path <dir> --format json --llm

   # Include usage-based resources (Lambda, S3 GB, NAT Gateway GB, DynamoDB, Bedrock)
   infracost breakdown --path <dir> --usage-file infracost-usage.yml --format json --llm
   ```
3. Parse the JSON output deterministically via Python (`python3 -c`) or `jq` to extract `totalMonthlyCost`, `totalHourlyCost`, `diffTotalMonthlyCost`, and per-resource breakdowns. Never sum SKU line items mentally.

### Engine B: `awspricing` Project Scanners & Multi-Region Price List API (Preferred for AWS CDK, CloudFormation, or When Infracost Is Not Installed)
1. **Scan the IaC Project Automatically:**
   - For AWS CDK projects: call `awspricing:analyze_cdk_project` (`project_path="<absolute_path>"`).
   - For Terraform projects: call `awspricing:analyze_terraform_project` (`project_path="<absolute_path>"`).
   - For Bedrock / GenAI architectures: call `awspricing:get_bedrock_patterns` to retrieve reference architecture patterns and OpenSearch Serverless minimum OCU floors.
2. **Query Exact Regional SKU Rates (`awspricing:get_pricing`):**
   - Discover service codes and attributes (`get_pricing_service_codes`, `get_pricing_service_attributes`, `get_pricing_attribute_values`).
   - Call `awspricing:get_pricing` with:
     - `region`: single string (`"us-east-1"`) or multi-region array (`["us-east-1", "us-west-2", "eu-west-1"]`) for side-by-side regional cost comparison.
     - `filters`: supports `EQUALS`, `ANY_OF`, `CONTAINS`, and `NONE_OF` match types.
     - `output_options={"pricing_terms": ["OnDemand", "Reserved"]}` and `exclude_free_products=True` (~80% payload reduction).
3. **Generate Structured Cost Report (`awspricing:generate_cost_report`):**
   - Pass the pricing data, assumptions, and resource quantities to `awspricing:generate_cost_report` to produce a Markdown or CSV cost estimate report.

### Engine C: AWS Billing & Cost Management Pricing Calculator (`billing:bcm-pricing-calc`)
When modeling how a new workload interacts with existing Enterprise Discount Program (EDP) discounts and Savings Plans/RIs:
1. Call `billing:bcm-pricing-calc` (`list_workload_estimates`, `get_workload_estimate`, `list_workload_estimate_usage`).
2. Call `list_bill_estimates`, `get_bill_estimate`, `list_bill_estimate_line_items`, and `list_bill_estimate_commitments` to inspect full-bill projections net of commitments.

---

## 2. The 8-Point Architectural Cost Multiplier Checklist

Static IaC scanners often show `$0.00/mo` for usage-based resources or miss multi-AZ multiplication loops. Always inspect `.tf`, `.ts`, `.py`, and `.yaml` templates for these **8 High-Impact Cost Multipliers**:

| Cost Multiplier Pattern | IaC Resource / Property | Hidden Financial Impact | Shift-Left FinOps Fix |
|---|---|---|---|
| **1. Per-AZ NAT Gateways in Non-Prod** | `aws_nat_gateway` with `count = length(var.azs)` or CDK `Vpc(maxAzs=3, natGateways=3)` | `$32.85/mo × 3 = $98.55/mo` fixed hourly cost **per environment** + `$0.045/GB` data processing + `$3.65/mo × 3` EIP fees. | Set `natGateways: 1` in `dev`/`staging`/`sandbox` VPCs, and attach free S3 & DynamoDB Gateway Endpoints by default. |
| **2. Bedrock Knowledge Base with Default AOSS** | `AWS::OpenSearchServerless::Collection` (`type: VECTORSEARCH`) | Minimum **2 OCUs** (4 OCUs with standby replicas) = **$350.40 to $700.80/month fixed floor** even at 0 queries. | Switch dev/test and moderate-scale RAG to **S3 Vectors** or **Aurora PostgreSQL Serverless v2 (`pgvector`)** with `MinCapacity: 0` or `0.5 ACU` (~$43.80/mo). |
| **3. Default `gp2` EBS Volumes** | `aws_instance`, `aws_ebs_volume`, `aws_eks_node_group`, or Launch Templates omitting `volume_type = "gp3"` | Defaults to `gp2` ($0.10/GB-mo) instead of `gp3` ($0.08/GB-mo + free 3,000 IOPS / 125 MB/s). | Explicitly set `volume_type = "gp3"` across all EC2, EKS node group, and Launch Template definitions (instant 20% storage savings). |
| **4. Multi-AZ & High-Retention RDS in Non-Prod** | `aws_db_instance` with `multi_az = true` and `backup_retention_period = 35` in `dev`/`qa` | **Doubles (2x)** database compute and provisioned storage cost in non-production. | Parameterize `multi_az = var.environment == "prod"` and set `backup_retention_period = 7` in non-prod. |
| **5. Unbounded S3 Buckets (No Lifecycle / Bucket Key)** | `aws_s3_bucket` / `AWS::S3::Bucket` without lifecycle configuration or `BucketKeyEnabled` | Orphaned multipart uploads and noncurrent versions accumulate forever; KMS-encrypted buckets without `bucket_key_enabled = true` pay 100x KMS API fees. | Require `AbortIncompleteMultipartUpload` (7 days), `bucket_key_enabled = true` (for SSE-KMS), and Intelligent-Tiering or Glacier lifecycle transitions. |
| **6. Uncapped CloudWatch Log Groups** | `aws_cloudwatch_log_group` omitting `retention_in_days` and `log_group_class` | Defaults to **`Never Expire`** ($0.03/GB-mo forever) and `STANDARD` ($0.50/GB ingestion). | Set explicit `retention_in_days` (14–90 days) and use `log_group_class = "INFREQUENT_ACCESS"` ($0.25/GB — 50% savings) for verbose/debug logs. |
| **7. `x86_64` Compute Instead of Graviton (`arm64`)** | `aws_lambda_function` (`architectures = ["x86_64"]`), RDS `db.m6i`/`db.r6i`, ECS Fargate `X86_64`, EC2 `m6i`/`c6i` | Overpays **~20%** on compute hourly and GB-second rates compared to AWS Graviton (`arm64` / `g` families). | Default to `architectures = ["arm64"]` on Lambda/Fargate and `m7g`/`c7g`/`r7g` on EC2/RDS/ElastiCache unless an x86-only binary dependency exists. |
| **8. Public IPv4 Proliferation** | `map_public_ip_on_launch = true` on subnets or public RDS/ECS tasks | Every public IPv4 address (in-use or idle) bills **$0.005/hr ($3.65/month)**. A 200-node cluster in a public subnet adds **$730/month** in IPv4 fees. | Set `map_public_ip_on_launch = false`, run compute in private subnets, and use IPv6 (`dualstack`) where public addressability is required. |

---

## 3. Validating Generated Remediation IaC (`awsiac`)

When authoring a CloudFormation remediation template (such as an AWS Budget with `FORECASTED` alerts, an S3 Lifecycle rule, VPC Gateway Endpoints, or `gp3` volume updates), validate it before presenting or handing off to `aws-iac-engineer` / `aws-deployment-engineer`:
1. Call `awsiac:validate_cloudformation_template` (`cfn-lint` syntax and schema check).
2. Call `awsiac:check_cloudformation_template_compliance` (`cfn-guard` security & compliance check).
3. Present the validated template/diff alongside the **Monthly Cost Delta (`-$X,XXX.XX/mo`)**.
