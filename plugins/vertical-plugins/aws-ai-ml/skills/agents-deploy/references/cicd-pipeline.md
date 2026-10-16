# Immutable GitHub Actions CI/CD Pipeline & Two-Tier Evaluation Gate

## 1. Production CI/CD Pipeline Architecture

Never deploy production AgentCore changes from developer laptops or with long-lived IAM access keys. Enforce a 6-stage immutable pipeline:

1. **AWS OIDC Federation:** Authenticate GitHub Actions via `aws-actions/configure-aws-credentials@v4` using short-lived STS tokens.
2. **Schema & Unit Test Gate:** Validate `agentcore.json` (v0.4.0+ schema) and run unit tests with `OTEL_SDK_DISABLED=true pytest`.
3. **Container Build & Amazon Inspector Vulnerability Scan:** Build the ARM64 container image, push to Amazon ECR, and block deployment if Amazon Inspector detects any `CRITICAL` or unpatched `HIGH` CVEs.
4. **Infrastructure & Runtime Deployment:** Run `agentcore deploy --target staging -y` to create a new immutable `AgentRuntimeVersion`.
5. **Two-Tier Evaluation Gate:**
   - **Tier 1 (Deterministic Hard Gate — 100% Pass):** `Builtin.TrajectoryExactOrderMatch` and custom code-based Lambda evaluators.
   - **Tier 2 (LLM-as-a-Judge Suite Threshold Gate):** Aggregate scores across the golden dataset (`>= 50` test cases) for `Builtin.Helpfulness`, `Builtin.Faithfulness`, `Builtin.ToolSelectionAccuracy`, `Builtin.ToolParameterAccuracy`, `Builtin.GoalSuccessRate`, and `Builtin.Harmfulness`.
6. **Canary Traffic Promotion & Auto-Rollback:** Shift the `PROD` endpoint pointer (`10% -> 50% -> 100%`) and roll back immediately if `SystemErrorRate > 1%` or `ThrottleRate > 5%`.

---

## 2. Reference Workflow (`.github/workflows/deploy-agentcore.yml`)

```yaml
name: Deploy AgentCore Production Pipeline

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  id-token: write   # Required for AWS OIDC federation
  contents: read

env:
  AWS_REGION: us-east-1
  AGENT_NAME: My_Production_Agent
  ECR_REPOSITORY: agentcore/my-production-agent

jobs:
  validate-and-scan:
    name: 1. Validate Schema, Unit Test & Scan Image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS Credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_OIDC_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Set up Python & Node
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Dependencies & AgentCore CLI
        run: |
          npm install -g @aws/agentcore
          pip install -r requirements.txt pytest

      - name: Validate agentcore.json v0.4.0+ Schema & Run Unit Tests
        run: |
          agentcore validate
          OTEL_SDK_DISABLED=true pytest tests/unit

      - name: Login to Amazon ECR & Push Candidate Image
        id: ecr
        run: |
          ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
          ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"
          aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_URI}"
          docker buildx build --platform linux/arm64 -t "${ECR_URI}:${GITHUB_SHA}" --push .
          echo "image_digest=$(aws ecr describe-images --repository-name "${ECR_REPOSITORY}" --image-ids imageTag="${GITHUB_SHA}" --query 'imageDetails[0].imageDigest' --output text)" >> "$GITHUB_OUTPUT"

      - name: Gate on Amazon Inspector Container Vulnerability Scan
        run: |
          aws ecr wait image-scan-complete \
            --repository-name "${ECR_REPOSITORY}" \
            --image-id imageTag="${GITHUB_SHA}"
          CRITICAL_COUNT=$(aws inspector2 list-findings \
            --filter-criteria "{\"ecrImageHash\":[{\"comparison\":\"EQUALS\",\"value\":\"${{ steps.ecr.outputs.image_digest }}\"}],\"severity\":[{\"comparison\":\"EQUALS\",\"value\":\"CRITICAL\"}]}" \
            --query 'length(findings)' --output text)
          if [ "${CRITICAL_COUNT}" != "0" ]; then
            echo "ERROR: Amazon Inspector detected ${CRITICAL_COUNT} CRITICAL vulnerabilities. Blocking deploy."
            exit 1
          fi

  deploy-and-evaluate:
    name: 2. Deploy Staging, Run Two-Tier Evals & Promote Canary
    needs: validate-and-scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS Credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_OIDC_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Install AgentCore CLI
        run: npm install -g @aws/agentcore

      - name: Deploy Immutable Candidate Version to Staging
        run: agentcore deploy --target staging --yes

      - name: Smoke Test Candidate Endpoint
        run: |
          agentcore invoke --target staging --prompt "Health check: verify tool connectivity"

      - name: Tier 1 Hard Gate — Deterministic Trajectory & Code Evaluators (100% Required)
        run: |
          agentcore run evals \
            --runtime "${AGENT_NAME}" \
            --evaluator Builtin.TrajectoryExactOrderMatch \
            --evaluator Custom_SchemaCompliance_Lambda \
            --days 1 \
            --output-json tier1-eval.json
          python3 scripts/verify_eval_gate.py --tier 1 --input tier1-eval.json --min-score 1.0

      - name: Tier 2 Suite Gate — LLM-as-a-Judge Aggregate Thresholds
        run: |
          agentcore run batch-evaluation \
            --runtime "${AGENT_NAME}" \
            --dataset s3://${{ secrets.EVAL_BUCKET }}/golden-dataset-v1.jsonl \
            --output-s3 s3://${{ secrets.EVAL_BUCKET }}/results/${GITHUB_SHA}/ \
            --evaluators Builtin.Helpfulness,Builtin.Faithfulness,Builtin.ToolSelectionAccuracy,Builtin.ToolParameterAccuracy,Builtin.GoalSuccessRate,Builtin.Harmfulness

      - name: Promote Production Endpoint After Passing Gates
        run: agentcore deploy --target prod --yes
```

---

## 3. Ejecting Declarative Harnesses for CI/CD (`agentcore export harness`)

If a project began as a declarative **AgentCore Harness** in `agentcore.json` and now requires custom container builds, custom middleware, or hybrid LangGraph nodes in CI/CD:

```bash
agentcore export harness
```

Commit the generated `app/` directory and `EXPORT_NOTES.md` to version control so the CI/CD pipeline builds and scans the container image deterministically.
