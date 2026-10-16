---
name: amplify-storage-s3
description: >-
  Architects and implements Amazon S3 file storage in AWS Amplify Gen 2
  (amplify/storage/resource.ts via defineStorage). Enforces the 4 strict Amplify Gen 2 S3 path
  compiler rules (wildcards, single-level sub-path nesting, {entity_id} identity token placement
  and prefix collision rules), property-based access syntax (allow.guest, allow.authenticated,
  allow.entity('identity'), allow.groups, allow.resource), multi-bucket configurations
  (isDefault: true), S3 event triggers (onUpload, onDelete), and frontend uploadData/getUrl/StorageBrowser
  integration. Use whenever adding or debugging Amplify Gen 2 S3 storage.
---

# Amplify Storage & Amazon S3 (`defineStorage`)

Use this skill whenever configuring `amplify/storage/resource.ts`, enforcing user-scoped S3 path permissions, wiring multiple buckets or S3 Lambda triggers, or integrating file uploads/downloads in web and mobile clients.

## Four Strict Amplify Gen 2 S3 Path Compiler Rules

Unlike Amplify Gen 1's fixed `public` / `protected` / `private` storage levels, Amplify Gen 2 compiles custom path patterns in `defineStorage({ access: (allow) => ({ ... }) })` into IAM inline policies on Cognito Identity Pool roles. The `@aws-amplify/backend-storage` path compiler enforces **four strict rules** at synthesis time:

1. **Trailing Wildcard & No Leading Slash:**
   - Every path string **MUST** end with `/*` (e.g., `'public/*'`, `'avatars/{entity_id}/*'`) and **MUST NOT** start with `/`.
2. **Single-Level Sub-Path Nesting Along a Shared Prefix:**
   - Only one level of sub-path nesting is allowed under another defined prefix. For example, `'media/*'` and `'media/albums/*'` are valid together, but adding a third nested level `'media/albums/photos/*'` under the same chain fails compilation.
3. **No Sibling Wildcard and `{entity_id}` Conflict:**
   - A generic wildcard path and an `{entity_id}` token **cannot coexist at the same hierarchy level**. Defining both `'media/*'` and `'media/{entity_id}/*'` fails compilation.
4. **No Parent Wildcard Prefix Above an `{entity_id}` Path:**
   - A wildcard path **cannot be a parent prefix** of another path that contains `{entity_id}`. Defining both `'media/*'` and `'media/users/{entity_id}/*'` fails compilation—separate them into distinct top-level prefixes (e.g., `'public-media/*'` and `'user-media/{entity_id}/*'`).

---

## Five Non-Negotiable Storage Guardrails

1. **Property Syntax (`allow.guest` / `allow.authenticated`) vs. Method Syntax:**
   - In `defineStorage`, `allow.guest` and `allow.authenticated` are **properties** (NO parentheses): `allow.guest.to(['read'])`, `allow.authenticated.to(['read', 'write', 'delete'])`.
   - `allow.entity('identity')`, `allow.groups(['Admins'])`, and `allow.resource(myFunc)` take arguments, and every rule **MUST** end with `.to(['read' | 'get' | 'list' | 'write' | 'delete'])`.
2. **`{entity_id}` Requires `allow.entity('identity')`:**
   - The `{entity_id}` token resolves to the caller's Cognito Identity Pool `identityId` (`${cognito-identity.amazonaws.com:sub}`). It **MUST** be paired with `allow.entity('identity').to([...])` and placed immediately before `/*` (`'private/{entity_id}/*'`).
3. **Multi-Bucket Requires Unique `name` and Exactly One `isDefault: true`:**
   - When multiple `defineStorage()` buckets are registered in `amplify/backend.ts`, each bucket must have a unique `name` and **exactly one** must set `isDefault: true`.
4. **Lambda Access Grants Inject `<STORAGE_NAME>_BUCKET_NAME`:**
   - Grant Lambda functions bucket access declaratively inside `defineStorage` via `allow.resource(myFunc).to(['read', 'write', 'delete'])`. Amplify automatically injects `<STORAGE_NAME>_BUCKET_NAME` into `$amplify/env/<func-name>`.
5. **Dual CSS Imports for `@aws-amplify/ui-react-storage`:**
   - When rendering `<StorageBrowser />`, `<FileUploader />`, or `<StorageImage />`, always import **both** `@aws-amplify/ui-react/styles.css` and `@aws-amplify/ui-react-storage/styles.css`.

---

## Reference Routing

Load [`references/path-compiler-and-multi-bucket.md`](references/path-compiler-and-multi-bucket.md) for complete `defineStorage` blueprints, multi-bucket configurations, Lambda S3 triggers (`onUpload`/`onDelete`), and Data-record-to-S3 file linking patterns.
