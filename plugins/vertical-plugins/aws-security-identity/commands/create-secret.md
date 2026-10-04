---
description: Create a secret in Secrets Manager the right way
argument-hint: "<secret purpose>"
---

Create a secret for `$ARGUMENTS` with `creating-secrets-using-best-practices`.

1. Choose name/path, KMS key, resource policy, rotation (managed rotation where supported), and replication.
2. Never put the secret value in chat or shell history; have the user supply it through a file or prompt, following `aws-secrets-manager`.
3. Show how consumers retrieve it (SDK/caching, `{{resolve:secretsmanager:...}}` in IaC).

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
