---
description: Coordinate multi-account and cross-Region DevSecOps workflows across staging, prod, and security profiles via aws-mcp profile switching
argument-hint: "[list | compare <profile-a> <profile-b> | audit]"
---

Invoke the **orchestrating-multi-account-ops** skill to discover configured AWS CLI profiles, verify cross-account SigV4 identities via `aws___call_aws(aws_profile=...)`, compare staging vs. production drift or security posture, and orchestrate gated multi-account promotions.

Multi-account request: $ARGUMENTS
