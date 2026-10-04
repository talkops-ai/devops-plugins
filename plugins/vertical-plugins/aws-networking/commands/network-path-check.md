---
description: Explain why one AWS resource cannot reach another
argument-hint: "<source> <destination> [port]"
---

Diagnose connectivity from source to destination for `$ARGUMENTS`.

1. Use the `awsnetwork` server to trace the path: route tables, security groups, NACLs, Transit Gateway/peering routes, endpoints, and firewalls.
2. Where available, run Reachability Analyzer and check Network Monitor / flow-log evidence (`aws-network-monitoring`).
3. Return the blocking hop, the evidence, and the smallest change that opens exactly the required path.

This is a read-only workflow: do not create, modify, or delete resources.
