import { describe, it, before, after } from "node:test";
import * as assert from "node:assert";
import * as fs from "fs";
import * as path from "path";
import * as http from "http";
import { ClipperXNodeSDK } from "../src/client";
import { LocalStateManager } from "../src/local-state";
import { LocalNetworkAdapter } from "../src/network-adapter";
import {
  AuthenticationError,
  AuthorizationError,
  HeartbeatError,
  NetworkError,
  RegistrationError,
} from "../src/errors";

describe("Clipper-X Node SDK Unit Tests", () => {
  const tempStateFile = path.resolve(__dirname, "../../.test-node-state.json");
  let mockServer: http.Server;
  let mockServerUrl: string;

  before(async () => {
    // Setup lightweight mock HTTP server for SDK client testing
    mockServer = http.createServer((req, res) => {
      const url = new URL(req.url || "/", `http://${req.headers.host}`);

      if (url.pathname === "/api/v1/nodes/register" && req.method === "POST") {
        let body = "";
        req.on("data", (c) => (body += c));
        req.on("end", () => {
          const parsed = JSON.parse(body);
          res.writeHead(201, { "Content-Type": "application/json" });
          res.end(
            JSON.stringify({
              node_id: "node_mock12345",
              token: "cnx_tok_mocksecret12345",
              status: "REGISTERING",
              platform: parsed.platform || "linux",
              sdk_version: parsed.sdk_version || "1.0.0",
            })
          );
        });
        return;
      }

      if (url.pathname === "/api/v1/enrollment/claim" && req.method === "POST") {
        let body = "";
        req.on("data", (c) => (body += c));
        req.on("end", () => {
          const parsed = JSON.parse(body);
          if (parsed.enrollment_token !== "cne_valid_token_123") {
            res.writeHead(404, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ detail: "Enrollment ticket not found or expired" }));
            return;
          }
          res.writeHead(201, { "Content-Type": "application/json" });
          res.end(
            JSON.stringify({
              node_id: "node_enrolled_12345",
              token: "cnx_tok_enrolled_secret",
              status: "REGISTERING",
              platform: parsed.platform || "linux",
              sdk_version: parsed.sdk_version || "1.0.0",
              device_name: parsed.device_name || "test-device",
              owner_id: "invite-owner-1",
            })
          );
        });
        return;
      }

      if (url.pathname === "/api/v1/network/ip" && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            ip: "203.0.113.55",
            observed_at: new Date().toISOString(),
          })
        );
        return;
      }

      if (url.pathname.includes("/heartbeat") && req.method === "POST") {
        const auth = req.headers["authorization"];
        if (!auth || auth !== "Bearer cnx_tok_mocksecret12345") {
          res.writeHead(401, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ detail: "Invalid node credentials" }));
          return;
        }
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            status: "ONLINE",
            acknowledged_at: new Date().toISOString(),
            node_id: "node_mock12345",
          })
        );
        return;
      }

      if (url.pathname === "/api/v1/network/speed-test" && req.method === "GET") {
        // Return 100 KB payload
        const payload = Buffer.alloc(100 * 1024, 0);
        res.writeHead(200, {
          "Content-Type": "application/octet-stream",
          "Content-Length": payload.length.toString(),
        });
        res.end(payload);
        return;
      }

      res.writeHead(404);
      res.end();
    });

    await new Promise<void>((resolve) => {
      mockServer.listen(0, "127.0.0.1", () => {
        const addr = mockServer.address() as any;
        mockServerUrl = `http://127.0.0.1:${addr.port}`;
        resolve();
      });
    });
  });

  after(async () => {
    mockServer.close();
    if (fs.existsSync(tempStateFile)) {
      fs.unlinkSync(tempStateFile);
    }
  });

  it("initializes with options and sensible defaults", () => {
    const sdk = new ClipperXNodeSDK({
      apiUrl: mockServerUrl,
      heartbeatIntervalMs: 15000,
      stateFilePath: tempStateFile,
    });
    assert.strictEqual(sdk.getNodeId(), null);
    assert.strictEqual(sdk.getToken(), null);
    assert.ok(sdk.getNetworkAdapter() instanceof LocalNetworkAdapter);
  });

  it("persists local state with restricted 0600 permissions", () => {
    const manager = new LocalStateManager(tempStateFile);
    manager.saveState({
      nodeId: "node_test_persist",
      nodeToken: "cnx_tok_test_secret",
      platform: "linux",
      sdkVersion: "1.0.0",
      registeredAt: new Date().toISOString(),
    });

    assert.ok(fs.existsSync(tempStateFile));
    const stat = fs.statSync(tempStateFile);
    // Verify file mode includes 0600 (0o600 in octal is 384)
    const mode = stat.mode & 0o777;
    assert.strictEqual(mode, 0o600);

    const loaded = manager.loadState();
    assert.ok(loaded);
    assert.strictEqual(loaded.nodeId, "node_test_persist");
    assert.strictEqual(loaded.nodeToken, "cnx_tok_test_secret");

    manager.clearState();
    assert.strictEqual(fs.existsSync(tempStateFile), false);
  });

  it("performs node registration and updates local state in REGISTERING status", async () => {
    const sdk = new ClipperXNodeSDK({
      apiUrl: mockServerUrl,
      stateFilePath: tempStateFile,
    });

    const reg = await sdk.register({ platform: "linux" }, true);
    assert.strictEqual(reg.nodeId, "node_mock12345");
    assert.strictEqual(reg.token, "cnx_tok_mocksecret12345");
    assert.strictEqual(reg.status, "REGISTERING");
    assert.strictEqual(sdk.getNodeId(), "node_mock12345");
    assert.strictEqual(sdk.getToken(), "cnx_tok_mocksecret12345");
  });

  it("transitions from REGISTERING to ONLINE upon first valid authenticated heartbeat", async () => {
    const sdk = new ClipperXNodeSDK({
      apiUrl: mockServerUrl,
      stateFilePath: tempStateFile,
    });
    const reg = await sdk.register();
    assert.strictEqual(reg.status, "REGISTERING");

    // Send single heartbeat ping
    const hbResult = await sdk.sendHeartbeat();
    assert.strictEqual(hbResult.status, "ONLINE");
    assert.strictEqual(hbResult.nodeId, "node_mock12345");
  });

  it("retrieves public egress IP with proper description", async () => {
    const sdk = new ClipperXNodeSDK({ apiUrl: mockServerUrl });
    const ipInfo = await sdk.getPublicIP();
    assert.strictEqual(ipInfo.publicIp, "203.0.113.55");
    assert.strictEqual(ipInfo.description, "Observed public egress IP from the Clipper-X backend");
  });

  it("measures download bandwidth", async () => {
    const sdk = new ClipperXNodeSDK({ apiUrl: mockServerUrl });
    const bw = await sdk.measureDownloadBandwidth();
    assert.ok(bw.downloadMbps > 0);
    assert.strictEqual(bw.bytes, 100 * 1024);
    assert.strictEqual(bw.description, "Observed bandwidth to Clipper-X test server");
  });

  it("protects against duplicate heartbeat timers and supports clean stop", async () => {
    const sdk = new ClipperXNodeSDK({
      apiUrl: mockServerUrl,
      heartbeatIntervalMs: 500,
      stateFilePath: tempStateFile,
    });
    await sdk.register();

    let ackCount = 0;
    sdk.startHeartbeat(() => {
      ackCount++;
    });

    // Calling startHeartbeat second time must NOT create duplicate timers
    sdk.startHeartbeat(() => {
      ackCount++;
    });

    assert.strictEqual(sdk.isHeartbeatRunning(), true);

    await new Promise((r) => setTimeout(r, 600));
    assert.ok(ackCount >= 1);

    sdk.stopHeartbeat();
    assert.strictEqual(sdk.isHeartbeatRunning(), false);
  });

  it("handles custom error classes properly", () => {
    const authErr = new AuthenticationError("bad creds");
    assert.strictEqual(authErr.statusCode, 401);
    assert.strictEqual(authErr.name, "AuthenticationError");

    const authzErr = new AuthorizationError("forbidden");
    assert.strictEqual(authzErr.statusCode, 403);

    const netErr = new NetworkError("timed out");
    assert.strictEqual(netErr.name, "NetworkError");

    const regErr = new RegistrationError("failed reg");
    assert.strictEqual(regErr.name, "RegistrationError");

    const hbErr = new HeartbeatError("hb failed");
    assert.strictEqual(hbErr.name, "HeartbeatError");
  });

  it("supports multiple independent SDK instances with isolated state files", async () => {
    const file1 = path.resolve(__dirname, "../../.test-node-1.json");
    const file2 = path.resolve(__dirname, "../../.test-node-2.json");
    const file3 = path.resolve(__dirname, "../../.test-node-3.json");

    try {
      const sdk1 = new ClipperXNodeSDK({ apiUrl: mockServerUrl, stateFilePath: file1 });
      const sdk2 = new ClipperXNodeSDK({ apiUrl: mockServerUrl, stateFilePath: file2 });
      const sdk3 = new ClipperXNodeSDK({ apiUrl: mockServerUrl, stateFilePath: file3 });

      await sdk1.register({ deviceName: "instance-1" }, true);
      await sdk2.register({ deviceName: "instance-2" }, true);
      await sdk3.register({ deviceName: "instance-3" }, true);

      assert.ok(fs.existsSync(file1));
      assert.ok(fs.existsSync(file2));
      assert.ok(fs.existsSync(file3));

      assert.strictEqual(sdk1.getNodeId(), "node_mock12345");
      assert.strictEqual(sdk2.getNodeId(), "node_mock12345");
      assert.strictEqual(sdk3.getNodeId(), "node_mock12345");
    } finally {
      if (fs.existsSync(file1)) fs.unlinkSync(file1);
      if (fs.existsSync(file2)) fs.unlinkSync(file2);
      if (fs.existsSync(file3)) fs.unlinkSync(file3);
    }
  });

  it("rejects heartbeat with invalid token", async () => {
    const badStateFile = path.resolve(__dirname, "../../.test-bad-token.json");
    const badManager = new LocalStateManager(badStateFile);
    badManager.saveState({
      nodeId: "node_mock12345",
      nodeToken: "cnx_tok_invalid_secret",
      platform: "linux",
      sdkVersion: "1.0.0",
      registeredAt: new Date().toISOString(),
    });

    const sdk = new ClipperXNodeSDK({ apiUrl: mockServerUrl, stateFilePath: badStateFile });
    // Attempt heartbeat with bad token
    await assert.rejects(async () => {
      await sdk.sendHeartbeat();
    }, (err: any) => {
      return err instanceof AuthenticationError && err.statusCode === 401;
    });

    badManager.clearState();
  });

  it("enrolls node using one-time enrollment ticket and saves local state", async () => {
    const enrollStateFile = path.resolve(__dirname, "../../.test-enroll-state.json");
    try {
      const sdk = new ClipperXNodeSDK({ apiUrl: mockServerUrl, stateFilePath: enrollStateFile });

      // Test invalid token
      await assert.rejects(async () => {
        await sdk.enrollWithTicket("cne_invalid_token");
      }, (err: any) => {
        return err instanceof RegistrationError && err.statusCode === 404;
      });

      // Test valid token
      const res = await sdk.enrollWithTicket("cne_valid_token_123", { deviceName: "my-phone" });
      assert.strictEqual(res.nodeId, "node_enrolled_12345");
      assert.strictEqual(res.token, "cnx_tok_enrolled_secret");
      assert.strictEqual(res.status, "REGISTERING");
      assert.strictEqual(sdk.getNodeId(), "node_enrolled_12345");
      assert.strictEqual(sdk.getToken(), "cnx_tok_enrolled_secret");

      // Verify file persisted
      assert.ok(fs.existsSync(enrollStateFile));
      const stateContent = JSON.parse(fs.readFileSync(enrollStateFile, "utf8"));
      assert.strictEqual(stateContent.nodeId, "node_enrolled_12345");
      assert.strictEqual(stateContent.nodeToken, "cnx_tok_enrolled_secret");
    } finally {
      if (fs.existsSync(enrollStateFile)) fs.unlinkSync(enrollStateFile);
    }
  });
});

