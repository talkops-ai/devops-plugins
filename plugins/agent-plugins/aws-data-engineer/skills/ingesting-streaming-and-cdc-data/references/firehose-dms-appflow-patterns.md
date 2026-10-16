# Amazon Data Firehose (Iceberg & Parquet), AWS DMS CDC, DynamoDB Streams & AppFlow Reference

Use this reference when configuring continuous streaming ingestion or analytical CDC replication pipelines.

---

## 1. Amazon Data Firehose Direct Delivery to Apache Iceberg Tables

Firehose natively commits streaming records into Apache Iceberg tables tracked in the AWS Glue Data Catalog or Amazon S3 Tables (`s3tablescatalog`), including row-level `INSERT`, `UPDATE`, and `DELETE` operations.

```bash
aws firehose create-delivery-stream \
  --region <REGION> \
  --delivery-stream-name <STREAM_NAME> \
  --delivery-stream-type DirectPut \
  --iceberg-destination-configuration '{
    "RoleARN": "arn:aws:iam::<ACCOUNT>:role/<FIREHOSE_ICEBERG_ROLE>",
    "CatalogConfiguration": {
      "CatalogARN": "arn:aws:glue:<REGION>:<ACCOUNT>:catalog"
    },
    "DestinationTableConfigurationList": [
      {
        "DestinationDatabaseName": "<GLUE_DATABASE>",
        "DestinationTableName": "<ICEBERG_TABLE>",
        "UniqueKeys": ["order_id"],
        "S3ErrorOutputPrefix": "firehose-errors/orders/"
      }
    ],
    "BufferingHints": {
      "SizeInMBs": 128,
      "IntervalInSeconds": 60
    },
    "RetryOptions": {
      "DurationInSeconds": 300
    },
    "S3BackupMode": "FailedDataOnly",
    "S3Configuration": {
      "RoleARN": "arn:aws:iam::<ACCOUNT>:role/<FIREHOSE_ICEBERG_ROLE>",
      "BucketARN": "arn:aws:s3:::<DLQ_BACKUP_BUCKET>",
      "Prefix": "firehose-dlq/",
      "CompressionFormat": "GZIP"
    },
    "CloudWatchLoggingOptions": {
      "Enabled": true,
      "LogGroupName": "/aws/kinesisfirehose/<STREAM_NAME>",
      "LogStreamName": "IcebergDelivery"
    }
  }'
```

### Required IAM Permissions for the Firehose Iceberg Role
- `glue:GetTable`, `glue:GetDatabase`, `glue:UpdateTable` on the target catalog/database/table.
- `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on both the Iceberg warehouse bucket and the DLQ backup bucket (or `s3tables:PutTableData`, `s3tables:GetTableData`, `s3tables:GetTableMetadataLocation` for S3 Tables).
- `lakeformation:GetDataAccess` (when Lake Formation governs the target Iceberg table).
- `kms:GenerateDataKey`, `kms:Decrypt` on the bucket KMS CMK.

---

## 2. AWS DMS Analytical CDC to Amazon S3 (Parquet Bronze Landing)

When replicating ongoing changes from PostgreSQL, MySQL, Oracle, or SQL Server into an S3 Bronze zone for Iceberg compaction:

### 2.1 S3 Target Endpoint Extra Connection Attributes / `S3Settings`
```json
{
  "ServiceAccessRoleArn": "arn:aws:iam::<ACCOUNT>:role/<DMS_S3_TARGET_ROLE>",
  "BucketName": "<BRONZE_CDC_BUCKET>",
  "BucketFolder": "dms-cdc/sales_db",
  "DataFormat": "parquet",
  "ParquetVersion": "parquet-2-0",
  "CompressionType": "GZIP",
  "EncryptionMode": "SSE_KMS",
  "ServerSideEncryptionKmsKeyId": "arn:aws:kms:<REGION>:<ACCOUNT>:key/<KMS_KEY_ID>",
  "TimestampColumnName": "dms_commit_ts",
  "ParquetTimestampInMillisecond": true,
  "IncludeOpForFullLoad": true,
  "CdcInsertsAndUpdates": true,
  "PreserveTransactions": false,
  "DatePartitionEnabled": true,
  "DatePartitionSequence": "YYYYMMDD",
  "DatePartitionDelimiter": "SLASH",
  "MaxFileSize": 131072
}
```

### 2.2 Applying DMS CDC (`Op = 'I' | 'U' | 'D'`) into Silver Iceberg via Spark SQL
```sql
WITH ranked_cdc AS (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY order_id
           ORDER BY dms_commit_ts DESC
         ) AS _rn
  FROM bronze_dms_orders_cdc
  WHERE partition_date >= current_date - INTERVAL 1 DAY
)
MERGE INTO silver_db.orders AS target
USING (SELECT * FROM ranked_cdc WHERE _rn = 1) AS source
ON target.order_id = source.order_id
WHEN MATCHED AND source.Op = 'D' THEN DELETE
WHEN MATCHED AND source.Op IN ('U', 'I') THEN UPDATE SET *
WHEN NOT MATCHED AND source.Op != 'D' THEN INSERT *;
```

---

## 3. Amazon DynamoDB Streams & Amazon AppFlow SaaS Ingestion

### 3.1 DynamoDB Continuous Analytical Streaming
Instead of polling DynamoDB with full scans, enable **Kinesis Data Streams for DynamoDB**:
```bash
aws dynamodb enable-kinesis-streaming-destination \
  --region <REGION> \
  --table-name <DDB_TABLE_NAME> \
  --stream-arn arn:aws:kinesis:<REGION>:<ACCOUNT>:stream/<KINESIS_STREAM_NAME> \
  --enable-kinesis-streaming-configuration ApproximateCreationDateTimePrecision=MICROSECOND
```
Connect an Amazon Data Firehose delivery stream to `<KINESIS_STREAM_NAME>` to convert DynamoDB JSON change items into partitioned Parquet/Iceberg in S3.

### 3.2 Amazon AppFlow SaaS Ingestion (Salesforce, ServiceNow, SAP, Zendesk)
Configure AppFlow (`appflow:CreateFlow`) with:
- `DestinationFlowConfigList` targeting `S3` with `FileType = "PARQUET"` and `PrefixFormat = "DAY"`.
- `MetadataCatalogConfig.GlueDataCatalog`: specify `roleArn`, `databaseName`, and `tablePrefix` so AppFlow automatically registers and updates partitions in the AWS Glue Data Catalog after every flow execution.
- Always store SaaS OAuth/API credentials in AWS Secrets Manager via an AppFlow `ConnectorProfile` encrypted with a customer-managed KMS key.
