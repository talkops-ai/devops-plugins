# Direct Connect Read-Only MCP Data Collection & Exact `ipaddress` CIDR Coverage Engine

This reference provides the portable, open-source MCP execution implementation for `dx-vif-resilience` using **`aws-mcp` (`aws___run_script`)** so both live AWS Direct Connect route collection and exact CIDR containment / residual set-difference math run deterministically inside the MCP sandbox — **zero mental CIDR arithmetic, zero shell `run_command` calls, and zero dependency on external Lambda Function URLs**.

---

## 1. Read-Only `directconnect` API Allowlist (`aws-mcp` `aws___run_script`)

Only these read-only operations may be invoked via `await call_boto3(service_name="directconnect", ...)`:
1. **`DescribeConnections`** -> `connectionId`, `connectionName`, `connectionState`, `location`, `bandwidth`, `awsLogicalDeviceId`, `lagId`, `partnerName`.
2. **`DescribeLags`** -> verify LAG membership (remember: **a LAG is one logical connection; a VIF on a LAG is still one VIF and does NOT provide Layer-3 VIF redundancy**).
3. **`ListResiliencyGroups`** / **`DescribeResiliencyGroups`** (when supported in region) -> check declared Tier-1 connection redundancy and verify `PortPairFlatRateTier*` vs broken `FlatRateTier*` pairing.
4. **`DescribeVirtualInterfaces`** -> `virtualInterfaceId`, `virtualInterfaceName`, `virtualInterfaceType` (`private`, `transit`, `public`), `virtualInterfaceState`, `connectionId`, `location`, `awsLogicalDeviceId`, `directConnectGatewayId`, `virtualGatewayId`, `asn`, `amazonSideAsn`, `bgpPeers[]` (`bgpStatus`, `addressFamily`, `bgpPeerState`).
   - **Cross-Account / Hosted VIF Visibility:** If a VIF's `connectionId` does not appear in `DescribeConnections` (owned by a carrier/partner or separate Network account), set `all_vif_connections_visible = False` and report connection-derived checks (resiliency group, LAG) as **`cannot verify (connection owned by another account)`** — never `"none"`. VIF-level `location` and `awsLogicalDeviceId` remain valid!
5. **`DescribeDirectConnectGateways`** & **`DescribeDirectConnectGatewayAssociations`** -> map DXGWs to Transit Gateways / Cloud WAN Core Networks / VGWs and inspect `allowedPrefixesToDirectConnectGateway` (independent per DXGW↔gateway association!).
6. **`ListVirtualInterfaceRoutes`** -> **Paginate `nextToken` to exhaustion** for every BGP-`up` VIF across both `routeDirection` values (`"accepted"` and `"advertised"`). Exclude BGP-`down` VIFs from pairwise set-diff (reporting them separately as a BGP health finding so stale/empty tables don't generate false-positive prefix gaps).

---

## 2. Exact `ipaddress` CIDR Coverage & Residual Algorithm (Run Inside `aws___run_script`)

**Never compute CIDR containment or uncovered residuals mentally.** Run this exact pure-stdlib `ipaddress` logic inside `aws-mcp` `aws___run_script` on either live `ListVirtualInterfaceRoutes` results or operator-supplied VIF prefix tables:

```python
import ipaddress

DEFAULT_ROUTES = {"0.0.0.0/0", "::/0"}

def residual_cidrs(supernet, more_specifics):
    remaining = [supernet]
    for sub in ipaddress.collapse_addresses(more_specifics):
        nxt = []
        for chunk in remaining:
            if sub.subnet_of(chunk):
                nxt.extend(chunk.address_exclude(sub))
            elif chunk.subnet_of(sub):
                continue
            else:
                nxt.append(chunk)
        remaining = nxt
    return [str(n) for n in sorted(ipaddress.collapse_addresses(remaining))]

def classify_prefix_against_peer(prefix, peer_nets):
    # 1. Exact match or containing supernet on peer -> COVERED
    for net in peer_nets:
        if net.version == prefix.version and prefix.subnet_of(net):
            return {"status": "covered", "covered_by": str(net)}
    # 2. Strictly more-specific subnets inside prefix on peer -> check exact tiling vs residual
    inside = [n for n in peer_nets if n.version == prefix.version and n != prefix and n.subnet_of(prefix)]
    if inside:
        res = residual_cidrs(prefix, inside)
        if not res:
            return {"status": "covered", "tiled_by": [str(n) for n in sorted(ipaddress.collapse_addresses(inside))]}
        return {
            "status": "partial_supernet",
            "covered_subnets": [str(n) for n in sorted(ipaddress.collapse_addresses(inside))],
            "uncovered_residual": res,
        }
    # 3. Zero coverage -> GAP (guaranteed blackhole on failover)
    return {"status": "gap"}
```

### Critical Classification Rules Enforced by This Engine
1. **Default Routes (`0.0.0.0/0`, `::/0`) Are Separated First:** Record which VIFs advertise/accept a default route (`default_route_present`), and **exclude** `0.0.0.0/0` / `::/0` from `peer_nets` during prefix coverage checks so a default route NEVER masks missing specific prefixes!
2. **Exact Tiling = `covered`:** If VIF-A advertises `10.20.0.0/23` and VIF-B advertises both `10.20.0.0/24` and `10.20.1.0/24`, `residual_cidrs` returns `[]` -> status is **`covered`**, not `partial_supernet`.
3. **Partial Supernet Residual (`partial_supernet`):** If VIF-B advertises `10.10.0.0/22` and VIF-A advertises only `10.10.1.0/24`, `uncovered_residual` is **`['10.10.0.0/24', '10.10.2.0/23']`** — conditional severity (ask whether active workloads live in the residual subnets).
4. **Pairwise Directional Failover Impact:** For each VIF `X` in the redundant set, list the exact prefixes (`gaps` + `uncovered_residual`) that blackhole if `X` fails: *"If `dxvif-aaa` fails, traffic to `<prefixes>` in `<accepted|advertised>` direction is blackholed."*
