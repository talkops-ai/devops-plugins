# AWS Glue Data Quality (DQDL) Rule Library & In-Flight Quarantine Patterns

Use this reference when writing DQDL rulesets, running Glue Data Quality evaluation/recommendation runs via CLI/MCP, or splitting passed vs. quarantined records inside a Glue PySpark job.

---

## 1. Production DQDL Ruleset Reference

DQDL rulesets are enclosed in `Rules = [ ... ]` (and optional `Analyzers = [ ... ]` for dynamic anomaly detection):

```dqdl
Rules = [
    # 1. Volume & Freshness
    RowCount > 0,
    DataFreshness "updated_at" <= 24 hours,

    # 2. Primary Key Integrity (Not Null + 100% Unique)
    IsPrimaryKey "order_id",
    IsComplete "customer_id",
    Completeness "shipping_address_id" >= 0.98,

    # 3. Domain & Range Constraints
    ColumnValues "order_status" in ["PENDING", "PAID", "SHIPPED", "DELIVERED", "CANCELLED"],
    ColumnValues "order_total_usd" >= 0.0,
    ColumnValues "currency_code" matches "[A-Z]{3}",

    # 4. Statistical & Distribution Guards
    Mean "order_total_usd" between 10.0 and 5000.0,
    StandardDeviation "order_total_usd" < 10000.0,

    # 5. Cross-Column & Custom SQL Rules
    CustomSql "SELECT COUNT(*) FROM primary WHERE shipped_at < created_at" = 0,

    # 6. Cross-Table Referential Integrity
    ReferentialIntegrity "customer_id" "silver_db.customers.customer_id" >= 0.999
]

Analyzers = [
    RowCount,
    Completeness "email",
    Mean "order_total_usd"
]
```

---

## 2. Managing & Running DQDL Rulesets on Glue Catalog Tables (CLI / MCP)

```bash
# 1. Create a DQDL ruleset attached to a Glue Catalog table
aws glue create-data-quality-ruleset \
  --region <REGION> \
  --name orders_silver_dq_ruleset \
  --target-table '{"DatabaseName": "silver_db", "TableName": "orders"}' \
  --ruleset 'Rules = [ RowCount > 0, IsPrimaryKey "order_id", IsComplete "customer_id", ColumnValues "order_total_usd" >= 0.0 ]'

# 2. Trigger an on-demand Data Quality evaluation run (with pushdown predicate for the latest partition)
aws glue start-data-quality-ruleset-evaluation-run \
  --region <REGION> \
  --role arn:aws:iam::<ACCOUNT>:role/<GLUE_DQ_ROLE> \
  --ruleset-names '["orders_silver_dq_ruleset"]' \
  --data-source '{"GlueTable": {"DatabaseName": "silver_db", "TableName": "orders", "AdditionalOptions": {"pushDownPredicate": "event_date == '\''2026-10-14'\''"}}}' \
  --additional-run-options '{"CloudWatchMetricsEnabled": true, "ResultsS3Prefix": "s3://<DQ_RESULTS_BUCKET>/dq-results/orders/"}'
```

---

## 3. In-Flight Glue PySpark Row-Level Quarantine Pattern (`EvaluateDataQuality`)

Split clean records (`Passed`) from corrupted records (`Failed`) inside a Glue 5.1+ job so bad rows are routed to an S3 quarantine bucket while clean rows proceed to the Silver Iceberg table (or halt the job if $>1\%$ of rows fail):

```python
from awsgluedq.transforms import EvaluateDataQuality
from awsglue.transforms import SelectFromCollection

DQDL_RULESET = """
Rules = [
    RowCount > 0,
    IsComplete "order_id",
    IsUnique "order_id",
    ColumnValues "order_total_usd" >= 0.0,
    ColumnValues "order_status" in ["PENDING", "PAID", "SHIPPED", "DELIVERED", "CANCELLED"]
]
"""

dq_results = EvaluateDataQuality().process_rows(
    frame=staged_dyf,
    ruleset=DQDL_RULESET,
    publishing_options={
        "dataQualityEvaluationContext": "orders_silver_in_flight_dq",
        "enableDataQualityCloudWatchMetrics": True,
        "enableDataQualityResultsPublishing": True,
        "resultsS3Prefix": f"s3://{args['DQ_RESULTS_BUCKET']}/dq-metrics/",
    },
    additional_options={
        "observations.scope": "ALL",
        "performanceTuning.caching": "CACHE_LAZY",
    },
)

# Inspect rule-level outcomes for circuit-breaker halt
rule_outcomes_df = SelectFromCollection.apply(
    dfc=dq_results, key="ruleOutcomes", transformation_ctx="rule_outcomes_ctx"
).toDF()

# Split row-level outcomes into Passed vs. Quarantined
row_outcomes_df = SelectFromCollection.apply(
    dfc=dq_results, key="rowLevelOutcomes", transformation_ctx="row_outcomes_ctx"
).toDF()

passed_df = row_outcomes_df.filter("DataQualityEvaluationResult = 'Passed'").drop(
    "DataQualityRulesPass", "DataQualityRulesFail", "DataQualityRulesSkip", "DataQualityEvaluationResult"
)
failed_df = row_outcomes_df.filter("DataQualityEvaluationResult = 'Failed'")

if not failed_df.isEmpty():
    failed_df.write.mode("append").parquet(
        f"s3://{args['QUARANTINE_BUCKET']}/quarantine/orders/"
    )
```
