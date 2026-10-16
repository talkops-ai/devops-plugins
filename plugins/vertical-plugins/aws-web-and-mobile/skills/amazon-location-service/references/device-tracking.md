# Device Tracking

> **Audience Note**: Keywords MUST, SHOULD, MAY in this document indicate requirements for agent recommendations to users, following RFC 2119.

Track device locations in real time and query position history. This is the core tracking pattern — applicable to fleet dashboards, delivery tracking UIs, asset monitoring, and any scenario where you need to know where devices are or where they've been. For triggering actions when devices enter or exit geographic zones, trackers can be linked to geofence collections — see the **zone-alerts** reference.

> **Language note**: Code examples below use JavaScript (`@aws-sdk/client-location`). When the user's project uses a different language, translate the API calls to the equivalent AWS SDK — the operation names, parameters, and response shapes are identical across SDKs.

## Table of Contents

- [Step 1: Create a Tracker](#step-1-create-a-tracker)
- [Step 2: Send Position Updates](#step-2-send-position-updates)
- [Step 3: Query Device Positions](#step-3-query-device-positions)
- [Step 4: Display on a Map](#step-4-display-on-a-map)
- [Error Handling](#error-handling)
- [Cost Considerations](#cost-considerations)
- [Best Practices](#best-practices)
- [Position Integrity](#position-integrity)

## Step 1: Create a Tracker

A tracker stores position updates for a collection of devices. Choose a position filtering mode to control cost and reduce GPS jitter.

```javascript
import { CreateTrackerCommand } from "@aws-sdk/client-location";

await client.send(
  new CreateTrackerCommand({
    TrackerName: "my-fleet-tracker",
    PositionFiltering: "AccuracyBased", // or "DistanceBased" | "TimeBased"
  }),
);
```

### Position Filtering Modes

| Mode                    | Behavior                                                                                                         | Best For                                           |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| **AccuracyBased**       | Ignores updates where movement < measured accuracy. Example: accuracy of 5m and 10m → ignored if movement < 15m. | Devices that report accuracy (recommended)         |
| **DistanceBased**       | Ignores updates where device moved < 30m.                                                                        | Devices without accuracy data, reducing GPS jitter |
| **TimeBased** (default) | Evaluates all updates against geofences but stores only one per 30 seconds per device.                           | High-frequency updates (>1 per 30 seconds)         |

**IMPORTANT**: Filtering affects what gets **stored** and **evaluated against geofences**. AccuracyBased and DistanceBased filtering reduce both storage costs and geofence evaluation costs. TimeBased evaluates every update against geofences but limits storage.

### Customer-Managed KMS Encryption & Geospatial Queries (`KmsKeyEnableGeospatialQueries`)

When attaching a customer-managed AWS KMS key (`KmsKeyId`) to a tracker for regulatory compliance, the **Bounding Polygon geospatial query** feature (`ListDevicePositions` with `FilterGeometry`) is **disabled by default** because spatial indexing relies on an unencrypted representation of device positions (even though exact coordinates remain encrypted). You MUST explicitly set `KmsKeyEnableGeospatialQueries: true` during `CreateTracker` or `UpdateTracker` if bounding polygon queries are required alongside a customer-managed KMS key:

```javascript
import { CreateTrackerCommand } from "@aws-sdk/client-location";

await client.send(
  new CreateTrackerCommand({
    TrackerName: "my-compliant-fleet-tracker",
    PositionFiltering: "AccuracyBased",
    KmsKeyId: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
    KmsKeyEnableGeospatialQueries: true, // REQUIRED for FilterGeometry polygon queries when KmsKeyId is set
    EventBridgeEnabled: true, // REQUIRED only if you need raw position UPDATE events in EventBridge
  }),
);
```

### Raw Position `UPDATE` Events vs. Geofence `ENTER`/`EXIT` Events (`EventBridgeEnabled`)

- **Geofence `ENTER` and `EXIT` events** (`detail-type: "Location Geofence Event"`) are automatically published to Amazon EventBridge whenever a tracker is linked to a Geofence Collection via `AssociateTrackerConsumer`—no extra flag is required on the tracker.
- **Raw device position `UPDATE` events** (`detail-type: "Location Device Position Event"`) are **suppressed by default** to prevent EventBridge cost spikes. Set `EventBridgeEnabled: true` on the tracker only when downstream consumers need every filtered position update streamed via EventBridge.

## Step 2: Send Position Updates

Use `BatchUpdateDevicePosition` to send location data from devices. Each call accepts up to 10 device updates (default regional quota: **50 RPS**, adjustable up to **100 RPS**).

```javascript
import { BatchUpdateDevicePositionCommand } from "@aws-sdk/client-location";

await client.send(
  new BatchUpdateDevicePositionCommand({
    TrackerName: "my-fleet-tracker",
    Updates: [
      {
        DeviceId: "truck-01",
        Position: [-122.3394, 47.6159], // [longitude, latitude]
        SampleTime: new Date().toISOString(),
        Accuracy: { Horizontal: 10.0 }, // meters, optional but recommended
        PositionProperties: {
          // up to 4 key-value pairs
          VehicleType: "Truck",
          DriverId: "D-1234",
        },
      },
      {
        DeviceId: "truck-02",
        Position: [-122.351, 47.6205],
        SampleTime: new Date().toISOString(),
        Accuracy: { Horizontal: 8.0 },
        PositionProperties: { VehicleType: "Van" },
      },
    ],
  }),
);
```

### MQTT Ingestion (AWS IoT Core `LocationAction` & SigV4 HTTP Proxies)

For high-throughput IoT fleets, stream coordinates via MQTT through **AWS IoT Core** (or SigV4 HTTP cellular proxies such as **Soracom Beam** targeting `/tracking/v0/trackers/{trackerName}/positions`), avoiding heavy AWS SDK credentials on constrained edge devices. Configure an AWS IoT Topic Rule with a `location` action and an IAM role granting `geo:BatchUpdateDevicePosition`:

```json
{
  "sql": "SELECT * FROM 'iot/fleet/+/position'",
  "actions": [
    {
      "location": {
        "roleArn": "arn:aws:iam::123456789012:role/IoTLocationTrackerRole",
        "trackerName": "my-fleet-tracker",
        "deviceId": "${deviceId}",
        "latitude": "${latitude}",
        "longitude": "${longitude}",
        "timestamp": {
          "value": "${timestamp()}",
          "unit": "MILLISECONDS"
        }
      }
    }
  ]
}
```

### Update Frequency Guidance

| Scenario                        | Suggested Frequency | Filtering Mode |
| ------------------------------- | ------------------- | -------------- |
| Real-time fleet dashboard       | 5–15 seconds        | TimeBased      |
| Delivery ETA tracking           | 30–60 seconds       | AccuracyBased  |
| Asset monitoring (low movement) | 1–5 minutes         | DistanceBased  |
| Periodic check-in               | 15–60 minutes       | DistanceBased  |

## Step 3: Query Device Positions

### Current Position — Single Device

```javascript
import { GetDevicePositionCommand } from "@aws-sdk/client-location";

const response = await client.send(
  new GetDevicePositionCommand({
    TrackerName: "my-fleet-tracker",
    DeviceId: "truck-01",
  }),
);
// response.Position → [-122.3394, 47.6159]
// response.SampleTime → "2024-01-15T12:00:00Z"
// response.Accuracy → { Horizontal: 10.0 }
// response.PositionProperties → { VehicleType: "Truck", DriverId: "D-1234" }
```

### Current Position — Multiple Devices

```javascript
import { BatchGetDevicePositionCommand } from "@aws-sdk/client-location";

const response = await client.send(
  new BatchGetDevicePositionCommand({
    TrackerName: "my-fleet-tracker",
    DeviceIds: ["truck-01", "truck-02", "truck-03"],
  }),
);
// response.DevicePositions → array of position objects
// response.Errors → array of devices that failed (check this!)
```

### All Devices (Fleet View & Bounding Polygon Spatial Query)

```javascript
import { ListDevicePositionsCommand } from "@aws-sdk/client-location";

const response = await client.send(
  new ListDevicePositionsCommand({
    TrackerName: "my-fleet-tracker",
    MaxResults: 100,
    // Optional: filter devices currently inside a bounding polygon
    // (Requires KmsKeyEnableGeospatialQueries: true if tracker uses a customer-managed KMS key)
    FilterGeometry: {
      Polygon: [
        [
          [-122.36, 47.63],
          [-122.36, 47.60],
          [-122.32, 47.60],
          [-122.32, 47.63],
          [-122.36, 47.63], // First and last vertex MUST match to close the ring
        ],
      ],
    },
  }),
);
// response.Entries → array of { DeviceId, Position, SampleTime, ... }
// response.NextToken → use for pagination if more devices exist
```

### Position History

Retrieve historical positions for a device within a time range. Useful for route playback, dwell time analysis, and audit trails.

```javascript
import { GetDevicePositionHistoryCommand } from "@aws-sdk/client-location";

const response = await client.send(
  new GetDevicePositionHistoryCommand({
    TrackerName: "my-fleet-tracker",
    DeviceId: "truck-01",
    StartTimeInclusive: new Date("2024-01-15T00:00:00Z"),
    EndTimeExclusive: new Date("2024-01-15T23:59:59Z"),
    MaxResults: 100,
  }),
);
// response.DevicePositions → array of historical positions, ordered by SampleTime
// response.NextToken → use for pagination
```

**Note**: Position history retention depends on the tracker's position filtering mode. TimeBased filtering stores at most one position per 30 seconds. AccuracyBased and DistanceBased only store positions that pass the filter.

## Step 4: Display on a Map

Combine tracking data with MapLibre to show devices on an interactive map. See the **dynamic-map** reference for full MapLibre setup.

```javascript
// After map loads, add device markers
map.on("load", async () => {
  const response = await client.send(
    new ListDevicePositionsCommand({
      TrackerName: "my-fleet-tracker",
    }),
  );

  response.Entries.forEach((device) => {
    const content = document.createElement("div");
    const title = document.createElement("h4");
    title.textContent = device.DeviceId;
    const lastSeen = document.createElement("p");
    lastSeen.textContent = `Last seen: ${new Date(device.SampleTime).toLocaleString()}`;
    content.append(title, lastSeen);

    new maplibregl.Marker({ color: "#FF0000" })
      .setLngLat(device.Position)
      .setPopup(new maplibregl.Popup().setDOMContent(content))
      .addTo(map);
  });
});
```

### Real-Time Updates

For live tracking, poll for position updates on an interval:

```javascript
setInterval(async () => {
  const response = await client.send(
    new ListDevicePositionsCommand({
      TrackerName: "my-fleet-tracker",
    }),
  );
  // Update marker positions on the map
  updateMarkers(response.Entries);
}, 15000); // every 15 seconds
```

**Note**: If markers are **draggable** (e.g., for interactive dashboards), polling will fight with drag by calling `setLngLat()` mid-drag. Pause polling on `dragstart` and resume on `dragend`.

### Historical Path Visualization

Display a device's historical route as a line on the map. The [`amazon-location-utilities-datatypes-js`](https://github.com/aws-geospatial/amazon-location-utilities-datatypes-js) library provides `devicePositionsToFeatureCollection()` to convert tracking responses into GeoJSON FeatureCollections of Point features — useful for plotting individual position markers. For drawing a connected route line, extract coordinates directly as shown below.

```javascript
const history = await client.send(
  new GetDevicePositionHistoryCommand({
    TrackerName: "my-fleet-tracker",
    DeviceId: "truck-01",
    StartTimeInclusive: new Date("2024-01-15T08:00:00Z"),
    EndTimeExclusive: new Date("2024-01-15T17:00:00Z"),
  }),
);

const coordinates = history.DevicePositions.map((p) => p.Position);

map.addSource("route", {
  type: "geojson",
  data: {
    type: "Feature",
    geometry: { type: "LineString", coordinates },
  },
});

map.addLayer({
  id: "route-line",
  type: "line",
  source: "route",
  paint: {
    "line-color": "#3b82f6",
    "line-width": 3,
  },
});
```

## Error Handling

### Common Errors

| Error                       | HTTP Status | Cause                                                          |
| --------------------------- | ----------- | -------------------------------------------------------------- |
| `ResourceNotFoundException` | 404         | Tracker name doesn't exist, or device has never sent an update |
| `ValidationException`       | 400         | Invalid parameters (coordinate order, missing fields)          |
| `ThrottlingException`       | 429         | Request rate exceeded — implement exponential backoff          |
| `AccessDeniedException`     | 403         | IAM or Cognito permissions missing                             |

### Batch Operation Errors

`BatchUpdateDevicePosition` and `BatchGetDevicePosition` return partial success. Always check the `Errors` array:

```javascript
const response = await client.send(
  new BatchUpdateDevicePositionCommand({/* ... */}),
);

if (response.Errors?.length > 0) {
  response.Errors.forEach((error) => {
    console.error(`Failed device ${error.DeviceId}: ${error.Error.Message}`);
  });
}
```

### Device Not Found

`GetDevicePosition` throws `ResourceNotFoundException` if the device has never sent a position update, or if all positions have been deleted. Handle this gracefully in fleet dashboards — a missing device is not necessarily an error.

## Cost Considerations

- Billed per **position update received** and per **position query request**
- If linked to geofence collections, also billed per **geofence collection evaluation** per update
- Example: TimeBased filtering with 2 linked collections at 5-second update frequency = 720 update requests + 1,440 geofence evaluations **per device per hour**
- Use AccuracyBased or DistanceBased filtering to drop unnecessary updates and reduce costs
- Adjust update frequency to match your use case — not all applications need sub-minute updates

## Best Practices

- Set `Accuracy.Horizontal` on every update when available — it improves position filtering and geofence evaluation precision
- Use `PositionProperties` (max 4 key-value pairs) for device metadata that should travel with position data (vehicle type, driver ID, cargo status)
- Paginate `ListDevicePositions` and `GetDevicePositionHistory` — don't assume all results fit in one response
- Match update frequency to your use case — over-reporting wastes cost, under-reporting misses events
- For fleet dashboards, poll `ListDevicePositions` at a slower rate than devices report (e.g., poll every 15s even if devices report every 5s)
- Link trackers to geofence collections to automatically trigger zone-based alerts — see the **zone-alerts** reference
- Use `BatchDeleteDevicePositionHistory` to clean up test data or comply with data retention policies

## Position Integrity

This section covers optional position validation — separate from the core track→query→display flow above. Use `VerifyDevicePosition` to detect GPS spoofing or proxy usage by comparing a device's reported position against an inferred position derived from IP address, Wi-Fi signals, and cell tower data.

```javascript
import { VerifyDevicePositionCommand } from "@aws-sdk/client-location";

const response = await client.send(
  new VerifyDevicePositionCommand({
    TrackerName: "my-fleet-tracker",
    DeviceState: {
      DeviceId: "truck-01",
      SampleTime: new Date().toISOString(),
      Position: [-122.3394, 47.6159],
      Accuracy: { Horizontal: 10.0 },
      Ipv4Address: "203.0.113.25",
      WiFiAccessPoints: [{ MacAddress: "AA:BB:CC:DD:EE:FF", Rss: -65 }],
      CellSignals: {
        LteCellDetails: [
          {
            CellId: 1234567,
            Mcc: 310,
            Mnc: 410,
            LocalId: { Earfcn: 5230, Pci: 123 },
          },
        ],
      },
    },
  }),
);
```
