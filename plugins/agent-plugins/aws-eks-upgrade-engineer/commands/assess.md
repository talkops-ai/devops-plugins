---
description: Full read-only EKS upgrade readiness assessment (0-100% score + 60+-gate Best Practices report in Markdown, HTML, or CI/CD JSON)
argument-hint: "<cluster-name> [--region <region>] [--target <1.XX>] [--format md|html|json]"
---

Invoke **eks-upgrade-check** and **eks-upgrade-readiness** in strictly read-only mode to inspect the target EKS cluster, compute the 8-area 0–100% readiness score (applying hard-blocker caps where required), evaluate all `PF-*`, `INFRA-*`, `NODE-*`, `ADDON-*`, `WKLD-*`, `KARP-*`, `DRAIN-*`, and `ROLL-*` gates with Evidence Completeness (`EC%`), and generate the requested Markdown, HTML (`scripts/md_to_html.py`), or JSON readiness report.

Target cluster and options: $ARGUMENTS
