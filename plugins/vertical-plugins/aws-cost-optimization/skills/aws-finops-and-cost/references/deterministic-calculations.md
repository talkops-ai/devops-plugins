# Deterministic Financial Calculations (`billing:session-sql` & Python)

**You MUST NEVER perform arithmetic by reasoning in your response.** This includes sums, averages, percentages, percent changes, counts, min/max, Effective Savings Rate (ESR), break-even thresholds, or any math on data from API calls. LLM arithmetic is unreliable and produces wrong cost figures.

**You MUST ALWAYS use either the local SQLite session engine (`billing:session-sql`) or a Python script (`python3 -c`)** to perform calculations and print the result.

---

## Pattern 1: Local SQLite Aggregation (`billing:session-sql` — $0.00 Cost)

When any tool in `awslabs.billing-cost-management-mcp-server` returns a large dataset, it automatically persists the rows into a local in-process SQLite database (`session.db`) and returns a `table_name`. Query that table directly with `billing:session-sql` at **$0.00 AWS cost**:

```sql
-- Summarize deduplicated Cost Optimization Hub recommendations by ActionType and ResourceType
SELECT
  action_type,
  resource_type,
  COUNT(*) AS recommendation_count,
  ROUND(SUM(CAST(estimated_monthly_savings AS REAL)), 2) AS total_monthly_savings_usd,
  ROUND(SUM(CAST(estimated_monthly_cost AS REAL)), 2) AS current_monthly_cost_usd,
  ROUND(
    100.0 * SUM(CAST(estimated_monthly_savings AS REAL))
    / NULLIF(SUM(CAST(estimated_monthly_cost AS REAL)), 0),
    2
  ) AS blended_savings_pct
FROM [table_name]
GROUP BY action_type, resource_type
ORDER BY total_monthly_savings_usd DESC;
```

---

## Pattern 2: Python Script for Cost Explorer MoM Variance

After calling `billing:cost-explorer` or `aws ce get-cost-and-usage`, extract the numbers and calculate with a Python script:

```python
# Example: Calculate total cost and percent change from CE response data
current_month = [("EC2", 1500.42), ("S3", 823.17), ("RDS", 612.90)]
previous_month = [("EC2", 1200.00), ("S3", 750.00), ("RDS", 580.00)]

current_total = sum(cost for _, cost in current_month)
previous_total = sum(cost for _, cost in previous_month)
pct_change = ((current_total - previous_total) / previous_total) * 100

print(f"Current total: ${current_total:,.2f}")
print(f"Previous total: ${previous_total:,.2f}")
print(f"Change: {pct_change:+.1f}%")

for service, cost in current_month:
    pct_of_total = (cost / current_total) * 100
    print(f"  {service}: ${cost:,.2f} ({pct_of_total:.1f}%)")
```

---

## Pattern 3: Effective Savings Rate (ESR) & Commitment Sizing Math

```python
# Calculate Effective Savings Rate (ESR) and post-right-sizing commitment target
on_demand_equivalent_usd = 45000.00
amortized_covered_cost_usd = 24500.00
unused_commitment_fee_usd = 350.00
uncovered_on_demand_usd = 11000.00
stage3_physical_rightsizing_savings_usd = 3200.00

effective_total_usd = amortized_covered_cost_usd + unused_commitment_fee_usd + uncovered_on_demand_usd
esr_pct = (1.0 - (effective_total_usd / on_demand_equivalent_usd)) * 100.0

# Deduct physical right-sizing BEFORE sizing new Savings Plans (target 80% of remaining On-Demand floor)
remaining_uncovered_od_usd = max(0.0, uncovered_on_demand_usd - stage3_physical_rightsizing_savings_usd)
recommended_additional_sp_hourly = (remaining_uncovered_od_usd * 0.80) / 730.0

print(f"Current Effective Savings Rate (ESR): {esr_pct:.2f}%")
print(f"Post-Right-Sizing Uncovered On-Demand: ${remaining_uncovered_od_usd:,.2f}/mo")
print(f"Target Incremental Savings Plan Commitment (80% floor): ${recommended_additional_sp_hourly:.4f}/hr")
```

---

## Pattern 4: Count and Aggregate Budgets

```python
# Example: Count exceeded budgets from Budgets API response
budgets = [("Monthly-Total", "EXCEEDED"), ("Dev-Budget", "OK"), ("Prod-Budget", "EXCEEDED")]
exceeded = [name for name, status in budgets if status == "EXCEEDED"]
print(f"Exceeded budgets: {len(exceeded)} — {', '.join(exceeded)}")
```

## Pattern 5: Right-Sizing Savings Calculation

```python
# Example: Calculate savings from right-sizing recommendations
recs = [
    {"instance": "i-abc123", "current_cost": 121.03, "recommended_cost": 16.64},
    {"instance": "i-def456", "current_cost": 350.00, "recommended_cost": 175.00},
]
total_current = sum(r["current_cost"] for r in recs)
total_recommended = sum(r["recommended_cost"] for r in recs)
total_savings = total_current - total_recommended
pct_savings = (total_savings / total_current) * 100
print(f"Total monthly savings: ${total_savings:,.2f} ({pct_savings:.1f}%)")
print(f"Annual savings: ${total_savings * 12:,.2f}")
```

## Why This Matters

- LLMs frequently make arithmetic errors on multi-digit numbers, especially with percentages and aggregations.
- Cost data involves currency — wrong numbers erode customer trust immediately.
- `billing:session-sql` and Python scripts produce verifiable, reproducible results.
