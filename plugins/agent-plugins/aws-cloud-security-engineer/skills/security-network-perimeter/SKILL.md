---
name: security-network-perimeter
description: >-
  Audits and designs AWS VPC network perimeter, segmentation, and edge controls: 7-layer VPC
  perimeter, Security Groups, NACLs, PrivateLink VPC Endpoint policies, Transit Gateway and Cloud
  WAN inspection, AWS Network Firewall, Route 53 DNS Firewall, WAFv2 WebACL tuning/Bot/Fraud/log
  forensics, Shield Advanced L3/L4/L7 DDoS protection, VPC Flow Logs v5, and Traffic Mirroring
  packet capture.
version: 3
---

# Security Network Perimeter, Segmentation & Edge Audit

This skill is **strictly read-only** during detective audits. It evaluates network reachability, perimeter exposure, private endpoint policies, DNS/firewall inspection, VPC Traffic Mirroring packet capture, and edge WAFv2/Shield Advanced coverage, and produces remediation diffs (`approval_required: true`). Never authorize, revoke, add, or delete network or firewall rules directly during an audit.

## Reference Library (Load On-Demand)

- **[references/vpc-perimeter-and-endpoints.md](references/vpc-perimeter-and-endpoints.md)** — Load when auditing Security Groups, NACLs, Route Tables, VPC Endpoint Policies (`aws:PrincipalOrgID`, `aws:ResourceOrgID`), Transit Gateway & Cloud WAN route table isolation, AWS Network Firewall Suricata rules, Route 53 Resolver DNS Firewall, **VPC Traffic Mirroring (out-of-band IDS/packet forensics)**, or Systems Manager Session Manager hardening vs. SSH/RDP bastions.
- **[references/waf-and-flowlog-forensics.md](references/waf-and-flowlog-forensics.md)** — Load when querying **VPC Flow Logs v5** or **AWS WAFv2 Logs** via CloudWatch Logs Insights (`cloudwatch` MCP server) or Athena, tuning **WAFv2 Managed Rule Groups (`Count`-to-`Block`), Rate-Based Rules, Bot Control (`Common` vs. `Targeted`), Fraud Control (ATP/ACFP), inbound `x-amzn-waf-*` header-spoofing stripping, real client IP recovery behind CDNs**, or configuring **AWS Shield Advanced (Protection Groups, L7 auto-mitigation, Route 53 health-based detection, and SRT `drt.shield.amazonaws.com` trust scoping)**.

---

## Structured Tool Contract: VPC Security Group Exposure Audit

```json
{
  "name": "vpc_audit_security_group_ingress",
  "parameters": {
    "region": {"type": "string"},
    "vpc_id": {"type": "string"},
    "restricted_ports": {
      "type": "array",
      "items": {"type": "integer"},
      "default": [22, 23, 3389, 445, 1433, 1521, 3306, 5432, 6379, 9200, 11211, 27017, 8080, 8443]
    },
    "ignore_web_traffic": {"type": "boolean", "default": true}
  },
  "required": ["region"]
}
```

---

## Deterministic 7-Layer Network Perimeter Audit Procedure

1. **Enumerate VPCs, Subnets & Routing Reachability (`awsnetwork` & `aws-mcp`):**
   - Call `ec2:DescribeVpcs`, `ec2:DescribeSubnets`, `ec2:DescribeRouteTables`, `ec2:DescribeInternetGateways`, `ec2:DescribeNatGateways`, and `ec2:DescribeVpcPeeringConnections`.
   - Classify each subnet as **Public** (route table has `0.0.0.0/0` or `::/0` pointing to `igw-*`), **Private with Egress** (pointing to `nat-*`, `tgw-*`, or `vpce-*` firewall endpoint), or **Isolated** (local VPC route only + VPC Endpoints).
   - Flag any `MapPublicIpOnLaunch == true` on subnets hosting compute or databases.
2. **Audit Security Groups (Ingress & Egress):**
   - Expand IPv4 (`IpRanges`) and IPv6 (`Ipv6Ranges`) rules on `ec2:DescribeSecurityGroups`, including `IpProtocol == "-1"` (all protocols/ports) and wide port ranges (`FromPort <= restricted_port <= ToPort`).
   - Flag unrestricted `0.0.0.0/0` or `::/0` ingress on administrative/database ports (`22, 3389, 3306, 5432, 6379, 27017`, etc.).
   - When `ignore_web_traffic == true`, report `80/443` `0.0.0.0/0` only if attached directly to an EC2/ECS ENI (`ec2:DescribeNetworkInterfaces --filters Name=group-id,Values=<sg-id>`) rather than an ALB/NLB protected by WAF!
   - Check the **Default Security Group** (`GroupName == "default"`) in every VPC: CIS 5.4 / `EC2.2` requires it to have **zero inbound and zero outbound rules** and zero attached ENIs.
3. **Verify Blast Radius (Actual Subnet Routing & ENI Attachment):**
   - A Security Group with `0.0.0.0/0` on port 22 attached to an instance with **no public IP** in a **Private Subnet** has a *lateral/internal* blast radius, whereas an instance with a Public IP in a Public Subnet (`igw-*` route) has **immediate Internet exposure**. Always distinguish these two in `exposure_interpretation`.
4. **Audit Network ACLs (CIS 5.1 / EC2.21):**
   - Call `ec2:DescribeNetworkAcls` and check for `RuleAction == "allow"` with `0.0.0.0/0` or `::/0` on ports `22` or `3389` (or protocol `-1` without tighter precede rules).
5. **Audit VPC Flow Logs v5, DNS Query Logging & Traffic Mirroring (CIS 3.9 / EC2.6):**
   - Call `ec2:DescribeFlowLogs` for every VPC: verify `FlowLogStatus == "ACTIVE"`, `TrafficType == "ALL"` (never `ACCEPT`-only, which blinds you to port scans and blocked lateral movement), and recommend v5 custom format (`pkt-srcaddr`, `pkt-dstaddr`, `flow-direction`, `traffic-path`, `tcp-flags`).
   - Call `route53resolver:ListResolverQueryLogConfigAssociations` to check if VPC DNS query logging is enabled.
   - Call `ec2:DescribeTrafficMirrorSessions` and `ec2:DescribeTrafficMirrorTargets` when out-of-band packet inspection (Suricata/Zeek NIDS) or incident packet capture is required.
6. **Audit Administrative Access Paths (Session Manager vs. Bastions):**
   - Check if EC2 instances with port 22/3389 open can be migrated to **AWS Systems Manager Session Manager** via VPC Interface Endpoints (`ssm`, `ssmmessages`, `ec2messages`) with KMS-encrypted sessions and CloudWatch/S3 session logs.
7. **Audit Edge Protection (WAFv2, CloudFront Origin Locking & Shield Advanced):**
   - Call `wafv2:ListWebACLs` (`Scope=REGIONAL` and `Scope=CLOUDFRONT` in `us-east-1`), `wafv2:GetWebACL`, `wafv2:GetLoggingConfiguration`, and `wafv2:ListResourcesForWebACL`.
   - Flag any Internet-facing ALB, API Gateway Stage, AppSync GraphQL API, Cognito User Pool, or CloudFront Distribution lacking a WAFv2 WebACL association, or any WebACL where managed rules are left permanently in `Count` mode without enforcing rules.
   - Verify WAFv2 logging redacts sensitive headers (`authorization`, `cookie`) and that any origin trusting `x-amzn-waf-*` signal headers strips spoofed inbound `x-amzn-waf-*` headers first.
   - For CloudFront → ALB/S3 architectures, verify **Origin Access Control (OAC)** on S3 and verify the ALB Security Group is locked to the AWS-managed CloudFront prefix list (`com.amazonaws.global.cloudfront.origin-facing`) plus a custom secret header verified by WAF/ALB listener rules so attackers cannot bypass CloudFront/WAF by hitting the ALB DNS name directly.
   - Audit **AWS Shield Advanced** (`shield:DescribeSubscription`, `shield:ListProtections`, `shield:ListProtectionGroups`, `shield:DescribeDRTAccess` in `us-east-1`) for critical internet-facing resources, verifying Route 53 health-based detection, L7 automatic application-layer mitigation, and confused-deputy `aws:SourceAccount` scoping on the `drt.shield.amazonaws.com` role.

---

## Output Contract

Return `security_group_id`, `vpc_id`, `subnet_exposure_class` (`PUBLIC_IGW` | `PRIVATE_NAT` | `ISOLATED`), `protocol`, `port_range`, `cidr`, `security_group_rule_id`, `attached_enis_and_resources`, `flow_logs_active`, `waf_associated`, `evidence_api`, `exposure_interpretation`, `recommended_iac_or_cli_diff`, and `approval_required: true`.
