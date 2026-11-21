# Short-Term IAM Role Assumption (`sts:AssumeRole` & OIDC)

## Recommended Short-Term Credential Patterns

1. **Named Profile `role_arn` Chaining**: Configure `source_profile` (or `credential_process`) + `role_arn` in `~/.aws/config` so SDKs and MCP servers refresh temporary `ASIA...` credentials automatically.
2. **CI/CD Workload Identity**: Use OIDC federation (`sts:AssumeRoleWithWebIdentity` for GitHub Actions / GitLab CI / EKS IRSA, or `pods.eks.amazonaws.com` for EKS Pod Identity) — never create static IAM user access keys (`AKIA...`).
3. **Session Scoping**: Set `--duration-seconds` (`900`–`3600`s default) and Descriptive `--role-session-name` values for CloudTrail attribution.
