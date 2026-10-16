# AWS IAM Privilege Escalation Paths & Multi-Hop Trust Graph Analysis

When auditing an IAM User, Role, Group, or Permission Set, never evaluate actions in isolation. Attackers chain seemingly non-admin permissions to escalate to `AdministratorAccess` or pivot across accounts.

---

## 1. The 21 Canonical AWS IAM Privilege Escalation Primitives

Scan every attached managed policy (`iam:GetPolicyVersion`) and inline policy (`iam:GetRolePolicy`, `iam:GetUserPolicy`, `iam:GetGroupPolicy`) for these 5 classes of privilege escalation:

### Class A: Direct IAM Policy Self-Mutation (8 Primitives)

If a principal holds any of the following on `*` or on a resource ARN that includes itself (or a role it can assume), it has **effective AdministratorAccess**:

| Primitive | Attack Mechanism | Required Remediation |
|---|---|---|
| `iam:CreatePolicyVersion` | Creates a new `v2`+ version of an attached customer-managed policy with `"Effect": "Allow", "Action": "*", "Resource": "*"` and `"SetAsDefault": true`. | Restrict to CI/CD deployment role; enforce Permission Boundary on all created/modified roles; scope `Resource` away from self-attached policies. |
| `iam:SetDefaultPolicyVersion` | Reverts an attached customer-managed policy to an older, more permissive policy version (`v1`–`v5`). | Delete obsolete permissive policy versions (`iam:DeletePolicyVersion`) and restrict `iam:SetDefaultPolicyVersion`. |
| `iam:AttachUserPolicy` | Attaches `arn:aws:iam::aws:policy/AdministratorAccess` directly to the caller's IAM user (or another user they control). | Remove from non-admin principals; require Permission Boundary and `Condition.ArnEquals["iam:PermissionsBoundary"]`. |
| `iam:AttachGroupPolicy` | Attaches `AdministratorAccess` to an IAM group the caller belongs to. | Restrict to IaC pipeline role with SCP guardrails. |
| `iam:AttachRolePolicy` | Attaches `AdministratorAccess` to the caller's currently assumed role or any role the caller can `sts:AssumeRole` into. | Restrict `Resource` and require `iam:PermissionsBoundary` condition. |
| `iam:PutUserPolicy` | Embeds an inline admin policy on the caller's user. | Deny `iam:PutUserPolicy` via SCP or restrict to IaC automation role. |
| `iam:PutGroupPolicy` | Embeds an inline admin policy on the caller's group. | Deny `iam:PutGroupPolicy` for human principals. |
| `iam:PutRolePolicy` | Embeds an inline admin policy on the caller's role or an assumable role. | Restrict `Resource` and enforce Permission Boundaries. |

### Class B: Identity & Trust Graph Manipulation (5 Primitives)

| Primitive | Attack Mechanism | Required Remediation |
|---|---|---|
| `iam:AddUserToGroup` | Adds the caller's user to an existing `Admins` IAM group. | Restrict `Resource` (`arn:aws:iam::<account>:group/*`) so non-admins cannot modify privileged groups. |
| `iam:UpdateAssumeRolePolicy` | Modifies the trust policy (`AssumeRolePolicyDocument`) of a privileged role (e.g., an Organization Admin or CI/CD role) to allow the caller to call `sts:AssumeRole`. | High-severity privilege escalation: treat `iam:UpdateAssumeRolePolicy` on `*` as equivalent to full admin. Scope strictly to non-privileged role paths and protect admin roles via SCP. |
| `iam:CreateAccessKey` | Creates a permanent access key (`AKIA...`) for another IAM user who has higher privileges. | Scope `Resource` to `"arn:aws:iam::*:user/${aws:username}"` (self-only) or disable IAM user keys in favor of IAM Roles / Identity Center. |
| `iam:CreateLoginProfile` / `iam:UpdateLoginProfile` | Sets or resets the AWS Console password for another privileged IAM user without MFA. | Scope to self or deny entirely when using IAM Identity Center (SSO). |
| `sts:AssumeRole` (Role Chaining / Transitive Escalation) | Principal A assumes Role B, which has permissions to assume Admin Role C (multi-hop trust path). | Build the full directed graph of `AssumeRolePolicyDocument` principals vs. `sts:AssumeRole` identity permissions across accounts. |

### Class C: `iam:PassRole` + Service Execution Escalation (5 Primitives)

`iam:PassRole` with `Resource: "*"` (or targeting a high-privilege service role) combined with **any** compute/job creation permission allows the caller to execute arbitrary code as the passed role:

| Combination | Attack Mechanism | Required Remediation |
|---|---|---|
| `iam:PassRole` + `ec2:RunInstances` | Launches an EC2 instance attached to a privileged Instance Profile with attacker `UserData` script or SSH key. | Scope `iam:PassRole` `Resource` to exact low-privilege role ARNs and add `"StringEquals": {"iam:PassedToService": "ec2.amazonaws.com"}`. |
| `iam:PassRole` + `lambda:CreateFunction` + (`lambda:InvokeFunction` or `lambda:CreateEventSourceMapping` or `lambda:CreateFunctionUrlConfig`) | Creates a Lambda function running as a privileged role and invokes it to run arbitrary AWS SDK calls (e.g., exfiltrating secrets or mutating IAM). | Scope `iam:PassRole` to specific `arn:aws:iam::<acct>:role/lambda-app-*` ARNs + `"iam:PassedToService": "lambda.amazonaws.com"`. |
| `iam:PassRole` + `ecs:RegisterTaskDefinition` + (`ecs:RunTask` or `ecs:StartTask` or `ecs:UpdateService`) | Registers a container task with a privileged `taskRoleArn` or `executionRoleArn` and runs it. | Separate task roles per workload; scope `iam:PassRole` by role path `/ecs-tasks/` and `iam:PassedToService: ecs-tasks.amazonaws.com`. |
| `iam:PassRole` + `cloudformation:CreateStack` / `UpdateStack` | CloudFormation executes stack creation using the passed `RoleARN`, creating admin users/roles on the caller's behalf. | Restrict `iam:PassRole` for `cloudformation.amazonaws.com` to dedicated deployment roles with a Permission Boundary mandate. |
| `iam:PassRole` + `glue:CreateDevEndpoint` / `glue:CreateJob` / `sagemaker:CreateNotebookInstance` / `sagemaker:CreateProcessingJob` / `sagemaker:CreateTrainingJob` / `codebuild:CreateProject` / `datapipeline:CreatePipeline` / `bedrock:CreateModelCustomizationJob` | Spawns an interactive notebook, build container, or ETL job bound to a privileged IAM role. | Scope `iam:PassRole` to exact service-specific role ARNs and enforce `iam:PassedToService`. |

### Class D: Existing Compute & Runtime Hijacking (3 Primitives)

Even **without** `iam:PassRole`, a caller can hijack an **already-deployed** compute resource that has a privileged role attached:

| Primitive | Attack Mechanism | Required Remediation |
|---|---|---|
| `lambda:UpdateFunctionCode` or `lambda:UpdateFunctionConfiguration` | Overwrites the code of an existing privileged Lambda function, OR injects `AWS_LAMBDA_EXEC_WRAPPER` / malicious Lambda Layer / environment variables via `UpdateFunctionConfiguration` to steal its execution role credentials. | Treat `lambda:UpdateFunctionCode` and `lambda:UpdateFunctionConfiguration` on `*` as privilege escalation to the highest-privilege Lambda execution role in the account. Scope `Resource` by function prefix/tag. |
| `ssm:SendCommand` or `ssm:StartSession` | Executes arbitrary shell commands (`AWS-RunShellScript`) or opens an interactive shell as `root` on any EC2/ECS instance managed by SSM, stealing its Instance Profile / Task Role credentials from IMDS. | Scope `ssm:SendCommand` and `ssm:StartSession` using `aws:ResourceTag/*` conditions on both the instance (`arn:aws:ec2:*:*:instance/*`) and the SSM Document (`arn:aws:ssm:*:*:document/*`). |
| `ec2-instance-connect:SendSSHPublicKey` or `ec2:ModifyInstanceAttribute` (`userData`) | Pushes a temporary SSH public key or modifies `userData` on an existing EC2 instance to assume its Instance Profile role. | Restrict by `ec2:ResourceTag/*` and require `ec2:osuser`. |

---

## 2. Permission Boundary & Resource Policy Bypass Vectors

When auditing Permission Boundaries (`PermissionsBoundary.PermissionsBoundaryArn`), verify these three classic bypass pitfalls:

1. **Same-Account Resource Policy Bypass (IAM Users):**
   - In AWS IAM, if a KMS Key Policy or S3 Bucket Policy in the **same account** explicitly lists an IAM User ARN (`arn:aws:iam::111122223333:user/alice`) in `Principal`, **that resource policy grants access even if Alice's Permission Boundary does not allow it** (unless the Permission Boundary contains an explicit `Effect: Deny`).
   - *Fix:* Never grant access to individual IAM users in resource policies; use IAM Roles, and use explicit `Deny` statements in Permission Boundaries for sensitive actions.
2. **Role Creation Without Boundary Propagation:**
   - If a developer role has a Permission Boundary attached and is allowed `iam:CreateRole`, the developer can create a *new* role **without** attaching the Permission Boundary (escalating out of the boundary!) unless their policy enforces:
     ```json
     "Condition": {
       "StringEquals": {
         "iam:PermissionsBoundary": "arn:aws:iam::111122223333:policy/DeveloperBoundary"
       }
     }
     ```
   - And denies deleting or detaching the boundary (`iam:DeleteRolePermissionsBoundary`, `iam:PutRolePermissionsBoundary` with any other ARN, and `iam:DeletePolicy` / `iam:CreatePolicyVersion` on `DeveloperBoundary`).
3. **`ForAllValues` Vacuous Truth Bypass:**
   - A policy condition using `"ForAllValues:StringEquals": {"aws:TagKeys": ["Env"]}` evaluates to **`true`** when the caller passes **zero tags**!
   - *Fix:* Always include `"Null": {"aws:TagKeys": "false"}` in the same `Condition` block.
