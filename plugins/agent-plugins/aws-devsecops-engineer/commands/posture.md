---
description: Triage and remediate cloud security posture (CSPM) findings across Security Hub, GuardDuty, Inspector, and AWS Config
argument-hint: "[--severity CRITICAL,HIGH] [--service guardduty|securityhub|inspector]"
---

Invoke the **triaging-cloud-security-posture** skill (and **auditing-cloudtrail-forensics** if active runtime threats are detected) to sweep AWS Security Hub, Amazon GuardDuty, Amazon Inspector, and AWS Config, deduplicate and rank findings by exploitability and blast radius, map affected AWS resource ARNs back to local Terraform/CDK/CloudFormation/Dockerfile files, and synthesize verified remediation patches.

Scope / filters: $ARGUMENTS
