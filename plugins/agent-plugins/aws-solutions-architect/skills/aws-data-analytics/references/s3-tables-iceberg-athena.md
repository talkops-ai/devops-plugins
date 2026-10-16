# Amazon S3 Tables (Apache Iceberg) & Athena Optimization Reference

## 1. Amazon S3 Tables (`AWS::S3Tables::TableBucket`) Architecture

Amazon S3 Tables provides purpose-built storage for Apache Iceberg tables with native AWS Glue Data Catalog and Lake Formation integration (`s3tablescatalog`).

### CloudFormation / CDK Blueprint (`AWS::S3Tables::TableBucket`)
```yaml
Resources:
  AnalyticsTableBucket:
    Type: AWS::S3Tables::TableBucket
    Properties:
      TableBucketName: !Sub "${Environment}-${WorkloadName}-lakehouse"
      EncryptionConfiguration:
        SseAlgorithm: aws:kms
        KmsKeyArn: !GetAtt LakehouseKmsKey.Arn
      UnreferencedFileRemoval:
        Status: Enabled
        UnreferencedDays: 3
        NoncurrentDays: 7
```

## 2. Apache Iceberg Partitioning & Compaction Best Practices
- **Use Hidden Partitioning**: Avoid exposing physical partition columns (`year`, `month`, `day`) to analysts. Define Iceberg partition transforms (` days(event_timestamp)`, `bucket(32, customer_id)`, `truncate(8, trace_id)`) so Athena and Spark prune files automatically on standard `WHERE event_timestamp >= ...` predicates.
- **Target File Size**: Configure `write.target-file-size-bytes` to `268435456` (256 MB) or `536870912` (512 MB) for analytical scan efficiency.
- **Merge-on-Read (MoR) vs. Copy-on-Write (CoW)**:
  - Use **Copy-on-Write (CoW)** for read-heavy Gold tables with infrequent batch updates.
  - Use **Merge-on-Read (MoR)** with positional deletes for high-frequency CDC/streaming upserts (Silver layer), relying on S3 Tables automatic compaction (`binpack` / `sort` / `z-order`) to merge delete files in the background.

## 3. Amazon Athena v3 Workgroup Cost & Performance Guardrails
```yaml
  GovernedAthenaWorkGroup:
    Type: AWS::Athena::WorkGroup
    Properties:
      Name: !Sub "${Environment}-analytics-wg"
      State: ENABLED
      WorkGroupConfiguration:
        EnforceWorkGroupConfiguration: true
        PublishCloudWatchMetricsEnabled: true
        BytesScannedCutoffPerQuery: 10737418240 # 10 GiB hard cap per query
        EngineVersion:
          SelectedEngineVersion: "Athena engine version 3"
        ResultConfiguration:
          OutputLocation: !Sub "s3://${AthenaResultsBucket}/results/"
          EncryptionConfiguration:
            EncryptionOption: SSE_KMS
            KmsKey: !GetAtt LakehouseKmsKey.Arn
```
