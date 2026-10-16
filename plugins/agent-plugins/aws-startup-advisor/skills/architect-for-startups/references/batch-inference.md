# High-Throughput Batch AI Inference & Async Document Pipelines for Startups

Many startup AI workloads — nightly CRM enrichment, bulk PDF/document extraction, backfill embeddings, evaluation suites, and catalog classification — **do not require synchronous real-time (<2s) responses**. Running bulk workloads through synchronous real-time APIs burns 2x the budget and hits RPM/TPM throttling limits (`ThrottlingException`).

Load this reference whenever a startup processes bulk records, backfills data, runs offline evals, or hits Bedrock real-time quota limits.

---

## 1. Pattern 1: Amazon Bedrock Batch Inference (50% Token Discount — Default)

**Amazon Bedrock Batch Inference** runs asynchronous jobs against JSONL files in Amazon S3 at a **flat 50% discount** off On-Demand input and output token rates, with **separate quota pools** that never consume or throttle your customer-facing real-time traffic.

### Cost Comparison (100 Million Input + 20 Million Output Tokens)

| Model | Real-Time On-Demand Cost | Bedrock Batch Inference Cost (50% Off) | Savings per Run |
|---|---|---|---|
| **Claude Sonnet 5** (`anthropic.claude-sonnet-5`) | `$400.00` | **`$200.00`** | `$200.00` |
| **Claude Haiku 4.5** (`anthropic.claude-haiku-4-5-20251001-v1:0`) | `$200.00` | **`$100.00`** | `$100.00` |
| **Amazon Nova Lite** (`amazon.nova-lite-v1:0`) | `$10.80` | **`$5.40`** | `$5.40` |

### Reference Serverless Pipeline Architecture (`$0` Idle Cost)
1. **Ingest**: Upload records as `s3://<bucket>/batch-in/input.jsonl` (each line: `{"recordId": "001", "modelInput": {...}}`).
2. **Trigger**: S3 Event Notification or EventBridge Schedule invokes a lightweight **AWS Lambda** function calling `bedrock:CreateModelInvocationJob`.
3. **Completion Event**: EventBridge catches `Batch Inference Job State Change` (`Completed` / `Failed`) and triggers a post-processing Lambda to load `s3://<bucket>/batch-out/input.jsonl.out` into Postgres/DynamoDB.

---

## 2. Pattern 2: Queue-Buffered Micro-Batching (Minutes SLA: 1–15 Min Turnaround)

When Bedrock Batch Inference's multi-hour SLA is too slow (e.g., user uploads a 50-page pitch deck and expects results in 60 seconds), use **SQS + Lambda + Bedrock Cross-Region Inference (`us.anthropic.*`)**:

1. **API Gateway / Presigned S3 Upload** drops a job message onto an **Amazon SQS Standard Queue** (with a Dead-Letter Queue `maxReceiveCount = 3`).
2. **Lambda Event Source Mapping** sets `MaximumConcurrency` (e.g., `5`–`20` concurrent executions) to pace Bedrock `Converse` calls smoothly below your account's TPM/RPM ceiling.
3. **Prompt Caching Integration**: If all chunks from the same 50-page document share a common document prefix or system rubric, place the shared context in a `cachePoint` block (`cache_read_per_1k_usd` is **90% cheaper** than base input tokens).

---

## 3. Pattern 3: Spot GPU Batch Processing (`AWS Batch` for Custom Vision / Whisper / Embeddings)

For non-Bedrock models (e.g., Whisper audio transcription, custom YOLO/SAM vision models, or massive local BGE/E5 embedding backfills):

- Use **AWS Batch** with an **EC2 Spot Compute Environment** (`g6.xlarge`, `g6e.xlarge`, or `inf2.xlarge`, allocation strategy `SPOT_PRICE_CAPACITY_OPTIMIZED`).
- **Why**: Spot GPUs run at a **60–70% discount** (`~$0.28/hr` for `g6.xlarge`), scale from `minvCpus = 0` to `maxvCpus = 64` when jobs arrive in the queue, and scale back to **exact `$0.00/hr`** the moment the queue empties.
