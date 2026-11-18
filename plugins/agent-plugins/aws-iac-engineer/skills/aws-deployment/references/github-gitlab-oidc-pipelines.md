# GitHub Actions & GitLab CI Passwordless OIDC Deployment Pipelines

## 1. IAM OIDC Identity Provider & Least-Privilege Trust Policy

Never store `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in GitHub Secrets or GitLab CI variables. Provision an IAM OIDC Provider and lock the IAM Role trust policy to the exact repository and branch/environment:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:<org>/<repo>:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

---

## 2. GitHub Actions: ECR Build + ECS CodeDeploy Blue/Green Pipeline

```yaml
name: Deploy to AWS ECS Fargate (Blue/Green)
on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS Credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/${{ vars.DEPLOY_ROLE_NAME }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, Tag (Git SHA), and Push Image to ECR
        env:
          REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          REPOSITORY: ${{ vars.ECR_REPOSITORY }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build --platform linux/arm64 -t "$REGISTRY/$REPOSITORY:$IMAGE_TAG" .
          docker push "$REGISTRY/$REPOSITORY:$IMAGE_TAG"

      - name: Render ECS Task Definition & Trigger CodeDeploy Blue/Green
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: infra/taskdef.json
          service: ${{ vars.ECS_SERVICE }}
          cluster: ${{ vars.ECS_CLUSTER }}
          codedeploy-appspec: infra/appspec.yaml
          codedeploy-application: ${{ vars.CODEDEPLOY_APP }}
          codedeploy-deployment-group: ${{ vars.CODEDEPLOY_DG }}
          wait-for-service-stability: true
```

---

## 3. GitHub Actions: AWS SAM Serverless Canary Deployment

```yaml
      - name: Setup SAM CLI
        uses: aws-actions/setup-sam@v2

      - name: Validate, Build & Deploy SAM Stack
        run: |
          sam validate --lint
          sam build --cached --parallel
          sam deploy \
            --stack-name "${{ vars.SAM_STACK_NAME }}" \
            --resolve-s3 \
            --capabilities CAPABILITY_IAM \
            --no-confirm-changeset \
            --no-fail-on-empty-changeset
```

---

## 4. GitLab CI: OIDC Federation to AWS (`id_tokens`)

```yaml
deploy_production:
  image: amazon/aws-cli:latest
  id_tokens:
    GITLAB_OIDC_TOKEN:
      aud: https://gitlab.com
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  script:
    - >
      export $(printf "AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s AWS_SESSION_TOKEN=%s"
      $(aws sts assume-role-with-web-identity
      --role-arn "${AWS_ROLE_ARN}"
      --role-session-name "GitLabCI-${CI_PIPELINE_ID}"
      --web-identity-token "${GITLAB_OIDC_TOKEN}"
      --duration-seconds 3600
      --query "Credentials.[AccessKeyId,SecretAccessKey,SessionToken]"
      --output text))
    - aws sts get-caller-identity
    - npx cdk deploy --all --require-approval never --method=change-set
```
