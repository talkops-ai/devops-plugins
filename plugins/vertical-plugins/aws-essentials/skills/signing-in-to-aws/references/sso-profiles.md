# AWS IAM Identity Center (SSO) & Named Profile Configuration

## Standard SSO Login & Profile Verification

1. Inspect configured profiles in `~/.aws/config` (`aws configure list-profiles` — never read `~/.aws/credentials`).
2. Authenticate via `aws login` or `aws sso login --profile <profile-name>`.
3. Verify active session identity using `aws sts get-caller-identity --profile <profile-name>` (or connected `aws-mcp` read-only identity check).
4. Export `AWS_PROFILE=<profile-name>` and `AWS_REGION=<region>` for downstream CLI, SDK, and stdio MCP processes.
