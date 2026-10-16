# AWS Marketplace Seller

End-to-end AWS Marketplace ISV & Seller engineering for the main agent: Metering & Entitlement APIs (ResolveCustomer, BatchMeterUsage, RegisterUsage, GetEntitlements), Catalog API product listings (StartChangeSet for SaaS, Container, AMI, GenAI), Private Offers & CPPO with Flexible Payment Scheduler, Agreement API, and SaaS control-plane onboarding.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-marketplace-seller@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-solutions-architect`](../../agent-plugins/aws-solutions-architect) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-marketplace-seller:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-marketplace-seller:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `aws-marketplace-catalog-and-listings` | Author, update, and automate AWS Marketplace product listings (SaaS, Container/EKS/ECS, AMI, and GenAI Agent/Model products) using the AWS Marketplace Catalog API (StartChangeSet), SNS entitlement/su… |
| `aws-marketplace-metering` | Deploys, queries, and debugs AWS Marketplace usage-based (PAYG) metering — the pipeline (ResolveCustomer, BatchMeterUsage, EventBridge via SAM) and querying/debugging metering records, statuses, fail… |
| `aws-marketplace-private-offers-and-agreements` | Create and manage AWS Marketplace Private Offers, Channel Partner Private Offers (CPPO), Flexible Payment Scheduler (FPS), Agreement API queries, and Seller Data Feeds (Commerce Analytics / CFT / S3… |
| `aws-marketplace-saas-architecture` | Design and deploy end-to-end AWS Marketplace SaaS and Container control planes: tenant registration landing pages, Step Functions onboarding workflows, DynamoDB tenant-to-CustomerIdentifier mapping,… |

## Commands

| Command | Description |
|---|---|
| `/aws-marketplace-seller:create-private-offer-workflow` | Construct an atomic Catalog API `StartChangeSet` for a Private Offer or CPPO with custom pricing, Flexible Payment Scheduler (FPS), and SCMP legal terms. |
| `/aws-marketplace-seller:integrate-metering` | Implement AWS Marketplace Metering & Entitlement integration (`ResolveCustomer`, `BatchMeterUsage`, `RegisterUsage`, `GetEntitlements`) with retry and idempotency guards. |
| `/aws-marketplace-seller:publish-catalog-product` | Author and execute an AWS Marketplace Catalog API `StartChangeSet` payload to create or update product listings, dimensions, and delivery options. |
| `/aws-marketplace-seller:verify-seller-setup` | Audit IAM roles, SNS subscription/entitlement topic handlers, DynamoDB tenant tables, and CloudWatch metering alarms before Marketplace launch. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-marketplace-seller_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-marketplace-seller_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-marketplace-seller_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-marketplace-seller_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-marketplace-seller_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-marketplace-seller_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-marketplace-seller_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
