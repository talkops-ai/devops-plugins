---
name: start-building-for-startups
description: "Interactive discovery + implementation workflow that scans the codebase first, gathers missing requirements via one structured picker question per turn (intent, scope, constraints, preferences), and scaffolds/writes AWS architecture and code directly into the project. Includes vibe-coded stack graduation (Lovable, Bolt.new, Replit, v0). Not for Activate FAQ lookups, single copy-paste prompts, architecture advice without code changes (architect-for-startups), AI agent runtime scoring (agent-advisor), or cloud/LLM migrations. Query live AWS state via MCP tools only (never raw aws CLI)."
---

# Start Building for Startups — Interactive Discovery & AWS Implementation

Two-phase Solutions Architect workflow: **Phase 1 (Discovery)** scans the codebase first and gathers missing human context via **one structured picker question per turn**, followed by **Phase 2 (Implementation)** writing AWS architecture and application code directly after explicit opt-in.

Full conversation rules, question-quality rubric, `'Start implementation'` gating, and inline contextual-offer formatting live in [`references/discovery-and-offers-protocol.md`](./references/discovery-and-offers-protocol.md) and [`references/vibe-coded-stacks.md`](./references/vibe-coded-stacks.md).

## Mandatory Guardrails & Phase Gates

1. **Codebase Scan First (Primary Source of Truth):**
   - When a codebase exists, scan project structure and non-secret config files (`package.json`, `pyproject.toml`, `Dockerfile`, IaC files, `README.md` — **never read `.env`, `.env.*`, `*.pem`, `*.key`, or `.tfstate`**) BEFORE asking any question.
   - **Never ask about facts already present in the codebase** (language, framework, DB, auth library, IaC tool, conventions). State partial findings and ask only to confirm/clarify.
   - **Vibe-Coded Stack Detection:** If the repo shows **Lovable** (`lovable-tagger` / `supabase/`), **Bolt.new** (`.bolt/`), **Replit** (`.replit` / `replit.nix`), or **v0** exports, load [`references/vibe-coded-stacks.md`](./references/vibe-coded-stacks.md) to guide low-friction graduation onto Free-Tier / Activate-eligible AWS primitives with `git push` CI/CD.
   - Summarize findings in `<= 7` sentences (or invite free-form description on greenfield projects), then transition into structured picker questions.
2. **Discovery Phase Mandate (1 Structured Picker Question per Turn):**
   - **Never enter Implementation before at least one discovery question has been answered**, even if the user asks for immediate code — ask one highest-impact foundational picker question first.
   - Produce **exactly one structured picker question per turn**, **always rendered directly in your Markdown response** as a bold question followed by numbered selectable options (`1.`, `2.`, `3.`, ...). **Do NOT rely solely on interactive host picker tools (`ask_question`) that omit options from Markdown output or block in headless CLI sessions** — always write the full question and numbered options in your Markdown reply!
   - **Strict `< 15`-Word Option Ceiling (Target `5–10` Words per Option):** Every single option label MUST be **strictly under 15 words** (aim for `5–10` words in natural phrasing, e.g., `1. Hybrid: S3/CloudFront + Bedrock now, keep Supabase`). Put architectural nuance in your short summary *above* the picker — **never** stuff multi-clause explanations into option labels! Never output plain-prose questions, never repeat covered topics, and move on if the user says *"I don't know"*.
   - **Breadth before depth** across 4 ordered topic areas: (1) *Coding intent* -> (2) *Scope & maturity* -> (3) *Requirements & constraints* -> (4) *Preferences & style*.
   - **Greetings & Clarifications:** On greetings/vague replies (`"hi"`, `"sure"`), skip pleasantries and immediately output the next highest-impact Markdown picker question (`<= 10`-word options). On clarifying questions (`"What is Terraform?"`), give a 1–2 sentence plain-English explanation and **immediately re-present the full Markdown picker question and numbered `< 15`-word options right below it**.
   - **`'Start implementation'` Option Gate:** Include `'Start implementation'` as the final numbered option **only** when (a) a clear goal is stated, (b) at least one follow-up question was answered, and (c) enough context exists (include by round 3–4; omit on turn 1 or when the user's message already says *"let's build it"* / *"start coding"*).
   - **Phase 2 Implementation Deliverable & Walkthrough:** Once the user opts into implementation, write clean application + IaC files, run local tests and policy validators (`pytest`, `terraform fmt`/`validate`, `validate-terraform-policy.py`), and **always conclude your response with an explicit `## End-to-End Setup-to-Verification Walkthrough` section** covering: (1) Prerequisites & AWS credentials, (2) Secret/config initialization (without hardcoding secrets), (3) Exact `terraform init` / `plan` / `apply` deployment commands, (4) A concrete live smoke test (`curl` / signed webhook payload) with expected HTTP status, and (5) Post-deploy verification in CloudWatch Logs, metrics/alarms, and storage/DynamoDB.
3. **AWS Architecture Defaults & MCP-Only Live Verification:**
   - Query live AWS identity, regional service availability, and pricing strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `aws___get_regional_availability`, `aws-pricing`, `awsknowledge`) — **never execute raw `aws` CLI commands in shell (`run_command`)**.
   - **Early-Stage Defaults:** Recommend AWS Budgets + billing alerts early; prefer serverless/managed services (Lambda, Fargate) over self-managed infra; **do not recommend Kubernetes/EKS unless already in the codebase**; design for **10x** current scale (not 1000x); prefer **VPC Gateway Endpoints over NAT Gateways** for S3/DynamoDB; prefer **Terraform** by default (or respect user's CDK/SAM choice and run [`../tf-best-practices/SKILL.md`](../tf-best-practices/SKILL.md) posture checks); match Bedrock model tiers adaptively (Haiku vs Sonnet/Opus) and AgentCore for multi-step workflows; include compliance/PII guidance for regulated workloads and Security Hub / Inspector when heading to production.
4. **Companion Skill Routing:**
   - Factual Activate FAQ / credits / programs / learn articles → `knowledge-base-for-startups`
   - Single copy-paste starter prompt / downloadable agent → `prompt-library-for-startups`
   - Architecture advice without code changes → `architect-for-startups`
   - AI agent runtime scoring / POC → `agent-advisor`
   - Cloud/LLM migrations → `gcp-to-aws`, `azure-to-aws`, `heroku-to-aws`, `llm-to-bedrock`
   - Live production outage / 5xx / DevOps Agent → `operate-on-aws`
5. **Contextual Offers (Mandatory Final Step on Finalized Recommendations):**
   - After any finalized recommendation/scaffold (never influencing merit-first choices), check [`../knowledge-base-for-startups/references/offers.md`](../knowledge-base-for-startups/references/offers.md) per [`references/discovery-and-offers-protocol.md`](./references/discovery-and-offers-protocol.md): if one offer clears the bar (named-product, direct intent/component, or stage-appropriate transparent-alternative under an AWS-native pick, never competing with an existing tool the founder is keeping), read only `../knowledge-base-for-startups/references/offers/<slug>.md` and append **at most one** single italic line with `<source_url>?source=ide-startupAdvisor-<host>`.
