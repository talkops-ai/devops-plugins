---
description: Diagnose a failed Spark job on EMR, Glue, or SageMaker notebooks
argument-hint: "<job run ID or application ID>"
---

Find the root cause of the failed Spark application `$ARGUMENTS`.

1. Use the `spark-troubleshooting` server to analyze the run (driver/executor logs, stages, errors).
2. Cross-check with the `dataprocessing` server for job configuration (workers, memory, Spark properties, Glue version).
3. Return root cause, evidence, and the configuration or code change; for version-related failures, suggest the `spark-upgrade` server.

This is a read-only workflow: do not create, modify, or delete resources.
