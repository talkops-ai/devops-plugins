---
name: aws-billing-and-cost-management
description: >-
  Principal AWS FinOps and Cloud Financial Management (CFM) skill across the
  FinOps lifecycle (Inform, Optimize, Operate, Shift-Left): analyze AWS spend,
  run 7-stage cost audits, isolate MoM variance drivers with Cost Comparison,
  triage Cost Anomalies, deduplicate savings in Cost Optimization Hub, validate
  Compute Optimizer right-sizing (EC2, ASG, EBS, RDS/Aurora, Lambda, ECS/EKS)
  with Two-Key CloudWatch P95/P99 telemetry and Compute Optimizer Automation,
  query CUR 2.0 and FOCUS 1.0/1.2+ with Athena SQL, engineer Savings Plans and
  Reserved Instance portfolios (Effective Savings Rate, Purchase Analyzer),
  optimize NAT Gateway/Cross-AZ data transfer and S3 Storage Lens lifecycles,
  optimize Bedrock/SageMaker, containers, and database unit economics, estimate
  Shift-Left IaC costs (Infracost, CDK/Terraform pricing, BCM Pricing
  Calculator, cfn-lint/cfn-guard), and govern multi-account billing (Billing
  Views, Billing Conductor, Cost Categories, Budgets, Credits, Support,
  Invoicing, Free Tier).
metadata:
  version: "2.1"
---

# AWS Billing, Cost Management, and FinOps Engineering

Analyze, optimize, govern, and forecast AWS cloud spend across the FinOps Foundation lifecycle (**Inform**, **Optimize**, **Operate**, and **Shift-Left**).

## Usage

Use this skill when:
- Analyzing AWS spend, Month-over-Month variance drivers (`cost-comparison`), cost forecasts (`cost-explorer`), or cost anomalies (`cost-anomaly`)
- Running 7-stage FinOps audits and producing deduplicated Decision Packets (`cost-optimization`)
- Right-sizing EC2, ASGs, EBS, RDS/Aurora, Lambda, or ECS/EKS with Two-Key CloudWatch P95/P99 validation (`compute-optimizer`, `cloudwatch`)
- Engineering Savings Plans and Reserved Instance portfolios, calculating Effective Savings Rate (ESR), or running commitment simulations (`sp-performance`, `ri-performance`)
- Querying granular resource-level billing data in CUR 2.0 or FOCUS 1.0/1.2+ via Athena (`list-bcm-data-exports`, `cur-*`, `athena`)
- Optimizing network data transfer (`NatGateway-Bytes`, `Regional-Bytes`, egress), S3 Storage Lens lifecycles (`cur-storage-lens`), Bedrock/SageMaker, EKS/Karpenter, Aurora Standard vs. I/O-Optimized, DynamoDB, and CloudWatch Logs
- Estimating Shift-Left IaC costs for Terraform, CDK, or CloudFormation (`awspricing`, `awsiac`) and governing Billing Views (`list-billing-views`), Billing Conductor (`list-billing-groups`), Cost Categories (`list-cost-category-definitions`), Budgets (`budgets`), Credits, Support, Invoicing, and Free Tier (`free-tier-usage`)

---

## Non-Negotiable FinOps Execution Rules

### 1. MCP-First Execution & Current Date Check (Zero Raw `aws` CLI in `Bash`)
- **MCP-First Hygiene & Turn Efficiency:** Always execute live AWS billing, pricing, telemetry, IaC validation, and resource discovery calls using connected MCP servers (`billing`, `awspricing`, `cloudwatch`, `awsiac`, `aws-mcp` `aws___call_aws`, and `awsknowledge`) rather than running raw `aws ...` CLI commands in `Bash`. Any CLI examples in `references/*.md` are reference syntax to be executed via the corresponding MCP tool or `aws___call_aws`. Skip live `awspricing` / `billing` API calls when the prompt already provides explicit dollar/unit figures or submits an adversarial mutation/secret/SQL request, and consolidate Python calculations into a single `python3 -c` call.
- **Current Date Check:** Before making ANY Cost Explorer, Budgets, Anomaly, or Savings Plans API call, determine the current date from system metadata. Note that Cost Explorer `End` dates are **exclusive** (`Start=2026-10-01,End=2026-11-01` covers Oct 1–31).
- **Empty / Zero-Resource Account Honesty:** When live queries against the target region and `us-east-1` return `0` anomalies, `0` budgets, `0` exports, `Inactive` Compute Optimizer / Cost Optimization Hub enrollment, or `0` EC2/EBS/NAT resources, report those exact live facts honestly without fabricating resource IDs, anomalies, or spend figures.

### 2. Zero-Hallucination Deterministic Calculations & Vague Workload Guard
- **NEVER perform numerical calculations (sums, averages, percentages, MoM deltas, break-even thresholds, ESR, WACC yield, or invoice totals) mentally.**
  - **Local SQLite Session Engine (`billing:session-sql`):** Query spilled `session.db` tables with `SUM()`, `AVG()`, `ROUND()`, and `GROUP BY` at **$0.00 AWS cost**.
  - **Python Calculator (`Bash`):** For break-even formulas, ESR, WACC yield math, or multi-step ratios, run a Python one-liner (`python3 -c "..."`) and cite the exact computed output. See [`references/deterministic-calculations.md`](./references/deterministic-calculations.md).
- **Vague Workload & Cost Guard:** If a user asks for an exact monthly AWS bill, right-sizing target, or Savings Plan commitment without providing concrete workload sizing metrics (instance types/counts, vCPU/RAM, storage GiB, IOPS, request rate, or data transfer GB) and live account discovery shows no matching workload, **refuse to fabricate or guess dollar totals** and list the exact clarifying inputs and CloudWatch/Cost Explorer metrics required.

### 3. The Two-Key Right-Sizing Validation Rule (Financial + Telemetry)
Never recommend downsizing or terminating production compute, database, or storage capacity using billing or Compute Optimizer metadata alone:
- **Key 1 (Financial Opportunity):** Pull deduplicated recommendations from `billing:cost-optimization` (`list_recommendations`) and technical options from `billing:compute-optimizer`.
- **Key 2 (CloudWatch Telemetry Proof):** Verify **14–30 day `p95`, `p99`, and `Maximum` utilization** via `cloudwatch:get_metric_data` (never `Average` alone) and confirm no active saturation alarms exist via `cloudwatch:get_active_alarms` and `cloudwatch:get_alarm_history`. If OS memory telemetry (`CWAgent` `mem_used_percent` on EC2) is missing, explicitly state `Memory Telemetry: Unverified (CWAgent not installed)` and **refuse** downsizing recommendations that reduce total GiB of RAM.
- **Integer Parameter Coercion:** Always pass `max_items`, `limit`, `max_results`, and `period` as **native JSON integers** (`50`, `3600`), never strings (`"50"`).

### 4. Savings Reconciliation & Deduplication Law
Never sum raw Compute Optimizer right-sizing savings + Savings Plans recommendations + Cost Optimization Hub totals—doing so double- or triple-counts the same dollar.
- Always use `billing:cost-optimization` (`list_recommendation_summaries` top-level `estimatedTotalDedupedSavings`) as the deduplicated baseline.
- Always sequence **Physical Right-Sizing & Idle Elimination (Stages 3–5) BEFORE Rate Commitments (Stage 6)**, deducting physical hourly savings (`monthly_physical_savings / 730.0`) from uncovered On-Demand spend before sizing Savings Plans or RIs.

### 5. Athena Parquet Scan Discipline ($5.00/TB), Read-Only Mutation & Secret Safety Gates
- **FinOps SQL & Cost Gate (`hooks/finops-sql-and-cost-gate.py`):**
  - **Never run `SELECT *` on Amazon Athena or `billing:cur-storage-lens`** (CUR 2.0 and FOCUS Parquet tables have 125+ columns; `SELECT *` forces a full-column scan at $5.00/TB). Project only required columns, include a partition filter (`billing_period`, `bill_billing_period_start_date`, `BillingPeriodStart`, `year`/`month`, or `dt`), and pass `--work-group` (e.g., `--work-group finops-readonly`).
  - **Never execute destructive or mutating SQL (`DROP`, `DELETE`, `TRUNCATE`, `INSERT`, `UPDATE`, `ALTER`, `CREATE`, `MSCK`, `UNLOAD`)** on Athena or `session-sql`.
  - Note: `billing:session-sql` queries local SQLite at **$0.00 cost**, where `SELECT * FROM <table> LIMIT 10` is safe and permitted.
- **Read-Only AWS Mutation Gate (`hooks/aws-mutation-gate.py`):** Execute only read-only discovery calls (`Describe*`, `Get*`, `List*`, `Query*`). Never execute mutating AWS commands (`budgets create-budget`, `budgets delete-budget`, `ec2 delete-volume`, `ec2 modify-volume`, `rds modify-db-instance`, `s3 rb`, `ce delete-cost-category-definition`, `terraform apply`, `cdk deploy`); output validated CLI/IaC remediation plans for user approval.
- **Secret Safety Gate (`hooks/secret-safety.py`):** Never call `secretsmanager:GetSecretValue`, `kms:Decrypt`, or curl `localhost:2773/secretsmanager/get` to fetch plaintext secrets. Use `secretsmanager:DescribeSecret` for metadata/cost inspection and `{{resolve:secretsmanager:...}}` dynamic references in IaC.

### 6. `awsknowledge` MCP Fallback When No Local Sub-Skill Matches
If **no** sub-skill or local `references/*.md` file matches the user's specialized AWS billing/FinOps question, immediately query the connected `awsknowledge` MCP server (`aws___search_documentation` / `aws___read_documentation` — 1–2 focused searches; skip unrelated skills or pricing calls unless asked) and answer directly.

---

## Decision Guide & Reference Routing Table

Load the matching reference file from `references/` before running domain-specific workflows:

| Question / FinOps Task | Primary MCP Tools | Reference Playbook |
|---|---|---|
| How do I run a complete 7-stage FinOps audit and generate a Decision Packet? | `billing:*`, `cloudwatch:*`, `aws-mcp` | [`references/cost-audit.md`](./references/cost-audit.md) |
| What am I spending, what drove MoM variance, or what caused a cost spike? | `billing:cost-explorer`, `billing:cost-comparison`, `billing:cost-anomaly` | [`references/cost-explorer.md`](./references/cost-explorer.md) |
| Where can I save money across the account/org (deduplicated starting point)? | `billing:cost-optimization`, `billing:compute-optimizer-automation`, `billing:session-sql` | [`references/cost-optimization-hub.md`](./references/cost-optimization-hub.md) |
| How do I perform deterministic math on API results or spilled SQLite tables? | `billing:session-sql`, `Bash` (`python3 -c`) | [`references/deterministic-calculations.md`](./references/deterministic-calculations.md) |
| How do I query resource-level CUR 2.0 or FOCUS 1.0/1.2+ data in Athena? | `aws-mcp` (`bcm-data-exports`, `athena`), `billing:storage-lens` | [`references/cur-athena.md`](./references/cur-athena.md) |
| How do I right-size EC2 instances, ASGs, or migrate to Graviton (`arm64`) safely? | `billing:compute-optimizer`, `cloudwatch:get_metric_data`, `cloudwatch:get_active_alarms` | [`references/ec2-rightsizing.md`](./references/ec2-rightsizing.md), [`references/graviton-migration-matrix.md`](./references/graviton-migration-matrix.md) |
| How do I optimize EBS volumes (`gp2`->`gp3`, `io1`->`io2`, idle volumes, Snapshot Archive)? | `billing:compute-optimizer`, `billing:compute-optimizer-automation`, `cloudwatch` | [`references/ebs-optimization.md`](./references/ebs-optimization.md), [`references/compute-and-storage-rightsizing.md`](./references/compute-and-storage-rightsizing.md) |
| How do I right-size RDS/Aurora or calculate Aurora I/O-Optimized vs. Standard break-even? | `billing:compute-optimizer`, `cloudwatch:get_metric_data`, `billing:cost-explorer` | [`references/rds-optimization.md`](./references/rds-optimization.md) |
| How do I optimize Lambda memory, architecture (`arm64`), or Provisioned Concurrency / SnapStart? | `billing:compute-optimizer`, `cloudwatch:execute_log_insights_query` | [`references/lambda-optimization.md`](./references/lambda-optimization.md) |
| How do I engineer a Savings Plans portfolio, compute ESR, or run Purchase Analyzer simulations? | `billing:sp-performance`, `billing:sp-explorer`, `billing:sp-recommendation`, `billing:sp-purchase-analyzer` | [`references/savings-plans.md`](./references/savings-plans.md) |
| How do I evaluate Reserved Instances across EC2, RDS, ElastiCache, Redshift, and OpenSearch? | `billing:ri-performance`, `awspricing:get_pricing` | [`references/reserved-instances.md`](./references/reserved-instances.md) |
| How do I optimize NAT Gateways, VPC Endpoints, S3 Storage Lens, Bedrock GenAI, EKS, DynamoDB, or CloudWatch Logs? | `billing:storage-lens`, `billing:cost-explorer`, `awspricing:get_bedrock_patterns`, `cloudwatch` | [`references/service-optimization.md`](./references/service-optimization.md), [`references/observability-cost-traps.md`](./references/observability-cost-traps.md) |
| How do I look up service SKU pricing or inspect BCM Pricing Calculator workload/bill estimates? | `awspricing:get_pricing`, `billing:aws-pricing`, `billing:bcm-pricing-calc` | [`references/pricing-lookup.md`](./references/pricing-lookup.md) |
| How do I estimate Shift-Left Terraform/CDK/CloudFormation costs or validate remediation IaC? | `Bash` (`infracost`), `awspricing:analyze_cdk_project`, `awspricing:analyze_terraform_project`, `awsiac:*` | [`references/shift-left-iac-estimation.md`](./references/shift-left-iac-estimation.md) |
| How do I design AWS Budgets (`COST`, `USAGE`, `SP/RI_UTILIZATION`) and Budget Actions? | `billing:budgets`, `billing:budget-actions`, `billing:budget-notifications` | [`references/budgets.md`](./references/budgets.md) |
| How do I govern Billing Conductor, Cost Categories, Credits, Enterprise Support, and Invoicing? | `billing:list-billing-groups`, `billing:list-cost-category-definitions`, `billing:credits`, `billing:enterprise-support`, `billing:invoicing`, `billing:invoice-units` | [`references/governance-and-invoicing.md`](./references/governance-and-invoicing.md) |
| How do I check AWS Free Tier status (Legacy 12-month vs. July 2025 $200 Credit Model)? | `billing:free-tier-usage`, `aws-mcp` (`freetier:GetAccountPlanState`) | [`references/free-tier.md`](./references/free-tier.md) |

---

## Complete MCP Tool Inventory (`billing`, `awspricing`, `cloudwatch`, `awsiac`, `aws-mcp`, `awsknowledge`)

| Server | Tool / Module | Key Operations & Parameters |
|---|---|---|
| `billing` | `cost-explorer` | `operation="getCostAndUsage"` (`start_date`, `end_date`, `granularity`, `metrics`, `group_by`, `filter`, `billing_view_arn`), `getCostAndUsageWithResources` (14d max), `getDimensionValues`, `getCostForecast`, `getUsageForecast`, `getTags`, `getCostCategories` |
| `billing` | `cost-comparison` | `operation="getCostAndUsageComparisons"` or `"getCostComparisonDrivers"` (`baseline_start_date`, `baseline_end_date`, `comparison_start_date`, `comparison_end_date`, `metric_for_comparison`) |
| `billing` | `cost-anomaly` | Takes `start_date`, `end_date` directly (optional `monitor_arn`, `max_results`, `total_impact_operator`, `total_impact_start` — do **NOT** pass `operation`) |
| `billing` | `cost-optimization` / `rec-details` | `operation="list_recommendation_summaries"`, `"list_recommendations"`, `"get_recommendation"`, `"list_efficiency_metrics"` |
| `billing` | `compute-optimizer` & Top-Level Tools | `compute-optimizer` (`operation="get_enrollment_status"`, `"get_ec2_instance_recommendations"`, `"get_ebs_volume_recommendations"`, `"get_lambda_function_recommendations"`, `"get_rds_database_recommendations"`, `"get_ecs_service_recommendations"`) or top-level tools `get_enrollment_status`, `get_ec2_instance_optimization_recommendations`, `get_ebs_volume_optimization_recommendations`, `get_rds_optimization_recommendations`, `get_lambda_optimization_recommendations`, `get_eks_Optimization_recommendations` |
| `billing` | `sp-performance` / `ri-performance` | `sp-performance` (`operation="get_savings_plans_coverage"`, `"get_savings_plans_utilization"`, `"get_savings_plans_utilization_details"`, `"get_savings_plans_purchase_recommendation"`), `ri-performance` (`operation="get_reservation_coverage"`, `"get_reservation_utilization"`, `"get_reservation_purchase_recommendation"`) |
| `billing` | `budgets` / `free-tier-usage` | `budgets` takes `account_id`, `budget_name`, `max_items` directly (no `operation` param); `free-tier-usage` takes `filter`, `max_results` directly (no `operation` param) |
| `billing` | Billing Views / Billing Conductor / Cost Categories | Top-level tools: `list-billing-views`, `get-billing-view`, `list-source-views-for-billing-view`, `list-billing-groups`, `list-account-associations`, `get-billing-group-cost-report`, `list-custom-line-items`, `list-pricing-rules`, `list-pricing-plans`, `list-cost-category-definitions`, `describe-cost-category-definition` |
| `billing` | BCM Data Exports & CUR Tools | `list-bcm-data-exports`, `get-bcm-data-export`, `list-bcm-data-export-tables`, `get-bcm-data-export-table`, `cur-WoW`, `cur-MoM`, `cur-daily`, `cur-hourly`, `cur-sp-inventory`, `cur-ri-inventory`, `cur-net-unblended`, `cur-cost-allocation`, `cur-data-transfer`, `cur-storage-lens` |
| `billing` | `session-sql` | `session-sql` (`query` — $0.00 local SQLite engine for spilled MCP tables) |
| `awspricing` | Project & SKU Pricing | `analyze_cdk_project`, `analyze_terraform_project`, `get_pricing` (multi-region array, `ANY_OF`/`CONTAINS`/`NONE_OF`, `output_options`), `get_bedrock_patterns`, `get_price_list_urls`, `generate_cost_report` |
| `cloudwatch` | FinOps Telemetry Tools | `get_metric_data`, `get_metric_metadata`, `analyze_metric`, `get_recommended_metric_alarms`, `get_active_alarms`, `get_alarm_history`, `execute_log_insights_query` |
| `awsiac` | IaC Validation | `validate_cloudformation_template` (`cfn-lint`), `check_cloudformation_template_compliance` (`cfn-guard`), `search_cdk_documentation`, `search_cloudformation_documentation` |
| `aws-mcp` / `awsknowledge` | Read-Only Inspection & Docs | `aws___call_aws` / `aws___run_script` (read-only API calls protected by `aws-mutation-gate.py` & `finops-sql-and-cost-gate.py`), `aws___search_documentation`, `aws___read_documentation`, `aws___get_regional_availability` |

---

## Billing Views Scoping

A billing view scopes cost and usage data to a specific slice of an organization's billing (`PRIMARY`, `BILLING_GROUP`, or `CUSTOM`). Discover views first via `billing:list-billing-views`:

| Supports `--billing-view-arn` / `billing_view_arn` | Does NOT support it |
|-------------------------------|---------------------|
| `ce get-cost-and-usage` | `ce get-reservation-coverage` |
| `ce get-cost-and-usage-with-resources` | `ce get-reservation-utilization` |
| `ce get-cost-forecast` / `ce get-usage-forecast` | `ce get-savings-plans-coverage` |
| `ce get-dimension-values` / `ce get-tags` | `ce get-savings-plans-utilization` |
| `ce get-cost-and-usage-comparisons` / `ce get-cost-comparison-drivers` | |
| `budgets create-budget` / `describe-budgets` (in budget JSON) | |

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ValidationException` on Cost Explorer | Wrong dimension key (e.g., `CHARGE_TYPE` instead of `RECORD_TYPE`) | Use `RECORD_TYPE` for charge type filtering |
| Empty results with filter | Filter value doesn't match exact Cost Explorer string (e.g., `"EC2-Other"` instead of `"EC2 - Other"`) | Call `getDimensionValues` first to get valid values |
| `AccessDeniedException` on hourly data | Hourly granularity not enabled | Enable in Cost Explorer preferences; limited to past 14 days |
| `Account not registered` / `Inactive` on Compute Optimizer | Not opted in | Report `status: Inactive` honestly and recommend `aws compute-optimizer update-enrollment-status --status Active` |
| Budgets API fails outside `us-east-1` | Budgets control plane is global in `us-east-1` | Query via `billing:budgets` or `--region us-east-1` |
| Cost Explorer `Total` empty with `GroupBy` | By design — AWS omits top-level `Total` when grouping | Aggregate grouped rows via `billing:session-sql` or Python script |
| `ValidationException` on `cost-comparison` | Dates do not align to exact 1-month boundaries | Both periods must start on the `01` of a month and end on the `01` of the next month |
| `ValidationException` on `cloudwatch` MCP | `max_items`, `limit`, or `period` passed as a string | Pass integer parameters as native JSON integers (`50`, `3600`) |
