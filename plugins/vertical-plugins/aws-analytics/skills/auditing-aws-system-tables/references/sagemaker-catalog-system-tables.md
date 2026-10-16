# SageMaker Catalog Asset Metadata System Tables (`aws-sagemaker-catalog`)

Use this reference when enabling or querying Amazon SageMaker Unified Studio / Amazon DataZone catalog metadata snapshots exported as Apache Iceberg tables in `"s3tablescatalog/aws-sagemaker-catalog"."asset_metadata"."asset"`.

---

## 1. Check Status & Enable Export (Always With KMS CMK)

```bash
# Check export configuration
aws datazone get-data-export-configuration --domain-identifier <DOMAIN_ID> --region <REGION>

# Enable export with KMS encryption (encryption cannot be changed after creation!)
aws datazone put-data-export-configuration \
  --domain-identifier <DOMAIN_ID> \
  --region <REGION> \
  --enable-export \
  --encryption-configuration kmsKeyArn=<KMS_KEY_ARN>,sseAlgorithm=aws:kms
```

Grant Lake Formation `DESCRIBE` and `SELECT` on `"s3tablescatalog/aws-sagemaker-catalog"."asset_metadata"."asset"` to the querying role.

---

## 2. Worked Athena SQL Queries (Always Filter on `snapshot_time`!)

> **Mandatory Rule:** Data is exported once daily partitioned by `snapshot_time`. Always include `WHERE DATE(snapshot_time) = CURRENT_DATE` (or a specific date window) to avoid scanning all historical snapshots and returning duplicate rows per asset.

### 2.1 Current Catalog Asset Inventory by Type
```sql
SELECT resource_type_enum, COUNT(*) AS asset_count
FROM "s3tablescatalog/aws-sagemaker-catalog"."asset_metadata"."asset"
WHERE DATE(snapshot_time) = CURRENT_DATE
GROUP BY resource_type_enum
ORDER BY asset_count DESC;
```

### 2.2 Governance Audit: Find Assets Missing Business Descriptions or Owners
```sql
SELECT asset_name,
       resource_name,
       resource_type_enum,
       extended_metadata['owningEntityId'] AS owner
FROM "s3tablescatalog/aws-sagemaker-catalog"."asset_metadata"."asset"
WHERE DATE(snapshot_time) = CURRENT_DATE
  AND (business_description IS NULL OR extended_metadata['owningEntityId'] IS NULL);
```

### 2.3 Snapshot Time-Travel: Compare Today vs. 7 Days Ago
```sql
SELECT t.asset_id,
       t.resource_name,
       p.business_description AS before_desc,
       t.business_description AS current_desc
FROM "s3tablescatalog/aws-sagemaker-catalog"."asset_metadata"."asset" t
JOIN "s3tablescatalog/aws-sagemaker-catalog"."asset_metadata"."asset" p
  ON t.asset_id = p.asset_id
WHERE DATE(t.snapshot_time) = CURRENT_DATE
  AND DATE(p.snapshot_time) = CURRENT_DATE - INTERVAL '7' DAY
  AND p.business_description IS NULL
  AND t.business_description IS NOT NULL;
```
