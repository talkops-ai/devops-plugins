---
name: eks-operations-and-troubleshooting
description: "Diagnose and remediate Amazon EKS production incidents across Pod lifecycle failures (CrashLoopBackOff, OOMKilled, ImagePullBackOff, Pending/Unschedulable), Karpenter and EKS Auto Mode node provisioning, VPC CNI IP exhaustion, CoreDNS latency, EBS/EFS CSI volume mounts, and EKS Pod Identity/IRSA. Use when the user asks about EKS troubleshooting, Kubernetes pod failures, node NotReady states, Karpenter consolidation, or EKS cluster upgrades. Query live AWS state via MCP tools only (never raw aws CLI)."
---

# Amazon EKS Operations & Production Troubleshooting Guide

> **MCP-Only Live AWS Execution:** Execute ALL live AWS API discovery, account/region preflight checks (`sts:GetCallerIdentity`), stack/cluster/resource inspection, pricing (`awspricing`/`billing`), IaC validation (`awsiac`), and documentation lookups (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `awsknowledge`, `awsiac`, `awspricing`, `eks`, `ecs`, `cloudwatch`) — **never invoke raw `aws ...` CLI commands in shell (`run_command`)**. Offline local linters/synthesizers (`cdk synth`, `terraform validate`, `python3`) may run locally without mutating live AWS.

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
| **`ContainerCreating` (`FailedCreatePodSandBox`)** | **VPC CNI (`aws-node`) IP exhaustion** in the subnet (`InsufficientFreeAddressesInSubnet`) or Security Group for Pods ENI limit reached. | Inspect `aws-node` Ipamd logs + query subnet IP availability via `eks` MCP (`get_eks_vpc_config`) or `aws-mcp` (`aws___call_aws`: `aws ec2 describe-subnets --query 'Subnets[*].[SubnetId,AvailabilityZone,AvailableIpAddressCount]'`). | Enable **VPC CNI Prefix Delegation** (`ENABLE_PREFIX_DELEGATION="true"`), add secondary CIDR blocks (`100.64.0.0/16`) to the VPC, or enable IPv6. |
| **`ContainerCreating` (`FailedMount` / `FailedAttachVolume`)** | Missing `ebs-csi-controller` addon, missing IAM permission on CSI controller role, KMS key grant missing, or `ReadWriteOnce` volume stuck on a terminating node (`Multi-Attach error`). | `get_k8s_events` + `cloudtrail.lookup_events` for `AttachVolume` / `CreateGrant` errors. | Attach `AmazonEBSCSIDriverPolicy` to the CSI Pod Identity role, grant KMS `CreateGrant`, or force detach stale volume if old node is terminated. |
| **`ImagePullBackOff` / `ErrImagePull`** | Missing ECR repo/tag, cross-account ECR repository policy missing, node IAM role missing `AmazonEC2ContainerRegistryReadOnly`, or missing VPC Endpoints (`ecr.api`, `ecr.dkr`, `s3` Gateway) in private subnet. | `get_k8s_events` (`403 Forbidden` vs `i/o timeout` vs `manifest unknown`). | **Mandatory 2-Part Checklist**: Always prescribe BOTH (1) verifying `AmazonEC2ContainerRegistryReadOnly` is attached to the worker node IAM role AND (2) provisioning both ECR Interface VPC endpoints (`ecr.api`, `ecr.dkr`) + the Amazon S3 Gateway VPC endpoint (`s3` in private subnet route tables for ECR image layer blobs). |

---

## 3. CoreDNS, VPC CNI, and Service Mesh Latency Triage

1. **CoreDNS `ndots:5` Amplification & Conntrack Exhaustion**:
   - By default, Kubernetes sets `ndots:5` in `/etc/resolv.conf`, causing every external hostname lookup (e.g., `sts.<region>.amazonaws.com` or `rds.amazonaws.com`, which have <5 dots) to trigger **4 failed search-domain queries** (`<ns>.svc.cluster.local`, `svc.cluster.local`, `cluster.local`, `<ec2-domain>`) across both `A` (IPv4) and `AAAA` (IPv6) records (**8 failed UDP DNS packets**) before querying the absolute FQDN.
   - **Fix**: Recommend (a) deploying **NodeLocal DNSCache** (`node-local-dns` DaemonSet), (b) autoscaling CoreDNS (`cluster-proportional-autoscaler`), and (c) setting `dnsConfig.options: [{name: ndots, value: "2"}]` on the workload `Deployment` spec (keep YAML focused on the workload `Deployment` rather than dumping the entire upstream `node-local-dns` DaemonSet manifest).
2. **ALB Ingress (`aws-load-balancer-controller`) 502 / 504 During Rollouts**:
   - Occurs when Kubernetes removes a terminating Pod from Endpoints *after* `SIGTERM` while ALB target group deregistration is still in flight.
   - **Fix**: Label the Namespace with Pod Readiness Gates (`elbv2.k8s.aws/pod-readiness-gate-inject: enabled`) and configure a `preStop` lifecycle hook (`sleep 15`) with `terminationGracePeriodSeconds: 60` on the `Deployment`.

---

## Reference Files

- [references/pod-failure-matrix.md](references/pod-failure-matrix.md) — Deep-dive exit code reference (`1`, `126`, `127`, `137`, `139`, `143`), probe anti-patterns, and Container Insights Logs Insights queries
- [references/eks-auto-mode-and-irsa.md](references/eks-auto-mode-and-irsa.md) — EKS Auto Mode (`NodePool`/`NodeClass`), Karpenter consolidation debugging, and EKS Pod Identity vs. IRSA `AccessDenied` troubleshooting
- [references/k8s-resiliency-checklist.md](references/k8s-resiliency-checklist.md) — Production EKS resilience checklist (`PodDisruptionBudget`, `topologySpreadConstraints`, `PriorityClass`, HPA/KEDA, and zero-downtime ALB rollout manifest)

## MCP-First Execution, Guardrails & `awsknowledge` Fallback

- **MCP-Only Execution (Zero Raw AWS CLI in Shell)**: When querying live AWS state, telemetry, pricing, or IaC compliance, always use connected MCP tools (`eks`, `aws-mcp` `aws___call_aws`, `cloudwatch`, `awspricing`, `awsiac`, `awsknowledge`) in strictly read-only mode. NEVER execute raw `aws`, `eksctl`, `kubectl`, or `helm` CLI commands via `run_command` / `Bash`.
- **Honest Zero-Resource Reporting**: If `0` EKS clusters or log groups exist in the queried region, report `0` matching resources honestly without fabricating cluster ARNs, pod names, or log lines, and then provide the complete diagnostic runbook.
- **Vague Workload Sizing & Cost Guard**: If the user asks for Karpenter `NodePool` CPU/memory limits, pod resource requests/limits, or monthly EKS cost estimates without providing concrete workload metrics (`pod_cpu_utilization`, `pod_memory_working_set`, replica count, RPS), refuse to fabricate or guess specific sizing numbers or monthly dollar totals and state which Container Insights / Prometheus metrics must be gathered first.
- **Read-Only & Secret Safety (`aws-mutation-gate.py`, `secret-safety.py`)**: Never run mutating cluster/node operations (`kubectl delete/drain/apply`, `eksctl upgrade/delete`) or fetch plaintext secrets (`aws secretsmanager get-secret-value`, `curl localhost:2773/secretsmanager/get`); recommend `DescribeSecret` metadata checks and Secrets Store CSI Driver / EKS Pod Identity instead.
- **`awsknowledge` Edge-Case Fallback**: Only when **no** local `references/*.md` file covers the user's specific edge-case question (e.g., EKS Hybrid Nodes or Mountpoint for Amazon S3 CSI Driver), query the connected `awsknowledge` MCP server (`aws___search_documentation` and `aws___read_documentation` — max 1–2 focused searches) and answer directly. Never call `awsknowledge` for topics already covered in local `references/*.md`.
- **Fast, Bounded Discovery & Pricing Calls (Avoid Tool Loops)**: When a prompt asks to inspect live clusters/logs in the target region, limit live AWS discovery to 1–3 read-only MCP calls (`eks`, `cloudwatch`, or `aws-mcp` `aws___call_aws`). For architecture/design or symptom-triage questions that do not ask for live cluster discovery, answer directly from local `references/*.md` without unnecessary MCP calls. Only call `awspricing` (`get_pricing`) if the user explicitly asks for pricing, and make at most 2–3 filtered `get_pricing` calls total.
