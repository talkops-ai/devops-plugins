#!/usr/bin/env python3
"""finops-sql-and-cost-gate: PreToolUse guard for FinOps SQL & Athena scan cost governance.

Works alongside `secret-safety.py` and `aws-mutation-gate.py` using the Claude Code and Codex
PreToolUse JSON protocol:
  * safe / unrelated call               -> silent exit 0 (host's normal permission policy applies)
  * destructive SQL DDL/DML             -> deny
  * `SELECT *` on Athena / Storage Lens -> deny (destroys Parquet columnar projection; $5/TB scan risk)
  * `SELECT *` on `billing:session-sql` -> allowed ($0.00 local in-process SQLite session DB)
  * Athena query missing partition
    predicate or `--work-group`         -> ask (Claude Code) or context warning (Codex)

Override with TALKOPS_FINOPS_SQL_GATE=off|warn|ask|deny.

Self-test: python3 finops-sql-and-cost-gate.py --self-test
"""

from __future__ import annotations

import json
import os
import re
import sys

MODES = {"off", "warn", "ask", "deny"}

DDL_DML_RE = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE|ALTER|CREATE|GRANT|REVOKE|MSCK|UNLOAD|VACUUM)\b",
    re.IGNORECASE,
)

# Matches `SELECT *` or `SELECT table.*`, while ignoring `COUNT(*)`
SELECT_STAR_RE = re.compile(
    r"\bSELECT\s+(?:DISTINCT\s+)?(?:[A-Za-z0-9_]+\.)?\*",
    re.IGNORECASE,
)

# Metadata-only queries that do not scan S3 Parquet partitions
METADATA_QUERY_RE = re.compile(
    r"^\s*(SHOW\b|DESCRIBE\b|DESC\b|EXPLAIN\b)|"
    r"\bFROM\s+information_schema\.",
    re.IGNORECASE,
)

# Recognized partition predicates for CUR 2.0, Legacy CUR, FOCUS 1.0/1.2+, and Storage Lens
PARTITION_PREDICATE_RE = re.compile(
    r"\b("
    r"billing_period|"
    r"bill_billing_period_start_date|"
    r"line_item_usage_start_date|"
    r"billingperiodstart|"
    r"chargeperiodstart|"
    r"x_billing_period|"
    r"year|"
    r"month|"
    r"dt|"
    r"record_date"
    r")\b",
    re.IGNORECASE,
)

ATHENA_START_RE = re.compile(r"\bathena\s+start-query-execution\b", re.IGNORECASE)
WORKGROUP_FLAG_RE = re.compile(r"--work-?group\b", re.IGNORECASE)
QUERY_STRING_RE = re.compile(
    r"--query-string\s+(?:'([^']*)'|\"([^\"]*)\"|(\S+))",
    re.IGNORECASE | re.DOTALL,
)


def emit(decision: str | None, message: str) -> None:
    out: dict = {"hookEventName": "PreToolUse"}
    if decision:
        out["permissionDecision"] = decision
        out["permissionDecisionReason"] = message
    else:
        out["additionalContext"] = message
    json.dump({"hookSpecificOutput": out}, sys.stdout)
    sys.exit(0)


def _extract_athena_sql_from_cli(cli: str) -> str:
    m = QUERY_STRING_RE.search(cli)
    if not m:
        return cli
    return next((g for g in m.groups() if g is not None), cli)


def inspect_sql(sql: str, *, is_local_sqlite: bool, has_workgroup: bool = True) -> tuple[str, str] | None:
    """Return ('deny'|'ask', reason) when a SQL query violates FinOps safety or cost rules."""
    cleaned = (sql or "").strip()
    if not cleaned:
        return None

    # 1. Block DDL/DML mutations across all SQL surfaces (Athena, Storage Lens, and session-sql)
    m_ddl = DDL_DML_RE.search(cleaned)
    if m_ddl:
        verb = m_ddl.group(1).upper()
        return (
            "deny",
            f"FinOps SQL Gate: Blocked destructive or mutating SQL keyword '{verb}'. "
            "The FinOps agent is strictly read-only and may only execute SELECT, WITH, SHOW, DESCRIBE, or EXPLAIN queries.",
        )

    # Local SQLite (`billing:session-sql`) has $0.00 scan cost and no S3 partitions
    if is_local_sqlite:
        return None

    # 2. Block `SELECT *` on billable Athena / Storage Lens Parquet tables ($5.00/TB scan cost)
    if SELECT_STAR_RE.search(cleaned):
        return (
            "deny",
            "FinOps Cost Gate: Blocked 'SELECT *' on Amazon Athena / S3 Storage Lens. "
            "CUR 2.0 and FOCUS tables contain 125+ columns in columnar Parquet; 'SELECT *' forces a full-column scan "
            "at $5.00/TB. Explicitly project only the columns required for your analysis.",
        )

    # 3. Allow metadata-only queries (`SHOW`, `DESCRIBE`, `EXPLAIN`, `information_schema`) without partition checks
    if METADATA_QUERY_RE.search(cleaned):
        return None

    # 4. Require partition filter on Athena queries that scan a FROM table
    if re.search(r"\bFROM\b", cleaned, re.IGNORECASE) and not PARTITION_PREDICATE_RE.search(cleaned):
        return (
            "ask",
            "FinOps Cost Warning: Athena SQL query does not include a recognized partition filter "
            "(e.g., `billing_period`, `bill_billing_period_start_date`, `BillingPeriodStart`, `year`/`month`, or `dt`). "
            "Scanning unpartitioned historical CUR/FOCUS data can incur high Athena scan charges ($5.00/TB). Proceed?",
        )

    # 5. Require `--work-group` on CLI Athena executions so BytesScannedCutoffPerQuery applies
    if not has_workgroup:
        return (
            "ask",
            "FinOps Cost Warning: `aws athena start-query-execution` is missing `--work-group` (e.g., `--work-group finops-readonly`). "
            "Running on the default workgroup may bypass per-query byte scan cutoffs. Proceed?",
        )

    return None


def classify_call(tool_name: str, tool_input: dict) -> tuple[str, str] | None:
    name = tool_name or ""
    inp = tool_input if isinstance(tool_input, dict) else {}

    # Case 1: billing:session-sql (local in-process SQLite DB — $0 scan cost, check DDL/DML only)
    if name.endswith("session-sql"):
        query = str(inp.get("query") or "")
        return inspect_sql(query, is_local_sqlite=True)

    # Case 2: billing:storage-lens (executes Athena SQL against S3 Storage Lens manifests)
    if name.endswith("storage-lens"):
        query = str(inp.get("query") or "")
        return inspect_sql(query, is_local_sqlite=False, has_workgroup=True)

    # Case 3: Bash or aws___call_aws running `aws athena start-query-execution`
    cli = ""
    if name == "Bash" or name.lower() in ("shell", "exec_command", "local_shell"):
        cmd = inp.get("command", "")
        cli = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
    elif name.endswith("call_aws"):
        cmd = inp.get("cli_command") or inp.get("command") or ""
        cli = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
    elif name == "use_aws":
        service = str(inp.get("service_name", "")).lower()
        op = str(inp.get("operation_name", "")).lower().replace("_", "-")
        if service == "athena" and op == "start-query-execution":
            params = inp.get("parameters") if isinstance(inp.get("parameters"), dict) else inp
            query = str(params.get("QueryString") or params.get("query_string") or "")
            has_wg = bool(params.get("WorkGroup") or params.get("work_group"))
            return inspect_sql(query, is_local_sqlite=False, has_workgroup=has_wg)

    if cli and ATHENA_START_RE.search(cli):
        has_wg = bool(WORKGROUP_FLAG_RE.search(cli))
        sql = _extract_athena_sql_from_cli(cli)
        return inspect_sql(sql, is_local_sqlite=False, has_workgroup=has_wg)

    return None


def decide(data: dict, env: dict) -> tuple[str | None, str] | None:
    mode = env.get("TALKOPS_FINOPS_SQL_GATE", "").strip().lower()
    mode = mode if mode in MODES else ""
    if mode == "off":
        return None

    tool_name = str(data.get("tool_name", ""))
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    hit = classify_call(tool_name, tool_input)
    if not hit:
        return None

    decision, reason = hit
    if decision == "deny" or mode == "deny":
        return "deny", reason

    is_codex = "turn_id" in data or bool(env.get("PLUGIN_ROOT"))
    if mode == "warn" or (is_codex and mode != "ask"):
        return None, reason
    return "ask", reason


def self_test() -> int:
    tests: list[tuple[str, dict, str | None]] = [
        # 1. Local SQLite `session-sql` allows SELECT * ($0 cost)
        (
            "mcp__plugin_aws-finops-engineer_billing__session-sql",
            {"query": "SELECT * FROM s_cost_explorer LIMIT 10"},
            None,
        ),
        # 2. Local SQLite `session-sql` blocks DROP TABLE
        (
            "mcp__plugin_aws-finops-engineer_billing__session-sql",
            {"query": "DROP TABLE user_notes"},
            "deny",
        ),
        # 3. Storage Lens Athena blocks SELECT *
        (
            "mcp__plugin_aws-finops-engineer_billing__storage-lens",
            {"query": "SELECT * FROM storage_lens_metrics WHERE dt = '2026-04-01'"},
            "deny",
        ),
        # 4. Storage Lens Athena allows projected columns with partition filter
        (
            "mcp__plugin_aws-finops-engineer_billing__storage-lens",
            {"query": "SELECT bucket_name, metric_name, metric_value FROM storage_lens_metrics WHERE dt = '2026-04-01'"},
            None,
        ),
        # 5. Athena CLI via aws___call_aws blocks SELECT *
        (
            "mcp__plugin_aws-finops-engineer_aws-mcp__aws___call_aws",
            {
                "cli_command": (
                    "aws athena start-query-execution "
                    "--query-string \"SELECT * FROM cur_db.cur_table WHERE billing_period = '2026-04'\" "
                    "--work-group finops"
                )
            },
            "deny",
        ),
        # 6. Athena CLI via Bash blocks DELETE FROM
        (
            "Bash",
            {
                "command": (
                    "aws athena start-query-execution "
                    "--query-string \"DELETE FROM cur_db.cur_table WHERE billing_period = '2026-04'\" "
                    "--work-group finops"
                )
            },
            "deny",
        ),
        # 7. Athena CLI asks when partition predicate is missing
        (
            "mcp__plugin_aws-finops-engineer_aws-mcp__aws___call_aws",
            {
                "cli_command": (
                    "aws athena start-query-execution "
                    "--query-string \"SELECT line_item_product_code, SUM(line_item_unblended_cost) FROM cur_db.cur_table GROUP BY 1\" "
                    "--work-group finops"
                )
            },
            "ask",
        ),
        # 8. Athena CLI asks when --work-group is missing
        (
            "Bash",
            {
                "command": (
                    "aws athena start-query-execution "
                    "--query-string \"SELECT line_item_product_code, SUM(line_item_unblended_cost) "
                    "FROM cur_db.cur_table WHERE billing_period = '2026-04' GROUP BY 1\""
                )
            },
            "ask",
        ),
        # 9. Athena CLI passes silently when columns are projected, partitioned, and workgroup is specified
        (
            "mcp__plugin_aws-finops-engineer_aws-mcp__aws___call_aws",
            {
                "cli_command": (
                    "aws athena start-query-execution "
                    "--query-string \"SELECT line_item_product_code, COUNT(*) "
                    "FROM cur_db.cur_table WHERE bill_billing_period_start_date = TIMESTAMP '2026-04-01 00:00:00' GROUP BY 1\" "
                    "--work-group finops-readonly"
                )
            },
            None,
        ),
        # 10. Athena metadata discovery (`information_schema.columns`) passes without partition filter
        (
            "mcp__plugin_aws-finops-engineer_aws-mcp__aws___call_aws",
            {
                "cli_command": (
                    "aws athena start-query-execution "
                    "--query-string \"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'cur_table'\" "
                    "--work-group finops-readonly"
                )
            },
            None,
        ),
        # 11. Unrelated Bash command returns None (does not auto-allow)
        (
            "Bash",
            {"command": "infracost breakdown --path . --format json"},
            None,
        ),
    ]
    failed = 0
    for idx, (t_name, t_inp, want) in enumerate(tests, 1):
        res = decide({"tool_name": t_name, "tool_input": t_inp}, {})
        got = res[0] if res else None
        if got != want:
            print(f"FAIL test #{idx} ({t_name}): got={got!r}, want={want!r} (res={res})")
            failed += 1
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    result = decide(data if isinstance(data, dict) else {}, dict(os.environ))
    if result:
        emit(*result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
