---
name: executing-synthetic-release-tests
description: >-
  Runs post-deployment User Acceptance Testing (UAT), smoke tests, CloudWatch Synthetics
  canaries, API Gateway test invocations, and live Golden Signal metric/alarm verification,
  triggering automated rollback if SLOs breach. Use when the user asks to "run release tests",
  "verify the deployment", "run synthetic smoke tests", "run UAT", or runs `/release-testing`.
---

# Post-Deployment Synthetic Release Testing & UAT Verification

## When to Use
Invoke this skill immediately after a deployment completes (or during a Blue/Green or Canary bake window) to verify that the newly deployed version passes functional smoke tests, CloudWatch Synthetics canaries, and error/latency SLO assertions.

## 4-Stage Release Verification Workflow

### Stage 1: Endpoint & Target Group Health Verification
Verify that the deployed compute targets and load balancers have reached a healthy steady state via `aws___run_script`:
1. **CloudFormation Stack Status**: Confirm stack status is `UPDATE_COMPLETE` or `CREATE_COMPLETE` and extract stack `Outputs` (API URLs, ALB DNS names, CloudFront domains).
2. **ALB Target Health**: Call `elbv2.describe_target_health` to confirm all registered targets report `TargetHealth.State == "healthy"` and `UnHealthyHostCount == 0`.
3. **ECS / Lambda Readiness**:
   - ECS: Confirm `runningCount == desiredCount` on the `PRIMARY` deployment and zero tasks are stuck in `PENDING` or crash-looping.
   - Lambda: Confirm `State == "Active"` and `LastUpdateStatus == "Successful"`.

### Stage 2: Synthetic Canary & API Smoke Execution
Execute automated smoke tests against the live or test-listener (`:8443`) endpoint:
1. **CloudWatch Synthetics Canaries**:
   - Discover existing canaries via `aws synthetics describe-canaries`.
   - Trigger an immediate canary run (`aws synthetics start-canary --name <canary-name>`) after user confirmation, and poll `aws synthetics get-canary-runs --name <canary-name>` until `Status.State` completes (`PASSED` or `FAILED`).
2. **API Gateway Control-Plane Test Invocations**:
   - For REST APIs, run `aws apigateway test-invoke-method --rest-api-id <id> --resource-id <res> --http-method GET` to validate status codes, response latency, and payload schemas without external network hops.
3. **Local Integration / UAT Suite**:
   - If the repository defines smoke or UAT tests (`pytest -m smoke`, `npm run test:e2e`, ` playwright test`), execute them against the staging/canary URL and capture pass/fail counts.

### Stage 3: Bake-Window Telemetry & SLO Assertion
During and immediately after test execution, query `aws-cloudwatch` (`get_active_alarms`, `get_metric_data`, `execute_log_insights_query`) over the last 10–15 minutes:
- **Zero New Alarms**: Verify no CloudWatch alarms transitioned to `ALARM`.
- **Golden Signals Check**:
  - `5XXError` / `HTTPCode_Target_5XX_Count` == `0`
  - Lambda `Errors` == `0` and `Throttles` == `0`
  - Latency `p99` within baseline threshold
- **Log Exception Check**: Run a CloudWatch Logs Insights query for newly introduced stack traces or `ERROR`/`FATAL` messages emitted by the new version.

### Stage 4: Release Sign-Off or Automated Rollback
- **PASS**: Present a UAT Verification Report with Canary run IDs, HTTP status/latency assertions, and CloudWatch Golden Signal metrics.
- **FAIL**: Immediately alert the user with the failing test/alarm evidence and provide the exact rollback command (`aws deploy stop-deployment --deployment-id <id> --auto-rollback-enabled` or `aws cloudformation rollback-stack`) gated by `aws-mutation-gate.py`.
