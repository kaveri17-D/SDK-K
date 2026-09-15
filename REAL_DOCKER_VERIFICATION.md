# Real Docker Integration Verification Runbook

This guide contains the exact, step-by-step instructions to verify the **Clipper-X Node SDK + Node Registry (V1)** on a developer machine with **Docker Desktop** (Linux, macOS, or Windows).

---

## Current Status

```
CODE VERIFICATION          : PASS (17/17 backend pytest cases, 12/12 SDK unit tests passed)
REAL DOCKER VERIFICATION   : PENDING (to be executed on host with Docker Desktop)
PRODUCTION READINESS       : NOT YET VERIFIED
```

---

## Prerequisites

- **Docker & Docker Compose**: Docker Desktop 4.x+ or Docker Engine 24+
- **Node.js**: v18.0.0+ and npm 9+
- **Terminal**: Bash (Linux/macOS) or PowerShell (Windows)

---

## 1. Clean Docker Startup

Wipe any previous container volumes and start fresh instances of PostgreSQL, Redis, and the FastAPI backend.

### Bash (Linux / macOS)
```bash
# 1. Stop any running containers and remove volumes
docker compose down -v

# 2. Build and start services in background
docker compose up --build -d

# 3. Wait for containers to reach healthy status
docker compose ps
```

### Windows PowerShell
```powershell
# 1. Stop any running containers and remove volumes
docker compose down -v

# 2. Build and start services in background
docker compose up --build -d

# 3. Wait for containers to reach healthy status
docker compose ps
```

---

## 2. Infrastructure Health Checks

Verify that PostgreSQL, Redis, and the FastAPI backend are fully operational and communicating.

### Bash (Linux / macOS)
```bash
# A. PostgreSQL health
docker exec -it clipper-x-postgres pg_isready -U postgres -d clipper_x

# B. Redis health
docker exec -it clipper-x-redis redis-cli ping

# C. Backend API health
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
```

### Windows PowerShell
```powershell
# A. PostgreSQL health
docker exec -it clipper-x-postgres pg_isready -U postgres -d clipper_x

# B. Redis health
docker exec -it clipper-x-redis redis-cli ping

# C. Backend API health
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" | ConvertTo-Json
```

*Expected output*: `status: "ok"`, `database: "connected"`, `redis: "connected"`.

---

## 3. Database Migration Verification

The backend automatically executes `alembic -c backend/alembic.ini upgrade head` upon container startup. Verify the migration table:

### Bash (Linux / macOS)
```bash
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c "SELECT version_num FROM alembic_version;"
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c "\d nodes"
```

### Windows PowerShell
```powershell
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c "SELECT version_num FROM alembic_version;"
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c "\d nodes"
```

*Expected output*: Version `001_initial_nodes` and the complete `nodes` schema.

---

## 4. Node Registration & State Rule Verification

State Rule: **Registration must set the node to `REGISTERING`. Only upon the first valid authenticated heartbeat does it transition to `ONLINE`.**

### Bash (Linux / macOS)
```bash
# 1. Register a new node
REG_RESP=$(curl -s -X POST http://localhost:8000/api/v1/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"platform":"linux","sdk_version":"1.0.0","device_name":"docker-node-1"}')

echo "$REG_RESP" | python3 -m json.tool

NODE_ID=$(echo "$REG_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['node_id'])")
NODE_TOKEN=$(echo "$REG_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

# 2. Verify initial status is REGISTERING (NOT ONLINE)
curl -s "http://localhost:8000/api/v1/nodes/$NODE_ID" | python3 -m json.tool

# 3. Check persistent PostgreSQL record
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c \
  "SELECT node_id, status, last_heartbeat_at, created_at FROM nodes WHERE node_id = '$NODE_ID';"

# 4. Check Redis runtime cache
docker exec -it clipper-x-redis redis-cli HGETALL "node:heartbeat:$NODE_ID"
```

### Windows PowerShell
```powershell
# 1. Register a new node
$body = @{
    platform = "windows"
    sdk_version = "1.0.0"
    device_name = "docker-node-1"
} | ConvertTo-Json

$reg = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/register" -Method Post -ContentType "application/json" -Body $body
$reg | ConvertTo-Json

$NODE_ID = $reg.node_id
$NODE_TOKEN = $reg.token

# 2. Verify initial status is REGISTERING
$node = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE_ID"
$node | ConvertTo-Json

# 3. Check persistent PostgreSQL record
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c "SELECT node_id, status, last_heartbeat_at, created_at FROM nodes WHERE node_id = '$NODE_ID';"

# 4. Check Redis runtime cache
docker exec -it clipper-x-redis redis-cli HGETALL "node:heartbeat:$NODE_ID"
```

---

## 5. First Heartbeat: `REGISTERING` &rarr; `ONLINE` Transition

### Bash (Linux / macOS)
```bash
# 1. Send first authenticated heartbeat
curl -s -X POST "http://localhost:8000/api/v1/nodes/$NODE_ID/heartbeat" \
  -H "Authorization: Bearer $NODE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sdk_version":"1.0.0","health":{"network":true}}' | python3 -m json.tool

# 2. Verify status is now ONLINE
curl -s "http://localhost:8000/api/v1/nodes/$NODE_ID" | python3 -m json.tool

# 3. Inspect updated last_heartbeat_at in PostgreSQL
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c \
  "SELECT node_id, status, last_heartbeat_at FROM nodes WHERE node_id = '$NODE_ID';"
```

### Windows PowerShell
```powershell
# 1. Send first authenticated heartbeat
$hbBody = @{
    sdk_version = "1.0.0"
    health = @{ network = $true }
} | ConvertTo-Json

$headers = @{ Authorization = "Bearer $NODE_TOKEN" }
$hbRes = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE_ID/heartbeat" -Method Post -Headers $headers -ContentType "application/json" -Body $hbBody
$hbRes | ConvertTo-Json

# 2. Verify status is now ONLINE
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE_ID" | ConvertTo-Json

# 3. Inspect updated last_heartbeat_at in PostgreSQL
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c "SELECT node_id, status, last_heartbeat_at FROM nodes WHERE node_id = '$NODE_ID';"
```

---

## 6. STALE & OFFLINE Transitions and Recovery

Verify the background worker transitions inactive nodes to `STALE` (> 90s), then `OFFLINE` (> 180s), and that a restored heartbeat recovers the node back to `ONLINE`.

### Bash (Linux / macOS)
```bash
# 1. Fast-forward last_heartbeat_at by 100 seconds to trigger STALE
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c \
  "UPDATE nodes SET last_heartbeat_at = NOW() - INTERVAL '100 seconds' WHERE node_id = '$NODE_ID';"

# Wait 12 seconds for the background worker (check interval is 10s)
sleep 12

# Verify node is now STALE
curl -s "http://localhost:8000/api/v1/nodes/$NODE_ID" | python3 -m json.tool

# 2. Fast-forward last_heartbeat_at by 200 seconds to trigger OFFLINE
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c \
  "UPDATE nodes SET last_heartbeat_at = NOW() - INTERVAL '200 seconds' WHERE node_id = '$NODE_ID';"

sleep 12

# Verify node is now OFFLINE
curl -s "http://localhost:8000/api/v1/nodes/$NODE_ID" | python3 -m json.tool

# 3. RECOVERY: Send new authenticated heartbeat
curl -s -X POST "http://localhost:8000/api/v1/nodes/$NODE_ID/heartbeat" \
  -H "Authorization: Bearer $NODE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sdk_version":"1.0.0"}' | python3 -m json.tool

# Verify node recovered immediately to ONLINE
curl -s "http://localhost:8000/api/v1/nodes/$NODE_ID" | python3 -m json.tool
```

### Windows PowerShell
```powershell
# 1. Fast-forward last_heartbeat_at by 100 seconds to trigger STALE
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c "UPDATE nodes SET last_heartbeat_at = NOW() - INTERVAL '100 seconds' WHERE node_id = '$NODE_ID';"

Start-Sleep -Seconds 12

# Verify node is now STALE
(Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE_ID").status

# 2. Fast-forward last_heartbeat_at by 200 seconds to trigger OFFLINE
docker exec -it clipper-x-postgres psql -U postgres -d clipper_x -c "UPDATE nodes SET last_heartbeat_at = NOW() - INTERVAL '200 seconds' WHERE node_id = '$NODE_ID';"

Start-Sleep -Seconds 12

# Verify node is now OFFLINE
(Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE_ID").status

# 3. RECOVERY: Send new authenticated heartbeat
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE_ID/heartbeat" -Method Post -Headers $headers -ContentType "application/json" -Body $hbBody

# Verify node recovered immediately to ONLINE
(Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE_ID").status
```

---

## 7. Security: Authentication & Cross-Node Authorization

Verify that unauthenticated requests return `401 Unauthorized` and cross-node tampering returns `403 Forbidden`.

### Bash (Linux / macOS)
```bash
# 1. Register Node 2
REG2=$(curl -s -X POST http://localhost:8000/api/v1/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"platform":"linux","sdk_version":"1.0.0","device_name":"docker-node-2"}')
NODE2_ID=$(echo "$REG2" | python3 -c "import sys, json; print(json.load(sys.stdin)['node_id'])")
NODE2_TOKEN=$(echo "$REG2" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

# 2. Unauthenticated request: must return HTTP 401
curl -s -o /dev/null -w "No Auth HTTP Status: %{http_code}\n" \
  -X POST "http://localhost:8000/api/v1/nodes/$NODE_ID/heartbeat" \
  -H "Content-Type: application/json" \
  -d '{"sdk_version":"1.0.0"}'

# 3. Invalid token: must return HTTP 401
curl -s -o /dev/null -w "Bad Token HTTP Status: %{http_code}\n" \
  -X POST "http://localhost:8000/api/v1/nodes/$NODE_ID/heartbeat" \
  -H "Authorization: Bearer cnx_tok_bogus_token_12345" \
  -H "Content-Type: application/json" \
  -d '{"sdk_version":"1.0.0"}'

# 4. Cross-node tampering (Node 1 token used to update Node 2): must return HTTP 403
curl -s -o /dev/null -w "Cross-Node HTTP Status: %{http_code}\n" \
  -X POST "http://localhost:8000/api/v1/nodes/$NODE2_ID/heartbeat" \
  -H "Authorization: Bearer $NODE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sdk_version":"1.0.0"}'
```

### Windows PowerShell
```powershell
# 1. Register Node 2
$reg2 = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/register" -Method Post -ContentType "application/json" -Body (@{ platform = "windows"; sdk_version = "1.0.0"; device_name = "docker-node-2" } | ConvertTo-Json)
$NODE2_ID = $reg2.node_id
$NODE2_TOKEN = $reg2.token

# 2. Unauthenticated request: must return 401
try {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE_ID/heartbeat" -Method Post -ContentType "application/json" -Body (@{ sdk_version = "1.0.0" } | ConvertTo-Json)
} catch {
    Write-Host "No Auth HTTP Status: $($_.Exception.Response.StatusCode.value__)"
}

# 3. Invalid token: must return 401
try {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE_ID/heartbeat" -Method Post -Headers @{ Authorization = "Bearer cnx_tok_invalid_fake" } -ContentType "application/json" -Body (@{ sdk_version = "1.0.0" } | ConvertTo-Json)
} catch {
    Write-Host "Bad Token HTTP Status: $($_.Exception.Response.StatusCode.value__)"
}

# 4. Cross-node tampering: must return 403
try {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE2_ID/heartbeat" -Method Post -Headers @{ Authorization = "Bearer $NODE_TOKEN" } -ContentType "application/json" -Body (@{ sdk_version = "1.0.0" } | ConvertTo-Json)
} catch {
    Write-Host "Cross-Node HTTP Status: $($_.Exception.Response.StatusCode.value__)"
}
```

---

## 8. Network Telemetry: Public IP & Controlled Bandwidth

### Bash (Linux / macOS)
```bash
# 1. Public IP observation
curl -s http://localhost:8000/api/v1/network/ip | python3 -m json.tool

# 2. Download bandwidth test (2 MB payload)
curl -s -w "\nDownloaded %{size_download} bytes in %{time_total}s\n" \
  http://localhost:8000/api/v1/network/speed-test?size_mb=2 -o /dev/null

# 3. Upload bandwidth test (1 MB upload)
head -c 1048576 /dev/zero | curl -s -X POST http://localhost:8000/api/v1/network/speed-test/upload \
  -H "Content-Type: application/octet-stream" \
  --data-binary @- | python3 -m json.tool
```

### Windows PowerShell
```powershell
# 1. Public IP observation
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/network/ip" | ConvertTo-Json

# 2. Download bandwidth test (2 MB payload)
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$dl = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/network/speed-test?size_mb=2"
$sw.Stop()
Write-Host "Downloaded $($dl.RawContentLength) bytes in $($sw.ElapsedMilliseconds) ms"

# 3. Upload bandwidth test
$ulData = New-Object byte[] (1024 * 1024)
$ulRes = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/network/speed-test/upload" -Method Post -ContentType "application/octet-stream" -Body $ulData
$ulRes | ConvertTo-Json
```

---

## 9. Testing 3 Concurrent SDK Nodes

Build the TypeScript SDK and launch 3 concurrent demo instances with isolated state files.

### Bash (Linux / macOS)
```bash
cd sdk
npm install
npm run build

# Run 3 instances in parallel with isolated state files
CLIPPER_X_API_URL="http://localhost:8000" STATE_FILE_PATH=".state-node-1.json" DEVICE_NAME="worker-node-1" MAX_HEARTBEATS=3 npm run demo &
CLIPPER_X_API_URL="http://localhost:8000" STATE_FILE_PATH=".state-node-2.json" DEVICE_NAME="worker-node-2" MAX_HEARTBEATS=3 npm run demo &
CLIPPER_X_API_URL="http://localhost:8000" STATE_FILE_PATH=".state-node-3.json" DEVICE_NAME="worker-node-3" MAX_HEARTBEATS=3 npm run demo &

wait
cd ..

# Verify all 3 nodes appear in backend registry
curl -s http://localhost:8000/api/v1/nodes | python3 -m json.tool
```

### Windows PowerShell
```powershell
Set-Location sdk
npm install
npm run build

# Run 3 instances in parallel with isolated state files
$p1 = Start-Process -NoNewWindow -PassThru -FilePath "npm" -ArgumentList "run demo" -Environment @{ CLIPPER_X_API_URL="http://localhost:8000"; STATE_FILE_PATH=".state-node-1.json"; DEVICE_NAME="worker-node-1"; MAX_HEARTBEATS="3" }
$p2 = Start-Process -NoNewWindow -PassThru -FilePath "npm" -ArgumentList "run demo" -Environment @{ CLIPPER_X_API_URL="http://localhost:8000"; STATE_FILE_PATH=".state-node-2.json"; DEVICE_NAME="worker-node-2"; MAX_HEARTBEATS="3" }
$p3 = Start-Process -NoNewWindow -PassThru -FilePath "npm" -ArgumentList "run demo" -Environment @{ CLIPPER_X_API_URL="http://localhost:8000"; STATE_FILE_PATH=".state-node-3.json"; DEVICE_NAME="worker-node-3"; MAX_HEARTBEATS="3" }

$p1.WaitForExit()
$p2.WaitForExit()
$p3.WaitForExit()
Set-Location ..

# Verify all 3 nodes appear in backend registry
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes" | ConvertTo-Json
```

---

## 10. Fault-Tolerance: Restart Services & Verify Persistence

Verify system resilience against service crashes and restarts.

### Bash (Linux / macOS)
```bash
# 1. Restart Redis container
docker compose restart redis
sleep 3
# Verify Redis is back and heartbeat succeeds
curl -s -X POST "http://localhost:8000/api/v1/nodes/$NODE_ID/heartbeat" \
  -H "Authorization: Bearer $NODE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sdk_version":"1.0.0"}' | python3 -m json.tool

# 2. Restart Backend container
docker compose restart backend
sleep 5
# Verify persistent PostgreSQL records survived backend restart
curl -s "http://localhost:8000/api/v1/nodes/$NODE_ID" | python3 -m json.tool
```

### Windows PowerShell
```powershell
# 1. Restart Redis container
docker compose restart redis
Start-Sleep -Seconds 3
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE_ID/heartbeat" -Method Post -Headers $headers -ContentType "application/json" -Body $hbBody | ConvertTo-Json

# 2. Restart Backend container
docker compose restart backend
Start-Sleep -Seconds 5
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nodes/$NODE_ID" | ConvertTo-Json
```

---

## 11. Clean Teardown

Stop and remove all containers, networks, and named storage volumes.

### Bash (Linux / macOS)
```bash
docker compose down -v
rm -f sdk/.state-node-*.json .clipper-x-state*.json
```

### Windows PowerShell
```powershell
docker compose down -v
Remove-Item -Path "sdk/.state-node-*.json", ".clipper-x-state*.json" -Force -ErrorAction SilentlyContinue
```
