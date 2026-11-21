# AWS IAM Condition Keys, MCP Principal Governance & SCP Patterns Reference

## 1. Governing Autonomous Agents & AWS MCP Servers (`aws:ViaAWSMCPService` & `aws:CalledViaAWSMCP`)

When an AI agent or developer tool connects through the AWS MCP Server (`aws-mcp`) or AWS service-linked MCP proxies, AWS populates specialized request context keys that Solutions Architects must incorporate into IAM roles and SCPs:

- **`aws:ViaAWSMCPService` (Boolean)**: `true` when a request is made by or routed through an AWS MCP service principal on behalf of the caller.
- **`aws:CalledViaAWSMCP` / `aws:CalledVia` (Array of Strings)**: Identifies downstream calls made by an AWS service or MCP proxy in the call chain.

### Canonical Read-Only Guardrail Statement for Solutions Architect Roles
Attach this explicit `Deny` statement to any IAM role used by `aws-solutions-architect` so even if a broad policy is attached, any request arriving via MCP is strictly restricted to read-only inspection, pricing, Cost Explorer, Compute Optimizer, and Athena read queries:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceReadOnlyForAWSMCP",
      "Effect": "Deny",
      "NotAction": [
        "*:Get*",
        "*:Describe*",
        "*:List*",
        "*:Search*",
        "ce:*",
        "cost-optimization-hub:*",
        "compute-optimizer:*",
        "pricing:*",
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults"
      ],
      "Resource": "*",
      "Condition": {
        "Bool": {
          "aws:ViaAWSMCPService": "true"
        }
      }
    }
  ]
}
```

## 2. High-Value IAM Condition Keys for Enterprise Architecture

| Condition Key | Architectural Purpose | Example Value |
|---|---|---|
| `aws:PrincipalOrgID` | Restrict access strictly to IAM principals belonging to your AWS Organization | `"o-a1b2c3d4e5"` |
| `aws:ResourceOrgID` | Prevent your principals from writing to external S3 buckets/SQS queues/KMS keys (exfiltration defense) | `"o-a1b2c3d4e5"` |
| `aws:SourceVpc` / `aws:SourceVpce` | Bind resource access to a specific VPC or VPC Endpoint | `"vpc-0123456789abcdef0"` |
| `aws:SourceArn` & `aws:SourceAccount` | Prevent Cross-Service Confused Deputy attacks on service trust policies | `"arn:aws:s3:::my-bucket"` |
| `aws:RequestTag/<key>` & `aws:TagKeys` | Enforce mandatory ABAC tags (`Environment`, `Owner`, `CostCenter`) at creation | `"prod"` |
| `kms:ViaService` | Allow KMS key usage only when invoked through a specific regional AWS service | `"s3.us-east-1.amazonaws.com"` |
| `ec2:MetadataHttpTokens` | Require IMDSv2 session tokens on all EC2 `RunInstances` calls | `"required"` |
