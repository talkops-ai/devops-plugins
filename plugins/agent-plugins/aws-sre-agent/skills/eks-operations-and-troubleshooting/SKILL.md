---
name: eks-operations-and-troubleshooting
description: Diagnose and remediate Amazon EKS production incidents across Pod lifecycle failures (CrashLoopBackOff, OOMKilled, ImagePullBackOff, Pending/Unschedulable), Karpenter and EKS Auto Mode node provisioning, VPC CNI IP exhaustion, CoreDNS latency, EBS/EFS CSI volume mounts, and EKS Pod Identity/IRSA. Use when the user asks about EKS troubleshooting, Kubernetes pod failures, node NotReady states, Karpenter consolidation, or EKS cluster upgrades.
---

# Amazon EKS Operations & Production Troubleshooting Guide

Use this skill whenever triaging or operating workloads on **Amazon EKS** (Standard Managed Node Groups, Karpenter, Fargate, or **EKS Auto Mode**). Always combine the `eks` MCP server with `cloudwatch`, `prometheus`, and `cloudtrail` for full-stack correlation.

---

## 1. EKS MCP Diagnostic Tool Hierarchy (Read-Only Default)

| Diagnostic Step | `eks` MCP Tool | Parameters & Usage Notes |
|---|---|---|
| **1. Cluster Control Plane & Insights** | `get_eks_insights` | Inspect `UPGRADE_READINESS` (deprecated K8s APIs, add-on version skew) and `MISCONFIGURATION` insights. |
| **2. Cluster & Node Group Metrics** | `get_eks_metrics_guidance` | Retrieve official CloudWatch Container Insights / Prometheus metric definitions for CNI, CoreDNS, and kubelet. |
| **3. Workload Enumeration** | `list_k8s_resources` | List `Pod`, `Deployment`, `StatefulSet`, `DaemonSet`, `Node`, `NodePool`, `NodeClaim`, `Ingress`, or `PVC` (`kind`, `api_version`, `namespace`). |
| **4. Resource Spec & Status Inspection** | `manage_k8s_resource` | Call with `operation="read"` **only** to inspect `status.conditions`, `lastState.terminated`, `exitCode`, and resource `requests`/`limits`. |
| **5. Warning & Scheduling Events** | `get_k8s_events` | Retrieve `Warning` events (`FailedScheduling`, `FailedMount`, `BackOff`, `Unhealthy`, `FailedCreatePodSandBox`). |
| **6. Container Logs (`--previous`)** | `get_pod_logs` | Fetch live container logs or crashed container logs (when `--allow-sensitive-data-access` is enabled; otherwise query `/aws/containerinsights/<cluster>/application` via `cloudwatch.execute_log_insights_query`). |
| **7. Curated Runbooks** | `search_eks_troubleshoot_guide` | Search official AWS EKS troubleshooting guides for specific error strings. |

> **Safety Rule**: Never call `manage_k8s_resource` with `create`, `replace`, `patch`, or `delete`, and never call `apply_yaml`, `manage_eks_stacks(operation="deploy"|"delete")`, or `add_inline_policy`. Generate the Kubernetes YAML or IaC patch locally and present it for user approval.

---

## 2. Pod & Container Failure Triage Matrix

| Pod Status / Symptom | Primary Root Causes | Exact Diagnostic Verification | Remediation |
|---|---|---|---|
| **`CrashLoopBackOff` (`Exit Code 1` / `2` / `127`)** | Unhandled application exception, missing ConfigMap/Secret env var, bad entrypoint, or failing `livenessProbe`. | `get_k8s_events` + `cloudwatch.execute_log_insights_query` on `/aws/containerinsights/<cluster>/application`. | Fix application config/secret or increase `initialDelaySeconds` / `failureThreshold` on `startupProbe` & `livenessProbe`. |
| **`OOMKilled` (`Exit Code 137`)** | Container `working_set` memory exceeded `resources.limits.memory`, or host node ran out of memory (`NodeOOM`). | `manage_k8s_resource(operation="read")` (`lastState.terminated.reason == "OOMKilled"`) + `prometheus.ExecuteQuery` (`container_memory_working_set_bytes`). | Right-size `resources.limits.memory` (set `requests.memory == limits.memory` for Guaranteed/Burstable stability) and tune runtime heap (`JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75.0"`, `GOMEMLIMIT`). |
| **`Pending` (`FailedScheduling`)** | Insufficient node CPU/memory, taint/toleration mismatch, `nodeSelector` / `topologySpreadConstraints` deadlock, EBS AZ affinity mismatch, or Karpenter `NodePool` limit reached. | `get_k8s_events` on the Pod + inspect `NodePool` / `EC2NodeClass` status (`list_k8s_resources`). | Relax over-constrained affinity, expand Karpenter `NodePool` instance families/limits, or verify EBS PV AZ matches available subnets. |
| **`ContainerCreating` (`FailedCreatePodSandBox`)** | **VPC CNI (`aws-node`) IP exhaustion** in the subnet (`InsufficientFreeAddressesInSubnet`) or Security Group for Pods ENI limit reached. | Inspect `aws-node` Ipamd logs + `aws ec2 describe-subnets --query 'Subnets[*].[SubnetId,AvailabilityZone,AvailableIpAddressCount]'`. | Enable **VPC CNI Prefix Delegation** (`ENABLE_PREFIX_DELEGATION="true"`), add secondary CIDR blocks (`100.64.0.0/16`) to the VPC, or enable IPv6. |
| **`ContainerCreating` (`FailedMount` / `FailedAttachVolume`)** | Missing `ebs-csi-controller` addon, missing IAM permission on CSI controller role, KMS key grant missing, or `ReadWriteOnce` volume stuck on a terminating node (`Multi-Attach error`). | `get_k8s_events` + `cloudtrail.lookup_events` for `AttachVolume` / `CreateGrant` errors. | Attach `AmazonEBSCSIDriverPolicy` to the CSI Pod Identity role, grant KMS `CreateGrant`, or force detach stale volume if old node is terminated. |
| **`ImagePullBackOff` / `ErrImagePull`** | Missing ECR repo/tag, cross-account ECR repository policy missing, node IAM role missing `AmazonEC2ContainerRegistryReadOnly`, or missing VPC Endpoints (`ecr.api`, `ecr.dkr`, `s3` Gateway) in private subnet. | `get_k8s_events` (`403 Forbidden` vs `i/o timeout` vs `manifest unknown`). | Add ECR VPC endpoints + S3 Gateway endpoint in private route tables, or fix image tag/IAM policy. |

---

## 3. CoreDNS, VPC CNI, and Service Mesh Latency Triage

1. **CoreDNS `ndots:5` Amplification & Conntrack Exhaustion**:
   - By default, Kubernetes sets `ndots:5` in `/etc/resolv.conf`, causing every external hostname lookup (e.g., `sts.us-east-1.amazonaws.com`) to trigger **4 failed search-domain queries** (`A` + `AAAA` = 8 UDP packets) before querying the FQDN.
   - **Fix**: Enable **NodeLocal DNSCache** DaemonSet, autoscale CoreDNS (`cluster-proportional-autoscaler`), or set `dnsConfig.options: [{name: ndots, value: "2"}]` on high-throughput pods.
2. **ALB Ingress (`aws-load-balancer-controller`) 502 / 504 During Rollouts**:
   - Occurs when Kubernetes removes a terminating Pod from Endpoints *after* `SIGTERM` while ALB target group deregistration is still in flight.
   - **Fix**: Annotate Service/Ingress with Pod Readiness Gates (`elbv2.k8s.aws/pod-readiness-gate-inject: enabled`) and add a `preStop` lifecycle hook (`sleep 15`) with `terminationGracePeriodSeconds: 60`.

---

## Reference Files

- [references/pod-failure-matrix.md](references/pod-failure-matrix.md) — Deep-dive exit code reference (`1`, `126`, `127`, `137`, `139`, `143`), probe anti-patterns, and Container Insights Logs Insights queries
- [references/eks-auto-mode-and-irsa.md](references/eks-auto-mode-and-irsa.md) — EKS Auto Mode (`NodePool`/`NodeClass`), Karpenter consolidation debugging, and EKS Pod Identity vs. IRSA `AccessDenied` troubleshooting
- [references/k8s-resiliency-checklist.md](references/k8s-resiliency-checklist.md) — Production EKS resilience checklist (`PodDisruptionBudget`, `topologySpreadConstraints`, `PriorityClass`, HPA/KEDA, and zero-downtime ALB rollout manifest)
