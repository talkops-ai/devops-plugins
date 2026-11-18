# Honeycomb

Official Honeycomb high-cardinality production investigation, wide-event/BubbleUp query patterns, OpenTelemetry metrics, SLO burn-rate & trigger triage, trace verification, and board creation skills with bundled remote MCP configuration (`HONEYCOMB_API_KEY`, `HONEYCOMB_MCP_URL`).

Maintained by **Honeycomb.io** (skills redistributed unmodified from [`aws/tools-for-devops-agent`](https://github.com/aws/tools-for-devops-agent) under Apache-2.0).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install honeycomb@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install `honeycomb` |
| Other Agent Plugins hosts | Load this directory (`plugin.json`, `skills/`, `mcp.json`) |

## Configuration

Set `HONEYCOMB_API_KEY` and optional `HONEYCOMB_MCP_URL` (`https://mcp.honeycomb.io/mcp` US default or `https://mcp.eu1.honeycomb.io/mcp` EU) before starting your session. See [`CONNECTORS.md`](./CONNECTORS.md) for endpoint details.

## Skills (7)

| Skill | Description |
|---|---|
| `honeycomb-create-board` | Load when the operator asks for a Honeycomb board or dashboard: a board for a service, a feature, or an incident, a golden signals dashboard, or a board to visualize service hea... |
| `honeycomb-metrics-queries` | Load before querying a Honeycomb OpenTelemetry metrics dataset (dataset_type=metrics): gauges, counters, histograms and sums, including infrastructure metrics such as CPU, memor... |
| `honeycomb-observability-fundamentals` | Load when the operator asks a conceptual question about observability or Honeycomb: what observability is, why wide events, what high cardinality or dimensionality means, events... |
| `honeycomb-production-investigation` | Load when an investigation needs Honeycomb telemetry to find a root cause: a latency spike, an error surge, a deployment regression, a failing dependency or an SLO burning budge... |
| `honeycomb-query-patterns` | Load before building or reading a Honeycomb run_query on a trace, log or event dataset. Covers which operation to pick (percentiles and HEATMAP over AVG), relational fields (roo... |
| `honeycomb-slos-and-triggers` | Load before calling Honeycomb get_slos or get_triggers, or when an investigation must judge SLO compliance, error budget burn or trigger status. Explains what the numbers mean, ... |
| `honeycomb-verify-recent-trace` | Load when the operator asks to verify a recent test or deployment in Honeycomb, find the most recent trace, or show the trace a test produced. Finds the traces created since the... |

## Slash commands (4)

| Command | Purpose |
|---|---|
| `/honeycomb:build-board` | Create a curated Honeycomb Board with validated latency, error, and high-cardinality breakdown queries |
| `/honeycomb:investigate-anomaly` | Run high-cardinality Honeycomb BubbleUp, wide-event breakdown, and trace outlier investigation |
| `/honeycomb:triage-slo` | Triage Honeycomb SLO burn alerts, error budget exhaustion, and firing triggers |
| `/honeycomb:verify-instrumentation` | Audit OpenTelemetry trace structure, span propagation, and wide-event attribute quality in Honeycomb |

## Hooks

- **`hooks/secret-safety.py`** (`PreToolUse`): Prevents reading or echoing local credentials, `.env` files, private keys, and tokens.
