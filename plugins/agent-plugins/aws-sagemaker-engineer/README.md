# AWS SageMaker Engineer

Principal Amazon SageMaker AI Solutions Architect & ML Platform Engineer: Well-Architected ML design, Studio Domain VpcOnly/PrivateLink/KMS/IAM IaC, pre-provisioning FinOps cost estimation, Foundation Model SFT/DPO/RLVR/RLAIF customization, custom/distributed training (@remote, Estimators, Vision/SAM, DDP/FSDP, Spot, Autopilot v2), production inference (InferenceComponent bin-packing, Scale-to-Zero, LMI/vLLM, Inferentia2, MCE, MME, Serverless, Async, Batch), MLOps Pipelines/Feature Store/Model Registry/MLflow/Catalog SQL, Deployment Guardrails, Model Monitor drift detection, and HyperPod EKS/Slurm operations.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-sagemaker-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-sagemaker-engineer.toml`](./codex/agents/aws-sagemaker-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-sagemaker-engineer`](./agents/aws-sagemaker-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-sagemaker-engineer:aws-sagemaker-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-sagemaker-engineer:aws-sagemaker-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `aws-sagemaker-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills

| Skill | What it does |
|---|---|
| `dataset-evaluation` | Validates dataset formatting and quality for SageMaker model fine-tuning (SFT, DPO, or RLVR). |
| `dataset-transformation` | Generates code that transforms datasets between ML schemas for model training or evaluation. |
| `directory-management` | Manages project directory setup and artifact organization. |
| `endpoint-diagnostics` | Collects deterministic, read-only diagnostic information from a SageMaker AI endpoint using documented AWS APIs and CloudWatch MCP tools. |
| `finetuning` | Generates code that initiates a SageMaker Serverless Model Customization job and optionally creates a reward function for RLVR or configures RLAIF. |
| `finetuning-technique` | Selects a fine-tuning technique (SFT, DPO, RLVR, or RLAIF) for the user's use case and validates it against the selected model's available recipes. |
| `hyperpod-cluster-debugger` | Diagnose and remediate cluster-wide HyperPod (EKS or Slurm) problems — creation / deployment failures (CloudFormation, EFA health check, lifecycle scripts, capacity), EKS access, node replacement, CloudFormation nested-… |
| `hyperpod-issue-report` | Generate comprehensive issue reports from HyperPod clusters (EKS and Slurm) by collecting diagnostic logs and configurations for troubleshooting and AWS Support cases. |
| `hyperpod-nccl` | Diagnose NCCL failures and adjacent training-pod failures on HyperPod GPU clusters (EKS or Slurm) — training hangs, AllReduce / collective-op timeouts, EFA or libfabric errors, rendezvous failures, EFA TCP fallback, /de… |
| `hyperpod-node-debugger` | Diagnose and remediate per-node issues on a HyperPod cluster (EKS or Slurm) — a specific node is unhealthy, unresponsive, stuck, or needs replacing. |
| `hyperpod-performance-debugger` | Diagnose performance issues on Amazon SageMaker HyperPod clusters — uneven NCCL bandwidth across nodes and poor filesystem throughput. |
| `hyperpod-slurm-debugger` | Diagnostic-only skill for Slurm scheduler and node-daemon issues on Amazon SageMaker HyperPod Slurm clusters. |
| `hyperpod-ssm` | Remote command execution and file transfer on SageMaker HyperPod cluster nodes via AWS Systems Manager (SSM). |
| `hyperpod-version-checker` | Check and compare software component versions on SageMaker HyperPod cluster nodes - NVIDIA drivers, CUDA toolkit, cuDNN, NCCL, EFA, AWS OFI NCCL, GDRCopy, MPI, Neuron SDK (Trainium/Inferentia), Python, and PyTorch. |
| `manage-mlflow` | Manages the full lifecycle of Amazon SageMaker Managed MLflow Apps: discover existing apps, create new apps, update configuration, and safely delete using the modern MLflow App APIs (CreateMlflowApp, ListMlflowApps, Des… |
| `model-deployment` | Deploys fine-tuned models (Nova or OSS LoRA from SageMaker Serverless Model Customization) to SageMaker endpoints or Amazon Bedrock, deploys open-weight JumpStart foundation models to SageMaker real-time endpoints, and… |
| `model-evaluation` | Generates python code that evaluates SageMaker models. |
| `model-selection` | Selects a base model or ML algorithm pathway for the user's use case. |
| `planning` | Discovers user intent and generates a structured, step-by-step execution and architectural plan across the entire Amazon SageMaker AI lifecycle — including Well-Architected ML solution design, Studio Domain VPC/IAM/KMS… |
| `querying-aws-sagemaker-catalog` | Runs SQL analytics on SageMaker Catalog asset metadata tables exported as Apache Iceberg in S3 Tables. |
| `sagemaker-cost-estimator` | Calculates pre-provisioning FinOps cost estimates and architectural savings comparisons for Amazon SageMaker AI workloads using live queries to the awspricing MCP server. |
| `sagemaker-domain-vpc-iac` | Architects and generates production-grade AWS CDK (TypeScript/Python) and CloudFormation Infrastructure-as-Code for Amazon SageMaker AI Studio Domains, User Profiles, Private/Shared Spaces (JupyterLab & CodeEditor), Cus… |
| `sagemaker-inference-architect` | Architects and generates production inference and model-hosting solutions across all Amazon SageMaker AI deployment patterns. |
| `sagemaker-mlops-pipelines` | Architects and generates end-to-end MLOps automation on Amazon SageMaker AI. |
| `sagemaker-observability-governance` | Architects production observability, safe deployment guardrails, drift monitoring, and root-cause diagnostics for Amazon SageMaker AI. |
| `sagemaker-solution-architect` | Designs end-to-end Amazon SageMaker AI architectures grounded in the AWS Well-Architected Machine Learning Lens and Responsible AI Lens. |
| `sagemaker-training-architect` | Architects and generates production training code for Amazon SageMaker AI Managed Training Jobs, Distributed Training, Custom Vision/Multimodal Fine-Tuning, and AutoML. |
| `sdk-getting-started` | Validates the user's local and cloud environment for SageMaker AI operations — checks SageMaker Python SDK v3 version (>=3.17.0,<4.0), AWS region, execution role trust/permissions, and local MCP/IaC platform prerequisit… |
| `signing-in-to-aws` | Gets AWS credentials for CLI/SDK access via `aws login`. |
| `use-case-specification` | Creates a reusable use case specification file (*_use_case_spec.md) that defines the business problem, stakeholders, measurable success criteria (Success Tenets for fine-tuning), deployment constraints (for base model d… |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws@latest` | `mcp__plugin_aws-sagemaker-engineer_aws-mcp__*` | Managed AWS MCP Server via the proxy used by awslabs/agent-plugins. |
| `sagemaker` | stdio | `uvx awslabs.sagemaker-ai-mcp-server@latest` | `mcp__plugin_aws-sagemaker-engineer_sagemaker__*` | Read-only by default. Add --allow-write / --allow-sensitive-data-access to enable mutations. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-sagemaker-engineer_awspricing__*` |  |
| `awsiac` | stdio | `uvx fastmcp<4.0.0` `--with` | `mcp__plugin_aws-sagemaker-engineer_awsiac__*` | Pinned to 0.2.14 with fastmcp<4.0.0 to prevent FastMCP 4.0 breaking import crashes (awslabs/mcp#4567). |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-sagemaker-engineer_cloudwatch__*` |  |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-sagemaker-engineer_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-sagemaker-engineer_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`sagemaker-ai`](https://github.com/awslabs/agent-plugins) (awslabs/agent-plugins, Apache-2.0)
- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`specialized-skills/system-table-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
