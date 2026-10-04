# IAM guardrails for TalkOps AWS agents

The agents' read-only and approval rules are enforced in three layers. The first two are conveniences; **IAM is the only boundary an agent can't talk its way around.**

| Layer | Where | Covers | Bypassed by |
|---|---|---|---|
| 1. Server flags | `--read-only` on `aws-mcp` for read-only agents; read-only defaults on awslabs servers | MCP tool calls, on every host | The shell (`aws ...`, `terraform ...`) |
| 2. `aws-mutation-gate` hook | `hooks/aws-mutation-gate.py` in every agent plugin | Shell and AWS MCP calls. Deny or ask in Claude Code; warn in Codex | Unusual command forms, scripts the classifier can't see into, hosts without hooks, `TALKOPS_AWS_MUTATION_GATE=off` |
| 3. IAM | Your AWS account | Every API call, from any tool | Nothing |

So configure IAM as if layers 1 and 2 did not exist.

## 1. Give read-only agents read-only credentials

`aws-sre-agent`, `aws-finops-agent`, and `aws-solutions-architect` are marked `aws_read_only`. Run them with a profile whose role only reads:

- Attach the AWS managed policy `ReadOnlyAccess` (broad) or `ViewOnlyAccess` (metadata only, no data reads), plus `AWSBillingReadOnlyAccess` for FinOps.
- Add an explicit deny for data that the agents should never see, even when reading. `ReadOnlyAccess` includes `secretsmanager:GetSecretValue`, `ssm:GetParameter*`, and `s3:GetObject`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenySecretMaterial",
      "Effect": "Deny",
      "Action": [
        "secretsmanager:GetSecretValue",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
        "kms:Decrypt"
      ],
      "Resource": "*"
    }
  ]
}
```

- `aws-sre-agent` bundles `awssupport`, which can create support cases. Add `support:CreateCase` and `support:AddCommunicationToCase` to the deny if case creation should stay with humans.

Point the agent at that profile with `AWS_PROFILE` in the shell that starts your agent host. In Codex, also set it in the server's `env` in `~/.codex/config.toml`, because Codex starts MCP servers with a minimal environment.

## 2. Give write-capable agents scoped credentials

The IaC, platform, serverless, deployment, and database agents can change infrastructure after approval. Don't run them as administrator:

- Use a deployment role scoped to the accounts, regions, and services in play. For CDK, prefer letting CloudFormation assume the bootstrap execution role, and give the agent's own role only `cloudformation:*` on its stacks plus `sts:AssumeRole` on the CDK roles.
- For Terraform, separate the **plan** role (read-only plus state-bucket read and lock-file write) from the **apply** role. Have the agent plan with the plan role, and switch profiles only after the user approves the saved plan.
- Protect state: restrict `s3:PutObject`/`s3:DeleteObject` on the state bucket to the apply role, and turn on versioning.
- Add an SCP or permissions boundary that denies destructive actions on production resources unless a tag or principal you control is present.

## 3. Restrict what the managed AWS MCP server can do

Requests that go through the managed AWS MCP server (`aws-mcp`) carry two IAM condition keys that the caller can't spoof:

- `aws:ViaAWSMCPService` (Boolean) is `true` for any request forwarded by an AWS-managed MCP server.
- `aws:CalledViaAWSMCP` (String) is the service principal of the MCP server that forwarded it, for example `aws-mcp.amazonaws.com`.

To block the write actions you care most about when they come through MCP, while still allowing reads, extend this example:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyHighRiskWritesViaMCP",
      "Effect": "Deny",
      "Action": [
        "iam:*",
        "organizations:*",
        "ec2:Delete*", "ec2:Terminate*", "ec2:Modify*", "ec2:Authorize*", "ec2:Revoke*",
        "s3:Delete*", "s3:PutBucketPolicy", "s3:PutBucketAcl", "s3:PutPublicAccessBlock",
        "rds:Delete*", "rds:Modify*",
        "dynamodb:DeleteTable", "dynamodb:UpdateTable",
        "cloudformation:CreateStack", "cloudformation:UpdateStack", "cloudformation:DeleteStack",
        "cloudformation:ExecuteChangeSet",
        "lambda:Delete*", "lambda:Update*", "lambda:AddPermission",
        "kms:ScheduleKeyDeletion", "kms:DisableKey", "kms:PutKeyPolicy"
      ],
      "Resource": "*",
      "Condition": { "Bool": { "aws:ViaAWSMCPService": "true" } }
    }
  ]
}
```

To deny everything through MCP for a role, use `"Action": "*"` with the same condition. The read-only agents already drop the MCP API-call tools with `--read-only`, so this mainly protects the write-capable agents and the vertical plugins.

> [!IMPORTANT]
> These keys exist only on requests that flow through the managed MCP server. The same agent running `aws ...` or `terraform apply` in its shell sends ordinary requests without them. Use the condition keys to narrow the MCP path, and the role itself (sections 1 and 2) to bound the shell path.

## 4. Audit

- Turn on CloudTrail in every account the agents touch. MCP-forwarded calls can be filtered with the condition-key context, and shell calls show the agent's role session.
- Use a distinct role session name per agent (set `role_session_name = talkops-aws-iac-engineer` in that agent's AWS profile), so CloudTrail shows which agent did what.
