---
description: Export an RDS or Aurora snapshot to S3 for analytics
argument-hint: "<snapshot or DB identifier> <bucket>"
---

Use the `exporting-rds-to-s3` skill to export `$ARGUMENTS` to S3 (Parquet).

1. Confirm the snapshot (or create one), target bucket/prefix, KMS key, and the IAM role the export task assumes.
2. Choose which databases/tables to export and estimate cost.
3. Start the export only after approval, then monitor it and show how to query the result with Athena.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
