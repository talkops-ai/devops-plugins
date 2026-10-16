# IAM Role Assumption (`sts:AssumeRole`) & CI/CD OIDC Federation

## 1. Cross-Account Role Chaining in `~/.aws/config`

When deploying from a central identity or workstation profile into a target workload account via `sts:AssumeRole`, configure `source_profile` in `~/.aws/config` rather than exporting raw temporary credentials in shell history:

```ini
[profile workload-prod]
role_arn = arn:aws:iam::222233334444:role/CrossAccountDeploymentRole
source_profile = dev-deploy
role_session_name = aws-deployment-agent
region = us-west-2
```

Verify role assumption via:

```bash
aws sts get-caller-identity --profile workload-prod
```

## 2. CI/CD Pipelines: Use OIDC Federation (Never `aws login` or Static `AKIA` Keys)

Never use `aws login` or long-lived IAM User access keys (`AKIA*`) inside GitHub Actions, GitLab CI, or Bitbucket Pipelines. Always provision an IAM OIDC Identity Provider (`token.actions.githubusercontent.com`) and an IAM Role with a strict `sub` and `aud` condition:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:ref:refs/heads/main"
        }
      }
    }
  ]
}
```
