---
name: amplify-auth-cognito
description: >-
  Architects and implements Amazon Cognito authentication in AWS Amplify Gen 2
  (amplify/auth/resource.ts via defineAuth and referenceAuth). Covers email/phone login,
  passwordless OTP and WebAuthn passkeys, MFA (TOTP/SMS/Email), social OAuth/OIDC providers
  with secret(), enterprise SAML 2.0 via CDK CfnUserPoolIdentityProvider, RBAC user groups,
  Cognito lifecycle triggers, declarative allow.resource() admin API grants, and frontend
  Authenticator / SSR session flows. Use whenever adding, modifying, or debugging Amplify
  Gen 2 authentication and authorization.
---

# Amplify Auth & Amazon Cognito (`defineAuth` & `referenceAuth`)

Use this skill whenever configuring or troubleshooting authentication, user groups, external identity providers, Cognito triggers, or SSR session management in an AWS Amplify Gen 2 application (`amplify/auth/resource.ts`).

## Five Non-Negotiable Auth Guardrails

1. **Zero Plaintext OAuth Secrets:**
   - Every external OAuth/OIDC client ID, client secret, Apple private key, or SAML metadata secret in `defineAuth` **MUST** use `secret('<NAME>')` from `@aws-amplify/backend`. Never commit plaintext secrets.
2. **Declarative Trigger Registration & Admin Access Grants:**
   - Defining a trigger function with `defineFunction()` without adding it to `triggers: { ... }` inside `defineAuth()` is a **silent no-op**.
   - When a trigger or backend function calls Cognito `Admin*` APIs (such as `AdminAddUserToGroup` or `AdminUpdateUserAttributes`), **ALWAYS** grant access declaratively inside `amplify/auth/resource.ts` via:
     `access: (allow) => [allow.resource(myFunc).to(['addUserToGroup', 'manageUsers'])]`
     and co-locate the trigger function with `resourceGroupName: 'auth'` in `defineFunction` to prevent CloudFormation circular dependencies.
3. **Enterprise SAML 2.0 Uses CDK Escape Hatches:**
   - `defineAuth`'s `externalProviders` supports `google`, `facebook`, `loginWithAmazon`, `signInWithApple`, and `oidc`, but **does NOT have a `saml` property**. Always configure SAML 2.0 providers (Microsoft Entra ID, Okta, Ping) via `CfnUserPoolIdentityProvider` in `amplify/backend.ts` (or use `externalProviders.saml` only if verified in the installed `@aws-amplify/backend-auth` version via `aws-mcp`).
4. **Google Attribute Mapping & Scopes:**
   - Always include `scopes: ['email', 'profile', 'openid']` on external providers so user attributes populate.
   - In `attributeMapping`, Google's `name` claim maps to Cognito's `fullname` key using plain strings: `{ email: 'email', fullname: 'name' }` (never objects).
5. **Switch on Every `signInStep` in Custom Auth UI:**
   - When building custom sign-in flows with `signIn()` from `aws-amplify/auth` instead of `<Authenticator>`, always switch exhaustively on `result.nextStep.signInStep` (`DONE`, `CONFIRM_SIGN_UP`, `CONFIRM_SIGN_IN_WITH_TOTP_CODE`, `CONFIRM_SIGN_IN_WITH_SMS_CODE`, `CONFIRM_SIGN_IN_WITH_EMAIL_CODE`, `CONTINUE_SIGN_IN_WITH_TOTP_SETUP`, `CONTINUE_SIGN_IN_WITH_MFA_SELECTION`, `RESET_PASSWORD`, `CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED`, `CONFIRM_SIGN_IN_WITH_CUSTOM_CHALLENGE`).

---

## Workflow & Reference Routing

| Task | Reference to Load |
|---|---|
| Configure RBAC groups (`groups`), Cognito lifecycle triggers (`postConfirmation`, `preSignUp`, `preTokenGeneration`), declarative `access: (allow) => [allow.resource(fn).to([...])]` grants, or import existing Cognito resources (`referenceAuth`) | [`references/triggers-groups-and-access.md`](references/triggers-groups-and-access.md) |
| Configure passwordless login (Email/SMS OTP, WebAuthn Passkeys), MFA, Social OAuth (`google`, `signInWithApple`), OIDC, Enterprise SAML 2.0 CDK overrides, or Next.js SSR cookie auth | [`references/external-idp-saml-and-passkeys.md`](references/external-idp-saml-and-passkeys.md) |
