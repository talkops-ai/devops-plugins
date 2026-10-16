---
description: Author least-privilege IAM policies, troubleshoot AccessDenied errors, configure CI/CD OIDC, and validate with IAM Access Analyzer
argument-hint: "<role, policy file, AccessDenied error, or CI/CD OIDC target>"
---

Invoke the **engineering-iam-least-privilege** skill to scan local SDK/IaC usage or CloudTrail `AccessDenied` events, synthesize least-privilege IAM identity/resource/trust policies or keyless GitHub/GitLab OIDC federation, validate policies via IAM Access Analyzer (`validate-policy` / `check-no-new-access`), and enforce `aws:CalledViaAWSMCP` safety guardrails.

Target or request: $ARGUMENTS
