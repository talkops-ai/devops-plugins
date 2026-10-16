# S3 Path Authorization, Multi-Bucket Rules, Triggers, and Record-Linking

## 1. Production `defineStorage` Blueprint (`amplify/storage/resource.ts`)

```typescript
import { defineStorage } from '@aws-amplify/backend';
import { imageThumbnailFn } from '../functions/image-thumbnail/resource';

export const primaryStorage = defineStorage({
  name: 'appPrimaryAssets',
  isDefault: true, // Mandatory when multiple buckets exist
  triggers: {
    onUpload: imageThumbnailFn,
  },
  access: (allow) => ({
    // Publicly readable catalog images, writable only by Admins and thumbnail Lambda
    'catalog-images/*': [
      allow.guest.to(['read']),
      allow.authenticated.to(['read']),
      allow.groups(['ADMINS']).to(['read', 'write', 'delete']),
      allow.resource(imageThumbnailFn).to(['read', 'write']),
    ],
    // Protected user avatars: readable by any signed-in user, mutable only by owner
    'avatars/{entity_id}/*': [
      allow.authenticated.to(['read']),
      allow.entity('identity').to(['read', 'write', 'delete']),
    ],
    // Strictly private user documents: accessible only by the owning identity
    'vault/{entity_id}/*': [
      allow.entity('identity').to(['read', 'write', 'delete']),
    ],
  }),
});

export const complianceArchive = defineStorage({
  name: 'complianceArchiveBucket',
  access: (allow) => ({
    'reports/*': [
      allow.groups(['AUDITORS', 'ADMINS']).to(['read']),
      allow.resource(imageThumbnailFn).to(['write']),
    ],
  }),
});
```

---

## 2. Consuming the Auto-Generated Bucket Name in Lambda (`$amplify/env/*`)

When `imageThumbnailFn` is granted access in `defineStorage({ name: 'appPrimaryAssets', ... })`, Amplify converts the `name` to `SNAKE_UPPER_CASE` and appends `_BUCKET_NAME` (`APP_PRIMARY_ASSETS_BUCKET_NAME`) in `$amplify/env/image-thumbnail`:

```typescript
// amplify/functions/image-thumbnail/handler.ts
import type { S3Handler } from 'aws-lambda';
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import { env } from '$amplify/env/image-thumbnail';

const s3 = new S3Client();

export const handler: S3Handler = async (event) => {
  const bucketName = env.APP_PRIMARY_ASSETS_BUCKET_NAME;
  for (const record of event.Records) {
    const key = decodeURIComponent(record.s3.object.key.replace(/\+/g, ' '));
    const obj = await s3.send(new GetObjectCommand({ Bucket: bucketName, Key: key }));
    console.log(`Processed ${key} (${obj.ContentLength} bytes)`);
  }
};
```

> **Circular Dependency Reminder:** If `imageThumbnailFn` is both an S3 `onUpload` trigger and granted access to mutate `defineData` or `defineStorage`, set `resourceGroupName: 'storage'` in `defineFunction` inside `amplify/functions/image-thumbnail/resource.ts`.

---

## 3. Associating Uploaded S3 Files with AppSync Data Records (Frontend Pattern)

Never upload an orphan file without tying its S3 path to the owning database record:

1. **Create the AppSync Data record first** to obtain its unique `id` (or generate a UUID).
2. **Upload the file to S3** using `uploadData()` with a deterministic path (`avatars/${identityId}/${record.id}-${file.name}`).
3. **Update the Data record** with the returned `result.path`.
4. **Render the file** using `<StorageImage path={record.avatarPath} alt="..." />` or `await getUrl({ path: record.avatarPath })`.

```typescript
import { uploadData, getUrl } from 'aws-amplify/storage';
import { client } from './client';

export async function attachInvoicePdf(orderId: string, file: File) {
  const uploadTask = uploadData({
    path: ({ identityId }) => `vault/${identityId}/orders/${orderId}/${file.name}`,
    data: file,
    options: {
      bucket: 'appPrimaryAssets', // Use the defineStorage 'name', never raw S3 ARN
      contentType: file.type,
      onProgress: ({ transferredBytes, totalBytes }) => {
        if (totalBytes) {
          console.log(`Upload: ${Math.round((transferredBytes / totalBytes) * 100)}%`);
        }
      },
    },
  });

  const { path } = await uploadTask.result;
  await client.models.Order.update({
    id: orderId,
    invoiceStoragePath: path,
  });
  return path;
}
```
