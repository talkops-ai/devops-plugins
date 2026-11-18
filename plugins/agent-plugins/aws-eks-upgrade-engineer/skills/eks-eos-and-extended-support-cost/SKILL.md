---
name: eks-eos-and-extended-support-cost
description: Discovers Amazon EKS clusters across AWS regions approaching or currently in EKS Extended Support, verifies live Kubernetes version Standard vs Extended Support end-of-support dates via aws-documentation-mcp, queries live Extended Support hourly surcharge rates via awspricing, and builds a prioritized multi-quarter upgrade savings roadmap.
---

# EKS End-of-Support (EOS) & Extended Support Cost Analysis

Strictly **read-only** multi-region EKS fleet discovery and FinOps surcharge analysis skill.

## 1. Live Fleet & Calendar Discovery (Never Hardcode Dates or Prices)

1. **Verify Current EKS Release Calendar**: Query `aws-documentation-mcp` (`https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html`) to retrieve authoritative **Standard Support End Date** and **Extended Support End Date** for every Kubernetes minor version (`1.28` through latest).
2. **Verify Live Regional Pricing**: Query `awspricing` (`service_code="AmazonEKS"`) for both Standard control-plane hourly rates (`$0.10/hr` baseline in `us-east-1`) and **Extended Support** hourly rates (`$0.60/hr` total = `+$0.50/hr` surcharge per cluster, ~`$365/month` extra per cluster; verify exact regional SKU rate!).
3. **Multi-Region Cluster Inventory**: Use `aws-mcp` / `aws-api` (`eks:ListClusters` + `eks:DescribeCluster` across target regions) to collect cluster name, region, current `version`, `createdAt`, tags (`Environment`, `Owner`, `CostCenter`), node count, and Fargate/Karpenter footprint.

## 2. Surcharge Exposure & Risk Classification

Classify every discovered cluster into four tiers:
- **CRITICAL (In Extended Support & < 60 days to Force-Auto-Upgrade / EOS)**: Immediate forced-upgrade blast radius + active `$0.50/hr` (`~$4,380/yr`) surcharge per cluster.
- **ACTIVE SURCHARGE (In Extended Support)**: Currently accruing Extended Support hourly surcharges; quantify monthly and annualized avoidable spend.
- **UPCOMING (< 90 days to Standard Support End)**: Schedule in current quarter sprint before surcharge begins.
- **STANDARD SUPPORT (> 90 days headroom)**: Healthy lifecycle posture.

## 3. Deliverable Format

Produce an executive + engineering Markdown report containing:
1. **Fleet EOS & Extended Support Exposure Table** (Cluster, Region, K8s Version, Tier, Days to Next Cutoff, Current Monthly Cost, Avoidable Extended Support Surcharge/mo).
2. **Multi-Step Version Hop Matrix** (note that EKS control-plane in-place upgrades advance **one minor version at a time**, e.g. `1.29 -> 1.30 -> 1.31 -> 1.32`, vs. Blue/Green cluster replacement when `>= 3` minor versions behind).
3. **Prioritized Wave Roadmap** sequencing Dev/Staging soak clusters ahead of Production clusters.
