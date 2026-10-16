---
description: Run a 5-gate pre-deployment release-readiness review across git diffs, IaC change sets, security diff scans, IAM validation, and rollback alarms
argument-hint: "[<branch, PR, or stack-name>]"
---

Invoke the **validating-release-readiness** skill (chaining **diff-scanning-with-aws-security-agent** and **engineering-iam-least-privilege** when applicable) to evaluate the candidate release across 5 gates:
1. Git diff classification and database migration backward-compatibility check.
2. Dry-run CloudFormation Change Set / `cdk diff` / `terraform plan` blast-radius check (blocking on stateful `Replacement: True`).
3. Security Agent git diff vulnerability scan.
4. IAM Access Analyzer policy validation.
5. Target environment CloudWatch alarm health and automated rollback circuit-breaker verification.

Release target: $ARGUMENTS
