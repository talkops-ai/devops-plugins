---
description: AL2 to AL2023 nodeadm NodeConfig translation, cgroup v2 / IMDSv2 workload audit, and parallel node-group cutover plan
argument-hint: "<cluster-name> [--region <region>] [--nodegroup <name>]"
---

Invoke **eks-al2-to-al2023-migration** in strictly read-only mode to inventory AL2 Managed Node Groups, Launch Templates, Custom AMIs, and Karpenter `EC2NodeClass` specs; translate `/etc/eks/bootstrap.sh` arguments into `nodeadm` `NodeConfig` (`node.eks.aws/v1alpha1`); audit IMDSv2 hop limits and cgroup v2 compatibility; and generate a zero-downtime parallel node-group cutover plan.

Cluster and node group target: $ARGUMENTS
