---
name: auditing-cloudtrail-forensics
description: >-
  Executes AWS CloudTrail forensic investigations, management and data event timeline
  reconstruction, CloudTrail Lake SQL queries, `AccessDenied` spike analysis, root account
  activity checks, and `aws:CalledViaAWSMCP` AI agent audit trails. Use when the user asks
  "who changed or deleted this resource", "audit CloudTrail events", "investigate suspicious
  IAM activity", or needs forensic evidence during incident or security triage.
---

# CloudTrail Security Forensics & Audit Trail Analysis

## When to Use
Invoke this skill whenever you need to answer **"Who did what, when, from where, and how?"** in an AWS account: investigating unauthorized infrastructure mutations, tracing compromised IAM credentials, auditing root user logins, diagnosing `AccessDenied` spikes, or auditing AI agent actions via `aws:CalledViaAWSMCP`.

## 4-Phase Forensic Investigation Workflow

### Phase 1: Scope the Forensic Query Window & Pivot Attribute
Identify the primary pivot key for the investigation:
- **By Resource**: `ResourceName` (e.g., S3 bucket name, Security Group ID `sg-...`, IAM role name, KMS key ARN)
- **By Actor**: `Username` or `AccessKeyId` (`AKIA...` / `ASIA...`)
- **By Action**: `EventName` (e.g., `AuthorizeSecurityGroupIngress`, `PutBucketPolicy`, `CreateAccessKey`, `AssumeRole`, `StopLogging`)
- **By Error**: `errorCode` (`AccessDenied`, `Client.UnauthorizedOperation`)

### Phase 2: Event Lookup & CloudTrail Lake SQL Analysis
1. **Standard Management Event Lookup (`aws-cloudtrail`)**:
   Call `lookup_events` via the `aws-cloudtrail` MCP server across the target window.
2. **CloudTrail Lake SQL Queries (`aws-cloudtrail`)**:
   If CloudTrail Lake event data stores are enabled (`list_event_data_stores`), use `lake_query` to run high-speed SQL aggregations across multi-region management and data events:

```sql
SELECT
    eventTime,
    userIdentity.arn AS principalArn,
    userIdentity.type AS identityType,
    eventSource,
    eventName,
    sourceIPAddress,
    userAgent,
    errorCode,
    errorMessage
FROM <event-data-store-id>
WHERE eventTime >= '2026-10-14 00:00:00'
  AND (
    readOnly = false
    OR errorCode IN ('AccessDenied', 'Client.UnauthorizedOperation')
  )
ORDER BY eventTime DESC
LIMIT 100
```

3. **Deep Event Inspection via `aws___run_script`**:
   Parse raw `CloudTrailEvent` JSON payloads to inspect `requestParameters`, `responseElements`, `sessionContext.sessionIssuer`, `tlsDetails`, and `invokedBy`:

```python
import boto3
import json
from datetime import datetime, timedelta, timezone

ct = boto3.client("cloudtrail")
now = datetime.now(timezone.utc)
events = ct.lookup_events(
    StartTime=now - timedelta(hours=24),
    EndTime=now,
    LookupAttributes=[{"AttributeKey": "ReadOnly", "AttributeValue": "false"}],
    MaxResults=50,
)["Events"]

for e in events:
    raw = json.loads(e["CloudTrailEvent"])
    ui = raw.get("userIdentity", {})
    print(json.dumps({
        "time": raw.get("eventTime"),
        "event": f"{raw.get('eventSource')}:{raw.get('eventName')}",
        "actor": ui.get("arn") or ui.get("type"),
        "sourceIP": raw.get("sourceIPAddress"),
        "userAgent": raw.get("userAgent"),
        "error": raw.get("errorCode"),
        "requestParameters": raw.get("requestParameters"),
    }))
```

### Phase 3: High-Risk Forensic Detection Patterns
Check for these critical compromise and privilege-escalation indicators:
1. **Root Account Usage**: `userIdentity.type == "Root"` performing interactive console actions or creating access keys.
2. **IAM Privilege Escalation**: `CreatePolicyVersion`, `SetDefaultPolicyVersion`, `AttachRolePolicy`, `PutRolePolicy`, `CreateAccessKey`, `UpdateAssumeRolePolicy`, or `PassRole` followed by compute creation (`RunInstances`, `CreateFunction20150331`).
3. **Defense Evasion**: `StopLogging`, `DeleteTrail`, `UpdateTrail`, `DeleteFlowLogs`, `DeleteDetector` (GuardDuty), or `DisableSecurityHub`.
4. **Credential Exfiltration**: EC2 instance role credentials (`ASIA*` issued to `i-...`) used from an external non-AWS IP address (`sourceIPAddress`).
5. **AI Agent / MCP Audit Trail**: Inspect events where `userAgent` or session context reflects `mcp-proxy-for-aws` (`aws:CalledViaAWSMCP` / `aws:ViaAWSMCPService`).

### Phase 4: Forensic Timeline & Containment Plan
Produce an immutable forensic report containing:
- **Chronological Event Table**: Timestamp (UTC), Principal ARN, Source IP, User Agent, API Call, Target Resource, and Result (`Success` / `AccessDenied`).
- **Containment Recommendations**: Exact AWS CLI commands to revoke active role sessions (`aws iam put-role-policy` with `DateLessThan` `aws:TokenIssueTime` deny policy), deactivate compromised `AKIA*` keys (`aws iam update-access-key --status Inactive`), and revert unauthorized resource changes via IaC.
