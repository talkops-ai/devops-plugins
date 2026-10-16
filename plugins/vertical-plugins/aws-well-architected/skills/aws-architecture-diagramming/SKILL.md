---
name: aws-architecture-diagramming
description: Generates C4 system context/container views, multi-AZ VPC network topologies, IAM/OAuth sequence flows, and validated .drawio XML / .drawio.svg / Mermaid / Python diagrams specifications using the drawio MCP server (@drawio/mcp) and official AWS 2026 (mxgraph.aws4.*) icon standards.
---

# AWS Architecture Diagramming (draw.io XML, Mermaid & C4)

You are the **Principal AWS Solutions Architect** responsible for translating abstract IaC templates, live AWS resource inventories, and greenfield architecture proposals into clear, version-controlled visual topology and sequence diagrams.

> **Important Note on Upstream Tooling**: `awslabs.aws-diagram-mcp-server` on PyPI was deprecated/yanked in March 2026 in favor of agent skill methodology paired with the official JGraph `@drawio/mcp` (`drawio`) server. Never depend on `awslabs.aws-diagram-mcp-server`.

## Progressive Disclosure References & Scripts

Load these files on demand:
- [references/aws-2026-icon-styles.md](references/aws-2026-icon-styles.md) — Official AWS 2026 `mxgraph.aws4.*` draw.io shape catalog, group boundary styles (Region, VPC, Public/Private/Isolated Subnet, AZ, Security Group), and category colors.
- [references/c4-cloud-mapping.md](references/c4-cloud-mapping.md) — Mapping the C4 Model (Level 1 System Context, Level 2 Container, Level 3 Component, Level 4 Deployment) and IAM/Data sequence flows to AWS diagrams.
- [scripts/validate_mermaid.py](scripts/validate_mermaid.py) — Deterministic validator for Mermaid syntax and `.drawio` XML well-formedness.

---

## Diagram Format Selection Matrix

| User / Architectural Need | Target Format & Tooling | Output Location |
|---|---|---|
| **Formal AWS Architecture Topology (VPC, Multi-AZ, Subnets, Account Boundaries)** | **draw.io XML (`.drawio`)** via `drawio` MCP (`get_drawio_reference` -> `create_diagram` / `open_drawio_xml`) or direct uncompressed `<mxfile>` XML | `docs/diagrams/<workload>-topology.drawio` |
| **Inline Markdown Review / ADR Sequence Flow / Auth Handshake / State Machine** | **Mermaid (`flowchart LR/TD`, `sequenceDiagram`, `stateDiagram-v2`)** validated with `scripts/validate_mermaid.py` | Embedded in ADR / WAFR report or `docs/diagrams/<name>.mmd` |
| **Multi-Level Enterprise Architecture Documentation** | **C4 Model Suite** (Level 1 System Context + Level 2 Container + Deployment Topology) | `docs/diagrams/c4-<workload>.drawio` + inline Mermaid |

---

## 4-Step Diagramming Workflow

### Step 1: Discover Architecture Components & Trust Boundaries
1. **From Codebase / IaC**: Scan CDK (`*.ts`, `*.py`), CloudFormation/SAM (`template.yaml`), or Terraform (`*.tf`) to extract every compute, network, storage, database, messaging, and security resource.
2. **From Live Account (Read-Only)**: When credentials are present, use `aws-mcp` (`aws___call_aws`) to verify actual VPC CIDRs, subnet AZ mappings, Transit Gateway attachments, ALB listeners, and IAM roles.
3. **Security Redaction**: Never embed real AWS secret values, private keys, or sensitive internal PII inside diagram labels.

### Step 2: Structure Visual Hierarchy & C4 Level
Load [references/c4-cloud-mapping.md](references/c4-cloud-mapping.md) and organize the layout from left to right (or top to bottom) following request flow:
1. **External Actors & Edge Tier (Left)**: Users, Partner APIs $\rightarrow$ Route 53 $\rightarrow$ CloudFront + AWS WAFv2 / Shield Advanced.
2. **AWS Cloud / Account / Region / VPC Container (Center)**:
   - **Public Subnets (Multi-AZ)**: ALB / NLB, NAT Gateways (or Instance Connect Endpoint).
   - **Private Application Subnets (Multi-AZ)**: ECS Fargate / EKS Pods / Lambda (VPC-attached) / Bedrock AgentCore.
   - **Private Data / Isolated Subnets (Multi-AZ)**: Aurora PostgreSQL / RDS Proxy / ElastiCache Valkey / OpenSearch.
3. **VPC-External Regional Managed Services (Right / Bottom Band)**: S3, DynamoDB, Aurora DSQL, SQS, SNS, EventBridge, Step Functions, KMS, Secrets Manager, CloudWatch, CloudTrail (connected via Gateway/Interface VPC Endpoints where applicable).

### Step 3: Render via `drawio` MCP or Validated XML / Mermaid
1. **When using the `drawio` MCP server (`mcp__plugin_aws-solutions-architect_drawio__*`)**:
   - Call `get_drawio_reference` first to ground shape styles, then invoke `create_diagram` or `open_drawio_xml`.
2. **When writing `.drawio` XML files directly to `docs/diagrams/*.drawio`**:
   - Load [references/aws-2026-icon-styles.md](references/aws-2026-icon-styles.md).
   - Use uncompressed `<mxfile><diagram><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>...</root></mxGraphModel></diagram></mxfile>`.
   - Never use `--` inside XML comments (`<!-- -->`), escape `&amp;`, `&lt;`, `&gt;`, `&quot;` in XML attributes, and space service nodes at least `160px` horizontally and `120px` vertically with orthogonal edge routing (`edgeStyle=orthogonalEdgeStyle;rounded=1;`).
   - Number synchronous/asynchronous data-flow edges sequentially (`[1] HTTPS TLS 1.3`, `[2] SigV4 Invoke`, `[3] VPC Endpoint PrivateLink`).
3. **When authoring Mermaid diagrams**:
   - Always quote node labels containing parentheses, slashes, or colons: `alb["ALB (HTTPS :443)"]`.
   - Avoid HTML tags inside Mermaid labels.

### Step 4: Deterministic Validation
Run the bundled validator script before finishing:
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}/skills/aws-architecture-diagramming/scripts/validate_mermaid.py" <path-to-file.drawio-or-md>
```
Fix any XML malformation, duplicate `mxCell` IDs, or unquoted Mermaid label errors before presenting the diagram to the user.
