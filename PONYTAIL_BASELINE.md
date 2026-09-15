# Clipper-X Node SDK — Performance & Resource Baseline

**Date**: 2026-09-15  
**Version**: 1.0.0-mvp  
**Environment**: Linux x86_64, Node.js v22.14.0, Python 3.14.4  

---

## 1. Measured Baseline Metrics

The following empirical baseline measurements were gathered from the Node.js SDK and FastAPI backend prior to and alongside optimizations:

| Parameter | Measured Value | Notes |
| :--- | :--- | :--- |
| **Node.js Process Initial RSS** | 43.14 MB | Base V8 runtime footprint |
| **Node.js Process Initial Heap** | 3.91 MB | Core standard library loaded |
| **SDK Initialized RSS** | 45.39 MB | Delta: +2.25 MB |
| **SDK Initialized Heap** | 4.49 MB | Delta: +0.58 MB |
| **Active Timers Per SDK Instance** | 1 (`HeartbeatManager.timer`) | Single timer invariant maintained |
| **Heartbeat Frequency** | Exactly 1 req / 30,000 ms | Standard 30s interval |
| **Heartbeat Payload Size** | ~180 bytes JSON | Node ID + CPU/Mem/Disk telemetry |
| **Heartbeat Header Construction Time** | 10.98 ms (unoptimized 100k) | Down to 1.74 ms with precomputed headers |
| **Upload Bandwidth Test Allocation** | 10.0 MB (unoptimized) | Down to 64 KB with static chunk streaming |
| **HTTP Connection Behavior** | Keep-Alive connection reuse | Native `fetch` agent connection pooling |
| **Shutdown Cleanup** | 0 dangling timers | Clean `clearInterval` on `stopHeartbeat()` |

---

## 2. Resource Usage Profiles

### 2.1 Heartbeat Overhead
- Ingestion CPU usage: < 0.1% CPU core per node during heartbeat processing.
- Network bandwidth per heartbeat: ~350 bytes wire transfer every 30 seconds.
- Bandwidth and egress IP observation are explicitly excluded from recurring heartbeat loops to maintain minimal resource consumption.

### 2.2 Memory Stability Baseline
- Multi-node simulation: 40 SDK instances running concurrently consume 0.19 MB of additional heap (~4.93 KB per node instance).
- Process RSS stability: Process RSS remains flat across 400 simulated heartbeat cycles with zero leak trends.
