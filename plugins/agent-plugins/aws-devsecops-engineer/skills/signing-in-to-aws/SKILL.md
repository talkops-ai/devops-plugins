---
name: signing-in-to-aws
description: >-
  Gets AWS credentials for CLI, SDK, and MCP server access via `aws login` or `aws sso login`,
  validates caller identity across single or multi-account named profiles, and verifies SigV4
  readiness for `mcp-proxy-for-aws`. Activates when a developer needs to authenticate to AWS,
  when an AWS or MCP operation fails due to missing or expired credentials (`ExpiredToken`,
  `NoCredentialsError`, `InvalidClientTokenId`), or when configuring named profiles for
  multi-account DevSecOps operations.
---

# Sign In — Get CLI, SDK & MCP Credentials

Help developers authenticate to AWS for local development and cloud-native MCP execution using short-term, auto-rotating credentials (`aws login` or `aws sso login`). All bundled MCP servers (`aws-mcp`, `aws-security-agent`, `aws-cloudwatch`, `aws-cloudtrail`, `aws-well-architected-security`, `aws-billing`) authenticate locally via standard AWS SigV4 credential chains—no bearer tokens or custom HTTP headers are required.

**Important:**

- You MUST run `aws login`, `aws sso login`, and `aws --version` in the user's local shell — NOT via MCP/API tools.
- You MUST ask the user for confirmation before running `aws login` or `aws sso login`. Do not tell the user to run the command themselves — ask if YOU should run it (e.g., "Ready for me to run `aws login`?" or "Shall I proceed with `aws sso login --profile prod`?"). Wait for their response before proceeding.
- Never read or print `~/.aws/credentials`, `.env`, or secret files.

## Prerequisites

The `aws login` command requires **AWS CLI version 2.32.0 or later**.

```bash
aws --version
```

If the CLI is not installed or is below 2.32.0, inform the user and link them to the [AWS CLI installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).

## Flow

### 1. Lead with the recommendation

In your first response, tell the user that `aws login` (or `aws sso login` if they use IAM Identity Center) is the fix — explain that it provides short-term, auto-rotating credentials used directly by the AWS CLI and all bundled MCP servers.

### 2. Precondition checks (run silently before asking confirmation)

1. `aws --version` — confirm AWS CLI 2.32.0+ is installed.
2. `aws sts get-caller-identity` (or with `--profile <name>` if a target profile was specified) — check current credentials:
   - **Succeeds**: Display `Account`, `Arn`, and active `AWS_REGION` (`aws configure get region`). Ask whether to keep these credentials or authenticate a different profile (`aws login --profile <name>`).
   - **Fails** (`ExpiredToken`, `Unable to locate credentials`, `SSO session token has expired`): check `aws configure list-profiles` to see if an SSO profile is configured; otherwise proceed with `aws login`.
3. *(Only if Step 2 succeeded and the user wants different credentials)* `aws configure list` — if `access_key` starts with `AKIA`, explain that long-term static access keys persist on disk and never expire, whereas `aws login` issues short-term rotating tokens.

### 3. Confirm and run authentication

Ask the user for confirmation specifically for the `aws login` (or `aws sso login --profile <name>`) invocation. Wait for their confirmation, then execute it in the local shell.

### 4. Verify & Multi-Account Profile Check

After login completes, verify caller identity and region:

```bash
aws sts get-caller-identity --output json
aws configure get region
```

If the user operates across multiple environments (`dev`, `staging`, `prod`, `security-audit`), remind them that `aws-mcp` tools (`aws___call_aws`, `aws___run_script`) accept `aws_profile: "<profile-name>"` per call without requiring shell restarts.

## Handling Errors

- **Browser doesn't open**: Suggest `aws login --remote` for cross-device URL/code authentication.
- **Permission error after login**: The IAM principal needs the `SignInLocalDevelopmentAccess` managed policy attached.
- **IAM Identity Center (`aws sso login`)**: Respect existing `~/.aws/config` SSO profiles. If `aws sso login` fails, check expired SSO sessions or `~/.aws/sso/cache/` token state.
- **GovCloud or China regions**: `aws login` is not supported in `aws-us-gov` or `aws-cn`; fall back to `aws sso login` or `aws configure` only when operating in those partitions.
- **CI/CD Pipelines**: Do not use `aws login` for GitHub Actions or GitLab CI — use the `engineering-iam-least-privilege` skill to configure keyless OIDC federation (`sts:AssumeRoleWithWebIdentity`).
