---
name: agents-get-started
description: >
  Use when a developer wants to create a new agent project or get started
  with AgentCore. Handles framework selection, project scaffolding, first
  deploy, and first invocation. Triggers on: "build an agent", "create an
  agent", "get started", "new project", "agentcore create", "which
  framework", "Strands vs LangGraph", "hello world agent", "first agent",
  "create MCP server", "host MCP server", "agentcore dev", "dev server",
  "what port", "local development".
  Not for adding capabilities to existing projects — use agents-build
  or agents-connect. Strands vs LangGraph in a migration context routes
  to agents-build, not here. Connecting to an existing MCP server routes
  to agents-connect, not here.
allowed-tools: Read Grep Glob Bash
metadata:
  type: skill
  version: "1.0.0"
  author: aws-agentcore
  requires-cli: ">=0.9.0"
---

# get-started

Walk a developer from zero to a running agent on AWS.

## When to use

- Developer wants to build an agent on AWS and doesn't know where to start
- Developer wants to create a new AgentCore project (`agentcore create`)
- Developer is choosing between frameworks (Strands, LangGraph, GoogleADK, OpenAI Agents, or BYO Container)
- Developer just ran `agentcore create` and wants to know what to do next (`agentcore dev`, first deploy, first invoke)

Do NOT use for:
- Environment/prerequisite issues (CLI not found, credentials broken) → use `agents-debug` ([`references/doctor.md`](references/doctor.md))
- Adding capabilities to an existing project (memory, tools, policies) → use `agents-build` or `agents-connect`
- Migrating an existing Bedrock Agent → use `agents-build` ([`references/migrate.md`](references/migrate.md))

## MCP-Only Execution & Read-Only Safety

- **MCP-Only Live Discovery & Docs:** Execute **all** live AWS discovery, AgentCore runtime/gateway/memory inspection, telemetry/log/trace queries, IAM policy checks, and documentation lookups **exclusively via connected MCP tools**: `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`, `aws___search_documentation`, `aws___read_documentation`), `agentcore` (`search_agentcore_docs`, `fetch_agentcore_doc`, `list_agent_runtimes`, `get_agent_runtime`, etc.), `strands-agents` (`search_docs`, `fetch_doc`, `find_integrations`), `cloudwatch`, `appsignals`, `cloudtrail`, `awspricing`, `awsiac`, and `awsknowledge`.
- **Zero Raw CLI Execution, Strictly Read-Only & Secret-Safe:** **Never** run raw `aws ...` or `agentcore ...` CLI commands in Bash/`run_command` to query or mutate live AWS accounts (present CLI commands in Markdown strictly as operator reference snippets). **Never** invoke live mutations (`create_*`, `update_*`, `delete_*`, `InvokeAgentRuntime`, `InvokeModel`) — refuse unapproved destructive/mutating requests and explain the safe approval-gated operator workflow with verification and rollback guidance. **Never** read or print plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter` with `WithDecryption=True`, `.env` / `.env.local` values, or raw memory record contents).
- **Edge-Case Documentation Fallback:** For unmapped AWS/AgentCore/Bedrock/Strands edge cases, run 1–2 focused queries via `agentcore`, `strands-agents`, `awsknowledge`, or `aws-mcp` documentation search tools.

## Input

`$ARGUMENTS` can be:
- A framework preference (`"using LangGraph"`, `"with Strands"`), a protocol (`"MCP server"`, `"A2A"`), a task description (`"a customer support agent"`), or empty (guides selection interactively).

## Process

### Step 0: Verify CLI & toolchain prerequisites

AgentCore CLI `>= 0.9.0` (Node.js `20+`) and **`uv`** (for Python starter projects) are required. Provide these operator checks:
- Check versions: `agentcore --version` and `uv --version` (if `agentcore < 0.9.0`, upgrade via `agentcore update`; if missing, install via `npm install -g @aws/agentcore` on Node.js 20+, and uninstall legacy `bedrock-agentcore-starter-toolkit` if shadowing; see [`references/doctor.md`](references/doctor.md)). Preserve all developer context across upgrades.

### Step 1: Determine intent — exploring or ready to create?

Ask: *"Are you exploring options (comparing frameworks, understanding AgentCore) or ready to create a project?"*
- **Exploring** → Go to Step 2, present options, and wait (do not emit `agentcore create` yet).
- **Ready to create** → Skip to Step 3 (and skip Step 2 if framework is already chosen).
- **Already has a project** → Check if `agentcore/agentcore.json` exists in the workspace (never read `.env.local`); if found, inspect it and skip to Step 5 without re-scaffolding.

### Step 2: Framework selection

Check conversation context first so you don't repeat tables already discussed. When presenting for the first time:

| Framework | CLI `--framework` value | Best for |
|---|---|---|
| Strands | `Strands` | AWS-native, simplest path, tightest AgentCore integration (default **only** if user says "no preference") |
| LangGraph | `LangChain_LangGraph` | Complex cyclic/graph workflows with conditional branching, existing LangChain investment |
| Google ADK | `GoogleADK` | Teams standardized on Google's agent toolkit (`gemini-*` models) |
| OpenAI Agents | `OpenAIAgents` | Teams standardized on OpenAI's Agents SDK |

**Key architecture decision points:**
- **Zero-code declarative config in `agentcore.json`?** → **AgentCore Harness** (ejectable later via `agentcore export harness` into `app/` + `EXPORT_NOTES.md`).
- **Deterministic cyclic graph + `interrupt_before` HITL + AWS-native Bedrock streaming/MCP?** → **Hybrid LangGraph + Strands** (outer `StateGraph` + inner Strands `Agent` nodes — load [`references/harness-and-hybrid.md`](references/harness-and-hybrid.md)).
- **Non-listed frameworks (CrewAI, AutoGen, Semantic Kernel, plain LangChain), `claude-agent-sdk` (`CLAUDE_CODE_USE_BEDROCK=1`, `AWS_REGION`, `ANTHROPIC_MODEL` set in `os.environ` BEFORE `ClaudeAgentOptions`), Java Spring AI / TypeScript / Go / Rust BYO Containers (`POST /invocations` + `GET /ping`), or Framework vs. Model Provider questions?** → Load [`references/byo-container.md`](references/byo-container.md).

> [!IMPORTANT]
> **`agentcore.json` v0.4.0+ Schema Compliance (when inspecting older `< v0.4.0` projects):**
> (1) Top-level array key MUST be `"runtimes"` (never legacy `"agents"`); (2) strip `"type": "AgentCoreRuntime"` from runtime entries; (3) rename `"type"` to `"authorizerType"` inside `"credentials"` entries.

### Step 3: Validate name & construct `agentcore create`

**Validate `<ProjectName>` up front before presenting any command** (the CLI fails late):
- **Length `<= 23` characters** (`MyCustomerSupportBotApp` = 23 fits; `MyCustomerSupportChatBot` = 24 **fails** — state exact character count if near/over 23 and suggest a shorter name)
- **Alphanumeric only** (no hyphens, underscores, dots, or spaces) and **must start with a letter**

Present the tailored command with flag explanations and wait for operator confirmation (never auto-execute):

```bash
# Minimal defaults (Strands, Bedrock, CodeZip, memory=none)
agentcore create --name <ProjectName> --defaults

# Explicit options
agentcore create \
  --name <ProjectName> \
  --framework Strands \
  --model-provider Bedrock \
  --build CodeZip \
  --memory none
```

| Flag | Values | Default & Guidance |
|---|---|---|
| `--name` | alphanumeric, starts with letter, max **23** chars | prompted |
| `--framework` | `Strands`, `LangChain_LangGraph`, `GoogleADK`, `OpenAIAgents` | prompted |
| `--protocol` | `HTTP`, `MCP`, `A2A` | `HTTP` (for `A2A`, `A2A_PORT=9000`; never install `bedrock-agentcore[a2a]` and `bedrock-agentcore[a2a-v1]` together; for AG-UI use `serve_ag_ui` / `AGUIApp`) |
| `--build` | `CodeZip`, `Container` | `CodeZip` (packages Python + cross-compiled `uv` wheels directly into a zip; `--build Container` builds ARM64 images remotely via AWS CodeBuild — neither requires local Docker/Podman/Finch for `agentcore deploy`) |
| `--model-provider` | `Bedrock`, `Anthropic`, `OpenAI`, `Gemini` | `Bedrock` recommended (IAM auth, zero API keys to manage) |
| `--memory` | `none`, `shortTerm`, `longAndShortTerm` | Start with `none`; add later via `agents-build` ([`references/memory.md`](references/memory.md)) |
| `--network-mode` | `PUBLIC`, `VPC` | `PUBLIC` |
| `--dry-run` | — | Preview scaffold without writing files |

### Step 4: Explain generated project structure

```
<ProjectName>/
├── agentcore/
│   ├── agentcore.json      ← Project config (runtimes, gateways, memory, credentials)
│   ├── aws-targets.json    ← Target AWS account + region
│   ├── .env.local          ← Local-only dev env vars (gitignored — NEVER read by agent)
│   └── cdk/                ← Auto-managed CDK infrastructure (do not hand-edit)
└── app/<AgentName>/
    ├── main.py             ← Agent entrypoint (tools, prompts, logic)
    ├── mcp_client/         ← Example MCP client (points to public demo MCP server initially)
    └── pyproject.toml      ← Python dependencies
```

**Scaffolded `mcp_client` gotchas:** (1) Repointing `mcp_client/client.py` to `os.getenv("AGENTCORE_GATEWAY_<NAME>_URL")` before `agentcore deploy` yields `None` in local dev and silently binds zero tools — guard with `if not GATEWAY_URL: tools = []` (`agents-connect`). (2) If MCP tools aren't needed, remove `mcp_clients` from `main.py`.

### Step 5: Local development (`agentcore dev`)

```bash
agentcore dev --local    # purely local server (avoids deploying cloud backing resources)
agentcore dev            # binds HTTP=8080, MCP=8000, A2A=9000 (auto-increments 8081/8082 if busy; pin via --port <N>)
```

- **COST WARNING:** Plain `agentcore dev` synthesizes CDK and **deploys real cloud backing resources** if `agentcore.json` defines Memory/Gateway/Identity and an AWS target exists — pass `agentcore dev --local` for strictly local testing (LLM calls still incur Bedrock/provider token charges).
- **Unit tests:** Run with `OTEL_SDK_DISABLED=true pytest` so ADOT instrumentation does not hang waiting for a local collector.

### Step 6: First deploy, verification & rollback

```bash
agentcore validate                         # verify schema before CDK synth
agentcore deploy --dry-run                 # preview resources safely
agentcore deploy                           # interactive confirmation (first deploy ~3–5 min)
agentcore status                           # verify runtime status is READY
agentcore invoke "Hello, what can you do?" # smoke-test invocation

# Safe rollback / teardown (operator approval required)
agentcore remove agent --name <AgentName> && agentcore deploy
```

### Step 7: Next steps & task walkthroughs

For customer-support/chatbot prompts, load [`references/example-support-agent.md`](references/example-support-agent.md). Suggest 1–2 next skills matched to intent:
- App integration (`agentcore fetch access`), Memory (`agentcore add memory`), Multi-agent (`--protocol A2A`), or VPC (`--network-mode VPC`) → `agents-build`
- External APIs/MCP tools (`agentcore add gateway`) or Cedar tool policies (`agentcore add policy-engine`) → `agents-connect`
- Quality evaluators (`agentcore add evaluator`) or observability → `agents-optimize`
- Production security/lifecycle checklist → `agents-harden`

## Output & Quality Criteria

- Validated `agentcore create` command (`--name` `<= 23` chars, alphanumeric, valid CLI v0.9.x flags) + `@aws/agentcore >= 0.9.0` and `uv` prerequisites tailored to context
- Clear explanation of scaffolded files, local dev cost/port behavior, verification (`validate`/`status`), and rollback commands
- **Always end preflight/scaffolding plans by explicitly asking user confirmation before creating project files (`agentcore create`) or deploying (`agentcore deploy`)**
