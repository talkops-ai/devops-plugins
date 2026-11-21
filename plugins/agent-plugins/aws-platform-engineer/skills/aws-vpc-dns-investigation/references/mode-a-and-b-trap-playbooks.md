# VPC DNS Diagnostic Trap Playbooks (Mode A, Mode B & Opaque Boundaries)

Load this reference to classify observed DNS resolution symptoms (Mode A), predicted pre-change blast-radius traps (Mode B), cross-account opacity (`OPAQUE`), and reporting boundaries.

---

## 1. Critical Safety Rules (Mandatory for All Recommendations)

1. **Never Recommend a DNS Change Without Simulating Blast Radius First (Mode B):** Any change to VPC Endpoint `PrivateDnsEnabled`, a Route 53 Resolver `FORWARD`/`SYSTEM` rule, a Private Hosted Zone association, a DNS Firewall rule group, or a Route 53 Profile association can silently redirect or `NXDOMAIN` currently working workloads across the entire VPC.
2. **Resolver Agreement Is NOT the Goal — Category Correctness Is:**
   - **On-prem / corporate zone (`corp.internal`):** Custom/forwarded resolver *should* answer and raw VPC `.2` (without `FORWARD`) *should* `NXDOMAIN`.
   - **AWS service FQDN with PrivateLink (`secretsmanager.<region>.amazonaws.com`):** VPC `.2` *should* return private ENI IPs while an unintegrated custom resolver returns public IPs (breaking private-only subnets!). Judge every answer by **name category**, never by whether two resolvers agree.
3. **Check VPC Attribute Preconditions First:** Always inspect `enableDnsSupport` and `enableDnsHostnames` before diagnosing security groups, NACLs, or routing. PrivateLink Private DNS (`PrivateDnsEnabled=true`) and Private Hosted Zones require **both** `enableDnsSupport=true` AND `enableDnsHostnames=true`.
4. **Never Route Around Missing SSM via Public Internet or EICE:** In-guest DNS probing via SSM Run Command requires `AmazonSSMManagedInstanceCore` plus private reachability to all **three** Interface VPC Endpoints: `ssm`, `ssmmessages`, and `ec2messages`. An **EC2 Instance Connect Endpoint (EICE)** is an *inbound* SSH/RDP tunnel and carries **zero** outbound SSM agent control-plane traffic — an instance with EICE alone stays `ConnectionStatus: Not connected` in SSM.
5. **Respect Subnet Address Family:** In an **IPv6-only subnet**, `169.254.169.253` does not exist; only **`fd00:ec2::253`** answers. Timing out against `169.254.169.253` from an IPv6-only instance is expected behavior, never a resolver fault.

---

## 2. Mode A Live Diagnosis Trap Signatures

| Trap Slug | Symptom Signature | Root Cause & Remediation |
| :--- | :--- | :--- |
| **`A-resolver-disabled-precondition`** | All DNS queries to `.2` / `fd00:ec2::253` time out; PHZs, Resolver rules, and PrivateLink DNS all dark. | `enableDnsSupport=false` on the VPC (`DescribeVpcAttribute`). Enable `enableDnsSupport=true` (and `enableDnsHostnames=true` if PHZs or Interface Endpoint Private DNS are used). |
| **`A-custom-resolver-divergence`** | Resolution works on one EC2 instance and fails on another, or PrivateLink/PHZ names resolve to public IPs / `NXDOMAIN`. | DHCP Option Set `domain-name-servers` specifies custom on-prem DNS servers instead of `AmazonProvidedDNS`, or `/etc/resolv.conf` / `systemd-resolved` was overridden in-guest. Custom DNS servers cannot see VPC-associated PHZs or PrivateLink private DNS unless they forward back to a Route 53 Resolver Inbound Endpoint. Prefer `AmazonProvidedDNS` + targeted Outbound `FORWARD` rules. |
| **`A-forward-vs-phz-precedence-collision`** | Internal zone (`internal.corp`) **times out** (slow hang) even though an associated PHZ exists in the VPC, while public & AWS names work. | Both a Resolver `FORWARD` rule and a PHZ cover `internal.corp` (or parent `.corp`). **Level 2 `FORWARD` outranks Level 5 PHZ**, sending queries to an unreachable/unauthoritative target IP. Always present **all three safe remediation options** (and run a Mode B simulation before applying): **(1) narrow the `FORWARD` rule** `DomainName` to only the specific on-premises subdomain, **(2) add a more-specific `SYSTEM` carve-out rule** for `internal.corp` (verifying longest-suffix specificity), or **(3) split overlapping namespaces cleanly** (e.g., `onprem.corp` vs `internal.corp`). |
| **`A-address-family-divergence`** | `A` record resolves cleanly while `AAAA` returns empty `NOERROR` (`NODATA`), or `AAAA`-only client fails. | Distinguish **zone data gap** (PHZ only holds `A` records, returning `NODATA` for `AAAA` — normal unless client lacks `AI_ADDRCONFIG` / Happy Eyeballs) vs **IPv6-only subnet** (`169.254.169.253` absent, use `fd00:ec2::253`) vs **IPv4-only VPC Endpoint** (upgrade endpoint to `IpAddressType: dualstack`). |

---

## 3. Mode B Pre-Change Validation Trap Signatures

| Trap Label | Triggering Change | Blast Radius & Remediation |
| :--- | :--- | :--- |
| **`VPCE-shadow-NXDOMAIN`** | Enabling `PrivateDnsEnabled=true` on an Interface VPC Endpoint or VPC Lattice shadow. | Installs an authoritative shadow PHZ over `service_apex`. Exact apex and `served_names` resolve to private ENI IPs, **but every other strict subdomain under that apex now returns `NXDOMAIN`** instead of falling through to public DNS (breaking sibling endpoints, regional/OIDC/bootstrap aliases under the same parent domain). Fix: use an unshadowed alternate FQDN, keep `PrivateDnsEnabled=false` and address endpoint DNS explicitly, or add targeted records/rules. |
| **`broad-FORWARD-sweep`** | Adding a Resolver `FORWARD` rule for `.` (root) or broad `amazonaws.com`. | Sweeps AWS service FQDNs (`*.amazonaws.com`, `*.api.aws`), PrivateLink Private DNS, and associated PHZs off to on-prem DNS (causing timeouts or public-IP hairpinning bypassing VPC Endpoints!). Fix: narrow `FORWARD` rules to specific corporate domains (`corp.example.com`), or if `.` forwarding is mandatory, add explicit **`SYSTEM` carve-out rules** for `amazonaws.com`, `api.aws`, and **every** associated PHZ domain. |
| **`flag-AND-mismatch`** | Publishing custom domains over **Amazon VPC Lattice** (`ResourceConfiguration` / Service Network). | Lattice custom-domain private DNS requires **two independent create-only flags AND-ed together**: (1) `privateDnsEnabled=true` on the Service Network Resource Association AND (2) compatible `dnsOptions.privateDnsPreference` (`VERIFIED_DOMAINS_ONLY`, `SPECIFIED_DOMAINS_ONLY` + `specifiedDomains`, or `ALL_DOMAINS`) on the Service Network VPC Association (`SNVA`). Note: `privateDnsEntry.domainName` is populated even when `privateDnsEnabled=false` (misleading!), and both flags are **immutable create-only** (requiring resource replacement / new CloudFormation logical ID). |
| **`DNS-Firewall-block`** | Associating a Route 53 DNS Firewall rule group (directly or via Profile) without auditing `Priority` & `Action=BLOCK`. | Lowest numeric `Priority` wins; an overly broad wildcard block list (`*.amazonaws.com` or missing high-priority `ALLOW` rule) blocks critical control-plane/data-plane endpoints (`NXDOMAIN` / `NODATA` / `OVERRIDE`). Test in `ALERT` mode before switching to `BLOCK`. |
| **`profile-union-shift`** | Associating/modifying a **Route 53 Profile** (`AWS::Route53Profiles::ProfileAssociation`). | Effective VPC DNS becomes the **union** of direct VPC associations and Profile-inherited PHZs, Resolver rules, and DNS Firewall groups. Inherited `FORWARD` or Firewall rules can override direct PHZs! Also warn that Profile changes propagate asynchronously (**300–350s typical, up to 900s worst-case** with negative TTL caching). |

---

## 4. Cross-Account Opacity (`OPAQUE`) & Mandatory Reporting Format

- **Cross-Account `OPAQUE` Constructs:** Resources shared via AWS RAM or a cross-account Route 53 Profile (such as a shared Resolver `FORWARD` rule where `GetResolverRule` returns `AccessDenied`, or a RAM-shared / AWS Managed DNS Firewall domain list where `ListFirewallDomains` is unreadable) are enumerable as *associated* with the VPC, but their internal match list cannot be read from the consumer account. **Never treat unreadable constructs as empty/safe** — classify affected predictions as **`OPAQUE` (`present, match set unknown`)** and instruct inspecting from the owning Network/Security account.
- **Mode A Wins Over Mode B:** Mode A observes actual subnet resolution (`Observed`); Mode B models documented control-plane precedence (`Predicted`). Whenever Mode A and Mode B disagree, **Mode A is ground truth** and the discrepancy itself signals an undocumented behavior, in-guest override (`/etc/hosts`, local cache), or an `OPAQUE` construct.
- **Required Output Checklist:** Every response MUST explicitly state:
  1. Evidence labels on every finding: **`Observed`** (live MCP API / probe truth) vs **`Predicted`** (symbolic Mode B model).
  2. Conflict precedence rule (**"Mode A wins"** when comparing live vs predicted).
  3. **Candidate-set coverage boundary**: exact count of names evaluated, their source (API-derived vs operator-supplied), and that names outside this set ( plus JVM/sidecar DNS caches) were not evaluated.
  4. Any **`OPAQUE`** cross-account / Managed constructs and their impact.
  5. Concrete read-only verification and safe remediation steps (never executing mutations).
