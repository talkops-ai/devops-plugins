# Partner-built plugins

Plugins that wrap third-party or cloud-native ecosystem products (IaC tooling, Kubernetes control planes, observability). They preserve the upstream project's conventions, identity, and license, and ship the Claude Code, portable Agent Plugins 1.0.0, and Codex layouts.

| Plugin | Vendor / Maintainer | License | Skills | What it holds |
|---|---|---|---:|---|
| [`terraform`](./terraform) | HashiCorp | MPL-2.0 | 16 | All 16 official HashiCorp Terraform skills: configuration style, modules, tests, search/import, Stacks, Sentinel/OPA policy, Azure Verified Modules, and provider development. Includes optional `terraform` registry MCP connector. |
| [`crossplane-aws-engineer`](./crossplane-aws-engineer) | TalkOps | MIT | 1 | Crossplane AWS platform engineering skill and specialist agent: Upbound `provider-family-aws`, XRDs, Claims, Pipeline Compositions, IRSA/ProviderConfig authentication, tested teaching fixtures (`vpc-network`, `s3-bucket`, `rds-postgres`), and offline schema validation scripts. |

To add or maintain a partner-built plugin, follow the standards in [docs/authoring-agent-plugins.md](../../docs/authoring-agent-plugins.md#partner-built-plugins).
