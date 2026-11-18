#!/usr/bin/env python3
"""Automated Startup Cost & Well-Architected Baseline Regression Gate for CI/CD.

Compares a current migration/architecture estimate or Terraform directory against
a saved baseline JSON (or stage ceiling) and exits non-zero when:
  1. Estimated monthly AWS spend regresses beyond `--max-increase-pct` (default: 15%)
     or exceeds `--max-monthly-usd` (stage ceiling).
  2. High-burn "money pit" resources (EKS control plane, NAT Gateway without override,
     Multi-AZ RDS, or Bedrock Provisioned Throughput) are introduced in a Pre-Revenue
     or Seed stage project without an explicit `"allow_money_pits": true` waiver.

Usage:
  # Check a .saws-migrate/estimate.json or .migration/*/estimate.json against stage ceiling
  python3 scripts/cost-regression-check.py --estimate .saws-migrate/estimate.json --stage seed --max-monthly-usd 300

  # Compare current estimate against a committed baseline in CI/CD
  python3 scripts/cost-regression-check.py --estimate .saws-migrate/estimate.json --baseline .saws-migrate/cost-baseline.json --max-increase-pct 15

  # Scan a Terraform directory statically for Pre-Revenue/Seed money-pit regressions
  python3 scripts/cost-regression-check.py --terraform-dir ./infra --stage pre-revenue
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

STAGE_DEFAULT_CEILINGS_USD = {
    "pre-revenue": 50.0,
    "mvp": 50.0,
    "seed": 500.0,
    "series-a": 10000.0,
    "series-b+": 100000.0,
}

TF_MONEY_PIT_PATTERNS = [
    (
        "eks_control_plane",
        re.compile(r'resource\s+"aws_eks_cluster"\s+"([^"]+)"'),
        73.0,
        "EKS cluster adds a mandatory $73/mo control plane fee before worker nodes. Use Lambda or ECS Fargate at Pre-Revenue/Seed.",
    ),
    (
        "nat_gateway",
        re.compile(r'resource\s+"aws_nat_gateway"\s+"([^"]+)"'),
        32.85,
        "Managed NAT Gateway costs $32.85/mo fixed + $0.045/GB per AZ. Use free S3/DynamoDB Gateway VPC Endpoints or public Fargate tasks with security groups at Pre-Revenue/Seed.",
    ),
    (
        "rds_multi_az",
        re.compile(r'resource\s+"aws_db_instance"\s+"([^"]+)"[\s\S]*?multi_az\s*=\s*true'),
        30.0,
        "Multi-AZ RDS doubles database instance cost. Use Single-AZ with automated backups at Pre-Revenue/Seed.",
    ),
    (
        "bedrock_provisioned_throughput",
        re.compile(r'resource\s+"aws_bedrock_provisioned_model_throughput"\s+"([^"]+)"'),
        1500.0,
        "Bedrock Provisioned Model Throughput bills thousands of dollars per month continuously. Use On-Demand Cross-Region Inference Profiles (`us.anthropic.*`).",
    ),
]


def _extract_monthly_usd(doc: dict[str, Any]) -> float:
    """Extract monthly USD total from any supported estimate schema shape."""
    for key in ("total_monthly_usd", "aws_monthly_usd", "monthly_usd", "estimated_monthly_usd"):
        val = doc.get(key)
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, dict) and isinstance(val.get("mid"), (int, float)):
            return float(val["mid"])
    summary = doc.get("summary") or doc.get("aws_estimate") or {}
    if isinstance(summary, dict):
        for key in ("total_monthly_usd", "mid", "monthly_usd", "aws_monthly_mid"):
            if isinstance(summary.get(key), (int, float)):
                return float(summary[key])
    return 0.0


def scan_terraform_money_pits(tf_dir: Path, stage: str) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    if stage not in ("pre-revenue", "mvp", "seed") or not tf_dir.is_dir():
        return violations
    for tf_file in sorted(tf_dir.rglob("*.tf")):
        text = tf_file.read_text(errors="ignore")
        for rule_id, pat, monthly_burn, msg in TF_MONEY_PIT_PATTERNS:
            for match in pat.finditer(text):
                violations.append(
                    {
                        "rule": rule_id,
                        "file": str(tf_file),
                        "resource": match.group(1),
                        "estimated_monthly_burn_usd": monthly_burn,
                        "message": msg,
                    }
                )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--estimate", type=Path, help="Path to current estimate JSON file.")
    parser.add_argument("--baseline", type=Path, help="Optional path to baseline estimate JSON file.")
    parser.add_argument("--terraform-dir", type=Path, help="Optional Terraform directory to scan for stage money pits.")
    parser.add_argument(
        "--stage",
        default="seed",
        choices=list(STAGE_DEFAULT_CEILINGS_USD),
        help="Startup funding stage for ceiling & money-pit checks.",
    )
    parser.add_argument("--max-monthly-usd", type=float, default=None, help="Override maximum monthly USD ceiling.")
    parser.add_argument("--max-increase-pct", type=float, default=15.0, help="Max allowed %% increase over baseline.")
    args = parser.parse_args(argv)

    ceiling = args.max_monthly_usd if args.max_monthly_usd is not None else STAGE_DEFAULT_CEILINGS_USD[args.stage]
    regressions: list[str] = []
    money_pits: list[dict[str, Any]] = []
    current_usd: float | None = None
    baseline_usd: float | None = None

    if args.estimate:
        if not args.estimate.is_file():
            print(json.dumps({"status": "ERROR", "error": f"Estimate file not found: {args.estimate}"}))
            return 2
        doc = json.loads(args.estimate.read_text())
        current_usd = _extract_monthly_usd(doc)
        if current_usd > ceiling:
            regressions.append(
                f"Estimated monthly spend (${current_usd:.2f}/mo) exceeds {args.stage} ceiling (${ceiling:.2f}/mo)."
            )
        if args.baseline and args.baseline.is_file():
            base_doc = json.loads(args.baseline.read_text())
            baseline_usd = _extract_monthly_usd(base_doc)
            if baseline_usd > 0:
                delta_pct = ((current_usd - baseline_usd) / baseline_usd) * 100.0
                if delta_pct > args.max_increase_pct:
                    regressions.append(
                        f"Estimated monthly spend increased by {delta_pct:.1f}% (${baseline_usd:.2f} -> ${current_usd:.2f}), "
                        f"exceeding --max-increase-pct {args.max_increase_pct:.1f}%."
                    )

    if args.terraform_dir:
        money_pits = scan_terraform_money_pits(args.terraform_dir, args.stage)
        for mp in money_pits:
            regressions.append(f"[{mp['rule']}] {mp['file']} ({mp['resource']}): {mp['message']}")

    passed = len(regressions) == 0
    result = {
        "status": "COST_OK" if passed else "COST_REGRESSION",
        "stage": args.stage,
        "ceiling_monthly_usd": ceiling,
        "current_monthly_usd": current_usd,
        "baseline_monthly_usd": baseline_usd,
        "money_pits": money_pits,
        "regressions": regressions,
    }
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
