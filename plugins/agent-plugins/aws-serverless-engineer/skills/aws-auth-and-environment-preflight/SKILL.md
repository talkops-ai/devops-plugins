---
name: aws-auth-and-environment-preflight
description: Verify AWS credentials, IAM identity, region configuration, and local serverless toolchain readiness (SAM CLI, AWS CDK, Docker daemon, AWS CLI v2). Guides users through signing in with aws login, AWS IAM Identity Center (aws sso login), or IAM roles before running MCP tools or deployments.
---

# AWS Authentication & Serverless Environment Preflight

Authenticate to AWS and verify local toolchain readiness before executing MCP server tools, local invokes, or cloud deployments.

## When to Use

- Before running any live AWS inspection, local container invoke (`sam_local_invoke`), DynamoDB Local validation (`dynamodb_data_model_validation`), or deployment (`sam_deploy`, `deploy_webapp`)
- When AWS CLI or MCP tools fail with `Unable to locate credentials`, `ExpiredTokenException`, `Token has expired`, `NoRegionError`, or `AccessDeniedException`
- When setting up a new developer workstation or switching AWS accounts/profiles

---

## Step 1: Run the Non-Destructive Preflight Check

Run this single read-only preflight check to inspect identity, active region, and local serverless tooling:

```bash
echo "=== 1. AWS Credentials & Identity ===" && \
aws sts get-caller-identity 2>&1 || true
echo "=== 2. Active Region & Profile ===" && \
echo "AWS_PROFILE=${AWS_PROFILE:-default} | AWS_REGION=${AWS_REGION:-$(aws configure get region 2>/dev/null || echo 'UNSET (fallback: us-east-1)')}"
echo "=== 3. Serverless Toolchain ===" && \
aws --version 2>&1 && \
(sam --version 2>&1 || echo "SAM CLI: not installed") && \
(cdk --version 2>&1 || echo "AWS CDK: not installed") && \
(docker info --format 'Docker Server: {{.ServerVersion}}' 2>&1 || echo "Docker Daemon: not running / not installed")
```

### Portable Region Fallback Rule (`AWS_REGION`)
Portable MCP hosts (such as Codex using `mcp.json`) do not expand `${AWS_REGION:-us-east-1}` default syntax in static JSON configs. If `AWS_REGION` and `AWS_DEFAULT_REGION` are unset in the shell and no default region is configured in `~/.aws/config`:
- Export `export AWS_REGION=us-east-1` (or the user's target region) in the shell environment, OR
- Pass the explicit `region` parameter directly to MCP tool calls (`sam_deploy`, `get_metrics`, `aws-pricing`, etc.).

### Docker Daemon Readiness Rule
Docker (or an OCI-compatible runtime like Finch/Colima) must be running when using:
- `sam_local_invoke` (testing Lambda functions locally in a Lambda runtime container)
- `sam_build` with `use_container=true` (compiling native C/Rust/Python wheels for Linux `arm64`/`x86_64`)
- `dynamodb_data_model_validation` (automatically spins up DynamoDB Local in Docker/Podman/Finch/nerdctl)

---

## Step 2: Inspect Existing AWS Configuration (If Unauthenticated)

If `aws sts get-caller-identity` fails, inspect the existing profile configuration before prompting the user:

```bash
aws configure list
aws configure list-profiles 2>/dev/null
```

- **If `aws configure list` shows expired SSO or `aws login` credentials**: Refresh the session directly (see Step 3).
- **If named profiles exist in `~/.aws/config`**: Ask the user which profile corresponds to their target environment (`export AWS_PROFILE=<profile-name>`).

---

## Step 3: Choose the Right Sign-In Method

Recommend **`aws login`** as the default for individual developers and console users:

| Situation | Recommended Method | Command |
|---|---|---|
| Console user, new setup, or unsure | **`aws login`** (browser-based sign-in with console credentials; no access keys to manage) | `aws login` |
| Organization uses AWS IAM Identity Center (SSO) (`sso_start_url` in `~/.aws/config`) | **IAM Identity Center** | `aws sso login --profile <profile>` |
| CI/CD runner or headless server without browser access | **IAM Role Assumption / OIDC / Access Keys** | `aws configure` or `AWS_ROLE_ARN` |

> **Security Rule:** Never ask the user to paste `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` into the chat window. Always instruct them to run credential commands in their own terminal or use browser-based `aws login` / `aws sso login`.

### Method A: `aws login` (Recommended Default — AWS CLI v2.32.0+)

1. Verify AWS CLI version is `>= 2.32.0` (`aws --version`). If older, upgrade first:
   - **macOS (Homebrew)**: `brew upgrade awscli`
   - **Linux (x86_64)**: `curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip" && unzip -q -o /tmp/awscliv2.zip -d /tmp && sudo /tmp/aws/install --update`
   - **Linux (ARM64)**: `curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "/tmp/awscliv2.zip" && unzip -q -o /tmp/awscliv2.zip -d /tmp && sudo /tmp/aws/install --update`
2. Run `aws login` (or `aws login --profile <name>`).
3. Complete the browser approval flow and verify with `aws sts get-caller-identity`.

### Method B: IAM Identity Center (`aws sso login`)

If the profile in `~/.aws/config` already defines `sso_start_url` or `sso_session`:
```bash
aws sso login --profile <profile-name>
export AWS_PROFILE=<profile-name>
aws sts get-caller-identity
```

If configuring SSO for the first time, run `aws configure sso` and supply the organization's SSO start URL and region.

---

## Step 4: Verify IAM Permissions for Serverless Deployment

Before running `sam_deploy` or `deploy_webapp`, ensure the authenticated principal has permissions to manage CloudFormation stacks (`cloudformation:*`), S3 deployment artifacts, IAM execution roles (`iam:CreateRole`, `iam:PassRole`, `iam:AttachRolePolicy`), and the target serverless services (`lambda:*`, `apigateway:*`, `dynamodb:*`, `states:*`, `events:*`, `sqs:*`, `sns:*`, `logs:*`).
