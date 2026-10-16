# AWS Free Tier (`billing:free-tier`)

## July 2025 Transition (Time-Based vs. Credit-Based Free Tier)

AWS transitioned from a time-based 12-month Free Tier to a **credit-based Free Tier** on **July 15, 2025**:

| Account Type | Model | Details |
|-------------|-------|---------|
| **Legacy (created before July 15, 2025)** | 12-month free tier + Always Free | Original 12-month monthly usage caps (e.g., 750 hrs EC2 `t2.micro`/`t3.micro`, 750 hrs Single-AZ RDS, 5 GB S3 Standard) complete naturally. Always Free services remain available. |
| **Free Plan (created on/after July 15, 2025)** | Up to **$200 credits for 6 months** ($100 at sign-up + up to $100 via guided foundational activities) | **Hard safety cap:** No cash charges during the 6-month / $200 credit period; account closes/suspends when 6 months expire or $200 credits exhaust unless upgraded to a Paid Plan. Always Free services remain available. |
| **Paid Plan (created on/after July 15, 2025)** | Up to **$200 credits** ($100 at sign-up + up to $100 via activities) | Full production access; credits automatically offset eligible AWS usage, and usage exceeding credits is billed at standard rates. Always Free services remain available. |

~30 **Always Free** services (e.g., 1M Lambda requests + 400,000 GB-seconds/month, 25 GB DynamoDB storage + 25 WCU/RCU, 1M SNS publishes, 10 CloudWatch custom metrics/alarms) remain available indefinitely across all account types.

## Recommended Workflow (`billing:free-tier` & `billing:credits`)

1. **Check account plan state (`aws___call_aws` / `Bash`):**
   ```bash
   aws freetier get-account-plan-state
   ```
   Determines whether the account is on `FREE`, `PAID`, or Legacy tier and how much credit balance remains.
2. **Check current Free Tier usage (`billing:free-tier`):**
   - Call `billing:free-tier` (`operation="get_free_tier_usage"`) or CLI `aws freetier get-free-tier-usage`.
   - Flag any service where `actualUsageAmount / limit > 0.80` (80% of monthly cap) or `forecastedUsageAmount > limit`.
3. **Check credit ledger (`billing:credits`):**
   - Call `billing:credits` (`get_credits`, `get_credit_allocation_history`) to inspect remaining sign-up/activity/Activate credits and expiration dates.

## Critical Rules & Common Traps

- **NEVER cite specific 12-month free tier limits from training data without checking the account's plan state** — offers changed July 15, 2025 and vary by account type.
- `get_free_tier_usage` only returns services with `usage > 0`. A missing service means either no metered Free Tier offer exists OR the customer hasn't used it yet in the current month.
- **The Multi-Instance 750-Hour Trap (Legacy Accounts):** 750 hours/month covers **one** instance running 24x7 (730 hours). Running **two** `t3.micro` instances consumes `2 × 730 = 1,460 hours`, billing `710 hours` at On-Demand rates + **$3.65/month per public IPv4 address** (`PublicIPv4:InUseAddress` is NOT covered by Legacy Free Tier when in use beyond free limits or on Elastic IPs)!
- For questions about available offers before provisioning a service, direct users to https://aws.amazon.com/free/
