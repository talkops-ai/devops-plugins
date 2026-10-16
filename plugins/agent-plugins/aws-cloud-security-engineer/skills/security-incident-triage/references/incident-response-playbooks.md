# Tactical AWS Cloud Incident Response Playbooks

Use these playbooks to guide read-only forensic investigation and generate **advisory, human-approved containment and eradication plans** (`approval_required: true`).

---

## Playbook 1: Compromised IAM User / Access Key (`AKIA...`) or Assumed Role (`ASIA...`)

**Common Triggers:**
- `Policy:IAMUser/RootCredentialUsage`
- `UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B`
- `Recon:IAMUser/UserPermissions`
- `Persistence:IAMUser/AnomalousBehavior`
- `PrivilegeEscalation:IAMUser/AnomalousBehavior`
- Exposed key alert (`Health` event `AWS_RISK_CREDENTIALS_EXPOSED` or GitHub secret scan)

### Phase 1: Read-Only Forensic Investigation
1. **Determine Key Type (`AKIA` vs. `ASIA`):**
   - `AKIA...` = Long-term IAM User access key. Call `iam:GetAccessKeyLastUsed` to identify the exact IAM User, last service, and region.
   - `ASIA...` = Temporary STS session token. Query `cloudtrail:LookupEvents` (`LookupAttributeKey=AccessKeyId`) or look up the `AssumeRole` / `GetSessionToken` / `GetFederationToken` event that issued this `accessKeyId` in `responseElements.credentials.accessKeyId`.
2. **Detect Attacker Reconnaissance ("Whoami"):**
   - Look for `sts:GetCallerIdentity` (logged to CloudTrail even with zero IAM permissions), `iam:GetAccountAuthorizationDetails`, `iam:ListUsers`, `iam:ListRoles`, `s3:ListAllMyBuckets`, `secretsmanager:ListSecrets`.
3. **Audit for Attacker Persistence (CRITICAL before containment!):**
   - Did the attacker create a second access key (`iam:CreateAccessKey`) on the same or another user?
   - Did they add a console login profile (`iam:CreateLoginProfile`) or virtual MFA device (`iam:CreateVirtualMFADevice`)?
   - Did they backdoor a role's trust policy (`iam:UpdateAssumeRolePolicy`) to allow an external AWS account ID?
   - Did they create a scheduled Lambda function or EventBridge rule?

### Phase 2: Advisory Containment Proposal (Requires Human Approval)
> **CRITICAL AWS IAM GOTCHA:** Deactivating an `AKIA...` access key (`iam:UpdateAccessKey --status Inactive`) **does NOT revoke temporary `ASIA...` STS tokens** that the attacker already minted via `sts:GetSessionToken` or `sts:AssumeRole`!

To completely contain a compromised IAM User or Role, the proposed remediation plan must include **both**:
1. **Deactivate (do not delete yet, to preserve forensic evidence) the compromised `AKIA` key:**
   ```bash
   aws iam update-access-key --user-name <user> --access-key-id <AKIA...> --status Inactive
   ```
2. **Attach AWSCompromisedKeyQuarantineV2 AND an inline `RevokeOlderSessions` policy to immediately invalidate all active STS tokens issued before the containment timestamp:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "RevokeAllActiveSessionsIssuedBeforeContainment",
         "Effect": "Deny",
         "Action": "*",
         "Resource": "*",
         "Condition": {
           "DateLessThan": {
             "aws:TokenIssueTime": "2026-10-14T15:30:00Z"
           }
         }
       }
     ]
   }
   ```

---

## Playbook 2: EC2 / EKS Instance Credential Exfiltration & SSRF (`InstanceCredentialExfiltration.OutsideAWS`)

**Common Triggers:**
- `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS` (EC2/EKS Instance Profile `ASIA...` credentials are being used from an external IP outside AWS)
- `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.InsideAWS` (Used from an EC2 instance in a *different* AWS account)
- `AttackSequence:EC2/CompromisedInstanceGroup`
- `Execution:Runtime/NewBinaryExecuted` or `CryptoCurrency:Runtime/BitcoinTool.B`

### Phase 1: Read-Only Forensic Investigation
1. **Identify both the Victim Instance and the Stolen Role:**
   - From the GuardDuty finding `Resource.InstanceDetails` and `Resource.AccessKeyDetails`, record `InstanceId`, `VpcId`, `SubnetId`, `SecurityGroups`, `IamInstanceProfile.Arn`, and the external attacker `RemoteIpDetails.IpAddressV4`.
2. **Check IMDS Configuration:**
   - Call `ec2:DescribeInstances --instance-ids <id>` and inspect `MetadataOptions`:
     - If `HttpTokens == "optional"`, SSRF against `169.254.169.254` allowed trivial IMDSv1 credential theft.
     - If `HttpTokens == "required"` and `HttpPutResponseHopLimit > 1`, check whether a container on the host had RCE or SSRF with PUT header injection.
3. **Trace What the Attacker Did With the Instance Role:**
   - Run `cloudtrail:LookupEvents` by `AccessKeyId = <ASIA...>` and `Username = <InstanceId>` (remember: for EC2 Instance Profiles, the `RoleSessionName` is always the `i-xxxxxxxxxxxxxxxxx` Instance ID!).

### Phase 2: Advisory Forensic Isolation & Containment Proposal (Requires Human Approval)
> **Forensic Preservation Rule:** Never propose `ec2:TerminateInstances` or `ec2:StopInstances` as the first step if memory forensics is required (stopping wipes volatile RAM).

Propose this exact sequence for operator approval:
1. **Revoke Active Role Sessions Immediately:** Attach the `aws:TokenIssueTime` inline `Deny` policy (or click **Revoke sessions** in IAM Role console) on the Instance Profile's IAM Role so the stolen `ASIA...` token stops working outside AWS immediately.
2. **Enable Termination Protection & Isolate Network (Quarantine Security Group):**
   - Enable `disableApiTermination` so an automated ASG doesn't destroy the evidence.
   - If in an Auto Scaling Group, propose `autoscaling:DetachInstances --should-decrement-desired-capacity false` (suspending ASG health-check termination first).
   - Replace the instance's Security Groups (`ec2:ModifyInstanceAttribute --groups <sg-quarantine>`) with a dedicated **Forensic Quarantine Security Group** that has **0 inbound rules and 0 outbound rules** (note: Security Groups are stateful; to drop *already-established* TCP connections immediately, also add a temporary NACL rule denying traffic to/from the instance's private IP).
3. **Preserve Disk Evidence:**
   - Propose `ec2:CreateSnapshots` across all attached EBS volumes (`BlockDeviceMappings`) tagged with `ForensicCaseId`, encrypted with the IR team's KMS key.
4. **Enforce IMDSv2:**
   - Propose `ec2:ModifyInstanceMetadataOptions --http-tokens required --http-put-response-hop-limit 1`.

---

## Playbook 3: S3 Ransomware & Mass Data Exfiltration

**Common Triggers:**
- `Exfiltration:S3/AnomalousBehavior`, `Impact:S3/AnomalousBehavior.Delete`, `Impact:S3/AnomalousBehavior.Write`
- `Policy:S3/BucketBlockPublicAccessDisabled`, `Policy:S3/BucketAnonymousAccessGranted`
- Sudden spike in `s3:GetObject`, `s3:DeleteObject`, `s3:PutObject` encrypted with an external KMS CMK, or unauthorized `s3:PutBucketReplication`.

### Phase 1: Read-Only Forensic Investigation
1. **Inspect Bucket Protection State:**
   - Call `s3api:GetBucketVersioning`, `s3api:GetObjectLockConfiguration`, `s3api:GetBucketEncryption`, `s3api:GetBucketReplication`, `s3api:GetBucketLifecycleConfiguration`, and `s3api:GetBucketPolicy`.
   - **Ransomware Pattern Check:** Attackers either (a) re-encrypt objects in-place using `CopyObject` with an attacker-controlled external KMS key (`SSEKMSKeyId` in another account) and delete previous versions, or (b) add an aggressive 1-day `LifecycleConfiguration` expiration rule to purge noncurrent versions!
2. **Correlate Data Events:**
   - Query CloudTrail Lake / Security Lake S3 Data Events or S3 Server Access Logs for the principal and source IP performing bulk `GetObject` / `DeleteObject` / `PutBucketLifecycleConfiguration`.

### Phase 2: Advisory Containment Proposal (Requires Human Approval)
1. **Revoke the Compromised Principal's Sessions** (Playbook 1).
2. **Apply an Emergency Bucket Policy Lockdown** denying all `s3:DeleteObject`, `s3:DeleteObjectVersion`, `s3:PutLifecycleConfiguration`, `s3:PutBucketReplication`, and `s3:GetObject` for all principals except the designated Incident Response Role ARN (`aws:PrincipalArn`).
3. **Remove Malicious Replication or Lifecycle Rules** before noncurrent object versions expire.

---

## Playbook 4: Amazon Bedrock / GenAI Abuse ("LLMjacking")

**Common Triggers:**
- Spike in `bedrock:InvokeModel` or `bedrock:InvokeModelWithResponseStream` calls or CloudWatch `InvocationClientErrors` / token consumption metrics.
- Calls to `bedrock:ListFoundationModels` or `bedrock:GetFoundationModelAvailability` from leaked IAM credentials (attackers test leaked keys for Claude/Llama quota immediately after `sts:GetCallerIdentity`).

### Phase 1: Read-Only Forensic Investigation
1. Query `cloudtrail:LookupEvents` for `EventName=InvokeModel`, `InvokeModelWithResponseStream`, `CreateModelInvocationJob`, `PutModelInvocationLoggingConfiguration`, and `DeleteGuardrail`.
2. Check `bedrock:GetModelInvocationLoggingConfiguration` in each active region to see if prompt/completion audit logging to S3/CloudWatch Logs is enabled (and whether the attacker disabled it).
3. Attribute the IAM User/Role and Source IP invoking Bedrock APIs.

### Phase 2: Advisory Containment Proposal (Requires Human Approval)
1. Contain the compromised IAM credential (Playbook 1).
2. Propose an explicit `Deny` on `bedrock:InvokeModel*` for all principals except authorized application execution roles constrained by `aws:SourceVpc` / `aws:SourceVpce`.
3. Propose enabling Bedrock Model Invocation Logging with KMS encryption if not active.
