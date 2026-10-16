# Reserved Instances (`billing:ri-performance`)

## RI Types

| Type | Discount | Flexibility | Marketplace |
|------|----------|-------------|-------------|
| **Standard** | Up to 72% | Size flexibility within family (regional Linux/default tenancy) | Can sell (EC2 only) |
| **Convertible** | Up to 66% | Can exchange for equal-or-greater value family/size/OS | Cannot sell |

## Payment Options
All Upfront (highest discount) > Partial Upfront > No Upfront (lowest discount). Always evaluate incremental upfront capital yield against corporate WACC (see [`savings-plans.md`](./savings-plans.md)).

## Break-Even Points

- 1-year RI: typically 7–10 months
- 3-year RI: typically 10–14 months

## Size Flexibility (Regional RIs)

Regional RIs automatically apply across instance sizes within the same family using normalization factors (`small=1`, `medium=2`, `large=4`, `xlarge=8`, `2xlarge=16`, etc.). Example: 1 `c6g.xlarge` (8 units) covers 2 `c6g.large` (2×4 units) or 4 `c6g.medium` (4×2 units) instances.
- **Exception 1 (AZ-Scoped EC2 RIs):** Provide an Availability Zone capacity reservation, but **NO size flexibility**.
- **Exception 2 (Operating Systems with License Fees):** EC2 size flexibility applies to Linux/Unix (shared tenancy) without additional OS charges; RHEL, SUSE, and Windows Server RIs do **not** offer instance-size flexibility.

## Application Order
RIs apply **first** (Zonal RIs → Regional RIs), and then Savings Plans cover remaining eligible On-Demand usage.

## Service-Specific Considerations (`billing:ri-performance`)

- **EC2 (`Amazon Elastic Compute Cloud - Compute`):** Prefer **Compute Savings Plans** or **EC2 Instance Savings Plans** over EC2 RIs unless you specifically need AZ-level capacity reservation (or pair Savings Plans with On-Demand Capacity Reservations [ODCR]) or EC2 Standard RI Marketplace liquidity.
- **RDS (`Amazon Relational Database Service`):**
  - **Size-flexible engines:** MySQL, MariaDB, PostgreSQL, Amazon Aurora, and Db2 (BYOL) support instance-size flexibility within the same instance family and region, and automatically apply across both Single-AZ and Multi-AZ deployments (e.g., two Single-AZ `db.r7g.large` RIs cover one Multi-AZ `db.r7g.large` instance).
  - **Non-size-flexible engines:** License-Included **SQL Server** and **Oracle** RIs are locked to the exact instance size, edition (`Standard` vs `Enterprise`), and deployment option.
  - **Modernize to Graviton (`db.r7g` / `db.m7g`) first:** Never purchase `db.r5` or `db.r6i` RIs before upgrading the instance class to Graviton (`db.r7g`), as RDS RIs cannot cross instance families!
- **ElastiCache (`Amazon ElastiCache`):**
  - Valkey and Redis OSS reserved nodes support size flexibility within the same node family (`cache.r7g`). Memcached reserved nodes do not.
  - **Critical Valkey Rule:** Migrate Redis OSS clusters to **ElastiCache for Valkey on Graviton (`cache.r7g`)** (20%–33% lower base price) **before** purchasing ElastiCache Reserved Nodes—Redis OSS RIs do not cover Valkey nodes!
- **OpenSearch (`Amazon OpenSearch Service`):** Locked to specific instance type and region (`r7g.large.search`). No size flexibility and cannot be sold on Marketplace.
- **Redshift (`Amazon Redshift`):** Locked to specific `ra3` node types and regions.

## CLI & MCP Commands (`billing:ri-performance`)

```bash
# RI utilization (`get_reservation_utilization`)
aws ce get-reservation-utilization \
  --time-period Start=2026-03-01,End=2026-04-01 \
  --granularity MONTHLY

# RI purchase recommendations (`get_reservation_purchase_recommendation`)
aws ce get-reservation-purchase-recommendation \
  --service "Amazon Relational Database Service" \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days SIXTY_DAYS

# RI coverage (`get_reservation_coverage`)
aws ce get-reservation-coverage \
  --time-period Start=2026-03-01,End=2026-04-01 \
  --granularity MONTHLY
```

## Gotchas

- Compare `SEVEN_DAYS`, `THIRTY_DAYS`, and `SIXTY_DAYS` lookback periods before recommending any RI purchase.
- Always deduct Stage 3–4 right-sizing and Single-AZ non-prod conversions before sizing RDS/ElastiCache/OpenSearch RIs.
- Standard EC2 RIs can be sold on the AWS RI Marketplace (subject to a 12% AWS Marketplace service fee and US bank account requirement); Convertible EC2 RIs and non-EC2 RIs (RDS, ElastiCache, OpenSearch, Redshift) **cannot** be sold on the Marketplace.
- DynamoDB Reserved Capacity is deprecated — use **Database Savings Plans** instead.
