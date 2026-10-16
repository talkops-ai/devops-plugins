# AWS Solutions Architect

Principal AWS Solutions Architect (SAP-C02): evidence-backed 6-pillar Well-Architected Framework reviews (WAFR) & Lenses, MADR/Nygard Architectural Decision Records (ADRs) with One-Way vs Two-Way Door trade-off matrices, CDK/CloudFormation blueprint authoring with local cfn-lint & cfn-guard compliance verification, dual-horizon FinOps (greenfield TCO pricing + live Cost Explorer, Cost Optimization Hub & Compute Optimizer auditing), phased STRIDE threat modeling, enterprise multi-account Landing Zones (Control Tower, SCPs/RCPs, Data Perimeters, Cloud WAN, VPC Lattice), RTO/RPO multi-region DR & 7 Rs migration architecture, workload & lakehouse design (Serverless, Containers, Databases, S3 Tables/Iceberg, Bedrock & AgentCore, SageMaker, SDKs), and automated draw.io / Mermaid / C4 topology diagrams. Strictly read-only against live AWS environments.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-solutions-architect@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-solutions-architect.toml`](./codex/agents/aws-solutions-architect.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-solutions-architect`](./agents/aws-solutions-architect.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-solutions-architect:aws-solutions-architect` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-solutions-architect:aws-solutions-architect`
- Codex: install the custom agent above, then ask Codex to spawn `aws-solutions-architect`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.
- **Read-only on AWS.** The `aws-mutation-gate` hook (and `finops-sql-and-cost-gate` where bundled) denies mutating shell/MCP calls from this agent while keeping read-only `aws___call_aws` inspection available. Pair it with a read-only AWS profile (see `examples/`).

## Skills

| Skill | What it does |
|---|---|
| `amazon-bedrock` | Builds generative AI applications on Amazon Bedrock. |
| `aws-adr-generator` | Authors immutable MADR 3.0 and Nygard-style Architectural Decision Records (docs/adr/ADR-NNNN-<slug>.md) grounded in AWS Prescriptive Guidance, evaluating multi-option trade-off matrices across all 6 Well-Architected pi… |
| `aws-ai-ml` | Selects, deploys, and customizes AI models on Amazon SageMaker. |
| `aws-architecture-diagramming` | Generates C4 system context/container views, multi-AZ VPC network topologies, IAM/OAuth sequence flows, and validated .drawio XML / .drawio.svg / Mermaid / Python diagrams specifications using the drawio MCP server (@dr… |
| `aws-billing-and-cost-management` | Analyze AWS costs, find savings, manage budgets, evaluate Savings Plans and Reserved Instances, right-size EC2/Lambda/RDS/EBS with Compute Optimizer, look up service pricing, query CUR with Athena, detect cost anomalies… |
| `aws-blocks` | Guides building full-stack applications with AWS Blocks — an Infrastructure-from-Code framework. |
| `aws-cdk` | Authors, deploys, and troubleshoots AWS infrastructure using CDK with TypeScript or Python. |
| `aws-cloudformation` | Authors, validates, and troubleshoots AWS CloudFormation templates. |
| `aws-containers` | Builds and deploys containerized workloads on Elastic Kubernetes Service (EKS), Elastic Container Service (ECS), Fargate, and ECR (Elastic Container Registry). |
| `aws-data-analytics` | Architects modern transactional data lakes, zero-ETL pipelines, and analytical lakehouses using Amazon S3 Tables (managed Apache Iceberg), AWS Glue 5.1+, AWS Lake Formation (LF-TBAC), Amazon Athena, Amazon Redshift Serv… |
| `aws-database` | Routes any task involving AWS databases — choosing, comparing, recommending, getting started with, or operating a database — to the correct service-specific skill. |
| `aws-enterprise-landing-zone-and-networking` | Architects enterprise multi-account AWS Organizations and Control Tower Landing Zones, OU hierarchies, SCPs, Resource Control Policies (RCPs), Declarative Policies, AWS Data Perimeters, Shared VPCs (AWS RAM), VPC IPAM,… |
| `aws-iam` | Provides verified corrections for IAM behaviors that AI agents frequently get wrong — policy evaluation edge cases, trust policy gotchas, STS session limits, Organizations quirks, and SAML/MFA specifics. |
| `aws-messaging-and-streaming` | Guides general use of AWS messaging and streaming services. |
| `aws-observability` | Builds, configures, debugs, and optimizes AWS observability - operator-symptom questions and detecting Omni vs classic CloudWatch. |
| `aws-resilience-dr-and-migration-architecture` | Architects RTO/RPO-driven Multi-Region Disaster Recovery topologies (Backup & Restore, Pilot Light, Warm Standby, Active-Active), Cell-Based Architectures & Shuffle Sharding, Route 53 ARC (Zonal Autoshift, Routing Contr… |
| `aws-sdk-js-v3-usage` | AWS SDK for JavaScript v3 development patterns. |
| `aws-sdk-python-usage` | AWS SDK for Python (boto3/botocore) development patterns. |
| `aws-sdk-swift-usage` | AWS SDK for Swift development patterns. |
| `aws-serverless` | Builds, deploys, manages, debugs, configures, and optimizes serverless applications on AWS using Lambda, API Gateway, Step Functions, EventBridge, and SAM/CDK. |
| `aws-storage` | Selects, investigates, and compares AWS object, file, and block storage services, and answers cost, performance, configuration, security, and troubleshooting questions about storage services. |
| `aws-threat-modeling` | Executes phased STRIDE threat modeling across business context, trust boundaries, data asset flows, threat actors, OWASP LLM Top 10 / MITRE ATT&CK vectors, and AWS preventative/detective/responsive controls using the tm… |
| `aws-well-architected-review` | Performs a full AWS Well-Architected Framework review evaluating every framework question across all pillars discovered from the live AWS documentation by analyzing code, IaC, and configurations to produce evidence-back… |
| `signing-in-to-aws` | Gets AWS credentials for CLI/SDK access via `aws login`. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0` `--skip-auth --metadata` | `mcp__plugin_aws-solutions-architect_aws-mcp__*` | Managed AWS MCP Server: live read-only API introspection (aws___call_aws), remote sandboxed boto3 discovery scripts (aws___run_script), regional availability, and runtime skill retrieval. Guarded by aws-mutation-gate.py + IAM ReadOnlyAccess. |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-solutions-architect_awsknowledge__*` |  |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-solutions-architect_awspricing__*` |  |
| `iac` | stdio | `uvx fastmcp<4.0.0` `--with` | `mcp__plugin_aws-solutions-architect_iac__*` | Pinned to 0.2.14 with fastmcp<4.0.0 to prevent FastMCP 4.0 breaking import crashes (awslabs/mcp#4567). |
| `bcm` | stdio | `uvx awslabs.billing-cost-management-mcp-server@latest` | `mcp__plugin_aws-solutions-architect_bcm__*` |  |
| `tm` | stdio | `uvx git+https://github.com/awslabs/threat-modeling-mcp-server.git` | `mcp__plugin_aws-solutions-architect_tm__*` | Guided multi-phase STRIDE threat modeling across business context, trust boundaries, asset flows, and code mitigations; exports .threatmodel Markdown and JSON reports. |
| `drawio` | stdio | `npx @drawio/mcp` | `mcp__plugin_aws-solutions-architect_drawio__*` | Official JGraph draw.io MCP server for generating .drawio XML, .drawio.svg/.png, and Mermaid architecture and sequence diagrams. |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **SessionStart** `startup|resume` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/session-aws-preflight.py"`
- **PreToolUse** `Bash|Write|Edit|MultiEdit|use_aws|mcp__aws.*|mcp__plugin_aws-solutions-architect_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-solutions-architect_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PostToolUse** `Write|Edit|MultiEdit` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/iac-post-write-lint.py"`
- **Stop** `*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/turn-completion-verifier.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`aws-data-analytics`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`deploy-on-aws`](https://github.com/awslabs/agent-plugins) (awslabs/agent-plugins, Apache-2.0)
