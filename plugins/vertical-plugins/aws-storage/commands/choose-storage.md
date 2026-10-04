---
description: Pick the right AWS storage service for a workload
argument-hint: "<workload description>"
---

Recommend storage for `$ARGUMENTS` using the `aws-storage` skill.

1. Clarify access pattern (object, block, file, shared POSIX), latency, throughput, durability, and sharing needs.
2. Compare the best two options (e.g. S3 vs S3 Files vs EFS vs FSx vs EBS) with cost drivers.
3. Give a recommendation with configuration defaults (storage class/tier, encryption, backup, lifecycle).

This is a read-only workflow: do not create, modify, or delete resources.
