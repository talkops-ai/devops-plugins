# AWS Service Trade-Off Matrices (2026 SAP-C02 Reference)

Use these reference matrices to ground ADR option evaluations before querying `awspricing` and `awsknowledge` for exact regional numbers.

## 1. Compute Runtime Trade-Off Matrix

| Dimension | AWS Lambda | Amazon ECS Fargate / Express Mode | Amazon ECS Managed Instances | Amazon EKS (Auto Mode / Karpenter) |
|---|---|---|---|---|
| **Ideal Workload** | Spiky, event-driven APIs & async workers (<15 min) | Steady/variable containerized services without K8s overhead | High-throughput containers needing EC2 Savings Plans, GPU, or high disk I/O | Multi-team platforms needing Kubernetes APIs/CRDs, service mesh, or portability |
| **Scale-to-Zero** | Native (`$0` idle unless Provisioned Concurrency) | Min tasks = 0 (event-scaled) or 1+ for ALB HA | Requires ASG/Capacity Provider min capacity | Pod scale-to-zero via KEDA; `$73/mo` control plane fixed floor |
| **Max Execution / Timeout** | 15 minutes (Standard); longer via Lambda Durable Functions | Unlimited | Unlimited | Unlimited |
| **Pricing Crossover** | Lowest cost below ~20–30% average utilization | Cost-effective for 24/7 HTTP APIs with Fargate Compute Savings Plans | Lowest unit cost at steady high scale with EC2 Instance Savings Plans | Best amortized across 10+ microservices sharing Karpenter Spot/Graviton nodes |
| **Reversibility** | Two-Way Door (if using Lambda Web Adapter / standard HTTP) | Two-Way Door (OCI container image) | Two-Way Door (same ECS Task Definition) | One-Way Door (adopting Kubernetes control plane & CRD ecosystem) |

## 2. Transactional & Operational Database Trade-Off Matrix

| Dimension | Amazon DynamoDB | Amazon Aurora PostgreSQL / MySQL (Serverless v2 / Provisioned) | Amazon Aurora DSQL | Amazon DocumentDB / MemoryDB (Valkey) |
|---|---|---|---|---|
| **Data Model & Joins** | Key-Value / Wide-Column; single-table design; no SQL joins | Full relational SQL, ACID, pgvector, triggers, foreign keys | Distributed PostgreSQL-compatible SQL with ACID & optimistic concurrency | JSON Document (`DocumentDB`) or In-Memory Durable Key-Value (`MemoryDB`) |
| **Multi-Region Active-Active** | Global Tables (eventual consistency or MRSC strong consistency) | Global Database (single writer region + read replicas + write forwarding; `<1s` RPO) | Native active-active multi-region strong consistency (zero replication lag) | Global Clusters (single primary + secondary read regions) |
| **Connection Management** | HTTP/HTTPS stateless API (no connection pool exhaustion) | Requires **RDS Proxy** or connection pooling for Lambda/serverless bursts | Stateless IAM-authenticated connections; scales automatically | Stateful TCP connections (use VPC PrivateLink / security groups) |
| **Operational Quotas & Gotchas** | 400 KB max item size; 1,000 WCU / 3,000 RCU per physical partition | ACU scaling increments (0.5 ACU); storage I/O-Optimized vs Standard pricing crossover at ~25% I/O spend | Optimistic Concurrency Control (OCC) retries on hot-row contention; subset of PG extensions | DocumentDB emulates MongoDB API; MemoryDB stores dataset in RAM + Multi-AZ transaction log |

## 3. Asynchronous Messaging & Event Streaming Trade-Off Matrix

| Dimension | Amazon SQS (Standard / FIFO) | Amazon SNS + SQS Fan-Out | Amazon EventBridge (Event Bus / Pipes) | Amazon Kinesis Data Streams / Amazon MSK |
|---|---|---|---|---|
| **Primary Pattern** | Point-to-point queue buffering, work queues, DLQ redrive | High-throughput pub/sub fan-out to multiple independent queues | Schema-driven event routing, SaaS partner events, content/prefix filtering | High-throughput ordered log streaming, replay, stateful stream processing (Flink) |
| **Ordering & Deduplication** | Best-effort (Standard) or exact-once per `MessageGroupId` (FIFO up to 70k TPS) | Supports FIFO topic-to-FIFO queue strict ordering | Best-effort ordering; EventBridge Pipes preserves source order (1-to-1) | Strict per-shard (`Kinesis`) or per-partition (`MSK`) ordering |
| **Retention & Replay** | Up to 14 days (deleted upon consumption) | No native retention (use SQS subscribers or EventBridge Archive) | EventBridge Archive & Replay (up to indefinite retention) | 24h to 365 days (`Kinesis`); configurable tiered storage (`MSK`) |

## 4. Analytical & Lakehouse Storage Trade-Off Matrix

| Dimension | Amazon S3 Tables (Managed Apache Iceberg) | Standard S3 + Glue Data Catalog (Parquet/Iceberg) | Amazon Redshift (Serverless / RA3 Provisioned) | Amazon OpenSearch Service (Provisioned / Serverless) |
|---|---|---|---|---|
| **Primary Use Case** | Petabyte-scale transactional lakehouse with ACID upserts/deletes & automatic compaction | Raw bronze/silver object storage + multi-engine lake access | High-concurrency BI dashboards, complex star-schema joins, materialized views | Full-text lexical search (BM25), log analytics (PPL), k-NN vector search |
| **Maintenance Overhead** | Fully managed automatic compaction, snapshot expiration, and unreferenced file cleanup | Requires configuring Glue Iceberg compaction jobs & lifecycle rules | Automated table optimization (Auto Vacuum/Sort/DistKey) | Index lifecycle management (ISM) or OpenSearch Serverless OCU auto-scaling |
