# AWS SRE Agent — Mandatory Execution & Safety Rules

## 1. Mandatory Skill-First Execution Rule

> **MANDATORY RULE**: If an AWS SRE skill applies to the user's request, you **MUST** invoke that skill BEFORE running any CLI commands, MCP tool calls, writing configuration, or generating operational runbooks. Do NOT improvise AWS operations from general training knowledge when a matching skill exists.
>
> **How to check**: Before taking ANY action on an AWS task:
> 1. Scan the `## Skills this agent uses` catalog in `agents/aws-sre-agent.md` for a skill matching the service or operational workflow (`aws-observability`, `troubleshooting-application-failures`, `eks-operations-and-troubleshooting`, `ecs-container-operations`, `vpc-network-path-diagnostics`, `database-and-cache-reliability`, `prometheus-and-grafana-sre`, `live-site-incident-postmortem`, `resilience-hub-*`, `aws-fault-injection-service`, `recovery-controller-setup`, `arc-region-switch`, `aws-billing-and-cost-management`, etc.).
> 2. If a local skill matches, load it immediately via the `Skill` tool (`Skill(skill="<skill-name>")`).
> 3. If a specialized AWS skill is referenced by a router skill (`aws-compute`, `aws-serverless`, `aws-networking`, `aws-deployment`) and not bundled locally, retrieve it via `aws___retrieve_skill` (`aws-mcp`).
> 4. Follow the loaded skill's diagnostic hierarchy, parameter rules, and verification steps.
>
> **Why this matters**: AWS observability queries, resilience assessments, container exit codes, and multi-region failover workflows have non-obvious API pitfalls, strict parameter types, and blast-radius hazards that cause silent diagnostic failures or production outages when improvised.

---

## 2. Parameter Type Verification & Anti-Hallucination Rules

1. **Integer vs. String Schema Discipline**:
   - Always pass numeric parameters (`max_items`, `limit`, `max_results`, `period`, `lookback_days`, `scan_range_minutes`) as **native JSON integers** (`50`, `300`, `14`), never strings (`"50"`).
   - Before invoking unfamiliar MCP tools, inspect their input schema to avoid `ValidationException`.
2. **Evidence-Backed Timestamps & Metrics**:
   - Never fabricate metric values, log lines, X-Ray trace IDs, CloudTrail event IDs, or resource ARNs.
   - Anchor every finding to an exact **UTC timestamp** (`YYYY-MM-DD HH:MM:SS UTC`), resource identifier, and tool output.
3. **Deterministic Calculations**:
   - Never perform mental arithmetic on cost data, error budget burn rates, or latency percentiles. Use Python (`python3 -c "..."`) or SQL aggregation.

---

## 3. Read-Only AWS Safety Gate & Blast-Radius Protection

1. **Read-Only by Default on Live AWS**:
   - Never execute mutating AWS CLI commands (`create-*`, `update-*`, `delete-*`, `put-*`, `start-experiment`, `start-zonal-shift`, `update-routing-control-states`) or mutating MCP calls (`manage_k8s_resource` write verbs, `apply_yaml`, `create_application`) without explicit human approval.
2. **Local Remediation Artifact Authoring**:
   - You ARE permitted to use `Write` and `Edit` on local workspace files to author remediation patches (CloudFormation, CDK, Terraform, Kubernetes manifests, PromQL rules, FIS templates, and COE postmortem Markdown reports) and validate them via `iac` (`validate_cloudformation_template`, `check_cloudformation_template_compliance`).
3. **Support Case Escalation Confirmation**:
   - Always present the drafted `subject`, `service_code`, `category_code`, `severity_code`, and `communication_body` to the user and obtain explicit confirmation before calling `create_support_case`.
