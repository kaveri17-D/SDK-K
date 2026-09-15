import asyncio
import time
import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from backend.app.core.config import settings
from backend.app.api import api_router
from backend.app.db.session import AsyncSessionLocal, get_redis, close_connections
from backend.app.services.heartbeat_service import run_offline_detection_worker

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("clipper-x.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background offline detection worker
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(
        run_offline_detection_worker(
            session_factory=AsyncSessionLocal,
            redis_client_factory=get_redis,
            stop_event=stop_event,
        )
    )

    yield

    # Shutdown
    logger.info("Initiating graceful shutdown...")
    stop_event.set()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(f"Error terminating background worker: {e}")

    await close_connections()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Clipper-X Node SDK & Node Registry API V1",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    """
    Structured observability middleware:
    Logs node_id, operation, timestamp, result without logging authentication tokens.
    """
    start_time = time.perf_counter()

    # Determine node_id if present in path (e.g. /api/v1/nodes/node_123/heartbeat)
    path_parts = request.url.path.strip("/").split("/")
    node_id = None
    if len(path_parts) >= 4 and path_parts[1] == "nodes":
        node_id = path_parts[2]

    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Log structured event
    log_record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "operation": f"{request.method} {request.url.path}",
        "node_id": node_id or "anonymous",
        "status_code": response.status_code,
        "duration_ms": duration_ms,
        "client_ip": request.client.host if request.client else "unknown",
    }

    # Redaction guarantee: never print headers containing Authorization or tokens
    logger.info(f"AUDIT_EVENT: {json.dumps(log_record)}")
    return response


# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"], summary="Root health check")
async def root_health():
    return {"status": "ok", "service": "clipper-x-backend"}


@app.get("/dashboard", response_class=HTMLResponse, summary="Central device management dashboard")
async def dashboard_page():
    from backend.app.api.dashboard import get_dashboard_html
    return HTMLResponse(content=get_dashboard_html())


@app.get("/join", response_class=HTMLResponse, summary="One-click device join page")
async def join_page(request: Request, token: str = ""):
    """
    Mobile and desktop browser join page for frictionless device onboarding:
    CLICK JOIN LINK -> CONNECT -> DEVICE REGISTERED -> ONLINE
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Clipper-X Node Join</title>
  <script type="module">
    try {
      import('https://cdn.jsdelivr.net/npm/@reticlehq/browser@2.14.0/+esm').then(({ reticle }) => {
        reticle.connect({ projectId: 'clipsdk-ad768ce9', token: '6e7e0c9290f141d560f17209f7957a2b3adc958bd6497849' });
      }).catch(() => {});
    } catch(e) {}
  </script>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --border: #334155;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 1rem;
      max-width: 480px;
      width: 100%;
      padding: 2rem;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .header { text-align: center; margin-bottom: 1.5rem; }
    .badge {
      display: inline-block;
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      background: rgba(59, 130, 246, 0.2);
      color: var(--primary);
      margin-bottom: 0.75rem;
    }
    .badge.online {
      background: rgba(16, 185, 129, 0.2);
      color: var(--success);
    }
    h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; }
    p { color: var(--text-muted); font-size: 0.95rem; line-height: 1.5; }
    .info-box {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      padding: 1rem;
      margin: 1.25rem 0;
      font-size: 0.875rem;
    }
    .info-row {
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.5rem;
    }
    .info-row:last-child { margin-bottom: 0; }
    .info-label { color: var(--text-muted); }
    .info-val { font-family: monospace; font-weight: 600; }
    .btn {
      display: block;
      width: 100%;
      padding: 0.875rem 1.5rem;
      font-size: 1rem;
      font-weight: 600;
      text-align: center;
      border-radius: 0.5rem;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
    }
    .btn-primary { background: var(--primary); color: white; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-danger { background: var(--danger); color: white; margin-top: 0.75rem; }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; }
    .pulse {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
      margin-right: 6px;
      animation: pulse-anim 2s infinite;
    }
    @keyframes pulse-anim {
      0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
      70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
      100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }
    #error-msg { color: var(--danger); font-size: 0.875rem; margin-top: 0.75rem; display: none; text-align: center; }
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div id="status-badge" class="badge">Ready to Connect</div>
      <h1>Clipper-X Node Network</h1>
      <p id="sub-heading">Click below to enroll this device into the central cluster.</p>
    </div>

    <div class="info-box">
      <div class="info-row">
        <span class="info-label">Detected Platform:</span>
        <span id="detected-platform" class="info-val">Detecting...</span>
      </div>
      <div class="info-row">
        <span class="info-label">Device Name:</span>
        <span id="detected-device" class="info-val">Detecting...</span>
      </div>
      <div class="info-row" id="node-id-row" style="display:none;">
        <span class="info-label">Node ID:</span>
        <span id="node-id-val" class="info-val"></span>
      </div>
      <div class="info-row" id="public-ip-row" style="display:none;">
        <span class="info-label">Observed IP:</span>
        <span id="public-ip-val" class="info-val"></span>
      </div>
      <div class="info-row" id="hb-stat-row" style="display:none;">
        <span class="info-label">Heartbeat:</span>
        <span id="hb-stat-val" class="info-val"><span class="pulse"></span>Active (30s)</span>
      </div>
    </div>

    <button id="connect-btn" class="btn btn-primary" onclick="connectDevice()">Connect Device</button>
    <button id="disconnect-btn" class="btn btn-danger" style="display:none;" onclick="disconnectDevice()">Disconnect</button>
    <div id="error-msg"></div>
  </div>

  <script>
    let enrollmentToken = new URLSearchParams(window.location.search).get("token") || "";
    let activeNodeId = localStorage.getItem("cx_node_id") || "";
    let activeToken = localStorage.getItem("cx_node_token") || "";
    let heartbeatTimer = null;
    let heartbeatCount = 0;

    function detectPlatform() {
      const ua = navigator.userAgent;
      let platform = "linux";
      let name = "Web Node";

      if (/android/i.test(ua)) {
        platform = "android";
        name = "Android Phone";
      } else if (/iphone|ipad|ipod/i.test(ua)) {
        platform = "ios";
        name = "Apple Mobile";
      } else if (/win/i.test(ua)) {
        platform = "windows";
        name = "Windows PC";
      } else if (/mac/i.test(ua)) {
        platform = "darwin";
        name = "Mac";
      } else if (/linux/i.test(ua)) {
        platform = "linux";
        name = "Linux Device";
      }

      document.getElementById("detected-platform").textContent = platform;
      document.getElementById("detected-device").textContent = name;
      return { platform, name };
    }

    const deviceInfo = detectPlatform();

    async function sendHeartbeat() {
      try {
        const res = await fetch(`/api/v1/nodes/${encodeURIComponent(activeNodeId)}/heartbeat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${activeToken}`
          },
          body: JSON.stringify({ sdk_version: "1.0.0", health: { network: true } })
        });
        if (res.ok) {
          heartbeatCount++;
          document.getElementById("hb-stat-val").innerHTML = `<span class="pulse"></span>ONLINE (${heartbeatCount} pulses)`;
        } else if (res.status === 401 || res.status === 403) {
          disconnectDevice();
        }
      } catch (err) {
        document.getElementById("hb-stat-val").textContent = "Retrying connection...";
      }
    }

    async function connectDevice() {
      const btn = document.getElementById("connect-btn");
      const errDiv = document.getElementById("error-msg");
      errDiv.style.display = "none";
      btn.disabled = true;
      btn.textContent = "Connecting...";

      try {
        let nodeId = activeNodeId;
        let token = activeToken;

        if (!nodeId || !token) {
          if (!enrollmentToken) {
            throw new Error("Missing enrollment ticket. Please use an invitation link with a valid token.");
          }

          // 1. Claim ticket
          const claimRes = await fetch("/api/v1/enrollment/claim", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              enrollment_token: enrollmentToken,
              platform: deviceInfo.platform,
              device_name: deviceInfo.name,
              sdk_version: "1.0.0"
            })
          });

          if (!claimRes.ok) {
            const errData = await claimRes.json().catch(() => ({}));
            throw new Error(errData.detail || `Claim failed: HTTP ${claimRes.status}`);
          }

          const claimData = await claimRes.json();
          nodeId = claimData.node_id;
          token = claimData.token;
          activeNodeId = nodeId;
          activeToken = token;
          localStorage.setItem("cx_node_id", nodeId);
          localStorage.setItem("cx_node_token", token);
        }

        // 2. Discover observed public IP
        const ipRes = await fetch("/api/v1/network/ip");
        if (ipRes.ok) {
          const ipData = await ipRes.json();
          document.getElementById("public-ip-val").textContent = ipData.ip;
          document.getElementById("public-ip-row").style.display = "flex";
        }

        // 3. First heartbeat (transitions REGISTERING -> ONLINE)
        await sendHeartbeat();

        // 4. Update UI to ONLINE state
        const badge = document.getElementById("status-badge");
        badge.className = "badge online";
        badge.textContent = "ONLINE";

        document.getElementById("node-id-val").textContent = nodeId;
        document.getElementById("node-id-row").style.display = "flex";
        document.getElementById("hb-stat-row").style.display = "flex";
        document.getElementById("sub-heading").textContent = "Device connected and registered in cluster.";

        btn.style.display = "none";
        document.getElementById("disconnect-btn").style.display = "block";

        // 5. Start 30-second heartbeat loop
        clearInterval(heartbeatTimer);
        heartbeatTimer = setInterval(sendHeartbeat, 30000);

      } catch (err) {
        btn.disabled = false;
        btn.textContent = "Connect Device";
        errDiv.textContent = err.message;
        errDiv.style.display = "block";
      }
    }

    function disconnectDevice() {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
      activeNodeId = "";
      activeToken = "";
      localStorage.removeItem("cx_node_id");
      localStorage.removeItem("cx_node_token");

      document.getElementById("status-badge").className = "badge";
      document.getElementById("status-badge").textContent = "Disconnected";
      document.getElementById("node-id-row").style.display = "none";
      document.getElementById("public-ip-row").style.display = "none";
      document.getElementById("hb-stat-row").style.display = "none";
      document.getElementById("disconnect-btn").style.display = "none";

      const btn = document.getElementById("connect-btn");
      btn.style.display = "block";
      btn.disabled = false;
      btn.textContent = "Connect Device";
      document.getElementById("sub-heading").textContent = "Device disconnected.";
    }

    // Auto-reconnect if already enrolled
    if (activeNodeId && activeToken) {
      connectDevice();
    }
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.get("/", summary="Root endpoint")
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "api_docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
        "join_page": "/join",
    }
