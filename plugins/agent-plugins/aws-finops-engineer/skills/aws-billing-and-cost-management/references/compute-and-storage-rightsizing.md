# SRE Compute & Storage Right-Sizing Playbook (Reliability-Safe FinOps)

As an SRE, cost optimization must never degrade availability, tail latency, or AZ failover headroom. Every right-sizing recommendation must pass the **Two-Key SRE Safety Gate**:
1. **Key 1 — 14-Day P99.5 Telemetry + AZ Failover Headroom Check**: Never size to `Average` utilization. Verify 14-day `p99` / `Maximum` CPU, memory, network bandwidth, and EBS IOPS/throughput, and ensure that if **one Availability Zone fails**, the remaining AZs stay below **70% utilization** without immediate cold-start scaling lag.
2. **Key 2 — Zero Active Saturation Alarms**: Confirm via `cloudwatch.get_active_alarms` and `cloudwatch.get_alarm_history` that the target resource had zero CPU/memory/IOPS/queue saturation alarms over the lookback window.

---

## 1. High-Confidence SRE Quick Wins (Zero Reliability Risk)

| Optimization | Savings Impact | Reliability Risk | Verification & Execution Pattern |
|---|---|---|---|
| **EBS `gp2` → `gp3` Volume Migration** | **20% lower $/GB-month** + baseline 3,000 IOPS & 125 MB/s free | **Zero** (Online via Elastic Volumes `ModifyVolume`, no reboot required) | Inspect `describe-volumes --filters Name=volume-type,Values=gp2`. Verify `BurstBalance` and `VolumeWriteOps`/`VolumeReadOps` via CloudWatch; modify volume type online. |
| **Unattached EBS Volumes & Orphaned Snapshots** | 100% of wasted volume cost | **Zero** (after final snapshot tag verification) | `describe-volumes --filters Name=status,Values=available`. Take final snapshot with retention tag before deletion. |
| **Unassociated Elastic IPs (EIPs) & Idle NAT Gateways / ALBs** | $3.65/mo per EIP; ~$32/mo per idle NAT GW; ~$16/mo per idle ALB | **Zero** if `ActiveConnectionCount == 0` and `ProcessedBytes == 0` over 14 days | Verify 14-day `Sum` of `ProcessedBytes` and `ActiveConnectionCount` in CloudWatch before decommissioning. |
| **Graviton4 (`m8g`, `c8g`, `r8g`) Migration for Managed Runtimes** | **Up to 20–40% better price-performance** | **Low** on RDS, Aurora, ElastiCache, OpenSearch, Lambda (`arm64`), and multi-arch EKS/ECS containers | Test in staging or canary capacity provider first; verify no x86-only native C extensions exist. |

---

## 2. Compute Optimizer Right-Sizing with SRE Headroom Guardrails

### EC2, Auto Scaling Groups, ECS Fargate, and EKS Nodes
1. Query `cost-explorer` / `compute-optimizer` (`get_ec2_recommendations`, `get_asg_recommendations`, `get_ecs_recommendations`).
2. Pull 14-day CloudWatch metrics (`CPUUtilization`, `mem_used_percent`, `NetworkIn`, `NetworkOut`, `EBSIOBalance%`):
   - **Reject downsizing** if `Maximum` `mem_used_percent > 75%` (OOM kill risk) or if the workload experiences bursty traffic faster than ASG/Karpenter scale-out latency (2–4 minutes).
   - **Approve downsizing** when `p99` CPU < 35% and `p99` memory < 50% across a full 14-day business cycle.

### Savings Plans vs. Spot Instances for Stateless Tiers
- **Stateful / Control-Plane / Latency-Sensitive APIs**: Recommend **Compute Savings Plans** or **Instance Savings Plans** after physical right-sizing.
- **Fault-Tolerant Stateless Workers, Batch, CI/CD, and Karpenter Consolidation Pools**: Combine **70% On-Demand/Savings Plans baseline** with **30% diversified Spot capacity** (`price-capacity-optimized` across >= 5 instance families) and AWS Node Termination Handler / Karpenter interruption queues.
