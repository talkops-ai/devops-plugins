# Optional connectors: AWS EKS Upgrade Engineer

These optional region-bound or third-party observability/security MCP servers require user-specific endpoints, OAuth sign-in, or API keys, so the plugin does **not** start them automatically. Add any you use under the exact key shown (`mcp__<key>__*`).

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `eks-managed` | [AWS-Managed Amazon EKS MCP Server](https://docs.aws.amazon.com/eks/latest/userguide/eks-mcp.html) | Region-bound SigV4 managed EKS MCP endpoint (`https://eks-mcp.<region>.api.aws/mcp`). |
| `terraform` | [HashiCorp Terraform MCP Server](https://github.com/hashicorp/terraform-mcp-server) | Resolve provider/module version constraints for `terraform-aws-modules/eks/aws` upgrades. |
| `grafana-cloud` | [Grafana Cloud Hosted MCP](https://grafana.com/docs/grafana-cloud/ai-tools/mcp-servers/cloud-mcp/) | Compare pre/post-upgrade Prometheus, Loki, and Tempo SLO signals in Grafana Cloud. |
| `coralogix` | [Coralogix MCP Server](https://coralogix.com/docs/user-guides/ai-center/mcp-server/) | Query Coralogix DataPrime logs and Kubernetes span/alert regressions during upgrade validation. |
| `wiz` | [Wiz DevOps MCP](https://docs.wiz.io/) | Enrich cluster upgrade assessments with Wiz container/AMI CVE and Kubernetes posture findings. |

### `eks-managed`

Connect via `mcp-proxy-for-aws` against `https://eks-mcp.<region>.api.aws/mcp` with `AmazonEKSMCPReadOnlyAccess`.
