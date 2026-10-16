# AWS Web and Mobile

Full-stack web, mobile, and geospatial engineering for the main agent: AWS Amplify Gen 2 (TypeScript-first Auth/Cognito, Data/AppSync GraphQL, Functions/CDK, Storage/S3, Hosting CI/CD, AI Kit), AWS Blocks, and Amazon Location Service V2 (Maps, Places, Routes, Trackers, Geofences).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-web-and-mobile@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-amplify-engineer`](../../agent-plugins/aws-amplify-engineer) or [`aws-location-engineer`](../../agent-plugins/aws-location-engineer) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-web-and-mobile:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-web-and-mobile:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `amazon-location-service` | Integrates Amazon Location Service APIs for AWS applications. |
| `amplify-ai-kit` | >- |
| `amplify-auth-cognito` | >- |
| `amplify-data-appsync` | >- |
| `amplify-functions-cdk` | >- |
| `amplify-hosting-cicd` | >- |
| `amplify-storage-s3` | >- |
| `amplify-workflow` | >- |
| `aws-amplify` | > |
| `aws-blocks` | Guides building full-stack applications with AWS Blocks — an Infrastructure-from-Code framework. |
| `location-migration-specialist` | End-to-end migration playbook for moving from Google Maps Platform (Web JS, Android Kotlin, iOS Swift, Backend REST), Mapbox GL/APIs, or Legacy Amazon Location Service V1 (`PlaceIndex`, `RouteCalcula… |
| `location-security-iac-and-finops` | Security, authentication, Infrastructure-as-Code (AWS CDK, Terraform, CloudFormation, Amplify Gen 2), FinOps cost optimization, and regional TPS/RPS quota engineering for Amazon Location Service. |
| `location-tracking-geofencing-iot` | Stateful fleet tracking, geofencing, location integrity verification, predictive ETA breaching, and IoT ingestion architectures using `@aws-sdk/client-location` (`location`). |
| `location-v2-maps-places-routes` | Production implementation blueprint for Amazon Location Service V2 resourceless APIs (`geo-maps`, `geo-places`, `geo-routes`) and bulk Postal Address Validation Jobs (`location:StartJob`). |

## Commands

| Command | Description |
|---|---|
| `/aws-web-and-mobile:amplify-gen2-deploy` | Configure Amplify Hosting full-stack CI/CD branches, SSR compute, custom domains, WAF protection, and AI Kit (`defineConversation`) routes. |
| `/aws-web-and-mobile:amplify-init` | Scaffold an AWS Amplify Gen 2 TypeScript backend (`amplify/backend.ts`) with Auth, Data, Storage, and CDK custom resources. |
| `/aws-web-and-mobile:configure-auth` | Configure Amazon Cognito user pools, identity pools, OAuth/OIDC social providers, MFA, and Lambda triggers in Amplify Gen 2. |
| `/aws-web-and-mobile:graphql-api` | Design an AWS AppSync / Amplify Gen 2 `defineData` GraphQL schema with fine-grained authorization rules, DynamoDB indexes, and custom resolvers. |
| `/aws-web-and-mobile:location-maps-and-geofencing` | Integrate Amazon Location Service V2 (Maps, Places, Routes, Trackers, Geofences, and MapLibre GL JS) with least-privilege API keys/Cognito and EventBridge alerts. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-web-and-mobile_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-web-and-mobile_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `appsync` | stdio | `uvx awslabs.aws-appsync-mcp-server@latest` | `mcp__plugin_aws-web-and-mobile_appsync__*` | AWS AppSync GraphQL and Event APIs, resolvers, and data sources. |
| `awslocation` | stdio | `uvx awslabs.aws-location-mcp-server@latest` | `mcp__plugin_aws-web-and-mobile_awslocation__*` | Amazon Location Service V2 maps, places, geocoding, routes, geofences, and trackers. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-web-and-mobile_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |
| `dynamodb` | stdio | `uvx awslabs.dynamodb-mcp-server>=2.1.6` | `mcp__plugin_aws-web-and-mobile_dynamodb__*` | DynamoDB table/index modeling, capacity inspection, and query validation. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-web-and-mobile_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-web-and-mobile_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-web-and-mobile_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
