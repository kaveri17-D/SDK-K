# Clipper-X Node SDK & Registry MVP — Final Execution Plan

**Date**: 2026-09-15  
**Execution Pass**: Final Master Execution Pass  
**Repository**: `/home/system/Desktop/ClipSdk`  

---

## 1. Current State Audit

### What is Complete:
1. **FastAPI Backend Services**: Full API for node registration, authentication, HMAC-SHA256 token hashing, single-use ticket enrollment (`cne_...`), egress IP observation, bandwidth testing (64 KB chunk streaming), and health checks.
2. **Central Dashboard**: `GET /dashboard` and `GET /api/v1/dashboard/stats` serving live stats and node list with 3s polling.
3. **FSM Lifecycle**: `REGISTERING` -> `ONLINE` (first heartbeat) -> `STALE` (90s) -> `OFFLINE` (180s) -> `ONLINE` (recovery).
4. **TypeScript SDK**: `ClipperXNodeSDK` with 30s heartbeat loop (`30000` ms), static chunk streaming, cached headers, single-timer invariant, and `0600` state persistence.
5. **Automated Test Suites**: 21/21 pytest backend tests passing; 13/13 Node.js SDK tests passing.
6. **Progressive Scale Simulation**: 1 -> 5 -> 10 -> 20 -> 30 -> 40 simulated nodes verified with 0 failures and 0.0 MB memory leak over 1,000 transactions.
7. **Host Docker Stack**: PostgreSQL 16 on 5432, Redis 7 on 6379, and FastAPI container active on 8000.

### What is Incomplete / Requires Action in this Pass:
1. **Ponytail**: Must activate the actual Ponytail agent ruleset/skills (`AGENTS.md`, `.agents/rules/ponytail.md`, workspace skills) in Antigravity, execute Ponytail review/audit on target files, measure before/after, and produce `PONYTAIL_EXECUTION_REPORT.md`.
2. **Reticle Real Application Verification**: Wire dev-only Reticle browser module into `/dashboard` and `/join`, drive the actual user journey (`Dashboard -> Generate Link -> Join -> Claim -> ONLINE -> Dashboard shows node`), run assertions on actual consequences, and produce `RETICLE_FINAL_VERIFICATION.md`.
3. **One-Click Phone Join & QR Support**: Enhance `/join` mobile browser client with zero-install execution (browser-side lightweight node client running 30s heartbeat loop), and add QR code display to dashboard modal.
4. **Device Data Model in Dashboard**: Include Device Name, platform, battery/network where available (or null if unsupported).
5. **Real Phone Test Harness**: Create `scripts/real_device_checklist.md` and `scripts/real_device_smoke_test.py`.
6. **Final Master Verification**: Create `FINAL_MVP_VERIFICATION.md` with master acceptance matrix.

---

## 2. Exact Files to Modify / Create

### Files to Modify:
- [`backend/app/api/dashboard.py`](file:///home/system/Desktop/ClipSdk/backend/app/api/dashboard.py): Add QR code rendering in modal, device_name column in table, Reticle dev-only client script.
- [`backend/app/main.py`](file:///home/system/Desktop/ClipSdk/backend/app/main.py): Update `/join` page with browser-side lightweight node client (30s heartbeat, metrics detection, live status badges, Reticle dev-only hook).
- [`backend/app/models/node.py`](file:///home/system/Desktop/ClipSdk/backend/app/models/node.py) & [`schemas`](file:///home/system/Desktop/ClipSdk/backend/app/schemas/): Ensure device_name is exposed cleanly.
- [`sdk/src/heartbeat.ts`](file:///home/system/Desktop/ClipSdk/sdk/src/heartbeat.ts) & [`client.ts`](file:///home/system/Desktop/ClipSdk/sdk/src/client.ts): Verify Ponytail review findings.

### Files to Create:
- `AGENTS.md` & `.agents/rules/ponytail.md`: Official Ponytail agent ruleset for Antigravity.
- `PONYTAIL_EXECUTION_REPORT.md`: Documenting Ponytail activation, review findings, applied optimizations, and before/after benchmarks.
- `RETICLE_FINAL_VERIFICATION.md`: Documenting actual Reticle live browser session and journey assertions.
- `scripts/real_device_checklist.md`: Step-by-step physical phone operator verification checklist.
- `scripts/real_device_smoke_test.py`: Interactive smoke test for physical devices.
- `FINAL_MVP_VERIFICATION.md`: Final verification table and completion evaluation.

---

## 3. Verification Plan
1. Re-run `pytest backend/tests -v` (ensure all tests pass).
2. Re-run `cd sdk && npm test` (ensure all tests pass).
3. Run Reticle verification driving real browser session against running dashboard and join flows.
4. Run progressive scale test `scripts/progressive_device_scale_test.py`.
5. Verify live Docker stack on `http://127.0.0.1:8000`.
