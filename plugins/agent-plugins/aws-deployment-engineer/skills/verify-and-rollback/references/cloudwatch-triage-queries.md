# CloudWatch Alarm, Metric & Logs Insights Triage Queries

Use the bound `cloudwatch` MCP server (`get_active_alarms`, `get_alarm_history`, `get_metric_data`, `describe_log_groups`, `analyze_log_group`, `execute_log_insights_query`, `execute_promql_query`) immediately after every deployment and during incident triage.

## 1. Active Alarm Verification

Call `cloudwatch` tool `get_active_alarms` for the target region:
- Verify no alarms prefixed with the stack, cluster, service, ALB, or function name are in `ALARM` state.
- If an alarm is in `ALARM` state, call `get_alarm_history` to check whether the transition occurred during or immediately after the deployment timestamp.

## 2. Ready-to-Run CloudWatch Logs Insights Queries (`execute_log_insights_query`)

### A. ECS Fargate / Container Startup & Runtime Faults (`/ecs/<service>`)

```sql
fields @timestamp, @logStream, @message
| filter @message like /(?i)(error|exception|fatal|panic|oom|killed|econnrefused|timeout)/
| sort @timestamp desc
| limit 50
```

### B. AWS Lambda Cold-Start, Timeout, OOM & Handler Exceptions (`/aws/lambda/<fn>`)

```sql
fields @timestamp, @requestId, @message
| filter @message like /(?i)(ERROR|Exception|Task timed out|Process exited before completing|Runtime.ExitError|Memory Size)/
| sort @timestamp desc
| limit 50
```

### C. Lambda Performance & Memory Right-Sizing Summary (`REPORT` lines)

```sql
filter @type = "REPORT"
| stats count() as invocations,
        avg(@duration) as avg_duration_ms,
        pct(@duration, 95) as p95_duration_ms,
        max(@maxMemoryUsed / 1000000) as max_mem_used_mb,
        max(@memorySize / 1000000) as allocated_mem_mb,
        sum(@initDuration > 0) as cold_starts
```

### D. API Gateway Integration Errors & 5xx Faults

```sql
fields @timestamp, requestId, httpMethod, routeKey, status, integrationErrorMessage, responseLatency
| filter status >= 500 or ispresent(integrationErrorMessage)
| sort @timestamp desc
| limit 50
```

### E. Elastic Beanstalk nginx & Application Error Triage (`/aws/elasticbeanstalk/<env>/...`)

```sql
fields @timestamp, @logStream, @message
| filter @message like /(?i)(502 Bad Gateway|connect\(\) failed|error|traceback|exception)/
| sort @timestamp desc
| limit 50
```

## 3. Golden Signal Metric Checks (`get_metric_data`)

Query a 15-minute window (`period = 60`) across the deployed stack's primary namespaces:

| Archetype | Namespace | Critical Metrics to Check |
| --- | --- | --- |
| **ALB + ECS Fargate** | `AWS/ApplicationELB`, `AWS/ECS` | `HTTPCode_Target_5XX_Count` (Sum = 0), `UnHealthyHostCount` (Max = 0), `TargetResponseTime` (p95), `CPUUtilization`, `MemoryUtilization` |
| **Lambda + API Gateway** | `AWS/Lambda`, `AWS/ApiGateway` | `Errors` (Sum = 0), `Throttles` (Sum = 0), `Duration` (p95 < Timeout), `5XXError` (Sum = 0), `IntegrationLatency` |
| **Aurora / RDS** | `AWS/RDS` | `DatabaseConnections`, `ServerlessDatabaseCapacity` (ACUs), `CPUUtilization`, `FreeableMemory` |
| **Elastic Beanstalk** | `AWS/ElasticBeanstalk` | `EnvironmentHealth` (0 = Ok), `ApplicationRequests5xx`, `InstancesSevere` |
