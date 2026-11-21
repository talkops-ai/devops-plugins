---
name: aws-finops-and-cost-optimization
description: >-
  Generates pre-deployment AWS unit price and monthly run-rate estimates via the
  awspricing/pricing MCP server, audits existing account spend, idle resources,
  and commitments via the billing/billing-cost MCP server (Cost Explorer, Cost
  Optimization Hub, Compute Optimizer, Savings Plans, RIs, Budgets) and
  cloudwatch MCP, right-sizes compute/networking/storage tiers with Two-Key
  P95/P99 telemetry verification, and enforces mandatory cost-allocation tags.
metadata:
  version: "2.1"
---

# AWS FinOps and Platform Cost Optimization

## Purpose

Prevent surprise cloud bills and architectural cost leaks across non-production and production AWS environments. Application developers and platform engineers rarely anticipate compounding AWS cost mechanics—such as `$32.85/mo/AZ + $0.045/GB` per NAT Gateway (`730 hrs`), `$73.00/mo` (`$0.10/hr`) per EKS cluster control plane (`$438.00/mo` / `$0.60/hr` on Extended Support), Cross-AZ data transfer (`$0.02/GB` round-trip), or `t3`/`t4g` `unlimited` CPU credit surplus charges (`$0.05/vCPU-hr`). This skill enforces **Shift-Left Platform FinOps** (pre-deployment cost modeling via `awspricing` / `pricing` MCP) and **Day-2 Platform FinOps** (idle resource elimination, right-sizing, and commitment auditing via `billing` / `billing-cost`, `cloudwatch`, and `aws-mcp`).

---

## Non-Negotiable Platform FinOps Rules

1. **MCP-First Hygiene (Zero Raw `aws` CLI in `Bash`):**
   - Always execute live AWS pricing, billing, telemetry, IaC validation, and resource discovery calls via connected MCP servers (`awspricing` / `pricing`, `billing` / `billing-cost`, `cloudwatch`, `awsiac` / `aws-iac`, `aws-mcp` `aws___call_aws`, and `awsknowledge`) rather than running raw `aws ...` CLI commands in `Bash`.
   - Use `Bash` only for deterministic Python math (`python3 -c "..."`) or local tools (`infracost`).
2. **Current Date Check, Deterministic Math & Empty-Account Honesty:**
   - Check the current system date before making Cost Explorer, Budgets, or Anomaly calls (Cost Explorer `End` dates are **exclusive**).
   - Never perform mental math—compute all hourly-to-monthly (`* 730`), GB-month, break-even, and delta calculations via `python3 -c "..."` or `session-sql`.
   - If live discovery in the target region and `us-east-1` shows `0` EC2/EBS/NAT/EIP resources, `0` budgets, or `Inactive` Compute Optimizer / Cost Optimization Hub enrollment, report those exact live facts honestly without inventing resource IDs or savings numbers.
3. **Vague Workload & Cost Guard:**
   - If a user asks for a monthly AWS cost estimate, right-sizing target, or Savings Plan commitment without providing concrete workload sizing metrics (instance types/counts, vCPU/RAM, storage GiB, IOPS, request rate, data transfer GB) and live account discovery shows no matching workload, **refuse to guess or fabricate a single dollar figure** and list the exact clarifying sizing inputs required.
4. **Two-Key Right-Sizing Validation & Integer Coercion:**
   - Never downsize or terminate production compute/database/storage capacity using billing or Compute Optimizer metadata alone. Cross-check 14–30 day **P95, P99, and Maximum** utilization in `cloudwatch:get_metric_data` and active alarms in `cloudwatch:get_active_alarms`.
   - If OS memory telemetry (`CWAgent` `mem_used_percent` on EC2) is missing, explicitly state `Memory Telemetry: Unverified (CWAgent not installed)` and **refuse** downsizing recommendations that reduce total GiB of RAM.
   - Pass `max_items`, `limit`, `max_results`, and `period` as **native JSON integers** (`50`, `3600`), never strings.
5. **Security, Read-Only Mutation & FinOps SQL Gates:**
   - **Read-Only AWS Mutation Gate (`hooks/aws-mutation-gate.py`):** Never execute mutating AWS commands (`ec2 delete-volume`, `ec2 release-address`, `ec2 terminate-instances`, `rds modify-db-instance`, `budgets create-budget`, `budgets delete-budget`, `terraform apply`, `cdk deploy`). Output validated CLI/CloudFormation/Terraform remediation plans for user approval.
   - **Secret Safety Gate (`hooks/secret-safety.py`):** Never call `secretsmanager:GetSecretValue` or `kms:Decrypt` to fetch plaintext secrets. Use `secretsmanager:DescribeSecret` for metadata/cost audits ($0.40/secret/month) and `{{resolve:secretsmanager:...}}` in IaC.
   - **FinOps SQL & Cost Gate (`hooks/finops-sql-and-cost-gate.py`):** Never execute `SELECT *`, unpartitioned queries, or destructive SQL (`DROP`, `DELETE`, `ALTER`, `CREATE`) on Amazon Athena or Storage Lens.
6. **`awsknowledge` MCP Fallback:**
   - If **no** local section matches the user's specialized AWS billing/platform cost question, immediately query the `awsknowledge` MCP server (`aws___search_documentation` / `aws___read_documentation` — 1–2 focused searches) and answer directly.

---

## Mandatory Platform FinOps Workflow

### 1. Pre-Deployment Unit Price & Monthly Run-Rate Estimation (`awspricing` / `pricing` MCP)

Before provisioning any new environment, cluster, database, or network stack, query `awspricing:get_pricing` (and `get_bedrock_patterns` for GenAI stacks) for the target region (e.g., `us-east-1`, `us-west-2`, `eu-west-1`) and present a structured Markdown cost table using `730 hours/month`:

| Cost Component | Baseline Unit Price Mechanics (`us-east-1` reference; always verify regional SKU price via `awspricing:get_pricing`) | Dev / QA / Prod Cost-Optimization Lever |
|---|---|---|
| **Amazon EKS Control Plane** | `$0.10/hr` (`$73.00/mo` at 730 hrs) on Standard Support; **`$0.60/hr` (`$438.00/mo` — 6x penalty)** on Extended Support for deprecated Kubernetes versions | Upgrade clusters to standard-support Kubernetes versions (`$365.00/mo` saved per cluster); consolidate ephemeral Dev/QA clusters into a shared multi-namespace cluster with `ResourceQuota` + `LimitRange` + `NetworkPolicy`, or use **ECS Fargate** (`$0.00` control-plane fee). |
| **VPC NAT Gateway & Public IPv4** | `~$0.045/hr` (`$32.85/mo/AZ` at 730 hrs) + `$0.045/GB` data processed (`$98.55/mo` fixed base for 3 AZs before traffic) + `$0.005/hr` (`$3.65/mo`) per Public IPv4 | Attach **free S3 & DynamoDB Gateway Endpoints (`$0.00`)** to every private route table; provision Interface Endpoints (`$7.30/mo/AZ` + `$0.01/GB`) when monthly ECR/Logs/Secrets traffic exceeds **~209 GB/mo per AZ** (`$7.30 / ($0.045 - $0.01)`); use Dual-Stack **IPv6 Egress-Only Internet Gateway (`$0.00`)**; use 1 NAT Gateway in `dev`/`qa`. |
| **EC2 / EKS Nodes / ECS Fargate** | On-Demand x86 (`amd64`) vs. Graviton (`arm64`) vs. Spot | Default to **AWS Graviton3/4 (`arm64`)** (`t4g`, `m7g`, `c7g`, `r7g`, or Fargate `ARM64`) for **20% lower cost and up to 40% better price-performance**; use **Fargate Spot** or **Karpenter Spot consolidation** (`consolidationPolicy: WhenEmptyOrUnderutilized`) for up to 70% savings on stateless workloads. |
| **Aurora / RDS Databases** | Provisioned instance hours + storage (`$0.10/GB-mo`) + I/O (Standard) vs. I/O-Optimized (+30% compute, +125% storage, `$0.00` I/O) | Use Single-AZ in `dev`/`qa` (`Multi-AZ` doubles cost `2x`) or **Aurora Serverless v2** (`MinCapacity: 0` auto-pause or `0.5` ACU); for `prod` workloads where I/O charges exceed **25% of total database spend**, switch to **Aurora I/O-Optimized** (`aurora-iopt1`). |
| **Amazon EBS Volumes** | `gp2` (`$0.10/GB-mo`, 3 IOPS/GB tied to size) vs. `gp3` (`$0.08/GB-mo`, 3,000 IOPS + 125 MB/s free baseline) | Always provision **`gp3`** (20% cheaper per GB than `gp2`); for `gp2` volumes >1,000 GiB (e.g., 2 TB = 6,000 IOPS), explicitly provision matching `iops` on `gp3` if P95 IOPS exceeds 3,000; delete unattached `available` volumes and archive stale snapshots (`>90d`). |
| **CloudWatch Logs & Custom Metrics** | Standard Logs ingestion (`$0.50/GB`) + storage (`$0.03/GB-mo`); Custom Metrics (`$0.30/metric/mo` first 10k) | Use **CloudWatch Logs Infrequent Access (`INFREQUENT_ACCESS` at `$0.25/GB` — 50% cheaper)** for verbose VPC Flow Logs, WAF logs, and container stdout; set explicit `RetentionInDays` (`7`–`14` non-prod, `30`–`90` prod); drop high-cardinality labels (`request_id`, `pod_uid`, `user_id`) from custom metrics. |

---

### 2. High-Impact Platform Cost Traps to Block Proactively

1. **T3 / T3a / T4g `unlimited` CPU Credit Surplus Leak (`$0.05/vCPU-hr`)**:
   - Burstable instances launch in `unlimited` mode by default. If a misconfigured container, noisy neighbor, or background cron job pegs CPU above the baseline (20%–40%), AWS bills **`$0.05/vCPU-hour`** for Linux (`$0.096/vCPU-hr` for Windows) in `CPUSurplusCreditsCharged`—making a sustained `t3.medium` or `t3.xlarge` cost **more than a fixed-performance `m7g.large` / `m7i.xlarge`**.
   - **Fix**: Check `CPUCreditBalance` and `CPUSurplusCreditsCharged` in `cloudwatch:get_metric_data`. Set `CreditSpecification: { CpuCredits: standard }` for non-prod sandboxes, or migrate sustained CPU workloads (`p95 CPU > baseline`) to `m7g`/`c7g` fixed-performance instances.
2. **Cross-AZ Data Transfer Bleed (`$0.02/GB` Round-Trip — `Regional-Bytes`)**:
   - Chatty microservices, Kafka/MSK brokers, or ElastiCache/Aurora clusters communicating across Availability Zones incur `$0.01/GB` egress + `$0.01/GB` ingress (`$0.02/GB` total round-trip).
   - **Fix**: Enable **ALB Target Group AZ Affinity / Traffic Distribution**, Kubernetes **Topology Aware Routing** (`service.kubernetes.io/topology-mode: Auto`), and read-from-local-AZ replica policies on ElastiCache and Aurora.
3. **ECR Container Image Pulls Through NAT Gateway**:
   - Pulling a 2 GB container image across 50 ECS/EKS tasks without VPC endpoints sends 100 GB through NAT Gateway (`100 GB * $0.045/GB = $4.50` per rollout, or `$675/mo` across 5 rollouts/day).
   - **Fix**: Provision `com.amazonaws.<region>.ecr.api` and `com.amazonaws.<region>.ecr.dkr` Interface Endpoints (`$7.30/mo/AZ` each) **plus** the free `com.amazonaws.<region>.s3` Gateway Endpoint (`$0.00`, because ECR stores actual container image layers in S3!).

---

### 3. Live Account Spend, Idle Resource & Commitment Auditing (`billing` / `billing-cost`, `cloudwatch` & `aws-mcp`)

When auditing or optimizing a live AWS account (including `/aws-cost-optimization:waste-hunt-audit` and `/aws-cost-optimization:rightsize-commitment`), orchestrate these exact MCP calls:
1. **Billing Views & Cost Explorer Baseline**:
   - Call `list-billing-views` on `billing` MCP to check for `PRIMARY` or custom Billing Views.
   - Call `cost-explorer` (`operation="getCostAndUsage"`, `granularity="MONTHLY"`, `metrics='["AmortizedCost", "UnblendedCost", "UsageQuantity"]'`, `group_by='[{"Type":"DIMENSION","Key":"SERVICE"}]'`) and `cost-comparison` (`operation="getCostAndUsageComparisons"` / `"getCostComparisonDrivers"`).
2. **Deduplicated Optimization & Idle Resource Sweep**:
   - Call `cost-optimization` (`operation="list_recommendation_summaries"` and `"list_recommendations"`) for deduplicated Cost Optimization Hub opportunities.
   - Call `compute-optimizer` (`operation="get_enrollment_status"`, `"get_ec2_instance_recommendations"`, `"get_ebs_volume_recommendations"`, `"get_rds_database_recommendations"`, `"get_lambda_function_recommendations"`, `"get_ecs_service_recommendations"`) or top-level `get_eks_Optimization_recommendations`.
   - Call `aws-mcp` (`aws___call_aws`) in the target region to inspect live unattached EBS volumes (`aws ec2 describe-volumes --filters Name=status,Values=available`), unassociated Elastic IPs (`aws ec2 describe-addresses`), NAT Gateways (`aws ec2 describe-nat-gateways`), VPC Endpoints (`aws ec2 describe-vpc-endpoints`), and Log Groups missing `retentionInDays` (`aws logs describe-log-groups`).
   - **Two-Key Verification**: Cross-check 14–30 day **P95/P99/Maximum** utilization in `cloudwatch:get_metric_data` and active alarms in `cloudwatch:get_active_alarms` before recommending any downsizing.
3. **Savings Plans, RIs & Budgets Governance**:
   - Call `sp-performance` (`operation="get_savings_plans_coverage"` and `"get_savings_plans_utilization"`), `ri-performance` (`operation="get_reservation_coverage"` and `"get_reservation_utilization"`), `budgets` (pass `{}` or `max_items=20` directly — no `operation` parameter), and `free-tier-usage` (no `operation` parameter).
   - Sequence **Physical Right-Sizing & Idle Elimination BEFORE Rate Commitments** (`adjusted_uncovered_hourly_spend = current_uncovered_hourly_spend - (monthly_physical_savings / 730.0)`).

---

### 4. Mandatory Cost-Allocation Tagging Governance

Every CloudFormation stack, CDK app, SAM template, and Terraform module authored or remediated by this skill **must** apply these five standard tags at the root stack/provider level (`default_tags` in Terraform):
- `Environment`: `dev` | `qa` | `staging` | `prod`
- `Owner`: team or service owner identifier
- `CostCenter`: billing unit or project code
- `Workload`: application or microservice name
- `ManagedBy`: `aws-platform-engineer-agent` (or `terraform` / `cloudformation`)
