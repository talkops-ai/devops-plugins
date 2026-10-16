---
description: Analyze AWS spend, detect cost anomalies, sweep idle resources, and generate FinOps right-sizing patches in local IaC
argument-hint: "[--days 30] [--service <service-name>]"
---

Invoke the **optimizing-cloud-costs-and-finops** skill using the `aws-billing` and `aws-mcp` servers to break down 30-day spend and cost anomalies, sweep idle/unattached resources (EBS volumes, Elastic IPs, NAT Gateways, unretained CloudWatch Logs), evaluate Graviton and Compute Optimizer right-sizing recommendations, and patch local IaC templates.

Cost scope: $ARGUMENTS
