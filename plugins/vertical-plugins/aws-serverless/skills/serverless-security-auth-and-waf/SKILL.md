---
name: serverless-security-auth-and-waf
description: Design and harden serverless security across Amazon Cognito, API Gateway JWT and Lambda Authorizers, IAM least-privilege execution roles, Secrets Manager Lambda Extension caching, Lambda MicroVM snapshot/CSPRNG security, and FinOps-optimized AWS WAFv2 WebACLs. Use when securing APIs, fixing IAM over-privilege, caching secrets, protecting MicroVM sandboxes, or configuring WAF rate limiting and Bot Control without runaway costs.
---

# Serverless Security, Identity, Secrets & FinOps-Optimized AWS WAF

Implement defense-in-depth security across API Gateway, AWS Lambda, Lambda MicroVMs, Amazon Cognito, IAM, Secrets Manager, and AWS WAFv2 while avoiding common authorization bugs and WAF cost traps.

## When to Use

- Choosing and configuring **API Gateway authentication** (Native JWT Authorizer, Cognito User Pools, Custom Lambda Authorizers, `AWS_IAM`, or mTLS)
- Writing least-privilege IAM Execution Roles and resource-based policies with confused-deputy guards (`aws:SourceAccount`, `aws:SourceArn`)
- Caching secrets from AWS Secrets Manager or SSM Parameter Store inside Lambda using the **AWS Parameters and Secrets Lambda Extension**
- Securing **Lambda MicroVMs** (`CreateMicrovmAuthToken`, `X-aws-proxy-auth`, and CSPRNG reseeding on `/resume`)
- Designing a **FinOps-optimized AWS WAFv2 WebACL** for API Gateway REST APIs or CloudFront distributions

---

## 1. API Gateway Authentication & Authorizer Selection Matrix

| Mechanism | Supported API Type | Execution Cost | Latency Overhead | Best For |
|---|---|---|---|---|
| **Native JWT Authorizer** (`HttpJwtAuthorizer`) | HTTP API (v2) | **$0.00 (Free)** | **< 2 ms** (validated at API Gateway edge) | **Default choice** for OIDC/OAuth 2.0 tokens from Amazon Cognito, Okta, Auth0, or Microsoft Entra ID |
| **Cognito User Pool Authorizer** | REST API (v1) | **$0.00 (Free)** | **< 5 ms** | REST APIs using Cognito ID or Access tokens |
| **Custom Lambda Authorizer (Simple Response v2.0)** | HTTP API (v2) | Standard Lambda invocation charge (amortized via TTL cache) | 5–50 ms on cache miss; ~1 ms on cache hit | Custom API keys, HMAC signatures, tenant-lookup enrichment (`context` map), or multi-IdP logic |
| **Custom Lambda Authorizer (IAM Policy v1.0)** | REST API (v1) & HTTP API (v2) | Standard Lambda invocation charge | 5–50 ms on cache miss | Fine-grained per-route IAM policy enforcement |
| **`AWS_IAM` (SigV4)** | HTTP API, REST API, Function URL | **$0.00 (Free)** | **< 2 ms** | Service-to-service microservices, cross-account callers, or Cognito Identity Pool federated clients |

### CRITICAL Pitfall: Lambda Authorizer Caching (`AuthorizerResultTtlInSeconds`)
When using an IAM-Policy-returning Lambda Authorizer with caching enabled (`Identity.ReauthorizeEvery` / `AuthorizerResultTtlInSeconds: 300`):
- API Gateway caches the returned IAM policy **keyed only by the identity source (e.g., `Authorization` header)** across **ALL routes in the API stage**.
- **Bug**: If your authorizer returns `Resource: event["methodArn"]` (which points only to `GET /orders`), the cached policy will **deny (`403 Forbidden`)** the user's very next request to `POST /orders` or `GET /profile` for the next 5 minutes!
- **Fix**:
  - On **HTTP API (v2)**: Always use `AuthorizerPayloadFormatVersion: "2.0"` with `EnableSimpleResponses: true` (`{"isAuthorized": True, "context": {"tenantId": "t-123"}}`).
  - On **REST API (v1)**: Construct the allowed ARN with a stage-level wildcard (`arn:aws:execute-api:${region}:${accountId}:${apiId}/${stage}/*/*`) or explicit list of all routes the caller's role permits.

---

## 2. IAM Least-Privilege & Confused-Deputy Hardening

1. **One Execution Role Per Function**:
   - Never share a single monolithic IAM Role across multiple Lambda functions. If an API reader function only needs `dynamodb:GetItem` and `dynamodb:Query`, do not grant it `dynamodb:DeleteItem` or `s3:PutObject`.
2. **Use Scoped AWS SAM Policy Templates**:
   - Prefer built-in SAM policy templates (`DynamoDBReadPolicy`, `DynamoDBCrudPolicy`, `SQSPollerPolicy`, `SQSSendMessagePolicy`, `SNSPublishMessagePolicy`, `StepFunctionsExecutionPolicy`) parameterized with `!Ref` or `!GetAtt`.
   - When granting GSI queries, always include **both** the base table ARN and `!Sub "${Table.Arn}/index/*"`.
3. **Cross-Service Confused Deputy Protection**:
   - Every resource-based policy (`AWS::Lambda::Permission`, `AWS::SQS::QueuePolicy`, `AWS::SNS::TopicPolicy`, `AWS::S3::BucketPolicy`) allowing an AWS service principal (`s3.amazonaws.com`, `sns.amazonaws.com`, `events.amazonaws.com`, `apigateway.amazonaws.com`) MUST include `aws:SourceArn` (and `aws:SourceAccount` where applicable).

---

## 3. Secrets Management with the Parameters & Secrets Lambda Extension

Never store database passwords, API keys, or JWT signing keys in plaintext Lambda environment variables. Instead of calling `secretsmanager:GetSecretValue` over the network on every invocation (`$0.05 / 10,000 API calls` + 15–40 ms latency), attach the **AWS Parameters and Secrets Lambda Extension** layer, which caches secrets in memory on `localhost:2773`:

```python
import json
import os
import urllib.request

EXTENSION_PORT = os.environ.get("PARAMETERS_SECRETS_EXTENSION_HTTP_PORT", "2773")

def get_cached_secret(secret_id: str) -> dict:
    url = f"http://localhost:{EXTENSION_PORT}/secretsmanager/get?secretId={secret_id}"
    req = urllib.request.Request(
        url,
        headers={"X-Aws-Parameters-Secrets-Token": os.environ["AWS_SESSION_TOKEN"]},
    )
    with urllib.request.urlopen(req, timeout=2) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return json.loads(payload["SecretString"])
```

---

## 4. Lambda MicroVMs Security & Snapshot Hygiene

When deploying stateful or multi-tenant workloads on **Lambda MicroVMs** (`aws-lambda-microvms`):

1. **Data-Plane Authentication (`CreateMicrovmAuthToken`)**:
   - External clients or routers invoking a MicroVM data-plane endpoint must obtain a short-lived token via `lambda:CreateMicrovmAuthToken` (`DurationSeconds` up to **3,600 seconds / 60 minutes max**) and pass it in the **`X-aws-proxy-auth`** HTTP header.
2. **Mandatory CSPRNG Reseeding & Secret Refresh on `/resume`**:
   - Because MicroVMs restore from a memory snapshot across clones/resumes, any in-memory pseudo-random number generator (PRNG) state or cached temporary credentials frozen in the snapshot will be identical across resumed instances.
   - Inside your **`POST /resume`** lifecycle handler, ALWAYS:
     - Reseed language PRNGs/CSPRNGs from `/dev/urandom` (`random.seed(os.urandom(32))`, `OpenSSL RAND_poll()`)
     - Evict cached IAM/STS credentials and database auth tokens so fresh tokens are fetched post-resume.
3. **Tenant Isolation**:
   - Enforce a deterministic 1-to-1 mapping between authenticated `tenantId`/`sessionId` and `microvmId` (`^[a-zA-Z0-9._-]+$`, max 128 chars) at your API authorizer layer so Tenant A can never supply Tenant B's `microvmId`.

---

## 5. FinOps-Optimized AWS WAFv2 Architecture

Misconfigured AWS WAF WebACLs are a frequent source of serverless bill shock because **AWS Managed Bot Control (`$10/mo + $1.00 per 1M requests inspected`)** and **CloudWatch Logs (`$0.50/GB ingested`)** bill on every request that reaches them.

### Mandatory WAF Rule Priority Ordering (Cheapest First -> Most Expensive Last)

AWS WAF evaluates rules in ascending `Priority` order and stops at the first terminating `Block` or `Allow`. Always order rules from cheapest to most expensive:

| Priority | Rule Type | Cost Impact | Purpose |
|---|---|---|---|
| **10** | **Amazon IP Reputation List & Custom IP Blocklist** | Included in base WebACL | Drops known botnets, scanners, and Tor exit nodes immediately |
| **20** | **Geo-Match Block Rule** (`GeoMatchStatement`) | Included in base WebACL | Blocks traffic from non-serviceable regions before deeper inspection |
| **30** | **IP Rate-Based Rule** (`RateBasedStatement`, e.g., `1000` req / 5 min) | Included in base WebACL | Throttles DDoS/credential-stuffing bursts at the edge |
| **40** | **OWASP Core & Known Bad Inputs** (`AWSManagedRulesCommonRuleSet`, `AWSManagedRulesSQLiRuleSet`) | Included in base WebACL | Blocks SQLi, XSS, Log4j, and malformed payloads |
| **50** | **AWS Managed Bot Control** (`AWSManagedRulesBotControlRuleSet` — *Common level*) | **$1.00 / 1M requests inspected** | **MUST use a `ScopeDownStatement`** restricting evaluation ONLY to `/login`, `/signup`, `/checkout`, or `/api/auth/*`—never inspect static `.js/.css/.png` or health-check routes! |

### WAF Logging FinOps Guardrail
Never send unfiltered WAF logs (`ALL` traffic) to CloudWatch Logs. Configure **one** of:
- A **WAF `LoggingFilter`** with `DefaultBehavior: DROP` that only keeps requests where `Action == BLOCK` or `Action == COUNT`, OR
- Delivery via **Amazon Data Firehose** to an S3 bucket with GZIP/Parquet compression.
