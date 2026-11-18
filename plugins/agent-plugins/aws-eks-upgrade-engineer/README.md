# AWS EKS Upgrade Engineer

Principal Amazon EKS Upgrade, Readiness & Lifecycle Engineer: runs **strictly read-only**, evidence-backed EKS Kubernetes version upgrade assessments combining quantitative **0–100% Readiness Scoring** (8 assessment areas, hard-blocker caps, HTML/Markdown reports) with **60+-gate AWS EKS Best Practices validation** (EKS Upgrade Insights, live `managedFields` writer-identity & Helm stored-manifest deprecated API scanning, paginated `DescribeAddonVersions` & live upstream OSS add-on compatibility, Karpenter `KARP-01..14` & `v0.37 → v1.0+` `v1beta1 → v1` migrations, AL2-to-AL2023 `nodeadm` `NodeConfig` & containerd 2.x migrations, `DRAIN-01..06` pre-drain & overlapping-PDB safety, 5-mode VPC CNI surge capacity & ODCR/FDCR sizing, IaC/GitOps ownership routing, post-upgrade smoke validation, 7-day `ROLLBACK_READINESS` checks, and live Extended Support EOS cost exposure analysis).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-eks-upgrade-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-eks-upgrade-engineer.toml`](./codex/agents/aws-eks-upgrade-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins 1.0.0](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, slash command, safety hook, and MCP server below is bound to the [`aws-eks-upgrade-engineer`](./agents/aws-eks-upgrade-engineer.md) specialist sub-agent.

- Claude Code: `@agent-aws-eks-upgrade-engineer:aws-eks-upgrade-engineer` or let Claude delegate automatically on EKS upgrade, AL2023 migration, Karpenter compatibility, or Extended Support cost questions
- Headless: `claude --agent aws-eks-upgrade-engineer:aws-eks-upgrade-engineer`
- Codex: copy [`codex/agents/aws-eks-upgrade-engineer.toml`](./codex/agents/aws-eks-upgrade-engineer.toml) into `~/.codex/agents/` and ask Codex to spawn `aws-eks-upgrade-engineer`

## Skills (7)

| Domain | Skill | What it does |
|---|---|---|
| **Scored Readiness (0–100%)** | `eks-upgrade-check` | Runs 8-area quantitative upgrade readiness scoring (`READY`/`GOOD`/`FAIR`/`RISKY`/`NOT READY`), hard-blocker overrides (`<= 59%`), `managedFields` writer-identity deprecated API filtering, live OSS add-on lookups (`oss_addon_registry.json`), and Markdown + zero-dependency HTML report generation (`scripts/md_to_html.py`). |
| **Best Practices (60+ Gates)** | `eks-upgrade-readiness` | Runs the 17-step AWS EKS Best Practices assessment across `PF-*`, `INFRA-*`, `NODE-*`, `ADDON-*`, `WKLD-*`, `KARP-01..14`, `DRAIN-01..06`, and `ROLL-01..02` gates with Evidence Completeness (`EC%`), 5-mode VPC CNI surge math, Helm stored-manifest scanning, IaC/GitOps ownership routing, Blue-Green vs. In-Place strategy, and CI/CD JSON verdicts. |
| **Node OS & Runtime Migration** | `eks-al2-to-al2023-migration` | Audits AL2 Managed Node Groups, Self-Managed ASGs, Custom AMIs, and Karpenter `EC2NodeClass` resources; translates `/etc/eks/bootstrap.sh` flags into `nodeadm` `NodeConfig` (`node.eks.aws/v1alpha1`) MIME multipart user data; checks cgroup v2 & IMDSv2 hop limits; and plans containerd 2.x cutovers. |
| **Add-ons & Karpenter** | `eks-karpenter-and-addon-upgrades` | Validates EKS Managed Add-ons (`DescribeAddonVersions` pagination, `eksbuild` numeric ordering, `PRESERVE`/`OVERWRITE` conflict resolution), self-managed `aws-node`/`coredns`/`kube-proxy`, retired `ingress-nginx` → Gateway API / AWS LBC migrations, and two-step Karpenter `karpenter-crd` + controller upgrades. |
| **Validation & Rollback** | `eks-post-upgrade-validation-and-rollback` | Executes post-upgrade functional smoke validation against pre-upgrade baselines, triages stalled upgrades (`PodEvictionFailure`, `InsufficientInstanceCapacity`, `ConfigurationConflict`), and evaluates 7-day control-plane `ROLLBACK_READINESS` insights with reverse-order component rollback plans. |
| **EOS & FinOps** | `eks-eos-and-extended-support-cost` | Discovers EKS clusters across regions approaching or in Extended Support, verifies live release calendar dates (`aws-documentation-mcp`), queries live Extended Support surcharge rates (`awspricing`), and builds a prioritized wave upgrade roadmap. |
| **Authentication** | `signing-in-to-aws` | Acquires and validates short-term AWS CLI, SDK, and MCP credentials via `aws login`, `aws sso login`, or `sts:AssumeRole`. |

## Slash commands (5)

| Command | Arguments | Purpose |
|---|---|---|
| `/aws-eks-upgrade-engineer:assess` | `<cluster-name> [--region <region>] [--target <1.XX>] [--format md\|html\|json]` | Full read-only EKS upgrade readiness assessment (0–100% score + 60+-gate report in Markdown, HTML, or CI/CD JSON). |
| `/aws-eks-upgrade-engineer:plan` | `<cluster-name> [--region <region>] [--target <1.XX>] [--strategy in-place\|blue-green]` | IaC/GitOps-routed 12-phase upgrade runbook, VPC CNI surge & ODCR/FDCR capacity plan, and soak/rollback gates. |
| `/aws-eks-upgrade-engineer:migrate-al2023` | `<cluster-name> [--region <region>] [--nodegroup <name>]` | AL2 → AL2023 `nodeadm` `NodeConfig` translation, cgroup v2 / IMDSv2 workload audit, and parallel node-group cutover plan. |
| `/aws-eks-upgrade-engineer:validate-or-rollback` | `<cluster-name> [--region <region>] [--mode post-upgrade\|triage\|rollback]` | Post-upgrade smoke verification, stuck-upgrade triage, or 7-day `ROLLBACK_READINESS` eligibility evaluation. |
| `/aws-eks-upgrade-engineer:eos-cost` | `[--regions <us-east-1,us-west-2,...>]` | Multi-region EKS Extended Support surcharge exposure report and prioritized upgrade savings roadmap. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). **All bundled servers start in read-only mode** (`--read-only` on `aws-mcp`, `READ_OPERATIONS_ONLY=true` on `aws-api`, and `--allow-write` omitted on `eks`).

| Server | Transport | Launch | Claude Code tool pattern |
|---|---|---|---|
| `eks` | stdio | `uvx awslabs.eks-mcp-server@latest` | `mcp__plugin_aws-eks-upgrade-engineer_eks__*` |
| `aws-documentation-mcp` | stdio | `uvx awslabs.aws-documentation-mcp-server@latest` | `mcp__plugin_aws-eks-upgrade-engineer_aws-documentation-mcp__*` |
| `aws-api` | stdio | `uvx awslabs.aws-api-mcp-server@latest` (`READ_OPERATIONS_ONLY=true`) | `mcp__plugin_aws-eks-upgrade-engineer_aws-api__*` |
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 ... --read-only` | `mcp__plugin_aws-eks-upgrade-engineer_aws-mcp__*` |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-eks-upgrade-engineer_cloudwatch__*` |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-eks-upgrade-engineer_awspricing__*` |
| `awsiac` | stdio | `uvx --with 'fastmcp<4.0.0' awslabs.aws-iac-mcp-server@latest` | `mcp__plugin_aws-eks-upgrade-engineer_awsiac__*` |

Optional region-bound and partner telemetry/posture connectors (`eks-managed` for the AWS-Managed EKS MCP Server, `terraform`, `grafana-cloud`, `coralogix`, and `wiz`) are documented in [`CONNECTORS.md`](./CONNECTORS.md).

## Hooks & safety posture

- **`hooks/aws-mutation-gate.py`** (`PreToolUse`, configured with `aws-eks-upgrade-engineer` in `read_only_agents`): Hard-denies any mutating AWS CLI, `kubectl`, `helm`, `eksctl`, `terraform`, `cdk`, or MCP operation against live infrastructure. Local workspace file writes (`Write`/`Edit` for reports and IaC/YAML remediation patches) and `scripts/md_to_html.py` remain allowed.
- **`hooks/secret-safety.py`** (`PreToolUse`) + `permissions.deny`: Blocks `secretsmanager:GetSecretValue` and local credential/key reads (`.env`, `*.pem`, `*.key`, `~/.aws/credentials`).

## Required permissions (read-only)

### AWS IAM

Attach `AmazonEKSMCPReadOnlyAccess` (when using `eks-managed`) or scope a custom read-only IAM policy with:
- **EKS:** `eks:ListClusters`, `eks:DescribeCluster`, `eks:ListNodegroups`, `eks:DescribeNodegroup`, `eks:ListAddons`, `eks:DescribeAddon`, `eks:DescribeAddonVersions`, `eks:ListInsights`, `eks:DescribeInsight`, `eks:ListFargateProfiles`, `eks:DescribeFargateProfile`, `eks:ListUpdates`, `eks:DescribeUpdate`, `eks:ListPodIdentityAssociations`
- **EC2 / Auto Scaling / IAM / Quotas / Pricing:** `ec2:DescribeSubnets`, `ec2:DescribeNetworkInterfaces`, `ec2:DescribeLaunchTemplateVersions`, `ec2:DescribeImages`, `ec2:DescribeCapacityReservations`, `ec2:DescribeSecurityGroups`, `autoscaling:DescribeAutoScalingGroups`, `iam:GetRole`, `iam:ListAttachedRolePolicies`, `servicequotas:GetServiceQuota`, `pricing:GetProducts`

### Kubernetes RBAC

Grant your assessing IAM principal an EKS Access Entry (`AmazonEKSViewPolicy` / `AmazonAIOpsAssistantPolicy` + a least-privilege read-only `ClusterRole` with `["get", "list"]` on `nodes`, `pods`, `services`, `endpoints`, `configmaps`, `events`, `persistentvolumeclaims`, `certificatesigningrequests`, `deployments`, `statefulsets`, `daemonsets`, `replicasets`, `poddisruptionbudgets`, `ingresses`, `networkpolicies`, `horizontalpodautoscalers`, `customresourcedefinitions`, `validatingwebhookconfigurations`, `mutatingwebhookconfigurations`, `flowschemas`, `prioritylevelconfigurations`, `clusterrolebindings`, `nodepools.karpenter.sh`, `nodeclaims.karpenter.sh`, `ec2nodeclasses.karpenter.k8s.aws`, `eniconfigs.crd.k8s.amazonaws.com`, `storageclasses`, and `csinodes`). Any denied read is reported transparently under `## Unassessed` / `UNKNOWN` rather than assumed clean.
