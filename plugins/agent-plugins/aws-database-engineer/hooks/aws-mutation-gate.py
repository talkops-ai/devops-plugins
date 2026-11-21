#!/usr/bin/env python3
"""aws-mutation-gate: PreToolUse guard for AWS-mutating operations and catastrophic platform anti-patterns.

Works with the Claude Code and Codex hook protocols (same stdin/stdout JSON schema).
Reads the hook event on stdin, classifies the pending tool call, and:

  * catastrophic platform anti-pattern  -> deny (unconditional hard-deny unless mode=off)
      1. Attaching arn:aws:iam::aws:policy/AdministratorAccess to workload roles
      2. Opening 0.0.0.0/0 or ::/0 ingress on SSH (22) or RDP (3389)
      3. Recursive/forced S3 bucket deletion (`aws s3 rm|rb ... --recursive|--force`)
      4. Creating long-lived IAM user access keys (`aws iam create-access-key`)
  * read-only call                      -> no output (the host's normal policy applies)
  * mutating call by an aws_read_only
    agent (Claude Code `agent_type`)    -> deny
  * mutating call, Claude Code          -> ask (forces an explicit human confirmation)
  * mutating call, Codex                -> warning added to the model context

Covered tool calls: shell (`Bash`) commands that run aws, terraform/tofu/terragrunt, cdk,
sam, eksctl, kubectl, helm, copilot, amplify, eb, or agentcore; and AWS MCP calls (`aws___call_aws`,
`aws___run_script`, `aws___get_presigned_url`, `use_aws`, plus mutating tools across bound platform
MCP servers such as `sam_deploy`, `deploy_webapp`, `create_*`, `delete_*`, `update_*`, `put_*`, `attach_*`).

Override with TALKOPS_AWS_MUTATION_GATE=off|warn|ask|deny.

Self-test: python3 aws-mutation-gate.py --self-test
"""

from __future__ import annotations

import ast
import json
import os
import re
import shlex
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("aws-mutation-gate.json")
MODES = {"off", "warn", "ask", "deny"}

# ---------------------------------------------------------------- catastrophic hard-deny patterns
ADMIN_POLICY_RE = re.compile(r"arn:aws(?:-cn|-us-gov)?:iam::aws:policy/AdministratorAccess\b", re.I)
S3_DESTRUCTIVE_RE = re.compile(
    r"\baws\s+(?:--\S+(?:\s+\S+)?\s+)*s3\s+(?:rm|rb)\b.*?(?:--recursive|--force)\b",
    re.I,
)
IAM_ACCESS_KEY_RE = re.compile(
    r"\baws\s+(?:--\S+(?:\s+\S+)?\s+)*iam\s+create-access-key\b",
    re.I,
)
SG_WORLD_ADMIN_PORT_RE = re.compile(
    r"\bauthorize-security-group-ingress\b(?=.*?(?:0\.0\.0\.0/0|::/0))(?=.*?(?:--port\s+(?:22|3389)\b|FromPort['\"\s:=]+(?:22|3389)\b))",
    re.I | re.S,
)

# ---------------------------------------------------------------- aws CLI rules
AWS_VALUE_OPTS = {
    "--profile", "--region", "--output", "--query", "--endpoint-url", "--cli-read-timeout",
    "--cli-connect-timeout", "--color", "--ca-bundle", "--cli-binary-format", "--cli-input-json",
    "--cli-input-yaml",
}
AWS_READ_PREFIXES = (
    "describe-", "get-", "list-", "search-", "lookup-", "batch-get-", "head-", "filter-",
    "validate-", "estimate-", "preview-", "simulate-", "detect-", "query", "scan", "select-",
    "wait", "help", "view-", "show-", "check-", "can-paginate", "verify-",
)
AWS_READ_PAIRS = {
    ("logs", "tail"), ("logs", "start-query"), ("logs", "stop-query"), ("logs", "start-live-tail"),
    ("athena", "start-query-execution"), ("athena", "stop-query-execution"),
    ("eks", "update-kubeconfig"), ("cloudformation", "detect-stack-drift"),
    ("cloudtrail", "start-query"), ("ce", "get-cost-and-usage"),
}
AWS_LOCAL_SERVICES = {"configure", "sso", "login", "logout", "help", "history", "--version"}
S3_READ_OPS = {"ls", "presign"}

# ----------------------------------------------------------- other CLIs
TF_MUTATING = {"apply", "destroy", "import", "taint", "untaint", "force-unlock", "refresh"}
TF_STATE_MUTATING = {"rm", "mv", "push", "replace-provider"}
CDK_MUTATING = {"deploy", "destroy", "bootstrap", "import", "migrate", "watch", "rollback", "gc", "refactor"}
SAM_MUTATING = {"deploy", "delete", "sync", "remote", "publish"}
EKSCTL_MUTATING = {
    "create", "delete", "upgrade", "scale", "set", "unset", "drain", "enable", "disable",
    "update", "register", "deregister", "associate", "disassociate",
}
KUBECTL_MUTATING = {
    "apply", "create", "delete", "edit", "patch", "replace", "scale", "autoscale", "drain",
    "cordon", "uncordon", "taint", "label", "annotate", "set", "expose", "run", "exec", "debug",
}
HELM_MUTATING = {"install", "upgrade", "uninstall", "delete", "rollback", "push"}
COPILOT_MUTATING = {"deploy", "delete", "init"}
AMPLIFY_MUTATING = {"push", "publish", "delete"}
EB_MUTATING = {
    "create", "deploy", "terminate", "setenv", "scale", "clone", "upgrade", "restore",
    "abort", "swap", "config",
}
AGENTCORE_MUTATING = {"deploy", "remove", "destroy", "pause", "resume"}
AGENTCORE_CLOUD_UNLESS_LOCAL = {"dev", "invoke", "run"}
AGENTCORE_MCP_DESTRUCTIVE_PREFIXES = ("delete_", "stop_", "batch_delete_", "clear_")
AGENTCORE_MCP_BILLABLE_PREFIXES = (
    "create_", "update_", "invoke_", "start_", "put_", "batch_create_", "batch_update_",
)
PLATFORM_MCP_MUTATING_PREFIXES = (
    "create_", "delete_", "update_", "put_", "attach_", "detach_", "remove_",
    "apply_", "deploy_", "terminate_", "reboot_", "start_stack_", "execute_",
)
PLATFORM_MCP_MUTATING_EXACT = {
    "sam_deploy", "deploy_webapp", "manage_eks_stacks", "apply_yaml",
}
PLATFORM_MCP_SAFE_EXACT = {
    "create_diagram", "generate_eks_manifest", "validate_cloudformation_template",
    "check_cloudformation_template_compliance", "troubleshoot_cloudformation_deployment",
}

WRAPPERS = {"sudo", "env", "time", "nohup", "command", "exec", "nice"}
RUNNERS = {"npx", "pnpx", "bunx", "pnpm", "yarn", "uvx", "poetry", "uv", "pipx"}
RUNNER_NOISE = {"-y", "--yes", "exec", "run", "dlx", "--"}
SEGMENT_SPLIT = re.compile(r"\$\(|`|&&|\|\||[;&|\n()]")


def _tokens(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def _strip_prefix(toks: list[str]) -> list[str]:
    """Drop env assignments, wrappers, and package runners before the real program."""
    i = 0
    while i < len(toks):
        t = toks[i]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t) or t in WRAPPERS:
            i += 1
        elif t == "aws-vault":
            i = toks.index("--", i) + 1 if "--" in toks[i:] else len(toks)
        elif t in RUNNERS or t in RUNNER_NOISE:
            i += 1
        else:
            break
    toks = toks[i:]
    if toks:
        toks[0] = os.path.basename(toks[0])
    if toks and toks[0] == "aws-cdk":
        toks[0] = "cdk"
    return toks


def _positionals(toks: list[str], value_opts: set[str] = frozenset()) -> list[str]:
    out, skip = [], False
    for t in toks:
        if skip:
            skip = False
            continue
        if t.startswith("-"):
            if t in value_opts:
                skip = True
            continue
        out.append(t)
    return out


def check_catastrophic(tool_name: str, tool_input) -> str | None:
    """Return a hard-deny reason if the tool call matches a catastrophic platform anti-pattern."""
    blob = ""
    if isinstance(tool_input, dict):
        blob = json.dumps(tool_input)
    elif isinstance(tool_input, str):
        blob = tool_input

    # Only enforce on execution/mutation tools (Bash, use_aws, MCP calls), not Read/Grep
    if not (tool_name == "Bash" or tool_name == "use_aws" or tool_name.startswith("mcp__")):
        return None

    if ADMIN_POLICY_RE.search(blob) and any(
        v in blob.lower() for v in ("attach-role-policy", "attach-user-policy", "attach-group-policy", "attach_role_policy")
    ):
        return (
            "HARD DENY: Attaching arn:aws:iam::aws:policy/AdministratorAccess is prohibited by platform security guardrails. "
            "Synthesize a least-privilege IAM policy scoped to specific actions, resource ARNs, and conditions."
        )
    if SG_WORLD_ADMIN_PORT_RE.search(blob):
        return (
            "HARD DENY: Opening 0.0.0.0/0 or ::/0 ingress on SSH (port 22) or RDP (port 3389) is prohibited. "
            "Use AWS Systems Manager Session Manager or EC2 Instance Connect Endpoint instead."
        )
    if S3_DESTRUCTIVE_RE.search(blob):
        return (
            "HARD DENY: Recursive or forced S3 bucket deletion (`aws s3 rm/rb --recursive/--force`) is blocked to prevent data loss."
        )
    if IAM_ACCESS_KEY_RE.search(blob) or (tool_name.endswith("create_access_key")):
        return (
            "HARD DENY: Creating long-lived IAM user access keys (`create-access-key`) is prohibited. "
            "Use IAM Roles, OIDC Federation, EKS Pod Identity, or ECS Task Roles with STS short-lived credentials."
        )
    return None


def classify_aws(args: list[str]) -> bool:
    """True when `aws <args>` mutates AWS. Unknown verbs count as mutating (fail-safe)."""
    if any(a in ("--dry-run", "--dryrun") for a in args):
        return False
    pos = _positionals(args, AWS_VALUE_OPTS)
    if not pos or pos[0] in AWS_LOCAL_SERVICES or "--version" in args:
        return False
    service = pos[0]
    op = pos[1] if len(pos) > 1 else None
    if op is None:
        return False
    if service == "s3":
        return op not in S3_READ_OPS
    if (service, op) in AWS_READ_PAIRS:
        return False
    return not op.startswith(AWS_READ_PREFIXES)


def classify_segment(toks: list[str]) -> str | None:
    """Return a short description when the simple command mutates AWS, else None."""
    toks = _strip_prefix(toks)
    if not toks:
        return None
    prog, args = toks[0], toks[1:]
    pos = _positionals(args)
    sub = pos[0] if pos else ""
    cmd = " ".join(toks)[:200]
    if prog == "aws":
        return cmd if classify_aws(args) else None
    if prog in ("terraform", "tofu"):
        if sub in TF_MUTATING:
            return cmd
        if sub == "state" and len(pos) > 1 and pos[1] in TF_STATE_MUTATING:
            return cmd
        if sub == "workspace" and len(pos) > 1 and pos[1] == "delete":
            return cmd
        return None
    if prog == "terragrunt":
        return cmd if TF_MUTATING.intersection(pos) else None
    if prog == "cdk":
        return cmd if sub in CDK_MUTATING else None
    if prog == "sam":
        return cmd if sub in SAM_MUTATING else None
    if prog == "eksctl":
        if sub in EKSCTL_MUTATING:
            return cmd
        if sub == "utils" and len(pos) > 1 and not pos[1].startswith(("describe-", "get-", "nodegroup-health")):
            return cmd
        return None
    if prog == "kubectl":
        if sub == "rollout":
            return cmd if len(pos) > 1 and pos[1] not in ("status", "history") else None
        return cmd if sub in KUBECTL_MUTATING else None
    if prog == "helm":
        return cmd if sub in HELM_MUTATING else None
    if prog == "copilot":
        return cmd if COPILOT_MUTATING.intersection(pos) else None
    if prog == "amplify":
        return cmd if sub in AMPLIFY_MUTATING else None
    if prog == "eb":
        return cmd if sub in EB_MUTATING else None
    if prog == "agentcore":
        if any(a in ("--help", "-h", "--version") for a in args):
            return None
        if sub in AGENTCORE_MUTATING:
            return cmd
        if sub in AGENTCORE_CLOUD_UNLESS_LOCAL and "--local" not in args and "-l" not in args:
            return cmd
        return None
    return None


def classify_shell(command: str) -> str | None:
    for segment in SEGMENT_SPLIT.split(command or ""):
        if segment.strip():
            hit = classify_segment(_tokens(segment))
            if hit:
                return hit
    return None


def _op_to_kebab(op: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", op)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s)
    return s.replace("_", "-").lower()


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_boto3_arg(call: ast.Call, kw_name: str, pos_idx: int) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg is None:
            return None  # **kwargs cannot be statically proven read-only
        if kw.arg == kw_name:
            return kw.value
    if len(call.args) > pos_idx:
        return call.args[pos_idx]
    return None


def classify_run_script(name: str, inp: dict) -> str | None:
    """Inspect aws___run_script Python AST; allow only provably read-only call_boto3 / pure-Python scripts."""
    code = inp.get("code")
    if not isinstance(code, str) or not code.strip():
        return f"{name} (arbitrary script against AWS)"
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return f"{name} (unparseable script against AWS)"

    # Block dynamic execution/reflection primitives that could obscure AWS mutations
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec", "compile", "__import__"):
                return f"{name} (dynamic {node.func.id} in run_script)"
            if node.func.id == "getattr":
                attr_lit = _const_str(node.args[1]) if len(node.args) >= 2 else None
                tgt = node.args[0] if node.args else None
                bad_tgt = isinstance(tgt, ast.Name) and tgt.id in ("aws_mcp", "builtins", "__builtins__")
                if attr_lit is None or attr_lit == "call_boto3" or bad_tgt:
                    return f"{name} (dynamic getattr in run_script)"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
            if any(m == "aws_mcp" or m.startswith("aws_mcp.") for m in mods):
                # Allow aws_mcp only if every attribute call on aws_mcp is search_functions
                for sub in ast.walk(tree):
                    if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "aws_mcp":
                        if sub.attr not in ("search_functions",):
                            return f"{name} (aws_mcp.{sub.attr} in run_script)"

    boto_name_refs = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "call_boto3"]
    boto_calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "call_boto3"
    ]
    # Disallow aliasing or passing call_boto3 as a first-class value
    if len(boto_name_refs) != len(boto_calls):
        return f"{name} (aliased call_boto3 in run_script)"
    if not boto_calls:
        return None  # Pure Python computation (e.g., CIDR / DNS simulation math) with zero AWS API calls

    # Collect single-assignment constant list/tuple variables (e.g., ops = [("versioning", "GetBucketVersioning"), ...])
    assign_counts: dict[str, int] = {}
    seq_candidates: dict[str, ast.List | ast.Tuple] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    assign_counts[tgt.id] = assign_counts.get(tgt.id, 0) + 1
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        seq_candidates[tgt.id] = node.value
                elif isinstance(tgt, (ast.Tuple, ast.List)):
                    for elt in tgt.elts:
                        if isinstance(elt, ast.Name):
                            assign_counts[elt.id] = assign_counts.get(elt.id, 0) + 1
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)) and isinstance(node.target, ast.Name):
            assign_counts[node.target.id] = assign_counts.get(node.target.id, 0) + 1
    const_seqs = {k: v for k, v in seq_candidates.items() if assign_counts.get(k) == 1}

    def _bind_iter_target(
        target: ast.AST,
        iter_node: ast.AST,
        cur_loops: dict[str, list[str]],
    ) -> dict[str, list[str]]:
        seq_node: ast.List | ast.Tuple | None = None
        if isinstance(iter_node, (ast.List, ast.Tuple)):
            seq_node = iter_node
        elif isinstance(iter_node, ast.Name) and iter_node.id in const_seqs:
            seq_node = const_seqs[iter_node.id]
        if seq_node is None:
            return cur_loops
        new_loops = dict(cur_loops)
        if isinstance(target, ast.Name):
            vals = [_const_str(el) for el in seq_node.elts]
            if vals and all(v is not None for v in vals):
                new_loops[target.id] = [v for v in vals if v is not None]
        elif isinstance(target, (ast.Tuple, ast.List)) and all(isinstance(t, ast.Name) for t in target.elts):
            names = [t.id for t in target.elts if isinstance(t, ast.Name)]
            per_idx: list[list[str]] = [[] for _ in names]
            ok = bool(seq_node.elts)
            for el in seq_node.elts:
                if not (isinstance(el, (ast.Tuple, ast.List)) and len(el.elts) == len(names)):
                    ok = False
                    break
                strs = [_const_str(item) for item in el.elts]
                if any(s is None for s in strs):
                    ok = False
                    break
                for idx, s in enumerate(strs):
                    per_idx[idx].append(s or "")
            if ok:
                for idx, nm in enumerate(names):
                    new_loops[nm] = per_idx[idx]
        return new_loops

    # Map enclosing function definitions and constant for-loop / comprehension bindings for ALL ast.Call nodes
    func_defs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    parent_func: dict[int, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    call_loop_bindings: dict[int, dict[str, list[str]]] = {}

    def _walk_scope(
        node: ast.AST,
        cur_fn: ast.FunctionDef | ast.AsyncFunctionDef | None,
        cur_loops: dict[str, list[str]],
    ) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_defs[node.name] = node
            cur_fn = node
        if isinstance(node, ast.For):
            cur_loops = _bind_iter_target(node.target, node.iter, cur_loops)
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            comp_loops = dict(cur_loops)
            for gen in node.generators:
                comp_loops = _bind_iter_target(gen.target, gen.iter, comp_loops)
            cur_loops = comp_loops
        if isinstance(node, ast.Call):
            if cur_fn is not None:
                parent_func[id(node)] = cur_fn
            call_loop_bindings[id(node)] = cur_loops
        for child in ast.iter_child_nodes(node):
            _walk_scope(child, cur_fn, cur_loops)

    _walk_scope(tree, None, {})

    def _resolve_expr_strs(expr: ast.AST | None, call_id: int) -> list[str] | None:
        if expr is None:
            return None
        lit = _const_str(expr)
        if lit is not None:
            return [lit]
        if isinstance(expr, ast.Name):
            bound = call_loop_bindings.get(call_id, {}).get(expr.id)
            if bound:
                return bound
        return None

    def _resolve_fn_arg(call_node: ast.Call, param_names: list[str], target_param: str) -> list[str] | None:
        for kw in call_node.keywords:
            if kw.arg is None:
                return None
            if kw.arg == target_param:
                return _resolve_expr_strs(kw.value, id(call_node))
        if target_param in param_names:
            idx = param_names.index(target_param)
            if len(call_node.args) > idx:
                return _resolve_expr_strs(call_node.args[idx], id(call_node))
        return None

    resolved_pairs: list[tuple[str, str]] = []
    for bcall in boto_calls:
        if any(kw.arg is None for kw in bcall.keywords):
            return f"{name} (**kwargs in call_boto3)"
        svc_node = _extract_boto3_arg(bcall, "service_name", 0)
        op_node = _extract_boto3_arg(bcall, "operation_name", 1)
        if svc_node is None or op_node is None:
            return f"{name} (missing service/operation in call_boto3)"

        svcs = _resolve_expr_strs(svc_node, id(bcall))
        ops = _resolve_expr_strs(op_node, id(bcall))
        if svcs and ops:
            for s in svcs:
                for o in ops:
                    resolved_pairs.append((s, o))
            continue

        # Check wrapper function parameters resolved at all wrapper call sites
        enclosing = parent_func.get(id(bcall))
        if enclosing is not None:
            pnames = [a.arg for a in enclosing.args.posonlyargs + enclosing.args.args]
            kwonly = [a.arg for a in enclosing.args.kwonlyargs]
            all_params = pnames + kwonly
            svc_param = svc_node.id if isinstance(svc_node, ast.Name) and svc_node.id in all_params else None
            op_param = op_node.id if isinstance(op_node, ast.Name) and op_node.id in all_params else None
            if (svcs is not None or svc_param is not None) and (ops is not None or op_param is not None):
                fn_refs = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == enclosing.name]
                fn_calls = [
                    n for n in ast.walk(tree)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == enclosing.name
                ]
                if len(fn_refs) != len(fn_calls):
                    return f"{name} (aliased wrapper {enclosing.name} in run_script)"
                for fcall in fn_calls:
                    s_vals = svcs if svcs is not None else _resolve_fn_arg(fcall, pnames, svc_param or "")
                    o_vals = ops if ops is not None else _resolve_fn_arg(fcall, pnames, op_param or "")
                    if not s_vals or not o_vals:
                        return f"{name} (dynamic wrapper {enclosing.name} call in run_script)"
                    for s_v in s_vals:
                        for o_v in o_vals:
                            resolved_pairs.append((s_v, o_v))
                continue

        return f"{name} (dynamic call_boto3 arguments in run_script)"

    for svc, op in resolved_pairs:
        svc_cli = "s3api" if svc == "s3" else svc
        kebab_op = _op_to_kebab(op)
        if classify_aws([svc_cli, kebab_op]):
            return f"aws {svc} {kebab_op} (in run_script)"
    return None


def classify_tool(tool_name: str, tool_input) -> str | None:
    name = tool_name or ""
    inp = tool_input if isinstance(tool_input, dict) else {}
    if name == "Bash" or name.lower() in ("shell", "exec_command", "local_shell"):
        command = inp.get("command", "")
        if isinstance(command, list):
            command = " ".join(command)
        return classify_shell(str(command))
    if name.endswith("run_script"):
        return classify_run_script(name, inp)
    if name.endswith("get_presigned_url"):
        method = str(inp.get("http_method") or inp.get("method") or "").upper()
        return None if method in ("", "GET", "HEAD") else f"{name} ({method} URL)"
    if name.endswith("call_aws"):
        cli = inp.get("cli_command") or inp.get("command") or ""
        if isinstance(cli, list):
            cli = " ".join(cli)
        cli = str(cli).strip()
        if not cli:
            return f"{name} (unparseable input)"
        toks = _tokens(cli)
        if toks and toks[0] == "aws":
            toks = toks[1:]
        return cli[:200] if classify_aws(toks) else None
    if name == "use_aws":
        service = str(inp.get("service_name", ""))
        service = "s3api" if service == "s3" else service
        op = str(inp.get("operation_name", "")).replace("_", "-")
        return f"aws {service} {op}" if classify_aws([service, op]) else None
    if "agentcore" in name:
        short = name.rsplit("__", 1)[-1]
        if short.startswith(AGENTCORE_MCP_DESTRUCTIVE_PREFIXES):
            return f"{short} (WARNING: destructive AgentCore operation)"
        if short.startswith(AGENTCORE_MCP_BILLABLE_PREFIXES):
            return f"{short} (COST WARNING: billable AgentCore mutation or invocation)"
    if name.startswith("mcp__"):
        short = name.rsplit("__", 1)[-1]
        if short in PLATFORM_MCP_SAFE_EXACT:
            return None
        if short in PLATFORM_MCP_MUTATING_EXACT or short.startswith(PLATFORM_MCP_MUTATING_PREFIXES):
            return f"{short} (MCP mutation)"
    return None


# ---------------------------------------------------------------- decisions
def load_read_only_agents() -> set[str]:
    try:
        data = json.loads(CONFIG_PATH.read_text())
        return {str(a) for a in data.get("read_only_agents", [])}
    except (OSError, ValueError):
        return set()


def emit(decision: str | None, message: str) -> None:
    out: dict = {"hookEventName": "PreToolUse"}
    if decision:
        out["permissionDecision"] = decision
        out["permissionDecisionReason"] = message
    else:
        out["additionalContext"] = message
    json.dump({"hookSpecificOutput": out}, sys.stdout)
    sys.exit(0)


def decide(data: dict, env: dict) -> tuple[str | None, str] | None:
    """Return (decision, message), (None, message) for a warning, or None to stay silent."""
    mode = env.get("TALKOPS_AWS_MUTATION_GATE", "").strip().lower()
    mode = mode if mode in MODES else ""
    if mode == "off":
        return None
    tool_name = str(data.get("tool_name", ""))
    tool_input = data.get("tool_input")

    # 1. Check catastrophic platform anti-patterns first (unconditional deny)
    catastrophic = check_catastrophic(tool_name, tool_input)
    if catastrophic:
        return "deny", catastrophic

    agent = str(data.get("agent_type") or "")
    agent_name = agent.split(":")[-1]
    read_only = agent_name in load_read_only_agents()
    try:
        hit = classify_tool(tool_name, tool_input)
    except Exception as exc:  # noqa: BLE001
        if read_only:
            return "deny", f"aws-mutation-gate could not classify this call ({exc}); failing closed for read-only agent {agent_name}."
        return None
    if not hit:
        return None
    if read_only:
        return "deny", (
            f"{agent_name} is a read-only AWS agent and may not run mutating operations: {hit}. "
            "Return the proposed change to the caller and hand off to an agent that owns the change."
        )
    if mode == "deny":
        return "deny", f"Mutating AWS operation blocked by TALKOPS_AWS_MUTATION_GATE=deny: {hit}"
    is_codex = "turn_id" in data or bool(env.get("PLUGIN_ROOT"))
    if mode == "warn" or (is_codex and mode != "ask"):
        return None, (
            f"aws-mutation-gate: `{hit}` changes AWS resources. Only proceed if the user explicitly approved "
            "this exact change (plan, diff, or change set) in this conversation; otherwise stop and ask."
        )
    return "ask", f"Mutating AWS operation — confirm the user approved this exact change: {hit}"


def self_test() -> int:
    cases = {
        "aws ec2 describe-instances --region us-east-1": False,
        "aws --profile prod s3 ls s3://bucket": False,
        "aws s3 cp a.txt s3://b/": True,
        "AWS_PROFILE=x aws ec2 terminate-instances --instance-ids i-1": True,
        "aws ec2 run-instances --dry-run --image-id ami-1": False,
        "aws logs tail /aws/lambda/x --follow": False,
        "aws sts get-caller-identity && aws iam create-user --user-name x": True,
        "terraform plan -out tf.plan": False,
        "terraform -chdir=infra apply tf.plan": True,
        "terraform state list": False,
        "terraform state rm aws_s3_bucket.b": True,
        "npx cdk diff": False,
        "npx aws-cdk deploy --all": True,
        "sam build && sam validate": False,
        "kubectl get pods -A | grep x": False,
        "kubectl rollout restart deploy/x": True,
        "helm upgrade --install x chart/": True,
        "eksctl get clusters": False,
        "echo aws ec2 delete-vpc": False,
        "aws-vault exec prod -- aws ec2 delete-vpc --vpc-id v": True,
        "agentcore status": False,
        "agentcore doctor": False,
        "agentcore invoke --local --prompt hello": False,
        "agentcore invoke --prompt hello": True,
        "agentcore deploy -y": True,
        "agentcore remove memory --name MyMem": True,
        "eb status": False,
        "eb health --refresh": False,
        "eb create prod-env --single": True,
        "eb deploy prod-env": True,
        "eb terminate prod-env --force": True,
    }
    bad = [c for c, want in cases.items() if bool(classify_shell(c)) != want]
    mcp = [
        ("mcp__plugin_x_aws-mcp__aws___call_aws", {"cli_command": "aws ec2 describe-vpcs"}, False),
        ("mcp__plugin_x_aws-mcp__aws___call_aws", {"cli_command": "aws ec2 delete-vpc --vpc-id v"}, True),
        ("mcp__aws-mcp__aws___run_script", {"script": "..."}, True),
        ("mcp__aws-mcp__aws___run_script", {"code": "result = await call_boto3(service_name='ec2', operation_name='DescribeVpcs')\nresult"}, False),
        ("mcp__aws-mcp__aws___run_script", {"code": "async def safe_call(s, o):\n    return await call_boto3(service_name=s, operation_name=o)\nresult = await safe_call('ec2', 'DescribeVpcAttribute')\nresult"}, False),
        ("mcp__aws-mcp__aws___run_script", {"code": "import ipaddress\nresult = str(ipaddress.ip_network('10.0.0.0/16'))\nresult"}, False),
        ("mcp__aws-mcp__aws___run_script", {"code": "async def safe_call(s, o):\n    return await call_boto3(service_name=s, operation_name=o)\nresult = await safe_call('ec2', 'DeleteVpc')\nresult"}, True),
        ("mcp__aws-mcp__aws___run_script", {"code": "result = await call_boto3(service_name='fsx', operation_name='UpdateFileSystem')\nresult"}, True),
        ("use_aws", {"service_name": "s3", "operation_name": "list_buckets"}, False),
        ("mcp__plugin_aws-agentcore-engineer_agentcore__search_agentcore_docs", {"query": "memory"}, False),
        ("mcp__plugin_aws-agentcore-engineer_agentcore__get_agent_runtime", {"agentRuntimeId": "r-1"}, False),
        ("mcp__plugin_aws-agentcore-engineer_agentcore__create_agent_runtime", {"agentRuntimeName": "r"}, True),
        ("mcp__plugin_aws-agentcore-engineer_agentcore__delete_memory", {"memoryId": "m-1"}, True),
        ("mcp__plugin_aws-platform-engineer_serverless__sam_deploy", {"project_directory": "."}, True),
        ("mcp__plugin_aws-platform-engineer_aws-iac__validate_cloudformation_template", {"template_content": "{}"}, False),
    ]
    bad += [f"{n} {i}" for n, i, want in mcp if bool(classify_tool(n, i)) != want]

    # Verify catastrophic hard-deny checks
    cat_cases = [
        ("Bash", {"command": "aws iam attach-role-policy --role-name r --policy-arn arn:aws:iam::aws:policy/AdministratorAccess"}, True),
        ("Bash", {"command": "aws ec2 authorize-security-group-ingress --group-id sg-1 --protocol tcp --port 22 --cidr 0.0.0.0/0"}, True),
        ("Bash", {"command": "aws s3 rm s3://my-bucket --recursive"}, True),
        ("Bash", {"command": "aws iam create-access-key --user-name bob"}, True),
        ("Bash", {"command": "aws ec2 describe-security-groups"}, False),
    ]
    bad += [f"catastrophic:{n} {i}" for n, i, want in cat_cases if bool(check_catastrophic(n, i)) != want]

    for b in bad:
        print(f"FAIL {b}")
    total = len(cases) + len(mcp) + len(cat_cases)
    print(f"{total - len(bad)}/{total} passed")
    return 1 if bad else 0


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
