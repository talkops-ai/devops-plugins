# Amazon ECR Provisioning, Image Scanning & Lifecycle Policies

## 1. Provisioning a Hardened ECR Repository

Always configure ECR repositories with scan-on-push, encryption at rest, tag immutability, and a lifecycle policy to prevent unbounded storage growth.

### AWS CLI (Approval-Gated)

```bash
aws ecr create-repository \
  --region "${AWS_REGION}" \
  --repository-name "${REPO_NAME}" \
  --image-tag-mutability IMMUTABLE \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256
```

### Lifecycle Policy (Expire Untagged Images > 1 Day, Keep Last 15 Tagged Releases)

```bash
aws ecr put-lifecycle-policy \
  --region "${AWS_REGION}" \
  --repository-name "${REPO_NAME}" \
  --lifecycle-policy-text '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Expire untagged images after 1 day",
        "selection": {
          "tagStatus": "untagged",
          "countType": "sinceImagePushed",
          "countUnit": "days",
          "countNumber": 1
        },
        "action": { "type": "expire" }
      },
      {
        "rulePriority": 2,
        "description": "Keep last 15 release images",
        "selection": {
          "tagStatus": "any",
          "countType": "imageCountMoreThan",
          "countNumber": 15
        },
        "action": { "type": "expire" }
      }
    ]
  }'
```

## 2. Deterministic Build, Tag, Push & Scan Verification

Always tag images with an immutable version or Git commit SHA so ECS task definition rollbacks reference an exact digest:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)

aws ecr get-login-password --region "${AWS_REGION}" | \
  ${CONTAINER_CLI} login --username AWS --password-stdin "${ECR_URI}"

${CONTAINER_CLI} build --platform linux/arm64 -t "${ECR_URI}/${REPO_NAME}:${IMAGE_TAG}" .
${CONTAINER_CLI} push "${ECR_URI}/${REPO_NAME}:${IMAGE_TAG}"
```

### Verify ECR Vulnerability Scan Findings Post-Push

```bash
aws ecr describe-image-scan-findings \
  --region "${AWS_REGION}" \
  --repository-name "${REPO_NAME}" \
  --image-id imageTag="${IMAGE_TAG}" \
  --query '{Status:imageScanStatus.status,FindingCounts:imageScanFindings.findingSeverityCounts}'
```

If `CRITICAL` vulnerabilities are reported in OS packages, upgrade the base image in `Dockerfile` and rebuild before promoting to production.
