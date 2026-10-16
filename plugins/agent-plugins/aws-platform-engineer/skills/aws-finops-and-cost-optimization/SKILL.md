---
name: aws-finops-and-cost-optimization
description: Generates pre-deployment AWS unit price and monthly run-rate estimates via the pricing MCP server, audits existing account spend and idle resources via the billing-cost MCP server (Cost Explorer, Cost Optimization Hub, Compute Optimizer), right-sizes compute/networking/storage tiers, and enforces mandatory cost-allocation tags.
metadata:
  version: "2.0"
---

# AWS FinOps and Platform Cost Optimization

## Purpose

Prevent surprise cloud bills and architectural cost leaks across non-production and production AWS environments. Application developers and QA engineers rarely anticipate compounding AWS cost mechanics—such as `$32.40/mo/AZ + $0.045/GB` per NAT Gateway, `$73/mo` per EKS cluster control plane, Cross-AZ data transfer (`$0.02/GB` round-trip), or `t3`/`t4g` unlimited CPU credit surplus charges. This skill enforces **Shift-Left FinOps** (pre-deployment cost modeling via `pricing` MCP) and **Day-2 FinOps** (idle resource elimination and right-sizing via `billing-cost` MCP).

---

## Mandatory Platform FinOps Workflow

### 1. Pre-Deployment Unit Price & Monthly Run-Rate Estimation (`pricing` MCP)

Before provisioning any new environment, cluster, database, or network stack, query the `pricing` MCP server (`awslabs.aws-pricing-mcp-server`) for the target `AWS_REGION` and present a structured Markdown cost table:

| Cost Component | Baseline Unit Price Mechanics (`us-east-1` reference; always verify regional price via `pricing` MCP) | Dev / QA Cost-Optimization Lever |
|---|---|---|
| **Amazon EKS Control Plane** | `$0.10/hr` (`~$73.00/mo`) standard support; `$0.60/hr` (`~$438/mo`) on Extended Support for deprecated K8s versions | Keep clusters on standard-support Kubernetes versions (`get_eks_insights`); share a multi-namespace Dev/QA cluster with network policies & ResourceQuotas instead of 1 cluster per developer, or use **ECS Fargate / ECS Express Mode** (`$0.00` control-plane fee). |
| **VPC NAT Gateway** | `~$0.045/hr` (`~$32.40/mo/AZ`) + `$0.045/GB` data processed (`~$97.20/mo` base for 3 AZs before traffic) | Attach **free S3 & DynamoDB Gateway Endpoints (`$0.00`)** to every private route table; use Interface Endpoints (`~$7.20/mo/AZ`) when monthly ECR/Logs/Secrets traffic exceeds `~160 GB/AZ`; use Dual-Stack **IPv6 Egress-Only Internet Gateway (`$0.00`)** for public outbound IPv6 traffic; use 1 NAT Gateway for `dev`/`qa`. |
| **EC2 / EKS Nodes / ECS Fargate** | On-Demand x86 (`amd64`) vs Graviton (`arm64`) vs Spot | Default to **AWS Graviton3/4 (`arm64`)** (`t4g`, `m7g`, `c7g`, `r7g`, or Fargate `ARM64`) for up to **20% lower cost and 40% better price-performance**; use **Fargate Spot** or **Karpenter Spot consolidation** (`WhenEmptyOrUnderutilized`) for up to 70% savings on stateless workloads. |
| **Aurora / RDS Databases** | Provisioned instance hours + storage (`$0.10/GB-mo`) + I/O (Standard) vs I/O-Optimized | Use **Aurora Serverless v2** with `MinCapacity: 0` (scale-to-zero after idle timeout) for `dev`/`qa`; for `prod` workloads where I/O charges exceed 25% of database spend, switch to **Aurora I/O-Optimized**. |
| **Amazon EBS Volumes** | `gp2` (`$0.10/GB-mo`, IOPS tied to size) vs `gp3` (`$0.08/GB-mo`, 3,000 IOPS + 125 MB/s free baseline) | Always provision **`gp3`** (20% cheaper per GB than `gp2` with decoupled IOPS/throughput); delete unattached `available` volumes and stale snapshots. |
| **CloudWatch Logs & WAF** | Standard Logs ingestion (`$0.50/GB`) + storage (`$0.03/GB-mo`) | Use **CloudWatch Logs Infrequent Access (`$0.25/GB` — 50% cheaper)** for verbose VPC Flow Logs, WAF logs, and container stdout; always set explicit `RetentionInDays` (`7`/`14` for non-prod, `30`–`90` for prod); filter WAF logs to `BLOCK`/`COUNT`. |

---

### 2. High-Impact Platform Cost Traps to Block Proactively

1. **T3 / T3a / T4g `unlimited` CPU Credit Leak**:
   - Burstable instances launch in `unlimited` mode by default. If a misconfigured container or background cron job pegs CPU above the baseline (20%–40%), AWS bills `$0.05/vCPU-hour` in surplus credits—making a `t3.medium` cost more than an `m7g.large`.
   - **Fix**: Set `CreditSpecification: { CpuCredits: standard }` for non-prod, or right-size sustained CPU workloads to `m7g`/`c7g` fixed-performance instances.
2. **Cross-AZ Data Transfer Bleed (`$0.02/GB` Round-Trip)**:
   - Chatty microservices, Kafka/MSK brokers, or ElastiCache clusters communicating across Availability Zones incur `$0.01/GB` egress + `$0.01/GB` ingress (`$0.02/GB` total).
   - **Fix**: Enable **ALB Cross-Zone Load Balancing / Target Group AZ Affinity**, Kubernetes **Topology Aware Routing** (`service.kubernetes.io/topology-mode: Auto`), and read-from-local-AZ replica policies on ElastiCache and Aurora.
3. **ECR Pulls Through NAT Gateway**:
   - Pulling a 2 GB container image across 50 ECS/EKS tasks without VPC endpoints sends 100 GB through NAT Gateway (`$4.50` per rollout).
   - **Fix**: Provision `com.amazonaws.<region>.ecr.api` and `com.amazonaws.<region>.ecr.dkr` Interface Endpoints **plus** the free `com.amazonaws.<region>.s3` Gateway Endpoint (since ECR stores image layers in S3).

---

### 3. Live Account Spend, Idle Resource & Commitment Auditing (`billing-cost` MCP)

When optimizing an existing AWS account, orchestrate the `billing-cost` MCP server (`awslabs.billing-cost-management-mcp-server`) alongside `cloudwatch`:
1. **Cost Explorer & Variance Triage**:
   - Query `cost-explorer` / `cost-comparison` grouped by `SERVICE`, `USAGE_TYPE`, `LINKED_ACCOUNT`, and cost-allocation tags to isolate month-over-month spend drivers (always inspect both `UnblendedCost` and `NetAmortizedCost`).
2. **Idle & Right-Sizing Recommendations**:
   - Query `compute-optimizer` (`get_idle_recommendations`) and `cost-optimization` (Cost Optimization Hub) to surface:
     - Idle EC2 instances, unattached Elastic IPs (`$3.60/mo` each), idle ALBs/NLBs (`$16.20/mo` with `ActiveConnectionCount == 0`), unattached EBS volumes, and over-provisioned ECS/Lambda/RDS resources.
   - **Two-Key Verification**: Before downsizing any production compute or database resource, cross-check 14-day **P95/P99** `CPUUtilization` and memory/connection metrics in `cloudwatch` (`get_metric_data`) to ensure peak burst traffic will not be throttled.
3. **Savings Plans & Reserved Instance Coverage**:
   - Inspect Savings Plans / RI coverage and utilization via `billing-cost` tools; flag expiring commitments or low utilization before recommending instance-family migrations.

---

### 4. Mandatory Cost-Allocation Tagging Governance

Every CloudFormation stack, CDK app, SAM template, and Terraform module authored by this plugin **must** apply these five standard tags at the root stack/provider level:
- `Environment`: `dev` | `qa` | `staging` | `prod`
- `Owner`: team or service owner identifier
- `CostCenter`: billing unit or project code
- `Workload`: application or microservice name
- `ManagedBy`: `aws-platform-engineer-agent`
