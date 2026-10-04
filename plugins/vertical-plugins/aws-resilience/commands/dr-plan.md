---
description: Plan multi-Region disaster recovery and failover
argument-hint: "<application> <primary and recovery regions>"
---

Plan DR for `$ARGUMENTS`.

1. Load `aws-resilience-lifecycle` to set RTO/RPO and pick the strategy (backup/restore, pilot light, warm standby, active-active).
2. Load `arc-region-switch` (and `recovery-controller-setup` if routing controls are needed) to design the failover plan and its execution blocks.
3. Return the architecture, data replication approach, runbook, and a test schedule.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
