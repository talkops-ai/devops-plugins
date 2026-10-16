# Direct AWS CLI & Native MCP Fallback Runbook

When the remote `aws-devops-agent` MCP server is unavailable (or `DEVOPS_AGENT_TOKEN` is not configured), `aws-sre-agent` executes a two-tier fallback:
1. **Tier 1 — Direct `aws devops-agent` CLI / `aws-api` Inspection**: Query existing Agent Spaces, backlog tasks, and journal records via `aws-api` (`call_aws`) or read-only CLI commands.
2. **Tier 2 — Native SRE MCP Hypothesis Loop**: Run the full 4-phase SRE investigation directly using `cloudwatch`, `appsignals`, `prometheus`, `cloudtrail`, `eks`, `ecs`, and `network` MCP servers.

---

## Tier 1: Direct `aws devops-agent` CLI Commands

### 1. Discover Agent Spaces (Multi-Account / Multi-Space Routing)
```bash
aws devops-agent list-agent-spaces --region us-east-1
```
Identify the target `agentSpaceId` matching the workload account or environment (`prod`, `staging`).

### 2. Inspect Existing Backlog Tasks & Executions (Read-Only via `aws-api`)
```bash
aws devops-agent list-backlog-tasks \
  --agent-space-id "$SPACE_ID" \
  --region us-east-1

aws devops-agent get-backlog-task \
  --agent-space-id "$SPACE_ID" \
  --task-id "$TASK_ID" \
  --region us-east-1

aws devops-agent list-executions \
  --agent-space-id "$SPACE_ID" \
  --task-id "$TASK_ID" \
  --region us-east-1
```

### 3. Stream Journal Records with `nextToken`
```bash
aws devops-agent list-journal-records \
  --agent-space-id "$SPACE_ID" \
  --execution-id "$EXEC_ID" \
  --page-size 50 \
  --region us-east-1
```

### 4. Starting a New Investigation Task (Requires User Approval in Read-Only Mode)
Because `create-backlog-task` and `update-backlog-task` are mutating control-plane calls, present the exact command to the user for approval or run it once approved:
```bash
aws devops-agent create-backlog-task \
  --agent-space-id "$SPACE_ID" \
  --task-type INVESTIGATION \
  --title "ECS 503 errors on checkout-service since commit abc1234 deployed 2h ago" \
  --priority HIGH \
  --description "Local git log + stack trace + task-def diff attached" \
  --region us-east-1
```

---

## Tier 2: Native SRE MCP Parallel Triage (Zero Dependency on DevOps Agent Space)

Whenever `aws-devops-agent` is not provisioned in the account, execute the native SRE triage loop in parallel:
1. **Alarms & Golden Signals**: `cloudwatch.get_active_alarms` + `appsignals.list_monitored_services` + `appsignals.get_service_detail`.
2. **SLOs & Traces**: `appsignals.list_slos` + `appsignals.query_sampled_traces` (filter `Fault=true` or `Throttle=true`).
3. **Log Anomalies**: `cloudwatch.analyze_log_group` + `cloudwatch.execute_log_insights_query`.
4. **Change Correlation**: `cloudtrail.lookup_events` across the `[T_onset - 90m, T_onset + 15m]` window for `Update*`, `Put*`, `Deploy*`, `RegisterTaskDefinition`, `Modify*`.
