# VPC Path Trace, Reachability Analyzer, and Route 53 DNS Runbook

## 1. Security Groups (Stateful) vs. Network ACLs (Stateless)

| Property | Security Group (SG) | Network ACL (NACL) |
|---|---|---|
| **Boundary** | Elastic Network Interface (`eni-...`) | Entire Subnet (`subnet-...`) |
| **Statefulness** | **Stateful**: Return traffic is automatically permitted regardless of outbound/inbound rules. | **Stateless**: Both the forward request AND the ephemeral return traffic (`TCP 1024–65535`) must be explicitly allowed in inbound and outbound rules. |
| **Rule Evaluation** | Evaluates all `ALLOW` rules; no `DENY` rules exist. | Evaluates rules in strict numeric `RuleNumber` order; first matching rule wins. |

### The Classic Stateless NACL Trap
- Client (`10.0.1.10`) sends HTTPS (`TCP 443`) to Server (`10.0.2.20:443`) from source port `51234`.
- Server responds from `10.0.2.20:443` to `10.0.1.10:51234`.
- If the Client subnet's Inbound NACL only allows `TCP 443` (and blocks `TCP 1024–65535`), the return `SYN-ACK` is dropped at the subnet boundary!

---

## 2. VPC Reachability Analyzer `ExplanationCode` Quick Decoder

| `ExplanationCode` | Meaning & Remediation |
|---|---|
| `ENI_SG_RULES_MISMATCH` | Source ENI outbound SG rule or Destination ENI inbound SG rule does not allow the protocol/port. |
| `SUBNET_NACL_MISMATCH` | Subnet NACL blocks either the destination port on forward path or ephemeral port (`1024–65535`) on return path. |
| `ROUTE_TABLE_NO_ROUTE` | Subnet route table has no matching route for the destination CIDR. |
| `ROUTE_TABLE_BLACKHOLE_ROUTE` | Route points to a deleted VPC Peering connection, stopped NAT instance, or detached TGW attachment (`State: blackhole`). |
| `TGW_ATTACHMENT_APPLIANCE_MODE_DISABLED` | Cross-AZ traffic traversing a stateful inspection firewall via TGW is dropped due to asymmetric AZ routing. |
| `VPC_ENDPOINT_POLICY_MISMATCH` | VPC Endpoint resource policy denies the IAM principal or target S3 bucket / service ARN. |

---

## 3. Route 53 Private Hosted Zone & Resolver (`r53resolver`) Diagnostics

1. **`NXDOMAIN` or Public IP Returned Instead of Private Endpoint IP**:
   - Check VPC attributes (`enableDnsSupport` and `enableDnsHostnames` MUST both be `true`).
   - Verify the Private Hosted Zone is associated with the VPC (`aws route53 list-hosted-zones-by-vpc --vpc-id <vpc-id> --vpc-region <region>`).
2. **Hybrid On-Premises DNS Forwarding Failures**:
   - Inspect Route 53 Resolver Rules (`aws route53resolver list-resolver-rules`) and Outbound Endpoint ENI health.
   - Query Route 53 Resolver Query Logs in CloudWatch Logs Insights for `rcode` (`SERVFAIL`, `NXDOMAIN`, `REFUSED`).
