# EBS Volume & Snapshot Optimization

> **Pricing note:** All prices shown are `us-east-1` approximate as of early 2026. Prices vary by region and may change. Always verify current pricing via `awspricing:get_pricing` or `billing:aws-pricing` before reporting to users.

## Volume Type Comparison

### `gp2` vs `gp3` (Online Zero-Downtime Win)

- `gp2`: IOPS tied to volume size (3 IOPS/GB, min 100, max 16,000 IOPS). Uses burst buffer — can burst to 3,000 IOPS temporarily for volumes `< 1 TB`, then drops to baseline when credits deplete (`BurstBalance` drops to 0). A 100 GB `gp2` volume has only 300 IOPS baseline.
- `gp3`: **~20% lower per-GB cost ($0.08/GB-mo vs $0.10/GB-mo in `us-east-1`)**. Consistent **3,000 IOPS + 125 MB/s baseline included free** for ANY volume size. No burst buffer. Additional IOPS (up to 16,000) cost **$0.005/IOPS-month**; additional throughput (up to 1,000 MB/s) costs **$0.04/MB/s-month**.

**`gp2` → `gp3` migration is almost always an immediate win:** lower cost, consistent performance, zero downtime via Elastic Volumes (`ModifyVolume`).
- **Large `gp2` Volume Check (> 1 TB):** A 2,000 GB `gp2` volume provides 6,000 baseline IOPS and 250 MB/s. Always check 14–30d CloudWatch `VolumeReadOps + VolumeWriteOps` (`Maximum`, `p99`) and `VolumeReadBytes + VolumeWriteBytes` (`Maximum`) before migrating a `> 1 TB` `gp2` volume so you provision matching `gp3` IOPS/throughput if peak demand exceeds 3,000 IOPS / 125 MB/s.

### `io1` vs `io2` vs `gp3`
- `io1` and `io2` have the same base price ($0.125/GB-mo + $0.065/provisioned IOPS-mo in `us-east-1` for first 32K IOPS). `io2` offers 100x higher durability (99.999% vs 99.8%) and up to 256K IOPS on Nitro (`io2 Block Express`). Always prefer `io2` over `io1`.
- **Downsizing `io1`/`io2` to `gp3`:** If an `io1`/`io2` volume has peak 30-day P99 IOPS `<= 16,000`, peak throughput `<= 1,000 MB/s`, does not use Multi-Attach, and does not require sub-millisecond `io2 Block Express` latency, migrating to `gp3` saves **50%–75% of monthly volume + PIOPS spend**.

## Compute Optimizer & Automation for EBS

Prerequisites: supported type (`gp2`/`gp3`/`io1`/`io2`), attached and in-use for full lookback, ≥24h CloudWatch metrics, no modification in past 24h.

Metrics (`AWS/EBS`): `VolumeReadOps`, `VolumeWriteOps` (Max + P99 + Sum), `VolumeReadBytes`, `VolumeWriteBytes` (Max + P99), `VolumeQueueLength` (P99), `BurstBalance` (Minimum).

Findings: `NotOptimized` (can improve), `Optimized` (may still recommend `gp2`→`gp3` or `io1`→`io2` migration for cost/durability).

```bash
# Compute Optimizer EBS recommendations (`billing:compute-optimizer`)
aws compute-optimizer get-ebs-volume-recommendations \
  --filters Name=Finding,Values=NotOptimized

# Unattached EBS volumes (`available`)
aws ec2 describe-volumes --filters Name=status,Values=available \
  --query "Volumes[].{ID:VolumeId,Size:Size,Type:VolumeType,IOPS:Iops,Created:CreateTime}" --output table
```

Also inspect `billing:compute-optimizer-automation` (`list_automation_rules`, `list_recommended_actions`, `list_automation_rule_preview_summaries`) to see if automated rules are configured for snapshotting/deleting unattached volumes or upgrading `gp2` to `gp3`.

## Orphaned Snapshots & EBS Snapshot Archive Tier (75% Savings)

1. **Orphaned Snapshots:** Cross-reference `aws ec2 describe-snapshots --owner-ids self` against `aws ec2 describe-images --owners self` to identify aged snapshots no longer backing any registered AMI.
2. **EBS Snapshot Archive Tier:** For compliance snapshots retained for **≥ 90 days** and rarely restored, recommend moving them from Standard ($0.05/GB-month) to **EBS Snapshot Archive ($0.0125/GB-month — up to 75% savings)**. Note the 90-day minimum storage duration and $0.03/GB restore fee.

## Root Volume Considerations

- Root volumes contain the OS — modifications require extra caution
- All modern Nitro/Xen instance types support Elastic Volumes for online `gp2`→`gp3` modification without detaching or rebooting
- Always verify instance type supports online modification before proceeding

## Deterministic Savings Formulas (Run via Python Script)

**`io1`/`io2` optimization:**
`Savings = (current_GB * $/GB + current_PIOPS * $/PIOPS) - (recommended_GB * $/GB + recommended_PIOPS * $/PIOPS)`

**`gp2` → `gp3` migration:**
`Savings = (current_GB * gp2_$/GB) - (current_GB * gp3_$/GB + max(0, needed_IOPS - 3000) * gp3_$/IOPS + max(0, needed_throughput_MBps - 125) * gp3_$/throughput_MBps)`

Look up regional prices via `awspricing:get_pricing` or `billing:aws-pricing` (see [`pricing-lookup.md`](./pricing-lookup.md)). Use Compute Optimizer recommended IOPS/throughput when available, otherwise observed 14–30d P99 from `cloudwatch:get_metric_data`.

## Gotchas

- `gp2` burst buffer depletion (`BurstBalance == 0`) causes sudden 10x IOPS drops — migrating to `gp3` fixes both latency and cost
- Volume modifications are online (no detach needed) but enter an `optimizing` state while completing
- EBS volume size (`Size`) can only be increased online, never decreased
- After modifying a volume, AWS enforces a **6-hour cooldown** before the next modification on that volume
