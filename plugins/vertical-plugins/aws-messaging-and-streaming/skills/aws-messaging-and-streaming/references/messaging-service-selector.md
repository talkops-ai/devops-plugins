# Messaging Service Selector, DLQ & Idempotency Patterns Reference

## 1. Event-Driven Messaging Decision Tree

1. **Need point-to-point decoupling, backpressure buffering, or concurrency smoothing for workers?**
   $\rightarrow$ **Amazon SQS** (Standard for maximum throughput; FIFO with `MessageGroupId` + `ContentBasedDeduplication` for strict per-entity ordering).
2. **Need high-throughput fan-out of the exact same message to multiple SQS queues, Lambdas, or HTTP endpoints?**
   $\rightarrow$ **Amazon SNS Topic + SQS Queue Subscriptions** (the canonical SNS-to-SQS fan-out pattern).
3. **Need content-based routing, schema registry validation, SaaS partner integration, or Archive & Replay across domain microservices?**
   $\rightarrow$ **Amazon EventBridge Event Bus** (or **EventBridge Pipes** for 1-to-1 point-to-point enrichment from DynamoDB Streams / Kinesis / SQS).
4. **Need sub-second ordered stream processing, multiple concurrent stream consumers with independent offsets, or Apache Flink windowing?**
   $\rightarrow$ **Amazon Kinesis Data Streams** (or **Amazon MSK** when Apache Kafka protocol compatibility is required).

## 2. Non-Negotiable Reliability & Idempotency Controls

- **Dead-Letter Queues (DLQs) Everywhere**:
  - Every SQS queue must configure a `RedrivePolicy` (`maxReceiveCount: 3..5`) pointing to a dedicated DLQ with `MessageRetentionPeriod: 1209600` (14 days) and `RedriveAllowPolicy: byQueue`.
  - Every EventBridge Rule target and asynchronous Lambda invocation must configure a `DeadLetterConfig` (SQS DLQ) or `DestinationConfig` (`OnFailure`).
- **Visibility Timeout Formula**:
  $$\text{SQS VisibilityTimeout} \ge 6 \times \text{Consumer Function Timeout} + \text{MaxBatchingWindowInSeconds}$$
- **Partial Batch Response (`ReportBatchItemFailures`)**:
  - Always enable `FunctionResponseTypes: [ReportBatchItemFailures]` on SQS/Kinesis/DynamoDB Event Source Mappings so a single failed record does not re-process the entire batch.
- **Consumer Idempotency**:
  - Because SQS Standard, EventBridge, and SNS deliver **at-least-once**, consumers must enforce idempotency using a conditional DynamoDB write (`attribute_not_exists(idempotency_key)` with TTL) or Powertools Idempotency utility.
