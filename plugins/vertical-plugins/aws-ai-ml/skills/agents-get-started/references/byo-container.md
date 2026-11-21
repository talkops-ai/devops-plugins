# Non-Scaffolded Frameworks, BYO Container & Model Provider Matrix

Load this reference in `agents-get-started` when a developer asks about frameworks or languages outside the four CLI-scaffolded Python templates (`Strands`, `LangChain_LangGraph`, `GoogleADK`, `OpenAIAgents`), or confuses frameworks with model providers / IDE tools.

---

## 1. Frameworks & Tools Outside the CLI Scaffold Table

| Developer asks about | Guidance |
|---|---|
| **CrewAI, AutoGen, Semantic Kernel** | Not scaffolded directly by `agentcore create`, but fully supported via the **BYO Container** path below. AgentCore Runtime is framework-agnostic — any container implementing `POST /invocations` and `GET /ping` works. |
| **Anthropic SDK / Claude Agent SDK (`claude-agent-sdk`)** | Model/agent SDK usable standalone or inside Strands/LangGraph. **Critical ordering rule:** When using `claude-agent-sdk` with Bedrock, always set `CLAUDE_CODE_USE_BEDROCK=1`, `AWS_REGION`, and `ANTHROPIC_MODEL` in `os.environ` **before** constructing `ClaudeAgentOptions`. |
| **Claude Code / Cursor / GitHub Copilot** | IDE/coding harnesses where developers *write* code, not runtime agent frameworks deployed to AgentCore. Select a runtime framework (`Strands`, `LangChain_LangGraph`, etc.) for the deployed agent. |
| **LangChain (without LangGraph)** | `LangChain` is the component library; `LangGraph` (`LangChain_LangGraph`) is the scaffolded orchestration framework. Plain LangChain chains can run via BYO Container. |
| **Custom / homegrown framework** | Use the BYO Container path below. |

---

## 2. BYO Container Path (Any Framework, Any Language)

AgentCore Runtime hosts any container implementing the HTTP contract (`POST /invocations` on port `8080`, `GET /ping` health check). Present these commands for the operator to run locally:

1. `agentcore create --name <ProjectName> --defaults` — scaffolds workspace metadata and CDK directory (`<ProjectName>` must be alphanumeric, start with a letter, `<= 23` chars).
2. `agentcore add agent --type byo --build Container --language <Language> --code-location <path>` — registers the custom container agent in `agentcore/agentcore.json`.
3. Add a `Dockerfile` implementing `CMD ["opentelemetry-instrument", ...]` (for Python OTEL log/span export) and listening on the Runtime HTTP contract.
4. `agentcore validate` and `agentcore deploy` — builds/pushes to ECR and provisions Runtime via CDK.

### Language-Specific Notes

| Language | Recommended Path |
|---|---|
| **Java (Spring Boot)** | [Spring AI SDK for AgentCore](https://aws.amazon.com/blogs/machine-learning/spring-ai-sdk-for-amazon-bedrock-agentcore-is-now-generally-available) — implements Runtime contract, SSE streaming, and `/ping` health checks out of the box. Register with `--language Other --build Container`. |
| **JavaScript / TypeScript** | Implement `POST /invocations` and `GET /ping` in Express/Fastify/Hono. Register with `--language TypeScript --build Container`. |
| **Go, Rust, .NET, other** | Implement the Runtime HTTP contract (`POST /invocations`, `GET /ping`). Register with `--language Other --build Container`. |

---

## 3. Framework vs. Model Provider

The **orchestration framework** (how your agent plans, loops, and calls tools) is independent of the **model provider** (which LLM endpoint generates completions):

- **Strands + Bedrock (default):** Fully AWS-native IAM auth, zero external API keys.
- **Strands + Anthropic:** Strands orchestration calling direct Anthropic API (register key via `agentcore add credential`, never runtime env vars).
- **LangGraph + Bedrock:** LangGraph `StateGraph` orchestration backed by Amazon Bedrock models.
- **OpenAI Agents + OpenAI:** OpenAI Agents SDK backed by OpenAI models.

When a developer says *"I want to use Claude"*, clarify that Claude is the model (available natively on **Bedrock** without API keys, or via direct Anthropic API), then help them choose an orchestration framework.
