# Coralogix

Official Coralogix DataPrime log/span analytics, PromQL metrics, alerts, cases, service catalog, RUM, AI Center, dashboards, Olly, and TCO data-usage skills with bundled remote MCP configuration (`CORALOGIX_API_KEY`, `CORALOGIX_REGION`).

Maintained by **Coralogix** (skills redistributed unmodified from [`aws/tools-for-devops-agent`](https://github.com/aws/tools-for-devops-agent) under Apache-2.0).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install coralogix@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install `coralogix` |
| Other Agent Plugins hosts | Load this directory (`plugin.json`, `skills/`, `mcp.json`) |

## Configuration

Set `CORALOGIX_API_KEY` and `CORALOGIX_REGION` (`us1`, `us2`, `eu1`, `eu2`, `ap1`, `ap2`, `ap3`; default `us2`) before starting your session. See [`CONNECTORS.md`](./CONNECTORS.md) for endpoint details.

## Skills (19)

| Skill | Description |
|---|---|
| `coralogix-ai-center` | Coralogix AI Center — observe, evaluate, and guard GenAI/LLM applications and agents. Use for questions or actions about the user's AI/GenAI applications or agents — their behav... |
| `coralogix-alerts` | Alert and case terminology, alert definitions, alert events, cases, IDs, alert types, and skill routing. Load whenever working with alerts or cases to understand shared terminol... |
| `coralogix-case-analytics` | Fleet/aggregate analytics across many cases via the `system/labs.cases.state_updates` DataPrime dataset. Load when the user asks counts, trends, distributions or rates across ca... |
| `coralogix-case-management` | Create and change Coralogix Cases — open a case, comment, re-prioritise, assign, acknowledge, retitle, resolve, close, mute, link and unlink. Load when the user asks to "open a ... |
| `coralogix-cases` | Triage and manage Coralogix Cases. Load when a user wants to inspect a case, update it, add a comment, assign or acknowledge it, resolve or close it, change its priority, inspec... |
| `coralogix-dashboards` | Dashboard analysis and editing workflow and rules for using dashboard JSON, filters, variables, and time ranges. Load when the user provides dashboard context (for example a das... |
| `coralogix-data-usage` | Data usage, billing units, plan consumption, quota metrics, anomaly detection, and time-series analysis concepts and query workflow. Load when the user asks about data usage, in... |
| `coralogix-dataprime` | DataPrime query language for logs/spans/custom datasets (shared syntax, patterns, and rules). Load when you need to write a DataPrime query to explore logs or spans. Also load i... |
| `coralogix-datasets` | Dataset discovery and source-selection guidance for DataPrime system and user-defined datasets. Load when the user asks what datasets exist, how to use `list_datasets`, how to q... |
| `coralogix-docs` | Search and read official Coralogix platform documentation using **`search_docs`** and **`fetch_doc`**. Use when the user asks how Coralogix features work, how to configure or us... |
| `coralogix-infrastructure` | Find and inspect infrastructure resources: monitored resource types, resource inventory, health history, raw source data, and configuration changes. Load when the user asks to "... |
| `coralogix-logs` | Log-specific concepts, fields, field discovery usage, and troubleshooting patterns. The `coralogix-dataprime` skill should be loaded alongside this skill. Load when you need to ... |
| `coralogix-metrics-query` | PromQL fundamentals and metric discovery/query workflow. Load when you need to explore metrics in your investigation or to answer a question about metrics. For service-level RED... |
| `coralogix-olly` | - Use when the user wants to investigate or analyze data in Coralogix, or explicitly asks to use Olly. Examples: "ask Olly", "why is my service slow", "what alerts fired", "inve... |
| `coralogix-rum` | Use when the user asks to "query RUM", "cx_rum", "real user monitoring", "frontend errors", "browser errors", "mobile app crashes", "Web Vitals", "slow page load", "LCP", "CLS",... |
| `coralogix-service-catalog` | The fast, authoritative path for APM/RED data — error rate, latency percentiles (p50-p99), throughput, health status, resource saturation (CPU/memory/OOMKilled for k8s-pod, heap... |
| `coralogix-single-case` | Deep single-case investigation. Load when the user asks about one specific case by ID (UUID or readable id like "CASE-123") — e.g. summarize comments, explain who was notified w... |
| `coralogix-spans` | Span-specific concepts, fields, duration handling, and investigation patterns. Load when you need to explore spans in your investigation or to answer a question about spans. For... |
| `coralogix-views` | Manage Coralogix saved views and saved-view folders. Load when the user asks to create, update, delete, inspect, organize, or list saved log views. |

## Slash commands (4)

| Command | Purpose |
|---|---|
| `/coralogix:audit-tco` | Analyze Coralogix ingestion volume, TCO pipeline routing tiers, and high-cardinality telemetry waste |
| `/coralogix:build-dashboard` | Design and build a Coralogix Custom Dashboard backed by DataPrime and PromQL queries |
| `/coralogix:query-dataprime` | Author and execute Coralogix DataPrime log or span queries across Frequent Search and Archive tiers |
| `/coralogix:triage-incident` | Investigate active Coralogix alerts, cases, service catalog dependencies, errors, and deployment regressions |

## Hooks

- **`hooks/secret-safety.py`** (`PreToolUse`): Prevents reading or echoing local credentials, `.env` files, private keys, and tokens.
