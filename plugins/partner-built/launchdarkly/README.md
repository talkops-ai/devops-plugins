# LaunchDarkly

Official LaunchDarkly feature flag management, progressive guarded rollouts, experimentation, observability (logs, traces, errors, sessions), and AI Config / Agent Control graph skills with bundled remote MCP configuration (`LAUNCHDARKLY_ACCESS_TOKEN`).

Maintained by **LaunchDarkly** (skills redistributed unmodified from [`aws/tools-for-devops-agent`](https://github.com/aws/tools-for-devops-agent) under Apache-2.0).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install launchdarkly@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install `launchdarkly` |
| Other Agent Plugins hosts | Load this directory (`plugin.json`, `skills/`, `mcp.json`) |

## Configuration

Set `LAUNCHDARKLY_ACCESS_TOKEN` (LaunchDarkly API access token; optional `LAUNCHDARKLY_MCP_URL` override, default `https://mcp.launchdarkly.com/mcp`) before starting your session. See [`CONNECTORS.md`](./CONNECTORS.md) for endpoint details.

## Skills (19)

| Skill | Description |
|---|---|
| `launchdarkly-agent-graphs` | Create and manage agent graphs — directed graphs of configs connected by edges with handoff logic. Use when building multi-agent workflows where configs route to each other. |
| `launchdarkly-alert-investigation` | Investigates a firing or recently fired observability alert: finds the firing and replays the value it evaluated, decides whether the alert is chronic noise or a new problem, re... |
| `launchdarkly-configs-create` | Create and configure configs in LaunchDarkly. Helps you choose between agent vs completion mode, create the config, add variations with models and prompts, and verify the setup. |
| `launchdarkly-configs-targeting` | Configure AgentControl config targeting to control which variation each context receives. Set the default rule or a percentage split, add attribute and segment rules, target ind... |
| `launchdarkly-configs-update` | Update, retire, and delete LaunchDarkly configs and their variations. Use when you need to modify config properties, change model parameters, update instructions or messages, ta... |
| `launchdarkly-configs-variations` | Experiment with configs by creating and managing variations. Helps you test different models, prompts, and parameters to find what works best through systematic experimentation. |
| `launchdarkly-create-graph` | Creates observability dashboards and graphs from logs, traces, errors, sessions, metrics, and events data by previewing charts inline and saving them to a dashboard. |
| `launchdarkly-custom-metrics` | Create, track, retrieve, update, and delete custom business metrics for configs. Covers full lifecycle: define metrics with the LaunchDarkly MCP server, emit events via SDK, and... |
| `launchdarkly-experiment-setup` | Set up and run experiments in LaunchDarkly. Create experiments with metrics, treatments, and flag config, start iterations to collect data, swap design between iterations, and s... |
| `launchdarkly-flag-command` | Resolve `/flag` style requests into the right LaunchDarkly flag lookup flow. Use when the user types `/flag`, asks to quickly find a flag by name/key, wants a direct flag detail... |
| `launchdarkly-flag-discovery` | Audit your LaunchDarkly feature flags to understand the landscape, find stale or launched flags, and assess removal readiness. Use when the user asks about flag debt, stale flag... |
| `launchdarkly-flag-release` | Record an automated rollout for an existing LaunchDarkly flag that guards a pull request's change, so the change releases safely when the PR merges. Honors a stated release inte... |
| `launchdarkly-flag-targeting` | Control LaunchDarkly feature flag targeting including toggling flags on/off, percentage rollouts, targeting rules, individual targets, and copying flag configurations between en... |
| `launchdarkly-guarded-rollout` | Configure guarded rollouts with progressive traffic increases, metric monitoring, and automatic rollback. Use when releasing features gradually with safety thresholds. |
| `launchdarkly-investigate` | Finds the root cause of a production problem from observability data (logs, traces, errors, sessions, metrics): scope and onset, what changed (deploys and flag changes), which h... |
| `launchdarkly-metric-choose` | Choose the right metrics for a LaunchDarkly experiment, guarded rollout, or release policy. Use when the user wants to know which metrics to use, which is the primary metric for... |
| `launchdarkly-online-evals` | Attach judges to config variations for automatic LLM-as-a-judge evaluation. Create custom judges, configure sampling rates, and monitor quality scores. |
| `launchdarkly-snippets` | Create and manage prompt snippets — reusable text blocks referenced inside config variation prompts. Keeps common instructions, personas, and guardrails consistent across multip... |
| `launchdarkly-tools` | Give your agents capabilities through tools (function calling). Helps you identify what your agent needs to do, create tool definitions, and attach them to config variations. |

## Slash commands (4)

| Command | Purpose |
|---|---|
| `/launchdarkly:audit-stale-flags` | Audit stale, temporary, or fully rolled-out LaunchDarkly feature flags ready for cleanup and code removal |
| `/launchdarkly:flag-rollout` | Create, target, or progressively roll out a LaunchDarkly feature flag with guarded release gates |
| `/launchdarkly:investigate-errors` | Triage production errors, traces, logs, and user sessions via LaunchDarkly Observability |
| `/launchdarkly:manage-ai-config` | Create, version, target, or inspect LaunchDarkly AI Configs and Agent Control graphs |

## Hooks

- **`hooks/secret-safety.py`** (`PreToolUse`): Prevents reading or echoing local credentials, `.env` files, private keys, and tokens.
