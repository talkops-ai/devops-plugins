# AWS Step Functions & EventBridge Serverless Data Pipeline Patterns

Use this reference when authoring Amazon States Language (ASL) state machines, EventBridge S3 arrival rules, or EventBridge Scheduler definitions for data engineering pipelines.

---

## 1. Production Step Functions ASL: Bronze $\rightarrow$ Silver Glue ETL $\rightarrow$ DQ Gate $\rightarrow$ Athena Validation $\rightarrow$ Redshift Serving

```json
{
  "Comment": "End-to-End Medallion Lakehouse Pipeline with Synchronous Glue, Athena DQ Gate, and Failure Quarantine",
  "StartAt": "RunBronzeToSilverGlueJob",
  "States": {
    "RunBronzeToSilverGlueJob": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {
        "JobName": "orders-bronze-to-silver-iceberg",
        "Arguments": {
          "--BATCH_ID.$": "$$.Execution.Name",
          "--SOURCE_S3_PATH.$": "$.sourceS3Path"
        }
      },
      "Retry": [
        {
          "ErrorEquals": [
            "Glue.ConcurrentRunsExceededException",
            "Glue.AWSGlueException"
          ],
          "IntervalSeconds": 30,
          "MaxAttempts": 3,
          "BackoffRate": 2.0,
          "JitterStrategy": "FULL"
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.errorInfo",
          "Next": "PublishPipelineFailureAlert"
        }
      ],
      "ResultPath": "$.glueJobResult",
      "Next": "ValidateSilverRowCountAthena"
    },
    "ValidateSilverRowCountAthena": {
      "Type": "Task",
      "Resource": "arn:aws:states:::athena:startQueryExecution.sync",
      "Parameters": {
        "QueryString": "SELECT COUNT(*) AS row_cnt, SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) AS null_pks FROM silver_db.orders WHERE event_date = current_date",
        "WorkGroup": "analytics-production",
        "QueryExecutionContext": {
          "Catalog": "AwsDataCatalog",
          "Database": "silver_db"
        }
      },
      "ResultPath": "$.athenaValidation",
      "Next": "FetchAthenaValidationResults"
    },
    "FetchAthenaValidationResults": {
      "Type": "Task",
      "Resource": "arn:aws:states:::athena:getQueryResults",
      "Parameters": {
        "QueryExecutionId.$": "$.athenaValidation.QueryExecution.QueryExecutionId"
      },
      "ResultPath": "$.validationRows",
      "Next": "EvaluateDataQualityGate"
    },
    "EvaluateDataQualityGate": {
      "Type": "Choice",
      "Choices": [
        {
          "And": [
            {
              "Variable": "$.validationRows.ResultSet.Rows[1].Data[0].VarCharValue",
              "StringGreaterThan": "0"
            },
            {
              "Variable": "$.validationRows.ResultSet.Rows[1].Data[1].VarCharValue",
              "StringEquals": "0"
            }
          ],
          "Next": "RefreshRedshiftGoldMaterializedView"
        }
      ],
      "Default": "PublishPipelineFailureAlert"
    },
    "RefreshRedshiftGoldMaterializedView": {
      "Type": "Task",
      "Resource": "arn:aws:states:::aws-sdk:redshiftdata:executeStatement",
      "Parameters": {
        "WorkgroupName": "analytics-serverless-wg",
        "Database": "prod_dw",
        "Sql": "REFRESH MATERIALIZED VIEW gold.daily_order_metrics;"
      },
      "End": true
    },
    "PublishPipelineFailureAlert": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:<REGION>:<ACCOUNT>:data-pipeline-alerts",
        "Subject": "CRITICAL: Orders Medallion Pipeline Failed or Quarantined",
        "Message.$": "$"
      },
      "Next": "FailExecution"
    },
    "FailExecution": {
      "Type": "Fail",
      "Error": "DataPipelineOrQualityGateFailed",
      "Cause": "Glue ETL job failed or Silver table failed zero-null primary key / positive row-count gate."
    }
  }
}
```

---

## 2. S3 Object Arrival EventBridge Rule (`aws.s3` $\rightarrow$ Step Functions)

First, enable EventBridge on the S3 landing bucket:
```bash
aws s3api put-bucket-notification-configuration \
  --bucket <LANDING_BUCKET> \
  --notification-configuration '{"EventBridgeConfiguration": {}}'
```

EventBridge Event Pattern matching `_SUCCESS` marker files or `.parquet` arrivals under `raw/orders/`:
```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": {
      "name": ["<LANDING_BUCKET>"]
    },
    "object": {
      "key": [
        { "prefix": "raw/orders/" },
        { "suffix": ".parquet" }
      ],
      "size": [
        { "numeric": [">", 0] }
      ]
    }
  }
}
```
