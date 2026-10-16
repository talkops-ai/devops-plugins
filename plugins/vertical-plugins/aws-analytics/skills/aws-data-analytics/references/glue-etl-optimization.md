# AWS Glue 5.1+, Zero-ETL & EMR Serverless Optimization Reference

## 1. ETL Engine Selection Matrix

| Workload Profile | Recommended Service | Architectural Rationale |
|---|---|---|
| **Operational DB $\rightarrow$ Redshift / S3 Tables Replication** | **AWS Zero-ETL** | Zero custom code, zero DPU compute charges for standard replication, automatic schema change propagation. |
| **Lightweight Python File Processing (<10 GB, single node)** | **AWS Glue Python Shell** or **AWS Lambda** | Uses `0.0625` or `1` DPU instead of spinning up a multi-node Spark cluster (minimum 2 DPUs). |
| **Batch Spark ETL (<50 DPUs, Glue Catalog native)** | **AWS Glue 5.1+ Spark (Auto Scaling + Flex Execution)** | Enables ` --enable-auto-scaling=true`; use `ExecutionClass: FLEX` for non-urgent batch jobs to save **~34%** per DPU-hour. |
| **Large-Scale Spark (>50 DPUs, Graviton, custom Docker images)** | **Amazon EMR Serverless (Graviton3/4 `arm64`)** | Fine-grained vCPU + Memory decoupled sizing, Graviton cost/performance advantage, sub-second pre-initialized worker pools. |

## 2. Glue Spark Performance & FinOps Rules
1. **Always Enable Glue Auto Scaling**: Set `--enable-auto-scaling = true` so Glue dynamically scales workers down during I/O waits and scales up only for shuffle/join stages.
2. **Prevent Small-File Explosion**: Coalesce or use `groupFiles: inPartition` (`groupSize: 134217728`) when reading millions of small S3 objects, and write directly to Apache Iceberg (`S3 Tables`) rather than raw Hive-style Parquet folders.
3. **Enforce Glue Data Quality (DQDL) in the Pipeline**:
   ```text
   Rules = [
     RowCount > 0,
     IsComplete "transaction_id",
     IsUnique "transaction_id",
     ColumnValues "amount" >= 0,
     DataFreshness "event_timestamp" <= 2 hours
   ]
   ```
   Configure DQDL actions to publish CloudWatch metrics and halt downstream Gold table promotion when critical completeness or uniqueness thresholds fail.
