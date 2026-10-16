---
name: setup
description: >-
  Configures and verifies the AWS DevSecOps Engineer plugin environment: checks `uvx` and AWS CLI
  prerequisites, verifies SigV4 credentials and named AWS profiles, validates bundled MCP servers
  (`aws-mcp`, `aws-security-agent`, `aws-cloudwatch`, `aws-cloudtrail`, `aws-well-architected-security`,
  `aws-billing`), checks `aws:CalledViaAWSMCP` IAM safety guardrails, and optionally initializes
  AWS Security Agent spaces via `setup-security-agent`. Use when the user asks to "set up the
  devsecops plugin", "configure aws-devsecops-engineer", "verify MCP setup", or runs `/setup`.
---

# AWS DevSecOps Engineer — Environment Setup & Readiness Verification

This skill performs a fast, non-destructive readiness check of your local AWS DevSecOps environment and guides you through any missing prerequisites. Unlike legacy AgentSpace setups, `aws-devsecops-engineer` connects directly to AWS services using your local AWS SigV4 credentials (`aws login` or `aws sso login`) — no bearer tokens or external webhook registrations are required.

## Step 1: Verify Local Tooling Prerequisites

Run a single shell check to verify required CLI binaries:

```bash
aws --version && uvx --version && python3 --version
```

- **AWS CLI (`aws`)**: Version `2.32.0+` is recommended (required for `aws login` and `aws securityagent` operations).
- **`uvx` (from Astral `uv`)**: Required to launch the stdio MCP servers (`mcp-proxy-for-aws-cli`, `awslabs.security-agent-mcp-server`, `awslabs.cloudwatch-mcp-server`, `awslabs.cloudtrail-mcp-server`, `awslabs.well-architected-security-mcp-server`, `awslabs.billing-cost-management-mcp-server`). If `uvx` is missing, offer to install `uv` via `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`.

## Step 2: Verify AWS Identity, Region & Named Profiles

Check active AWS credentials and configured profiles:

```bash
aws sts get-caller-identity --output json
aws configure get region
aws configure list-profiles
```

- If `aws sts get-caller-identity` fails, invoke the `signing-in-to-aws` skill to authenticate via `aws login` or `aws sso login`.
- Confirm `AWS_REGION` is set (defaults to `us-east-1` in `.mcp.json`; portable hosts such as Codex should export `AWS_REGION` in the shell environment).
- List available named profiles (`staging`, `prod`, `security`, etc.) that can be targeted dynamically via `aws_profile` in `aws-mcp`.

## Step 3: Verify MCP Server Connectivity

Test that `aws-mcp` is reachable and authenticated by calling `aws___call_aws` with a read-only STS check:

```
Tool: aws___call_aws
Arguments:
  cli_command: "aws sts get-caller-identity"
```

Verify the 6 bundled MCP servers declared in `.mcp.json` / `mcp.json`:
1. **`aws-mcp`**: Full AWS control-plane CLI (`aws___call_aws`), sandboxed multi-step boto3 scripts (`aws___run_script`), documentation search (`aws___search_documentation`), and SOP skill retrieval (`aws___retrieve_skill`).
2. **`aws-security-agent`**: Application security posture — SAST code scans, git diff scans, STRIDE threat modeling, and DAST penetration testing.
3. **`aws-cloudwatch`**: Metrics, active alarms, Logs Insights queries, and Application Signals / X-Ray triage.
4. **`aws-cloudtrail`**: Management and data event lookup plus CloudTrail Lake SQL forensics.
5. **`aws-well-architected-security`**: Well-Architected Security Pillar reviews and multi-service posture checks.
6. **`aws-billing`**: Cost Explorer queries, cost anomaly detection, AWS Budgets, and Savings Plans / RI analysis.

## Step 4: Recommend `aws:CalledViaAWSMCP` IAM Guardrail Policy

For production accounts, recommend attaching a defense-in-depth IAM Deny statement (or AWS Organizations SCP) using the `aws:CalledViaAWSMCP` condition key so that even if a human accidentally approves a destructive prompt, IAM blocks catastrophic deletions initiated via MCP:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyDestructiveActionsViaMCP",
      "Effect": "Deny",
      "Action": [
        "iam:Delete*",
        "iam:CreateAccessKey",
        "organizations:*",
        "account:*",
        "s3:DeleteBucket",
        "rds:DeleteDBInstance",
        "rds:DeleteDBCluster",
        "dynamodb:DeleteTable",
        "kms:ScheduleKeyDeletion",
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail"
      ],
      "Resource": "*",
      "Condition": {
        "Bool": {
          "aws:CalledViaAWSMCP": "true"
        }
      }
    }
  ]
}
```

## Step 5: Optional AWS Security Agent Onboarding

Ask the user whether they also want to run application SAST code scans, STRIDE threat modeling, or DAST penetration testing with AWS Security Agent (`aws securityagent`).
- If **yes**, invoke the `setup-security-agent` skill to discover or provision an AWS Security Agent application, Agent Space, `SecurityAgentScanRole`, and S3 artifact bucket.
- If **no** (e.g., they only need CloudWatch incident triage, IAM least-privilege engineering, Security Hub/GuardDuty CSPM triage, CloudTrail forensics, IaC hardening, release readiness, or FinOps), setup is complete! Present a concise readiness table showing Account ID, Region, Active Profile(s), and verified MCP servers.
