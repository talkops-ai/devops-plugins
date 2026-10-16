# AWS Well-Architected

Principal Solutions Architecture toolkit for the main agent: AWS Well-Architected Six-Pillar reviews, MADR 3.0 Architecture Decision Records (ADRs), Draw.io & Mermaid architecture diagrams, STRIDE threat modeling, multi-account Landing Zone design, and multi-region DR architecture.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-well-architected@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-solutions-architect`](../../agent-plugins/aws-solutions-architect) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-well-architected:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-well-architected:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `aws-adr-generator` | Authors immutable MADR 3.0 and Nygard-style Architectural Decision Records (docs/adr/ADR-NNNN-<slug>.md) grounded in AWS Prescriptive Guidance, evaluating multi-option trade-off matrices across all 6… |
| `aws-architecture-diagramming` | Generates C4 system context/container views, multi-AZ VPC network topologies, IAM/OAuth sequence flows, and validated .drawio XML / .drawio.svg / Mermaid / Python diagrams specifications using the dr… |
| `aws-enterprise-landing-zone-and-networking` | Architects enterprise multi-account AWS Organizations and Control Tower Landing Zones, OU hierarchies, SCPs, Resource Control Policies (RCPs), Declarative Policies, AWS Data Perimeters, Shared VPCs (… |
| `aws-resilience-dr-and-migration-architecture` | Architects RTO/RPO-driven Multi-Region Disaster Recovery topologies (Backup & Restore, Pilot Light, Warm Standby, Active-Active), Cell-Based Architectures & Shuffle Sharding, Route 53 ARC (Zonal Auto… |
| `aws-threat-modeling` | Executes phased STRIDE threat modeling across business context, trust boundaries, data asset flows, threat actors, OWASP LLM Top 10 / MITRE ATT&CK vectors, and AWS preventative/detective/responsive c… |
| `aws-well-architected-review` | Performs a full AWS Well-Architected Framework review evaluating every framework question across all pillars discovered from the live AWS documentation by analyzing code, IaC, and configurations to p… |

## Commands

| Command | Description |
|---|---|
| `/aws-well-architected:architecture-diagram` | Generate an AWS 2026 architecture diagram (Draw.io & Mermaid) with VPC/AZ boundaries, IAM trust edges, and numbered data flows. |
| `/aws-well-architected:generate-adr` | Author a MADR 3.0 Architecture Decision Record (ADR) with option trade-offs, Well-Architected pillar alignment, and FinOps TCO impact. |
| `/aws-well-architected:landing-zone-design` | Design a multi-account AWS Control Tower Landing Zone with OU hierarchy, SCP/RCP guardrails, IAM Identity Center, and centralized networking/logging. |
| `/aws-well-architected:review` | Conduct an evidence-based AWS Well-Architected Framework review across all Six Pillars with High/Medium Risk Issues (HRIs/MRIs) and remediation plans. |
| `/aws-well-architected:threat-model` | Produce a comprehensive STRIDE threat model and AWS Threat Composer `.tc.json` specification mapped to AWS security controls. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-well-architected_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-well-architected_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `wa-security` | stdio | `uvx awslabs.well-architected-security-mcp-server@latest` | `mcp__plugin_aws-well-architected_wa-security__*` | Well-Architected Security Pillar assessment, Security Hub, and GuardDuty posture checks. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-well-architected_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-well-architected_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |
| `tm` | stdio | `uvx --from git+https://github.com/awslabs/threat-modeling-mcp-server.git threat-modeling-mcp-server` | `mcp__plugin_aws-well-architected_tm__*` | AWS Threat Composer STRIDE threat modeling and mitigation validation. |
| `drawio` | stdio | `npx -y @drawio/mcp` | `mcp__plugin_aws-well-architected_drawio__*` | Architecture diagram authoring and rendering via Draw.io MCP. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-well-architected_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-well-architected_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
