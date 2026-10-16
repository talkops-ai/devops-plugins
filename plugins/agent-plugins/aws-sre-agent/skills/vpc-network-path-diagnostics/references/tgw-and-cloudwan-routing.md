# AWS Transit Gateway (TGW) & Cloud WAN Routing Reference

## 1. Transit Gateway Association vs. Propagation

A Transit Gateway attachment uses two distinct mechanisms across TGW Route Tables:
- **Association** (1-to-1): Determines **which TGW Route Table a packet uses when entering the TGW** from that attachment.
- **Propagation** (1-to-many): Advertises the attachment's CIDR into one or more TGW Route Tables so other attachments know how to reach it.

### Hub-and-Spoke Inspection VPC Pattern
To force traffic between `Spoke-A` (`10.1.0.0/16`) and `Spoke-B` (`10.2.0.0/16`) through a central `Inspection-VPC` running AWS Network Firewall:
1. **Spoke TGW Route Table**:
   - **Associated with**: `Spoke-A` and `Spoke-B` attachments.
   - **Static Route**: `0.0.0.0/0` -> `Inspection-VPC` attachment (do NOT propagate spoke CIDRs directly into the Spoke Route Table, or spokes will bypass the firewall!).
2. **Firewall / Inspection TGW Route Table**:
   - **Associated with**: `Inspection-VPC` attachment.
   - **Propagated with**: `Spoke-A` (`10.1.0.0/16`) and `Spoke-B` (`10.2.0.0/16`) attachments.
3. **Mandatory Appliance Mode**:
   - Enable `ApplianceModeSupport: enable` on the `Inspection-VPC` TGW attachment (`aws ec2 modify-transit-gateway-vpc-attachment --transit-gateway-attachment-id tgw-attach-... --options ApplianceModeSupport=enable`). Without Appliance Mode, TGW hashes return traffic to the source AZ's firewall ENI instead of the forward-path firewall ENI, causing 50–67% of cross-AZ TCP handshakes to fail!

---

## 2. AWS Cloud WAN (`network` MCP Tools)

When operating global/multi-region networks on AWS Cloud WAN:
1. Call `list_core_networks` to identify the Core Network ID (`core-network-...`).
2. Call `get_cloudwan_details` and `get_cloudwan_attachment_details` to inspect segments (`prod`, `nonprod`, `shared-services`), attachment states, and Network Function Groups (NFGs).
3. Call `simulate_cloudwan_route` and `analyze_cloudwan_policy` to verify whether segment-sharing and service-insertion rules route traffic between source and destination segments as intended.
