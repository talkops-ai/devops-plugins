---
name: aws-crossplane
description: Designs, authors, renders, and validates production-grade Crossplane v1.20 / v2 control-plane configurations targeting AWS with the Upbound provider-family-aws ecosystem, IRSA/Pod Identity DeploymentRuntimeConfig, XRDs, Pipeline-mode Compositions, and offline crossplane render/validate loops.
---

# AWS Crossplane Control-Plane Engineering

Use this skill whenever authoring, validating, importing, or debugging **Crossplane** control-plane manifests (`Provider`, `DeploymentRuntimeConfig`, `ProviderConfig`, `CompositeResourceDefinition` / XRD, `Composition`, `Claim`) targeting AWS via the **Upbound `provider-family-aws`** ecosystem.

## 1. Golden Rules for Crossplane on AWS

1. **Always use monolithic `spec.mode: Pipeline` Compositions** with `function-patch-and-transform` and `function-auto-ready`. The legacy top-level `spec.resources` patch-and-transform array is deprecated and removed in Crossplane v2.0.
2. **Use granular Upbound family providers** (`xpkg.upbound.io/upbound/provider-aws-s3:v1`, `provider-aws-rds:v1`, `provider-aws-ec2:v1`, `provider-aws-eks:v1`, `provider-aws-iam:v1`), never the deprecated monolithic `provider-aws`. Installing any family provider automatically pulls `upbound/provider-family-aws`.
3. **Always authenticate with IRSA or EKS Pod Identity (`source: InjectedIdentity`)** via a `DeploymentRuntimeConfig`. Never embed static AWS access keys in Kubernetes `Secret` objects for production control planes.
4. **Verify Managed Resource (MR) API group, version, kind, and `forProvider` fields** before authoring (`kubectl explain <kind>.spec.forProvider` or `crossplane beta validate`). Note that `Bucket.s3.aws.upbound.io/v1beta1` does **not** have a `spec.forProvider.bucket` field — the external bucket name comes from `metadata.name` or the `crossplane.io/external-name` annotation.
5. **Protect stateful resources** (`RDSInstance`, `Cluster`, `Bucket`, `Table`) with `deletionPolicy: Orphan` in production Compositions.
6. **Filter connection secrets**: Never pass raw `RDSInstance` connection secrets (`attribute.password`) directly to developer namespaces without explicit `writeConnectionSecretToRef` scoping and key filtering.

## 2. Standard Authoring & Validation Workflow

### Step 1: Provider & IRSA / Pod Identity Wiring
Configure the family provider with a `DeploymentRuntimeConfig` (annotating the provider `ServiceAccount` with `eks.amazonaws.com/role-arn` for IRSA) and a `ProviderConfig` using `credentials.source: InjectedIdentity`. See [`references/providers-and-auth.md`](references/providers-and-auth.md).

### Step 2: Define the Platform API (`CompositeResourceDefinition` — XRD)
Author the XRD with a strict OpenAPIv3 schema (`x-kubernetes-validations` CEL rules for valid CIDR blocks, engine versions, and storage bounds), `connectionSecretKeys`, and `defaultCompositionRef`. See [`references/xrd-and-compositions.md`](references/xrd-and-compositions.md).

### Step 3: Author Pipeline-Mode `Composition`
Structure every `Composition` with `spec.mode: Pipeline`:
- Step 1: `function-patch-and-transform` (or `function-go-templating` / `function-kcl`) rendering each Managed Resource (`base` + `patches` + `connectionDetails`).
- Step 2: `function-auto-ready` to automatically compute readiness across all composed Managed Resources.
- Propagate standard AWS tags (`Environment`, `ManagedBy: Crossplane`, `ClaimNamespace`) across every Managed Resource via a `PatchSet`.

### Step 4: Offline Render & Schema Validation (Mandatory Before Apply)
Always validate offline using the Crossplane CLI before applying to a live Kubernetes cluster (see [`references/validation-and-troubleshooting.md`](references/validation-and-troubleshooting.md) and `scripts/render-and-validate.sh`):
```bash
# 1. Render the XR + Composition + Functions locally into composed Managed Resources
crossplane render xr.yaml composition.yaml functions.yaml --include-full-xr > rendered.yaml

# 2. Validate the rendered Managed Resources against the Upbound AWS provider CRD schemas
crossplane beta validate providers.yaml rendered.yaml
```

## 3. Brownfield Observe & Adopt (`managementPolicies`)

To inspect or adopt existing AWS resources without risking modification or deletion:
1. Set `spec.managementPolicies: ["Observe"]` and `metadata.annotations["crossplane.io/external-name"]: "<live-aws-id>"` on the Managed Resource.
2. Verify `READY=True` and `SYNCED=True` and inspect `.status.atProvider`.
3. Transition to `["Observe", "Create", "Update", "LateInitialize"]` (omitting `"Delete"` or pairing with `deletionPolicy: Orphan`) once spec matches live state.

## 4. Bundled References, Templates & Validation Scripts

- **[`references/providers-and-auth.md`](references/providers-and-auth.md)**: Upbound `provider-family-aws`, IRSA, EKS Pod Identity, and multi-account `AssumeRole` chains.
- **[`references/xrd-and-compositions.md`](references/xrd-and-compositions.md)**: XRD OpenAPIv3 schemas, Pipeline-mode `Composition` patterns, `PatchSet` reuse, and cross-resource references (`Selector` / `Ref`).
- **[`references/aws-service-blueprints.md`](references/aws-service-blueprints.md)**: Production blueprints for S3, RDS PostgreSQL, Multi-AZ VPC, and EKS with Crossplane.
- **[`references/validation-and-troubleshooting.md`](references/validation-and-troubleshooting.md)**: Offline `crossplane render` + `crossplane beta validate`, ArgoCD sync-wave ordering, and diagnosing `SYNCED=False` / `READY=False` events.
- **`assets/`**: Ready-to-customize templates for `provider-setup.yaml`, `xrd-template.yaml`, `composition-pipeline.yaml`, `functions.yaml`, and `claim-example.yaml`.
- **`scripts/render-and-validate.sh`** & **`scripts/diagnose-claim.sh`**: Automated local rendering/validation and live cluster Claim/XR/MR hierarchy diagnostics.
