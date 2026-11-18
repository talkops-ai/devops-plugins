# Workload Autoscaling (HPA / KEDA / VPA + Karpenter) & CAS → Karpenter Migration

## 1. Two-Tier Kubernetes Autoscaling Architecture

Karpenter scales **nodes** from unschedulable pod `requests` (in 30–60 seconds); **HPA**, **KEDA**, and **VPA** scale **pods**:

| Scaler | What It Scales | Signal Source | How to Align It with Karpenter |
|---|---|---|---|
| **HPA (`autoscaling/v2`)** | Replica count (`Deployment`/`StatefulSet`) | CPU/Memory (`metrics-server` `Op19`) or custom/external metrics | Set `behavior.scaleDown.stabilizationWindowSeconds: 300` so HPA doesn't oscillate replicas faster than Karpenter's `consolidateAfter` (`1m`–`2m`), avoiding node launch/terminate thrashing. |
| **KEDA (`keda.sh/v1alpha1`)** | Event-driven replica count (`0 → N`) | SQS `ApproximateNumberOfMessagesVisible`, Kafka/MSK lag, AMP PromQL, Cron | Ideal partner for Karpenter: KEDA bursts queue consumers from `0 → 50` pods on SQS backlog → Karpenter launches right-sized Spot nodes in ~45s → KEDA scales back to `0` → Karpenter consolidates empty nodes after `consolidateAfter`. |
| **VPA (`autoscaling.k8s.io/v1`)** | Pod `resources.requests` | Historical CPU/memory working-set | Run VPA in **`Off` (recommendation-only)** or **`Initial`** mode for HPA-managed workloads (never run VPA `Auto`/`Recreate` on CPU/memory alongside CPU/memory HPA on the same metric!). Use VPA recommendations to right-size over-requested pods so Karpenter stops over-provisioning EC2! |

### Consolidation-Safe Workload Contract (`Op21`, `OpM8`, `Sc10`)
1. **Memory `requests == limits` (`Op21`):** Always set `resources.requests.memory == resources.limits.memory` on pods running on `WhenEmptyOrUnderutilized` `NodePool`s (enforce defaults per namespace via `LimitRange`). Set accurate `requests.cpu` and omit or relax `limits.cpu` to avoid Linux CFS CPU throttling.
2. **Non-Blocking `PodDisruptionBudget`s:** Every multi-replica service needs a `policy/v1` PDB (`maxUnavailable: 1` or `25%`, NEVER `maxUnavailable: 0` or `minAvailable: 100%`, which permanently blocks Karpenter consolidation, expiry, and drift!).
3. **Topology Spread Across AZs & Hosts:** Pair `topologySpreadConstraints` (`topology.kubernetes.io/zone` + `kubernetes.io/hostname`) so Karpenter spreads replicas across `>= 2–3` AZs instead of bin-packing every replica of a critical service onto a single large Spot instance!
4. **Opt-Out Annotation (`OpM8`):** Annotate pods (not nodes) that must never be evicted mid-execution:
   ```yaml
   metadata:
     annotations:
       karpenter.sh/do-not-disrupt: "true"
   ```
5. **CoreDNS Scaling Under Churn (`OpM7`, `Sc6`–`Sc8`):** Deploy `cluster-proportional-autoscaler` (e.g., `coresPerReplica: 256`, `nodesPerReplica: 16`, `min: 2`), ensure Corefile includes `health { lameduck 5s }` + `ready`, and add `NodeLocal DNSCache` on clusters >50 nodes or high Spot churn.

---

## 2. Production KEDA + SQS + Karpenter Worker Pattern

Use **EKS Pod Identity** (`TriggerAuthentication` `podIdentity.provider: aws`) — zero static credentials:

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-aws-pod-identity
  namespace: workers
spec:
  podIdentity:
    provider: aws
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-processor-scaler
  namespace: workers
spec:
  scaleTargetRef:
    name: order-processor
  minReplicaCount: 0          # Scales to zero when queue is empty; Karpenter reclaims nodes
  maxReplicaCount: 60
  pollingInterval: 15
  cooldownPeriod: 180         # > Karpenter consolidateAfter (60s) to prevent node thrash
  triggers:
    - type: aws-sqs-queue
      authenticationRef:
        name: keda-aws-pod-identity
      metadata:
        queueURL: https://sqs.us-east-1.amazonaws.com/111122223333/orders-queue
        queueLength: "25"
        awsRegion: us-east-1
        identityOwner: operator
```

---

## 3. Zero-Downtime Cluster Autoscaler (CAS) → Karpenter Migration Runbook

**CRITICAL ANTI-PATTERN (`Op18`):** Never leave Cluster Autoscaler and Karpenter actively scaling overlapping node pools indefinitely — CAS scales ASGs while Karpenter launches standalone `NodeClaim`s, causing oscillation and stuck scale-ins.

Execute this **7-step zero-downtime cutover**:

1. **Step 1 — Pre-Migration Audit:**
   - Verify VPC CNI IP headroom (`aws ec2 describe-subnets` / Prefix Delegation `ENABLE_PREFIX_DELEGATION=true`) for temporary parallel nodes during cutover.
   - Audit all multi-replica Deployments/StatefulSets for valid PDBs (`disruptionsAllowed > 0`), `readinessProbe`s, `requests.memory == limits.memory`, and EBS PV AZ topology constraints.
2. **Step 2 — Pin System Add-ons to a Small System MNG:**
   - Keep (or create) one small 2–3 node Managed Node Group (`system-mng`, `minSize=2, maxSize=4`, WITHOUT `k8s.io/cluster-autoscaler/enabled` tags) with `nodeAffinity` / taint `CriticalAddonsOnly=true:NoSchedule` to host `karpenter`, `coredns`, and critical cluster controllers (`Op20`, `Sc21`).
3. **Step 3 — Provision Karpenter AWS Prerequisites & Install Helm Chart:**
   - Tag subnets/SGs with `karpenter.sh/discovery = <cluster-name>`.
   - Create `KarpenterNodeRole` + `EC2_LINUX` Access Entry, `KarpenterControllerRole` + Pod Identity association, and the SQS Spot Interruption Queue + 4 EventBridge rules (`bootstrap-iam-sqs-and-iac.md`).
   - Install `karpenter-crd` and `karpenter` (2 replicas on `system-mng`). At this point **zero `NodePool`s exist yet**, so Karpenter takes zero action.
4. **Step 4 — Disable Cluster Autoscaler BEFORE Creating Active `NodePool`s:**
   - Scale down Cluster Autoscaler to `0` replicas so CAS stops reacting to unschedulable pods:
     ```bash
     kubectl scale deploy/cluster-autoscaler -n kube-system --replicas=0
     ```
5. **Step 5 — Apply `EC2NodeClass` and `NodePool`s:**
   - Apply the validated `EC2NodeClass` and `NodePool` manifests (`nodepool-and-nodeclass-patterns.md`). Verify `kubectl get ec2nodeclass,nodepool` shows `Ready=True` (zero `NodeClassNotReady` conditions).
6. **Step 6 — Cordon & Gradually Drain Legacy CAS Node Groups:**
   - One legacy MNG/ASG at a time:
     1. Cordon nodes in that MNG (`kubectl cordon -l eks.amazonaws.com/nodegroup=<old-ng>`).
     2. Drain 1–2 nodes (`kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`).
     3. Observe Pending pods trigger Karpenter `NodeClaim` creation (`kubectl get nodeclaims -w` and `kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter`). Confirm new Karpenter nodes reach `Ready` in ~45–60s and pods pass `readinessProbe`s.
     4. Drain remaining nodes in the legacy MNG and delete the legacy MNG via Terraform/CDK/CloudFormation/eksctl.
7. **Step 7 — Decommission Cluster Autoscaler Cleanly:**
   - Uninstall the `cluster-autoscaler` Helm release/Deployment, remove `k8s.io/cluster-autoscaler/*` ASG tags, and delete the legacy CAS IRSA/IAM role in IaC.
