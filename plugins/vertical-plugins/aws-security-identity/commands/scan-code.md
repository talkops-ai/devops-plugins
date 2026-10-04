---
description: Run an AWS Security Agent code scan on the repository
argument-hint: "[path or git ref for diff scan]"
---

Scan the code in `$ARGUMENTS` (default: the current repository) with the `security-agent` server.

1. Explain that the scan uploads source to AWS Security Agent, that it is a billed service, and that first use may provision an agent space and IAM role; wait for approval.
2. Run a full scan, or a diff scan when a git ref is provided, and poll until complete.
3. Summarize findings by severity with file references and suggested fixes. Do not commit exported findings.
