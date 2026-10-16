---
name: iac-architecture-advisor
description: Day-0 multi-engine AWS IaC architecture advisor and rapid-prototyping router. Evaluates team language expertise, multi-cloud portability, state/control-plane governance, and Day-0 feature needs to select and scaffold AWS CDK, CloudFormation, Terraform/OpenTofu, Pulumi, Crossplane, or AWS Blocks / Launch-with-AWS.
---

# AWS IaC Architecture Advisor & Rapid-Prototyping Router

Use this skill for **Day-0 architectural routing** when starting a new AWS infrastructure project, comparing IaC engines, or migrating a rapid prototype ("vibe-coded" application or AWS Blocks app) to production AWS infrastructure.

> **Never switch IaC engines on an existing repository without explicit user consent.** First inspect the workspace (`*.tf`, `cdk.json`, `*.cfn.yaml`/`*.template.json`, `Pulumi.yaml`, `crossplane.yaml`/`composition.yaml`, `samconfig.toml`) to detect the active toolchain.

## 1. Engine Selection Decision Matrix

Evaluate the user's constraints against these six axes before recommending or scaffolding an IaC engine:

| Evaluation Dimension | AWS CDK (TS / Python) | AWS CloudFormation | Terraform / OpenTofu (`aws` + `awscc`) | Pulumi (TS / Python / Go) | Crossplane (`provider-family-aws`) | AWS Blocks / Launch-with-AWS |
|---|---|---|---|---|---|---|
| **Primary Paradigm** | Imperative OOP Constructs synthesizing to CloudFormation | Declarative YAML/JSON templates managed by AWS | Declarative HCL with graph-based state files | Imperative general-purpose languages with state graph | Kubernetes-native declarative control plane (CRDs/XRs) | Infrastructure-from-Code (IfC) / rapid full-stack prototyping |
| **State Management** | Managed by AWS CloudFormation service (zero state bucket maintenance) | Managed by AWS CloudFormation service | S3 backend (`use_lockfile = true`) or HCP Terraform workspaces | Pulumi Cloud (encrypted state + ESC) or S3 backend | Kubernetes `etcd` + continuous active reconciliation loop | Managed via synthesized CDK / CloudFormation stacks |
| **Drift Healing** | On-demand drift detection (`DetectStackDrift`) | On-demand drift detection (`DetectStackDrift`) | Plan-time detection (`terraform plan -refresh-only`) | Preview/refresh detection (`pulumi refresh`) | **Continuous automatic drift healing** via K8s controllers | Synthesized stack drift detection |
| **Day-0 AWS API Coverage** | L1 (`Cfn*`) constructs via CloudFormation registry; L2/L3 curated | Immediate via CloudFormation registry | Immediate via `hashicorp/awscc` (Cloud Control API) + `hashicorp/aws` | Immediate via `pulumi-aws-native` + `pulumi-aws` | Upbound `provider-family-aws` (~900+ MR types) | Opinionated web/API app primitives |
| **Multi-Cloud / SaaS** | AWS-focused (requires Custom Resources for external SaaS) | AWS-only (unless third-party registry extensions deployed) | **Best-in-class** (Cloudflare, Datadog, GitHub, Okta, Snowflake alongside AWS) | **Best-in-class** (150+ providers in native TS/Python/Go) | High (any Kubernetes/Crossplane provider) | AWS-only rapid app deployment |
| **Best Fit For** | Application teams in TypeScript/Python wanting AWS-managed state and high-level L2/L3 patterns | Zero-dependency AWS governance, StackSets across AWS Organizations, strict declarative change sets | Dedicated platform/infra teams standardizing on HCL across AWS and third-party SaaS providers | Software engineering teams wanting real unit tests, strong typing, and multi-provider orchestration without CloudFormation wait times | Kubernetes/EKS platform engineering teams building self-service Internal Developer Platforms (IDPs) via ArgoCD/Flux | Day-0 prototypes, hackathons, and migrating vibe-coded web apps to AWS |

## 2. Decision Workflow

1. **Workspace Inspection**:
   - Check for existing manifests (`cdk.json`, `*.tf`, `Pulumi.yaml`, `crossplane.yaml`, `*.cfn.yaml`). If present, immediately route to the matching engine skill (`aws-cdk`, `aws-terraform`, `aws-pulumi`, `aws-crossplane`, or `aws-cloudformation`).
   - If `samconfig.toml` or `AWS::Serverless-2016-10-31` is detected and the user needs deep Lambda/SAM tuning, hand off to `aws-serverless-engineer`.
2. **Gather Requirements (When Starting Fresh)**:
   - **Team Background**: HCL-first Ops (`aws-terraform`), TypeScript/Python App Devs (`aws-cdk` or `aws-pulumi`), or Kubernetes Platform Team (`aws-crossplane`)?
   - **State & Governance**: Want AWS to host state with zero backend setup (`aws-cdk` / `aws-cloudformation`), S3/HCP state (`aws-terraform`), Pulumi Cloud + ESC (`aws-pulumi`), or continuous Kubernetes reconciliation (`aws-crossplane`)?
   - **Scope**: Multi-account AWS Organizations baseline (`aws-cloudformation` StackSets or `aws-terraform` Stacks), multi-provider AWS + Cloudflare/Datadog (`aws-terraform` or `aws-pulumi`), or rapid prototype deployment (`references/aws-blocks.md` / `references/launch-with-aws.md`)?
3. **Architecture & Blast-Radius Isolation**:
   - Split stateful resources (VPC, RDS/Aurora, DynamoDB, KMS, S3 data lakes) from stateless application compute (ECS, EKS workloads, Lambda, API Gateway) into separate stacks/workspaces/claims.
   - Enforce mandatory resource tagging (`Environment`, `Owner`, `ManagedBy`, `CostCenter`, `Repository`) at the provider/app root (`default_tags` in Terraform, `Tags.of(app)` in CDK, stack tags in Pulumi/CloudFormation, `function-patch-and-transform` in Crossplane).
4. **Handoff to Specialized Engine Skill**:
   - Load the selected engine skill (`aws-terraform`, `aws-pulumi`, `aws-crossplane`, `aws-cdk`, or `aws-cloudformation`) plus `aws-iam-and-security`, `aws-networking-and-compute`, and `aws-finops-and-cost`.

## 3. Rapid Prototyping & App Migration References

- **[`references/aws-blocks.md`](references/aws-blocks.md)**: Building full-stack applications with AWS Blocks (Infrastructure-from-Code framework).
- **[`references/launch-with-aws.md`](references/launch-with-aws.md)** and **`scripts/`**: Migrating rapid/vibe-coded web applications to AWS using the Launch-with-AWS workflow.
