---
description: Run an evidence-backed Well-Architected review
argument-hint: "<workload or IaC path> [pillar]"
---

Run the `aws-well-architected-review` skill on `$ARGUMENTS` (all six pillars unless one is named).

1. Gather evidence from IaC and the live account (read-only) rather than assumptions.
2. Use `wa-security` for security-service and encryption checks and `awsknowledge` for current best practices.
3. Return high/medium risks per pillar with evidence and prioritized improvements.

This is a read-only workflow: do not create, modify, or delete resources.
