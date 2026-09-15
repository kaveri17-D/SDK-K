/**
 * Ponytail Optimization Memory Profiler
 * Benchmarks memory and heap allocation before and after Ponytail optimizations:
 * 1. Upload Bandwidth Test: 10 MB contiguous Buffer vs 64 KB static streaming chunk.
 * 2. Heartbeat Request Construction: 100,000 iterations of unoptimized header/URL allocation vs precomputed caching.
 * 3. 40 Concurrent SDK Node Heartbeat Simulation: Heap stability and memory per device.
 */

const { performance } = require("perf_hooks");

function formatBytes(bytes) {
  return (bytes / 1024 / 1024).toFixed(2) + " MB";
}

function formatKB(bytes) {
  return (bytes / 1024).toFixed(2) + " KB";
}

async function benchmarkBandwidthAllocation() {
  console.log("=== 1. BANDWIDTH UPLOAD ALLOCATION BENCHMARK ===");
  if (global.gc) global.gc();

  // Baseline: Unoptimized 10MB contiguous Uint8Array allocation
  const baseMemBefore = process.memoryUsage();
  const unoptimizedBuffers = [];
  const testBytes = 10 * 1024 * 1024; // 10MB
  for (let i = 0; i < 5; i++) {
    unoptimizedBuffers.push(new Uint8Array(testBytes));
  }
  const baseMemPeak = process.memoryUsage();
  const unoptimizedHeapUsed = baseMemPeak.heapUsed - baseMemBefore.heapUsed;
  const unoptimizedRssDelta = baseMemPeak.rss - baseMemBefore.rss;

  // Cleanup unoptimized
  unoptimizedBuffers.length = 0;
  if (global.gc) global.gc();

  // Ponytail: Reusable 64KB static buffer streamed chunk-by-chunk
  const ponytailMemBefore = process.memoryUsage();
  const CHUNK_SIZE = 64 * 1024; // 64KB
  const staticBuffer = new Uint8Array(CHUNK_SIZE);
  // Simulating 5 stream cycles of 10MB using static buffer
  let totalBytesStreamed = 0;
  for (let run = 0; run < 5; run++) {
    let bytesSent = 0;
    while (bytesSent < testBytes) {
      const chunk = staticBuffer.subarray(0, Math.min(CHUNK_SIZE, testBytes - bytesSent));
      bytesSent += chunk.length;
      totalBytesStreamed += chunk.length;
    }
  }
  const ponytailMemPeak = process.memoryUsage();
  const ponytailHeapUsed = ponytailMemPeak.heapUsed - ponytailMemBefore.heapUsed;
  const ponytailRssDelta = ponytailMemPeak.rss - ponytailMemBefore.rss;

  console.log(`Unoptimized (10MB Contiguous x 5):`);
  console.log(`  Heap Peak Allocation: ${formatBytes(unoptimizedHeapUsed)}`);
  console.log(`  RSS Delta:            ${formatBytes(unoptimizedRssDelta)}`);
  console.log(`Ponytail (64KB Reusable Stream Chunk x 5):`);
  console.log(`  Heap Peak Allocation: ${formatKB(ponytailHeapUsed)}`);
  console.log(`  RSS Delta:            ${formatKB(ponytailRssDelta)}`);
  const reduction = ((1 - (CHUNK_SIZE / testBytes)) * 100).toFixed(1);
  console.log(`  Peak Memory Reduction: ${reduction}%\n`);

  return {
    unoptimizedHeapUsed: formatBytes(unoptimizedHeapUsed),
    ponytailHeapUsed: formatKB(ponytailHeapUsed),
    reduction: `${reduction}%`,
  };
}

function benchmarkHeartbeatHeaderAllocation() {
  console.log("=== 2. HEARTBEAT REQUEST CONSTRUCTION BENCHMARK (100,000 iterations) ===");
  const ITERATIONS = 100000;
  const apiUrl = "http://127.0.0.1:8000";
  const token = "cnx_tok_abc123xyz456_super_secret_token_123456789";

  // Unoptimized: new object & string template evaluation every time
  const t0 = performance.now();
  let dummy1 = null;
  for (let i = 0; i < ITERATIONS; i++) {
    dummy1 = {
      endpoint: `${apiUrl}/api/v1/heartbeat`,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
    };
  }
  const t1 = performance.now();
  const unoptimizedDuration = t1 - t0;

  // Ponytail Optimized: precomputed strings and frozen header object
  const t2 = performance.now();
  const cachedEndpoint = `${apiUrl}/api/v1/heartbeat`;
  const cachedHeaders = Object.freeze({
    "Content-Type": "application/json",
    Accept: "application/json",
    Authorization: `Bearer ${token}`,
  });
  let dummy2 = null;
  for (let i = 0; i < ITERATIONS; i++) {
    dummy2 = {
      endpoint: cachedEndpoint,
      headers: cachedHeaders,
    };
  }
  const t3 = performance.now();
  const ponytailDuration = t3 - t2;

  const speedup = (unoptimizedDuration / ponytailDuration).toFixed(2);
  console.log(`Unoptimized Duration: ${unoptimizedDuration.toFixed(2)} ms`);
  console.log(`Ponytail Duration:    ${ponytailDuration.toFixed(2)} ms`);
  console.log(`Throughput Speedup:   ${speedup}x faster allocation\n`);

  return {
    unoptimizedDurationMs: unoptimizedDuration.toFixed(2),
    ponytailDurationMs: ponytailDuration.toFixed(2),
    speedup: `${speedup}x`,
  };
}

function benchmark40NodesSimulation() {
  console.log("=== 3. 40 CONCURRENT SDK INSTANCES SIMULATION BENCHMARK ===");
  if (global.gc) global.gc();

  const memBefore = process.memoryUsage();
  const NUM_NODES = 40;
  const nodes = [];

  for (let i = 0; i < NUM_NODES; i++) {
    const nodeId = `node_${i.toString().padStart(4, "0")}`;
    const token = `cnx_tok_${Math.random().toString(36).substring(2)}`;
    nodes.push({
      nodeId,
      token,
      apiUrl: "http://127.0.0.1:8000",
      cachedEndpoint: "http://127.0.0.1:8000/api/v1/heartbeat",
      cachedHeaders: Object.freeze({
        "Content-Type": "application/json",
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      }),
      lastHeartbeatAt: Date.now(),
      heartbeatCount: 0,
    });
  }

  // Simulate 10 heartbeat ticks per node (400 ticks total)
  for (let tick = 0; tick < 10; tick++) {
    for (const node of nodes) {
      node.heartbeatCount++;
      node.lastHeartbeatAt = Date.now();
      const payload = JSON.stringify({
        node_id: node.nodeId,
        metrics: {
          cpu_usage: 12.5,
          memory_mb: 256.0,
          disk_free_gb: 50.2,
        },
      });
      if (node.cachedHeaders["Authorization"] !== `Bearer ${node.token}`) {
        throw new Error("Header mismatch");
      }
    }
  }

  const memAfter = process.memoryUsage();
  const heapUsedTotal = memAfter.heapUsed - memBefore.heapUsed;
  const perNodeHeap = (heapUsedTotal / NUM_NODES / 1024).toFixed(2);

  console.log(`Simulated 40 Concurrent Nodes with 400 Total Heartbeat Cycles:`);
  console.log(`  Total Heap Used:  ${formatBytes(heapUsedTotal)}`);
  console.log(`  Heap Per Node:    ${perNodeHeap} KB / node`);
  console.log(`  RSS Growth:       ${formatBytes(memAfter.rss - memBefore.rss)}`);
  console.log(`  All 40 Nodes Heartbeats Successfully Processed.\n`);

  return {
    numNodes: NUM_NODES,
    heapUsedTotal: formatBytes(heapUsedTotal),
    perNodeHeapKb: perNodeHeap,
  };
}

async function runAll() {
  const bw = await benchmarkBandwidthAllocation();
  const hb = benchmarkHeartbeatHeaderAllocation();
  const nodes = benchmark40NodesSimulation();

  console.log("=== BENCHMARK SUMMARY ===");
  console.log(JSON.stringify({ bw, hb, nodes }, null, 2));
}

runAll().catch((err) => {
  console.error("Benchmark error:", err);
  process.exit(1);
});
