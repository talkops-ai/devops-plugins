---
description: Onboard a workload or repository into Kubernetes GitOps delivery across Helm charts, ArgoCD projects/applications, Kargo promotion stages, and Traefik ingress
argument-hint: "<service-name, repo-url, or chart-path> [--namespace <ns>] [--gitops argocd|kargo]"
---

Invoke **onboarding-argocd-repositories-and-projects**, **deploying-helm-charts**, **onboarding-kargo-pipelines**, and **managing-traefik-traffic-routing** (plus **securing-traefik-tls-and-certificates** when external ingress is requested) to onboard the target service end-to-end:
1. Inspect existing Kubernetes cluster context, target namespace, and repository/chart layout.
2. Scaffold or validate Helm chart values, security contexts, probes, and resource requests/limits (**reviewing-helm-release-security**).
3. Author least-privilege ArgoCD `AppProject` + `Application` manifests (and optional Kargo `Warehouse` + `Stage` promotion pipeline).
4. Configure Traefik `IngressRoute` / TLS policies if external or internal routing is needed, dry-run validate all rendered manifests, and present the diff before applying any cluster mutations.

Onboarding target: $ARGUMENTS
