---
name: governing-and-securing-data-lake
description: >-
  Configures and troubleshoots AWS Lake Formation fine-grained access control (database, table,
  column, and row-level Data Cell Filters, LF-Tag-Based Access Control LF-TBAC, and
  IAMAllowedPrincipals hybrid-mode resolution), cross-account RAM catalog sharing, KMS encryption for
  S3/S3 Tables/Glue/Athena/Redshift, Secrets Manager credential rotation for Glue connections,
  Amazon Macie PII discovery, and VPC endpoint/self-referencing security groups for data engines.
version: 1
---

# Governing & Securing the AWS Data Lake (Lake Formation, IAM, KMS, VPC, Macie)

Use this skill when configuring or troubleshooting **AWS Lake Formation permissions**, resolving `AccessDeniedException` / `Insufficient Lake Formation permission(s)` errors on Athena/Glue/Redshift/S3 Tables, implementing **Column-Level and Row-Level Data Cell Filters**, configuring **LF-Tag-Based Access Control (LF-TBAC)**, securing Glue/Redshift VPC connectivity, or scanning S3 data lakes for PII with **Amazon Macie**.

## Reference Library (Load On-Demand)

- **[references/lake-formation-and-vpc-governance.md](references/lake-formation-and-vpc-governance.md)** — Load for exact AWS CLI commands and JSON payloads for Lake Formation hybrid-mode (`IAMAllowedPrincipals`) diagnosis and revocation, LF-TBAC tag creation and grants, Row/Column Data Cell Filters, cross-account AWS RAM catalog sharing, Glue self-referencing Security Group + S3 Gateway Endpoint rules, and Glue Data Catalog / Athena KMS encryption.

---

## Deterministic Lake Formation & Data Security Workflow

1. **Diagnose `AccessDenied` / `Insufficient Lake Formation permission(s)` First:**
   - **Coarse-grained IAM + Fine-grained Lake Formation Dual Check:** For any principal querying a Lake Formation-governed table via Athena, Glue, or Redshift Spectrum, **both** coarse-grained IAM permissions (`glue:GetDatabase`, `glue:GetTable`, `lakeformation:GetDataAccess`) **and** explicit Lake Formation `SELECT` / `DESCRIBE` grants must succeed!
   - **Check `IAMAllowedPrincipals` Hybrid Mode:**
     - Run `aws lakeformation list-permissions --resource '{"Table": {"DatabaseName": "<DB>", "Name": "<TABLE>"}}'`.
     - If `Principal.DataLakePrincipalIdentifier == "IAM_ALLOWED_PRINCIPALS"` (`Super` permission) is present, the table is in legacy IAM pass-through mode (where Lake Formation fine-grained grants and column/row filters are ignored unless revoked, or conversely, if `IAMAllowedPrincipals` was removed on the database without granting LF permissions to the ETL role, existing Glue jobs fail with `Insufficient Lake Formation permission(s)`).
   - **Check Registered Data Lake Locations:**
     - Run `aws lakeformation list-resources` and `aws lakeformation describe-resource --resource-arn arn:aws:s3:::<BUCKET>`.
     - Verify the data-access IAM role registered with Lake Formation has `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on the S3 path **and** `kms:Decrypt` / `kms:GenerateDataKey` on the bucket's KMS CMK, plus `lakeformation.amazonaws.com` in its trust policy (`sts:AssumeRole`, `sts:SetContext`).
2. **Prefer LF-Tag-Based Access Control (LF-TBAC) Over Per-Table Grants:**
   - Never manage thousands of individual table grants (`GrantPermissions` per table) at scale.
   - Define an LF-Tag ontology (e.g., `domain = [finance, marketing, operations]`, `sensitivity = [public, internal, confidential, pii]`), attach LF-Tags to databases/tables/columns (`AddLFTagsToResource`), and grant permissions on the LF-Tag expression (`GrantPermissions` with `LFTagPolicy`).
3. **Enforce Row-Level and Column-Level Security via Data Cell Filters:**
   - Use `lakeformation:CreateDataCellsFilter` to restrict sensitive PII columns (`ssn`, `email`, `credit_card` via `ColumnNames` or `ColumnWildcard.ExcludedColumnNames`) and filter rows by tenant/region (`RowFilter.FilterExpression`, e.g., `country_code = 'US'`), then grant `SELECT` on the `DataCellsFilter` resource.
4. **Enforce Encryption & Network Isolation Across the Data Stack:**
   - Encrypt the **Glue Data Catalog** (`glue:PutDataCatalogEncryptionSettings` with `SSE-KMS` for metadata and connection passwords), **Glue Security Configurations** (S3 + CloudWatch Logs + Job Bookmarks KMS encryption), **Athena Workgroups** (`EnforceWorkGroupConfiguration=true` with `SSE_KMS`), and **S3 Tables** (`--s3-table-kms-key-id`).
   - Ensure Glue JDBC/VPC connections have a **self-referencing Security Group inbound rule** (allowing all TCP ports `0–65535` from its own Security Group ID `sg-xxxx`) and a **VPC Gateway Endpoint for S3** (`com.amazonaws.<region>.s3`) in the private subnet route table.
