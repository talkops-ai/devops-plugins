# `.saws-migrate/aws-design-ai.json` & `.saws-migrate/discover-ai.json` Contract

To prevent tight coupling between cloud infrastructure migrations (`heroku-to-aws`, `gcp-to-aws`, `azure-to-aws`) and application-code AI/LLM migrations, all AI discovery and target design state is persisted in dedicated `.saws-migrate/*-ai.json` artifacts.

---

## 1. `.saws-migrate/discover-ai.json` Schema

Generated during the `discover` phase whenever application code uses an external LLM SDK, gateway (`OpenRouter`, `LiteLLM`), or agent framework.

```json
{
  "schema_version": "1.0",
  "discovered_at": "2026-08-21T12:00:00Z",
  "source_providers": ["openai", "openrouter"],
  "gateway": {
    "detected": true,
    "type": "openrouter",
    "base_url_locations": ["src/lib/llm.ts:14"],
    "env_vars": ["OPENROUTER_API_KEY"],
    "routed_models": [
      "anthropic/claude-3.5-sonnet",
      "openai/gpt-4o-mini",
      "google/gemini-2.5-flash"
    ]
  },
  "call_sites": [
    {
      "id": "cs-1",
      "file": "src/lib/llm.ts",
      "line": 28,
      "sdk": "openai",
      "source_model": "openai/gpt-4o-mini",
      "capabilities": ["chat", "streaming", "tool_use"],
      "estimated_monthly_input_tokens": 25000000,
      "estimated_monthly_output_tokens": 5000000
    }
  ],
  "agent_frameworks": []
}
```

---

## 2. `.saws-migrate/aws-design-ai.json` Schema

Generated during the `design` phase and consumed by:
- **Infrastructure generators (`heroku-to-aws`, `gcp-to-aws`, `azure-to-aws`)**: Reads `iam_policy_statements` and `required_env_vars` to inject least-privilege Bedrock IAM permissions and environment variables into the generated Terraform (`infra/`) or CDK stack.
- **Application-code rewriters (`ai-to-bedrock`, `llm-to-bedrock`)**: Reads `model_mappings`, `track`, and `behavior_delta_decisions` to rewrite SDK clients and prompt parameters.

```json
{
  "schema_version": "1.0",
  "target_region": "us-east-1",
  "track": "track_2_converse_rewrite",
  "model_mappings": [
    {
      "call_site_id": "cs-1",
      "source_provider": "openrouter",
      "source_model": "anthropic/claude-3.5-sonnet",
      "target_service": "bedrock-runtime",
      "target_api": "converse",
      "target_model_id": "us.anthropic.claude-sonnet-5",
      "same_model_family": true,
      "rationale": "Cross-region inference profile provides highest default TPM/RPM burst quota and 33% lower token cost than Sonnet 4.6."
    },
    {
      "call_site_id": "cs-2",
      "source_provider": "openrouter",
      "source_model": "openai/gpt-4o-mini",
      "target_service": "bedrock-runtime",
      "target_api": "converse",
      "target_model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
      "same_model_family": false,
      "alternative_mantle_model_id": "global.openai.gpt-5.6-luna",
      "rationale": "Claude Haiku 4.5 on Converse unifies all calls under a single SDK; global.openai.gpt-5.6-luna on bedrock-mantle is available if strict GPT family parity is required."
    }
  ],
  "iam_policy_statements": [
    {
      "Sid": "BedrockCrossRegionInferenceInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*:${aws_account_id}:inference-profile/us.anthropic.*",
        "arn:aws:bedrock:*::foundation-model/anthropic.*"
      ]
    }
  ],
  "required_env_vars": {
    "AWS_REGION": "us-east-1",
    "BEDROCK_DEFAULT_MODEL_ID": "us.anthropic.claude-sonnet-5"
  },
  "estimated_monthly_cost_usd": {
    "source_monthly_usd": 142.5,
    "bedrock_on_demand_monthly_usd": 88.0,
    "bedrock_with_prompt_caching_monthly_usd": 41.2,
    "activate_credit_eligible": true
  }
}
```

---

## 3. Handoff Rules Across Skills

1. **Infrastructure Skills (`heroku-to-aws`, `gcp-to-aws`, `azure-to-aws`)**:
   - If `.saws-migrate/aws-design-ai.json` is present during the `generate` phase, merge `iam_policy_statements` into the workload's ECS Task Role / Lambda Execution Role / App Runner Instance Role and inject `required_env_vars` into the container/function environment block.
   - Never hardcode model IDs inside Terraform compute templates; reference `var.bedrock_model_id` defaulted from `aws-design-ai.json`.
2. **Code Rewrite Skills (`ai-to-bedrock`, `llm-to-bedrock`)**:
   - Read `model_mappings` from `.saws-migrate/aws-design-ai.json` so the user is never asked to choose a target Bedrock model twice.
