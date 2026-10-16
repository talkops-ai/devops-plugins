# Event Source Mapping (ESM) Optimization & Resilience Guide

Misconfigured Lambda Event Source Mappings (ESMs) cause message loss, poison-pill retry storms, downstream database connection exhaustion, or runaway Lambda concurrency costs. Apply these rules whenever wiring SQS, Kinesis, DynamoDB Streams, or MSK/Kafka to AWS Lambda.

## 1. Mandatory ESM Invariants by Event Source

| Event Source | Required Resilience Settings | Scaling & Concurrency Control |
| --- | --- | --- |
| **Amazon SQS (Standard & FIFO)** | `FunctionResponseTypes: [ReportBatchItemFailures]`, Queue `RedrivePolicy` (DLQ with `maxReceiveCount: 3–5`), Queue `VisibilityTimeout >= 6 * Function.Timeout` | Set `ScalingConfig.MaximumConcurrency` (2–1000) on the ESM to protect downstream databases; never rely solely on `ReservedConcurrentExecutions` on the function, which causes SQS throttling and premature DLQ drops. |
| **Amazon DynamoDB Streams** | `FunctionResponseTypes: [ReportBatchItemFailures]`, `BisectBatchOnFunctionError: true`, `MaximumRetryAttempts: 3`, `MaximumRecordAgeInSeconds: 3600`, `DestinationConfig.OnFailure` (SQS/SNS/S3) | Set `ParallelizationFactor` (1–10 batches per shard concurrently) and `BatchSize` (100–500) with `MaximumBatchingWindowInSeconds: 5`. |
| **Amazon Kinesis Data Streams** | `FunctionResponseTypes: [ReportBatchItemFailures]`, `BisectBatchOnFunctionError: true`, `MaximumRetryAttempts: 3`, `DestinationConfig.OnFailure`, `TumblerWindowInSeconds` (optional aggregation) | Use Enhanced Fan-Out (`ConsumerARN`) when multiple consumers read the same stream; tune `ParallelizationFactor` (1–10). |
| **Amazon MSK / Apache Kafka** | `DestinationConfig.OnFailure` (SQS/SNS/S3), `ProvisionedPollerConfig` (`MinimumPollers` / `MaximumPollers`) | Attach `FilterCriteria` at the ESM layer so irrelevant events are dropped before invoking Lambda. |

## 2. Event Filtering (`FilterCriteria`)

Always push payload filtering into the ESM (`FilterCriteria`) rather than invoking Lambda only to return early—ESM filtering is free and eliminates unnecessary invocations:

```yaml
Events:
  OrderCreatedStream:
    Type: DynamoDB
    Properties:
      Stream: !GetAtt OrdersTable.StreamArn
      StartingPosition: TRIM_HORIZON
      BatchSize: 100
      MaximumBatchingWindowInSeconds: 5
      BisectBatchOnFunctionError: true
      MaximumRetryAttempts: 3
      FunctionResponseTypes:
        - ReportBatchItemFailures
      DestinationConfig:
        OnFailure:
          Destination: !GetAtt StreamDlq.Arn
      FilterCriteria:
        Filters:
          - Pattern: '{"eventName": ["INSERT", "MODIFY"], "dynamodb": {"NewImage": {"status": {"S": ["PAID"]}}}}'
```

## 3. SQS ESM Template with `MaximumConcurrency` & Partial Batch Responses

```yaml
OrderQueue:
  Type: AWS::SQS::Queue
  Properties:
    VisibilityTimeout: 180 # 6x Lambda Timeout (30s)
    kmsMasterKeyId: alias/aws/sqs
    RedrivePolicy:
      deadLetterTargetArn: !GetAtt OrderDlq.Arn
      maxReceiveCount: 5

OrderConsumerFunction:
  Type: AWS::Serverless::Function
  Properties:
    Timeout: 30
    CodeUri: src/consumer/
    Handler: app.handler
    Runtime: nodejs22.x
    Policies:
      - SQSPollerPolicy:
          QueueName: !GetAtt OrderQueue.QueueName
    Events:
      SqsTrigger:
        Type: SQS
        Properties:
          Queue: !GetAtt OrderQueue.Arn
          BatchSize: 10
          MaximumBatchingWindowInSeconds: 2
          FunctionResponseTypes:
            - ReportBatchItemFailures
          ScalingConfig:
            MaximumConcurrency: 20
```

Your handler returns only failed message IDs so succeeded messages in the same batch are not reprocessed:

```json
{
  "batchItemFailures": [
    { "itemIdentifier": "msg-id-that-failed" }
  ]
}
```
