# 7-Stage Principal FinOps Cost Audit Workflow

> **Pricing note:** All prices shown are `us-east-1` approximate as of early 2026. Prices vary by region and may change. Always verify current pricing via `awspricing:get_pricing` or `billing:aws-pricing` before reporting to users.

Execute this 7-stage protocol when a user asks to audit costs, reduce their AWS bill, investigate spend growth, or find savings. Prioritize **Immediate (delete unused/idle)** → **Short-Term (Two-Key validated right-sizing, storage/network configuration)** → **Long-Term (Savings Plans & Reserved Instance commitments sized to post-right-sizing usage)**.

---

## Stage 1: Scope, Identity, Accounting Basis & Active Credits

1. **Confirm current date and caller identity** (`aws sts get-caller-identity`).
2. **Discover Billing Views & Preferences:**
   - Call `billing:billing-views` (`list_billing_views`) to check if analysis should be scoped to a `PRIMARY`, `BILLING_GROUP`, or `CUSTOM` `billing_view_arn`.
   - Call `billing:get-billing-preferences` to check RI/SP discount sharing and credit sharing across member accounts.
3. **Select Accounting Metric:**
   - **`AmortizedCost`** (or **`NetAmortizedCost`** for Enterprise Discount Program [EDP] / PPA customers): Default for workload showback, right-sizing, and trend analysis when Savings Plans or RIs exist.
   - **`UnblendedCost`** (or **`NetUnblendedCost`**): Use for cash-flow invoice reconciliation (`billing:invoicing`) or single accounts with zero commitments.
4. **Check Active Credits & Free Tier:**
   - Call `billing:credits` (`get_credits`, `get_credit_allocation_history`) and `billing:free-tier` (`get_free_tier_usage`) so expiring credits do not disguise underlying spend growth.

---

## Stage 2: Macro Spend Drivers, MoM Variance & Anomaly Triage

### 1. Top Cost Drivers (`billing:cost-explorer`)
Exclude `Credit` and `Refund` record types when measuring operational usage run-rate:

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-04-01 \
  --granularity MONTHLY \
  --metrics AmortizedCost UnblendedCost \
  --filter '{"Not":{"Dimensions":{"Key":"RECORD_TYPE","Values":["Credit","Refund"]}}}' \
  --group-by Type=DIMENSION,Key=SERVICE
```

### 2. Month-over-Month Comparison & Variance Drivers (`billing:cost-comparison`)
Use `billing:cost-comparison` (`get_cost_and_usage_comparisons` and `get_cost_comparison_drivers`) between two exact 1-month periods (both starting on the `01` of the month) to automatically isolate the top 10 variance drivers, and calculate exact percent change per service using `billing:session-sql` or Python (see [`deterministic-calculations.md`](./deterministic-calculations.md)). Flag services with `>20%` MoM increase.

### 3. Cost Anomaly Correlation (`billing:cost-anomaly`)
Call `billing:cost-anomaly` (`get_anomalies`) for the last 30–90 days. For any detected spike, drill into `[AnomalyStartDate - 7d, AnomalyEndDate + 2d]` at `DAILY` or `HOURLY` granularity grouped by `USAGE_TYPE` and `OPERATION` to separate a **volume surge (`UsageQuantity` spike)** from a **rate jump (commitment expiration or credit exhaustion)**.

---

## Stage 3: Deduplicated Optimization Hub & Two-Key Right-Sizing

1. **Start with Cost Optimization Hub (`billing:cost-optimization`):**
   - Call `list_recommendation_summaries` with `group_by="ActionType"` and `group_by="ResourceType"`. Always use top-level `estimatedTotalDedupedSavings` as the deduplicated total.
   - Call `list_efficiency_metrics` to benchmark overall organizational efficiency.
   - See [`cost-optimization-hub.md`](./cost-optimization-hub.md) for CLI and MCP parameter syntax.
2. **Pull Technical Options (`billing:compute-optimizer` & `billing:compute-optimizer-automation`):**
   - Query `get_ec2_recommendations`, `get_asg_recommendations`, `get_ebs_recommendations`, `get_rds_recommendations`, `get_lambda_recommendations`, and `get_ecs_recommendations`.
   - Check `compute-optimizer-automation` (`list_automation_rules`, `list_recommended_actions`) for existing scheduled cleanup rules.
3. **Execute Two-Key Telemetry Validation (`cloudwatch`):**
   - Never recommend downsizing production resources without checking 14–30 day `p95`, `p99`, and `Maximum` utilization via `cloudwatch:get_metric_data` and verifying no active saturation alarms via `cloudwatch:get_active_alarms` / `cloudwatch:get_alarm_history`.
   - See [`ec2-rightsizing.md`](./ec2-rightsizing.md), [`rds-optimization.md`](./rds-optimization.md), [`ebs-optimization.md`](./ebs-optimization.md), and [`lambda-optimization.md`](./lambda-optimization.md).

---

## Stage 4: Idle Resources, Storage & Database Tiering

```bash
# Unattached EBS volumes (`available`)
aws ec2 describe-volumes --filters Name=status,Values=available \
  --query "Volumes[].{ID:VolumeId,Size:Size,Type:VolumeType,Created:CreateTime}" --output table

# Unattached Elastic IPs (~$3.65/month each — all public IPv4 addresses cost $0.005/hr whether in-use or idle)
aws ec2 describe-addresses \
  --query "Addresses[?!InstanceId && !NetworkInterfaceId]"

# EBS gp2 volumes eligible for online zero-downtime migration to gp3 (20% base storage savings)
aws ec2 describe-volumes --filters Name=volume-type,Values=gp2 \
  --query "Volumes[].{ID:VolumeId,Size:Size,IOPS:Iops,State:State}" --output table
```

- Audit S3 Storage Lens (`billing:storage-lens`) for incomplete multipart uploads, noncurrent version sprawl, S3 128 KB minimum object size traps, and missing S3 Bucket Keys on KMS-encrypted buckets.
- Audit Aurora clusters for **Aurora Standard vs. Aurora I/O-Optimized** break-even (25% I/O spend threshold — see [`rds-optimization.md`](./rds-optimization.md)).

---

## Stage 5: Network, Data Transfer & Per-Service Quick Wins

```bash
# CloudWatch Log groups without retention (`Never Expire` accumulates at $0.03/GB-month)
aws logs describe-log-groups \
  --query "logGroups[?!retentionInDays].{Name:logGroupName,StoredBytes:storedBytes,Class:logGroupClass}" --output table

# Lambda functions still on x86_64 (eligible for ~20% cheaper arm64 Graviton)
aws lambda list-functions \
  --query "Functions[?Architectures[0]=='x86_64'].{Name:FunctionName,Runtime:Runtime,Memory:MemorySize}" --output table

# Existing S3 & DynamoDB free Gateway Endpoints (cross-reference against all VPCs to find missing ones)
aws ec2 describe-vpc-endpoints --filters Name=service-name,Values=*s3*,*dynamodb* \
  --query "VpcEndpoints[].{VPC:VpcId,Service:ServiceName,Type:VpcEndpointType}"
```

- Classify all `*Bytes*` usage types (`NatGateway-Bytes`, `Regional-Bytes`, `DataTransfer-Out-Bytes`, `TransitGateway-Bytes`) and calculate the **~209 GB/month per-AZ break-even** between NAT Gateways ($0.045/GB) and VPC Interface Endpoints ($7.30/mo/AZ + $0.01/GB). See [`service-optimization.md`](./service-optimization.md).

---

## Stage 6: Commitment Portfolio & Effective Savings Rate (ESR)

**Critical Sequencing Rule:** Deduct all Stage 3–5 physical right-sizing and waste reductions from uncovered On-Demand spend **before** sizing commitments.

```bash
# Savings Plans coverage & utilization (`billing:sp-performance`)
aws ce get-savings-plans-coverage \
  --time-period Start=2026-03-01,End=2026-04-01 --granularity MONTHLY
aws ce get-savings-plans-utilization \
  --time-period Start=2026-03-01,End=2026-04-01 --granularity MONTHLY

# Reserved Instance coverage & utilization (`billing:ri-performance`)
aws ce get-reservation-coverage \
  --time-period Start=2026-03-01,End=2026-04-01 --granularity MONTHLY
aws ce get-reservation-utilization \
  --time-period Start=2026-03-01,End=2026-04-01 --granularity MONTHLY
```

- Check `billing:sp-explorer` for expiring commitments within 60 days, compare `SEVEN_DAYS`, `THIRTY_DAYS`, and `SIXTY_DAYS` lookback windows in `billing:sp-recommendation`, run custom simulations via `billing:sp-purchase-analyzer`, and compute **Effective Savings Rate (ESR)**. See [`savings-plans.md`](./savings-plans.md) and [`reserved-instances.md`](./reserved-instances.md).

---

## Stage 7: Generate the FinOps Decision Packet

Label all figures as **ACTUAL DATA** (from API) or **ESTIMATED SAVINGS** (calculated deterministically via `billing:session-sql` or Python script). Never hallucinate cost numbers. Conclude every audit with this structured **Decision Packet**:

```markdown
### FinOps Executive Summary & Accounting Basis
- **Scope:** Accounts / Billing View / Region / Date Window (`YYYY-MM-DD` to `YYYY-MM-DD`)
- **Accounting Metric:** [AmortizedCost | NetAmortizedCost | UnblendedCost]
- **Current Monthly Run-Rate (ACTUAL DATA):** $X,XXX.XX/mo | **Forecasted EOM:** $X,XXX.XX
- **Active Credits & Free Tier:** $X,XXX.XX remaining (Projected Exhaustion: YYYY-MM-DD)
- **Effective Savings Rate (ESR):** XX.X% (Current) -> XX.X% (Projected Post-Optimization)
- **Total Deduplicated Monthly Savings Potential (ESTIMATED SAVINGS):** **$X,XXX.XX/mo ($XX,XXX.XX/yr)**
  - *Immediate (Idle / Waste Elimination):* $X,XXX.XX/mo
  - *Short-Term (Two-Key Validated Right-Sizing, Storage & Network):* $X,XXX.XX/mo
  - *Long-Term (Incremental SP/RI Commitments, net of physical changes):* $X,XXX.XX/mo

### Prioritized Optimization Roadmap (Deduplicated)
| Priority | Category | Resource / Scope | Current Config & Cost | Target Config & Cost | Net Monthly Savings | Telemetry Proof (14–30d P95/P99) | Risk & Reversibility | Owning Hand-Off Agent |
|---|---|---|---|---|---|---|---|---|
| P0 | Idle / Waste | `vol-0abc...` (`us-east-1`) | 1 TB `gp2` (`available`), $100.00/mo | Snapshot + Delete, $50.00/mo | $50.00/mo | `VolumeReadOps=0`, `VolumeWriteOps=0` (30d) | Low (Snapshot retained) | `aws-platform-engineer` |
| P1 | Storage Modernization | 14 EBS Volumes | `gp2` (4.2 TB), $420.00/mo | `gp3` (3,000 IOPS / 125 MB/s), $336.00/mo | $84.00/mo | Max IOPS < 1,800; Zero-downtime online modify | Zero-downtime (`ModifyVolume`) | `aws-iac-engineer` |
```
