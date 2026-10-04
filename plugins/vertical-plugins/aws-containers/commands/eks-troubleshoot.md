---
description: Diagnose an unhealthy EKS cluster, node group, or workload
argument-hint: "<cluster> [namespace/workload]"
---

Troubleshoot EKS for `$ARGUMENTS` using the `aws-containers` skill and the read-only `eks` server.

1. Start with cluster insights and upgrade-readiness findings, then node group/Karpenter status.
2. For a workload: pod events, status, and logs; check VPC/subnet IP capacity and security groups with the cluster VPC config.
3. Search the EKS troubleshooting guide for the observed symptom and return root cause, evidence, and the fix.

This is a read-only workflow: do not create, modify, or delete resources. Do not enable sensitive-data access or write mode unless the user asks.
