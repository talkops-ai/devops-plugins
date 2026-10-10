# Crossplane AWS Platform Engineer

Partner-built Agent Plugin for authoring, reviewing, validating, and operating Crossplane AWS platform APIs. It teaches a general schema-discovery workflow for the full AWS provider surface and includes tested teaching fixtures for foundational VPC, S3, RDS PostgreSQL, provider authentication, and composition functions.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install crossplane-aws-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugin hosts | Load this directory; `plugin.json` and `skills/` follow the portable Agent Plugins format |

## Requirements

Crossplane 1.16+, `kubectl`, Docker for composition rendering, pinned Crossplane Functions, and the exact Upbound provider packages/CRD schemas used by the target cluster. AWS provisioning additionally requires a correctly scoped IRSA role and ProviderConfig.

## What it covers

- Crossplane control-plane concepts and Terraform migration
- XRDs, namespaced Claims, Pipeline Compositions, patches, transforms, selectors, and readiness
- Any AWS service through provider-package and CRD schema discovery
- Upbound modular providers, IRSA, ProviderConfig, and least privilege
- Network, storage, database, compute, messaging, identity, security, edge, and observability review checklists
- Connection-secret filtering, lifecycle protection, Argo CD, troubleshooting, and offline validation

## Included fixtures

- `assets/vpc-network/`: minimal routed VPC/public subnet teaching fixture
- `assets/s3-bucket/`: encrypted, private, versioned S3 fixture
- `assets/rds-postgres/`: private PostgreSQL fixture with subnet group, security group, deletion protection, and filtered credentials
- `assets/authentication/`: provider-family/service provider and IRSA examples

These are reviewed examples, not universal production defaults. Replace placeholders, verify exact provider schemas, and adapt IAM/network/security policies to the environment.

## Beginner path

1. Read `references/getting-started.md`.
2. Select and pin Crossplane, provider, and function versions.
3. Configure IRSA and install only required provider packages.
4. Read `references/provider-schema-discovery.md` for the target AWS service.
5. Design an XRD/Claim and Composition using `references/aws-service-authoring.md`.
6. Run the scripts under `skills/crossplane-aws-engineer/scripts/`.
7. Apply through GitOps or a reviewed server-side dry run, then inspect asynchronous conditions/events.

## Validation

```bash
skills/crossplane-aws-engineer/scripts/check-manifests.sh
skills/crossplane-aws-engineer/scripts/render-test.sh <claim> <composition> <functions-manifest>
skills/crossplane-aws-engineer/scripts/validate-schemas.sh <claim> <composition> <provider-schema-bundle> <functions-manifest>
```

Rendering and schema validation do not create AWS infrastructure and do not prove IAM, quota, networking, or readiness. Never commit credentials, kubeconfigs, generated secrets, or unreviewed package versions.
