# Amazon Security Lake (OCSF v1.1) & CloudTrail Lake Threat Hunting SQL

Use these production SQL queries when the operator explicitly requests threat hunting across **Amazon Security Lake** (via Amazon Athena) or **AWS CloudTrail Lake**.

> **Cost & Performance Rule:** Always filter Security Lake queries by the partition columns (`region`, `accountid`, and `eventday` in `YYYYMMDD` format) to avoid full-table Parquet scans across S3!

---

## 1. Amazon Security Lake OCSF Event Class Reference

| OCSF Class Name | `class_uid` | Security Lake Source Table | Primary Use Case |
|---|---|---|---|
| **Account Change** | `3001` | `amazon_security_lake_table_<region>_cloud_trail_mgmt_2_0` | User/Role creation, deletion, password resets |
| **Authentication** | `3002` | `amazon_security_lake_table_<region>_cloud_trail_mgmt_2_0` | Console logins, MFA status, `AssumeRole`, federation |
| **Entity Management / IAM** | `3005` / `3006` | `amazon_security_lake_table_<region>_cloud_trail_mgmt_2_0` | Policy attachment, trust policy modification, access key creation |
| **API Activity** | `6003` | `amazon_security_lake_table_<region>_cloud_trail_mgmt_2_0` / `s3_data_2_0` / `lambda_execution_2_0` | General AWS API calls, `AccessDenied` bursts, secret reads, S3 data events |
| **Network Activity** | `4001` | `amazon_security_lake_table_<region>_vpc_flow_2_0` | VPC Flow Logs (accepted/rejected flows, port scans, C2 egress) |
| **DNS Activity** | `4003` | `amazon_security_lake_table_<region>_route53_2_0` | Route 53 Resolver DNS queries (DGA, C2 domains, DNS tunneling) |
| **Security Finding** | `2001` / `2004` | `amazon_security_lake_table_<region>_sh_findings_2_0` | Security Hub, GuardDuty, Inspector, Macie findings in OCSF format |

---

## 2. Production Athena SQL Queries for Security Lake (OCSF v1.1)

### 2.1 Hunt for `AccessDenied` Reconnaissance Bursts by Actor (OCSF `class_uid = 6003`)

Attackers running automated enumeration tools (`Pacu`, `ScoutSuite`, `enumerate-iam`) generate high volumes of distinct `AccessDenied` / `Client.UnauthorizedOperation` calls within a short window:

```sql
SELECT
  actor.user.uid AS principal_arn,
  actor.user.type AS principal_type,
  src_endpoint.ip AS source_ip,
  http_request.user_agent AS user_agent,
  COUNT(*) AS total_denied_calls,
  COUNT(DISTINCT api.operation) AS distinct_denied_apis,
  ARRAY_AGG(DISTINCT api.operation) AS sample_apis,
  MIN(from_unixtime(time / 1000)) AS first_seen_utc,
  MAX(from_unixtime(time / 1000)) AS last_seen_utc
FROM amazon_security_lake_glue_db_us_east_1.amazon_security_lake_table_us_east_1_cloud_trail_mgmt_2_0
WHERE eventday >= '20261007'
  AND status_code IN ('AccessDenied', 'AccessDeniedException', 'Client.UnauthorizedOperation')
GROUP BY
  actor.user.uid,
  actor.user.type,
  src_endpoint.ip,
  http_request.user_agent
HAVING COUNT(DISTINCT api.operation) >= 5
ORDER BY distinct_denied_apis DESC, total_denied_calls DESC
LIMIT 50;
```

### 2.2 Hunt for Console Logins Without MFA or Root Account Activity (`class_uid = 3002`)

```sql
SELECT
  from_unixtime(time / 1000) AS event_time_utc,
  accountid,
  region,
  actor.user.uid AS principal_arn,
  actor.user.type AS user_type,
  src_endpoint.ip AS source_ip,
  http_request.user_agent AS user_agent,
  is_mfa,
  status
FROM amazon_security_lake_glue_db_us_east_1.amazon_security_lake_table_us_east_1_cloud_trail_mgmt_2_0
WHERE eventday >= '20261007'
  AND class_uid = 3002
  AND api.operation = 'ConsoleLogin'
  AND (is_mfa = false OR actor.user.type = 'Root')
ORDER BY time DESC
LIMIT 100;
```

### 2.3 Hunt for IAM Persistence & Privilege Escalation API Calls (`class_uid IN (3001, 3005, 6003)`)

```sql
SELECT
  from_unixtime(time / 1000) AS event_time_utc,
  accountid,
  actor.user.uid AS actor_arn,
  src_endpoint.ip AS source_ip,
  api.service.name AS service,
  api.operation AS operation,
  status,
  status_code,
  resources
FROM amazon_security_lake_glue_db_us_east_1.amazon_security_lake_table_us_east_1_cloud_trail_mgmt_2_0
WHERE eventday >= '20261007'
  AND api.operation IN (
    'CreateAccessKey',
    'CreateUser',
    'CreateLoginProfile',
    'UpdateLoginProfile',
    'UpdateAssumeRolePolicy',
    'AttachUserPolicy',
    'AttachRolePolicy',
    'AttachGroupPolicy',
    'PutUserPolicy',
    'PutRolePolicy',
    'PutGroupPolicy',
    'CreatePolicyVersion',
    'SetDefaultPolicyVersion',
    'StopLogging',
    'DeleteTrail',
    'DeleteDetector',
    'DisableSecurityHub'
  )
ORDER BY time DESC
LIMIT 200;
```

### 2.4 Hunt for EC2 Instance Profile Credentials Used From Non-AWS External IPs

Detects IMDS credential theft (`i-*` session name used from an external IP outside EC2):

```sql
SELECT
  from_unixtime(time / 1000) AS event_time_utc,
  accountid,
  region,
  actor.user.uid AS assumed_role_arn,
  actor.session.uid AS session_issuer,
  src_endpoint.ip AS caller_ip,
  http_request.user_agent AS user_agent,
  api.service.name AS service,
  api.operation AS operation
FROM amazon_security_lake_glue_db_us_east_1.amazon_security_lake_table_us_east_1_cloud_trail_mgmt_2_0
WHERE eventday >= '20261007'
  AND actor.user.type = 'AssumedRole'
  AND regexp_like(actor.user.uid, ':assumed-role/.+/i-[0-9a-f]{8,17}$')
  AND NOT regexp_like(src_endpoint.ip, '^AWS Internal|.*\.amazonaws\.com$')
ORDER BY time DESC
LIMIT 100;
```

### 2.5 Hunt for High-Volume Egress or Lateral Port Scanning in VPC Flow Logs (`class_uid = 4001`)

```sql
SELECT
  accountid,
  region,
  src_endpoint.ip AS src_ip,
  dst_endpoint.ip AS dst_ip,
  dst_endpoint.port AS dst_port,
  disposition AS action,
  COUNT(*) AS flow_count,
  SUM(traffic.bytes) AS total_bytes
FROM amazon_security_lake_glue_db_us_east_1.amazon_security_lake_table_us_east_1_vpc_flow_2_0
WHERE eventday >= '20261013'
  AND dst_endpoint.port IN (22, 3389, 445, 3306, 5432, 6379, 27017)
GROUP BY
  accountid,
  region,
  src_endpoint.ip,
  dst_endpoint.ip,
  dst_endpoint.port,
  disposition
ORDER BY flow_count DESC
LIMIT 100;
```

---

## 3. CloudTrail Lake SQL Queries ( via `cloudtrail` MCP Server)

When using the `cloudtrail` MCP server's `lake_query` tool against an Event Data Store (`<EDS_ID>`):

```sql
SELECT
  eventTime,
  userIdentity.arn AS actor_arn,
  userIdentity.accessKeyId AS access_key_id,
  sourceIPAddress,
  userAgent,
  eventSource,
  eventName,
  awsRegion,
  errorCode,
  errorMessage
FROM <EDS_ID>
WHERE eventTime >= '2026-10-07 00:00:00'
  AND (
    userIdentity.accessKeyId = '<SUSPECT_KEY_ID>'
    OR sourceIPAddress = '<SUSPECT_IP>'
  )
ORDER BY eventTime ASC
LIMIT 500;
```
