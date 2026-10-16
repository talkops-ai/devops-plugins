# AWS Modernization Agent

Migrates and modernizes codebases with AWS Transform: .NET Framework to .NET 8/10, mainframe COBOL to Java, VMware to EC2, SQL Server to Aurora, language and AWS SDK upgrades, and continuous tech-debt remediation.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-modernization-agent@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-modernization-agent.toml`](./codex/agents/aws-modernization-agent.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-modernization-agent`](./agents/aws-modernization-agent.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-modernization-agent:aws-modernization-agent` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-modernization-agent:aws-modernization-agent`
- Codex: install the custom agent above, then ask Codex to spawn `aws-modernization-agent`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills

| Skill | What it does |
|---|---|
| `app-data-layer-remediation` | Synchronizes application-layer SQL queries, stored procedure calls, and ORM persistence frameworks (JPA/Hibernate, MyBatis, EF Core) across Java, .NET, Node.js, and Python with DMS Schema Conversion when migrating Oracl… |
| `aws-billing-and-cost-management` | Analyze AWS costs, find savings, manage budgets, evaluate Savings Plans and Reserved Instances, right-size EC2/Lambda/RDS/EBS with Compute Optimizer, look up service pricing, query CUR with Athena, detect cost anomalies… |
| `aws-containers` | Builds and deploys containerized workloads on Elastic Kubernetes Service (EKS), Elastic Container Service (ECS), Fargate, and ECR (Elastic Container Registry). |
| `aws-lambda-microvms` | Builds, runs, debugs, and operates applications on AWS Lambda MicroVMs — Firecracker-isolated, snapshot-resumable serverless compute environments running inside a container with up to 8 hr lifetimes. |
| `aws-serverless` | Builds, deploys, manages, debugs, configures, and optimizes serverless applications on AWS using Lambda, API Gateway, Step Functions, EventBridge, and SAM/CDK. |
| `aws-transform` | Migrate, modernize, and upgrade codebases to AWS. |
| `aws-well-architected-review` | Performs a full AWS Well-Architected Framework review evaluating every framework question across all pillars discovered from the live AWS documentation by analyzing code, IaC, and configurations to produce evidence-back… |
| `creating-amazon-aurora-db-cluster-with-instances` | Creates a complete Amazon Aurora database cluster with instances, handling cluster creation, instance provisioning, and Secrets Manager password management in the proper sequence. |
| `creating-production-vpc-multi-az` | Creates a production-ready VPC with public and private subnets across multiple Availability Zones, including internet gateway, NAT gateways, route tables, and security groups following AWS Well-Architected principles. |
| `dms-schema-conversion` | Handles the full DMS Schema Conversion lifecycle including creating migration projects, converting database schemas to a target engine, running compatibility assessments, navigating metadata trees, exporting converted D… |
| `legacy-vm-and-mainframe-replatform` | Guides legacy VM containerization via AWS App2Container (A2C 5-stage workflow for Java and .NET to ECS, EKS Standard/Auto Mode, App Runner) standalone and via AWS MGN SSM automation. |
| `modernization-parity-and-cutover` | Engineers functional, data, and performance parity for modernized workloads using automated unit tests, Testcontainers (PostgreSQL, Kafka), REST/event contract tests, mainframe batch/online record-replay equivalence tes… |
| `modernization-strategy-and-strangler-fig` | Executes 7 Rs portfolio triage, bounded-context domain decomposition, distributed data patterns (Saga, Outbox, Idempotent Consumer), and multi-account Strangler Fig incremental routing using API Gateway Canary + SigV4 f… |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-transform-mcp` | stdio | `uvx awslabs.aws-transform-mcp-server@latest` | `mcp__plugin_aws-modernization-agent_aws-transform-mcp__*` |  |
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0` `--skip-auth --metadata` | `mcp__plugin_aws-modernization-agent_aws-mcp__*` | Managed AWS MCP Server via the toolkit's pinned proxy (aws___call_aws, aws___search_documentation, aws___retrieve_skill, ...). |
| `awsiac` | stdio | `uvx fastmcp<4.0.0` `--with` | `mcp__plugin_aws-modernization-agent_awsiac__*` | Pinned to 0.2.14 with fastmcp<4.0.0 to prevent FastMCP 4.0 breaking import crashes (awslabs/mcp#4567). |
| `postgres` | stdio | `uvx awslabs.postgres-mcp-server@latest` | `mcp__plugin_aws-modernization-agent_postgres__*` | Aurora/RDS PostgreSQL, read-only (no --allow_write_query). Pick the cluster at runtime with the connect_to_database tool; use a read-only database role. |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`aws-transform`](https://github.com/awslabs/agent-plugins) (awslabs/agent-plugins, Apache-2.0)
- [`specialized-skills/migration-and-modernization-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`core-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`specialized-skills/serverless-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`specialized-skills/database-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`specialized-skills/networking-and-content-delivery-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
