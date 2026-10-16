# TalkOps DevOps Plugins

Production-grade agents, skills, slash commands, deterministic safety hooks, and MCP servers for AWS architecture, cloud engineering, FinOps, security, and SRE operations.

The marketplace contains **40 plugins** across three categories:

- **[Agent plugins (17)](./plugins/agent-plugins)**: one named Principal-level AWS specialist agent per plugin. Every skill, slash command, safety hook, and MCP server in the plugin is bound to that agent, and the host runtime spawns the agent as an isolated sub-agent. Each agent plugin is **self-contained**.
- **[Vertical plugins (21)](./plugins/vertical-plugins)**: focused AWS domain bundles of skills (**245 total**), multi-phase slash-command playbooks (**109 total**), safety hooks, and MCP servers that attach **directly to your main agent**, with no sub-agent hand-off. Install a vertical when you want deep AWS domain capability directly in your primary session.
- **[Partner-built plugins (2)](./plugins/partner-built)**: ecosystem and vendor plugins (`terraform` and `crossplane-aws-engineer`) that ship with Claude Code, portable Agent Plugins 1.0.0, and Codex layouts.

---

## Agent Plugins (Sub-Agent Specialists)

Each [agent plugin](./plugins/agent-plugins) spawns a dedicated specialist sub-agent with its own scoped MCP servers, skills, slash commands, and guardrails:

| Function | Agent | Skills | Commands | MCP servers | What it does |
|---|---|---:|---:|---|---|
| **Build & deliver** | **[AWS IaC Engineer](./plugins/agent-plugins/aws-iac-engineer)** (`aws-iac-engineer`) | 12 | 0 | `aws-mcp`, `awsiac`, `terraform`, `pulumi` | Multi-engine AWS IaC (CDK, CloudFormation, Terraform/OpenTofu, Pulumi, Crossplane), FinOps cost estimates, brownfield imports, and CI/CD & GitOps pipelines. |
|  | **[AWS Deployment Engineer](./plugins/agent-plugins/aws-deployment-engineer)** (`aws-deployment-engineer`) | 9 | 0 | `awsknowledge`, `awsiac`, `awspricing`, `awsapi`, `cloudwatch` | Codebase discovery → hosting architecture → pre-deploy cost estimate → IaC scaffolding → deployment verification & rollback. |
|  | **[AWS Serverless Engineer](./plugins/agent-plugins/aws-serverless-engineer)** (`aws-serverless-engineer`) | 24 | 0 | `aws-serverless-mcp`, `aws-documentation-mcp`, `aws-dynamodb-mcp`, `aws-sns-sqs-mcp`, `aws-cloudwatch-mcp`, `aws-billing-cost-mcp` + connectors | Lambda (SnapStart, Power Tuning, Durable Functions, Managed Instances), API Gateway, Step Functions, EventBridge, SQS/SNS, DynamoDB, Aurora DSQL, and SAM/CDK. |
|  | **[AWS Amplify Engineer](./plugins/agent-plugins/aws-amplify-engineer)** (`aws-amplify-engineer`) | 9 | 0 | `aws-mcp`, `awsknowledge`, `appsync`, `awsiac`, `dynamodb`, `cloudwatch` | Amplify Gen 2 TypeScript-first full-stack web & mobile apps: Cognito Auth, AppSync Data, S3 Storage, Functions, Custom CDK, and Hosting CI/CD. |
|  | **[AWS Location Engineer](./plugins/agent-plugins/aws-location-engineer)** (`aws-location-engineer`) | 6 | 0 | `aws-mcp`, `awslocation` | Maps, geocoding, places search, route calculation/matrix, geofencing, and device tracking with Amazon Location Service V2. |
| **Platform & operations** | **[AWS Platform Engineer](./plugins/agent-plugins/aws-platform-engineer)** (`aws-platform-engineer`) | 33 | 0 | `aws-mcp`, `aws-iac`, `iam`, `cloudwatch`, `cloudtrail`, `pricing`, `billing-cost`, `well-architected-security`, `eks`, `ecs`, `serverless`, `awsnetwork`, `finch`, `sns-sqs`, `mq` | EC2, Golden AMIs, EKS (Auto Mode, Karpenter, Pod Identity), ECS Fargate, multi-AZ VPC/TGW/Cloud WAN networking, S3/EFS/FSx storage, and Golden Path landing zones. |
|  | **[AWS SRE Agent](./plugins/agent-plugins/aws-sre-agent)** (`aws-sre-agent`) | 29 | 0 | `aws-mcp`, `aws-api`, `cloudwatch`, `appsignals`, `prometheus`, `cloudtrail`, `eks`, `ecs`, `network`, `iac`, `cost-explorer`, `awssupport` | CloudWatch, Application Signals APM, X-Ray, CloudTrail forensics, Managed Prometheus/Grafana, EKS/ECS/VPC/DB reliability, FIS chaos, ARC zonal shift, and COE postmortems. |
|  | **[AWS DevSecOps Engineer](./plugins/agent-plugins/aws-devsecops-engineer)** (`aws-devsecops-engineer`) | 18 | 11 | `aws-mcp`, `aws-security-agent`, `aws-cloudwatch`, `aws-cloudtrail`, `aws-well-architected-security`, `aws-billing` | Live incident RCA, Security Hub CSPM triage, least-privilege IAM, IaC/perimeter hardening, AWS Security Agent SAST/DAST/pentest scans, release gates, and FinOps guardrails. |
| **Security & cost** | **[AWS Cloud Security Engineer](./plugins/agent-plugins/aws-cloud-security-engineer)** (`aws-cloud-security-engineer`) | 9 | 0 | `aws-mcp`, `iam`, `wa-security`, `cloudtrail`, `awsiac`, `cloudwatch`, `awsnetwork` | IAM & SCPs/RCPs, KMS & Secrets Manager data protection, Security Hub OCSF CSPM, GuardDuty & CloudTrail incident response, WAF/Network Firewall perimeter, and container security. |
|  | **[AWS FinOps Engineer](./plugins/agent-plugins/aws-finops-engineer)** (`aws-finops-engineer`) | 2 | 0 | `aws-mcp`, `billing`, `awspricing`, `cloudwatch`, `awsiac` | Cost Explorer & Anomaly Detection, CUR 2.0 Athena SQL analytics, Compute Optimizer P95/P99 rightsizing, Savings Plans/RI modeling, Shift-Left IaC cost estimation, and waste elimination. |
| **Architecture & advisory** | **[AWS Solutions Architect](./plugins/agent-plugins/aws-solutions-architect)** (`aws-solutions-architect`) | 24 | 0 | `aws-mcp`, `awsknowledge`, `awspricing`, `iac`, `bcm`, `tm`, `drawio` | Well-Architected 6-pillar reviews, ADRs, STRIDE threat modeling, Draw.io architecture diagrams, multi-account Landing Zones, multi-region DR tiers, and Bedrock/ML architecture. |
|  | **[AWS Startup Advisor](./plugins/agent-plugins/aws-startup-advisor)** (`aws-startup-advisor`) | 14 | 1 | `aws-mcp`, `aws-pricing`, `aws-billing` | Stage-aware Pre-Seed to Series B architecture, account hygiene audits, Azure/GCP/Heroku → AWS migrations, OpenAI/Anthropic → Bedrock migrations, and AWS Activate optimization. |
| **Data & AI** | **[AWS Data Engineer](./plugins/agent-plugins/aws-data-engineer)** (`aws-data-engineer`) | 25 | 0 | `aws-mcp`, `dataprocessing`, `redshift`, `s3tables`, `cloudwatch`, `spark-troubleshooting` | S3 Tables (Apache Iceberg), AWS Glue (Catalog, Spark ETL, DQDL Data Quality), Lake Formation governance, Athena, Redshift, Kinesis/MSK streaming, MWAA, OpenSearch, and DataZone. |
|  | **[AWS Database Engineer](./plugins/agent-plugins/aws-database-engineer)** (`aws-database-engineer`) | 18 | 0 | `awsknowledge`, `aws-mcp`, `dynamodb`, `cloudwatch`, `postgres`, `mysql`, `elasticache`, `awspricing` + connectors | Workload-driven DB selection, Aurora (PostgreSQL/MySQL/DSQL), RDS, DynamoDB single-table design, ElastiCache (Valkey/Redis), DocumentDB, Keyspaces, Neptune, Performance Insights, and DMS. |
|  | **[AWS AgentCore Engineer](./plugins/agent-plugins/aws-agentcore-engineer)** (`aws-agentcore-engineer`) | 9 | 0 | `aws-mcp`, `awsknowledge`, `agentcore`, `strands-agents`, `cloudwatch`, `appsignals`, `cloudtrail` | Build, connect, deploy, harden, debug, evaluate, and optimize production AI agents on Amazon Bedrock AgentCore (Runtime, Gateway, Memory, Identity, Observability) & Strands Agents. |
|  | **[AWS SageMaker Engineer](./plugins/agent-plugins/aws-sagemaker-engineer)** (`aws-sagemaker-engineer`) | 30 | 0 | `aws-mcp`, `sagemaker`, `awspricing`, `awsiac`, `cloudwatch` | End-to-end ML engineering on Amazon SageMaker AI: distributed training, HyperPod clusters, Bedrock/SageMaker fine-tuning, vLLM/LMI inference endpoints, MLOps Pipelines, and cost/endpoint triage. |
| **Migration & modernization** | **[AWS Modernization Agent](./plugins/agent-plugins/aws-modernization-agent)** (`aws-modernization-agent`) | 13 | 0 | `aws-transform-mcp`, `aws-mcp`, `awsiac`, `postgres` | 7Rs portfolio assessment, Strangler Fig decomposition, AWS Transform (.NET, Java, mainframe COBOL, SQL Server), VMware MGN replatforming, DMS cutover, and parity verification. |

Each plugin's own `README.md` lists its skills, slash commands, MCP servers, hooks, and optional connectors.

---

## Vertical Plugins (Main-Agent Capability Bundles)

Each [vertical plugin](./plugins/vertical-plugins) binds its skills, slash commands, safety hooks (`secret-safety.py`, `aws-mutation-gate.py`, plus domain linters/gates), and MCP servers **directly to the main agent**:

| Domain | Vertical plugin | Skills | Commands | MCP servers | What it does |
|---|---|---:|---|---|---|
| **Foundation** | **[`aws-essentials`](./plugins/vertical-plugins/aws-essentials)** | 6 | `account-baseline-audit` `sdk-snippet` `setup-auth` `troubleshoot-auth` `whoami` | `aws-mcp`, `awsknowledge`, `awsapi` | Foundational AWS skills for the main agent: credential & SSO preflight verification, account baseline security/billing hygiene audits, and SDK best practices for Python (Boto3), JavaScript/TypeScript v3, and Swift. |
| **Build** | **[`aws-infrastructure-as-code`](./plugins/vertical-plugins/aws-infrastructure-as-code)** | 16 | `bootstrap-app` `brownfield-import` `compare-iac-tools` `generate-iac` `troubleshoot-deploy` `validate-stack` | `aws-mcp`, `awsknowledge`, `awsiac`, `awspricing`, `pulumi` + connectors | End-to-end AWS IaC and deployment skills for the main agent: AWS CDK, CloudFormation, Terraform/OpenTofu, Pulumi, Crossplane/ACK, brownfield resource import, preflight discovery, deployment verification/rollback, and vibe-coded app migration. |
|  | **[`aws-serverless`](./plugins/vertical-plugins/aws-serverless)** | 26 | `api-gateway-design` `configure-event-bus` `debug-invocation` `optimize-cold-starts` `orchestrate-workflow` `scaffold-function` | `aws-mcp`, `aws-serverless-mcp`, `awsknowledge`, `dynamodb`, `sns-sqs`, `cloudwatch`, `billing` + connectors | Comprehensive serverless engineering skills for the main agent: AWS Lambda (SnapStart, Power Tuning, Durable Functions, Managed Instances), API Gateway, Step Functions, EventBridge (Buses, Scheduler, Pipes), SQS/SNS, Event Source Mappings, DynamoDB single-table modeling, Aurora DSQL, and SAM/CDK deployment. |
|  | **[`aws-web-and-mobile`](./plugins/vertical-plugins/aws-web-and-mobile)** | 14 | `amplify-gen2-deploy` `amplify-init` `configure-auth` `graphql-api` `location-maps-and-geofencing` | `aws-mcp`, `awsknowledge`, `appsync`, `awslocation`, `awsiac`, `dynamodb`, `cloudwatch` | Full-stack web, mobile, and geospatial engineering for the main agent: AWS Amplify Gen 2 (TypeScript-first Auth/Cognito, Data/AppSync GraphQL, Functions/CDK, Storage/S3, Hosting CI/CD, AI Kit), AWS Blocks, and Amazon Location Service V2 (Maps, Places, Routes, Trackers, Geofences). |
| **Platform** | **[`aws-compute`](./plugins/vertical-plugins/aws-compute)** | 6 | `beanstalk-ops` `configure-asg` `golden-ami-pipeline` `launch-instance` `rightsize-fleet` | `aws-mcp`, `awsknowledge`, `cloudwatch`, `awspricing`, `awsiac` | EC2 and PaaS compute skills for the main agent: instance family selection (Graviton4, compute/memory/GPU), Auto Scaling Groups, EC2 Image Builder golden AMIs, Elastic Beanstalk, instance profiles, and CloudWatch/Compute Optimizer right-sizing. |
|  | **[`aws-containers`](./plugins/vertical-plugins/aws-containers)** | 5 | `build-push-image` `container-security-audit` `ecs-troubleshoot` `eks-troubleshoot` `karpenter-rightsize` | `aws-mcp`, `eks`, `ecs`, `finch`, `cloudwatch`, `awspricing`, `awsiac` | Production container operations for the main agent: Amazon EKS (Auto Mode, Karpenter, Pod Identity, VPC CNI, CoreDNS), Amazon ECS (Fargate, Express Mode, circuit breakers, stopped-task triage), ECR build/push, and container runtime security. |
|  | **[`aws-networking`](./plugins/vertical-plugins/aws-networking)** | 18 | `audit-vpc` `design-hub-spoke` `harden-network-perimeter` `trace-connectivity` `troubleshoot-dns` | `aws-mcp`, `awsnetwork`, `cloudwatch`, `awsiac`, `awsknowledge` | Enterprise AWS networking and edge perimeter skills for the main agent: multi-AZ VPC design, Transit Gateway, Cloud WAN, VPC Lattice, IPAM, VPC Endpoints/PrivateLink, Direct Connect, Site-to-Site VPN, Route 53, CloudFront, WAF, Shield Advanced, Network Firewall, and Reachability Analyzer diagnostics. |
|  | **[`aws-storage`](./plugins/vertical-plugins/aws-storage)** | 6 | `audit-s3-security` `backup-and-replication-plan` `optimize-storage-tiers` `troubleshoot-efs` | `aws-mcp`, `s3tables`, `cloudwatch`, `awspricing`, `awsiac` | Cloud storage architecture, security, and operations for the main agent: Amazon S3 (Storage Lens, Intelligent-Tiering, Object Lock, S3 Tables), EFS performance & mount troubleshooting, EBS gp3/io2, FSx, AWS Backup vault lock, KMS data protection, and cross-region DR replication. |
|  | **[`aws-messaging-and-streaming`](./plugins/vertical-plugins/aws-messaging-and-streaming)** | 12 | `choose-messaging` `eventbridge-routing` `kinesis-stream-ops` `msk-troubleshoot` `queue-health` | `aws-mcp`, `sns-sqs`, `msk`, `mq`, `cloudwatch`, `awspricing` | Event-driven messaging, streaming, and customer communications for the main agent: SQS, SNS, EventBridge (Event Buses, Pipes, Scheduler), Amazon MSK (Kafka), Kinesis Data Streams, Managed Service for Apache Flink, Amazon MQ, and End-User Messaging (SES, SMS, WhatsApp, Push). |
| **Data & AI** | **[`aws-databases`](./plugins/vertical-plugins/aws-databases)** | 19 | `aurora-cluster-ops` `blue-green-schema-migration` `caching-strategy` `choose-database` `dynamodb-single-table-design` `troubleshoot-db` | `aws-mcp`, `awsknowledge`, `dynamodb`, `postgres`, `mysql`, `elasticache`, `cloudwatch`, `awspricing` + connectors | Full-lifecycle AWS database engineering for the main agent: Aurora (PostgreSQL, MySQL, DSQL), RDS (PostgreSQL, MySQL, MariaDB, Oracle, SQL Server, Db2), DynamoDB, DocumentDB, ElastiCache (Valkey/Redis/Memcached), Keyspaces, Neptune, Timestream for InfluxDB, Performance Insights wait-event triage, Blue/Green deployments, and DMS migrations. |
|  | **[`aws-analytics`](./plugins/vertical-plugins/aws-analytics)** | 27 | `glue-data-quality` `lake-formation-governance` `lakehouse-design` `opensearch-ops` `redshift-optimize` `spark-debug` | `aws-mcp`, `awsdataprocessing`, `redshift`, `s3tables`, `cloudwatch`, `spark-troubleshooting`, `awspricing` | Modern data lakehouse and analytics engineering for the main agent: S3 Tables (Apache Iceberg), AWS Glue (Catalog, Spark ETL, Data Quality DQDL), Lake Formation governance, Amazon Athena, Amazon Redshift, Amazon OpenSearch, EMR, MWAA (Airflow), Kinesis/MSK streaming ingestion, and system-table auditing. |
|  | **[`aws-ai-ml`](./plugins/vertical-plugins/aws-ai-ml)** | 23 | `agentcore-deploy` `bedrock-agent` `genai-rag` `migrate-llm-to-bedrock` `sagemaker-endpoint-triage` `sagemaker-job` | `aws-mcp`, `awsknowledge`, `sagemaker`, `agentcore`, `strands-agents`, `cloudwatch`, `awspricing`, `awsiac` | Production Generative AI, Agentic AI, and ML engineering for the main agent: Amazon Bedrock (Converse API, Knowledge Bases, Guardrails, LLM migration), Amazon Bedrock AgentCore (Build, Connect, Deploy, Harden, Debug, Optimize, Pay) & Strands Agents, and Amazon SageMaker AI (Training, Inference, Fine-Tuning, MLOps Pipelines, Cost Estimation, Endpoint Diagnostics). |
| **Operate** | **[`aws-observability`](./plugins/vertical-plugins/aws-observability)** | 10 | `create-canary` `postmortem-coe` `promql-slo-burnrate` `query-logs` `setup-apm` `triage-incident` | `aws-mcp`, `cloudwatch`, `appsignals`, `cloudtrail`, `prometheus`, `awssupport`, `awsknowledge` | Full-stack AWS observability and SRE incident triage for the main agent: CloudWatch (Metrics, Logs Insights, Alarms, SLOs, Synthetics Canaries), Application Signals APM, X-Ray, Amazon Managed Prometheus (PromQL burn rates) & Grafana, CloudTrail multi-region auditing, GenAI observability, and COE postmortems. |
|  | **[`aws-resilience`](./plugins/vertical-plugins/aws-resilience)** | 11 | `assess-resilience` `chaos-experiment` `dr-strategy-matrix` `game-day-runbook` `zonal-shift` | `aws-mcp`, `awsknowledge`, `cloudwatch`, `appsignals`, `cloudtrail`, `awssupport` | Resilience engineering, disaster recovery, and chaos testing for the main agent: AWS Resilience Hub assessments, AWS Fault Injection Service (FIS) chaos experiments with CloudWatch stop conditions, Route 53 Application Recovery Controller (ARC) zonal shift/region switch, and multi-region RTO/RPO DR architecture. |
| **Secure & govern** | **[`aws-security-identity`](./plugins/vertical-plugins/aws-security-identity)** | 15 | `audit-iam` `audit-kms-and-data-protection` `rotate-secrets` `security-posture` `threat-model-stride` `triage-guardduty-incident` | `aws-mcp`, `iam`, `wa-security`, `aws-security-agent`, `cloudtrail`, `awsiac`, `cloudwatch`, `tm` | Cloud security, identity governance, and incident forensics for the main agent: IAM least-privilege & Access Analyzer, AWS Organizations SCPs/RCPs, KMS & Secrets Manager, Security Hub CSPM (OCSF), GuardDuty & CloudTrail incident triage, WAF/Network Firewall perimeter hardening, container workload security, and STRIDE threat modeling. |
|  | **[`aws-cost-optimization`](./plugins/vertical-plugins/aws-cost-optimization)** | 3 | `cost-anomaly` `cur-athena-query` `estimate-architecture` `rightsize-commitment` `waste-hunt-audit` | `aws-mcp`, `billing`, `awspricing`, `cloudwatch`, `awsiac` | Cloud FinOps and cost engineering for the main agent: Cost Explorer & Anomaly Detection, CUR 2.0 Athena SQL analytics, Compute Optimizer P95/P99 right-sizing, Savings Plans & Reserved Instance commitment modeling, Shift-Left IaC cost estimation, AWS Budgets/Invoicing governance, and waste elimination. |
|  | **[`aws-well-architected`](./plugins/vertical-plugins/aws-well-architected)** | 6 | `architecture-diagram` `generate-adr` `landing-zone-design` `review` `threat-model` | `aws-mcp`, `awsknowledge`, `wa-security`, `awspricing`, `awsiac`, `tm`, `drawio` | Principal Solutions Architecture toolkit for the main agent: AWS Well-Architected Six-Pillar reviews, MADR 3.0 Architecture Decision Records (ADRs), Draw.io & Mermaid architecture diagrams, STRIDE threat modeling, multi-account Landing Zone design, and multi-region DR architecture. |
| **Modernize** | **[`aws-migration`](./plugins/vertical-plugins/aws-migration)** | 10 | `cloud-to-aws-migration` `convert-schema` `migration-plan` `modernize-code` `strangler-fig-cutover` | `aws-mcp`, `aws-transform-mcp`, `awsiac`, `postgres`, `awspricing`, `cloudwatch` | Application, database, and cloud-to-AWS migration skills for the main agent: 7 Rs migration strategy & Strangler Fig decomposition, AWS Transform (.NET, Java, mainframe, SQL), AWS MGN & App2Container, DMS schema conversion & CDC cutover, Babelfish/SQL remediation, and Azure/GCP/Heroku to AWS migrations. |
| **Specialty** | **[`aws-marketplace-seller`](./plugins/vertical-plugins/aws-marketplace-seller)** | 4 | `create-private-offer-workflow` `integrate-metering` `publish-catalog-product` `verify-seller-setup` | `aws-mcp`, `awsknowledge`, `awspricing`, `awsiac`, `cloudwatch` | End-to-end AWS Marketplace ISV & Seller engineering for the main agent: Metering & Entitlement APIs (ResolveCustomer, BatchMeterUsage, RegisterUsage, GetEntitlements), Catalog API product listings (StartChangeSet for SaaS, Container, AMI, GenAI), Private Offers & CPPO with Flexible Payment Scheduler, Agreement API, and SaaS control-plane onboarding. |
|  | **[`aws-end-user-computing`](./plugins/vertical-plugins/aws-end-user-computing)** | 4 | `optimize-euc-costs` `provision-workspaces-fleet` `setup-agent-access` `troubleshoot-stream` | `aws-mcp`, `awsknowledge`, `cloudwatch`, `awspricing`, `awsiac` | AWS End User Computing (EUC) fleet architecture and operations for the main agent: Amazon WorkSpaces Personal & Pools, Active Directory & IAM Identity Center integration, WSP streaming tuning, AutoStop/AlwaysOn cost optimization, Amazon AppStream 2.0 (Elastic, On-Demand, Always-On fleets & Image Builder), WorkSpaces Secure Browser, EUC CloudWatch triage, and WorkSpaces Agent Access. |
|  | **[`aws-quantum-computing`](./plugins/vertical-plugins/aws-quantum-computing)** | 3 | `debug-quantum-task` `design-circuit` `estimate-braket-cost` `launch-hybrid-job` | `aws-mcp`, `awsknowledge`, `cloudwatch`, `awspricing` | Quantum computing and hybrid algorithm engineering on Amazon Braket for the main agent: OpenQASM 3.0 & Braket SDK circuit design, Managed Simulators (SV1, DM1, TN1), QPU hardware targeting (IonQ, Rigetti, IQM, QuEra), Braket Hybrid Jobs (VQE, QAOA, PennyLane adjoint differentiation), pre-execution shot/task cost governance, and VPC/KMS security. |

See the [vertical plugins index](./plugins/vertical-plugins/README.md) for the mapping between each vertical plugin and its counterpart specialist agent plugin(s).

---

## Partner-Built Plugins

| Plugin | Vendor / Maintainer | License | Skills | What it holds |
|---|---|---|---:|---|
| [`terraform`](./plugins/partner-built/terraform) | HashiCorp | MPL-2.0 | 16 | All 16 official Terraform skills: style, modules, tests, search/import, Stacks, Sentinel/OPA policy, Azure Verified Modules, and provider development. Cloud-agnostic; attaches to the main agent. |
| [`crossplane-aws-engineer`](./plugins/partner-built/crossplane-aws-engineer) | TalkOps | MIT | 1 | Crossplane AWS platform engineering skill and specialist agent: Upbound `provider-family-aws`, XRDs, Claims, Pipeline Compositions, IRSA authentication, tested fixtures, and offline schema validation scripts. |

---

## Getting started

### Claude Code

```bash
# Add the marketplace
claude plugin marketplace add talkops-ai/devops-plugins

# Install specialist sub-agents
claude plugin install aws-sre-agent@talkops-devops-plugins
claude plugin install aws-iac-engineer@talkops-devops-plugins

# ...or attach domain capabilities directly to your main agent
claude plugin install aws-networking@talkops-devops-plugins
claude plugin install aws-serverless@talkops-devops-plugins
claude plugin install aws-databases@talkops-devops-plugins
```

Claude delegates to an installed agent plugin automatically based on its description, or you can invoke it explicitly with `@agent-<plugin>:<agent>`, or run it as the main thread:

```bash
claude --agent aws-sre-agent:aws-sre-agent
```

When using a vertical plugin, skills activate automatically on relevant tasks or explicitly via `/<plugin>:<skill>`, and multi-phase operational workflows run via `/<plugin>:<command>` (for example, `/aws-networking:trace-connectivity` or `/aws-databases:troubleshoot-db`).

### Codex

```bash
# Add the marketplace (Codex reads .agents/plugins/marketplace.json)
codex plugin marketplace add talkops-ai/devops-plugins
```

Then install plugins from the Plugins Directory (`/plugins`), or enable them in `~/.codex/config.toml`:

```toml
[plugins."aws-iac-engineer@talkops-devops-plugins"]
enabled = true

[plugins."aws-networking@talkops-devops-plugins"]
enabled = true
```

Codex loads each plugin's skills, MCP servers (from the portable `mcp.json`), and hooks. Approve the hooks when Codex asks you to trust them. Codex plugins can't bundle agents directly, so each agent plugin also ships a Codex custom agent definition. To use a specialist as a sub-agent in Codex, copy its `.toml` into your agents directory:

```bash
cp plugins/agent-plugins/aws-iac-engineer/codex/agents/aws-iac-engineer.toml ~/.codex/agents/
```

Codex starts MCP servers with a minimal environment. If a server can't see your AWS profile, set `AWS_PROFILE` and `AWS_REGION` for it in `~/.codex/config.toml`.

### Other agent hosts

Every agent, vertical, and partner plugin follows the portable [Agent Plugins 1.0.0](https://agent-plugins.org) format: `plugin.json`, `skills/`, and `mcp.json` at the plugin root. Any host that implements it (Cursor, GitHub Copilot, Gemini CLI / Antigravity, Windsurf, and others) can load the skills and MCP servers. Sub-agents, slash commands, and hooks depend on the host.

| Capability | Claude Code | Codex | Other Agent Plugins hosts |
|---|---|---|---|
| Skills | yes | yes | yes |
| Bundled MCP servers | yes (`.mcp.json`) | yes (`mcp.json`) | yes (`mcp.json`) |
| Specialist sub-agent | yes (`agents/`) | copy `codex/agents/<name>.toml` | host-dependent |
| Hooks (secret safety, mutation gate, linters) | yes | yes, after trust | host-dependent |
| Slash commands (`commands/*.md`) | yes | no (skills still apply) | host-dependent |

### Prerequisites

- [`uv`](https://docs.astral.sh/uv/) so that `uvx` can launch the stdio MCP servers, and Node.js (`npx`) for `@drawio/mcp`.
- AWS CLI v2. Credentials come from your environment (`AWS_PROFILE`, IAM Identity Center SSO, or an instance/task role). Foundational plugins bundle `signing-in-to-aws` and `aws-auth-and-environment-preflight`.
- `AWS_REGION` defaults to `us-east-1` in Claude Code when it isn't set; on other hosts, set it in your environment.
- Python 3 on `PATH` for the deterministic safety hooks.
- Optional connection-bound connectors (e.g., RDS/Aurora endpoints, scoped Lambda/Step Functions tools, or the Docker-based `hashicorp/terraform-mcp-server`) are documented in each plugin's `CONNECTORS.md`.

---

## Safety model

Three layers protect your AWS accounts from accidental secret exposure or unapproved mutations across **both agent plugins and vertical plugins**:

1. **Server side (all hosts).** Bundled `awslabs` MCP servers default to read-only flags where supported (`--readonly`, `ALLOW_WRITE=false`, `READ_OPERATIONS_ONLY=true`). Dedicated read-only specialist agents (`aws-sre-agent`, `aws-finops-engineer`, `aws-solutions-architect`) also run `aws-mcp` with `--read-only`.
2. **Deterministic `PreToolUse` / `PostToolUse` hooks.**
   - **`secret-safety.py`**: Blocks shell commands and AWS MCP calls that attempt to print, exfiltrate, or hardcode AWS secret keys, session tokens, or private keys.
   - **`aws-mutation-gate.py`**: Intercepts mutating `aws`, `terraform`, `tofu`, `cdk`, `sam`, `pulumi`, `eksctl`, `kubectl`, `helm`, `copilot`, and `amplify` operations across all 17 agent plugins and all 21 vertical plugins. It blocks mutations outright for read-only agents and requires explicit user confirmation otherwise (`TALKOPS_AWS_MUTATION_GATE=off|warn|ask|deny`).
   - **Domain-specific hooks**: `session-aws-preflight.py` (credential & region preflight), `iac-post-write-lint.py` (`cfn-lint` / `cfn-guard` / `terraform validate` after template edits), `finops-sql-and-cost-gate.py` (Athena CUR SQL partition & cost guardrails), and Aurora DSQL `PostToolUse` transaction checks.
3. **IAM.** The ultimate boundary. See [docs/iam-guardrails.md](./docs/iam-guardrails.md) for read-only roles and AWS MCP condition keys.

---

## How MCP servers bind to plugins

1. Each server is declared in the plugin's `.mcp.json` (Claude Code) and `mcp.json` (portable Agent Plugins 1.0.0 schema).
2. In **agent plugins**, the agent's `tools:` allowlist grants that server by pattern (`mcp__plugin_<plugin>_<server>__*`), isolating each sub-agent to its own MCP servers.
3. In **vertical plugins**, there is no sub-agent wrapper — the bundled skills, slash commands, hooks, and MCP servers attach directly to the main agent.
4. **Connectors.** Servers that require a user-supplied target endpoint, secret ARN, or local Docker runtime at startup (Aurora DSQL, DocumentDB, Neptune, Keyspaces, Valkey, Memcached, SQL Server, Oracle, Timestream for InfluxDB, scoped Lambda/Step Functions tools, and `terraform`) are documented in `CONNECTORS.md` with copy-pasteable `claude mcp add`, `codex mcp add`, and `config.toml` snippets. See [docs/mcp-server-coverage.md](./docs/mcp-server-coverage.md) for the full 62-server coverage matrix.

---

## Repository layout

```
.claude-plugin/marketplace.json   # Claude Code marketplace catalog (name: talkops-devops-plugins)
.agents/plugins/marketplace.json  # Codex marketplace catalog
plugins/
  agent-plugins/<agent>/          # .claude-plugin/plugin.json · agents/<agent>.md · skills/ · commands/ · .mcp.json · hooks/
                                  # plugin.json · mcp.json (portable) · .codex-plugin/plugin.json · codex/agents/<agent>.toml
  vertical-plugins/<domain>/      # .claude-plugin/plugin.json · skills/ · commands/ · .mcp.json · hooks/ · CONNECTORS.md
                                  # plugin.json · mcp.json (portable) · .codex-plugin/plugin.json
  partner-built/<plugin>/         # vendor/ecosystem plugins: same three layouts (Claude Code, Portable, Codex)
src/
  hooks/aws-mutation-gate.py      # canonical TalkOps safety hook
scripts/
  _plugin_lib.py                  # shared dependency-free frontmatter and schema helpers
  validate_plugins.py             # structural, binding, portable-format, and Codex validation across all 40 plugins
docs/
  authoring-agent-plugins.md      # standards for authoring and maintaining agent, vertical, and partner plugins
  iam-guardrails.md               # IAM patterns that back read-only and approval rules
  mcp-server-coverage.md          # how each MCP server is used across agent, vertical, and partner plugins
```

## Validating plugins

All 40 plugins in `plugins/agent-plugins/`, `plugins/vertical-plugins/`, and `plugins/partner-built/` are authored and maintained directly in-place. Run the validator before opening a PR:

```bash
python3 scripts/validate_plugins.py           # structural, manifest, hook, and MCP binding checks
python3 scripts/validate_plugins.py --claude  # also run `claude plugin validate`
```

See [docs/authoring-agent-plugins.md](./docs/authoring-agent-plugins.md) before adding or modifying a plugin.

## License

Apache-2.0. See [LICENSE](./LICENSE) and [NOTICE](./NOTICE) for upstream attribution.
