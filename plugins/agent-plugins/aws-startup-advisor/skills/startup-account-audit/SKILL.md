---
name: startup-account-audit
description: >-
  Run a read-only 26-point AWS Startup Account Health, Security, Scalability, and Spend-Leak Audit
  across four vectors: Identity & Secret Hygiene, Network & Data Encryption, Scalability & AI
  Readiness, and Immediate Spend Leaks & AWS Activate Credit Burn Runway. Use when a founder or
  engineer asks to audit their AWS account, find why their AWS bill or credit burn spiked, check
  security readiness before a SOC 2 or enterprise customer review, find wasted resources, or
  calculate remaining AWS Activate credit runway.
---

# Startup Account Health, Security & Spend-Leak Audit

This skill brings the 26 automated read-only AWS account checks from the AWS Startup Advisor IDE extension directly into the CLI/IDE agent workflow. Every check is strictly **read-only**, calibrated to the startup's funding stage (**Pre-Revenue / MVP**, **Seed**, **Series A**, **Series B+**), and maps findings directly to **monthly USD savings** and **AWS Activate credit runway extension**.

---

## Mandatory Operational Guardrails

1. **Strictly Read-Only Discovery**:
   - Only invoke `Describe*`, `List*`, `Get*` read-only AWS API calls via `aws-mcp`, `aws-billing`, or `<SKILL_BASE>/scripts/run_startup_audit.py`.
   - Never delete, stop, or modify any resource during an audit without presenting the finding and receiving explicit user approval through `aws-mutation-gate.py`.
2. **Cost Explorer (`ce:*`) `$0.01/call` Warning**:
   - Before invoking `ce:GetCostAndUsage`, `ce:GetReservationPurchaseRecommendation`, or running `<SKILL_BASE>/scripts/run_startup_audit.py --include-cost-explorer`, explicitly inform the user:
     > *"Note: AWS Cost Explorer API calls cost $0.01 per request and are billed directly (not covered by AWS Activate credits)."*
   - Prefer free `budgets:DescribeBudgets` and resource-level configuration checks first when the user wants a zero-cost scan.
3. **Never Read Plaintext Secret Values**:
   - When checking Lambda environment variables for leaked secrets (`Vector 1.6`), inspect **only variable key names** (or redact values immediately). To remediate leaked secrets, use `${CLAUDE_PLUGIN_ROOT}/scripts/asm-exec` so plaintext credentials never enter the LLM context window.
4. **Stage-Calibrated Prioritization**:
   - Do **not** lecture a Pre-Revenue or Seed founder for running single-AZ RDS or skipping AWS Shield Advanced.
   - **Do** flag existential risks at every stage (root access keys, missing root MFA, `0.0.0.0/0` on SSH/DB ports, plaintext API keys in Lambda env vars) and immediate money pits (NAT Gateways without free S3/DynamoDB Gateway Endpoints, stopped EC2 instances with attached EBS, unattached Elastic IPs, unbounded CloudWatch log retention).

---

## Progressive-Disclosure References & Scripts

- **Detailed Check Catalog & Remediation Playbooks**: Load [`references/audit-vectors.md`](./references/audit-vectors.md) for the complete 26-check specification, severity rubric, and copy-paste CLI/Terraform remediations.
- **Automated Local Audit Runner**: Run `<SKILL_BASE>/scripts/run_startup_audit.py` via `Bash` to execute the read-only boto3 audit across the active AWS profile/region and emit a structured JSON + Markdown scorecard.

```bash
# Zero-cost read-only audit (skips $0.01/call Cost Explorer queries)
python3 "<SKILL_BASE>/scripts/run_startup_audit.py" --region "${AWS_REGION:-us-east-1}" --stage seed

# Full audit including trailing 30-day spend & Activate credit burn calculation ($0.01 CE API call)
python3 "<SKILL_BASE>/scripts/run_startup_audit.py" --region "${AWS_REGION:-us-east-1}" --stage seed --include-cost-explorer --credit-balance 10000
```

---

## Audit Workflow

### Step 1: Confirm Scope, Stage & Region
1. Determine the startup stage (`pre-revenue`, `seed`, `series-a`, `series-b+`) from conversation context or ask a single clarifying question if unknown.
2. Confirm the target AWS region(s) and whether to include the optional Cost Explorer credit-burn analysis (`$0.01/call`).

### Step 2: Execute the 4-Vector Read-Only Scan
Run `<SKILL_BASE>/scripts/run_startup_audit.py` (or execute the targeted MCP checks in [`references/audit-vectors.md`](./references/audit-vectors.md)) across all 4 vectors:

| Vector | Focus Area | Checks | Key Signals |
|---|---|---|---|
| **1. Identity & Secret Hygiene** | Prevent account takeover & credential leaks | 6 checks | Root access keys, Root MFA, IAM keys >90d, wildcard policies, Cognito MFA, Lambda env var secrets |
| **2. Network & Data Encryption** | Close public DB/SSH exposure & compliance blockers | 7 checks | SG `0.0.0.0/0` on DB/SSH ports, default VPC usage, S3 public access, RDS/EBS/ElastiCache encryption, CloudTrail |
| **3. Scalability & AI Readiness** | Prevent silent outages & runaway LLM loops | 5 checks | CloudWatch 5xx/CPU/throttle alarms, Lambda throttles, API GW rate limits, stage-calibrated RDS HA, Bedrock Guardrails |
| **4. Spend Leaks & Credit Runway** | Stop idle cash/credit burn immediately | 8 checks | Stopped EC2 EBS burn, unattached EIPs/EBS, aged snapshots, infinite CloudWatch logs, idle SageMaker, NAT Gateway missing S3/DDB endpoints, Activate credit exhaustion date |

### Step 3: Present the Stage-Aware Executive Scorecard
Present findings grouped by urgency:
1. **Stop the Bleeding (Security Criticals — Fix Today)**: Root keys/MFA, public DB security groups, plaintext Lambda secrets (offer `scripts/asm-exec` remediation).
2. **Instant Runway Extensions (Zero-Downtime Cost Wins)**: Exact monthly USD saved by releasing unattached EIPs, adding free S3/DynamoDB VPC Gateway Endpoints, setting CloudWatch log retention, and deleting orphaned EBS volumes/snapshots.
3. **AWS Activate Credit Runway Forecast**:
   - Show Gross Monthly Run-Rate, Monthly Credit Offset, Net Cash Burn, and **Estimated Credit Exhaustion Date** (`Remaining Credits / Monthly Gross Burn`).
4. **Stage-Appropriate Next Steps**: Only surface Series A/B enterprise hardening checks (Multi-AZ RDS, WAF, multi-account SCPs) if the startup is at or approaching that stage.

### Step 4: Contextual Offers (Final Step)
After presenting the audit scorecard, run the inline offer check against [`../knowledge-base-for-startups/references/offers.md`](../knowledge-base-for-startups/references/offers.md) per [`../contextual-offers-for-startups/SKILL.md`](../contextual-offers-for-startups/SKILL.md) rules (at most 1 offer, strictly post-recommendation).
