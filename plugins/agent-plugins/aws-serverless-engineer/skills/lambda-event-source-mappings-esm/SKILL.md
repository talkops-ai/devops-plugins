---
name: lambda-event-source-mappings-esm
description: Configure, optimize, and troubleshoot AWS Lambda Event Source Mappings (ESMs) across Amazon SQS, Kinesis Data Streams, DynamoDB Streams, Amazon MSK, and self-managed Apache Kafka using aws-serverless-mcp (esm_guidance, esm_optimize, esm_kafka_troubleshoot). Covers batching, ParallelizationFactor, BisectBatchOnFunctionError, OnFailure destinations, FilterCriteria, Provisioned Pollers, and Kafka VPC/SASL-SCRAM debugging.
---

# AWS Lambda Event Source Mappings (ESM) Optimization & Troubleshooting

Design, validate, tune, and debug Lambda Event Source Mappings (ESMs) for queues and streams using the specialized `aws-serverless-mcp` ESM tools (`esm_guidance`, `esm_optimize`, `esm_kafka_troubleshoot`).

## When to Use

- Connecting Lambda consumers to **Amazon SQS**, **Amazon Kinesis Data Streams**, **Amazon DynamoDB Streams**, **Amazon MSK**, or **Self-Managed Apache Kafka**
- Optimizing ESM throughput, latency, or poller/invocation costs (`esm_optimize`)
- Debugging stream poison pills (`IteratorAge` spikes), infinite retry loops, or throttled downstream targets
- Resolving Kafka/MSK ESM connection timeouts, VPC security group failures, or SASL/SCRAM `AmazonMSK_` secret errors (`esm_kafka_troubleshoot`)

---

## 1. MCP Tool Workflow for Event Source Mappings (`aws-serverless-mcp`)

Always use the built-in `aws-serverless-mcp` ESM tools instead of guessing parameters:

1. **`esm_guidance`**:
   - Call with `event_source` (`"dynamodb" | "kinesis" | "kafka" | "sqs" | "unspecified"`) and `guidance_type` (`"setup" | "networking" | "troubleshooting"`).
   - Retrieves official IAM policies, VPC networking prerequisites, and baseline configuration templates.
2. **`esm_optimize`**:
   - **`action: "analyze"`**: Evaluates trade-offs across `optimization_targets` (`"failure_rate"`, `"latency"`, `"throughput"`, `"cost"`).
   - **`action: "validate"`**: Validates proposed `configs` against AWS service limits for the specific `event_source` (`"kinesis"`, `"dynamodb"`, `"kafka"`, `"sqs"`).
   - **`action: "generate_template"`**: Generates a safe SAM/CloudFormation template to update an existing `esm_uuid` with validated parameters.
3. **`esm_kafka_troubleshoot`**:
   - Call first with `kafka_type: "auto-detect"` (or `"msk"` / `"self-managed"`) and `issue_type: "Overview"`, then drill into `"diagnosis"`, `"network"`, `"security"`, `"authentication"`, `"on-premise"`, or `"resolution"`.

---

## 2. ESM Configuration Matrix by Event Source

| Parameter | Amazon SQS | Kinesis & DynamoDB Streams | Amazon MSK / Self-Managed Kafka |
|---|---|---|---|
| **`BatchSize`** | `1–10,000` (Standard)<br>`1–10` (FIFO or if batching window = 0) | `1–10,000` (constrained by 6 MB Lambda invocation payload limit) | `1–10,000` (constrained by 6 MB payload limit) |
| **`MaximumBatchingWindowInSeconds`** | `0–300` seconds | `0–300` seconds | `0–300` seconds |
| **Concurrency Control** | `ScalingConfig.MaximumConcurrency` (`2–1,000`) | `ParallelizationFactor` (`1–10` concurrent batches per shard) | `ProvisionedPollerConfig` (`MinimumPollers`, `MaximumPollers`) |
| **Partial Failure Isolation** | `FunctionResponseTypes: [ReportBatchItemFailures]` | `FunctionResponseTypes: [ReportBatchItemFailures]` + **`BisectBatchOnFunctionError: true`** | `FunctionResponseTypes: [ReportBatchItemFailures]` (or Kafka OnFailure destination) |
| **Retry & Age Caps** | Configured on SQS `RedrivePolicy` (`maxReceiveCount`) | **`MaximumRetryAttempts`** (`0–10,000`, default `-1` infinite!) + **`MaximumRecordAgeInSeconds`** (`60–604,800`) | Retry policy / `DestinationConfig.OnFailure` (SQS, SNS, S3) |
| **Dead-Letter Destination** | SQS Queue `RedrivePolicy` DLQ | **`DestinationConfig.OnFailure`** (SQS Queue, SNS Topic, or S3 Bucket) | **`DestinationConfig.OnFailure`** (SQS, SNS, S3, or Kafka topic) |
| **Event Filtering** | `FilterCriteria` (up to 5 patterns, free at poller level) | `FilterCriteria` (filters before invoking Lambda) | `FilterCriteria` (JSON/string matching on `value` or `key`) |

---

## 3. Critical Production Guardrails for Stream ESMs (Kinesis & DynamoDB Streams)

### Guardrail A: Never Leave `MaximumRetryAttempts` at Default (`-1`)
By default, Kinesis and DynamoDB Stream ESMs retry a failed batch **until the record expires from the stream (up to 7 days)**, blocking the entire shard (`IteratorAge` climbs continuously) while burning Lambda compute non-stop.

**Always configure the "Stream Resilience Triad" on every Kinesis/DynamoDB Stream ESM:**
1. **`BisectBatchOnFunctionError: true`**: Recursively splits a failing batch in half to isolate the exact poison-pill record while allowing valid sibling records to succeed.
2. **`MaximumRetryAttempts: 3`** (or `2–5`) and/or **`MaximumRecordAgeInSeconds: 3600`**.
3. **`DestinationConfig.OnFailure`**: Routes the metadata (or full payload when targeted to S3) of discarded records to an SQS DLQ, SNS Topic, or S3 Bucket so zero data is lost.
4. **`FunctionResponseTypes: [ReportBatchItemFailures]`**: Allows your handler to checkpoint all records prior to the first failed record in the batch.

### Guardrail B: Scaling Stream Throughput Without Losing Partition Ordering
By default, Lambda runs **1 concurrent execution per Kinesis/DynamoDB shard**. If `IteratorAge` grows because processing takes too long:
- Set **`ParallelizationFactor: 2` to `10`**: Runs up to 10 concurrent Lambda executions per shard while **strictly preserving in-order processing for each partition key (`PartitionKey`)** via consistent hashing.

### Production SAM Snippet: Resilient DynamoDB Stream ESM

```yaml
  OrdersStreamConsumer:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: python3.13
      Handler: stream_worker.handler
      Architectures: [arm64]
      Timeout: 30
      MemorySize: 512
      Policies:
        - SQSSendMessagePolicy:
            QueueName: !GetAtt StreamRecordsDlq.QueueName
      Events:
        DynamoStreamEvent:
          Type: DynamoDB
          Properties:
            Stream: !GetAtt OrdersTable.StreamArn
            StartingPosition: LATEST
            BatchSize: 100
            MaximumBatchingWindowInSeconds: 5
            ParallelizationFactor: 4
            BisectBatchOnFunctionError: true
            MaximumRetryAttempts: 3
            MaximumRecordAgeInSeconds: 3600
            FunctionResponseTypes:
              - ReportBatchItemFailures
            DestinationConfig:
              OnFailure:
                Destination: !GetAtt StreamRecordsDlq.Arn
            FilterCriteria:
              Filters:
                - Pattern: '{"eventName": ["INSERT", "MODIFY"]}'
```

---

## 4. FinOps & Throughput Tuning (`esm_optimize`)

| Goal | Configuration Levers | Why It Works |
|---|---|---|
| **Minimize Cost (FinOps)** |1. Add **`FilterCriteria`** at the ESM level<br>2. Increase `BatchSize` (`100–500`) + `MaximumBatchingWindowInSeconds` (`5–30s`)<br>3. Set `ScalingConfig.MaximumConcurrency` to match downstream DB limits |1. Filtered-out messages are dropped by the AWS poller for **$0 Lambda invocation charge**<br>2. Packing 100 messages into 1 invocation reduces Lambda request charges by 99% and amortizes cold starts |
| **Minimize Latency** |1. `MaximumBatchingWindowInSeconds: 0`<br>2. Smaller `BatchSize` (`10–25`)<br>3. Increase `ParallelizationFactor` (streams) or `ProvisionedPollerConfig.MinimumPollers` (Kafka/SQS) | Dispatches messages immediately upon arrival and keeps dedicated pollers warm |
| **Maximize Throughput** |1. Increase `ProvisionedPollerConfig` (`MinimumPollers` / `MaximumPollers`)<br>2. Increase `BatchSize` up to payload limit<br>3. Increase `ParallelizationFactor: 10` | Each Provisioned Event Poller supports up to **5 MB/sec** ingress and scales faster than default pollers |

---

## 5. Troubleshooting Amazon MSK & Self-Managed Kafka ESMs (`esm_kafka_troubleshoot`)

When a Kafka/MSK Event Source Mapping is stuck in `Creating`, `Enabling`, or `PROBLEM: Connection error`:

1. **Run `esm_kafka_troubleshoot`** (`kafka_type: "auto-detect"`, `issue_type: "diagnosis"`).
2. **Verify the 4 Most Common Root Causes**:
   - **SASL/SCRAM Secret Naming & KMS Key Rule (Amazon MSK)**:
     - The Secrets Manager secret name **MUST start with `AmazonMSK_`** (e.g., `AmazonMSK_orders_consumer`).
     - The secret **MUST be encrypted with a Customer Managed KMS Key (CMK)**—the default `aws/secretsmanager` key is rejected by MSK!
   - **Security Group Self-Referencing & Broker Ports**:
     - The MSK/Kafka cluster Security Group must allow inbound traffic from the ESM's Security Group on the exact broker port (`9092` plaintext, `9094` TLS, `9096` SASL/SCRAM, `9098` IAM).
   - **VPC Outbound Connectivity to AWS APIs**:
     - Self-managed Kafka ESMs (and MSK ESMs without PrivateLink) require outbound connectivity from the ESM subnets to `lambda.<region>.amazonaws.com`, `sts.<region>.amazonaws.com`, `secretsmanager.<region>.amazonaws.com`, and `kms.<region>.amazonaws.com` via **VPC Interface Endpoints** or a **NAT Gateway**.
   - **IAM Execution Role Permissions**:
     - Must include `kafka-cluster:Connect`, `kafka-cluster:DescribeGroup`, `kafka-cluster:AlterGroup`, `kafka-cluster:DescribeTopic`, `kafka-cluster:ReadData`, plus `ec2:CreateNetworkInterface`, `ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface`, `secretsmanager:GetSecretValue`, and `kms:Decrypt`.
