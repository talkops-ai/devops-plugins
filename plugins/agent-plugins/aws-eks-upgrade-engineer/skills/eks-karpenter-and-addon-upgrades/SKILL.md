---
name: eks-karpenter-and-addon-upgrades
description: "Validates Amazon EKS Managed Add-ons (paginated DescribeAddonVersions compatibility, integer eksbuild ordering, PRESERVE vs OVERWRITE configuration conflict checks), self-managed aws-node/coredns/kube-proxy DaemonSets, retired ingress-nginx to Gateway API or AWS Load Balancer Controller migrations, and two-step Karpenter CRD + controller v0.37-to-v1.x upgrades. Do NOT use for EKS Extended Support surcharge/EOS calendars, AL2 bootstrap.sh-to-nodeadm OS migration, or post-upgrade rollback/PodEvictionFailure triage. Query live AWS state via MCP tools only (never raw aws CLI)."
---

# EKS Add-ons & Karpenter Upgrade Validation

> **MCP-Only Live AWS Execution:** Execute ALL live AWS API discovery, add-on version compatibility lookups (`eks:DescribeAddonVersions`), and documentation checks strictly via connected MCP tools (`aws-mcp`, `aws-api`, `eks`, `aws-documentation-mcp`, `cloudwatch`) — **never invoke raw `aws ...` CLI commands in shell (`run_command`)**.

Strictly **read-only** compatibility audit and upgrade sequencing skill for **EKS Managed Add-ons**, **self-managed cluster add-ons**, and **Karpenter (`v0.32`/`v0.37` -> `v1.0+`)**.

## 1. EKS Managed Add-on Compatibility Rules

1. **Always Paginate `eks:DescribeAddonVersions`**: Never assume the first page contains the target version; pass `--kubernetes-version <target>` and paginate all `addons[].addonVersions[]`.
2. **Numeric `eksbuild` Comparison**: Parse `-eksbuild.<N>` as an **integer** (`eksbuild.12 > eksbuild.9`, never lexicographical string sort!).
3. **Configuration Drift Preservation**: Inspect `eks:DescribeAddon` `configurationValues`. Recommend `--resolve-conflicts PRESERVE` (or explicit IaC `configuration_values` merge) so custom CoreDNS `Corefile` stanzas, VPC CNI `ENABLE_PREFIX_DELEGATION`, or `WARM_IP_TARGET` settings are never wiped by `OVERWRITE`.
4. **Upgrade Order**:
   - `vpc-cni` -> `coredns` -> `kube-proxy` -> `eks-pod-identity-agent` -> CSI drivers (`aws-ebs-csi-driver`, `aws-efs-csi-driver`) -> observability/security add-ons.
   - Verify `vpc-cni` minor version skew against control plane before upgrading nodes.

## 2. Karpenter Upgrade & API Migration Gates (`KARP-01..14`)

1. **Version Matrix**:
   - Karpenter **`v0.37.x`** is the mandatory bridge release before upgrading to **`v1.0+`** (converts `v1beta1` `NodePool`/`EC2NodeClass`/`NodeClaim` webhooks to `v1`).
   - Check EKS Kubernetes version compatibility (`Karpenter v1.0+` required for EKS `1.31+` / `1.32+` lifecycle support).
2. **Two-Step Helm Upgrade**:
   - Always upgrade **`karpenter-crd`** chart FIRST to the exact target version, verify CRD `Established` condition and stored `v1` versions, and THEN upgrade the **`karpenter`** controller chart.
3. **CRD & Field Breaking Changes (`v1beta1` -> `v1`)**:
   - `spec.disruption.consolidationPolicy: WhenUnderutilized` -> renamed to **`WhenEmptyOrUnderutilized`**.
   - `spec.disruption.expireAfter` moved from `NodePool.spec.disruption` -> **`NodePool.spec.template.spec.expireAfter`**.
   - `EC2NodeClass` requires explicit **`spec.amiSelectorTerms`** (e.g., `alias: al2023@latest` or pinned SSM/AMI ID) alongside `amiFamily`.

## 3. Retired `ingress-nginx` & Critical OSS Controllers

- Flag `ingress.k8s.io/nginx` (`k8s.io/ingress-nginx`) deployments approaching upstream retirement and provide structured migration paths to **AWS Load Balancer Controller (`elbv2.k8s.aws`)** or **Kubernetes Gateway API**.
- Audit `cert-manager`, `external-dns`, `argo-cd`, and `metrics-server` against target Kubernetes API removals.
