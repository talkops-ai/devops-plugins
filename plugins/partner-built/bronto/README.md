# Bronto Log Analytics

Official Bronto dataset/collection discovery, SQL-style log search and time-series aggregation, and production error spike investigation skills with bundled remote MCP configuration (`BRONTO_API_KEY`, `BRONTO_REGION`).

Maintained by **Bronto** (skills redistributed unmodified from [`aws/tools-for-devops-agent`](https://github.com/aws/tools-for-devops-agent) under Apache-2.0).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install bronto@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install `bronto` |
| Other Agent Plugins hosts | Load this directory (`plugin.json`, `skills/`, `mcp.json`) |

## Configuration

Set `BRONTO_API_KEY` and `BRONTO_REGION` (`us` or `eu`; default `us`) before starting your session. See [`CONNECTORS.md`](./CONNECTORS.md) for endpoint details.

## Skills (3)

| Skill | Description |
|---|---|
| `bronto-dataset-discovery` | Load this skill when investigating an incident or answering a question that needs logs from Bronto and the dataset that holds them is not already known - for example a service, ... |
| `bronto-error-investigation` | Load this skill when an investigation needs to explain errors in logs held in Bronto - an error surge, a failing service, a specific error event or a Bronto monitor alert. It is... |
| `bronto-log-search` | Load this skill before writing or running a Bronto log search - counting, grouping, trending or fetching log events with the Bronto MCP tools. It explains which tool answers whi... |

## Slash commands (3)

| Command | Purpose |
|---|---|
| `/bronto:discover-logs` | Discover Bronto log collections, datasets, tags, and parsed schema attributes |
| `/bronto:investigate-spike` | Investigate a production error or latency spike in Bronto logs and isolate top offending dimensions |
| `/bronto:search-logs` | Execute targeted Bronto SQL-style log searches and time-series aggregations |

## Hooks

- **`hooks/secret-safety.py`** (`PreToolUse`): Prevents reading or echoing local credentials, `.env` files, private keys, and tokens.
