---
description: IaC/GitOps-routed 12-phase EKS upgrade runbook, 5-mode VPC CNI surge & ODCR/FDCR capacity plan, and soak/rollback gates
argument-hint: "<cluster-name> [--region <region>] [--target <1.XX>] [--strategy in-place|blue-green]"
---

Invoke **eks-upgrade-readiness**, **eks-karpenter-and-addon-upgrades**, and **eks-al2-to-al2023-migration** in strictly read-only mode to detect cluster IaC/GitOps ownership, calculate 5-mode VPC CNI IP surge and subnet capacity requirements, compare In-Place vs. Blue-Green trade-offs, and produce a sequenced 12-phase upgrade runbook with pre-filled commands/IaC diffs and rollback checkpoints.

Target cluster and strategy: $ARGUMENTS
