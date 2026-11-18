---
description: Validate rendered manifests, security posture, and live diffs before executing a gated Kubernetes Helm, ArgoCD, or Kargo deployment
argument-hint: "<release, argocd-app, or kargo-stage> [--namespace <ns>] [--revision <tag-or-sha>]"
---

Invoke **deploying-helm-charts**, **reviewing-helm-release-security**, **deploying-argocd-applications**, and **promoting-and-approving-freight** (as applicable to the workload's delivery mechanism) to perform a gated Kubernetes deployment:
1. Discover whether the target is managed via Helm release, ArgoCD `Application`, or Kargo `Stage` freight.
2. Render manifests and compute live cluster diffs (`helm template` / diff, ArgoCD diff/dry-run, or Kargo freight verification) while scanning for container/RBAC/secret security regressions.
3. Verify rollout readiness gates, PDBs, and target namespace health prior to mutation.
4. Execute the atomic upgrade, sync, or freight promotion and verify healthy pod convergence.

Deployment target: $ARGUMENTS
