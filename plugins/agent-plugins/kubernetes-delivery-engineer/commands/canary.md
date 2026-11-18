---
description: Configure, start, analyze, or promote progressive canary/blue-green rollouts using Argo Rollouts AnalysisTemplates and Traefik traffic splitting
argument-hint: "<rollout-or-service> [--namespace <ns>] [--step promote|pause|abort|migrate]"
---

Invoke **onboarding-and-migrating-to-argo-rollouts**, **progressing-argo-rollouts**, **gating-rollouts-with-analysis-and-experiments**, and **managing-traefik-traffic-routing** to manage progressive delivery safely:
1. If migrating from a standard `Deployment`, author an Argo `Rollout` spec with canary steps or blue-green preview/active services and Traefik weighted `TraefikService` routing.
2. Attach or validate Prometheus/HTTP `AnalysisTemplate` / `ClusterAnalysisTemplate` SLO gates (error rate, p95/p99 latency, saturation).
3. Inspect active `Rollout` and `AnalysisRun` status, evaluate canary vs. stable telemetry, and advance, pause, or abort the rollout based on verified health signals.

Canary target and action: $ARGUMENTS
