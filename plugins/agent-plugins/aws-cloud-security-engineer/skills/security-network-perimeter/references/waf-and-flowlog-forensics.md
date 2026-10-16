# VPC Flow Logs v5 & AWS WAFv2 Forensics (CloudWatch Logs Insights Queries)

Use these **CloudWatch Logs Insights** queries (via the `cloudwatch` MCP server `execute_log_insights_query` tool) to analyze **VPC Flow Logs** and **AWS WAFv2 Logs** during perimeter audits, DDoS/bot triage, or lateral movement investigations.

---

## 1. VPC Flow Logs Forensics

> **VPC Flow Log v5 Pitfall (`srcaddr` vs. `pkt-srcaddr`):**
> When traffic traverses a Transit Gateway, NAT Gateway, or Gateway Load Balancer (AWS Network Firewall), standard v2 `srcaddr`/`dstaddr` fields show the **intermediate ENI IP**, NOT the original source/destination IP! Always check whether v5 fields `pkt-srcaddr`, `pkt-dstaddr`, `flow-direction`, `traffic-path`, and `tcp-flags` are logged.

### 1.1 Detect Inbound Port Scanning / Reconnaissance (`REJECT` Bursts Across Distinct Ports)

```
fields @timestamp, srcaddr, dstaddr, dstport, protocol, action
| filter action = "REJECT"
| stats count(*) as rejected_packets, count_distinct(dstport) as distinct_ports_probed by srcaddr, dstaddr
| filter distinct_ports_probed >= 15
| sort distinct_ports_probed desc, rejected_packets desc
| limit 50
```

### 1.2 Detect Internal East-West Lateral Movement Attempts on Admin/Database Ports

Filters for RFC1918 private source IPs probing SSH (`22`), SMB (`445`), RDP (`3389`), MySQL (`3306`), PostgreSQL (`5432`), or Redis (`6379`) inside the VPC:

```
fields @timestamp, srcaddr, dstaddr, dstport, action, bytes, packets
| filter (srcaddr like /^10\./ or srcaddr like /^172\.(1[6-9]|2[0-9]|3[0-1])\./ or srcaddr like /^192\.168\./)
| filter dstport in [22, 445, 1433, 3306, 3389, 5432, 6379, 27017]
| stats count(*) as attempts, sum(bytes) as total_bytes by srcaddr, dstaddr, dstport, action
| sort attempts desc
| limit 100
```

### 1.3 Detect High-Volume Data Exfiltration / Unusual Egress Destinations

Identifies top outbound transfers from internal workloads to public IPv4 addresses on non-ephemeral destination ports:

```
fields @timestamp, srcaddr, dstaddr, dstport, bytes, packets, action
| filter action = "ACCEPT" and dstport < 32768
| filter not (dstaddr like /^10\./ or dstaddr like /^172\.(1[6-9]|2[0-9]|3[0-1])\./ or dstaddr like /^192\.168\./)
| stats sum(bytes)/1048576 as total_megabytes, count(*) as flows by srcaddr, dstaddr, dstport
| filter total_megabytes > 50
| sort total_megabytes desc
| limit 50
```

---

## 2. AWS WAFv2 Log Forensics & Rule Tuning

AWS WAF log groups (`aws-waf-logs-*`) emit structured JSON records per inspected HTTP request.

### 2.1 Top Blocked vs. Counted WAF Rules & Terminating Rule Analysis

Use this query before flipping an AWS Managed Rule Group from `Count` to `Block` to verify false-positive rates:

```
fields @timestamp, action, terminatingRuleId, terminatingRuleType, httpRequest.clientIp as clientIp, httpRequest.uri as uri
| stats count(*) as request_count by action, terminatingRuleId, nonTerminatingMatchingRules.0.ruleId as counted_rule
| sort request_count desc
| limit 50
```

### 2.2 Identify Top Attacking IPs, Countries, JA3/JA4 TLS Fingerprints & URIs

Even when attackers rotate proxy IPs, their tooling often shares an identical **JA3 / JA4 TLS fingerprint** (`ja3Fingerprint` / `ja4Fingerprint`):

```
fields @timestamp, httpRequest.clientIp as ip, httpRequest.country as country, ja3Fingerprint, ja4Fingerprint, httpRequest.httpMethod as method, httpRequest.uri as uri, terminatingRuleId
| filter action = "BLOCK"
| stats count(*) as blocked_requests, count_distinct(httpRequest.clientIp) as distinct_ips by ja3Fingerprint, ja4Fingerprint, country, uri, terminatingRuleId
| sort blocked_requests desc
| limit 50
```

### 2.3 Calculate P99 Request Rate per IP (5-Minute Windows) for WAF Rate-Based Rule Sizing

Before configuring a WAF Rate-Based Rule (`RateBasedStatement` with `EvaluationWindowSec: 300`), measure legitimate peak 5-minute traffic per IP and sets of `2x–3x` headroom:

```
fields @timestamp, httpRequest.clientIp as clientIp
| filter action = "ALLOW"
| stats count(*) as req_per_5min by clientIp, bin(5m) as window
| sort req_per_5min desc
| limit 50
```

---

## 3. Baseline WAFv2 Managed Rule Stack Recommendation

When a public ALB, CloudFront distribution, API Gateway, or AppSync endpoint has no WAF WebACL or an incomplete rule set, recommend this prioritized evaluation order (lowest priority number evaluated first):

1. **Priority 10 — IP Reputation List:** `AWSManagedRulesAmazonIpReputationList` (Action: `Block`).
2. **Priority 20 — Anonymous IP List:** `AWSManagedRulesAnonymousIpList` (Action: `Block` or `CAPTCHA` on auth endpoints; watch `HostingProviderIPList` if legitimate webhooks call the API).
3. **Priority 30 — Rate-Based Blanket & Auth-Endpoint Limits:**
   - Dedicated tight rate limit (`100–300` req / 5 min) scoped down to `/login`, `/auth`, `/token`, `/graphql`, `/api/v1/reset-password`.
   - Global rate limit (`2000+` req / 5 min) across all URIs.
4. **Priority 40 — Core Rule Set (OWASP Top 10):** `AWSManagedRulesCommonRuleSet` (Start in `Count` to inspect `SizeRestrictions_BODY` for file-upload routes, then move to `Block` with surgical scope-down overrides—never leave the whole rule group in `Count`).
5. **Priority 50 — Known Bad Inputs (Log4j / SSRF / Deserialization):** `AWSManagedRulesKnownBadInputsRuleSet` (Action: `Block`).
6. **Priority 60 — SQLi Protection:** `AWSManagedRulesSQLiRuleSet` (Action: `Block`).

---

## 4. Advanced WAFv2 Engineering: Bot Control, Fraud Control, Header Stripping & CDN IP Recovery

### 4.1 Bot Control (`Common` vs. `Targeted`) & Fraud Control (ATP / ACFP)
- **`Common` vs. `Targeted` Bot Control (`AWSManagedRulesBotControlRuleSet`):**
  - `Common` inspection level only catches self-identifying bots and known-bad bot IPs.
  - For login, checkout, gift-card, or high-value API endpoints facing evasive headless browsers, require **`Targeted` inspection level** paired with the WAF Application Integration SDK token (`x-aws-waf-token`).
- **Fraud Control vs. Rate Limiting:**
  - Rate-based rules stop volumetric HTTP floods from a single IP, but distributed credential stuffing and fake-account creation rotate across thousands of residential proxy IPs.
  - Recommend **`AWSManagedRulesATPRuleSet` (Account Takeover Prevention)** for `/login` routes and **`AWSManagedRulesACFPRuleSet` (Account Creation Fraud Prevention)** for `/signup` routes.

### 4.2 Mandatory Inbound `x-amzn-waf-*` Header-Spoofing Protection
Whenever WAF forwards custom signal headers (e.g., `x-amzn-waf-bot-confidence`, `x-amzn-waf-client-ip`) to the origin via `CustomRequestHandling.InsertHeaders`:
- **Vulnerability:** AWS WAF prefixes inserted headers with `x-amzn-waf-`. However, if an attacker sends their own inbound HTTP request containing `x-amzn-waf-bot-confidence: low` and the rule that sets the header does not match, the attacker's forged header passes straight through to the origin!
- **Mandatory Control:** Add an early low-priority rule in the WebACL that matches requests where `SingleHeader` / `Headers` starts with `x-amzn-waf-` (or overwrite/strip those headers unconditionally at the first rule) before evaluating downstream signal-forwarding rules.

### 4.3 Recovering the Real Client IP Behind a Third-Party CDN
When a regional ALB or API Gateway sits behind a proxy/CDN, `httpRequest.clientIp` reflects the CDN edge IP rather than the end user:
1. Configure `ForwardedIPConfig` (`HeaderName: "X-Forwarded-For"` or CDN-specific header, `FallbackBehavior: "MATCH"`) on Rate-Based, Geo-Match, and IP Set statements.
2. **CRITICAL:** Only trust `X-Forwarded-For` in WAF after locking the ALB Security Group (or an earlier WAF IP Set rule) strictly to the **verified CDN egress IP ranges**—otherwise any attacker can spoof `X-Forwarded-For: 1.2.3.4` to bypass WAF rate limits and IP bans!

### 4.4 Redacting Sensitive Fields in WAFv2 Logs (`wafv2:PutLoggingConfiguration`)
WAF logs record full HTTP headers and query strings. Always verify `RedactedFields` in `wafv2:GetLoggingConfiguration` includes:
- `SingleHeader: {"Name": "authorization"}`
- `SingleHeader: {"Name": "cookie"}`
- `SingleHeader: {"Name": "x-api-key"}`

---

## 5. AWS Shield Advanced (L3/L4/L7 DDoS Mitigation & SRT Governance)

All AWS Shield Advanced control-plane API calls (`aws shield ...`) run in **`us-east-1`**.

1. **Audit Subscription, Resource Protections & Protection Groups:**
   - Call `shield:DescribeSubscription`, `shield:ListProtections`, and `shield:ListProtectionGroups --region us-east-1`.
   - Ensure internet-facing CloudFront distributions, ALBs, NLBs, Elastic IPs, Global Accelerators, and Route 53 Hosted Zones are enrolled in `ListProtections` and grouped into **Protection Groups** (`Aggregation: SUM | MEAN | MAX`).
2. **Distinguish Health-Based Detection vs. Automatic L7 Mitigation:**
   - **Health-Based Detection (`shield:AssociateHealthCheck`):** Links a Route 53 Health Check to the protected resource to accelerate DDoS detection and is a **mandatory prerequisite for SRT Proactive Engagement**.
   - **Automatic Application-Layer (L7) Mitigation (`shield:EnableApplicationLayerAutomaticResponse`):** Automatically synthesizes and places `COUNT` or `BLOCK` rules into the associated WAFv2 WebACL during a L7 flood.
3. **Shield Response Team (SRT) IAM Role Hardening (`drt.shield.amazonaws.com`):**
   - Call `shield:DescribeDRTAccess --region us-east-1`.
   - When granting SRT access (`shield:AssociateDRTRole`), verify the IAM role's trust policy for `Principal: {"Service": "drt.shield.amazonaws.com"}` enforces a confused-deputy condition (`"StringEquals": {"aws:SourceAccount": "<account-id>"}`) and only shares encrypted WAF log buckets free of unredacted credentials.
4. **DDoS CloudWatch Alarms:**
   - Verify CloudWatch alarms exist on `AWS/DDoSProtection` metrics `DDoSDetected` and `DDoSAttackBitsPerSecond` (and `DDoSAttackRequestsPerSecond` for L7) in `us-east-1` (for CloudFront/Route 53) and workload regions.

