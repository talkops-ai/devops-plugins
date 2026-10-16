# Cost Explorer, Cost Comparison, and Anomaly Forensics

> **Pricing note:** All prices shown are approximate as of early 2026 and may change. Always verify current pricing before reporting to users.

## Selecting the Right Cost Metric

| Cost Explorer Metric | Definition | Mandatory FinOps Use Case |
|---|---|---|
| `AmortizedCost` | Spreads upfront and recurring RI/Savings Plans fees across the actual consuming hours/resources, plus unused commitment fees on the purchasing account. | **Default when customer has Savings Plans or RIs.** Use for workload showback, right-sizing, and anomaly detection. |
| `NetAmortizedCost` | `AmortizedCost` after contracted private pricing discounts (EDP / PPA). | **Default for enterprise organizations with EDP/PPA** (when net-cost visibility is enabled). |
| `UnblendedCost` | Cash-basis cost charged at billing time. Upfront RI/SP fees spike on the 1st of the month; covered usage appears as `$0.00` or negated. | **Default for single accounts without SPs/RIs, cash-flow forecasting, and invoice reconciliation (`billing:invoicing`).** |
| `NetUnblendedCost` | `UnblendedCost` after contracted EDP/PPA discounts. | **Payable invoice reconciliation** for enterprises with private pricing. |
| `UsageQuantity` / `NormalizedUsageAmount` | Physical consumption units (`Hrs`, `GB-Mo`, `Bytes`, `Requests`). | **Price-vs-volume decomposition** (separating a rate jump from a traffic surge). |

## Defaults

- Metric: `AmortizedCost` when customer has SPs/RIs; `UnblendedCost` (single account without commitments).
- Exclude Credits/Refunds when analyzing usage trends: `--filter '{"Not":{"Dimensions":{"Key":"RECORD_TYPE","Values":["Credit","Refund"]}}}'`
- End date is **exclusive**: `Start=2026-03-01,End=2026-04-01` returns all of March.
- Max 2 `GroupBy` dimensions per request.

## Critical Gotchas

**EC2 service names:** EC2 charges split into two services. `"Amazon Elastic Compute Cloud - Compute"` is instance usage. `"EC2 - Other"` (with spaces around hyphen) is NAT Gateway, EBS, data transfer. WRONG: `"EC2-Other"`, `"EC2Other"`. If `"EC2 - Other"` returns $0, call `GetDimensionValues` to confirm the exact service name, then retry.

**RECORD_TYPE not CHARGE_TYPE:** The dimension for charge type filtering is `RECORD_TYPE` (`Usage`, `SavingsPlanCoveredUsage`, `DiscountedUsage`, `SavingsPlanNegation`, `SavingsPlanRecurringFee`, `RIFee`, `Tax`, `Credit`, `Refund`, `Support`). Using `CHARGE_TYPE` throws `ValidationException`.

**Empty Total with GroupBy:** By design — `Total` is empty when `GroupBy` is used. Sum grouped results using `billing:session-sql` or a Python script (see [`deterministic-calculations.md`](./deterministic-calculations.md)), or make a separate call without `GroupBy`.

**Filter validation:** Cost Explorer does not distinguish between valid filters with no data and invalid filters. If a filter returns no results, call `GetDimensionValues` to verify the filter value exists.

**API cost:** Each paginated `GetCostAndUsage` or `GetCostForecast` call costs **$0.01**. Cache results and prefer free aggregators (`billing:cost-optimization`, `billing:compute-optimizer`) first when hunting for optimization candidates.

**Hourly granularity:** Requires opt-in in Cost Explorer preferences. Only available for past 14 days. Hourly + resource-level only works for EC2 Compute.

**Tags take 24 hours** to appear after activation in Billing Cost Allocation Tags, and only for resources that incurred costs after activation — not retroactive (use Cost Categories or CUR 2.0 backfill rules for historical grouping).

---

## Month-over-Month Variance Drivers (`billing:cost-comparison`)

Instead of manually fetching two months of Cost Explorer data and diffing every usage type by hand, use `billing:cost-comparison`:

1. **`get_cost_and_usage_comparisons`**:
   - Compares `baseline_time_period` vs. `comparison_time_period`.
   - **Strict API constraint:** Both periods must be **exact 1-month intervals starting on the `01` of a month** (e.g., `2026-02-01` to `2026-03-01` vs. `2026-03-01` to `2026-04-01`).
   - Supports `metric_for_comparison` (`AmortizedCost`, `UnblendedCost`, `NetAmortizedCost`, `NetUnblendedCost`, `UsageQuantity`), `group_by`, `filter`, and `billing_view_arn`.
2. **`get_cost_comparison_drivers`**:
   - Automatically isolates the **top 10 root-cause cost variance drivers** across services, accounts, and usage types between two months.

---

## Cost Anomaly Root-Cause Forensics (`billing:cost-anomaly`)

When investigating a cost spike:
1. Call `billing:cost-anomaly` (`operation="get_anomalies"`) with `start_date` and `end_date` (optional `monitor_arn`, `total_impact_operator`, `total_impact_start`).
2. Extract `AnomalyStartDate`, `AnomalyEndDate`, `Impact.TotalImpact`, and `RootCauses` (`Service`, `Region`, `LinkedAccount`, `UsageType`).
3. Run `billing:cost-explorer` (`get_cost_and_usage`) over `[AnomalyStartDate - 7 days, AnomalyEndDate + 2 days]` with `granularity="DAILY"`, `metrics=["AmortizedCost", "UsageQuantity"]`, filtered to the anomalous `Service`/`LinkedAccount`/`Region`, and grouped by `USAGE_TYPE` + `OPERATION`:
   - If `UsageQuantity` spiked alongside `AmortizedCost` -> physical traffic surge, runaway loop, or new resource provisioning.
   - If `UsageQuantity` stayed flat while `AmortizedCost` spiked -> a Savings Plan or RI expired (`billing:sp-explorer`, `billing:ri-performance`) or credits ran out (`billing:credits`).
4. If the spike occurred within the last 14 days, call `get_cost_and_usage_with_resources` to pinpoint the exact `RESOURCE_ID` / ARN, and correlate with `cloudwatch:get_metric_data` or hand off to `aws-sre-agent` / `aws-cloud-security-engineer` for CloudTrail `LookupEvents` principal attribution.

---

## Usage Quantity Analysis

When using `USAGE_QUANTITY` metric:

- MUST group by usage type OR filter for usage types with the same unit (e.g., GB-month)
- NEVER aggregate different usage units (GB-months + instance-hours)
- If API returns usage units of `"NA"`, multiple units were aggregated — discard these results

## Data Transfer Analysis

Data transfer costs in Cost Explorer are spread across multiple usage type patterns. Use a script with regex for accurate filtering — do NOT rely on broad keyword matching (`Bytes`, `Transfer`) as it produces many false positives.

**Core data transfer** (product family "Data Transfer" in CUR):

- `DataTransfer-*-Bytes` — Internet ingress/egress, intra-region cross-AZ (`Regional-Bytes`)
- `*-AWS-Out-Bytes`, `*-AWS-In-Bytes` — inter-region transfer
- `*-Bytes-Internet`, `*-Bytes-AWS` — Global Accelerator
- `CloudFront-*-Bytes` — CloudFront to/from origin
- `*-DataXfer-*` — Direct Connect
- `*-ABytes-*` — S3 Transfer Acceleration

**Networking data processing** (billed under respective services, not under "Data Transfer"):

- `*-NatGateway-Bytes` — per-byte NAT Gateway processing (service: `EC2 - Other`, ~$0.045/GB)
- `*-VpcEndpoint-Bytes` — per-byte VPC Endpoint / PrivateLink processing (service: `Amazon Virtual Private Cloud`, ~$0.01/GB)
- `*-TransitGateway-Bytes` — per-byte Transit Gateway processing (service: `Amazon Virtual Private Cloud`, ~$0.02/GB)
- `*-DataProcessing-Bytes` — per-byte processing, but source varies by service:
  - `Elastic Load Balancing` → NLB/GLB data processing (networking, include)
  - `AmazonCloudWatch` → VPC Flow Logs processing (observability, exclude)
  - Other services → check context before including

Group by both `SERVICE` and `USAGE_TYPE` to disambiguate `DataProcessing-Bytes`. Only include it when the service is `Elastic Load Balancing`.

**Networking infrastructure** (hourly charges for networking resources that facilitate data movement):

- `*-NatGateway-Hours` — NAT Gateway hourly charge (~$0.045/hr = $32.85/mo/AZ)
- `*-VpcEndpoint-Hours` — VPC Endpoint hourly charge (~$0.01/hr = $7.30/mo/AZ)
- `*-TransitGateway-Hours` — Transit Gateway attachment hourly charge (~$0.05/hr = $36.50/mo)
- `GlobalAccelerator*` — Global Accelerator hourly + data transfer
- `*-LCUUsage` — ALB capacity units
- `*PublicIPv4:InUseAddress`, `*PublicIPv4:IdleAddress` — Public IPv4 address hourly charge ($0.005/hr = $3.65/mo per IPv4)

Include both networking categories in your analysis as separate sections — customers asking about "data transfer costs" often want to see the full networking picture, not just per-byte charges.

**NOT data transfer** (common false positives):
`Ingestion-Bytes` (CloudWatch Logs), `PaidEventsAnalyzed-Bytes` (CloudTrail), `QueryScanned-Bytes` (Logs Insights), `VendedLog-Bytes`, `LambdaNetworkLogsAnalyzed-Bytes`, `Select-Scanned-Bytes`/`Select-Returned-Bytes` (S3 Select).

**Script:** Query `GetCostAndUsage` grouped by both `SERVICE` and `USAGE_TYPE` (max 2 GroupBy per request), then filter:

```python
import re
TRANSFER_RE = re.compile(r'DataTransfer|AWS-(In|Out)-Bytes|Bytes-(Internet|AWS)|CloudFront-.*-Bytes|DataXfer|-ABytes-|Regional-Bytes')
NETWORKING_PROCESSING_RE = re.compile(r'NatGateway-Bytes|VpcEndpoint-Bytes|TransitGateway-Bytes')
NETWORKING_INFRA_RE = re.compile(r'NatGateway-Hours|VpcEndpoint-Hours|TransitGateway-Hours|GlobalAccelerator|LCUUsage|PublicIPv4')

# Each group has keys [service, usage_type] and cost
for service, usage_type, cost in results:
    if TRANSFER_RE.search(usage_type):
        pass  # Core data transfer
    elif NETWORKING_PROCESSING_RE.search(usage_type):
        pass  # Networking data processing
    elif 'DataProcessing-Bytes' in usage_type and service == 'Elastic Load Balancing':
        pass  # ELB data processing (networking) — exclude CloudWatch/other services
    elif NETWORKING_INFRA_RE.search(usage_type):
        pass  # Networking infrastructure (hourly / IPv4)
    # Everything else: not data transfer
```

Usage types with no regional prefix may be `us-east-1` or global. The `"EU"` prefix means `eu-west-1`.

For deeper analysis with resource-level detail, use CUR 2.0 + Athena ([`cur-athena.md`](./cur-athena.md)). Reference: https://aws.amazon.com/blogs/networking-and-content-delivery/understand-aws-data-transfer-details-in-depth-from-cost-and-usage-report-using-athena-query-and-quicksight/

## Resource-Level Analysis (`GetCostAndUsageWithResources`)

Use `GetCostAndUsageWithResources` (not `GetCostAndUsage`) for individual resource costs in Cost Explorer:

- Only available for the **past 14 days**
- Requires opt-in via Cost Management Preferences (per-service)
- MUST include a filter (typically by service) and group by `RESOURCE_ID`
- Resources without opt-in show as `"No Resource ID"` (use CUR 2.0 / FOCUS in Athena for >14 days)

## Date Handling

- If user says "last month" without a year, use the most recent completed month
- **ALWAYS check the current date before querying.** Use `date` or equivalent to confirm the current year and month. Models frequently default to dates from training data.
- NEVER compare a complete month to a partial current month without calculating daily averages
- Cost data has ~24-hour delay — current day data is estimated

## Common CLI Commands

```bash
# Monthly cost by service
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-04-01 \
  --granularity MONTHLY --metrics AmortizedCost UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE

# Month-over-Month cost comparison drivers
aws ce get-cost-comparison-drivers \
  --baseline-time-period Start=2026-02-01,End=2026-03-01 \
  --comparison-time-period Start=2026-03-01,End=2026-04-01 \
  --metric-for-comparison AmortizedCost

# Cost forecast
aws ce get-cost-forecast \
  --time-period Start=2026-04-02,End=2026-05-01 \
  --metric AMORTIZED_COST --granularity MONTHLY

# Get valid dimension values
aws ce get-dimension-values \
  --time-period Start=2026-03-01,End=2026-04-01 \
  --dimension SERVICE

# Cost anomaly detection
aws ce get-anomalies \
  --date-interval '{"StartDate":"2026-03-01","EndDate":"2026-04-01"}'
```
