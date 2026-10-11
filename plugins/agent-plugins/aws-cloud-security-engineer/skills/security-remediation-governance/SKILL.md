---
name: security-remediation-governance
description: >-
  Converts AWS security findings into safe remediation proposals with blast-radius analysis,
  least-privilege changes, approval gates, and post-change verification. Use after detective
  audits when an operator requests remediation planning.
version: 1
---

# Security Remediation Governance

Use a four-phase lifecycle:

1. **Detective:** collect read-only evidence and preserve the evidence timestamp.
2. **Advisory:** calculate the minimal Terraform, CLI, or IAM policy diff; do not mutate AWS.
3. **Approval:** present affected accounts, regions, resources, permissions, downtime risk,
   rollback, and required approver. Do not treat model/tool availability as approval.
4. **Execution and verification:** an approved Step Functions/Lambda or operator workflow applies
   one controlled change, records CloudTrail/CloudWatch evidence, and re-runs the original audit.

## Proposal contract

```json
{
  "finding_id": "string",
  "root_cause": "string",
  "affected_resources": [],
  "proposed_change": {"iac": "string", "cli": "string"},
  "permissions_required": [],
  "blast_radius": "string",
  "rollback": "string",
  "approval_required": true,
  "verification_query": "string"
}
```

Never propose destructive actions without explicit operator authorization. Never purge logs,
reveal secrets, broadly attach administrator policies, or use wildcard `iam:PassRole` as a shortcut.
