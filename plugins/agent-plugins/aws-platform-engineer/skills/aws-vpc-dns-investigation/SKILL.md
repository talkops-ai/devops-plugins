---
name: aws-vpc-dns-investigation
description: Use this skill when a name is not resolving as expected inside an Amazon VPC, or before applying a DNS control-plane change. Activate on symptoms such as NXDOMAIN, SERVFAIL, or DNS timeouts from an EC2 instance or container, a hostname resolving to a public IP when a PrivateLink endpoint IP was expected, an AWS service FQDN that stopped resolving after a VPC endpoint or Route 53 change, resolution that works from one instance/subnet but not another, IPv6 or dualstack A vs AAAA resolution differences, hybrid on-premises forwarding collisions, or pre-change blast-radius validation before enabling Interface Endpoint private DNS, adding a Route 53 Resolver FORWARD/SYSTEM rule, associating a Private Hosted Zone, attaching DNS Firewall, configuring VPC Lattice private DNS, or associating a Route 53 Profile.
metadata:
  author: ddericco
  version: "1.1.0"
  aws-devops-agent-skills.agent-types: "CHAT, INCIDENT_RCA"
  aws-devops-agent-skills.aws-services: "Amazon VPC, Amazon Route 53, Amazon EC2, AWS Systems Manager"
  aws-devops-agent-skills.technical-domains: "Networking"
---

# Investigate Amazon VPC DNS Resolution & Pre-Change Blast Radius

Diagnose live VPC DNS resolution failures (**Mode A — Reactive Diagnosis**) and symbolically simulate proposed DNS control-plane changes before they break production (**Mode B — Predictive Pre-Change Validation**).

## Execution & MCP-Only Guardrail Rules (Mandatory)

1. **Strictly Read-Only & MCP-Only Execution:** Execute **all** live AWS discovery, VPC attribute checks, Route 53 / Resolver / Profile / VPC Lattice inspections, and symbolic precedence simulations **exclusively via connected MCP servers** (`aws-mcp` `aws___run_script` using read-only `call_boto3`, `awsnetwork` `list_vpcs` / `get_vpc_network`, and `cloudtrail` `lookup_events`). **Never** shell out to raw `aws` CLI commands or `python3 -c` in Bash/`run_command`, and **never** create, modify, or delete DNS/VPC resources or run mutating `ssm:SendCommand` calls. Whenever refusing a request to mutate live VPC/DNS settings (such as `ec2:ModifyVpcAttribute --no-enable-dns-support` or `route53resolver:DisassociateResolverRule`), explicitly warn of the blast radius **and mandate running a Mode B pre-change blast-radius simulation** before any DNS change is approved or applied. (If an enterprise environment additionally registers the optional `aws-vpc-dns-diagnostics` MCP server, its read-only tools may also be used; never block or abort when it is absent — run the full control-plane inspection and symbolic 7-level precedence simulation directly via `aws-mcp` `aws___run_script`.)
2. **Load Local References Before Diagnosing or Simulating:**
   - Read [references/dns-precedence-and-simulation-engine.md](references/dns-precedence-and-simulation-engine.md) for the **7-level VPC DNS precedence stack**, exact `call_boto3` read-only API sequence (including mandatory `DescribeVpcAttribute` calls for `enableDnsSupport` and `enableDnsHostnames`), Route 53 Profile union logic, and symbolic simulation engine.
   - Read [references/mode-a-and-b-trap-playbooks.md](references/mode-a-and-b-trap-playbooks.md) for all **Mode A & Mode B trap signatures**, SSM vs EICE boundaries, `OPAQUE` cross-account construct rules, and mandatory reporting requirements.
3. **`awsknowledge` Fallback for Unmapped Edge Cases:** If a niche AWS DNS feature (e.g., Route 53 Resolver DNSSEC validation, Outposts Resolver, delegated resolver endpoints) is not covered in `references/*.md`, immediately query the `awsknowledge` / `aws-mcp` documentation tools (`aws___search_documentation` / `aws___read_documentation` — 1–2 focused searches) and answer directly.

---

## Step 1: Classify the Request (Mode A, Mode B, or Clarify)

Before calling AWS APIs, classify the operator's intent:

- **Mode A (Live / Reactive Diagnosis):** Operator reports an active resolution symptom (`NXDOMAIN`, `SERVFAIL`, timeout, wrong public IP instead of PrivateLink IP, A vs AAAA mismatch) for a specific VPC/subnet/instance and failing DNS name.
- **Mode B (Predictive Pre-Change Validation):** Operator asks *"What will break if we enable `PrivateDnsEnabled`, add a `FORWARD` rule, associate a PHZ, attach DNS Firewall, configure VPC Lattice private DNS, or associate a Route 53 Profile?"* No EC2 instance is required.
- **Ambiguous / Missing Scope:** If a live symptom lacks target VPC/instance/hostname context (and discovery in the requested region finds multiple VPCs or zero matching instances), inspect the region's VPCs in read-only mode via `aws-mcp` (`aws___run_script`) or `awsnetwork`, report what exists honestly without fabricating ARNs, and ask for the missing identifier alongside explaining the governing precedence rule.

---

## Step 2: Mode A Workflow — Reactive VPC DNS Diagnosis

1. **Inspect Preconditions First (`aws___run_script`):**
   - Query `ec2:DescribeVpcs`, `ec2:DescribeVpcAttribute(Attribute="enableDnsSupport")`, `ec2:DescribeVpcAttribute(Attribute="enableDnsHostnames")`, and `ec2:DescribeDhcpOptions`.
   - If **`enableDnsSupport=false`**, stop chasing routing/SGs — the VPC resolver is intentionally dark (`A-resolver-disabled-precondition`).
   - If PrivateLink Private DNS or a PHZ is not resolving while public DNS works, check **`enableDnsHostnames`** — both flags must be `true`!
   - Check instance/subnet **address family**: in an IPv6-only subnet `169.254.169.253` does not exist; only **`fd00:ec2::253`** answers (`A-address-family-divergence`).
   - Compare DHCP Option Set `domain-name-servers` (`AmazonProvidedDNS` vs custom IPs — `A-custom-resolver-divergence`).
2. **Inventory Effective VPC DNS Stack (`aws___run_script`):**
   - Collect direct + **Route 53 Profile**-inherited DNS Firewall rule groups, Resolver `FORWARD`/`SYSTEM` rules, Interface VPC Endpoints (`PrivateDnsEnabled`, `DnsEntries`), VPC Lattice `SNVA` `PrivateDnsPreference`, and associated Private Hosted Zones (`ListHostedZonesByVPC`).
   - Check recent DNS control-plane changes via `cloudtrail` (`lookup_events`) when an endpoint "suddenly stopped resolving".
3. **Evaluate SSM In-Guest Probe Preconditions (Read-Only):**
   - Check `ssm:DescribeInstanceInformation` and verify `ssm`, `ssmmessages`, and `ec2messages` Interface VPC Endpoints exist for private subnets. Explicitly note that an **EC2 Instance Connect Endpoint (EICE)** cannot carry SSM Run Command traffic. Provide exact read-only `dig` commands (`dig @169.254.169.253 <fqdn> A`, `dig @<resolver> CHAOS TXT hostname.bind`) for operator verification without executing mutating `SendCommand`.
4. **Match Trap Signature & Judge by Name Category:**
   - Apply [references/mode-a-and-b-trap-playbooks.md](references/mode-a-and-b-trap-playbooks.md) (`A-forward-vs-phz-precedence-collision` when a `FORWARD` rule at Level 2 overrides a PHZ at Level 5 causing timeouts; `VPCE-shadow-NXDOMAIN` when an Interface Endpoint shadow PHZ returns `NXDOMAIN` for unserved sibling subdomains).

---

## Step 3: Mode B Workflow — Pre-Change Symbolic Blast-Radius Simulation

Never approve a DNS control-plane change without evaluating all **7 precedence levels**:
`0: enableDnsSupport` -> `1: DNS Firewall` -> `2: Resolver FORWARD (most-specific)` -> `3: Resolver SYSTEM (most-specific)` -> `4: VPCE / Lattice Shadow PHZ (+ SNVA PrivateDnsPreference gate)` -> `5: Associated PHZ` -> `6: Unforwarded on-prem zone` -> `7: VPC .2 public recursion`.

1. **Collect Effective Config (Direct + Route 53 Profile Union)** via `aws-mcp` `aws___run_script` for the target VPC. Tag every construct with `source` (`direct` vs `profile:<id>`). Mark cross-account unreadable Resolver rules or RAM/Managed Firewall domain lists as **`OPAQUE`** (`present, match set unknown` — never assume empty/inert!).
2. **Build Candidate Name Set & Simulate Delta in `aws___run_script`:**
   - Evaluate candidate FQDNs (PHZ records, rule domains, VPCE service apexes, critical AWS endpoints like `sts`, `s3`, `ecr.api`, `ecr.dkr`, `logs`, `oidc.eks`, plus operator-supplied names) before and after the proposed change.
   - Check all 5 Mode B traps from [references/mode-a-and-b-trap-playbooks.md](references/mode-a-and-b-trap-playbooks.md):
     1. **`VPCE-shadow-NXDOMAIN`** (authoritative shadow PHZ breaking unserved strict subdomains under `service_apex`).
     2. **`broad-FORWARD-sweep`** (`.` or `amazonaws.com` `FORWARD` rule hijacking PrivateLink/PHZ/AWS FQDNs without `SYSTEM` carve-outs).
     3. **`flag-AND-mismatch`** (VPC Lattice `privateDnsEnabled` × `SNVA` `PrivateDnsPreference` AND-gate, misleading `privateDnsEntry.domainName`, and create-only replacement requirement).
     4. **`DNS-Firewall-block`** (priority ordering / wildcard `BLOCK` rules).
     5. **`profile-union-shift`** (Profile-inherited overrides + **300–900s asynchronous propagation window**).

---

## Mandatory Final Response Contract

Every response produced by this skill MUST include:
1. **Explicit Evidence Labels:** Label every finding **`Observed`** (verified from live MCP reads or operator probe output) or **`Predicted`** (derived from symbolic 7-level precedence simulation). State **"Mode A wins"** whenever live observation and symbolic prediction are compared.
2. **Winning Precedence Level & Construct:** Name the exact level (0–7), construct ID, and `source` (`direct` vs `profile:<id>`) governing each evaluated hostname.
3. **Coverage & Opacity Disclosure:** State the exact candidate-set count and provenance, warn that names outside the candidate set (and application/JVM DNS caches) are untested, and surface any **`OPAQUE`** cross-account constructs honestly.
4. **Safe Remediation & Read-Only Verification:** Provide copy-pasteable IaC / read-only verification steps without executing live mutations.
