---
name: dx-vif-resilience
description: >
  Assess Layer-3 (BGP prefix) failover resilience across redundant AWS Direct
  Connect virtual interfaces (VIFs). Use when the user asks whether their Direct
  Connect setup is resilient, whether failover will work, whether the same
  routes/prefixes are advertised across redundant VIFs, why traffic was lost
  after a VIF or connection failure, to audit DX BGP route symmetry, or about
  Direct Connect VIF fast-failover BFD timers and SiteLink inter-POP VIF
  resilience. Checks both directions (accepted routes from on-prem and advertised
  routes from AWS) using read-only Direct Connect APIs and deterministic
  ipaddress CIDR containment/residual math via connected MCP tools.
metadata:
  version: "1.1.0"
  author: abed-kayyali
  summary: Audit Layer-3 failover coverage across redundant Direct Connect VIFs — deterministic BGP prefix-symmetry analysis in both directions.
  aws-devops-agent-skills.agent-types: "CHAT"
  aws-devops-agent-skills.aws-services: "AWS Direct Connect"
  aws-devops-agent-skills.technical-domains: "Networking"
---

# Direct Connect VIF Resilience Assessment (Layer 3 / BGP Prefix Coverage)

## Problem This Skill Solves

High availability on AWS Direct Connect is customer-managed at the BGP layer. AWS does not enforce that equivalent prefixes are advertised across redundant VIFs. If a prefix is reachable via `VIF-A` but has zero or partial coverage on `VIF-B`, traffic to uncovered CIDRs is **silently blackholed** during a real failover — even when physical Layer-1/2 diversity is perfect.

This skill audits **Layer-3 BGP prefix symmetry in both directions** (`accepted`: on-prem → AWS; `advertised`: AWS → on-prem) alongside VIF-visible **physical diversity** (`awsLogicalDeviceId` device diversity AND DX `location` site diversity, reported independently).

## Hard Constraints & MCP-Only Execution

1. **Strictly Read-Only & MCP-Only Execution:** Execute **all** AWS Direct Connect discovery (`DescribeConnections`, `DescribeLags`, `DescribeVirtualInterfaces`, `DescribeDirectConnectGateways`, `DescribeDirectConnectGatewayAssociations`, `ListVirtualInterfaceRoutes`) AND deterministic Python `ipaddress` CIDR set-difference calculations **exclusively via connected MCP tools** (`aws-mcp` `aws___run_script`, plus `awsnetwork` when inspecting attached TGWs/Cloud WAN). (If an enterprise environment additionally mounts `dx-resilience-mcp`, its read-only tools may also be called; never fail or abort when `dx-resilience-mcp` is absent — run the exact engine in [references/cidr-coverage-and-mcp-collection.md](references/cidr-coverage-and-mcp-collection.md) inside `aws-mcp` `aws___run_script`.) **Never** run raw `aws` CLI or `python3 -c` commands in Bash/`run_command`, and **never** create, modify, delete, or trigger BGP failover tests.
2. **Never Do CIDR Coverage Math Mentally:** Always execute exact `ipaddress` containment and `address_exclude` residual math inside `aws___run_script` per [references/cidr-coverage-and-mcp-collection.md](references/cidr-coverage-and-mcp-collection.md).
3. **`awsknowledge` Fallback for Unmapped Edge Cases:** If a question involves niche Direct Connect features outside local references (e.g., MACsec key-chain/CKN/CAK rotation, SiteLink inter-POP routing, BFD timer minimums), immediately query `awsknowledge` / `aws-mcp` (`aws___search_documentation` / `aws___read_documentation` — 1–2 focused searches) and answer directly.

---

## Key Domain Invariants (Load References First)

Read [references/cidr-coverage-and-mcp-collection.md](references/cidr-coverage-and-mcp-collection.md), [references/dx-bgp-resilience-concepts.md](references/dx-bgp-resilience-concepts.md), and [references/report-template.md](references/report-template.md) before rendering findings:

- **Two Mandatory Directions:**
  - `accepted` (on-prem → AWS): missing prefix means AWS cannot reach that on-prem subnet after primary VIF failure.
  - `advertised` (AWS → on-prem): critical in **multi-DXGW** topologies where each DXGW↔TGW/VGW association has its own independent `allowedPrefixesToDirectConnectGateway` list.
- **CIDR-Aware Classification (Never String Equality):**
  - `covered`: exact match, containing supernet on peer, OR more-specifics on peer that **completely tile** the supernet (`residual == []`).
  - `partial_supernet`: supernet on one VIF only partially covered by more-specifics on peer (e.g., `10.10.0.0/22` vs `10.10.1.0/24` → exact uncovered residual `10.10.0.0/24`, `10.10.2.0/23`). Conditional severity — ask whether active workloads reside in the residual CIDRs.
  - `gap`: zero exact, supernet, or subnet match on peer → **guaranteed blackhole on failover** (`🚨 Highest Risk`).
  - `default_route_present` (`0.0.0.0/0`, `::/0`): report separately and **never** allow a default route to suppress specific prefix gap/residual findings!
- **Intentional BGP Traffic Engineering Is NOT a Gap:** Identical prefixes with different `AS_PATH` prepending, `MED`, or DX local-preference communities (`7224:7300` High / `7224:7200` Medium / `7224:7100` Low) represent deliberate active/passive path steering — not a coverage gap.
- **LAG Caveat:** A LAG (`dxcon`/`dxlag`) is **one logical connection**; a single VIF on a LAG provides link redundancy, **not** Layer-3 VIF redundancy.
- **Route-View Convergence Lag (`1–14 minutes`) & Snapshot Timestamp:** `ListVirtualInterfaceRoutes` is eventually consistent after BGP changes. Always **record the exact point-in-time snapshot timestamp (`UTC`)** in the report; if a VIF has BGP `up` but an empty or suspiciously tiny `accepted` table while its peer is full (or right after a route change), flag **both** the empty-VIF failover blackhole risk AND the **1–14 minute convergence-lag caveat**, explicitly recommending **recording the point-in-time snapshot timestamp and re-running the check after ~15 minutes** before declaring newly modified prefixes permanent gaps.
- **Quotas That Mimic Gaps:** Flag route counts near **200 advertised prefixes** (IPv4+IPv6 combined per DXGW↔TGW transit VIF association; 5,000 on Cloud WAN) or **100 accepted prefixes** per BGP family on private/transit VIFs (adjustable to 1,000 via prefix controls; exceeding the limit drops the BGP session `DOWN` rather than silently truncating routes!).

---

## 6-Step Assessment Workflow

1. **Step 1 — Discover the Estate (`aws___run_script`):** Query `DescribeConnections`, `DescribeLags`, `DescribeVirtualInterfaces`, and `DescribeDirectConnectGateways` in the target region (reporting honestly if `0` DX connections/VIFs exist in the account/region without fabricating resources; if the user provided VIF/route payloads directly in the prompt, run the deterministic CIDR engine on those payloads via `aws___run_script`).
2. **Step 2 — Group Redundant VIF Sets by Precedence Tier:**
   - **Tier 1 (Declared Resiliency Groups):** Check `PortPairFlatRateTier*` vs broken `FlatRateTier*` pairing.
   - **Tier 2 (Inferred Intent):** Same DXGW/VGW + same VIF type + same customer ASN (**never** group by route-table overlap — disjoint routes are the exact catastrophic bug this audit catches!).
   - **Tier 3 (Multi-DXGW / Ambiguous):** Present proposed grouping and ask confirmation; flag any lone `available` VIF with `"no redundant peer detected for dxvif-..."`.
3. **Step 3 — Paginate Routes & Run Exact CIDR Analysis (`aws___run_script`):** Exclude BGP-`down` VIFs with a BGP health warning; paginate `ListVirtualInterfaceRoutes` (`nextToken`) for both `accepted` and `advertised`; run the `ipaddress` engine from [references/cidr-coverage-and-mcp-collection.md](references/cidr-coverage-and-mcp-collection.md).
4. **Step 4 — Evaluate Physical Diversity & Cross-Account Visibility Independently:**
   - Report **`device_diverse`** (`awsLogicalDeviceId`) and **`location_diverse`** (DX site/facility) as **two separate findings** — a set on two devices at the *same* DX facility still suffers total outage on a site power/fiber event!
   - For hosted/cross-account VIFs where parent `connectionId` is invisible, report connection-level checks (LAG, resiliency group) as **`cannot verify (connection owned by another account)`**, never `"none"`.
5. **Step 5 — Self-Check Against Deterministic Output:** Verify both `accepted` and `advertised` directions are reported, exact residual CIDRs match `ipaddress` output, default routes did not mask gaps, and convergence-lag + snapshot-time notes are included.
6. **Step 6 — Render Structured Report:** Follow [references/report-template.md](references/report-template.md) with directional pairwise blast radius (*"If `dxvif-X` fails, traffic to `<CIDRs>` is blackholed"*).
