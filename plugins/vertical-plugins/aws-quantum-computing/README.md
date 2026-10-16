# AWS Quantum Computing

Quantum computing and hybrid algorithm engineering on Amazon Braket for the main agent: OpenQASM 3.0 & Braket SDK circuit design, Managed Simulators (SV1, DM1, TN1), QPU hardware targeting (IonQ, Rigetti, IQM, QuEra), Braket Hybrid Jobs (VQE, QAOA, PennyLane adjoint differentiation), pre-execution shot/task cost governance, and VPC/KMS security.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-quantum-computing@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-solutions-architect`](../../agent-plugins/aws-solutions-architect) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-quantum-computing:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-quantum-computing:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `amazon-braket` | Runs quantum computing workflows on AWS through Amazon Braket — discovering devices (QPUs and simulators) and their availability, building gate-model circuits and analog Hamiltonian programs, submitt… |
| `braket-cost-governance-and-security` | Enforce pre-execution QPU and simulator cost estimation, budget circuit breakers, S3 KMS encryption, VPC private networking, and IAM least-privilege execution roles for Amazon Braket quantum workload… |
| `braket-hybrid-jobs-and-algorithms` | Design, containerize, and execute Amazon Braket Hybrid Quantum-Classical Jobs (QAOA, VQE, QML, PennyLane, Qiskit-Braket), manage checkpointing and hyperparameters, and select optimal simulators (SV1,… |

## Commands

| Command | Description |
|---|---|
| `/aws-quantum-computing:debug-quantum-task` | Inspect a failed or queued Braket Quantum Task or Hybrid Job, check QPU availability windows and device calibration fidelity, and diagnose CloudWatch logs. |
| `/aws-quantum-computing:design-circuit` | Design a quantum circuit or Analog Hamiltonian Simulation using the Amazon Braket Python SDK / OpenQASM 3.0 and validate it on the local simulator. |
| `/aws-quantum-computing:estimate-braket-cost` | Calculate the exact QPU per-shot/per-task fee, managed simulator duration cost, and Hybrid Job instance cost before submitting quantum workloads. |
| `/aws-quantum-computing:launch-hybrid-job` | Package and launch an Amazon Braket Hybrid Quantum-Classical Job with priority QPU queueing, S3 checkpointing, and PennyLane/Qiskit integration. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-quantum-computing_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-quantum-computing_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-quantum-computing_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-quantum-computing_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-quantum-computing_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-quantum-computing_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
