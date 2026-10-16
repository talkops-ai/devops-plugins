# Preflight Checks

Run these checks directly — do NOT generate a notebook or script for the user. Execute each check yourself and store the results in conversation context for downstream skills.

## Step 1: Check SDK Version

Run:

```bash
python -c "from importlib.metadata import version; print(version('sagemaker'))"
```

- If version ≥ 3.17.0 → the SDK is ready. Report the version and move on. Only upgrade if the user explicitly asks for it.
- If missing or < 3.17.0 → install:

```bash
pip install 'sagemaker>=3.17.0,<4.0' boto3 -q
```

Then re-run the version check to confirm.

> Baseline is `'sagemaker>=3.17.0,<4.0'` (not 3.7.x) — the release that adds fine-tuned support to the deployment-config API (`list_deployment_configs` / `set_deployment_config`) the OSS deploy pathway uses, alongside `@remote` / `@step` decorators and `ModelBuilder`.

### If install fails

STOP. Do NOT proceed with the plan. Tell the user:

- Python ≥ 3.10 is required
- Check pip / virtualenv setup
- Offer to retry once fixed

## Step 2: Resolve Region

Run:

```bash
python -c "import boto3; print(boto3.session.Session().region_name)"
```

- `None` → STOP. Tell user: "Set your region via `export AWS_DEFAULT_REGION={region}` or `aws configure`."
- Set → store `REGION` in context, continue.

## Step 3: Resolve Execution Role

Read and follow `references/execution-role-setup.md`.

Store `ROLE_ARN` in context when done.

## Step 4: Platform & Local MCP Tooling Checks (When Using IaC or Local MCP Servers)

If the user is generating Infrastructure-as-Code (`sagemaker-domain-vpc-iac` / `awsiac` MCP server) or experiencing MCP server startup errors:

1. **macOS Apple Silicon (`arm64`) + `awsiac` (`cfn-guard` / `guardpycfn`)**:
   - `awslabs.aws-iac-mcp-server` compiles `guardpycfn` via Rust (`cargo`). On Apple Silicon Macs (`uname -m == arm64`), `cargo` may fail if the `x86_64-apple-darwin` target is missing.
   - Verify / remediate with:
     ```bash
     rustup target add x86_64-apple-darwin
     ```
2. **Windows Native Shells**:
   - When running `uvx awslabs.<server>@latest` on native Windows (outside WSL2), `uvx` requires explicit package separation and `.exe` suffix:
     ```powershell
     uvx --from awslabs.sagemaker-ai-mcp-server@latest awslabs.sagemaker-ai-mcp-server.exe
     ```

## Step 5: Report Summary

Present a brief status block to the user:

```
Environment ready:
  SDK:    sagemaker <version> ✅
  Region: <region> ✅
  Role:   <arn> ✅
          sagemaker trust ✅ | bedrock trust ⚠️ | lambda trust ✅
```

Downstream skills use `REGION` and `ROLE_ARN` from conversation context. They MUST NOT re-resolve these values.
