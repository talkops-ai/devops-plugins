---
name: amazon-location-service
description: Integrates Amazon Location Service APIs for AWS applications. Use this skill when users want to add maps (interactive MapLibre or static images); geocode addresses to coordinates or reverse geocode coordinates to addresses; calculate routes, travel times, or service areas; find places and businesses through text search, nearby search, or autocomplete suggestions; retrieve detailed place information including hours, contacts, and addresses; monitor geographical boundaries with geofences; or track device locations. Covers authentication, SDK integration, and all Amazon Location Service capabilities.
license: Apache-2.0
metadata:
  author: aws-geospatial
  version: "1.1"
---

## Overview

Amazon Location Service provides geospatial APIs for maps, geocoding, routing, places search, geofencing, and tracking. Prefer the bundled JavaScript client (@aws/amazon-location-client) for web development and use resourceless API operations to avoid managing AWS resources.

## When to Use This Skill

Use this skill when:

- Building location-aware web or mobile applications
- Working with Amazon Location Service projects
- Implementing maps, geocoding, routing, or places search
- Adding geofencing or device tracking functionality
- Integrating geospatial features into AWS applications

Do NOT use this skill for:

- Google Maps, Mapbox, or Leaflet-with-OSM projects (unless migrating to Amazon Location)
- Generic GIS operations without AWS context
- Non-AWS geospatial services

## Amazon Location Service API Overview

**Places** (SDK: geo-places, JS: @aws-sdk/client-geo-places)

- Geocode (Forward/Reverse): Convert addresses to coordinates and vice versa
- Search (Text/Nearby): Find points of interest with contact and hours info
- Autocomplete: Predict addresses based on user input
- Suggest: Predict places and points of interest based on partial or misspelled user input
- Get Place: Retrieve place details by place ID

**Jobs** (SDK: location, JS: @aws-sdk/client-location)

- Address Validation: Verify and standardize addresses in bulk with the asynchronous Jobs API (StartJob with Action `ValidateAddress`, then GetJob/ListJobs/CancelJob). It adds what Geocode lacks — a postal-authority verdict (ValidationGranularity, Mailable/Locatable, per-component StatusDetail), not just coordinates. Coverage is US, CA, UK, and AU only; for other countries use Geocode.

**Maps** (SDK: geo-maps, JS: @aws-sdk/client-geo-maps)

- Dynamic Maps: Interactive maps using tiles with [MapLibre](https://maplibre.org/) rendering
- Static Maps: Pre-rendered, non-interactive map images, good for including an image into a web page, or for thumbnail images

**Routes** (SDK: geo-routes, JS: @aws-sdk/client-geo-routes)

- Route calculation with traffic and distance estimation
- Service area/isoline creation
- Matrix calculations for multiple origins/destinations
- GPS trace alignment to road segments
- Route optimization (traveling salesman problem)

**Geofences & Trackers** (SDK: location, JS: @aws-sdk/client-location)

- Geofences: Detect entry/exit from geographical boundaries
- Trackers: Current and historical device location tracking

**API Keys** (SDK: location, JS: @aws-sdk/client-location)

- API Keys: Grant access to public applications without exposing AWS credentials

## Common Mistakes

Avoid these frequent errors:

1. **Using `Title` instead of `Address.Label` for display**: In Autocomplete results, always display `Address.Label`. The `Title` field may show components in reverse order and is not suitable for user-facing text.

2. **Using GetStyleDescriptor API for map initialization**: MUST use direct URL passing to MapLibre (`https://maps.geo.{region}.amazonaws.com/v2/styles/Standard/descriptor?key={apiKey}`) instead of making GetStyleDescriptor API calls. The direct URL method is required for proper map rendering.

3. **Forgetting `validateStyle: false` in MapLibre config**: Always set `validateStyle: false` in the MapLibre Map constructor for faster map load times with Amazon Location styles.

4. **Mixing resource-based and resourceless operations**: When possible, prefer resourceless operations (direct API calls without pre-created resources) for simpler deployment and permissions.

5. **Inconsistent API operation naming**: Use the format `service:Operation` when referencing APIs (e.g., `geo-places:Geocode`, `geo-maps:GetStyleDescriptor`). SDK clients use `@aws-sdk/client-*` format.

6. **Not handling nested Address objects correctly**: The Address object from GetPlace contains nested objects (`Region.Code`, `Region.Name`, `Country.Code2`, etc.), not flat strings. Access nested properties correctly.

7. **Wrong action names in API Key permissions**: API key `AllowActions` use `geo-maps:`, `geo-places:`, `geo-routes:` prefixes (e.g., `geo-places:Geocode`, `geo-routes:CalculateRoutes`). Do NOT use SDK client names (`@aws-sdk/client-geo-places`) or IAM-style actions. See the Authentication and Permissions section for the complete list.

8. **Synthesizing deprecated V1 resources in IaC**: Never create `AWS::Location::Map`, `AWS::Location::PlaceIndex`, or `AWS::Location::RouteCalculator` in CDK, CloudFormation, Terraform, or Amplify Gen 2. Maps, Places, and Routes V2 are resourceless (`provider/default`); only provision `AWS::Location::APIKey`, `AWS::Location::Tracker`, `AWS::Location::GeofenceCollection`, and `AWS::Location::TrackerConsumer`.

9. **Reversing coordinates (`[lat, lng]` instead of `[lng, lat]`)**: Every Amazon Location Service API and MapLibre GL JS expects `[longitude, latitude]` (GeoJSON order). Passing `[latitude, longitude]` places North American coordinates in Antarctica or the Indian Ocean.

10. **Missing `AssociateTrackerConsumer` or `KmsKeyEnableGeospatialQueries: true`**: Creating a Tracker and a GeofenceCollection without linking them via `AssociateTrackerConsumer` (`AWS::Location::TrackerConsumer`) results in zero geofence evaluations. Enabling a customer-managed KMS key (`KmsKeyId`) on a Tracker without setting `KmsKeyEnableGeospatialQueries: true` breaks polygon-filtered `ListDevicePositions` queries.

## Defaults

Use these default choices unless the user explicitly requests otherwise:

- **JavaScript SDK**: Bundled client (CDN) for browser-only apps; npm modular SDKs (@aws-sdk/client-geo-*) for React and build tool apps
- **API operations**: Resourceless for Maps/Places/Routes (Geofencing/Tracking always require pre-created resources)
- **Authentication**: API Key for Maps/Places/Routes; Cognito for Geofencing/Tracking
- **Map style**: Standard
- **Coordinate format**: [longitude, latitude] (GeoJSON order)

Override: User can specify "use Cognito for Maps/Places/Routes" or "use bundled client for React".

## API Selection Guidance

Choose the right API for your use case:

### Address Input (interactive forms)

- **Autocomplete** → Type-ahead in address forms (partial input: "123 Main")
- **GetPlace** → Get full details after user selects autocomplete result (by PlaceId)
- **Geocode** → Resolve a complete user-typed address to coordinates. Returns coordinates, a matched label, and match quality (`MatchScores` overall + per-component, `AddressNumberCorrected`) synchronously in one call — but no postal-deliverability verdict or standardized output.

### Address Validation (verify & standardize)

- **StartJob (Action `ValidateAddress`)** → Verify and standardize addresses in bulk against authoritative postal data; async Jobs API with Parquet input/output in Amazon S3. **Coverage: US, CA, UK, AU only; for other countries use Geocode.**
- **GetJob / ListJobs / CancelJob** → Track, enumerate, and cancel validation jobs
- Choose the Jobs API when you need a postal-authority verdict (ValidationGranularity, Mailable/Locatable, per-component StatusDetail) or bulk throughput. For a single ad-hoc check of whether one address resolves and how well it matched, the synchronous Geocode `MatchScores` is the right tool — do not stand up a job. See the address-verification reference.

### Finding Locations

- **SearchText** → General text search ("pizza near Seattle")
- **SearchNearby** → Find places near a coordinate (restaurants within 5km)
- **Suggest** → Predict places/POIs from partial or misspelled input (note: V2 `/suggest` does not support server-side category filtering; use `SearchNearby` with `Filter.IncludeCategories` when category filtering is required)
- **Autocomplete** → Address-specific predictions (not for general POI search)

### Geocoding

- **Geocode (Forward)** → Address string → Coordinates
- **ReverseGeocode** → Coordinates → Address

### Maps

- **Dynamic Maps (tiles + MapLibre)** → Interactive maps requiring pan, zoom, markers
- **Static Maps (image)** → Non-interactive map images for thumbnails or email

### Routing

- **CalculateRoutes** → Single route between origin and destination
- **CalculateRouteMatrix** → Multiple origins/destinations travel times (requires mandatory `RoutingBoundary`)
- **CalculateIsolines** → Service areas (all locations reachable within time/distance)
- **OptimizeWaypoints** → Optimal stop sequence (Traveling Salesperson Problem)
- **SnapToRoads** → Align noisy GPS traces to the physical road network

## LLM Context Files

When you need detailed API parameter specifications or service capabilities not covered in the reference files, fetch these llms.txt resources:

- **Developer Guide**: https://docs.aws.amazon.com/location/latest/developerguide/llms.txt
- **API Reference**: https://docs.aws.amazon.com/location/latest/APIReference/llms.txt

## Key Guidance for Better Recommendations

### Prefer the Bundled JavaScript Client for Web Development

For convenient web application development, Amazon Location Service provides a bundled JavaScript client that simplifies integration and provides optimized functionality without custom bundling. This bundled client includes all libraries required to build client side web applications with Amazon Location Service.

**Features included in the bundled client:**

- Enables direct pre-bundled dependency inclusion without custom bundle / build
- Simplified authentication and API integration
- TypeScript support with comprehensive type definitions
- Support for all Amazon Location SDKs

**Included SDKs and Libraries:**

- @aws-sdk/client-geo-maps
- @aws-sdk/client-geo-places
- @aws-sdk/client-geo-routes
- @aws-sdk/client-location
- @aws-sdk/credential-providers
- https://github.com/aws-geospatial/amazon-location-utilities-auth-helper-js

**Resources:**

- NPM Package: [@aws/amazon-location-client](https://www.npmjs.com/package/@aws/amazon-location-client)
- GitHub Repository: [aws-geospatial/amazon-location-client-js](https://github.com/aws-geospatial/amazon-location-client-js)

### Prefer Resourceless Operations

Amazon Location Places, Maps and Routes services offer both resource-based and resourceless API operations. Resourceless operations are often simpler and more appropriate for many use cases.

**Resource-based operations** require you to:

- Create and configure Amazon Location Service resources (maps, place indexes, route calculators)
- Manage resource lifecycle and permissions
- Handle resource naming and organization

**Resourceless operations** allow you to:

- Make API calls directly without pre-creating resources
- Reduce deployment complexity
- Simplify IAM permissions and API Key permissions

### Authentication and Permissions

When discussing permissions for Amazon Location Places, Maps and Routes services, always include both IAM permissions and API Key permissions in your guidance. If the type of application being developed is clear, recommend the appropriate authorization tool as described below:

**IAM Permissions** - Recommended for server-side applications and AWS SDK usage:

- Used with AWS credentials (access keys, roles, etc.)
- Provide fine-grained access control
- Required for resource management operations

**API Key Permissions** - Alternative authentication method, especially useful for client-side applications or applications deployed to unauthenticated (public) users:

- Simplified authentication without exposing AWS credentials
- Can be configured with specific allowed operations
- Useful for web and mobile applications
- Supports both resource-based and resourceless operations
- Enables faster subsequent map loads through CDN caching

**API Key Action Names** - API keys use their own action naming convention. Do NOT use SDK client names or IAM action names — they will be rejected.

Resourceless API key actions (recommended):

| Service | AllowActions                                                                                                                                                                  | AllowResources                                |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| Maps    | `geo-maps:GetTile`, `geo-maps:GetStaticMap`, `geo-maps:GetStyleDescriptor`, `geo-maps:GetSprites`, `geo-maps:GetGlyphs`                                                       | `arn:aws:geo-maps:REGION::provider/default`   |
| Places  | `geo-places:Autocomplete`, `geo-places:Geocode`, `geo-places:ReverseGeocode`, `geo-places:SearchText`, `geo-places:SearchNearby`, `geo-places:Suggest`, `geo-places:GetPlace` | `arn:aws:geo-places:REGION::provider/default` |
| Routes  | `geo-routes:CalculateRoutes`, `geo-routes:CalculateRouteMatrix`, `geo-routes:CalculateIsolines`, `geo-routes:OptimizeWaypoints`, `geo-routes:SnapToRoads`                     | `arn:aws:geo-routes:REGION::provider/default` |

Do NOT use legacy `geo:` prefixed actions (e.g., `geo:GetMap*`, `geo:CalculateRoute`) — these are for pre-created resources only and will not work with resourceless APIs.

### LocationClient Setup

Geofencing and Tracking use `LocationClient` (`@aws-sdk/client-location`). These are **resource-based operations** — you MUST create resources (trackers, geofence collections) before using them.

```javascript
import { LocationClient } from "@aws-sdk/client-location";

// Server-side: uses IAM credentials from environment/role
const client = new LocationClient({ region: "us-east-1" });
```

```javascript
// Client-side: uses Amazon Cognito
import { LocationClient } from "@aws-sdk/client-location";
import { fromCognitoIdentityPool } from "@aws-sdk/credential-providers";

const client = new LocationClient({
  region: "us-east-1",
  credentials: fromCognitoIdentityPool({
    identityPoolId: "us-east-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    clientConfig: { region: "us-east-1" },
  }),
});
```

## MCP Server Integration

This plugin integrates two complementary MCP servers:

1. **Amazon Location Service MCP Server (`awslocation` — `awslabs.aws-location-mcp-server@latest`)**:
   - Provides 8 dedicated, latency-optimized tools backed by `boto3.client('geo-places')` and `boto3.client('geo-routes')`:
     - `geocode`, `reverse_geocode`, `search_places`, `search_nearby`, `search_places_open_now`, `get_place`, `calculate_route`, `optimize_waypoints`
   - **Two-Step Landmark Rule**: When searching near a named landmark ("coffee shops near the Space Needle"), first call `geocode` to resolve `[longitude, latitude]`, then pass `longitude` and `latitude` to `search_nearby`.
2. **AWS MCP Server (`aws-mcp`)**:
   - Provides AWS documentation search (`aws___search_documentation`, `aws___read_documentation`), regional availability checks (`aws___get_regional_availability`), Agent SOPs (`aws___retrieve_agent_sop`), and live AWS CLI execution (`aws___call_aws`).
   - Use `aws___call_aws` for V2 APIs not wrapped by `awslocation` (`aws geo-places autocomplete`, `aws geo-places suggest`, `aws geo-routes calculate-isolines`, `aws geo-routes calculate-route-matrix`, `aws geo-routes snap-to-roads`, `aws geo-maps get-static-map`) and all stateful `aws location` operations (API keys, trackers, geofence collections, address validation jobs).

## Additional Resources

- [Amazon Location Service Developer Guide](https://docs.aws.amazon.com/location/latest/developerguide/)
- [Amazon Location Service API Reference](https://docs.aws.amazon.com/location/latest/APIReference/)
- [Amazon Location Service Samples](https://github.com/aws-geospatial)

## Reference Files

Load these resources as needed for specific implementation guidance:

- [Address Input](./references/address-input.md) - Create effective address input forms for users with address type ahead completion improving input speed and accuracy
- [Address Verification](./references/address-verification.md) - Verify and standardize addresses in bulk against authoritative postal data using the asynchronous Jobs API (StartJob with Action ValidateAddress), before persisting to databases or taking downstream actions
- [Calculate Routes](./references/calculate-routes.md) - Calculate routes between locations with customizable travel options, route matrices, isolines, waypoint optimization, and road snapping
- [Device Tracking](./references/device-tracking.md) - Track device locations in real time, configure KMS geospatial encryption, ingest via AWS IoT Core MQTT rules, and query polygon-filtered position history
- [Dynamic Map Rendering](./references/dynamic-map.md) - Render dynamic vector maps with MapLibre GL, static map images with GeoJSON overlays, geopolitical views, and GrabMaps
- [Google Maps Migration (Android)](./references/google-migration-android.md) - Migrate Android application from Google Maps SDK for Android to Amazon Location Service
- [Google Maps Migration (iOS)](./references/google-migration-ios.md) - Migrate iOS application from Google Maps SDK for iOS to Amazon Location Service
- [Google Maps Migration (JavaScript)](./references/google-migration-web.md) - Migrate JavaScript web application from Google Maps API to Amazon Location Service
- [Migration, IaC, and FinOps](./references/migration-and-finops.md) - Migrate from Google Maps, Mapbox, or Legacy AWS Location V1 to V2; synthesize CDK, Terraform, and Amplify Gen 2 IaC; and optimize Places/Routes/Tracker costs and RPS quotas
- [Places Search](./references/places-search.md) - Search for places or points of interest with category filters, open-now checks, and two-step landmark geocoding
- [Web JavaScript](./references/web-javascript.md) - Integrate Amazon Location services into web browser applications
- [Zone Alerts](./references/zone-alerts.md) - Monitor device positions against geographic boundaries, bind trackers via AssociateTrackerConsumer, and react to EventBridge ENTER/EXIT/UPDATE alerts
