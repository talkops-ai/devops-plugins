# AWS Graviton4 Migration Matrix & S3 Storage Lens FinOps Reference

## 1. AWS Graviton (`arm64`) Price-Performance Migration Matrix

When auditing workloads via `bcm` (`list_recommendations`, `get_ec2_instance_recommendations`, `get_rds_database_recommendations`, `get_lambda_function_recommendations`), prioritize **Two-Way Door Graviton migrations** that deliver **20%–40% better price-performance**:

| AWS Service | x86_64 Legacy SKU | Graviton3 / Graviton4 (`arm64`) Target | Direct Unit Cost Reduction | Migration Effort & Compatibility Check |
|---|---|---|---|---|
| **AWS Lambda** | `Architectures: [x86_64]` | `Architectures: [arm64]` | **20% lower** per GB-second | Zero code changes for pure Python/Node.js/Java/.NET/Go; rebuild native C/C++/Rust wheels for `manylinux_aarch64`. |
| **Amazon ECS Fargate** | `X86_64` | `runtimePlatform.cpuArchitecture: ARM64` | **20% lower** per vCPU-hour & GB-hour | Multi-arch Docker build (`docker buildx build --platform linux/amd64,linux/arm64`). |
| **Amazon RDS / Aurora** | `db.m5` / `db.r5` / `db.m6i` / `db.r6i` | `db.m7g` / `db.r7g` / `db.r8g` | **Up to 20% lower** hourly rate + higher throughput | Fully managed engine binary; zero application code change (perform via RDS Blue/Green Deployment or Read Replica promotion). |
| **Amazon ElastiCache / MemoryDB** | `cache.m5` / `cache.r5` / `cache.r6i` | **ElastiCache for Valkey** on `cache.r7g` or Serverless | **~20% lower** for Graviton + **20%–33% lower** for Valkey vs Redis OSS | Drop-in wire-compatible upgrade from Redis OSS to Valkey. |
| **Amazon OpenSearch** | `m5` / `r5` / `r6i` | `m7g` / `r7g` / `or1` | **~15%–25% lower** cost per TiB indexed | Rolling blue/green domain configuration update. |
| **Amazon EC2 / EKS Nodes** | `m5` / `c5` / `r5` / `m6i` | `m7g` / `m8g` / `c7g` / `r7g` / `r8g` | **~20% lower** per vCPU-hour | In Karpenter `NodePool`, allow `kubernetes.io/arch: ["amd64", "arm64"]` with multi-arch container images. |

## 2. S3 Storage Lens High-ROI Audit Checks (`storage_lens_run_query`)

1. **Incomplete Multipart Upload Leaks**:
   - Check `IncompleteMultipartUploadStorageBytes` > 1% of bucket bytes.
   - **Remediation**: Add `AbortIncompleteMultipartUpload: { DaysAfterInitiation: 7 }` to every S3 bucket lifecycle configuration.
2. **Noncurrent Version Sprawl**:
   - Check `NonCurrentVersionStorageBytes` > 20% of total bucket bytes on versioned buckets.
   - **Remediation**: Add `NoncurrentVersionTransitions` (to `GLACIER_IR` after 30 days) and `NoncurrentVersionExpiration` (after 90–365 days) with `NewerNoncurrentVersions: 3`.
3. **Cold Standard Storage**:
   - Check buckets with low retrieval ratios (`GetRequests` / `StorageBytes`) sitting in `S3 Standard`.
   - **Remediation**: Transition objects `>= 128 KB` to **`INTELLIGENT_TIERING`** (zero retrieval fees, automatic Archive Instant Access tiering).
