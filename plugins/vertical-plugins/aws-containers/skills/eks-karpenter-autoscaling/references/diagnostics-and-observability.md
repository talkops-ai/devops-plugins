# Karpenter Operational Audit Scorecard, Troubleshooting & `:8080/metrics` Observability

## 1. The 16-Gate Karpenter Operational Audit Scorecard

When asked to audit or right-size an existing Karpenter / EKS Auto Mode cluster, discover clusters first via `aws-mcp` `aws___run_script` (`await call_boto3(service_name="eks", operation_name="ListClusters", region_name=...)` + `sts:GetCallerIdentity` — **never** run `aws eks list-clusters` or `aws sts get-caller-identity` in Bash/`run_command`!) and evaluate every gate below using read-only `eks`, `aws-mcp`, and `cloudwatch` MCP calls:

| Gate ID | Check | Pass Criteria | Severity |
|---|---|---|---|
| **KP-01 (`Op17`/`Op18`)** | Single node autoscaler | Zero simultaneous CAS + Karpenter; zero self-managed Karpenter on Auto Mode | Critical |
| **KP-02 (`Op20`)** | Controller placement | `karpenter` pods run on MNG or Fargate, NEVER on `karpenter.sh/nodepool` nodes | Critical |
| **KP-03 (`OpM1`)** | Interruption queue wired | `--interruption-queue` / `settings.interruptionQueue` set + SQS queue & 4 EventBridge rules active | High |
| **KP-04 (`Op10`)** | `NodePool` resource limits | Every `NodePool` defines bounded `spec.limits.cpu` and `spec.limits.memory` | High |
| **KP-05 (`Op11`)** | Production AMI hygiene | No EOL `AL2`; prod `EC2NodeClass` pins tested `al2023@v...` alias (not static `ami-*` ID or untested `@latest`) | High |
| **KP-06 (`Op12`)** | Consolidation policy | `WhenEmptyOrUnderutilized` on general pools; `WhenEmpty` on GPU/training pools (`M8`) | Medium |
| **KP-07 (`Op13`)** | Node expiry (`expireAfter`) | `expireAfter` set (e.g. `720h`, `<=504h` on Auto Mode), NOT `Never` | Medium |
| **KP-08 (`Op22`/`Sc4`)** | Spot instance & AZ diversity | Spot `NodePool` allows `>=3` families across `>=2–3` AZs; excludes burstable `t` for steady prod (`Sc5`) | High |
| **KP-09 (`Op27`)** | `NodePool` weighting / exclusivity | Overlapping `NodePool`s set deterministic `spec.weight` or mutually exclusive taints | Medium |
| **KP-10 (`Op28`)** | `SpotToSpotConsolidation` | `spotToSpotConsolidation=true` enabled when Spot `NodePool`s exist | Low |
| **KP-11** | Disruption budgets | `spec.disruption.budgets` neither blocks all drains (`nodes: "0"` 24x7) nor allows 100% simultaneous eviction | High |
| **KP-12 (`Op21`)** | Workload memory sizing | Consolidated pods set `requests.memory == limits.memory` + valid PDB (`disruptionsAllowed > 0`) | High |
| **KP-13 (`OpM7`)** | CoreDNS churn resilience | `coredns` has `>=2` replicas + CPA/HPA + `lameduck` + AZ spread | Medium |
| **KP-14** | Multi-arch Graviton adoption | `kubernetes.io/arch` includes `arm64` where multi-arch OCI images exist (~20% savings) | Medium |
| **KP-15 (`R-ETCD-6`)** | Controller health & lease count | 2 Ready replicas (1 leader + 1 standby), zero CrashLoops, no duplicate Karpenter installs churning etcd `leases` | High |
| **KP-16 (`O18`)** | Metrics & alarms configured | `:8080/metrics` scraped into AMP / CloudWatch with `NH24`–`NH24c` alerts | Medium |

---

## 2. Pending-Pod & Provisioning Failure Decision Tree

When pods remain `Pending` or `NodeClaim`s fail to join `Ready`, inspect `get_k8s_events`, `NodePool`/`NodeClaim`/`EC2NodeClass` status conditions, and Karpenter controller logs in this exact order:

| Symptom / Event | Root Cause | Exact Verification | Fix |
|---|---|---|---|
| **`NodeClassNotReady` (`SubnetsNotFound` / `SecurityGroupsNotFound` / `AMIUnavailable`)** | Missing `karpenter.sh/discovery` tags on subnets/SGs, missing `ssm:GetParameter` / `ec2:Describe*` on controller role, or invalid `amiSelectorTerms`. | `manage_k8s_resource(operation="read", kind="EC2NodeClass")` → `.status.conditions`, `.status.subnets`, `.status.amis`. | Tag private subnets & node SG with `karpenter.sh/discovery=<cluster>`, fix `amiSelectorTerms`, or attach missing controller IAM actions. |
| **`FailedScheduling`: `no instance type met all requirements`** | Contradictory pod `nodeSelector`/`affinity`/resource requests vs `NodePool.spec.template.spec.requirements` (e.g., pod requests `arm64` or `64Gi` RAM, but `NodePool` caps `instance-cpu` at `4` or `amd64`-only). | Compare Pod `spec` (`nodeSelector`, `affinity`, `tolerations`, `resources.requests`, PVC AZ) against every `NodePool` `requirements` + `taints`. | Broaden `NodePool` `requirements` (`instance-cpu`, `instance-category`, `arch`) or add matching toleration to the pod. |
| **`NodePool` `limits` Reached** | Total provisioned CPU/memory/GPU across `NodeClaim`s hit `NodePool.spec.limits`. | `manage_k8s_resource(operation="read", kind="NodePool")` → compare `.status.resources` vs `.spec.limits`. | Right-size over-requested pods first; if legitimate growth, raise `spec.limits` via IaC/GitOps. |
| **`InsufficientCapacityError` (ICE) on EC2 `CreateFleet`** | Regional/AZ Spot or GPU capacity exhaustion for narrow instance selection, or Regional EC2 vCPU Service Quota (`L-1216C47A` Standard / `L-34B43A08` Spot / `L-DB2E81BA` G/VT) reached. | Controller logs + `service-quotas get-service-quota` + `NodeClaim` events. | Expand Spot `NodePool` across `c`/`m`/`r` generations 6–8, add lower-weight On-Demand fallback `NodePool` (`weight: 10`), or request vCPU quota increase. |
| **`NodeClaim` Launched EC2, Node Never Joins (`NodeNotRegistered`)** | Missing `EC2_LINUX` EKS Access Entry for `KarpenterNodeRole`, private subnet lacks NAT or ECR/STS/S3/EKS VPC Endpoints, or broken custom `EC2NodeClass.spec.userData` (`bootstrap.sh` used on AL2023!). | Check `aws eks list-access-entries`, `ec2 describe-instances` state, and VPC route tables / endpoints (`ecr.api`, `ecr.dkr`, `s3`, `sts`). | Create `EC2_LINUX` Access Entry for `KarpenterNodeRole`, convert `userData` to `nodeadm` `NodeConfig`, and verify private subnet egress/endpoints. |
| **Pod Stuck `ContainerCreating` After Node Joins (`FailedAttachVolume` / `FailedCreatePodSandBox`)** | EBS volume attachment limit per instance exceeded (`Sc22`: ~28 shared ENI+EBS slots on 5th/6th-gen Nitro; up to 64 dedicated on 7th-gen+), or VPC CNI subnet IP exhaustion. | `get_k8s_events` + `ec2 describe-subnets` `AvailableIpAddressCount`. | Require `instance-generation Gt 6` (`m7g`/`m7i`+) for PVC-dense workloads, or enable VPC CNI Prefix Delegation (`ENABLE_PREFIX_DELEGATION=true`). |
| **Frequent Latency Spikes / Pod Restarts Every Few Minutes** | Aggressive consolidation (`consolidateAfter: 0s`) evicting pods without `preStop` hooks, ALB readiness gates, PDBs, or with `requests.memory < limits.memory`. | `get_k8s_events` (`Disrupting` / `Consolidating` events) + pod `exitCode` (`143` SIGTERM vs `137` OOMKilled). | Increase `consolidateAfter` (`2m`–`5m`), set `requests.memory == limits.memory`, add PDBs + ALB readiness gates + `preStop: sleep 15`, or set `karpenter.sh/do-not-disrupt: "true"` on stateful/batch pods. |

---

## 3. Karpenter Prometheus Metrics (`:8080/metrics`) & Recommended Alarms (`O18`, `NH24`)

Scrape port `8080` (`/metrics`) on the `karpenter` Service into Amazon Managed Service for Prometheus (AMP) or CloudWatch Container Insights Prometheus, and configure these production alerts:

| Check ID | Metric / PromQL Expression | Healthy Baseline | Alert Threshold & Severity | Meaning |
|---|---|---|---|---|
| **`NH24`** | `sum(increase(karpenter_cloudprovider_errors_total[5m])) by (controller, error)` | `< 10` / 5m | `> 10` in 5m (**High**) | EC2 `InsufficientCapacityError`, `RequestLimitExceeded` API throttling (`ScM6`), or IAM `UnauthorizedOperation`. |
| **`NH24b`** | `max(karpenter_scheduler_unschedulable_pods_count)` and `max(karpenter_scheduler_queue_depth)` | `< 5` | `> 5` sustained for 10m (**High**) | Karpenter scheduling loop is falling behind or blocked by `NodePool` limits / unsatisfiable pod constraints. |
| **`NH24c`** | `histogram_quantile(0.95, sum(rate(karpenter_pods_startup_duration_seconds_bucket[10m])) by (le))` | `< 120s` | `> 180s` sustained (**Medium**) | Slow pending-to-running pod latency (large uncached container images, slow `userData`, or repeated ICE retries). |
| **Pool Utilization** | `karpenter_nodepools_usage{resource_type="cpu"} / karpenter_nodepools_limit{resource_type="cpu"} * 100` | `< 80%` | `> 85%` (**Warning**) / `> 95%` (**Critical**) | `NodePool` approaching `spec.limits` ceiling; scale-out will halt at 100%. |
| **Interruption Rate** | `sum(increase(karpenter_interruption_received_messages_total[15m])) by (message_type)` | Occasional | Spike in `spot_interrupted_warning` (**Info/Warn**) | Regional Spot pool reclamation wave; verify workloads failed over cleanly to diversified Spot or On-Demand pools. |
