# EKS, ECS, ECR, Lambda, EC2 & Amazon Bedrock Workload Security Hardening Reference

Use this reference when auditing or generating least-privilege trust policies and hardening diffs for **Amazon EKS**, **Amazon ECS / Fargate**, **Amazon ECR**, **AWS Lambda**, **Amazon EC2**, and **Amazon Bedrock**.

---

## 1. Amazon EKS Identity & Cluster Hardening

### 1.1 EKS Pod Identity vs. IRSA (IAM Roles for Service Accounts)

#### A. EKS Pod Identity (`pods.eks.amazonaws.com`) — Hardened Trust Policy
EKS Pod Identity simplifies credential delivery via the EKS Pod Identity Agent (`169.254.170.23`), but **if you omit condition keys on the role's trust policy, ANY pod in ANY cluster in the account where a Pod Identity Association is created can assume the role**. Always scope the trust policy by cluster ARN or namespace/service-account tags:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EKSPodIdentityScopedToClusterAndNamespace",
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ],
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "111122223333",
          "eks-cluster-arn": "arn:aws:eks:us-east-1:111122223333:cluster/prod-eks"
        },
        "StringEqualsIfExists": {
          "aws:RequestTag/kubernetes-namespace": "payments",
          "aws:RequestTag/kubernetes-service-account": "payment-processor-sa"
        }
      }
    }
  ]
}
```

#### B. IRSA (IAM Roles for Service Accounts via OIDC) — Hardened Trust Policy
**Critical Vulnerability to Flag:** An IRSA trust policy that uses `StringLike` with `"oidc.eks.<region>.amazonaws.com/id/<ID>:sub": "system:serviceaccount:*"` (or omits the `:sub` condition entirely) allows **every pod in every namespace in the cluster** (including `default` or compromised monitoring pods) to assume that IAM role!

Always enforce **`StringEquals`** on both `:aud` and `:sub`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "IRSAStrictServiceAccountBinding",
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111122223333:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/EXAMPLEID123456"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLEID123456:aud": "sts.amazonaws.com",
          "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLEID123456:sub": "system:serviceaccount:payments:payment-processor-sa"
        }
      }
    }
  ]
}
```

### 1.2 Blocking Pod Access to the EKS Worker Node Instance Profile Role

If pods use IRSA or EKS Pod Identity, they should **never** be able to query EC2 IMDS (`169.254.169.254`) to steal the underlying EC2 Worker Node's IAM role (`AmazonEKSNodeRole`):
- Enforce `HttpTokens = "required"` and **`HttpPutResponseHopLimit = 1`** on EKS Managed Node Group launch templates (`ec2:DescribeLaunchTemplateVersions`). With a hop limit of `1`, packets originating inside a non-`hostNetwork` container namespace are dropped at the host bridge before reaching IMDS!

---

## 2. Amazon ECS / Fargate & ECR Hardening

### 2.1 Separating `executionRoleArn` and `taskRoleArn`

| Role Property in Task Definition | Who Uses It | Allowed Permissions | Common Security Misconfiguration |
|---|---|---|---|
| `executionRoleArn` | **ECS Container Agent** (infrastructure plane) | `ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, `logs:CreateLogStream`, `logs:PutLogEvents`, `secretsmanager:GetSecretValue` (for startup secret injection only) | Attaching S3/DynamoDB/SQS application permissions to `executionRoleArn` or using the same IAM role for both `executionRoleArn` and `taskRoleArn`. |
| `taskRoleArn` | **Application Code inside the Container** (runtime plane) | Scoped application permissions (`dynamodb:GetItem`, `s3:GetObject` on specific ARNs). | Giving `taskRoleArn` wildcard `secretsmanager:GetSecretValue` on `*` instead of injecting specific secrets at startup via `executionRoleArn`. |

### 2.2 Hardened ECS TaskRole Trust Policy (Confused Deputy Protection)

Always include `aws:SourceAccount` and `aws:SourceArn` on `ecs-tasks.amazonaws.com` trust policies:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "ArnLike": {
          "aws:SourceArn": "arn:aws:ecs:us-east-1:111122223333:*"
        },
        "StringEquals": {
          "aws:SourceAccount": "111122223333"
        }
      }
    }
  ]
}
```

---

## 3. AWS Lambda & EC2 Instance Profile Security Hardening

### 3.1 Auditing Public Lambda Function URLs & Resource Policies

1. **Function URL Exposure (`lambda:ListFunctionUrlConfigs` / `lambda:GetFunctionUrlConfig`):**
   - If `AuthType == "NONE"`, anyone on the Internet can invoke the `https://<url-id>.lambda-url.<region>.on.aws/` endpoint directly.
   - Recommend either:
     - Switching `AuthType` to `"AWS_IAM"` and fronting the Function URL with **Amazon CloudFront Origin Access Control (OAC)** (`lambda:InvokeFunctionUrl` granted only to `Principal: {"Service": "cloudfront.amazonaws.com"}` with `Condition.StringEquals["aws:SourceArn"] = "arn:aws:cloudfront::111122223333:distribution/<ID>"`), OR
     - Removing the Function URL and routing through API Gateway with a Cognito/JWT/IAM authorizer and WAFv2 WebACL.
2. **Secrets in Lambda Environment Variables (`lambda:GetFunctionConfiguration`):**
   - Inspect `Environment.Variables` keys (never print secret values if someone hardcoded a credential!).
   - Flag keys matching `*_SECRET*`, `*_PASSWORD*`, `*_KEY*`, `*_TOKEN*`, `DATABASE_URL` that contain raw credentials rather than secret ARNs/names fetched at runtime via the **AWS Parameters and Secrets Lambda Extension** (`arn:aws:lambda:<region>:177933569100:layer:AWS-Parameters-and-Secrets-Lambda-Extension:*`).
3. **Lambda SnapStart Snapshot Security (`SnapStart.ApplyOn == "PublishedVersions"`):**
   - Lambda SnapStart takes a Firecracker MicroVM memory snapshot at the end of the `INIT` phase and restores multiple execution environments from that identical memory state.
   - **Security Invariants:**
     - Never cache short-lived session tokens, database credentials, or tenant-specific secrets in global variables during `INIT` without registering an **`afterRestore`** runtime hook (`register_after_restore` in Python, `CRaC` `Resource.afterRestore` in Java, `Snapshot.RegisterAfterRestore` in .NET) to refresh credentials after restore.
     - Ensure cryptographic libraries re-seed via OS CSPRNG (`/dev/urandom` / `getrandom()`) after snapshot restore rather than user-space PRNGs seeded only during `INIT`.

### 3.2 EC2 Instance Profile Least-Privilege & `iam:PassRole` Hardening

1. **Dedicated Instance Profile Per Application Tier:**
   - Every EC2 workload tier must have its own dedicated IAM Role and Instance Profile (`iam:CreateInstanceProfile` -> `iam:AddRoleToInstanceProfile`).
2. **Preventing Instance Profile Swap Privilege Escalation:**
   - An attacker with `ec2:AssociateIamInstanceProfile` + `ec2:ReplaceIamInstanceProfileAssociation` + broad `iam:PassRole` can swap a running EC2 instance's profile to a high-privilege role and extract its temporary credentials via IMDSv2.
   - Restrict `iam:PassRole` using `iam:PassedToService = "ec2.amazonaws.com"` and explicit role ARN allowlists (`arn:aws:iam::111122223333:role/app-tier-*`).

---

## 4. Amazon Bedrock & Generative AI Workload Hardening

### 4.1 Model Invocation Logging & Immutable Audit Trails

Read-only verification:
```bash
aws bedrock get-model-invocation-logging-configuration --region us-east-1
```

**Hardened Baseline:**
- `textDataDeliveryEnabled: true`, `imageDataDeliveryEnabled: true`, `embeddingDataDeliveryEnabled: true`.
- Deliver logs to an S3 bucket protected by **S3 Block Public Access**, **SSE-KMS (CMK)**, and **S3 Object Lock** (`GOVERNANCE` or `COMPLIANCE` mode), and/or a **KMS-encrypted CloudWatch Log Group** so prompt-injection attempts and sensitive data exfiltration can be forensically investigated.

### 4.2 Amazon Bedrock Guardrails (`bedrock:GetGuardrail`)

Every customer-facing or RAG-enabled Bedrock application and Bedrock Agent should attach a `guardrailIdentifier` and `guardrailVersion` enforcing:
1. **Prompt Attack & Content Filters (`contentPolicyConfig.filtersConfig`):**
   - `PROMPT_ATTACK`: `inputStrength = "HIGH"` (defends against jailbreaks and indirect prompt injection embedded in retrieved RAG documents).
   - `HATE`, `INSULTS`, `SEXUAL`, `VIOLENCE`, `MISCONDUCT`: `inputStrength = "HIGH"`, `outputStrength = "HIGH"`.
2. **PII & Secret Redaction (`sensitiveInformationPolicyConfig`):**
   - `piiEntitiesConfig`: Set `AWS_SECRET_KEY`, `AWS_ACCESS_KEY`, `PASSWORD`, `CREDIT_DEBIT_CARD_NUMBER`, `US_SOCIAL_SECURITY_NUMBER` to `Action = "BLOCK"` and general contact PII (`EMAIL`, `PHONE`, `NAME`) to `Action = "ANONYMIZE"`.
   - `regexesConfig`: Block internal token/key patterns before they leave the model response.
3. **Contextual Grounding Checks (`contextualGroundingPolicyConfig`):**
   - Enable `GROUNDING` (e.g., threshold `>= 0.75`) and `RELEVANCE` (e.g., threshold `>= 0.75`) to block hallucinated responses that diverge from retrieved Knowledge Base source chunks.

### 4.3 Bedrock Knowledge Base & Agent Role Confused-Deputy Protection

When Amazon Bedrock (`bedrock.amazonaws.com`) assumes an IAM service role to query an OpenSearch Serverless (`aoss`) index, read S3 data sources, or invoke Lambda action groups, always enforce `aws:SourceAccount` and `aws:SourceArn` on the role trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockKnowledgeBaseConfusedDeputyProtection",
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "111122223333"
        },
        "ArnLike": {
          "aws:SourceArn": [
            "arn:aws:bedrock:us-east-1:111122223333:knowledge-base/*",
            "arn:aws:bedrock:us-east-1:111122223333:agent/*"
          ]
        }
      }
    }
  ]
}
```
