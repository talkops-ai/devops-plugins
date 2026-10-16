---
name: vpc-network-path-diagnostics
description: Trace and diagnose AWS network connectivity incidents across VPC route tables, Security Groups, NACLs, NAT Gateways, Transit Gateway (TGW), AWS Cloud WAN, AWS Network Firewall, PrivateLink VPC Endpoints, and Route 53 DNS resolution. Use when the user reports connection timeouts, packet drops, blackhole routes, asymmetric routing, NAT Gateway port exhaustion, or cross-VPC/hybrid connectivity failures.
---

# AWS VPC, Transit Gateway, Cloud WAN & Network Path Diagnostics Guide

Use this skill whenever triaging **network connectivity timeouts, packet drops, DNS resolution failures, asymmetric routing, or firewall blocks** across AWS VPCs, Transit Gateways, Cloud WAN, and AWS Network Firewall.

---

## 1. Deterministic 5-Step Network Path Trace Workflow (`network` MCP)

Never guess which Security Group, NACL, or Route Table is dropping traffic. Trace the exact source-to-destination packet path step by step using the `network` MCP server:

| Step | `network` MCP Tool | Diagnostic Objective |
|---|---|---|
| **1. Locate Endpoint ENIs** | `find_ip_address` (or `get_eni_details`) | Resolve both source IP and destination IP to their exact Elastic Network Interfaces (`eni-...`), Subnets, Availability Zones, Security Groups, and VPC IDs. |
| **2. Inspect Source & Dest VPCs** | `get_vpc_network_details` | Inspect Subnet Route Tables (`0.0.0.0/0` -> `nat-...` vs `igw-...` vs `tgw-...`), NACL inbound/outbound rules (including **ephemeral return ports `1024–65535`**), and VPC CIDR blocks. |
| **3. Inspect Transit / Core Routing** | `list_transit_gateways` -> `get_tgw_details` -> `get_all_tgw_routes` (or `list_core_networks` -> `get_cloudwan_details` -> `simulate_cloudwan_route`) | Check for `blackhole` routes, missing TGW route table associations/propagations, or Appliance Mode disabled (`ApplianceModeSupport: disable`) causing asymmetric AZ drops through inspection firewalls. |
| **4. Inspect Network Firewall** | `get_firewall_rules` + `get_network_firewall_flow_logs` | Verify stateless default actions and Suricata stateful rules (`drop http`, `drop tls` SNI inspection) and check alert/flow logs. |
| **5. Analyze Flow Logs** | `get_vpc_flow_logs` / `get_tgw_flow_logs` | Confirm `REJECT` vs `ACCEPT` records, TCP flags (`SYN` sent with zero return packets = routing/stateless NACL drop; `SYN` -> `RST` = application port closed or Security Group/Firewall reset). |

---

## 2. Top Production AWS Network Failure Signatures

| Symptom / Metric | Root Cause | Diagnostic Verification | Remediation |
|---|---|---|---|
| **`ErrorPortAllocation > 0` on NAT Gateway** | Single destination IP exhausted the 55,000 SNAT ephemeral port limit (`64,512` total ports per NAT Gateway IP). | `cloudwatch.get_metric_data` (`AWS/NATGateway`: `ErrorPortAllocation`, `ActiveConnectionCount`). | Associate **secondary Elastic IPs** to the NAT Gateway (up to 8 IPs = 440,000 concurrent connections per destination) or add **Interface/Gateway VPC Endpoints** to bypass NAT for AWS services. |
| **Intermittent Timeouts Across AZs Through TGW Inspection VPC** | **Asymmetric Routing**: Request enters Firewall ENI in `AZ-a`, but return traffic routes through Firewall ENI in `AZ-b`, which drops the unknown TCP state. | `get_tgw_details` on the Inspection VPC attachment (`ApplianceModeSupport`). | Enable **Appliance Mode** (`--options ApplianceModeSupport=enable`) on the Transit Gateway VPC attachment (or Cloud WAN attachment) for the inspection VPC. |
| **Private Subnet Cannot Reach S3 / ECR / CloudWatch / Bedrock** | Missing VPC Endpoint or Private DNS disabled, or Endpoint Security Group blocks inbound TCP `443` from the workload CIDR. | `get_vpc_network_details` + `aws ec2 describe-vpc-endpoints`. | Enable `PrivateDnsEnabled=true` on Interface Endpoints and allow TCP `443` from the VPC CIDR on the Endpoint's Security Group. |
| **VPC Reachability Analyzer Path Failure** | Stateless NACL blocking ephemeral return ports (`1024–65535`), missing return route in peered/TGW VPC, or Security Group egress restriction. | Run `aws ec2 create-network-insights-path` + `start-network-insights-analysis` (or inspect via `describe-network-insights-analyses` on `aws-api`). | Fix the exact blocking component (`Explanations[].ExplanationCode`, e.g., `ENI_SG_RULES_MISMATCH`, `SUBNET_NACL_MISMATCH`, `ROUTE_TABLE_NO_ROUTE`). |

---

## Reference Files

- [references/path-trace-runbook.md](references/path-trace-runbook.md) — End-to-end VPC Reachability Analyzer (`ExplanationCode` reference), Security Group vs. Stateless NACL ephemeral port rules, and Route 53 Resolver (`r53resolver`) DNS debugging
- [references/tgw-and-cloudwan-routing.md](references/tgw-and-cloudwan-routing.md) — Transit Gateway route table association/propagation patterns, Inspection VPC Appliance Mode, and Cloud WAN segment policy simulation
- [references/flow-logs-and-pcap-forensics.md](references/flow-logs-and-pcap-forensics.md) — CloudWatch Logs Insights queries for VPC/TGW/Network Firewall Flow Logs (`tcp-flags`, `pkt-srcaddr`, `pkt-dstaddr`)
