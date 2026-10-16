---
name: aws-marketplace-saas-architecture
description: "Design and deploy end-to-end AWS Marketplace SaaS and Container control planes: tenant registration landing pages, Step Functions onboarding workflows, DynamoDB tenant-to-CustomerIdentifier mapping, and least-privilege IAM roles for EKS Pod Identity, ECS Task Roles, and Lambda."
---

# AWS Marketplace SaaS & Container Control Plane Architecture

Use this skill when architecting or troubleshooting the infrastructure required to sell a SaaS or Container product on AWS Marketplace.

## Reference Control Plane Architecture

1. **Fulfillment & Registration Endpoint (API Gateway + Lambda or ALB + ECS)**:
   - Receives `POST` with form-urlencoded `x-amzn-marketplace-token`.
   - Calls `meteringmarketplace:ResolveCustomer` to obtain `CustomerIdentifier`, `CustomerAWSAccountId`, and `ProductCode`.
   - Redirects buyer to your SaaS sign-up/SSO linking page with a short-lived signed session token.
2. **Tenant Onboarding State Machine (AWS Step Functions + DynamoDB)**:
   - Stores `{ CustomerIdentifier, CustomerAWSAccountId, ProductCode, TenantId, SubscriptionStatus, EntitlementDimensions }` in a `MarketplaceTenants` DynamoDB table with a GSI on `TenantId`.
   - Subscribes an SQS queue (with DLQ) to the AWS Marketplace-provided `aws-mp-subscription-notification` and `aws-mp-entitlement-notification` SNS topics.
3. **Hourly Metering Aggregator (EventBridge Scheduler + Lambda)**:
   - Runs every hour (`rate(1 hour)`), aggregates tenant usage from your application telemetry store, and submits batches of up to 25 records via `meteringmarketplace:BatchMeterUsage`.
   - Persists `UsageRecordId` and status (`Success`, `CustomerNotSubscribed`, `DuplicateRecord`) for auditability.

## Least-Privilege IAM Policy for SaaS Control Plane

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "MarketplaceSaaSMeteringAndResolve",
      "Effect": "Allow",
      "Action": [
        "aws-marketplace:ResolveCustomer",
        "aws-marketplace:BatchMeterUsage",
        "aws-marketplace:MeterUsage"
      ],
      "Resource": "*"
    },
    {
      "Sid": "MarketplaceEntitlementRead",
      "Effect": "Allow",
      "Action": [
        "aws-marketplace:GetEntitlements"
      ],
      "Resource": "*"
    }
  ]
}
```
