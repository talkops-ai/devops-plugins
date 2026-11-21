# AgentCore Payments (`agents-pay`) Wiring, Operator Walkthrough & Cross-Platform Enforcement

Detailed architecture diagram, browser handle code, operator setup steps, OpenClaw host checks, and cross-platform policy enforcement details referenced by `agents-pay`. Keep the admin path strictly in a separate operator TTY outside the LLM loop, never read `.env` or `agentcore/.env.local`, and never execute live AWS/AgentCore mutations without explicit operator approval.

---

## 1. Architecture: Admin Path vs. Runtime Path

Payments split into an **admin path** (a human at a TTY) and a **runtime path** (the agent). They share non-secret resource identifiers and nothing else:

```
ADMIN PATH — human only, holds credentials (ControlPlaneRole / ManagementRole)
  agentcore add payment-manager / payment-connector   (provider secrets via interactive wizard)
  agents_pay_admin.py init-config                    -> ~/.agents-pay/config.json (0600)
  agents_pay_admin.py new-session                    -> budget-bounded session, typed 'approve' at TTY
        |
        |  passes ONLY: PAYMENT_MANAGER_ARN, PAYMENT_INSTRUMENT_ID,
        |               PAYMENT_SESSION_ID, PAYMENT_USER_ID
        v
RUNTIME PATH — spend only; never create (ProcessPaymentRole)
  x402_fetch(url)                        payment_session_status()   [read-only]
        |-- load policy, vet destination      (refuse before any network I/O)
        |-- GET, no redirects, pinned IP, bounded body
        |-- parse 402 challenge strictly
        |-- authorize_payment()               <-- THE decision, in code
        |-- settle, attach proof, discard it  (proof never returned)
        `-- return metadata + body hash; paid body withheld

  prepare_browser_payment(url)           -> opaque single-use handle (90s TTL, origin+path bound), no proof
        `-- attach_browser_payment(...)   -> trusted glue only, at navigation (never exposed to model)
```

### Browser / Header-Only Handle Flow

When a paid resource must render in a real browser, keep the signed proof out of model context by using the two-step handle pattern:

```python
# 1. Model-facing tool: settles payment, returns opaque handle + redacted receipt (never the proof)
result = json.loads(prepare_browser_payment("https://merchant.example/paid"))
# {"paid": true, "handle": "x402h_...", "receipt": {...}}

# 2. Trusted host glue (NOT model-callable) redeems single-use handle (90s TTL, origin+path bound)
header = attach_browser_payment(result["handle"], "https://merchant.example/paid")
browser.set_extra_http_headers(header)
browser.navigate("https://merchant.example/paid")
```

---

## 2. Full Operator Setup & Verification Walkthrough (Steps 0–6)

### Step 0: Local Prerequisites (Operator Terminal)

```bash
python3 --version                      # 3.9+
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
agentcore --version
python -c "from bedrock_agentcore.payments import PaymentManager"
```

### Step 1: Provision Payment Resources (Human Only — Outside LLM Loop)

Instruct the operator to run these commands in a separate terminal **with no CLI secret flags** so Coinbase CDP / Stripe Privy credentials never enter shell history, process lists, or chat context (`agentcore/.env.local` is gitignored and uploaded to AgentCore Identity on deploy — **the agent must never read `.env.local`**):

```bash
npm install -g @aws/agentcore
agentcore add payment-manager          # NO FLAGS — interactive wizard
agentcore add payment-connector        # NO FLAGS — interactive wizard
agentcore deploy                       # interactive deployment
```

### Step 2: Write Operator Policy (`~/.agents-pay/config.json`, Mode `0600`)

Until `~/.agents-pay/config.json` exists, every payment is refused (fail-closed):

```bash
python3 scripts/agents_pay_admin.py init-config \
  --max-per-payment-usd 0.05 \
  --network eip155:84532 \
  --recipient 0xMerchantWalletAddress
```

- Pass repeatable `--recipient` flags for explicit wallet allowlisting, **or** `--allow-any-recipient` (mutually exclusive; missing or setting both denies).
- Optionally pass repeatable `--origin https://<host>` to pin allowed HTTPS origins.
- USDC token contracts are resolved from a pinned table inside `agents_pay_admin.py` to prevent look-alike token spoofing.

### Step 3: Create a Per-User Payment Instrument (Human Only)

```bash
python3 scripts/agents_pay_admin.py create-instrument --email you@example.com
```

Reads `manager-arn` and `connector-id` from `agentcore/.cli/deployed-state.json` (or `--manager-arn` / `--connector-id`) and prints the wallet address, end-user delegation URL, and runtime `export` variables.

### Step 4: Approve a Budget-Bounded Session at a TTY (Human Only)

```bash
python3 scripts/agents_pay_admin.py new-session --budget 1.00 --expiry-minutes 60
```

Requires typing `approve` interactively at a real TTY (no `--yes` flag exists). Ensure the runtime IAM role (`ProcessPaymentRole`) **excludes** `bedrock-agentcore:CreatePaymentSession` and all `Create*` setup actions.

### Step 5: Wire Runtime Identifiers & Run Preflight (Human Local Terminal)

```bash
export PAYMENT_MANAGER_ARN=...   PAYMENT_INSTRUMENT_ID=...
export PAYMENT_SESSION_ID=...    PAYMENT_USER_ID=alice
export AWS_REGION=us-west-2
python3 scripts/agents_pay_admin.py preflight
```

Do not ask the user to paste identifiers or command output into chat. Once confirmed, the agent may run only read-only session status (`python3 scripts/x402_fetch_cli.py --status` or `payment_session_status()`).

### Step 6: Run Security Regression Suite & Invoke Runtime CLI

```bash
# 1. Verify policy gate controls locally
python3 scripts/test_x402_policy.py

# 2. Check read-only session usability
python3 scripts/x402_fetch_cli.py --status

# 3. Fetch x402-protected URL (exit 0 = paid/free, exit 2 = refused/unconfigured, exit 1 = error)
python3 scripts/x402_fetch_cli.py https://merchant.example/paid
```

**Transient On-Chain Settlement Replay:** If testnet settlement lags and the paid retry still returns `402`, `x402_fetch` replays the **exact same derived authorization** up to `X402_MAX_PAYMENT_ATTEMPTS` times (default `5`, clamped `1–10`). Reusing the identical idempotency token keeps `ProcessPayment` idempotent and prevents double charges.

### Rollback / Emergency Spend Freeze (Operator Commands)

- **Freeze runtime spending immediately:** Clear `PAYMENT_SESSION_ID` in the runtime environment, lower `max_per_payment_usd` to `0` (or remove `~/.agents-pay/config.json`), or revoke/expire the payment session / `ProcessPaymentRole` policy.
- **Remove provisioned payment resources:** Use `agentcore remove` and `agentcore deploy` from an operator terminal under `ControlPlaneRole`.

---

## 3. OpenClaw & Cross-Platform Enforcement Details

### OpenClaw Host Setup

```bash
openclaw plugins install clawhub:@aws/aws-agents-pay
openclaw plugins inspect aws-agents-pay
python3 scripts/agents_pay_admin.py preflight
```

- **Choose exactly one runtime path:** OpenClaw uses the TypeScript plugin (`get_paid_content`); Python harnesses (Claude Code, Codex, Cursor, Kiro) use `x402_fetch_cli.py` / `x402_fetch`. Never enable both simultaneously.
- **Safety audit before trusting any host plugin:** Confirm (1) **no tool accepts a wallet secret or provider key as a parameter**, and (2) **no model-visible tool can call `CreatePaymentSession`**.

### Why Policy Holds Across Harnesses

`SKILL.md` text and `allowed-tools` frontmatter are **not** load-bearing: `ProcessPayment` is reachable in the sanctioned Python path only after `x402_policy.load_config()` resolves `~/.agents-pay/config.json` from the OS account entry (`pwd.getpwuid`, immune to `HOME`, `AGENTS_PAY_CONFIG`, or `X402_POLICY_FILE` overrides) and passes every destination, scheme, network, asset, recipient, and amount check.

| Platform / Runtime Condition | Policy Gate Still Enforced? |
|---|---|
| `allowed-tools` frontmatter ignored by harness | **Yes** — enforced in `x402_policy.py`, not frontmatter |
| Prompt injection inside fetched `402` challenge or paid body | **Yes** — paid body is withheld (only content-type, byte count, SHA-256 returned) and authorization ignores model text |
| Altered CLI flags (`argv`) | **Yes** — `argv` selects URL/`GET\|HEAD`/`--purchase-id`, never spend limits or recipients |
| Unrestricted same-role shell access on host | **Platform boundary caveat** — isolate signer/config in a separate OS user/container/process, and enforce IAM separation (`ProcessPaymentRole` without `CreatePaymentSession`) as the hard cryptographic backstop |
