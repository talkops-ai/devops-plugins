---
description: Triage Security Hub, GuardDuty, and Inspector findings
argument-hint: "[severity or resource filter]"
---

Triage security findings for `$ARGUMENTS` using the `aws-security` skill and the `wa-security` server.

1. Check which security services are enabled, then pull active findings (critical/high first).
2. Deduplicate across services, group by resource, and rank by exploitability and blast radius.
3. Return a prioritized remediation list with concrete steps.

This is a read-only workflow: do not create, modify, or delete resources.
