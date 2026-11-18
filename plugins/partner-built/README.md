# Partner-built plugins

Plugins that wrap third-party or cloud-native ecosystem products (IaC tooling, Kubernetes control planes, feature management, observability, security, and graph databases). They preserve the upstream project's conventions, identity, and license, and ship the Claude Code, portable Agent Plugins 1.0.0, and Codex layouts.

| Plugin | Vendor / Maintainer | License | Skills | Commands | What it holds |
|---|---|---|---:|---:|---|
| [`terraform`](./terraform) | HashiCorp | MPL-2.0 | 16 | 0 | All 16 official HashiCorp Terraform skills: configuration style, modules, tests, search/import, Stacks, Sentinel/OPA policy, Azure Verified Modules, and provider development. |
| [`crossplane-aws-engineer`](./crossplane-aws-engineer) | TalkOps | MIT | 1 | 0 | Crossplane AWS platform engineering skill and specialist agent: Upbound `provider-family-aws`, XRDs, Claims, Pipeline Compositions, IRSA/ProviderConfig authentication, tested fixtures, and offline schema validation scripts. |
| [`launchdarkly`](./launchdarkly) | LaunchDarkly | Apache-2.0 | 19 | 4 | Official LaunchDarkly feature flag management, progressive guarded rollouts, experimentation, observability (logs, traces, errors, sessions), and AI Config / Agent Control graph skills (`LAUNCHDARKLY_ACCESS_TOKEN`). |
| [`coralogix`](./coralogix) | Coralogix | Apache-2.0 | 19 | 4 | Official Coralogix DataPrime log/span analytics, PromQL metrics, alerts, cases, service catalog, RUM, AI Center, dashboards, Olly, and TCO data-usage skills (`CORALOGIX_API_KEY`, `CORALOGIX_REGION`). |
| [`honeycomb`](./honeycomb) | Honeycomb.io | Apache-2.0 | 7 | 4 | Official Honeycomb high-cardinality production investigation, wide-event/BubbleUp query patterns, OpenTelemetry metrics, SLO burn-rate & trigger triage, trace verification, and board creation skills (`HONEYCOMB_API_KEY`, `HONEYCOMB_MCP_URL`). |
| [`elastic`](./elastic) | Elastic | Apache-2.0 | 6 | 4 | Official Elastic SRE incident triage, service reliability, Kubernetes investigation, Cloud Security Posture (CSP), and LLM observability skills (`ELASTIC_PROJECT`, `ELASTIC_REGION`, `ELASTIC_API_KEY`). |
| [`neo4j`](./neo4j) | Neo4j, Inc. | Apache-2.0 | 1 | 2 | Official Neo4j 2026.x read-only diagnostics and `A1`–`A12` support runbooks for self-managed Neo4j on Amazon EKS, ECS, and EC2 (`NEO4J_MCP_URL`, `NEO4J_MCP_AUTH`). |
| [`bronto`](./bronto) | Bronto | Apache-2.0 | 3 | 3 | Official Bronto dataset/collection discovery, SQL-style log search and time-series aggregation, and production error spike investigation skills (`BRONTO_API_KEY`, `BRONTO_REGION`). |

To add or maintain a partner-built plugin, follow the standards in [docs/authoring-agent-plugins.md](../../docs/authoring-agent-plugins.md#partner-built-plugins).
