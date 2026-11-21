---
name: aws-marketplace-private-offers-and-agreements
description: "Create and manage AWS Marketplace Private Offers, Channel Partner Private Offers (CPPO), Flexible Payment Scheduler (FPS), Agreement API queries (SearchAgreements, GetAgreementTerms), and Seller Data Feeds (BillingEventFeed, S3/Glue/Athena revenue and disbursement reporting). Query live AWS state via MCP tools only (never raw aws CLI)."
---

# AWS Marketplace Private Offers, Agreements & Seller Reporting

Use this skill to automate AWS Marketplace **Private Offers**, **Channel Partner Private Offers (CPPO)**, **Agreement API (`marketplace-agreement`)** lifecycle inspection, and **Seller Data Feeds** for revenue/disbursement reconciliation.

> **Global Control-Plane Requirement (`us-east-1` Only):** Both AWS Marketplace Catalog API (`marketplace-catalog`, `Catalog="AWSMarketplace"`) and AWS Marketplace Agreement API (`marketplace-agreement`) are global control-plane APIs hosted **exclusively in `us-east-1`**. Always target `region_name="us-east-1"` via MCP tools (never raw `aws` CLI) and explicitly note this `us-east-1` control-plane requirement in audit summaries even when customer workloads run in other regions (e.g., `ap-south-1` or `eu-west-1`).

## 1. Programmatic Private Offers & Amendments via Catalog API

Private Offers are `Offer` entities in the `AWSMarketplace` catalog (`us-east-1`). Creating and publishing a Private Offer requires a single atomic `StartChangeSet` containing modular offer change types (using intra-changeset `ChangeName` -> `"$NewOffer"` references):

1. **`CreateOffer`** (or **`CreateReplacementOffer`** referencing `AgreementId` for mid-term agreement amendments/upgrades): Associates the offer with `ProductId` (or `ResaleAuthorizationId` for Channel Partner Private Offers / CPPO).
2. **`UpdateInformation`**: Sets offer `Name`, `Description`, and internal seller notes.
3. **`UpdateTargeting`**: Restricts the offer to specific `PositiveTargeting.BuyerAccounts` (12-digit AWS account IDs).
4. **`UpdatePricingTerms`** (and `UpdatePaymentScheduleTerms` where applicable):
   - **`ConfigurableUpfrontPricingTerm`**: Committed contract dimensions/seats & custom unit prices (**use `ConfigurableUpfrontPricingTerm` for seat/tier quantity upgrades and mid-term co-termed amendments**, rather than `FixedUpfrontPricingTerm`, whenever buyers commit to configurable seat/unit quantities).
   - **`UsageBasedPricingTerm`**: Custom rate cards for metered overage dimensions.
   - **`PaymentScheduleTerm`** (**Flexible Payment Scheduler / FPS**): Custom invoice `ChargeDate` and `ChargeAmount` installments across multi-year deals (sum must match total contract value and all `ChargeDate`s must fall within the agreement validity window).
5. **`UpdateLegalTerms`**:
   - **Standard Contract for AWS Marketplace (SCMP / `StandardEula`)**: AWS Marketplace's standardized click-through contract for rapid commercial procurement without legal redlining.
   - **Enterprise Contract for AWS Marketplace (ECMP)**: AWS Marketplace's **pre-negotiated multi-party enterprise contract framework** (with optional enterprise addendum) established between participating ISVs and regulated enterprise buyers (governed at the enterprise program/discovery layer rather than raw redlined EULAs).
   - **Custom Seller EULA (`CustomEula`)**: Custom S3 PDF legal agreement URL uploaded for bespoke redlined deals.
6. **`UpdateValidityTerms`**: Sets `AgreementDuration` (e.g., `P12M`, `P36M`) OR explicit `AgreementStartDate` / `AgreementEndDate`:
   - **Future-Dated Agreements**: Set explicit future `AgreementStartDate` and `AgreementEndDate` so the buyer can accept the Private Offer today while entitlements and billing activate automatically on `AgreementStartDate`.
   - **Mid-Term Co-Termed Upgrades / Amendments**: Read the active contract's `endTime` and remaining installments via `DescribeAgreement` + `GetAgreementTerms`, then submit an amendment/replacement Private Offer (`CreateReplacementOffer` with `AgreementId`) using updated **`ConfigurableUpfrontPricingTerm`** seat quantities, adjusted **`PaymentScheduleTerm`** installments for the remaining balance, and explicit **`AgreementEndDate`** matching the original contract end date (co-terming).
7. **`UpdateAvailability`**: Sets the `AvailabilityEndDate` (offer expiration date by which the buyer must accept).
8. **`ReleaseOffer`**: Publishes the Private Offer to the targeted buyer accounts.

## 2. Inspecting Active Contracts via Agreement API (`marketplace-agreement`)

Use `marketplace-agreement` (`us-east-1` control plane, queried via MCP `call_boto3`) to inspect accepted offers, renewal dates, committed dimensions, and FPS payment schedules:

1. **`SearchAgreements`**: Filter on `catalog="AWSMarketplace"` with `PartyType=["Proposer"]`, `AgreementType=["PurchaseAgreement"]` (plus optional `Status=["ACTIVE"]` and `BeforeEndTime` for expiring-contract renewal radars).
2. **`DescribeAgreement`**: Retrieve top-level contract metadata (`agreementId`, `startTime`, `endTime`, `acceptanceTime`, `acceptor.accountId`, `proposer`, `estimatedCharges`).
3. **`GetAgreementTerms`**: Paginate and inspect all structured term blocks — **`configurableUpfrontPricingTerm`** (committed dimensions/quantities), **`paymentScheduleTerm`** (FPS installment dates & amounts), **`renewalTerm`** (auto-renewal configuration), **`validityTerm`** (`agreementDuration` or `agreementStartDate`/`agreementEndDate`), `usageBasedPricingTerm`, and `legalTerm`.

## 3. Seller Data Feeds & Financial Reconciliation

AWS Marketplace delivers daily/monthly seller datasets to an SSE-KMS encrypted S3 bucket (with `PublicAccessBlock` and TLS-only bucket policy) via **AWS Marketplace Seller Data Feeds**:
- **Core Feeds**: **`BillingEventFeed_v1`** (invoices, AWS listing fees, adjustments, and buyer disbursement events), **`TaxItemFeed_v1`** (`TaxItemsSummary_v1`), **`OfferFeed_v1`**, **`AccountFeed_v1`**, **`ProductFeed_v1`**, **`CustomerSubscriberHourlyMonthlySubscriptions_v1`**, and **`SalesCompensationSummary_v1`**.
- **Analytics Pattern**: Register the Seller Data Feed S3 prefixes in **AWS Glue Data Catalog** partitioned by `year`/`month` and query with **Amazon Athena** to reconcile Gross Billed Revenue, AWS Listing Fees, CPPO partner wholesale payouts/margins, taxes, and disbursed vs uncollected buyer balances.
