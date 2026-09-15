# @clipper-x/node-sdk

Production-quality V1 Node.js / TypeScript SDK for Clipper-X Node Registration and Network Telemetry.

## Features

- **Node Registration**: Registers device with unique `NODE_ID` and receives secure Bearer authentication credentials.
- **Local State Persistence**: Stores credentials locally with restricted `0600` permissions.
- **Observed Public IP**: Queries the Clipper-X backend for observed public egress IP (with reverse proxy validation).
- **Controlled Bandwidth Testing**: Measures download/upload bandwidth using controlled payload sizes without saturating network connections.
- **Robust Heartbeat Service**: Periodic heartbeats with duplicate timer protection and bounded exponential backoff on network failures.
- **Network Adapter Extensibility**: Abstract `NetworkAdapter` interface designed for future V2 Tailscale/Headscale integration.

## Installation

```bash
npm install
npm run build
```

## Quick Start

```typescript
import { ClipperXNodeSDK } from "@clipper-x/node-sdk";

const sdk = new ClipperXNodeSDK({
  apiUrl: "http://localhost:8000",
  heartbeatIntervalMs: 30000,
  deviceName: "worker-node-1",
});

async function main() {
  // 1. Register or load existing credentials
  const registration = await sdk.register();
  console.log(`Registered with ID: ${registration.nodeId}`);

  // 2. Discover observed egress IP
  const ip = await sdk.getPublicIP();
  console.log(`Public IP: ${ip.publicIp}`);

  // 3. Measure bandwidth
  const bandwidth = await sdk.measureDownloadBandwidth(5);
  console.log(`Bandwidth: ${bandwidth.downloadMbps} Mbps`);

  // 4. Report measurements to backend
  await sdk.reportNetworkInfo({
    observed_public_ip: ip.publicIp,
    download_mbps: bandwidth.downloadMbps,
  });

  // 5. Start heartbeat loop
  sdk.startHeartbeat(
    (ack) => console.log("Heartbeat acknowledged:", ack.acknowledgedAt),
    (err) => console.error("Heartbeat error:", err.message)
  );
}

main().catch(console.error);
```

## Running the Demo

```bash
npm run build
npm run demo
```
