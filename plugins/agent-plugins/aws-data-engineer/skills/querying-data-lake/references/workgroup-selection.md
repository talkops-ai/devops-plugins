# Workgroup Selection

Always list workgroups first before executing any query.

## Detect Execution Context

Before selecting a workgroup, determine the current IAM identity:

```bash
aws sts get-caller-identity --query Arn --output text
```

The ARN pattern reveals the execution context:

| ARN Pattern | Context | Workgroup Strategy |
|---|---|---|
| `arn:aws:sts::*:assumed-role/AmazonDataZone-<project-id>-<suffix>/<session>` | SageMaker Unified Studio project role | Use the project-scoped workgroup (see below) |
| `arn:aws:sts::*:assumed-role/SageMakerUnifiedStudio-<project-id>-<suffix>/<session>` | SageMaker Unified Studio project role | Use the project-scoped workgroup (see below) |
| `arn:aws:sts::*:assumed-role/AmazonSageMaker-ExecutionRole-*` | SageMaker notebook/studio role | Prefer `sagemaker-studio-workgroup-*` |
| Anything else | Standard IAM user/role | Follow general priority order |

## SageMaker Project Role Selection

When running as a SageMaker project role (`AmazonDataZone-*` or `SageMakerUnifiedStudio-*`):

1. List all workgroups the role can access:

   ```bash
   aws athena list-work-groups --query 'WorkGroups[].Name' --output json
   ```

2. Extract the project ID from the role ARN. Split the role name on `-`.
   The first segment is the prefix (e.g., `AmazonDataZone`), the second
   segment is the project ID (e.g., `abc123def`), and subsequent segments
   form the suffix (e.g., `DataLakeAccess`). Take the second segment.
   The project ID is an **alphanumeric string (no hyphens)**.
   Known suffixes that follow the project ID: `DataLakeAccess`, `SparkAccess`,
   `QueryAccess`, `IngestionAccess`. Example:

   ```
   arn:aws:sts::123456789012:assumed-role/AmazonDataZone-abc123def-DataLakeAccess/session
                                                         ^^^^^^^^^
                                                         project ID = abc123def
   ```

3. Match the workgroup to the project. Project workgroups follow the pattern
   `sagemaker-studio-workgroup-<project-id>` or contain the project ID.
4. If exactly one `sagemaker-studio-workgroup-*` exists, verify its suffix
   contains the project ID extracted in step 2. If it matches, use it.
   If it does not match, fall through to step 6.
5. If multiple exist, pick the one whose suffix matches the project ID
   extracted from the role ARN. Optionally check environment variables
   `SAGEMAKER_PROJECT_ID` or `SAGEMAKER_PROJECT_NAME` if the ARN extraction
   is ambiguous.
6. If no `sagemaker-studio-workgroup-*` exists, **do not fall back** to other
   workgroups. Inform the user that no project-scoped workgroup was found and
   ask them to verify their project configuration or IAM permissions.

Project roles typically have IAM permissions scoped to their own workgroup.
Attempting to use `primary` or another project's workgroup will fail with
AccessDeniedException. Do not retry with `primary` in this context.

## General Priority Order (Non-Project Roles)

1. `sagemaker-studio-workgroup-*` workgroups -- most reliable, always have output locations configured
2. Workgroups with explicitly configured output locations
3. `primary` workgroup (use with caution, may lack output location)

## Error Recovery

| Error | Context | Action |
|---|---|---|
| No output location | Any | Retry with the next workgroup in priority order |
| AccessDeniedException on workgroup | Project role | Do not retry with other workgroups. Inform the user their project role lacks access. |
| AccessDeniedException on workgroup | Standard role | Retry with the next workgroup in priority order |
| No workgroups found | Any | Ask the user to configure a workgroup or check IAM permissions |

## Anti-patterns

- Never default to `primary` workgroup without checking others first
- Never hardcode a workgroup name across sessions
- Never retry with `primary` when running as a SageMaker project role -- it will fail with AccessDeniedException

## Workgroup Cost Controls, Partition Pruning, Partition Projection & Federated Queries

### 1. Athena Scan & Join Optimization Rules
- **Direct Partition Predicates (Preserve Partition Pruning)**: Always filter directly on partition columns (e.g., `WHERE event_date >= '2026-03-01'` or `WHERE year = '2026' AND month = '03'`). Never wrap partition columns in functions (`WHERE DATE_PARSE(dt, '%Y-%m-%d') = ...` or `WHERE SUBSTR(dt, 1, 7) = '2026-03'`), which disables partition pruning and triggers a full table scan (`$5.00/TB`).
- **Columnar Projection**: Never run `SELECT *` on wide Parquet/ORC/Iceberg tables; project only required columns so Athena reads only those column chunks from S3.
- **Join Ordering**: Place the **largest table on the left** (`FROM large_fact_table f JOIN small_dimension_table d ON ...`) so Athena's distributed engine broadcasts the smaller right-hand build side across workers.

### 2. Glue Partition Projection (`projection.enabled = true`)
For high-partition tables (thousands of daily/hourly/region partitions), enable **Glue Partition Projection** in `TBLPROPERTIES` so Athena calculates partition S3 paths mathematically in memory instead of calling `glue:GetPartitions` or running `MSCK REPAIR TABLE`:

```sql
ALTER TABLE prod_lake.clickstream_events SET TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.dt.type' = 'date',
  'projection.dt.range' = '2024-01-01,NOW',
  'projection.dt.format' = 'yyyy-MM-dd',
  'projection.dt.interval' = '1',
  'projection.dt.interval.unit' = 'DAYS',
  'storage.location.template' = 's3://my-lake-bucket/clickstream/dt=${dt}/'
);
```

### 3. Workgroup Cost Governance & Query Result Reuse
- **Per-Query Scan Cap (`BytesScannedCutoffPerQuery`)**: Configure a hard byte-scan ceiling on the Athena Workgroup (e.g., `107374182400` = `100 GiB`) so runaway unpartitioned queries are aborted automatically before incurring large scan charges.
- **Enforce Workgroup Configuration (`EnforceWorkGroupConfiguration=true`)**: Prevent client callers from overriding workgroup S3 output locations, KMS encryption settings, or scan limits.
- **Athena Query Result Reuse (`ResultReuseByAgeConfiguration`)**: Enable result caching (`Enabled=true`, `MaxAgeInMinutes=60`) on repeated dashboard queries in Athena Engine v3 so identical scans against unchanged data return at `$0` scan cost.

### 4. Athena Federated Query (`aws-athena-federated-query-*`)
- To join S3 Data Lake tables with operational databases (Aurora PostgreSQL, RDS, DynamoDB, Redshift, OpenSearch), deploy the pre-built **Athena Data Source Connector** (`aws-athena-federated-query-*` Lambda via SAR/CDK), register the Lambda ARN as an Athena Data Catalog (`Type=LAMBDA`), and configure an encrypted **S3 `SpillBucket`** (`SPILL_BUCKET` + `KMS_KEY_ID`) for payloads exceeding the 6 MB Lambda synchronous response limit.

