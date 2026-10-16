---
name: location-v2-maps-places-routes
description: Production implementation blueprint for Amazon Location Service V2 resourceless APIs (`geo-maps`, `geo-places`, `geo-routes`) and bulk Postal Address Validation Jobs (`location:StartJob`). Use when building interactive MapLibre GL JS v5 / Native maps (3D terrain, 3D buildings, live traffic, political views, static maps with GeoJSON overlays), address autocomplete and geocoding (`MatchScores`), POI discovery (`SearchText`, `SearchNearby`, `Suggest`, `GetPlace`), bulk S3 Parquet address validation (US/CA/UK/AU), or advanced routing (`CalculateRoutes`, `CalculateRouteMatrix` with `RoutingBoundary`, `CalculateIsolines`, `OptimizeWaypoints`, `SnapToRoads`, toll calculation).
---

# Amazon Location Service V2: Maps, Places, Address Validation Jobs & Routes

Amazon Location Service V2 replaces legacy pre-created resources (`AWS::Location::Map`, `AWS::Location::PlaceIndex`, `AWS::Location::RouteCalculator`) with **resourceless `provider/default` endpoints** across three independent AWS SDK v3 / boto3 namespaces:

| Capability | AWS SDK v3 Package | boto3 Client | AWS CLI v2 Namespace | API Key Resource ARN |
|---|---|---|---|---|
| **Maps V2** | `@aws-sdk/client-geo-maps` | `boto3.client('geo-maps')` | `aws geo-maps` | `arn:aws:geo-maps:<region>::provider/default` |
| **Places V2** | `@aws-sdk/client-geo-places` | `boto3.client('geo-places')` | `aws geo-places` | `arn:aws:geo-places:<region>::provider/default` |
| **Routes V2** | `@aws-sdk/client-geo-routes` | `boto3.client('geo-routes')` | `aws geo-routes` | `arn:aws:geo-routes:<region>::provider/default` |
| **Address Validation Jobs** | `@aws-sdk/client-location` | `boto3.client('location')` | `aws location` | IAM Role only (`geo:StartJob`, `geo:GetJob`) |

> **Non-Negotiable Coordinate Rule**: Every Amazon Location Service API and MapLibre GL JS uses **`[longitude, latitude]`** (GeoJSON order), never `[latitude, longitude]`.

---

## 1. Maps V2 (`geo-maps`) & MapLibre GL JS v5

### Mandatory Rendering Rules

1. **Direct Style Descriptor URL Only**: Pass the direct HTTPS descriptor URL into `new maplibregl.Map({ style: ... })`. Never call `GetStyleDescriptor` via SDK to parse JSON manually—it breaks relative sprite/glyph/tile resolution and bypasses CDN caching.
2. **Always Set `validateStyle: false`**: Skips redundant client-side Mapbox GL style spec validation and cuts initial map render time by 30–50%.
3. **Choose the Right V2 Style (`Standard` | `Monochrome` | `Hybrid` | `Satellite`)**:
   - `Standard`: General-purpose navigation and POI display (supports `Light` and `Dark` color schemes).
   - `Monochrome`: Clean backdrop for dense data visualizations, heatmaps, and fleet overlays (supports `Light` and `Dark`).
   - `Hybrid`: Satellite imagery with road networks and place labels overlaid.
   - `Satellite`: Pure aerial/satellite raster tiles without road labels.

### Interactive Map with 3D Terrain, 3D Buildings, Traffic & Geopolitical View

```typescript
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const region = "us-east-1";
const apiKey = process.env.NEXT_PUBLIC_LOCATION_API_KEY!;
const styleName = "Standard"; // Standard | Monochrome | Hybrid | Satellite

// Query parameters customize the style descriptor server-side:
// - color-scheme: Light | Dark (for Standard and Monochrome)
// - terrain: Terrain3D (enables 3D elevation mesh)
// - buildings: Buildings3D (enables extruded 3D building footprints)
// - traffic: All | Congestion (overlays real-time road traffic flow)
// - political-view: ISO-3166-1 alpha-3 code (e.g., IND, ARG, MAR, TUR, EGY)
// - language: BCP-47 language tag (e.g., en, es, fr, ja)
const styleUrl =
  `https://maps.geo.${region}.amazonaws.com/v2/styles/${styleName}/descriptor` +
  `?key=${encodeURIComponent(apiKey)}` +
  `&color-scheme=Light` +
  `&terrain=Terrain3D` +
  `&buildings=Buildings3D` +
  `&traffic=All`;

const map = new maplibregl.Map({
  container: "map",
  style: styleUrl,
  center: [-122.3321, 47.6062], // [longitude, latitude] — Seattle
  zoom: 14,
  pitch: 60, // Tilt camera to reveal 3D buildings and terrain
  bearing: -20,
  validateStyle: false, // Mandatory performance optimization
});

map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
```

### Static Maps (`GetStaticMap`) with GeoJSON Overlays

Use `GetStaticMap` (`geo-maps:GetStaticMap`) for email receipts, delivery confirmations, PDF reports, or thumbnail previews without loading JavaScript.

```typescript
import { GeoMapsClient, GetStaticMapCommand } from "@aws-sdk/client-geo-maps";
import { writeFileSync } from "node:fs";

const mapsClient = new GeoMapsClient({ region: "us-east-1" });

const geoJsonOverlay = JSON.stringify({
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      geometry: { type: "Point", coordinates: [-122.3321, 47.6062] },
      properties: { "marker-color": "#FF5722", "marker-size": "large", label: "A" },
    },
    {
      type: "Feature",
      geometry: { type: "Point", coordinates: [-122.3493, 47.6205] },
      properties: { "marker-color": "#2196F3", "marker-size": "large", label: "B" },
    },
  ],
});

const response = await mapsClient.send(
  new GetStaticMapCommand({
    FileName: "delivery-summary",
    Width: 800,
    Height: 400,
    ScaleBarUnit: "Kilometers",
    Style: "Satellite", // Standard | Monochrome | Hybrid | Satellite
    BoundedPositions: "-122.3600,47.6000,-122.3200,47.6300",
    Padding: 40,
    GeoJsonOverlay: geoJsonOverlay,
    Key: process.env.LOCATION_API_KEY,
  })
);

if (response.Blob) {
  const bytes = await response.Blob.transformToByteArray();
  writeFileSync("delivery-summary.png", Buffer.from(bytes));
}
```

> **Southeast Asia (`ap-southeast-1`) Regional Data Note**: When deploying workloads targeting Southeast Asia (Singapore, Malaysia, Philippines, Thailand, Vietnam, Indonesia, Myanmar, Cambodia), deploy in **`ap-southeast-1` (Singapore)** to leverage **GrabMaps** hyper-local street, alley, and POI coverage.

---

## 2. Places V2 (`geo-places`) Decision Matrix & Guardrails

### Choosing the Right Places V2 Operation

| User Scenario | API Operation | Key Guardrails |
|---|---|---|
| **Address form type-ahead** ("123 Main St") | `Autocomplete` $\rightarrow$ `GetPlace` | Always render **`Address.Label`** (never `Title`, which reverses street/number order in many locales). Call `GetPlace` with the selected `PlaceId` to retrieve `[lng, lat]` coordinates and parsed components. |
| **POI / brand search-box predictions** ("Starb...") | `Suggest` $\rightarrow$ `GetPlace` | Predicts POIs, chains, and query completions. **Warning**: `/suggest` does **not** support `Filter.IncludeCategories`. Do not fetch `Suggest` results and filter categories client-side with `AdditionalFeatures: ["Core"]`. If category filtering is required, use `SearchNearby` or `SearchText`. |
| **Single address geocoding & match confidence** | `Geocode` | Synchronous resolution returning `[lng, lat]`, `Address.Label`, and `MatchScores` (`Overall` + `Components`). Inspect `MatchScores.Overall >= 0.85` and `ParsedQuery` to detect `AddressNumberCorrected`. |
| **Coordinates to street address** | `ReverseGeocode` | Pass `QueryPosition: [lng, lat]`. |
| **Free-text POI or business search** | `SearchText` | Supports `QueryText`, `BiasPosition: [lng, lat]` or `Filter.BoundingBox`, and `Filter.IncludeCategories`. |
| **Proximity POI search around a point** | `SearchNearby` | Supports `QueryPosition: [lng, lat]`, `MaxRadius` (meters), and `Filter.IncludeCategories` (e.g., `["restaurant", "coffee_shop", "electric_vehicle_charging_station"]`). |
| **Named landmark proximity search** ("coffee near Space Needle") | `Geocode` $\rightarrow$ `SearchNearby` | **Two-Step Rule**: First resolve the landmark name to `[lng, lat]` via `Geocode` (or MCP `geocode`), then pass those coordinates to `SearchNearby` (or MCP `search_nearby`). |

### FinOps & Compliance Guardrails for Places V2

- **`AdditionalFeatures` SKU Tier Escalation**:
  - Omitting `AdditionalFeatures` bills at the **Core** tier (~4x cheaper).
  - Requesting `AdditionalFeatures: ["Phonemes"]` stays in the Core/Base tier.
  - Requesting `AdditionalFeatures: ["Contact", "OpeningHours", "TimeZone", "Access"]` upgrades the call to the **Advanced** pricing tier. Only request `Contact` or `OpeningHours` when displaying business details on a selected place card.
- **`IntendedUse` Data Storage Compliance**:
  - Default is `IntendedUse: "SingleUse"` (ephemeral display or immediate in-flight routing).
  - If you persist geocoded coordinates, `PlaceId`s, or standardized addresses into DynamoDB, PostgreSQL/PostGIS, OpenSearch, or S3 cache tables beyond transient caching, you **must** pass `IntendedUse: "Storage"` to comply with AWS Location Service terms.

### Address Autocomplete + `GetPlace` Pattern (TypeScript)

```typescript
import {
  GeoPlacesClient,
  AutocompleteCommand,
  GetPlaceCommand,
} from "@aws-sdk/client-geo-places";

const placesClient = new GeoPlacesClient({ region: "us-east-1" });

// Step 1: Type-ahead predictions as user types
export async function suggestAddresses(partialAddress: string, userLngLat?: [number, number]) {
  const res = await placesClient.send(
    new AutocompleteCommand({
      QueryText: partialAddress,
      MaxResults: 5,
      BiasPosition: userLngLat, // [lng, lat]
      Filter: { IncludeCountries: ["USA", "CAN"] },
      Key: process.env.LOCATION_API_KEY,
    })
  );

  return (res.ResultItems ?? []).map((item) => ({
    placeId: item.PlaceId!,
    // CRITICAL: Always display Address.Label, never item.Title!
    displayText: item.Address?.Label ?? item.Title ?? "",
    highlights: item.Highlights?.Address?.Label ?? [],
  }));
}

// Step 2: Resolve full structured address & coordinates when user selects a suggestion
export async function resolveSelectedAddress(placeId: string) {
  const place = await placesClient.send(
    new GetPlaceCommand({
      PlaceId: placeId,
      IntendedUse: "SingleUse", // Set to "Storage" if saving to database
      // Omit AdditionalFeatures to stay on Core pricing tier
      Key: process.env.LOCATION_API_KEY,
    })
  );

  return {
    placeId: place.PlaceId,
    position: place.Position as [number, number], // [lng, lat]
    label: place.Address?.Label,
    streetNumber: place.Address?.AddressNumber,
    street: place.Address?.Street,
    city: place.Address?.Locality,
    stateCode: place.Address?.Region?.Code, // Nested object: Region.Code, NOT flat string
    postalCode: place.Address?.PostalCode,
    countryCode: place.Address?.Country?.Code2, // Nested object: Country.Code2
  };
}
```

---

## 3. Bulk Postal Address Verification (`location:StartJob` `ValidateAddress`)

### When to Use `StartJob` vs. Synchronous `Geocode`

| Requirement | Recommended API | Why |
|---|---|---|
| Single interactive checkout address check | `geo-places:Geocode` (`MatchScores`) | Synchronous (<100ms), supports 200+ countries, checks `MatchScores.Overall` and `AddressNumberCorrected`. |
| Bulk CRM/ERP hygiene, postal deliverability verdict (`Mailable` / `Locatable`), standardized postal output | `location:StartJob` (`Action: "ValidateAddress"`) | Asynchronous batch job over S3 Parquet files; provides official postal-authority validation (`ValidationGranularity`, `StatusDetail`). |

### Mandatory Constraints for `StartJob` (`ValidateAddress`)

1. **Country Coverage**: Only **US, CA, UK (GB), and AU** are supported. Addresses in other countries must use `geo-places:Geocode`.
2. **S3 Bucket Versioning & Same Region**: Both the input S3 bucket and output S3 bucket **must** reside in the same AWS Region as the `StartJob` call and **must have S3 Versioning enabled**.
3. **Parquet Input Schema**: Input files must be Apache Parquet (`.parquet`) objects in the input S3 prefix.
4. **Execution Role Trust Policy**: The `ExecutionRoleArn` passed to `StartJob` must trust `geo.amazonaws.com` and grant `s3:GetObject`, `s3:GetObjectVersion`, `s3:ListBucket` on the input prefix and `s3:PutObject` on the output prefix.

```typescript
import {
  LocationClient,
  StartJobCommand,
  GetJobCommand,
} from "@aws-sdk/client-location";

const locationClient = new LocationClient({ region: "us-east-1" });

export async function runBulkAddressValidationJob(params: {
  inputBucket: string;
  inputPrefix: string;
  outputBucket: string;
  outputPrefix: string;
  executionRoleArn: string;
}) {
  const started = await locationClient.send(
    new StartJobCommand({
      Action: "ValidateAddress",
      ActionOptions: {
        ValidateAddress: {
          AdditionalFeatures: ["Position", "StandardizedAddress"],
        },
      },
      ExecutionRoleArn: params.executionRoleArn,
      InputOptions: {
        Location: `s3://${params.inputBucket}/${params.inputPrefix}`,
        Format: "Parquet",
      },
      OutputOptions: {
        Location: `s3://${params.outputBucket}/${params.outputPrefix}`,
        Format: "Parquet",
      },
    })
  );

  // Poll GetJobCommand({ JobId: started.JobId }) until Status === "Completed" | "Failed"
  return started.JobId!;
}
```

---

## 4. Routes V2 (`geo-routes`) Complete Capability Matrix

| Operation | SDK Command | Primary Use Case & Mandatory Parameters |
|---|---|---|
| **Turn-by-Turn Routing** | `CalculateRoutesCommand` | Point-to-point or multi-stop routes. Set `LegGeometryFormat: "Simple"` to get a `[lng, lat][]` array directly for MapLibre GeoJSON `LineString` (avoids flexpolyline decoding). Supports `TravelMode: "Car" \| "Truck" \| "Pedestrian" \| "Scooter"`, `Avoid: { Tolls, Ferries, DirtRoads }`, and `Tolls: { Currency: "USD" }`. |
| **Origin-Destination Matrix** | `CalculateRouteMatrixCommand` | $N \times M$ travel durations and distances. **Mandatory**: Must provide `RoutingBoundary` (`AutoCircle: { Margin: 10000 }` or explicit `Circle` / `Geometry`), or use `AllowUnboundedDestination: true` (bounded to max 100 cells vs. 625 bounded cells). |
| **Reachability / Drive-Time Areas** | `CalculateIsolinesCommand` | Isochrone (`Thresholds.Time` in seconds) or isodistance (`Thresholds.Distance` in meters) polygons. Set `IsolineGeometryFormat: "Simple"` to render directly as a MapLibre `Polygon` layer. |
| **Traveling Salesperson (TSP)** | `OptimizeWaypointsCommand` | Optimal stop ordering for up to 50 waypoints (`Origin`, `Destination`, `Waypoints[]`), supporting `AccessHours` delivery windows and `ServiceTime`. |
| **GPS Trace Map-Matching** | `SnapToRoadsCommand` | Snaps noisy raw GPS telemetry (`TracePoints: [{ Position: [lng, lat], Timestamp }]`) onto the road network and returns interpolated road geometry + speed limits. |

### Commercial Truck Routing with Toll Cost Calculation

```typescript
import { GeoRoutesClient, CalculateRoutesCommand } from "@aws-sdk/client-geo-routes";

const routesClient = new GeoRoutesClient({ region: "us-east-1" });

const routeResponse = await routesClient.send(
  new CalculateRoutesCommand({
    Origin: [-74.006, 40.7128], // [lng, lat] New York
    Destination: [-75.1652, 39.9526], // [lng, lat] Philadelphia
    TravelMode: "Truck",
    TravelModeOptions: {
      Truck: {
        GrossWeight: 36000, // kg
        Height: 410, // cm
        Width: 259, // cm
        Length: 1615, // cm
        AxleCount: 5,
        HazardousCargos: ["Flammable"], // Routes around hazmat-restricted tunnels/bridges
      },
    },
    LegGeometryFormat: "Simple", // Returns LineString [[lng, lat], ...]
    LegAdditionalFeatures: ["Summary", "Tolls", "TravelStepInstructions"],
    Tolls: {
      AllTransponders: true,
      Currency: "USD",
    },
    DepartNow: true,
    Key: process.env.LOCATION_API_KEY,
  })
);
```
