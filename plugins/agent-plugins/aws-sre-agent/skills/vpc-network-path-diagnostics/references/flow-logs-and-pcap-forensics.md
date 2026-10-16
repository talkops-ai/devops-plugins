# VPC, TGW & Network Firewall Flow Log Forensics Reference

## 1. TCP Flags Bitmask Decoder (`tcp-flags` in VPC Flow Logs v3+)

| Bitmask Value | Flag(s) Set | Operational Meaning |
|---|---|---|
| **`2`** | `SYN` | Connection initiation attempt. If `action="ACCEPT"` on egress but no corresponding `SYN-ACK` (`18`) returns, routing or a downstream stateless NACL/firewall dropped the packet. |
| **`4`** | `RST` | Connection reset. Target port has no listening process, or AWS Network Firewall / proxy injected a TCP reset. |
| **`18`** | `SYN` + `ACK` | Server accepted the handshake. |
| **`1`** / **`17`** | `FIN` / `FIN+ACK` | Normal connection teardown. |

---

## 2. CloudWatch Logs Insights Queries for VPC Flow Logs

### Top Rejected Source/Destination Pairs & Ports
```sql
fields @timestamp, interfaceId, srcAddr, dstAddr, srcPort, dstPort, protocol, action, tcpFlags
| filter action = "REJECT"
| stats count(*) as rejectedPackets by srcAddr, dstAddr, dstPort, protocol
| sort rejectedPackets desc
| limit 25
```

### Detect NAT Gateway or PrivateLink Data-Volume Spikes (`bytes` Transferred)
```sql
fields srcAddr, dstAddr, dstPort, bytes
| filter action = "ACCEPT"
| stats sum(bytes)/1073741824 as totalGiB by srcAddr, dstAddr, dstPort
| sort totalGiB desc
| limit 25
```

### Trace Asymmetric or Hairpin Traffic Using v5Original Packet Fields (`pkt-srcaddr`, `pkt-dstaddr`)
```sql
fields @timestamp, interfaceId, srcAddr, dstAddr, `pkt-srcaddr`, `pkt-dstaddr`, srcPort, dstPort, action, `flow-direction`
| filter `pkt-srcaddr` = "10.1.14.25" or `pkt-dstaddr` = "10.1.14.25"
| sort @timestamp desc
| limit 100
```
