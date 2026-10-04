---
description: Choose the right AWS database for a workload
argument-hint: "<workload description>"
---

Run the `aws-database` skill's selection flow for `$ARGUMENTS`.

1. Capture data model, access patterns, consistency, scale, latency, and operational constraints.
2. Verify facts (limits, pricing, regional availability) with the knowledge cards and `awsknowledge` instead of memory.
3. Recommend a service with the decision trail and runner-up, then hand off to the bundled service skill for next steps.

This is a read-only workflow: do not create, modify, or delete resources.
