# External Identity Providers, Passkeys, MFA, and Next.js SSR Auth

## 1. Passwordless Login (Email OTP, SMS OTP, WebAuthn Passkeys) & MFA

```typescript
import { defineAuth, secret } from '@aws-amplify/backend';

export const auth = defineAuth({
  loginWith: {
    email: {
      otpLogin: true, // Enables passwordless Email OTP alongside or instead of passwords
    },
    phone: {
      otpLogin: true, // Enables SMS OTP
    },
    webAuthn: true,   // Enables FIDO2 / Passkeys (or { relyingPartyId: 'app.example.com' })
    externalProviders: {
      google: {
        clientId: secret('GOOGLE_CLIENT_ID'),
        clientSecret: secret('GOOGLE_CLIENT_SECRET'),
        scopes: ['email', 'profile', 'openid'],
        attributeMapping: {
          email: 'email',
          fullname: 'name', // Plain string values required
        },
      },
      oidc: [
        {
          name: 'OktaOIDC',
          clientId: secret('OKTA_CLIENT_ID'),
          clientSecret: secret('OKTA_CLIENT_SECRET'),
          issuerUrl: 'https://dev-123456.okta.com/oauth2/default',
          scopes: ['openid', 'email', 'profile'],
        },
      ],
      callbackUrls: [
        'http://localhost:3000/auth/callback',
        'https://app.example.com/auth/callback',
      ],
      logoutUrls: [
        'http://localhost:3000/',
        'https://app.example.com/',
      ],
    },
  },
  multifactor: {
    mode: 'OPTIONAL', // 'REQUIRED' | 'OPTIONAL' | 'OFF'
    totp: true,
    sms: true,
  },
  userAttributes: {
    phoneNumber: { required: true }, // Required when SMS MFA or phone login is enabled
  },
});
```

### Frontend WebAuthn Passkey Enrollment & Sign-In

```typescript
import { associateWebAuthnCredential, listWebAuthnCredentials, signIn } from 'aws-amplify/auth';

// 1. Register a passkey for the currently signed-in user
await associateWebAuthnCredential();

// 2. Sign in with passkey using USER_AUTH flow
const { nextStep } = await signIn({
  username: 'user@example.com',
  options: {
    authFlowType: 'USER_AUTH',
    preferredChallenge: 'WEB_AUTHN',
  },
});
```

---

## 2. Enterprise SAML 2.0 Federation (Microsoft Entra ID / Okta)

When configuring SAML 2.0 via CDK in `amplify/backend.ts`:

```typescript
import { defineBackend } from '@aws-amplify/backend';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { auth } from './auth/resource';

const backend = defineBackend({ auth });
const { userPool, userPoolClient } = backend.auth.resources;

const samlProvider = new cognito.UserPoolIdentityProviderSaml(
  backend.auth.stack,
  'EntraIdSamlProvider',
  {
    userPool,
    name: 'EntraID',
    metadata: cognito.UserPoolIdentityProviderSamlMetadata.url(
      'https://login.microsoftonline.com/<tenant-id>/federationmetadata/2007-06/federationmetadata.xml',
    ),
    attributeMapping: {
      email: cognito.ProviderAttribute.other(
        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
      ),
    },
  },
);

userPool.registerIdentityProvider(samlProvider);
```

---

## 3. Next.js App Router SSR Session & Cookie Auth (`@aws-amplify/adapter-nextjs`)

In Next.js App Router, Server Components, Server Actions, and Middleware have no access to browser `localStorage`:

1. Create a client boundary (`components/ConfigureAmplifyClientSide.tsx`) that calls `Amplify.configure(outputs, { ssr: true })` and mount it inside `app/layout.tsx`.
2. Create `utils/amplify-server-utils.ts` using `createServerRunner` and `generateServerClientUsingCookies`:

```typescript
// utils/amplify-server-utils.ts
import { createServerRunner } from '@aws-amplify/adapter-nextjs';
import { generateServerClientUsingCookies } from '@aws-amplify/adapter-nextjs/data';
import { cookies } from 'next/headers';
import outputs from '@/amplify_outputs.json';
import type { Schema } from '@/amplify/data/resource';

export const { runWithAmplifyServerContext } = createServerRunner({
  config: outputs,
});

export const cookiesClient = generateServerClientUsingCookies<Schema>({
  config: outputs,
  cookies,
});
```
