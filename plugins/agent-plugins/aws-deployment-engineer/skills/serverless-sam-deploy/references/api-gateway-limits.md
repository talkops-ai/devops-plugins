# Amazon API Gateway Limits, Selection Matrix & CloudFront Cache Invalidation

## 1. Ingress Selection Matrix for Serverless Workloads

| Ingress Option | Max Timeout | Max Payload | Unit Cost (us-east-1) | Best For |
| --- | --- | --- | --- | --- |
| **API Gateway HTTP API (v2)** | **30 seconds** | **10 MB** | ~$1.00 / million requests | Default for JSON REST/HTTP APIs, OIDC/JWT & IAM auth, CORS, low latency, ~70% lower cost than REST API |
| **API Gateway REST API (v1)** | **29 seconds** (soft quota raisable for Regional/Private) | **10 MB** | ~$3.50 / million requests | API Keys & Usage Plans, AWS WAF association, Private VPC endpoints, request validation, response streaming |
| **Lambda Function URL + CloudFront OAC** | **15 minutes** (Lambda max, CloudFront origin read timeout up to 60–180s) | **6 MB** (20 MB streamed) | CloudFront + Lambda only | Long-running LLM/SSE response streaming (`InvokeMode: RESPONSE_STREAM`) with CloudFront edge protection |

## 2. Hardening API Gateway Stages

1. **Access Logging:** Always enable `AccessLogSettings` to a dedicated CloudWatch Log Group with JSON format (`requestId`, `ip`, `httpMethod`, `routeKey`, `status`, `integrationErrorMessage`).
2. **Throttling:** Configure `DefaultRouteSettings.ThrottlingBurstLimit` (e.g., `500`) and `ThrottlingRateLimit` (e.g., `1000` req/s) so traffic spikes or abusive clients cannot exhaust account-level concurrency.
3. **CORS:** Scope `CorsConfiguration.AllowOrigins` to explicit frontend origins in production (never `*` when `AllowCredentials: true`).
4. **Custom Domains:** Bind ACM certificate (`ENDPOINT_CONFIGURATION=REGIONAL`) and Route 53 `A`/`AAAA` Alias records targeting the API Gateway regional domain name and hosted zone ID.

## 3. CloudFront Static Asset Deployment & Cache Invalidation

When deploying SPA/SSR static assets to a private S3 bucket fronted by Amazon CloudFront with **Origin Access Control (OAC)**:

1. Sync immutable hashed assets (`/assets/*`) with long cache control:
   ```bash
   aws s3 sync ./dist/assets "s3://${BUCKET_NAME}/assets" \
     --cache-control "public,max-age=31536000,immutable" \
     --delete
   ```
2. Sync entry HTML (`index.html`) with `no-cache`:
   ```bash
   aws s3 cp ./dist/index.html "s3://${BUCKET_NAME}/index.html" \
     --cache-control "no-cache,no-store,must-revalidate"
   ```
3. Invalidate the CloudFront distribution cache and poll completion:
   ```bash
   INVALIDATION_ID=$(aws cloudfront create-invalidation \
     --distribution-id "${DISTRIBUTION_ID}" \
     --paths "/index.html" "/config.json" \
     --query 'Invalidation.Id' --output text)

   aws cloudfront wait invalidation-completed \
     --distribution-id "${DISTRIBUTION_ID}" \
     --id "${INVALIDATION_ID}"
   ```

> **FinOps Tip:** Avoid invalidating `/*` when only `index.html` and manifest files changed, and keep invalidation paths concise (first 1,000 invalidation paths per month are free).
