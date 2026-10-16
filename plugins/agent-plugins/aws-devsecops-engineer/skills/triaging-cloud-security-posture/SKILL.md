---
name: triaging-cloud-security-posture
description: >-
  Aggregates, correlates, and remediates cloud security posture (CSPM) findings and runtime
  threats across AWS Security Hub (CIS, FSBP), Amazon GuardDuty, Amazon Inspector (ECR, Lambda,
  EC2 CVEs), and AWS Config, mapping live resource ARNs directly to local Terraform, CDK,
  CloudFormation, and Dockerfile code. Use when the user asks to "check cloud security posture",
  "triage GuardDuty or Security Hub findings", "fix Inspector CVEs", or runs `/posture`.
---

# Cloud Security Posture (CSPM) & Runtime Threat Triage

## When to Use
Invoke this skill whenever a user asks for an account security posture review, wants to triage active GuardDuty threat alerts, needs to remediate Security Hub compliance failures (AWS Foundational Security Best Practices, CIS Benchmark, PCI-DSS), or wants to fix Amazon Inspector CVE vulnerabilities across ECR containers, Lambda functions, or EC2 instances.

## 4-Stage Posture Triage & Remediation Workflow

### Stage 1: Multi-Service Posture Sweep (Sandboxed Execution)
Use `aws-well-architected-security` (`CheckSecurityServices`, `GetSecurityFindings`) and `aws___run_script` in `aws-mcp` to sweep Security Hub, GuardDuty, Inspector2, and AWS Config in a single consolidated pass:

```python
import boto3

session = boto3.Session()
summary = {"guardduty": [], "securityhub": [], "inspector": [], "config_noncompliant": []}

# 1. GuardDuty active threats (Severity >= 4.0)
gd = session.client("guardduty")
for det_id in gd.list_detectors().get("DetectorIds", []):
    f_ids = gd.list_findings(
        DetectorId=det_id,
        FindingCriteria={"Criterion": {"severity": {"Gte": 4}, "service.archived": {"Eq": ["false"]}}},
        MaxResults=25,
    ).get("FindingIds", [])
    if f_ids:
        for f in gd.get_findings(DetectorId=det_id, FindingIds=f_ids).get("Findings", []):
            summary["guardduty"].append({
                "id": f["Id"], "type": f["Type"], "severity": f["Severity"],
                "title": f["Title"], "resource": f.get("Resource", {}).get("ResourceType")
            })

# 2. Security Hub CRITICAL & HIGH active findings
sh = session.client("securityhub")
sh_findings = sh.get_findings(
    Filters={
        "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}, {"Value": "NOTIFIED", "Comparison": "EQUALS"}],
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
        "SeverityLabel": [{"Value": "CRITICAL", "Comparison": "EQUALS"}, {"Value": "HIGH", "Comparison": "EQUALS"}],
    },
    MaxResults=50,
).get("Findings", [])
for f in sh_findings:
    summary["securityhub"].append({
        "id": f["Id"], "severity": f["Severity"]["Label"], "title": f["Title"],
        "resources": [r["Id"] for r in f.get("Resources", [])],
        "control": f.get("Compliance", {}).get("SecurityControlId"),
    })

# 3. Inspector2 CRITICAL & HIGH CVEs with available fixes
insp = session.client("inspector2")
insp_findings = insp.list_findings(
    filterCriteria={
        "findingStatus": [{"comparison": "EQUALS", "value": "ACTIVE"}],
        "severity": [{"comparison": "EQUALS", "value": "CRITICAL"}, {"comparison": "EQUALS", "value": "HIGH"}],
        "fixAvailable": [{"comparison": "EQUALS", "value": "YES"}],
    },
    maxResults=25,
).get("findings", [])
for f in insp_findings:
    summary["inspector"].append({
        "arn": f["findingArn"], "severity": f["severity"], "title": f.get("title"),
        "resource": f["resources"][0]["id"] if f.get("resources") else "unknown",
    })

print(summary)
```

### Stage 2: Risk Deduplication & Blast-Radius Prioritization
Deduplicate overlapping alerts (e.g., an AWS Config rule, a Security Hub control, and an Inspector CVE all flagging the same workload) and rank them by:
1. **Active Exploitation / Runtime Threat (P0)**: GuardDuty findings (`UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration`, `CryptoCurrency:EC2/*`, `Execution:Runtime/*`). Immediately chain `auditing-cloudtrail-forensics` for any P0 GuardDuty alert.
2. **Publicly Exposed Misconfigurations & Exploitable CVEs (P1)**: Public S3 buckets, `0.0.0.0/0` administrative ports (`22`, `3389`, `5432`, `6379`), unencrypted public RDS snapshots, and CRITICAL Inspector CVEs with `fixAvailable == YES` on internet-facing ECS/EKS/Lambda workloads.
3. **Compliance & Defense-in-Depth Drift (P2)**: Missing KMS rotation, missing VPC Flow Logs, IMDSv1 enabled on EC2 (`HttpTokens: optional`), or unattached WAF WebACLs.

### Stage 3: Resource-ARN-to-IaC Mapping
Never recommend manual console ClickOps if the resource is managed by Infrastructure-as-Code:
1. Extract the resource identifier, logical ID, or `aws:cloudformation:stack-name` tag from the finding's `Resources` block.
2. Use `Grep` and `Glob` across the local repository (`*.tf`, `*.ts`, `*.py`, `template.yaml`, `Dockerfile`, `package.json`, `requirements.txt`) to locate the exact construct or container base image defining the resource.

### Stage 4: Verified Remediation & Workflow Update
1. Apply the IaC or dependency patch locally (`Edit`) and validate with `hardening-iac-and-perimeter` or `diff-scanning-with-aws-security-agent`.
2. Present any live containment command (e.g., isolating a compromised instance security group or rotating exposed credentials) for explicit user approval via `aws-mutation-gate.py`.
3. Once remediated and verified, offer to update the Security Hub finding workflow status (`aws securityhub batch-update-findings --workflow Status=RESOLVED`) after user confirmation.
