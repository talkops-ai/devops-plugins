---
name: aws-billing-and-cost-management
description: |
  Principal AWS FinOps and Cloud Financial Management (CFM) skill across the full
  FinOps Foundation lifecycle (Inform, Optimize, Operate, Shift-Left): analyze AWS
  costs, run 7-stage forensic cost audits, isolate MoM variance drivers with Cost
  Comparison, triage Cost Anomalies, deduplicate savings in Cost Optimization Hub,
  validate Compute Optimizer right-sizing (EC2, ASG, EBS, RDS/Aurora, Lambda,
  ECS/EKS) with Two-Key CloudWatch P95/P99 telemetry and Compute Optimizer
  Automation, query CUR 2.0 and FOCUS 1.0/1.2+ with Athena SQL, engineer Savings
  Plans and Reserved Instance portfolios (Effective Savings Rate, Purchase
  Analyzer simulations), optimize NAT Gateway/Cross-AZ data transfer and S3
  Storage Lens lifecycles, optimize GenAI/Bedrock/SageMaker/Containers/Databases
  unit economics, estimate Shift-Left IaC costs (Infracost, CDK/Terraform pricing,
  BCM Pricing Calculator, cfn-lint/cfn-guard validation), and govern multi-account
  billing (Billing Views, Billing Conductor, Cost Categories, Budgets, Credits,
  Enterprise Support, Invoice Units, and Free Tier).
metadata:
  version: "2.0"
---

# AWS Billing, Cost Management, and FinOps Engineering

## Overview

Analyze, optimize, govern, and forecast AWS cloud spend across the FinOps Foundation lifecycle (**Inform**, **Optimize**, **Operate**, and **Shift-Left**). This skill encodes Principal AWS FinOps engineering practices, API gotchas, deterministic calculation rules, Two-Key CloudWatch telemetry verification, CUR 2.0 / FOCUS 1.0/1.2+ Athena SQL patterns, and multi-account governance workflows.

## Usage

Use this skill when:

- Analyzing AWS spending, Month-over-Month variance drivers (`cost-comparison`), or cost forecasts (`cost-explorer`)
- Investigating cost spikes and anomalies (`cost-anomaly`) and decomposing price vs. volume shifts
- Running comprehensive 7-stage FinOps audits and producing deduplicated Decision Packets (`cost-optimization`)
- Right-sizing EC2, Auto Scaling Groups, EBS, RDS/Aurora, Lambda, or ECS/EKS with Two-Key CloudWatch P95/P99 validation (`compute-optimizer`, `compute-optimizer-automation`, `cloudwatch`)
- Engineering Savings Plans and Reserved Instance portfolios, calculating Effective Savings Rate (ESR), or running custom commitment simulations (`sp-performance`, `sp-explorer`, `sp-recommendation`, `sp-purchase-analyzer`, `ri-performance`)
- Querying granular resource-level billing data in CUR 2.0 or FOCUS 1.0/1.2+ via Amazon Athena (`bcm-data-exports`, `athena`)
- Optimizing network data transfer (`NatGateway-Bytes`, `Regional-Bytes`, egress) and S3 Storage Lens lifecycles (`storage-lens`)
- Optimizing workload unit economics across Amazon Bedrock / SageMaker AI, EKS / Karpenter / Fargate, Aurora Standard vs. I/O-Optimized, DynamoDB, Glue, and CloudWatch Logs
- Estimating pre-deployment Shift-Left IaC costs for Terraform, OpenTofu, AWS CDK, or CloudFormation (`infracost`, `awspricing`, `bcm-pricing-calc`, `awsiac`)
- Managing multi-account governance: Billing Views (`billing-views`), Billing Conductor pro-forma pricing (`billing-conductor`), Cost Categories (`cost-categories`), Budgets (`budgets`), Credits (`credits`), Enterprise Support (`enterprise-support`), Invoice Units (`invoice-units`, `invoicing`), and Free Tier (`free-tier`)

---

## Non-Negotiable FinOps Execution Rules

### 1. Always Check the Current Date First
**Before making ANY Cost Explorer, Budgets, Anomaly, or Savings Plans API call, determine the current date** (via `date` or system metadata). Never assume or guess the year from training data. Note that Cost Explorer `End` dates are **exclusive** (`Start=2026-03-01,End=2026-04-01` covers March 1 through March 31).

### 2. Zero-Hallucination Deterministic Calculations
**NEVER perform numerical calculations (sums, averages, percentages, MoM deltas, break-even thresholds, ESR, or invoice totals) mentally in your response.**
- **Local SQLite Session Engine (`billing:session-sql`):** The `billing` MCP server automatically stores large API responses in a local in-process SQLite database (`session.db`) and returns a `table_name`. Query it with `SUM()`, `AVG()`, `ROUND()`, and `GROUP BY` at **$0.00 AWS cost**.
- **Python Calculator (`Bash`):** For break-even formulas, ESR, WACC yield math, or multi-step ratios, run a Python one-liner (`python3 -c "..."`) and cite the exact computed output. See [`references/deterministic-calculations.md`](./references/deterministic-calculations.md).

### 3. The Two-Key Right-Sizing Validation Rule (Financial + Telemetry)
Never recommend downsizing or terminating production compute, database, or storage capacity using billing or Compute Optimizer metadata alone:
- **Key 1 (Financial Opportunity):** Pull deduplicated recommendations from `billing:cost-optimization` (`list_recommendations`) and technical options from `billing:compute-optimizer`.
- **Key 2 (CloudWatch Telemetry Proof):** Verify **14–30 day `p95`, `p99`, and `Maximum` utilization** via `cloudwatch:get_metric_data` (never `Average` alone, which hides diurnal spikes) and confirm no active saturation alarms exist via `cloudwatch:get_active_alarms` and `cloudwatch:get_alarm_history`.
- **Integer Parameter Coercion:** Always pass `max_items`, `limit`, `max_results`, and `period` as **native JSON integers** (`50`, `3600`), never strings (`"50"`).

### 4. Savings Reconciliation & Deduplication Law
Never sum raw Compute Optimizer right-sizing savings + Savings Plans recommendations + Cost Optimization Hub totals—doing so double- or triple-counts the same dollar.
- Always use `billing:cost-optimization` (`list_recommendation_summaries` top-level `estimatedTotalDedupedSavings`) as the deduplicated baseline.
- Always sequence **Physical Right-Sizing & Idle Elimination (Stages 3–5) BEFORE Rate Commitments (Stage 6)**, deducting physical hourly savings from uncovered On-Demand spend before sizing Savings Plans or RIs.

### 5. Athena Parquet Scan Discipline ($5.00/TB)
- **Never run `SELECT *` on Amazon Athena or `billing:storage-lens`** (blocked by `hooks/finops-sql-and-cost-gate.py`). CUR 2.0 and FOCUS Parquet tables have 125+ columns; project only required columns, include a partition filter (`billing_period`, `bill_billing_period_start_date`, `BillingPeriodStart`, `year`/`month`, or `dt`), and specify `--work-group`.
- Note: `billing:session-sql` queries local SQLite at **$0.00 cost**, where `SELECT * FROM <table> LIMIT 10` is safe and permitted.

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
| How do I right-size EC2 instances, ASGs, or migrate to Graviton (`arm64`) safely? | `billing:compute-optimizer`, `cloudwatch:get_metric_data`, `cloudwatch:get_active_alarms` | [`references/ec2-rightsizing.md`](./references/ec2-rightsizing.md) |
| How do I optimize EBS volumes (`gp2`->`gp3`, `io1`->`io2`, idle volumes, Snapshot Archive)? | `billing:compute-optimizer`, `billing:compute-optimizer-automation`, `cloudwatch` | [`references/ebs-optimization.md`](./references/ebs-optimization.md) |
| How do I right-size RDS/Aurora or calculate Aurora I/O-Optimized vs. Standard break-even? | `billing:compute-optimizer`, `cloudwatch:get_metric_data`, `billing:cost-explorer` | [`references/rds-optimization.md`](./references/rds-optimization.md) |
| How do I optimize Lambda memory, architecture (`arm64`), or Provisioned Concurrency / SnapStart? | `billing:compute-optimizer`, `cloudwatch:execute_log_insights_query` | [`references/lambda-optimization.md`](./references/lambda-optimization.md) |
| How do I engineer a Savings Plans portfolio, compute ESR, or run Purchase Analyzer simulations? | `billing:sp-performance`, `billing:sp-explorer`, `billing:sp-recommendation`, `billing:sp-purchase-analyzer` | [`references/savings-plans.md`](./references/savings-plans.md) |
| How do I evaluate Reserved Instances across EC2, RDS, ElastiCache, Redshift, and OpenSearch? | `billing:ri-performance`, `awspricing:get_pricing` | [`references/reserved-instances.md`](./references/reserved-instances.md) |
| How do I optimize NAT Gateways, VPC Endpoints, S3 Storage Lens, Bedrock GenAI, EKS, DynamoDB, or CloudWatch Logs? | `billing:storage-lens`, `billing:cost-explorer`, `awspricing:get_bedrock_patterns`, `cloudwatch` | [`references/service-optimization.md`](./references/service-optimization.md) |
| How do I look up service SKU pricing or inspect BCM Pricing Calculator workload/bill estimates? | `awspricing:get_pricing`, `billing:aws-pricing`, `billing:bcm-pricing-calc` | [`references/pricing-lookup.md`](./references/pricing-lookup.md) |
| How do I estimate Shift-Left Terraform/CDK/CloudFormation costs or validate remediation IaC? | `Bash` (`infracost`), `awspricing:analyze_cdk_project`, `awspricing:analyze_terraform_project`, `awsiac:*` | [`references/shift-left-iac-estimation.md`](./references/shift-left-iac-estimation.md) |
| How do I design AWS Budgets (`COST`, `USAGE`, `SP/RI_UTILIZATION`) and Budget Actions? | `billing:budgets` | [`references/budgets.md`](./references/budgets.md) |
| How do I govern Billing Conductor, Cost Categories, Credits, Enterprise Support, and Invoicing? | `billing:billing-conductor`, `billing:cost-categories`, `billing:credits`, `billing:enterprise-support`, `billing:invoicing`, `billing:invoice-units` | [`references/governance-and-invoicing.md`](./references/governance-and-invoicing.md) |
| How do I check AWS Free Tier status (Legacy 12-month vs. July 2025 $200 Credit Model)? | `billing:free-tier` | [`references/free-tier.md`](./references/free-tier.md) |

---

## Complete MCP Tool Inventory (`billing`, `awspricing`, `cloudwatch`, `awsiac`, `aws-mcp`)

| Server | Tool / Module | Key Operations |
|---|---|---|
| `billing` | `cost-explorer` | `get_cost_and_usage`, `get_cost_and_usage_with_resources` (14d max), `get_dimension_values`, `get_cost_forecast`, `get_usage_forecast`, `get_tags`, `get_cost_categories` (supports `billing_view_arn`) |
| `billing` | `cost-comparison` | `get_cost_and_usage_comparisons`, `get_cost_comparison_drivers` (automatic top-10 MoM variance drivers between two exact 1-month periods) |
| `billing` | `cost-anomaly` | `get_anomalies` (filter by `start_date`, `end_date`, `monitor_arn`, `total_impact_start`) |
| `billing` | `cost-optimization` | `list_recommendation_summaries`, `list_recommendations`, `get_recommendation`, `list_efficiency_metrics`, `get_preferences`, `list_enrollment_statuses` |
| `billing` | `compute-optimizer` | `get_ec2_recommendations`, `get_asg_recommendations`, `get_ebs_recommendations`, `get_lambda_recommendations`, `get_rds_recommendations`, `get_ecs_recommendations`, `get_enrollment_status` |
| `billing` | `compute-optimizer-automation` | `get_enrollment_configuration`, `list_automation_rules`, `get_automation_rule`, `list_automation_events`, `list_recommended_actions`, `list_automation_rule_preview`, `list_automation_rule_preview_summaries` |
| `billing` | `sp-performance` / `sp-explorer` | `get_savings_plans_coverage`, `get_savings_plans_utilization`, `get_savings_plans_utilization_details`, `describe_savings_plans`, `describe_savings_plan_rates`, `describe_savings_plans_offerings`, `describe_savings_plans_offering_rates` |
| `billing` | `sp-recommendation` / `sp-purchase-analyzer` | `get_savings_plans_purchase_recommendation`, `get_savings_plan_purchase_recommendation_details`, `start_savings_plans_purchase_recommendation_generation`, `start_commitment_purchase_analysis`, `get_commitment_purchase_analysis`, `list_commitment_purchase_analyses` |
| `billing` | `ri-performance` | `get_reservation_coverage`, `get_reservation_utilization`, `get_reservation_purchase_recommendation` |
| `billing` | `budgets` / `free-tier` / `credits` | `describe_budgets`, `get_free_tier_usage`, `get_credits`, `get_credit_allocation_history` |
| `billing` | `enterprise-support` | `get_charge_summary`, `get_contract_details`, `list_linked_account_charges` |
| `billing` | `billing-views` / `billing-conductor` / `cost-categories` | `list_billing_views`, `get_billing_view`, `list_source_views_for_billing_view`, `list_billing_Groups`, `get_billing_group_cost_report`, `list_custom_line_items`, `list_pricing_rules`, `list_pricing_plans`, `list_cost_category_definitions`, `describe_cost_category_definition` |
| `billing` | `invoicing` / `invoice-units` / `preferences` | `list_invoice_summaries`, `list_invoice_units`, `get_invoice_unit`, `batch_get_invoice_profile`, `get-billing-preferences`, `procurement-preferences` |
| `billing` | `aws-pricing` / `bcm-pricing-calc` | `get_service_codes`, `get_service_attributes`, `get_attribute_values`, `get_pricing_from_api`, `list_workload_estimates`, `get_workload_estimate`, `list_bill_estimates`, `get_bill_estimate`, `list_bill_estimate_line_items` |
| `billing` | `storage-lens` / `session-sql` | `storage_lens_run_query` (Athena SQL on Storage Lens manifests), `session_sql` ($0.00 local SQLite engine for spilled MCP tables) |
| `awspricing` | Project & SKU Pricing | `analyze_cdk_project`, `analyze_terraform_project`, `get_pricing` (multi-region array, `ANY_OF`/`CONTAINS`/`NONE_OF`, `output_options`), `get_bedrock_patterns`, `get_price_list_urls`, `generate_cost_report` |
| `cloudwatch` | 7 FinOps Telemetry Tools | `get_metric_data`, `get_metric_metadata`, `analyze_metric`, `get_recommended_metric_alarms`, `get_active_alarms`, `get_alarm_history`, `execute_log_insights_query` (+ log query status/cancel helpers) |
| `awsiac` | IaC Validation | `validate_cloudformation_template` (`cfn-lint`), `check_cloudformation_template_compliance` (`cfn-guard`), `search_cdk_documentation`, `search_cloudformation_documentation` |
| `aws-mcp` | Read-Only Inspection | `aws___call_aws` (read-only CLI calls protected by `aws-mutation-gate.py` & `finops-sql-and-cost-gate.py`), `aws___search_documentation`, `aws___read_documentation`, `aws___get_regional_availability` |

---

## Billing Views Scoping

A billing view scopes cost and usage data to a specific slice of an organization's billing (`PRIMARY`, `BILLING_GROUP`, or `CUSTOM`). Discover views first via `billing:billing-views` (`list_billing_views`) or CLI:

```bash
aws billing list-billing-views --billing-view-types PRIMARY CUSTOM BILLING_GROUP
```

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
| Empty results with filter | Filter value doesn't match exact Cost Explorer string (e.g., `"EC2-Other"` instead of `"EC2 - Other"`) | Call `get_dimension_values` first to get valid values |
| `AccessDeniedException` on hourly data | Hourly granularity not enabled | Enable in Cost Explorer preferences; limited to past 14 days |
| `Account not registered` on Compute Optimizer | Not opted in | Recommend `aws compute-optimizer update-enrollment-status --status Active` |
| Budgets API fails outside `us-east-1` | Budgets control plane is global in `us-east-1` | Set `--region us-east-1` |
| Cost Explorer `Total` empty with `GroupBy` | By design — AWS omits top-level `Total` when grouping | Aggregate grouped rows via `billing:session-sql` or Python script |
| `ValidationException` on `cost-comparison` | Dates do not align to exact 1-month boundaries | Both periods must start on the `01` of a month and end on the `01` of the next month |
| `ValidationException` on `cloudwatch` MCP | `max_items`, `limit`, or `period` passed as a string | Pass integer parameters as native JSON integers (`50`, `3600`) |

## Additional Resources

- AWS Cost Management User Guide: https://docs.aws.amazon.com/cost-management/
- AWS Pricing Calculator: https://calculator.aws/
- Compute Optimizer User Guide: https://docs.aws.amazon.com/compute-optimizer/
- Well-Architected Cost Optimization Pillar: https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/
