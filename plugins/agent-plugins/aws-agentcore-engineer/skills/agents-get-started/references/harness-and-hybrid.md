# AgentCore Harness, v0.4.0+ Schema Migration & Hybrid LangGraph + Strands Architecture

## 1. Execution Model Decision Matrix

Choose the right execution and orchestration model before scaffolding or refactoring an agent:

| Execution Model | Best For | Key Mechanism |
| :--- | :--- | :--- |
| **AgentCore Harness** | Single-agent assistant, standard MCP tool-calling, rapid declarative setup with zero Python boilerplate. | Declarative configuration in `agentcore.json`. Eject to full source code anytime via `agentcore export harness`. |
| **AgentCore Runtime (Strands Native)** | Custom Python tools, streaming callbacks, multi-agent Handoffs/Swarms, or voice (`BidiAgent`). | `BedrockAgentCoreApp` (`@app.entrypoint`), `A2AServer` (`serve_a2a`), or `AGUIApp` (`serve_ag_ui`). |
| **Hybrid LangGraph + Strands** | Complex cyclic state graphs, strict deterministic routing, human-in-the-loop (`interrupt_before`), or compliance gates. | Outer **LangGraph `StateGraph`** (state schema + `checkpointer`) with inner **Strands `Agent`** specialist nodes. |
| **Bedrock Agent Classic** | **Legacy migration source only.** Do not use for new builds. | Migrate to AgentCore Runtime + Gateway (see [migrate.md](migrate.md)). |

---

## 2. Declarative AgentCore Harness & Code Ejection (`agentcore export harness`)

When starting with **AgentCore Harness**, the agent's model, system prompt, memory, and Gateway MCP tools are declared directly in `agentcore.json` without custom Python orchestration code.

When the team outgrows declarative configuration (e.g., needing custom pre/post-processing, Hybrid LangGraph state machines, or custom middleware), eject the harness into a full AgentCore Runtime Python codebase:

```bash
agentcore export harness
```

### What `agentcore export harness` Produces
- Generates a standalone `app/` directory containing the Python entrypoint (`main.py`), `Dockerfile`, and `pyproject.toml` / `requirements.txt`.
- Writes `EXPORT_NOTES.md` documenting the exact mapping from declarative harness settings to SDK primitives (`BedrockAgentCoreApp`, `MemorySessionManager`, `MCPClient`).
- Updates `agentcore.json` to point the runtime entry to the exported `app/` code directory.

---

## 3. Mandatory `agentcore.json` Schema Migration (`< v0.4.0` to `>= v0.4.0`)

The `@aws/agentcore` CLI (v0.4.0+) enforces a strict JSON schema. Legacy configurations will fail validation or deployment unless migrated with these three rules:

1. **Top-Level `"agents"` -> `"runtimes"`:** Rename the top-level `"agents"` array to `"runtimes"`.
2. **Strip `"type": "AgentCoreRuntime"`:** Remove `"type": "AgentCoreRuntime"` from every object inside `"runtimes"`.
3. **Credential `"type"` -> `"authorizerType"`:** Inside `"credentials"` objects, rename `"type"` to `"authorizerType"` (e.g., `"OAuthCredentialProvider"` or `"ApiKeyCredentialProvider"`).
4. **Strict Identifier Regex:** All resource `name` fields MUST match `^[A-Za-z][A-Za-z0-9_]*$` (letters, digits, underscores only—**no hyphens**).

### Before (`< v0.4.0` — Invalid) vs. After (`>= v0.4.0` — Valid)

```json
// ❌ LEGACY (< v0.4.0) — FAILS SCHEMA VALIDATION
{
  "version": 1,
  "agents": [
    {
      "type": "AgentCoreRuntime",
      "name": "my-Production-Agent",
      "entrypoint": "main.py:app"
    }
  ],
  "credentials": [
    {
      "name": "github-cred",
      "type": "OAuthCredentialProvider"
    }
  ]
}
```

```json
// ✅ MODERN (>= v0.4.0) — COMPLIANT
{
  "version": 1,
  "runtimes": [
    {
      "name": "My_Production_Agent",
      "entrypoint": "main.py:app",
      "networkMode": "PUBLIC",
      "protocol": "HTTP"
    }
  ],
  "credentials": [
    {
      "name": "Github_Cred",
      "authorizerType": "OAuthCredentialProvider"
    }
  ]
}
```

---

## 4. Hybrid LangGraph + Strands Architecture Pattern

For enterprise workflows requiring deterministic cyclic routing, human-in-the-loop checkpoints (`interrupt_before`), and AWS-native Bedrock Converse streaming:
- Use **LangGraph (`StateGraph`)** as the outer state machine managing typed state transitions and checkpointing.
- Instantiate **Strands `Agent`** instances as module-level singletons and invoke them **inside** specialist LangGraph nodes.

```python
import os
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp, RequestContext

app = BedrockAgentCoreApp()

# 1. Warm-Pool Module-Level Singletons (reused across 15-min microVM lifecycle)
bedrock_model = BedrockModel(
    model_id=os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    temperature=0.1,
)

analyst_strands_agent = Agent(
    model=bedrock_model,
    system_prompt=(
        "You are a specialist financial analyst node. "
        "Analyze the provided telemetry and return a concise risk assessment."
    ),
)


# 2. Deterministic LangGraph State Schema
class WorkflowState(TypedDict):
    query: str
    session_id: str
    analysis: str
    risk_score: float
    approved: bool
    audit_trail: Annotated[list[str], operator.add]


def specialist_analyst_node(state: WorkflowState) -> dict:
    """Executes a Strands Agent inside a deterministic LangGraph node."""
    result = analyst_strands_agent(state["query"])
    text = str(result)
    score = 0.85 if "CRITICAL" in text.upper() else 0.20
    return {
        "analysis": text,
        "risk_score": score,
        "audit_trail": [f"specialist_analyst_node: score={score}"],
    }


def compliance_gate_node(state: WorkflowState) -> dict:
    """Deterministic policy gate before external action execution."""
    approved = state["risk_score"] < 0.70
    return {
        "approved": approved,
        "audit_trail": [f"compliance_gate_node: approved={approved}"],
    }


def route_after_compliance(state: WorkflowState) -> str:
    return "execute_action" if state["approved"] else "escalate_human"


def execute_action_node(state: WorkflowState) -> dict:
    return {"audit_trail": ["execute_action_node: completed"]}


def escalate_human_node(state: WorkflowState) -> dict:
    return {"audit_trail": ["escalate_human_node: queued for human approval"]}


# 3. Compile Graph Once at Module Scope
builder = StateGraph(WorkflowState)
builder.add_node("analyst", specialist_analyst_node)
builder.add_node("compliance_gate", compliance_gate_node)
builder.add_node("execute_action", execute_action_node)
builder.add_node("escalate_human", escalate_human_node)

builder.set_entry_point("analyst")
builder.add_edge("analyst", "compliance_gate")
builder.add_conditional_edges(
    "compliance_gate",
    route_after_compliance,
    {"execute_action": "execute_action", "escalate_human": "escalate_human"},
)
builder.add_edge("execute_action", END)
builder.add_edge("escalate_human", END)

checkpointer = MemorySaver()
compiled_graph = builder.compile(checkpointer=checkpointer)


@app.entrypoint
async def invoke(payload: dict, context: RequestContext):
    session_id = getattr(context, "session_id", None) or payload.get("sessionId", "default-session")
    config = {"configurable": {"thread_id": session_id}}
    final_state = await compiled_graph.ainvoke(
        {
            "query": payload.get("prompt", ""),
            "session_id": session_id,
            "analysis": "",
            "risk_score": 0.0,
            "approved": False,
            "audit_trail": [],
        },
        config=config,
    )
    return {
        "analysis": final_state["analysis"],
        "approved": final_state["approved"],
        "audit_trail": final_state["audit_trail"],
    }


if __name__ == "__main__":
    app.run()
```

---

## 5. Protocol & SDK Runtime Guardrails

### AG-UI Protocol (`serve_ag_ui` / `AGUIApp`)
For interactive frontend applications using the Agent-User Interaction (AG-UI) protocol:
- Wrap your entrypoint with `AGUIApp` / `serve_ag_ui` from `bedrock-agentcore` to stream structured state deltas, tool call progress, and UI events over SSE/HTTP.

### A2A Protocol Package Mutual Exclusivity
- **Port Contract:** A2A servers run on port `9000` (`A2A_PORT=9000`), whereas standard HTTP runtimes use `8080` and MCP servers use `8000`.
- **Mutual Exclusivity:** Never install `bedrock-agentcore[a2a]` (`a2a-sdk < 1.0`) and `bedrock-agentcore[a2a-v1]` (`a2a-sdk >= 1.0`) in the same environment—they share the `a2a` Python import namespace and will cause runtime `ImportError` / schema collisions.

### Anthropic Claude Agent SDK (`claude-agent-sdk`) Ordering
When building an AgentCore Runtime with `claude-agent-sdk`, environment variables **must** be populated in `os.environ` **before** `ClaudeAgentOptions` is instantiated:

```python
import os

# MUST execute BEFORE constructing ClaudeAgentOptions
os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("ANTHROPIC_MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0")

from claude_agent_sdk import ClaudeAgentOptions, query
```

### Unit Testing with OpenTelemetry Disabled
Because `bedrock-agentcore` bundles ADOT auto-instrumentation (`aws-opentelemetry-distro`), local unit tests will attempt to export spans and hang/warn unless the OTel SDK is disabled during test runs:

```bash
OTEL_SDK_DISABLED=true pytest
```
