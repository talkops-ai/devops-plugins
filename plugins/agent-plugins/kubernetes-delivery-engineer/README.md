# Kubernetes Delivery Engineer

Principal Kubernetes Application Onboarding, GitOps & Progressive Delivery Engineer: end-to-end workload packaging and release management with Helm (chart discovery, values validation, security scanning, atomic upgrades, rollbacks), GitOps continuous delivery with ArgoCD (repository/project onboarding, sync orchestration, drift remediation, history rollbacks), progressive delivery with Argo Rollouts (Deployment-to-Rollout migration, canary/blue-green strategies, Prometheus AnalysisTemplate gating, experiments), multi-stage freight promotion pipelines with Kargo (Warehouse discovery, Stage DAGs, freight promotion/approval, stage verification), and ingress/traffic routing with Traefik v3 (HTTP/TCP/UDP IngressRoutes, weighted canary services, traffic mirroring, middlewares, TLS/mTLS policies, NGINX annotation migration, and security posture auditing).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install kubernetes-delivery-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/kubernetes-delivery-engineer.toml`](./codex/agents/kubernetes-delivery-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, hook, and MCP server below is bound to the [`kubernetes-delivery-engineer`](./agents/kubernetes-delivery-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-kubernetes-delivery-engineer:kubernetes-delivery-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent kubernetes-delivery-engineer:kubernetes-delivery-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `kubernetes-delivery-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills (24)

| Domain | Skill | What it does |
|---|---|---|
| **Helm** | `deploying-helm-charts` | Discover, validate, plan, and install Helm charts on Kubernetes clusters using the Helm MCP server. |
| **Helm** | `reviewing-helm-release-security` | Audit rendered Helm chart manifests for Kubernetes security risks before installation or upgrade. |
| **Helm** | `troubleshooting-helm-releases` | Diagnose and remediate failed, degraded, or stuck Helm releases and Kubernetes pods. |
| **Helm** | `upgrading-and-rolling-back-helm-releases` | Plan, diff, upgrade, and roll back existing Helm releases safely with values-merge strategy guidance. |
| **ArgoCD** | `deploying-argocd-applications` | Deploy, sync, diff, and update Kubernetes applications through ArgoCD GitOps workflows. |
| **ArgoCD** | `onboarding-argocd-repositories-and-projects` | Onboard Git/Helm/OCI repositories and configure AppProject RBAC boundaries in ArgoCD. |
| **ArgoCD** | `rolling-back-argocd-applications` | Safely roll back degraded or misconfigured ArgoCD applications to a previous deployment revision. |
| **ArgoCD** | `troubleshooting-argocd-applications` | Diagnose and resolve OutOfSync, Degraded, Unknown, and ComparisonError states in ArgoCD applications. |
| **Argo Rollouts** | `gating-rollouts-with-analysis-and-experiments` | Gate Argo Rollouts on automated metric checks and run side-by-side canary baseline Experiments. |
| **Argo Rollouts** | `onboarding-and-migrating-to-argo-rollouts` | Create new Argo Rollouts or migrate existing Kubernetes Deployments to Canary or Blue-Green progressive delivery. |
| **Argo Rollouts** | `progressing-argo-rollouts` | Operate day-2 progressive delivery releases for Argo Rollouts (image updates, step promotion, pause/resume, abort). |
| **Argo Rollouts** | `troubleshooting-argo-rollouts` | Diagnose and recover Degraded, paused, or stuck Argo Rollouts and failed AnalysisRuns. |
| **Kargo** | `managing-kargo-credentials-and-access` | Configure Kargo repository credentials (`git`, `image`, `chart`, `generic`) and project RBAC roles. |
| **Kargo** | `onboarding-kargo-pipelines` | Design and bootstrap new Kargo v1.12 projects, Warehouses, PromotionTasks, and multi-stage pipelines. |
| **Kargo** | `promoting-and-approving-freight` | Discover freight, approve manual gates, promote freight to target stages, and manage verification runs. |
| **Kargo** | `rolling-back-kargo-stages` | Safely roll back a Kargo stage to a previously verified freight and re-run post-rollback verification. |
| **Kargo** | `troubleshooting-kargo-pipelines` | Diagnose and resolve Kargo v1.12 pipeline failures across Warehouses, Stages, Promotions, and AnalysisRuns. |
| **Traefik v3** | `adopting-traefik-nginx-ingress-provider` | Migrate Kubernetes Ingress resources from `ingress-nginx` to Traefik v3 NGINX provider or native IngressRoutes. |
| **Traefik v3** | `auditing-traefik-security-posture` | Audit Traefik v3 static and dynamic Kubernetes configurations against CIS and OWASP hardening guidelines. |
| **Traefik v3** | `configuring-traefik-middlewares` | Configure and attach Traefik v3 HTTP and TCP middlewares (`Middleware` and `MiddlewareTCP` CRDs). |
| **Traefik v3** | `managing-traefik-traffic-routing` | Configure Traefik v3 HTTP routing, weighted canary/blue-green `TraefikService` splits, and traffic mirroring. |
| **Traefik v3** | `routing-traefik-tcp-and-udp` | Configure Traefik v3 Layer-4 TCP and UDP routing (`IngressRouteTCP` and `IngressRouteUDP`). |
| **Traefik v3** | `securing-traefik-tls-and-certificates` | Configure Traefik v3 TLS policies (`TLSOption`, `TLSStore`) and backend mTLS (`ServersTransport`). |
| **Traefik v3** | `troubleshooting-traefik-routing` | Diagnose and resolve Traefik v3 routing, middleware, TLS, and upstream errors (404, 500, 502, 503, 504). |

## Slash commands (4)

| Command | Arguments | Purpose |
|---|---|---|
| `/kubernetes-delivery-engineer:canary` | `<rollout-or-service> [--namespace <ns>] [--step promote\|pause\|abort\|migrate]` | Configure, start, analyze, or promote progressive canary/blue-green rollouts with Argo Rollouts `AnalysisTemplate` gates and Traefik traffic splitting. |
| `/kubernetes-delivery-engineer:deploy` | `<release, argocd-app, or kargo-stage> [--namespace <ns>] [--revision <tag-or-sha>]` | Validate rendered manifests, security posture, and live diffs before executing a gated Helm, ArgoCD, or Kargo deployment. |
| `/kubernetes-delivery-engineer:onboard` | `<service-name, repo-url, or chart-path> [--namespace <ns>] [--gitops argocd\|kargo]` | Onboard a workload or repository end-to-end across Helm charts, ArgoCD projects/applications, Kargo promotion stages, and Traefik ingress. |
| `/kubernetes-delivery-engineer:rollback` | `<release, rollout, argocd-app, or kargo-stage> [--namespace <ns>] [--to-revision <rev>]` | Capture pre-rollback diagnostics and execute a safe rollback across Helm releases, ArgoCD applications, Argo Rollouts, or Kargo stages. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). Every server is pinned to its published PyPI release (also available on Docker Hub under `talkopsai/<server-name>`) and starts in read-only mode (`MCP_ALLOW_WRITE=false`) by default.

`.mcp.json` and `mcp.json` intentionally keep only `FASTMCP_LOG_LEVEL`, `MCP_ALLOW_WRITE`, and portable `${PLUGIN_DATA}` paths in `env` so they never override `.env` files, alternate variable aliases, or local `KUBECONFIG` discovery. Each server applies the built-in defaults below automatically when an environment variable is unset, and your agent host or runtime can pass any of the variables below in `env` to customize connectivity and behavior.

| Server | Package & release | Launch (`stdio`) | Claude Code tool pattern | Surface |
|---|---|---|---|---|
| `helm` | [`talkops-helm-mcp-server==0.5.1`](https://pypi.org/project/talkops-helm-mcp-server/0.5.1/) · [`helm-mcp-server/v0.5.1`](https://github.com/talkops-ai/talkops-mcp/releases/tag/helm-mcp-server/v0.5.1) | `uvx --from talkops-helm-mcp-server==0.5.1 helm-mcp-server --transport stdio` | `mcp__plugin_kubernetes-delivery-engineer_helm__*` | 13 tools (7 read-only), 10 `helm://` resources |
| `argocd` | [`talkops-argocd-mcp-server==0.4.1`](https://pypi.org/project/talkops-argocd-mcp-server/0.4.1/) · [`argocd-mcp-server/v0.4.1`](https://github.com/talkops-ai/talkops-mcp/releases/tag/argocd-mcp-server/v0.4.1) | `uv run --no-project --quiet python .../scripts/launch_argocd_mcp.py --from talkops-argocd-mcp-server==0.4.1 argocd-mcp-server --transport stdio` | `mcp__plugin_kubernetes-delivery-engineer_argocd__*` | 24 tools (13 read-only), 8 `argocd://` resources |
| `argo-rollout` | [`talkops-argo-rollout-mcp-server==0.2.1`](https://pypi.org/project/talkops-argo-rollout-mcp-server/0.2.1/) · [`argo-rollout-mcp-server/v0.2.1`](https://github.com/talkops-ai/talkops-mcp/releases/tag/argo-rollout-mcp-server/v0.2.1) | `uvx --from talkops-argo-rollout-mcp-server==0.2.1 argo-rollout-mcp-server --transport stdio` | `mcp__plugin_kubernetes-delivery-engineer_argo-rollout__*` | 15 tools (3 read-only), 13 `argorollout://` resources |
| `kargo` | [`talkops-kargo-mcp-server==0.2.1`](https://pypi.org/project/talkops-kargo-mcp-server/0.2.1/) · [`kargo-mcp-server/v0.2.1`](https://github.com/talkops-ai/talkops-mcp/releases/tag/kargo-mcp-server/v0.2.1) | `uvx --from talkops-kargo-mcp-server==0.2.1 kargo-mcp-server --transport stdio` | `mcp__plugin_kubernetes-delivery-engineer_kargo__*` | 20 tools (4 read-only), 18 `kargo://` resources |
| `traefik` | [`talkops-traefik-mcp-server==0.2.1`](https://pypi.org/project/talkops-traefik-mcp-server/0.2.1/) · [`traefik-mcp-server/v0.2.1`](https://github.com/talkops-ai/talkops-mcp/releases/tag/traefik-mcp-server/v0.2.1) | `uvx --from talkops-traefik-mcp-server==0.2.1 traefik-mcp-server --transport stdio` | `mcp__plugin_kubernetes-delivery-engineer_traefik__*` | 15 tools (5 read-only), 12 `traefik://` resources |

### Environment variable reference (defaults & customization)

Pass these environment variables from your shell, `.env`, agent runtime `env` map, or `~/.codex/config.toml` (`[mcp_servers.<server>.env]`) to target your clusters and control planes:

#### `helm` (`talkops-helm-mcp-server`)

| Environment variable | Requirement | Built-in default | Description |
|---|---|---|---|
| `KUBECONFIG` | Required if `~/.kube/config` is absent | `~/.kube/config` | Path to kubeconfig file used by Helm and Kubernetes API calls (use an absolute path, not `~`, because the `helm` binary does not expand `~` in `KUBECONFIG`). |
| `HELM_CACHE_HOME` | Optional | `${PLUGIN_DATA}/helm-cache` (`mcp.json`) | Isolated Helm repository/chart cache directory. |
| `HELM_CONFIG_HOME` | Optional | `${PLUGIN_DATA}/helm-config` (`mcp.json`) | Isolated Helm repository config directory. |
| `HELM_TIMEOUT` | Optional | `300` | Timeout in seconds for Helm CLI operations. |
| `K8S_TIMEOUT` | Optional | `30` | Timeout in seconds for Kubernetes API operations. |
| `MCP_ALLOW_WRITE` | Optional | `false` | Set to `true` to enable `helm_install_chart`, `helm_upgrade_release`, `helm_rollback_release`, `helm_uninstall_release`, and `helm_ensure_repository`. |
| `MCP_TOOLSETS` | Optional | `all` | Comma-separated toolset filter: `all`, `read`, `mutate`. |

#### `argocd` (`talkops-argocd-mcp-server`)

Supports **either** a pre-issued `ARGOCD_AUTH_TOKEN` **or** automatic session login from `ARGOCD_USERNAME` + `ARGOCD_PASSWORD` via [`scripts/launch_argocd_mcp.py`](./scripts/launch_argocd_mcp.py) (which exchanges credentials at `POST /api/v1/session`, validates the JWT at `GET /api/v1/applications?limit=1`, injects `ARGOCD_AUTH_TOKEN` in-memory, scrubs `ARGOCD_PASSWORD`, and `execvp`s `uvx --from talkops-argocd-mcp-server==0.4.1 ...`):

| Environment variable | Requirement | Built-in default | Description |
|---|---|---|---|
| `ARGOCD_SERVER_URL` (or `ARGOCD_SERVER`) | **Required** outside in-cluster DNS | `https://argocd-server.argocd.svc:443` | Base URL of your ArgoCD API server (e.g., `https://argocd.example.com` or `https://localhost:8080`). |
| `ARGOCD_AUTH_TOKEN` | **Required** (unless `ARGOCD_USERNAME` + `ARGOCD_PASSWORD` are set) | *auto-fetched if username/password set* | ArgoCD API Bearer token. When omitted, `launch_argocd_mcp.py` automatically fetches and validates a session token before starting `argocd-mcp-server`. |
| `ARGOCD_USERNAME` / `ARGOCD_PASSWORD` | Alternative to `ARGOCD_AUTH_TOKEN` | *none* | ArgoCD login credentials exchanged at startup (`POST /api/v1/session`) when `ARGOCD_AUTH_TOKEN` is unset. |
| `ARGOCD_INSECURE` (or `ARGOCD_VERIFY_TLS=false`) | Optional | `false` (`ARGOCD_VERIFY_TLS=true`) | Skip TLS certificate verification for self-signed ArgoCD servers. |
| `ARGOCD_TIMEOUT` | Optional | `300` | Timeout in seconds for ArgoCD API requests (`ARGOCD_MAX_RETRIES` defaults to `2`). |
| `GIT_USERNAME` / `GIT_PASSWORD` | Conditional | `""` / *none* | Server-side HTTPS credentials used by `onboard_repository` for private Git/Helm repos. |
| `SSH_PRIVATE_KEY_PATH` | Conditional | `~/.ssh/id_rsa` | Server-side SSH private key path used by `onboard_repository` for SSH repos. |
| `MCP_ALLOW_WRITE` | Optional | `false` | Set to `true` to enable application create/sync/rollback/delete and repository/project onboarding tools. |
| `MCP_TOOLSETS` | Optional | `all` | Comma-separated toolset filter: `all`, `applications`, `deployments`, `repositories`, `projects`, `readonly`. |

#### `argo-rollout` (`talkops-argo-rollout-mcp-server`)

| Environment variable | Requirement | Built-in default | Description |
|---|---|---|---|
| `K8S_KUBECONFIG` (or `KUBECONFIG`) | Required if `~/.kube/config` is absent and `K8S_IN_CLUSTER=false` | `~/.kube/config` | Path to kubeconfig file. |
| `K8S_CONTEXT` | Optional | current kubeconfig context | Target Kubernetes context name (omit rather than setting `""` when using current context). |
| `K8S_IN_CLUSTER` | Optional | `false` | Set to `true` when running inside a Kubernetes Pod with a ServiceAccount. |
| `K8S_NAMESPACE` (or `MCP_NAMESPACE`) | Optional | *all namespaces* | Default namespace scope when omitted in tool arguments. |
| `PROMETHEUS_URL` | Conditional | `http://prometheus:9090` | Prometheus base URL required for `argo_compare_canary_metrics` and `argorollout://metrics/*` resources. |
| `MCP_ALLOW_WRITE` | Optional | `false` | Set to `true` to enable rollout creation, image/strategy updates, promote/pause/abort, and Deployment migration tools. |
| `MCP_TOOLSETS` | Optional | `all` | Comma-separated toolset filter: `all`, `rollouts`, `migration`, `analysis`, `diagnostics`, `readonly`. |

#### `kargo` (`talkops-kargo-mcp-server`)

| Environment variable | Requirement | Built-in default | Description |
|---|---|---|---|
| `KARGO_BASE_URL` (or `KARGO_API_URL`) | **Required** if not on `localhost:8080` | `http://localhost:8080` | Kargo API server URL (e.g., `https://kargo.example.com`). |
| `KARGO_AUTH_MODE` | Optional | `admin` | Authentication mode: `admin`, `static`, or `passthrough`. |
| `KARGO_ADMIN_PASSWORD` | **Required when `KARGO_AUTH_MODE=admin`** | *none* | Admin password exchanged for a Kargo admin token (`RuntimeError` if `admin` mode is used without it). |
| `KARGO_STATIC_BEARER_TOKEN` (or `KARGO_AUTH_TOKEN`) | **Required when `KARGO_AUTH_MODE=static`** | *none* | Static OIDC / Kubernetes ServiceAccount Bearer token for Kargo API authentication. |
| `KARGO_VERIFY_SSL` | Optional | `true` | Set to `false` to skip TLS verification on self-signed Kargo endpoints. |
| `KARGO_PROJECT` (or `KARGO_DEFAULT_PROJECT`) | Optional | *none* | Default Kargo project name when omitted in tool calls. |
| `KARGO_REPO_USERNAME` / `KARGO_REPO_PASSWORD` / `KARGO_CRED_<REF>_*` / `KARGO_CREDENTIALS_FILE` | Conditional | *none* | Server-side credential sources read by `kargo_manage_credentials` so secrets never pass through LLM tool arguments. |
| `MCP_ALLOW_WRITE` | Optional | `false` | Set to `true` to enable project/warehouse/stage/freight promotion, approval, rollback, credential, and RBAC mutation tools. |
| `MCP_TOOLSETS` | Optional | `all` | Comma-separated toolset filter: `all`, `pipeline`, `promotion`, `verification`, `credentials`, `rbac`, `diagnostics`, `readonly`. |

#### `traefik` (`talkops-traefik-mcp-server`)

| Environment variable | Requirement | Built-in default | Description |
|---|---|---|---|
| `K8S_KUBECONFIG` (or `KUBECONFIG`) | Required if `~/.kube/config` is absent and `K8S_IN_CLUSTER=false` | `~/.kube/config` | Path to kubeconfig file. |
| `K8S_CONTEXT` | Optional | current kubeconfig context | Target Kubernetes context name (omit rather than setting `""` when using current context). |
| `K8S_IN_CLUSTER` | Optional | `false` | Set to `true` when running inside a Kubernetes Pod. |
| `TRAEFIK_NAMESPACE` | Optional | `traefik` | Namespace where the Traefik v3 controller runs (automatically added to `MCP_PROTECTED_NAMESPACES`). |
| `TRAEFIK_API_URL` / `TRAEFIK_HTTP_URL` / `TRAEFIK_HTTPS_URL` | Optional | *via Kubernetes pod/proxy discovery* | Direct URLs to the Traefik dashboard API and HTTP/HTTPS entrypoints for `traefik_trace_request`. |
| `PROMETHEUS_URL` (or `PROMETHEUS_BASE_URL`) | Conditional | `http://prometheus:9090` | Prometheus base URL required for `traefik_compare_traffic_metrics`. |
| `MCP_ALLOWED_NAMESPACES` / `MCP_PROTECTED_NAMESPACES` | Optional | *all* / `kube-system,traefik` | Comma-separated namespace write allowlist and confirmation-gated namespaces. |
| `MCP_ALLOW_WRITE` | Optional | `false` | Set to `true` to enable route, weighted service, mirroring, middleware, TLS, and resource deletion tools. |
| `MCP_TOOLSETS` | Optional | `all` | Comma-separated toolset filter: `all`, `traffic`, `policies`, `diagnostics`, `readonly`. |

### Passing custom `env` values from an agent host

When injecting environment variables from an agent platform or overriding `mcpServers.<server>.env`, pass only the non-empty settings you want to customize:

```json
{
  "helm": {
    "env": {
      "KUBECONFIG": "/etc/kube/config",
      "MCP_ALLOW_WRITE": "false"
    }
  },
  "argocd": {
    "env": {
      "ARGOCD_SERVER_URL": "https://argocd.example.com",
      "ARGOCD_USERNAME": "admin",
      "ARGOCD_PASSWORD": "<argocd-password-or-set-ARGOCD_AUTH_TOKEN-directly>",
      "ARGOCD_INSECURE": "false",
      "MCP_ALLOW_WRITE": "false"
    }
  },
  "argo-rollout": {
    "env": {
      "KUBECONFIG": "/etc/kube/config",
      "K8S_CONTEXT": "prod-cluster",
      "PROMETHEUS_URL": "http://prometheus.monitoring.svc:9090",
      "MCP_ALLOW_WRITE": "false"
    }
  },
  "kargo": {
    "env": {
      "KARGO_BASE_URL": "https://kargo.example.com",
      "KARGO_AUTH_MODE": "static",
      "KARGO_STATIC_BEARER_TOKEN": "<kargo-bearer-token>",
      "MCP_ALLOW_WRITE": "false"
    }
  },
  "traefik": {
    "env": {
      "KUBECONFIG": "/etc/kube/config",
      "K8S_CONTEXT": "prod-cluster",
      "TRAEFIK_NAMESPACE": "traefik",
      "PROMETHEUS_URL": "http://prometheus.monitoring.svc:9090",
      "MCP_ALLOW_WRITE": "false"
    }
  }
}
```

## Hooks

- **SessionStart** `startup|resume` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/session-argocd-preflight.py"` (validates or auto-fetches `ARGOCD_AUTH_TOKEN` from `ARGOCD_USERNAME`/`ARGOCD_PASSWORD`, exports it to `CLAUDE_ENV_FILE` when supported, and injects a redacted preflight status).
- **PreToolUse** `Bash|mcp__.*|mcp__plugin_kubernetes-delivery-engineer_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`

## Upstream

MCP servers and domain skills are maintained in [`talkops-ai/talkops-mcp`](https://github.com/talkops-ai/talkops-mcp) (Apache-2.0).
