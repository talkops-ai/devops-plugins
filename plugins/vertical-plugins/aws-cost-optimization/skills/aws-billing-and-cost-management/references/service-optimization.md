# Per-Service & Workload FinOps Optimization Playbooks

> **Pricing note:** All prices shown are `us-east-1` approximate as of early 2026. Prices vary by region and may change. Always verify current pricing via `awspricing:get_pricing` or `billing:aws-pricing` before reporting to users.

High-ROI architectural and per-service optimizations that do not require 1-year or 3-year commitment purchases. Prioritize by estimated monthly savings and zero-downtime reversibility.

---

## 1. Amazon S3 & Storage Lens Optimization (`billing:storage-lens`)

| Strategy | Savings | When to Recommend |
|----------|---------|------|
| **Abort Incomplete Multipart Uploads** (`AbortIncompleteMultipartUpload: 7 days`) | **100% of orphaned part storage** | Every S3 bucket (`IncompleteMultipartUploadStorageBytes > 0` in Storage Lens) |
| **S3 Bucket Keys (`BucketKeyEnabled: true`)** | **Up to 99% of KMS request charges** | Any S3 bucket using `aws:kms` (SSE-KMS) encryption |
| **Intelligent-Tiering** | Auto-optimized (up to 68%–95%) | Unknown or shifting access patterns, **average object size ≥ 128 KB** |
| **Lifecycle to S3 Standard-IA** | ~45% storage | Known infrequent access after 30+ days, objects ≥ 128 KB |
| **Lifecycle to Glacier Instant Retrieval** | ~68% storage | Medical/media/archive accessed 1–4x/yr, millisecond retrieval, objects ≥ 128 KB |
| **Lifecycle to Glacier Deep Archive** | ~95% storage ($0.00099/GB-mo) | Compliance retention, 12+ hour restore acceptable |

### Critical S3 Gotchas & Storage Lens Audit (`billing:storage-lens`)
- **The 128 KB Minimum Object Size Trap:** S3 Intelligent-Tiering does **not** auto-tier objects `< 128 KB` (they stay in Frequent Access forever), and S3 Standard-IA, One Zone-IA, and Glacier Instant Retrieval bill a **minimum of 128 KB per object** plus **$0.01–$0.02 per 1,000 transition requests**. Always calculate `avg_object_size_kb = (TotalStorageBytes / ObjectCount) / 1024` via `billing:storage-lens` (`storage_lens_run_query`) before recommending IA/Glacier/IT!
- **Minimum Storage Durations:** S3-IA (30 days), Glacier IR (90 days), Glacier Flexible (90 days), Deep Archive (180 days) — early deletion or overwrite incurs prorated charges.
- **Versioned Buckets:** Always pair `NoncurrentVersionTransition` with `NoncurrentVersionExpiration` and `ExpiredObjectDeleteMarker: true` — otherwise overwritten/deleted objects accumulate indefinitely.

---

## 2. Network, NAT Gateway & VPC Endpoint Break-Even Math

### A. NAT Gateway vs. VPC Endpoints
NAT Gateway charges **~$0.045/hr (~$32.85/month per AZ)** + **~$0.045/GB processed** (`NatGateway-Bytes`). It is frequently the #1 surprise line item under `EC2 - Other`.

1. **Always create FREE Gateway Endpoints for S3 and DynamoDB ($0.00/hr and $0.00/GB):**
   ```bash
   aws ec2 create-vpc-endpoint --vpc-id vpc-123abc \
     --service-name com.amazonaws.<REGION>.s3 --route-table-ids rtb-123abc
   ```
   Eliminates 100% of `$0.045/GB` NAT Gateway charges for S3 and DynamoDB traffic in private subnets.
2. **VPC Interface Endpoints (PrivateLink) Break-Even Formula (~209 GB/month per AZ):**
   - VPC Interface Endpoint cost: **`$7.30/month/AZ`** (`$0.01/hr × 730`) + **`$0.01/GB`**.
   - Net variable savings vs. NAT Gateway: `$0.045 - $0.010 = $0.035/GB`.
   - **Break-Even Volume per AZ:** `$7.30 / $0.035 = 208.6 GB/month per AZ` (~`626 GB/month` across 3 AZs).
   - Recommend Interface Endpoints for `ecr.dkr`, `ecr.api`, `logs` (CloudWatch Logs), `sts`, `kms`, `ssm`, `secretsmanager`, or `bedrock-runtime` whenever private-subnet traffic to that service exceeds ~209 GB/mo/AZ.

### B. Cross-AZ Data Transfer (`Regional-Bytes` — $0.02/GB Round-Trip) & Public IPv4 ($3.65/mo)
- **Cross-AZ (`$0.01/GB` Out + `$0.01/GB` In = `$0.02/GB`):** Enable AZ-local routing (ALB/NLB target group AZ affinity, EKS Topology Aware Hints, MSK rack-aware consumers, ElastiCache/RDS same-AZ replica reads).
- **Internet Egress (`DataTransfer-Out-Bytes`, $0.09/GB):** Place Amazon CloudFront in front of S3/ALB origins ($0.00 origin fetch fee + lower edge egress + CloudFront Security Savings Bundle 30% discount).
- **Public IPv4 Addresses (`$0.005/hr = $3.65/mo` each):** Release idle Elastic IPs, disable `MapPublicIpOnLaunch` on subnets, and use IPv6 (`dualstack`).

---

## 3. Generative AI & ML FinOps (Amazon Bedrock & SageMaker AI)

### A. Amazon Bedrock Token & Architecture Optimization
1. **Batch Inference (50% Discount):** Use Bedrock Batch Inference for asynchronous workloads (bulk summarization, document extraction, classification, offline evals) for an immediate **50% token discount**.
2. **Prompt Caching (Up to 90% Discount on Cached Input Tokens):** Enable `cachePoint` on long system prompts, large MCP tool definitions, and multi-turn RAG documents to cut cached input token costs by **up to 90%** and reduce time-to-first-token by up to 85%.
3. **Intelligent Prompt Routing & Model Tiering (80%–95% Savings):** Route classification, extraction, and simple Q&A from frontier models (Claude Opus / Sonnet) to smaller models (Claude Haiku / Amazon Nova Micro or Lite).
4. **Provisioned Throughput (Model Units) Break-Even:** Only purchase Bedrock Provisioned Throughput when sustained 24x7 token utilization exceeds **65%–70%** of Model Unit capacity; otherwise On-Demand + Prompt Caching + Cross-Region Inference (CRI) is far cheaper.
5. **The Bedrock Knowledge Base Vector Store Cost Trap ($350.40+/mo Floor):**
   - Default **Amazon OpenSearch Serverless (AOSS)** vector collections require a minimum of **2 OCUs** (4 OCUs with HA) at `$0.24/OCU-hr` = **$350.40 to $700.80/month minimum**, even at 0 queries!
   - Use `awspricing:get_bedrock_patterns` to inspect alternatives: recommend **Amazon S3 Vectors** or **Aurora PostgreSQL Serverless v2 (`pgvector`) with `MinCapacity=0.0` (auto-pause) or `0.5 ACU` (~$43.80/mo)** to save **85%–98%** on small-to-medium Knowledge Bases.

### B. Amazon SageMaker AI
- **Idle Real-Time Endpoints:** Check CloudWatch `AWS/SageMaker` `Invocations` (`Sum` over 14 days). Delete zero-invocation endpoints, consolidate multi-model workloads onto **Inference Components**, or migrate spiky endpoints to **SageMaker Serverless Inference** / **Asynchronous Inference** (scales to 0).
- **Idle Studio Spaces & Notebooks:** Enforce auto-shutdown extensions (60-minute idle timeout) on `ml.g5` / `ml.p4d` Studio Spaces.
- **Managed Spot Training:** Set `EnableManagedSpotTraining=True` with S3 checkpointing for **up to 70%–90% savings**.

---

## 4. Containers & Kubernetes FinOps (EKS, Karpenter, ECS & Fargate)

- **EKS/ECS Split Cost Allocation Data:** Query CUR 2.0 ([`cur-athena.md`](./cur-athena.md) Query 6) to separate utilized pod cost (`split_line_item_net_split_cost`) from unallocated node slack (`split_line_item_net_unused_cost`).
- **Karpenter Node Consolidation:** When node slack exceeds 25%, migrate from static Managed Node Groups to **Karpenter** (`consolidationPolicy: WhenEmptyOrUnderutilized`) with multi-family Graviton (`m7g`, `c7g`, `r7g`) and Spot/On-Demand `NodePool` specs (**30%–55% compute reduction**).
- **Fargate Spot & ARM64:** Combine `ARM64` task definitions (20% cheaper) with `FARGATE_SPOT` capacity providers (**up to 70% discount**, 2-minute `SIGTERM` warning; keep `FARGATE` `base=1` or `2` covered by Compute Savings Plans).

---

## 5. DynamoDB, ElastiCache, Glue & Observability FinOps

### A. Amazon DynamoDB
- **Capacity Mode:** On-Demand (after AWS's 50% price reduction) is ideal for spiky traffic (peak-to-average `> 2.5x`); Provisioned + Auto Scaling remains **30%–50% cheaper** for steady-state workloads (`> 45%` utilization). **Database Savings Plans** now cover DynamoDB!
- **Standard-IA Table Class (60% Storage Discount):** Switch a table to `Standard-IA` when monthly storage cost exceeds **~42% of monthly throughput (RCU+WCU) cost**.
- **TTL Free Deletes:** Use DynamoDB **Time-To-Live (TTL)** (`$0.00` / 0 WCUs) to expire old items instead of `Scan` + `DeleteItem` (which burns full WCUs).
- **Orphaned GSIs:** Delete any Global Secondary Index with `ConsumedReadCapacityUnits == 0` over 30 days in CloudWatch.

### B. ElastiCache & Analytics (Glue, Athena, Redshift)
- **ElastiCache for Valkey on Graviton (`cache.r7g`):** Upgrading Redis OSS to **Valkey on Graviton** delivers an immediate **20%–33% AWS price reduction**.
- **AWS Glue FLEX Execution Class:** Switch non-urgent batch ETL jobs from `STANDARD` ($0.44/DPU-hr) to `FLEX` (**$0.29/DPU-hr — 34% savings**) with `EnableAutoScaling=True`.
- **Redshift Serverless RPU Caps:** Configure `UsageLimits` (`max-rpu-hours`) on Redshift Serverless workgroups to prevent runaway dashboard queries.

### C. Observability & Security (CloudWatch, AWS Config, CloudTrail, KMS)
- **CloudWatch Logs Standard ($0.50/GB) vs. Infrequent Access ($0.25/GB — 50% Savings):**
  - Use `INFREQUENT_ACCESS` log class for high-volume container, debug, and audit logs that do not need real-time Metric Filters, Subscription Filters, or Live Tail.
  - Set explicit `retentionInDays` (14–90 days) on all log groups (`Never Expire` accumulates at $0.03/GB-month).
  - Route **VPC Flow Logs** and **ALB Access Logs** directly to **S3 (Parquet)** instead of CloudWatch Logs Standard.
- **AWS Config Recording Storms ($0.003/CI):** Switch high-churn ephemeral resource types (e.g., container ENIs) from Continuous Recording to **Daily Periodic Recording** or scoped exclusions.
- **Duplicate CloudTrail Trails:** The first management event trail per region is free; duplicate trails cost **$2.00 per 100,000 events**. Consolidate into a single Organization Trail.

---

## 6. Unit Economics KPIs

Correlate `AmortizedCost` (`EffectiveCost`) against business output metrics via `billing:session-sql` or Python:
- **Cost per 1,000 API Requests:** `Workload_Amortized_Cost / (ALB_or_APIGW_Requests / 1000)`
- **Cost per Active Tenant:** `(Direct_Tenant_Tagged_Cost + Proportional_Shared_Platform_Cost) / Active_Tenants`
- **Cost per 1M AI Tokens / Agent Resolution:** `(Bedrock_Inference_Cost + Vector_Store_Cost) / Successful_Resolutions`
