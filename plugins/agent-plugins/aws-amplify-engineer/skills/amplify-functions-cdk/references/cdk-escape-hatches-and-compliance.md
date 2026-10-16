# CDK Escape Hatches, Custom Stacks, and Template Compliance

## 1. Modifying Amplify-Generated Resources (`cfnResources` L1 Overrides)

Every Amplify category exposes its underlying L1 CloudFormation constructs under `backend.<category>.resources.cfnResources` in `amplify/backend.ts`:

```typescript
import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import { storage } from './storage/resource';

const backend = defineBackend({ auth, data, storage });

// 1. Cognito User Pool & Identity Pool L1 Overrides
const { cfnUserPool, cfnIdentityPool } = backend.auth.resources.cfnResources;
cfnUserPool.policies = {
  passwordPolicy: {
    minimumLength: 12,
    requireLowercase: true,
    requireUppercase: true,
    requireNumbers: true,
    requireSymbols: true,
    temporaryPasswordValidityDays: 3,
  },
};
// Disable unauthenticated guest identities when not needed
cfnIdentityPool.allowUnauthenticatedIdentities = false;

// 2. DynamoDB Table L1 Overrides (PITR, TTL, Billing, Deletion Protection)
const { amplifyDynamoDbTables } = backend.data.resources.cfnResources;
for (const table of Object.values(amplifyDynamoDbTables)) {
  table.pointInTimeRecoveryEnabled = true;
  table.deletionProtectionEnabled = true;
}
amplifyDynamoDbTables['Session'].timeToLiveAttribute = {
  attributeName: 'expiresAt',
  enabled: true,
};

// 3. S3 Bucket L1 Overrides (Lifecycle Rules, Versioning)
const { cfnBucket } = backend.storage.resources.cfnResources;
cfnBucket.versioningConfiguration = {
  status: 'Enabled',
};
```

---

## 2. Adding Custom CDK Stacks (`backend.createStack()`)

Use `backend.createStack('<UniqueStackName>')` in `amplify/backend.ts` to provision AWS resources not covered by `define*` primitives (API Gateway REST/HTTP APIs, SQS/SNS, EventBridge buses, Step Functions, Amazon Location Service, IoT PubSub, or WAFv2):

```typescript
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import { HttpUserPoolAuthorizer } from 'aws-cdk-lib/aws-apigatewayv2-authorizers';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';

const apiStack = backend.createStack('HttpApiStack');

const userPoolAuthorizer = new HttpUserPoolAuthorizer(
  'CognitoAuthorizer',
  backend.auth.resources.userPool,
  {
    userPoolClients: [backend.auth.resources.userPoolClient],
  },
);

const httpApi = new apigwv2.HttpApi(apiStack, 'WebhookHttpApi', {
  corsPreflight: {
    allowOrigins: ['https://app.example.com'],
    allowMethods: [apigwv2.CorsHttpMethod.POST, apigwv2.CorsHttpMethod.GET],
    allowHeaders: ['Authorization', 'Content-Type'],
  },
});

httpApi.addRoutes({
  path: '/webhooks/orders',
  methods: [apigwv2.HttpMethod.POST],
  integration: new HttpLambdaIntegration(
    'OrderWebhookIntegration',
    backend.orderProcessor.resources.lambda,
  ),
  authorizer: userPoolAuthorizer,
});

// Expose custom endpoints to amplify_outputs.json
backend.addOutput({
  custom: {
    webhookApiUrl: httpApi.url!,
    region: apiStack.region,
  },
});
```

---

## 3. CloudFormation Synthesis Validation & Compliance (`awsiac` MCP)

Whenever you add custom CDK constructs or override `cfnResources` in `amplify/backend.ts`:

1. Synthesize or deploy to sandbox (`npx ampx sandbox --once`), which emits CloudFormation templates to `.amplify/artifacts/cdk.out/`.
2. Run the `awsiac` MCP tools against the generated `.template.json` files:
   - `validate_cloudformation_template`: Runs `cfn-lint` to catch invalid property combinations, missing required attributes, and circular resource references before CloudFormation execution.
   - `check_cloudformation_template_compliance`: Runs AWS CloudFormation Guard (`cfn-guard`) rules to detect overly permissive IAM wildcards (`"Action": "*"`), unencrypted storage, or public buckets.
   - `troubleshoot_cloudformation_deployment`: If a sandbox or pipeline deployment rolls back, inspect stack events and root-cause the failing logical ID.
