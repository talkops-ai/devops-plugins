# Glue 5.1+ & EMR Serverless PySpark Medallion Templates and Performance Tuning Reference

Use this reference when authoring production PySpark scripts, configuring Apache Iceberg catalogs (`s3tablescatalog` and `glue_catalog`), tuning Spark shuffle/skew/OOM issues, or sizing Glue/EMR workers.

---

## 1. Production Glue 5.1+ PySpark Template (Medallion Bronze $\rightarrow$ Silver Iceberg `MERGE INTO`)

```python
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.window import Window

args = getResolvedOptions(
    sys.argv,
    ["JOB_NAME", "SOURCE_S3_PATH", "TARGET_CATALOG", "TARGET_DATABASE", "TARGET_TABLE"]
)

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# 1. Incremental read from S3 Bronze using Glue Job Bookmarks (transformation_ctx is MANDATORY)
bronze_dyf = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [args["SOURCE_S3_PATH"]], "recurse": True},
    format="json",
    transformation_ctx="bronze_s3_read_ctx",
)

bronze_df = bronze_dyf.toDF()

if not bronze_df.isEmpty():
    # 2. Deduplicate within micro-batch by primary key (order_id) and latest updated_at
    dedup_window = Window.partitionBy("order_id").orderBy(F.col("updated_at").desc())
    silver_df = (
        bronze_df
        .withColumn(" order_ts", F.to_timestamp("updated_at"))
        .withColumn("event_date", F.to_date("order_ts"))
        .withColumn("_rn", F.row_number().over(dedup_window))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )

    silver_df.createOrReplaceTempView("staged_orders")
    full_table = f"`{args['TARGET_CATALOG']}`.`{args['TARGET_DATABASE']}`.`{args['TARGET_TABLE']}`"

    # 3. ACID Upsert into Apache Iceberg (S3 Tables or Glue Catalog)
    spark.sql(f"""
        MERGE INTO {full_table} AS target
        USING staged_orders AS source
        ON target.order_id = source.order_id
           AND target.event_date = source.event_date
        WHEN MATCHED AND source.order_ts >= target.order_ts THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

# 4. Commit Glue Job Bookmark state ONLY after successful Iceberg commit
job.commit()
```

---

## 2. Spark Catalog Configuration for S3 Tables vs. Standard Glue Iceberg

### 2.1 Amazon S3 Tables (`s3tablescatalog`) Spark Configuration
Pass via `--conf` in Glue Job parameters or EMR Serverless `sparkSubmitParameters`:
```text
--conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
--conf spark.sql.catalog.s3tablesbucket=org.apache.iceberg.spark.SparkCatalog
--conf spark.sql.catalog.s3tablesbucket.catalog-impl=software.amazon.s3tables.iceberg.S3TablesCatalog
--conf spark.sql.catalog.s3tablesbucket.warehouse=arn:aws:s3tables:<REGION>:<ACCOUNT>:bucket/<TABLE_BUCKET_NAME>
```

### 2.2 Standard Glue Data Catalog Iceberg (`glue_catalog`) Spark Configuration
```text
--datalake-formats iceberg
--conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
--conf spark.sql.catalog.glue_catalog=org.apache.iceberg.spark.SparkCatalog
--conf spark.sql.catalog.glue_catalog.catalog-impl=org.apache.iceberg.aws.glue.GlueCatalog
--conf spark.sql.catalog.glue_catalog.io-impl=org.apache.iceberg.aws.s3.S3FileIO
--conf spark.sql.catalog.glue_catalog.warehouse=s3://<DATA_LAKE_BUCKET>/warehouse/
```

---

## 3. Diagnosing & Fixing Spark Skew, Shuffle & OOM Failures

| Symptom / Error | Root Cause | Concrete Fix |
|---|---|---|
| `java.lang.OutOfMemoryError: Java heap space` on **Driver** | Calling `.collect()`, `.toPandas()`, broadcasting a table $> 2$ GB, or listing millions of small S3 files on the driver. | Remove `.collect()`/`.toPandas()`; enable Glue `useS3ListImplementation: true` or group small files (`groupFiles: inPartition`, `groupSize: 134217728`); scale worker type to `G.2X`/`G.4X`. |
| `Container killed by YARN/Spark for exceeding memory limits` on **Executor** | High-cardinality `GROUP BY`, `COUNT(DISTINCT)`, or skewed `JOIN` key; off-heap overhead exhausted during Parquet/Iceberg columnar vectorization. | Increase `spark.executor.memoryOverhead` (`>= 20%` of executor memory); enable AQE skew join (`spark.sql.adaptive.skewJoin.enabled=true`); salt hot join keys (`NULL` or default IDs) before joining. |
| Iceberg / Parquet write fails with `OutOfMemoryError: Direct buffer memory` | Writing to a partitioned table without sorting by partition keys first, causing each task to hold open hundreds of concurrent S3 output streams. | Configure Iceberg table property `'write.distribution-mode'='hash'` or append `DISTRIBUTE BY <partition_col> SORT BY <partition_col>, <sort_col>` before writing. |
| 999 of 1000 Spark tasks finish in 10s, last task runs for 2 hours | **Data Skew** on a join or window partition key (often `NULL`, `""`, or a single enterprise tenant ID). | Split `NULL` keys into a separate `UNION ALL` branch (`df.filter(col.isNull())` vs `df.filter(col.isNotNull())`) and set `spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes=64MB`. |

---

## 4. AWS Glue Worker Type & Auto-Scaling Matrix

| Worker Type | vCPU | RAM | Disk | Best Use Case |
|---|---|---|---|---|
| `G.1X` | 4 vCPU | 16 GB | 64 GB | Standard S3-to-S3 and JDBC ingestion jobs without heavy shuffles. |
| `G.2X` | 8 vCPU | 32 GB | 128 GB | Medium transformations, Iceberg `MERGE INTO`, wide joins. |
| `G.4X` / `G.8X` | 16 / 32 vCPU | 64 / 128 GB | 256 / 512 GB | Memory-intensive aggregations, large broadcasts, high-skew joins. |
| `Z.2X` (Ray) | 8 vCPU | 64 GB | 128 GB | Distributed Python / Ray data processing workloads. |

Always enable **Glue Auto Scaling** (`--enable-auto-scaling true`) and CloudWatch continuous logging (`--enable-continuous-cloudwatch-log true`, `--enable-metrics true`, `--enable-observability-metrics true`) so idle executors scale down automatically and `spark-troubleshooting` / `cloudwatch` MCP servers can inspect task metrics.
