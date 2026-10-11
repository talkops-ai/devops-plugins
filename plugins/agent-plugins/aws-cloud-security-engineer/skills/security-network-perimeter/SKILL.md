---
name: security-network-perimeter
description: >-
  Audits AWS VPC perimeter controls: security groups, NACLs, route tables, VPC Flow Logs,
  WAF associations, and administrative access paths. Use for public ingress, segmentation,
  exposed management ports, and Session Manager versus bastion reviews.
version: 1
---

# Security Network Perimeter Audit

This skill is read-only. It identifies exposure and produces remediation diffs; it does not
authorize, revoke, add, or delete network rules.

## Structured contract

```json
{
  "name": "vpc_audit_security_group_ingress",
  "parameters": {
    "region": {"type": "string"},
    "vpc_id": {"type": "string"},
    "restricted_ports": {"type": "array", "items": {"type": "integer"}, "default": [22, 3389, 3306, 5432, 27017, 6379, 8080]},
    "ignore_web_traffic": {"type": "boolean", "default": true}
  },
  "required": ["region"]
}
```

## Procedure

1. Enumerate VPCs and security groups in the requested region, optionally constrained by VPC ID.
2. Expand IPv4 and IPv6 ingress permissions, including `-1` protocols and port ranges.
3. Flag unrestricted administrative and database ports, but report unrestricted 80/443 separately
   when `ignore_web_traffic` is true.
4. Inspect NACL entries, route tables, internet/NAT gateways, VPC Flow Logs, and ENI/resource
   associations to establish blast radius.
5. Check whether administrative access has a private Systems Manager Session Manager path rather
   than a public bastion or public instance address.
6. Check WAF web ACL association for internet-facing CloudFront, ALB, API Gateway, and AppSync
   resources. WAF rule design belongs to the `waf` skill.

## Output

Return security-group ID, VPC ID, protocol, port bounds, CIDR, rule ID where available, attached
resource context, evidence API, exposure interpretation, recommended IaC/CLI diff, and
`approval_required: true`. Never apply a rule change during an audit.
