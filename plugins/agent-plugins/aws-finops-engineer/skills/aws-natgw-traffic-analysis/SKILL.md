---
name: aws-natgw-traffic-analysis
description: 'Use this skill when a user wants to understand what traffic is going through an AWS NAT Gateway, why it takes that path, or how to reduce NAT Gateway cost - for example "why is my NAT Gateway bill so high", "what is going through my NAT Gateway", traffic leaving through NAT instead of over peering or a VPC endpoint, EKS, ECS, or other private-subnet workloads sending heavy AWS API, container image, or S3 traffic through NAT, S3 traffic still hitting NAT even though a Gateway Endpoint exists, whether Gateway or Interface Endpoints are actually being used, customer-owned or BYOIP public IPs appearing as NAT destinations, estimating how much fixing NAT traffic would save, which flow logs to use for NAT analysis, or before recommending a Cross-Region S3 Interface Endpoint. Also use it when the user shares or points to NAT Gateway VPC Flow Logs, or asks which resource or service is behind a NAT Gateway destination IP. Read-only and advisory: reports traffic in GB and percent and never changes resources.'
metadata:
  version: "1.1.0"
  author: abitnar1
  summary: "Traces AWS NAT Gateway traffic from flow logs to find endpoint, peering, and cross-region paths that bypass NAT. Read-only, GB and percent only."
  aws-devops-agent-skills.agent-types: "CHAT"
  aws-devops-agent-skills.aws-services: "Amazon VPC, Amazon S3, Amazon EC2, AWS CloudTrail, Amazon CloudWatch"
  aws-devops-agent-skills.technical-domains: "Networking, Cost Optimization"
---

# AWS NAT Gateway Traffic & Bypass Analysis

Analyze NAT Gateway traffic — *where bytes are actually going and why they take the NAT path* — to uncover bypassed or missing VPC Endpoints, public-IP hairpinning to customer-owned/RDS endpoints, and cross-region S3 flows. Strictly **read-only and advisory**: reports traffic in **GB and % only**, recommends architectural options with tradeoffs, and never mutates AWS resources.

## MCP-Only Execution & Verification Directives (Mandatory)

1. **MCP-Only Execution (Zero Raw Shell CLI):** Execute **all** live AWS inspections **exclusively via connected MCP servers**: `aws-mcp` (`aws___run_script` using read-only `call_boto3` for `ec2` `DescribeNatGateways`, `DescribeFlowLogs`, `DescribeVpcEndpoints`, `DescribeRouteTables`, `DescribeManagedPrefixLists`, `GetManagedPrefixListEntries`, `DescribeAddresses`, `DescribeNetworkInterfaces`, `DescribeVpcPeeringConnections`), `cloudwatch` (`get_metric_data`, `describe_log_groups`, `execute_log_insights_query`), `cloudtrail` (`lookup_events` or `aws___run_script` `LookupEvents`), and `awsnetwork` (when available). **Never** run raw `aws` CLI or `python3 -c` commands in Bash/`run_command`, and **never** create/modify/delete endpoints, route tables, or flow logs.
2. **Answer First, Then Ask:** Answer from the user's description or supplied flow logs first (explaining causes, stating assumptions, and running read-only MCP checks if an account/region is in scope), then list any additional confirmation data needed.
3. **Zero Dollar Figures (Strict GB & % Rule):** **Do NOT report dollar figures anywhere** — no monthly/yearly dollar totals, ranges, or per-GB `$` prices, **even when the user explicitly asks for dollars or provides rates**! Report volumes strictly in **GB and % of total**, then provide the symbolic pricing formula: `(Addressable_GB × Account_NAT_Per_GB_Rate) − (Addressable_GB × Replacement_Path_Rate + Endpoint_AZ_Hours × Hourly_Endpoint_Rate)`.
4. **Anti-Hallucination & Attribution Discipline:** Never invent IP owners or traffic volumes. Never name a specific non-S3/DynamoDB AWS API service (e.g., STS, ECR, Logs) from an IP range or flow-log `pkt-dst-aws-service` tag alone — attribute S3 and DynamoDB strictly via AWS-managed prefix lists (`com.amazonaws.<region>.s3` / `.dynamodb`), and identify other AWS APIs via CloudTrail (`sourceIPAddress` = NAT Gateway public EIP).
5. **`awsknowledge` Fallback:** For niche NAT Gateway features outside local references (e.g., Regional NAT Gateway mode, Private NAT Gateway overlapping-CIDR translation, secondary EIP scaling limits), query `awsknowledge` / `aws-mcp` (`aws___search_documentation` / `aws___read_documentation` — 1–2 focused searches).

## Investigation Workflow (Execute in Order)

Load each reference file as its step applies:

1. **Step 1 — Confirm Data Source & Locate Flow Logs ([references/flow-log-location.md](references/flow-log-location.md)):**
   - Flow logs **must** come from the **NAT Gateway's own ENI** (`interface-id = nat_gw_eni`), **never** an instance ENI (instance ENIs include traffic routed to Gateway Endpoints and cannot show what traversed NAT!). If the user supplied instance-ENI logs, explain why they are invalid for NAT attribution and show how to query the NAT Gateway ENI instead.
   - Via `aws___run_script`, call `DescribeNatGateways` -> extract NAT ENI ID & public EIP -> `DescribeFlowLogs` (on ENI, subnet, or VPC) -> query via `cloudwatch` `execute_log_insights_query` filtered to `interface-id = <nat-eni>`. If `0` NAT Gateways or `0` flow logs exist, report that honestly without fabricating records.
2. **Step 2 — Verify Region & Analysis Window:** Never default to a 5–60 minute window (misses nightly ETL/backups). Use the user's stated window, or inspect 14-day hourly CloudWatch `BytesOutToDestination` / `BytesInFromDestination` (`Sum`) via `cloudwatch` `get_metric_data` and analyze `>= 7` days (or available retention, disclosed explicitly).
3. **Step 3 — Categorize Destination IPs ([references/traffic-categorization.md](references/traffic-categorization.md)):**
   - Classify every destination IP into exactly one bucket: **AWS Service**, **Customer-Owned Public IP**, **RFC1918** (initiator side of bidirectional NAT flow — never treat RFC1918 as an external destination; handle `src|dst` pipe-aggregation artifacts), or **Third-Party / CDN**.
   - Check `ec2:DescribeAddresses` (account EIPs) before labeling any IP third-party, and map S3/DynamoDB IPs against local + cross-region managed prefix lists (`GetManagedPrefixListEntries`), naming the exact AWS region of every S3/DynamoDB destination.
4. **Step 4 & 5 — Audit S3/DynamoDB Gateway Endpoints & Cross-Region S3 ([references/endpoint-coverage-and-cross-region.md](references/endpoint-coverage-and-cross-region.md)):**
   - Check `DescribeVpcEndpoints` (`Gateway`) and verify **every** private workload subnet's route table contains the `pl-*` route.
   - If destination S3 IPs match *another* region's `com.amazonaws.<other-region>.s3` prefix list, explain that **Gateway Endpoints are same-region only** (Hard Rule 1 — expected bypass, not a broken endpoint!).
5. **Step 6 — Audit Interface Endpoints & ECR Layer Pattern ([references/interface-endpoints.md](references/interface-endpoints.md)):**
   - Query CloudTrail (`sourceIPAddress = <NAT EIP>`) to see which AWS APIs (`eventSource`) traverse NAT. Verify `PrivateDnsEnabled=true`, VPC `enableDnsSupport` + `enableDnsHostnames`, and endpoint ENI coverage in **every** workload AZ.
   - **ECR Pull Rule:** ECR manifests use `ecr.api`/`ecr.dkr`, but **image layer bytes come from Amazon S3** — without an S3 Gateway Endpoint, layer downloads still traverse NAT!
6. **Step 7 — Trace Customer-Owned Public IPs ([references/customer-ip-tracing.md](references/customer-ip-tracing.md)):** Check `DescribeAddresses` -> `DescribeNetworkInterfaces` (including public-IP RDS hairpinning), `DescribeVpcPeeringConnections`, and route tables.
7. **Step 8 — Mandatory `CopyObject` / `UploadPartCopy` Gate Before Cross-Region S3 Fixes ([references/endpoint-coverage-and-cross-region.md](references/endpoint-coverage-and-cross-region.md)):** Check whether workloads run cross-region `CopyObject` / `UploadPartCopy` before ever suggesting a Cross-Region S3 Interface Endpoint!
8. **Step 9 & 10 — Format & Self-Validate Output ([references/output-and-limitations.md](references/output-and-limitations.md)):** Render GB + `%` category table (summing to total / ~100%), data-window representativeness disclaimer, option comparison with tradeoffs, mandatory **"What We Cannot Determine"** limitations block, and a **Read-Only Validation Commands** block (`aws ec2 describe-nat-gateways`, `aws ec2 describe-flow-logs`, `aws ec2 describe-vpc-endpoints` — include these copy-pasteable read-only validation commands **even when `0` NAT Gateways or `0` flow logs exist** so operators can repeat the check in other regions/accounts; zero dollar signs!).

## The 14 Non-Negotiable Hard Rules

1. **Gateway Endpoints (S3/DynamoDB) are strictly same-region** — cross-region S3 IPs bypass them by design; never blame local endpoint config for cross-region S3 bytes.
2. **Gateway Endpoints intercept matching local prefix-list traffic**; everything else takes `0.0.0.0/0`.
3. **A Cross-Region S3 Interface Endpoint with Private DNS breaks cross-region `CopyObject`/`UploadPartCopy` across the ENTIRE VPC (all public & private subnets!).** Always gate on `CopyObject` check first; if active, recommend **S3 Cross-Region Replication (CRR) + local reads** or **S3 Multi-Region Access Points (MRAP)** instead.
4. **`CopyObject` data payloads move AWS-backbone S3-to-S3 and NEVER traverse NAT Gateway** (only tiny control-plane API bytes do — never count `CopyObject` object sizes as NAT GB savings!).
5. **Only NAT Gateway ENI flow logs prove NAT traversal** — instance ENI flow logs include local/Gateway-Endpoint traffic and cannot measure NAT bytes.
6. **S3 Cross-Region Replication (`PutObjectForRepl`) never traverses customer NAT Gateways.**
7. **NAT Gateway ENI flow logs mask the internal source pod/container/EC2 instance** (NAT's own private IP appears on the outside leg; state this limitation explicitly).
8. **VPC Peering / TGW existing != being used** — calling a target's public/EIP hostname or missing a subnet route table entry still routes `0.0.0.0/0` -> NAT.
9. **Absence of evidence != evidence of absence** — empty/denied API responses could reflect region, account, or IAM scope.
10. **Cross-Region Interface Endpoints incur BOTH PrivateLink processing AND inter-region data transfer** on the same bytes (state structurally; quote zero `$` numbers).
11. **Interface Endpoints silently bypass to NAT** if `PrivateDnsEnabled=false`, VPC `enableDnsSupport`/`enableDnsHostnames` is `false`, or the workload's AZ lacks an endpoint subnet; ECR pulls also require the S3 Gateway Endpoint for layer blobs.
12. **`ip-ranges.amazonaws.com` `AMAZON` ranges share dozens of APIs** — label `"AWS (service unidentified)"` until CloudTrail confirms `eventSource`.
13. **Never trust flow-log `pkt-src-aws-service` / `pkt-dst-aws-service` tags** for service attribution — use managed prefix lists for S3/DynamoDB and CloudTrail for other APIs.
14. **Only S3 and DynamoDB map deterministically to flow-log bytes** — CloudTrail gives API call counts (not bytes), so Interface Endpoint recommendations must state that exact GB payoff is unquantified from CloudTrail alone alongside the per-AZ hourly endpoint tradeoff.

## References

- [references/flow-log-location.md](references/flow-log-location.md) — Locating & querying NAT Gateway ENI flow logs.
- [references/traffic-categorization.md](references/traffic-categorization.md) — 4-bucket IP classification, `src|dst` & RFC1918 rules, prefix-list region mapping.
- [references/endpoint-coverage-and-cross-region.md](references/endpoint-coverage-and-cross-region.md) — Gateway Endpoint route audits, cross-region S3 detection, and `CopyObject` decision tree.
- [references/interface-endpoints.md](references/interface-endpoints.md) — CloudTrail NAT EIP correlation, PrivateLink DNS/AZ checks, ECR S3 layer trap.
- [references/customer-ip-tracing.md](references/customer-ip-tracing.md) — EIP/ENI/RDS public-endpoint hairpinning and peering route checks.
- [references/output-and-limitations.md](references/output-and-limitations.md) — Mandatory GB/% table, zero-dollar rule, window disclaimer, and limitations block.
