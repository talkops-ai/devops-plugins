---
name: aws-backup-coverage-review
description: AWS Backup coverage, vault architecture, and data protection posture
  review. Determines which backup-eligible resources are protected by AWS Backup
  across enabled Regions, evaluates backup plan frequency and retention,
  cross-Region and cross-account copies, vault encryption, Vault Lock, Logically
  Air-Gapped Vaults, Multi-party approval (MPA), and per-Region resource opt-in.
  Uses read-only control-plane API calls via connected MCP tools and produces a
  rated report with a coverage matrix and prioritized remediation. Use when a user
  asks about backup coverage, unprotected resources, AWS Backup audit or posture,
  backup plan or vault review, Logically Air-Gapped Vaults or MPA ransomware
  controls, or data protection gaps ("what is not being backed up", "AWS Backup
  coverage review", "audit my backup plans", "are my volumes protected", "review
  my backup vaults"). Do NOT use for restoring data, backup/restore job failure
  triage, backup cost optimization, or RDS-native snapshots outside AWS Backup.
metadata:
  author: vediyappan-kk
  version: "1.1.0"
  aws-devops-agent-skills.agent-types: "CHAT"
  aws-devops-agent-skills.aws-services: "AWS Backup"
  aws-devops-agent-skills.technical-domains: "Storage, Operations"
---

# AWS Backup Coverage Review

Perform a structured, strictly read-only coverage and posture review of AWS Backup in an AWS account across enabled Regions, answering precisely **which backup-eligible resources are actually recoverable, which are not, why each gap exists, and how to close it**.

## MCP-Only Execution & Edge-Case Rules (Mandatory)

1. **Strictly Read-Only & MCP-Only Execution:** Execute **all** AWS control-plane reads (`sts`, `ec2`, `backup`, `config`, `kms`, `rds`, `dynamodb`, `efs`, `fsx`, `s3`, `redshift`, `timestream`, `storagegateway`, `backup-gateway`, `cloudformation`, `eks`) **exclusively via connected MCP tools** (`aws-mcp` `aws___run_script` using `await call_boto3(...)`, batching multi-region discovery with `asyncio.gather` so full-account sweeps finish rapidly). **Never** shell out to raw `aws` CLI commands or `python3 -c` in Bash/`run_command`, and **never** invoke mutating calls (`StartBackupJob`, `StartRestoreJob`, `StartCopyJob`, `StartReportJob`, `Create*`, `Put*`, `Update*`, `Delete*`).
2. **`awsknowledge` Fallback for Unmapped AWS Backup Features:** If the user asks about a specialized AWS Backup feature not covered in local references (e.g., logically air-gapped vaults cross-account sharing specifics, indexed backup search, MPA approval teams), immediately query `awsknowledge` / `aws-mcp` (`aws___search_documentation` / `aws___read_documentation` — 1–2 focused searches) and answer directly.

## Mandatory Output Contract

Unless answering a direct follow-up to a report already rendered earlier in the same conversation, **every review response MUST render the complete standard report** defined in [assets/report-format.md](assets/report-format.md) containing, in order:
1. **Scope** (Account ID, Inventory Strategy: Config fast path vs direct enumeration, Regions swept, Regions not swept, and `NotEnumerated` / `AccessDenied` / `ToolingFailure` disclosures)
2. **`## Coverage Rating`** (`High` / `Medium` / `Low` / `Indeterminate`) with exact **coverage percentage** (identical across headline, Coverage Rating, and summary tables!)
3. **Executive Summary**
4. **Coverage Matrix** (per-resource rows: Region, Type, Identifier/ARN, Coverage State, Last Backup, Matched Selection)
5. **Findings & Recommendations** (with Severity + SLA bucket)
6. **Check Coverage Matrix with all 23 rows** (`1.1`–`5.3`, never fewer or more than 23 rows!)
7. **Next Steps** (concrete operator actions — never end with "want me to run the full review?" or "shall I fix these for you?")

- **Scoped Requests:** A narrow prompt ("Are my EBS volumes protected in `ap-south-1`?") narrows **what is swept**, never **what is rendered** — still render the full report structure and all 23 Check Coverage Matrix rows (marking out-of-scope checks per [references/coverage-logic.md](references/coverage-logic.md)).
- **When to Use vs Sibling Skills:** Do NOT use for active restore execution, backup job failure triage, backup cost optimization, or RDS-native snapshots outside AWS Backup. Route S3 bucket versioning/replication/Object Lock posture audits to `storage-s3-resiliency-expertise`.

## The Six-State Coverage Model

Every eligible live resource resolves to one of 5 active states; deleted resources still appearing in `ListProtectedResources` resolve to `OrphanedRecoveryPoint`:

| State | Meaning | Severity | Numerator / Denominator |
|---|---|---|---|
| `Protected` | `>= 1` non-expired recovery point AND newest `LastBackupTime` is within plan schedule | ✅ | In numerator & denominator |
| `Stale` | Has recovery points, but newest is older than plan schedule allows | ⚠️ HIGH | In denominator only |
| `SelectedNotProtected` | Matched by a backup selection, but `0` recovery points exist | ❌ CRITICAL | In denominator only |
| `Unprotected` | Eligible live resource, matched by no selection, `0` recovery points | ❌ CRITICAL | In denominator only |
| `OptInBlocked` | Matched by a selection, but its resource type is **not opted in** via `DescribeRegionSettings` in that Region | ❌ CRITICAL | In denominator only |
| `OrphanedRecoveryPoint` | In `ListProtectedResources`, but live resource no longer exists in inventory | ⚠️ MEDIUM | **Excluded from both numerator & denominator** (report separately with age) |

## Scope Resolution & Execution Workflow

1. **Step 1 — Resolve Scope Silently via `aws___run_script`:** Never ask for Account ID or Region list. Call `sts:GetCallerIdentity`, `ec2:DescribeRegions(AllRegions=False)`, and `backup:GetSupportedResourceTypes`. Sweep **all** enabled Regions unless the user narrowed the Region/type scope (use a fast batched probe across enabled Regions inside `aws___run_script`; any skipped enabled Region MUST be listed under "Regions not swept" and caps Coverage Rating at `Medium`).
2. **Step 2 — Load [references/data-collection.md](references/data-collection.md) & Choose Inventory Strategy:** Check `config:DescribeConfigurationRecorderStatus` per Region (`recording == True` → Config `SelectResourceConfig` fast path; otherwise → direct per-service `Describe*`/`List*` enumeration). Disclose which strategy was used and whether Config covers all eligible types.
3. **Step 3 & 4 — Collect Backup Posture & Live Eligible Inventory (`aws___run_script`):** Collect `DescribeRegionSettings`, `DescribeGlobalSettings`, `ListBackupPlans` + **`GetBackupPlan`**, `ListBackupSelections` (`BackupSelectionsList`) + **`GetBackupSelection`**, `ListBackupVaults` + `DescribeBackupVault` + `GetBackupVaultAccessPolicy` + `GetBackupVaultNotifications`, `ListProtectedResources`, `ListRestoreTestingPlans`, `ListFrameworks`, `ListReportPlans`, plus live resource inventory.
4. **Step 5 & 6 — Load [references/coverage-logic.md](references/coverage-logic.md) & Evaluate All 23 Checks:** Resolve each resource's coverage state and score all 23 checks (`OK`, `NotConfigured`, `AccessDenied`, `ToolingFailure`, `NotEnumerated`). Load [references/backup-best-practices.md](references/backup-best-practices.md) for remediation details.
5. **Step 7 — Handle `AccessDenied` / `ToolingFailure` Honesty:** Never conflate `NotConfigured` (feature absent → real finding) with `AccessDenied` or `ToolingFailure` (blind spot → **no false finding**, caps Coverage Rating at `Medium`). Present the permissions/tooling notice clearly when encountered.
6. **Step 8 — Load [assets/report-format.md](assets/report-format.md) & Render Complete Report:** Verify Check Coverage Matrix has **exactly 23 rows** and coverage counts/percentages reconcile identically everywhere.

## Coverage Rating & Severity Roll-Up

| Rating | Criteria |
|---|---|
| `High` | Zero `CRITICAL` findings, zero `OptInBlocked` resources, coverage `>= 95%`, and every plan meets frequency/retention thresholds |
| `Medium` | Zero `CRITICAL` findings and coverage `>= 80%`, OR any check/region capped by `AccessDenied`, `ToolingFailure`, or unswept Regions |
| `Low` | Any `CRITICAL` finding (including `0` backup plans when eligible resources exist, `Unprotected`, `SelectedNotProtected`, `OptInBlocked`), or coverage `< 80%` |
| `Indeterminate` | Eligible resource inventory could not be established at all (or `0` eligible resources exist in scope — state `0/0` N/A honestly) |

Severity SLAs: `CRITICAL` (`❌` 24–48h) · `HIGH` (`⚠️` 1 week) · `MEDIUM` (`⚠️` 30 days) · `LOW` (`ℹ️` when convenient) · `INFO` (`ℹ️` N/A).

## Critical Rules & Known AWS Backup API Quirks

- **Never Mutate, Even If Asked:** If asked to create a backup plan, enable Vault Lock, opt in a resource type, or delete orphan recovery points, **refuse to execute any write call**, state that this review skill is strictly read-only, and provide the exact CLI/IaC remediation steps for human change control.
- **S3 Per-Region Opt-In:** `s3:ListBuckets` is global, but AWS Backup protects S3 per Region — always resolve each bucket's Region via `s3:GetBucketLocation` and check *that* Region's `DescribeRegionSettings` S3 opt-in!
- **Cluster Engine Separation:** `rds:DescribeDBClusters` returns `Aurora`, `Neptune`, and `DocumentDB` clusters together — separate them by `Engine` before mapping to AWS Backup resource types (`Aurora`, `Neptune`, `DocumentDB`).
- **`ResourceNotFoundException` on Vault Policy / Notifications:** Both `GetBackupVaultAccessPolicy` and `GetBackupVaultNotifications` (`Failed reading notifications from database for Backup vault`) raise `ResourceNotFoundException` when unset — classify as **`NotConfigured`**, never `ToolingFailure`.
- **Unsupported / Hypervisor Enumeration:** `SAP HANA on Amazon EC2` cannot be enumerated via control-plane APIs → disclose as `NotEnumerated`. `VirtualMachine` is only unenumerable when `backup-gateway:ListHypervisors` returns `>= 1` hypervisor; `0` hypervisors means `0` VMs (not a blind spot).
- **Pagination & Metadata-Only List Calls:** Always paginate `NextToken` (`MaxResults=1000`), call `GetBackupPlan` per plan and `GetBackupSelection` per selection (`BackupSelectionsList`), and verify `LastBackupTime` rather than trusting selection membership alone.

## References & Assets

- [references/data-collection.md](references/data-collection.md) — Read-only API allowlist, hard denials, Config fast path, resource-type mapping, and error classification.
- [references/coverage-logic.md](references/coverage-logic.md) — All 23 checks across 5 dimensions, thresholds, verdict rules, and Coverage Rating roll-up.
- [references/backup-best-practices.md](references/backup-best-practices.md) — Threshold rationale, Vault Lock / cross-Region / cross-account remediation patterns, and AWS doc URLs.
- [assets/report-format.md](assets/report-format.md) — Mandatory report layout, Coverage Matrix, 23-row Check Coverage Matrix, and pre-render validation.
