# AWS Cloud Security Engineer

Principal AWS cloud security and identity engineer: IAM policies, roles, Cognito auth boundaries, and Organizations SCP/RCP Data Perimeters; S3 Object Lock, Macie, KMS CMKs/grants, Private CA/mTLS, and Secrets Manager zero-plaintext rotation; VPC/TGW/Network Firewall/DNS Firewall/WAFv2/Shield Advanced perimeters; EKS/ECS/Lambda/EC2 and Bedrock GenAI workload security; AWS STRIDE threat modeling and multi-IaC validation (cfn-guard, cdk-nag, Terraform); Security Hub/GuardDuty/Inspector/Macie/Detective/Security Lake (OCSF) incident triage and CloudTrail forensics; and CIS/FSBP/Well-Architected posture audits.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-cloud-security-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-cloud-security-engineer.toml`](./codex/agents/aws-cloud-security-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-cloud-security-engineer`](./agents/aws-cloud-security-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-cloud-security-engineer:aws-cloud-security-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-cloud-security-engineer:aws-cloud-security-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `aws-cloud-security-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills

| Skill | What it does |
|---|---|
| `aws-iam` | Provides verified corrections for IAM behaviors that AI agents frequently get wrong — policy evaluation edge cases, trust policy gotchas, STS session limits, Organizations quirks, and SAML/MFA specifics. |
| `aws-security` | Covers AWS security services and workflows — Security Hub V2 (OCSF) findings, connectors, aggregators, automation rules, and security posture summaries; Security Hub CSPM (V1/ASFF) controls and compliance standards; Gua… |
| `security-data-protection` | Audits and designs AWS data protection, cryptographic governance, forensic storage immutability, secret management, sensitive data discovery, and PKI/mTLS controls across AWS KMS, Amazon S3 (Block Public Access, Bucket… |
| `security-identity-governance` | Audits and designs AWS IAM identities, 8-layer policy evaluation, 21 privilege-escalation paths, IAM Access Analyzer, Organizations SCPs and RCPs (Resource Control Policies), Data Perimeters, aws:CalledViaAWSMCP and aws… |
| `security-incident-triage` | Performs AWS threat triage, incident response investigation, and forensic correlation across GuardDuty (including Attack Sequences and Runtime Monitoring), Security Hub V2 Exposure findings, Inspector, Macie, Detective,… |
| `security-network-perimeter` | Audits and designs AWS VPC network perimeter, segmentation, and edge controls: 7-layer VPC perimeter, Security Groups, NACLs, PrivateLink VPC Endpoint policies, Transit Gateway and Cloud WAN inspection, AWS Network Fire… |
| `security-posture-audit` | Performs read-only AWS security posture, compliance, and multi-account governance audits across Security Hub CSPM, AWS Config, GuardDuty, Inspector, Macie, IAM Access Analyzer, Detective, Security Lake, CloudTrail, AWS… |
| `security-remediation-governance` | Performs AWS Cloud Architectural Threat Modeling (STRIDE across trust boundaries and multi-service attack paths) and converts AWS security findings and audit gaps into safe, shift-left validated remediation proposals ac… |
| `security-workload-containers` | Audits and hardens AWS compute, container, serverless, and Generative AI workloads across Amazon EKS, Amazon ECS/Fargate, Amazon ECR, AWS Lambda, Amazon EC2, and Amazon Bedrock. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0` `--skip-auth --metadata` | `mcp__plugin_aws-cloud-security-engineer_aws-mcp__*` | Managed AWS MCP Server via the toolkit's pinned proxy (aws___call_aws, aws___search_documentation, aws___retrieve_skill, ...). |
| `iam` | stdio | `uvx awslabs.iam-mcp-server@latest` | `mcp__plugin_aws-cloud-security-engineer_iam__*` | Read-only by default (the server only mutates with --allow-write). Add --allow-write to allow IAM mutations. |
| `wa-security` | stdio | `uvx awslabs.well-architected-security-mcp-server@latest` | `mcp__plugin_aws-cloud-security-engineer_wa-security__*` |  |
| `cloudtrail` | stdio | `uvx awslabs.cloudtrail-mcp-server@latest` | `mcp__plugin_aws-cloud-security-engineer_cloudtrail__*` |  |
| `awsiac` | stdio | `uvx fastmcp<4.0.0` `--with` | `mcp__plugin_aws-cloud-security-engineer_awsiac__*` | Pinned to 0.2.14 with fastmcp<4.0.0 to prevent FastMCP 4.0 breaking import crashes (awslabs/mcp#4567). |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-cloud-security-engineer_cloudwatch__*` |  |
| `awsnetwork` | stdio | `uvx awslabs.aws-network-mcp-server@latest` | `mcp__plugin_aws-cloud-security-engineer_awsnetwork__*` |  |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
