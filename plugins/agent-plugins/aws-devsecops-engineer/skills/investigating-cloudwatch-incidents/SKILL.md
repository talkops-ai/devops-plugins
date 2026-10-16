---
name: investigating-cloudwatch-incidents
description: >-
  Performs native AWS SRE root-cause analysis (RCA) for production outages, latency spikes,
  5xx errors, and alarm breaches using CloudWatch Alarms, Metrics, Logs Insights, Application
  Signals, X-Ray traces, and CloudTrail change correlation. Use when the user asks to "investigate
  an incident", "debug a 5xx spike", "why is my alarm firing", "triage latency", or runs `/investigate`.
---

# CloudWatch & X-Ray Native Incident Investigation

## When to Use
Invoke this skill whenever a user reports an active production incident, firing CloudWatch Alarm, latency degradation, elevated 5xx/4xx error rate, Lambda throttling, or container crash loop. This skill executes directly against live AWS telemetry via `aws-cloudwatch`, `aws-cloudtrail`, and `aws-mcp` — no external DevOps Agent Space is required.

## 4-Phase Incident Triage Workflow

### Phase 1: Blast-Radius & Active Alarm Triage (Read-Only)
1. Query `aws-cloudwatch` (`get_active_alarms`) or `aws___call_aws` (`aws cloudwatch describe-alarms --state-value ALARM`) to identify all currently breaching alarms and their state transition timestamps (`StateUpdatedTimestamp`).
2. Check AWS Health events (`aws health describe-events --filter eventStatusCodes=open,upcoming`) via `aws-mcp` to rule out underlying AWS regional service disruptions.
3. Establish the **Incident Window**: `[T_breach - 30 minutes, Now]`.

### Phase 2: Change & Deployment Correlation ("What Changed?")
Over 70% of production incidents are triggered by a code deployment, configuration mutation, or infrastructure update. Run `aws___run_script` (or query `aws-cloudtrail` `lookup_events`) across the incident window to correlate changes:

```python
import boto3
from datetime import datetime, timedelta, timezone

session = boto3.Session()
now = datetime.now(timezone.utc)
start_time = now - timedelta(minutes=60)

ct = session.client("cloudtrail")
cfn = session.client("cloudformation")

# 1. Recent CloudFormation stack updates or failures
stacks = cfn. list_stacks(
    StackStatusFilter=[
        "UPDATE_IN_PROGRESS", "UPDATE_COMPLETE",
        "UPDATE_ROLLBACK_IN_PROGRESS", "UPDATE_ROLLBACK_COMPLETE",
        "ROLLBACK_COMPLETE"
    ]
)["StackSummaries"]
recent_stacks = [
    s for s in stacks
    if s.get("LastUpdatedTime", s["CreationTime"]) >= start_time
]

# 2. Recent mutating control-plane events in CloudTrail
events = ct.lookup_events(
    StartTime=start_time,
    EndTime=now,
    LookupAttributes=[{"AttributeKey": "ReadOnly", "AttributeValue": "false"}],
    MaxResults=50,
)["Events"]

print(f"Recent Stack Updates: {[s['StackName'] for s in recent_stacks]}")
for e in events[:20]:
    print(f"{e['EventTime']} | {e['EventName']} | {e.get('Username', 'unknown')}")
```

Also check recent ECS service deployments (`aws ecs describe-services`), Lambda `LastModified` timestamps (`aws lambda list-functions`), and recent Git commits (`git log -n 10 --oneline`) in the local repository.

### Phase 3: Deep Telemetry & Trace Isolation
1. **Service-Level Topology & SLOs**: Query Application Signals (`aws-cloudwatch`) and X-Ray service graph (`aws xray get-service-graph --start-time ... --end-time ...`) to isolate the exact downstream dependency (RDS, DynamoDB, external API, or microservice) contributing to fault rate or p99 latency.
2. **Trace Exception Extraction**: Fetch failing trace summaries (`aws xray get-trace-summaries --filter-expression 'fault = true OR error = true'`) and inspect `aws xray batch-get-traces` for subsegment exceptions, HTTP status codes, and database wait times.
3. **CloudWatch Logs Insights**: Execute targeted Logs Insights queries via `aws-cloudwatch` (`execute_log_insights_query`):

```sql
fields @timestamp, @message, @logStream
| filter @message like /(?i)(ERROR|Exception|Task timed out|OutOfMemory|Connection refused|FATAL)/
| stats count(*) as error_count by bin(1m), @logStream
| sort @timestamp desc
| limit 50
```

4. **Resource Saturation Metrics**: Pull golden signals via `get_metric_data`:
   - **ALB**: `HTTPCode_Target_5XX_Count`, `TargetResponseTime`, `UnHealthyHostCount`
   - **ECS / EKS**: `CPUUtilization`, `MemoryUtilization`, container exit codes (`ExitCode: 137` OOMKilled)
   - **Lambda**: `Errors`, `Throttles`, `Duration`, `ConcurrentExecutions`, `IteratorAge`
   - **RDS / DynamoDB**: `DatabaseConnections`, `CPUUtilization`, `FreeableMemory`, `ReadThrottleEvents`, `WriteThrottleEvents`

### Phase 4: Mitigation, Rollback & Local Code Fix
1. **Root-Cause Timeline**: Present a chronological timeline correlating the exact change or traffic anomaly (`T-12m: UpdateFunctionConfiguration`) with the metric inflection point (`T-10m: p99 latency > 5s`) and alarm breach (`T-8m`).
2. **Immediate Mitigation / Rollback**: Provide the exact rollback command (e.g., `aws deploy stop-deployment --deployment-id ... --auto-rollback-enabled`, `aws ecs update-service --task-definition <previous-revision>`, or `aws cloudformation rollback-stack`) and **wait for user confirmation** via `aws-mutation-gate.py` before executing.
3. **Permanent Repository Fix**: Locate the offending application code or IaC configuration in the local repository and apply a permanent patch so the next deployment does not re-introduce the failure.
