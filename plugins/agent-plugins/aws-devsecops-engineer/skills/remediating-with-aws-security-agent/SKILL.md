---
name: remediating-with-aws-security-agent
description: >-
  Pull AWS Security Agent findings (penetration tests and code reviews) via the `aws-security-agent`
  MCP server or `aws securityagent` CLI, export them to a gitignored `.security-agent/` directory,
  prioritize by exploitability and severity, patch local application and IaC code, and verify fixes
  with `diff-scanning-with-aws-security-agent`. Trigger for "get my security findings", "what
  vulnerabilities do we have", "fix the pentest results", or "triage the security report".
---

# Security Agent Remediation

AWS Security Agent runs on-demand penetration tests (DAST) and code reviews (SAST) against your applications and reports verified security risks. This skill takes you from discovered findings in AWS to verified local code and IaC fixes while keeping sensitive exploit details out of source control.

The workflow has five stages:

1. **Discover** which Agent Spaces, code reviews, and pentests exist (via `aws-security-agent` MCP tools or `aws securityagent` CLI).
2. **Export** findings to a local gitignored `.security-agent/` directory.
3. **Triage** findings into a prioritized remediation plan.
4. **Remediate** by applying surgical code/IaC fixes after user confirmation.
5. **Verify** fixes locally by running `diff-scanning-with-aws-security-agent`.

## Why the ordering and guardrails matter

Findings contain working attack scripts, reproduction steps, file paths, and sometimes environment details. **Findings MUST be written only to `.security-agent/`, and that directory MUST be gitignored before anything is written.**

## Stage 1: Discover scans (live, read-only)

Discover existing Agent Spaces, pentests, and code reviews using `aws-security-agent` MCP tools (`ListAgentSpaces`, `ListPentests`, `ListCodeReviews`, `ListPentestJobsForPentest`, `ListCodeReviewJobsForCodeReview`) or the AWS CLI:

```bash
aws securityagent list-agent-spaces
aws securityagent list-pentests          --agent-space-id <as-...>
aws securityagent list-code-reviews      --agent-space-id <as-...>
aws securityagent list-pentest-jobs-for-pentest         --agent-space-id <as-...> --pentest-id <pt-...>
aws securityagent list-code-review-jobs-for-code-review --agent-space-id <as-...> --code-review-id <cr-...>
```

Job `status` is one of `IN_PROGRESS`, `STOPPING`, `STOPPED`, `FAILED`, `COMPLETED`. Only `COMPLETED` jobs have a complete set of findings.

### Match the codebase to a scan, then confirm

Infer the application identity from the workspace (`git remote -v`, `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `README.md`) and compare against Agent Space names. Present your best match and confirm with the user before exporting.

## Stage 2: Export findings to `.security-agent/` (gitignored)

### 1. Lock down the output directory before pulling anything

```bash
mkdir -p .security-agent
echo '*' > .security-agent/.gitignore
```

### 2. Resolve the latest COMPLETED job & list findings

```bash
# Pentest findings:
aws securityagent list-findings \
  --agent-space-id <as-...> --pentest-job-id <pj-...>

# Code review findings:
aws securityagent list-findings \
  --agent-space-id <as-...> --code-review-job-id <cj-...>
```

Keep `HIGH` and `MEDIUM` confidence findings by default (widen only if requested).

### 3. Fetch full detail in batches of 25

```bash
aws securityagent batch-get-findings \
  --agent-space-id <as-...> \
  --finding-ids <fid-1> <fid-2> ... <fid-25>
```

Write a full markdown report per job to `.security-agent/findings_<jobId>.md` containing all fields returned by the API. Never paste raw `attackScript` or exploit payloads into chat.

## Stage 3: Triage into a prioritized plan

Sort findings deterministically by:
1. **Risk level**: `CRITICAL` → `HIGH` → `MEDIUM` → `LOW` → `INFORMATIONAL` → `UNKNOWN`
2. **Risk score**: highest `riskScore` first (e.g., `"10.0"`)
3. **Confidence**: `HIGH` → `MEDIUM` → `LOW` → `UNCONFIRMED` → `FALSE_POSITIVE`

Correlate pentest findings (endpoint + attack chain) with code-review findings (`filePath:lineStart` + `suggestedFix`) when they point to the same underlying root cause.

Present a compact summary:

```markdown
## Security Agent Triage — <agent space name>

<N> findings exported (<P pentest, C code review>) · confidence: <levels> · severity: <counts>

### Priority Order
1. [CRITICAL · score 10.0 · HIGH confidence] <finding name>
   - Type: <riskType> · Source: <pentest|code-review>
   - Where: <file:line or endpoint>
   - Impact: <one-line plain-language summary>
```

## Stage 4: Remediate in Local Code & IaC

Offer to start fixing the highest-priority findings. Once confirmed:
1. Read the full finding detail from `.security-agent/findings_<jobId>.md`.
2. Patch the affected source file or IaC template (`*.tf`, `*.ts`, `template.yaml`, `Dockerfile`) using `Edit`.
3. Report each fix concisely: `Fixed <finding name> in <filePath>:<lineStart>`.

## Stage 5: Verify Remediation via Diff Scan

After applying code fixes, run `diff-scanning-with-aws-security-agent` against the local git diff to verify that the vulnerability is resolved and no regressions were introduced before opening a pull request.
