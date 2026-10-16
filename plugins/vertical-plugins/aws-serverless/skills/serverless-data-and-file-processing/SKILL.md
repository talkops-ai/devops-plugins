---
name: serverless-data-and-file-processing
description: Architect serverless file upload, event-driven S3 processing, and high-concurrency batch data pipelines. Covers S3 Presigned URLs (bypassing API Gateway 10 MB / Lambda 6 MB payload limits), S3 EventBridge notifications, S3 recursive loop prevention, and AWS Step Functions Distributed Map (ItemReader, ItemBatcher, ResultWriter) for multi-GB CSV/JSON/Parquet processing.
---

# Serverless Data & File Processing Pipelines

Design and implement production-grade serverless file ingestion, asynchronous transformation, and massively parallel batch pipelines on Amazon S3, AWS Lambda, Amazon EventBridge, Amazon SQS, and AWS Step Functions Distributed Map.

## When to Use

- Users need to upload or download files larger than **Lambda's 6 MB synchronous payload limit** or **API Gateway's 10 MB payload limit**
- Processing newly uploaded S3 objects (images, PDFs, audio/video metadata, CSV/JSON/Parquet datasets) via EventBridge, SQS, or Step Functions
- Running massively parallel fan-out jobs across thousands or millions of S3 objects or multi-GB CSV/JSONL/Manifest files using **Step Functions Distributed Map**
- Preventing runaway AWS bills caused by S3 -> Lambda -> S3 recursive invocation loops

---

## 1. Architecture Pattern Selection

| Workload Pattern | Payload / Dataset Size | Recommended Architecture | Why |
|---|---|---|---|
| **Direct Client Upload / Download** | 1 KB – 5 TB per file | **API Gateway -> Lambda (Presigned URL Generator) -> Direct Client-to-S3 PUT/Multipart Upload** | Bypasses API Gateway 10 MB and Lambda 6 MB limits; eliminates double-hop Lambda compute charges |
| **Simple Object Post-Processing** | Single file, < 15 min processing | **S3 (`EventBridgeEnabled: true`) -> EventBridge Rule (prefix/suffix filter) -> SQS -> Lambda** | Decoupled, buffered, supports DLQ and concurrency limits |
| **Multi-Step File Pipeline** (Validate -> Transform -> Enrich -> Notify) | Single file, multi-stage orchestration | **S3 -> EventBridge -> Step Functions Standard/Express Workflow** | Visual state tracking, granular retries, and redrive from point of failure (`references/step-functions-s3-processing.md`) |
| **Massive S3 Batch / CSV / JSONL Dataset Processing** | 1,000s of objects or multi-GB CSV/JSONL files | **Step Functions Distributed Map (`ProcessorConfig.Mode: DISTRIBUTED`)** with `ItemReader`, `ItemBatcher`, and `ResultWriter` | Up to **10,000 parallel child executions**, native S3 CSV/JSON/Manifest streaming without loading the file into state payload (256 KB limit) |

---

## 2. CRITICAL Guardrail: S3 Recursive Loop Prevention

Writing processed output back to the same S3 bucket that triggers your event notification is the #1 cause of runaway serverless bills.

**Enforce all three defenses on every S3-triggered pipeline:**
1. **Separate Source and Destination Buckets (Preferred)**: Ingest uploads into ` RawUploadsBucket` and write processed artifacts to `ProcessedOutputBucket`.
2. **Strict Prefix & Suffix Event Filtering**: If a single bucket is mandatory, scope the S3 notification or EventBridge rule strictly to `prefix: "incoming/"` and write outputs exclusively to `processed/`, with an explicit `anything-but` exclusion on `"processed/"`:
   ```json
   {
     "source": ["aws.s3"],
     "detail-type": ["Object Created"],
     "detail": {
       "bucket": { "name": ["my-data-bucket"] },
       "object": {
         "key": [
           { "prefix": "incoming/" },
           { "anything-but": { "prefix": "processed/" } }
         ]
       }
     }
   }
   ```
3. **Reserved Concurrency Circuit Breaker**: Set `ReservedConcurrentExecutions` on the processing Lambda function (or `MaxConcurrency` on Step Functions Distributed Map) to cap blast radius.

---

## 3. Pattern A: S3 Presigned URL Upload (Bypassing 6 MB / 10 MB Limits)

Never base64-encode binary files through API Gateway and Lambda. Generate a short-lived S3 Presigned `put_object` (or Presigned POST / Multipart Upload) URL with strict `ContentType` and `ContentLengthRange` conditions:

```python
import os
import uuid
import boto3
from botocore.config import Config

s3 = boto3.client(
    "s3",
    region_name=os.environ["AWS_REGION"],
    config=Config(signature_version="s3v4"),
)
UPLOAD_BUCKET = os.environ["UPLOAD_BUCKET"]

def handler(event, context):
    object_key = f"incoming/{uuid.uuid4()}.csv"
    # Generate a 5-minute presigned POST with a strict 50 MB size limit
    presigned = s3.generate_presigned_post(
        Bucket=UPLOAD_BUCKET,
        Key=object_key,
        Fields={"Content-Type": "text/csv"},
        Conditions=[
            {"Content-Type": "text/csv"},
            ["content-length-range", 1, 52_428_800],  # 1 byte to 50 MB
        ],
        ExpiresIn=300,
    )
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": presigned,
    }
```

---

## 4. Pattern B: Step Functions Distributed Map for Multi-GB S3 Datasets

Standard Step Functions `Inline` Map states are constrained by the **256 KB state payload limit** and max ~40 concurrent iterations. For large S3 CSV, JSON, JSONL, or S3 Inventory Manifest workloads, use **Distributed Map (`DISTRIBUTED` mode)**:

- **`ItemReader`**: Streams rows directly from an S3 CSV/JSON/JSONL file or lists objects in an S3 bucket without passing the full dataset through state machine input.
- **`ItemBatcher`**: Groups items (e.g., `MaxItemsPerBatch: 100` or `MaxInputBytesPerBatch: 131072`) so each child execution invokes Lambda once per batch of 100 rows instead of 1 Lambda invocation per row (reducing Lambda invocation and Step Functions transition costs by up to 99%).
- **`MaxConcurrency`**: Caps parallel child executions (up to 10,000; set e.g. `100` to protect downstream databases/APIs).
- **`ResultWriter`**: Writes child execution results directly to an S3 output prefix (`processed/results/`) to avoid blowing past the 256 KB parent state output limit.
- **`ToleratedFailurePercentage` / `ToleratedFailureCount`**: Allows partial batch failures without aborting the entire run, paired with **Map Run Redrive** for failed items.

### ASL Definition: Distributed Map Reading a Large S3 CSV File

```json
{
  "Comment": "Process a multi-GB CSV file in S3 using Distributed Map with batching",
  "StartAt": "ProcessCsvInBatches",
  "States": {
    "ProcessCsvInBatches": {
      "Type": "Map",
      "ItemProcessor": {
        "ProcessorConfig": {
          "Mode": "DISTRIBUTED",
          "ExecutionType": "EXPRESS"
        },
        "StartAt": "ProcessRecordBatch",
        "States": {
          "ProcessRecordBatch": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "OutputPath": "$.Payload",
            "Parameters": {
              "FunctionName": "${BatchWorkerFunctionArn}",
              "Payload.$": "$"
            },
            "Retry": [
              {
                "ErrorEquals": [
                  "Lambda.ServiceException",
                  "Lambda.AWSLambdaException",
                  "Lambda.SdkClientException",
                  "Lambda.TooManyRequestsException"
                ],
                "IntervalSeconds": 2,
                "MaxAttempts": 5,
                "BackoffRate": 2.0,
                "JitterStrategy": "FULL"
              }
            ],
            "End": true
          }
        }
      },
      "ItemReader": {
        "Resource": "arn:aws:states:::s3:getObject",
        "ReaderConfig": {
          "InputType": "CSV",
          "CSVHeaderLocation": "FIRST_ROW"
        },
        "Parameters": {
          "Bucket.$": "$.detail.bucket.name",
          "Key.$": "$.detail.object.key"
        }
      },
      "ItemBatcher": {
        "MaxItemsPerBatch": 100,
        "MaxInputBytesPerBatch": 131072
      },
      "MaxConcurrency": 100,
      "ToleratedFailurePercentage": 5,
      "ResultWriter": {
        "Resource": "arn:aws:states:::s3:putObject",
        "Parameters": {
          "Bucket": "${ProcessedOutputBucket}",
          "Prefix": "processed/map-results"
        }
      },
      "End": true
    }
  }
}
```

---

## 5. Pattern C: Event-Driven S3 Object Processing Workflow

For complete step-by-step instructions on wiring S3 `EventBridgeEnabled: true` -> EventBridge Rule -> Step Functions State Machine (with IAM execution roles, CloudWatch log groups, and end-to-end verification):
- Run `python3 scripts/check_prerequisites.py` to check local CLI and environment readiness.
- Follow `references/step-functions-s3-processing.md` for the complete deployment and verification playbook.
