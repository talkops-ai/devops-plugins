---
name: setting-up-ec2-instance-profiles
description: Configures EC2 instances to securely call AWS services by creating and attaching IAM roles via instance profiles, eliminating hardcoded credentials. Use when an EC2 instance needs permissions to access AWS services like S3, DynamoDB, SQS, or CloudWatch through temporary credentials.
version: 1
---

# Setting Up EC2 Instance Profiles

## Overview

Domain expertise for granting EC2 instances secure access to AWS services using IAM roles
and instance profiles. Covers the full lifecycle: identifying required permissions, creating
or reusing IAM roles with least-privilege policies, creating instance profiles, attaching
them to EC2 instances, and verifying credential availability.

## Configure an EC2 instance profile

To set up an IAM role and instance profile for an EC2 instance, follow the procedure exactly.
See [EC2 instance profile setup procedure](references/ec2-instance-profile-setup.md).

## Troubleshooting

### Instance not found

Verify the instance ID and region are correct. List instances with `aws ec2 describe-instances --region <region>`.

### Instance already has a profile

The procedure handles replacement — it will prompt before disassociating the existing profile.

### Credentials not available after attachment

Instance profile propagation can take 30–60 seconds. Applications may need a restart to pick up new credentials.

### Access denied errors

Check that the role's policies include the required actions and resource ARNs. Review CloudTrail logs for the specific denied action.

### Application still uses hardcoded credentials

Remove credentials from config files, environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`), and `~/.aws/credentials`. The SDK default credential chain will then use the instance profile.

## MCP-First Execution, Guardrails & `awsknowledge` Fallback

- **MCP-Only Execution (Zero Raw AWS CLI in Shell)**: When inspecting live EC2 instances, IAM roles, or instance profile associations in the target region, always use connected MCP tools (`aws-mcp` `aws___run_script` / `aws___call_aws`, `awsiac`, `awsknowledge`) in strictly read-only mode. NEVER execute raw `aws` CLI commands via `run_command` / `Bash`.
- **Honest Zero-Resource Reporting**: If `0` EC2 instances (or a non-existent instance ID like `i-0123456789abcdef0`) exist in the target region, report `0` matching instances honestly without fabricating instance state or association IDs, and provide the complete IAM Role + Instance Profile setup workflow.
- **IAM Role vs. Instance Profile & Privilege Escalation Guardrails**:
  - **IAM Role vs. Instance Profile Container**: Explain that an IAM Role (`ec2.amazonaws.com` trust policy with `sts:AssumeRole`) cannot be attached to an EC2 instance directly via the CLI/API; it must be wrapped inside an **IAM Instance Profile** container (`aws iam create-instance-profile` -> `aws iam add-role-to-instance-profile`, which holds at most **1 IAM role** — the AWS Console creates this container automatically, whereas the AWS CLI/SDK does not). Attach to an instance via `aws ec2 associate-iam-instance-profile`, or swap on a running instance without rebooting via `aws ec2 describe-iam-instance-profile-associations` (filtered by `instance-id` to get `AssociationId`) -> `aws ec2 replace-iam-instance-profile-association` (or `disassociate-iam-instance-profile` then `associate-iam-instance-profile`). To delete an old profile, follow the mandatory teardown order: `remove-role-from-instance-profile` -> `delete-instance-profile`, and `detach-role-policy` / `delete-role-policy` -> `delete-role`.
  - **IMDSv2 Token Verification & SDK Default Credential Chain**: Verify credentials inside the instance using two-step IMDSv2 `curl`: (1) `TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")` and (2) `curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>`. AWS SDKs (`boto3`, AWS SDK for JS v3) automatically fetch and rotate these temporary STS credentials via the default credential provider chain — warn that `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` environment variables or `~/.aws/credentials` take higher precedence in the SDK chain and must be removed.
  - **Reject Static AWS Keys on EC2 & Wildcard `iam:PassRole` Escalation**: Strictly forbid storing static `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in `.env` files, environment variables, or `~/.aws/credentials` on EC2, and forbid attaching `*FullAccess` (`AmazonS3FullAccess`) or `AdministratorAccess` managed policies. Explain how granting an operator `iam:PassRole` on `Resource: "*"` alongside `ec2:RunInstances` (or `ec2:AssociateIamInstanceProfile` / `ec2:ReplaceIamInstanceProfileAssociation`) enables **privilege escalation to Admin** (by launching or re-associating an EC2 instance with an Admin role and extracting temporary credentials from IMDS). Enforce scoping `iam:PassRole` to specific approved role ARNs (`arn:aws:iam::<account>:role/app-ec2-*`) with `Condition: {"StringEquals": {"iam:PassedToService": "ec2.amazonaws.com"}}`.
- **Vague Permission Scope Guard**: If the user asks to generate and attach a production IAM policy for an EC2 instance without specifying which AWS services, actions (read vs. write), and specific resource ARNs (bucket names, table names, secret prefixes) the workload needs, refuse to grant wildcard `"Action": "*"` or `"Resource": "*"` permissions and ask for the exact target services and resource ARNs first.
- **Read-Only & Secret Safety (`aws-mutation-gate.py`, `secret-safety.py`)**: Never execute mutating IAM or EC2 commands (`iam create-role`, `iam attach-role-policy`, `iam delete-role`, `ec2 associate-iam-instance-profile`) or fetch plaintext secrets (`secretsmanager get-secret-value`) during read-only inspection.
- **`awsknowledge` Edge-Case Fallback**: If **no** local `references/*.md` file covers the user's specific edge-case question (e.g., Systems Manager Default Host Management Configuration `DHMC` precedence vs. attached instance profiles, or IAM Roles Anywhere for hybrid servers), immediately query the connected `awsknowledge` MCP server (`aws___search_documentation` and `aws___read_documentation` — 1–2 focused searches) and answer directly.
