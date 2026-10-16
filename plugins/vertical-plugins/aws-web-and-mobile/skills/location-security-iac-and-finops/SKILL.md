---
name: location-security-iac-and-finops
description: Security, authentication, Infrastructure-as-Code (AWS CDK, Terraform, CloudFormation, Amplify Gen 2), FinOps cost optimization, and regional TPS/RPS quota engineering for Amazon Location Service. Use when provisioning V2 API Keys (`v1.public.*`), configuring Cognito Identity Pools or least-privilege IAM policies, encrypting Trackers with KMS CMKs (`KmsKeyEnableGeospatialQueries`), synthesizing CDK/Terraform/Amplify Gen 2 templates (strictly blocking deprecated V1 `Map`/`PlaceIndex`/`RouteCalculator` resources), or optimizing Places/Routes/Tracker costs and throughput limits.
---

# Amazon Location Service: Security, Infrastructure-as-Code & FinOps Engineering

## 1. Authentication Selection Matrix

| Workload / Client Type | Target APIs | Recommended Auth Mechanism | Why |
|---|---|---|---|
| **Public Web / Mobile App** | Maps V2 (`geo-maps`), Places V2 (`geo-places`), Routes V2 (`geo-routes`) | **Scoped V2 API Key** (`v1.public.*`) | Enables CloudFront CDN edge caching for vector tiles/sprites/glyphs and avoids Cognito STS token latency on initial map load. |
| **Authenticated Mobile / Web Client** | Trackers & Geofences (`location`) | **Amazon Cognito Identity Pool** (IAM temporary credentials) | Trackers and Geofence Collections **do not support API Keys**; Cognito Identity Pools issue short-lived SigV4 credentials scoped to `cognito-identity.amazonaws.com:sub`. |
| **Backend Services / Lambda / ECS / Step Functions** | All V2 APIs (`geo-*`) and Stateful (`location`) | **IAM Role (SigV4)** | Zero static secrets, automatic rotation, fine-grained resource and condition keys. |
| **Hardware IoT Trackers** | `BatchUpdateDevicePosition` (`location`) | **AWS IoT Core `LocationAction`** or **Soracom Beam** | X.509 mTLS certificate authentication at IoT Core edge or cellular SIM-authenticated SigV4 proxy. |

---

## 2. V2 API Key Security Guardrails (`AWS::Location::APIKey`)

### Mandatory Action & Resource Naming Rules

> **Critical Pitfall**: Never use legacy `geo:GetMap*`, `geo:SearchPlaceIndex*`, or `geo:CalculateRoute*` actions in V2 API Keys or IAM policies—they fail with `403 AccessDeniedException` against V2 endpoints. Always use `geo-maps:*`, `geo-places:*`, and `geo-routes:*` paired with resourceless `provider/default` ARNs.

| Service | Valid V2 `AllowActions` | Valid V2 `AllowResources` |
|---|---|---|
| **Maps V2** | `geo-maps:GetTile`, `geo-maps:GetStaticMap`, `geo-maps:GetStyleDescriptor`, `geo-maps:GetSprites`, `geo-maps:GetGlyphs` | `arn:aws:geo-maps:<region>::provider/default` |
| **Places V2** | `geo-places:Autocomplete`, `geo-places:Geocode`, `geo-places:ReverseGeocode`, `geo-places:SearchText`, `geo-places:SearchNearby`, `geo-places:Suggest`, `geo-places:GetPlace` | `arn:aws:geo-places:<region>::provider/default` |
| **Routes V2** | `geo-routes:CalculateRoutes`, `geo-routes:CalculateRouteMatrix`, `geo-routes:CalculateIsolines`, `geo-routes:OptimizeWaypoints`, `geo-routes:SnapToRoads` | `arn:aws:geo-routes:<region>::provider/default` |

### Hardening Browser & Mobile API Keys

1. **Always Set `AllowReferers` for Browser Keys**: Restrict browser-exposed keys to explicit origins/paths (e.g., `["https://app.example.com/*", "http://localhost:3000/*"]`). Never deploy an unrestricted wildcard key to client-side code.
2. **Restrict Mobile App Packages**: When creating keys for Android/iOS apps, configure `AndroidApps` (package name + SHA-1 certificate fingerprint) or `AppleApps` (bundle ID).
3. **Never Log `v1.public.*` Key Values**: Retrieve key values at runtime via `aws location describe-key` or inject via environment variables (`NEXT_PUBLIC_LOCATION_API_KEY` / `VITE_LOCATION_API_KEY`).

---

## 3. Infrastructure-as-Code (IaC) Guardrails

### Non-Negotiable V1 Deprecation Rule

**NEVER synthesize any of the following deprecated V1 resources** in AWS CDK, CloudFormation, Terraform, or Amplify Gen 2:
- ❌ `AWS::Location::Map` / `location.CfnMap` / `aws_location_map`
- ❌ `AWS::Location::PlaceIndex` / `location.CfnPlaceIndex` / `aws_location_place_index`
- ❌ `AWS::Location::RouteCalculator` / `location.CfnRouteCalculator` / `aws_location_route_calculator`

Maps, Places, and Routes V2 are **100% resourceless**. Only provision:
- ✅ `AWS::Location::APIKey` (`location.CfnAPIKey` / `aws_location_api_key`)
- ✅ `AWS::Location::Tracker` (`location.CfnTracker` / `aws_location_tracker`)
- ✅ `AWS::Location::GeofenceCollection` (`location.CfnGeofenceCollection` / `aws_location_geofence_collection`)
- ✅ `AWS::Location::TrackerConsumer` (`location.CfnTrackerConsumer` / `aws_location_tracker_association`)

### AWS CDK v2 (TypeScript) Complete Production Stack

```typescript
import * as cdk from "aws-cdk-lib";
import * as location from "aws-cdk-lib/aws-location";
import * as kms from "aws-cdk-lib/aws-kms";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";

export class LocationProductionStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 1. Scoped V2 API Key for Resourceless Maps, Places, and Routes
    const frontendApiKey = new location.CfnAPIKey(this, "FrontendV2ApiKey", {
      keyName: `${this.stackName}-frontend-v2-key`,
      noExpiry: false,
      expireTime: "2027-12-31T23:59:59Z",
      restrictions: {
        allowActions: [
          "geo-maps:GetTile",
          "geo-maps:GetStaticMap",
          "geo-maps:GetStyleDescriptor",
          "geo-maps:GetSprites",
          "geo-maps:GetGlyphs",
          "geo-places:Autocomplete",
          "geo-places:Suggest",
          "geo-places:GetPlace",
          "geo-places:Geocode",
          "geo-places:ReverseGeocode",
          "geo-places:SearchText",
          "geo-places:SearchNearby",
          "geo-routes:CalculateRoutes",
          "geo-routes:CalculateIsolines",
        ],
        allowResources: [
          `arn:aws:geo-maps:${this.region}::provider/default`,
          `arn:aws:geo-places:${this.region}::provider/default`,
          `arn:aws:geo-routes:${this.region}::provider/default`,
        ],
        allowReferers: [
          "https://app.example.com/*",
          "http://localhost:3000/*",
        ],
      },
    });

    // 2. Customer-Managed KMS Key for Tracker Encryption
    const trackerKmsKey = new kms.Key(this, "TrackerKmsKey", {
      enableKeyRotation: true,
      description: "CMK for Amazon Location Tracker with geospatial query support",
    });

    // 3. Stateful Tracker with AccuracyBased Filtering & KMS Geospatial Queries Enabled
    const fleetTracker = new location.CfnTracker(this, "FleetTracker", {
      trackerName: `${this.stackName}-fleet-tracker`,
      positionFiltering: "AccuracyBased",
      kmsKeyId: trackerKmsKey.keyArn,
      kmsKeyEnableGeospatialQueries: true, // Required for polygon-filtered ListDevicePositions
      eventBridgeEnabled: false, // Keep false unless raw UPDATE events are needed on EventBridge
    });

    // 4. Stateful Geofence Collection
    const geofenceCollection = new location.CfnGeofenceCollection(this, "DeliveryZones", {
      collectionName: `${this.stackName}-delivery-zones`,
      kmsKeyId: trackerKmsKey.keyArn,
    });

    // 5. Mandatory Binding: AssociateTrackerConsumer
    const trackerBinding = new location.CfnTrackerConsumer(this, "TrackerGeofenceBinding", {
      trackerName: fleetTracker.trackerName,
      consumerArn: geofenceCollection.attrArn,
    });
    trackerBinding.addDependency(fleetTracker);
    trackerBinding.addDependency(geofenceCollection);

    // 6. EventBridge Rule for Geofence ENTER / EXIT Alerts
    new events.Rule(this, "GeofenceBreachRule", {
      eventPattern: {
        source: ["aws.geo"],
        detailType: ["Location Geofence Event"],
        detail: {
          EventType: ["ENTER", "EXIT"],
          TrackerName: [fleetTracker.trackerName],
          CollectionName: [geofenceCollection.collectionName],
        },
      },
    });
  }
}
```

### AWS Amplify Gen 2 (`amplify/backend.ts`) V2 Escape Hatch

Amplify Gen 2 projects must attach V2 resourceless IAM permissions (`geo-maps:*`, `geo-places:*`, `geo-routes:*`) directly to the authenticated/unauthenticated Cognito IAM roles or provision a `CfnAPIKey` via CDK constructs—never V1 `CfnMap` or `CfnPlaceIndex`:

```typescript
import { defineBackend } from "@aws-amplify/backend";
import { Stack } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as location from "aws-cdk-lib/aws-location";
import { auth } from "./auth/resource";

const backend = defineBackend({ auth });
const geoStack = backend.createStack("LocationV2Stack");
const region = Stack.of(geoStack).region;

// Grant authenticated Cognito users direct access to V2 Places & Routes
backend.auth.resources.authenticatedUserIamRole.addToPrincipalPolicy(
  new iam.PolicyStatement({
    effect: iam.Effect.ALLOW,
    actions: [
      "geo-places:Autocomplete",
      "geo-places:Suggest",
      "geo-places:GetPlace",
      "geo-places:Geocode",
      "geo-places:ReverseGeocode",
      "geo-places:SearchText",
      "geo-places:SearchNearby",
      "geo-routes:CalculateRoutes",
      "geo-routes:CalculateIsolines",
      "geo-routes:CalculateRouteMatrix",
      "geo-routes:OptimizeWaypoints",
    ],
    resources: [
      `arn:aws:geo-places:${region}::provider/default`,
      `arn:aws:geo-routes:${region}::provider/default`,
    ],
  })
);
```

---

## 4. FinOps, Data Licensing Compliance & RPS Quota Engineering

### Cost Optimization Checklist

1. **Keep Places V2 Calls in the `Core` Pricing Tier**:
   - Omit `AdditionalFeatures` on `Autocomplete`, `Suggest`, `Geocode`, `ReverseGeocode`, `SearchText`, `SearchNearby`, and `GetPlace` unless you specifically need `Contact`, `OpeningHours`, `TimeZone`, or `Access` (which trigger the **Advanced** tier at ~4x higher cost).
2. **Respect `IntendedUse: "SingleUse"` vs. `"Storage"`**:
   - Use `"SingleUse"` (default) for live UI rendering, type-ahead dropdowns, and immediate routing.
   - Set `"Storage"` whenever persisting geocoded coordinates, `PlaceId`s, or standardized addresses into a database or data lake.
3. **Debounce `Autocomplete` / `Suggest` Keystrokes**:
   - Enforce a `250ms–300ms` debounce and minimum `3-character` threshold on frontend search inputs, and only invoke `GetPlace` once when the user selects a suggestion.
4. **Filter Noisy Tracker Streams with `AccuracyBased` or `DistanceBased`**:
   - Avoids paying for geofence evaluations and history storage when GPS drift occurs while devices are parked or indoors.

### Regional Default RPS Quotas & Adaptive Retry Configuration

| API Operation | Default Regional Quota (RPS) | Burst / Retry Strategy |
|---|---|---|
| `CalculateRouteMatrix`, `CalculateIsolines` | **10 RPS** | Batch origins/destinations into a single matrix call (up to 625 cells bounded); configure SDK `retryMode: "adaptive"`. |
| `OptimizeWaypoints` | **10 RPS** | Consolidate up to 50 stops per request; offload batch dispatch planning to SQS with concurrency control. |
| `CalculateRoutes`, `SnapToRoads` | **50 RPS** | Use `retryMode: "adaptive"` (`maxAttempts: 5`). |
| `Geocode`, `ReverseGeocode`, `SearchText`, `SearchNearby`, `GetPlace`, `Autocomplete`, `Suggest` | **100 RPS** | For bulk US/CA/UK/AU address datasets (>10,000 records), use `location:StartJob` (`ValidateAddress`) instead of hammering synchronous `Geocode`. |
| `GetTile`, `GetStaticMap` | **10,000+ RPS** | Served via CloudFront CDN edge caching when authenticated with V2 API Keys (`?key=...`). |
