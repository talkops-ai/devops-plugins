# AWS Lake Formation Fine-Grained Governance, LF-TBAC, Data Cell Filters & VPC Security Reference

Use this reference when configuring or debugging AWS Lake Formation permissions, Data Cell Filters, LF-Tags, Glue Data Catalog encryption, or Glue/Redshift VPC networking.

---

## 1. Transitioning From `IAMAllowedPrincipals` to Fine-Grained Lake Formation Control

### 1.1 Inspect Current Lake Formation Settings & Table Grants
```bash
# Check default Data Lake Settings and Admins
aws lakeformation get-data-lake-settings --region <REGION>

# List permissions on a specific table
aws lakeformation list-permissions \
  --region <REGION> \
  --resource '{"Table": {"CatalogId": "<ACCOUNT>", "DatabaseName": "<DB_NAME>", "Name": "<TABLE_NAME>"}}'
```

### 1.2 Revoking `IAMAllowedPrincipals` (`Super`) to Enforce Fine-Grained Lake Formation Mode
> **Important:** Before revoking `IAM_ALLOWED_PRINCIPALS` on a production database or table, first grant explicit Lake Formation permissions (`SELECT`, `DESCRIBE`, `ALTER`, `INSERT`, `DELETE`) to the active Glue ETL and Athena/Redshift roles so pipelines do not break!

```bash
# 1. Grant explicit LF permissions to the Glue ETL Role first
aws lakeformation grant-permissions \
  --region <REGION> \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::<ACCOUNT>:role/<GLUE_ETL_ROLE> \
  --resource '{"Table": {"CatalogId": "<ACCOUNT>", "DatabaseName": "<DB_NAME>", "Name": "<TABLE_NAME>"}}' \
  --permissions SELECT DESCRIBE INSERT DELETE ALTER

# 2. Revoke legacy IAM_ALLOWED_PRINCIPALS pass-through
aws lakeformation revoke-permissions \
  --region <REGION> \
  --principal DataLakePrincipalIdentifier=IAM_ALLOWED_PRINCIPALS \
  --resource '{"Table": {"CatalogId": "<ACCOUNT>", "DatabaseName": "<DB_NAME>", "Name": "<TABLE_NAME>"}}' \
  --permissions ALL
```

---

## 2. LF-Tag-Based Access Control (LF-TBAC)

```bash
# 1. Create an LF-Tag key and allowed values
aws lakeformation create-lf-tag \
  --region <REGION> \
  --tag-key sensitivity \
  --tag-values public internal confidential pii

# 2. Assign the LF-Tag to a table or specific columns
aws lakeformation add-lf-tags-to-resource \
  --region <REGION> \
  --resource '{"TableWithColumns": {"CatalogId": "<ACCOUNT>", "DatabaseName": "silver_db", "Name": "customers", "ColumnNames": ["email", "phone", "tax_id"]}}' \
  --lf-tags '[{"TagKey": "sensitivity", "TagValues": ["pii"]}]'

# 3. Grant SELECT on all non-PII columns/tables matching sensitivity=internal or public
aws lakeformation grant-permissions \
  --region <REGION> \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::<ACCOUNT>:role/AnalyticsReaderRole \
  --resource '{
    "LFTagPolicy": {
      "CatalogId": "<ACCOUNT>",
      "ResourceType": "TABLE",
      "Expression": [
        {"TagKey": "sensitivity", "TagValues": ["public", "internal"]}
      ]
    }
  }' \
  --permissions SELECT DESCRIBE
```

---

## 3. Row-Level and Column-Level Security with Data Cell Filters

Create a Data Cell Filter that hides PII columns (`ssn`, `credit_card`) and restricts rows to `region = 'NA'`:

```bash
aws lakeformation create-data-cells-filter \
  --region <REGION> \
  --table-data '{
    "TableCatalogId": "<ACCOUNT>",
    "DatabaseName": "silver_db",
    "TableName": "orders",
    "Name": "na_non_pii_filter",
    "RowFilter": {
      "FilterExpression": "sales_region = '\''NA'\''"
    },
    "ColumnWildcard": {
      "ExcludedColumnNames": ["customer_ssn", "payment_card_token"]
    }
  }'

# Grant SELECT on the Data Cell Filter to the regional analyst role
aws lakeformation grant-permissions \
  --region <REGION> \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::<ACCOUNT>:role/NAAnalystRole \
  --resource '{
    "DataCellsFilter": {
      "TableCatalogId": "<ACCOUNT>",
      "DatabaseName": "silver_db",
      "TableName": "orders",
      "Name": "na_non_pii_filter"
    }
  }' \
  --permissions SELECT
```

---

## 4. Glue VPC Self-Referencing Security Group & KMS Catalog Encryption

### 4.1 Mandatory Self-Referencing Security Group Rule for AWS Glue Connections
AWS Glue Spark drivers and executors communicate inside the customer ENI subnet over all TCP ports. If the Security Group attached to a Glue Connection lacks a **self-referencing inbound TCP rule**, the Glue connection test and ETL job fail with `Check that your connection definition references your JDBC database with correct URL syntax, username, and password` or ENI timeout!

```bash
# Add required self-referencing All-TCP inbound rule to Glue Security Group
aws ec2 authorize-security-group-ingress \
  --region <REGION> \
  --group-id <GLUE_SG_ID> \
  --protocol tcp \
  --port 0-65535 \
  --source-group <GLUE_SG_ID>
```

### 4.2 Encrypting the Glue Data Catalog & Connection Passwords with KMS
```bash
aws glue put-data-catalog-encryption-settings \
  --region <REGION> \
  --data-catalog-encryption-settings '{
    "EncryptionAtRest": {
      "CatalogEncryptionMode": "SSE-KMS",
      "SseAwsKmsKeyId": "arn:aws:kms:<REGION>:<ACCOUNT>:key/<KMS_KEY_ID>"
    },
    "ConnectionPasswordEncryption": {
      "ReturnConnectionPasswordEncrypted": true,
      "AwsKmsKeyId": "arn:aws:kms:<REGION>:<ACCOUNT>:key/<KMS_KEY_ID>"
    }
  }'
```
