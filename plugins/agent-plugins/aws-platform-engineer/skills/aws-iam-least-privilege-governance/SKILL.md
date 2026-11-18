---
name: aws-iam-least-privilege-governance
description: Designs, audits, and simulates least-privilege AWS IAM roles, inline/managed policies, trust policies, permissions boundaries, EKS Pod Identity / IRSA bindings, ECS task roles, and EC2 instance profiles using the iam and cloudtrail MCP servers.
metadata:
  version: "2.0"
---

# AWS IAM Least-Privilege Governance & Policy Simulation

## Purpose

Prevent privilege-escalation vulnerabilities, wildcard over-permissioning, and static credential leaks across AWS platform workloads. Application developers and QA engineers frequently attempt to resolve `AccessDeniedException` errors by attaching `AdministratorAccess`, `PowerUserAccess`, or `"Action": "*", "Resource": "*"`. This skill replaces guesswork with CloudTrail forensic lookup, scoped policy synthesis, confused-deputy trust guards, permissions boundaries, and non-destructive IAM policy simulation via the `iam` MCP server.

## MCP-Only Execution & Edge-Case Fallback Rules (Mandatory)

1. **MCP-Only Execution (Zero Raw Shell CLI):** Execute **all** IAM inspections, policy simulations, Access Analyzer validations, and CloudTrail `AccessDenied` forensics **exclusively via connected MCP servers**: `iam` (`list_roles`, `list_role_policies`, `get_role_policy`, `list_users`, `list_policies`, `get_managed_policy_document`, `simulate_principal_policy`), `cloudtrail` (`lookup_events`), and `aws-mcp` (`aws___run_script` using read-only `call_boto3` for `iam` `GetRole` / `SimulateCustomPolicy` / `GetServiceLastAccessedDetails` and `accessanalyzer` `ValidatePolicy` / `ListFindings` / `ListAnalyzers`). **Never** run raw `aws iam ...`, `aws sts ...`, or `python3 -c` commands in Bash/`run_command`, **never** create IAM users or access keys (`create-access-key`), **never** attach `AdministratorAccess`, and **never** call `secretsmanager:GetSecretValue` (always recommend `secretsmanager:DescribeSecret` for metadata audits and `{{resolve:secretsmanager:secret-id:SecretString:key}}` dynamic references at runtime).
2. **`awsknowledge` Fallback:** If a question involves a specialized AWS identity mechanism outside local guidance (e.g., IAM Roles Anywhere X.509 trust anchors, S3 Access Grants, STS `SourceIdentity` propagation), query `awsknowledge` / `aws-mcp` (`aws___search_documentation` / `aws___read_documentation` — 1–2 focused searches) and answer directly.

---

## Mandatory 5-Step IAM Governance Workflow

### Step 1: Forensic Diagnosis of Permission Failures (Never Guess Actions)

When a workload, deployment pipeline, or developer encounters `AccessDenied`, `AccessDeniedException`, `UnauthorizedOperation`, or `Client.UnauthorizedOperation`:
1. **Query CloudTrail First**: Call `lookup_events` on the `cloudtrail` MCP server across the last 30–60 minutes filtering by the principal (`Username` / assumed-role session name) or `EventName`.
2. **Extract the Exact Denial Context**:
   - Identify the exact `eventSource` and `eventName` (note where IAM action names differ from API names, e.g., S3 `ListObjectsV2` requires `s3:ListBucket` on the bucket ARN while `GetObject` requires `s3:GetObject` on `<bucket-arn>/*`).
   - Inspect `errorMessage` to determine *which* policy layer denied the request:
     - **Explicit Deny** in an SCP, Resource Control Policy (RCP), IAM Permissions Boundary, Session Policy, or identity/resource policy.
     - **Implicit Deny** in an identity-based policy, KMS Key Policy, S3 Bucket Policy, or VPC Endpoint Policy.
3. **Inspect Current Principal Posture**: Use the `iam` MCP server (`list_roles`, `list_role_policies`, `get_role_policy`, `list_policies`, `get_managed_policy_document`) and `aws-mcp` (`aws___run_script` `iam:GetRole`) to inspect the role's current attached policies, inline policies, trust policy (`AssumeRolePolicyDocument`), and `PermissionsBoundary`.

---

### Step 2: Ephemeral Workload Identity Architecture (Zero Static Keys)

Never create IAM users or long-lived static access keys (`aws iam create-access-key` is hard-blocked by `aws-mutation-gate.py`). Always bind workloads to short-lived STS credentials using the canonical platform identity mechanism for each runtime:

| Compute Runtime | Canonical Identity Mechanism | Key Platform Engineering Rules |
|---|---|---|
| **Amazon EKS (v1.24+)** | **EKS Pod Identity** (`pods.eks.amazonaws.com`) + **EKS Access Entries** | Prefer **EKS Pod Identity** (`AWS::EKS::PodIdentityAssociation` + `eks-pod-identity-agent` add-on) over legacy IRSA for new workloads: single trust policy (`Principal: {"Service": "pods.eks.amazonaws.com"}` with `sts:AssumeRole` and `sts:TagSession`), automatic session tags (`eks-cluster-arn`, `kubernetes-namespace`, `kubernetes-service-account`), and no OIDC thumbprint sprawl. Use **EKS Access Entries** (`authenticationMode: API`) instead of editing the legacy `aws-auth` ConfigMap. Use IRSA (`sts:AssumeRoleWithWebIdentity`) when cross-account OIDC federation or non-EKS K8s is required. |
| **Amazon ECS / Fargate** | **Separate `TaskRoleArn` & `ExecutionRoleArn`** | Strictly separate the **ECS Task Execution Role** (`ecs-tasks.amazonaws.com` — used only by the ECS agent to pull ECR images, push initial CloudWatch logs, and inject `Secrets` at startup) from the **ECS Task Role** (`TaskRoleArn` — used by the application code inside the container at runtime). Never grant application S3/DynamoDB/SQS permissions to the `ExecutionRoleArn`. |
| **Amazon EC2 / ASG** | **IAM Instance Profile** (`setting-up-ec2-instance-profiles`) + **IMDSv2** | Attach a single IAM role per application tier via an Instance Profile. Enforce `HttpTokens: required` (IMDSv2) and **always contrast both hop-limit settings explicitly**: set `HttpPutResponseHopLimit: 2` on containerized EC2/EKS hosts (so the PUT token response survives the extra Docker/CNI bridge hop) versus `HttpPutResponseHopLimit: 1` on standard non-containerized EC2 hosts. Enable `AmazonSSMManagedInstanceCore` for SSH-less Session Manager access. |
| **AWS Lambda** | **Per-Function Execution Role** (`lambda.amazonaws.com`) | Create a dedicated execution role per function (never share a monolithic "all-lambdas-role" across functions). Scope SQS/Kinesis/DynamoDB Stream ESM permissions to the exact source ARNs. |
| **CI/CD Pipelines (GitHub / GitLab)** | **IAM OIDC Identity Provider** (`token.actions.githubusercontent.com`) | Use `sts:AssumeRoleWithWebIdentity` with strict `StringEquals` on `aud` (`sts.amazonaws.com`) and `StringLike` on `sub` (`repo:<org>/<repo>:ref:refs/heads/main` or `environment:production`). Never store AWS keys in CI secrets. |

---

### Step 3: Scoped Policy Synthesis & Condition-Key Hardening

When authoring IAM identity policies, resource policies, or KMS key policies:
1. **Action & Resource Scoping**:
   - Explicitly list required actions (e.g., `s3:GetObject`, `s3:PutObject`, `dynamodb:GetItem`, `dynamodb:Query`, `sqs:SendMessage`).
   - Separate bucket-level actions (`s3:ListBucket` on `arn:aws:s3:::my-bucket`) from object-level actions (`s3:GetObject` on `arn:aws:s3:::my-bucket/prefix/*`).
   - For actions that do not support resource-level permissions (e.g., `ec2:Describe*`, `cloudwatch:PutMetricData`), isolate them in a dedicated statement with `"Resource": "*"` and constrain them with conditions (`cloudwatch:namespace`, `aws:RequestedRegion`) where supported.
2. **Mandatory `iam:PassRole` Guards**:
   - Never grant `iam:PassRole` on `"Resource": "*"`.
   - Always scope `iam:PassRole` to the exact target role ARN(s) and add `"Condition": {"StringEquals": {"iam:PassedToService": ["ecs-tasks.amazonaws.com", "lambda.amazonaws.com", "ec2.amazonaws.com"]}}`.
3. **Cross-Service Confused-Deputy Prevention**:
   - Every role trust policy or resource-based policy (S3 bucket policy, SQS queue policy, SNS topic policy, KMS key policy) granting access to an AWS service principal (`events.amazonaws.com`, `sns.amazonaws.com`, `s3.amazonaws.com`, `cloudfront.amazonaws.com`, `logging.s3.amazonaws.com`) **must** include `aws:SourceAccount` and `aws:SourceArn` conditions.
4. **Permissions Boundaries for Delegated Role Creation**:
   - Whenever a CI/CD deployment role or developer role is allowed `iam:CreateRole`, `iam:AttachRolePolicy`, or `iam:PutRolePolicy`, enforce a `iam:PermissionsBoundary` condition requiring every created/modified role to carry the organization's `WorkloadPermissionsBoundary` policy.

---

### Step 4: Pre-Deployment Policy Simulation & Access Analyzer Validation

Before proposing any IAM attachment or IaC deployment:
1. **IAM Policy Simulator (`iam` & `aws-mcp` MCP)**:
   - For existing IAM roles/users, call `simulate_principal_policy` on the `iam` MCP server; for candidate un-deployed JSON policy documents, execute `iam` `SimulateCustomPolicy` via `aws-mcp` (`aws___run_script` `call_boto3`) with:
     - Positive test cases: verify the exact required `ActionNames` and `ResourceArns` return `allowed`.
     - Negative boundary test cases: verify destructive or out-of-scope actions (`iam:CreateUser`, `s3:DeleteBucket`, `rds:DeleteDBCluster`, accessing another workload's bucket/table) return `implicitDeny` or `explicitDeny`.
2. **IAM Access Analyzer Policy Validation**:
   - Run `aws accessanalyzer validate-policy --policy-type IDENTITY_POLICY --policy-document ...` (or `RESOURCE_POLICY`) via `aws-mcp` to catch syntax errors, security warnings (`PASS_ROLE_WITH_STAR_IN_RESOURCE`), and condition operator mismatches (`ArnEquals` vs `StringLike`).

---

### Step 5: Continuous Unused Access Auditing & Right-Sizing

During Day-2 security reviews:
1. Query `aws iam get-service-last-accessed-details` (after `generate-service-last-accessed-details`) and IAM Access Analyzer unused-access findings (`list-findings`) to identify roles with unused services, actions, or stale credentials.
2. Generate a right-sized replacement policy in IaC and verify via `simulate_principal_policy` that active workload operations remain unaffected before removing unused permissions.
