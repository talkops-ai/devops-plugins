# AWS Trust Boundary Patterns & Data Perimeter Reference

Use these canonical trust boundary definitions when decomposing AWS architectures in Phase 3 of `aws-threat-modeling`.

## 1. Network & Edge Trust Boundaries
- **Public Internet $\rightarrow$ Edge Perimeter (`TB-EDGE`)**:
  - Crossed by: Client browsers, mobile apps, webhook senders.
  - Mandatory Controls: Route 53 DNSSEC, CloudFront with Origin Access Control (OAC) or Origin Custom Header + ALB SG locked to `com.amazonaws.global.cloudfront.origin-facing` managed prefix list, AWS WAFv2 (`AWSManagedRulesCommonRuleSet`, `AWSManagedRulesKnownBadInputsRuleSet`, rate-limiting), TLS 1.3 minimum policy.
- **Public Subnet $\rightarrow$ Private Application Subnet (`TB-APP-NET`)**:
  - Crossed by: ALB/NLB forwarding traffic to ECS Tasks, EKS Pods, or EC2 instances.
  - Mandatory Controls: Security Group chaining (`SourceSecurityGroupId: !Ref AlbSecurityGroup` — never CIDR `0.0.0.0/0`), no public IPv4 addresses on compute tasks/nodes.
- **Private Application Subnet $\rightarrow$ Isolated Data Subnet / VPC Endpoints (`TB-DATA-NET`)**:
  - Crossed by: Application queries to Aurora/RDS, ElastiCache Valkey, OpenSearch, or AWS API calls over PrivateLink.
  - Mandatory Controls: Isolated subnets with zero route to `igw-*` or `nat-*`; Database SG allowing port `5432`/`3306`/`6379` exclusively from the Application SG; Gateway/Interface VPC Endpoints with scoped Endpoint Policies.

## 2. Identity, Multi-Account & Data Perimeter Trust Boundaries
- **Service-to-Service IAM Assumption (`TB-IAM-STS`)**:
  - Crossed by: EventBridge, Lambda, Step Functions, Bedrock, or CodeBuild assuming an execution role.
  - Mandatory Controls: Explicit `aws:SourceArn` and `aws:SourceAccount` condition keys on the role's `AssumeRolePolicyDocument` to prevent Cross-Service Confused Deputy attacks.
- **Organization Data Perimeter (`TB-DATA-PERIMETER`)**:
  - Enforces the 3 AWS Data Perimeter invariants across AWS Organizations via SCPs and RCPs:
    1. **Only Trusted Identities**: `aws:PrincipalOrgID == "${org-id}"`
    2. **Only Trusted Resources**: `aws:ResourceOrgID == "${org-id}"`
    3. **Only From Expected Networks**: `aws:SourceVpc` / `aws:VpceOrgID == "${org-id}"` or `aws:ViaAWSService == true`
- **Autonomous AI Agent / MCP Boundary (`TB-AGENT-MCP`)**:
  - Crossed by: AI agents invoking AWS APIs through MCP servers or Bedrock AgentCore Gateways.
  - Mandatory Controls: Local `PreToolUse` hooks (`secret-safety.py` + `aws-mutation-gate.py`) paired with IAM `Deny` statements conditioned on `"Bool": {"aws:ViaAWSMCPService": "true"}` for all non-read-only actions.
