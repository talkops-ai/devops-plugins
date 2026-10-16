---
description: Run a native 4-phase SRE root-cause investigation using CloudWatch Alarms, Logs Insights, Application Signals, X-Ray, and CloudTrail
argument-hint: "<symptom, alarm name, service, or error message>"
---

Invoke the **investigating-cloudwatch-incidents** skill (and **auditing-cloudtrail-forensics** or **operating-containers-and-serverless** as needed) to perform a 4-phase root-cause investigation:
1. Triage active CloudWatch Alarms and AWS Health events.
2. Correlate recent CloudFormation, ECS, Lambda, and CloudTrail mutating events across the incident window.
3. Isolate failing dependencies and stack traces via Application Signals, X-Ray traces, and CloudWatch Logs Insights.
4. Deliver a chronological root-cause timeline, gated rollback command, and local IaC/code remediation patch.

Incident context: $ARGUMENTS
