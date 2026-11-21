# AWS Marketplace Metering — Complete Setup Questionnaire, Lifecycle & Query Reference

## SETUP PATH — Deploy New Metering Integration

Full walkthrough: `references/setup-path.md` + `references/deployment-steps.md`.

### Seller Questionnaire (ask ALL before generating code)

- **Q1 Product code (or product ID).** Accept either; resolve a product ID to the code via the Catalog API (`describe-entity`) at validation. The dimension list is NOT a deploy input (dimension validity is server-authoritative); you may list dimensions for the seller's info only. **Recommend validating dimension NAMES against the catalog with the Marketplace Catalog API `DescribeEntity` (us-east-1)** before the seller wires them into usage rows — the returned entity details enumerate the product's registered dimension API names (case-sensitive). Confirming the seller's dimension strings match the catalog exactly at setup time is the way to avoid the runtime **`InvalidUsageDimensionException`** (an undefined/misspelled/wrong-case dimension fails the whole `BatchMeterUsage` call). This is a validation aid only — it does NOT make the dimension list a deploy input.
- **Q2 Are you the ISV/seller?** Only the seller (publisher) or an authorized 3PI may integrate; a 3PI is out of scope — decline. Confirm publishing-account access.
- **Q3 Which region(s) do you meter from?** Events stack is always us-east-1; deploy a main stack in EACH region where usage occurs and meter in-region. Dedup is per `CustomerAWSAccountId + LicenseArn + dimension + hour`, scoped to the submission region — do NOT funnel all usage into one region. [Region support](https://docs.aws.amazon.com/marketplace/latest/developerguide/metering-regions.html#batchmeterusage-region-support).
- **Q4 Stage name (MANDATORY).** API Gateway stage (e.g. `v1`/`live`/`prod` — seller's choice). **No default, no fallback to `prod`**; deploy fails fast if empty. Pass via `STAGE_NAME`.
- **Q5 Does a stack already exist for this product?** If yes → modify/extend: gather context and inspect the seller's existing stack (may use arbitrary naming) before changing anything — see `references/existing-sellers.md`.
- **Q6 Metering lock hours** (`METERING_LOCK_HOURS` → `MeteringLockHours`, default 1, validated **1..20**). How many hours an hour stays open for late usage before it is aggregated/submitted (default 1 = process the just-completed hour). At the cap, an hour is first submitted at age 20, leaving ≥4h in the 24h billable window for retries/re-drive. **Month-aware:** previous-month hours keep the lock until 03:00 UTC on the 1st, then no-lock (submit each run) until the 06:00 UTC cutoff, and aren't aged out before then; a previous-month record written after 03:00 must already be pre-aggregated (else `DuplicateRecord`).
- **Q7 TTL / retention** (per table, `deploy.sh` env vars; `0` disables):
  - Raw usage table `USAGE_TABLE_TTL_DAYS` (default 365) — RECOMMEND on (high-volume table). The seller's writer sets the `ttl` epoch attribute; the template only makes DynamoDB honor it. Floor ≥2 days that must exceed `MeteringLockHours`+24h so a row can't expire before metering.
  - Aggregated table `AGGREGATED_USAGE_TTL_DAYS` (default 0 = retain) — RECOMMEND omit/large (small billing audit trail). When >0 the submitter sets `ttl` only on `Success` rows.
  - Enabling TTL needs the deployer's `dynamodb:UpdateTimeToLive` (already in the policy).
- **Q8 Create health dashboards?** (`CREATE_DASHBOARD`, default true). Per-product main-stack dashboard (per-Lambda Errors/Throttles/Invocations/Duration; queue/DLQ depth + oldest-age; EMF `UsageRecordRejected` by reason, `UsageRecordUnprocessed`, `CustomerNotSubscribed`, `BatchMeterUsageException` by exception, `UsageAggregationExpired`, `UsageSubmissionExpired`, `DuplicateRecord`) + a shared events-stack dashboard. Health-only; reflects the deployed mode (Q9); sellers can opt out / customize.
- **Q9 Full pipeline vs direct-submit** (`DEPLOYMENT_MODE`, default `full`) — explain both so the seller chooses knowingly:
  - **full** — seller emits RAW per-second events; the skill deploys the raw `usage` table + discoverer→aggregator→cleanup→submitter→submission-expiry, and the pipeline aggregates each `(licenseArn, account, dimension, hour)` group to one `BatchMeterUsage` record/hour. Best when the seller doesn't already aggregate or wants platform-owned aggregation + client-side rejection visibility.
  - **direct-submit** — seller ALREADY produces finalized hourly totals; the skill deploys ONLY `aggregated_usage` + submitter + submission-expiry + register/subscription (smaller/cheaper). Seller writes finalized records straight to `aggregated_usage` (PK `licenseArn`, SK `customerAWSAccountId#dimension#hour`, `quantity`, `meteringPending`=hour bucket).
  - **Finalize-before-insert (direct-submit, critical):** any record in `aggregated_usage` MAY be submitted on the next 5-min run — write a record ONLY when FINAL for its group, because a second write returns `DuplicateRecord` and the later quantity is NOT billed. The seller owns upstream aggregation/idempotency here.
  - **Not a one-way door:** the seller can switch modes later (a stack UPDATE that adds/removes mode-specific resources; raw `usage` table is `Retain`). Call out the blast radius before flipping a live stack.
- **Q10 Registration fields + profile lookups** (`ALLOWED_REGISTRATION_FIELDS`) — EXPLAIN first, then ask. The in-region register Lambda persists ONLY these allowlisted fields (each length-bounded; the token is never stored) as a **`registrationData` map** on the in-region **`customer-profile`** table (PK `licenseArn`, SK `customerAWSAccountId`) — buyer **PII stays in-region and OUT of the PII-free us-east-1 subscribers table**. Fields in the map are retrievable by the base key but NOT independently queryable. Ask: (a) which form fields to capture (incl. any KYB fields — name/email/company/use-case); (b) whether any field must be **looked up directly** (e.g. by `email`) — if so it is **promoted** to a top-level attribute + a **GSI** (ask HASH-only or HASH+RANGE per promoted field). Keep fields OPTIONAL/seller-confirmed; invent no PII; mask PII in logs. **Mapping `licenseArn`→the seller's internal SaaS tenant ID is the SELLER's responsibility** — anchor it on the subscribers table (`licenseArn` from `License Updated`, PII-free) and/or the customer-profile table (`licenseArn` captured at registration); add a `tenantId` attribute + GSI if lookup-by-tenant is needed (`references/architecture.md`).

> **Product Type Gate:** after credentials, verify via the Catalog API the product is SaaS + usage-based (`ExternallyMetered`). AMI/Container/SaaS-Contract-only → out of scope, redirect to [public docs](https://docs.aws.amazon.com/marketplace/).
> **Concurrent Agreements is the silent default** — all new products use `CustomerAWSAccountId` + `LicenseArn`; do NOT ask. A pre-existing legacy stack may use `ProductCode` + `CustomerIdentifier` — understand it before changing (`references/existing-sellers.md`).

### Setup ordering (do NOT skip or reorder)

1. Obtain ephemeral credentials (SSO → `sts assume-role`; never long-lived keys; don't ask for keys first).
2. Product type gate (SaaS + ExternallyMetered).
3. Product visibility gate — deploy/mutate the product-specific MAIN stack ONLY when the CURRENT product is `Limited`, never `Published` (provide code for the seller's own pipeline instead). Direct-deploy the main stack only when the current product is `Limited` AND there is no existing per-product stack (an existing one is modify/extend, seller-confirmed). The SHARED events stack is never redeployed/mutated when it already exists (it may serve other, possibly `Published`, products with live traffic — reuse its outputs); only the first onboarding creates it. See `references/existing-sellers.md`.
4. Confirm the questionnaire answers (incl. stage name).
5. Only THEN generate + deploy: **materialize the template(s) + Lambda handlers + `deploy.sh` in the seller's workspace and deploy THOSE on-disk files** (`sam build --template-file` + `sam deploy`) — never an inline/transient template. Modify/extend edits the seller's existing files in place (merge env vars). Leave all artifacts in the workspace afterward (code/stack parity; seller can version/re-deploy/develop, customizing only `TODO:` sections).
6. **EXISTING-STACK guardrails (ENFORCE, do not bypass).** WHEN a stack already exists for this scope, the skill SHALL NOT auto-apply changes: it SHALL (a) present the exact diff/change set for the seller's review, (b) require the seller's EXPLICIT confirmation and their normal CODE REVIEW + change-management process before applying, (c) scope changes to the CURRENT product's main stack, and (d) never redeploy/mutate the shared events stack that already serves other (possibly `Published`) products — reuse it. Direct auto-deploy is reserved for a `Limited` product with NO existing stack. See `references/existing-sellers.md`.
7. **After integration, run the full test plan.** At the END of setup/modify, the skill SHALL recommend and (where it can) walk the seller through the complete hands-on test plan (`references/test-plan.md`) — verifying every expected observable outcome — and SHALL state that the integration should not carry PRODUCTION billing traffic until that review + testing passes.

A failure at any gate stops the workflow before deployment.

### Stack naming

| Component | Pattern | Example |
|-----------|---------|---------|
| Events stack | `awsmp-events-stack` | Shared, us-east-1 |
| Main stack | `awsmp-<productCode>-metering` | `awsmp-4ml54db8vrmjuykaw1psroool-metering` |
| Events stack (staged) | `awsmp-events-<stageName>-stack` | `awsmp-events-beta-stack` |
| Main stack (staged) | `awsmp-<productCode>-<stageName>-metering` | `awsmp-4ml54db8vrmjuykaw1psroool-beta-metering` |

For a non-production sandbox, deploy stage-scoped stacks (the stage folds into every resource name) and set `MeteringMode=dry-run` so the submitter never calls the real `BatchMeterUsage` — use test accounts only. See `references/existing-sellers.md` / the setup path.

### Supported features

SaaS Usage (PAYG) ✅ | Concurrent Agreements ✅ | VMT ✅ | Multi-region ✅ | Multi-product ✅
Out of scope (→ [public docs](https://docs.aws.amazon.com/marketplace/)): CCP, AMI/Container, SaaS-Contract-only (GetEntitlements), 3PI.

> **Scale:** the pipeline is decoupled (discoverer → work queue → aggregator → aggregated-usage + cleanup queue → submitter) so it is designed to handle thousands of metering records per hour. Second-precision rows bound a group at ≤3600 rows/hour → supports high volume at ≤~1 write/sec per `(licenseArn, account, dimension)` group. For finer/higher rates, recommend a streaming ingestion tier (e.g. Kinesis Data Streams) that pre-aggregates to per-second/hour rows (public-knowledge/host-model-determined, not first-class to this skill). Full design: `references/scalable-metering-design.md`.
> **GSI-driven discovery (never a Scan):** the discoverer finds pending usage via the sparse **`metering_pending` GSI — HASH = `meteringPending` hour-bucket (`YYYY-MM-DDTHH`), RANGE = `licenseArn`**, projecting **`customerAWSAccountId` + `dimension`** (INCLUDE/ALL, NOT `KEYS_ONLY`) so a query returns the `(licenseArn, customerAWSAccountId, dimension)` tuples directly — no follow-up read to discover the group. Each group is then read with a **targeted `begins_with` sort-key prefix** (`begins_with(customerAWSAccountId#dimension#timestamp, "{account}#{dimension}#{hourPrefix}")`), NOT a full `licenseArn`-partition query + timestamp `FilterExpression`.

### Deployment (summary; full steps in `references/deployment-steps.md`)

1. Generate SAM template + Lambda code (fill `TODO:`s).
2. Deploy events stack (us-east-1) — shared EventBridge + subscribers table.
3. Deploy main stack (seller's region) — Lambdas + DynamoDB + API Gateway + alarms.
4. Set the AMMP **Fulfillment URL** to the **branded registration page** (S3+CloudFront front-end that captures buyer/KYB fields and calls `RegistrationUrl`), NOT the raw `RegistrationUrl` (smoke-test fallback only) — manual seller step. See `references/registration-page.md`.
5. End-to-end test (subscribe → resolve → write a conforming usage row → discoverer → aggregator → submitter → verify `Aggregated` + `Success`).
6. Validate via CloudTrail logs.

**After deploy, state the seller's ongoing responsibilities and guide the hands-on test** (`references/test-plan.md`): the stacks do nothing until the seller **writes conforming usage rows** — whole-second `customerAWSAccountId#dimension#timestamp` sort key (matching segments) and a `meteringPending` bucket that **equals the row's own UTC timestamp hour**. A **mis-stamped `meteringPending` is the ONE writer error the pipeline cannot detect** (silently never metered) — confirm via the test. Also: subscribe a notification to the alarms + watch the dashboards (`UsageRecordRejected` by reason, `BatchMeterUsageException` by exception, `CustomerNotSubscribed`, `UsageAggregationExpired`/`UsageSubmissionExpired`); catalog dimension changes need no redeploy. Several results are async (post-subscribe `License Updated` → `licenseArn`/`subscriptionStatus`; hourly discoverer + `rate(5m)` submitter/expiry) — **poll with bounded backoff**, or manually invoke a Lambda to exercise a path immediately (say which). **Recommend running the FULL test plan (`references/test-plan.md`) end-to-end at the end of the integration and verifying every expected observable outcome — plus a review of all created/changed resources — BEFORE the integration carries production billing traffic** (AI-generated output; see the review-before-production callout above).

Prerequisites, credentials, and the full least-privilege deployer policy: `references/iam-credentials.md`.

### Event & status model (recite when asked how cancellation/metering works)

Two INDEPENDENT status fields on the subscriber row (never conflate):

- **`agreementStatus`** = `active`/`inactive` (agreement lifecycle).
- **`subscriptionStatus`** = `active`/`deprovisioning`/`inactive` (license lifecycle; there is **no `deprovisioned` value**).

Metering follows the LICENSE lifecycle only:

- **`License Updated`** → agreement+subscription `active` (metering allowed).
- **`License Deprovisioned`** → `subscriptionStatus=deprovisioning` + a `deprovisioningExpiry` (event time + ~1h); OPENS the ~1-hour final-usage flush window. **The lock-bypass mechanism:** during this window the pipeline submits ALL remaining pending usage for that license IMMEDIATELY, **ignoring `MeteringLockHours` and the normal completed-hours-only gate** — it does NOT wait for `MeteringLockHours` to elapse and it DOES meter the **current in-progress hour** (the one hour the normal path always skips). **Concrete mechanism/marker:** the `License Deprovisioned` handler sets `subscriptionStatus=deprovisioning` + `deprovisioningExpiry` on that subscriber row; the discoverer runs in a **flush-deprovisioning mode** that keys off that marker and enqueues the pending buckets (over `now-23h … now-1h` PLUS the current hour) for **only that license**, oldest-first. **The bypass is SCOPED to the deprovisioning license ONLY** — other active licenses keep the normal `MeteringLockHours` gate and completed-hours-only behavior; one buyer's deprovisioning never force-flushes another buyer's open hour. It is the deprovisioning flush that bypasses the lock, NOT a change to `MeteringLockHours` itself and NOT a `Purchase Agreement Ended` event. Once the window has elapsed, the events-stack **deprovision-cleanup** Lambda (rate(15m)) sets `inactive` and clears the deprovisioning markers — finalization is time-based, so it is correct across multiple hours and regions. After the server window closes, `BatchMeterUsage` returns `CustomerNotSubscribed`.
- **`Purchase Agreement Ended`** → `agreementStatus=inactive` ONLY (does NOT change subscriptionStatus, stop metering, or flush).
- **`Purchase Agreement Amended`** → refresh agreement metadata (stays active).
- **`Purchase Agreement Created`** → NOT consumed by metering (no licenseArn); the seller handles it if needed (pre-provisioning, CRM), without activating metering.

Do NOT invert these (`License Deprovisioned`, not `Purchase Agreement Ended`, opens the flush window). Do NOT discard queued records before flushing. `registeredRegions` is reference-only and NEVER gates metering.

### Setup references

- Full walkthrough + writer contract + Common Mistakes + VMT/token/timestamp/schema/meter-flow: `references/setup-path.md`
- Deployment steps: `references/deployment-steps.md` · IAM policy: `references/iam-credentials.md`
- Concurrent Agreements + data model: `references/concurrent-agreements.md` · Architecture + status lifecycle: `references/architecture.md`
- Existing sellers (modify/extend, legacy): `references/existing-sellers.md`
- Branded buyer page + Know Your Buyer (KYB) capture: `references/registration-page.md`
- Hands-on test plan (manual steps, scoped cases, async polling): `references/test-plan.md`
- Monitoring & alarms: `references/troubleshooting.md` · Client-side guardrails (all checks before `BatchMeterUsage`): `references/client-side-guardrails.md`
- Reference implementation: `scripts/metering_core.py` (shared) + `discoverer.py`/`aggregator.py`/`cleanup.py`/`submitter.py`/`expiry.py` (pipeline) + `register.py`/`subscription.py`; `scripts/test_event_publisher.py` (non-prod sandbox test-event generator, dry-run stages only); `scripts/deploy.sh` (needs `assets/requirements.txt`); SAM templates `assets/template-main.yaml`, `assets/template-events.yaml`

### Monitoring & alarms (seller-owned)

The deployed stack creates `awsmp-*` metrics + CloudWatch alarms in the SELLER's account covering the revenue-loss signals (per-stage Lambda `Errors`/`Throttles` across discoverer/aggregator/cleanup/submitter/expiry, a "did not run" invocations alarm, `>24h` age-out, and the EMF business-status metrics). Alarms are always created; actions wire to an OPTIONAL in-region SNS topic (`AlertsTopicArn`). Business-status metrics use EMF from the Lambda logs (no extra runtime IAM). **Handling alarms is the seller's responsibility** — AWS Marketplace and this skill do not track client-side errors; neither the deployer nor any Lambda publishes to the topic (CloudWatch fires the action). Thresholds/actions/topic are seller `TODO:`s. Detail: `references/troubleshooting.md`.

**"What alarms tell me metering records are being REJECTED / not metered?"** — the stack creates a dedicated alarm on each rejection/failure signal so a seller is paged the moment records stop metering (all fire into `AlertsTopicArn`; thresholds are seller `TODO:`s):

- **`UsageRecordUnprocessed`** (alarm `*-usage-unprocessed`) — `BatchMeterUsage` returned `UnprocessedRecords` that were STILL unprocessed after the submitter's one automatic retry. The submitter does NOT raise on this (it leaves them pending for the next `rate(5m)` cycle), so this metric is the ONLY alarm-able signal for the `UnprocessedRecords` case — it does NOT trip the Lambda `Errors` alarm. A persistent breach = records repeatedly failing to meter (throttling, timestamp bounds, downstream issue) → investigate.
- **`UsageRecordRejected`** (`*-usage-rejected`) — client-side guardrail rejections before metering (summed across reasons; per-reason breakdown on the dashboard); fix source rows + resubmit. **`BatchMeterUsageException`** (`*-batchmeterusage-exception`) — a REQUEST-level exception failed a whole call (dimension/license/etc.); pipeline bisects to isolate. **`CustomerNotSubscribed`** (`*-customer-not-subscribed`) — per-record status, no active subscription (do NOT retry).
- Plus age-out alarms (`UsageAggregationExpired`/`UsageSubmissionExpired`, `>24h`) catch usage that silently never metered, and Lambda `Errors`/`Throttles`/DLQ-depth alarms catch pipeline failures. `DuplicateRecord` is a dashboard metric (informational — first submission already billed), not an alarm.

---

## QUERY PATH — Find, Debug, and Analyze Metering Records

Full routing/patterns: `references/query-path.md` + `references/query-patterns.md`.

**Capability boundary (state it; don't return a bounded answer as authoritative).** This query **USES** CloudTrail Event History (`LookupEvents`) in the seller's region, last ≤90 days, **page-bounded and processed in memory** — a recent, regional, SUBMISSIONS view (includes rejected/duplicate records that were NOT billed) for BASIC operational/debug queries (lookups + simple filters/counts/summaries by customer, dimension, status, time). It **RECOMMENDS** (does not run): Seller Reports/SDDS for billed totals + >90-day history; the host agent + model for complex/open-ended analytics (hand it the fetched data); and — for CA/LicenseArn metering with no LicenseArn→productCode mapping (single-product-stack context, CloudTrail `additionalEventData`, or the subscribers table) — only non-product-scoped queries (never guess attribution). Every result carries `complete`/`truncated`/`windowClipped`. **Before presenting a result, CONFIRM these signals:** if `complete` is false (page-truncated OR clipped at the 90-day retention limit), either re-run for a complete answer where feasible (narrow/adjust range for a clip; raise `--max-pages` or add filters for truncation) or state explicitly that the result is PARTIAL — what was clipped/truncated and the covered range — and point to Seller Reports for the authoritative/older portion. A truncated or clipped aggregate (summary/count/top_customers) is a **lower-bound sample, NOT authoritative**. Never report a partial result as the full requested range. Do not refuse a basic query just because a richer answer is possible in the host agent. **CloudTrail-derived SQL is the WRONG source for billing/usage analytics** — CloudTrail Lake OR Athena over a `trail → S3` export both see SUBMISSIONS only (rejected/duplicate, regional, no CA `productCode`); do NOT set up CloudTrail **Lake** for metering; for complex analytics / billing-grade totals / >90-day data use **SDDS** (recommend, don't run), and use a `trail → S3` (never Lake) only for long-term raw-submission audit retention. Full boundary: `references/query-path.md`.

**Complex / billing-grade query steering — MUST NOT vs allowed sources (enforce; do not violate).** For any complex-analytics or billing-accuracy question over metering data:

- **MUST NOT** recommend **CloudTrail Lake** (`create-event-data-store`) for metering — ever.
- **MUST NOT** present CloudTrail (Event History OR a `trail → S3`/Athena export) as a source of **billed/billing-grade totals** — CloudTrail sees SUBMISSIONS only (includes rejected/duplicate, regional, no CA `productCode`), so it is never authoritative for revenue.
- **Allowed sources only:** for billed/disbursed totals and >90-day billed history → **Seller Reports / AMMP Billed Revenue dashboard** and **SDDS** (recommend, do not run); for recent (≤90-day) regional SUBMISSION debugging → **CloudTrail Event History**; for complex/open-ended analytics → hand the fetched data to the **host agent + model**; for long-term RAW-submission audit retention only → a plain **`trail → S3`** (NOT Lake) + Athena, understanding it is submissions-not-billing. Route every complex-billing ask to these allowed sources and name why CloudTrail is not billing-authoritative.

### Steps

1. **Ask the metering region** (MUST — CloudTrail is regional).
2. Extract filters: `customer_id`, `status`, `dimension`, `start_date`/`end_date`, `query_type` (summary/detail/count/list_failures/top_customers), `top_n`.
3. Run the script (default: last 7 days):

```bash
python3 ./scripts/query_metering.py \
  --region <SELLER_METERING_REGION> \
  [--days N] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] \
  [--customer-id ACCT_ID] [--status STATUS] [--dimension DIM] \
  [--product-code PC] [--deployment-product-code PC] \
  [--query-type summary|detail|count|list_failures|top_customers] \
  [--top-n N] [--limit N] [--max-pages N]
```

**CloudTrail Event History recipe (what the script does; use directly if querying by hand).**
Event History is on by DEFAULT — no data store, no setup, **never CloudTrail Lake /
`create-event-data-store`** for metering. Query IN the seller's metering region and filter on
the metering event source:

```bash
aws cloudtrail lookup-events --region <SELLER_METERING_REGION> \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=metering-marketplace.amazonaws.com \
  --start-time <ISO> --end-time <ISO>
```

Each `BatchMeterUsage` event's CloudTrail `responseElements` carries **`results`** (per-record `status`:
`Success`/`CustomerNotSubscribed`/`DuplicateRecord` — those are the ONLY per-record statuses) and
**`unprocessedRecords`** — to verify a submission, check `results` vs `unprocessedRecords` FIRST
(records in `unprocessedRecords` were not processed — see the `UnprocessedRecords` note below). CloudTrail lowercases the
first letter of response fields, so read `results`/`status`/`meteringRecordId`/`unprocessedRecords`
(lowercase) — the direct SDK `BatchMeterUsage` response uses PascalCase (`Results`/`Status`/
`MeteringRecordId`/`UnprocessedRecords`). An undefined dimension
is NOT a per-record status — it fails the whole call with a request-level
`InvalidUsageDimensionException` (see below). ≤90 days only; for older/billed totals use Seller
Reports/SDDS (recommended, not queried). **CloudTrail is NOT revenue** — it shows submissions
(incl. rejected/duplicate, not billed). Metered usage **bills at the START of the following month
(the 2nd/3rd)** — e.g. November usage lands on the December invoice — and dashboard revenue is
**estimated** until the month closes; use Seller Reports for billed/disbursed amounts.

### Status meanings

Per-record `Results[].Status` values:

| Status | Meaning | Action |
|--------|---------|--------|
| `Success` | Accepted and billed | None |
| `CustomerNotSubscribed` | No active subscription | ⚠️ Do NOT retry |
| `DuplicateRecord` | First-write-wins and reported; a differing-quantity resubmit is NOT billed | Safe only for an identical retry; never to change a quantity (under-billing risk) |

Request-level exceptions (fail the ENTIRE `BatchMeterUsage` call, NOT a per-record status). Each has a **client-side guardrail reason code** the pipeline stamps when it rejects the row BEFORE the API call (`RejectedClientSide`, not billed), plus the **server-side exception** if a row reaches the API — surface BOTH when explaining a rejection:

| Server-side exception | Client-side reason code | Meaning | Action |
|-----------|-----------|---------|--------|
| `InvalidUsageDimensionException` | `InvalidDimension` | A dimension not defined in the catalog (server-authoritative; case-sensitive; not billed) | Fix the dimension key / define it in AMMP. The pipeline isolates the offending record by bisection (depth-bounded, ⌈log2(batch size)⌉=5) so its co-batched records still meter, marks it `RejectedClientSide` (reason = the exception name), and emits the `BatchMeterUsageException` metric. |
| `TimestampOutOfBoundsException` | `MalformedTimestamp` | A record older than 24h (e.g. a 30h-old row) or otherwise outside the window — REJECTED, not submitted | Fix the timestamp; the client-side guardrail rejects the row with reason `MalformedTimestamp` before batching, and one bad timestamp that reaches the API rejects the whole batch until isolated. |
| `InvalidLicenseException` | `InvalidLicenseArn` | A malformed/invalid `LicenseArn` | Shape-validate client-side (reason `InvalidLicenseArn`); a server-side `InvalidLicenseException` is isolated by (bounded) bisection and marked `RejectedClientSide` with the exception name. |
| `TooManyTagsException` | `TooManyTags` | More than 5 `usageAllocations` tags on a UsageRecord | Reduce to ≤5 tags; the client-side guardrail rejects the row with reason `TooManyTags` before batching. |

**Sort-key / reject-code ordering:** the pipeline validates a row's shape BEFORE it can enter a batch. A row whose sort key (`customerAWSAccountId#dimension#timestamp`) carries a malformed or out-of-window timestamp is **rejected client-side with reason code `MalformedTimestamp`** (marked `RejectedClientSide`, emits `UsageRecordRejected`) — it never reaches `BatchMeterUsage`, so it does NOT surface as a server-side `TimestampOutOfBoundsException` unless a bad timestamp slips through into a batch. Always name the client-side `MalformedTimestamp` reason code for a malformed-timestamp sort key, and its server-side `TimestampOutOfBoundsException` equivalent.

**Full reject-/status-code catalog (the ONE place to cite for any reason-code question).** A question like "what does `UnknownDimension` mean?" should be answered from this complete set, mapping the client-side guardrail reason code to its server-side equivalent:

| Client-side reason code (`RejectedClientSide`, pre-API, not billed) | Server-side equivalent | Meaning |
|---|---|---|
| `MalformedSortKey` / `SortKeyMismatch` | — (never reaches API) | Sort key not `customerAWSAccountId#dimension#timestamp`, or its segments don't match the row's own attributes |
| `MalformedTimestamp` / `TimestampOutOfWindow` | `TimestampOutOfBoundsException` | Non-whole-second, unparseable, or >24h-old timestamp |
| `MissingDimension` | — | Row has no `dimension` |
| `InvalidDimension` / `UnknownDimension` | `InvalidUsageDimensionException` | Dimension not defined in the catalog (case-sensitive) — `UnknownDimension`/`InvalidDimension` are the same "dimension not in the AMMP catalog" condition |
| `NegativeQuantity` | — | Quantity < 0 |
| `NonIntegerQuantity` | — | Quantity not a whole integer |
| `TooManyTags` | `TooManyTagsException` | >5 `usageAllocations` tags on a record |
| `TooManyAllocations` | — | >2500 merged tag-sets in a group |
| `AllocationSumMismatch` | — | `AllocatedUsageQuantity` values don't sum to the row `quantity` |
| `MixedAllocatedAndUnallocated` | — | Group mixes tagged and untagged non-zero rows |
| `InvalidLicenseArn` | `InvalidLicenseException` | Malformed/invalid `LicenseArn` (also fires when products are mixed in one batch) |

Plus the terminal per-record `Results[].Status` verdicts returned BY the API (not client-side reasons): **`Success`** (billed), **`DuplicateRecord`** (first-write-wins; a differing-quantity resubmit is NOT billed — under-billing risk, not "benign"), **`CustomerNotSubscribed`** (no active subscription — do NOT retry). And `UnprocessedRecords` (transient, retryable) — see below.

**`UnprocessedRecords` (a THIRD, distinct outcome — neither a per-record `Results[].Status` verdict nor a request-level exception):** a PARTIAL-BATCH result (succeeded records in `results`; failed-to-process ones in `unprocessedRecords` — NOT billed, typically TRANSIENT `ThrottlingException`/`InternalServiceException`), SAFE to re-submit (idempotent); the submitter retries ONCE then leaves it for the NEXT scheduled run (alarmed via `UsageRecordUnprocessed`). Do NOT treat it as accepted/billed or confuse it with the FINAL `Results[].Status` verdicts above.

**Data tiers:** CloudTrail Event History (≤90 days, free, real-time) is the tier the skill queries directly; it shows ALL submissions (incl. rejected/duplicate), Seller Reports show only billed — so "totals don't match" = the rejected/duplicate delta. Two separate history questions, don't conflate them:

> **Reconciling SUBMITTED (CloudTrail) vs BILLED (Seller Reports).** Treat **Seller Reports / AMMP Billed Revenue as the billed source of truth**; CloudTrail is submissions only. To reconcile, **filter CloudTrail to `Status=Success`** (exclude `DuplicateRecord`, `CustomerNotSubscribed`, and request-level exceptions — none of those bill) and compare that to the billed report; the leftover gap is the expected rejected/duplicate delta. **Watch for `DuplicateRecord`s with DIFFERENT quantities** for the same `(account, licenseArn, dimension, hour)` — that is NOT benign: first-write-wins means the later (often larger) quantity was NOT billed, so it can indicate **under-reporting/under-billing**. Surface those as a reconciliation red flag rather than dismissing duplicates.

- **BILLED history (any range) needs NO setup** — the AMMP Insights **"Billed Revenue" dashboard** (only `aws-marketplace:GetSellerDashboard`; default 6 months, widen the invoice-date filter). Console-only (QuickSight) + manual CSV export — **no on-demand billed API**. Programmatic billed data = **SDDS** (daily S3 push + your Athena/ETL), but push-only and **enrollment-forward (no backfill)**. Skill recommends, doesn't run; **never `GenerateDataSet`**. Detail: `references/seller-reports.md`.
  - **Discounts / private offers are NOT a metering or Seller-Reports concern — redirect to the public AWS Marketplace channel (AMMP).** If a seller asks why billed amounts differ from metered usage because of a **discount or private offer**, or how to apply/change one, do NOT try to explain or reconcile it from metering data and do NOT stop at "out of metering scope." The pricing that turns metered quantity into billed revenue (public price, private offers, discounts, EULA terms) is managed in the **AWS Marketplace Management Portal (AMMP)** — state that the discount/private-offer delta is expected (Seller Reports show BILLED revenue after any negotiated discount, while CloudTrail shows raw metered SUBMISSIONS) and redirect discount/private-offer creation and management to AMMP → [AWS Marketplace Management Portal](https://aws.amazon.com/marketplace/management/) / [private offers](https://docs.aws.amazon.com/marketplace/latest/userguide/private-offers-overview.html).
- **RAW SUBMISSION history beyond 90 days has NO out-of-the-box source** (Seller Reports/SDDS are billed-only; Event History keeps 90 days). Retain via a self-managed **CloudTrail trail → S3** on `metering-marketplace.amazonaws.com` (plain trail, **NOT Lake**; Athena) — also **from setup forward, no backfill**; complementary DynamoDB PITR export of `aggregated_usage`. Detail: `references/query-patterns.md`.

### Query references

- Routing + parameters: `references/query-path.md` · CloudTrail CLI patterns + pagination: `references/query-patterns.md`
- Seller Reports reconciliation + SDDS automation boundary: `references/seller-reports.md` · Dimension reference: `references/dimension-reference.md`

---

## Key APIs

| API | Region | Purpose |
|-----|--------|---------|
| ResolveCustomer | any region (seller's choice) | Resolve token → LicenseArn + customerAWSAccountId + productCode at registration; regional, from the publishing account; independent of the BatchMeterUsage region |
| BatchMeterUsage | seller's metering region | Submit usage records (hourly) |
| DescribeEntity | us-east-1 | Validate product / type / visibility |
| LookupEvents | seller's region | Query metering records (≤90 days) |

IAM action names: `aws-marketplace:BatchMeterUsage` (meter), `aws-marketplace:ResolveCustomer` (register), `aws-marketplace:GetSellerDashboard` (reports). Namespace is `aws-marketplace:`, NOT `meteringmarketplace:*`. When diagnosing AccessDenied, name the exact action and check the execution role, condition keys, and Resource-ARN mismatches.

## Security

- **Least privilege:** execution roles grant ONLY the actions used — meter path: `aws-marketplace:BatchMeterUsage` + scoped DynamoDB `Query`/`UpdateItem` on its tables + the `metering_pending` index; register: `aws-marketplace:ResolveCustomer` + scoped `Query` on the `customerAWSAccountId` GSI + item ops. **No `dynamodb:Scan`** (lookups use GSI `Query`); never `dynamodb:*` or broad `aws-marketplace:*`.
- **No swallowed auth errors:** subscriber/license lookups do NOT catch `AccessDeniedException` as "not found" — permission/config errors surface (Lambda error / 500 / DLQ).
- **Encryption at rest:** SQS (`SqsManagedSseEnabled`), SNS (`alias/aws/sns`), DynamoDB (`SSEEnabled`); Lambda + API log groups are explicit resources with `RetentionInDays` + optional `KmsKeyId` (they contain buyer account IDs / license ARNs).
- **Public registration API:** intentionally open (Marketplace POSTs the token unauthenticated) → template attaches a baseline WAF WebACL by default (rate-based + common-exploit; `WebAclArn` overrides); API Gateway throttling + access logging always on; register Lambda returns security headers and persists ONLY an allowlist of length-bounded fields (`AllowedRegistrationFields`).
- **Credentials (ephemeral-first):** SSO → `sts assume-role`; no long-lived keys, don't ask for keys first. Deployer role uses a conditioned trust policy (not open `:root`) + permissions-boundary-bounded `iam:CreateRole`.
- **Stage name:** `StageName` has no default + an `AllowedPattern` rejecting empty; mandatory questionnaire answer; `sam deploy` and `deploy.sh` fail fast (no `prod` fallback).
- **Event scoping:** EventBridge rule scoped to `source: ["aws.agreement-marketplace"]`; the EventBridge→SQS policy via `aws:SourceArn`.
- **Data classification:** customer AWS account IDs + agreement metadata are sensitive — avoid logging full identifiers; encrypt log groups that contain them.
