# Schema Modeling, Composite Keys, GSIs, Relationships, and Authorization Rules

## 1. Composite Identifiers, GSIs, and Disabling Operations

```typescript
import { type ClientSchema, a, defineData } from '@aws-amplify/backend';

const schema = a.schema({
  OrderStatus: a.enum(['PENDING', 'PAID', 'SHIPPED', 'CANCELLED']),

  Order: a
    .model({
      tenantId: a.id().required(),
      orderId: a.id().required(),
      customerEmail: a.email().required(),
      status: a.ref('OrderStatus'), // Do NOT chain .default() on enum fields
      totalCents: a.integer().required(),
      createdAt: a.datetime().required(),
      items: a.hasMany('OrderItem', 'orderId'),
    })
    // Composite Primary Key (Partition Key: tenantId, Sort Key: orderId)
    .identifier(['tenantId', 'orderId'])
    // Global Secondary Index (GSI) with composite sort key and custom query method name
    .secondaryIndexes((index) => [
      index('tenantId')
        .sortKeys(['status', 'createdAt'])
        .queryField('listOrdersByTenantAndStatus')
        .name('byTenantStatus'),
    ])
    // Disable destructive delete or real-time subscriptions when required by compliance
    .disableOperations(['delete'])
    .authorization((allow) => [
      allow.owner(),
      allow.GroupsDefinedIn ? allow.groupsDefinedIn('allowedGroups') : allow.group('ADMINS'),
    ]),

  OrderItem: a
    .model({
      sku: a.string().required(),
      quantity: a.integer().default(1),
      orderId: a.id().required(), // MUST be a.id() to match Order identifier
      order: a.belongsTo('Order', 'orderId'),
    })
    .authorization((allow) => [allow.owner()]),
});

export type Schema = ClientSchema<typeof schema>;
export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: 'userPool',
  },
});
```

---

## 2. Complete Authorization Strategy Decision Matrix

| Strategy | Syntax in `.authorization((allow) => [...])` | Backing Auth Mode | Best For |
|---|---|---|---|
| **Single-User Owner** | `allow.owner()` or `allow.ownerDefinedIn('ownerId')` | `userPool` or `oidc` | Personal records where only the creator has full CRUD |
| **Multi-User Owners** | `allow.ownersDefinedIn('collaborators')` (on `a.string().array()`) | `userPool` or `oidc` | Shared documents, workspaces, or collaborative tickets |
| **Static Group RBAC** | `allow.group('ADMINS').to(['read', 'update', 'delete'])` | `userPool` or `oidc` | Role-based admin/moderator tiers |
| **Dynamic Group RBAC** | `allow.groupsDefinedIn('teamGroups')` (on `a.string().array()` or `a.string()`) | `userPool` or `oidc` | Multi-tenant SaaS where record access is scoped to tenant groups |
| **Signed-In Users** | `allow.authenticated().to(['read'])` | `userPool`, `oidc`, or `iam` | Authenticated catalog/directory browsing |
| **Unauthenticated Guest** | `allow.guest().to(['read'])` | `iam` (Identity Pool) | Public read access using temporary IAM credentials |
| **Public API Key** | `allow.publicApiKey().to(['read'])` | `apiKey` | Development prototypes or public marketing feeds |
| **Custom Lambda** | `allow.custom()` | `lambda` | External JWTs or bespoke authorization engines |
| **Backend Function** | `allow.resource(myLambdaFunc).to(['create', 'read', 'update'])` | `iam` (Execution Role) | Granting Amplify `defineFunction` Lambdas least-privilege Data access |

### Field-Level Authorization Override

When a field has `.authorization(...)`, **field-level rules completely override model-level rules for that field**:

```typescript
Employee: a.model({
  name: a.string().required(),
  department: a.string().required(),
  salaryCents: a.integer().authorization((allow) => [
    allow.owner().to(['read']),
    allow.group('HR_ADMINS'),
  ]),
}).authorization((allow) => [
  allow.authenticated().to(['read']),
  allow.group('HR_ADMINS'),
])
```
