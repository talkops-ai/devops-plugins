---
name: security-incident-triage
description: >-
  Performs AWS daily threat triage and forensic correlation across GuardDuty, Security Hub,
  Inspector, Macie, Detective, Security Lake, CloudTrail, and IAM. Use for exposed credentials,
  suspicious API activity, attack sequences, finding prioritization, and incident timelines.
version: 1
---

# Security Incident Triage

## Triage order

1. Surface GuardDuty findings whose type starts with `AttackSequence:`.
2. Surface Security Hub Exposure findings and attack paths.
3. Group remaining active findings by AWS-provided severity, resource, principal, and evidence.
4. Correlate the finding with CloudTrail `lookup_events`; for access keys use `AccessKeyId`, and
   for principals use `Username` or resource attributes.
5. Use Detective for entity relationships and Security Lake/Athena only for explicitly requested
   OCSF threat hunting.
6. Produce containment recommendations without directly disabling users, keys, sessions, network
   rules, or resources.

## Structured contract

```json
{
  "name": "cloudtrail_correlate_actor",
  "parameters": {
    "access_key_id": {"type": "string"},
    "actor_arn": {"type": "string"},
    "start_time": {"type": "string"},
    "end_time": {"type": "string"},
    "region": {"type": "string"}
  },
  "required": ["start_time", "end_time"]
}
```

## Timeline output

Return chronological events with event time, event name/source, principal, source IP, region,
read/write classification, error code, affected resource, and confidence. Redact secrets and
summarize sensitive IP/resource data before displaying full evidence.

## Containment boundary

The advisory report may propose access-key deactivation, session restriction, security-group
isolation, finding workflow updates, or Step Functions/Lambda remediation. Every proposal must
include blast radius, rollback, required permissions, and `approval_required: true`. Execution
belongs to a human-approved external workflow.
