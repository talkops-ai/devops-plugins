# EC2 & Auto Scaling Group Right-Sizing with Two-Key CloudWatch Validation

## Prerequisites
Opt in first: `aws compute-optimizer update-enrollment-status --status Active`

## The Two-Key Validation Protocol (Mandatory)

Never recommend downsizing or terminating a production EC2 instance or Auto Scaling Group based on Compute Optimizer or billing metadata alone:
1. **Key 1 (Financial & Technical Options):** Call `billing:cost-optimization` (`list_recommendations`) and `billing:compute-optimizer` (`get_ec2_recommendations`, `get_asg_recommendations`) to extract `finding`, `findingReasonCodes`, `recommendationOptions`, `performanceRisk`, and `savingsOpportunityAfterDiscounts`.
2. **Key 2 (CloudWatch Telemetry & Alarm Proof):** Call `cloudwatch:get_metric_data` over a **14-to-30 day lookback** (`period=3600` or `86400`) requesting **`p95`, `p99`, and `Maximum`** statistics (never `Average` alone, which conceals diurnal spikes), and check `cloudwatch:get_active_alarms` + `cloudwatch:get_alarm_history` to confirm no saturation alarms fired.
   - *Note:* Always pass `max_items`, `limit`, and `period` as native JSON integers (`50`, `3600`) to `cloudwatch` MCP tools.

## CloudWatch Validation Thresholds for EC2

| Metric & Namespace | Required Statistics (14–30d) | Safe to Downsize When | Hold / Block Downsizing When |
|---|---|---|---|
| `AWS/EC2` `CPUUtilization` | `p95`, `p99`, `Maximum` | `P95 < 35%` AND `P99 < 55%` | `P99 > 70%` or active CPU alarm |
| `CWAgent` `mem_used_percent` | `p95`, `p99`, `Maximum` | `P95 < 50%` AND `Maximum < 70%` | `P95 > 75%` or **`CWAgent` missing** (never reduce GiB RAM without memory metrics!) |
| `AWS/EC2` `NetworkIn` + `NetworkOut` | `Maximum`, `p99` | Peak bandwidth `< 60%` of target instance ceiling | Peak bandwidth exceeds smaller instance's baseline/burst Gbps limit |
| `AWS/EC2` `EBSReadBytes` + `EBSWriteBytes` | `Maximum`, `p99` | Peak EBS throughput `< 60%` of target instance EBS cap | Peak throughput exceeds target instance's EBS-Optimized bandwidth |
| `AWS/EC2` `CPUCreditBalance` / `CPUSurplusCreditsCharged` (`t3`/`t3a`/`t4g`) | `Minimum`, `Sum` | `CPUCreditBalance` stays well above `0` and `CPUSurplusCreditsCharged == 0` | If `CPUSurplusCreditsCharged > 0`, Unlimited burst charges ($0.05/vCPU-hr) often make `t3`/`t4g` **more expensive** than fixed `m7g`/`c7g`! |

### Missing CloudWatch Agent Memory Guardrail
Hypervisor-level `AWS/EC2` metrics do **not** include OS memory (`mem_used_percent`). Memory metrics enable up to 4x more savings opportunities.
- If `CWAgent` `mem_used_percent` is absent:
  1. Explicitly label the recommendation: `Memory Telemetry: Unverified (CWAgent not installed)`.
  2. **Never recommend reducing total GiB of RAM** (e.g., do not move `r6i.xlarge` [32 GiB] to `c6i.xlarge` [8 GiB]).
  3. Generation upgrades (`m5.xlarge` → `m6i.xlarge` / `m7i.xlarge`) and Graviton migrations (`m6i.xlarge` → `m7g.xlarge`) that preserve the exact same vCPU and GiB RAM are safe without `CWAgent` metrics.

## Finding Classifications

| Finding | Meaning |
|---------|---------|
| `Overprovisioned` | Can be downsized while meeting workload needs |
| `Underprovisioned` | Too small, risking performance issues |
| `Optimized` | Appropriately sized |
| `NotOptimized` | Could benefit from newer generation or Graviton (`arm64`) family |

## Finding Reason Codes

Each finding includes reason codes explaining which metrics triggered it: `CPUOverprovisioned`, `CPUUnderprovisioned`, `MemoryOverprovisioned`, `MemoryUnderprovisioned`, `EBSThroughputOverprovisioned`, `EBSIOPSOverprovisioned`, `NetworkBandwidthOverprovisioned`, `NetworkPPSOverprovisioned`, `GPUOverprovisioned`, etc. Found in `findingReasonCodes` array.

## Lookback Periods

| Period | Datapoints | Cost |
|--------|-----------|------|
| 14-day (default) | ~4,032 | Free |
| 32-day | ~9,216 | Free (enhanced) |
| 93-day | ~26,784 | Paid (enhanced infrastructure metrics — $0.25/instance/mo, essential for quarterly batch peaks) |

Uses P99.5 percentile by default (excludes top 0.5% outliers). Default 20% CPU/memory headroom buffer.

## Migration Effort Levels & AWS Graviton (`arm64`) Modernization

| Level | Example | Typical Savings & Notes |
|-------|---------|-------------------------|
| Very Low | Same family size change (`c6i.xlarge` → `c6i.large`) | 50% per step down |
| Low | Generation change (`m5.xlarge` → `m6i.xlarge` / `m7i.xlarge`) | Better price-performance, same x86_64 AMI |
| Medium | Family change (`m6i.xlarge` → `c6i.xlarge`) | Requires verified `CWAgent` memory headroom |
| High | Architecture change (`x86_64` → Graviton3/4 `m7g` / `c7g` / `r7g` / `r8g`) | **Up to 20% lower hourly cost + 20%–40% higher perf/watt**; requires `arm64` AMI and multi-arch binaries/containers |

## Performance Risk Scale
0-1: Very Low | >1-2: Low | >2-3: Medium | >3-4: High

## Savings Estimation Modes

Check `effectiveRecommendationPreferences.savingsEstimationMode.source`:

- `PublicPricing`: On-Demand pricing (default)
- `CostExplorerRightsizing`: Incorporates SP/RI discounts
- `CostOptimizationHub`: Custom pricing

If only `savingsOpportunity` is present, calculation uses On-Demand. If `savingsOpportunityAfterDiscounts` is also present, always report `savingsOpportunityAfterDiscounts` so existing commitments are respected.

## CLI Commands

```bash
# Over-provisioned EC2 instances
aws compute-optimizer get-ec2-instance-recommendations \
  --filters Name=Finding,Values=Overprovisioned

# Request Graviton (AWS_ARM64) options explicitly
aws compute-optimizer get-ec2-instance-recommendations \
  --recommendation-preferences '{"cpuVendorArchitectures":["AWS_ARM64"]}'

# Idle resources (near-zero utilization)
aws compute-optimizer get-idle-recommendations
```

## Presenting a Right-Sizing Recommendation

When presenting a right-sizing recommendation to the user, include:

1. Current instance type, region, and specs (vCPUs, GiB memory, network/EBS limits)
2. Which metrics triggered the finding + **verified 14–30d CloudWatch P95/P99/Max values and alarm status**
3. Recommended instance type and specs
4. Monthly savings ($ and %, net of discounts) — calculate with `billing:session-sql` or Python script, NEVER manually
5. Migration effort level, `performanceRisk`, and any platform differences (Xen→Nitro, `x86_64`→`arm64`)
6. Whether OS memory metrics (`CWAgent`) were available (if not, flag `Memory Telemetry: Unverified`)
