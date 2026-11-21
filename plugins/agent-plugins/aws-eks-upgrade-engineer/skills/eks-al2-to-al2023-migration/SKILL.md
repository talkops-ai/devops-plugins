---
name: eks-al2-to-al2023-migration
description: "Audits Amazon Linux 2 (AL2) Managed Node Groups, Self-Managed Auto Scaling Groups, Custom AMIs, and Karpenter EC2NodeClass resources ahead of EKS 1.33+ AL2 deprecation; translates legacy /etc/eks/bootstrap.sh flags into nodeadm NodeConfig (node.eks.aws/v1alpha1) MIME multipart user data; checks cgroup v2, IMDSv2 hop-limit=2, and containerd 2.x compatibility; and generates zero-downtime parallel node-group cutover plans. Do NOT use for EKS Extended Support billing/EOS date calendars, Karpenter CRD v1 Helm upgrades without AL2-to-AL2023 migration, or post-upgrade rollback triage. Query live AWS state via MCP tools only (never raw aws CLI)."
---

# Amazon EKS AL2 to AL2023 Node Migration

> **MCP-Only Live AWS Execution:** Execute ALL live AWS API discovery, cluster/nodegroup/launch-template inspection, and documentation lookups strictly via connected MCP tools (`aws-mcp`, `aws-api`, `eks`, `aws-documentation-mcp`, `cloudwatch`, `awspricing`) — **never invoke raw `aws ...` CLI commands in shell (`run_command`)**.

Strictly **read-only** assessment and migration planning skill for transitioning Amazon EKS worker nodes from **Amazon Linux 2 (AL2)** (deprecated / unsupported starting EKS `1.33+`) to **Amazon Linux 2023 (AL2023)**.

## 1. Read-Only Discovery Workflow

1. **Inventory Node Compute Types**:
   - Inspect EKS Managed Node Groups (`eks:ListNodegroups`, `eks:DescribeNodegroup`) for `amiType` (`AL2_x86_64`, `AL2_ARM_64`, `AL2_x86_64_GPU`, `CUSTOM`).
   - Inspect EC2 Launch Templates (`ec2:DescribeLaunchTemplateVersions`) for `/etc/eks/bootstrap.sh` invocations in decoded Base64 `UserData`.
   - Inspect Karpenter `EC2NodeClass` CRs (`karpenter.k8s.aws/v1` and `v1beta1`) for `spec.amiFamily: AL2` and `spec.userData`.
   - Inspect live Kubernetes `Node` `.status.nodeInfo` (`osImage`, `kernelVersion`, `containerRuntimeVersion`).
2. **Audit Breaking OS & Runtime Changes**:
   - **`nodeadm` Initialization (`node.eks.aws/v1alpha1`)**: AL2023 replaces `/etc/eks/bootstrap.sh` entirely with declarative `NodeConfig` YAML inside a `MIME` multipart archive (`Content-Type: application/node.eks.aws`) when custom user data is supplied. Managed Node Groups without custom AMI must include `apiServerEndpoint`, `certificateAuthority`, and `cidr` ONLY when using custom AMIs (EKS injects cluster details automatically on standard Managed Node Groups).
   - **IMDSv2 Default (`HttpTokens=required`, `HttpPutResponseHopLimit=1` on raw EC2 vs `2` for non-hostNetwork pods)**: Any pod still relying on IMDS instead of **EKS Pod Identity** or **IRSA** will fail on AL2023 if hop limit is `1`; flag pods lacking Pod Identity/IRSA and verify Launch Template `MetadataOptions`.
   - **cgroup v2 Unified Hierarchy**: Flag legacy Java (`< 11.0.16` / `< 17`), Go (`< 1.19` without `GOMEMLIMIT`), or `.NET` containers reading `/sys/fs/cgroup/memory/memory.limit_in_bytes` instead of `/sys/fs/cgroup/memory.max`.
   - **containerd 2.x Readiness (EKS 1.35+/1.36)**: Flag deprecated Schema 1 container images and CRI v1alpha2 consumers.

## 2. `/etc/eks/bootstrap.sh` to `nodeadm` Translation Rules

| Legacy AL2 `bootstrap.sh` Flag | AL2023 `NodeConfig` (`node.eks.aws/v1alpha1`) Mapping |
|---|---|
| `--kubelet-extra-args '--node-labels=k=v --register-with-taints=...'` | `spec.kubelet.flags: ["--node-labels=k=v", "--register-with-taints=..."]` |
| `--b64-cluster-ca` / `--apiserver-endpoint` | `spec.cluster.certificateAuthority` / `spec.cluster.apiServerEndpoint` + `spec.cluster.cidr` |
| `--dns-cluster-ip` | Derive `spec.cluster.cidr` (`10.100.0.0/16` or `172.20.0.0/16` from `eks:DescribeCluster` `kubernetesNetworkConfig.serviceIpv4Cidr`) |
| `--use-max-pods false` | Compute explicit `maxPods` in `spec.kubelet.config.maxPods` (AL2023 does not run `max-pods-calculator.sh` automatically when prefix delegation changes) |
| `--container-runtime containerd` | Omit (containerd is the sole runtime in AL2023) |

## 3. Parallel Cutover Plan (Never Mutate Live Infrastructure)

Always output copy-paste IaC patches (Terraform / CDK / CloudFormation / Karpenter `EC2NodeClass` YAML) implementing a **blue/green parallel node group or NodePool cutover**:
1. Provision parallel AL2023 Managed Node Group / `EC2NodeClass` (`amiFamily: AL2023` with pinned `amiSelectorTerms` alias e.g. `al2023@v...`).
2. Verify `Ready` status, CoreDNS/CNI DaemonSet pods, and canary workload scheduling.
3. Validate `PodDisruptionBudget` (`disruptionsAllowed > 0`) before cordoning and draining AL2 nodes.
