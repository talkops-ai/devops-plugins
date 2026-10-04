---
description: Assess an application's resilience with AWS Resilience Hub
argument-hint: "<application or CloudFormation stack>"
---

Assess `$ARGUMENTS` with AWS Resilience Hub.

1. Load `resilience-hub-getting-started` to define the app (stacks, tags, or resource groups) and a resiliency policy with RTO/RPO targets.
2. Run the assessment, then load `resilience-hub-failure-mode-assessment` to interpret failure modes and recommendations.
3. Return policy compliance, the top gaps, and recommended fixes (alarms, SOPs, FIS experiments).

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
