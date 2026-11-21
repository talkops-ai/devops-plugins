---
name: agents-optimize
description: >
  Use when measuring or improving agent quality and performance — set up
  evaluators, online monitoring, CI/CD quality gates, observability, or
  cost optimization. Triggers on: "evaluate my agent", "add evaluator",
  "measure quality", "quality gate", "run evals", "agent too slow",
  "why is it slow", "reduce latency", "set up observability", "CloudWatch
  dashboard", "how much does my agent cost", "cost optimization", "logs
  not showing up", "logs missing", "spans not found", "eval failing",
  "eval error", "dev traces", "local traces", "agentcore dev traces",
  "traces to CloudWatch", "Evaluate API", "sessionSpans", "AgentCore pricing".
  Not for debugging errors or crashes — use agents-debug. Slow but
  correct routes here; broken routes to debug.
allowed-tools: Read Grep Glob Bash
metadata:
  type: skill
  version: "1.0.0"
  author: aws-agentcore
  requires-cli: ">=0.9.0"
---

# optimize

Measure and improve your AgentCore agent's quality through evaluation, monitoring, and observability.

## When to use

- You want to know if your agent is giving good answers
- You want to set up continuous quality monitoring in production
- You want to add a quality gate to your CI/CD pipeline
- You want to understand agent behavior through logs, metrics, and traces
- You want to set up CloudWatch dashboards or X-Ray tracing

Do NOT use for:

- Debugging a specific broken agent (wrong answers, errors) → use `agents-debug`
- Production security hardening (IAM, auth) → use `agents-harden`

## MCP-Only Execution & Read-Only Safety

- **MCP-Only Live Discovery & Docs:** Execute **all** live AWS discovery, AgentCore runtime/gateway/memory/evaluator inspection, telemetry/log/trace queries, pricing checks, IAM reviews, and documentation lookups **exclusively via connected MCP tools**: `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`, `aws___search_documentation`, `aws___read_documentation`), `agentcore` (`search_agentcore_docs`, `fetch_agentcore_doc`, `list_agent_runtimes`, `get_agent_runtime`, etc.), `strands-agents` (`search_docs`, `fetch_doc`, `find_integrations`), `cloudwatch`, `appsignals`, `cloudtrail`, `awspricing`, `awsiac`, and `awsknowledge`.
- **Zero Raw CLI Execution, Strictly Read-Only & Secret-Safe:** **Never** run raw `aws ...` or `agentcore ...` CLI commands in Bash/`run_command` to query or mutate live AWS accounts (present CLI commands in Markdown strictly as operator reference snippets). **Never** invoke live mutations (`create_*`, `update_*`, `delete_*`, `InvokeAgentRuntime`, `InvokeModel`) — refuse unapproved destructive/mutating requests and explain the safe, approval-gated operator workflow with verification and rollback steps. **Never** read or print plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter` with `WithDecryption=True`, `.env` / `.env.local` values, or raw memory record contents).
- **Edge-Case Documentation Fallback:** For unmapped AWS/AgentCore/Bedrock observability, evaluator, or pricing edge cases, run 1–2 focused queries via `agentcore`, `strands-agents`, `awsknowledge`, or `aws-mcp` documentation search tools.

## Input

`$ARGUMENTS` can be:

- An eval goal: "add a quality gate", "set up monitoring"
- An observability goal: "set up CloudWatch dashboard", "understand my traces"
- A specific evaluator: "llm-as-a-judge", "code-based"
- Empty — the skill will guide based on project context

## Process

### Step 0: Verify CLI version prerequisite

AgentCore CLI `>= 0.9.0` is required (operators can check locally via `agentcore --version` and upgrade via `agentcore update`).

### Step 1: Read project context

Read `agentcore/agentcore.json` to understand existing evaluators, online eval configs, and agent setup (never read `.env` or `agentcore/.env.local`).

If `agentcore/agentcore.json` is not found:
> "This skill requires an AgentCore project. Use `agents-get-started` to create one."

### Step 2: Determine the workflow

| Developer intent | Action |
|---|---|
| Measure quality, add evaluator, Two-Tier CI/CD evaluation gating (`Builtin.TrajectoryExactOrderMatch` + LLM-as-a-Judge suite), batch evaluation (`StartBatchEvaluation`), online monitoring | Load [`references/evals.md`](references/evals.md) and follow its workflow |
| Set up observability, CloudWatch, X-Ray, logs, metrics, dashboards, third-party OTLP export (Langfuse, MLflow, Elastic, Dynatrace) | Load [`references/observability.md`](references/observability.md) and follow its workflow |
| Understand or reduce AgentCore costs, elastic memory reclamation vs. committed baseline pricing, MCP context pruning (`AGENTCORE_DISABLE_TOOLS`) | Load [`references/cost.md`](references/cost.md) |
| Both — "I want to understand and improve my agent" | Start with observability setup, then add evals |

### Step 3: Follow the loaded reference

The reference file contains the full procedure. Follow it step by step.

### Cross-references

- After setting up evals, suggest `agents-harden` for production readiness
- If eval results reveal agent issues, suggest `agents-debug` for root cause analysis
- If the developer needs to add capabilities first, suggest `agents-build`

## Output

Depends on the workflow — see the loaded reference for specific outputs.

## Quality criteria

- Evaluator configuration uses only valid CLI flags (when discussing custom `--rating-scale` definitions, contrast against all 4 built-in CLI presets: `1-5-quality`, `1-3-simple`, `pass-fail`, and `good-neutral-bad`)
- Local vs. deployed eval boundary is explicit: works **without deploying** (`agentcore dev` local spans -> `agentcore run eval`, `OTEL_SDK_DISABLED=true pytest` for `@custom_code_based_evaluator`, `evaluate(sessionSpans=...)`) vs. **requires deploying** (`StartBatchEvaluation` / `agentcore run batch-evaluation`, `OnDemandEvaluationDatasetRunner`, and `online-eval`)
- Online eval sampling rate is appropriate (not 100% in production without discussion)
- CI/CD quality gate has a clear pass/fail threshold
- Observability setup includes both tracing and logging
- The developer understands the eval data delay: **~10 seconds put-to-get, end-to-end** — one ingestion step covers both trace reads and eval queries; there is no separate indexing wait
