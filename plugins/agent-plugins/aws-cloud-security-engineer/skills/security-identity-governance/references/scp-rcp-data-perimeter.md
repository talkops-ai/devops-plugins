# AWS Organizations SCPs, RCPs, Data Perimeters & Federation Hardening

Use this reference when auditing or authoring **Service Control Policies (SCPs)**, **Resource Control Policies (RCPs)**, **AWS Data Perimeters**, **OIDC/SAML Workforce & CI/CD Federation**, and **Zero-Trust Agentic Execution Policies**.

---

## 1. AWS Data Perimeter Triangle (Identity, Resource, Network)

An AWS Data Perimeter enforces three invariant boundaries across your AWS Organization (`o-xxxxxxxxxx`):

| Perimeter Boundary | Security Invariant | Primary Policy Vehicle | Core IAM Condition Keys |
|---|---|---|---|
| **1. Identity Perimeter** | Only **trusted identities** (principals from our Organization) can access our resources. | Resource Control Policies (RCPs), S3/KMS/SQS/SNS Resource Policies, VPC Endpoint Policies | `aws:PrincipalOrgID`, `aws:PrincipalAccount`, `aws:PrincipalIsAWSService` |
| **2. Resource Perimeter** | Our trusted identities can only access **trusted resources** (resources owned by our Organization). | Service Control Policies (SCPs), VPC Endpoint Policies | `aws:ResourceOrgID`, `aws:ResourceAccount`, `aws:PrincipalIsAWSService` |
| **3. Network Perimeter** | Our trusted identities and resources can only be accessed from **expected networks** (our VPCs, VPC Endpoints, or corporate CIDRs). | SCPs, RCPs, Role Trust Policies, Bucket/Key Policies | `aws:SourceVpce`, `aws:SourceVpc`, `aws:SourceIp`, `aws:ViaAWSService`, `ec2:SourceInstanceARN` |

---

## 2. Production-Tested Service Control Policies (SCPs)

> **Critical SCP Rules:**
> - SCPs **never** affect principals in the **Management Account**. Never deploy workloads in the Management Account.
> - SCPs **never** affect **Service-Linked Roles** (`AWSServiceRoleFor*`).
> - Always exempt `aws:PrincipalIsAWSService == "true"` or specific break-glass Incident Response / Control Tower roles (`aws:PrincipalArn`) when restricting network or resource perimeters.

### 2.1 Protect Security & Audit Telemetry Guardrail (CloudTrail, GuardDuty, Security Hub, Config, Access Analyzer)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyTamperingWithSecurityServices",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:DeleteTrail",
        "cloudtrail:StopLogging",
        "cloudtrail:UpdateTrail",
        "cloudtrail:PutEventSelectors",
        "config:DeleteConfigurationRecorder",
        "config:DeleteDeliveryChannel",
        "config:StopConfigurationRecorder",
        "guardduty:DeleteDetector",
        "guardduty:DeleteMembers",
        "guardduty:DisassociateFromMasterAccount",
        "guardduty:DisassociateFromAdministratorAccount",
        "guardduty:StopMonitoringMembers",
        "guardduty:UpdateDetector",
        "securityhub:DeleteMembers",
        "securityhub:DisableSecurityHub",
        "securityhub:DisassociateFromMasterAccount",
        "securityhub:DisassociateFromAdministratorAccount",
        "access-analyzer:DeleteAnalyzer",
        "macie2:DisableMacie",
        "inspector2:Disable",
        "ec2:DisableEbsEncryptionByDefault",
        "s3:PutAccountPublicAccessBlock"
      ],
      "Resource": "*",
      "Condition": {
        "ArnNotLike": {
          "aws:PrincipalArn": [
            "arn:aws:iam::*:role/AWSControlTowerExecution",
            "arn:aws:iam::*:role/SecurityAdminBreakGlassRole"
          ]
        }
      }
    }
  ]
}
```

### 2.2 Enforce IMDSv2 & Prevent Public EC2/EBS/S3 Exposure

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RequireIMDSv2OnLaunch",
      "Effect": "Deny",
      "Action": "ec2:RunInstances",
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "StringNotEquals": {
          "ec2:MetadataHttpTokens": "required"
        }
      }
    },
    {
      "Sid": "DenyDisablingIMDSv2",
      "Effect": "Deny",
      "Action": "ec2:ModifyInstanceMetadataOptions",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "ec2:MetadataHttpTokens": "required"
        }
      }
    },
    {
      "Sid": "DenyRootAccountUsageAndMemberLeaveOrg",
      "Effect": "Deny",
      "Action": [
        "organizations:LeaveOrganization"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2.3 Region Restriction SCP (With Mandatory Global Service Exemptions)

Never block global services (`iam`, `sts`, `organizations`, `route53`, `cloudfront`, `wafv2`, `support`, `budgets`, `ce`, `Billing`, `health`, `sso`) that execute in `us-east-1`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyNonApprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "a4b:*", "acm:*", "aws-marketplace-management:*", "aws-marketplace:*",
        "aws-portal:*", "budgets:*", "ce:*", "Chatbot:*", "chime:*",
        "cloudfront:*", "config:*", "cur:*", "directconnect:*",
        "ec2:DescribeRegions", "ec2:DescribeTransitGateways", "ec2:DescribeVpnGateways",
        "fms:*", "globalaccelerator:*", "health:*", "iam:*", "importexport:*",
        "kms:*", "mobileanalytics:*", "networkmanager:*", "organizations:*",
        "pricing:*", "route53:*", "route53domains:*", "route53-recovery-cluster:*",
        "route53-recovery-control-config:*", "route53-recovery-readiness:*",
        "s3:GetAccountPublicAccessBlock", "s3:ListAllMyBuckets", "s3:ListMultiRegionAccessPoints",
        "shield:*", "sso:*", "sts:*", "support:*", "trustedadvisor:*",
        "waf-regional:*", "waf:*", "wafv2:*", "wellarchitected:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "us-east-1",
            "us-west-2",
            "eu-west-1"
          ]
        },
        "BoolIfExists": {
          "aws:PrincipalIsAWSService": "false"
        }
      }
    }
  ]
}
```

---

## 3. Resource Control Policies (RCPs) — Enforcing the Identity Perimeter on Resources

AWS Organizations **Resource Control Policies (`RESOURCE_CONTROL_POLICY`)** enforce organization-wide resource guardrails on `s3:*`, `sts:*`, `kms:*`, `sqs:*`, and `secretsmanager:*` across member accounts without modifying thousands of individual bucket or key policies:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RCPFullAWSAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "*",
      "Resource": "*"
    },
    {
      "Sid": "EnforceOrgIdentityPerimeterOnResources",
      "Effect": "Deny",
      "Principal": "*",
      "Action": [
        "s3:*",
        "kms:*",
        "secretsmanager:*",
        "sqs:*"
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
    },
    {
      "Sid": "EnforceHTTPSOnAllS3BucketsOrgWide",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "*",
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```
> **Note:** Every RCP must include the `RCPFullAWSAccess` base Allow statement (`Principal: "*", Action: "*", Resource: "*"`) because RCPs are default-deny intersection filters like SCPs.

---

## 4. OIDC & CI/CD Federation Trust Policy Hardening

A top root cause of cloud breaches is an overly broad OIDC trust policy on GitHub Actions (`token.actions.githubusercontent.com`) or GitLab CI.

### 4.1 Vulnerable Anti-Pattern (NEVER ALLOW)

- Missing `sub` condition entirely (allows **any** GitHub repository on earth to assume your AWS role!).
- Using `"StringLike": {"token.actions.githubusercontent.com:sub": "repo:my-org/*"}` on a production deployment role (allows any forked/sandbox repo or unreviewed feature branch in `my-org` to assume production admin).

### 4.2 Hardened GitHub Actions OIDC Trust Policy

Always pin `aud` to `sts.amazonaws.com` with `StringEquals` and lock `sub` to the exact repository and protected branch or environment:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GitHubActionsProtectedMainOnly",
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": [
            "repo:my-org/infra-repo:ref:refs/heads/main",
            "repo:my-org/infra-repo:environment:production"
          ]
        }
      }
    }
  ]
}
```

---

### 4.3 Amazon Cognito Identity Pool & User Pool Security Auditing

A Cloud Security Engineer audits Cognito federation boundaries to prevent unauthenticated access and cross-tenant role escalation:

1. **Cognito Identity Pool Authenticated vs. Unauthenticated Role Trust (`cognito-identity:DescribeIdentityPool`, `GetIdentityPoolRoles`):**
   - Flag `AllowUnauthenticatedIdentities == true` unless strictly required for anonymous telemetry, and ensure the unauthenticated IAM Role has zero access to S3, DynamoDB, or API Gateway administrative routes.
   - **Critical Trust Policy Vulnerability:** If an Identity Pool's **Authenticated Role** trust policy checks only `cognito-identity.amazonaws.com:aud` and omits `cognito-identity.amazonaws.com:amr`, an **unauthenticated guest token from the same Identity Pool can assume the Authenticated Role!**
   - Always enforce both `:aud` and `:amr` in the Authenticated Role trust policy:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Sid": "CognitoAuthenticatedRoleStrictBinding",
           "Effect": "Allow",
           "Principal": {
             "Federated": "cognito-identity.amazonaws.com"
           },
           "Action": "sts:AssumeRoleWithWebIdentity",
           "Condition": {
             "StringEquals": {
               "cognito-identity.amazonaws.com:aud": "us-east-1:12345678-1234-1234-1234-1234567890ab"
             },
             "ForAnyValue:StringLike": {
               "cognito-identity.amazonaws.com:amr": "authenticated"
             }
           }
         }
       ]
     }
     ```
2. **Cognito User Pool Privilege Escalation via Writable Custom Attributes (`cognito-idp:DescribeUserPool`, `DescribeUserPoolClient`):**
   - If an application maps `custom:role`, `custom:tenant_id`, or `custom:tier` to IAM roles (via Identity Pool rule-based mapping or ABAC `sts:TagSession`) or backend authorization, inspect `WriteAttributes` on every App Client (`DescribeUserPoolClient`).
   - If the App Client allows the user to write `custom:role` or `custom:tenant_id`, any authenticated user can call `aws cognito-idp update-user-attributes --access-token <token>` directly against the public Cognito endpoint to escalate to admin or pivot to another tenant! Remove authorization-bearing custom attributes from `WriteAttributes`.
   - Verify `PreventUserExistenceErrors == "ENABLED"`, MFA (`MfaConfiguration == "ON"`), OAuth 2.0 Authorization Code Grant with PKCE (never `implicit` flow), and WAFv2 WebACL association (`wafv2:GetWebACLForResource`).

---

## 5. Zero-Trust IAM Guardrails for AI Agents & AWS MCP Servers (`aws:ViaAWSMCPService` & `aws:CalledViaAWSMCP`)

AWS provides two dedicated IAM condition keys to govern requests originating from AWS-managed MCP servers:
- **`aws:ViaAWSMCPService`** (Boolean): Evaluates to `"true"` whenever an AWS API request is routed through any AWS-managed MCP service.
- **`aws:CalledViaAWSMCP`** (String / Array of Strings): Contains the service principal of the specific AWS-managed MCP server invoked (e.g., `aws-mcp.amazonaws.com`).

### 5.1 Separating Human Operator Permissions from AI Agent Permissions (SCP / IAM Policy)
When developers or security engineers share an AWS SSO role with an AI coding assistant, attach this guardrail so humans retain normal console/CLI permissions while AI agent calls passing through MCP are blocked from destructive mutations and credential retrieval:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyDestructiveAndPrivilegedMutationsViaMCP",
      "Effect": "Deny",
      "Action": [
        "iam:*",
        "organizations:*",
        "account:*",
        "s3:DeleteBucket",
        "s3:DeleteBucketPolicy",
        "s3:DeleteObject",
        "s3:DeleteObjectVersion",
        "s3:PutBucketPublicAccessBlock",
        "s3:PutAccountPublicAccessBlock",
        "s3:BypassGovernanceRetention",
        "s3:PutObjectLegalHold",
        "dynamodb:DeleteTable",
        "rds:DeleteDBInstance",
        "rds:DeleteDBCluster",
        "rds:ModifyDBSnapshotAttribute",
        "ec2:TerminateInstances",
        "ec2:DeleteVpc",
        "ec2:DisableEbsEncryptionByDefault",
        "kms:ScheduleKeyDeletion",
        "kms:DisableKey",
        "kms:PutKeyPolicy",
        "secretsmanager:GetSecretValue",
        "secretsmanager:BatchGetSecretValue",
        "secretsmanager:DeleteSecret",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail",
        "guardduty:DeleteDetector",
        "securityhub:DisableSecurityHub"
      ],
      "Resource": "*",
      "Condition": {
        "Bool": {
          "aws:ViaAWSMCPService": "true"
        }
      }
    },
    {
      "Sid": "RestrictAllowedMCPServerPrincipals",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "Bool": {
          "aws:ViaAWSMCPService": "true"
        },
        "ForAnyValue:StringNotEquals": {
          "aws:CalledViaAWSMCP": [
            "aws-mcp.amazonaws.com"
          ]
        }
      }
    }
  ]
}
```

### 5.2 Enforce ABAC Session Tagging (`sts:TagSession` & `sts:TransitiveTagKeys`)
- Require agent role assumptions to pass immutable session tags (`AgentId`, `TenantId`, `WorkflowRunId`) so every CloudTrail event carries cryptographic attribution in `userIdentity.sessionContext.attributes`.
- Restrict resource access using `"StringEquals": {"aws:ResourceTag/TenantId": "${aws:PrincipalTag/TenantId}"}` to prevent cross-tenant lateral movement.

