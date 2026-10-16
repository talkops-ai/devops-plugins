# AWS Location Engineer

Principal AWS Location Service Engineer & Geospatial Architect: resourceless V2 Maps (`geo-maps`, MapLibre GL JS v5 / Native, 3D terrain/buildings, traffic, political views, static maps), Places V2 (`geo-places`, Autocomplete, Suggest, Geocode `MatchScores`, ReverseGeocode, SearchText, SearchNearby, GetPlace), bulk S3 Parquet Postal Address Validation Jobs (`location:StartJob` `ValidateAddress` for US/CA/UK/AU), Routes V2 (`geo-routes`, CalculateRoutes, CalculateRouteMatrix, CalculateIsolines, OptimizeWaypoints, SnapToRoads, truck & toll routing), stateful fleet Trackers & Geofences (`Geobuf`, `AssociateTrackerConsumer`, `ForecastGeofenceEvents`, `VerifyDevicePosition`, IoT Core MQTT `LocationAction`, EventBridge), V2 API key/Cognito/IAM security, CDK/Terraform/Amplify Gen 2 IaC, FinOps optimization, and migrations from Google Maps, Mapbox, or Legacy AWS Location V1.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-location-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-location-engineer.toml`](./codex/agents/aws-location-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-location-engineer`](./agents/aws-location-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-location-engineer:aws-location-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-location-engineer:aws-location-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `aws-location-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills

| Skill | What it does |
|---|---|
| `amazon-location-service` | Integrates Amazon Location Service APIs for AWS applications. |
| `location-migration-specialist` | End-to-end migration playbook for moving from Google Maps Platform (Web JS, Android Kotlin, iOS Swift, Backend REST), Mapbox GL/APIs, or Legacy Amazon Location Service V1 (`PlaceIndex`, `RouteCalculator`, `Map`) to Reso… |
| `location-security-iac-and-finops` | Security, authentication, Infrastructure-as-Code (AWS CDK, Terraform, CloudFormation, Amplify Gen 2), FinOps cost optimization, and regional TPS/RPS quota engineering for Amazon Location Service. |
| `location-tracking-geofencing-iot` | Stateful fleet tracking, geofencing, location integrity verification, predictive ETA breaching, and IoT ingestion architectures using `@aws-sdk/client-location` (`location`). |
| `location-v2-maps-places-routes` | Production implementation blueprint for Amazon Location Service V2 resourceless APIs (`geo-maps`, `geo-places`, `geo-routes`) and bulk Postal Address Validation Jobs (`location:StartJob`). |
| `signing-in-to-aws` | Gets AWS credentials for CLI/SDK access via `aws login`. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws@latest` | `mcp__plugin_aws-location-engineer_aws-mcp__*` | Managed AWS MCP Server for AWS Location documentation, Agent SOPs, regional availability checks, unwrapped V2 operations (Autocomplete, Suggest, CalculateIsolines, CalculateRouteMatrix, SnapToRoads, GetStaticMap), and stateful location control/data plane APIs (API keys, trackers, geofences, address validation jobs). |
| `awslocation` | stdio | `uvx awslabs.aws-location-mcp-server@latest` | `mcp__plugin_aws-location-engineer_awslocation__*` | Amazon Location Service MCP Server (v2.0.18+) providing 8 live V2 tools (geocode, reverse_geocode, search_places, search_nearby, search_places_open_now, get_place, calculate_route, optimize_waypoints) backed by boto3 geo-places and geo-routes. |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`amazon-location-service`](https://github.com/awslabs/agent-plugins) (awslabs/agent-plugins, Apache-2.0)
- [`amazon-location-agent-context`](https://github.com/aws-geospatial/amazon-location-agent-context) (aws-geospatial/amazon-location-agent-context, MIT-0)
- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
