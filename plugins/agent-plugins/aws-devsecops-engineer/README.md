# AWS DevSecOps Engineer

Principal AWS DevSecOps Engineer: native CloudWatch/Application Signals/X-Ray/CloudTrail incident root-cause investigations, Security Hub/GuardDuty/Inspector/Config posture triage, least-privilege IAM & Access Analyzer validation, Terraform/CDK/CloudFormation & VPC/WAFv2/KMS/S3 perimeter hardening, AWS Security Agent SAST code/diff scans, STRIDE threat modeling, DAST penetration testing, finding remediation, 5-gate release-readiness reviews, synthetic UAT testing, ECS/EKS/Lambda operations, FinOps cost optimization, and multi-account orchestration.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-devsecops-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-devsecops-engineer.toml`](./codex/agents/aws-devsecops-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-devsecops-engineer`](./agents/aws-devsecops-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-devsecops-engineer:aws-devsecops-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-devsecops-engineer:aws-devsecops-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `aws-devsecops-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills

| Skill | What it does |
|---|---|
| `auditing-cloudtrail-forensics` | Executes AWS CloudTrail forensic investigations, management and data event timeline reconstruction, CloudTrail Lake SQL queries, `AccessDenied` spike analysis, root account activity checks, and `aws:CalledViaAWSMCP` AI… |
| `diff-scanning-with-aws-security-agent` | Run a fast AWS Security Agent diff scan on only the changed code since a git ref. |
| `engineering-iam-least-privilege` | Authors, audits, and validates least-privilege AWS IAM policies, trust policies, permission boundaries, SCPs, and keyless CI/CD OIDC federation (`sts:AssumeRoleWithWebIdentity`) using IAM Access Analyzer (`validate-poli… |
| `executing-synthetic-release-tests` | Runs post-deployment User Acceptance Testing (UAT), smoke tests, CloudWatch Synthetics canaries, API Gateway test invocations, and live Golden Signal metric/alarm verification, triggering automated rollback if SLOs brea… |
| `hardening-iac-and-perimeter` | Audits and hardens Infrastructure-as-Code templates (Terraform, AWS CDK, CloudFormation, SAM, Dockerfiles) and live AWS network, storage, and encryption perimeters (VPC Security Groups, NACLs, WAFv2 WebACLs, S3 Block Pu… |
| `investigating-cloudwatch-incidents` | Performs native AWS SRE root-cause analysis (RCA) for production outages, latency spikes, 5xx errors, and alarm breaches using CloudWatch Alarms, Metrics, Logs Insights, Application Signals, X-Ray traces, and CloudTrail… |
| `operating-containers-and-serverless` | Troubleshoots, secures, and optimizes AWS container (ECS Fargate, EKS, ECR) and serverless (Lambda, API Gateway, EventBridge, SQS) workloads: diagnoses `StoppedReason` / `ExitCode: 137` OOM kills, image pull failures, c… |
| `optimizing-cloud-costs-and-finops` | Analyzes AWS spend, detects cost anomalies, audits idle and unattached resources (EBS volumes, Elastic IPs, NAT Gateways, underutilized RDS/ECS/EC2), evaluates Compute Optimizer and Savings Plans/RI recommendations via… |
| `orchestrating-multi-account-ops` | Coordinates cross-account and multi-region AWS DevSecOps operations across development, staging, production, and security/audit accounts using `aws-mcp` dynamic `aws_profile` switching and AWS Organizations hierarchy di… |
| `pentesting-with-aws-security-agent` | Run an AWS Security Agent penetration test against a live web application — registers and verifies the target domain, exercises the supplied endpoints with the managed Security Agent service, and returns verified runtim… |
| `remediating-with-aws-security-agent` | Pull AWS Security Agent findings (penetration tests and code reviews) via the `aws-security-agent` MCP server or `aws securityagent` CLI, export them to a gitignored `.security-agent/` directory, prioritize by exploitab… |
| `scanning-with-aws-security-agent` | Run an AWS Security Agent scan on the workspace — uploads the source to AWS, scans it with the managed Security Agent service, and returns ranked, verified findings with code locations and remediations. |
| `setup` | Configures and verifies the AWS DevSecOps Engineer plugin environment: checks `uvx` and AWS CLI prerequisites, verifies SigV4 credentials and named AWS profiles, validates bundled MCP servers (`aws-mcp`, `aws-security-a… |
| `setup-security-agent` | Configure AWS Security Agent for the current workspace — provision or reuse an agent space, IAM service role, and S3 bucket. |
| `signing-in-to-aws` | Gets AWS credentials for CLI, SDK, and MCP server access via `aws login` or `aws sso login`, validates caller identity across single or multi-account named profiles, and verifies SigV4 readiness for `mcp-proxy-for-aws`. |
| `threat-modeling-with-aws-security-agent` | Run an AWS Security Agent threat model review on spec/design documents. |
| `triaging-cloud-security-posture` | Aggregates, correlates, and remediates cloud security posture (CSPM) findings and runtime threats across AWS Security Hub (CIS, FSBP), Amazon GuardDuty, Amazon Inspector (ECR, Lambda, EC2 CVEs), and AWS Config, mapping… |
| `validating-release-readiness` | Executes a comprehensive pre-deployment and pre-merge release-readiness gate on local git diffs, pull requests, and IaC change sets: inspects CloudFormation change sets / `cdk diff` / `terraform plan` for stateful resou… |

## Commands

| Command | Description |
|---|---|
| `/aws-devsecops-engineer:accounts` | Coordinate multi-account and cross-Region DevSecOps workflows across staging, prod, and security profiles via aws-mcp profile switching |
| `/aws-devsecops-engineer:cost` | Analyze AWS spend, detect cost anomalies, sweep idle resources, and generate FinOps right-sizing patches in local IaC |
| `/aws-devsecops-engineer:harden` | Audit and harden IaC templates (Terraform, CDK, CloudFormation, Dockerfiles), network perimeters (VPC, WAFv2), S3, KMS, and Secrets Manager |
| `/aws-devsecops-engineer:iam` | Author least-privilege IAM policies, troubleshoot AccessDenied errors, configure CI/CD OIDC, and validate with IAM Access Analyzer |
| `/aws-devsecops-engineer:investigate` | Run a native 4-phase SRE root-cause investigation using CloudWatch Alarms, Logs Insights, Application Signals, X-Ray, and CloudTrail |
| `/aws-devsecops-engineer:pentest` | Verify target domain ownership, execute AWS Security Agent DAST penetration tests, and remediate verified findings |
| `/aws-devsecops-engineer:posture` | Triage and remediate cloud security posture (CSPM) findings across Security Hub, GuardDuty, Inspector, and AWS Config |
| `/aws-devsecops-engineer:release-readiness` | Run a 5-gate pre-deployment release-readiness review across git diffs, IaC change sets, security diff scans, IAM validation, and rollback alarms |
| `/aws-devsecops-engineer:release-testing` | Execute post-deployment synthetic smoke tests, CloudWatch Synthetics canaries, API Gateway test invocations, and bake-window SLO verification |
| `/aws-devsecops-engineer:scan` | Run AWS Security Agent full SAST code scans or pre-PR git diff scans and remediate discovered vulnerabilities |
| `/aws-devsecops-engineer:setup` | Configure AWS SigV4 credentials, verify MCP servers and IAM safety guardrails, and optionally initialize AWS Security Agent |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0` `--skip-auth --metadata` | `mcp__plugin_aws-devsecops-engineer_aws-mcp__*` | Managed AWS MCP Server via the toolkit's pinned proxy (aws___call_aws, aws___search_documentation, aws___retrieve_skill, ...). |
| `aws-security-agent` | stdio | `uvx awslabs.security-agent-mcp-server@latest` | `mcp__plugin_aws-devsecops-engineer_aws-security-agent__*` | AWS Security Agent MCP Server for SAST code reviews, git diff scans, STRIDE threat modeling, DAST penetration testing, and finding retrieval. |
| `aws-cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-devsecops-engineer_aws-cloudwatch__*` |  |
| `aws-cloudtrail` | stdio | `uvx awslabs.cloudtrail-mcp-server@latest` | `mcp__plugin_aws-devsecops-engineer_aws-cloudtrail__*` |  |
| `aws-well-architected-security` | stdio | `uvx awslabs.well-architected-security-mcp-server@latest` | `mcp__plugin_aws-devsecops-engineer_aws-well-architected-security__*` |  |
| `aws-billing` | stdio | `uvx awslabs.billing-cost-management-mcp-server@latest` | `mcp__plugin_aws-devsecops-engineer_aws-billing__*` |  |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-devsecops-engineer_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-devsecops-engineer_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`aws-agents-for-devsecops`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
