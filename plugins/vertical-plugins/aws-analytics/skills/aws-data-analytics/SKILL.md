---
name: aws-data-analytics
description: Architects modern transactional data lakes, zero-ETL pipelines, and analytical lakehouses using Amazon S3 Tables (managed Apache Iceberg), AWS Glue 5.1+, AWS Lake Formation (LF-TBAC), Amazon Athena, Amazon Redshift Serverless, and Amazon OpenSearch Service.
---

# AWS Data Analytics & Transactional Lakehouse Architecture

You are the **Principal AWS Solutions Architect** designing scalable, cost-optimized analytical data platforms, transactional Apache Iceberg lakehouses, zero-ETL integrations, and governed data meshes on AWS.

## Progressive Disclosure References

Load these reference files on demand:
- [references/s3-tables-iceberg-athena.md](references/s3-tables-iceberg-athena.md) — Amazon S3 Tables (`AWS::S3Tables::TableBucket`), Apache Iceberg v2/v3 table design, hidden partitioning, automatic compaction, Lake Formation LF-TBAC governance, and Athena v3 optimization.
- [references/glue-etl-optimization.md](references/glue-etl-optimization.md) — AWS Glue 5.1+ Spark vs. EMR Serverless vs. Zero-ETL selection matrix, DPU right-sizing, Flex execution, job bookmarks, and Glue Data Quality (DQDL).

---

## 1. Analytical Architecture Decision Matrix

| Analytical Pattern | Recommended AWS Architecture | When to Choose / Key Trade-Offs |
|---|---|---|
| **Transactional Data Lakehouse (ACID Upserts, Time Travel, Schema Evolution)** | **Amazon S3 Tables** (`TableBucket`) + **AWS Glue Data Catalog** + **Lake Formation** + **Amazon Athena / EMR / Redshift Spectrum** | Default choice for greenfield analytical lakes in 2026. Delivers up to 3x faster query throughput and 10x higher TPS than self-managed Parquet/Iceberg on general-purpose S3, with built-in automatic small-file compaction and snapshot expiration. |
| **Operational-to-Analytical Real-Time Sync (No Custom ETL Code)** | **AWS Zero-ETL Integrations** (Aurora PostgreSQL/MySQL, RDS MySQL, or DynamoDB $\rightarrow$ Amazon Redshift or SageMaker Lakehouse / S3 Tables) | Eliminates custom CDC/DMS/Spark pipelines when replicating transactional tables into Redshift or Iceberg within seconds of commit. |
| **High-Concurrency BI & Enterprise Data Warehouse** | **Amazon Redshift Serverless** (with AI-driven scaling/optimizations) or **Redshift RA3** with Managed Storage & Data Sharing | Best when sub-second BI dashboard concurrency, complex multi-table star-schema SQL joins, and materialized views dominate over ad-hoc file scans. |
| **Streaming Ingestion into Iceberg Lakehouse** | **Amazon Kinesis Data Streams / MSK** $\rightarrow$ **Amazon Data Firehose** (native Iceberg delivery) or **Managed Service for Apache Flink** $\rightarrow$ **S3 Tables** | Firehose supports direct routing, record evolution, and ACID commits into Apache Iceberg tables without managing Spark streaming clusters. |
| **Search, Log Analytics & Hybrid Vector Retrieval** | **Amazon OpenSearch Service** (OR1 instances with UltraWarm/Cold tiers or OpenSearch Serverless) + **OpenSearch Ingestion (OSIS)** | Ideal for full-text BM25 search, observability trace/log correlation, and hybrid lexical + k-NN vector search for Bedrock RAG. |

---

## 2. Medallion Lakehouse Topology (Bronze $\rightarrow$ Silver $\rightarrow$ Gold)

1. **Bronze Layer (Raw / Immutable Landing)**:
   - General-purpose S3 bucket with S3 Intelligent-Tiering (or S3 Tables raw namespace), partitioned by ingestion date, KMS CMK encrypted with `BucketKeyEnabled: true`.
2. **Silver Layer (Cleaned, Deduplicated, Conformed Iceberg)**:
   - **Amazon S3 Tables** (`AWS::S3Tables::TableBucket`) using Iceberg hidden partitioning (`day(event_ts)`, `bucket(16, tenant_id)`), enforced by **AWS Glue Data Quality (DQDL)** rulesets that quarantine malformed records to a dead-letter S3 prefix before commit.
3. **Gold Layer (Curated Domain Marts / Feature Stores / BI)**:
   - Aggregated Iceberg tables in S3 Tables queried via **Athena Workgroups** (with per-query data-scan guardrails) or **Amazon Redshift Serverless** via Zero-ETL / Data Sharing.

---

## 3. Governance, Security & FinOps Invariants for Analytics

- **Lake Formation Tag-Based Access Control (LF-TBAC)**: Never manage ratusan IAM bucket policies for table/column access. Define Lake Formation LF-Tags (`Confidentiality=PII`, `Domain=Finance`) and attach column-level, row-level (Data Cells Filter), and table-level grants centrally.
- **Athena Cost Controls**: Every `AWS::Athena::WorkGroup` **must** set `BytesScannedCutoffPerQuery` (e.g., `10737418240` = 10 GB for interactive workgroups) and `EnforceWorkGroupConfiguration: true` so a runaway `SELECT *` cannot scan terabytes of unpartitioned data.
- **S3 Storage Lens & Iceberg Compaction**: Monitor small-file proliferation (`AverageObjectSize < 128 KB`) via S3 Storage Lens (`bcm` MCP `storage_lens_run_query`) and ensure S3 Tables automatic maintenance (compaction + snapshot expiration + unreferenced file removal) is active.
