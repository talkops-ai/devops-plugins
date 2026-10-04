---
description: Find who changed an AWS resource and when
argument-hint: "<resource name/ARN> [time window]"
---

Attribute changes to `$ARGUMENTS` using the `cloudtrail` server.

1. Look up management events for the resource in the window (default: last 24 hours), filtering for write events (`Create*`, `Update*`, `Put*`, `Delete*`, `Modify*`).
2. For each change: time, principal (role/session), source IP/user agent, and the request parameters.
3. Summarize as a timeline and note gaps (data events or other regions not covered by the trail).

This is a read-only workflow: do not create, modify, or delete resources.
