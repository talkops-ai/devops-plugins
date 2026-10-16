# Optional connectors: AWS Infrastructure as Code

These MCP servers need a local container runtime (such as Docker) or external workspace credentials (`TFE_TOKEN`) that only you can supply, so the plugin does **not** start them automatically. Add the ones you need to your own agent host configuration with the exact key shown; the key determines the tool names (`mcp__<key>__*`).

Each connector below has a Claude Code command, a Codex command, and the equivalent `~/.codex/config.toml` block. Other MCP hosts take the same `command`, `args`, and `env`.

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `terraform` | [`hashicorp/terraform-mcp-server`](https://github.com/hashicorp/terraform-mcp-server) | Query Terraform Registry provider docs (`hashicorp/aws`, `hashicorp/awscc`), modules, Sentinel/OPA policies, and read-only HCP Terraform workspace state. |

### `terraform`

Claude Code:

```bash
claude mcp add --scope user terraform -- docker run -i --rm -e ENABLE_TF_OPERATIONS=false -e TFE_TOKEN -e TFE_ADDRESS hashicorp/terraform-mcp-server:1
```

Codex:

```bash
codex mcp add terraform -- docker run -i --rm -e ENABLE_TF_OPERATIONS=false -e TFE_TOKEN -e TFE_ADDRESS hashicorp/terraform-mcp-server:1
```

Codex `config.toml`:

```toml
[mcp_servers.terraform]
command = "docker"
args = ["run", "-i", "--rm", "-e", "ENABLE_TF_OPERATIONS=false", "-e", "TFE_TOKEN", "-e", "TFE_ADDRESS", "hashicorp/terraform-mcp-server:1"]
```

Keep `ENABLE_TF_OPERATIONS=false` so the server only inspects documentation, schemas, and workspace state without executing unreviewed `apply`/`destroy` operations.
