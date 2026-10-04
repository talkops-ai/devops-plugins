---
description: Inventory the Glue Data Catalog and data lake assets
argument-hint: "[database or catalog]"
---

Produce a data catalog inventory for `$ARGUMENTS` (default: the whole account/region) with the `exploring-data-catalog` skill.

1. Enumerate catalogs, databases, tables (incl. S3 Tables and federated catalogs), formats, partitions, and locations using the `dataprocessing` and `s3tables` servers.
2. Flag stale, unpartitioned, or ungoverned tables.
3. Return a summary table plus notable findings.

This is a read-only workflow: do not create, modify, or delete resources.
