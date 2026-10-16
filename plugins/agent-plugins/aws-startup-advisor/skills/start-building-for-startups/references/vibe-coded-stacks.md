# Migrating Vibe-Coded Prototypes (`Lovable`, `Bolt.new`, `Replit`, `v0`) to Production AWS

Non-technical and product-focused startup founders frequently prototype MVPs in AI app builders (**Lovable**, **Bolt.new**, **Replit**, **v0**) and then need to graduate onto AWS to unlock **AWS Activate credits**, pass enterprise security questionnaires (SOC 2 / HIPAA), or eliminate per-seat / platform hosting limits.

Load this reference during `start-building-for-startups` whenever codebase inspection detects a vibe-coded export or when the user mentions **Lovable**, **Bolt**, **Bolt.new**, **Replit**, or **v0**.

---

## 1. Codebase Fingerprinting (Detect Automatically — Never Ask)

Inspect the repository root and `package.json` before asking any discovery questions:

| Origin Platform | File & Dependency Signatures | Typical Generated Stack |
|---|---|---|
| **Lovable (`lovable.dev`)** | `lovable-tagger` in `devDependencies`, `vite.config.ts` importing `componentTagger`, `supabase/functions/`, `supabase/config.toml`, `@supabase/supabase-js`, `@tanstack/react-query`, `shadcn/ui` (`components.json`) | Vite + React + TypeScript SPA + Supabase (Auth, Postgres, Edge Functions, Storage) |
| **Bolt.new (`stackblitz`)** | `.bolt/` directory (`.bolt/config.json`, `.bolt/prompt`), `vite.config.ts`, `@supabase/supabase-js` or local SQLite/Prisma | Vite + React/Next.js + Tailwind + Supabase or Node/Express backend |
| **Replit** | `.replit`, `replit.nix`, `.upm/`, `@replit/vite-plugin-*`, `server/index.ts` + `client/` monorepo, `drizzle.config.ts` with `@neondatabase/serverless` or `pg` | Express + Vite full-stack monorepo on single Node process + Postgres (`DATABASE_URL`) + Replit Auth / Passport.js |
| **v0 (`v0.dev`)** | Next.js App Router (`app/`), `components.json` (shadcn), `@ai-sdk/openai` or `@ai-sdk/anthropic`, Vercel Blob/KV imports | Next.js 14/15 App Router + Server Actions + Vercel AI SDK |

---

## 2. Stage-Calibrated Target AWS Architecture Matrix

Never over-engineer a vibe-coded MVP into EKS or multi-AZ Aurora. Map each prototype layer to the lowest-ops, Free-Tier-eligible AWS primitive that preserves the founder's developer experience:

| Prototype Layer | Source in Lovable / Bolt / Replit | Pre-Revenue / MVP Target ($0–$25/mo) | Seed / Early Production Target ($30–$150/mo) |
|---|---|---|---|
| **Static SPA Frontend** (`Vite + React`) | Lovable / Bolt static build (`dist/`) | **S3 + CloudFront (OAC)** or **AWS Amplify Hosting** (Free Tier: 1 TB transfer/mo, automatic HTTPS) | **S3 + CloudFront + AWS WAF** with GitHub Actions CI/CD |
| **Full-Stack SSR / Node Server** (`Express` / `Next.js`) | Replit Express+Vite server or Next.js App Router | **AWS Lambda + Lambda Web Adapter** (Function URL / API Gateway HTTP API — $0 idle cost) or **AWS Amplify Hosting** | **ECS Express Mode / Fargate** (`0.25 vCPU / 0.5 GB` Graviton `arm64`, ~$9/mo) |
| **Authentication** | Supabase Auth (`supabase.auth.*`) or Replit Auth | **Amazon Cognito UserPool** (Essentials/Lite tier: first 10,000 MAUs **FREE**) | **Amazon Cognito** with Managed Login + Google/Apple OIDC & Passkeys |
| **Database** | Supabase Postgres / Neon / Replit Postgres (`drizzle` / `prisma`) | **Keep Supabase Free Tier temporarily** OR **RDS PostgreSQL `db.t4g.micro` Single-AZ** (Free Tier: 750 hrs/mo for 12 months, then ~$12/mo) or **DynamoDB On-Demand** | **RDS PostgreSQL `db.t4g.small` / `Aurora Serverless v2`** (with RDS Proxy if Lambda-backed) |
| **Serverless Functions** | `supabase/functions/*` (Deno) or Express routes | **AWS Lambda** (Node.js 22 / TypeScript via `esbuild`, 1M requests/mo **FREE**) | **AWS Lambda + API Gateway HTTP API** |
| **File / Object Storage** | Supabase Storage (`supabase.storage.from(...)`) | **Amazon S3 + Presigned URLs** (5 GB Free Tier) | **Amazon S3 + CloudFront Signed URLs** |
| **AI / LLM Calls** | `openai`, `@anthropic-ai/sdk`, `OPENROUTER_API_KEY`, `@ai-sdk/*` | **Amazon Bedrock (`us.anthropic.claude-sonnet-5` / `haiku-4-5`)** — 100% covered by AWS Activate credits | **Amazon Bedrock + Bedrock Guardrails + Prompt Caching** (delegate SDK rewrite to `ai-to-bedrock`) |

> **Important Note on Supabase Co-Existence**: If a Pre-Revenue founder only wants to move their frontend/backend or AI spend to AWS first while keeping Supabase Auth/DB during MVP validation, support that hybrid path cleanly — do not force a mandatory database rewrite if their immediate goal is just deploying the app or moving OpenAI calls onto Bedrock Activate credits.

---

## 3. The 5-Step Guided Vibe-to-AWS Migration Flow

When the user selects **"Start implementation"** after discovery, execute these 5 concrete steps in order:

### Step 1: Strip Platform Lock-In Shims
- **Lovable**: Remove `lovable-tagger` from `package.json` and `componentTagger()` from `vite.config.ts` so standard CI builds succeed outside Lovable's sandbox.
- **Replit**: Remove `@replit/vite-plugin-cartographer` and `@replit/vite-plugin-runtime-error-modal` from `vite.config.ts`, and ensure `server/index.ts` reads `process.env.PORT || 8080` and binds to `0.0.0.0`.
- **Environment Variables**: Create a clean `.env.example` documenting all required `VITE_*` / backend variables. Never read or commit `.env` (protected by `secret-safety.py`).

### Step 2: Adapt Auth, Storage & Data Clients (When Requested)
- **Supabase → Cognito + API**: Replace `supabase.auth.signInWithPassword` / `useSession` with `aws-amplify/auth` (~15 lines) backed by a Cognito User Pool, or keep Drizzle/Prisma pointing at the new RDS PostgreSQL connection string stored in AWS Secrets Manager (injected via `${CLAUDE_PLUGIN_ROOT}/scripts/asm-exec`).
- **Supabase Storage → S3 Presigned URLs**: Replace `supabase.storage.from(bucket).upload(...)` with a lightweight Lambda endpoint issuing `@aws-sdk/s3-request-presigner` `PutObjectCommand` / `GetObjectCommand` URLs.
- **AI SDKs → Amazon Bedrock**: If the prototype uses `@ai-sdk/openai`, `openai`, or `OpenRouter`, invoke `ai-to-bedrock` to switch to `@ai-sdk/amazon-bedrock` or Bedrock `Converse` so token costs burn Activate credits instead of founder cash.

### Step 3: Package Backend Runtime
- **For Express / Fastify / Next.js on Lambda (Zero Idle Cost)**: Add a `Dockerfile` using the official **AWS Lambda Web Adapter** (`public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4`) so the existing Express or Next.js server runs unmodified on AWS Lambda with $0 idle cost.
- **For Always-On WebSockets / Background Workers**: Generate a multi-stage `linux/arm64` Graviton `Dockerfile` targeting **ECS Express Mode / Fargate**.

### Step 4: Generate Stage-Calibrated IaC (Terraform or CDK)
- Generate a clean `infra/` directory (Terraform by default per `tf-best-practices`, or AWS CDK TypeScript if the founder prefers staying in 100% TypeScript).
- Include an **AWS Budget** (`aws_budgets_budget`) set to the founder's monthly threshold (default `$25/mo` for MVP) with email alerts at 50%, 80%, and 100%.
- Use **VPC Gateway Endpoints** for S3/DynamoDB (free) and avoid NAT Gateways ($32.85/mo) at Pre-Revenue/Seed.

### Step 5: Generate "Git Push" CI/CD (`.github/workflows/deploy.yml`)
- Vibe-coders are used to "click Publish". Preserve that experience by generating `.github/workflows/deploy.yml` using **GitHub Actions OIDC** (`aws-actions/configure-aws-credentials@v4` with an IAM OIDC role — zero long-lived AWS access keys stored in GitHub) so every `git push origin main` automatically builds, deploys, and invalidates CloudFront.
