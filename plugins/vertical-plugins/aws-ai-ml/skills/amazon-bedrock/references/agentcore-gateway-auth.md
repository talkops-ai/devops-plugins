# Amazon Bedrock, AgentCore Runtime, RAG Knowledge Bases & Strands Multi-Agent Reference

## 1. Generative AI Runtime & Agent Architecture Selection Matrix

| Use Case | Recommended AWS Architecture | Key Design Controls |
|---|---|---|
| **Stateless Foundation Model Inference / Structured Output / Tool Use** | **Amazon Bedrock `Converse` / `ConverseStream` API** + **Prompt Caching** + **Cross-Region Inference Profiles (`us.*` / `global.*`)** | Always use Cross-Region Inference (CRIS) profiles for higher throughput bursts and resilience; enable Prompt Caching on static system prompts/schemas to cut input token cost by up to 90%. |
| **Stateful Production AI Agents (Long-running tool loops, MCP tools, OBO Auth, Memory)** | **Amazon Bedrock AgentCore** (AgentCore Runtime + AgentCore Gateway + STM/LTM Memory + Cedar Policy Engine) + **Strands Agents SDK / LangGraph** | Use AgentCore Gateway with Two-Step OBO (On-Behalf-Of) user token exchange and Cedar policies to enforce deterministic authorization before any MCP tool executes. |
| **Enterprise Grounded RAG (Document Q&A, Citations, Multi-Tenant Isolation)** | **Amazon Bedrock Knowledge Bases** backed by **S3 Vectors** (cost-optimized), **Aurora PostgreSQL (`pgvector`)**, or **OpenSearch Serverless** | Inject mandatory tenant metadata filters (`equals: { key: "tenant_id", value: $jwt_tenant }`) in the application retrieval layer — never rely on prompt instructions for tenant isolation. |
| **High-Volume Batch Summarization / Classification (Non-Interactive)** | **Amazon Bedrock Batch Inference** | Delivers **50% lower token pricing** compared to On-Demand inference and bypasses real-time RPM/TPM quotas. |

## 2. Bedrock Guardrails & Safety Architecture
Every customer-facing Bedrock architecture must attach an `AWS::Bedrock::Guardrail` enforcing:
1. **Prompt Attack Filter (`HIGH`)** against indirect prompt injection in retrieved RAG chunks or tool outputs.
2. **PII Redaction / Masking** (`ANONYMIZE` or `BLOCK` for SSN, Credit Card, AWS Access Keys).
3. **Contextual Grounding Check** (hallucination detection threshold `>= 0.75` for RAG responses).
