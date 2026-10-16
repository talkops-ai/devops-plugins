---
name: security-workload-containers
description: >-
  Audits and hardens AWS compute, container, serverless, and Generative AI workloads across Amazon
  EKS, Amazon ECS/Fargate, Amazon ECR, AWS Lambda, Amazon EC2, and Amazon Bedrock. Covers EKS Pod
  Identity vs. IRSA OIDC trust policies, EKS public API endpoint and Access Entries, ECR image
  immutability and Inspector container scanning, ECS task vs. execution role separation, ECS Exec
  audit logging, Lambda Function URLs, SnapStart snapshot credential safety, EC2 IMDSv2 hop limits
  and Instance Profile least-privilege, and Amazon Bedrock Guardrails, Model Invocation Logging,
  PrivateLink isolation, and Knowledge Base RAG security.
version: 2
---

# Workload, Container, Serverless & GenAI Security (EKS, ECS, ECR, Lambda, EC2, Bedrock)

Use this skill for **read-only security auditing and advisory hardening** of compute and AI runtimes across **Amazon EKS**, **Amazon ECS / Fargate**, **Amazon ECR**, **AWS Lambda**, **Amazon EC2**, and **Amazon Bedrock**. Never mutate cluster configurations, task definitions, Lambda functions, instances, or Bedrock guardrails directly during an audit.

## Reference Library (Load On-Demand)

- **[references/eks-ecs-lambda-hardening.md](references/eks-ecs-lambda-hardening.md)** — Load for detailed read-only API procedures, IAM trust policy templates, and remediation patterns across EKS (Pod Identity, IRSA, Access Entries, control plane logging), ECS/ECR (task role separation, ECS Exec logging, Inspector ECR scanning), Lambda (Function URLs, resource policies, SnapStart PRNG/secret isolation, env-var KMS encryption), EC2 (IMDSv2 hop limits, Instance Profile `iam:PassRole` scoping, EBS encryption), and Amazon Bedrock (Guardrails, Model Invocation Logging, PrivateLink, RAG Knowledge Base and Agent execution role boundaries).

---

## Deterministic Compute, Container & GenAI Audit Workflow

1. **Amazon EKS Cluster & Identity Audit:**
   - Enumerate clusters (`eks:ListClusters` → `eks:DescribeCluster`).
   - Check **Control Plane Endpoint Exposure**: Flag `resourcesVpcConfig.endpointPublicAccess == true` when `publicAccessCidrs` contains `"0.0.0.0/0"` (EKS.1).
   - Check **Control Plane Audit Logging**: Verify `logging.clusterLogging` has all 5 log types enabled (`api`, `audit`, `authenticator`, `controllerManager`, `scheduler`) (EKS.8).
   - Check **Envelope Encryption**: Verify `encryptionConfig` encrypts Kubernetes `secrets` with a KMS CMK (EKS.3).
   - Check **EKS Access Entries & Authentication Mode**: Call `eks:ListAccessEntries` and `eks:ListAssociatedAccessPolicies` — ensure `authenticationMode` is `API` or `API_AND_CONFIG_MAP` and flag overly broad `AmazonEKSClusterAdminPolicy` grants.
   - Audit **EKS Pod Identity (`eks:ListPodIdentityAssociations`) & IRSA OIDC Roles**: Verify IAM role trust policies scope `:sub` to a specific `system:serviceaccount:<namespace>:<serviceaccount>` with `StringEquals` (never `StringLike` with `*`).
2. **Amazon ECS / Fargate & ECR Container Audit:**
   - Enumerate ECR repositories (`ecr:DescribeRepositories`): verify `imageTagMutability == "IMMUTABLE"`, `imageScanningConfiguration.scanOnPush == true` (with Amazon Inspector Enhanced Scanning enabled), and KMS encryption (`encryptionConfiguration.encryptionType == "KMS"`).
   - Inspect ECR Repository Policies (`ecr:GetRepositoryPolicy`) for cross-account or wildcard exposure.
   - Enumerate ECS Clusters (`ecs:DescribeClusters`) and Task Definitions (`ecs:DescribeTaskDefinition`):
     - **Separate `executionRoleArn` from `taskRoleArn`:** The `executionRoleArn` (used by the ECS agent to pull ECR images and fetch Secrets Manager secrets at startup) must NEVER be reused as the application container's `taskRoleArn`!
     - Flag containers with `privileged: true`, `user: "0"`/`root`, `readonlyRootFilesystem: false` (ECS.5), or plaintext secrets inside `environment` instead of `secrets` (`valueFrom` Secrets Manager / SSM Parameter Store ARN) (ECS.2).
     - If `enableExecuteCommand == true` (`ECS Exec`) on a service/task, verify the ECS cluster's `configuration.executeCommandConfiguration` enforces `kmsKeyId` encryption and `logging: "OVERRIDE"` to CloudWatch Logs or S3 (ECS.4).
3. **AWS Lambda Serverless & SnapStart Security Audit:**
   - Enumerate functions (`lambda:ListFunctions`):
   - **Check Public Function URLs (`lambda:GetFunctionUrlConfig`):** Flag any Function URL with `AuthType == "NONE"` unless explicitly intended as a public webhook guarded by CloudFront + WAF (`Lambda.3`).
   - **Check Resource-Based Policies (`lambda:GetPolicy`):** Flag any statement granting `lambda:InvokeFunction` or `lambda:InvokeFunctionUrl` to `Principal: "*"` or to an AWS service (`s3.amazonaws.com`, `sns.amazonaws.com`, `events.amazonaws.com`) without `aws:SourceArn` / `aws:SourceAccount` / `aws:PrincipalOrgID` confused-deputy conditions (`Lambda.1`).
   - **Check Execution Role Per-Function Isolation:** Flag multiple unrelated Lambda functions sharing a single catch-all IAM execution role, or any Lambda role holding `iam:*`, `s3:*`, or `dynamodb:*`.
   - **Check SnapStart Snapshot Isolation (`SnapStart.ApplyOn == "PublishedVersions"`):** Verify that functions using Lambda SnapStart do not fetch long-lived secrets or initialize static PRNG seeds during the `INIT` phase without refreshing them in an `afterRestore` runtime hook.
   - **Check Runtime & Code Vulnerability Scanning:** Flag deprecated runtimes (`Lambda.2`) and check `inspector2:GetCoverageStatistics` for `AWS_LAMBDA_FUNCTION` package and code scanning.
4. **Amazon EC2 Instance, IMDSv2 & Instance Profile Audit:**
   - Check **IMDSv2 Enforcement (`ec2:DescribeInstances`):**
     - Standard EC2 instances: require `MetadataOptions.HttpTokens == "required"` and `HttpPutResponseHopLimit == 1` (`EC2.8`).
     - Container hosts (EKS nodes / ECS EC2 instances): require `HttpTokens == "required"` and `HttpPutResponseHopLimit == 1` when pods/tasks strictly use IRSA, EKS Pod Identity, or `awsvpc` task roles so containers cannot steal host node IAM credentials!
   - Check **Instance Profile Hygiene (`iam:ListInstanceProfiles`, `ec2:DescribeIamInstanceProfileAssociations`):**
     - Verify 1:1 role-to-workload mapping (never attach a generic catch-all EC2 role across disparate web, worker, and bastion fleets).
     - Verify `iam:PassRole` and `ec2:AssociateIamInstanceProfile` / `ec2:ReplaceIamInstanceProfileAssociation` are restricted to specific role ARNs so operators cannot swap a running instance's profile to a higher-privilege role.
   - Check attached EBS volume encryption (`ec2:DescribeVolumes`) and public AMI/Snapshot sharing (`ec2:DescribeImages --owners self`, `ec2:DescribeSnapshots --owner-ids self --restorable-by-user-ids all`).
5. **Amazon Bedrock & Generative AI Workload Security Audit:**
   - **Model Invocation Logging (`bedrock:GetModelInvocationLoggingConfiguration`):** Verify that Model Invocation Logging is enabled to an encrypted S3 bucket (with S3 Object Lock) and/or KMS-encrypted CloudWatch Log Group to maintain an immutable audit trail of prompts, responses, and token usage.
   - **Bedrock Guardrails (`bedrock:ListGuardrails` → `bedrock:GetGuardrail`):** Verify production AI applications and Bedrock Agents enforce a Guardrail with:
     - `contentPolicyConfig` (hate, insults, sexual, violence, misconduct, and **`PROMPT_ATTACK`** input filters set to `HIGH`),
     - `sensitiveInformationPolicyConfig` (PII entities and custom regexes set to `BLOCK` or `ANONYMIZE`),
     - `contextualGroundingPolicyConfig` (`GROUNDING` and `RELEVANCE` thresholds enabled to prevent RAG hallucinations).
   - **Private Network Path (`ec2:DescribeVpcEndpoints`):** Verify VPC workloads invoke Bedrock through Interface VPC Endpoints (`com.amazonaws.<region>.bedrock-runtime`, `com.amazonaws.<region>.bedrock-agent-runtime`) with endpoint policies scoped to `aws:PrincipalOrgID` and allowed foundation model ARNs.
   - **Bedrock Knowledge Bases & Agents (`bedrock-agent:ListKnowledgeBases`, `bedrock-agent:ListAgents`):**
     - Verify Knowledge Base vector stores (Amazon OpenSearch Serverless `aoss` or Aurora PostgreSQL) enforce KMS CMK encryption and strict data access policies.
     - Verify Bedrock Agent and Knowledge Base IAM service roles (`bedrock.amazonaws.com`) enforce `aws:SourceAccount` and `aws:SourceArn` conditions on their trust policies to prevent cross-tenant confused-deputy exploitation.

---

## Output Contract

Emit findings using the standard audit schema (`scope`, `evidence_timestamp`, `control_id`, `finding_type`, `resource_arn_or_id`, `observed_state`, `expected_state`, `evidence`, `recommended_change`, `approval_required: true`).
