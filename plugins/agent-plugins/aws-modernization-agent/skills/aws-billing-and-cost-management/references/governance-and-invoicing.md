# Multi-Account Governance, Billing Conductor, Credits, Enterprise Support & Invoicing

This reference covers enterprise financial governance, showback/chargeback, credit burn-rate tracking, Enterprise Support allocation, and invoice reconciliation across the governance modules in `awslabs.billing-cost-management-mcp-server` (`billing`).

---

## 1. Pro-Forma Chargeback: AWS Billing Conductor (`billing:billing-conductor`)

When an enterprise platform team, FinOps Center of Excellence, or MSP needs to generate customized **pro-forma** billing rates (for example, keeping payer-level EDP/RI/SP discounts central or distributing shared platform costs to business units):

1. **Audit Billing Groups & Account Associations:**
   - Call `billing:billing-conductor` (`list_billing_Groups`, `list_account_associations`) to verify that every active member account in AWS Organizations is assigned to a Billing Group (unassigned accounts leak out of pro-forma chargeback reports).
2. **Audit Pricing Plans & Pricing Rules:**
   - Call `list_pricing_plans`, `list_pricing_rules`, and `list_ pricing_rules_associated_to_pricing_plan` to inspect global or service-specific `MARKUP`, `DISCOUNT`, and `TIERING` pricing rules.
3. **Audit Custom Line Items (Shared Service Fee / Credit Distribution):**
   - Call `list_custom_line_items`, `list_custom_line_item_versions`, and `list_resources_associated_to_custom_line_item` to inspect flat or percentage-based platform fees (e.g., shared networking, security, or platform engineering overhead) allocated across Billing Groups.
4. **Analyze Pro-Forma Margin Reports:**
   - Call `list_Billing_group_cost_reports` and `get_billing_group_cost_report` to compute the exact margin between actual AWS Payer cost (`AWSCost`) and the Billing Group's pro-forma cost (`ProformaCost`) using `billing:session-sql` or Python.

---

## 2. Cost Categories & Tag Governance (`billing:cost-categories`)

### A. Cost Categories & Split-Charge Rules
1. Call `billing:cost-categories` (`list_cost_category_definitions`, `describe_cost_category_definition`, `list_cost_category_resource_associations`).
2. Verify that Cost Category definitions include:
   - Deterministic `REGULAR` rules mapping `LINKED_ACCOUNT`, `TAG`, `SERVICE`, and `USAGE_TYPE` to business dimensions (`BusinessUnit`, `Environment`, `Product`, `CostType`).
   - An explicit `default_value` (e.g., `"Unallocated"`) so untagged spend is surfaced rather than hidden.
   - `split_charge_rules` (`PROPORTIONAL`, `FIXED`, or `EVEN`) to allocate shared Transit Gateway, Data Lake, Security, or Observability accounts back to consuming business units.

### B. Tag Compliance & Enforcement Architecture
1. Call `billing:cost-explorer` (`get_tags`) or query CUR 2.0 (`resource_tags`) to calculate the percentage of spend missing mandatory cost-allocation tags (`Environment`, `Owner`, `CostCenter`, `Workload`).
2. Recommend a two-layer tag enforcement architecture (handed off to `aws-cloud-security-engineer` or `aws-iac-engineer`):
   - **AWS Organizations Tag Policies:** Enforce standardized tag key capitalization and allowed values (`prod`, `staging`, `dev`).
   - **Service Control Policies (SCPs) & CloudFormation Guard (`awsiac`):** Deny creation of high-cost resources (`ec2:RunInstances`, `rds:CreateDBInstance`, `eks:CreateCluster`, `s3:CreateBucket`, `bedrock:CreateProvisionedModelThroughput`) when mandatory cost-allocation tags are missing (`aws:RequestTag/<Key>`).

---

## 3. Credit Ledger & Exhaustion Cliff Forecasting (`billing:credits`)

Expiring or exhausting AWS credits (Activate, Migration Acceleration Program [MAP], PoC, or service credits) cause sudden jumps in `NetUnblendedCost` cash invoices even when physical usage is flat:

1. Call `billing:credits` (`get_credits`, `get_credit_allocation_history`) to inventory all active credit programs, remaining balances, eligible services, and expiration dates.
2. Using `billing:session-sql` or Python (`python3 -c`), calculate:
   - `daily_credit_burn_usd = credits_applied_last_30d / 30.0`
   - `days_until_balance_exhausted = remaining_credit_balance / daily_credit_burn_usd`
   - `effective_cliff_date = min(expiration_date, today + days_until_balance_exhausted)`
3. **Warning Rule:** Flag any credit program that will exhaust or expire within **60 days**, and report the underlying uncredited run-rate (`AmortizedCost` excluding `RECORD_TYPE = Credit`) so finance and engineering prepare for the post-credit cash bill.

---

## 4. Enterprise Support Tier & Chargeback (`billing:enterprise-support`)

1. Call `billing:enterprise-support` (`get_charge_summary`, `get_contract_details`, `list_linked_account_charges`).
2. Verify Enterprise Support tier progression ($15,000/mo minimum or 10% of first $150k, 7% of $150k–$500k, 5% of $500k–$1M, 3% above $1M; or Enterprise On-Ramp $5,500/mo / 10%) and include linked-account support charges in total cost of ownership (TCO) and internal chargeback models.

---

## 5. Invoice Reconciliation, Invoice Units & Billing Preferences (`billing:invoicing`, `billing:invoice-units`, `billing:get-billing-preferences`, `billing:procurement-preferences`)

1. **Invoice Reconciliation (`billing:invoicing`):**
   - Call `list_invoice_summaries` to reconcile official issued AWS tax/commercial invoices (including AWS Marketplace invoices, taxes, and out-of-cycle adjustments) against Cost Explorer `UnblendedCost` / `NetUnblendedCost`.
2. **Invoice Units (`billing:invoice-units`):**
   - Call `list_invoice_units`, `get_invoice_unit`, and `batch_get_invoice_profile` to audit how AWS splits monthly invoices across legal entities, subsidiaries, or purchase orders (`taxInheritanceDisabled`, account/tag rules).
3. **Consolidated Billing & Procurement Preferences (`billing:get-billing-preferences`, `billing:procurement-preferences`):**
   - Verify whether **RI/Savings Plans Discount Sharing** and **Credit Sharing** are enabled across all member accounts. If discount sharing is disabled on the account that purchased a Savings Plan, unused commitment on that account will not float to sister accounts unless intentionally isolated.
