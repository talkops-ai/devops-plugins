---
description: Audit and harden an S3 bucket
argument-hint: "<bucket name>"
---

Assess bucket `$ARGUMENTS` with the `securing-s3-buckets` skill.

1. Check Block Public Access (account and bucket), bucket policy and ACLs, Object Ownership, default encryption (SSE-KMS where required), versioning/Object Lock, TLS-only access, and access logging.
2. Report each control as pass/fail with evidence.
3. Propose the hardened bucket policy and settings; apply only after approval, and warn about anything that could break existing consumers.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
