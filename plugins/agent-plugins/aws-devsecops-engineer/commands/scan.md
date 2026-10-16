---
description: Run AWS Security Agent full SAST code scans or pre-PR git diff scans and remediate discovered vulnerabilities
argument-hint: "[diff | full | remediate]"
---

Invoke **diff-scanning-with-aws-security-agent** (for git diffs / pre-PR checks), **scanning-with-aws-security-agent** (for full repository scans), and **remediating-with-aws-security-agent** to discover, export (to gitignored `.security-agent/`), prioritize, and patch application and IaC vulnerabilities.

Scan mode or target: $ARGUMENTS
