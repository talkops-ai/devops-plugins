---
name: engineering-iam-least-privilege
description: >-
  Authors, audits, and validates least-privilege AWS IAM policies, trust policies, permission
  boundaries, SCPs, and keyless CI/CD OIDC federation (`sts:AssumeRoleWithWebIdentity`) using
  IAM Access Analyzer (`validate-policy`, `check-no-new-access`, `check-access-not-granted`)
  and CloudTrail activity history. Use when the user asks to "write an IAM policy", "fix
  AccessDenied", "scope down wildcard permissions", "set up GitHub Actions OIDC", or runs `/iam`.
---

# IAM Least-Privilege Engineering & Access Analyzer Validation

## When to Use
Invoke this skill whenever a user needs to author a new IAM policy, troubleshoot an `AccessDenied` / `UnauthorizedOperation` error, scope down overly permissive `Action: "*"` or `Resource: "*"` policies, configure keyless CI/CD OIDC federation for GitHub Actions or GitLab CI, or apply `aws:CalledViaAWSMCP` safety guardrails.

## 4-Step IAM Engineering Workflow

### Step 1: Discover Required Actions & Diagnose `AccessDenied`
1. **Static SDK & IaC Extraction**: Scan local application code (`boto3.client(...)`, `@aws-sdk/client-*`) and IaC templates (`*.tf`, `*.ts`, `template.yaml`) to inventory every AWS API operation invoked by the workload.
2. **Authoritative Action Lookup**: Use `aws-mcp` (`aws___search_documentation` and `aws___read_documentation`) to look up the exact IAM Service Authorization Reference actions, resource ARN types, and condition keys for each service. Never guess IAM action names.
3. **Live `AccessDenied` Diagnosis**: If troubleshooting a permission failure, query `aws-cloudtrail` (`lookup_events`) for `errorCode` in `["AccessDenied", "Client.UnauthorizedOperation"]` to extract the exact `eventSource`, `eventName`, `userIdentity.arn`, and explicit vs. implicit deny context.

### Step 2: Synthesize Least-Privilege Policy & OIDC Trust
Apply strict least-privilege rules when constructing identity, resource, or trust policies:
- **Zero Wildcards on Write Actions**: Scope `Resource` to exact ARNs (`arn:aws:s3:::my-bucket/*`, `arn:aws:dynamodb:${Region}:${Account}:table/Orders`) and add condition keys (`aws:ResourceAccount`, `aws:PrincipalOrgID`, `kms:ViaService`).
- **PassRole Guardrail**: Whenever `iam:PassRole` is required, scope `Resource` to the exact target role ARN and enforce `iam:PassedToService`:

```json
{
  "Sid": "ScopedPassRole",
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::123456789012:role/AppExecutionRole",
  "Condition": {
    "StringEquals": {
      "iam:PassedToService": "ecs-tasks.amazonaws.com"
    }
  }
}
```

- **Keyless CI/CD OIDC Trust Policy (GitHub Actions / GitLab CI)**: Replace static `AKIA*` keys in CI/CD with `sts:AssumeRoleWithWebIdentity` pinned to the exact repository and branch/environment:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:org/repo:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

### Step 3: Mandatory IAM Access Analyzer Validation
**Never deliver an IAM policy without validating it through IAM Access Analyzer** via `aws___run_script` or `aws___call_aws`:

```python
import boto3
import json

aa = boto3.client("accessanalyzer")

policy_doc = {
    "Version": "2012-10-17",
    "Statement": [
        # Candidate policy statements
    ]
}

# 1. Validate syntax, security warnings, and best-practice suggestions
resp = aa.validate_policy(
    policyDocument=json.dumps(policy_doc),
    policyType="IDENTITY_POLICY",  # or RESOURCE_POLICY / SERVICE_CONTROL_POLICY
)

for finding in resp.get("findings", []):
    print(f"[{finding['findingType']}] {finding['issueCode']}: {finding['findingDetails']} ({finding['learnMoreLink']})")
```

- Resolve all `ERROR` and `SECURITY_WARNING` findings before presenting the policy.
- For policy updates on existing roles, also run `aws accessanalyzer check-no-new-access` or `aws accessanalyzer check-access-not-granted` against critical actions (`iam:CreateAccessKey`, `s3:DeleteBucket`, `kms:Decrypt`) when the `accessanalyzer-custom-policy-checks` extension is available.

### Step 4: Enforce `aws:CalledViaAWSMCP` Agent Safety Guardrail
When hardening roles used by developers or AI coding agents, include the `DenyDestructiveActionsViaMCP` statement conditioned on `"Bool": {"aws:CalledViaAWSMCP": "true"}` to block destructive IAM, KMS, S3, RDS, DynamoDB, and CloudTrail deletions initiated through MCP.
