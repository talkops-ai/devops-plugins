---
description: Estimate the monthly cost of an architecture
argument-hint: "<architecture description or IaC path>"
---

Estimate the monthly cost of `$ARGUMENTS` with the `awspricing` server.

1. Extract the services and usage assumptions (region, instance types, requests, storage, data transfer); ask for missing volumes or state assumptions.
2. Price each component with current list prices and sum them.
3. Return a line-item table, the assumptions, and the top two levers to reduce cost.

This is a read-only workflow: do not create, modify, or delete resources.
