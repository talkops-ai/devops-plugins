# CUR 2.0, FOCUS 1.0/1.2+, and AWS Data Exports (Athena SQL)

## Which Report Format?

AWS supports three billing export formats in Amazon Athena. Always discover which format the customer has deployed before writing SQL queries:

| Format | Table Name | Status | Key Differences |
|--------|-----------|--------|-----------------|
| **CUR 2.0** | `COST_AND_USAGE_REPORT` | Recommended | Fixed schema, nested columns (`resource_tags`, `cost_category`, `product`, `discount` are `MAP<STRING, STRING>`), Parquet/GZIP. Created via AWS Data Exports (`bcm-data-exports`). |
| **FOCUS 1.0 / 1.2+** | `FOCUS_1_0_AWS` / `FOCUS_1_2_AWS` | GA | FinOps Open Cost and Usage Specification — cloud-agnostic schema for multi-cloud FinOps. Standardized columns (`BilledCost`, `EffectiveCost`, `ListCost`, `ContractedCost`, `ServiceName`, `SubAccountId`, `ResourceId`, `ChargeCategory`, `CommitmentDiscountId`, `Tags`). Created via AWS Data Exports. |
| **Legacy CUR** | User-defined | Supported | Dynamic schema (columns vary monthly based on usage), tags/categories as flattened columns (e.g., `resource_tags_user_creator`), supports CSV/ZIP/GZIP/Parquet. Created via legacy CUR API (`cur`). |

### Mandatory Pre-Query Discovery Protocol

Before running analytical Athena queries, run these read-only discovery commands via `aws___call_aws` or `Bash`:

```bash
# 1. Discover active Data Exports (CUR 2.0 or FOCUS)
aws bcm-data-exports list-exports
aws bcm-data-exports get-export --export-arn <export-arn>

# 2. Discover Athena workgroups (pick one with BytesScannedCutoffPerQuery) and Glue tables
aws athena list-work-groups
aws glue get-tables --database-name <cur_or_focus_database>
```

Or run a `$0.00` metadata query against `information_schema.columns`:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = '<database_name>' AND table_name = '<table_name>'
ORDER BY ordinal_position;
```

---

## Side-by-Side Column Mapping (FOCUS 1.0/1.2+ vs. CUR 2.0 vs. Legacy CUR)

| Concept | FOCUS 1.0 / 1.2+ (`FOCUS_1_2_AWS`) | CUR 2.0 (`COST_AND_USAGE_REPORT`) | Legacy CUR |
|---|---|---|---|
| **Partition Filter** | `billing_period = '2026-03'` or `BillingPeriodStart = TIMESTAMP '2026-03-01'` | `bill_billing_period_start_date = TIMESTAMP '2026-03-01'` or `billing_period = '2026-03'` | `billing_period = '2026-03'` or `year = '2026' AND month = '3'` |
| **Amortized / Effective Cost** | `EffectiveCost` | `COALESCE(savings_plan_savings_plan_effective_cost, reservation_effective_cost, line_item_unblended_cost)` | Same as CUR 2.0 |
| **Cash / Invoiced Cost** | `BilledCost` | `line_item_unblended_cost` | `line_item_unblended_cost` |
| **Public On-Demand List Cost** | `ListCost` | `pricing_public_on_demand_cost` | `pricing_public_on_demand_cost` |
| **Contracted Cost (EDP)** | `ContractedCost` | `line_item_net_unblended_cost` | `line_item_net_unblended_cost` |
| **Service Name / Code** | `ServiceName` (`x_ServiceCode`) | `line_item_product_code` | `line_item_product_code` |
| **Linked Account ID** | `SubAccountId` / `SubAccountName` | `line_item_usage_account_id` | `line_item_usage_account_id` |
| **Resource ID** | `ResourceId` | `line_item_resource_id` | `line_item_resource_id` |
| **Charge Type** | `ChargeCategory` (`Usage`, `Purchase`, `Tax`, `Credit`, `Adjustment`) | `line_item_line_item_type` (`Usage`, `SavingsPlanCoveredUsage`, `DiscountedUsage`, `Fee`, `RIFee`, `Tax`, `Credit`) | `line_item_line_item_type` |
| **Tags** | `Tags['user:Environment']` (`MAP<STRING, STRING>`) | `resource_tags['user:Environment']` (`MAP<STRING, STRING>`) | `resource_tags_user_environment` (flattened column) |
| **Product Attributes** | `x_UsageType`, `x_Operation` | `product['attribute']` (`MAP`), `line_item_usage_type`, `line_item_operation` | `product_<attribute>`, `line_item_usage_type` |

---

## Athena Cost-Protection Guardrails (Enforced by `hooks/finops-sql-and-cost-gate.py`)

1. **NEVER run `SELECT *` on Amazon Athena or `billing:storage-lens`:** CUR 2.0 and FOCUS tables contain 125+ columns in Apache Parquet. `SELECT *` scans every column across S3 at **$5.00/TB**. Projecting only 5–8 needed columns cuts scanned bytes by **90%–98%**. (Note: `SELECT *` IS allowed on `billing:session-sql` because `session-sql` queries local in-process SQLite at $0.00 cost.)
2. **ALWAYS filter by partition key in the `WHERE` clause:** Include `bill_billing_period_start_date`, `billing_period`, `BillingPeriodStart`, `year`/`month`, or `dt`.
3. **ALWAYS pass `--work-group` on `aws athena start-query-execution`:** Ensures workgroup byte-scan cutoffs are enforced.

---

## Setup Reference (CUR 2.0 via Data Exports)

*(For reference or hand-off to `aws-iac-engineer` — `aws-finops-engineer` is read-only against live AWS accounts)*

```bash
aws bcm-data-exports create-export --export '{
  "Name":"MyCUR2Export",
  "DataQuery":{"QueryStatement":"SELECT bill_billing_period_start_date, line_item_usage_start_date, line_item_usage_account_id, line_item_product_code, line_item_usage_type, line_item_operation, line_item_resource_id, line_item_line_item_type, line_item_usage_amount, line_item_unblended_cost, pricing_public_on_demand_cost, savings_plan_savings_plan_effective_cost, savings_plan_savings_plan_a_r_n, reservation_effective_cost, reservation_reservation_a_r_n, resource_tags, cost_category FROM COST_AND_USAGE_REPORT",
    "TableConfigurations":{"COST_AND_USAGE_REPORT":{"TIME_GRANULARITY":"DAILY","INCLUDE_RESOURCES":"TRUE","INCLUDE_SPLIT_COST_ALLOCATION_DATA":"TRUE"}}},
  "DestinationConfigurations":{"S3Destination":{"S3Bucket":"my-cur-bucket","S3Prefix":"cur2","S3Region":"us-east-1",
    "S3OutputConfigurations":{"OutputType":"CUSTOM","Format":"PARQUET","Compression":"PARQUET","Overwrite":"OVERWRITE_REPORT"}}},
  "RefreshCadence":{"Frequency":"SYNCHRONOUS"}}'
```

Always use `PARQUET` — 10–100x cheaper Athena queries than CSV.

---

## Production Athena SQL Query Library

### 1. Monthly Cost by Service (CUR 2.0)
```sql
SELECT
  line_item_product_code AS service,
  ROUND(SUM(line_item_unblended_cost), 2) AS unblended_cost_usd,
  ROUND(
    SUM(COALESCE(savings_plan_savings_plan_effective_cost, reservation_effective_cost, line_item_unblended_cost)),
    2
  ) AS amortized_usage_cost_usd
FROM cost_and_usage_report
WHERE bill_billing_period_start_date = TIMESTAMP '2026-03-01'
  AND line_item_line_item_type IN ('Usage', 'SavingsPlanCoveredUsage', 'DiscountedUsage')
GROUP BY line_item_product_code
ORDER BY amortized_usage_cost_usd DESC;
```

### 2. Top 20 Most Expensive Individual Resources (CUR 2.0)
```sql
SELECT
  line_item_usage_account_id AS account_id,
  line_item_product_code AS service,
  line_item_resource_id AS resource_id,
  line_item_usage_type AS usage_type,
  ROUND(
    SUM(COALESCE(savings_plan_savings_plan_effective_cost, reservation_effective_cost, line_item_unblended_cost)),
    2
  ) AS amortized_cost_usd
FROM cost_and_usage_report
WHERE bill_billing_period_start_date = TIMESTAMP '2026-03-01'
  AND line_item_resource_id <> ''
  AND line_item_line_item_type IN ('Usage', 'SavingsPlanCoveredUsage', 'DiscountedUsage')
GROUP BY 1, 2, 3, 4
ORDER BY amortized_cost_usd DESC
LIMIT 20;
```

### 3. Effective Savings Rate (ESR) by Service & Commitment Type (FOCUS 1.0 / 1.2+)
```sql
SELECT
  ServiceName,
  COALESCE(CommitmentDiscountType, 'On-Demand / Uncovered') AS commitment_type,
  ROUND(SUM(ListCost), 2) AS public_on_demand_list_cost_usd,
  ROUND(SUM(EffectiveCost), 2) AS effective_amortized_cost_usd,
  ROUND(SUM(ListCost - EffectiveCost), 2) AS realized_savings_usd,
  ROUND(
    100.0 * (1.0 - SUM(EffectiveCost) / NULLIF(SUM(ListCost), 0)),
    2
  ) AS effective_savings_rate_pct
FROM focus_1_2_aws
WHERE billing_period = '2026-03'
  AND ChargeCategory = 'Usage'
GROUP BY 1, 2
HAVING SUM(ListCost) > 10.0
ORDER BY realized_savings_usd DESC
LIMIT 50;
```

### 4. Savings Plans Effective Rate vs. On-Demand (CUR 2.0)
```sql
SELECT
  line_item_product_code,
  ROUND(SUM(savings_plan_savings_plan_effective_cost), 2) AS sp_effective_cost_usd,
  ROUND(SUM(pricing_public_on_demand_cost), 2) AS ondemand_equivalent_usd,
  ROUND(
    100.0 * (1.0 - SUM(savings_plan_savings_plan_effective_cost) / NULLIF(SUM(pricing_public_on_demand_cost), 0)),
    2
  ) AS esr_pct
FROM cost_and_usage_report
WHERE savings_plan_savings_plan_a_r_n IS NOT NULL
  AND savings_plan_savings_plan_a_r_n <> ''
  AND bill_billing_period_start_date = TIMESTAMP '2026-03-01'
GROUP BY line_item_product_code
ORDER BY ondemand_equivalent_usd DESC;
```

### 5. Network Data Transfer Breakdown by Category & Resource (CUR 2.0)
```sql
SELECT
  line_item_usage_account_id AS account_id,
  line_item_product_code AS service,
  product['from_location'] AS from_location,
  product['to_location'] AS to_location,
  line_item_usage_type AS usage_type,
  line_item_resource_id AS resource_id,
  ROUND(SUM(line_item_usage_amount), 2) AS usage_gb,
  ROUND(SUM(line_item_unblended_cost), 2) AS cost_usd
FROM cost_and_usage_report
WHERE bill_billing_period_start_date = TIMESTAMP '2026-03-01'
  AND (
    REGEXP_LIKE(line_item_usage_type,
      'DataTransfer|AWS-(In|Out)-Bytes|Bytes-(Internet|AWS)|CloudFront-.*-Bytes|DataXfer|-ABytes-|Regional-Bytes')
    OR REGEXP_LIKE(line_item_usage_type,
      'NatGateway-Bytes|VpcEndpoint-Bytes|TransitGateway-Bytes')
    OR (line_item_usage_type LIKE '%DataProcessing-Bytes%'
        AND line_item_product_code = 'AWSELB')
  )
GROUP BY 1, 2, 3, 4, 5, 6
HAVING SUM(line_item_unblended_cost) > 10.0
ORDER BY cost_usd DESC
LIMIT 100;
```

### 6. EKS / ECS Split Cost Allocation by Cluster, Namespace & Workload (CUR 2.0)
Handles both colon-delimited (`aws:eks:cluster-name`) and underscore-normalized (`aws_eks_cluster_name`) tag map keys, separating utilized pod cost from idle node slack:
```sql
SELECT
  line_item_usage_account_id AS account_id,
  COALESCE(
    resource_tags['aws:eks:cluster-name'],
    resource_tags['aws_eks_cluster_name'],
    resource_tags['aws:ecs:clusterName'],
    'non-container'
  ) AS cluster_name,
  COALESCE(
    resource_tags['aws:eks:namespace'],
    resource_tags['aws_eks_namespace'],
    resource_tags['aws:ecs:serviceName'],
    'unallocated'
  ) AS namespace_or_service,
  COALESCE(
    resource_tags['aws:eks:workload-name'],
    resource_tags['aws_eks_workload_name'],
    'unallocated'
  ) AS workload_name,
  ROUND(SUM(COALESCE(split_line_item_net_split_cost, split_line_item_split_cost, 0)), 2) AS utilized_workload_cost_usd,
  ROUND(SUM(COALESCE(split_line_item_net_unused_cost, split_line_item_unused_cost, 0)), 2) AS idle_node_slack_cost_usd,
  ROUND(
    100.0 * SUM(COALESCE(split_line_item_net_unused_cost, split_line_item_unused_cost, 0))
    / NULLIF(
        SUM(
          COALESCE(split_line_item_net_split_cost, split_line_item_split_cost, 0) +
          COALESCE(split_line_item_net_unused_cost, split_line_item_unused_cost, 0)
        ),
        0
      ),
    2
  ) AS node_slack_waste_pct
FROM cost_and_usage_report
WHERE bill_billing_period_start_date = TIMESTAMP '2026-03-01'
  AND (
    split_line_item_split_cost IS NOT NULL
    OR resource_tags['aws:eks:cluster-name'] IS NOT NULL
    OR resource_tags['aws_eks_cluster_name'] IS NOT NULL
  )
GROUP BY 1, 2, 3, 4
ORDER BY utilized_workload_cost_usd DESC
LIMIT 100;
```

### 7. Amazon Bedrock Token, Batch, Cache & Provisioned Throughput Breakdown (CUR 2.0)
```sql
SELECT
  line_item_usage_account_id AS account_id,
  line_item_product_code AS service_code,
  line_item_usage_type AS usage_type,
  line_item_operation AS operation,
  CASE
    WHEN line_item_usage_type LIKE '%Batch%' THEN 'Batch Inference (50% Discount)'
    WHEN line_item_usage_type LIKE '%CacheRead%' OR line_item_usage_type LIKE '%CacheWrite%' THEN 'Prompt Caching (Up to 90% Discount)'
    WHEN line_item_usage_type LIKE '%ProvisionedThroughput%' OR line_item_usage_type LIKE '%ModelUnit%' THEN 'Provisioned Throughput (Model Units)'
    default 'On-Demand Token / GenAI Usage'
  END AS inference_mode,
  ROUND(SUM(line_item_usage_amount), 4) AS usage_units,
  ROUND(SUM(line_item_unblended_cost), 2) AS total_cost_usd
FROM cost_and_usage_report
WHERE bill_billing_period_start_date = TIMESTAMP '2026-03-01'
  AND (line_item_product_code LIKE '%Bedrock%' OR line_item_product_code = 'AmazonSageMaker')
  AND line_item_line_item_type IN ('Usage', 'DiscountedUsage', 'SavingsPlanCoveredUsage')
GROUP BY 1, 2, 3, 4, 5
HAVING SUM(line_item_unblended_cost) > 1.0
ORDER BY total_cost_usd DESC
LIMIT 100;
```

## Gotchas

- **Confirm the report format first.** Legacy CUR, CUR 2.0, and FOCUS 1.2 have different column names, filtering syntax, and table names.
- **Service names differ between Cost Explorer and CUR.** Cost Explorer uses human-readable names (e.g., `Elastic Load Balancing`). CUR uses API-style product codes (e.g., `AWSELB`). Before writing filter queries, run `SELECT DISTINCT line_item_product_code` with a partition filter to discover available values.
- **Tags differ by format:** Legacy CUR uses `resource_tags_user_<tagname>` columns. CUR 2.0 uses `resource_tags['user:tagname']` map syntax. FOCUS uses `Tags['user:tagname']`.
- CUR data is delivered to S3 up to 3 times daily — not real-time.
- Current month CUR is incomplete until the month closes (~3rd–5th of the following month).

## Additional Resources

- **CUR Query Library** (Well-Architected Labs): https://wellarchitectedlabs.com/cost-optimization/cur_queries/
- **Data Transfer Cost Analysis Dashboard** (Well-Architected Labs): https://wellarchitectedlabs.com/cost/200_labs/200_enterprise_dashboards/3_create_data_transfer_cost_analysis_dashboard/
- **CUR 2.0 column reference**: https://docs.aws.amazon.com/cur/latest/userguide/table-dictionary-cur2.html
- **FOCUS 1.2 column reference**: https://docs.aws.amazon.com/cur/latest/userguide/table-dictionary-focus-1-2-aws.html
