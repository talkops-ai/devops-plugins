---
description: Explain why an AWS API call was denied
argument-hint: "<principal> <action> <resource>"
---

Diagnose the AccessDenied for `$ARGUMENTS` using the `aws-iam` skill and the read-only `iam` server.

1. Collect the failing CloudTrail event if available.
2. Evaluate each policy layer: SCPs/RCPs, permission boundary, session policy, identity policy, resource policy, and KMS key policy; simulate the call.
3. Name the denying layer with evidence and propose the narrowest fix.

This is a read-only workflow: do not create, modify, or delete resources.
