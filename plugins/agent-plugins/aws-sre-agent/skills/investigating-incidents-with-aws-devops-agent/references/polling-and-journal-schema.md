# Polling Cadence, Journal Record Schema, and Pagination Reference

## 1. Journal Record Schema (`list_journal_records`)

Each record returned by `aws_devops_agent__list_journal_records` or `aws devops-agent list-journal-records` follows this structure:

```json
{
  "recordId": "rec-0123456789abcdef",
  "executionId": "exec-abcdef0123456789",
  "recordType": "FINDING",
  "timestamp": "2026-04-15T14:35:12Z",
  "content": "Root cause identified: ECS task definition revision 42 reduced container memory from 512 MiB to 256 MiB, triggering OOMKilled (Exit Code 137) under peak checkout load.",
  "metadata": {
    "service": "ecs",
    "resourceArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/checkout-service:42",
    "confidence": "HIGH"
  }
}
```

### Record Type Mapping & SRE Triage Actions

| Record Type | UI Prefix | SRE Meaning | Action Required During Live Stream |
|---|---|---|---|
| `PLANNING` | 📋 | Hypothesis tree construction across metrics, logs, traces, and changes | Summarize the investigation branches to the Incident Commander |
| `SEARCHING` | 🔍 | Querying CloudWatch Metrics, Logs Insights, X-Ray traces, or CloudTrail | Note which telemetry sources are being inspected |
| `ANALYSIS` | 🔬 | Correlating anomaly timestamps against deployment or config changes | Report intermediate correlation results |
| `FINDING` | 🎯 | Confirmed anomaly or causal evidence | **Highlight immediately** with exact timestamp, metric/log evidence, and resource ARN |
| `ACTION` | 🔧 | Executing a read-only diagnostic verification step | Log the diagnostic query executed |
| `SUMMARY` | 📊 | Final root-cause synthesis and blast-radius assessment | Extract into the Incident Postmortem / COE timeline |
| `SUGGESTION` | 💡 | Concrete mitigation or IaC remediation proposal | Present diff/commands for human approval; never auto-execute |
| `mitigation_summary_md` | 🛡️ | Markdown runbook generated after mitigation execution completes | Present step-by-step rollback/fix verification plan |

---

## 2. Polling Cadence & Backoff State Machine

Never poll faster than **30 seconds** to avoid `ThrottlingException`. Always stream incremental progress to the user on every poll cycle.

| Task Status | Poll Interval | Max Dwell Time | Transition / Escalation Action |
|---|---|---|---|
| `CREATED` | 30s | 90s | Agent space worker is claiming the task. Continue polling up to 90s. |
| `IN_PROGRESS` | 30–45s | 10 min | Call `list_journal_records` with `next_token` (`--next-token`) and `order="ASC"`. Summarize only newly arrived records. |
| `COMPLETED` | Stop | — | Fetch final summary (`order="DESC"`, `limit=10`) + `list_recommendations(task_id=...)`. |
| `FAILED` | Stop | — | Fetch partial journal records (`order="ASC"`); pivot immediately to native SRE MCP servers (`cloudwatch`, `appsignals`, `cloudtrail`, `eks`, `ecs`, `network`). |

### Incremental Pagination Pattern
1. On Poll #1, call `list_journal_records(execution_id=EXEC_ID, order="ASC")` without `next_token`.
2. Store the returned `nextToken` (if non-empty) and the set of seen `recordId`s.
3. On subsequent polls, pass `next_token=SAVED_TOKEN` so only new records are transferred over the wire.
