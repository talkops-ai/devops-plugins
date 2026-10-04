---
description: Generate a least-privilege IAM policy
argument-hint: "<code path, Terraform plan, or description>"
---

Write a least-privilege IAM policy for `$ARGUMENTS` with the `aws-iam` skill.

1. Derive the exact actions and resource ARNs from the code/plan/description; use condition keys to narrow further.
2. Validate the draft with IAM Access Analyzer policy validation and explain each statement.
3. Flag anything that remains broad and why.

This is a read-only workflow: do not create, modify, or delete resources. Policy changes are applied through IaC or an explicitly approved step.
