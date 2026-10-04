---
description: Validate a CloudFormation/SAM template with cfn-lint and cfn-guard
argument-hint: "<template path>"
---

Validate `$ARGUMENTS` (default: templates found in the repository) using the `aws-cloudformation` skill.

1. Run syntax and schema validation with the `awsiac` server (cfn-lint), then security/compliance rules (cfn-guard).
2. Group results into errors, warnings, and policy violations with resource logical IDs and line numbers.
3. Propose minimal fixes for each issue; edit the template only after the user agrees.

This is a read-only workflow: do not create, modify, or delete resources.
