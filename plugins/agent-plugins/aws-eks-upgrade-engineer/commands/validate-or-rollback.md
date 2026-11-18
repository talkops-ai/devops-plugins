---
description: Post-upgrade smoke verification, stuck-upgrade triage, or 7-day ROLLBACK_READINESS eligibility evaluation
argument-hint: "<cluster-name> [--region <region>] [--mode post-upgrade|triage|rollback]"
---

Invoke **eks-post-upgrade-validation-and-rollback** in strictly read-only mode to run post-upgrade control-plane/node/add-on/SLO smoke verification, diagnose stalled `DescribeUpdate` or node-group errors (`PodEvictionFailure`, `InsufficientInstanceCapacity`, `ConfigurationConflict`), or evaluate 7-day `ROLLBACK_READINESS` insights and reverse-order rollback procedures.

Cluster and mode: $ARGUMENTS
