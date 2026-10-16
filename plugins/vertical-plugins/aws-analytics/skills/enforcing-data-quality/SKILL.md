---
name: enforcing-data-quality
description: >-
  Authors, executes, and automates data quality rulesets using AWS Glue Data Quality (Data Quality
  Definition Language - DQDL) for both Glue Data Catalog tables at rest and in-flight Glue ETL
  PySpark jobs, alongside AWS Glue DataBrew profiling recipes, Athena SQL validation checks, and
  quarantine/circuit-breaker alerting patterns.
version: 1
---

# Enforcing Automated Data Quality (AWS Glue Data Quality / DQDL & Quarantine Patterns)

Use this skill whenever validating newly ingested or transformed tables, authoring **AWS Glue Data Quality rulesets in Data Quality Definition Language (DQDL)**, embedding in-flight quality circuit breakers inside Glue PySpark jobs, or configuring **AWS Glue DataBrew** data profiling jobs.

## Reference Library (Load On-Demand)

- **[references/dqdl-and-quarantine-patterns.md](references/dqdl-and-quarantine-patterns.md)** — Load for complete DQDL syntax and rule libraries (`RowCount`, `IsComplete`, `IsPrimaryKey`, `IsUnique`, `ColumnValues`, `Completeness`, `ReferentialIntegrity`, `CustomSql`, `Analyzers` for dynamic anomaly detection), in-flight Glue PySpark `EvaluateDataQuality` bad-record splitting (`rowLevelOutcomes`), and CLI ruleset evaluation commands.

---

## Deterministic Data Quality Workflow

1. **Mandatory 3-Point Post-Ingestion Check (Every Table Load):**
   After every ingestion (`ingesting-into-data-lake`, `ingesting-streaming-and-cdc-data`) or transformation (`authoring-glue-and-emr-spark-jobs`) run, execute:
   1. **Row Count & Freshness Check:** Verify target row count $> 0$ and matches source delta within tolerance (`RowCount > 0`, `ColumnValues "updated_at" > (now() - 24 hours)`).
   2. **Primary Key Completeness & Uniqueness:** Verify 0 `NULL` primary keys and 0 duplicate primary keys (`IsPrimaryKey "<pk_col>"`).
   3. **Domain Value & Referential Integrity:** Verify status enums, positive currency/quantity constraints, and foreign key joins.
2. **Choose At-Rest Catalog Evaluation vs. In-Flight ETL Circuit Breaker:**
   - **At-Rest Glue Data Catalog DQDL Ruleset (`glue:CreateDataQualityRuleset` $\rightarrow$ `glue:StartDataQualityRulesetEvaluationRun`):** Attach directly to an existing Glue Catalog or S3 Tables Iceberg table to evaluate scheduled partitions and publish pass/fail metrics to CloudWatch and EventBridge (`aws.glue-dataquality`).
   - **In-Flight Glue ETL PySpark `EvaluateDataQuality` Transform:** Embed directly inside the Bronze $\rightarrow$ Silver PySpark script with `publishingOptions` and `additionalOptions={"performanceTuning.caching": "CACHE_LAZY", "observations.scope": "ALL"}`. Split output into `Passed` rows (written to the Silver Iceberg table) and `Failed` rows (written to an S3 quarantine prefix `s3://<bucket>/quarantine/<table_name>/` for inspection).
3. **Bootstrap Rules Automatically When Schema Is Large:**
   - For wide tables with 50+ columns, run `aws glue start-data-quality-rule-recommendation-run` against a representative baseline table snapshot first, review the generated DQDL ruleset, tighten thresholds on primary keys and financial columns, and save via `create-data-quality-ruleset`.
