# Messaging Service Selector, DLQ & Idempotency Patterns Reference

## 1. Event-Driven Messaging Decision Tree

1. **Need point-to-point decoupling, backpressure buffering, or concurrency smoothing for workers?**
   $\rightarrow$ **Amazon SQS** (Standard for maximum throughput; FIFO with `MessageGroupId` + `ContentBasedDeduplication` for strict per-entity ordering).
2. **Need high-throughput fan-out of the exact same message to multiple SQS queues, Lambdas, or HTTP endpoints?**
   $\rightarrow$ **Amazon SNS Topic + SQS Queue Subscriptions** (the canonical SNS-to-SQS fan-out pattern).
3. **Need content-based routing, schema registry validation, SaaS partner integration, or Archive & Replay across domain microservices?**
   $\rightarrow$ **Amazon EventBridge Event Bus** (or **EventBridge Pipes** for 1-to-1 point-to-point enrichment from DynamoDB Streams / Kinesis / SQS, and **EventBridge Scheduler** for millions of cron/rate or one-time `at()` schedules with `ActionAfterCompletion=DELETE`).
4. **Need lift-and-shift broker compatibility for legacy industry protocols (AMQP 0-9-1, JMS, NMS, STOMP, MQTT, OpenWire) with zero application code changes?**
   $\rightarrow$ **Amazon MQ** (Managed RabbitMQ or ActiveMQ).
5. **Need sub-second ordered stream processing, multiple concurrent stream consumers with independent offsets, or Apache Flink windowing?**
   $\rightarrow$ **Amazon Kinesis Data Streams** (or **Amazon MSK** when Apache Kafka protocol/ecosystem compatibility is required, **Amazon Data Firehose** for zero-admin buffered delivery to S3/Iceberg/Redshift/OpenSearch, and **Amazon Managed Service for Apache Flink** for stateful sliding/tumbling window analytics).

## 2. Decision Matrix: Messaging vs. Streaming

| Dimension | Messaging (SQS / SNS / EventBridge) | Streaming (Kinesis Data Streams / Amazon MSK) |
|---|---|---|
| **Message Lifecycle** | Consumed and deleted upon acknowledgment (or routed once; EventBridge optional Archive) | Retained in an append-only log for the configured retention period (24h to 365 days in Kinesis; configurable/tiered in MSK) |
| **Consumer Model** | Competing consumers share a queue (each message processed by one consumer per queue) | Multiple independent consumer groups read the same stream simultaneously at their own offset/sequence position |
| **Ordering Guarantees** | Best-effort (Standard) or per-`MessageGroupId` (SQS/SNS FIFO) | Strict ordering per Shard (`PartitionKey` in Kinesis) or per Topic Partition (MSK) |
| **Replay Capability** | DLQ redrive or EventBridge Archive replay | Native replay by seeking sequence numbers, timestamps (`AT_TIMESTAMP`), or consumer group offsets |
| **Throughput Unit** | Per-message API requests (virtually unlimited for Standard; 3,000–70,000+ msg/s with high-throughput FIFO) | Per-Shard (`1 MB/s` ingress, `2 MB/s` egress or Enhanced Fan-Out) or per-Broker/Partition |
| **Typical Latency** | Low tens of milliseconds (point-to-point / pub-sub) to ~hundreds of milliseconds | Sub-second (`< 70–200 ms` with Kinesis Enhanced Fan-Out or MSK; `60s+` buffered for Data Firehose) |

## 3. Canonical Multi-Service Integration Patterns

1. **Pattern 1 — Decoupled Microservices Fan-Out (`SNS -> SQS -> Workers`)**:
   Publish domain events once to an **Amazon SNS Topic** with subscription filter policies fanning out to independent **Amazon SQS Queues** per downstream microservice, each backed by its own Dead-Letter Queue (DLQ) and consumer scaling.
2. **Pattern 2 — Event-Driven SaaS & Domain Routing (`EventBridge Bus -> SQS -> Consumer`)**:
   Ingest SaaS partner events (Stripe, Shopify, Auth0) or cross-account domain events into an **Amazon EventBridge Event Bus** with Schema Registry and Archive enabled, and buffer matched rules into **Amazon SQS** so downstream consumers survive target outages and throttling.
3. **Pattern 3 — Real-Time Streaming Analytics (`Kinesis / MSK -> Managed Flink -> Data Firehose -> S3 / Iceberg`)**:
   Ingest high-velocity clickstream/IoT telemetry into **Kinesis Data Streams** or **Amazon MSK**, compute stateful tumbling/sliding window aggregations with **Managed Service for Apache Flink**, and sink raw/aggregated streams via **Amazon Data Firehose** into S3/Apache Iceberg.
4. **Pattern 4 — Point-to-Point Change Data Capture (`DynamoDB Streams -> EventBridge Pipes -> Target`)**:
   Connect **DynamoDB Streams** (or Kinesis/SQS) via **Amazon EventBridge Pipes** with built-in event filtering and optional Lambda/API Gateway enrichment directly to Step Functions, EventBridge, Kinesis, or SQS without writing polling glue code.
5. **Pattern 5 — Transactional Outbox Pattern (`Database -> AWS DMS / Debezium -> MSK / Kinesis -> Consumers`)**:
   Avoid dual-write inconsistencies between a relational database and a message bus by writing business state and outbox events in a single ACID database transaction, streaming binlog/WAL changes via **AWS DMS** or **Debezium Kafka Connect** into **Amazon MSK** or **Kinesis Data Streams**.

## 4. Non-Negotiable Reliability & Idempotency Controls

- **Dead-Letter Queues (DLQs) Everywhere**:
  - Every SQS queue must configure a `RedrivePolicy` (`maxReceiveCount: 3..5`) pointing to a dedicated DLQ with `MessageRetentionPeriod: 1209600` (14 days) and `RedriveAllowPolicy: byQueue`.
  - Every EventBridge Rule target, EventBridge Pipe, EventBridge Schedule, and asynchronous Lambda invocation must configure a `DeadLetterConfig` (SQS DLQ) or `DestinationConfig` (`OnFailure`).
- **Visibility Timeout Formula**:
  $$\text{SQS VisibilityTimeout} \ge 6 \times \text{Consumer Function Timeout} + \text{MaxBatchingWindowInSeconds}$$
- **Partial Batch Response (`ReportBatchItemFailures`)**:
  - Always enable `FunctionResponseTypes: [ReportBatchItemFailures]` on SQS/Kinesis/DynamoDB/MSK Event Source Mappings so a single failed record does not re-process the entire batch.
- **Consumer Idempotency**:
  - Because SQS Standard, EventBridge, and SNS deliver **at-least-once**, consumers must enforce idempotency using a conditional DynamoDB write (`attribute_not_exists(idempotency_key)` with TTL) or Powertools Idempotency utility.
