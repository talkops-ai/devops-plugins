---
description: Fix EFS mount, permission, or performance problems
argument-hint: "<file system ID> [client instance/task]"
---

Troubleshoot EFS for `$ARGUMENTS` using the `troubleshooting-efs` skill.

1. Verify mount targets per AZ, security groups (NFS 2049), DNS resolution, and the client mount helper/TLS options.
2. For permission errors, check POSIX ownership, access points, and the file system policy; for performance, check throughput mode, burst credits, and metered I/O.
3. Return root cause, evidence, and the fix.

This is a read-only workflow: do not create, modify, or delete resources.
