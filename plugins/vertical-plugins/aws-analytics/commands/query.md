---
description: Run an Athena or Redshift query against the data lake
argument-hint: "<question or SQL>"
---

Answer `$ARGUMENTS` with SQL.

1. Locate the right tables first (`finding-data-lake-assets`), then load `querying-data-lake` for Athena or `redshift-guide` when the data lives in Redshift.
2. Write cost-aware SQL (partition filters, `LIMIT`, column pruning) and state the expected scan before running large queries.
3. Return results with the SQL used and any caveats about data freshness.

This is a read-only workflow: do not create, modify, or delete resources. Only run `SELECT` statements.
