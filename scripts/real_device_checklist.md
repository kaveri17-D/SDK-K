# Clipper-X Node SDK & Registry MVP — Real Device Operator Checklist

**Document Version**: 1.0.0-mvp  
**Target Environment**: Production / Staging Host with 30–40 Physical Handsets  
**Network Requirement**: Devices must have HTTP/HTTPS network connectivity to the Clipper-X Host IP.

---

## 1. Overview & Architecture

This checklist guides the QA/Infrastructure operator in connecting **30 to 40 physical smartphones** (Android / iOS) to the Clipper-X Central Node Registry.

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Host Machine (Laptop / Server)                          │
│    - Runs FastAPI Backend + PostgreSQL 16 + Redis 7        │
│    - Serves Central Dashboard at http://<HOST_IP>:8000/dashboard│
└─────────────────────────────────────────────────────────────┘
                               │
                Generates Join Link / QR Code
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Physical Mobile Handset (Phone 1 .. Phone 40)            │
│    - Scans QR Code or opens http://<HOST_IP>:8000/join?token=cne_... │
│    - Auto-detects device platform and model                 │
│    - Clicks "Connect Device"                                │
│    - Receives unique node_id & token                        │
│    - Establishes persistent 30s heartbeat loop (ONLINE)     │
└─────────────────────────────────────────────────────────────┘
                               │
               Every 30s Heartbeat Telemetry
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Central Dashboard Live Display                           │
│    - Total devices count increments                         │
│    - Status: ONLINE | Health: HEALTHY                       │
│    - Observed Public Egress IP recorded                     │
│    - Last Heartbeat shows active pulse                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Pre-Requisite Setup on Host Machine

1. **Obtain Host Machine Local IP Address**:
   ```bash
   # On Linux / macOS:
   hostname -I | awk '{print $1}'
   # Example: 192.168.1.150
   ```

2. **Verify Docker Stack is Healthy**:
   ```bash
   curl -s http://127.0.0.1:8000/api/v1/health
   # Expected response:
   # {"status":"ok","service":"clipper-x-backend","version":"1.0.0","database":"connected","redis":"connected"}
   ```

3. **Open the Central Dashboard**:
   Open browser at: `http://localhost:8000/dashboard` (or `http://<HOST_IP>:8000/dashboard`).

---

## 3. Step-by-Step Device Onboarding Procedure

For each physical phone (Phone 1 through Phone 40):

### Step 1: Generate Join Invitation
1. On the Central Dashboard, click **"+ Create 1-Click Join Link"**.
2. A single-use enrollment URL will be generated:
   `http://<HOST_IP>:8000/join?token=cne_<token>`
3. Click **"Show QR"** to render the QR code modal.

### Step 2: Open Join Link on Mobile Device
1. On the physical phone, open the native Camera app or QR Scanner.
2. Scan the QR code displayed on the host dashboard screen (or send/paste the join URL).
3. The phone's browser opens the `/join?token=...` onboarding page.

### Step 3: Connect the Device
1. The onboarding page automatically detects the mobile platform (e.g., `android`, `ios`) and user agent.
2. The user taps the green **"Connect Device"** button.
3. The browser claims the ticket atomically:
   - Backend registers node into PostgreSQL.
   - Backend issues a unique 16-hex `node_<hex>` identifier and authentication bearer token.
   - Public egress IP is observed and recorded.
   - Initial heartbeat is transmitted.
4. The device UI updates to display:
   - **Status Badge**: `ONLINE` (green)
   - **Node ID**: `node_<hex>`
   - **Observed IP**: `<public_or_local_ip>`
   - **Heartbeat Indicator**: Active pulsing green badge (`ONLINE (N pulses)` every 30s).

### Step 4: Verify on Central Dashboard
1. Look at the Central Dashboard at `http://<HOST_IP>:8000/dashboard`.
2. Within 3 seconds (auto-poll interval):
   - **Total Devices** card increments by 1.
   - **ONLINE** count increments by 1.
   - The device appears in the active table:
     - **Node ID**: matches the phone's issued `node_<hex>`
     - **Device Name**: Phone model (e.g. "Pixel 8 Pro", "iPhone 15", or custom name)
     - **Platform**: `android` / `ios`
     - **Status**: `ONLINE`
     - **Health**: `HEALTHY`
     - **Observed IP**: Matches phone's egress IP
     - **Last Heartbeat**: `Just now` (updates every 30s)

### Step 5: Test Lifecycle Transitions (Optional Sample)
1. Close the browser tab or tap **"Disconnect"** on one test device.
2. Observe dashboard:
   - After **90 seconds**: Status transitions from `ONLINE` to `STALE` (amber).
   - After **180 seconds**: Status transitions from `STALE` to `OFFLINE` (red).
3. Re-open / reconnect the device:
   - Status instantly recovers to `ONLINE` on the next heartbeat.

---

## 4. Physical Device Verification Matrix (30–40 Handsets)

Record each physical device connection during testing:

| # | Device Model / OS | QR Scanned? | Unique Node ID Issued | Status ONLINE | 30s HB Pulse | Dashboard Row | Operator Initials | Pass / Fail |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 2 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 3 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 4 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 5 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 6 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 7 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 8 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 9 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 10 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 11 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 12 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 13 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 14 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 15 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 16 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 17 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 18 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 19 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 20 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 21 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 22 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 23 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 24 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 25 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 26 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 27 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 28 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 29 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 30 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 31 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 32 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 33 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 34 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 35 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 36 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 37 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 38 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 39 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |
| 40 | | [ ] | | [ ] | [ ] | [ ] | | [ ] PASS [ ] FAIL |

---

## 5. Security & Invariant Verification on Devices

- [ ] **Single-Use Replay Protection**: Attempt to open and claim the same join link on a second phone. Ensure it is rejected with `"Enrollment ticket has already been used"`.
- [ ] **Expiration Enforcement**: Generate an invite with short TTL (e.g. 5 minutes). Attempt to claim after expiration. Ensure it is rejected with `"Invalid or expired enrollment ticket"`.
- [ ] **Token Secrecy**: Verify join URL does not contain permanent node credentials (only the short-lived `cne_...` single-use token).
- [ ] **Cross-Device Isolation**: Verify device A cannot modify or ping device B's heartbeat.

---

## 6. Sign-Off & Verdict

- **Total Physical Devices Tested**: `____ / 40`
- **Total Devices Successfully ONLINE**: `____`
- **All Devices Unique IDs**: `[ ] YES  [ ] NO`
- **Zero Memory Leaks Observed on Host**: `[ ] YES  [ ] NO`
- **Final Acceptance Verdict**: `[ ] ACCEPTED  [ ] REJECTED`

**Operator Signature**: _______________________  
**Date**: _______________
