---
name: aws-marketplace-catalog-and-listings
description: "Author, update, and automate AWS Marketplace product listings (SaaS, Container/EKS/ECS, AMI, and GenAI Agent/Model products) using the AWS Marketplace Catalog API (StartChangeSet), SNS entitlement/subscription notifications, and AWS Marketplace Entitlement Service (GetEntitlements)."
---

# AWS Marketplace Catalog & Product Listings

Use this skill when an ISV or seller needs to programmatically manage AWS Marketplace product listings via the **AWS Marketplace Catalog API (`marketplace-catalog`)**, verify customer subscriptions via **AWS Marketplace Entitlement Service (`marketplace-entitlement`)**, or wire up SNS notifications for SaaS/Container onboarding.

## Core Architecture & Service Boundaries

| API / Service | Endpoint Region | Primary Operations | Purpose |
| :--- | :--- | :--- | :--- |
| **Marketplace Catalog API** (`marketplace-catalog`) | `us-east-1` (Required) | `ListEntities`, `DescribeEntity`, `StartChangeSet`, `DescribeChangeSet`, `CancelChangeSet` | Create products, update pricing/dimensions, add AMI/ECR versions, configure SaaS fulfillment URLs, and publish offers |
| **Marketplace Entitlement Service** (`marketplace-entitlement`) | `us-east-1` (Required) | `GetEntitlements` | Verify active customer contract dimensions, seat counts, or tier entitlements for SaaS and Paid Container products |
| **Marketplace Metering Service** (`meteringmarketplace`) | Regional (where workload runs) | `ResolveCustomer`, `MeterUsage`, `BatchMeterUsage`, `RegisterUsage` | Exchange registration tokens (`x-amzn-marketplace-token`) and report hourly consumption |
| **Seller SNS Notifications** | Provisioned by AWS Marketplace | `aws-mp-subscription-notification`, `aws-mp-entitlement-notification` | Asynchronous webhook events for `subscribe-success`, `subscribe-fail`, `unsubscribe-pending`, `unsubscribe-success`, and `entitlement-updated` |

## 1. Managing Products via Catalog API (`StartChangeSet`)

All Catalog API calls **must** target `us-east-1` (`--region us-east-1`). Changes are asynchronous and executed via change sets:

1. **Discover Entity ID & Type**:
   ```bash
   aws marketplace-catalog list-entities \
     --catalog AWSMarketplace \
     --entity-type SaaSProduct \
     --region us-east-1
   ```
   Supported `EntityType` values: `SaaSProduct`, `ContainerProduct`, `AmiProduct`, `MachineLearningProduct`, `Offer`, `ResaleAuthorization`, `Experience`.

2. **Inspect Current Product Details**:
   ```bash
   aws marketplace-catalog describe-entity \
     --catalog AWSMarketplace \
     --entity-id <entity-id> \
     --region us-east-1
   ```

3. **Execute a ChangeSet (`StartChangeSet`)**:
   - Every change entry requires `ChangeType`, `Entity` (`Type` + `Identifier`), and `DetailsDocument` (prefer `DetailsDocument` inline JSON object over escaped string `Details`).
   - Common SaaS/Container change types:
     - `CreateProduct` / `UpdateInformation` (title, description, logo, support, categories)
     - `AddDimension` / `UpdateDimensions` (metered or contract usage dimensions)
     - `AddDeliveryOptions` / `UpdateDeliveryOptions` (SaaS Fulfillment URL, ECR repository + Helm chart / ECS task template, or AMI ID + access role)
     - `UpdateTargeting` (restrict visibility to buyer AWS Account IDs during staging/testing)
     - `ReleaseProduct` (publish limited/public product)

## 2. SaaS Subscription & Entitlement Verification Flow

```
Buyer Clicks "Set Up Your Account" in AWS Marketplace
        │
        ▼ (HTTP POST with x-amzn-marketplace-token)
SaaS Registration Landing Page (API Gateway + Lambda / ALB)
        │
        ├─► 1. meteringmarketplace:ResolveCustomer(RegistrationToken)
        │      Returns: CustomerIdentifier, CustomerAWSAccountId, ProductCode
        │
        ├─► 2. marketplace-entitlement:GetEntitlements(ProductCode, Filter={CUSTOMER_IDENTIFIER: [...]})
        │      Returns: Active contract dimensions, quantities, ExpirationDate
        │
        └─► 3. Persist Tenant Record in DynamoDB + Listen to SNS Topics:
               • aws-mp-entitlement-notification (contract upgrades/renewals)
               • aws-mp-subscription-notification (unsubscribe-pending / unsubscribe-success)
```

### Mandatory Operational Guardrails
1. **Idempotent SNS Handling**: Always re-query `marketplace-entitlement:GetEntitlements` when receiving an `entitlement-updated` SNS message rather than trusting message payload order—SNS messages can arrive out of order or duplicate.
2. **Unsubscribe Grace Period**: On `unsubscribe-pending`, continue accepting final usage batches (`BatchMeterUsage` accepts records up to 6 hours old and during the 1-hour post-unsubscribe window). On `unsubscribe-success`, revoke tenant access and archive data per retention policy.
3. **Zero Hardcoded Product Codes**: Store `ProductCode`, SNS Topic ARNs, and Catalog `EntityId` in AWS Systems Manager Parameter Store or environment variables.
