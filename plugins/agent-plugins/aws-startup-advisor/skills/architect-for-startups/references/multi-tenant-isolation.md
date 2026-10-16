# Multi-Tenant SaaS Isolation Patterns for Startups

B2B SaaS founders frequently face a tension between **Seed-stage cost efficiency** (one shared database) and **Enterprise customer security questionnaires** ("How do you guarantee Tenant A can never read Tenant B's data or noisy-neighbor their performance?").

Load this reference whenever a B2B SaaS startup asks about multi-tenancy, tenant isolation, Row-Level Security (RLS), noisy neighbors, or enterprise "single-tenant / BYOC" requests.

---

## 1. Stage-Calibrated Multi-Tenancy Model Selection

| Model | How It Works | Monthly Floor | When to Use | When NOT to Use |
|---|---|---|---|---|
| **1. Pooled Model + Logical Isolation (Default for Pre-Revenue → Series A)** | All tenants share compute and database; isolation enforced at the data layer via **PostgreSQL Row-Level Security (RLS)** or **DynamoDB `tenant_id` Partition Key + IAM ABAC** | **$15–$100/mo** (1 database for 1,000 tenants) | Pre-Revenue, Seed, and Series A SaaS startups | Regulated enterprise deals that contractually mandate physical DB separation |
| **2. Bridge Model (Shared Compute + Per-Tenant Schema / DB / S3 Prefix for Enterprise Tier)** | Standard tier uses the Pooled DB; high-ACV Enterprise tenants (`>$50K/yr` ARR) get a dedicated RDS schema/instance or dedicated KMS key (`aws:kms` per tenant) | **$15–$50/mo** per Enterprise silo | Series A+ startups closing their first Fortune 500 / healthcare / finserv contracts | Never give free or `$49/mo` self-serve users a dedicated RDS instance |
| **3. Full Silo / Per-Tenant AWS Account (Series B+ Only)** | Dedicated VPC/ECS/RDS or AWS Organizations member account per enterprise customer | **$200–$1,000+/mo** per tenant | Series B+ with `>$100K/yr` ACV and a dedicated platform engineering team | **Fatal anti-pattern at Seed** — managing 20 Terraform states and 20 RDS instances kills velocity and burns Activate credits |

---

## 2. Defense-in-Depth Logical Isolation (Passing Enterprise Security Reviews on Pooled Infra)

Enterprise CISOs do **not** require a separate AWS account per tenant if you prove **cryptographic and database-enforced tenant scoping** (rather than relying on developers remembering `WHERE tenant_id = ?` in every SQL query):

### A. PostgreSQL Row-Level Security (RLS) on RDS / Aurora
Enforce tenant isolation inside the database engine itself:
```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON documents
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
```
In your application middleware (verified from the Cognito JWT `custom:tenant_id` claim, **never** from a client-supplied request body/header), set `SET LOCAL app.current_tenant_id = '<verified-jwt-tenant-id>'` inside each transaction. Even if a developer writes `SELECT * FROM documents`, Postgres returns only that tenant's rows.

### B. DynamoDB + S3 Tenant Scoping via IAM Session Tags (ABAC)
For DynamoDB (`PK = TENANT#<tenant_id>#...`) and S3 (`s3://bucket/<tenant_id>/*`), use `sts:AssumeRole` with `PrincipalTag/tenant_id` so the AWS IAM plane rejects cross-tenant reads even if application code has a bug:
- **DynamoDB Condition**: `"ForAllValues:StringLike": { "dynamodb:LeadingKeys": ["TENANT#${aws:PrincipalTag/tenant_id}#*"] }`
- **S3 Condition**: `"StringLike": { "s3:prefix": ["${aws:PrincipalTag/tenant_id}/*"] }`

### C. Multi-Tenant AI / RAG Isolation (Amazon Bedrock Knowledge Bases & Vector Stores)
- **Never return unfiltered vector similarity search results across tenants.**
- In **Bedrock Knowledge Bases** / **OpenSearch Serverless** / **pgvector**, always inject a mandatory metadata pre-filter (`{"equals": {"key": "tenant_id", "value": verified_tenant_id}}`) derived from the authenticated JWT token before executing vector retrieval.
- For pgvector on RDS PostgreSQL, RLS policies on the embeddings table automatically filter vector queries by `tenant_id`.

---

## 3. Preventing "Noisy Neighbor" Outages Without Siloing

1. **API Gateway Per-Tenant Usage Plans / WAF Rate Limits**: Rate-limit by `tenant_id` or API key so one runaway customer script cannot exhaust Lambda concurrency for everyone else.
2. **SQS Fair Queues (`MessageGroupId = tenant_id`)**: When background jobs (PDF parsing, LLM batching, webhook delivery) run through **SQS FIFO with `MessageGroupId = tenant_id`**, AWS SQS automatically interleaves messages across tenants so one tenant enqueueing 50,000 jobs cannot block another tenant enqueueing 1 job.
3. **Per-Tenant Token Attribution**: Log `tenant_id`, `inputTokens`, and `outputTokens` from every Bedrock `Converse` response (`response["usage"]`) so you can spot unprofitable tenants early and enforce tier quotas.
