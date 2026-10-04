---
description: Debug a failing Amazon MWAA (Airflow) DAG
argument-hint: "<environment> <dag_id>"
---

Debug `$ARGUMENTS` with the `debugging-mwaa-workflow` skill.

1. Pull the failing DAG run and task instance logs, scheduler/worker logs, and environment health.
2. Classify the failure (import error, dependency, permissions, resource limits, upstream data) and identify the root cause.
3. Propose the fix (DAG code, requirements, configuration, IAM) and how to re-run safely.

Do not trigger or clear DAG runs without approval.
