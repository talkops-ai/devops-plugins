---
name: eks-karpenter-autoscaling
description: "Architect, bootstrap, audit, right-size, migrate, and troubleshoot Amazon EKS node and workload autoscaling with Karpenter v1 (karpenter.sh/v1 & karpenter.k8s.aws/v1) and EKS Auto Mode (eks.amazonaws.com/v1), paired with HPA, KEDA, and VPA. Covers AWS infrastructure prerequisites (KarpenterControllerRole via EKS Pod Identity/IRSA, KarpenterNodeRole + EC2_LINUX Access Entry, SQS Spot Interruption Queue + 4 EventBridge rules, karpenter.sh/discovery tags, Terraform/CDK/CloudFormation/Helm OCI setup), multi-arch Graviton + x86 On-Demand/Spot/GPU NodePool & EC2NodeClass authoring, consolidation & disruption budgets (WhenEmptyOrUnderutilized, SpotToSpotConsolidation, expireAfter, do-not-disrupt), zero-downtime Cluster Autoscaler (CAS) to Karpenter migration, and Karpenter provisioning/Prometheus (:8080/metrics) diagnostics. Strictly MCP-only live inspection via aws-mcp (aws___run_script) and eks MCP — never run raw aws, kubectl, eksctl, or helm CLI shell commands."
---

# Amazon EKS Autoscaling with Karpenter v1 & EKS Auto Mode

Design, provision, audit, right-size, and troubleshoot Kubernetes compute and workload autoscaling on Amazon EKS using **Karpenter v1 (`karpenter.sh/v1`)**, **EKS Auto Mode (`eks.amazonaws.com/v1`)**, and **HPA / KEDA / VPA**.

## Authoritative Reference Routing (Load Before Acting)

Always read the matching local reference file(s) before authoring manifests, IaC, migration runbooks, or diagnostic plans:

| Task / User Intent | Reference File to Load |
|---|---|
| Bootstrap Karpenter from scratch, IAM roles (`KarpenterControllerRole`, `KarpenterNodeRole`), EKS Pod Identity / Access Entries, SQS Spot Interruption Queue + 4 EventBridge rules, subnet/SG `karpenter.sh/discovery` tags, Terraform / CDK / CloudFormation / OCI Helm install | [references/bootstrap-iam-sqs-and-iac.md](references/bootstrap-iam-sqs-and-iac.md) |
| Author or right-size `NodePool` & `EC2NodeClass` (`karpenter.sh/v1`) or EKS Auto Mode `NodeClass` (`eks.amazonaws.com/v1`), Graviton (`arm64`) + `amd64`, Spot/On-Demand pools, `weight` & exclusivity, `limits`, `consolidationPolicy`, cron `budgets`, pinned `al2023@v...` AMIs, GPU/Neuron/ML pools | [references/nodepool-and-nodeclass-patterns.md](references/nodepool-and-nodeclass-patterns.md) |
| Combine HPA / KEDA / VPA with Karpenter, enforce `requests.memory == limits.memory`, tune CoreDNS under node churn, or execute a zero-downtime **Cluster Autoscaler (CAS) → Karpenter** migration | [references/workload-autoscaling-and-cas-migration.md](references/workload-autoscaling-and-cas-migration.md) |
| Run a 16-gate Karpenter operational best-practices audit, debug `Pending` pods / `InsufficientCapacityError` / `NodeClassNotReady` / consolidation thrashing / etcd lease churn, or configure Prometheus `:8080/metrics` & CloudWatch alarms | [references/diagnostics-and-observability.md](references/diagnostics-and-observability.md) |

---

## Core Architecture Decision: EKS Auto Mode vs. Self-Managed Karpenter v1

Evaluate this boundary first — **NEVER deploy self-managed Karpenter on an EKS Auto Mode cluster (`Op17`)** unless Auto Mode compute is explicitly disabled, or two controllers will fight over unschedulable pods:

| Dimension | EKS Auto Mode (`computeConfig.enabled = true`) | Self-Managed Karpenter v1 (`oci://public.ecr.aws/karpenter/karpenter`) |
|---|---|---|
| **Control Plane / Hosting** | AWS-managed off-cluster (zero controller pods in `kube-system`, zero SQS/EventBridge setup). | Customer-managed Helm deployment — **MUST run on a small 2-node MNG or Fargate profile (`Op20`), NEVER on Karpenter-managed nodes!** |
| **NodeClass CRD** | `apiVersion: eks.amazonaws.com/v1`, `kind: NodeClass` | `apiVersion: karpenter.k8s.aws/v1`, `kind: EC2NodeClass` |
| **NodePool CRD** | `apiVersion: karpenter.sh/v1`, `kind: NodePool` (labels prefixed `eks.amazonaws.com/*`) | `apiVersion: karpenter.sh/v1`, `kind: NodePool` (labels prefixed `karpenter.k8s.aws/*`) |
| **OS & Node Access** | Appliance OS (Bottlerocket-based, SELinux enforcing, read-only rootfs, no SSH/SSM, max 21-day node lifetime). | AL2023, Bottlerocket, Windows, or custom AMIs; full `nodeadm` `userData`, custom `blockDeviceMappings`, and SSM access. |
| **Pricing** | Per-instance EKS Auto Mode management fee on top of EC2 cost. | `$0` Karpenter software fee (standard EC2 + MNG/Fargate hosting cost only). |
| **Best Fit** | Turnkey operations, standard web/API/GPU workloads, built-in ALB ingress + EBS storage + Pod Identity. | Fine-grained Spot-to-Spot consolidation, custom AMIs/init scripts, custom `expireAfter` (>21d), EFA/custom EBS/instance-store RAID, or strict zero-surcharge FinOps. |

---

## Non-Negotiable Production Invariants (`Op10`–`Op28`)

Every Karpenter design, IaC module, or cluster audit produced by this skill MUST enforce these 12 invariants:

1. **Single Node Autoscaler (`Op18`) & Auto Mode Dedup (`Op17`):** Never allow Cluster Autoscaler (CAS) and Karpenter to scale the same workload pool simultaneously (causes race conditions, double scale-out, and scale-down deadlocks). On Auto Mode clusters, ensure zero leftover self-managed `karpenter` / `cluster-autoscaler` deployments exist.
2. **Never Self-Host the Karpenter Controller (`Op20`):** Host `karpenter` pods (2 replicas with zone anti-affinity + PDB) on a dedicated system Managed Node Group (`CriticalAddonsOnly` taint) or an EKS Fargate profile for the `karpenter` namespace — never on `karpenter.sh/nodepool` nodes where consolidation/drift can evict the controller itself.
3. **Wire SQS Interruption Handling (`OpM1`):** For self-managed Karpenter using Spot, always provision the encrypted SQS interruption queue + all 4 EventBridge rules (EC2 Spot Interruption Warning, EC2 Rebalance Recommendation, EC2 Instance State-Change, AWS Health Scheduled Change) and pass `--interruption-queue=<queue-name>` (`settings.interruptionQueue`).
4. **Enforce Blast-Radius `limits` on Every `NodePool` (`Op10`):** Every `NodePool` MUST set realistic `spec.limits.cpu` and `spec.limits.memory` ceilings so a runaway HPA/Job loop cannot launch unbounded EC2 spend.
5. **Broaden Spot Instance Diversity (`Op22`, `Sc4`):** Spot `NodePool`s MUST allow `>= 3` instance families (`c`, `m`, `r` across generations `>= 6`, excluding burstable `t` instances for steady prod workloads `Sc5`) across `>= 2–3` AZs so `price-capacity-optimized` allocation avoids `InsufficientCapacityError` (ICE).
6. **Pin Tested AMI Aliases in Production (`Op11`):** In production `EC2NodeClass`, pin a staging-verified alias version (`alias: al2023@v20260807`) rather than floating `al2023@latest`, while keeping `al2023@latest` in Dev/Staging to catch regressions early. Never use EOL `AL2` (`>= 1.33` hard blocker).
7. **Make Multiple `NodePool`s Mutually Exclusive or Weighted (`Op27`):** When >1 `NodePool` can match a pod, either isolate pools with distinct `taints`/`nodeSelector`s OR set explicit `spec.weight` (`10`–`100`) so scheduling is deterministic rather than random.
8. **Enable Consolidation + `SpotToSpotConsolidation` + Bounded `expireAfter` (`Op12`, `Op13`, `Op28`):** Configure `consolidationPolicy: WhenEmptyOrUnderutilized` with `consolidateAfter` (`30s`–`2m`), `expireAfter: 720h` (never `Never`), `disruption.budgets` (including business-hours cron freezes where needed), and `settings.featureGates.spotToSpotConsolidation=true`.
9. **Enforce `requests.memory == limits.memory` on Consolidated Pods (`Op21`):** Karpenter packs nodes based on pod `requests`. If `requests.memory << limits.memory`, tight consolidation packs bursting pods onto smaller nodes and triggers kernel `OOMKilled` (`Exit Code 137`). Pair with `PodDisruptionBudget` (`minAvailable` / `maxUnavailable`, never `maxUnavailable: 0` on 1-replica apps) and `topologySpreadConstraints`.
10. **Protect Interruption-Sensitive Jobs with `do-not-disrupt` (`OpM8`, `M8`):** Add `karpenter.sh/do-not-disrupt: "true"` on long-running ML/GPU training pods, non-checkpointed batch jobs, or active migration workers (or isolate them in a `consolidationPolicy: WhenEmpty` `NodePool`).
11. **Scale CoreDNS for Rapid Node Churn (`OpM7`, `Sc6`–`Sc8`):** Pair Karpenter with `cluster-proportional-autoscaler` (or HPA) on `coredns`, `lameduck 5s` in the Corefile, and **NodeLocal DNSCache** on high-churn clusters.
12. **Scrape `:8080/metrics` & Alert on Queue/CloudProvider Failures (`O18`, `NH24`):** Scrape Karpenter controller Prometheus metrics and alert on `karpenter_cloudprovider_errors_total`, `karpenter_scheduler_unschedulable_pods_count`, and `karpenter_pods_startup_duration_seconds`.

---

## Execution & Guardrail Rules

1. **MCP-Only Live Inspection (Zero Raw Shell CLI):** Execute **all** live EKS, EC2, IAM, CloudWatch, Pricing, and IaC checks **exclusively via connected MCP servers**: use `aws-mcp` (`aws___run_script` calling read-only `call_boto3` for `sts:GetCallerIdentity`, `eks:ListClusters`, `eks:DescribeCluster`, `eks:ListAccessEntries`, `ec2`, `iam`, `sqs`, `events`), `eks` (`list_k8s_resources`, `manage_k8s_resource(operation="read")`, `get_k8s_events`, `get_eks_vpc_config`, `get_eks_insights`, `search_eks_troubleshoot_guide`), `cloudwatch` (`get_metric_data`, `get_active_alarms`), `awspricing` / `pricing` (`get_pricing`), and `awsiac` / `aws-iac` (`validate_cloudformation_template`, `check_cloudformation_template_compliance`). **Never** shell out to raw `aws` (including `aws sts get-caller-identity` or `aws eks list-clusters`), `kubectl`, `eksctl`, `helm`, or `python3 -c` commands in Bash/`run_command`!
2. **`awsknowledge` Fallback for Unmapped Edge Cases:** If a question involves an EKS Auto Mode or Karpenter AWS integration detail not covered in `references/*.md`, immediately query `awsknowledge` / `aws-mcp` (`aws___search_documentation` / `aws___read_documentation` — 1–2 focused searches) and answer directly.
3. **Vague Sizing Guard:** Never invent `NodePool` `limits.cpu` / `limits.memory` or monthly dollar savings without either live cluster node/pod request telemetry or user-supplied vCPU/memory figures; show exact Container Insights / PromQL queries to collect baseline slack when missing.
4. **Approval-Gated GitOps/IaC Changes & Safe Node Rollover:** Present complete IaC/GitOps diffs (Terraform, CDK, CloudFormation, or Kubernetes `NodePool`/`EC2NodeClass` YAML via ArgoCD/Flux GitOps PRs), blast radius, and rollback steps, and wait for explicit user approval before any live apply. When refusing unapproved live mutations (`helm upgrade`, `kubectl apply`, or destructive `kubectl delete nodes --all`), always warn of the catastrophic cluster-wide outage and prescribe **approval-gated GitOps/IaC deployments** paired with **gradual node cordoning and draining** (`kubectl cordon` + rolling canary `kubectl drain`, or declarative `NodePool` drift/expiry rollover).
