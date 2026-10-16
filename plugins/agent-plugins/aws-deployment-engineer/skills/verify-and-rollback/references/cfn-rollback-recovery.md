# CloudFormation, ECS, Lambda & Elastic Beanstalk Rollback Recovery Runbook

## 1. Diagnosing Failed CloudFormation / CDK / SAM Deployments

When a stack enters `ROLLBACK_IN_PROGRESS`, `ROLLBACK_COMPLETE`, `UPDATE_ROLLBACK_IN_PROGRESS`, or `UPDATE_ROLLBACK_FAILED`:

1. **Run Automated Stack + CloudTrail Correlation First:**
   Call `awsiac` tool `troubleshoot_cloudformation_deployment` with:
   - `stack_name`: `<stack-name>`
   - `region`: `<target-region>`
   - `include_cloudtrail`: `true`
2. **Inspect First Root-Cause Event (`ResourceStatus == CREATE_FAILED | UPDATE_FAILED`):**
   Ignore cascading `Resource creation cancelled` events; isolate the **chronologically earliest** `CREATE_FAILED` or `UPDATE_FAILED` event:
   ```bash
   aws cloudformation describe-stack-events \
     --region "${AWS_REGION}" \
     --stack-name "${STACK_NAME}" \
     --query 'reverse(StackEvents[?ResourceStatus==`CREATE_FAILED` || ResourceStatus==`UPDATE_FAILED`])[0:5].{Time:Timestamp,LogicalId:LogicalResourceId,Type:ResourceType,Reason:ResourceStatusReason}' \
     --output table
   ```

## 2. Recovery Playbooks by Stack State

| Stack State | Meaning | Safe Recovery Procedure (Requires User Confirmation) |
| --- | --- | --- |
| `ROLLBACK_COMPLETE` | Initial greenfield stack creation failed and rolled back all created resources; stack shell remains with 0 resources. | Delete the empty failed stack shell (`aws cloudformation delete-stack --stack-name <name>`) before re-running `cdk deploy` or `sam deploy`. |
| `UPDATE_ROLLBACK_COMPLETE` | Stack update failed, automatically reverted to the previous working template, and is stable. | Fix the IaC defect locally, validate with `awsiac`, and re-deploy. |
| `UPDATE_ROLLBACK_FAILED` | Stack update failed AND rollback could not complete (e.g., manual out-of-band edit or dependent ENI). | Inspect failing resource, fix out-of-band dependency, and run `aws cloudformation continue-update-rollback --stack-name <name>` (skipping only broken non-critical resources if required). |
| `DELETE_FAILED` | Stack teardown blocked by non-empty S3 bucket, ECR repository with images, or lingering Lambda VPC ENIs. | Identify the retaining resource in `ResourceStatusReason`. Never empty S3 buckets or ECR repos containing user data without explicit user authorization. |

## 3. Compute-Specific Fast Rollback Commands (Approval-Gated)

When a deployment succeeds at the CloudFormation layer but runtime telemetry (`cloudwatch`) reveals elevated `5xx` errors or application regressions:

### A. Amazon ECS Service (Revert to Previous Task Definition Revision)

```bash
# 1. List recent task definition revisions
aws ecs list-task-definitions --family-prefix "${TASK_FAMILY}" --sort DESC --max-items 5

# 2. After user confirmation, update service to previous known-good revision
aws ecs update-service \
  --region "${AWS_REGION}" \
  --cluster "${CLUSTER_NAME}" \
  --service "${SERVICE_NAME}" \
  --task-definition "${TASK_FAMILY}:${PREVIOUS_REVISION}" \
  --force-new-deployment
```

### B. AWS Lambda Alias (Instant Traffic Shift to Previous Version)

```bash
aws lambda update-alias \
  --region "${AWS_REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --name live \
  --function-version "${PREVIOUS_VERSION}" \
  --routing-config AdditionalVersionWeights={}
```

### C. AWS Elastic Beanstalk (Revert to Previous Application Version)

```bash
# 1. Identify previous application version label
aws elasticbeanstalk describe-application-versions \
  --region "${AWS_REGION}" \
  --application-name "${APP_NAME}" \
  --query 'ApplicationVersions[0:5].{Label:VersionLabel,Created:DateCreated,Status:Status}' \
  --output table

# 2. After user confirmation, roll back environment to previous version label
aws elasticbeanstalk update-environment \
  --region "${AWS_REGION}" \
  --environment-name "${ENV_NAME}" \
  --version-label "${PREVIOUS_VERSION_LABEL}"
```

### D. AWS CodeDeploy (Abort Active Blue/Green or Canary & Roll Back to Blue)

```bash
aws deploy stop-deployment \
  --region "${AWS_REGION}" \
  --deployment-id "${DEPLOYMENT_ID}" \
  --auto-rollback-enabled
```

### E. AWS AppConfig (Instant Feature-Flag / Configuration Rollback)

```bash
aws appconfig stop-deployment \
  --region "${AWS_REGION}" \
  --application-id "${APP_ID}" \
  --environment-id "${ENV_ID}" \
  --deployment-number "${DEPLOYMENT_NUMBER}"
```

### F. EC2 Auto Scaling Group Instance Refresh (Cancel & Revert)

```bash
aws autoscaling cancel-instance-refresh \
  --region "${AWS_REGION}" \
  --auto-scaling-group-name "${ASG_NAME}"

aws autoscaling rollback-instance-refresh \
  --region "${AWS_REGION}" \
  --auto-scaling-group-name "${ASG_NAME}"
```

### G. CloudFront Continuous Deployment (Disable Staging Traffic Policy)

Disable or detach the `ContinuousDeploymentPolicyId` on the primary CloudFront distribution so 100% of edge traffic returns immediately to the primary production origin.
