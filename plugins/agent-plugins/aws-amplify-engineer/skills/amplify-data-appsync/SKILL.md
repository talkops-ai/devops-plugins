---
name: amplify-data-appsync
description: >-
  Models, secures, and integrates AWS AppSync GraphQL and Amazon DynamoDB data layers in
  Amplify Gen 2 (amplify/data/resource.ts via defineData and a.schema). Covers bidirectional
  relationships (hasMany, belongsTo, hasOne with a.id() foreign keys), composite identifiers
  (.identifier), Global Secondary Indexes (.secondaryIndexes), .disableOperations(), fine-grained
  authorization rules (owner, ownersDefinedIn, group, groupsDefinedIn, authenticated, guest,
  publicApiKey, custom, allow.resource), custom queries/mutations with Lambda/HTTP/OpenSearch/RDS
  PostgreSQL/MySQL, and typed frontend generateClient<Schema>() / SSR clients. Use whenever
  designing or debugging Amplify Gen 2 data schemas, AppSync resolvers, or DynamoDB access patterns.
---

# Amplify Data, AppSync GraphQL, and DynamoDB Modeling (`defineData`)

Use this skill whenever authoring or debugging `amplify/data/resource.ts`, designing DynamoDB partition/sort keys and GSIs (alongside the `dynamodb` MCP server), inspecting deployed AppSync APIs (via the `appsync` MCP server), or wiring frontend data clients.

## Six Non-Negotiable Data Modeling Guardrails

1. **Always Export `ClientSchema<typeof schema>`:**
   - Every `amplify/data/resource.ts` **MUST** include `export type Schema = ClientSchema<typeof schema>;` so frontend and Lambda clients receive end-to-end TypeScript inference via `generateClient<Schema>()`.
2. **Bidirectional Relationships Require `a.id()` Foreign Keys:**
   - Both sides of every `a.hasMany('Child', 'fkId')` / `a.belongsTo('Parent', 'fkId')` or `a.hasOne('Child', 'fkId')` relationship **MUST** be declared explicitly, and the foreign key field (`fkId`) on the child model **MUST** be `a.id()` (never `a.string()`).
3. **Never Chain `.default()` on `a.enum()`:**
   - Default values (`.default(...)`) are supported only on scalar fields (`a.string()`, `a.boolean()`, `a.integer()`, `a.float()`). Chaining `.default()` on `a.enum()` fails deployment.
4. **Match `defaultAuthorizationMode` to Model Rules & Subscriptions:**
   - In `defineData({ authorizationModes: { defaultAuthorizationMode: '...' } })`, the default mode (`'userPool'`, `'iam'`, `'apiKey'`, `'oidc'`, `'lambda'`) must match the primary rule on your models.
   - Real-time subscriptions (`observeQuery()`, `onCreate`, `onUpdate`, `onDelete`) require `'userPool'` or `'iam'`—API key subscriptions fail silently unless explicitly authorized.
   - Notice the syntax difference from Storage: Data authorization uses **method calls** (`allow.guest()`, `allow.authenticated()`, `allow.group('Admins')`), whereas Storage uses properties (`allow.guest`, `allow.authenticated`).
5. **Module-Scope `generateClient<Schema>()` Singleton:**
   - Always instantiate `const client = generateClient<Schema>()` **once at module scope** outside React/Vue/Angular component render functions, and always return `() => sub.unsubscribe()` inside `useEffect` cleanup callbacks.
6. **Inspect via `appsync` MCP, Mutate via `amplify/data/resource.ts`:**
   - Use the `appsync` and `dynamodb` MCP servers to inspect generated schemas, resolvers, data sources, and access patterns, but never mutate Amplify-managed AppSync APIs out-of-band—always apply changes in `amplify/data/resource.ts`.

---

## Workflow & Reference Routing

| Task | Reference to Load |
|---|---|
| Design `a.model()` schemas, composite keys (`.identifier`), GSIs (`.secondaryIndexes`), `.disableOperations()`, bidirectional relationships, or model/field-level authorization rules (`owner`, `ownersDefinedIn`, `groupsDefinedIn`, `resource`) | [`references/schema-relationships-and-authz.md`](references/schema-relationships-and-authz.md) |
| Build custom queries/mutations (`a.query()`, `a.mutation()`), custom JS AppSync pipeline resolvers (`a.handler.custom`), external DynamoDB/HTTP/OpenSearch/EventBridge data sources, RDS PostgreSQL/MySQL integration (`schema-from-database`), or frontend/SSR clients | [`references/custom-resolvers-and-external-dbs.md`](references/custom-resolvers-and-external-dbs.md) |
