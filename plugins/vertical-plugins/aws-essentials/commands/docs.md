---
description: Answer an AWS question from current AWS documentation
argument-hint: "<question>"
---

Answer `$ARGUMENTS` from current AWS sources rather than training data.

1. Search with the `awsknowledge` server (or `aws___search_documentation` on `aws-mcp`); read the most relevant pages.
2. For regional availability or quotas, check the dedicated tools/pages instead of inferring.
3. Answer concisely, cite the documentation URLs used, and say explicitly when something could not be verified.

This is a read-only workflow: do not create, modify, or delete resources.
