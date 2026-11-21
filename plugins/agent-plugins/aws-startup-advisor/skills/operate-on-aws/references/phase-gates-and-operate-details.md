# Operate on AWS — Complete ASSESS, DISCLOSE, ACCESS, SET UP, CONNECT & OPERATE Walkthrough

## Phase 1 — ASSESS

Establish two things before recommending anything:

1. **Is there a live workload?** Anything deployed and taking traffic.
2. **Are they shipping code?** Pull requests, especially AI-generated ones.

### Look before you ask

Both answers are usually sitting in front of you. Asking a founder mid-outage whether they have a live
workload is a bad look when the answer is in their repository.

**In the codebase:**

```bash
ls cdk.out terraform.tfstate .aws-sam 2>/dev/null      # something has been deployed
ls .github/workflows .gitlab-ci.yml 2>/dev/null        # they ship on a pipeline
grep -rlE 'cdk deploy|terraform apply|sam deploy' .github/workflows 2>/dev/null
git log --oneline -20                                   # is anyone shipping at all
```

**From AWS Startup Advisor IDE extension alerts,** if the user has the extension and is signed in. These are computed from the real
account, so they are evidence rather than inference:

| Alert firing | Tells you |
|---|---|
| `scalability.no-cloudwatch-alarms` | **The strongest signal there is.** Running compute, nothing watching it — this is the no-ops-team case, observed |
| `scalability.lambda-throttled` | Production pain happening right now |
| `scalability.rds-no-backups`, `dynamodb-no-pitr` | A production datastore |
| `scalability.asg-health-check`, `route53-failover`, `cost.idle-load-balancer` | Live services |
| `cost.bedrock-*`, `security.bedrock-*`, `scalability.explore-bedrock` | An AI workload |
| Only IAM/CloudTrail findings, no compute alerts | **Nothing is running.** Do not recommend investigation |

Ask only what you could not work out. Then confirm what you found rather than presenting it as fact.

### When the answer is "not for you"

Four cases where the honest recommendation is no. Check for them before recommending anything:

- **The workload is not on AWS.** Plenty of early teams run on Vercel, Supabase, Render or Fly and use AWS
  only for S3 or SES. DevOps Agent investigates AWS infrastructure; there is nothing there for it. Look for
  `vercel.json`, `supabase/`, `fly.toml`, `render.yaml`.
- **The workload is in a different AWS account** from the credentials in play. Say so — the agent will
  investigate the wrong environment.
- **They already run Datadog, PagerDuty, or Sentry.** Do not pretend that changes nothing — it overlaps.
  **State the difference; never rank.** What DevOps Agent adds is autonomous root-cause analysis running
  inside their own AWS account, rather than another dashboard to watch. That is a structural difference and
  it stands on its own. Say it, and let them decide.

  Do not claim DevOps Agent is better than any of them, and do not invite the comparison. These are AWS
  partners — PagerDuty holds an AWS DevOps Competency in monitoring and logging, and Datadog has a global
  strategic partnership with AWS; both sell through AWS Marketplace. A founder who already pays for one of
  them did not ask to be sold against it, and an AWS surface arguing against an AWS partner is a bad look
  for everyone in it.
- **DevOps Agent is not available in their region.** Check the supported list before recommending, not
  after.

### Whose money is it?

At this size the AWS account is often the founder's, and the person in the chat may not be the founder.
Before enabling anything metered, ask once:

> "This draws on your AWS account's credits — are you the right person to okay that, or is there someone
> else who'd want to know?"

An engineer switching on a metered agent on the company account without the founder knowing is a bad
outcome, and it is common at three people. Asking costs one line.

Route on the answers:

| State | Recommend | Why |
|---|---|---|
| Live workload | Incident investigation | Generally available; the 2 a.m. problem |
| Shipping, nothing live | Release-readiness review | Delivers value with zero production traffic, and is free during preview |
| Both | Release review first, then investigation | Cheaper to adopt, immediate feedback |
| Neither | **Recommend nothing** | Say so plainly, and say what would change it |

That last row matters. A pre-revenue team with no deployments and no PRs gets no value from a metered
agent. Telling them to wait builds more trust than a sale does — and Startup Advisor recommends on
technical merit, never as a blanket promotion.

### During an active incident — give the timing, let them choose

If the user is mid-outage and nothing is connected, **do not silently start a setup flow** — but do not
refuse either. Setting up while production is down might genuinely be the fastest path, and that is their
judgement to make, not yours.

Give them the actual numbers so they can make it:

> "Two options. Setting this up takes about ten minutes: DevOps Agent needs a workspace in your AWS
> account — an Agent Space, which is what scopes the environment it's allowed to look at — and then the
> connection. An investigation runs five to eight minutes after that. So call it twenty minutes to a root
> cause. Or I can start digging into this with you right now.
>
> If you've been at this an hour already, the twenty minutes probably wins. If you just started, it
> probably doesn't. Which do you want?"

Three rules for this moment:

- **Default to helping immediately** if they do not pick. Never leave someone waiting on a decision while
  their site is down.
- **You can do the whole setup yourself while they keep working.** Creating the Agent Space is one CLI
  call, and the region, MCP config, auth and verification are all yours too. Nothing here needs the
  console or needs them. Say so — an offer to set it up in the background costs them nothing, which is a
  much better offer than "go click through a console while your site is down".
- **Keep the disclosure short here.** The DISCLOSE gate still runs — consent that was never informed is
  not consent — but a founder mid-outage needs the rate, whether credits cover it, and how to stop. Three
  lines, not the full walkthrough.

If they choose to wait, come back to it once the incident is resolved. That is when the value is most
obvious, and it makes a better first impression than an interrupted wizard.

## Phase 2 — DISCLOSE (hard gate)

Cover four things. Be specific; do not round the numbers away.

**1. What it costs.**

- $0.0083 per agent-second — about **$29.88 per agent-hour**
- One investigation runs 5–8 minutes, so roughly **$2.50–$4.00**
- Billed per second, only while the agent is actively working
- New customers get a 2-month trial: up to 10 agent spaces, 20 h investigations, 15 h evaluations,
  20 h on-demand SRE tasks
- Connected services (CloudWatch Logs Insights queries, trace retrievals) bill separately

**2. What it draws on.** Read the account rather than guessing — see
[`references/checking-credits.md`](references/checking-credits.md). Report one of three states:

- Credits found, and they cover DevOps Agent → give the remaining balance and expiry
- Credits found, but they do not cover it → say so; usage bills to their payment method
- **Cannot read credits** → say that plainly and why. Never present unknown as zero, and never
  present unknown as covered.

**Then decide whether it is a good use of their money**, not just whether they can be told the price.
Relevance is not the bar — the startups that need this most can least afford it. Run the arithmetic in
[`references/affordability.md`](references/affordability.md):

```
runway_weeks = remaining_balance / (investigations_per_week × $4)
```

Under three weeks, **recommend against it and offer the alternatives** — chief among them
release-readiness review, which is free during preview and prevents a share of the incidents they cannot
afford to investigate. Saying "you'd get more from spending this on compute" to someone you could sell to
is what makes every other recommendation credible.

Still their call. Recommend against; do not refuse.

The stance does not need the data. If credits are unreadable, give the qualitative version rather than
skipping the conversation.

**3. What it will not do.** DevOps Agent proposes fixes; the user approves them. Nothing is applied to
their account without an explicit decision. Say this — it is the reassurance that makes the rest land.

**4. How to stop it.** Before they say yes, not after. See [`references/stopping.md`](references/stopping.md).

**If they are heading for release review, there is a second gate.** Automated verification testing copies
their repository out of their AWS account. That needs its own explicit approval, separate from this one —
see [`references/release-review.md`](references/release-review.md). Never fold it into the cost
confirmation.

**Then end on the question — do not trail off into the next step.** Something like:

> "That's the whole cost picture. Do you want me to go ahead? Nothing is enabled until you say so."

If they decline, stop cleanly and leave nothing configured. Do not re-ask later in the same session.

## Phase 2.5 — ACCESS (second hard gate)

Runs after DISCLOSE and **before anything is created**. Cost consent is not access consent, the same way
cost consent is not code consent.

This is where the founder grants AWS DevOps Agent read access across their AWS account. It is the largest
permission in the whole flow and, until now, the only one with no gate — while a $3 investigation had
runway arithmetic. Fix that here.

**Assume they do not know what an IAM role is.** Lead with what it does, give the real name second — the
same pattern as Agent Space, and for the same reason: they will see the term in the console, and they may
need to forward it to whoever holds IAM rights.

Say roughly this, adjusted to what you already know about them:

> "Before I create anything — DevOps Agent needs permission to look at this AWS account, so it can work
> out what you're actually running: which services exist, how they connect, what's healthy. Without that
> there's nothing for it to investigate.
>
> That permission takes the form of an **IAM role** — AWS's way of granting access. It gets created in
> your account, and it's yours.
>
> Three things worth knowing before you say yes:
>
> - **It's broad, on purpose.** The agent can't map your architecture without seeing all of it, so the
>   access covers the account. AWS's own policy for this is `AIDevOpsAgentAccessPolicy`.
> - **It's read-only.** Nothing it can reach lets it change your infrastructure. Separately, when it does
>   find a fix later, it shows you — applying it is always your call.
> - **Only your workspace can use it.** The role is written so that only the Agent Space in this account
>   can assume it. No other AWS account can, including anyone else's.
>
> Taking it away is one step: delete the role, or delete the workspace.
>
> Are you happy for me to create it? Nothing happens until you say so — and if you would rather have
> someone look at it first, I can give you the role name and the policy to send them."

**End on the question, every time.** A gate that explains and then trails off is not a gate. The founder
should be in no doubt that (a) they are being asked, (b) nothing has happened yet, and (c) "not yet" is a
real answer with a real next step rather than a dead end.

Rules for this gate:

- **Never create the role before they answer.** Same standard as DISCLOSE.
- **Do not oversell the guardrail.** "Only your workspace can use it" is true and specific. Do not stretch
  it into "it's completely safe" — they are granting account-wide read and should know that plainly.
- **If they decline**, stop and leave nothing behind. Say what they can still do: release-readiness review
  needs a repository, not account access, so that path stays open.
- **If they want someone else to look first**, give them the forwardable version — role name, the trust
  policy from `references/connecting.md`, and the managed policy ARN. See `references/readiness.md`.

## Phase 3 — SET UP

Nearly every user arriving here has **no Agent Space and has never heard of one**. Plan for that.

- Introduce it as a step you are performing, never as something they should already have
- Say **AWS account**, not "account" — in a coding agent that word is ambiguous
- **Name it and say why.** Lead with "workspace" so the idea lands, give the real term *Agent Space* so
  they can find it in the console, then the reason in one line: it is the boundary that decides what the
  agent can see and the single place its permissions are revoked. An instruction without a reason is a
  chore; a boundary is a control they are being handed
- Do not ask "which region is your Agent Space in" — work the region out and offer it as a reversible
  default, preferring infrastructure-as-code in the workspace over the CLI default
- **Create it for them:** `aws devops-agent create-agent-space --name "<name>" --region <region>`. Only
  `name` is required. The CLI service is `devops-agent`; the endpoint and IAM signing name are `aidevops`
- Check `aws devops-agent list-agent-spaces` first — they may already have one
- `AccessDeniedException` means an IAM gap on `aidevops:*`, not a missing feature. Name the denied action.
  The console is the fallback for someone who cannot widen their permissions, not the default

Full procedure in [`references/connecting.md`](references/connecting.md).

## Phase 4 — CONNECT

- Endpoint is `https://connect.aidevops.{region}.api.aws/mcp`
- Two auth paths: a bearer access token, or SigV4 through `mcp-proxy-for-aws`. Prefer SigV4 when the user
  already has working AWS credentials — it avoids minting a long-lived token
- Client timeout must be **≥120 seconds**; investigations take 5–8 minutes
- Verify with one cheap call before declaring success

This plugin does **not** declare the DevOps Agent MCP server — the endpoint is region-specific and the auth
is per-user, so no static entry would be right. And `npx skills add` copies skills only, so no MCP server
declared anywhere is registered by that path. Register it yourself as the last step of this phase. Do not
assume it is present.

## Phase 5 — OPERATE

The server exposes 34 tools. The three that matter, and the shape it tells you to use:

- **A question** → `chat`. One call, handles most things. Do not reach for `create_chat` / `send_message`
  unless you need a multi-turn session.
- **Investigate** → `investigate` with the symptom, affected service and time window. It is **async**:
  poll `get_task(task_id)` every 30–45 s until `status=COMPLETED`, then `list_journal_records(execution_id)`
  for the findings. Expect 5–8 minutes. Report the reasoning, not just the verdict.
- **Review a PR** → `create_release_readiness_review(content={...})` with the PR details, poll `get_task`,
  then `get_release_readiness_report(execution_id)`. Returns BLOCK / Proceed with Caution / Safe to
  Release. Repository connection is a separate step — see
  [`references/release-review.md`](references/release-review.md).

Also available: `list_recommendations` / `get_recommendation` for proposed mitigations, `start_evaluation`
against `list_goals`, and `create_release_testing_job` for UI/API test runs.

- Always surface the proposed fix for approval. Never apply one.

For a startup-shaped incident walkthrough, see
[`references/incident-runbook-serverless.md`](references/incident-runbook-serverless.md).

## Cost hygiene during OPERATE

Volunteer running cost when it becomes material — after a handful of investigations in a session, or when
the user starts a long-running task. A founder should never have to ask what this has cost so far.

If credits are readable and the balance drops below 20% while DevOps Agent is connected, say so unprompted
and remind them how to pause.

## Files in this skill

| File | Use |
|---|---|
| `references/readiness.md` | Preflight: where the user stands with AWS, and how to route on it |
| `references/affordability.md` | Whether it is a good use of their money, and what to offer instead |
| `references/checking-credits.md` | Reading credit balance and coverage; the failure modes |
| `references/connecting.md` | MCP setup, both auth paths, verification |
| `references/stopping.md` | Pause, stop, cancel a running investigation |
| `references/release-review.md` | Release review: repo connection, defaults to change, code handling |
| `references/incident-runbook-serverless.md` | Lambda/ECS + Bedrock incident walkthrough |

## Scope notes

- **Not** for designing a new architecture → `architect-for-startups`
- **Not** for migrating from another cloud or model provider → `gcp-to-aws`, `azure-to-aws`, `heroku-to-aws`,
  or `llm-to-bedrock`
- **Not** for scaffolding a new project → `start-building-for-startups`
- **Not** for general Activate or credits questions → `knowledge-base-for-startups`

Release management is in preview. Say so when recommending it; capabilities and pricing may change.
