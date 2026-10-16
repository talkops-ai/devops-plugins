# Savings Plans, Effective Savings Rate (ESR) & Purchase Analyzer

> **Pricing note:** All prices shown are approximate as of early 2026 and may change. Always verify current pricing via `billing:sp-explorer`, `awspricing:get_pricing`, or `billing:aws-pricing` before reporting to users.

## Plan Types

| Type | Discount | Flexibility | Covers |
|------|----------|-------------|--------|
| **Compute SP** | Up to 66% | **Any family, size, region, OS, tenancy** | **EC2, AWS Fargate, AWS Lambda** |
| **EC2 Instance SP** | Up to 72% | Any size, OS, tenancy within **one family + one region** | EC2 only |
| **Database SP** | Up to 35%–55% | Supported DB engines, families, sizes, regions (Provisioned & Serverless) | Aurora, RDS, DynamoDB, ElastiCache, DocumentDB, Neptune, Keyspaces, Timestream, DMS, OpenSearch |
| **SageMaker SP** | Up to 64% | Any family, size, region, component | SageMaker Studio, Training, Real-Time/Async Inference, Batch Transform |

Default recommendation: **Compute SP** for most users. The ~6% discount gap vs. EC2 Instance SP is rarely worth the risk of stranding commitments when migrating instance families (e.g., `m6i` → `m7g`), regions, or moving to Fargate/Lambda.

Default payment: **No Upfront** for first-time buyers to minimize cash lock-in risk.

---

## The Golden Rule: Physical Right-Sizing BEFORE Commitments

**Never size a Savings Plan against unoptimized On-Demand spend.**
1. Sum all physical right-sizing and idle-deletion monthly savings from Compute Optimizer / Cost Optimization Hub (`monthly_physical_savings_usd`).
2. Convert to an hourly On-Demand reduction: `hourly_reduction = monthly_physical_savings_usd / 730.0`.
3. Deduct `hourly_reduction` from the uncovered On-Demand hourly baseline before recommending a commitment purchase (or simulate the exact adjusted hourly commitment in `billing:sp-purchase-analyzer`).

---

## Effective Savings Rate (ESR) — The North-Star Portfolio Metric

Measuring **Utilization %** or **Coverage %** alone can mislead:
- 100% utilization on a tiny `$0.05/hr` SP yields ~0% real discount.
- 100% coverage achieved by over-committing yields negative savings due to `UnusedCommitment`.

Always calculate and report **Effective Savings Rate (ESR)** via `billing:session-sql` or Python:

$$\text{ESR (\%)} = \left(1 - \frac{\text{Amortized Covered Cost} + \text{Unused Commitment Fee} + \text{Uncovered On-Demand Cost}}{\text{Total Public On-Demand Equivalent Cost}}\right) \times 100$$

- **Target Utilization:** `> 95%` (ideally `98%+`)
- **Target Steady-State Coverage:** `75%–85%` of post-right-sizing On-Demand floor

---

## Multi-Horizon Volatility Check & MCP Tool Workflow

### 1. Audit Active Inventory & Expiration Cliffs (`billing:sp-explorer` & `billing:sp-performance`)
- Call `billing:sp-explorer` (`describe_savings_plans`) to list all `active`, `payment-pending` (queued), and `retired` plans. Flag any plan expiring within **60 days** (`end` date) so a queued replacement can be scheduled before On-Demand rates resume.
- Call `billing:sp-performance` (`get_savings_plans_utilization`, `get_savings_plans_utilization_details`, `get_savings_plans_coverage`).

### 2. Compare 7-Day, 30-Day, and 60-Day Lookbacks (`billing:sp-recommendation`)
Call `billing:sp-recommendation` (`get_savings_plans_purchase_recommendation`) across **all three lookback periods** (`SEVEN_DAYS`, `THIRTY_DAYS`, `SIXTY_DAYS`):
- If `7d`, `30d`, and `60d` recommended hourly commitments are within `±10%`, the baseline is stable.
- If `7d` is `>15%` lower than `60d`, the environment is shrinking — size only to `75%–80%` of the `7d` recommendation.
- If `7d` is `>15%` higher than `60d`, a recent spike or anomaly occurred — size to the `60d` steady-state floor.

### 3. Run Custom What-If Simulations (`billing:sp-purchase-analyzer`)
When modeling a custom hourly commitment (e.g., after subtracting right-sizing savings):
1. Call `billing:sp-purchase-analyzer` (`start_commitment_purchase_analysis`) with your custom hourly commitment parameters.
2. Call `get_commitment_purchase_analysis` to get AWS's exact simulated post-purchase coverage, utilization, and net savings.

---

## Capital Allocation: `NO_UPFRONT` vs. `PARTIAL_UPFRONT` vs. `ALL_UPFRONT`

When advising finance/CFO stakeholders on payment options, compute the **Incremental Return on Upfront Capital** using Python (`python3 -c`):
- `upfront_delta = upfront_fee_option_B - upfront_fee_option_A`
- `total_term_savings_delta = total_term_cost_option_A - total_term_cost_option_B`
- `annualized_yield_pct = ((total_term_savings_delta / upfront_delta) / term_years) * 100`
Compare `annualized_yield_pct` against the company's Weighted Average Cost of Capital (WACC, typically 8%–12%). Often `PARTIAL_UPFRONT` beats WACC (12%–18% effective return on upfront cash), whereas `ALL_UPFRONT` yields only 2%–4% incremental discount over `PARTIAL_UPFRONT` and fails the WACC hurdle!

---

## SP vs Reserved Instances

| Feature | Savings Plans | Reserved Instances |
|---------|--------------|-------------------|
| Flexibility | High (Compute SP covers EC2+Fargate+Lambda across regions) | Low (service- and region-specific) |
| Capacity reservation | No (pair with On-Demand Capacity Reservations [ODCR] if needed) | Yes (AZ-scoped RI only) |
| Marketplace resale | No | Yes (EC2 Standard RI only) |
| AWS recommendation | Preferred | Legacy / specialized engines |

**Application Order:** RIs apply **first**, then EC2 Instance SPs, then Compute SPs cover remaining eligible usage. SPs do NOT apply to Spot usage.

## Gotchas

- **7-day return window (conditional):** SPs with hourly commitment ≤ $100/hr, purchased in the past 7 days AND in the same calendar month, can be returned (`DeleteQueuedSavingsPlan` / return policy) for a full refund. Outside this window, the commitment is irreversible for 1 or 3 years.
- Compute SP does NOT cover RDS — use Database SP or RDS RIs.
- EKS control plane ($0.10/hr = $73/mo per cluster) and Extended Support fees are NOT covered by any SP.
- DynamoDB Reserved Capacity is deprecated in favor of Database Savings Plans.
- `EstimatedOnDemandCostWithCurrentCommitment` in `get_savings_plans_purchase_recommendation` covers the **lookback period** (7, 30, or 60 days) — do NOT conflate lookback-period totals with 30.4-day monthly costs!

## CLI Commands

```bash
# Get SP purchase recommendation
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days SIXTY_DAYS

# Check utilization
aws ce get-savings-plans-utilization \
  --time-period Start=2026-03-01,End=2026-04-01 \
  --granularity MONTHLY

# Check coverage
aws ce get-savings-plans-coverage \
  --time-period Start=2026-03-01,End=2026-04-01 \
  --granularity MONTHLY
```
