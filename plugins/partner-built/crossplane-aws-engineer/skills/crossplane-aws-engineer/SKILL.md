---
name: crossplane-aws-engineer
description: Design, generate, review, troubleshoot, and validate Crossplane platform APIs for AWS. Use for any AWS service Managed Resource, XRD, Claim, Pipeline Composition, Upbound provider package, IRSA, management policy, connection secret, Argo CD, Terraform-to-Crossplane migration, or composition rendering task.
license: Apache-2.0
compatibility: Requires Crossplane CLI 1.16 or later, kubectl, Docker for function rendering, and pinned Upbound provider/function packages. Verify versions against the target cluster.
metadata:
  version: "1"
  role: Principal Cloud Platform Architect
  target-provider: xpkg.upbound.io/upbound/provider-aws-*
  composition-mode: Pipeline
---

# Crossplane AWS Platform Engineer

## Scope and service coverage

This skill is a general Crossplane authoring and operations guide for AWS, not a pre-generated catalog of every AWS CRD. AWS provider families expose hundreds of resources whose fields vary by provider release. For any service, discover the exact installed provider CRD schema first, then generate the Managed Resource behind a domain-oriented XRD and Claim. The included assets are foundational teaching and review fixtures for VPC, S3, RDS PostgreSQL, providers, and IRSA; they are not a claim that every AWS service has a bundled Composition.

Use `references/aws-service-authoring.md` for the repeatable workflow for services not included in `assets/`, and `references/provider-schema-discovery.md` before using any provider field or API version.

## Non-negotiable guardrails

1. Use `spec.mode: Pipeline`; do not author new `mode: Resources` Compositions.
2. Hide provider Managed Resources behind an XRD and a namespaced Claim. Do not expose raw provider CRs to application teams unless explicitly designing a platform-admin API.
3. Install only the modular Upbound provider packages required by the platform. Pin versions and verify package compatibility; do not assume provider fields are stable across releases.
4. Use IRSA through `DeploymentRuntimeConfig` and `credentials.source: IRSA`; never generate or request long-lived AWS access keys.
5. Define the consumer API first with strict OpenAPI schemas, descriptions, defaults, enums/ranges/patterns, and a documented status/secret contract.
6. Use `managementPolicies` deliberately. For critical state, use `deletionPolicy: Orphan` and provider-side deletion protection where supported; explain the recovery and cleanup path.
7. Resolve composed-resource dependencies with `*Selector`/`matchControllerRef`, explicit refs, or observed composite status. Never assume a sibling composed resource has the XR name.
8. Treat connection data as sensitive. Write provider secrets only to the controlled system namespace, filter keys in the XRD, project only approved keys, and never print secret values.
9. Generate collision-resistant external names from claim/XR metadata. Do not hardcode physical names in reusable Compositions.
10. Render and schema-validate before GitOps synchronization. A successful render proves pipeline shape, not AWS authorization, quota, networking, or eventual readiness.
11. Never call a subnet public because it maps public IPs; verify route tables and routes to an Internet Gateway.
12. Do not make a parameter configurable unless the Composition actually implements it.

## Beginner workflow

1. Read `references/getting-started.md` and identify the target Crossplane/provider/function versions.
2. Inspect the repository's Crossplane, provider, function, Kubernetes, and GitOps conventions.
3. Select or install only the required provider family packages and composition functions. Configure IRSA before creating AWS Managed Resources.
4. For a new AWS service, read `references/aws-service-authoring.md`, discover the CRD using `references/provider-schema-discovery.md`, and record the exact `apiVersion`, `kind`, fields, references, and connection keys.
5. Translate the requested contract from Terraform variables/modules/outputs into an XRD, Composition, and Claim. Read `references/terraform-to-crossplane-cheatsheet.md`.
6. Define the consumer API: group, version, claim kind, required parameters, validation, status fields, lifecycle policy, and approved connection keys.
7. Implement a Pipeline Composition using `function-patch-and-transform`; add `function-auto-ready` last unless a custom readiness strategy is required.
8. Patch region, tags, provider config, parameters, and status explicitly. Use controller-reference selectors for sibling composed resources and late-binding refs for external dependencies.
9. Add lifecycle policy, provider authentication, secret propagation, and GitOps metadata only when owned by this repository. Read the matching reference file.
10. Run `scripts/check-manifests.sh`, then `scripts/render-test.sh` with pinned functions, then `scripts/validate-schemas.sh` with the exact provider schema bundle.
11. For a live cluster, use server-side dry run where appropriate, then inspect `kubectl get`, `kubectl describe`, conditions, events, provider logs, and Argo CD health. Crossplane is asynchronous; do not claim readiness from YAML alone.

## Terraform translation

- Terraform module -> XRD contract + Composition implementation.
- Terraform variables -> XRD OpenAPI parameters.
- Module call -> namespaced Claim.
- Terraform resource -> provider Managed Resource composed behind the API.
- `depends_on` -> references/selectors and reconciliation conditions.
- Terraform output -> XR status or filtered connection details.
- `prevent_destroy` -> `deletionPolicy: Orphan`, provider deletion protection, and restricted management policy where appropriate.
- `ignore_changes` -> narrowly scoped management/ownership policy; never silently suppress drift.

## Review checklist

Check every generated resource for: exact provider schema, providerConfigRef, region/account boundary, dynamic naming, selectors/refs, readiness, deletion behavior, encryption, private networking, IAM scope, secret exposure, tags, observability, backups, quotas, and GitOps ownership. Report file/line, severity, evidence, impact, and a concrete correction.

## Reference routing

- First run and lifecycle: `references/getting-started.md`
- Any AWS service: `references/aws-service-authoring.md`
- Provider CRD lookup: `references/provider-schema-discovery.md`
- Terraform migration: `references/terraform-to-crossplane-cheatsheet.md`
- Upbound providers and IRSA: `references/aws-provider-and-auth.md`
- Pipeline functions: `references/composition-functions.md`
- Secrets: `references/connection-secrets.md`
- Argo CD: `references/gitops-argocd-integration.md`
- Failure diagnosis: `references/troubleshooting.md`
- Reusable fixtures: `assets/`
- Verification: `scripts/`
