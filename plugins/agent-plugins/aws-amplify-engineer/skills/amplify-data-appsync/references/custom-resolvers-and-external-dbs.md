# Custom Queries/Mutations, AppSync JS Resolvers, External Databases, and SSR Clients

## 1. Custom Queries, Mutations, and Real-Time Subscriptions

Define strongly typed custom GraphQL operations without creating an API Gateway:

```typescript
const schema = a.schema({
  OrderReceipt: a.customType({
    orderId: a.id().required(),
    status: a.string().required(),
    processedAt: a.datetime().required(),
  }),

  // Custom Mutation backed by defineFunction
  checkoutOrder: a
    .mutation()
    .arguments({ cartId: a.id().required(), couponCode: a.string() })
    .returns(a.ref('OrderReceipt'))
    .handler(a.handler.function(checkoutHandler))
    .authorization((allow) => [allow.authenticated()]),

  // Custom Real-Time Subscription triggered by checkoutOrder
  onOrderProcessed: a
    .subscription()
    .for(a.ref('checkoutOrder'))
    .handler(
      a.handler.custom({
        entry: './resolvers/passThroughSubscription.js',
      }),
    )
    .authorization((allow) => [allow.authenticated()]),
});
```

Inside `amplify/functions/checkout/handler.ts`, use the generated `Schema['checkoutOrder']['functionHandler']` type for full argument and return-type safety:

```typescript
import type { Schema } from '../../data/resource';

export const handler: Schema['checkoutOrder']['functionHandler'] = async (event) => {
  const { cartId, couponCode } = event.arguments;
  return {
    orderId: `ord_${cartId}`,
    status: 'PAID',
    processedAt: new Date().toISOString(),
  };
};
```

---

## 2. Custom AppSync JS Resolvers & External Data Sources

Attach custom JavaScript resolvers (`a.handler.custom({ dataSource, entry })`) to connect AppSync directly to external DynamoDB tables, Amazon OpenSearch, Amazon EventBridge, or HTTP APIs:

```typescript
// amplify/backend.ts
import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';

const backend = defineBackend({ auth, data });

const externalTable = dynamodb.Table.fromTableName(
  backend.data.stack,
  'LegacyCustomersTable',
  'legacy-customers-prod',
);

backend.data.addDynamoDbDataSource('LegacyCustomersDS', externalTable);
```

---

## 3. Connecting to Existing RDS / Aurora PostgreSQL or MySQL Databases

1. Introspect the SQL schema and generate `amplify/data/schema.sql.ts`:
   ```bash
   npx ampx generate schema-from-database \
     --connection-uri-secret SQL_CONNECTION_STRING \
     --out amplify/data/schema.sql.ts
   ```
2. Combine the SQL schema with your DynamoDB schema in `amplify/data/resource.ts` using `a.combine([dynamoSchema, sqlSchema])`:
   ```typescript
   import { type ClientSchema, a, defineData } from '@aws-amplify/backend';
   import { schema as generatedSqlSchema } from './schema.sql';

   const sqlSchema = generatedSqlSchema.authorization((allow) => allow.authenticated());

   const dynamoSchema = a.schema({
     AuditLog: a.model({ action: a.string().required() }).authorization((allow) => [allow.owner()]),
   });

   const combinedSchema = a.combine([dynamoSchema, sqlSchema]);
   export type Schema = ClientSchema<typeof combinedSchema>;
   export const data = defineData({ schema: combinedSchema });
   ```

---

## 4. Frontend Client & Next.js SSR Patterns

### Browser / React Native Module-Scope Client

```typescript
import { generateClient } from 'aws-amplify/data';
import type { Schema } from '../amplify/data/resource';

export const client = generateClient<Schema>();

// Query with selectionSet to fetch related models in a single GraphQL request
const { data: orders, errors } = await client.models.Order.list({
  selectionSet: ['tenantId', 'orderId', 'status', 'items.sku', 'items.quantity'],
});
```
