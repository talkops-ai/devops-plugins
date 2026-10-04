---
description: Design a Fault Injection Service experiment
argument-hint: "<hypothesis and target>"
---

Design an AWS FIS experiment for `$ARGUMENTS` with the `aws-fault-injection-service` skill.

1. State the steady-state hypothesis and the metrics that measure it.
2. Choose actions and targets (scoped by tags), the experiment role, and mandatory stop conditions (CloudWatch alarms).
3. Produce the experiment template and a run plan, starting in a non-production environment.

Never start an experiment without explicit approval for the target environment.
