---
name: ingesting-streaming-and-cdc-data
description: >-
  Configures continuous streaming delivery and analytical Change Data Capture (CDC) pipelines using
  Amazon Data Firehose (direct delivery to S3 Parquet, Amazon S3 Tables / Apache Iceberg with
  multi-table routing, Amazon Redshift, and Amazon OpenSearch), AWS DMS (ongoing analytical CDC
  replication to S3 Parquet, Kinesis, or Redshift), Amazon DynamoDB Streams analytical consumers,
  and Amazon AppFlow SaaS ingestion (Salesforce, ServiceNow, SAP, Zendesk).
version: 1
---

# Ingesting Streaming, CDC & SaaS Data (Data Firehose, DMS CDC, DynamoDB Streams, AppFlow)

Use this skill when building **continuous streaming delivery**, **ongoing Change Data Capture (CDC)** from operational databases into the analytical lakehouse/warehouse, or **SaaS data ingestion**.

> **Scope Boundary with `aws-database-engineer` & `ingesting-into-data-lake`:**
> - For one-time or scheduled batch loads (JDBC, S3 files, Snowflake, BigQuery, DynamoDB full table export), use **`ingesting-into-data-lake`**.
> - For operational OLTP-to-OLTP database migrations (e.g., Oracle $\rightarrow$ Aurora PostgreSQL) or OLTP schema/index tuning, hand off to **`aws-database-engineer`**. This skill uses AWS DMS and DynamoDB Streams **strictly as analytical CDC extraction sources** into S3, S3 Tables (Iceberg), Kinesis, or Redshift.

## Reference Library (Load On-Demand)

- **[references/firehose-dms-appflow-patterns.md](references/firehose-dms-appflow-patterns.md)** — Load for production CLI/JSON configurations covering Amazon Data Firehose direct delivery to Apache Iceberg / S3 Tables (with dynamic table/database routing and row-level `INSERT`/`UPDATE`/`DELETE`), Firehose Parquet format conversion via Glue Data Catalog schemas, AWS DMS ongoing CDC (`full-load-and-cdc` / `cdc`) to S3 Parquet, DynamoDB Streams $\rightarrow$ Kinesis/Firehose pipelines, and Amazon AppFlow SaaS flows.

---

## Step 1: Select the Right Streaming / CDC Pattern

| Source & Latency Requirement | Recommended AWS Ingestion Pattern | Target Analytical Store |
|---|---|---|
| **Kinesis Data Streams, MSK (Kafka), or Direct Put $\rightarrow$ Lakehouse** (near real-time, 60–300s buffer) | **Amazon Data Firehose** with native **Apache Iceberg (`IcebergDestinationConfiguration`)** or S3 Parquet record format conversion | Amazon S3 Tables (`s3tablescatalog`) or Glue Catalog Iceberg / S3 Parquet |
| **Relational OLTP DB (RDS/Aurora/EC2 Postgres, MySQL, Oracle, SQL Server) $\rightarrow$ Continuous CDC** | **AWS DMS Serverless / Replication Instance** (`MigrationType: full-load-and-cdc` or `cdc`) writing Parquet with `Op` (`I`, `U`, `D`) and `_dms_timestamp` columns, OR **Aurora Zero-ETL** to Redshift / S3 Tables | Amazon S3 (Bronze CDC logs $\rightarrow$ Silver Iceberg `MERGE INTO`), Kinesis, or Amazon Redshift |
| **Amazon DynamoDB $\rightarrow$ Continuous Change Stream** | **DynamoDB Kinesis Data Streams integration** (or DynamoDB Streams + EventBridge Pipes) $\rightarrow$ **Amazon Data Firehose** | Amazon S3 Tables (Iceberg), S3 Parquet, or Amazon OpenSearch |
| **SaaS Platforms (Salesforce, ServiceNow, SAP OData, Zendesk, Marketo, Google Analytics)** | **Amazon AppFlow** with Glue Data Catalog registration and Parquet output | Amazon S3 + AWS Glue Data Catalog or Amazon Redshift |

---

## Step 2: Critical Engineering Rules

1. **Amazon Data Firehose to Apache Iceberg (`IcebergDestinationConfiguration`):**
   - Always configure an S3 backup bucket (`S3BackupMode: "FailedDataOnly"`) so malformed JSON or schema-mismatched records land in a dead-letter S3 prefix (`s3://<bucket>/firehose-errors/`) instead of being silently dropped.
   - Use JQ expressions (`DestinationTableConfigurationList`) or Lambda record transformation to route events dynamically to target Iceberg databases/tables and specify `UniqueKeys` when streaming row-level updates/deletes.
2. **AWS DMS Analytical CDC to S3:**
   - Never point downstream BI queries directly at raw DMS CDC Parquet files — DMS emits append-only change records (`Op = 'I' | 'U' | 'D'`).
   - Always configure DMS S3 endpoint settings with `DataFormat=parquet`, `TimestampColumnName=dms_commit_ts`, `IncludeOpForFullLoad=true`, and `CdcPath`, then compact and apply `I`/`U`/`D` records into a Silver Apache Iceberg table (`authoring-glue-and-emr-spark-jobs`).
3. **Post-Setup Verification:**
   - Verify Firehose `DeliveryToS3.Success` / `DeliveryToIceberg.Success` and DMS `CDCLatencySource` / `CDCLatencyTarget` metrics via the `cloudwatch` MCP server (`get_metric_data`), and validate target table row counts via `querying-data-lake`.
