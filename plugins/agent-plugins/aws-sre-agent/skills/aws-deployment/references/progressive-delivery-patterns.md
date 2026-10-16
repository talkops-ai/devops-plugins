# Progressive Delivery Patterns Across AWS Services

## 1. CloudFront Continuous Deployment (Edge Blue/Green & Canary)

Use CloudFront Continuous Deployment to test CDN and frontend/origin changes on live production traffic without DNS changes:

1. **Create Staging Distribution:** Clone the production CloudFront distribution with `Staging: true`.
2. **Create Continuous Deployment Policy (`AWS::CloudFront::ContinuousDeploymentPolicy`):**
   - **Header-Based Dark Launch (`SingleHeaderPolicyConfig`):** Route requests containing `aws-cf-cd-staging: true` to the staging distribution for synthetic E2E testing.
   - **Weight-Based Canary (`SingleWeightPolicyConfig`):** Route `Weight: 0.05` (5% of production traffic) with `SessionStickinessConfig` (`IdleTTL: 300`, `MaximumTTL: 3600`) so users stay pinned to one version.
3. **Promote Staging to Production:**
   ```bash
   aws cloudfront update-distribution-with-staging-config \
     --id <PROD_DIST_ID> \
     --staging-distribution-id <STAGING_DIST_ID> \
     --if-match <PROD_ETAG>,<STAGING_ETAG>
   ```

---

## 2. AWS AppConfig Feature Flag & Dynamic Configuration Rollouts

Decouple code deployment from feature activation using AWS AppConfig:

### Core Architecture
- `AWS::AppConfig::Application` -> `AWS::AppConfig::Environment` -> `AWS::AppConfig::ConfigurationProfile` (`Type: AWS.AppConfig.FeatureFlags` or `AWS.Freeform`).
- **Pre-Deployment Validation:** Attach a JSON Schema validator or a Lambda validator (`AWS::AppConfig::ConfigurationProfile.Validators`) to reject malformed configuration before rollout starts.
- **Deployment Strategy (`AWS::AppConfig::DeploymentStrategy`):**
  - Production Canary: `GrowthFactor: 10`, `DeploymentDurationInMinutes: 20`, `GrowthType: EXPONENTIAL`, `FinalBakeTimeInMinutes: 10`.
  - Fast Linear: `GrowthFactor: 25`, `DeploymentDurationInMinutes: 8`, `GrowthType: LINEAR`, `FinalBakeTimeInMinutes: 5`.
- **Automatic Rollback Monitors:** Bind CloudWatch Alarm ARNs + an IAM Role (`appconfig:StopDeployment`) to `AWS::AppConfig::Environment.Monitors`. Any alarm breach during deployment or `FinalBakeTimeInMinutes` triggers an immediate sub-second rollback to the previous configuration version.

---

## 3. EC2 Immutable Rollouts: Launch Templates + ASG Instance Refresh

For stateful or VM-based workloads on Amazon EC2 Auto Scaling Groups (ASGs), replace in-place patching with immutable **ASG Instance Refresh**:

1. **Bake Immutable AMI:** Use **EC2 Image Builder** (or Packer) to bake and test the application binary, OS hardening, and CloudWatch/SSM agents into a versioned AMI.
2. **Create New Launch Template Version:** Update `AWS::EC2::LaunchTemplate` with the new AMI ID and set `MetadataOptions: { HttpTokens: required, HttpPutResponseHopLimit: 1 }` (IMDSv2 enforced).
3. **Start Phased Instance Refresh with Checkpoints & Auto-Rollback:**
   ```bash
   aws autoscaling start-instance-refresh \
     --auto-scaling-group-name <asg-name> \
     --strategy Rolling \
     --preferences '{
       "MinHealthyPercentage": 90,
       "MaxHealthyPercentage": 120,
       "InstanceWarmup": 180,
       "CheckpointPercentages": [20, 50, 100],
       "CheckpointDelay": 600,
       "AutoRollback": true,
       "AlarmSpecification": {
         "Alarms": ["arn:aws:cloudwatch:<region>:<account>:alarm:<High5xxAlarm>"]
       }
     }'
   ```

---

## 4. Route 53 Weighted DNS Cross-Stack Blue/Green Cutover

When replacing an entire CloudFormation/CDK stack or migrating between compute platforms (e.g., Elastic Beanstalk to ECS Fargate):

1. Lower the existing Route 53 RecordSet TTL to `60` seconds at least 1 hour before cutover.
2. Convert the production record to **Weighted Routing** (`SetIdentifier: "blue-stack"`, `Weight: 100`, `HealthCheckId: <blue-hc>`).
3. Deploy the green stack and create its Weighted Alias/CNAME record (`SetIdentifier: "green-stack"`, `Weight: 0`, `HealthCheckId: <green-hc>`).
4. Shift weights progressively (`90/10` -> `50/50` -> `0/100`) while monitoring CloudWatch 5xx and latency alarms.
5. Keep `blue-stack` at `Weight: 0` during the bake window before decommission.

---

## 5. Zero-Downtime Database Schema Migration Choreography (Expand & Contract)

Never run breaking DDL migrations inside a container entrypoint or during a rolling/canary deployment where Blue (v1) and Green (v2) code run simultaneously against the same database:

1. **Phase 1 — Expand (Pre-Deploy):** Apply only additive, non-blocking schema changes (new nullable columns, new tables, `CREATE INDEX CONCURRENTLY`). Both v1 and v2 application code must work against this schema.
2. **Phase 2 — Dual-Write / App Rollout:** Deploy v2 application code via Canary or Blue/Green. v2 writes to both old and new columns (or reads with fallback).
3. **Phase 3 — Backfill:** Run an idempotent background job to backfill historical rows in batches.
4. **Phase 4 — Contract (Post-Bake):** Once v1 is 100% retired and rollback window has expired, deploy v3 removing old column references and execute cleanup DDL.
5. **Major Engine/Schema Upgrades:** Use **Amazon RDS / Aurora Managed Blue/Green Deployments** (`aws rds create-blue-green-deployment` -> test on green replica -> `aws rds switchover-blue-green-deployment`).
