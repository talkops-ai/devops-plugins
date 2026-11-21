---
name: sagemaker-domain-vpc-iac
description: >-
  Architects and generates production-grade AWS CDK (TypeScript/Python) and CloudFormation
  Infrastructure-as-Code for Amazon SageMaker AI Studio Domains, User Profiles, Private/Shared
  Spaces (JupyterLab & CodeEditor), Custom Studio Images (BYOI with SOCI index), VpcOnly private
  networking with PrivateLink endpoints, KMS customer-managed encryption keys, Cognito presigned
  URL authentication, and 5-persona least-privilege IAM execution roles. Always validates generated
  templates using the awsiac MCP server (cfn-lint and cfn-guard). Use when the user asks to
  provision a SageMaker Studio Domain, configure VpcOnly networking, set up IAM roles or KMS for
  SageMaker, create custom Studio Docker images, configure CfnSpace EbsStorageSettings or
  CustomFileSystems EFS mounts, or write CDK/CloudFormation for SageMaker.
  Always query live AWS state via connected MCP tools (never raw aws CLI).
metadata:
  version: "1.0.0"
---

# SageMaker Domain, VPC & Security IaC Architect

Generates compliant, production-hardened AWS CDK (TypeScript or Python) and CloudFormation templates for Amazon SageMaker AI platform infrastructure and validates every template with the `awsiac` MCP server.

## MCP-Only Execution & Read-Only Safety

- **MCP-Only Live Queries:** Execute **all** live AWS discovery, Bedrock/SageMaker control-plane checks, pricing lookups, IaC compliance checks, CloudWatch telemetry queries, and documentation searches **exclusively via connected MCP tools**: `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`, `aws___search_documentation`, `aws___read_documentation`), `sagemaker` (`describe_hp_cluster`), `agentcore`, `strands-agents`, `cloudwatch`, `awspricing` (`get_pricing`, `get_bedrock_patterns`), `awsiac` (`validate_cloudformation_template`, `check_cloudformation_template_compliance`), and `awsknowledge`. Offline pure-Python bundled helper scripts in `scripts/*.py` that perform local math/schema rendering without live AWS credentials are permitted when inspecting local inputs, whereas live AWS API queries must go through MCP rather than raw `aws` CLI or boto3 shell scripts.
- **Strict Read-Only & Secret Safety:** **Never** run raw `aws ...` (not even `aws sts get-caller-identity` — always call `sts.GetCallerIdentity` inside `aws___run_script`), `cdk deploy`, or `cdk destroy` CLI commands in Bash/`run_command`, **never** mutate live AWS resources (`Create*`, `Update*`, `Delete*`, `InvokeModel`, `CreateEndpoint` — refuse unapproved mutations and present a safe, approval-gated IaC rollout and rollback plan), and **never** read or expose plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter` with `WithDecryption=True`, or `.env` API keys). When running a live regional Studio Domain preflight audit, always inspect and summarize SageMaker Domains, VPCs/subnets/PrivateLink endpoints, **KMS CMKs (`kms:ListKeys` / `ListAliases`)**, and `AuthMode` (`SSO` vs `IAM`) readiness via MCP.
- **Unmapped Edge Cases:** Query `awsknowledge` / `aws-mcp` documentation search tools (`aws___search_documentation`, `aws___read_documentation`) with 1–2 focused queries before recommending unverified CloudFormation resource properties.

## Critical Architectural Rules (Read Before Writing Any Code)

1. **CDK L1 Construct Rule (`Cfn*` Only)**:
   - `aws-cdk-lib/aws-sagemaker` does **NOT** provide L2 constructs for Studio Domains, User Profiles, or Spaces.
   - **NEVER** write `new sagemaker.Domain(...)` or `new sagemaker.UserProfile(...)` — those classes do not exist and will fail compilation.
   - **ALWAYS** use L1 constructs: `sagemaker.CfnDomain`, `sagemaker.CfnUserProfile`, `sagemaker.CfnSpace`, `sagemaker.CfnImage`, `sagemaker.CfnImageVersion`, `sagemaker.CfnAppImageConfig`, `sagemaker.CfnFeatureGroup`, `sagemaker.CfnModelPackageGroup`.
2. **`AuthMode: 'SSO'` vs `'IAM'` Mutual Exclusivity**:
   - When `authMode: 'SSO'`: AWS IAM Identity Center MUST already be enabled in the target region, and `CfnUserProfile` requires `singleSignOnUserIdentifier: 'UserName'` and `singleSignOnUserValue: '<sso-user>'`.
   - When `authMode: 'IAM'`: You **MUST OMIT** `singleSignOnUserIdentifier` and `singleSignOnUserValue` on `CfnUserProfile` (including them causes CloudFormation failure). For external identity providers (e.g., Amazon Cognito User Pools), pair `authMode: 'IAM'` with an API Gateway + Lambda authorizer that calls `sagemaker:CreatePresignedDomainUrl`.
3. **`VpcOnly` Mode & Mandatory VPC Endpoints**:
   - Production domains MUST set `appNetworkAccessType: 'VpcOnly'` and deploy into private subnets (`PRIVATE_WITH_EGRESS` or `PRIVATE_ISOLATED`).
   - Provision the required VPC endpoints so Studio apps, training jobs, and pipelines operate without public internet traversal:
     - **S3 Gateway Endpoint**: `com.amazonaws.<region>.s3`
     - **Interface Endpoints (PrivateLink)**:
       1. `com.amazonaws.<region>.sagemaker.api`
       2. `com.amazonaws.<region>.sagemaker.runtime`
       3. `com.amazonaws.<region>.sagemaker.studio`
       4. `com.amazonaws.<region>.ecr.api`
       5. `com.amazonaws.<region>.ecr.dkr`
       6. `com.amazonaws.<region>.sts`
       7. `com.amazonaws.<region>.logs`
       8. Optional (when hybrid Bedrock / KMS / SSM): `com.amazonaws.<region>.bedrock-runtime`, `com.amazonaws.<region>.kms`, `com.amazonaws.<region>.ssm`
4. **Security Group Ingress Rules (EFS NFS 2049 + Inter-App Ephemeral Ports)**:
   - The Studio Domain Security Group MUST allow **self-referencing ingress**:
     - **TCP Port 2049 (NFS)** from itself (required for mounting the domain's Amazon EFS home volume `HomeEfsFileSystemUid` into Studio Spaces).
     - **TCP Ports 8192–65535** from itself (required for Jupyter kernel gateway, Spark processing, and inter-container traffic).
   - The VPC Endpoint Security Group MUST allow **TCP Port 443 (HTTPS)** from the Studio Domain Security Group.
5. **Studio Space (`CfnSpace`) App Type & Ownership Constraints**:
   - **`CodeEditor`** (VS Code-OSS) Spaces **ONLY** support `spaceSharingSettings: { sharingType: 'Private' }` and require `ownershipSettings: { ownerUserProfileName: ... }`.
   - **`JupyterLab`** Spaces support both `'Private'` and `'Shared'` sharing types (when `'Shared'`, omit `ownershipSettings`).
   - Always configure `appLifecycleManagement.idleSettings` (`lifecycleManagement: 'ENABLED'`, `idleTimeoutInMinutes: 60`) in `defaultUserSettings` and `defaultSpaceSettings` to prevent idle Studio compute bills.
6. **Mandatory `awsiac` MCP Server Validation**:
   - After generating or modifying any CloudFormation YAML/JSON or synthesizing a CDK stack (`cdk synth`), you **MUST** run:
     - `validate_cloudformation_template` (`cfn-lint`)
     - `check_cloudformation_template_compliance` (`cfn-guard`)
   - Fix all syntax, schema, or security compliance violations before presenting the final IaC to the user.

---

## Workflow

### Step 1: Gather Platform Requirements

Determine from `ARCHITECTURE.md` or user conversation:

1. **IaC Tooling**: AWS CDK (TypeScript or Python) or raw CloudFormation YAML?
2. **Authentication Mode**: `SSO` (IAM Identity Center) or `IAM` (with optional Cognito + Lambda `CreatePresignedDomainUrl` portal)?
3. **Network Topology**: Existing VPC ID/subnets or provision a new Multi-AZ VPC with `VpcOnly` + PrivateLink endpoints?
4. **Studio Spaces & Custom Images**: Do users need private `CodeEditor` spaces, shared `JupyterLab` spaces, idle auto-shutdown lifecycle configs, or custom Docker images (`CfnImage` + `CfnAppImageConfig` with SOCI fast-launch)?
5. **IAM Persona Roles**: Which of the 5 least-privilege roles are needed (`StudioDomainExecutionRole`, `DataScientistProfileRole`, `TrainingJobRole`, `PipelineExecutionRole`, `EndpointInferenceRole`)?

### Step 2: Generate Production IaC

Read `references/cdk-l1-domain-patterns.md` and generate the requested CDK or CloudFormation stacks:

- **Networking & KMS Stack**: Multi-AZ VPC, S3 Gateway Endpoint, 7+ PrivateLink Interface Endpoints, Studio Domain SG (self-referencing NFS 2049 + 8192–65535), VPC Endpoint SG (443), and customer-managed KMS Key (`enableKeyRotation: true`) with grants for `sagemaker.amazonaws.com`, `efs.amazonaws.com`, and `logs.<region>.amazonaws.com`.
- **5-Persona Least-Privilege IAM Stack**: Scoped execution roles with condition keys (`sagemaker:VpcSubnets`, `sagemaker:VpcSecurityGroupIds`, `sagemaker:VolumeKmsKey`, `sagemaker:NetworkIsolation`) and restricted `iam:PassRole`.
- **Studio Domain, UserProfiles & Spaces Stack**: `CfnDomain` (`appNetworkAccessType: 'VpcOnly'`, `kmsKeyId`, `defaultUserSettings`, `defaultSpaceSettings` with `IdleSettings`), `CfnUserProfile`, and `CfnSpace` (`JupyterLab` / `CodeEditor` with EBS `volumeSizeInGb`, `volumeKmsKeyId`, `instanceType`).
- **Optional BYOI Custom Image & Cognito Portal**: Custom Dockerfile (`USER 1000`), `CfnImage`, `CfnImageVersion`, `CfnAppImageConfig`, SOCI index generation commands, or Cognito presigned URL Lambda.

### Step 3: Validate with `awsiac` MCP Server

1. If using CDK, synthesize the CloudFormation template (`npx cdk synth` or `cdk synth`) or validate the generated CloudFormation template directly.
2. Invoke the `awsiac` MCP server tools:
   - `validate_cloudformation_template`
   - `check_cloudformation_template_compliance`
   - If CDK errors occur, use `troubleshoot_cloudformation_deployment` or `search_cdk_samples_and_constructs`.
3. Remediate any findings and present the validated IaC files + deployment instructions.

## References

- `references/cdk-l1-domain-patterns.md` — Complete TypeScript CDK L1 patterns for `CfnDomain`, `CfnUserProfile`, `CfnSpace` (`CodeEditor` vs `JupyterLab`), `VpcOnly` PrivateLink endpoints, NFS 2049 Security Groups, 5-Persona IAM policies, Cognito `CreatePresignedDomainUrl` Lambda, and BYOI Docker + SOCI index setup.
