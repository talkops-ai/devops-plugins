---
name: security-identity-governance
description: >-
  Audits and designs AWS IAM identities, 8-layer policy evaluation, 21 privilege-escalation paths,
  IAM Access Analyzer, Organizations SCPs and RCPs (Resource Control Policies), Data Perimeters,
  aws:CalledViaAWSMCP and aws:ViaAWSMCPService agentic IAM guardrails, permission boundaries, IAM
  Identity Center (SSO), OIDC/SAML federation, Cognito Identity/User Pool trust boundaries, and
  access-key hygiene. Use for least-privilege reviews, cross-account trust, or access-denied
  diagnosis.
version: 3
---

# Security Identity Governance & Data Perimeter Engineering

Use this skill for **identity posture auditing, access-denied root-cause diagnosis, privilege-escalation graph analysis, Cognito/OIDC federation boundary reviews, and least-privilege policy/SCP/RCP authoring (including `aws:CalledViaAWSMCP` agentic guardrails)**. Never execute IAM mutations (deactivating keys, attaching policies, modifying trust policies, or updating SCPs/RCPs) directly during detective or advisory passes.

## Reference Library (Load On-Demand)

- **[references/privilege-escalation-paths.md](references/privilege-escalation-paths.md)** — Load when auditing IAM principals for the 21 AWS privilege escalation techniques, multi-hop `sts:AssumeRole` chains, `iam:PassRole` + compute execution vectors, permission-boundary bypasses, or access-key/credential hygiene.
- **[references/scp-rcp-data-perimeter.md](references/scp-rcp-data-perimeter.md)** — Load when designing or auditing AWS Organizations Service Control Policies (SCPs), Resource Control Policies (RCPs), AWS Data Perimeters (`aws:PrincipalOrgID`, `aws:ResourceOrgID`, `aws:SourceVpce`), IAM Identity Center Permission Sets, OIDC/SAML federation (`token.actions.githubusercontent.com`), **Amazon Cognito Identity/User Pool trust policies**, or **Zero-Trust MCP execution guardrails (`aws:CalledViaAWSMCP` and `aws:ViaAWSMCPService`)**.

---

## Complete AWS Policy Evaluation Hierarchy (Access-Denied & Exposure Diagnosis)

When diagnosing `AccessDenied` errors or evaluating whether a principal can reach a resource, evaluate **all 8 policy layers** in exact AWS evaluation order:

1. **Explicit Deny anywhere** → Immediate **DENY** (overrides everything).
2. **AWS Organizations Service Control Policies (SCPs)** → Apply to member-account principals (never apply to the Organization Management Account or to service-linked roles). Must allow the action across every OU ancestor from Root to Account.
3. **AWS Organizations Resource Control Policies (RCPs)** → Apply to supported member-account resources (S3, STS, KMS, SQS, Secrets Manager). Must allow the incoming request across every OU ancestor.
4. **Resource-Based Policies (S3 Bucket Policy, KMS Key Policy, IAM Role Trust Policy, Lambda/SNS/SQS Policy, VPC Endpoint Policy)** →
   - **Critical Same-Account Asymmetry:** In the *same* AWS account, if a resource-based policy (e.g., S3 bucket policy or KMS key policy) explicitly grants `Allow` to a specific IAM User or Role ARN (not just `:root`), **access is allowed even without an identity-based policy Allow, and for IAM Users it bypasses the user's Permission Boundary!**
   - **Cross-Account Rule:** Across *different* AWS accounts, **both** the caller's identity-based policy AND the target's resource-based policy must explicitly allow the action (and neither account's SCP/RCP/Permission Boundary may deny it).
5. **IAM Permissions Boundary** → Defines the maximum permissions an IAM User or Role can have. Does not grant permissions on its own; intersects with identity-based policies.
6. **STS Session Policies** → Passed via `AssumeRole` (`Policy` / `PolicyArns`). Intersects with the role's identity-based policies for that session.
7. **Identity-Based Policies (Managed & Inline Policies on User/Group/Role, or IAM Identity Center Permission Sets)** → Must contain at least one `Effect: Allow` when not already satisfied by a same-account resource policy.
8. **ACLs (S3 Object/Bucket ACLs, Network ACLs) & KMS Grants** → Evaluated alongside resource policies where enabled.

---

## Deterministic Identity Audit Workflow

1. **Scope:** Identify account ID(s), Organization ID (`o-xxxxxxxxxx`), OU path, target principal(s) or resource ARN(s), and regions.
2. **Evidence Collection (Read-Only):**
   - Prefer the `iam` MCP server (`list_users`, `list_roles`, `get_user`, `get_role`, `list_attached_role_policies`, `get_role_policy`, `simulate_principal_policy`) and `aws-mcp` (`aws___call_aws`) for Organizations, Access Analyzer, SSO Admin, and Identity Store APIs.
   - Inspect **IAM Access Analyzer**:
     - `accessanalyzer:ListAnalyzers` & `ListFindings` for both `ACCOUNT`/`ORGANIZATION` (external exposure of S3, KMS, IAM roles, Lambda, SQS, SNS, RDS snapshots, ECR, EFS, DynamoDB, Secrets Manager) and `ACCOUNT_UNUSED_ACCESS`/`ORGANIZATION_UNUSED_ACCESS` (unused roles, unused access keys, unused service/action permissions).
   - Inspect **IAM Credential Hygiene**:
     - Enumerate users (`iam:ListUsers`), access keys (`iam:ListAccessKeys`), last-used data (`iam:GetAccessKeyLastUsed`), MFA devices (`iam:ListMFADevices`), and login profiles (`iam:GetLoginProfile`).
   - Build the **Trust, Federation & Escalation Graph**:
     - Inspect every role's `AssumeRolePolicyDocument` (`Principal`, `Action`, `Condition`).
     - Cross-check attached and inline policies against the 21 privilege escalation primitives in [references/privilege-escalation-paths.md](references/privilege-escalation-paths.md).
     - Audit **Amazon Cognito Identity Pools (`cognito-identity:DescribeIdentityPool`, `GetIdentityPoolRoles`) & User Pools (`cognito-idp:DescribeUserPool`, `DescribeUserPoolClient`)**: flag unauthenticated role over-privilege, missing `cognito-identity.amazonaws.com:amr == "authenticated"` trust conditions, writable custom attributes (`WriteAttributes`) used in role mapping, or missing WAFv2 WebACL protection.
     - Audit **Agentic & MCP IAM Boundaries**: verify whether roles shared by humans and AI coding/ops agents enforce `aws:ViaAWSMCPService` and `aws:CalledViaAWSMCP` condition keys to block destructive mutations via MCP.
3. **Policy Simulation & Access Analyzer Validation:**
   - For `AccessDenied` troubleshooting: run `iam:SimulatePrincipalPolicy` with `--policy-source-arn`, `--action-names`, `--resource-arns`, and `--context-entries` (e.g., `aws:SourceIp`, `aws:SourceVpce`, `aws:MultiFactorAuthPresent`, `aws:ViaAWSMCPService`, `aws:CalledViaAWSMCP`, `aws:PrincipalTag/*`).
   - For newly authored or remediated policies: validate syntax, security warnings, and least-privilege compliance using:
     - `aws accessanalyzer validate-policy --policy-type IDENTITY_POLICY|RESOURCE_POLICY|SERVICE_CONTROL_POLICY|RESOURCE_CONTROL_POLICY --policy-document ...`
     - `aws accessanalyzer check-no-new-access` / `check-access-not-granted` (when custom policy checks are requested).
4. **Emit Advisory Remediation Diff:**
   - Output the minimal IAM JSON policy, trust policy, SCP/RCP, or Terraform/CDK diff with per-statement rationale and `approval_required: true`.

---

## Structured Tool Contract: Access Key Hygiene Audit

```json
{
  "name": "iam_evaluate_access_keys",
  "parameters": {
    "max_age_days": {"type": "integer", "default": 90, "minimum": 1},
    "max_unused_days": {"type": "integer", "default": 45, "minimum": 1},
    "include_unused": {"type": "boolean", "default": true},
    "account_id": {"type": "string"}
  },
  "required": []
}
```

**Output Projection:** Return `user_arn`, `access_key_id` (masked or ID only—never secret material), `status`, `age_days`, `last_used_date`, `last_used_service`, `last_used_region`, `mfa_enabled`, `attached_admin_or_escalation_risk`, `evidence_api`, and `recommended_action` (e.g., migrate workload to IAM Role / OIDC Federation / Identity Center, then deactivate key via approved workflow).

---

## Mandatory IAM Authoring & Safety Rules

- **Never Grant Wildcard Admin as a Fix:** Never propose `"Action": "*"` or `"Resource": "*"` unless the statement is an explicit `Effect: Deny` guardrail or a read-only `Describe*`/`List*` action that AWS does not support resource-level ARN scoping for.
- **Constrain `iam:PassRole`:** Always scope `Resource` to exact target Role ARNs (never `*`) and add `Condition.StringEquals["iam:PassedToService"]` (and `iam:AssociatedResourceArn` where supported).
- **Prevent `ForAllValues` Vacuous Truth:** Whenever using `ForAllValues:StringEquals` or `ForAllValues:StringLike`, ALWAYS pair it with `"Null": {"<same-context-key>": "false"}` in the same Condition block so an empty request context does not evaluate to `true`.
- **Enforce Confused Deputy Protection on Service Trust Policies:** Always include `aws:SourceAccount` and `aws:SourceArn` conditions on `AssumeRolePolicyDocument` statements granting access to AWS service principals (`lambda.amazonaws.com`, `events.amazonaws.com`, `scheduler.amazonaws.com`, `codebuild.amazonaws.com`, `pipes.amazonaws.com`, `drt.shield.amazonaws.com`, etc.).
- **Harden OIDC & Cognito Federation Trust Policies:** For GitHub Actions (`token.actions.githubusercontent.com`), GitLab, or EKS IRSA, require `StringEquals` on `:aud` and scope `:sub` to explicit repositories/branches/environments or Kubernetes `system:serviceaccount:<namespace>:<sa-name>`—never allow unanchored wildcards like `repo:org/*`. For Cognito Identity Pools, always enforce `"StringEquals": {"cognito-identity.amazonaws.com:aud": "<pool-id>"}` and `"ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "authenticated"}`.
- **Enforce Agentic MCP Guardrails (`aws:ViaAWSMCPService` & `aws:CalledViaAWSMCP`):** When authoring SCPs or IAM policies for roles used with AWS-managed MCP servers, deny destructive/privileged mutations (`s3:DeleteBucket`, `dynamodb:DeleteTable`, `rds:DeleteDBInstance`, `iam:*`, `organizations:*`, `kms:ScheduleKeyDeletion`) when `aws:ViaAWSMCPService == "true"` or constrain allowed MCP service principals via `aws:CalledViaAWSMCP`.
