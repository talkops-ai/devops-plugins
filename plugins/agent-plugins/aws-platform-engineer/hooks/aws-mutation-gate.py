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


def classify_tool(tool_name: str, tool_input) -> str | None:
    name = tool_name or ""
    inp = tool_input if isinstance(tool_input, dict) else {}
    if name == "Bash" or name.lower() in ("shell", "exec_command", "local_shell"):
        command = inp.get("command", "")
        if isinstance(command, list):
            command = " ".join(command)
        return classify_shell(str(command))
    if name.endswith("run_script"):
        return f"{name} (arbitrary script against AWS)"
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
