import { describe, it } from "node:test";
import * as assert from "node:assert";

describe("Bandwidth Calculation Formulas", () => {
  it("calculates accurate Mbps for known byte and duration parameters", () => {
    // 5 MB = 5 * 1024 * 1024 = 5242880 bytes
    const bytes = 5242880;
    const durationMs = 1000; // 1 second
    const elapsedSeconds = durationMs / 1000;
    const bits = bytes * 8;
    const mbps = Number((bits / elapsedSeconds / 1_000_000).toFixed(2));

    // 5242880 * 8 / 1000000 = 41.94 Mbps
    assert.strictEqual(mbps, 41.94);
  });

  it("handles low-latency / small payload calculations without division by zero", () => {
    const bytes = 1024;
    const durationMs = 10;
    const elapsedSeconds = durationMs / 1000;
    const bits = bytes * 8;
    const mbps = Number((bits / elapsedSeconds / 1_000_000).toFixed(2));

    assert.ok(mbps > 0);
    assert.strictEqual(mbps, 0.82);
  });
});
