---
name: aws-iac-cloudformation-cdk
description: Authors, validates, compliance-checks, imports brownfield resources, reconciles drift, and troubleshoots AWS CloudFormation templates, AWS CDK applications, AWS SAM templates, and Terraform configurations using cfn-lint, cfn-guard, CDK-NAG, CloudFormation IaC Generator, and CloudTrail failure correlation.
metadata:
  version: "2.0"
---

# AWS Infrastructure as Code (CloudFormation, CDK, SAM & Brownfield Governance)

## Purpose

Ensure all platform infrastructure changes are declarative, version-controlled, syntactically valid, security-compliant, drift-free, and reproducible. This skill supersedes direct imperative resource creation via raw AWS CLI calls or Cloud Control API mutations.

---

## Operational Directives

### 1. Grounded Authoring via Official Schemas (`aws-iac` MCP)

Never guess CloudFormation resource property names or CDK construct props from memory:
1. **Documentation & Construct Lookup**: Before authoring CloudFormation resources or CDK constructs, invoke:
   - `search_cloudformation_documentation` and `read_iac_documentation_page` (`aws-iac` MCP) to verify exact CloudFormation resource types, required properties, return values (`Fn::GetAtt`, `Ref`), and update behaviors (*Replacement* vs *No interruption*).
   - `search_cdk_documentation`, `search_cdk_samples_and_constructs`, and `cdk_best_practices` (`aws-iac` MCP) to select hardened **AWS CDK L2/L3 constructs** and **AWS Solutions Constructs** over raw L1 `Cfn*` resources.
2. **Stateful vs. Stateless Stack Separation**:
   - Decouple stateful foundation resources (VPCs, KMS keys, RDS/Aurora clusters, DynamoDB tables, S3 buckets, ECR repositories) from stateless application compute (ECS services, EKS deployments, Lambda functions, API Gateway stages).
   - Always attach explicit retention and backup policies to stateful resources:
     - **CloudFormation / SAM**: `DeletionPolicy: Retain` (or `Snapshot` for RDS/EBS) and `UpdateReplacePolicy: Retain`.
     - **AWS CDK**: `removalPolicy: cdk.RemovalPolicy.RETAIN` and `deletionProtection: true`.
     - **Terraform / OpenTofu**: `lifecycle { prevent_destroy = true }`.
3. **Dynamic Secret References Only**:
   - Never pass plaintext passwords, API keys, or tokens into CloudFormation `Parameters` (without `NoEcho: true`), resource properties, or container `Environment` variables.
   - Use dynamic references (`{{resolve:secretsmanager:secret-id:SecretString:json-key}}`), container `Secrets` `valueFrom` ARNs, or RDS `ManageMasterUserPassword: true`.

---

### 2. Mandatory Pre-Deployment Validation Pipeline

Whenever a CloudFormation template (`*.template.yaml`, `*.template.yml`, `*.template.json`, `*.cfn.yaml`, `*.cfn.json`), SAM template (`template.yaml`), or CDK stack (`cdk synth --strict`) is authored or modified, execute **both** `aws-iac` validation tools before proposing deployment:

| Validation Gate | MCP Tool / CLI | What It Verifies | Required Outcome |
|---|---|---|---|
| **1. Syntax & Schema Linting** | `validate_cloudformation_template` (`aws-iac` MCP / `cfn-lint`) | Resource property schemas, intrinsic function types (`!Sub`, `!GetAtt`, `!FindInMap`), IAM action names, valid regional instance/service types | **Zero errors** (`E*` rules) |
| **2. Proactive Security & Control Tower Compliance** | `check_cloudformation_template_compliance` (`aws-iac` MCP / `cfn-guard`) | Encryption at rest (S3, EBS, RDS, DynamoDB, EFS, SQS, SNS), S3 Block Public Access, no `0.0.0.0/0` SSH/RDP ingress, no wildcard IAM admin grants, VPC isolation, log retention | **Zero compliance violations** |
| **3. CDK Construct Checks** (when using CDK) | `cdk-nag` (`AwsSolutionsChecks`) + `cdk diff` | Construct-level Well-Architected security and operational rules plus exact resource replacement diff | All `AwsSolutions-*` errors resolved or documented with granular suppressions |
| **4. Pre-Deploy Change Set Review** | `get_cloudformation_pre_deploy_validation_instructions` (`aws-iac` MCP) + `aws cloudformation create-change-set --include-nested-stacks` | Evaluates live target stack compatibility, `Replacement: True` blast radius, and early property validation hooks before execution | Human approval (`APPROVED`) of the Change Set / `cdk diff` |

If the repository uses **Terraform/OpenTofu (`*.tf`)** or **Kubernetes/Karpenter YAML**, run `terraform fmt -check`, `terraform validate`, and `kubectl apply --dry-run=client` before proposing changes.

---

### 3. Intelligent Deployment Failure & Rollback Troubleshooting

When a CloudFormation, CDK, or SAM stack enters `CREATE_FAILED`, `ROLLBACK_IN_PROGRESS`, `ROLLBACK_COMPLETE`, `UPDATE_ROLLBACK_IN_PROGRESS`, `UPDATE_ROLLBACK_COMPLETE`, or `IMPORT_ROLLBACK_COMPLETE`:

1. **Automated Pattern Diagnosis**: Immediately invoke `troubleshoot_cloudformation_deployment` on the `aws-iac` MCP server with:
   - `stack_name`: target stack name or ARN
   - `region`: target AWS region
   - `include_cloudtrail`: `true`
2. **CloudTrail Root-Cause Correlation**: Cross-reference the first failed logical resource ID (`ResourceStatus: CREATE_FAILED` or `UPDATE_FAILED`) and its exact failure timestamp against the `cloudtrail` MCP server (`lookup_events`) to uncover silent underlying errors masked by generic CloudFormation messages:
   - **Silent IAM / KMS Blocks**: `AccessDenied` on `kms:CreateGrant`, `kms:Decrypt`, `iam:PassRole`, or SCP/Permissions Boundary denials.
   - **Service Quotas & Capacity**: `InstanceLimitExceeded`, `VpcLimitExceeded`, `NatGatewayLimitExceeded`, or `InsufficientInstanceCapacity`.
   - **Network & Naming Conflicts**: Overlapping subnet CIDRs, S3 bucket global name collisions, or Security Group cyclic dependency deadlocks on teardown.
   - **Stabilization Timeouts**: ECS tasks failing ALB health checks (`EssentialContainerExited`, `CannotPullContainerError` due to missing NAT/ECR VPC endpoints), or ASG instances failing `cfn-signal`.
3. **Recovery Execution**: Present the exact root cause in plain language, apply the fix directly to the IaC template, re-run `validate_cloudformation_template` and `check_cloudformation_template_compliance`, and provide the exact recovery command (including `aws cloudformation delete-stack` or `continue-update-rollback` when a stack is wedged).

---

### 4. Brownfield Discovery, Drift Detection & Zero-Downtime IaC Import

Platform engineers routinely inherit untracked "ClickOps" resources or drifted stacks. Never delete and recreate stateful production resources to bring them under IaC management:

1. **Stack Drift Detection**:
   - Run `aws cloudformation detect-stack-drift --stack-name <stack>` and `aws cloudformation describe-stack-resource-drifts --stack-name <stack> --stack-resource-drift-status-filters MODIFIED DELETED` (via `aws-mcp`).
   - Compare `ExpectedProperties` vs `ActualProperties` and update the IaC template to reconcile benign console hotfixes or revert unauthorized drift via a controlled Change Set.
2. **Untracked Resource Adoption (CloudFormation IaC Generator & CDK Import)**:
   - Start a resource scan via `aws cloudformation start-resource-scan`, list scanned resources, and generate a template via `aws cloudformation create-generated-template` / `describe-generated-template`.
   - Ensure every resource being imported has an explicit `DeletionPolicy` (`Retain` or `Delete`) in the template.
   - Create an `IMPORT` Change Set (`--change-set-type IMPORT --resources-to-import ...`) or run `cdk import` / `terraform import` and verify that a subsequent `cdk diff` or Change Set shows **zero destructive replacements**.
