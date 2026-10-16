# AWS Networking

Enterprise AWS networking and edge perimeter skills for the main agent: multi-AZ VPC design, Transit Gateway, Cloud WAN, VPC Lattice, IPAM, VPC Endpoints/PrivateLink, Direct Connect, Site-to-Site VPN, Route 53, CloudFront, WAF, Shield Advanced, Network Firewall, and Reachability Analyzer diagnostics.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-networking@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-platform-engineer`](../../agent-plugins/aws-platform-engineer) or [`aws-solutions-architect`](../../agent-plugins/aws-solutions-architect) or [`aws-sre-agent`](../../agent-plugins/aws-sre-agent) or [`aws-cloud-security-engineer`](../../agent-plugins/aws-cloud-security-engineer) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-networking:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-networking:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `aws-enterprise-landing-zone-and-networking` | Architects enterprise multi-account AWS Organizations and Control Tower Landing Zones, OU hierarchies, SCPs, Resource Control Policies (RCPs), Declarative Policies, AWS Data Perimeters, Shared VPCs (… |
| `aws-landing-zone-and-platform-governance` | Architects and operates multi-account AWS Landing Zones, AWS Organizations (SCPs, RCPs, Declarative Policies), Control Tower guardrails, Shared VPCs via AWS RAM, hierarchical Amazon VPC IPAM, Amazon… |
| `aws-network-monitoring` | >- |
| `aws-networking` | Routes AWS networking requests to the correct service skill for implementation. |
| `cloudfront` | > |
| `configuring-vpc-endpoints-for-private-aws-service-access` | Configures VPC endpoints (interface and gateway) for private AWS service access using AWS PrivateLink. |
| `connecting-vpcs-with-peering` | Establishes VPC peering connections between two VPCs for direct private network connectivity. |
| `creating-production-vpc-multi-az` | Creates a production-ready VPC with public and private subnets across multiple Availability Zones, including internet gateway, NAT gateways, route tables, and security groups following AWS Well-Archi… |
| `directconnect` | >- |
| `enabling-lambda-vpc-internet-access` | Enables internet access for AWS Lambda functions deployed in VPC subnets by creating NAT Gateway infrastructure, configuring public/private subnet routing, and updating security groups. |
| `route53` | >- |
| `routing-traffic-with-route53-and-cloudfront` | Configures Amazon Route 53 to route traffic to a CloudFront distribution using a custom domain. |
| `security-network-perimeter` | >- |
| `shieldadvanced` | >- |
| `sitetositevpn` | > |
| `transitgateway` | >- |
| `vpc-network-path-diagnostics` | Trace and diagnose AWS network connectivity incidents across VPC route tables, Security Groups, NACLs, NAT Gateways, Transit Gateway (TGW), AWS Cloud WAN, AWS Network Firewall, PrivateLink VPC Endpoi… |
| `waf` | >- |

## Commands

| Command | Description |
|---|---|
| `/aws-networking:audit-vpc` | Audit a VPC for multi-AZ resilience, NAT Gateway cost/HA, CIDR exhaustion, flow logs, and Gateway/Interface VPC Endpoints. |
| `/aws-networking:design-hub-spoke` | Architect an enterprise multi-account network topology using AWS Transit Gateway, Cloud WAN, VPC Lattice, and IPAM. |
| `/aws-networking:harden-network-perimeter` | Design defense-in-depth perimeter protection with AWS WAF, Shield Advanced, AWS Network Firewall, and Route 53 DNS Firewall. |
| `/aws-networking:trace-connectivity` | Trace network reachability across VPCs, Security Groups, NACLs, Transit Gateway, and firewalls using Reachability Analyzer. |
| `/aws-networking:troubleshoot-dns` | Diagnose Route 53 public/private hosted zones, Resolver inbound/outbound endpoints, DNSSEC, and CloudFront origin routing. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-networking_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsnetwork` | stdio | `uvx awslabs.aws-network-mcp-server@latest` | `mcp__plugin_aws-networking_awsnetwork__*` | VPC, Transit Gateway, Cloud WAN, Network Firewall, and Reachability Analyzer inspection. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-networking_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-networking_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-networking_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-networking_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-networking_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
