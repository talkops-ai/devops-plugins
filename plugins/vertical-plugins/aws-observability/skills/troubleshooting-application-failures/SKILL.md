---
name: troubleshooting-application-failures
description: "Troubleshoots failing applications by discovering and analyzing CloudWatch log groups to identify error patterns, root causes, and actionable solutions. Use when an application is experiencing failures and log-based diagnosis is needed. Query live AWS state via MCP tools only (never raw aws CLI)."
version: 1
---

# Application Failure Troubleshooting

> **MCP-Only Live AWS Execution:** Perform ALL live AWS API discovery, caller/account verification (`sts:GetCallerIdentity`), resource inspection, logs/metrics queries, pricing (`awspricing`), and docs (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___call_aws` / `aws___run_script`, `cloudwatch`, `cloudtrail`, `prometheus`, `dynamodb`, `serverless`, `awspricing`, `awsknowledge`) — **never invoke raw `aws ...` CLI commands (such as `aws --version` or `aws sts get-caller-identity`) in shell (`run_command`)**.

## Overview

Domain expertise for diagnosing application failures through CloudWatch log analysis.
Discovers relevant log groups, searches for error patterns and stack traces, performs
root cause analysis, and generates prioritized remediation recommendations.

## Troubleshoot a failing application

To diagnose and resolve application failures using CloudWatch logs, follow the
procedure exactly. See [Application failure troubleshooting procedure](references/application-failure-troubleshooting.md).

## Troubleshooting

### No log groups found

Ask the user for specific log group names. Common patterns: `/aws/lambda/function-name`,
`/aws/apigateway/api-name`, or custom application log groups.

### Access denied errors

Verify AWS credentials have `logs:DescribeLogGroups`, `logs:DescribeLogStreams`,
`logs:StartQuery`, and `logs:GetQueryResults` permissions.

### Query timeouts

Reduce the time window or limit results. Large log groups may require multiple smaller queries.
