---
name: location-migration-specialist
description: End-to-end migration playbook for moving from Google Maps Platform (Web JS, Android Kotlin, iOS Swift, Backend REST), Mapbox GL/APIs, or Legacy Amazon Location Service V1 (`PlaceIndex`, `RouteCalculator`, `Map`) to Resourceless Amazon Location Service V2 (`geo-maps`, `geo-places`, `geo-routes`, MapLibre GL). Use when refactoring third-party map components, converting `[lat, lng]` coordinates to GeoJSON `[lng, lat]`, mapping Google/Mapbox/V1 response schemas to V2, or eliminating deprecated V1 AWS Location resources.
---

# Amazon Location Service Migration Playbook (Google Maps, Mapbox & Legacy AWS Location V1 $\rightarrow$ V2)

## 1. Universal Coordinate & Schema Guardrails

Before migrating any map, geocoder, or router call, enforce these three invariants across the entire codebase:

1. **Coordinate Inversion (`[lat, lng]` $\rightarrow$ `[lng, lat]`)**:
   - Google Maps (`{ lat: 47.6062, lng: -122.3321 }`) and Leaflet (`[47.6062, -122.3321]`) use **`[latitude, longitude]`**.
   - Amazon Location Service V2 (`geo-maps`, `geo-places`, `geo-routes`), Trackers/Geofences (`location`), and MapLibre GL use **`[longitude, latitude]`** (`[-122.3321, 47.6062]`).
2. **Display Label Selection (`Address.Label` vs. `Title`)**:
   - When migrating `google.maps.places.Autocomplete` or Mapbox Search Box, always display `item.Address?.Label` in dropdowns—never `item.Title` (which can invert house number and street name).
3. **Nested Address Components**:
   - In `geo-places`, `Address.Region` (`{ Code, Name }`) and `Address.Country` (`{ Code2, Code3, Name }`) are nested objects, unlike V1 where `Address.Region` and `Address.Country` were flat strings.

```typescript
// Type-safe coordinate converter from Google Maps LatLngLiteral to Amazon Location [lng, lat]
export function toLngLat(
  input: { lat: number; lng: number } | [number, number]
): [number, number] {
  if (Array.isArray(input)) {
    const [first, second] = input;
    // Detect obvious [lat, lng] inversion if second coordinate is outside [-90, 90]
    if (Math.abs(second) > 90 && Math.abs(first) <= 90) {
      return [second, first];
    }
    return [first, second];
  }
  return [input.lng, input.lat];
}
```

---

## 2. Google Maps Platform $\rightarrow$ Amazon Location Service V2 Mapping

| Google Maps Platform API | Amazon Location Service V2 Replacement | Key Parameter & Response Mapping |
|---|---|---|
| `google.maps.Map` (JS) | **MapLibre GL JS v5** (`maplibregl.Map`) + `geo-maps` V2 style URL | `center: { lat, lng }` $\rightarrow$ `center: [lng, lat]`; set `validateStyle: false`; pass `https://maps.geo.<region>.amazonaws.com/v2/styles/Standard/descriptor?key=<apiKey>` |
| `@aws/amazon-location-migration-sdk` | Rapid Phase 1 drop-in shim for `google.maps.*` web classes | Wraps `Map`, `Marker`, `InfoWindow`, `Autocomplete`, `DirectionsService` over Amazon Location V2; migrate to native MapLibre GL + `@aws-sdk/client-geo-*` in Phase 2 for smaller bundle size & 3D features. |
| Geocoding API (`/maps/api/geocode/json`) | `geo-places:Geocode` / `geo-places:ReverseGeocode` | `results[0].geometry.location` (`{lat, lng}`) $\rightarrow$ `ResultItems[0].Position` (`[lng, lat]`); `formatted_address` $\rightarrow$ `Address.Label`; inspect `MatchScores.Overall`. |
| Places Autocomplete | `geo-places:Autocomplete` (addresses) or `geo-places:Suggest` (POIs) | Follow up user selection with `geo-places:GetPlace({ PlaceId })`. |
| Places Text Search / Nearby Search | `geo-places:SearchText` / `geo-places:SearchNearby` | `includedTypes: ["restaurant"]` $\rightarrow$ `Filter: { IncludeCategories: ["restaurant"] }`; only request `AdditionalFeatures: ["Contact", "OpeningHours"]` when needed (Advanced tier). |
| Routes API `computeRoutes` | `geo-routes:CalculateRoutes` | `travelMode: "DRIVE"` $\rightarrow$ `TravelMode: "Car"`; set `LegGeometryFormat: "Simple"` for GeoJSON `[lng, lat][]` coordinates; supports `Tolls: { Currency: "USD" }`. |
| Routes API `computeRouteMatrix` | `geo-routes:CalculateRouteMatrix` | Requires mandatory `RoutingBoundary` (`{ AutoCircle: { Margin: 10000 } }`). |
| Roads API `snapToRoads` | `geo-routes:SnapToRoads` | Pass `TracePoints: [{ Position: [lng, lat], Timestamp }]`. |
| Address Validation API | `location:StartJob` (`Action: "ValidateAddress"`) for bulk US/CA/UK/AU; `geo-places:Geocode` (`MatchScores`) for single synchronous lookup | `StartJob` validates Parquet batches in S3 against official postal databases (`ValidationGranularity`, `Mailable`). |

### Android (Kotlin) & iOS (Swift) Migration Summary

- **Android**: Replace `com.google.android.gms:play-services-maps` (`SupportMapFragment`, `GoogleMap`, `LatLng(lat, lng)`) with **MapLibre Native for Android** (`org.maplibre.gl:android-sdk`, `MapView`, `LatLng(lat, lng)` in MapLibre Android SDK vs. `[lng, lat]` in AWS Kotlin SDK `aws.sdk.kotlin:geoplaces` / `georoutes`).
- **iOS**: Replace `GoogleMaps` (`GMSMapView`, `CLLocationCoordinate2D`) with **MapLibre Native for iOS** (`MapLibre`, `MLNMapView`) and the **AWS SDK for Swift** (`AWSGeoPlaces`, `AWSGeoRoutes`).

---

## 3. Mapbox $\rightarrow$ Amazon Location Service V2 Mapping

Because MapLibre GL JS forked directly from Mapbox GL JS, migrating from Mapbox to Amazon Location Service V2 requires minimal UI code changes:

1. **Swap Package Imports**:
   - Replace `import mapboxgl from "mapbox-gl"` and `"mapbox-gl/dist/mapbox-gl.css"` with `import maplibregl from "maplibre-gl"` and `"maplibre-gl/dist/maplibre-gl.css"`.
2. **Replace `mapbox://styles/...` Style URL and `mapboxgl.accessToken`**:
   - Remove `mapboxgl.accessToken = "pk.ey..."`.
   - Pass the Amazon Location V2 style URL:
     `https://maps.geo.${region}.amazonaws.com/v2/styles/Standard/descriptor?key=${apiKey}&color-scheme=Light`
   - Add `validateStyle: false` to the `maplibregl.Map` constructor.
3. **Replace Mapbox Geocoding & Directions REST Calls**:
   - Mapbox Geocoding v6 (`/search/geocode/v6/forward`) $\rightarrow$ `GeoPlacesClient` (`GeocodeCommand` / `AutocompleteCommand`).
   - Mapbox Search Box (`/search/searchbox/v1/suggest`) $\rightarrow$ `GeoPlacesClient` (`SuggestCommand` / `SearchTextCommand`).
   - Mapbox Directions v5 (`/directions/v5/mapbox/driving`) $\rightarrow$ `GeoRoutesClient` (`CalculateRoutesCommand` with `LegGeometryFormat: "Simple"`).
   - Mapbox Isochrone v1 (`/isochrone/v1/mapbox/driving`) $\rightarrow$ `GeoRoutesClient` (`CalculateIsolinesCommand` with `IsolineGeometryFormat: "Simple"`).
   - Mapbox Matrix v1 (`/directions-matrix/v1/mapbox/driving`) $\rightarrow$ `GeoRoutesClient` (`CalculateRouteMatrixCommand` with `RoutingBoundary`).
   - Mapbox Map Matching v5 (`/matching/v5/mapbox/driving`) $\rightarrow$ `GeoRoutesClient` (`SnapToRoadsCommand`).

---

## 4. Legacy Amazon Location Service V1 $\rightarrow$ Resourceless V2 Migration

### Step 1: Replace V1 SDK Operations (`@aws-sdk/client-location`) with V2 (`@aws-sdk/client-geo-*`)

| Legacy V1 (`@aws-sdk/client-location`) | Resourceless V2 Replacement | V2 Migration Changes |
|---|---|---|
| `SearchPlaceIndexForTextCommand` (`IndexName`) | `GeoPlacesClient` $\rightarrow$ `SearchTextCommand` or `GeocodeCommand` | Remove `IndexName`. Use `GeocodeCommand` for street addresses and `SearchTextCommand` for POIs. |
| `SearchPlaceIndexForPositionCommand` (`IndexName`) | `GeoPlacesClient` $\rightarrow$ `ReverseGeocodeCommand` | Remove `IndexName`; rename `Position` $\rightarrow$ `QueryPosition`. |
| `SearchPlaceIndexForSuggestionsCommand` (`IndexName`) | `GeoPlacesClient` $\rightarrow$ `AutocompleteCommand` or `SuggestCommand` | Remove `IndexName`; display `Address.Label`. |
| `GetPlaceCommand` (`IndexName`, `PlaceId`) | `GeoPlacesClient` $\rightarrow$ `GetPlaceCommand` (`PlaceId`) | Remove `IndexName`; access nested `Address.Region.Code` and `Address.Country.Code2`. |
| `CalculateRouteCommand` (`CalculatorName`) | `GeoRoutesClient` $\rightarrow$ `CalculateRoutesCommand` | Remove `CalculatorName`; rename `DeparturePosition` $\rightarrow$ `Origin`, `DestinationPosition` $\rightarrow$ `Destination`; set `LegGeometryFormat: "Simple"`. |
| `CalculateRouteMatrixCommand` (`CalculatorName`) | `GeoRoutesClient` $\rightarrow$ `CalculateRouteMatrixCommand` | Remove `CalculatorName`; rename `DeparturePositions` $\rightarrow$ `Origins: [{ Position }]`, `DestinationPositions` $\rightarrow$ `Destinations: [{ Position }]`; **add mandatory `RoutingBoundary`**. |
| `GetMapStyleDescriptorCommand` (`MapName`) | Direct V2 Style URL (`geo-maps`) | Remove `MapName`; pass `https://maps.geo.<region>.amazonaws.com/v2/styles/<Style>/descriptor?key=<apiKey>` directly to MapLibre. |

### Step 2: Upgrade IAM Policies & API Key Restrictions

Replace legacy `geo:*` V1 permissions with resourceless V2 permissions:
- Replace `geo:GetMapStyleDescriptor`, `geo:GetMapTile`, `geo:GetMapSprites`, `geo:GetMapGlyphs` on `arn:aws:geo:<region>:<account>:map/*` $\rightarrow$ `geo-maps:GetTile`, `geo-maps:GetStaticMap`, `geo-maps:GetStyleDescriptor`, `geo-maps:GetSprites`, `geo-maps:GetGlyphs` on `arn:aws:geo-maps:<region>::provider/default`.
- Replace `geo:SearchPlaceIndex*`, `geo:GetPlace` on `arn:aws:geo:<region>:<account>:place-index/*` $\rightarrow$ `geo-places:Geocode`, `geo-places:ReverseGeocode`, `geo-places:SearchText`, `geo-places:SearchNearby`, `geo-places:Autocomplete`, `geo-places:Suggest`, `geo-places:GetPlace` on `arn:aws:geo-places:<region>::provider/default`.
- Replace `geo:CalculateRoute*` on `arn:aws:geo:<region>:<account>:route-calculator/*` $\rightarrow$ `geo-routes:CalculateRoutes`, `geo-routes:CalculateRouteMatrix`, `geo-routes:CalculateIsolines`, `geo-routes:OptimizeWaypoints`, `geo-routes:SnapToRoads` on `arn:aws:geo-routes:<region>::provider/default`.

### Step 3: Decommission V1 IaC Resources Safely

Once application traffic is cut over to V2 resourceless endpoints, remove `AWS::Location::Map`, `AWS::Location::PlaceIndex`, and `AWS::Location::RouteCalculator` from CDK, CloudFormation, or Terraform stacks. Keep stateful `AWS::Location::Tracker`, `AWS::Location::GeofenceCollection`, `AWS::Location::TrackerConsumer`, and `AWS::Location::APIKey` resources.
