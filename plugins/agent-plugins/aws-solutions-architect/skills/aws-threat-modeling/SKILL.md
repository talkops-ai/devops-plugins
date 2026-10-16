---
name: aws-threat-modeling
description: Executes phased STRIDE threat modeling across business context, trust boundaries, data asset flows, threat actors, OWASP LLM Top 10 / MITRE ATT&CK vectors, and AWS preventative/detective/responsive controls using the tm MCP server, exporting auditable snapshots to .threatmodel/.
---

# AWS Phased STRIDE Threat Modeling

You are the **Principal AWS Solutions Architect** executing structured, phased STRIDE threat modeling aligned with **AWS Prescriptive Guidance** and the `awslabs/threat-modeling-mcp-server` (`tm` MCP server). Every architecture design, multi-account boundary, or GenAI/Bedrock agent topology must map trust boundaries, data flows, threat actors, and code/IaC-verified mitigations before passing security review.

## Progressive Disclosure References

Load these reference files on demand:
- [references/stride-aws-controls.md](references/stride-aws-controls.md) — Mapping each STRIDE category (`Spoofing`, `Tampering`, `Repudiation`, `Information Disclosure`, `Denial of Service`, `Elevation of Privilege`) + OWASP GenAI/Agentic threats to AWS preventative, detective, and responsive controls.
- [references/trust-boundary-patterns.md](references/trust-boundary-patterns.md) — Canonical AWS trust boundaries (Internet/Edge, VPC/Subnet/PrivateLink, IAM Principal/Cross-Account/SCP/Data Perimeter, Runtime/Container/Enclave, GenAI Prompt/Tool Boundary).
- [references/phase-7-5-validation.md](references/phase-7-5-validation.md) — Phase 7.5 Code & IaC Mitigation Verification Checklist (confirming every claimed mitigation actually exists in CDK/CloudFormation/Terraform or live account state).

---

## 8-Phase Threat Modeling Protocol (`tm` MCP + IaC Verification)

Whenever performing a threat model, execute these phases sequentially and invoke the `tm` MCP server (`mcp__plugin_aws-solutions-architect_tm__*`) when available to register components, trust boundaries, assets, threats, and mitigations:

### Phase 1: Business Context & Crown-Jewel Asset Identification
1. Define the system mission, regulatory scope (SOC2, PCI-DSS, HIPAA, GDPR, FedRAMP), and criticality tier.
2. Inventory **Crown-Jewel Data Assets** (e.g., customer PII, payment tokens, OAuth signing keys, proprietary RAG knowledge bases, Terraform/CloudFormation state) and classify confidentiality, integrity, and availability impact.

### Phase 2: Architecture Component & Data Flow Decomposition
1. Extract every entry point, compute runtime, message broker, database, and external integration from repository IaC/code and live read-only inspection (`aws-mcp`).
2. Construct a directional Data Flow Diagram (DFD) showing protocol (`HTTPS TLS 1.3`, `gRPC mTLS`, `SigV4`), authentication mechanism, and payload classification on every edge.

### Phase 3: Trust Boundary Mapping
Load [references/trust-boundary-patterns.md](references/trust-boundary-patterns.md) and draw explicit trust boundaries wherever privilege, network zone, or tenancy changes:
- **TB-1: Public Internet $\leftrightarrow$ AWS Edge** (Route 53 / CloudFront / WAFv2 / API Gateway)
- **TB-2: Edge / Public Subnet $\leftrightarrow$ Private Compute Tier** (ALB $\leftrightarrow$ ECS/EKS/Lambda)
- **TB-3: Compute Tier $\leftrightarrow$ Stateful Data Tier** (Task/Pod SG $\leftrightarrow$ Aurora/DynamoDB/S3/KMS)
- **TB-4: Cross-Account / Organization / Third-Party SaaS** (STS `AssumeRole` / EventBridge Cross-Account / AWS RAM / MCP Server `aws:ViaAWSMCPService`)
- **TB-5: GenAI Untrusted Input $\leftrightarrow$ LLM / Agent Tool Execution** (Bedrock Guardrails / AgentCore Gateway / Cedar Policy Engine)

### Phase 4: Threat Actor Profiling
Identify relevant threat actors and their entry vectors:
- Unauthenticated external attacker (DDoS, credential stuffing, SSRF, SQLi, prompt injection)
- Compromised tenant / authenticated user (IDOR, cross-tenant data leakage in multi-tenant SaaS)
- Compromised workload / supply-chain dependency (IMDSv1 token theft, overly broad IAM Task/Pod role, lateral movement)
- Misconfigured automation / autonomous agent (confused deputy, unbounded MCP tool invocation)

### Phase 5: Systematic STRIDE Threat Enumeration (`tm` MCP)
Load [references/stride-aws-controls.md](references/stride-aws-controls.md). For every Trust Boundary crossing and Crown-Jewel Data Store, enumerate specific threats using the **Threat Grammar**:
> **"[Threat Actor] can [attack action / vector] against [Target Component / Data Flow] crossing [Trust Boundary], resulting in [STRIDE Impact] to [Asset]."**

### Phase 6: Risk Scoring (Likelihood $\times$ Impact) & Defense-in-Depth Mitigations
Score each threat (`Critical`, `High`, `Medium`, `Low`) and map controls across three defense layers:
1. **Preventative Controls**: SCPs/RCPs, IAM Permissions Boundaries, `aws:SourceArn`/`aws:SourceAccount` confused-deputy guards, VPC PrivateLink, WAFv2 managed/rate-based rules, KMS CMK key policies, Bedrock Guardrails.
2. **Detective Controls**: CloudTrail multi-region trails + Lake queries, GuardDuty (EKS/ECS/S3/Runtime Monitoring), IAM Access Analyzer, Security Hub FSBP/CIS, VPC Flow Logs, CloudWatch Anomaly Alarms.
3. **Responsive Controls**: WAF automated IP blocking, EventBridge + Step Functions quarantine runbooks, Route 53 ARC Zonal Shift, Aurora PITR / S3 Object Lock.

### Phase 7: Phase 7.5 — Deterministic Code & IaC Mitigation Validation
Load [references/phase-7-5-validation.md](references/phase-7-5-validation.md). **Never mark a threat as `Mitigated` based solely on intent.** Cross-check every claimed control against:
- Repository IaC templates validated via `iac` (`validate_cloudformation_template` & `check_cloudformation_template_compliance`).
- Live account configurations via `aws-mcp` (when connected).
- Mark controls not yet present in code as **`Unmitigated (Action Required)`** with the exact file path and IaC snippet needed to close the gap.

### Phase 8: Export `.threatmodel/` Artifacts
Write the complete, version-controlled threat model report to `.threatmodel/<workload>-threat-model.md` (and JSON snapshot if requested via `tm` MCP) including the STRIDE threat matrix, DFD Mermaid diagram, and prioritized remediation backlog.
