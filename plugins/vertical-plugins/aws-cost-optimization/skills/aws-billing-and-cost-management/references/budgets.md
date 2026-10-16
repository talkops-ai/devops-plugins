# AWS Budgets & Automated Spend Guardrails (`billing:budgets`)

> **Pricing note:** All prices shown are approximate as of early 2026 and may change. Always verify current pricing before reporting to users.

## The 4-Tier Enterprise Budget Architecture

Call `billing:budgets` (`describe_budgets`) to audit existing budget coverage. Every production AWS environment should maintain four distinct classes of budgets:

| Budget Type | Recommended Scope | Notification Thresholds | Purpose & Escalation |
|------|----------|---|---|
| **`COST`** | Organization Total, per Member Account, per Billing View, and per Business Unit (Cost Category / Tag) | `50% ACTUAL`, `80% ACTUAL`, **`100% FORECASTED`**, `100% ACTUAL` | Catches spend trajectory breaches early via ML `FORECASTED` alerts before month-end. |
| **`SAVINGS_PLANS_UTILIZATION` & `SAVINGS_PLANS_COVERAGE`** | Payer / Commitment Management Account | Utilization **`< 95% ACTUAL`**; Coverage **`< 75% ACTUAL`** | Alerts FinOps immediately if a workload migration strands a Savings Plan or new On-Demand scale dilutes coverage. |
| **`RI_UTILIZATION` & `RI_COVERAGE`** | Payer Account (RDS, ElastiCache, Redshift, OpenSearch, EC2) | Utilization **`< 95% ACTUAL`** | Triggers RI size/AZ modification or workload alignment before monthly commitment waste accumulates. |
| **`USAGE`** | High-velocity usage types (`NatGateway-Bytes`, `DataTransfer-Out-Bytes`, S3 requests) | `80% ACTUAL`, `100% FORECASTED` | Detects runaway network or request loops independent of dollar discounts. |

---

## Create Budget with Multi-Stage Alerts (Reference / Hand-Off Snippet)

*(Remember: `aws-finops-engineer` is read-only against live AWS accounts; generate validated CLI or CloudFormation (`AWS::Budgets::Budget` via `awsiac`) for the user or `aws-iac-engineer` to apply.)*

```bash
aws budgets create-budget --region us-east-1 \
  --account-id 123456789012 \
  --budget '{"BudgetName":"Monthly-Total","BudgetLimit":{"Amount":"1000","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST","CostTypes":{"UseAmortized":true,"IncludeCredit":false,"IncludeRefund":false}}' \
  --notifications-with-subscribers '[
    {"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"},"Subscribers":[{"SubscriptionType":"EMAIL","Address":"team@example.com"}]},
    {"Notification":{"NotificationType":"FORECASTED","ComparisonOperator":"GREATER_THAN","Threshold":100,"ThresholdType":"PERCENTAGE"},"Subscribers":[{"SubscriptionType":"SNS","Address":"arn:aws:sns:us-east-1:123456789012:budget-alerts"}]}
  ]'
```

- Set `"UseAmortized": true`, `"IncludeCredit": false`, and `"IncludeRefund": false` in `CostTypes` so operational budgets track true amortized usage without being distorted by upfront RI/SP fees or temporary credits.
- Each threshold is a separate entry in `NotificationsWithSubscribers`. Do NOT put multiple thresholds in one notification object.

## Tag-Based, Cost-Category & Billing-View Budgets

Use `CostFilters` with `TagKeyValue` (`tag-key$tag-value`), `CostCategory`, or scope the budget to a `BillingViewArn`:

```json
"CostFilters": {
  "TagKeyValue": ["user:Environment$production"],
  "CostCategory": ["BusinessUnit$Payments"]
}
```

## Budget Actions (Automated Sandbox Quarantine)

Automatically apply IAM deny policies or Organizations Service Control Policies (SCPs) when a threshold (e.g., `100% ACTUAL` in a non-production sandbox account) is breached, or route SNS notifications to AWS Chatbot (Slack / Microsoft Teams) or EventBridge.
- Budget Actions cannot directly stop EC2/RDS instances — use an EventBridge / SNS → Lambda automation rule (or hand off to `aws-serverless-engineer`) for automated off-hours or threshold shutdowns.

## Gotchas

- **Budgets API requires `us-east-1` region** for global billing data.
- Monitoring-only budgets (no Budget Actions) are **free** — unlimited.
- First 2 action-enabled budgets per account are free; additional action-enabled budgets cost **$0.10/day (~$3.00/month)** each.
- Budget Reports cost **$0.01 per report delivered**.
- Budget alerts evaluate ~1–4 times per day (following Cost Explorer refresh) — not real-time sub-minute telemetry (pair with CloudWatch metric alarms on high-velocity metrics like NAT Gateway `BytesOutToDestination` or Bedrock `InputTokenCount` for real-time circuit breaking).
- `FORECASTED` alerts require ~5 weeks of historical spend data in the account before Cost Explorer's ML forecast engine can generate predictions.
- RI/SP utilization budgets default to 100% — set threshold to **`95%` (or `90%`)** with `ComparisonOperator="LESS_THAN"` for practical alerting.
