# Migration, Infrastructure as Code (IaC), and FinOps Guide

> **Audience Note**: Keywords MUST, SHOULD, MAY in this document indicate requirements for agent recommendations to users, following RFC 2119.

Comprehensive engineering reference for migrating existing applications (from Google Maps Platform, Mapbox, or legacy Amazon Location V1) to Amazon Location Service V2, provisioning stateful resources via Infrastructure as Code (AWS CDK, Terraform, CloudFormation, Amplify Gen 2), and optimizing costs and regional TPS quotas.

## Table of Contents

- [Part 1: Google Maps, Mapbox & AWS Location V1 to V2 Migration](#part-1-google-maps-mapbox--aws-location-v1-to-v2-migration)
  - [Coordinate Ordering Invariant](#coordinate-ordering-invariant)
  - [Google Maps & Mapbox to AWS Location V2 API Mapping](#google-maps--mapbox-to-aws-location-v2-api-mapping)
  - [Legacy AWS Location V1 to Resourceless V2 API Mapping](#legacy-aws-location-v1-to-resourceless-v2-api-mapping)
  - [Response Payload & Field Translation](#response-payload--field-translation)
- [Part 2: Infrastructure as Code (IaC) Guardrails & Templates](#part-2-infrastructure-as-code-iac-guardrails--templates)
  - [Strict V2 Resourceless vs. Stateful IaC Rule](#strict-v2-resourceless-vs-stateful-iac-rule)
  - [AWS CDK (TypeScript) Production Template](#aws-cdk-typescript-production-template)
  - [Terraform (HCL) Production Template](#terraform-hcl-production-template)
  - [Amplify Gen 2 (`amplify/backend.ts`) Integration](#amplify-gen-2-amplifybackendts-integration)
- [Part 3: FinOps, Data Licensing (`IntendedUse`), and Quota Engineering](#part-3-finops-data-licensing-intendeduse-and-quota-engineering)
  - [Places V2 Pricing Tiers (`Core` vs. `Advanced`)](#places-v2-pricing-tiers-core-vs-advanced)
  - [Data Storage & Licensing Compliance (`IntendedUse`)](#data-storage--licensing-compliance-intendeduse)
  - [Routes V2 Cost Optimization](#routes-v2-cost-optimization)
  - [Tracker & Geofence Cost Multiplication Formula](#tracker--geofence-cost-multiplication-formula)
  - [Regional Service Quotas (RPS / TPS) & Exponential Backoff](#regional-service-quotas-rps--tps--exponential-backoff)

---

## Part 1: Google Maps, Mapbox & AWS Location V1 to V2 Migration

### Coordinate Ordering Invariant

The single highest-frequency bug when migrating from Google Maps or Leaflet is reversed coordinates:

- **Google Maps / Leaflet**: `[latitude, longitude]` (`[y, x]` or `{ lat, lng }`)
- **Amazon Location Service (All APIs) & MapLibre GL**: `[longitude, latitude]` (`[x, y]` GeoJSON standard)

Agents MUST enforce this conversion helper at every boundary where external `[lat, lng]` coordinates enter the system:

```typescript
/**
 * Converts Google Maps { lat, lng } or [lat, lng] to Amazon Location GeoJSON [longitude, latitude].
 */
export function toLngLat(
  input: { lat: number; lng: number } | [number, number],
): [number, number] {
  const [lat, lng] = Array.isArray(input) ? input : [input.lat, input.lng];
  if (Math.abs(lat) > 90 || Math.abs(lng) > 180) {
    throw new RangeError(
      `Invalid coordinates: lat=${lat} (must be [-90, 90]), lng=${lng} (must be [-180, 180]). Check for [lng, lat] vs [lat, lng] swap.`,
    );
  }
  return [lng, lat];
}
```

### Google Maps & Mapbox to AWS Location V2 API Mapping

NEVER map Google Maps or Mapbox endpoints to legacy AWS Location V1 operations (`SearchPlaceIndexForText`, `CalculateRoute`, etc.). Always target the resourceless V2 APIs (`geo-places`, `geo-routes`, `geo-maps`):

| Capability | Google Maps Platform (V2 / New) | Mapbox API | Amazon Location Service V2 (`@aws-sdk/client-geo-*`) |
| --- | --- | --- | --- |
| **Interactive Vector Map** | `google.maps.Map` | `mapboxgl.Map` (`mapbox://styles/...`) | `maplibregl.Map` with `https://maps.geo.${region}.amazonaws.com/v2/styles/Standard/descriptor?key=${apiKey}` (`validateStyle: false`) |
| **Static Map Image** | `/maps/api/staticmap` | `/styles/v1/{user}/{style}/static/...` | `geo-maps:GetStaticMap` (`GetStaticMapCommand`) |
| **Address Autocomplete** | `places:autocomplete` (address types) | `/search/searchbox/v1/suggest` | `geo-places:Autocomplete` (`AutocompleteCommand`) $\rightarrow$ `geo-places:GetPlace` (`GetPlaceCommand`) |
| **POI / Place Type-Ahead** | `places:autocomplete` (establishment) | `/search/searchbox/v1/suggest` | `geo-places:Suggest` (`SuggestCommand`) $\rightarrow$ `geo-places:GetPlace` (`GetPlaceCommand`) |
| **Free-Text POI Search** | `POST /v1/places:searchText` | `/search/searchbox/v1/forward` | `geo-places:SearchText` (`SearchTextCommand`) |
| **Coordinate Proximity Search** | `POST /v1/places:searchNearby` | `/search/searchbox/v1/category` | `geo-places:SearchNearby` (`SearchNearbyCommand` with `Filter.IncludeCategories`) |
| **Place Details by ID** | `GET /v1/places/{placeId}` | `/search/searchbox/v1/retrieve/{id}` | `geo-places:GetPlace` (`GetPlaceCommand`) |
| **Forward Geocoding** | `/maps/api/geocode/json?address=` | `/search/geocode/v6/forward` | `geo-places:Geocode` (`GeocodeCommand`) |
| **Reverse Geocoding** | `/maps/api/geocode/json?latlng=` | `/search/geocode/v6/reverse` | `geo-places:ReverseGeocode` (`ReverseGeocodeCommand`) |
| **Bulk Postal Validation** | `POST /v1:validateAddress` | N/A | `location:StartJob` (`Action: "ValidateAddress"`) for bulk S3 Parquet (US/CA/UK/AU); `Geocode` (`MatchScores`) for single synchronous check |
| **Turn-by-Turn Routing** | `POST /directions/v2:computeRoutes` | `/directions/v5/mapbox/{profile}` | `geo-routes:CalculateRoutes` (`CalculateRoutesCommand`) |
| **Route Distance Matrix** | `POST /distanceMatrix/v2:computeRouteMatrix` | `/directions-matrix/v1/mapbox/{profile}` | `geo-routes:CalculateRouteMatrix` (`CalculateRouteMatrixCommand` with required `RoutingBoundary`) |
| **Service Areas / Isochrones** | N/A | `/isochrone/v1/mapbox/{profile}` | `geo-routes:CalculateIsolines` (`CalculateIsolinesCommand`) |
| **Multi-Stop TSP Optimization** | `computeRoutes` (`optimizeWaypointOrder: true`) | `/optimized-trips/v1/mapbox/{profile}` | `geo-routes:OptimizeWaypoints` (`OptimizeWaypointsCommand`) |
| **GPS Trace Road Alignment** | Roads API `/v1/snapToRoads` | `/matching/v5/mapbox/{profile}` | `geo-routes:SnapToRoads` (`SnapToRoadsCommand`) |

### Legacy AWS Location V1 to Resourceless V2 API Mapping

When upgrading an existing AWS codebase from `@aws-sdk/client-location` (V1 Maps, Places, Routes) to V2:

| Legacy V1 SDK (`@aws-sdk/client-location`) | Legacy Resource Required (Decommission) | Modern V2 SDK & Command (Resourceless) | Key Behavioral & Parameter Changes in V2 |
| --- | --- | --- | --- |
| `GetMapStyleDescriptorCommand` / `GetMapTileCommand` | `Map` (`CfnMap`) | `@aws-sdk/client-geo-maps` / Direct URL `/v2/styles/{Style}/descriptor?key=` | No `MapName` parameter; select `Standard`, `Monochrome`, `Hybrid`, or `Satellite` directly. |
| `SearchPlaceIndexForTextCommand` | `PlaceIndex` (`CfnPlaceIndex`) | `@aws-sdk/client-geo-places`: `SearchTextCommand` (POIs) or `GeocodeCommand` (addresses) | V2 splits address geocoding (`Geocode`) from POI discovery (`SearchText`). Results are in `ResultItems` (not `Results`). |
| `SearchPlaceIndexForPositionCommand` | `PlaceIndex` (`CfnPlaceIndex`) | `@aws-sdk/client-geo-places`: `ReverseGeocodeCommand` | Uses `QueryPosition: [lng, lat]` (not `Position`). Returns `ResultItems`. |
| `SearchPlaceIndexForSuggestionsCommand` | `PlaceIndex` (`CfnPlaceIndex`) | `@aws-sdk/client-geo-places`: `AutocompleteCommand` (addresses) or `SuggestCommand` (POIs) | V2 `/suggest` does NOT support request-level category filtering. Use `SearchNearby` with `Filter.IncludeCategories` for category filtering. |
| `GetPlaceCommand` (V1) | `PlaceIndex` (`CfnPlaceIndex`) | `@aws-sdk/client-geo-places`: `GetPlaceCommand` | No `IndexName` required. `Address` contains nested `Region: { Code, Name }` and `Country: { Code2, Code3, Name }`. |
| `CalculateRouteCommand` | `RouteCalculator` (`CfnRouteCalculator`) | `@aws-sdk/client-geo-routes`: `CalculateRoutesCommand` | Uses `Origin` and `Destination` (not `DeparturePosition` / `DestinationPosition`). Set `LegGeometryFormat: "Simple"` for GeoJSON coordinate arrays. |
| `CalculateRouteMatrixCommand` (V1) | `RouteCalculator` (`CfnRouteCalculator`) | `@aws-sdk/client-geo-routes`: `CalculateRouteMatrixCommand` | Uses `Origins: [{ Position: [lng, lat] }]`, `Destinations: [{ Position: [lng, lat] }]`, and **requires** `RoutingBoundary` (e.g., `{ AutoCircle: {} }`). |

### Response Payload & Field Translation

| Source Field (Google Maps / Legacy V1) | Amazon Location V2 Target Field | Critical Anti-Hallucination Rule |
| --- | --- | --- |
| `results[i].formatted_address` / `Place.Label` | `ResultItems[i].Address.Label` | **NEVER** display `ResultItems[i].Title` in `Autocomplete` dropdowns (`Title` reverses street/postal components). Always render `Address.Label`. |
| `results[i].geometry.location` (`{ lat, lng }`) | `ResultItems[i].Position` (`[lng, lat]`) | `Position` is `[longitude, latitude]`. In `SuggestCommand`, coordinates are at `ResultItems[i].Place.Position`. |
| `address_components` (flat array) | `ResultItems[i].Address` (nested object) | Access `Address.Region.Code` (not `Address.Region`) and `Address.Country.Code2` / `Address.Country.Code3` (not `Address.Country`). |
| `routes[0].distanceMeters` / `Summary.Distance` (km in V1) | `Routes[0].Summary.Distance` | V2 `Distance` is always in **meters** (integer) and `Duration` is always in **seconds** (integer). |
| `routes[0].polyline.encodedPolyline` | `Routes[0].Legs[0].Geometry.LineString` | Pass `LegGeometryFormat: "Simple"` in `CalculateRoutesCommand` to receive a ready-to-render `[lng, lat][]` GeoJSON `LineString` without polyline decoding. |

---

## Part 2: Infrastructure as Code (IaC) Guardrails & Templates

### Strict V2 Resourceless vs. Stateful IaC Rule

1. **NEVER provision legacy V1 resources for Maps, Places, or Routes**:
   - Block `aws_location.CfnMap`, `aws_location.CfnPlaceIndex`, `aws_location.CfnRouteCalculator` in AWS CDK / CloudFormation.
   - Block `aws_location_map`, `aws_location_place_index`, `aws_location_route_calculator` in Terraform.
   - Maps V2, Places V2, and Routes V2 operate directly against regional default provider ARNs:
     - `arn:aws:geo-maps:${region}::provider/default`
     - `arn:aws:geo-places:${region}::provider/default`
     - `arn:aws:geo-routes:${region}::provider/default`
2. **Stateful IaC is strictly reserved for**:
   - **API Keys** (`AWS::Location::APIKey` / `aws_location_api_key`) scoped to V2 `geo-maps:*`, `geo-places:*`, `geo-routes:*` actions and `arn:aws:geo-*:${region}::provider/default` resources.
   - **Trackers** (`AWS::Location::Tracker` / `aws_location_tracker`) with explicit `PositionFiltering` (`AccuracyBased`, `DistanceBased`, or `TimeBased`), `EventBridgeEnabled`, and optional customer-managed KMS encryption (`KmsKeyId` + `KmsKeyEnableGeospatialQueries: true`).
   - **Geofence Collections** (`AWS::Location::GeofenceCollection` / `aws_location_geofence_collection`).
   - **Tracker-to-Geofence Associations** (`AWS::Location::TrackerConsumer` / `aws_location_tracker_association`).
   - **EventBridge Rules & AWS IoT Core `LocationAction` Topic Rules**.

### AWS CDK (TypeScript) Production Template

```typescript
import * as cdk from "aws-cdk-lib";
import * as location from "aws-cdk-lib/aws-location";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as sns from "aws-cdk-lib/aws-sns";
import * as kms from "aws-cdk-lib/aws-kms";
import { Construct } from "constructs";

export class LocationServiceStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const region = cdk.Stack.of(this).region;

    // 1. Scoped V2 API Key for Client-Side Maps, Places, and Routes (Resourceless)
    const frontendApiKey = new location.CfnAPIKey(this, "FrontendV2ApiKey", {
      keyName: "prod-web-v2-key",
      description: "Scoped V2 API key for MapLibre, Places V2, and Routes V2",
      expireTime: "2027-01-01T00:00:00Z", // Always set an expiration time
      restrictions: {
        allowActions: [
          "geo-maps:GetTile",
          "geo-maps:GetStaticMap",
          "geo-places:Autocomplete",
          "geo-places:Geocode",
          "geo-places:ReverseGeocode",
          "geo-places:SearchText",
          "geo-places:SearchNearby",
          "geo-places:Suggest",
          "geo-places:GetPlace",
          "geo-routes:CalculateRoutes",
          "geo-routes:CalculateRouteMatrix",
          "geo-routes:CalculateIsolines",
          "geo-routes:OptimizeWaypoints",
          "geo-routes:SnapToRoads",
        ],
        allowResources: [
          `arn:aws:geo-maps:${region}::provider/default`,
          `arn:aws:geo-places:${region}::provider/default`,
          `arn:aws:geo-routes:${region}::provider/default`,
        ],
        allowReferers: [
          "https://app.example.com/*",
          "http://localhost:3000/*",
        ],
      },
    });

    // 2. Optional Customer-Managed KMS Key for Tracker Encryption
    const locationKmsKey = new kms.Key(this, "LocationTrackerKmsKey", {
      enableKeyRotation: true,
      description: "CMK for Amazon Location Tracker position encryption",
    });

    // 3. Stateful Device Tracker with AccuracyBased Filtering & KMS Geospatial Queries
    const fleetTracker = new location.CfnTracker(this, "FleetTracker", {
      trackerName: "prod-fleet-tracker",
      positionFiltering: "AccuracyBased", // Suppresses GPS jitter & extra geofence evaluations
      eventBridgeEnabled: true, // Required ONLY if downstream rules need raw position UPDATE events
      kmsKeyId: locationKmsKey.keyArn,
      kmsKeyEnableGeospatialQueries: true, // Required to allow Polygon bounding queries with CMK
    });

    // 4. Stateful Geofence Collection
    const geofenceCollection = new location.CfnGeofenceCollection(
      this,
      "DeliveryZonesCollection",
      {
        collectionName: "prod-delivery-zones",
        description: "Warehouse and customer delivery geofences",
        kmsKeyId: locationKmsKey.keyArn,
      },
    );

    // 5. Link Tracker to Geofence Collection (Mandatory for automatic ENTER/EXIT evaluation)
    new location.CfnTrackerConsumer(this, "FleetTrackerGeofenceLink", {
      trackerName: fleetTracker.trackerName,
      consumerArn: geofenceCollection.attrCollectionArn,
    });

    // 6. EventBridge Rule for Geofence ENTER/EXIT Alerts
    const alertTopic = new sns.Topic(this, "GeofenceAlertTopic");
    new events.Rule(this, "GeofenceEnterExitRule", {
      description: "Route Amazon Location geofence ENTER/EXIT events to SNS",
      eventPattern: {
        source: ["aws.geo"],
        detailType: ["Location Geofence Event"],
        detail: {
          EventType: ["ENTER", "EXIT"],
          TrackerName: [fleetTracker.trackerName],
          CollectionName: [geofenceCollection.collectionName],
        },
      },
      targets: [new targets.SnsTopic(alertTopic)],
    });
  }
}
```

### Terraform (HCL) Production Template

```hcl
data "aws_region" "current" {}

# 1. Scoped V2 API Key for Resourceless Maps, Places, and Routes
resource "aws_location_api_key" "frontend_v2" {
  key_name    = "prod-web-v2-key"
  description = "Least-privilege V2 API key for Maps, Places, and Routes"
  expire_time = "2027-01-01T00:00:00Z"

  restrictions {
    allow_actions = [
      "geo-maps:GetTile",
      "geo-maps:GetStaticMap",
      "geo-places:Autocomplete",
      "geo-places:Geocode",
      "geo-places:ReverseGeocode",
      "geo-places:SearchText",
      "geo-places:SearchNearby",
      "geo-places:Suggest",
      "geo-places:GetPlace",
      "geo-routes:CalculateRoutes",
      "geo-routes:CalculateRouteMatrix",
      "geo-routes:CalculateIsolines",
      "geo-routes:OptimizeWaypoints",
      "geo-routes:SnapToRoads",
    ]
    allow_resources = [
      "arn:aws:geo-maps:${data.aws_region.current.name}::provider/default",
      "arn:aws:geo-places:${data.aws_region.current.name}::provider/default",
      "arn:aws:geo-routes:${data.aws_region.current.name}::provider/default",
    ]
    allow_referers = [
      "https://app.example.com/*",
    ]
  }
}

# 2. Stateful Tracker with AccuracyBased Position Filtering
resource "aws_location_tracker" "fleet" {
  tracker_name       = "prod-fleet-tracker"
  position_filtering = "AccuracyBased"
}

# 3. Stateful Geofence Collection
resource "aws_location_geofence_collection" "delivery_zones" {
  collection_name = "prod-delivery-zones"
}

# 4. Bind Tracker to Geofence Collection
resource "aws_location_tracker_association" "fleet_to_zones" {
  tracker_name = aws_location_tracker.fleet.tracker_name
  consumer_arn = aws_location_geofence_collection.delivery_zones.collection_arn
}

# 5. EventBridge Rule for Geofence ENTER/EXIT Events
resource "aws_cloudwatch_event_rule" "geofence_events" {
  name        = "prod-location-geofence-events"
  description = "Capture ENTER and EXIT events from Amazon Location Service"
  event_pattern = jsonencode({
    source      = ["aws.geo"]
    detail-type = ["Location Geofence Event"]
    detail = {
      EventType      = ["ENTER", "EXIT"]
      CollectionName = [aws_location_geofence_collection.delivery_zones.collection_name]
    }
  })
}
```

### Amplify Gen 2 (`amplify/backend.ts`) Integration

In Amplify Gen 2 applications, attach V2 resourceless IAM permissions directly to the Cognito Identity Pool roles (or provision a `CfnTracker` / `CfnGeofenceCollection` in a dedicated custom stack):

```typescript
import { defineBackend } from "@aws-amplify/backend";
import * as iam from "aws-cdk-lib/aws-iam";
import * as location from "aws-cdk-lib/aws-location";
import { Stack } from "aws-cdk-lib";
import { auth } from "./auth/resource";
import { data } from "./data/resource";

const backend = defineBackend({ auth, data });
const geoStack = backend.createStack("GeoV2Stack");
const region = Stack.of(geoStack).region;

// Grant authenticated users access to V2 Resourceless Maps, Places, and Routes
backend.auth.resources.authenticatedUserIamRole.addToPrincipalPolicy(
  new iam.PolicyStatement({
    actions: [
      "geo-maps:GetTile",
      "geo-maps:GetStaticMap",
      "geo-places:Autocomplete",
      "geo-places:Geocode",
      "geo-places:ReverseGeocode",
      "geo-places:SearchText",
      "geo-places:SearchNearby",
      "geo-places:Suggest",
      "geo-places:GetPlace",
      "geo-routes:CalculateRoutes",
      "geo-routes:CalculateIsolines",
    ],
    resources: [
      `arn:aws:geo-maps:${region}::provider/default`,
      `arn:aws:geo-places:${region}::provider/default`,
      `arn:aws:geo-routes:${region}::provider/default`,
    ],
  }),
);

// Optional: Stateful Tracker & Geofence Collection for authenticated fleet tracking
const tracker = new location.CfnTracker(geoStack, "FleetTracker", {
  trackerName: "amplify-fleet-tracker",
  positionFiltering: "AccuracyBased",
});

backend.auth.resources.authenticatedUserIamRole.addToPrincipalPolicy(
  new iam.PolicyStatement({
    actions: [
      "geo:BatchUpdateDevicePosition",
      "geo:GetDevicePosition",
      "geo:GetDevicePositionHistory",
    ],
    resources: [tracker.attrTrackerArn],
  }),
);

backend.addOutput({
  custom: {
    awsRegion: region,
    trackerName: tracker.trackerName,
  },
});
```

---

## Part 3: FinOps, Data Licensing (`IntendedUse`), and Quota Engineering

### Places V2 Pricing Tiers (`Core` vs. `Advanced`)

Amazon Location Places V2 bills per request across pricing tiers determined by which parameters and `AdditionalFeatures` you request:

| Pricing Bucket | Triggered By | Cost Optimization Rule |
| --- | --- | --- |
| **Autocomplete / Suggest** | `AutocompleteCommand`, `SuggestCommand` (without `AdditionalFeatures`) | Lowest per-keystroke rate. Debounce client input by **300ms** and require $\ge 3$ characters before firing. |
| **Core (Default)** | `Geocode`, `ReverseGeocode`, `SearchText`, `SearchNearby`, `GetPlace` with default fields (`Title`, `Address`, `Position`, `PlaceType`, `Categories`, `Distance`). | **Default to Core** for search result lists and map pins. Do NOT pass `AdditionalFeatures` on initial list queries unless contact/hours are shown in the list view. |
| **Advanced (`AdditionalFeatures`)** | Requesting `AdditionalFeatures: ["Contact"]`, `["TimeZone"]`, `["Phonemes"]`, `["Access"]`, or `["SecondaryAddresses"]`. | **Two-Step Pattern**: Run `SearchText` / `SearchNearby` / `Suggest` at the Core tier, then call `GetPlace` with `AdditionalFeatures: ["Contact"]` **only** when the user clicks a specific POI to view phone/website/opening hours. |

> **Critical V2 `/suggest` FinOps Anti-Pattern**: Places V2 `SuggestCommand` does **not** support request-level category filtering. Never fetch a large `MaxResults` window with `AdditionalFeatures` on `Suggest` to filter categories on the client side—this inflates per-call costs and can return zero matches after filtering. Instead, use `SearchNearbyCommand` with `Filter: { IncludeCategories: ["restaurant", ...] }` or a two-step `Suggest` $\rightarrow$ `GetPlace` lookup.

### Data Storage & Licensing Compliance (`IntendedUse`)

Places V2 operations (`Geocode`, `ReverseGeocode`, `SearchText`, `SearchNearby`, `GetPlace`) accept an `IntendedUse` parameter:

- **`IntendedUse: "SingleUse"` (Default)**: Results are used immediately (e.g., rendering on a map, displaying in UI, or short-lived in-memory caching) and are **not** stored persistently in a database. Billed at the standard Core/Advanced rate.
- **`IntendedUse: "Storage"`**: Required whenever your application persists geocoded coordinates, standardized addresses, or POI attributes into a database (DynamoDB, Aurora/RDS, S3, OpenSearch). Always confirm with the user whether results will be persisted before setting `IntendedUse: "Storage"`, as stored results are billed at the storage tier rate.

### Routes V2 Cost Optimization

- **`CalculateRouteMatrix` Cell Billing**: `CalculateRouteMatrix` is billed **per matrix element** (`Origins.length × Destinations.length`). A $25 \times 25$ matrix bills 625 elements in a single API call. Pre-filter distant candidates using Haversine (straight-line) distance in application code before calling `CalculateRouteMatrix` on the top $K$ nearest candidates.
- **Avoid Unnecessary `Toll` and `SpanAdditionalFeatures`**: Requesting `LegAdditionalFeatures: ["Tolls"]` or `SpanAdditionalFeatures` moves `CalculateRoutes` into higher pricing tiers. Only request `"Tolls"` when the user or logistics workflow requires toll cost calculation.

### Tracker & Geofence Cost Multiplication Formula

When a Tracker is linked to $C$ Geofence Collections via `AssociateTrackerConsumer`, every position update that passes the tracker's filter triggers $C$ geofence collection evaluations:

$$\text{Monthly Billable Operations} = N_{\text{devices}} \times U_{\text{updates/month}} \times (1 + C_{\text{collections}})$$

- **Why `TimeBased` (default) is expensive with Geofences**: `TimeBased` filtering reduces *storage* to 1 point per 30 seconds, but **still evaluates 100% of incoming updates against all linked geofence collections**. A fleet of 1,000 trucks reporting every 5 seconds with 2 linked collections generates $1,000 \times 720 \times 2 = 1.44\text{M}$ geofence evaluations **per hour**!
- **FinOps Fix**:
  1. Set `PositionFiltering: "AccuracyBased"` (when devices report `Accuracy.Horizontal`) or `"DistanceBased"` (ignores moves $< 30\text{m}$), which drops stationary jitter **before** geofence evaluation—cutting evaluation costs by 70–90%.
  2. Consolidate zones into fewer Geofence Collections (up to 50,000 geofences per collection) and use `GeofenceProperties` (e.g., `Type: "Warehouse"`, `Region: "West"`) to filter events in EventBridge rather than creating separate collections per zone type.

### Regional Service Quotas (RPS / TPS) & Exponential Backoff

Design batching and retry policies around Amazon Location Service default regional quotas:

| Service / API Operation | Default Regional Quota | Adjustable Max | Hard Payload Limits |
| --- | --- | --- | --- |
| `geo-places:*` (`Geocode`, `SearchText`, `SearchNearby`, `Autocomplete`, `Suggest`, `GetPlace`) | 50 RPS (varies by region) | Yes (via Service Quotas) | `Autocomplete`/`Suggest` `MaxResults` $\le 15$; `SearchText`/`SearchNearby` `MaxResults` $\le 100$ |
| `geo-routes:CalculateRoutes` | 10–50 RPS | Yes | Max 50 intermediate `Waypoints` |
| `geo-routes:OptimizeWaypoints` | 10 RPS | Yes | Max 50 waypoints (fewer when `Driver` / `TimeWindows` constraints are used) |
| `location:BatchUpdateDevicePosition` | 50 RPS | 100 RPS | Max **10** device updates per batch call; max **4** `PositionProperties` per update |
| `location:GetDevicePosition` / `BatchGetDevicePosition` / `ListDevicePositions` | 50 RPS | 100 RPS | `BatchGetDevicePosition`: max **10** `DeviceIds` per call |
| `location:BatchEvaluateGeofences` / `BatchPutGeofence` | 50 RPS | 100 RPS | Max **10** entries per batch call; max **3** `GeofenceProperties` per geofence |
| `location:CreateTracker` / `AssociateTrackerConsumer` | 10 RPS | 20 RPS | Max **5** Geofence Collections linked per Tracker |
| Geofence Geometry Limits | N/A | N/A | Max **50,000** geofences per collection; max **1,000** vertices per Polygon/MultiPolygon (up to **100,000** via base64 `Geobuf`) |

Always configure the AWS SDK v3 `adaptive` retry mode for high-throughput backend workers:

```typescript
import { GeoPlacesClient } from "@aws-sdk/client-geo-places";

const placesClient = new GeoPlacesClient({
  region: process.env.AWS_REGION ?? "us-east-1",
  maxAttempts: 5,
  retryMode: "adaptive", // Built-in client-side rate limiting & exponential backoff with jitter on HTTP 429 ThrottlingException
});
```
