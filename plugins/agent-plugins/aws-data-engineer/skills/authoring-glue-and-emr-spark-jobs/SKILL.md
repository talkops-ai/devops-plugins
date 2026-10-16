---
name: authoring-glue-and-emr-spark-jobs
description: >-
  Authors, optimizes, and tunes distributed PySpark and Ray ETL jobs on AWS Glue 5.1+ and Amazon EMR
  (Serverless and EC2). Covers Medallion (Bronze/Silver/Gold) lakehouse modeling, Apache Iceberg
  MERGE INTO and schema evolution, Parquet/ORC columnar conversion, partition pruning, Spark data
  skew mitigation (AQE and key salting), shuffle and executor memory tuning, and Glue Job Bookmarks
  for stateful incremental processing.
version: 1
---

# Authoring & Tuning AWS Glue 5.1+ and Amazon EMR Spark Jobs

Use this skill when designing, writing, optimizing, or refactoring distributed **PySpark**, **Apache Spark SQL**, or **AWS Glue for Ray** ETL transformations on **AWS Glue 5.1+** or **Amazon EMR Serverless / EMR on EC2**.

## Reference Library (Load On-Demand)

- **[references/glue-emr-medallion-and-tuning.md](references/glue-emr-medallion-and-tuning.md)** — Load for production PySpark templates (Bronze $\rightarrow$ Silver $\rightarrow$ Gold Medallion pipelines, Apache Iceberg `MERGE INTO` upserts on S3 Tables and Glue Catalog, Glue Job Bookmarks `transformation_ctx` rules), Spark 3.5+ Adaptive Query Execution (AQE) skew/shuffle tuning, worker sizing (`G.1X` / `G.2X` / `G.4X` / `G.8X` / `Z.2X`), and EMR Serverless application configuration.

---

## Deterministic Spark ETL Workflow

1. **Choose the Compute Engine & Runtime Version:**
   - **AWS Glue 5.1+ (Spark 3.5+, Python 3.11):** Default for serverless batch/micro-batch lakehouse ETL, native Glue Data Catalog / Lake Formation integration, and incremental **Glue Job Bookmarks**.
   - **AWS Glue for Ray (`glueray`):** Choose when workloads are Python-native distributed tasks, Pandas/Polars transformations, or API-bound tasks that do not fit JVM Spark execution.
   - **Amazon EMR Serverless:** Choose for large-scale multi-terabyte Spark workloads requiring custom Docker images, fine-grained vCPU/memory per-driver/executor sizing, pre-initialized warm workers, or lower per-vCPU-hour compute cost at high utilization.
2. **Design the Medallion Lakehouse Transformation:**
   - **Bronze (Raw Landing):** Append-only raw payloads preserved with ingestion metadata (`_ingested_at`, `_source_file`, `_batch_id`). Convert small CSV/JSON files into compacted Apache Iceberg or Snappy-compressed Parquet (~128 MB–512 MB target file size).
   - **Silver (Cleaned, Deduplicated, Conformed):** Enforce explicit `StructType` schemas (never rely on `inferSchema=True` in production!), deduplicate via `ROW_NUMBER() OVER (PARTITION BY pk ORDER BY updated_at DESC)`, cast types, standardize timestamps to UTC, and execute ACID `MERGE INTO` into Apache Iceberg (`s3tablescatalog` or `glue_catalog`).
   - **Gold (Business Aggregates & Star Schemas):** Materialize domain-specific fact/dimension tables or pre-aggregated metrics in S3 Tables (Iceberg) or load into Amazon Redshift via the Redshift Spark connector (`tempformat = "CSV GZIP"` or Parquet with IAM Role).
3. **Enforce Incremental Processing & Idempotency:**
   - **Glue Job Bookmarks:** When reading from S3 or relational JDBC sources via `glueContext.create_dynamic_frame.from_catalog(...)` or `from_options(...)`, pass a unique, stable **`transformation_ctx`** parameter on every stateful operator and call `job.commit()` at the end of the script.
   - ** Warning:** Converting a `DynamicFrame` to a Spark `DataFrame` (`.toDF()`) **before** filtering or reading breaks Glue Job Bookmark state tracking for downstream operators unless the source read itself carries the `transformation_ctx`. For Apache Iceberg sources, prefer Iceberg incremental snapshot reads (`spark.read.option("start-snapshot-id", ...).option("end-snapshot-id", ...)`) or watermark timestamp predicates over Job Bookmarks.
4. **Prevent OOMs, Small-File Explosion & Data Skew:**
   - Enable Spark Adaptive Query Execution (AQE):
     - `spark.sql.adaptive.enabled=true`
     - `spark.sql.adaptive.coalescePartitions.enabled=true`
     - `spark.sql.adaptive.skewJoin.enabled=true`
   - Before writing partitioned tables, sort or distribute by partition columns (`WRITE ORDERED BY` / `.repartition("event_date")` or Iceberg ` fanout-enabled` / `write.distribution-mode=hash`) to prevent opening thousands of concurrent S3 multipart upload streams (`OutOfMemoryError: Direct buffer memory`).
5. **Validate Output Quality:**
   - Pair every Silver/Gold transformation job with in-flight **AWS Glue Data Quality (DQDL)** evaluation (`EvaluateDataQuality().process_rows(...)` via `enforcing-data-quality`) and post-load row-count verification (`querying-data-lake`).
