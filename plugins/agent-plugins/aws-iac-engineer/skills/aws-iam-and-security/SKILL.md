---
name: aws-iam-and-security
description: Authors least-privilege AWS IAM policies, Permission Boundaries, KMS CMK key policies, Secrets Manager dynamic references, and CI/CD OIDC trust relationships across CDK, CloudFormation, Terraform, Pulumi, and Crossplane; validates with IAM Access Analyzer and shift-left IaC security scanners.
---

# AWS IAM, Encryption & Shift-Left IaC Security

Use this skill whenever authoring or reviewing IAM roles, policies, trust relationships, KMS Customer Managed Keys (CMKs), Secrets Manager/SSM integrations, or security-group/WAF perimeters inside any IaC engine.

## 1. Non-Negotiable Least-Privilege IAM Rules in IaC

1. **No Wildcard Actions + Resources**:
   - Never emit `"Action": "*"` paired with `"Resource": "*"`.
   - Scope actions to the exact service operation prefix (`s3:GetObject`, `dynamodb:PutItem`, `kms:Decrypt`) and scope `Resource` to explicit construct/resource ARN references (`bucket.bucketArn`, `aws_s3_bucket.main.arn`, `!GetAtt MainBucket.Arn`).
   - When an AWS API genuinely requires `"Resource": "*"` (e.g., `ec2:Describe*`, `kms:CreateGrant` with conditions, `xray:PutTraceSegments`), isolate that statement from resource-specific CRUD statements and constrain it with `Condition` keys (`aws:RequestedRegion`, `aws:ResourceTag/*`, `kms:ViaService`).
2. **Workload Identity Over Static IAM Users**:
   - Never provision `AWS::IAM::AccessKey` or `aws_iam_access_key` in IaC unless explicitly requested and approved.
   - Use **EKS Pod Identity** (`AWS::EKS::PodIdentityAssociation` / `aws_eks_pod_identity_association`) or **IRSA** for Kubernetes workloads, **ECS Task Roles** for containers, **EC2 Instance Profiles** with IMDSv2 required (`http_tokens = "required"`), and **IAM Roles for OIDC** (`token.actions.githubusercontent.com`, GitLab CI, Pulumi ESC, HCP Terraform) for CI/CD pipelines.
3. **Confused-Deputy Prevention on Trust Policies**:
   - Every service-principal or cross-account `AssumeRolePolicyDocument` must include `aws:SourceArn` and/or `aws:SourceAccount` conditions (or `sts:ExternalId` for third-party SaaS roles).
4. **Permission Boundaries for Delegated Role Creation**:
   - When an application or CI/CD pipeline role is allowed to create IAM roles (`iam:CreateRole`, `iam:PutRolePolicy`), enforce a `PermissionsBoundary` condition so it cannot escalate privileges beyond the boundary.

## 2. Zero-Plaintext Secrets & Encryption-by-Default

1. **Never Hardcode or Read Secret Values**:
   - Never place passwords, API keys, or private keys in `.tf`, `.ts`, `.py`, `.yaml`, or `terraform.tfvars` files.
   - For RDS/Aurora master credentials, always enable AWS-managed secret rotation (`manage_master_user_password = true` in Terraform, `Credentials.fromGeneratedSecret()` in CDK, `ManageMasterUserPassword: true` in CloudFormation).
   - Reference secrets dynamically at deploy/runtime (`{{resolve:secretsmanager:SecretId:SecretString:JsonKey}}` in CloudFormation, ` ecs.Secret.fromSecretsManager(...)` in CDK, `ephemeral "aws_secretsmanager_random_password"` or write-only `password_wo` attributes in Terraform 1.10+).
2. **Mandatory Encryption at Rest & In Transit**:
   - Enable KMS or SSE encryption on every S3 bucket (`BucketKeyEnabled: true`), EBS volume, RDS instance/cluster (`StorageEncrypted: true`), DynamoDB table (`SSEEnabled: true`), SQS queue, SNS topic, and CloudWatch Log Group.
   - Attach an S3 bucket policy denying non-TLS requests (`aws:SecureTransport: "false"`).

## 3. Shift-Left Validation Matrix Across IaC Engines

Before presenting any infrastructure change set for approval, run the engine-appropriate security validator:

| IaC Engine | Primary Security Validator | IAM Policy Validation |
|---|---|---|
| **CloudFormation** | `awsiac` `check_cloudformation_template_compliance` (`cfn-guard` CIS/Well-Architected rules) | `aws accessanalyzer validate-policy` via `aws-mcp` |
| **AWS CDK** | `cdk-nag` (`AwsSolutionsChecks({ verbose: true })`) + `awsiac` on `cdk.out/*.template.json` | `aws accessanalyzer validate-policy` via `aws-mcp` |
| **Terraform / OpenTofu** | `checkov -d . --framework terraform` / `trivy config .` / `tflint` | `aws accessanalyzer validate-policy` on rendered `data.aws_iam_policy_document` JSON |
| **Pulumi** | CrossGuard Policy Pack (`@pulumi/policy`) during `pulumi preview` | `aws accessanalyzer validate-policy` via `aws-mcp` |
| **Crossplane** | `crossplane render` + `checkov --framework kubernetes` / Kyverno CEL validations | `aws accessanalyzer validate-policy` on `Role` / `Policy` MR `forProvider.policy` |

## 4. Bundled Reference Guides

- **[`references/policies.md`](references/policies.md)**: Least-privilege IAM policy structure, condition keys, and resource scoping patterns.
- **[`references/roles-and-trust-policies.md`](references/roles-and-trust-policies.md)**: Service roles, cross-account trust policies, OIDC federation, and confused-deputy guards.
- **[`references/permission-boundaries.md`](references/permission-boundaries.md)**: Designing and enforcing IAM Permission Boundaries for developer self-service.
- **[`references/access-analyzer.md`](references/access-analyzer.md)**: Validating policies (`validate-policy`), checking no-new-access (`check-no-new-access`), and custom policy checks.
- **[`references/organization-policies.md`](references/organization-policies.md)**: Service Control Policies (SCPs), Resource Control Policies (RCPs), and AWS Data Perimeter guardrails.
- **[`references/troubleshooting.md`](references/troubleshooting.md)**: Diagnosing `AccessDenied`, implicit vs. explicit deny evaluation order, and KMS grant/key-policy failures.
