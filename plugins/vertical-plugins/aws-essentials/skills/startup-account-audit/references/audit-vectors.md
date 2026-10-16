# 26-Point AWS Startup Account Audit — Vectors, API Calls & Remediations

This reference defines the 26 read-only checks executed by `startup-account-audit` (`scripts/run_startup_audit.py` and MCP inspection).

---

## Vector 1: Identity & Secret Hygiene (6 Checks)

| ID | Check | AWS API (Read-Only) | Pass Condition | Stage Severity | Remediation |
|---|---|---|---|---|---|
| `IAM-01` | **Root Account Access Keys** | `iam:GetAccountSummary` (`AccountAccessKeysPresent`) | `== 0` | **CRITICAL** (All Stages) | Delete root access keys immediately in IAM Console; use IAM Identity Center (SSO) or IAM roles. |
| `IAM-02` | **Root Account MFA** | `iam:GetAccountSummary` (`AccountMFAEnabled`) | `== 1` | **CRITICAL** (All Stages) | Enable hardware FIDO2/Passkey or virtual TOTP MFA on the root user. |
| `IAM-03` | **Unused / Stale IAM Access Keys (>90 days)** | `iam:ListUsers`, `iam:ListAccessKeys`, `iam:GetAccessKeyLastUsed` | All active keys created <90d ago and used within 90d | **HIGH** (All Stages) | Deactivate (`aws iam update-access-key --status Inactive`) and replace with OIDC federation (`aws-actions/configure-aws-credentials`) for CI/CD. |
| `IAM-04` | **Wildcard Administrator Policies on Workload Roles** | `iam:ListRoles`, `iam:ListAttachedRolePolicies` | No non-admin service role attaches `AdministratorAccess` or `Action: "*"` | **HIGH** (Seed+) | Scope task/execution roles to specific service actions and ARNs. |
| `IAM-05` | **Cognito User Pool MFA Posture** | `cognito-idp:ListUserPools`, `cognito-idp:DescribeUserPool` | `MfaConfiguration` is `ON` or `OPTIONAL` | **MEDIUM** (Seed+) | Enable optional or required TOTP/WebAuthn Passkey MFA on customer-facing User Pools. |
| `IAM-06` | **Plaintext Secrets in Lambda Env Vars** | `lambda:ListFunctions` (`Environment.Variables` **keys only**) | No env var key matching `SECRET`, `PASSWORD`, `API_KEY`, `PRIVATE_KEY`, `TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DATABASE_URL` with raw literal values | **CRITICAL** (All Stages) | Migrate secrets into AWS Secrets Manager using `${CLAUDE_PLUGIN_ROOT}/scripts/asm-exec` so values never pass through agent context. |

---

## Vector 2: Network & Data Encryption (7 Checks)

| ID | Check | AWS API (Read-Only) | Pass Condition | Stage Severity | Remediation |
|---|---|---|---|---|---|
| `NET-01` | **Security Groups Open to `0.0.0.0/0` on Sensitive Ports** | `ec2:DescribeSecurityGroups` | No ingress rule from `0.0.0.0/0` or `::/0` on ports `22` (SSH), `3389` (RDP), `5432` (Postgres), `3306` (MySQL), `6379` (Redis), `27017` (MongoDB) | **CRITICAL** (All Stages) | Restrict DB ingress to application Security Group IDs; replace port 22 SSH with AWS Systems Manager Session Manager. |
| `NET-02` | **Production Workloads in Default VPC** | `ec2:DescribeVpcs`, `ec2:DescribeInstances`, `rds:DescribeDBInstances` | Default VPC has 0 running EC2/RDS instances | **MEDIUM** (Seed+) / **LOW** (MVP) | Migrate stateful databases into isolated private subnets before Series A / SOC 2 audit. |
| `DATA-01` | **S3 Bucket Public Access Block & SSE** | `s3:ListBuckets`, `s3:GetPublicAccessBlock`, `s3:GetBucketEncryption` | All 4 `PublicAccessBlockConfiguration` flags `True` (except explicit CloudFront OAC / public asset buckets) + SSE enabled | **HIGH** (All Stages) | Enable account-level S3 Block Public Access (`s3control:PutPublicAccessBlock`). |
| `DATA-02` | **RDS Storage Encryption at Rest** | `rds:DescribeDBInstances` (`StorageEncrypted`) | `StorageEncrypted == True` on all DB instances | **HIGH** (All Stages) | Enable KMS encryption on snapshot restore (SOC 2 / HIPAA prerequisite; cannot be toggled in-place without snapshot copy). |
| `DATA-03` | **EBS Volume Encryption at Rest** | `ec2:DescribeVolumes` (`Encrypted`) | `Encrypted == True` on all volumes | **MEDIUM** (Seed+) | Call `ec2:EnableEbsEncryptionByDefault` in the target region so all future volumes are encrypted automatically. |
| `DATA-04` | **ElastiCache Encryption (At-Rest & In-Transit)** | `elasticache:DescribeReplicationGroups` | `AtRestEncryptionEnabled` and `TransitEncryptionEnabled` are `True` | **MEDIUM** (Seed+) | Enable TLS (`TransitEncryptionEnabled`) and at-rest encryption when creating Valkey/Redis clusters. |
| `SEC-01` | **CloudTrail Multi-Region Management Trail** | `cloudtrail:DescribeTrails`, `cloudtrail:GetTrailStatus` | At least 1 multi-region trail with `IsLogging == True` | **HIGH** (All Stages) | First management-events trail in CloudTrail is free (S3 storage only, <$1/mo for startups) and essential for incident forensics. |

---

## Vector 3: Scalability & AI Readiness (5 Checks)

| ID | Check | AWS API (Read-Only) | Pass Condition | Stage Severity | Remediation |
|---|---|---|---|---|---|
| `SCALE-01` | **Core CloudWatch Alarms Present** | `cloudwatch:DescribeAlarms` | Alarms exist for ALB `HTTPCode_Target_5XX_Count`, RDS `CPUUtilization`/`FreeStorageSpace`, and DynamoDB `SystemErrors`/`ThrottledRequests` | **MEDIUM** (Seed+) | Provision baseline CloudWatch alarms routed to SNS/Slack before production launch. |
| `SCALE-02` | **Lambda Throttling & Timeout Hotspots** | `lambda:ListFunctions`, `cloudwatch:GetMetricStatistics` (`Throttles`, `Errors`) | 0 throttled functions in trailing 7 days; timeout <900s with memory right-sized | **HIGH** (All Stages) | Increase reserved concurrency or switch synchronous spikes to SQS + Lambda buffering. |
| `SCALE-03` | **API Gateway Stage Rate Limiting** | `apigateway:GetRestApis`, `apigatewayv2:GetApis` | Default stage throttling (`ThrottlingBurstLimit`, `ThrottlingRateLimit`) configured | **MEDIUM** (All Stages) | Configure stage-level rate limits (e.g., 100 RPS / 200 burst for MVP) to prevent denial-of-wallet attacks. |
| `SCALE-04` | **Stage-Calibrated RDS Availability Posture** | `rds:DescribeDBInstances` (`MultiAZ`) | Pre-Revenue/Seed: `MultiAZ == False` (saves 50% DB cost); Series A+: `MultiAZ == True` on prod DBs | **COST/HA** (Stage-Aware) | Right-size HA to stage: turn OFF Multi-AZ on dev/staging and Pre-Revenue MVPs; turn ON Multi-AZ for Series A+ production DBs. |
| `AI-01` | **Amazon Bedrock Guardrails & Inference Profiles** | `bedrock:ListGuardrails`, `bedrock:ListInferenceProfiles` | Customer-facing Bedrock workloads have a Guardrail configured or explicit PII/prompt-attack filtering | **MEDIUM** (AI Startups) | Attach a Bedrock Guardrail for content/PII filtering and use Cross-Region Inference Profiles (`us.anthropic.*`) for higher burst quotas. |

---

## Vector 4: Immediate Spend Leaks & Activate Credit Burn (8 Checks)

| ID | Check | AWS API (Read-Only) | Monthly Waste Formula | Remediation |
|---|---|---|---|---|
| `COST-01` | **Stopped EC2 Instances with Attached EBS** | `ec2:DescribeInstances` (`instance-state-name=stopped`), `ec2:DescribeVolumes` | `Sum(volume_size_gb) * $0.08/mo` (gp3) or `$0.10/mo` (gp2) | Snapshot (`ec2:CreateSnapshot`) and terminate stopped instances if unused >14 days; upgrade any `gp2` volumes to `gp3` (20% cheaper). |
| `COST-02` | **Unattached Elastic IPs (EIPs)** | `ec2:DescribeAddresses` (missing `AssociationId`) | `Count(unattached_eips) * $3.65/mo` (`$0.005/hr`) | Release unassociated Elastic IPs (`aws ec2 release-address --allocation-id <id>`). |
| `COST-03` | **Unattached (`available`) EBS Volumes** | `ec2:DescribeVolumes` (`status=available`) | `Sum(size_gb) * $0.08–$0.10/mo` | Snapshot if needed, then delete unattached EBS volumes (`aws ec2 delete-volume`). |
| `COST-04` | **Aged Manual RDS & EBS Snapshots (>90 days)** | `rds:DescribeDBSnapshots` (`snapshot-type=manual`), `ec2:DescribeSnapshots` (`owner-self`) | `Sum(allocated_gb) * $0.05–$0.095/mo` | Delete obsolete manual snapshots older than 90 days or move cold backups to S3 Glacier. |
| `COST-05` | **CloudWatch Log Groups with Infinite Retention** | `logs:DescribeLogGroups` (missing `retentionInDays`) | `Sum(storedBytes / 1e9) * $0.03/GB/mo` compounding forever | Set `retentionInDays` to `14` or `30` days for dev/staging and `90` days for prod (`aws logs put-retention-policy`). |
| `COST-06` | **Idle SageMaker Notebook Instances / Studio Apps** | `sagemaker:ListNotebookInstances` (`Status=InService`) | `instance_hourly_rate * 730 hrs/mo` (often `$40–$900+/mo`) | Stop `InService` notebooks when not actively training and attach an auto-shutdown lifecycle configuration. |
| `COST-07` | **NAT Gateways Missing Free S3 / DynamoDB Gateway Endpoints** | `ec2:DescribeNatGateways` (`state=available`), `ec2:DescribeVpcEndpoints` | `$32.85/mo` fixed per NAT GW + `$0.045/GB` data processing for S3/DynamoDB traffic | Add **free** VPC Gateway Endpoints (`com.amazonaws.<region>.s3` and `com.amazonaws.<region>.dynamodb`) immediately; for Pre-Revenue/Seed, evaluate replacing NAT Gateways with NAT instances (`fck-nat` on `t4g.nano` at ~$3/mo) or VPC Endpoints. |
| `COST-08` | **Expiring Commitments & AWS Activate Credit Burn Runway** | `budgets:DescribeBudgets` (free) + optional `ce:GetCostAndUsage` (`$0.01/call` warning required) | `Runway_Months = Remaining_Activate_Credits_USD / Trailing_30d_Gross_Credit_Eligible_Spend_USD` | Alert if credit runway is <90 days or if non-credit-eligible charges (Marketplace SaaS, Route 53 domains, Cost Explorer API loops, upfront RI fees) are leaking cash. |
