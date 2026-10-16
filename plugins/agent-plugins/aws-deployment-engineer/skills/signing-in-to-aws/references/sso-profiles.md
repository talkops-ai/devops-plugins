# AWS IAM Identity Center (`aws sso login`) & Multi-Profile Configuration

## 1. Inspecting Configured Profiles Safely

Never read `~/.aws/credentials` directly. Use AWS CLI metadata commands to inspect configured profile names and credential sources without exposing secrets:

```bash
aws configure list-profiles
aws configure list --profile "${AWS_PROFILE:-default}"
```

## 2. Modern `sso-session` Configuration (`~/.aws/config`)

Organizations using AWS IAM Identity Center should use token-refreshable `sso-session` blocks with `sso_registration_scopes = sso:account:access`:

```ini
[sso-session my-org-sso]
sso_start_url = https://my-org.awsapps.com/start
sso_region = us-east-1
sso_registration_scopes = sso:account:access

[profile dev-deploy]
sso_session = my-org-sso
sso_account_id = 111122223333
sso_role_name = DeploymentEngineerRole
region = us-east-1
output = json
```

## 3. Authenticating & Binding the Profile for MCP Servers

1. Authenticate the SSO session (after user confirmation):
   ```bash
   aws sso login --profile dev-deploy
   ```
2. Verify the resolved caller identity:
   ```bash
   aws sts get-caller-identity --profile dev-deploy
   ```
3. Ensure `AWS_PROFILE` and `AWS_REGION` are exported in the shell or configured in the host's MCP environment (such as `~/.codex/config.toml` for OpenAI Codex) so stdio MCP servers (`awsiac`, `awspricing`, `awsapi`, `cloudwatch`) inherit the active session.
