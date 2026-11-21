# Elastic Observability & Security

Official Elastic SRE incident triage, service reliability, Kubernetes investigation, Cloud Security Posture (CSP), and LLM observability skills with bundled Elastic Agent Builder MCP configuration (`ELASTIC_PROJECT`, `ELASTIC_REGION`, `ELASTIC_API_KEY`).

Maintained by **Elastic** (skills redistributed unmodified from [`aws/tools-for-devops-agent`](https://github.com/aws/tools-for-devops-agent) under Apache-2.0).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install elastic@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install `elastic` |
| Other Agent Plugins hosts | Load this directory (`plugin.json`, `skills/`, `mcp.json`) |

## Configuration

Set `ELASTIC_API_KEY`, `ELASTIC_PROJECT`, and `ELASTIC_REGION` before starting your session. See [`CONNECTORS.md`](./CONNECTORS.md) for endpoint details.

## Skills (6)

| Skill | Description |
|---|---|
| `elastic-csp-investigation` | > |
| `elastic-k8s-investigation` | > |
| `elastic-llm-obs` | > |
| `elastic-onboarding` | > |
| `elastic-service-reliability` | > |
| `elastic-sre-triage` | > |

## Slash commands (4)

| Command | Purpose |
|---|---|
| `/elastic:audit-cloud-security` | Investigate Elastic Cloud Security Posture (CSP) misconfigurations, CIS benchmark findings, and cloud drift |
| `/elastic:audit-llm-telemetry` | Analyze GenAI/LLM token usage, latency, errors, and prompt/completion traces in Elastic Observability |
| `/elastic:investigate-k8s` | Investigate Kubernetes pod crashes, node pressure, and workload regressions in Elastic Observability |
| `/elastic:triage-incident` | Run Elastic SRE incident triage across APM service health, ES|QL logs, traces, and SLOs |

## Hooks

- **`hooks/secret-safety.py`** (`PreToolUse`): Prevents reading or echoing local credentials, `.env` files, private keys, and tokens.
