# Production CI/CD (`amplify.yml`), Monorepo Pipelines, Security Headers, and Gen 1 Migration

## 1. Standard Production `amplify.yml` with Security Headers

```yaml
version: 1
backend:
  phases:
    build:
      commands:
        - npm ci --cache .npm --prefer-offline
        - npx ampx pipeline-deploy --branch $AWS_BRANCH --app-id $AWS_APP_ID
frontend:
  phases:
    build:
      commands:
        - npm run build
  artifacts:
    # Vite: dist | Next.js SSR: .next | Next.js Export: out | Angular: dist/<name>/browser
    baseDirectory: dist
    files:
      - '**/*'
  cache:
    paths:
      - .npm/**/*
      - node_modules/**/*
  customHeaders:
    - pattern: '**/*'
      headers:
        - key: 'Strict-Transport-Security'
          value: 'max-age=63072000; includeSubDomains; preload'
        - key: 'X-Frame-Options'
          value: 'SAMEORIGIN'
        - key: 'X-Content-Type-Options'
          value: 'nosniff'
        - key: 'Referrer-Policy'
          value: 'strict-origin-when-cross-origin'
```

---

## 2. Monorepo `amplify.yml` (Shared Backend + Multiple Frontends)

When `packages/backend` (or `packages/web`) owns the `amplify/` directory and `packages/admin` is a second frontend consuming the same backend:

```yaml
version: 1
applications:
  - appRoot: packages/web
    backend:
      phases:
        build:
          commands:
            - cd ../.. && npm ci --cache .npm --prefer-offline
            - npx ampx pipeline-deploy --branch $AWS_BRANCH --app-id $AWS_APP_ID
    frontend:
      phases:
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: dist
        files:
          - '**/*'
  - appRoot: packages/admin
    frontend:
      phases:
        preBuild:
          commands:
            - cd ../.. && npm ci --cache .npm --prefer-offline
            - npx ampx generate outputs --branch $AWS_BRANCH --app-id $BACKEND_APP_ID
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: dist
        files:
          - '**/*'
```

---

## 3. Gen 1 to Gen 2 Migration Checklist (Requires Explicit User Consent)

If the repository contains `amplify/.config/`, `amplify/team-provider-info.json`, or `src/aws-exports.js`:

1. **Stop & Request Consent:** Never run Gen 1 CLI commands (`amplify push`, `amplify add`) or overwrite Gen 1 files without explicit migration approval.
2. **Inventory Stateful Resources:**
   - **Auth:** Preserve existing Cognito User Pool and Identity Pool IDs using `referenceAuth()` in `amplify/auth/resource.ts` so users do not lose accounts or passwords.
   - **Data:** Map Gen 1 `@model` / `@auth` GraphQL directives in `schema.graphql` to Gen 2 `a.model()` and `.authorization()` rules in `amplify/data/resource.ts`, or attach existing DynamoDB tables as custom data sources (`backend.data.addDynamoDbDataSource(...)`).
   - **Storage:** Import existing S3 buckets via `aws-cdk-lib/aws-s3` `Bucket.fromBucketName(...)` in `amplify/backend.ts` and expose them via `backend.addOutput({ storage: ... })`.
3. **Client Library Upgrade (`aws-amplify` v5 → v6):**
   - Replace `Amplify.configure(awsExports)` with `Amplify.configure(outputs)` (`amplify_outputs.json`).
   - Replace `API.graphql(graphqlOperation(...))` with `const client = generateClient<Schema>()`.
   - Replace `Auth.signIn(...)` / `Auth.currentAuthenticatedUser()` with modular imports from `'aws-amplify/auth'` (`signIn`, `getCurrentUser`, `fetchAuthSession`).
   - Replace `Storage.put(...)` / `Storage.get(...)` with `uploadData` / `downloadData` / `getUrl` from `'aws-amplify/storage'`.
