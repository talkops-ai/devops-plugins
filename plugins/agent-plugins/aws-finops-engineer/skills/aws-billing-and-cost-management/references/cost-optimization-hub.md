# Cost Optimization Hub & Compute Optimizer Automation

Cost Optimization Hub (COH) (`billing:cost-optimization`) is the **recommended starting point** for finding savings. It consolidates and de-duplicates recommendations from multiple sources (Compute Optimizer, Cost Explorer rightsizing, Savings Plans, Reserved Instances, idle resources) into a single prioritized view with estimated savings at **$0.00 API cost**.

## Why Start Here

- **De-duplication:** A single EC2 instance may appear in Compute Optimizer (right-size), Cost Explorer (RI recommendation), AND idle resource detection. COH consolidates these into one recommendation with the highest-impact action (`include_all_recommendations=False`).
- **Prioritization:** Recommendations ranked by estimated monthly savings across all services and recommendation types.
- **Efficiency Metrics:** Track organization-wide optimization efficiency over time via `list_efficiency_metrics`.

## MCP & CLI Commands (`billing:cost-optimization`)

```bash
# List recommendation summaries grouped by resource type or action type
aws cost-optimization-hub list-recommendation-summaries \
  --group-by ResourceType

aws cost-optimization-hub list-recommendation-summaries \
  --group-by ActionType

# List efficiency metrics over time
aws cost-optimization-hub list-efficiency-metrics \
  --granularity MONTHLY \
  --time-period '{"start":"2026-01-01T00:00:00Z","end":"2026-04-01T00:00:00Z"}'

# List recommendations sorted by savings (highest first)
aws cost-optimization-hub list-recommendations \
  --order-by '{"dimension":"EstimatedMonthlySavings","order":"Desc"}' \
  --max-results 20

# Get details for a specific recommendation
aws cost-optimization-hub get-recommendation \
  --recommendation-id <id>

# Filter by resource type
aws cost-optimization-hub list-recommendations \
  --filter '{"resourceTypes":["Ec2Instance"]}'
```

## boto3 / MCP Parameter Syntax

Parameter **values and inner key names** are the same for CLI and boto3 (top-level parameter names differ — CLI uses kebab-case like `--order-by`, boto3/MCP uses `order_by` / `orderBy`):

```python
# List recommendation summaries
# groupBy valid values: AccountId, Region, ActionType, ResourceType,
#   RestartNeeded, RollbackPossible, ImplementationEffort
client.list_recommendation_summaries(groupBy='ResourceType')

# List recommendations sorted by savings
# orderBy.dimension: EstimatedMonthlySavings, EstimatedSavingsPercentage
# orderBy.order: Asc, Desc (case-sensitive — "DESC" will fail)
client.list_recommendations(
    orderBy={'dimension': 'EstimatedMonthlySavings', 'order': 'Desc'},
    maxResults=20
)

# Filter by resource type
client.list_recommendations(
    filter={'resourceTypes': ['Ec2Instance']},
    maxResults=20
)

# Get details for a specific recommendation
client.get_recommendation(recommendationId='<id>')
```

**Common mistakes agents make with COH:**

- Using `RecommendationType` as `groupBy` (not a valid value — use `ResourceType` or `ActionType`)
- Using `CostReduction` as `orderBy` dimension (not valid — use `EstimatedMonthlySavings`)
- Using `DESC`/`ASC` instead of `Desc`/`Asc` (case-sensitive)
- Calling non-existent operations like `get_savings_summary` or `describe_recommendations`

## Recommendation Types

| Type | Source | What It Finds |
|------|--------|--------------|
| Rightsizing | Compute Optimizer | Over/under-provisioned EC2, ASG, Lambda, EBS, ECS, RDS/Aurora |
| Idle resources | Compute Optimizer / Cost Explorer | EC2, EBS, ELB, RDS, NatGateway with near-zero utilization |
| Savings Plans | Cost Explorer | Compute, EC2 Instance, Database, and SageMaker SP recommendations |
| Reserved Instances | Cost Explorer | EC2, RDS, ElastiCache, Redshift, OpenSearch, MemoryDB, DynamoDB RI recommendations |
| Graviton migration | Compute Optimizer | x86 → `arm64` opportunities across EC2, RDS, Lambda, ECS |
| EBS optimization | Compute Optimizer | `gp2`→`gp3`, `io1`→`io2` migrations and unattached volumes |

## Filtering and Action Types

**Action types** (valid values for `filter.actionTypes`):
`Rightsize`, `Stop`, `Upgrade`, `PurchaseSavingsPlans`, `PurchaseReservedInstances`, `MigrateToGraviton`, `Delete`, `ScaleIn`

**Implementation effort levels** (valid values for `filter.implementationEfforts`):
`VeryLow`, `Low`, `Medium`, `High`, `VeryHigh`

**Resource types** (valid values for `filter.resourceTypes`):
`Ec2Instance`, `Ec2AutoScalingGroup`, `EbsVolume`, `LambdaFunction`, `EcsService`, `RdsDbInstance`, `RdsDbInstanceStorage`, `ComputeSavingsPlans`, `Ec2InstanceSavingsPlans`, `SageMakerSavingsPlans`, `Ec2ReservedInstances`, `RdsReservedInstances`, `OpenSearchReservedInstances`, `RedshiftReservedNodes`, `ElastiCacheReservedNodes`, `MemoryDbReservedInstances`, `DynamoDbReservedCapacity`, `AuroraDbClusterStorage`, `NatGateway`

## Idle vs Overprovisioned — Do NOT Confuse

**Idle resources** = near-zero utilization, safe to stop/delete (after snapshot/verification). Action types: `Stop`, `Delete`.
**Overprovisioned resources** = actively used but larger than needed, should be rightsized after Two-Key CloudWatch P95/P99 verification. Action type: `Rightsize`.

When a user asks "what idle resources can I terminate?" — only include `Stop` and `Delete` action types. Do NOT include `Rightsize` recommendations — those resources are still in use.

## Compute Optimizer Detailed Operations (`billing:compute-optimizer`)

For deeper per-resource technical options and utilization percentiles beyond COH summaries, use `billing:compute-optimizer`:

```python
# Check enrollment first
client.get_enrollment_status()

# Per-resource-type operations (service: compute-optimizer)
client.get_ec2_instance_recommendations(instanceArns=[...], filters=[...])
client.get_auto_scaling_group_recommendations(autoScalingGroupArns=[...])
client.get_ebs_volume_recommendations(volumeArns=[...])
client.get_lambda_function_recommendations(functionArns=[...])
client.get_rds_database_recommendations(resourceArns=[...])
client.get_ecs_service_recommendations(serviceArns=[...])

# Filters accept finding types: Underprovisioned, Overprovisioned, Optimized, NotOptimized
# Recommendation preferences: cpuVendorArchitectures=['AWS_ARM64'] for Graviton, ['CURRENT'] for same arch
```

## Compute Optimizer Automation (`billing:compute-optimizer-automation`)

AWS Compute Optimizer Automation schedules recurring rules (e.g., snapshotting and deleting unattached EBS volumes, deleting aged snapshots, or upgrading EBS volumes):
1. Call `get_enrollment_configuration` to check if Automation is enabled.
2. Call `list_automation_rules` and `list_automation_rule_preview_summaries` (or `list_automation_rule_preview`) to see which resources match active/proposed automation rules and their monthly savings.
3. Call `list_recommended_actions` and `list_automation_events` to audit immediate automation-eligible actions and execution history.

## De-duplication of Savings Estimates

COH de-duplicates savings across overlapping recommendation types. A single EC2 instance may have recommendations for rightsizing, Savings Plans, Reserved Instances, AND Graviton migration — but implementing one changes the savings from the others.

- `list_recommendation_summaries` returns per-group `estimatedMonthlySavings` that are **NOT de-duped across groups** when overlapping — summing them across mutually exclusive categories can overcount.
- The same response includes `estimatedTotalDedupedSavings` at the top level — this IS the de-duped total. **Always use `estimatedTotalDedupedSavings` for total savings.**
- `list_recommendations` with `includeAllRecommendations=False` (default) returns only the top recommended action per resource; setting `includeAllRecommendations=True` returns mutually exclusive alternatives that must **never** be summed together.
- When recommendations spill into a local SQLite table (`table_name`), aggregate them deterministically via `billing:session-sql` (see [`deterministic-calculations.md`](./deterministic-calculations.md)).

## Workflow

1. **Start with COH (`billing:cost-optimization`)** to get the prioritized, de-duplicated list of all savings opportunities.
2. **For deeper analysis and Two-Key telemetry validation** on a specific recommendation, use `billing:compute-optimizer` + `cloudwatch:get_metric_data`:
   - EC2 rightsizing details → [`ec2-rightsizing.md`](./ec2-rightsizing.md)
   - EBS volume optimization → [`ebs-optimization.md`](./ebs-optimization.md)
   - RDS / Aurora optimization → [`rds-optimization.md`](./rds-optimization.md)
   - Lambda memory & SnapStart optimization → [`lambda-optimization.md`](./lambda-optimization.md)
   - SP purchase analysis → [`savings-plans.md`](./savings-plans.md)
   - RI purchase analysis → [`reserved-instances.md`](./reserved-instances.md)
3. **Calculate savings** using `billing:session-sql` or a Python script (see [`deterministic-calculations.md`](./deterministic-calculations.md)) — NEVER sum savings estimates manually.

## Gotchas

- COH requires opt-in: `aws cost-optimization-hub update-enrollment-status --status Active`
- COH is available in `us-east-1` only
- Recommendations refresh approximately every 24 hours
- Check `get_preferences` (`savings_estimation_mode`: `BEFORE_DISCOUNTS` vs `AFTER_DISCOUNTS`) to confirm whether savings reflect On-Demand or net-of-discount rates
- COH does NOT include architectural optimizations (S3 lifecycle rules, CloudWatch log retention/IA class, NAT Gateway endpoints, Bedrock prompt caching, Aurora I/O-Optimized break-even) — see [`service-optimization.md`](./service-optimization.md) and [`rds-optimization.md`](./rds-optimization.md) for those
