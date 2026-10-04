---
description: Sign in to AWS and verify the active credentials
argument-hint: "[profile or SSO start URL]"
---

Load the `signing-in-to-aws` skill and get the user to a working AWS session.

1. Detect the current state (`aws sts get-caller-identity`, `aws configure list`) without printing secrets.
2. If credentials are missing or expired, follow the skill's sign-in path (`aws login`, IAM Identity Center, or an existing profile). Use `$ARGUMENTS` as the profile or start URL if provided.
3. Confirm the account ID, principal ARN, and region that subsequent commands will use.

Ask before running any interactive login. Never echo access keys, session tokens, or SSO cache contents.
