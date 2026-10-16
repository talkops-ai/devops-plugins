---
name: auditing-aws-system-tables
description: >-
  Consolidates administrative system-table analytics exported as Apache Iceberg tables in Amazon S3
  Tables across three AWS-managed table buckets: (1) Redshift SYS_* system-table logs
  (s3tablescatalog/aws-redshift: sys_query_history, sys_connection_log, sys_query_detail), (2) S3
  Metadata and S3 Storage Lens system tables (s3tablescatalog/aws-s3: journal, inventory,
  annotation, default_storage_metrics), and (3) SageMaker Catalog asset metadata snapshots
  (s3tablescatalog/aws-sagemaker-catalog: asset_metadata.asset). Do NOT use for querying customer
  business data in Redshift (use redshift-guide) or querying analytical data lake tables in Athena
  (use querying-data-lake).
version: 1
---

# Auditing AWS System Tables in Amazon S3 Tables (`aws-redshift`, `aws-s3`, `aws-sagemaker-catalog`)

Use this skill ONLY when configuring, enabling, or querying **AWS-managed administrative system tables** exported in Apache Iceberg format into Amazon S3 Tables (`aws-redshift`, `aws-s3`, or `aws-sagemaker-catalog`).

> **Strict Routing Boundary:**
> - **Do NOT** use this skill when a user asks to query customer business data in Amazon Redshift — route to **`redshift-guide`**.
> - **Do NOT** use this skill when a user asks to query analytical data lake datasets in S3/Athena — route to **`querying-data-lake`**.
> - **Do NOT** use this skill to browse or discover live Glue Data Catalog tables — route to **`exploring-data-catalog`** or **`finding-data-lake-assets`**.

---

## Reference Library (Load On-Demand by System Table Domain)

- **[references/redshift-system-tables.md](references/redshift-system-tables.md)** — Load when enabling, checking status, configuring Lake Formation auto-mount, or querying Redshift `SYS_*` system-table logs (`sys_query_history`, `sys_query_text`, `sys_connection_log`, `sys_query_detail`, `sys_session_history`) in `"s3tablescatalog/aws-redshift"`.
- **[references/s3-metadata-and-storage-lens.md](references/s3-metadata-and-storage-lens.md)** — Load when enabling or querying Amazon S3 Metadata (`journal`, `inventory`, `annotation` tables in namespace `b_<bucket>`) or S3 Storage Lens metrics (`default_storage_metrics`, `default_activity_metrics`, `bucket_property_metrics` in namespace `lens_<config-id>_exp`) in `"s3tablescatalog/aws-s3"`.
- **[references/sagemaker-catalog-system-tables.md](references/sagemaker-catalog-system-tables.md)** — Load when enabling DataZone/SageMaker Catalog asset export (`put-data-export-configuration`) or running SQL governance, ownership, and time-travel queries on `"s3tablescatalog/aws-sagemaker-catalog"."asset_metadata"."asset"`.

---

## Step 1: Classify the System Table Domain

| User Intent | Target AWS-Managed S3 Table Bucket | Catalog & Namespace Pattern | Reference to Load |
|---|---|---|---|
| Audit historical Redshift queries, queue times, or failed logins off-cluster; enable `s3table` log publishing on Redshift Provisioned or Serverless | `aws-redshift` | `"s3tablescatalog/aws-redshift"."<S3TableNamespace>"."sys_*"` | [references/redshift-system-tables.md](references/redshift-system-tables.md) |
| Count objects at scale, audit who uploaded/deleted S3 objects (`requester`, `source_ip_address`), query object tags/annotations, or analyze Storage Lens metrics | `aws-s3` | `"s3tablescatalog/aws-s3"."b_<bucket>"."journal\|inventory\|annotation"` or `"lens_<id>_exp"` | [references/s3-metadata-and-storage-lens.md](references/s3-metadata-and-storage-lens.md) |
| Run SQL over SageMaker Catalog / DataZone asset inventory, find assets missing business descriptions/owners, or compare catalog snapshots over time | `aws-sagemaker-catalog` | `"s3tablescatalog/aws-sagemaker-catalog"."asset_metadata"."asset"` | [references/sagemaker-catalog-system-tables.md](references/sagemaker-catalog-system-tables.md) |

---

## Universal Constraints Across All AWS System Tables

1. **Read-Only Managed Iceberg Tables:** All tables in `aws-redshift`, `aws-s3`, and `aws-sagemaker-catalog` are AWS-managed and strictly read-only (`SELECT` only — never attempt `INSERT`, `UPDATE`, or `DELETE`).
2. **Verify S3 Tables Federated Catalog Registration First:**
   ```bash
   aws glue get-databases --region <REGION> --catalog-id "<ACCOUNT>:s3tablescatalog/<aws-redshift|aws-s3|aws-sagemaker-catalog>"
   ```
   If `EntityNotFoundException` or `CATALOG_NOT_FOUND` is returned, the S3 Tables Glue/Lake Formation integration must be enabled first.
3. **Mandatory Athena Workgroup Result Encryption:**
   System tables contain sensitive operational telemetry (`query_text` with potential literal credentials, `requester` ARNs, `source_ip_address`, `remote_host`, internal asset ownership). Always verify the Athena workgroup enforces `SSE_KMS` encryption (`EnforceWorkGroupConfiguration=true`) before executing queries.
4. **Domain-Specific Query Rules:**
   - **Redshift `SYS_*` tables:** Always resolve `S3TableNamespace` dynamically via `redshift:DescribeLoggingStatus` (Provisioned) or `redshift-serverless:GetNamespace` (Serverless) — never hand-construct it. Duration columns (`elapsed_time`, `queue_time`, `execution_time`) are in **microseconds** (divide by `1000000.0` for seconds).
   - **S3 Metadata `b_<bucket>` namespaces:** Dots (`.`) in bucket names are converted to underscores (`_`) in the namespace (`my.bucket` $\rightarrow$ `b_my_bucket`).
   - **SageMaker Catalog `asset_metadata.asset`:** Always include a `WHERE DATE(snapshot_time) = CURRENT_DATE` (or specific snapshot date) predicate to avoid scanning every historical daily snapshot and returning duplicate rows per asset.
