---
name: aws-marketplace-private-offers-and-agreements
description: "Create and manage AWS Marketplace Private Offers, Channel Partner Private Offers (CPPO), Flexible Payment Scheduler (FPS), Agreement API queries, and Seller Data Feeds (Commerce Analytics / CFT / S3 revenue and disbursement reporting)."
---

# AWS Marketplace Private Offers, Agreements & Seller Reporting

Use this skill to automate AWS Marketplace **Private Offers**, **Channel Partner Private Offers (CPPO)**, **Agreement API (`marketplace-agreement`)** lifecycle inspection, and **Seller Data Feeds** for revenue/disbursement reconciliation.

## 1. Programmatic Private Offers via Catalog API

Private Offers are `Offer` entities in the `AWSMarketplace` catalog (`us-east-1`). Creating and publishing a Private Offer requires a single atomic `StartChangeSet` containing modular offer change types:

1. **`CreateOffer`**: Associates the new offer with `ProductId`.
2. **`UpdateInformation`**: Sets offer `Name`, `Description`, and internal seller notes.
3. **`UpdateTargeting`**: Restricts the offer to specific `PositiveTargeting.BuyerAccounts` (12-digit AWS account IDs).
4. **`UpdatePricingTerms`**:
   - `ConfigurableUpfrontPricingTerm` (contract dimensions & unit prices)
   - `UsageBasedPricingTerm` (custom rate cards for metered dimensions)
   - `PaymentScheduleTerm` (**Flexible Payment Scheduler / FPS** — custom invoice dates and installment amounts across multi-year deals)
5. **`UpdateLegalTerms`**: Attaches **Standard Contract for AWS Marketplace (SCMP)**, Enterprise Contract (ECMP), or custom EULA S3 document.
6. **`UpdateValidityTerms`**: Sets `AgreementDuration` (e.g., `P12M`, `P36M`) or explicit start/end dates.
7. **`UpdateAvailability`**: Sets the `AvailabilityEndDate` (offer expiration date by which the buyer must accept).
8. **`ReleaseOffer`**: Publishes the Private Offer to the targeted buyer accounts.

## 2. Inspecting Active Contracts via Agreement API (`marketplace-agreement`)

Use `aws marketplace-agreement` (`us-east-1`) to inspect accepted offers, renewal dates, and payment schedules:

```bash
# Search agreements where you are the Proposer (Seller)
aws marketplace-agreement search-agreements \
  --catalog AWSMarketplace \
  --filters name=PartyType,values=Proposer name=AgreementType,values=PurchaseAgreement \
  --region us-east-1

# Inspect agreement terms (pricing, payment schedule, legal, renewal, validity)
aws marketplace-agreement get-agreement-terms \
  --agreement-id <agmt-id> \
  --region us-east-1
```

## 3. Seller Data Feeds & Financial Reconciliation

AWS Marketplace delivers daily/monthly seller datasets to an encrypted S3 bucket via **AWS Marketplace Seller Data Feeds**:
- **Key Feeds**: `BillingEventFeed_v1` (invoices, adjustments, disbursements), `CustomerSubscriberHourlyMonthlySubscriptions_v1`, `SalesCompensationSummary_v1`, `TaxItemsSummary_v1`.
- **Analytics Pattern**: Register the Seller Data Feed S3 prefix in **AWS Glue Data Catalog** and query with **Amazon Athena** partitioned by `year`/`month` to track Net Revenue, AWS Listing Fees, CPPO partner margins, and uncollected disbursements.
