# Cognito RBAC Groups, Lifecycle Triggers, Declarative Access, and `referenceAuth`

## 1. Static RBAC Groups & Declarative Trigger Access (`amplify/auth/resource.ts`)

When you need to automatically assign newly confirmed users to a Cognito group (or call any `cognito-idp` Admin API from a Lambda function), declare `groups`, `triggers`, and `access` inside `defineAuth`:

```typescript
// amplify/auth/post-confirmation/resource.ts
import { defineFunction } from '@aws-amplify/backend';

export const postConfirmation = defineFunction({
  name: 'post-confirmation',
  entry: './handler.ts',
  resourceGroupName: 'auth', // Prevents circular dependency with auth stack
});
```

```typescript
// amplify/auth/resource.ts
import { defineAuth } from '@aws-amplify/backend';
import { postConfirmation } from './post-confirmation/resource';

export const auth = defineAuth({
  loginWith: {
    email: true,
  },
  groups: ['ADMINS', 'EDITORS', 'VIEWERS'],
  triggers: {
    postConfirmation,
  },
  access: (allow) => [
    // Automatically grants cognito-idp:AdminAddUserToGroup on the User Pool
    // and injects AMPLIFY_AUTH_USERPOOL_ID into $amplify/env/post-confirmation
    allow.resource(postConfirmation).to(['addUserToGroup']),
  ],
});
```

### Trigger Handler Using Typed `$amplify/env/post-confirmation`

```typescript
// amplify/auth/post-confirmation/handler.ts
import type { PostConfirmationTriggerHandler } from 'aws-lambda';
import {
  CognitoIdentityProviderClient,
  AdminAddUserToGroupCommand,
} from '@aws-sdk/client-cognito-idp';
import { env } from '$amplify/env/post-confirmation';

const client = new CognitoIdentityProviderClient();

export const handler: PostConfirmationTriggerHandler = async (event) => {
  await client.send(
    new AdminAddUserToGroupCommand({
      GroupName: 'VIEWERS',
      Username: event.userName,
      UserPoolId: env.AMPLIFY_AUTH_USERPOOL_ID,
    }),
  );
  return event;
};
```

### Supported `allow.resource(fn).to([...])` Auth Actions

- `'addUserToGroup'` / `'removeUserFromGroup'` / `'listGroupsForUser'`
- `'manageUsers'` (grants read/write user management actions)
- `'getUser'` / `'listUsers'` / `'listUsersInGroup'`
- `'createUser'` / `'deleteUser'` / `'enableUser'` / `'disableUser'`
- `'resetUserPassword'` / `'setUserPassword'` / `'updateUserAttributes'`
- `'manageGroupMembership'` / `'manageGroups'` / `'managePasswordRecovery'`

---

## 2. Importing Existing / Gen 1 Cognito Resources (`referenceAuth`)

When migrating from Amplify Gen 1 or integrating with an existing brownfield Cognito User Pool and Identity Pool without recreating user accounts, use `referenceAuth()` in `amplify/auth/resource.ts`:

```typescript
import { referenceAuth } from '@aws-amplify/backend';

export const auth = referenceAuth({
  userPoolId: 'us-east-1_xxxxxxxxx',
  identityPoolId: 'us-east-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
  authRoleArn: 'arn:aws:iam::123456789012:role/existing-auth-role',
  unauthRoleArn: 'arn:aws:iam::123456789012:role/existing-unauth-role',
  userPoolClientId: '1234567890abcdefghijklmnop',
  groups: {
    ADMINS: 'arn:aws:iam::123456789012:role/existing-admins-group-role',
  },
});
```
