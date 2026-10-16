# AWS Data Perimeter, SCP, RCP & Declarative Policy Blueprints

## 1. The Three AWS Data Perimeter Invariants

| Data Perimeter Objective | Primary Policy Type | Condition Keys Used |
|---|---|---|
| **1. Only Trusted Identities can access our resources** | **Resource Control Policy (RCP)** + Resource Policies | `aws:PrincipalOrgID == "${org-id}"` (with `aws:PrincipalIsAWSService == "false"` exemption) |
| **2. Our principals can only access Trusted Resources** | **Service Control Policy (SCP)** + VPC Endpoint Policies | `aws:ResourceOrgID == "${org-id}"` |
| **3. Our principals/resources can only be accessed from Expected Networks** | **SCP + RCP** | `aws:SourceVpc` / `aws:VpceOrgID == "${org-id}"` (with `aws:ViaAWSService == "true"` exemption) |

## 2. Production Resource Control Policy (RCP) — Enforce Trusted Org Identities on S3/SQS/KMS/Secrets

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceOrgIdentitiesDataPerimeter",
      "Effect": "Deny",
      "Principal": "*",
      "Action": [
        "s3:*",
        "sqs:*",
        "kms:*",
        "secretsmanager:*",
        "sts:AssumeRole"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEqualsIfExists": {
          "aws:PrincipalOrgID": "o-exampleorgid"
        },
        "BoolIfExists": {
          "aws:PrincipalIsAWSService": "false"
        }
      }
    }
  ]
}
```

## 3. Production Service Control Policy (SCP) — Region Lock, Security Guardrails & MCP Safety

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyLeavingOrgAndDisablingAudit",
      "Effect": "Deny",
      "Action": [
        "organizations:LeaveOrganization",
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail",
        "guardduty:DeleteDetector",
        "guardduty:DisassociateFromMasterAccount",
        "securityhub:DisableSecurityHub",
        "config:StopConfigurationRecorder",
        "s3:PutAccountPublicAccessBlock"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyNonApprovedRegionsExceptGlobalServices",
      "Effect": "Deny",
      "NotAction": [
        "iam:*",
        "organizations:*",
        "sts:*",
        "route53:*",
        "cloudfront:*",
        "wafv2:*",
        "shield:*",
        "support:*",
        "ce:*",
        "budgets:*",
        "pricing:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "us-east-1",
            "us-west-2"
          ]
        },
        "BoolIfExists": {
          "aws:ViaAWSService": "false"
        }
      }
    }
  ]
}
```
