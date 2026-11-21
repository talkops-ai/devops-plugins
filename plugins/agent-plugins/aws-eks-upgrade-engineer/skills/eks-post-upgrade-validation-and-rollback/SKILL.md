---
name: eks-post-upgrade-validation-and-rollback
description: "Executes read-only post-upgrade functional smoke validation against pre-upgrade cluster baselines, triages stalled or degraded EKS control-plane and node-group upgrades (PodEvictionFailure, InsufficientInstanceCapacity, ConfigurationConflict, NodeCreationFailure), and evaluates 7-day EKS control-plane ROLLBACK_READINESS insights with reverse-order component rollback runbooks. Do NOT use for pre-upgrade Extended Support surcharge forecasting, AL2 bootstrap.sh-to-nodeadm OS migration, or Karpenter v1 CRD authoring. Query live AWS state via MCP tools only (never raw aws CLI)."
---

# EKS Post-Upgrade Validation, Stuck-Upgrade Triage & Rollback

> **MCP-Only Live AWS Execution:** Execute ALL live AWS API discovery, EKS cluster/update/insight checks, and CloudWatch log/metric queries strictly via connected MCP tools (`aws-mcp`, `aws-api`, `eks`, `cloudwatch`, `aws-documentation-mcp`) — **never invoke raw `aws ...` CLI commands in shell (`run_command`)**.

Strictly **read-only** verification, incident triage, and rollback eligibility skill for Amazon EKS upgrades.

## 1. Post-Upgrade Smoke Validation Checklist

Compare live cluster telemetry (`eks`, `cloudwatch`, `aws-mcp`) against pre-upgrade baselines:
1. **Control Plane & Insights**: `eks:DescribeCluster` (`version`, `status == ACTIVE`), `eks:ListUpdates` / `eks:DescribeUpdate` (`Successful`), and `eks:ListInsights` (zero new `ERROR` findings).
2. **Node & Runtime Parity**: All `Nodes` `Ready`, uniform kubelet target version skew (`<= 1` minor during rolling node cutover, `0` after completion), zero `NodeNotReady` or `PLEG` instability events.
3. **Core Networking & DNS**: `aws-node` (`ipamd` warm IP pool healthy), `kube-proxy`, `coredns` (`SERVFAIL`/`NXDOMAIN` rate normal), and CSI controller/node pods `Running`.
4. **Workload & SLO Health**: Zero new `CrashLoopBackOff`, `ImagePullBackOff`, `Evicted`, or `Pending` pods; ALB/NLB target groups healthy; CloudWatch `apiserver_request_total` `5xx` rate `< 0.1%`.

## 2. Stalled / Failed Upgrade Triage

| Update / Nodegroup Error Code | Read-Only Root-Cause Checks | Safe Remediation Plan |
|---|---|---|
| `PodEvictionFailure` | Check `PodDisruptionBudget` (`disruptionsAllowed == 0`, `minAvailable: 100%`, single-replica deployment with PDB, or overlapping PDB selectors) | Adjust PDB or scale replica count >= 2 via IaC/GitOps before retrying node drain |
| `InsufficientInstanceCapacity` / `AsgInstanceLaunchFailures` | Check subnet `AvailableIpAddressCount` (`ec2:DescribeSubnets`), EC2 vCPU quotas (`servicequotas`), and ASG diversify instance types | Add secondary CIDR / prefix delegation or diversify Launch Template instance types |
| `NodeCreationFailure` / `UnhealthyNodes` | Inspect `NodeConfig` MIME formatting, custom AMI `nodeadm` flags, Security Group egress/cluster-SG rules, and `aws-auth` / EKS Access Entries | Fix Launch Template version in IaC and trigger a controlled update |
| `ConfigurationConflict` (Add-ons) | Inspect `eks:DescribeAddon` schema diff against target `DescribeAddonVersions` JSON schema | Update `configurationValues` in IaC with `--resolve-conflicts PRESERVE` |

## 3. 7-Day Control-Plane Rollback Assessment (`ROLL-01..02`)

- Check `eks:ListInsights` (`category=ROLLBACK_READINESS` where available) and cluster upgrade completion timestamp (`<= 7 days` window when EKS supports control-plane version rollback, or Blue/Green cluster DNS weighted switchback).
- Document **reverse-order rollback sequencing** when applicable: workloads/webhooks -> add-ons -> worker node groups (parallel previous-minor node group) -> traffic switchback; highlight irreversible state (e.g., etcd CRD storage version migrations) before any operator action.
