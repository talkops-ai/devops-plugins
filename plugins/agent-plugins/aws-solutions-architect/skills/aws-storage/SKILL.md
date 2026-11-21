---
name: aws-storage
description: "Selects, investigates, and compares AWS object, file, and block storage services, and answers cost, performance, configuration, security, and troubleshooting questions about storage services. Applies when a user asks where to store or archive data based on their usage patterns; which storage service to choose or how two compare; how to migrate data from on-premises or between AWS services; how to protect, replicate, or recover data; how to optimize storage costs; where to deploy shared NFS, SMB, or POSIX file systems; where to store vector embeddings or tabular data; what storage backs enterprise file shares, self-managed databases on EC2, VMware, or stateful containers; or asks what an AWS storage service can do or how it works. Relevant for storage needs for workloads such as AI/ML, analytics, EDA, HPC, media, genomics, or financial trading. Not applicable for SQL query engines (Athena, Spark, Redshift, EMR), ETL (Glue), streaming (Kafka, MSK, Kinesis), or managed database services (RDS, Aurora, DynamoDB)."
metadata:
  version: "1"
---
## Overview

Domain expertise for choosing among AWS storage services, selecting storage classes, optimizing cost, and operating storage workloads:
- **Object storage**: S3 General Purpose buckets and storage classes, S3 Express One Zone (directory buckets), S3 Tables (managed Apache Iceberg), S3 Vectors, and S3 Metadata.
- **File storage**: Amazon EFS, S3 Files, FSx for Lustre, FSx for NetApp ONTAP, FSx for OpenZFS, and FSx for Windows File Server.
- **Block storage**: Amazon EBS (`gp3`, `io2` Block Express, `st1`, `sc1`) and EC2 Instance Store.
- **Data movement & protection**: AWS DataSync, AWS Storage Gateway, AWS Transfer Family, and AWS Backup.

## How to Handle User Queries

### Rules (Apply to All Responses)

1. **MCP-Only Execution & Live Verification (Zero Raw AWS CLI or Shell Directory Searches)**: Execute all live AWS discovery, telemetry, S3 Tables, IaC validation, and pricing lookups via connected MCP tools (`aws-mcp` `aws___call_aws` / `aws___run_script`, `s3tables`, `awspricing` `get_pricing`, `cloudwatch` `get_metric_data`, `awsiac`, `awsknowledge` `aws___search_documentation` / `aws___read_documentation`) in strictly read-only mode. **NEVER execute raw `aws` CLI or `ls`/`find` commands via `run_command` / `Bash`.** When handling a `/aws-storage:<command>` slash command (e.g., `/aws-storage:backup-and-replication-plan` or `/aws-storage:optimize-storage-tiers`), read `.agents/plugins/aws-storage/commands/<command>.md` directly, read only the directly relevant `references/*.md` files in `aws-storage` (do not activate extra secondary skills), batch all live AWS discovery into **1 consolidated `aws___run_script` call**, and skip `awspricing` calls unless the user explicitly asks for pricing/cost figures. Never fabricate resource ARNs, performance limits, or pricing figures; if `0` matching EBS volumes, EFS/FSx file systems, S3 Table buckets, or Backup vaults exist in the target region, report `0` honestly.
2. **Mandatory Reference Retrieval & `awsknowledge` Fallback**: Read the relevant local `references/*.md` file(s) from the **Routing** section below before answering questions about that service, and surface its operational gotchas (`< 128 KB` S3 Intelligent-Tiering/Glacier minimum size & 30/90/180-day duration traps, EBS Multi-Attach `xfs`/`ext4` corruption, EFS `50 KiB/s/GiB` burst credit exhaustion, Multi-AZ FSx ONTAP floating IP Transit Gateway requirement, S3 Tables `s3tables:*` & `maintenance.s3tables.amazonaws.com` KMS policy, Backup Vault Lock Compliance mode 3-day cooling-off window). If **no** local reference covers a niche edge case (e.g., S3 Metadata tables, Mountpoint for S3, or EBS Fast Snapshot Restore), immediately query the connected `awsknowledge` MCP server (`aws___search_documentation` / `aws___read_documentation` — 1–2 focused searches) and answer directly.
3. **Comprehensive Cost Analysis**: Always include TCO implications (storage capacity, per-request/IOPS fees, minimum storage duration charges, `128 KB` minimum billable object size padding, metadata/monitoring fees, retrieval fees, and cross-AZ/data-transfer costs). When querying `awspricing`, keep calls focused (1–3 targeted `get_pricing` lookups).
4. **Calibrated Specificity, Vague-Workload Guard & Read-Only/Secret Safety**: Match response specificity to the request. When key sizing metrics (capacity GiB/TiB, object size distribution, IOPS/throughput, access frequency, RPO/RTO) are missing, refuse to fabricate or guess specific monthly dollar totals or volume sizes and list the clarifying questions/CloudWatch metrics required. Never execute mutating storage commands (`s3 rb`, `s3 rm`, `ec2 delete-volume`, `efs delete-file-system`, `fsx delete-file-system`, `backup delete-recovery-point`) or fetch plaintext secrets (`secretsmanager get-secret-value`); whenever refusing `secretsmanager get-secret-value`, always explicitly recommend `aws secretsmanager describe-secret --secret-id <id>` for safe metadata verification.

---

### Step 1: Classify Intent

| Intent | Example Triggers | Action |
| --- | --- | --- |
| **SELECT** | "What should I use?", "Which service?", "Compare Service A vs Service B", "Help me choose", "Migrate X to AWS" | Follow **Step 2a: SELECT Path** |
| **INVESTIGATE** | "How do I configure Service X?", "Why is Service Y failing?", "What are the limits of Service Z?", "Reduce my storage bill" | Follow **Step 2b: INVESTIGATE Path** |

---

### Step 2a: SELECT Path

Evaluate these 5 decision factors, retrieve the candidate reference files from **Routing**, and recommend the best-fit service(s) with clear trade-off rationale:

| # | Decision Factor | Key Questions to Evaluate |
| --- | --- | --- |
| 1 | **Workload Context** | New build or migration (NetApp, ZFS, Windows File Server, Lustre, GPFS)? Access interface (REST/S3 API, NFS, SMB, iSCSI/NVMe-oF, POSIX block)? Client platform (EC2, EKS, ECS/Fargate, Lambda, on-prem) and data model (objects, Iceberg tables, vector embeddings, shared files, block)? |
| 2 | **Capacity & Access Patterns** | Total volume, object/file count, and average object/file size (e.g., `< 128 KB` small-object overhead in S3 Intelligent-Tiering/Glacier)? Sequential vs. random I/O? Read/write ratio? |
| 3 | **Performance Requirements** | Target latency (sub-ms, single-digit ms, or archive), IOPS, aggregate throughput (MiB/s or GB/s), and client concurrency? |
| 4 | **Durability & Data Protection** | Required RPO/RTO, cross-region replication (CRR/SnapMirror), WORM immutability (S3 Object Lock, SnapLock, Backup Vault Lock), and compliance mandates? |
| 5 | **Availability** | Multi-AZ Regional vs. Single-AZ / One Zone (S3 Express One Zone, EFS One Zone, Single-AZ FSx) co-located with compute? |

---

### Step 2b: INVESTIGATE Path

1. Classify the question domain, retrieve the relevant reference file(s) from **Routing**, and provide actionable guidance, CLI/MCP checks, gotchas, and observability recommendations (S3 Server Access Logs, CloudTrail Data Events, CloudWatch Metrics, Storage Lens):

| Question Domain | Example Triggers | What to Clarify / Verify |
| --- | --- | --- |
| **Migration & Data Transfer** | "Move data to AWS", "Set up DataSync", "Sync on-prem NFS to EFS/S3" | Source system/protocol, destination service, data volume/file count, network link (Direct Connect, VPN, internet) |
| **Data Protection & Resiliency** | "Set up backup", "Cross-region replication", "RTO under 1 hour", WORM | Failure scenario, RPO/RTO targets, replication scope (same-region, cross-region, cross-account) |
| **Cost & Lifecycle** | "Reduce storage bill", "Right-size volumes", "gp2 to gp3", tiering rules | Current service/class, object size distribution (`>= 128 KB` check), access frequency, minimum duration rules (30/90/180 days) |
| **Performance** | "Reads are slow", "Throughput bottleneck", "Need more IOPS" | Observed vs. required latency/IOPS/throughput, sequential vs. random I/O, burst credits / throughput mode |
| **Security & Compliance** | "Encrypt at rest", "Restrict bucket access", "Block Public Access", HIPAA | Access control boundary, KMS CMK vs. SSE-S3, Bucket Keys, TLS enforcement, VPC endpoints |
| **Configuration & Guidance** | "Mount EFS on EKS/Lambda", "Set up S3 Tables", deployment best practices | Client compute environment, VPC/subnet topology, IAM/mount options |
| **Troubleshooting** | "403 AccessDenied", "EFS mount hanging", "503 SlowDown", lifecycle stuck | Exact error code, recent IAM/network/KMS changes, target region (`AWS_REGION`) |

---

## Storage Options

See [Block, file, and object storage compared](https://aws.amazon.com/compare/the-difference-between-block-file-object-storage/).

### Object Storage

| Service | Key Characteristics | Common Workloads |
| --- | --- | --- |
| **S3 General Purpose** | Elastic regional object storage across Standard, Intelligent-Tiering, Standard-IA, One Zone-IA, Glacier Instant/Flexible/Deep Archive; lifecycle transitions and replication. | Data lakes, backups/archives, ML training datasets, media/CDN origin, logs, static assets, compliance WORM archives |
| **S3 Express One Zone** | Single-AZ directory buckets (`--x-s3`) delivering consistent single-digit millisecond latency and high request rates with session-based (`CreateSession`) auth. | Latency-sensitive ML training/inference, Spark/EMR shuffle, checkpoints, interactive hot analytics, high-TPS transactional objects |
| **S3 Tables** | Managed Apache Iceberg tables (`s3tables` MCP) with automatic compaction, snapshot expiration, and unreferenced file cleanup for SQL engines. | Lakehouse tabular datasets, streaming/ETL Iceberg outputs, Athena/EMR/Redshift Spectrum/DuckDB analytics |
| **S3 Vectors** | Native cost-effective vector storage and similarity search with S3 durability and elasticity. | RAG pipelines, semantic search, recommendation engines, large-scale embedding storage |
| **S3 Metadata** | Managed read-only Apache Iceberg tables automatically indexing S3 object system/user metadata and tags. | Content cataloging, storage governance, compliance auditing, AI agent discovery |

### File Storage

Always specify the full service name (**FSx for Lustre**, **FSx for Windows File Server**, **FSx for NetApp ONTAP**, **FSx for OpenZFS**). Both **Amazon EFS** and **S3 Files** can be mounted by Lambda and Fargate; **FSx for NetApp ONTAP** and **FSx for OpenZFS** expose file data to S3/serverless consumers via **S3 Access Points for FSx**.

| Service | Key Characteristics | Common Workloads |
| --- | --- | --- |
| **Amazon EFS** | Serverless elastic POSIX/NFSv4.1 file storage (Standard, IA, Archive classes; Elastic, Provisioned, or Bursting throughput; Regional Multi-AZ or One Zone). | Shared container/serverless storage (EKS, ECS, Fargate, Lambda), Linux web/CMS apps, ML home directories |
| **FSx for Lustre** | High-throughput parallel POSIX file system (SSD and elastic Intelligent-Tiering classes) with native S3 data repository integration. | Distributed ML/GPU training, HPC, genomics, seismic/financial modeling, EDA |
| **FSx for OpenZFS** | Managed ZFS file system (SSD and Intelligent-Tiering; Single-AZ/Multi-AZ) with sub-ms latency, instant copy-on-write clones, snapshots, compression, and S3 Access Points. | Low-latency Linux/ZFS migrations, EC2 databases, fast dev/test cloning, front-end EDA, financial trading |
| **FSx for NetApp ONTAP** | Managed enterprise ONTAP NAS/SAN (NFS, SMB, iSCSI, NVMe-oF, plus S3 Access Points; Single-AZ/Multi-AZ) with SnapMirror, FlexClone, inline dedup/compression, and SnapLock WORM. | Enterprise NAS migrations, multi-protocol (NFS+SMB) shares, SAP HANA/Oracle/SQL Server on EC2, VMware, hybrid DR |
| **FSx for Windows File Server** | Managed native Windows SMB file storage (Single-AZ/Multi-AZ) with Active Directory/Kerberos, NTFS ACLs, DFS Namespaces, Shadow Copies, and FSRM quotas. | Windows shared folders, .NET enterprise apps, SQL Server Failover Cluster Instances (FCI) |

### Block Storage

| Service | Key Characteristics | Common Workloads |
| --- | --- | --- |
| **Amazon EBS** | Network-attached AZ-scoped block volumes (`gp3` baseline 3,000 IOPS / 125 MiB/s with independent scaling; `io2` Block Express up to 256,000 IOPS and 99.999% durability; `st1`/`sc1` HDD), snapshots, Fast Snapshot Restore (FSR). | Self-managed relational/NoSQL databases on EC2, boot volumes, low-latency transactional workloads |
| **EC2 Instance Store** | Host-local ephemeral NVMe SSD delivering extreme IOPS and lowest latency; data does not survive instance stop/termination. | Ephemeral scratch space, distributed caches, shuffle buffers, replicated node storage |

---

## Cross-Service Protocol Bridges

| Feature | What It Enables | Reference |
| --- | --- | --- |
| **S3 Files** | Managed POSIX/NFSv4 file access directly over an S3 bucket (built on EFS infrastructure; S3 remains system of record with file locking and POSIX permissions). | `references/s3-files-knowledge.md`, `references/efs-knowledge.md` |
| **S3 Access Points for FSx** | Exposes FSx for NetApp ONTAP or FSx for OpenZFS file data directly through the S3 REST API without data duplication. | `references/fsx-ontap-knowledge.md`, `references/fsx-openzfs-knowledge.md` |

---

## Security Baseline

Always enforce these controls when recommending or auditing storage:
- **Encryption**: Enable encryption at rest (KMS CMK or SSE-S3; enable S3 Bucket Keys to cut KMS costs by up to 99%; note EFS/EBS/FSx encryption at rest must be enabled at creation) and in transit (`aws:SecureTransport: true` on S3, TLS mount options on EFS/FSx).
- **Access & Perimeter**: Enforce S3 Block Public Access (all 4 settings `true`) and `BucketOwnerEnforced` (disable ACLs). Scope IAM policies to least privilege, add confused-deputy conditions (`aws:SourceArn`, `aws:SourceAccount`, `aws:PrincipalOrgID`), and restrict EFS/FSx security groups to specific client security groups on port `2049` (NFS) or `445` (SMB).
- **Audit Logging**: Encrypt CloudTrail Data Events, CloudWatch Logs, and S3 Server Access Logs with KMS.

---

## Routing

### Local Reference Files (Read Before Answering)

| Topic | Reference |
| --- | --- |
| S3 General Purpose & S3 Metadata | `references/s3-general-purpose-knowledge.md` |
| S3 Tables (Managed Iceberg) | `references/s3-tables-knowledge.md` |
| S3 Vectors | `references/s3-vectors-knowledge.md` |
| S3 Express One Zone | `references/s3-express-knowledge.md` |
| S3 Files | `references/s3-files-knowledge.md` |
| Amazon EFS | `references/efs-knowledge.md` |
| FSx for Lustre | `references/fsx-lustre-knowledge.md` |
| FSx for NetApp ONTAP | `references/fsx-ontap-knowledge.md` |
| FSx for OpenZFS | `references/fsx-openzfs-knowledge.md` |
| FSx for Windows File Server | `references/fsx-windows-knowledge.md` |
| Amazon EBS & Instance Store | `references/ebs-knowledge.md` |
| Data Movement & Protection (DataSync, Transfer Family, Storage Gateway, AWS Backup) | `references/data-movement-and-protection-knowledge.md` |

### Companion Specialized Skills

| Topic | Skill Name |
| --- | --- |
| S3 Security Hardening & Audits | `securing-s3-buckets` |
| Troubleshooting S3 & S3 Files (`403`/`503`/`404`) | `troubleshooting-s3-files` |
| Troubleshooting Amazon EFS Mounts & Throughput | `troubleshooting-efs` |
| Multi-Region DR & Backup Architecture | `aws-resilience-dr-and-migration-architecture` |
| KMS, Object Lock & Macie Data Protection | `security-data-protection` |
