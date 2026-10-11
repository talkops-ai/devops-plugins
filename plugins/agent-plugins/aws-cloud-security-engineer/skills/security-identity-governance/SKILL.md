---
name: security-identity-governance
description: >-
  Audits AWS IAM identities, access keys, trust policies, IAM Access Analyzer findings,
  Organizations SCP guardrails, permission boundaries, and toxic privilege-escalation paths.
  Use for least-privilege reviews, cross-account trust, access-key hygiene, or access-denied
  analysis. Changes are advisory unless separately approved.
version: 1
---

# Security Identity Governance

## Workflow

1. Scope the account, principal, role/resource ARN, organization path, and region where relevant.
2. Collect IAM users, roles, groups, attached/inline policies, access keys, last-used data,
   trust policies, permission boundaries, session-policy context, and SCP/RCP context.
3. Query IAM Access Analyzer for external access and unused-access findings. Inspect trust graphs,
   not only individual policy documents.
4. Test an access-denied hypothesis with policy simulation when the required context is available.
5. Detect toxic combinations, especially unrestricted `sts:AssumeRole` combined with
   `iam:PassRole` and a compute/service creation permission.
6. Produce a remediation diff or least-privilege policy. Never apply access-key deactivation,
   policy attachment, trust-policy change, or SCP change directly from this skill.

## Structured tool contract

```json
{
  "name": "iam_evaluate_access_keys",
  "parameters": {
    "max_age_days": {"type": "integer", "default": 90, "minimum": 1},
    "include_unused": {"type": "boolean", "default": true},
    "account_id": {"type": "string"}
  },
  "required": []
}
```

Return user ARN, access-key ID suffix only when necessary, age, status, last-used service/region,
last-used timestamp, evidence API, and proposed action. Do not return secret material.

## Safety rules

- Do not grant `Action: "*"` or `Resource: "*"` as a generic fix.
- Scope `iam:PassRole` to exact role ARNs and constrain `iam:PassedToService` where applicable.
- Preserve `Null` checks when using `ForAllValues` condition operators.
- Require `aws:SourceAccount` and `aws:SourceArn` for service-principal trust where supported.
- Treat access-key revocation and trust-policy changes as human-approved containment/remediation.
