---
name: location-tracking-geofencing-iot
description: Stateful fleet tracking, geofencing, location integrity verification, predictive ETA breaching, and IoT ingestion architectures using `@aws-sdk/client-location` (`location`). Use when provisioning or operating Trackers (`PositionFiltering`, CMK `KmsKeyEnableGeospatialQueries`), Geofence Collections (`Circle`, `Polygon`, `MultiPolygon`, 100k-vertex `Geobuf`), binding Trackers via `AssociateTrackerConsumer`, forecasting geofence events (`ForecastGeofenceEvents`), detecting GPS spoofing (`VerifyDevicePosition`), or wiring AWS IoT Core MQTT `LocationAction` and EventBridge `ENTER`/`EXIT` rules.
---

# Amazon Location Service: Stateful Tracking, Geofencing, Location Integrity & IoT Ingestion

Unlike Maps, Places, and Routes V2 (which are resourceless), **Trackers** and **Geofence Collections** are **stateful AWS resources** managed via `@aws-sdk/client-location` (`boto3.client('location')`, AWS CLI `aws location`) and authenticated via **IAM SigV4** or **Amazon Cognito Identity Pools** (never public API Keys).

---

## 1. Tracker Architecture & Filtering Modes

### Choosing `PositionFiltering` (Cost & Storage Control)

Every device position ingested via `BatchUpdateDevicePosition` is evaluated against linked Geofence Collections **only if it survives the Tracker's `PositionFiltering` gate**:

| Mode | Behavior | Best For | FinOps Impact |
|---|---|---|---|
| **`AccuracyBased`** *(Recommended for Mobile)* | Ignores updates where moved distance is less than the reported GPS `Accuracy.Horizontal` jitter radius. | Delivery apps, field service phones, consumer mobile apps with indoor/urban canyon GPS drift. | Prevents false `ENTER`/`EXIT` geofence flapping and cuts redundant storage/evaluation charges by **60–80%**. |
| **`DistanceBased`** | Ignores updates where the device moved `< 30 meters` (100 ft) since the last stored position. | Commercial trucking, long-haul logistics, rail/marine assets. | Ideal when stationary vehicles transmit periodic heartbeats. |
| **`TimeBased`** | Evaluates and stores at most 1 position per **30 seconds** per `DeviceId`. | High-frequency telemetry streams where sub-minute breadcrumbs are unnecessary. | Caps downstream geofence evaluation rate per device at 2/minute. |

### Customer-Managed KMS Encryption (`KmsKeyEnableGeospatialQueries`)

When encrypting a Tracker with a Customer-Managed KMS Key (`KmsKeyId`):
- By default, KMS encryption disables spatial indexing, causing `ListDevicePositions` with `FilterGeometry: { Polygon: [...] }` to fail.
- **Mandatory Guardrail**: Always set **`KmsKeyEnableGeospatialQueries: true`** when creating a KMS-encrypted Tracker if your application queries devices inside a bounding box or polygon.

### `EventBridgeEnabled` vs. Geofence Events

- **Geofence `ENTER` / `EXIT` events** (`detail-type: "Location Geofence Event"`) are emitted to Amazon EventBridge **automatically** whenever a Tracker is linked to a Geofence Collection via `AssociateTrackerConsumer`.
- Setting `EventBridgeEnabled: true` on `CreateTracker` / `UpdateTracker` emits **raw position stream events** (`detail-type: "Location Device Position Event"`, `EventType: "UPDATE"`) on every stored position update. Only enable `EventBridgeEnabled: true` when downstream consumers need every raw coordinate update on EventBridge.

---

## 2. Geofence Collections & Geometry Limits

### Supported Geofence Geometry Types

| Geometry Type | Vertex / Size Limits | Winding & Format Rules |
|---|---|---|
| **`Circle`** | `Center: [lng, lat]`, `Radius` in meters ($>0$) | Simplest & fastest evaluation for radial zones around stores or depots. |
| **`Polygon`** | Up to **1,000 vertices** per geofence across all rings | Outer ring **must** be wound **counter-clockwise**; interior holes **clockwise**; first and last `[lng, lat]` pair must match (closed ring). |
| **`MultiPolygon`** | Up to **1,000 vertices** total | Multiple disjoint polygons grouped under a single `GeofenceId`. |
| **`Geobuf`** | Up to **100,000 vertices**, max **25,000 rings** | Base64/binary Protocol Buffer (`Geobuf`) encoding of a single GeoJSON `Feature` (`Polygon` or `MultiPolygon`). Mandatory for high-resolution municipal boundaries, coastlines, or parcel polygons exceeding 1,000 vertices. |

### Mandatory Tracker-to-Geofence Binding (`AssociateTrackerConsumer`)

> **Critical Pitfall**: Creating a Tracker and a Geofence Collection in the same stack does **nothing** on its own. You **must** call `AssociateTrackerConsumer` (or declare `AWS::Location::TrackerConsumer` / `aws_location_tracker_association`) passing the Geofence Collection ARN as `ConsumerArn`.

```typescript
import {
  LocationClient,
  AssociateTrackerConsumerCommand,
  BatchUpdateDevicePositionCommand,
} from "@aws-sdk/client-location";

const locationClient = new LocationClient({ region: "us-east-1" });

// 1. Bind Tracker to Geofence Collection (idempotent)
await locationClient.send(
  new AssociateTrackerConsumerCommand({
    TrackerName: "prod-fleet-tracker",
    ConsumerArn: "arn:aws:geo:us-east-1:111122223333:geofence-collection/prod-delivery-zones",
  })
);

// 2. Ingest batch telemetry (up to 10 devices per BatchUpdateDevicePosition call)
await locationClient.send(
  new BatchUpdateDevicePositionCommand({
    TrackerName: "prod-fleet-tracker",
    Updates: [
      {
        DeviceId: "truck-042",
        Position: [-122.3321, 47.6062], // [longitude, latitude]
        SampleTime: new Date(),
        Accuracy: { Horizontal: 4.5 }, // meters (used by AccuracyBased filtering)
        PositionProperties: {
          orderId: "ORD-9981",
          driverId: "DRV-204",
        },
      },
    ],
  })
);
```

---

## 3. Predictive Geofencing (`ForecastGeofenceEvents`)

Use `ForecastGeofenceEventsCommand` to predict upcoming `ENTER` or `EXIT` transitions **before** a moving vehicle crosses the boundary (e.g., triggering curbside pickup preparation 10 minutes before arrival):

```typescript
import { LocationClient, ForecastGeofenceEventsCommand } from "@aws-sdk/client-location";

const locationClient = new LocationClient({ region: "us-east-1" });

const forecast = await locationClient.send(
  new ForecastGeofenceEventsCommand({
    CollectionName: "prod-delivery-zones",
    DeviceState: {
      Position: [-122.345, 47.610], // [longitude, latitude]
      Speed: 13.4, // meters/second (~30 mph)
    },
    TimeHorizonMinutes: 15, // Look ahead 15 minutes
    DistanceUnit: "Kilometers",
    SpeedUnit: "KilometersPerHour",
  })
);

for (const event of forecast.ForecastedEvents ?? []) {
  console.log(
    `Geofence ${event.GeofenceId}: ${event.EventType} in ~${event.ForecastedBreachTime?.toISOString()} (NearestDistance: ${event.NearestDistance} km)`
  );
}
```

---

## 4. Anti-Spoofing Location Integrity (`VerifyDevicePosition`)

Use `VerifyDevicePositionCommand` for fraud prevention, territorial compliance, gig-economy driver check-in verification, and high-value cargo auditing. It cross-checks the device's claimed GPS coordinate against independent network signals (**IP address**, **Wi-Fi BSSID/RSSI**, and **LTE/NR Cell Tower measurements**):

```typescript
import { LocationClient, VerifyDevicePositionCommand } from "@aws-sdk/client-location";

const locationClient = new LocationClient({ region: "us-east-1" });

const verification = await locationClient.send(
  new VerifyDevicePositionCommand({
    TrackerName: "prod-fleet-tracker",
    DeviceState: {
      DeviceId: "driver-phone-88",
      SampleTime: new Date(),
      Position: [-122.3321, 47.6062], // [longitude, latitude]
      Accuracy: { Horizontal: 5.0 },
      Ipv4Address: "198.51.100.42",
      WiFiAccessPoints: [
        { MacAddress: "00:11:22:33:44:55", Rss: -58 },
        { MacAddress: "66:77:88:99:AA:BB", Rss: -64 },
      ],
      CellSignals: {
        LteCellDetails: [
          {
            CellId: 2849101,
            Mcc: 310,
            Mnc: 410,
            Tac: 14021,
          },
        ],
      },
    },
    DistanceUnit: "Kilometers",
  })
);

// Inspect InferredState.ProxyDetected and distance discrepancy between DeviceState.Position and InferredState.Position
console.log("Proxy/VPN Detected:", verification.InferredState?.ProxyDetected);
console.log("Inferred Position:", verification.InferredState?.Position);
console.log("Deviation Distance:", verification.InferredState?.DeviationDistance);
```

---

## 5. AWS IoT Core MQTT `LocationAction` & EventBridge Wiring

### Zero-Lambda IoT Core Topic Rule (`LocationAction`)

Hardware GPS trackers publishing over MQTT (`iot/fleet/+/telemetry`) can stream directly into an Amazon Location Tracker without an intermediate Lambda function:

- **IoT SQL Statement**:
  ```sql
  SELECT * FROM 'iot/fleet/+/telemetry'
  ```
- **`LocationAction` Configuration**:
  - `TrackerName`: `"prod-fleet-tracker"`
  - `DeviceId`: `"${deviceId}"`
  - `Latitude`: `"${latitude}"`
  - `Longitude`: `"${longitude}"`
  - `Timestamp`: `{ "Value": "${timestamp}", "Unit": "MILLISECONDS" }`
  - `RoleArn`: IAM Role trusting `iot.amazonaws.com` with `geo:BatchUpdateDevicePosition` on `arn:aws:geo:<region>:<account>:tracker/prod-fleet-tracker`.

> **Cellular IoT Simpler Alternative (Soracom Beam)**: Constrained cellular microcontrollers that cannot sign AWS SigV4 requests or hold TLS client certificates can send plain HTTP/UDP payloads over the cellular airlink to **Soracom Beam**, which attaches AWS IAM SigV4 headers in the cloud and calls `BatchUpdateDevicePosition` directly.

### EventBridge Pattern for Geofence `ENTER` / `EXIT` Alerts

```json
{
  "source": ["aws.geo"],
  "detail-type": ["Location Geofence Event"],
  "detail": {
    "EventType": ["ENTER", "EXIT"],
    "TrackerName": ["prod-fleet-tracker"],
    "CollectionName": ["prod-delivery-zones"]
  }
}
```
