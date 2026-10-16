# Hybrid Connectivity, Direct Connect & BGP Traffic Engineering Reference (SAP-C02)

## 1. High-Availability Hybrid Connectivity Topology (99.99% SLA)

To achieve the **99.99% Direct Connect SLA**, a production hybrid architecture must provision:
- **At least 2 Direct Connect Locations** (diverse physical facilities) with **2 Customer Routers** per location (4 total connections) terminating into a **Direct Connect Gateway (DXGW)** connected to an **AWS Transit Gateway (TGW)** via a **Transit VIF**.
- For single-DX-location deployments with a **Site-to-Site VPN backup** terminating on the same Transit Gateway:
  - AWS Transit Gateway always prefers **Direct Connect routes over VPN BGP routes** when both advertise the **exact same CIDR prefix length** (`/16` vs `/16`).
  - **Critical SAP-C02 Gotcha (Longest Prefix Match)**: If the VPN advertises a *more specific* prefix (e.g., `10.1.0.0/24`) while Direct Connect advertises a summary route (`10.0.0.0/16`), traffic will take the slower VPN! Always advertise identical prefix lengths on DX and backup VPN so DX wins automatically and fails over seamlessly to VPN.

## 2. BGP Path Selection & AWS Direct Connect BGP Communities

### Inbound to AWS (On-Premises $\rightarrow$ AWS)
Control which DX connection on-premises routers prefer using:
1. **BGP `Local_Pref`** on customer routers (highest wins), or
2. **BGP `AS_PATH` Prepending** on passive DX connections, or
3. **AWS BGP Local Preference Communities** attached to prefixes advertised *to* AWS:
   - `7224:7100` — **Low** preference
   - `7224:7200` — **Medium** preference
   - `7224:7300` — **High** preference (Active primary link for AWS $\rightarrow$ On-Premises return traffic!)

### Outbound from AWS (AWS $\rightarrow$ On-Premises)
AWS evaluates return paths in this order:
1. **Most specific prefix match** (Longest Prefix Match — e.g., `/24` beats `/16`).
2. **BGP Local Preference Community** (`7224:7300` > `7224:7200` > `7224:7100`).
3. **Same-region / Home-region DX location preference**.
4. **Shortest `AS_PATH`**.
5. **Lowest `MED` (Multi-Exit Discriminator)**.

### Scope Control Communities (For Public VIFs)
- `7224:9100` — Advertise only within the **local AWS Region**.
- `7224:9200` — Advertise to **all AWS Regions within the same continent** (North America / Europe / Asia).
- `7224:9300` — Global (all public AWS Regions).

## 3. Encryption Over Direct Connect (MACsec vs. IPsec Site-to-Site VPN over Transit VIF)
- **IEEE 802.1AE MACsec**: Layer-2 point-to-point hardware encryption on Dedicated 10 Gbps / 100 Gbps / 400 Gbps Direct Connect ports between the customer router and the AWS DX device.
- **Site-to-Site VPN over Direct Connect**: Terminate an IPsec VPN tunnel onto a Transit Gateway over a **Public VIF** (or Private/Transit VIF where supported) for end-to-end Layer-3 encryption into the VPC, using **ECMP (Equal-Cost Multi-Path)** across multiple VPN tunnels to scale beyond the single-tunnel `1.25 Gbps` IPsec limit.
