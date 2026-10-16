---
description: Configure AWS SigV4 credentials, verify MCP servers and IAM safety guardrails, and optionally initialize AWS Security Agent
argument-hint: "[--profile <aws-profile>] [--security-agent]"
---

Invoke the **setup** skill (and **signing-in-to-aws** or **setup-security-agent** when needed) to verify local prerequisites (`aws`, `uvx`), validate active AWS SigV4 credentials and named profiles, confirm connectivity across the 6 bundled MCP servers (`aws-mcp`, `aws-security-agent`, `aws-cloudwatch`, `aws-cloudtrail`, `aws-well-architected-security`, `aws-billing`), verify `aws:CalledViaAWSMCP` IAM guardrails, and optionally provision an AWS Security Agent workspace.

User arguments: $ARGUMENTS
