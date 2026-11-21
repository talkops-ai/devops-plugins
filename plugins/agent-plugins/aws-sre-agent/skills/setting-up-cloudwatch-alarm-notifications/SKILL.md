---
name: setting-up-cloudwatch-alarm-notifications
description: "Sets up notification channels for CloudWatch alarms using SNS topics and subscriptions. Always use this skill when configuring alarm notifications — it creates encrypted SNS topics, configures topic policies for CloudWatch access, sets up email/SMS/webhook subscriptions, and links alarms to notification actions with proper security controls. Query live AWS state via MCP tools only (never raw aws CLI)."
version: 1
---

# Setting Up CloudWatch Alarm Notifications

> **MCP-Only Live AWS Execution:** Perform ALL live AWS API discovery, caller/account verification (`sts:GetCallerIdentity`), resource inspection, logs/metrics queries, pricing (`awspricing`), and docs (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___call_aws` / `aws___run_script`, `cloudwatch`, `cloudtrail`, `prometheus`, `dynamodb`, `serverless`, `awspricing`, `awsknowledge`) — **never invoke raw `aws ...` CLI commands (such as `aws --version` or `aws sts get-caller-identity`) in shell (`run_command`)**.

## Overview

Domain expertise for configuring Amazon CloudWatch alarm notification channels
using Amazon SNS topics and subscriptions. Covers creating encrypted SNS topics,
setting up subscriptions for email, SMS, and webhook endpoints, configuring
topic policies for CloudWatch access, and linking alarms to notification actions.

## Set up alarm notifications

To configure notification channels for a CloudWatch alarm, follow the procedure exactly.
See [CloudWatch alarm notification setup procedure](references/setup-cloudwatch-alarm-notifications.md).

## Troubleshooting

### Email notifications not received

Verify the email subscription was confirmed. Use `aws sns list-subscriptions-by-topic`
to check that the subscription status is "Confirmed" rather than "PendingConfirmation".

### SMS notifications failing

Ensure the phone number is in E.164 format (e.g., +12345678901) and that SMS is
supported in your AWS region.

### Alarm not triggering notifications

Verify the alarm has the correct SNS topic ARN in its AlarmActions using
`aws cloudwatch describe-alarms`, and ensure ActionsEnabled is set to true.
