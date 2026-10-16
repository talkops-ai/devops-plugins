---
name: amazon-sqs-sns-async-messaging
description: Design, provision, and operate resilient asynchronous messaging pipelines with Amazon SQS and Amazon SNS using aws-sns-sqs-mcp and AWS SAM/CDK. Covers Standard vs High-Throughput FIFO queues, SNS-to-SQS fan-out with filter policies, visibility timeout sizing, Dead-Letter Queues (DLQs), message redrive tasks, partial batch failure handling (ReportBatchItemFailures), and idempotency.
---

# Amazon SQS & SNS Asynchronous Messaging Architecture

Architect, configure, and troubleshoot fault-tolerant pub/sub and queue-based serverless pipelines using Amazon SNS, Amazon SQS, AWS Lambda, and `aws-sns-sqs-mcp`.

## When to Use

- Decoupling synchronous APIs from slow or bursty background processing using SQS queues
- Broadcasting domain events to multiple independent microservices using the **SNS -> SQS Fan-Out** pattern
- Enforcing strict per-entity message ordering and deduplication with **SQS FIFO** and **SNS FIFO**
- Triaging poison-pill messages, configuring Dead-Letter Queues (DLQs), or redriving failed messages via `start_message_move_task`
- Eliminating empty-receive SQS polling costs and duplicate processing on partial batch failures

---

## 1. Mandatory Production Rules for SQS + Lambda

Never provision a production SQS queue or Lambda consumer without enforcing these 6 invariants:

1. **Visibility Timeout Formula**:
   $$\text{VisibilityTimeout} \ge (6 \times \text{Lambda Function Timeout}) + \text{MaximumBatchingWindowInSeconds}$$
   - *Example*: For a Lambda with `Timeout: 30` seconds and `MaximumBatchingWindowInSeconds: 10` seconds, set queue `VisibilityTimeout >= 190` seconds (`(6 * 30) + 10`). Setting `VisibilityTimeout < Lambda Timeout` causes SQS to redeliver the message to another worker while the first invocation is still running.
2. **Dead-Letter Queue (DLQ) + Redrive Policy**:
   - Every primary queue MUST have a dedicated DLQ of the **exact same queue type** (Standard -> Standard DLQ; FIFO -> FIFO DLQ).
   - Set `maxReceiveCount` between `3` and `5` in `RedrivePolicy`.
   - Configure `RedriveAllowPolicy` (`redrivePermission: byQueue`, `sourceQueueArns`) and a CloudWatch Alarm on DLQ `ApproximateNumberOfMessagesVisible > 0`.
3. **Partial Batch Failure Reporting (`ReportBatchItemFailures`)**:
   - Always enable `FunctionResponseTypes: [ReportBatchItemFailures]` on the Lambda Event Source Mapping (`AWS::Lambda::EventSourceMapping`).
   - Return `{"batchItemFailures": [{"itemIdentifier": record["messageId"]}]}` so only failed messages are retried, preventing already-succeeded messages in the same batch from re-executing.
4. **Long Polling Enabled (`ReceiveMessageWaitTimeSeconds: 20`)**:
   - Set `ReceiveMessageWaitTimeSeconds: 20` on every queue to eliminate empty `ReceiveMessage` API charges and reduce delivery latency.
5. **Encryption at Rest + KMS Key Reuse Optimization**:
   - Enable `SqsManagedSseEnabled: true` (SSE-SQS, free) or KMS CMK (`KmsMasterKeyId`). When using KMS CMKs, set `KmsDataKeyReusePeriodSeconds: 3600` (1 hour) to avoid excessive KMS API charges (`$0.03 per 10,000 KMS requests`).
6. **Idempotent Consumer Logic**:
   - Even SQS FIFO guarantees *exactly-once processing* only within the 5-minute deduplication interval and when the consumer completes within `VisibilityTimeout`. Always guard writes with a DynamoDB conditional write (`attribute_not_exists(idempotency_key)`) or AWS Lambda Powertools Idempotency utility.

---

## 2. Standard vs. High-Throughput FIFO Queues

| Dimension | SQS Standard Queue | SQS FIFO Queue (High-Throughput Mode) |
|---|---|---|
| **Throughput** | Nearly unlimited TPS | Up to **70,000+ TPS** (regional quota) with High-Throughput FIFO enabled |
| **Ordering** | Best-effort ordering | Strict **First-In-First-Out per `MessageGroupId`** |
| **Deduplication** | At-least-once delivery (occasional duplicates) | Exact deduplication within 5-minute window via `MessageDeduplicationId` or `ContentBasedDeduplication: true` |
| **Required Naming** | Standard name (e.g., `orders-queue`) | Must end with **`.fifo`** suffix (e.g., `orders-queue.fifo`) |
| **High-Throughput Config** | N/A | Set `DeduplicationScope: messageGroup` and `FifoThroughputLimit: perMessageGroupId` |
| **Key Design Rule** | Optimize `BatchSize` (`10`–`1000`) and `MaximumBatchingWindowInSeconds` | Use high-cardinality `MessageGroupId` (e.g., `tenant_id` or `order_id`, NEVER a single static value) so parallel Lambda workers can process distinct groups concurrently |

---

## 3. SNS-to-SQS Fan-Out Pattern with Filter Policies

Combine **1 SNS Topic** with **multiple SQS Queues** when a single domain event (e.g., `OrderPlaced`) must trigger independent consumers (Billing, Inventory, Analytics, Notifications) at their own pace:

- **Attribute vs. Payload Filtering**:
  - Prefer **`FilterPolicyScope: MessageAttributes`** (free, no payload parsing overhead) over `MessageBody` when possible.
- **Raw Message Delivery**:
  - Enable `RawMessageDelivery: true` on SNS-to-SQS subscriptions unless the consumer explicitly needs the SNS metadata wrapper (`TopicArn`, `Timestamp`, `Signature`).
- **Mandatory SQS Queue Policy for SNS**:
  - An SNS Topic cannot deliver to an SQS Queue unless the SQS Queue Policy grants `sqs:SendMessage` to `sns.amazonaws.com` with `aws:SourceArn` scoped to the SNS Topic ARN.
  - If the SQS Queue uses a customer-managed KMS key (CMK), the KMS Key Policy must also grant `kms:GenerateDataKey*` and `kms:Decrypt` to `sns.amazonaws.com`.

### Production AWS SAM Template: SNS Fan-Out -> SQS + DLQ -> Lambda (`ReportBatchItemFailures`)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  OrdersTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: orders-events
      KmsMasterKeyId: alias/aws/sns

  BillingDlq:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: billing-orders-dlq
      MessageRetentionPeriod: 1209600 # 14 days
      SqsManagedSseEnabled: true

  BillingQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: billing-orders-queue
      VisibilityTimeout: 190 # (6 * 30s Lambda Timeout) + 10s Batching Window
      ReceiveMessageWaitTimeSeconds: 20
      MessageRetentionPeriod: 345600 # 4 days
      SqsManagedSseEnabled: true
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt BillingDlq.Arn
        maxReceiveCount: 4

  BillingQueuePolicy:
    Type: AWS::SQS::QueuePolicy
    Properties:
      Queues:
        - !Ref BillingQueue
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Sid: AllowSnsOrdersTopicSendMessage
            Effect: Allow
            Principal:
              Service: sns.amazonaws.com
            Action: sqs:SendMessage
            Resource: !GetAtt BillingQueue.Arn
            Condition:
              ArnEquals:
                aws:SourceArn: !Ref OrdersTopic

  BillingSubscription:
    Type: AWS::SNS::Subscription
    Properties:
      TopicArn: !Ref OrdersTopic
      Protocol: sqs
      Endpoint: !GetAtt BillingQueue.Arn
      RawMessageDelivery: true
      FilterPolicyScope: MessageAttributes
      FilterPolicy:
        event_type:
          - ORDER_CREATED
          - ORDER_REFUNDED

  BillingConsumerFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: python3.13
      Handler: app.handler
      Architectures: [arm64]
      Timeout: 30
      MemorySize: 512
      Events:
        SqsBatchEvent:
          Type: SQS
          Properties:
            Queue: !GetAtt BillingQueue.Arn
            BatchSize: 25
            MaximumBatchingWindowInSeconds: 10
            FunctionResponseTypes:
              - ReportBatchItemFailures
            ScalingConfig:
              MaximumConcurrency: 50
```

---

## 4. Partial Batch Failure Handler Pattern (Python)

```python
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def process_record(body: dict) -> None:
    # Perform idempotent business logic here
    if "order_id" not in body:
        raise ValueError("Missing order_id")

def handler(event: dict, context) -> dict:
    batch_item_failures = []

    for record in event.get("Records", []):
        message_id = record["messageId"]
        try:
            payload = json.loads(record["body"])
            process_record(payload)
        except Exception as exc:
            logger.exception("Failed processing messageId=%s: %s", message_id, exc)
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
```

---

## 5. Operating & Redriving Queues with `aws-sns-sqs-mcp`

Use the `aws-sns-sqs-mcp` server for live inspection and operational recovery:
1. **Audit Queue Health & Backlog**:
   - Call `list_queues` and `get_queue_attributes` (`AttributeNames: ["All"]`) to inspect `ApproximateNumberOfMessages`, `ApproximateNumberOfMessagesNotVisible`, `ApproximateAgeOfOldestMessage`, and `RedrivePolicy`.
2. **Inspect DLQ Poison Messages (Non-Destructively)**:
   - Call `receive_message` on the DLQ with a short `VisibilityTimeout` (e.g., `5` seconds) and **do not call `delete_message`** while diagnosing root causes.
3. **Automated DLQ Redrive**:
   - Once the consumer bug or downstream outage is resolved, call `start_message_move_task` with `SourceArn` (the DLQ ARN), `DestinationArn` (the source queue ARN), and `MaxNumberOfMessagesPerSecond` (e.g., `50` to avoid overwhelming downstream databases).
   - Monitor progress with `list_message_move_tasks`.
4. **Tag Enforcement**:
   - Note that `aws-sns-sqs-mcp` automatically enforces the `mcp_server_version` tag when creating or mutating resources with `--allow-resource-creation`.
