---
description: Capture pre-rollback diagnostics and execute a safe rollback across Helm releases, ArgoCD applications, Argo Rollouts, or Kargo stages
argument-hint: "<release, rollout, argocd-app, or kargo-stage> [--namespace <ns>] [--to-revision <rev>]"
---

Invoke **upgrading-and-rolling-back-helm-releases**, **rolling-back-argocd-applications**, **troubleshooting-argo-rollouts**, or **rolling-back-kargo-stages** (matching the workload's delivery controller) to perform a controlled rollback:
1. Capture failing pod events, rollout conditions, AnalysisRun failures, and current revision metadata before mutating state so forensic evidence is preserved.
2. Identify the last known-good revision/freight and check for ArgoCD auto-sync self-heal loops or stateful schema incompatibilities that could interfere with rollback.
3. Execute the gated rollback (aborting degraded rollouts, rolling back Helm/ArgoCD revision, or re-promoting prior verified Kargo freight) and confirm service recovery.

Rollback target: $ARGUMENTS
