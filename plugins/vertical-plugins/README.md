# Vertical plugins

Skill, command, and MCP bundles that attach **directly to the main agent**, with no named sub-agent. Install a vertical when you want a specific capability (say, VPC design or database selection) in your own session; install the matching [agent plugin](../agent-plugins) when you want an isolated specialist with its own tools and guardrails instead.

```bash
claude plugin install aws-networking@talkops-devops-plugins
```

Skills activate from their descriptions, or explicitly with `/<plugin>:<skill>`. Commands run multi-step workflows with `/<plugin>:<command>`.

## AWS verticals

Built from the [AWS Agent Toolkit](https://github.com/aws/agent-toolkit-for-aws) core and specialized skills, grouped by domain (each domain's router skill plus its task skills), with the matching [awslabs/mcp](https://github.com/awslabs/mcp) servers.

| Domain | Plugin | Skills | Commands | MCP servers | Agent alternative |
|---|---|---|---|---|---|
| Foundation | [`aws-essentials`](./aws-essentials) | 4 | `signin` `whoami` `docs` `sdk-review` | aws-mcp, awsknowledge | [`aws-solutions-architect`](../agent-plugins/aws-solutions-architect) |
| Build | [`aws-infrastructure-as-code`](./aws-infrastructure-as-code) | 5 | `validate-template` `troubleshoot-stack` `cdk-preflight` `pipeline` | aws-mcp, awsiac | [`aws-iac-engineer`](../agent-plugins/aws-iac-engineer) |
| | [`aws-serverless`](./aws-serverless) | 13 | `debug-lambda-timeout` `lambda-to-api` `custom-domain` `event-bus` | aws-mcp, aws-serverless-mcp + connectors | [`aws-serverless-engineer`](../agent-plugins/aws-serverless-engineer) |
| | [`aws-web-and-mobile`](./aws-web-and-mobile) | 1 | `amplify-app` `inspect-api` | aws-mcp, appsync | [`aws-amplify-engineer`](../agent-plugins/aws-amplify-engineer) |
| Platform | [`aws-compute`](./aws-compute) | 4 | `launch-ec2` `instance-profile` `golden-ami` | aws-mcp | [`aws-platform-engineer`](../agent-plugins/aws-platform-engineer) |
| | [`aws-containers`](./aws-containers) | 1 | `eks-troubleshoot` `ecs-troubleshoot` `build-push-image` | aws-mcp, eks, ecs, finch | [`aws-platform-engineer`](../agent-plugins/aws-platform-engineer) |
| | [`aws-networking`](./aws-networking) | 14 | `create-vpc` `network-path-check` `protect-web-app` `private-endpoints` | aws-mcp, awsnetwork | [`aws-platform-engineer`](../agent-plugins/aws-platform-engineer) |
| | [`aws-storage`](./aws-storage) | 4 | `secure-s3-bucket` `troubleshoot-efs` `choose-storage` | aws-mcp | [`aws-platform-engineer`](../agent-plugins/aws-platform-engineer) |
| | [`aws-messaging-and-streaming`](./aws-messaging-and-streaming) | 8 | `queue-health` `ses-onboard` `msk-health` `choose-messaging` | aws-mcp, sns-sqs, mq | [`aws-platform-engineer`](../agent-plugins/aws-platform-engineer) |
| Data | [`aws-databases`](./aws-databases) | 16 | `choose-database` `create-aurora-cluster` `export-rds-to-s3` `inspect-schema` | aws-mcp, awsknowledge, dynamodb, postgres, mysql, elasticache + connectors | [`aws-database-engineer`](../agent-plugins/aws-database-engineer) |
| | [`aws-analytics`](./aws-analytics) | 19 | `query` `catalog-inventory` `ingest` `debug-dag` `spark-debug` | aws-mcp, dataprocessing, redshift, s3tables, spark-troubleshooting, spark-upgrade | [`aws-data-engineer`](../agent-plugins/aws-data-engineer) |
| | [`aws-ai-ml`](./aws-ai-ml) | 2 | `bedrock-app` `choose-ml-service` | aws-mcp, sagemaker | [`aws-sagemaker-engineer`](../agent-plugins/aws-sagemaker-engineer) |
| Operate | [`aws-observability`](./aws-observability) | 6 | `investigate` `who-changed` `alarm-setup` `enable-observability` | aws-mcp, cloudwatch, appsignals, cloudtrail, prometheus | [`aws-sre-agent`](../agent-plugins/aws-sre-agent) |
| | [`aws-resilience`](./aws-resilience) | 8 | `resilience-assessment` `chaos-experiment` `dr-plan` | aws-mcp, awsknowledge | [`aws-sre-agent`](../agent-plugins/aws-sre-agent) |
| Secure & govern | [`aws-security-identity`](./aws-security-identity) | 5 | `least-privilege-policy` `access-denied` `security-findings` `create-secret` `scan-code` | aws-mcp, iam, wa-security, security-agent | [`aws-cloud-security-engineer`](../agent-plugins/aws-cloud-security-engineer) |
| | [`aws-cost-optimization`](./aws-cost-optimization) | 1 | `cost-report` `savings` `estimate` | aws-mcp, billing, awspricing | [`aws-finops-agent`](../agent-plugins/aws-finops-agent) |
| | [`aws-well-architected`](./aws-well-architected) | 1 | `review` | aws-mcp, awsknowledge, wa-security | [`aws-solutions-architect`](../agent-plugins/aws-solutions-architect) |
| Modernize | [`aws-migration`](./aws-migration) | 2 | `assess` `convert-schema` | aws-mcp, aws-transform-mcp | [`aws-modernization-agent`](../agent-plugins/aws-modernization-agent) |
| Specialty | [`aws-marketplace-seller`](./aws-marketplace-seller) | 1 | `metering-integration` | aws-mcp | — |
| | [`aws-end-user-computing`](./aws-end-user-computing) | 1 | `workspaces-access` | aws-mcp | — |
| | [`aws-quantum-computing`](./aws-quantum-computing) | 1 | `run-circuit` | aws-mcp | — |

"Connectors" are connection-bound MCP servers (database endpoints, scoped Lambda/Step Functions tools) that you add yourself; see each plugin's `CONNECTORS.md`.

## Notes

- **Read-only by default.** Bundled MCP servers start without write flags; commands that change resources show the plan and wait for approval.
- **One `aws-mcp` per plugin.** Each vertical is self-contained. If you install several, toggle duplicate `aws-mcp` instances off in `/mcp`.
- **Skills, MCP servers, `README.md`, and `CONNECTORS.md` are generated** by `scripts/sync_aws_plugins.py`; `commands/*.md` are hand-written. See [docs/authoring-agent-plugins.md](../../docs/authoring-agent-plugins.md#vertical-plugins).
