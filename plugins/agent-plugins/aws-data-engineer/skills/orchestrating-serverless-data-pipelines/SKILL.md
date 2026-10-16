---
name: orchestrating-serverless-data-pipelines
description: >-
  Designs and deploys event-driven and scheduled serverless data pipelines using AWS Step Functions
  (Glue, EMR Serverless, Athena, and Redshift Data API .sync integrations plus Distributed Map),
  Amazon EventBridge Rules and EventBridge Scheduler, Amazon S3 EventBridge notifications, and AWS
  Glue Workflows/Triggers with retry, quarantine, and dead-letter alerting patterns.
version: 1
---

# Orchestrating Serverless Data Pipelines (Step Functions, EventBridge, Glue Workflows)

Use this skill when designing, authoring, or troubleshooting serverless data pipeline orchestration across **AWS Step Functions**, **Amazon EventBridge (Rules & Scheduler)**, **Amazon S3 Event Notifications**, and **AWS Glue Workflows/Triggers**.

> **When to Use Step Functions vs. Amazon MWAA vs. Glue Workflows:**
> - **AWS Step Functions + EventBridge:** Default for cloud-native serverless AWS data pipelines chaining Glue ETL jobs, Glue Data Quality checks, EMR Serverless runs, Athena queries, and Redshift Data API loads with zero idle cluster cost.
> - **Amazon MWAA (Apache Airflow):** Choose when the team requires Python-native DAGs, complex cross-cloud Airflow providers, or existing Airflow 2.x/3.x ecosystems (`authoring-mwaa-workflow`).
> - **AWS Glue Workflows:** Choose for simple, single-service chains of Glue Crawlers and Glue ETL Jobs triggered on a cron or event.

## Reference Library (Load On-Demand)

- **[references/stepfunctions-eventbridge-etl.md](references/stepfunctions-eventbridge-etl.md)** — Load for production Amazon States Language (ASL) Step Functions definitions (`glue:startJobRun.sync`, `glue:startDataQualityRuleRecommendationRun.sync`, `athena:startQueryExecution.sync`, `redshift-data:executeStatement`, and S3 Distributed Map), EventBridge S3 `Object Created` rules, and EventBridge Scheduler cron templates.

---

## Deterministic Pipeline Orchestration Workflow

1. **Choose the Trigger Mechanism:**
   - **Event-Driven Arrival (S3 $\rightarrow$ EventBridge):** Enable EventBridge notifications on the landing S3 bucket (`aws s3api put-bucket-notification-configuration --bucket <BUCKET> --notification-configuration '{"EventBridgeConfiguration": {}}'`) and match `source: ["aws.s3"]`, `detail-type: ["Object Created"]` on specific landing prefixes (`raw/orders/`).
   - **Time-Driven Schedule:** Use **Amazon EventBridge Scheduler** (`scheduler:CreateSchedule`) with explicit `FlexibleTimeWindow`, `ScheduleExpressionTimezone`, and a `DeadLetterConfig` SQS queue.
2. **Enforce Synchronous `.sync` Service Integrations in Step Functions:**
   - Never poll Glue, EMR Serverless, or Athena job status with a custom Lambda loop!
   - Always use native Step Functions optimized `.sync` integrations (`arn:aws:states:::glue:startJobRun.sync`, `arn:aws:states:::emr-serverless:startJobRun.sync`, `arn:aws:states:::athena:startQueryExecution.sync`) so Step Functions waits natively for job completion and surfaces job errors directly to `Retry` and `Catch` blocks.
3. **Wire Mandatory Data Quality Circuit Breakers:**
   - Between Silver transformation and Gold/Redshift serving steps, insert a **Data Quality Gate** state (`enforcing-data-quality`). If critical DQDL rules fail, route execution to a `QuarantineAndAlert` SNS/EventBridge state so corrupted data never reaches production Redshift tables or executive dashboards.
4. **Enforce Idempotency & Transient Error Retries:**
   - Attach `Retry` policies with exponential backoff (`IntervalSeconds: 30`, `BackoffRate: 2.0`, `MaxAttempts: 3`, `JitterStrategy: "FULL"`) for `Glue.ConcurrentRunsExceededException`, `Athena.TooManyRequestsException`, and `States.TaskFailed` transient capacity errors.
   - Pass an explicit execution window (`execution_date` / `batch_id`) into every Glue/Athena/Redshift step so re-running a failed state machine is 100% idempotent.
