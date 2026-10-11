---
name: security-posture-audit
description: >-
  Performs read-only AWS security posture and compliance audits across Security Hub CSPM,
  AWS Config, GuardDuty, Inspector, IAM Access Analyzer, Detective, Security Lake, KMS,
  and Well-Architected Security. Use for CIS/FSBP posture, service coverage, configuration
  drift, compliance summaries, and multi-region security baselines.
version: 1
---

# Security Posture Audit

Use this skill for detective and advisory work only. Never enable, disable, modify, archive,
suppress, or resolve a finding from this skill. Remediation is emitted as a proposed change
with `approval_required: true`.

## Operating cadence

- **Daily:** surface GuardDuty `AttackSequence:` findings first, then Security Hub Exposure
  findings, followed by active HIGH/CRITICAL findings from Security Hub, Inspector, and Macie.
  Correlate suspicious actors with CloudTrail before proposing containment.
- **Weekly:** compare service coverage, Config recorder/delivery health, Security Hub standards,
  IAM Access Analyzer findings, GuardDuty/Inspector coverage, encryption posture, VPC flow-log
  coverage, and public administrative ingress.
- **Monthly/periodic:** evaluate CIS AWS Foundations and FSBP controls, organization policies,
  cross-account trust, KMS policy/rotation posture, and multi-stage privilege-escalation paths.

## Evidence collection

1. Establish account, organization/member scope, enabled regions, and evidence timestamp.
2. Enumerate enabled regions before regional calls; bound concurrency and use SDK/CLI pagination.
3. Prefer the `wa-security` tools for service coverage, findings, storage encryption, and network
   checks. Use managed `aws-mcp` `aws___call_aws` for Config, Security Hub CSPM, Access Analyzer,
   GuardDuty, Inspector, KMS, EC2, Organizations, and WAF APIs.
4. Project responses to anomalies and control status; do not return full authorization details,
   configuration histories, or finding bodies unless explicitly requested.

## Required read-only API families

| Domain | Evidence |
|---|---|
| Config | `describe-configuration-recorders`, `describe-delivery-channels`, `describe-config-rules`, `get-compliance-details-by-config-rule`, `get-resource-config-history` |
| Security Hub CSPM | `get-enabled-standards`, `get-findings`, `describe-standards-controls` |
| Access Analyzer | `list-analyzers`, `list-findings`, `get-finding`, `get-analyzed-resource` |
| KMS | `list-keys`, `describe-key`, `get-key-rotation-status`, `get-key-policy`, `list-grants` |
| Network | `describe-security-groups`, `describe-network-acls`, `describe-flow-logs`, `describe-route-tables`, WAF list/get APIs |

## Output contract

Every audit result must include:

```json
{
  "scope": {"account_ids": [], "regions": []},
  "evidence_timestamp": "ISO-8601",
  "finding_type": "string",
  "resource_arn_or_id": "string",
  "observed_state": "string or object",
  "expected_state": "string or object",
  "evidence": ["service/API and concise result"],
  "recommended_change": "advisory only",
  "approval_required": true
}
```

Do not assign a severity to configuration state merely because it is absent. For findings, retain
AWS-provided severity and clearly separate it from analyst exploitability or blast-radius notes.
