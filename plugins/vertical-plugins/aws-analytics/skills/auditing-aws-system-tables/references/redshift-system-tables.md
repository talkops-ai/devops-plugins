# Redshift `SYS_*` System Tables in Amazon S3 Tables (`aws-redshift`)

Use this reference when enabling, configuring Lake Formation/IAM permissions, or querying Amazon Redshift `SYS_*` system tables (`sys_query_history`, `sys_query_text`, `sys_connection_log`, `sys_query_detail`, `sys_session_history`) published to the AWS-managed `aws-redshift` S3 Table bucket.

---

## 1. Check Status & Enable Publishing

### 1.1 Check If Configured
```bash
# Provisioned Cluster
aws redshift describe-logging-status --region <REGION> --cluster-identifier <CLUSTER_ID>

# Serverless Namespace
aws redshift-serverless get-namespace --region <REGION> --namespace-name <NAMESPACE_NAME>
```

| Meaning | Provisioned (`describe-logging-status`) | Serverless (`get-namespace`) |
|---|---|---|
| Destination includes S3 Tables | `LogDestinationType` contains `s3table` | `logDestinationType` contains `s3table` |
| Published `SYS_*` tables | `S3Tables.S3Tables` | `namespace.s3TablePublishStatus.s3Tables` |
| **Exact S3 Tables Namespace (Required)** | `S3Tables.S3TableNamespace` | `namespace.s3TablePublishStatus.s3TableNamespace` |
| Granularity | `S3Tables.S3TableGranularity` (`cluster`\|`account`) | `namespace.s3TablePublishStatus.s3TableGranularity` (`namespace`\|`account`) |
| Last Ingest Time | `S3Tables.LastIngestionTimes` | `namespace.s3TablePublishStatus.lastIngestionTimes` |

> **Critical Rule:** Always read `S3TableNamespace` directly from the API response; never construct it manually.

### 1.2 Enable Publishing (Always Pass Customer-Managed KMS Key)
```bash
# Provisioned Cluster (--log-exports)
aws redshift enable-logging \
  --region <REGION> \
  --cluster-identifier <CLUSTER_ID> \
  --log-destination-type s3table \
  --log-exports all \
  --s3-table-granularity cluster \
  --s3-table-kms-key-id <KMS_KEY_ARN>

# Serverless Namespace (--s3-table-names and --s3-table-action)
aws redshift-serverless update-namespace \
  --region <REGION> \
  --namespace-name <NAMESPACE_NAME> \
  --log-destination-type s3table \
  --s3-table-names all \
  --s3-table-action Enable \
  --s3-table-granularity namespace \
  --s3-table-kms-key-id <KMS_KEY_ARN>
```

---

## 2. KMS Key Policy & Least-Privilege IAM / Lake Formation Setup

### 2.1 Dual-Principal KMS Key Policy (Publisher + S3 Tables Compaction)
Granting only `systemtables.redshift.amazonaws.com` lets writes succeed while Iceberg compaction silently fails. Both principals are mandatory:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnableRedshiftSystemTableKeyUsage",
      "Effect": "Allow",
      "Principal": { "Service": "systemtables.redshift.amazonaws.com" },
      "Action": ["kms:DescribeKey", "kms:GenerateDataKey", "kms:Decrypt"],
      "Resource": "arn:aws:kms:<REGION>:<ACCOUNT>:key/<KEY_ID>",
      "Condition": { "StringEquals": { "aws:SourceAccount": "<ACCOUNT>" } }
    },
    {
      "Sid": "EnableS3TableMaintenanceKeyUsage",
      "Effect": "Allow",
      "Principal": { "Service": "maintenance.s3tables.amazonaws.com" },
      "Action": ["kms:GenerateDataKey", "kms:Decrypt"],
      "Resource": "arn:aws:kms:<REGION>:<ACCOUNT>:key/<KEY_ID>",
      "Condition": {
        "StringLike": {
          "kms:EncryptionContext:aws:s3:arn": "arn:aws:s3tables:<REGION>:<ACCOUNT>:bucket/aws-redshift/*"
        }
      }
    }
  ]
}
```

### 2.2 Redshift Auto-Mount & Athena Query Permissions
1. **IAM Role Trust Policy (`query_s3_tables`):** Must trust both `redshift.amazonaws.com` (`sts:AssumeRole`) and `lakeformation.amazonaws.com` (`sts:AssumeRole`, `sts:SetContext`, `sts:SetSourceIdentity`, `sts:TagSession`) with `Condition.StringEquals["aws:SourceAccount"] = "<ACCOUNT>"`.
2. **Inline Read-Only Policy:**
   - `s3tables:GetTable*`, `s3tables:GetNamespace`, `s3tables:List*`, `s3tables:GetTableBucket` on `arn:aws:s3tables:<REGION>:<ACCOUNT>:bucket/aws-redshift` and `/*`.
   - `glue:GetDatabase*`, `glue:GetTable*` on `catalog/s3tablescatalog/aws-redshift`, `database/s3tablescatalog/aws-redshift/*`, and `table/s3tablescatalog/aws-redshift/*/*`.
   - `lakeformation:GetDataAccess` on `"Resource": "*"` with `Condition.StringEquals["aws:ResourceAccount"] = "<ACCOUNT>"`.
3. **Lake Formation Registration & ReadOnlyAdmins:**
   ```bash
   aws lakeformation register-resource \
     --region <REGION> \
     --resource-arn "arn:aws:s3tables:<REGION>:<ACCOUNT>:bucket/aws-redshift" \
     --role-arn "arn:aws:iam::<ACCOUNT>:role/query_s3_tables"
   ```
   Add `AWSServiceRoleForRedshift` and `AWSServiceRoleForRedshiftInternal` to `ReadOnlyAdmins` in `lakeformation:PutDataLakeSettings` (preserving existing `DataLakeAdmins`).

---

## 3. Worked SQL Queries (Timing Columns in Microseconds!)

### 3.1 Top 10 Longest-Running Queries in the Last 7 Days (Athena)
```sql
SELECT query_id,
       username,
       database_name,
       query_type,
       round(elapsed_time / 1000000.0, 2) AS elapsed_sec,
       round(queue_time / 1000000.0, 2) AS queue_sec,
       round(execution_time / 1000000.0, 2) AS exec_sec,
       start_time,
       substr(query_text, 1, 120) AS query_preview
FROM "s3tablescatalog/aws-redshift"."<NAMESPACE>"."sys_query_history"
WHERE start_time > current_timestamp - interval '7' day
  AND status = 'success'
ORDER BY elapsed_time DESC
LIMIT 10;
```

### 3.2 Same Query from Redshift Auto-Mounted Catalog
```sql
SELECT query_id,
       username,
       round(elapsed_time / 1000000.0, 2) AS elapsed_sec,
       substring(query_text, 1, 120) AS query_preview
FROM "aws-redshift@s3tablescatalog"."<NAMESPACE>".sys_query_history
WHERE start_time > current_timestamp - interval '7 day'
ORDER BY elapsed_time DESC
LIMIT 10;
```

### 3.3 Failed Authentication Attempts (`sys_connection_log`)
```sql
SELECT user_name,
       remote_host,
       count(*) AS failed_attempts,
       min(record_time) AS first_seen,
       max(record_time) AS last_seen
FROM "s3tablescatalog/aws-redshift"."<NAMESPACE>"."sys_connection_log"
WHERE event = 'authentication failure'
  AND record_time > current_timestamp - interval '30' day
GROUP BY user_name, remote_host
ORDER BY failed_attempts DESC
LIMIT 20;
```

### 3.4 Reassemble Full Query Text (`sys_query_text`)
```sql
SELECT query_id,
       array_join(array_agg(text ORDER BY sequence), '') AS full_query_text
FROM "s3tablescatalog/aws-redshift"."<NAMESPACE>"."sys_query_text"
WHERE query_id = <QUERY_ID>
GROUP BY query_id;
```
