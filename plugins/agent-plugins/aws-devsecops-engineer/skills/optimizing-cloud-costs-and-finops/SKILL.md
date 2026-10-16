---
name: optimizing-cloud-costs-and-finops
description: >-
  Analyzes AWS spend, detects cost anomalies, audits idle and unattached resources (EBS volumes,
  Elastic IPs, NAT Gateways, underutilized RDS/ECS/EC2), evaluates Compute Optimizer and Savings
  Plans/RI recommendations via the `aws-billing` and `aws-mcp` servers, and generates right-sized
  IaC patches. Use when the user asks to "analyze AWS costs", "find cost savings", "explain a
  billing spike", "clean up idle resources", or runs `/cost`.
---

# Cloud Cost Optimization & FinOps Engineering

## When to Use
Invoke this skill whenever a user asks to break down AWS spend, investigate a billing spike or cost anomaly, identify wasted or idle infrastructure, evaluate Graviton (`arm64`) or Savings Plans savings, or right-size over-provisioned resources in local IaC.

## 4-Stage FinOps Analysis & Optimization Workflow

### Stage 1: Spend Breakdown, Forecast & Anomaly Triage (`aws-billing`)
Query the `aws-billing` MCP server (`get_cost_and_usage`, `get_cost_forecast`, `get_anomalies`, `get_budgets`) to establish the financial baseline:
1. **30-Day Spend by Service & Usage Type**: Group `UnblendedCost` and `AmortizedCost` by `SERVICE` and `USAGE_TYPE` (and by `LINKED_ACCOUNT` in multi-account organizations) to pinpoint top spend drivers and month-over-month deltas.
2. **Cost Anomaly Detection**: Query active cost anomalies to surface sudden spend spikes (e.g., runaway Lambda loops, cross-AZ data transfer surges, NAT Gateway `BytesProcessed` spikes, or CloudWatch Logs ingestion explosions).
3. **Budget Status**: Check AWS Budgets for any actual or forecasted breaches.

### Stage 2: Idle & Unattached Resource Sweep (`aws___run_script`)
Run a consolidated read-only sweep via `aws-mcp` (`aws___run_script`) to identify immediate zero-risk waste:

```python
import boto3

session = boto3.Session()
ec2 = session.client("ec2")
rds = session.client("rds")
logs = session.client("logs")

# 1. Unattached EBS volumes (status == 'available') and legacy gp2 volumes
avail_ebs = ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])["Volumes"]
gp2_ebs = ec2.describe_volumes(Filters=[{"Name": "volume-type", "Values": ["gp2"]}])["Volumes"]

# 2. Unassociated Elastic IPs
eips = [a for a in ec2.describe_addresses()["Addresses"] if "AssociationId" not in a]

# 3. CloudWatch Log Groups with never-expire retention (retentionInDays unset)
never_expire_logs = [
    lg["logGroupName"]
    for page in logs.get_paginator("describe_log_groups").paginate()
    for lg in page.get("logGroups", [])
    if "retentionInDays" not in lg and lg.get("storedBytes", 0) > 100_000_000
]

print({
    "unattached_ebs_volumes": [(v["VolumeId"], v["Size"], v["VolumeType"]) for v in avail_ebs],
    "gp2_volumes_upgradeable_to_gp3": len(gp2_ebs),
    "unassociated_eips": [a.get("AllocationId") for a in eips],
    "never_expire_log_groups_over_100mb": never_expire_logs[:20],
})
```

Also check:
- **NAT Gateways & Data Transfer**: Check CloudWatch `BytesOutToDestination` on NAT Gateways; if traffic is predominantly to S3 or DynamoDB, recommend free **Gateway VPC Endpoints** (`com.amazonaws.<region>.s3` / `dynamodb`).
- **Compute Optimizer Right-Sizing**: Query `aws compute-optimizer get-ec2-instance-recommendations`, `get-ecs-service-recommendations`, and `get-lambda-function-recommendations` for `Overprovisioned` workloads.

### Stage 3: High-ROI Architectural Optimizations
Rank optimization opportunities by **Monthly Savings ($)** vs. **Engineering Effort / Risk**:
1. **Zero-Downtime Quick Wins (Low Risk)**:
   - Migrate `gp2` EBS volumes to `gp3` (~20% lower cost + higher baseline IOPS).
   - Add S3 Gateway Endpoints and DynamoDB Gateway Endpoints to eliminate NAT Gateway per-GB processing charges.
   - Set CloudWatch Log Group retention policies (`7`, `30`, or `90` days) and S3 Intelligent-Tiering / Lifecycle rules for non-current versions and incomplete multipart uploads.
   - Delete unattached EBS volumes (after snapshot verification) and release unassociated Elastic IPs.
2. **Compute & Database Modernization (Medium Risk)**:
   - Migrate Lambda (`Architectures: [arm64]`), ECS Fargate (`runtimePlatform.cpuArchitecture: ARM64`), and RDS/ElastiCache (`db.t4g.*`, `db.r7g.*`) to AWS Graviton for up to 20–40% price-performance improvement.
   - Right-size over-provisioned ECS task definitions, Lambda memory, and RDS instance classes based on 14-day CloudWatch `CPUUtilization` and `MemoryUtilization` p95 metrics.
3. **Commitment Discounts (Financial)**:
   - Surface Savings Plans and Reserved Instance coverage/utilization recommendations from `aws-billing`.

### Stage 4: IaC Patch Synthesis
Map the recommended infrastructure changes back to the local repository (`*.tf`, `*.ts`, `template.yaml`) and offer to apply the right-sizing, Graviton architecture, S3 lifecycle, or log-retention patches directly in code.
