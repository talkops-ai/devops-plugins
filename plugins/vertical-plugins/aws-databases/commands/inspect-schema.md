---
description: Inspect a PostgreSQL or MySQL database schema read-only
argument-hint: "<cluster identifier> <database>"
---

Inspect the schema of `$ARGUMENTS` without changing it.

1. Use the `postgres` or `mysql` server's `connect_to_database` with the user-specified cluster, preferring RDS Data API or IAM auth and a read-only role.
2. List schemas, tables, columns, indexes, and constraints; sample row counts only if cheap.
3. Summarize the model and flag obvious issues (missing primary keys, unindexed foreign keys, oversized types) using the engine skill's guidance.

This is a read-only workflow: do not create, modify, or delete resources. Both servers run without `--allow_write_query`.
