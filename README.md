# TalkOps DevOps Plugins

[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](./LICENSE)
[![Agent Plugins](https://img.shields.io/badge/Agent_Plugins-1.0.0-0A66C2.svg)](https://agent-plugins.org)
[![MCP](https://img.shields.io/badge/Protocol-MCP-6E40C9.svg)](https://modelcontextprotocol.io)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

**Open-source DevOps and cloud engineering plugins for AI agents** — bundling specialist agents, domain skills, MCP servers, and safety hooks for AWS, Kubernetes, and modern infrastructure operations across Claude Code, Codex, and any Agent Plugins 1.0.0 host.

[Quick Start](#quick-start) · [Plugin Catalog](#plugin-catalog) · [Safety Model](#safety-model) · [Host Compatibility](#host-compatibility) · [Validation & Evals](#validation--skill-evaluations) · [Contributing](#contributing--community)

---

## Quick Start

### Claude Code

```bash
# 1. Add the marketplace
claude plugin marketplace add talkops-ai/devops-plugins

# 2. Install specialist sub-agents...
claude plugin install aws-sre-agent@talkops-devops-plugins
claude plugin install aws-iac-engineer@talkops-devops-plugins
claude plugin install kubernetes-delivery-engineer@talkops-devops-plugins

# ...or attach domain capabilities directly to your main agent
claude plugin install aws-networking@talkops-devops-plugins
claude plugin install aws-serverless@talkops-devops-plugins
claude plugin install aws-databases@talkops-devops-plugins
```

**Usage:**
- Specialist agents delegate automatically, or run directly via `claude --agent aws-sre-agent:aws-sre-agent` (or `@agent-<plugin>:<agent>`).
- Vertical skills activate automatically on relevant tasks, or run multi-phase workflows via `/<plugin>:<command>` (e.g., `/aws-networking:trace-connectivity`, `/aws-databases:troubleshoot-db`).

### OpenAI Codex

```bash
# Add the marketplace (Codex reads .agents/plugins/marketplace.json)
codex plugin marketplace add talkops-ai/devops-plugins
```

Install plugins from `/plugins` or enable them in `~/.codex/config.toml`:

```toml
[plugins."aws-iac-engineer@talkops-devops-plugins"]
enabled = true

[plugins."aws-networking@talkops-devops-plugins"]
enabled = true
```

To run an agent plugin as a custom sub-agent in Codex, copy its `.toml` into `~/.codex/agents/`:

```bash
cp plugins/agent-plugins/aws-iac-engineer/codex/agents/aws-iac-engineer.toml ~/.codex/agents/
```

### Other Agent Plugins 1.0.0 Hosts

Every plugin ships a portable [Agent Plugins 1.0.0](https://agent-plugins.org) root layout (`plugin.json`, `skills/`, `mcp.json`) compatible with **Cursor**, **GitHub Copilot**, **Gemini CLI / Antigravity**, **Windsurf**, and other spec-compliant hosts.

<details>
<summary><b>Prerequisites</b></summary>

- [`uv`](https://docs.astral.sh/uv/) (`uvx`) to launch stdio MCP servers, and Node.js (`npx`) for `@drawio/mcp`.
- **AWS CLI v2** with credentials from your environment (`AWS_PROFILE`, IAM Identity Center SSO, or an instance/task role). Set `AWS_REGION` in your environment (defaults to `us-east-1` in Claude Code).
- **Python 3** on `PATH` for deterministic safety hooks.
- **Optional connectors** (endpoint-bound DBs, scoped Lambda/Step Functions tools, Docker-based Terraform MCP, or third-party observability connectors) are documented in each plugin's `CONNECTORS.md`.

</details>

---

## Plugin Catalog

Plugins are organized into three categories depending on how you want capabilities loaded:

| Category | Directory | How It Loads | Best For |
|---|---|---|---|
| **Agent plugins** | [`plugins/agent-plugins`](./plugins/agent-plugins/README.md) | Isolated specialist sub-agent with scoped MCP tools & hooks | End-to-end Principal-level AWS & Kubernetes engineering roles |
| **Vertical plugins** | [`plugins/vertical-plugins`](./plugins/vertical-plugins/README.md) | Attaches directly to your main agent (no sub-agent hand-off) | Deep AWS domain skills and slash-command playbooks in your primary session |
| **Partner-built plugins** | [`plugins/partner-built`](./plugins/partner-built/README.md) | Attaches to your main agent (or vendor agent) | Official vendor & cloud-native ecosystem integrations |

<details>
<summary><b>Browse Agent Plugins (Specialist Sub-Agents)</b></summary>

| Function | Plugin | Focus |
|---|---|---|
| **Build & deliver** | [`aws-iac-engineer`](./plugins/agent-plugins/aws-iac-engineer) | CDK, CloudFormation, Terraform/OpenTofu, Pulumi, Crossplane, Karpenter IaC, brownfield imports, and GitOps CI/CD. |
| | [`aws-deployment-engineer`](./plugins/agent-plugins/aws-deployment-engineer) | Codebase discovery, target architecture, FinOps cost estimates, IaC scaffolding, and post-deploy verification & rollback. |
| | [`aws-serverless-engineer`](./plugins/agent-plugins/aws-serverless-engineer) | Lambda (SnapStart, Durable Functions, Managed Instances), API Gateway, Step Functions, EventBridge, SQS/SNS, DynamoDB, Aurora DSQL, and SAM/CDK. |
| | [`aws-amplify-engineer`](./plugins/agent-plugins/aws-amplify-engineer) | Amplify Gen 2 TypeScript-first full-stack apps: Cognito Auth, AppSync Data, S3 Storage, Functions, Custom CDK, and Hosting CI/CD. |
| | [`aws-location-engineer`](./plugins/agent-plugins/aws-location-engineer) | Amazon Location Service V2 maps, geocoding, places search, routing/matrices, geofencing, and fleet tracking. |
| **Platform & operations** | [`aws-platform-engineer`](./plugins/agent-plugins/aws-platform-engineer) | EC2, Golden AMIs, EKS (Auto Mode, Karpenter, Pod Identity), ECS Fargate, VPC/TGW/Cloud WAN/DX diagnostics, S3/EFS/FSx/Backup, and Golden Path landing zones. |
| | [`aws-sre-agent`](./plugins/agent-plugins/aws-sre-agent) | CloudWatch, Application Signals, X-Ray, CloudTrail forensics, Prometheus/Grafana, EKS/ECS health & ops reviews, AWS Health/Support, FIS/ARC resilience, COE postmortems, and observability connectors. |
| | [`aws-devsecops-engineer`](./plugins/agent-plugins/aws-devsecops-engineer) | Live incident RCA, Security Hub CSPM triage, least-privilege IAM, IaC/perimeter hardening, AWS Security Agent SAST/DAST/pentest scans, release gates, and FinOps guardrails. |
| **Security & cost** | [`aws-cloud-security-engineer`](./plugins/agent-plugins/aws-cloud-security-engineer) | IAM & SCP/RCP Data Perimeters, KMS & Secrets Manager, Security Hub (OCSF), GuardDuty/CloudTrail IR & telemetry cost governance, WAF/Network Firewall, and Wiz/Sumo Logic connectors. |
| | [`aws-finops-engineer`](./plugins/agent-plugins/aws-finops-engineer) | Cost Explorer & Anomaly Detection, CUR 2.0 Athena SQL, Compute Optimizer right-sizing, CloudTrail/Config/GuardDuty/NAT GW optimization, Extended Support EOS modeling, and Savings Plans/RIs. |
| **Architecture & advisory** | [`aws-solutions-architect`](./plugins/agent-plugins/aws-solutions-architect) | Well-Architected 6-pillar reviews, ADRs, STRIDE threat modeling, Draw.io architecture diagrams, multi-account Landing Zones, multi-region DR, and Bedrock/ML design. |
| | [`aws-startup-advisor`](./plugins/agent-plugins/aws-startup-advisor) | Pre-Seed to Series B architecture, account hygiene audits, Azure/GCP/Heroku → AWS migrations, OpenAI/Anthropic → Bedrock migrations, and AWS Activate optimization. |
| **Data & AI** | [`aws-data-engineer`](./plugins/agent-plugins/aws-data-engineer) | S3 Tables (Apache Iceberg), Glue Spark ETL & DQDL, Lake Formation, Athena, Redshift, Kinesis/Firehose/MSK, MWAA, and OpenSearch. |
| | [`aws-database-engineer`](./plugins/agent-plugins/aws-database-engineer) | Aurora (PostgreSQL/MySQL/DSQL), RDS ops reviews & DevOps health checks, DynamoDB, ElastiCache (Valkey/Redis), DocumentDB, Keyspaces, Neptune, Performance Insights, and DMS. |
| | [`aws-agentcore-engineer`](./plugins/agent-plugins/aws-agentcore-engineer) | Build, connect, deploy, harden, debug, evaluate, and operate AI agents on Amazon Bedrock AgentCore & Strands Agents, plus optional Arize AX trace investigation. |
| | [`aws-sagemaker-engineer`](./plugins/agent-plugins/aws-sagemaker-engineer) | SageMaker AI & Bedrock ML engineering: HyperPod GPU cluster debugging, AI/ML access diagnostics, fine-tuning, vLLM/LMI inference, MLOps Pipelines, and ops reviews. |
| **Migration & upgrades** | [`aws-modernization-agent`](./plugins/agent-plugins/aws-modernization-agent) | 7 Rs portfolio assessment, Strangler Fig decomposition, AWS Transform (.NET, Java, mainframe COBOL, SQL Server), VMware MGN replatforming, and DMS cutover. |
| | [`aws-eks-upgrade-engineer`](./plugins/agent-plugins/aws-eks-upgrade-engineer) | Read-only EKS upgrade readiness scoring, Best Practices audits, deprecated API scanning, Karpenter migrations, AL2→AL2023 `nodeadm` migration, CNI surge sizing, rollback, and EOS cost analysis. |
| **Kubernetes & cloud-native** | [`kubernetes-delivery-engineer`](./plugins/agent-plugins/kubernetes-delivery-engineer) | Kubernetes application onboarding, Helm packaging & security review, ArgoCD GitOps, Argo Rollouts canary/blue-green gating, Kargo freight promotion, and Traefik v3 routing. |
| | [`kubernetes-observability-engineer`](./plugins/agent-plugins/kubernetes-observability-engineer) | Full-stack Kubernetes observability & SRE: Prometheus 3.0+, Alertmanager, Grafana Tempo (TraceQL), Grafana Loki 3.x (LogQL), OpenTelemetry Collectors, and Grafana Cloud/Cribl connectors. |

See [`plugins/agent-plugins/README.md`](./plugins/agent-plugins/README.md) for full skill, command, and MCP server details.

</details>

<details>
<summary><b>Browse Vertical Plugins (Main-Agent AWS Domain Bundles)</b></summary>

| Domain | Plugin | Focus |
|---|---|---|
| **Foundation** | [`aws-essentials`](./plugins/vertical-plugins/aws-essentials) | Credential & SSO preflight, account baseline audits, and Python/JS-TS/Swift SDK best practices. |
| **Build** | [`aws-infrastructure-as-code`](./plugins/vertical-plugins/aws-infrastructure-as-code) | CDK, CloudFormation, Terraform/OpenTofu, Pulumi, Crossplane/ACK, brownfield imports, and deployment verification. |
| | [`aws-serverless`](./plugins/vertical-plugins/aws-serverless) | Lambda, API Gateway, Step Functions, EventBridge, SQS/SNS, ESMs, DynamoDB, Aurora DSQL, and SAM/CDK. |
| | [`aws-web-and-mobile`](./plugins/vertical-plugins/aws-web-and-mobile) | Amplify Gen 2 (Auth, Data/AppSync, Storage, Functions, Hosting, AI Kit), AWS Blocks, and Amazon Location Service V2. |
| **Platform** | [`aws-compute`](./plugins/vertical-plugins/aws-compute) | EC2 instance selection (Graviton4/GPU), Auto Scaling Groups, EC2 Image Builder golden AMIs, Elastic Beanstalk, and right-sizing. |
| | [`aws-containers`](./plugins/vertical-plugins/aws-containers) | EKS (Auto Mode, Karpenter, Pod Identity, VPC CNI), ECS Fargate/Express Mode, ECR build/push, and container security. |
| | [`aws-networking`](./plugins/vertical-plugins/aws-networking) | Multi-AZ VPC, Transit Gateway, Cloud WAN, VPC Lattice, Direct Connect, VPN, Route 53, CloudFront, WAF, Shield, and Network Firewall. |
| | [`aws-storage`](./plugins/vertical-plugins/aws-storage) | S3 (Storage Lens, Intelligent-Tiering, Object Lock, S3 Tables), EFS, EBS, FSx, AWS Backup, KMS, and cross-region DR. |
| | [`aws-messaging-and-streaming`](./plugins/vertical-plugins/aws-messaging-and-streaming) | SQS, SNS, EventBridge, Amazon MSK (Kafka), Kinesis, Managed Flink, Amazon MQ, and End-User Messaging (SES/SMS/WhatsApp). |
| **Data & AI** | [`aws-databases`](./plugins/vertical-plugins/aws-databases) | Aurora (PG/MySQL/DSQL), RDS, DynamoDB, DocumentDB, ElastiCache (Valkey/Redis), Keyspaces, Neptune, Timestream, Performance Insights, and DMS. |
| | [`aws-analytics`](./plugins/vertical-plugins/aws-analytics) | S3 Tables (Iceberg), Glue ETL & DQDL, Lake Formation, Athena, Redshift, OpenSearch, EMR, MWAA, and streaming ingestion. |
| | [`aws-ai-ml`](./plugins/vertical-plugins/aws-ai-ml) | Amazon Bedrock, Bedrock AgentCore & Strands Agents, and SageMaker AI training, inference, fine-tuning, and MLOps. |
| **Operate** | [`aws-observability`](./plugins/vertical-plugins/aws-observability) | CloudWatch, Application Signals APM, X-Ray, Managed Prometheus/Grafana, CloudTrail auditing, and COE postmortems. |
| | [`aws-resilience`](./plugins/vertical-plugins/aws-resilience) | AWS Resilience Hub, Fault Injection Service (FIS) chaos experiments, Route 53 ARC zonal shift/region switch, and DR matrices. |
| **Secure & govern** | [`aws-security-identity`](./plugins/vertical-plugins/aws-security-identity) | IAM least privilege, SCPs/RCPs, KMS & Secrets Manager, Security Hub (OCSF), GuardDuty, CloudTrail forensics, and STRIDE threat modeling. |
| | [`aws-cost-optimization`](./plugins/vertical-plugins/aws-cost-optimization) | Cost Explorer, CUR 2.0 Athena SQL, Compute Optimizer right-sizing, Savings Plans/RIs, and Shift-Left IaC cost estimation. |
| | [`aws-well-architected`](./plugins/vertical-plugins/aws-well-architected) | Well-Architected 6-pillar reviews, MADR ADRs, Draw.io & Mermaid diagrams, STRIDE threat modeling, and Landing Zone design. |
| **Modernize** | [`aws-migration`](./plugins/vertical-plugins/aws-migration) | 7 Rs strategy, Strangler Fig decomposition, AWS Transform, MGN, App2Container, DMS cutover, and Azure/GCP/Heroku → AWS migrations. |
| **Specialty** | [`aws-marketplace-seller`](./plugins/vertical-plugins/aws-marketplace-seller) | AWS Marketplace ISV metering & entitlements, Catalog API listings, Private Offers/CPPO, and SaaS control-plane onboarding. |
| | [`aws-end-user-computing`](./plugins/vertical-plugins/aws-end-user-computing) | Amazon WorkSpaces Personal & Pools, AppStream 2.0, WorkSpaces Secure Browser, EUC cost tuning, and Agent Access. |
| | [`aws-quantum-computing`](./plugins/vertical-plugins/aws-quantum-computing) | Amazon Braket OpenQASM 3.0 & SDK circuits, Managed Simulators, QPU targeting, Hybrid Jobs, and shot cost governance. |

See [`plugins/vertical-plugins/README.md`](./plugins/vertical-plugins/README.md) for slash commands, MCP servers, and agent alternatives.

</details>

<details>
<summary><b>Browse Partner-Built Plugins (Ecosystem & Vendor Integrations)</b></summary>

| Plugin | Vendor / Maintainer | License | Focus |
|---|---|---|---|
| [`terraform`](./plugins/partner-built/terraform) | HashiCorp | MPL-2.0 | Official HashiCorp Terraform skills: HCL style, modules, tests, search/import, Stacks, Sentinel/OPA policy, Azure Verified Modules, and provider development. |
| [`crossplane-aws-engineer`](./plugins/partner-built/crossplane-aws-engineer) | TalkOps | MIT | Crossplane AWS platform engineering: Upbound `provider-family-aws`, XRDs, Claims, Pipeline Compositions, IRSA auth, and offline validation. |
| [`launchdarkly`](./plugins/partner-built/launchdarkly) | LaunchDarkly | Apache-2.0 | Feature flag management, progressive guarded rollouts, experimentation, observability, and AI Config / Agent Control graphs. |
| [`coralogix`](./plugins/partner-built/coralogix) | Coralogix | Apache-2.0 | DataPrime log/span analytics, PromQL metrics, alerts, cases, service catalog, RUM, AI Center, dashboards, Olly, and TCO data-usage audits. |
| [`honeycomb`](./plugins/partner-built/honeycomb) | Honeycomb.io | Apache-2.0 | High-cardinality production investigation, BubbleUp/wide-event queries, OpenTelemetry metrics, SLO burn-rate triage, trace verification, and boards. |
| [`elastic`](./plugins/partner-built/elastic) | Elastic | Apache-2.0 | SRE incident triage, service reliability, Kubernetes investigation, Cloud Security Posture (CSP), and LLM observability. |
| [`neo4j`](./plugins/partner-built/neo4j) | Neo4j, Inc. | Apache-2.0 | Read-only Neo4j diagnostics and support runbooks for self-managed Neo4j on Amazon EKS, ECS, and EC2. |
| [`bronto`](./plugins/partner-built/bronto) | Bronto | Apache-2.0 | Dataset/collection discovery, SQL-style log search and time-series aggregation, and production error spike investigation. |

See [`plugins/partner-built/README.md`](./plugins/partner-built/README.md) for slash commands and MCP environment variables.

</details>

---

## Safety Model

Three defense-in-depth layers protect your cloud accounts and Kubernetes clusters across every plugin:

1. **Read-only MCP defaults.** Bundled `awslabs` and `talkops-mcp` servers start in read-only mode where supported (`--read-only`, `ALLOW_WRITE=false`, `MCP_ALLOW_WRITE=false`, `READ_OPERATIONS_ONLY=true`). Read-only specialists enforce read-only locks end-to-end.
2. **Deterministic `PreToolUse` / `PostToolUse` hooks.**
   - **`secret-safety.py`** blocks shell commands and MCP calls across all plugins that attempt to print, exfiltrate, or hardcode credentials, session tokens, `.env` secrets, or private keys.
   - **`aws-mutation-gate.py`** intercepts mutating `aws`, `terraform`, `tofu`, `cdk`, `sam`, `pulumi`, `eksctl`, `kubectl`, `helm`, `copilot`, and `amplify` operations—blocking outright on read-only agents and requiring confirmation otherwise (`TALKOPS_AWS_MUTATION_GATE=off|warn|ask|deny`).
   - **Domain hooks** provide credential/GitOps preflight (`session-aws-preflight.py`, `session-argocd-preflight.py`), IaC linters (`iac-post-write-lint.py`, `iac-verification-gate.py`), AWS4 `.drawio` validation, and Athena CUR cost guardrails (`finops-sql-and-cost-gate.py`).
3. **IAM & RBAC least privilege.** Hooks and prompts are defense-in-depth; IAM remains the ultimate boundary. See [docs/iam-guardrails.md](./docs/iam-guardrails.md).

---

## Host Compatibility

| Capability | Claude Code | OpenAI Codex | Other Agent Plugins 1.0.0 Hosts |
|---|---|---|---|
| Skills (`skills/`) | Yes | Yes | Yes |
| Bundled MCP servers | Yes (`.mcp.json`) | Yes (`mcp.json`) | Yes (`mcp.json`) |
| Specialist sub-agent | Yes (`agents/`) | Copy `codex/agents/<name>.toml` | Host-dependent |
| Deterministic hooks | Yes | Yes (after trust) | Host-dependent |
| Slash commands (`commands/*.md`) | Yes | No (skills still apply) | Host-dependent |

Bundled MCP servers start automatically when a plugin is enabled; connection-bound servers (endpoints, secrets, or Docker runtimes) are documented as optional connectors in each plugin's `CONNECTORS.md`. See [docs/mcp-server-coverage.md](./docs/mcp-server-coverage.md) for the full coverage matrix.

---

## Validation & Skill Evaluations

All plugins and canonical skills are backed by an open-source, three-layer validation and evaluation pipeline (`evals/` stays at the repo root so users incur zero install overhead):

```bash
python3 scripts/validate_plugins.py                                      # manifest, binding, hook, portable & Codex checks
python3 scripts/validate_plugins.py --claude                             # also run `claude plugin validate`
python3 scripts/eval_skills.py static                                    # static skill, link, script, drift & hygiene audit
python3 scripts/eval_skills.py trigger --skill <name> --harness claude   # 4-quadrant trigger precision/recall eval
python3 scripts/eval_skills.py run --skill <name> --harness claude       # isolated end-to-end skill, MCP & safety-hook eval
```

See [evals/README.md](./evals/README.md) for schemas and authoring rules, and [docs/authoring-agent-plugins.md](./docs/authoring-agent-plugins.md) for plugin specifications.

<details>
<summary><b>Repository Layout</b></summary>

```text
.claude-plugin/marketplace.json   # Claude Code marketplace catalog
.agents/plugins/marketplace.json  # Codex marketplace catalog
plugins/
  agent-plugins/<agent>/          # Specialist sub-agent plugins (Claude Code, Portable, Codex)
  vertical-plugins/<domain>/      # Main-agent AWS domain bundles
  partner-built/<vendor>/         # Vendor & cloud-native ecosystem plugins
evals/                            # Canonical skill evaluation suites & JSON Schemas
scripts/                          # Plugin validator (validate_plugins.py) & eval runner (eval_skills.py)
docs/                             # Authoring guide, IAM guardrails, MCP coverage, evals guides
llms.txt                          # Machine-readable repository index for LLMs & coding agents
```

</details>

---

## Contributing & Community

Contributions are welcome—new skills, bug fixes, safety hooks, evaluation suites, and new agent, vertical, or partner-built plugins.

- **[CONTRIBUTING.md](./CONTRIBUTING.md)** — How to update skills, sync shared mirrors, add new plugins, author evals, and pass pre-PR checks.
- **[docs/authoring-agent-plugins.md](./docs/authoring-agent-plugins.md)** — Technical specification for manifests, MCP bindings, connectors, and hooks.
- **[SECURITY.md](./SECURITY.md)** — Responsible vulnerability disclosure and defense-in-depth safety model.
- **[CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)** — Community standards and expectations.
- **[llms.txt](./llms.txt)** — Structured repository map for AI assistants and LLM crawlers.

## License

Apache-2.0. See [LICENSE](./LICENSE) and [NOTICE](./NOTICE) for full license terms and upstream attribution.
