---
description: Check an Amazon MSK cluster's health and configuration
argument-hint: "<cluster name or ARN>"
---

Assess MSK cluster `$ARGUMENTS` with the `managing-amazon-msk` skill.

1. Review broker/Express type and size, storage utilization and auto-scaling, partition and replication settings, authentication (IAM/SASL/TLS), and monitoring level.
2. Check CloudWatch metrics for under-replicated partitions, consumer lag, CPU, and disk.
3. Report risks and recommended changes, noting which ones cause broker restarts.

This is a read-only workflow: do not create, modify, or delete resources.
