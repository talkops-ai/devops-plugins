---
description: Put CloudFront, WAF, and Shield Advanced in front of a web app
argument-hint: "<origin, e.g. ALB DNS name or S3 bucket>"
---

Harden the internet-facing entry point for `$ARGUMENTS`.

1. Load `cloudfront` to design the distribution (origin access, TLS/ACM, caching, security response headers policy).
2. Load `waf` for a web ACL (managed rule groups, rate-based rules, logging) and `shieldadvanced` to decide whether DDoS protection and response-team access are warranted.
3. Produce the configuration as IaC with a rollout plan (count mode first for WAF rules).

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
