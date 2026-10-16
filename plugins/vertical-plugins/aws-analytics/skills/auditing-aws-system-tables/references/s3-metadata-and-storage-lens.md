# S3 Metadata & S3 Storage Lens System Tables (`aws-s3`)

Use this reference when enabling or querying Amazon S3 Metadata (`journal`, `inventory`, `annotation` tables) or S3 Storage Lens metrics (`default_storage_metrics`, `default_activity_metrics`, `bucket_property_metrics`) in the AWS-managed `aws-s3` S3 Table bucket via Amazon Athena.

---

## 1. Check Status & Enable S3 Metadata / Storage Lens

### 1.1 Check Configuration
```bash
# Check S3 Metadata on a bucket
aws s3api get-bucket-metadata-configuration --bucket <BUCKET> --region <REGION>

# Check S3 Storage Lens export
aws s3control get-storage-lens-configuration --account-id <ACCOUNT> --config-id <CONFIG_ID> --region <REGION>
```

### 1.2 Enable S3 Metadata & Storage Lens S3 Tables Export
```bash
# Enable S3 Metadata (Journal + Inventory)
aws s3api create-bucket-metadata-configuration \
  --bucket <BUCKET> \
  --region <REGION> \
  --metadata-configuration '{
    "JournalTableConfiguration": {"RecordExpiration": {"Expiration": "ENABLED", "Days": 90}},
    "InventoryTableConfiguration": {"ConfigurationState": "ENABLED"}
  }'

# Enable S3 Storage Lens S3 Tables Export
aws s3control put-storage-lens-configuration \
  --account-id <ACCOUNT> \
  --config-id <CONFIG_ID> \
  --region <REGION> \
  --storage-lens-configuration '{
    "Id": "<CONFIG_ID>",
    "IsEnabled": true,
    "AccountLevel": {"BucketLevel": {}},
    "DataExport": {"StorageLensTableDestination": {"IsEnabled": true}}
  }'
```

---

## 2. Namespaces & Table Schemas in `"s3tablescatalog/aws-s3"`

1. **S3 Metadata Namespace (`b_<bucket-name>`, where `.` is replaced with `_`):**
   - `journal`: Near real-time event log of `CREATE`, `DELETE`, `UPDATE_METADATA`, and annotation events (`key`, `record_type`, `record_timestamp`, `requester`, `source_ip_address`).
   - `inventory`: Current object state updated within 1 hour (`key`, `size`, `storage_class`, `last_modified_date`, `object_tags`).
   - `annotation`: Object annotations (`object_key`, `name`, `text_value`).
2. **S3 Storage Lens Namespace (`lens_<config-id>_exp`):**
   - `default_storage_metrics`: Daily object count, bytes, storage class breakdown.
   - `default_activity_metrics`: Daily GET/PUT/DELETE request counts.
   - `bucket_property_metrics`: Daily versioning, encryption, and lifecycle posture.

---

## 3. Worked Athena SQL Queries

### 3.1 Audit Recent Object Deletions (`journal`)
```sql
SELECT key, record_type, record_timestamp, requester, source_ip_address
FROM "s3tablescatalog/aws-s3"."b_<bucket>"."journal"
WHERE record_type = 'DELETE'
  AND record_timestamp > current_timestamp - interval '24' hour
ORDER BY record_timestamp DESC
LIMIT 100;
```

### 3.2 Find Objects by Storage Class or Tag (`inventory`)
```sql
SELECT key, size, storage_class, last_modified_date
FROM "s3tablescatalog/aws-s3"."b_<bucket>"."inventory"
WHERE storage_class = 'GLACIER'
  AND object_tags['environment'] = 'staging'
ORDER BY size DESC
LIMIT 50;
```

### 3.3 Query Storage Lens Metrics (`default_storage_metrics`)
```sql
SELECT *
FROM "s3tablescatalog/aws-s3"."lens_<config-id>_exp"."default_storage_metrics"
LIMIT 20;
```
