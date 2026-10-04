# TalkOps DevOps Plugins

Agents, skills, and MCP connectors for DevOps and cloud operations. AWS comes first; other clouds and tools follow the same layout.

The marketplace is modelled on [anthropics/financial-services](https://github.com/anthropics/financial-services) and uses three kinds of plugin:

- **[Agent plugins](./plugins/agent-plugins)**: one named specialist agent per plugin. Every skill, command, hook, and MCP server in the plugin is bound to that agent, and the host runtime spawns the agent as a dynamic sub-agent. Each agent plugin is **self-contained**, so installing it is all you need.
- **[Vertical plugins](./plugins/vertical-plugins)**: domain bundles of skills, slash commands, and MCP servers that attach directly to the main agent, with no sub-agent hand-off. Install one when you want a specific capability in your own session.
- **[Partner-built](./plugins/partner-built)**: vendor plugins that keep the vendor's own content, name, and license, such as HashiCorp's official Terraform skills.

## Agents

| Function | Agent | What it does |
|---|---|---|
| **Build & deliver** | **[AWS IaC Engineer](./plugins/agent-plugins/aws-iac-engineer)** | CDK, CloudFormation, AWS Blocks, CI/CD pipelines: author, validate, deploy, troubleshoot |
| | **[AWS Deployment Agent](./plugins/agent-plugins/aws-deployment-agent)** | Codebase → hosting choice → cost estimate → IaC → deployed app, plus draw.io diagrams |
| | **[AWS Serverless Engineer](./plugins/agent-plugins/aws-serverless-engineer)** | Lambda (durable, managed instances, MicroVMs), API Gateway, Step Functions, SAM/CDK |
| | **[AWS Amplify Engineer](./plugins/agent-plugins/aws-amplify-engineer)** | Amplify Gen2 full-stack web and mobile apps |
| | **[AWS Location Engineer](./plugins/agent-plugins/aws-location-engineer)** | Maps, geocoding, places, routing, and geofencing with Amazon Location Service |
| **Platform & operations** | **[AWS Platform Engineer](./plugins/agent-plugins/aws-platform-engineer)** | EC2, EKS/ECS/Fargate, VPC and edge networking, storage, messaging |
| | **[AWS SRE Agent](./plugins/agent-plugins/aws-sre-agent)** | CloudWatch, Application Signals, X-Ray, CloudTrail, Prometheus, Support cases |
| | **[AWS DevSecOps Agent](./plugins/agent-plugins/aws-devsecops-agent)** | AWS DevOps Agent investigations and release readiness, AWS Security Agent scans and pentests |
| **Security & cost** | **[AWS Cloud Security Engineer](./plugins/agent-plugins/aws-cloud-security-engineer)** | IAM, Security Hub/GuardDuty findings, Secrets Manager, app auth |
| | **[AWS FinOps Agent](./plugins/agent-plugins/aws-finops-agent)** | Cost analysis, anomalies, budgets, Savings Plans/RIs, rightsizing, pricing |
| **Architecture & advisory** | **[AWS Solutions Architect](./plugins/agent-plugins/aws-solutions-architect)** | Well-Architected reviews, Bedrock and ML architectures, AWS SDK guidance |
| | **[AWS Startup Advisor](./plugins/agent-plugins/aws-startup-advisor)** | Stage-aware advice, scaffolding, Azure/GCP/Heroku → AWS, LLM → Bedrock, Activate |
| | **[AWS Codebase Documentor](./plugins/agent-plugins/aws-codebase-documentor)** | Turns undocumented code into cited technical docs and architecture views |
| **Data & AI** | **[AWS Data Engineer](./plugins/agent-plugins/aws-data-engineer)** | S3 Tables/Iceberg, Glue, Athena, Redshift, S3 Vectors, OpenSearch, MWAA |
| | **[AWS Database Engineer](./plugins/agent-plugins/aws-database-engineer)** | Database selection, Aurora DSQL, DynamoDB, migrations, and query tuning |
| | **[AWS AgentCore Engineer](./plugins/agent-plugins/aws-agentcore-engineer)** | Build, deploy, harden, and debug agents on Bedrock AgentCore |
| | **[AWS SageMaker Engineer](./plugins/agent-plugins/aws-sagemaker-engineer)** | Fine-tuning, evaluation, and deployment on SageMaker AI, plus HyperPod operations |
| **Migration & modernization** | **[AWS Modernization Agent](./plugins/agent-plugins/aws-modernization-agent)** | AWS Transform: .NET, COBOL, VMware, SQL Server, and language/SDK upgrades |

Each plugin's own README lists its skills, MCP servers, hooks, and upstream sources.

## Verticals

| Domain | Vertical plugins |
|---|---|
| **Foundation** | [`aws-essentials`](./plugins/vertical-plugins/aws-essentials) (sign-in, SDK usage, docs) |
| **Build** | [`aws-infrastructure-as-code`](./plugins/vertical-plugins/aws-infrastructure-as-code) · [`aws-serverless`](./plugins/vertical-plugins/aws-serverless) · [`aws-web-and-mobile`](./plugins/vertical-plugins/aws-web-and-mobile) |
| **Platform** | [`aws-compute`](./plugins/vertical-plugins/aws-compute) · [`aws-containers`](./plugins/vertical-plugins/aws-containers) · [`aws-networking`](./plugins/vertical-plugins/aws-networking) · [`aws-storage`](./plugins/vertical-plugins/aws-storage) · [`aws-messaging-and-streaming`](./plugins/vertical-plugins/aws-messaging-and-streaming) |
| **Data & AI** | [`aws-databases`](./plugins/vertical-plugins/aws-databases) · [`aws-analytics`](./plugins/vertical-plugins/aws-analytics) · [`aws-ai-ml`](./plugins/vertical-plugins/aws-ai-ml) |
| **Operate** | [`aws-observability`](./plugins/vertical-plugins/aws-observability) · [`aws-resilience`](./plugins/vertical-plugins/aws-resilience) |
| **Secure & govern** | [`aws-security-identity`](./plugins/vertical-plugins/aws-security-identity) · [`aws-cost-optimization`](./plugins/vertical-plugins/aws-cost-optimization) · [`aws-well-architected`](./plugins/vertical-plugins/aws-well-architected) |
| **Modernize** | [`aws-migration`](./plugins/vertical-plugins/aws-migration) |
| **Specialty** | [`aws-marketplace-seller`](./plugins/vertical-plugins/aws-marketplace-seller) · [`aws-end-user-computing`](./plugins/vertical-plugins/aws-end-user-computing) · [`aws-quantum-computing`](./plugins/vertical-plugins/aws-quantum-computing) |

The [vertical index](./plugins/vertical-plugins) lists every vertical's commands, MCP servers, and the agent plugin that covers the same ground.

## Partner-built

| Plugin | Vendor | What it holds |
|---|---|---|
| [`terraform`](./plugins/partner-built/terraform) | HashiCorp (MPL-2.0) | All 16 official Terraform skills: style, modules, tests, search/import, Stacks, policy, Azure Verified Modules, and provider development. Cloud-agnostic; attaches to the main agent. |

## Getting started

### Claude Code

```bash
# Add the marketplace
claude plugin marketplace add talkops-ai/devops-plugins

# Install the agents you need
claude plugin install aws-sre-agent@talkops-devops-plugins
claude plugin install aws-iac-engineer@talkops-devops-plugins

# ...or attach domain skills directly to your main agent
claude plugin install aws-networking@talkops-devops-plugins
```

Claude delegates to an installed agent automatically based on its description. You can also invoke one explicitly with `@agent-<plugin>:<agent>`, or run it as the main thread:

```bash
claude --agent aws-sre-agent:aws-sre-agent
```

### Codex

```bash
# Add the marketplace (Codex reads .agents/plugins/marketplace.json)
codex plugin marketplace add talkops-ai/devops-plugins
```

Then install plugins from the Plugins Directory (`/plugins`), or enable them in `~/.codex/config.toml`:

```toml
[plugins."aws-iac-engineer@talkops-devops-plugins"]
enabled = true
```

Codex loads each plugin's skills, MCP servers (from the portable `mcp.json`), and hooks. Approve the hooks when Codex asks you to trust them. Codex plugins can't bundle agents, so each agent plugin also ships a Codex custom agent. To use the specialist as a sub-agent, copy it into your agents directory:

```bash
cp plugins/agent-plugins/aws-iac-engineer/codex/agents/aws-iac-engineer.toml ~/.codex/agents/
```

Codex starts MCP servers with a minimal environment. If a server can't see your AWS profile, set `AWS_PROFILE` and `AWS_REGION` for it in `~/.codex/config.toml`.

### Other agent hosts

Every agent and vertical plugin also follows the portable [Agent Plugins 1.0.0](https://agent-plugins.org) format: `plugin.json`, `skills/`, and `mcp.json` at the plugin root. Any host that implements it (Cursor, GitHub Copilot, and others) can load the skills and MCP servers. Sub-agents, slash commands, and hooks depend on the host.

| Capability | Claude Code | Codex | Other Agent Plugins hosts |
|---|---|---|---|
| Skills | yes | yes | yes |
| Bundled MCP servers | yes (`.mcp.json`) | yes (`mcp.json`) | yes (`mcp.json`) |
| Specialist sub-agent | yes (`agents/`) | copy `codex/agents/<name>.toml` | host-dependent |
| Hooks (secret safety, mutation gate) | yes | yes, after trust | host-dependent |
| Slash commands | yes | no (skills still apply) | host-dependent |

### Prerequisites

- [`uv`](https://docs.astral.sh/uv/) so that `uvx` can launch the stdio MCP servers.
- AWS CLI v2. Credentials come from your environment (`AWS_PROFILE`, SSO, or an instance role). Every agent bundles `signing-in-to-aws` for `aws login`.
- `AWS_REGION` defaults to `us-east-1` in Claude Code when it isn't set; on other hosts, set it in your environment.
- Python 3 on `PATH` for the safety hooks.
- Agent-specific extras are listed in each plugin README, for example `DEVOPS_AGENT_TOKEN` for the DevSecOps agent, and the `agentcore` CLI for AgentCore. The `terraform` partner plugin's optional registry connector needs Docker.

## Safety model

Three layers keep agents from changing AWS by accident:

1. **Server side (all hosts).** Bundled awslabs servers start read-only unless the upstream plugin shipped them with write access. The read-only agents (`aws-sre-agent`, `aws-finops-agent`, `aws-solutions-architect`) run the managed AWS MCP server with `--read-only`, which removes its API-call tools.
2. **`aws-mutation-gate` hook.** Every agent plugin checks shell and AWS MCP calls for mutating `aws`, `terraform`, `cdk`, `sam`, `eksctl`, `kubectl`, `helm`, `copilot`, and `amplify` operations. In Claude Code it blocks them for read-only agents and asks for confirmation otherwise. In Codex it adds a warning, and Codex's approval policy decides. Override with `TALKOPS_AWS_MUTATION_GATE=off|warn|ask|deny`.
3. **IAM.** The real boundary. See [docs/iam-guardrails.md](./docs/iam-guardrails.md) for read-only roles and the managed AWS MCP condition keys.

## How MCP servers bind to agents

Claude Code ignores `mcpServers`, `hooks`, and `permissionMode` in a plugin agent's frontmatter. These plugins bind MCP servers this way instead:

1. Each server is declared in the plugin's `.mcp.json`.
2. The agent's `tools:` allowlist grants that server by pattern, `mcp__plugin_<plugin>_<server>__*`.
3. Hooks are declared in `hooks/hooks.json`, using `${CLAUDE_PLUGIN_ROOT}` paths.

As a result, an agent can only reach its own servers. `scripts/validate_plugins.py` checks both directions: every declared server is bound to the agent, and every bound pattern has a server. Vertical plugins skip the binding step; their servers are available to the main agent.

The defaults are conservative. awslabs servers start read-only unless the upstream plugin already shipped them with write access.

**Connectors.** Plugin MCP files have no reliable "disabled" switch across hosts (Claude Code ignores `"disabled": true`; the portable schema has none), so servers that need a connection target or local runtime at startup (Aurora DSQL, DocumentDB, Neptune, Valkey, SQL Server, Oracle, scoped Lambda/Step Functions tools, the Terraform registry server, ...) are not bundled. Plugins list them in `CONNECTORS.md` with `claude mcp add`, `codex mcp add`, and `config.toml` snippets, and agent plugins pre-authorize them as `mcp__<key>__*`. [docs/mcp-server-coverage.md](./docs/mcp-server-coverage.md) shows how every awslabs/mcp server is used: bundled, connector, or not used (with the reason).

## Repository layout

```
.claude-plugin/marketplace.json   # Claude Code marketplace catalog (name: talkops-devops-plugins)
.agents/plugins/marketplace.json  # Codex marketplace catalog (generated)
plugins/
  agent-plugins/<agent>/          # .claude-plugin/plugin.json · agents/<agent>.md · skills/ · .mcp.json · hooks/ · commands/
                                  # plugin.json · mcp.json (portable) · .codex-plugin/plugin.json · codex/agents/<agent>.toml
  vertical-plugins/<domain>/      # .claude-plugin/plugin.json · skills/ · commands/ · .mcp.json · CONNECTORS.md
                                  # plugin.json · mcp.json (portable) · .codex-plugin/plugin.json
  partner-built/<plugin>/         # vendor plugins ("kind": "partner"): vendor identity + license, same three layouts
src/
  hooks/aws-mutation-gate.py      # TalkOps-authored hook, copied into every agent plugin by the sync
scripts/
  aws-plugin-map.json             # source of truth: upstream → plugin mapping, MCP/connector catalogs, host settings
  sync_aws_plugins.py             # regenerates the AWS agent and vertical plugins from upstream
  validate_plugins.py             # structural, binding, portable-format, and Codex validation
  render_handover_docs.py         # renders docs/handover/ (audit handbooks)
  handover-notes.json             # curated rationale and known gaps for the handbooks
docs/
  authoring-agent-plugins.md      # standards for writing new plugins
  iam-guardrails.md               # IAM patterns that back the agents' read-only and approval rules
  mcp-server-coverage.md          # generated: how each awslabs/mcp server is used
  handover/                       # generated: per-plugin audit handbooks (agent and vertical)
```

## Maintaining the AWS plugins

The AWS plugins are generated from upstream open-source repositories. `scripts/aws-plugin-map.json` maps each upstream into agent and vertical plugins. The upstream repos are checked out under `reference/`, which is gitignored:

| `reference/` path | Upstream |
|---|---|
| `agent-toolkit-for-aws` | [aws/agent-toolkit-for-aws](https://github.com/aws/agent-toolkit-for-aws) (plugins, core and specialized skills) |
| `agent-plugins` | [awslabs/agent-plugins](https://github.com/awslabs/agent-plugins) |
| `hashicorp-agent-skills` | [hashicorp/agent-skills](https://github.com/hashicorp/agent-skills) (Terraform skills for the IaC engineer, MPL-2.0) |
| `mcp` | [awslabs/mcp](https://github.com/awslabs/mcp) (MCP server catalog) |

```bash
python3 scripts/sync_aws_plugins.py                 # regenerate all AWS plugins + MCP coverage doc
python3 scripts/sync_aws_plugins.py --kind vertical # only vertical plugins
python3 scripts/sync_aws_plugins.py --only aws-sre-agent --dry-run
python3 scripts/validate_plugins.py --claude        # validate (and run `claude plugin validate`)
python3 scripts/render_handover_docs.py             # refresh the audit handbooks in docs/handover/
```

The sync owns `skills/`, `scripts/`, `hooks/`, `codex/`, `.mcp.json`, `mcp.json`, `plugin.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `CONNECTORS.md`, each plugin README (plus `commands/` in agent plugins), and both marketplace files. It never touches hand-written files: `agents/<agent>.md` in agent plugins, `commands/*.md` in vertical plugins, and `src/`. If an upstream file it patches has drifted, or a new awslabs/mcp server is not yet accounted for, the sync fails loudly.

For review and handover, [docs/handover/agent-plugins.md](./docs/handover/agent-plugins.md) and [docs/handover/vertical-plugins.md](./docs/handover/vertical-plugins.md) document every plugin: skills and their upstream provenance, agent definition, MCP launch configs, connectors, hooks, rewrites, design notes, automated findings, and an audit checklist.

See [docs/authoring-agent-plugins.md](./docs/authoring-agent-plugins.md) before adding a plugin.

## License

Apache-2.0. See [LICENSE](./LICENSE) and [NOTICE](./NOTICE) for upstream attribution.
