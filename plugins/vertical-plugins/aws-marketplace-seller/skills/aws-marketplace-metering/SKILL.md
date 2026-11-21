---
name: aws-marketplace-metering
description: Deploys, queries, and debugs AWS Marketplace SaaS usage-based (PAYG) metering pipelines (`BatchMeterUsage`, `ResolveCustomer`, Concurrent Agreements `CustomerAWSAccountId` + `LicenseArn`, VMT `usageAllocations`, EventBridge `License Updated` / `License Deprovisioned` flush, CloudTrail `metering-marketplace.amazonaws.com` Event History <=90d, and Seller Reports / SDDS reconciliation). Covers `DuplicateRecord`, `CustomerNotSubscribed`, `UnprocessedRecords`, `InvalidLicenseException`, `TimestampOutOfBoundsException`, `TooManyTags`, and `DisabledApiException`. Query live AWS state via MCP tools only (never raw aws CLI).
version: 1
---

# AWS Marketplace Metering (SaaS Usage-Based / PAYG)

Complete lifecycle management for **AWS Marketplace SaaS usage-based (PAYG) metering**:
- **Setup (SaaS PAYG):** Two-stack serverless SAM architecture (`awsmp-events-stack` in `us-east-1` + `awsmp-<productCode>-metering` per metering region) using `ResolveCustomer`, `BatchMeterUsage`, DynamoDB (`metering_pending` sparse GSI), SQS, and EventBridge.
- **Query & Debug:** Inspect recent metering submissions via regional **CloudTrail Event History** (`<= 90` days, `eventSource = metering-marketplace.amazonaws.com` — **never CloudTrail Lake**) and reconcile billed revenue via **Seller Reports / AMMP Billed Revenue dashboard / SDDS**.

> **Mandatory Production Review Gate:** Every generated SAM template, Lambda handler, IAM policy, and deployment plan is a proposal requiring seller code review, change management, and full execution of [`references/test-plan.md`](references/test-plan.md) before carrying production billing traffic.
> **MCP-Only Live Execution:** Execute all live AWS discovery and CloudTrail/Catalog inspections (`marketplace-catalog`, `cloudtrail`, `dynamodb`, `cloudwatch`) strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `awsknowledge`, `awsiac`, `cloudwatch`) — never run raw `aws` CLI commands in shell.

## Reference Map (Load Before Detailed Setup or Troubleshooting)

- **Complete Setup Questionnaire (Q1–Q10), Event Lifecycle & Query/Reject Tables:** [`references/metering-complete-reference.md`](references/metering-complete-reference.md)
- **Setup & Writer Contract / VMT / Guardrails:** [`references/setup-path.md`](references/setup-path.md) · [`references/client-side-guardrails.md`](references/client-side-guardrails.md) · [`references/deployment-steps.md`](references/deployment-steps.md)
- **Concurrent Agreements & Architecture:** [`references/concurrent-agreements.md`](references/concurrent-agreements.md) · [`references/architecture.md`](references/architecture.md) · [`references/scalable-metering-design.md`](references/scalable-metering-design.md)
- **Existing / Legacy Sellers & Registration UI:** [`references/existing-sellers.md`](references/existing-sellers.md) · [`references/registration-page.md`](references/registration-page.md) · [`references/iam-credentials.md`](references/iam-credentials.md)
- **Querying, Seller Reports & Monitoring:** [`references/query-path.md`](references/query-path.md) · [`references/query-patterns.md`](references/query-patterns.md) · [`references/seller-reports.md`](references/seller-reports.md) · [`references/troubleshooting.md`](references/troubleshooting.md) · [`references/test-plan.md`](references/test-plan.md)

## Out-of-Scope Boundaries (Decline & Redirect Cleanly)

This skill covers **SaaS Usage-Based (PAYG)** metering only. When asked about out-of-scope models, state clearly that it is outside SaaS PAYG metering scope and redirect:
- **SaaS Contract / Contract with Consumption Pricing (CCP)** (included units + overage billing, annual contract terms, or renewals) → SaaS Contract / Entitlements (`GetEntitlements`) in public AWS Marketplace docs (or `aws-marketplace-catalog-and-listings` / `aws-marketplace-private-offers-and-agreements`).
- **Flat-rate SaaS Subscriptions with NO usage metering** ("how do I check active customers?") → `GetEntitlements` + subscription lifecycle events in public docs.
- **Metered AMI / Container (`MeterUsage` / `RegisterUsage`)** → Out of scope for this SaaS PAYG pipeline; note the **opposite region rule**: AMI/Container `MeterUsage` **must** run in the **same region** as the EC2 instance / ECS task / EKS pod (authenticating via IAM instance/task role or Pod Identity/IRSA, never static keys), or it fails with **`InvalidEndpointRegionException`**.
- **Forecasting future bills/usage** → This skill queries historical submissions (`<= 90d` CloudTrail) and recommends Seller Reports/SDDS for historical billed data; hand fetched data to the host analytics layer for forecasting.
- **Discounts / Private Offers** → Managed in **AWS Marketplace Management Portal (AMMP)** (`aws-marketplace-private-offers-and-agreements`); CloudTrail shows raw metered quantities whereas Seller Reports show post-discount billed revenue.

## Critical Facts & Invariants (Apply to ALL Metering Operations)

1. **Concurrent Agreements (CA) Identity & Partition Key (`licenseArn`):**
   - All new SaaS products use **`CustomerAWSAccountId` + `LicenseArn`** per `UsageRecord` (`CustomerIdentifier` is deprecated and `null` for new CA integrations).
   - **`ResolveCustomer` DOES return top-level `LicenseArn`** alongside `customerAWSAccountId` and `productCode` from `x-amzn-marketplace-token`. It is a **regional** API (seller's choice of region, independent of `BatchMeterUsage` region) and **must** be called from the publishing AWS account.
   - **`x-amzn-marketplace-token` is REUSABLE for ~4 hours** (not one-time-use); after ~4h it raises `ExpiredTokenException` (buyer re-clicks *"Set up your account"* without resubscribing; malformed/invalid tokens raise `InvalidTokenException`).
   - **Metering is attributed PER LICENSE (`licenseArn`), never collapsed per account:** both the `us-east-1` PII-free `subscribers` table (`PK: licenseArn, SK: customerAWSAccountId`) and in-region `usage` table (`PK: licenseArn, SK: customerAWSAccountId#dimension#timestamp`) key on `licenseArn` for **three reasons**: (1) one buyer AWS account can hold multiple concurrent agreements/licenses for the same product; (2) keying by `customerAWSAccountId` would collapse distinct agreements and cause lost/double billing; (3) each license has independent lifecycle and `CustomerAWSAccountId + LicenseArn + dimension + hour` idempotency.
   - **One Product per `BatchMeterUsage` Call:** Every `UsageRecord` (`LicenseArn`) in a single `BatchMeterUsage` call **must belong to the same product**; mixing two products raises request-level **`InvalidLicenseException`** failing the entire batch.
2. **PII Separation (`customer-profile` vs `subscribers`):**
   - Buyer registration/KYB PII (`AllowedRegistrationFields`) is stored **only** in the **in-region `awsmp-<productCode>-customer-profile` table** (`PK: licenseArn, SK: customerAWSAccountId`, always upserted; missing `CUSTOMER_PROFILE_TABLE` env var fails loud with HTTP `500`).
   - The shared **`us-east-1` `subscribers` table is strictly PII-free** (stores only `licenseArn`, `customerAWSAccountId`, `agreementId`, `productCode`, `agreementStatus`, `subscriptionStatus`, `deprovisioningExpiry`, idempotent reference-only `registeredRegions`, and `createdAt`/`updatedAt` audit stamps).
3. **SaaS `BatchMeterUsage` Region Rule vs `DisabledApiException`:**
   - SaaS `BatchMeterUsage` is regional (seller chooses the region where usage occurs; deploy a main stack per metering region; dedup is per region). There is **NO `InvalidEndpointRegionException`** on SaaS `BatchMeterUsage`; unsupported commercial regions return **`DisabledApiException`**.
4. **24-Hour Timestamp Window, `MeteringLockHours`, & Age-Out:**
   - `BatchMeterUsage` accepts timestamps up to **24 hours** old (`now - 24h`; e.g., a **30-hour-old** record is **rejected**, never submitted — only exception is the 6-hour month-boundary grace until `06:00 UTC` on the 1st for previous-month records). Best practice: submit within ~1 hour of generation in whole-second **UTC**.
   - **In-progress current hour is NEVER metered on the normal path:** the pipeline processes only completed hours (`now-23h ... now-1h`) **oldest-first** via paginated `Query` on the sparse **`metering_pending` GSI** (`HASH: meteringPending` `YYYY-MM-DDTHH`, `RANGE: licenseArn`, projecting `customerAWSAccountId` + `dimension`; never `Scan` and never querying `subscribers` to find usage), gated by `MeteringLockHours` (`1..20`, default `1`). A mis-stamped `meteringPending` attribute is the one writer bug the pipeline cannot auto-detect.
   - Records aging past 24h transition to terminal **`AggregationExpired`** or **`SubmissionExpired`**, **clear `meteringPending`** (dropping off the sparse GSI so they don't loop forever), and fire `UsageAggregationExpired` / `UsageSubmissionExpired` alarms.
   - If a ~1-hour-old record hits `TimestampOutOfBoundsException`, suspect **(a) a co-batched poison record failing the whole call** or **(b) writer clock skew / non-UTC timestamps** — bisect the batch and check NTP.
5. **EventBridge Subscription & Deprovisioning Flush Lifecycle (`us-east-1` Events Stack):**
   - Two independent statuses on `subscribers`: **`agreementStatus`** (`active` | `inactive`) and **`subscriptionStatus`** (`active` | `deprovisioning` | `inactive` — no `deprovisioned` value). Metering follows **license `subscriptionStatus`**.
   - **`License Updated`** (`source: ["aws.agreement-marketplace"]` in `us-east-1`) → upserts subscriber with `agreementStatus=active` and `subscriptionStatus=active`. Eligibility is enforced server-side by `BatchMeterUsage` at submit time regardless of event arrival order.
   - **`License Deprovisioned`** → sets `subscriptionStatus=deprovisioning` + `deprovisioningExpiry` (`~1h`), opening the **license-scoped final-usage flush**: bypasses `MeteringLockHours` and **meters both completed hours AND the current in-progress hour immediately for that deprovisioning license ONLY** (never force-flushing other active buyers). After expiry, `deprovision-cleanup` (`rate(15m)`) sets `subscriptionStatus=inactive`.
   - **`Purchase Agreement Ended`** → sets `agreementStatus=inactive` ONLY (does NOT stop metering or trigger the flush; **`License Deprovisioned`** opens the flush). `Purchase Agreement Created` is not consumed by metering.
6. **Batch Caps, Serial Submitter Concurrency, & Retry Semantics:**
   - **Two independent `BatchMeterUsage` caps:** **`<= 25` `UsageRecords` AND `<= 1 MB` serialized payload** (large VMT `usageAllocations` can breach `1 MB` below 25 records — split into smaller batches).
   - **Decoupled serial submitter:** `submitter` runs with **`ReservedConcurrentExecutions=1`** to stay safely below the **`10 req/s`** regional `BatchMeterUsage` quota (`discoverer` = `30`; `aggregator`/`cleanup` use SQS `MaximumConcurrency`). On `ThrottlingException`, retry with **exponential backoff + JITTER**.
7. **Three Distinct Outcome Classes & Paired Client/Server Reject Codes (Always Name Both):**
   - **Per-record `Results[].Status` (terminal, do NOT blindly retry):**
     - `Success` — accepted and billed.
     - `DuplicateRecord` — **first-write-wins** (`CustomerAWSAccountId + LicenseArn + dimension + hour`, per region); original quantity stays billed. Safe for identical retries on throttled/unprocessed records, **never** to update a quantity (differing-quantity resubmit causes **under-billing**, never call it "benign").
     - `CustomerNotSubscribed` — invalid ID, ended agreement, or suspended buyer; **do NOT retry**.
   - **Partial-batch `UnprocessedRecords` (transient, NOT billed, safe to retry):** submitter retries **once** immediately, then leaves remaining records for the next `rate(5m)` scheduled run and alarms via **`UsageRecordUnprocessed`** (does not raise a Lambda `Errors` exception).
   - **Request-level exceptions (fail the ENTIRE `BatchMeterUsage` batch; isolated via bounded bisection `ceil(log2(25)) = 5`) paired with pre-API `RejectedClientSide` (`UsageRecordRejected`) reason codes:**
     - `MalformedTimestamp` / `TimestampOutOfWindow` ↔ **`TimestampOutOfBoundsException`**
     - `InvalidLicenseArn` ↔ **`InvalidLicenseException`**
     - `TooManyTags` ↔ **`TooManyTagsException`** (**max 5 VMT `usageAllocations` tags** per `UsageRecord`)
     - `InvalidDimension` / `UnknownDimension` ↔ **`InvalidUsageDimensionException`** (dimension validity is server-authoritative & case-sensitive; validate names upfront via `marketplace-catalog:DescribeEntity` in `us-east-1`)
     - Pre-API-only VMT/schema guardrails: `MalformedSortKey` / `SortKeyMismatch`, `MissingDimension`, `NegativeQuantity`, `NonIntegerQuantity`, **`MixedAllocatedAndUnallocated`** (VMT is **all-or-nothing** across non-zero rows within a `(licenseArn, account, dimension, hour)` group), `AllocationSumMismatch`, `TooManyAllocations` (`> 2,500` tag-sets).
8. **Setup Gates, IAM Namespace, & Query Source Boundaries:**
   - **Setup Gates:** Ephemeral credentials (`sts:AssumeRole`/SSO, never static keys) → `DescribeEntity` product-type gate (`SaaSProduct` + `ExternallyMetered`) → visibility gate (direct-deploy main stack only when `Limited`, never `Published`; never mutate an existing shared `awsmp-events-stack`; existing stacks require diff + explicit seller approval; `StageName` has **no default / no `prod` fallback**; `MeteringMode=dry-run` for sandboxes). See [`references/metering-complete-reference.md`](references/metering-complete-reference.md) for Q1–Q10 (`full` vs `direct-submit` finalize-before-insert, `USAGE_TABLE_TTL_DAYS` vs `AGGREGATED_USAGE_TTL_DAYS`).
   - **IAM Namespace:** `aws-marketplace:BatchMeterUsage`, `aws-marketplace:ResolveCustomer`, `aws-marketplace:GetSellerDashboard` (**`aws-marketplace:*`**, NEVER `meteringmarketplace:*`), scoped DynamoDB GSI `Query` (no `dynamodb:Scan`), explicit KMS/retention on logs, and baseline WAF + throttling on the public registration API.
   - **Query & Billing Source Truth:** CloudTrail Event History (`<= 90d`, regional, lowercase `results`/`status`/`unprocessedRecords` in `responseElements`) shows **submissions only** (not revenue; check `complete`/`truncated`/`windowClipped`). **NEVER recommend CloudTrail Lake (`create-event-data-store`).** Authoritative billed/disbursed revenue and `> 90d` billed history come from **Seller Reports / AMMP Billed Revenue dashboard / SDDS** (push-only, enrollment-forward, never `GenerateDataSet`); for `> 90d` raw submission retention, export a plain **CloudTrail trail → S3 + Athena** (never Lake).
