---
name: aws-deployment
description: "Configures CI/CD and GitOps pipelines for AWS infrastructure and workloads using AWS CodePipeline V2, CodeBuild, CodeDeploy, CodeConnections, and CodeArtifact, as well as GitHub Actions and GitLab CI with AWS OIDC federation, Atlantis PR automation for Terraform, Pulumi Neo/GitHub Actions workflows, and ArgoCD/Flux sync waves for Crossplane."
metadata:
  version: "2"
---

# AWS CI/CD & Multi-Engine GitOps Delivery

**Works best with** the `aws-mcp`, `awsiac`, `terraform`, and `pulumi` MCP servers for validating pipeline definitions and inspecting deployment state.

## Critical Warnings

**CodeConnections PENDING trap**: Connections created via CLI/CloudFormation remain `PENDING` indefinitely — MUST complete OAuth in the AWS Console. No API-only path exists.

**Cross-account triple requirement**: Cross-account deploys need ALL THREE: (1) KMS key policy granting target account (use key ID, not alias), (2) S3 bucket policy for target account, (3) cross-account IAM role with trust policy. Missing any one = cryptic `Access Denied`.

**CodeDeploy ApplicationStop uses PREVIOUS revision**: Broken stop scripts in a prior deployment block ALL future deploys. Make stop scripts idempotent (exit 0 if service absent). Unblock with `--ignore-application-stop-failures`.

**CodeBuild VPC without NAT**: Builds in VPC subnets without NAT gateway hang at `DOWNLOAD_SOURCE` silently. Private subnets MUST have NAT gateway or VPC endpoints.

**CodeConnections IAM**: Use `codeconnections:` prefix for API calls and IAM policy Actions. Resource ARNs must match exactly — new resources use `codeconnections` prefix, existing resources may use `codestar-connections` prefix. Specify both in Resource if you have mixed-age resources.

**UseConnection is over-permissive**: `codeconnections:UseConnection` grants access to ALL repositories the connection can reach. MUST specify condition keys (`codeconnections:FullRepositoryId`, `codeconnections:ProviderAction`, `codeconnections:BranchName`) to limit CodeBuild to only the required repository.

## 1. AWS-Native CI/CD (CodePipeline V2, CodeBuild, CodeDeploy)

CodeConnections → CodeBuild → CodeDeploy, orchestrated by CodePipeline.

| Layer | Service | Role |
|-------|---------|------|
| Source | CodeConnections | Authenticates to GitHub/GitLab/Bitbucket, delivers code |
| Packages | CodeArtifact | Private package registry, dependency caching from public registries |
| Build/Test | CodeBuild | Compiles, tests, runs `cdk synth` / `terraform plan` / `cfn-lint` |
| Deploy | CodeDeploy / CloudFormation | Deploys to EC2/ECS/Lambda/CloudFormation with traffic shifting & approval gates |
| Orchestrator | CodePipeline | Chains stages, manages transitions, manual approval gates |

Default: V2 pipeline type with `QUEUED` execution mode. Use `PARALLEL` only when executions are fully independent.

### Quick Navigation (AWS-Native References)

| You want to... | Go to |
|----------------|-------|
| Create a pipeline (V2, triggers, variables, modes) | [codepipeline.md](references/codepipeline.md) |
| Connect GitHub/GitLab/Bitbucket source | [codeconnections.md](references/codeconnections.md) |
| Write `buildspec.yml` / configure builds | [codebuild.md](references/codebuild.md) |
| Set up private package registry for builds | [codeartifact.md](references/codeartifact.md) |
| Configure deployment strategy (blue/green, canary) | [codedeploy.md](references/codedeploy.md) |
| Cross-account or cross-region deployment | [codepipeline.md](references/codepipeline.md) |
| Fix failing pipeline, build, or deployment | [troubleshooting.md](references/troubleshooting.md) |

## 2. External CI/CD & GitOps for Multi-Engine IaC

### A. GitHub Actions & GitLab CI with AWS IAM OIDC Federation
Never store static `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in GitHub or GitLab secrets. Provision an `AWS::IAM::OIDCProvider` (`https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`) and scope the IAM Role trust policy with `StringEquals` on `:aud` and `StringLike` on `:sub` (`repo:org/repo:ref:refs/heads/main` or `repo:org/repo:environment:production`):

```yaml
# .github/workflows/iac-deploy.yml
permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  plan-and-validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsIaCPlanRole
          aws-region: us-east-1
      # Run engine validation:
      # - Terraform: terraform fmt -check && terraform validate && tflint && checkov -d . && terraform plan -out=tfplan
      # - CDK: npm test && npx cdk synth --strict && npx cdk diff
      # - Pulumi: pulumi preview --diff
```

### B. Terraform PR Automation: HCP Terraform & Atlantis
- **Atlantis (`atlantis.yaml`)**: Configure `automerge: false`, `apply_requirements: [approved, mergeable, undiverged]`, and a custom workflow running `terraform fmt -check`, `tflint`, `checkov`, and `infracost diff` during `plan` before allowing `atlantis apply`.
- **HCP Terraform (`terraform` MCP)**: Use `list_workspaces`, `create_run` (`is_destroy: false`, plan-only by default), and inspect run status before user-approved `action_run` (`apply`).

### C. Pulumi CI/CD & Pulumi Neo
- Use `pulumi/actions@v6` with Pulumi ESC OIDC credentials (`env: org/aws-prod-oidc`) to run `pulumi preview --diff` on pull requests and `pulumi up` on merge to `main`.
- Use the `pulumi` MCP (`neo-bridge`) when delegating cloud-hosted PR generation or automated drift remediation to Pulumi Neo.

### D. Crossplane GitOps with ArgoCD & Flux
When syncing Crossplane manifests via ArgoCD or Flux, prevent `no matches for kind` CRD race conditions using sync waves and dry-run ignore annotations:
1. **Wave `-2`** (`argocd.argoproj.io/sync-wave: "-2"`): `Provider`, `Function`, and `DeploymentRuntimeConfig`.
2. **Wave `-1`**: `ProviderConfig` and `CompositeResourceDefinition` (XRD).
3. **Wave `0`**: `Composition` (`spec.mode: Pipeline`).
4. **Wave `1`** (with `argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true`): Namespaced `Claim` or cluster-scoped `XR` instances.
Always add `ServerSideApply=true` on large Upbound provider CRDs to avoid the 262 KB `kubectl.kubernetes.io/last-applied-configuration` annotation limit.

## Troubleshooting

| Error/Symptom | Cause | Fix |
|---------------|-------|-----|
| `YAML_FILE_ERROR` in CodeBuild | Missing or malformed `runtime-versions` in buildspec | Add `runtime-versions` block in install phase |
| `file already exists` on CodeDeploy | Redeployment without overwrite config | Set `file_exists_behavior: OVERWRITE` |
| Pipeline trigger not firing | File path filter checks only first 100 files in diff | Reduce path filter scope or merge smaller |
| PARALLEL mode wrong revision | Race between event and source action | Use QUEUED mode for sequential consistency |
| Docker: `Cannot connect to daemon` | Missing privileged mode | Set `privilegedMode: true` AND start dockerd in buildspec |
| `CODEBUILD_CLONE_REF` permission error | CodeBuild role missing UseConnection | Add `codeconnections:UseConnection` to CodeBuild service role |
| OIDC `NotAuthorizedToPerformAssumeRoleWithWebIdentity` | Subject claim (`sub`) or audience (`aud`) mismatch in IAM trust policy | Verify exact `repo:<org>/<repo>:environment:<env>` or branch pattern in `StringLike` condition |
| ArgoCD `ComparisonError: no matches for kind` on Crossplane Claim | XRD hasn't finished establishing CRD before dry-run | Add `argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true` and order via sync waves |

## Security

- MUST use OIDC federation (`aws-actions/configure-aws-credentials`, GitLab `id_tokens`, Pulumi ESC, HCP Terraform Workload Identity) — never store long-lived IAM user keys in CI secrets.
- Separate **Plan/Diff IAM Roles** (read-only + state lock) from **Apply/Deploy IAM Roles** (restricted to protected `main` branch or approved production environment).
- MUST store runtime secrets in Secrets Manager or Parameter Store; reference via CodeBuild `type: SECRETS_MANAGER` — MUST NOT embed in `buildspec.yml` as `PLAINTEXT`.
- MUST use customer-managed KMS keys for cross-account artifact encryption.
