---
description: Ingest data from a source into the data lake
argument-hint: "<source> <target table>"
---

Ingest `$ARGUMENTS` into the lake.

1. Load `connecting-to-data-source` to create or reuse a Glue connection (Secrets Manager or IAM auth, VPC settings).
2. Load `ingesting-into-data-lake` to plan a one-time or recurring job into S3 Tables (default) or Iceberg, including schema mapping and partitioning.
3. Present the plan and cost estimate; run the job only after approval and verify row counts afterward.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
