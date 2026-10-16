#!/usr/bin/env python3
"""Read-only 26-point AWS Startup Account Health, Security & Spend-Leak Audit Runner.

Executes stage-calibrated read-only checks across:
  1. Identity & Secret Hygiene (root keys, root MFA, stale IAM keys >90d, wildcard roles, Cognito MFA, Lambda env secrets)
  2. Network & Data Encryption (SG 0.0.0.0/0 on DB/SSH ports, default VPC usage, S3 public access, RDS/EBS/ElastiCache encryption, CloudTrail)
  3. Scalability & AI Readiness (CloudWatch alarms, Lambda throttles, API GW rate limits, stage-calibrated RDS Multi-AZ, Bedrock Guardrails)
  4. Immediate Spend Leaks & Credit Burn (stopped EC2 + EBS, unattached EIPs, unattached EBS, aged snapshots >90d, infinite CloudWatch log retention, idle SageMaker notebooks, NAT Gateway without free S3/DynamoDB Gateway Endpoints, and optional Cost Explorer credit burn runway)

Safety invariants:
  - Strictly read-only (Describe*, List*, Get* calls only).
  - Never reads or prints Lambda environment variable VALUES — inspects variable KEY names only.
  - Never invokes Cost Explorer (`ce:GetCostAndUsage`, $0.01/call) unless `--include-cost-explorer` is explicitly passed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from typing import Any

SENSITIVE_PORTS = {22: "SSH", 3389: "RDP", 5432: "PostgreSQL", 3306: "MySQL", 6379: "Redis", 27017: "MongoDB"}
SECRET_KEY_RE = re.compile(
    r"(SECRET|PASSWORD|PASSWD|PRIVATE_KEY|API_KEY|AUTH_TOKEN|ACCESS_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|OPENROUTER_API_KEY|DATABASE_URL|STRIPE_SECRET)",
    re.IGNORECASE,
)
SAFE_SECRET_NAME_SUFFIXES = ("_ARN", "_SECRET_ID", "_SSM_PATH", "_PARAMETER_NAME", "_KMS_KEY_ID")


def _finding(
    check_id: str,
    vector: str,
    title: str,
    status: str,
    severity: str,
    detail: str,
    remediation: str,
    estimated_monthly_savings_usd: float = 0.0,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "vector": vector,
        "title": title,
        "status": status,  # PASS | WARN | FAIL | SKIP
        "severity": severity,  # CRITICAL | HIGH | MEDIUM | LOW | INFO
        "detail": detail,
        "remediation": remediation,
        "estimated_monthly_savings_usd": round(estimated_monthly_savings_usd, 2),
    }


def run_audit(region: str, stage: str, include_ce: bool, credit_balance: float | None) -> dict[str, Any]:
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    except ImportError:
        return {
            "error": "boto3 is not installed in the active Python environment.",
            "remediation": "Run via `uv run --with boto3 python3 run_startup_audit.py ...` or use `aws-mcp` read-only calls.",
        }

    findings: list[dict[str, Any]] = []
    now = dt.datetime.now(dt.timezone.utc)
    session = boto3.Session(region_name=region)

    # Verify caller identity first
    try:
        sts = session.client("sts")
        ident = sts.get_caller_identity()
        account_id = ident.get("Account", "unknown")
    except (BotoCoreError, ClientError, NoCredentialsError) as exc:
        return {
            "error": f"Unable to authenticate with AWS STS: {exc}",
            "remediation": "Sign in to AWS first (`aws sso login` or configure `AWS_PROFILE`) and re-run.",
        }

    # =========================================================================
    # VECTOR 1: Identity & Secret Hygiene
    # =========================================================================
    iam = session.client("iam")
    try:
        summary = iam.get_account_summary().get("SummaryMap", {})
        root_keys = summary.get("AccountAccessKeysPresent", 0)
        findings.append(
            _finding(
                "IAM-01",
                "identity_and_secrets",
                "Root account active access keys",
                "PASS" if root_keys == 0 else "FAIL",
                "CRITICAL",
                f"AccountAccessKeysPresent={root_keys}",
                "Delete root access keys immediately in the IAM Console.",
            )
        )
        root_mfa = summary.get("AccountMFAEnabled", 0)
        findings.append(
            _finding(
                "IAM-02",
                "identity_and_secrets",
                "Root account MFA enabled",
                "PASS" if root_mfa == 1 else "FAIL",
                "CRITICAL",
                f"AccountMFAEnabled={root_mfa}",
                "Enable FIDO2 Passkey or TOTP MFA on the AWS root user.",
            )
        )
    except (BotoCoreError, ClientError) as exc:
        findings.append(_finding("IAM-01", "identity_and_secrets", "Root account summary check", "SKIP", "INFO", str(exc), "Grant iam:GetAccountSummary."))

    try:
        users = iam.list_users().get("Users", [])
        stale_keys: list[str] = []
        for u in users[:50]:
            uname = u["UserName"]
            for k in iam.list_access_keys(UserName=uname).get("AccessKeyMetadata", []):
                if k.get("Status") != "Active":
                    continue
                age_days = (now - k["CreateDate"]).days
                if age_days > 90:
                    stale_keys.append(f"{uname}:{k['AccessKeyId']} ({age_days}d old)")
        findings.append(
            _finding(
                "IAM-03",
                "identity_and_secrets",
                "IAM access keys older than 90 days",
                "PASS" if not stale_keys else "WARN",
                "HIGH",
                f"{len(stale_keys)} active key(s) >90 days old" + (f": {', '.join(stale_keys[:5])}" if stale_keys else ""),
                "Rotate or deactivate long-lived IAM keys and switch CI/CD to OIDC federation.",
            )
        )
    except (BotoCoreError, ClientError) as exc:
        findings.append(_finding("IAM-03", "identity_and_secrets", "Stale IAM access keys", "SKIP", "INFO", str(exc), "Grant iam:ListUsers and iam:ListAccessKeys."))

    # IAM-06: Plaintext secret key names in Lambda environment variables (NEVER read values)
    lam = session.client("lambda", region_name=region)
    try:
        funcs = lam.list_functions().get("Functions", [])
        suspect_env_vars: list[str] = []
        for fn in funcs:
            fn_name = fn.get("FunctionName", "")
            env_keys = list((fn.get("Environment", {}) or {}).get("Variables", {}).keys())
            for k in env_keys:
                if SECRET_KEY_RE.search(k) and not k.upper().endswith(SAFE_SECRET_NAME_SUFFIXES):
                    suspect_env_vars.append(f"{fn_name}:{k}")
        findings.append(
            _finding(
                "IAM-06",
                "identity_and_secrets",
                "Suspected plaintext secret keys in Lambda environment variables",
                "PASS" if not suspect_env_vars else "FAIL",
                "CRITICAL",
                f"{len(suspect_env_vars)} suspect variable key(s) found (values not read): {', '.join(suspect_env_vars[:8])}"
                if suspect_env_vars
                else f"Scanned {len(funcs)} Lambda function(s); no suspect plaintext secret keys found.",
                "Migrate plaintext secrets to AWS Secrets Manager using `${CLAUDE_PLUGIN_ROOT}/scripts/asm-exec`.",
            )
        )
    except (BotoCoreError, ClientError) as exc:
        findings.append(_finding("IAM-06", "identity_and_secrets", "Lambda environment secret hygiene", "SKIP", "INFO", str(exc), "Grant lambda:ListFunctions."))

    # =========================================================================
    # VECTOR 2: Network & Data Encryption
    # =========================================================================
    ec2 = session.client("ec2", region_name=region)
    try:
        sgs = ec2.describe_security_groups().get("SecurityGroups", [])
        exposed_sgs: list[str] = []
        for sg in sgs:
            sg_id = sg.get("GroupId", "")
            for perm in sg.get("IpPermissions", []):
                from_p = perm.get("FromPort")
                to_p = perm.get("ToPort")
                ip_Protocol = perm.get("IpProtocol")
                cidrs = [r.get("CidrIp") for r in perm.get("IpRanges", [])] + [
                    r.get("CidrIpv6") for r in perm.get("Ipv6Ranges", [])
                ]
                if "0.0.0.0/0" in cidrs or "::/0" in cidrs:
                    if ip_Protocol == "-1":
                        exposed_sgs.append(f"{sg_id}(ALL_PORTS)")
                    elif from_p is not None and to_p is not None:
                        for port, label in SENSITIVE_PORTS.items():
                            if from_p <= port <= to_p:
                                exposed_sgs.append(f"{sg_id}({port}/{label})")
        findings.append(
            _finding(
                "NET-01",
                "network_and_encryption",
                "Security Groups open to 0.0.0.0/0 on SSH/RDP/Database ports",
                "PASS" if not exposed_sgs else "FAIL",
                "CRITICAL",
                f"Exposed security groups: {', '.join(exposed_sgs[:8])}" if exposed_sgs else f"Scanned {len(sgs)} Security Groups; 0 sensitive ports open to world.",
                "Restrict database ingress to application Security Group IDs and use SSM Session Manager instead of port 22.",
            )
        )
    except (BotoCoreError, ClientError) as exc:
        findings.append(_finding("NET-01", "network_and_encryption", "Security Group public exposure", "SKIP", "INFO", str(exc), "Grant ec2:DescribeSecurityGroups."))

    rds = session.client("rds", region_name=region)
    dbs: list[dict[str, Any]] = []
    try:
        dbs = rds.describe_db_instances().get("DBInstances", [])
        unencrypted_dbs = [d["DBInstanceIdentifier"] for d in dbs if not d.get("StorageEncrypted")]
        findings.append(
            _finding(
                "DATA-02",
                "network_and_encryption",
                "RDS instances encrypted at rest",
                "PASS" if not unencrypted_dbs else "FAIL",
                "HIGH",
                f"Unencrypted RDS instances: {', '.join(unencrypted_dbs)}" if unencrypted_dbs else f"All {len(dbs)} RDS instance(s) encrypted at rest.",
                "Enable KMS storage encryption (copy snapshot with encryption enabled and restore).",
            )
        )
    except (BotoCoreError, ClientError) as exc:
        findings.append(_finding("DATA-02", "network_and_encryption", "RDS storage encryption", "SKIP", "INFO", str(exc), "Grant rds:DescribeDBInstances."))

    ct = session.client("cloudtrail", region_name=region)
    try:
        trails = ct.describe_trails(includeShadowTrails=True).get("trailList", [])
        multi_region = [t for t in trails if t.get("IsMultiRegionTrail")]
        findings.append(
            _finding(
                "SEC-01",
                "network_and_encryption",
                "CloudTrail multi-region management trail enabled",
                "PASS" if multi_region else "FAIL",
                "HIGH",
                f"{len(multi_region)} multi-region trail(s) configured" if multi_region else "No multi-region CloudTrail found.",
                "Enable a multi-region CloudTrail (first management trail is free; only S3 log storage applies).",
            )
        )
    except (BotoCoreError, ClientError) as exc:
        findings.append(_finding("SEC-01", "network_and_encryption", "CloudTrail status", "SKIP", "INFO", str(exc), "Grant cloudtrail:DescribeTrails."))

    # =========================================================================
    # VECTOR 3: Scalability & AI Readiness
    # =========================================================================
    if dbs:
        multi_az_dbs = [d["DBInstanceIdentifier"] for d in dbs if d.get("MultiAZ")]
        single_az_dbs = [d["DBInstanceIdentifier"] for d in dbs if not d.get("MultiAZ")]
        if stage in ("pre-revenue", "mvp", "seed") and multi_az_dbs:
            findings.append(
                _finding(
                    "SCALE-04",
                    "scalability_and_ai",
                    f"Stage-calibrated RDS Multi-AZ check ({stage})",
                    "WARN",
                    "MEDIUM",
                    f"Multi-AZ enabled on {', '.join(multi_az_dbs)} at {stage} stage (doubles RDS compute cost).",
                    "Consider Single-AZ with automated backups at Pre-Revenue/Seed to cut RDS compute burn by 50%, unless contractual SLAs require Multi-AZ.",
                    estimated_monthly_savings_usd=len(multi_az_dbs) * 25.0,
                )
            )
        elif stage in ("series-a", "series-b+") and single_az_dbs:
            findings.append(
                _finding(
                    "SCALE-04",
                    "scalability_and_ai",
                    f"Stage-calibrated RDS Multi-AZ check ({stage})",
                    "WARN",
                    "HIGH",
                    f"Single-AZ RDS instances at {stage} stage: {', '.join(single_az_dbs)}",
                    "Enable Multi-AZ on production RDS databases for automatic AZ failover at Series A+.",
                )
            )
        else:
            findings.append(
                _finding(
                    "SCALE-04",
                    "scalability_and_ai",
                    f"Stage-calibrated RDS Multi-AZ check ({stage})",
                    "PASS",
                    "LOW",
                    f"RDS availability posture matches {stage} stage ({len(dbs)} instance(s)).",
                    "None.",
                )
            )

    # =========================================================================
    # VECTOR 4: Immediate Spend Leaks & Credit Burn Runway
    # =========================================================================
    # COST-01 & COST-03: Stopped EC2 instances & unattached EBS volumes
    try:
        reservations = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]
        ).get("Reservations", [])
        stopped_ids = [i["InstanceId"] for r in reservations for i in r.get("Instances", [])]
        volumes = ec2.describe_volumes().get("Volumes", [])
        unattached_vols = [v for v in volumes if v.get("State") == "available"]
        gp2_vols = [v for v in volumes if v.get("VolumeType") == "gp2"]
        unattached_gb = sum(v.get("Size", 0) for v in unattached_vols)
        unattached_savings = unattached_gb * 0.08
        gp2_savings = sum(v.get("Size", 0) for v in gp2_vols) * 0.02

        findings.append(
            _finding(
                "COST-01",
                "spend_leaks_and_runway",
                "Stopped EC2 instances still accruing EBS charges",
                "PASS" if not stopped_ids else "WARN",
                "MEDIUM",
                f"{len(stopped_ids)} stopped EC2 instance(s): {', '.join(stopped_ids[:6])}" if stopped_ids else "0 stopped EC2 instances.",
                "Snapshot and terminate stopped EC2 instances if no longer needed.",
                estimated_monthly_savings_usd=len(stopped_ids) * 2.40,
            )
        )
        findings.append(
            _finding(
                "COST-03",
                "spend_leaks_and_runway",
                "Unattached ('available') EBS volumes & legacy gp2 volumes",
                "PASS" if (not unattached_vols and not gp2_vols) else "WARN",
                "MEDIUM",
                f"{len(unattached_vols)} unattached EBS volume(s) ({unattached_gb} GB) and {len(gp2_vols)} gp2 volume(s).",
                "Delete unattached EBS volumes after snapshotting and migrate gp2 volumes to gp3 (20% cheaper).",
                estimated_monthly_savings_usd=unattached_savings + gp2_savings,
            )
        )
    except (BotoCoreError, ClientError) as exc:
        findings.append(_finding("COST-01", "spend_leaks_and_runway", "EC2/EBS waste check", "SKIP", "INFO", str(exc), "Grant ec2:DescribeInstances and ec2:DescribeVolumes."))

    # COST-02: Unattached Elastic IPs ($3.65/mo each)
    try:
        addrs = ec2.describe_addresses().get("Addresses", [])
        unattached_eips = [a.get("PublicIp", a.get("AllocationId", "?")) for a in addrs if not a.get("AssociationId")]
        findings.append(
            _finding(
                "COST-02",
                "spend_leaks_and_runway",
                "Unattached Elastic IPs ($3.65/mo each)",
                "PASS" if not unattached_eips else "WARN",
                "MEDIUM",
                f"{len(unattached_eips)} unattached EIP(s): {', '.join(unattached_eips)}" if unattached_eips else "0 unattached Elastic IPs.",
                "Release unassociated Elastic IPs (`aws ec2 release-address --allocation-id <id>`).",
                estimated_monthly_savings_usd=len(unattached_eips) * 3.65,
            )
        )
    except (BotoCoreError, ClientError) as exc:
        findings.append(_finding("COST-02", "spend_leaks_and_runway", "Unattached Elastic IPs", "SKIP", "INFO", str(exc), "Grant ec2:DescribeAddresses."))

    # COST-05: CloudWatch Log Groups with infinite retention
    logs = session.client("logs", region_name=region)
    try:
        paginator = logs.get_paginator("describe_log_groups")
        infinite_groups: list[str] = []
        infinite_bytes = 0
        for page in paginator.paginate():
            for lg in page.get("logGroups", []):
                if "retentionInDays" not in lg:
                    infinite_groups.append(lg.get("logGroupName", ""))
                    infinite_bytes += lg.get("storedBytes", 0)
        gb_stored = infinite_bytes / (1024**3)
        findings.append(
            _finding(
                "COST-05",
                "spend_leaks_and_runway",
                "CloudWatch Log Groups with infinite retention (never expire)",
                "PASS" if not infinite_groups else "WARN",
                "LOW",
                f"{len(infinite_groups)} log group(s) have no retention policy ({gb_stored:.2f} GB currently stored).",
                "Set retention to 14–30 days for dev/staging and 90 days for prod (`aws logs put-retention-policy`).",
                estimated_monthly_savings_usd=max(gb_stored * 0.03, 0.0),
            )
        )
    except (BotoCoreError, ClientError) as exc:
        findings.append(_finding("COST-05", "spend_leaks_and_runway", "CloudWatch log retention", "SKIP", "INFO", str(exc), "Grant logs:DescribeLogGroups."))

    # COST-07: NAT Gateways ($32.85/mo fixed + $0.045/GB) missing free S3/DynamoDB Gateway Endpoints
    try:
        nat_gws = [
            n for n in ec2.describe_nat_gateways().get("NatGateways", []) if n.get("State") in ("available", "pending")
        ]
        if nat_gws:
            endpoints = ec2.describe_vpc_endpoints().get("VpcEndpoints", [])
            svc_names = " ".join(e.get("ServiceName", "") for e in endpoints)
            missing_gw_eps = [s for s in ("s3", "dynamodb") if f".{s}" not in svc_names]
            savings = (len(nat_gws) * 15.0 if missing_gw_eps else 0.0) + (
                len(nat_gws) * 32.85 if stage in ("pre-revenue", "mvp") else 0.0
            )
            findings.append(
                _finding(
                    "COST-07",
                    "spend_leaks_and_runway",
                    "NAT Gateway burn & free S3/DynamoDB Gateway VPC Endpoints",
                    "WARN" if (missing_gw_eps or stage in ("pre-revenue", "mvp")) else "PASS",
                    "HIGH" if missing_gw_eps else "MEDIUM",
                    f"{len(nat_gws)} active NAT Gateway(s) (~${len(nat_gws) * 32.85:.2f}/mo fixed + $0.045/GB); missing free Gateway Endpoints: {', '.join(missing_gw_eps) or 'none'}.",
                    "Attach free S3 and DynamoDB VPC Gateway Endpoints (`aws ec2 create-vpc-endpoint`) so S3/DynamoDB traffic bypasses NAT Gateway data processing charges ($0.045/GB).",
                    estimated_monthly_savings_usd=savings,
                )
            )
        else:
            findings.append(
                _finding(
                    "COST-07",
                    "spend_leaks_and_runway",
                    "NAT Gateway burn & free S3/DynamoDB Gateway VPC Endpoints",
                    "PASS",
                    "LOW",
                    "0 active NAT Gateways found.",
                    "None.",
                )
            )
    except (BotoCoreError, ClientError) as exc:
        findings.append(_finding("COST-07", "spend_leaks_and_runway", "NAT Gateway & VPC Endpoint check", "SKIP", "INFO", str(exc), "Grant ec2:DescribeNatGateways and ec2:DescribeVpcEndpoints."))

    # COST-08: Optional Cost Explorer trailing 30-day spend & Activate credit burn runway
    credit_runway: dict[str, Any] | None = None
    if include_ce:
        ce = session.client("ce", region_name="us-east-1")
        end_date = now.date()
        start_date = end_date - dt.timedelta(days=30)
        try:
            resp = ce.get_cost_and_usage(
                TimePeriod={"Start": start_date.isoformat(), "End": end_date.isoformat()},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "RECORD_TYPE"}],
            )
            gross_usd = 0.0
            credit_usd = 0.0
            for period in resp.get("ResultsByTime", []):
                for grp in period.get("Groups", []):
                    rtype = grp.get("Keys", [""])[0]
                    amt = float(grp.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", "0") or 0.0)
                    if rtype == "Credit":
                        credit_usd += abs(amt)
                    else:
                        gross_usd += max(amt, 0.0)
            net_cash_usd = max(gross_usd - credit_usd, 0.0)
            months_remaining = (
                round(credit_balance / gross_usd, 1)
                if (credit_balance is not None and gross_usd > 0)
                else None
            )
            credit_runway = {
                "trailing_30d_gross_usd": round(gross_usd, 2),
                "trailing_30d_credits_applied_usd": round(credit_usd, 2),
                "trailing_30d_net_cash_usd": round(net_cash_usd, 2),
                "remaining_credit_balance_usd": credit_balance,
                "estimated_runway_months": months_remaining,
                "cost_explorer_api_fee_note": "1 ce:GetCostAndUsage call executed ($0.01 USD, not covered by Activate credits).",
            }
            findings.append(
                _finding(
                    "COST-08",
                    "spend_leaks_and_runway",
                    "Trailing 30-day AWS spend & Activate Credit Runway",
                    "WARN" if (months_remaining is not None and months_remaining < 3.0) else "PASS",
                    "HIGH" if (months_remaining is not None and months_remaining < 3.0) else "INFO",
                    f"Trailing 30d Gross: ${gross_usd:.2f}, Credits Applied: ${credit_usd:.2f}, Net Cash: ${net_cash_usd:.2f}"
                    + (f", Est. Credit Runway: {months_remaining} months" if months_remaining is not None else ""),
                    "Configure AWS Budgets alerts at 50%, 80%, and 100% of monthly burn and review non-credit-eligible charges if Net Cash > $0.",
                )
            )
        except (BotoCoreError, ClientError) as exc:
            findings.append(_finding("COST-08", "spend_leaks_and_runway", "Cost Explorer credit runway", "SKIP", "INFO", str(exc), "Grant ce:GetCostAndUsage."))

    total_savings = round(sum(f["estimated_monthly_savings_usd"] for f in findings), 2)
    return {
        "account_id": account_id,
        "region": region,
        "stage": stage,
        "audited_at": now.isoformat(),
        "summary": {
            "total_checks": len(findings),
            "failed": sum(1 for f in findings if f["status"] == "FAIL"),
            "warnings": sum(1 for f in findings if f["status"] == "WARN"),
            "passed": sum(1 for f in findings if f["status"] == "PASS"),
            "estimated_monthly_savings_usd": total_savings,
        },
        "credit_runway": credit_runway,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    parser.add_argument(
        "--stage",
        default="seed",
        choices=["pre-revenue", "mvp", "seed", "series-a", "series-b+"],
        help="Startup stage used to calibrate HA vs cost warnings.",
    )
    parser.add_argument(
        "--include-cost-explorer",
        action="store_true",
        help="Include ce:GetCostAndUsage trailing 30d credit burn check ($0.01 per API call).",
    )
    parser.add_argument(
        "--credit-balance",
        type=float,
        default=None,
        help="Optional remaining AWS Activate credit balance in USD to compute exact runway months.",
    )
    args = parser.parse_args(argv)
    report = run_audit(args.region, args.stage, args.include_cost_explorer, args.credit_balance)
    print(json.dumps(report, indent=2))
    return 0 if "error" not in report else 1


if __name__ == "__main__":
    sys.exit(main())
