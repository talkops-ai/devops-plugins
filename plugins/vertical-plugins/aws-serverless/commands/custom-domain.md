---
description: Put a custom domain and TLS certificate on a REST API
argument-hint: "<domain> <API ID>"
---

Use `deploying-custom-domain-rest-api` to serve `$ARGUMENTS` on a custom domain.

1. Choose endpoint type (edge vs regional), ACM certificate (region rules), base path mappings, and Route 53 alias records.
2. Include TLS policy and mutual TLS if requested.
3. Produce the IaC or CLI plan and a verification checklist (DNS propagation, certificate validation).

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
