# EKS Auto Mode, Karpenter Consolidation, and Pod Identity / IRSA Troubleshooting

## 1. EKS Auto Mode & Karpenter (`karpenter.sh/v1`) Diagnostics

EKS Auto Mode and self-managed Karpenter v1 use `NodePool`, `NodeClaim`, and `NodeClass` (`eks.amazonaws.com/v1` in Auto Mode; `EC2NodeClass` in `karpenter.k8s.aws/v1`).

### Inspecting NodeProvisioning Failures via `eks` MCP
1. List `NodePool` and `NodeClaim` resources:
   - `list_k8s_resources(cluster_name=..., kind="NodePool", api_version="karpenter.sh/v1")`
   - `list_k8s_resources(cluster_name=..., kind="NodeClaim", api_version="karpenter.sh/v1")`
2. Check `get_k8s_events` for Karpenter events:
   - `InsufficientCapacityError` (ICE): AWS EC2 lacks Spot/On-Demand capacity for the requested instance family in that AZ. **Fix**: Broaden `karpenter.sh/capacity-type` and `node.kubernetes.io/instance-type` requirements in `NodePool`.
   - `NodeClassNotReady`: Missing subnet/security group discovery tags (`karpenter.sh/discovery`) or missing IAM instance profile permissions.
   - `Consolidating` / `Disrupting` churn: Karpenter is evicting pods to pack nodes more tightly, causing latency spikes on stateful or slow-starting pods. **Fix**: Set `karpenter.sh/do-not-disrupt: "true"` annotation on latency-critical pods or configure `disruption.budgets` in the `NodePool` spec.

---

## 2. EKS Pod Identity vs. IRSA (`AccessDenied` Triage)

### Option A: EKS Pod Identity (`eks-pod-identity-agent` — Recommended)
When a pod fails with `AccessDenied` or `Unable to load credentials from eks-pod-identity` (`169.254.170.23` / `[fd00:ec2::23]`):
1. Verify the `eks-pod-identity-agent` DaemonSet is running on the node (`list_k8s_resources(kind="DaemonSet", namespace="kube-system")`).
2. Inspect Pod Identity Associations (`aws eks list-pod-identity-associations --cluster-name <cluster>`):
   - Confirm `namespace` and `serviceAccount` match the Pod's `spec.serviceAccountName` exactly.
3. Verify the IAM Role Trust Policy allows `pods.eks.amazonaws.com` with **both** `sts:AssumeRole` and `sts:TagSession`:
   ```json
   {
     "Effect": "Allow",
     "Principal": { "Service": "pods.eks.amazonaws.com" },
     "Action": ["sts:AssumeRole", "sts:TagSession"]
   }
   ```
4. Check NetworkPolicies: If a restrictive `NetworkPolicy` blocks egress on port `80` to `169.254.170.23/32`, the pod cannot fetch credentials from the node-local Pod Identity Agent!

### Option B: IAM Roles for Service Accounts (IRSA — OIDC)
When a pod fails with `WebIdentityErr` or `InvalidIdentityToken`:
1. Confirm the ServiceAccount has annotation `eks.amazonaws.com/role-arn: arn:aws:iam::<account>:role/<role-name>`.
2. Confirm the Pod has projected volume `aws-iam-token` and env vars `AWS_ROLE_ARN` + `AWS_WEB_IDENTITY_TOKEN_FILE` (injected by the mutating webhook; if missing, the pod was created before the SA annotation).
3. Confirm the IAM Role Trust Policy `Condition` `StringEquals` matches `<oidc-issuer>:sub` = `system:serviceaccount:<namespace>:<sa-name>` and `<oidc-issuer>:aud` = `sts.amazonaws.com`.
