# VPC DNS Precedence Model, Read-Only MCP Data Collection & Symbolic Simulation

This reference defines the exact 7-level Amazon VPC DNS resolution precedence stack, the read-only control-plane API collection sequence executed via **`aws-mcp` (`aws___run_script`)** and **`awsnetwork`**, and the symbolic Mode B pre-change simulation engine.

---

## 1. The 7-Level VPC DNS Precedence Stack (Highest -> Lowest)

Every DNS query sent to the Amazon VPC Resolver (`169.254.169.253` / VPC base `+2` on IPv4, or `fd00:ec2::253` on IPv6) is evaluated deterministically in this order:

| Level | Construct | Winning Answer Class & Behavior |
| :---: | :--- | :--- |
| **0 (Gate)** | **VPC `enableDnsSupport` Attribute** | If `enableDnsSupport=false`, **nothing** the VPC Resolver would answer works — Resolver rules, Private Hosted Zones, PrivateLink DNS, and DNS Firewall do **not** evaluate. Short-circuits immediately (`VPC resolver disabled`). |
| **1** | **Route 53 DNS Firewall** | Evaluated before resolution completes in ascending `Priority` order (lowest number wins). A matching `BLOCK` rule short-circuits to `NXDOMAIN` (`NODATA`) or `BLOCKED` (`OVERRIDE`). `ALLOW` / `ALERT` pass through. Cross-account RAM-shared or Managed Domain Lists whose domain contents cannot be read (`AccessDenied` on `ListFirewallDomains`) are **`OPAQUE`** (`present, match set unknown`). |
| **2 & 3** | **Route 53 Resolver Rules (`FORWARD` vs `SYSTEM`)** | **Most-specific domain suffix match wins** (counted by label depth; `.` root has specificity `0`). At equal specificity, `FORWARD` beats `SYSTEM`.<br>• If the winning rule is **`FORWARD`** -> query is sent to the outbound endpoint's target IPs (`ONPREM`), outranking both PrivateLink Private DNS and Private Hosted Zones!<br>• If the winning rule is **`SYSTEM`** -> forces VPC-native resolution (carves the subdomain out of a broader parent `FORWARD` rule) and falls through to Level 4.<br>• `RECURSIVE` autodefined `.` rules are standard fallthrough, not overrides.<br>• Cross-account Profile-inherited rules where `GetResolverRule` returns `AccessDenied` are **`OPAQUE`**. |
| **4** | **PrivateLink / VPC Lattice Managed Private-DNS Shadows** | Covers Interface VPC Endpoints (`PrivateDnsEnabled=true`), VPC Lattice Service Network VPC Associations (`SNVA`), Service Network Endpoints, and Resource Endpoints.<br>• **Gated AWS-Owned FQDNs (`*.amazonaws.com`, `*.api.aws`):** Governed by the SNVA `PrivateDnsPreference` gate (`VERIFIED_DOMAINS_ONLY` default vs `ALL_DOMAINS` vs `SPECIFIED_DOMAINS_ONLY`). Note: standard PrivateLink Interface Endpoints install AWS-verified service zones directly when both `enableDnsSupport=true` AND `enableDnsHostnames=true`.<br>• **Shadow-NXDOMAIN Trap:** An installed shadow PHZ is **authoritative for its entire `service_apex`**. It answers the exact apex and `served_names`, while **any other strict subdomain under that apex returns `NXDOMAIN`** instead of falling back to public DNS! |
| **5** | **Associated Route 53 Private Hosted Zones (PHZ)** | Direct VPC-associated PHZs plus PHZs inherited via an associated **Route 53 Profile** (`source = "direct"` or `"profile:<id>"`). Most-specific matching PHZ apex wins (`PHZ_PRIVATE`). If the record does not exist inside that authoritative PHZ, it returns `NXDOMAIN` (no public fallback). |
| **6** | **Declared On-Premises / Corporate Zones Without `FORWARD`** | If an operator-declared corporate zone (e.g., `corp.internal`) reaches Level 6 with no matching `FORWARD` rule above, the VPC `.2` resolver has no path to on-prem and returns `NXDOMAIN`. |
| **7** | **Default VPC `.2` Public Recursion** | Resolves against public authoritative DNS (`PUBLIC`). |

---

## 2. Read-Only MCP Data Collection (`aws-mcp` `aws___run_script` & `awsnetwork`)

Execute **all** AWS control-plane reads through connected MCP tools (`aws-mcp` `aws___run_script` using `await call_boto3(...)`, plus `awsnetwork` `list_vpcs` / `get_vpc_network`). **Never** run raw `aws` CLI commands in the shell, and never mutate VPC, Route 53, or SSM resources.

### Mode A & Mode B Control-Plane Inspection (`call_boto3` Allowlist)

1. **VPC Attributes & DHCP Option Set (`ec2`):**
   - `DescribeVpcs(VpcIds=[vpc_id])` -> `CidrBlock`, `Ipv6CidrBlockAssociationSet`, `DhcpOptionsId`.
   - `DescribeVpcAttribute(VpcId=vpc_id, Attribute="enableDnsSupport")` and `DescribeVpcAttribute(VpcId=vpc_id, Attribute="enableDnsHostnames")` (**Note:** `DescribeVpcs` does NOT return `EnableDnsSupport`/`EnableDnsHostnames` — you MUST call `DescribeVpcAttribute` twice!).
   - `DescribeDhcpOptions(DhcpOptionsIds=[dhcp_id])` -> inspect `domain-name-servers` (`AmazonProvidedDNS` vs custom resolver IPs).
2. **Instance & SSM Preconditions (Mode A only — `ec2`, `ssm`):**
   - `DescribeInstances(InstanceIds=[instance_id])` -> `VpcId`, `SubnetId`, IPv4 vs IPv6-only addressing, IAM Instance Profile.
   - `DescribeInstanceInformation(Filters=[{"Key": "InstanceIds", "Values": [instance_id]}])` (`ssm`) -> verify `PingStatus == "Online"`. Check `DescribeVpcEndpoints` for `ssm`, `ssmmessages`, and `ec2messages` Interface Endpoints in the instance's AZ (`EC2 Instance Connect Endpoint` is **not** a substitute for SSM!).
   - In strict read-only environments (`aws-mutation-gate.py`), `ssm:SendCommand` is a gated execution API: never invoke `SendCommand` unprompted; instead verify all control-plane DNS preconditions + SSM reachability via MCP and provide the exact read-only `dig` / `resolvectl` verification commands (`dig @169.254.169.253 <name> A`, `dig @fd00:ec2::253 <name> AAAA`, `dig @<resolver> CHAOS TXT hostname.bind`) if in-guest probing is needed.
3. **Effective VPC DNS Configuration (Direct + Route 53 Profile Union):**
   - **Route 53 Profiles (`route53profiles`):** `ListProfileAssociations(ResourceId=vpc_id)` -> for each associated `ProfileId`, call `ListProfileResourceAssociations(ProfileId=profile_id)` to discover inherited PHZs, Resolver rules, and DNS Firewall rule groups (`source = f"profile:{profile_id}"`). Note: Route 53 Profile changes propagate asynchronously in **~300–350s (up to 900s worst-case with negative caching)**.
   - **DNS Firewall (`route53resolver`):** `ListFirewallRuleGroupAssociations(VpcId=vpc_id)` + Profile firewall groups -> `ListFirewallRules` -> `ListFirewallDomains` (if `AccessDenied`, mark `opaque=True`).
   - **Resolver Rules (`route53resolver`):** `ListResolverRuleAssociations(Filters=[{"Name": "VPCId", "Values": [vpc_id]}])` + Profile rules -> `GetResolverRule` (if `AccessDenied` on cross-account rule, mark `opaque=True`).
   - **Interface VPC Endpoints & VPC Lattice (`ec2`, `vpclattice`):** `DescribeVpcEndpoints(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])` (`VpcEndpointType == "Interface"`, `PrivateDnsEnabled`, `DnsEntries`) and `ListServiceNetworkVpcAssociations(vpcIdentifier=vpc_id)` (`dnsOptions.privateDnsPreference`).
   - **Private Hosted Zones (`route53`):** `ListHostedZonesByVPC(VPCId=vpc_id, VPCRegion=region)` + Profile PHZs -> `ListResourceRecordSets` (when readable in-account) to build the candidate FQDN set.

---

## 3. Symbolic Mode B Change Simulation Inside `aws___run_script`

When evaluating a proposed DNS change (`enable_vpce_private_dns`, `associate_phz`, `add_resolver_rule`, `associate_dns_firewall`, `associate_profile`, or `update_snva_preference`):
1. Build the current `EffectiveModel` from live MCP reads (or the user's stated architecture) and assemble the **candidate FQDN set** (all PHZ record names, Resolver rule domains, VPCE service FQDNs, plus operator-supplied hostnames).
2. Run the 7-level precedence function on every candidate name **before** and **after** applying the proposed change inside `aws___run_script`.
3. Flag any transition where a currently-resolving name shifts to `NXDOMAIN`, `BLOCKED`, `OPAQUE`, or unintended `ONPREM` / `PUBLIC` bypass, and map it to the canonical Mode B trap (`VPCE-shadow-NXDOMAIN`, `broad-FORWARD-sweep`, `flag-AND-mismatch`, `DNS-Firewall-block`, `profile-union-shift`).
4. Label all symbolic simulation outputs **`Predicted`** (never `Observed`), state the exact candidate-set count and source, and disclose that names outside the candidate set were not evaluated.
