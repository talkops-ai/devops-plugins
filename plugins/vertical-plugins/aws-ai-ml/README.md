# AWS AI and Machine Learning

Production Generative AI, Agentic AI, and ML engineering for the main agent: Amazon Bedrock (Converse API, Knowledge Bases, Guardrails, LLM migration), Amazon Bedrock AgentCore (Build, Connect, Deploy, Harden, Debug, Optimize, Pay) & Strands Agents, and Amazon SageMaker AI (Training, Inference, Fine-Tuning, MLOps Pipelines, Cost Estimation, Endpoint Diagnostics).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-ai-ml@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-agentcore-engineer`](../../agent-plugins/aws-agentcore-engineer) or [`aws-sagemaker-engineer`](../../agent-plugins/aws-sagemaker-engineer) or [`aws-solutions-architect`](../../agent-plugins/aws-solutions-architect) or [`aws-startup-advisor`](../../agent-plugins/aws-startup-advisor) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-ai-ml:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-ai-ml:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `agent-advisor` | Entry point for AI-agent work on AWS: pick a runtime, plan a migration for existing workloads, and build an executable POC — one phased flow. |
| `agents-build` | > |
| `agents-connect` | > |
| `agents-debug` | > |
| `agents-deploy` | > |
| `agents-get-started` | > |
| `agents-harden` | > |
| `agents-optimize` | > |
| `agents-pay` | > |
| `ai-to-bedrock` | >- |
| `amazon-bedrock` | Builds generative AI applications on Amazon Bedrock. |
| `aws-ai-ml` | > |
| `endpoint-diagnostics` | >- |
| `finetuning` | >- |
| `llm-to-bedrock` | Use when the user wants to migrate code that calls OpenAI, Gemini/Google AI, or the Anthropic API to Amazon Bedrock — a pure model/SDK rewrite. |
| `model-deployment` | >- |
| `sagemaker-cost-estimator` | >- |
| `sagemaker-domain-vpc-iac` | >- |
| `sagemaker-inference-architect` | >- |
| `sagemaker-mlops-pipelines` | >- |
| `sagemaker-observability-governance` | >- |
| `sagemaker-solution-architect` | >- |
| `sagemaker-training-architect` | >- |

## Commands

| Command | Description |
|---|---|
| `/aws-ai-ml:agentcore-deploy` | Deploy, harden (Cedar policy + Cognito OAuth), monitor, and cost-optimize an agent on Amazon Bedrock AgentCore Runtime. |
| `/aws-ai-ml:bedrock-agent` | Architect and build an Amazon Bedrock or Strands Agent with tool definitions, Guardrails, and Knowledge Base integration. |
| `/aws-ai-ml:genai-rag` | Design a production RAG pipeline using Amazon Bedrock Knowledge Bases, OpenSearch Serverless/Aurora pgvector, chunking strategies, and Guardrails. |
| `/aws-ai-ml:migrate-llm-to-bedrock` | Migrate existing OpenAI, Anthropic, or Gemini SDK code to the Amazon Bedrock Converse API with model mapping and prompt parity. |
| `/aws-ai-ml:sagemaker-endpoint-triage` | Diagnose SageMaker inference endpoint ModelError/5xx failures, container OOMs, cold starts, and auto-scaling bottlenecks. |
| `/aws-ai-ml:sagemaker-job` | Architect, launch, or right-size an Amazon SageMaker training/fine-tuning job or inference endpoint with cost and GPU memory calculation. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-ai-ml_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-ai-ml_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `sagemaker` | stdio | `uvx awslabs.sagemaker-ai-mcp-server@latest` | `mcp__plugin_aws-ai-ml_sagemaker__*` | Amazon SageMaker AI training jobs, endpoints, models, and HyperPod cluster management. |
| `agentcore` | stdio | `uvx awslabs.amazon-bedrock-agentcore-mcp-server@latest` | `mcp__plugin_aws-ai-ml_agentcore__*` | Amazon Bedrock AgentCore runtime, gateway, memory, identity, and observability tools. |
| `strands-agents` | stdio | `uvx strands-agents-mcp-server@latest` | `mcp__plugin_aws-ai-ml_strands-agents__*` | Strands Agents SDK documentation, multi-agent patterns, and tool definitions. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-ai-ml_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-ai-ml_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-ai-ml_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-ai-ml_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-ai-ml_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
