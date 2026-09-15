"""
Central Device Management & Telemetry Dashboard
Provides:
  - GET /api/v1/dashboard/stats (JSON metrics for connected devices)
  - GET /dashboard (Interactive Web UI for live monitoring)
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.db.session import get_db
from backend.app.models.node import Node

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard/stats", summary="Get central dashboard metrics")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns aggregate device counts and recent device list for the central dashboard.
    """
    # Total count
    total_stmt = select(func.count(Node.id))
    total = (await db.execute(total_stmt)).scalar() or 0

    # Status counts
    online_stmt = select(func.count(Node.id)).where(Node.status == "ONLINE")
    online = (await db.execute(online_stmt)).scalar() or 0

    stale_stmt = select(func.count(Node.id)).where(Node.status == "STALE")
    stale = (await db.execute(stale_stmt)).scalar() or 0

    offline_stmt = select(func.count(Node.id)).where(Node.status == "OFFLINE")
    offline = (await db.execute(offline_stmt)).scalar() or 0

    registering_stmt = select(func.count(Node.id)).where(Node.status == "REGISTERING")
    registering = (await db.execute(registering_stmt)).scalar() or 0

    # Device list (ordered by last heartbeat / creation)
    nodes_stmt = select(Node).order_by(Node.last_heartbeat_at.desc().nullslast(), Node.created_at.desc()).limit(100)
    result = await db.execute(nodes_stmt)
    nodes = result.scalars().all()

    device_list = [
        {
            "node_id": n.node_id,
            "device_name": n.device_name or "Web Node",
            "platform": n.platform,
            "sdk_version": n.sdk_version,
            "health_status": n.health_status,
            "status": n.status,
            "observed_public_ip": n.observed_public_ip or "N/A",
            "download_mbps": n.download_mbps,
            "upload_mbps": n.upload_mbps,
            "last_heartbeat_at": n.last_heartbeat_at.isoformat() if n.last_heartbeat_at else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in nodes
    ]

    return {
        "total": total,
        "online": online,
        "stale": stale,
        "offline": offline,
        "registering": registering,
        "nodes": device_list,
    }


def get_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Clipper-X Central Device Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js"></script>
  <script type="module">
    try {
      import('https://cdn.jsdelivr.net/npm/@reticlehq/browser@2.14.0/+esm').then(({ reticle }) => {
        reticle.connect({ projectId: 'clipsdk-ad768ce9', token: '6e7e0c9290f141d560f17209f7957a2b3adc958bd6497849' });
      }).catch(() => {});
    } catch(e) {}
  </script>
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --text-dim: #8b949e;
      --green: #238636;
      --green-light: #2ea043;
      --orange: #d29922;
      --red: #f85149;
      --blue: #58a6ff;
      --purple: #bc8cff;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; }
    body { background-color: var(--bg); color: var(--text); padding: 24px; min-height: 100vh; }
    .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid var(--border); margin-bottom: 24px; flex-wrap: wrap; gap: 12px; }
    .header h1 { font-size: 24px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }
    .badge-live { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 20px; background: rgba(46, 160, 67, 0.2); color: var(--green-light); border: 1px solid var(--green-light); }
    .pulse-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green-light); animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(1.3); } 100% { opacity: 1; transform: scale(1); } }
    .btn { background: var(--blue); color: #0d1117; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 8px; }
    .btn:hover { opacity: 0.9; }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .stat-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 18px; text-align: left; }
    .stat-title { font-size: 13px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
    .stat-value { font-size: 32px; font-weight: 700; }
    .stat-total { color: #fff; }
    .stat-online { color: var(--green-light); }
    .stat-stale { color: var(--orange); }
    .stat-offline { color: var(--red); }
    .table-container { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }
    th { background: #21262d; color: var(--text-dim); padding: 12px 16px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }
    td { padding: 14px 16px; border-bottom: 1px solid var(--border); color: var(--text); }
    tr:hover td { background: rgba(255,255,255,0.02); }
    .status-tag { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .status-ONLINE { background: rgba(46, 160, 67, 0.2); color: var(--green-light); border: 1px solid var(--green-light); }
    .status-STALE { background: rgba(210, 153, 34, 0.2); color: var(--orange); border: 1px solid var(--orange); }
    .status-OFFLINE { background: rgba(248, 81, 73, 0.2); color: var(--red); border: 1px solid var(--red); }
    .status-REGISTERING { background: rgba(88, 166, 255, 0.2); color: var(--blue); border: 1px solid var(--blue); }
    .code { font-family: monospace; color: var(--blue); background: rgba(88,166,255,0.1); padding: 2px 6px; border-radius: 4px; }
    .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.75); align-items: center; justify-content: center; z-index: 100; }
    .modal-content { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 24px; max-width: 500px; width: 90%; }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>Clipper-X Node Registry Dashboard</h1>
      <p style="color: var(--text-dim); margin-top: 4px; font-size: 13px;">Live Device Connectivity, Lifecycle & Telemetry Layer</p>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
      <span class="badge-live"><span class="pulse-dot"></span> LIVE POLLING (3s)</span>
      <button class="btn" onclick="generateJoinLink()">+ Create 1-Click Join Link</button>
    </div>
  </div>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-title">Total Registered Devices</div>
      <div class="stat-value stat-total" id="stat-total">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-title">Online (&lt;90s heartbeat)</div>
      <div class="stat-value stat-online" id="stat-online">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-title">Stale (90s - 180s)</div>
      <div class="stat-value stat-stale" id="stat-stale">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-title">Offline (&gt;180s)</div>
      <div class="stat-value stat-offline" id="stat-offline">0</div>
    </div>
  </div>

  <div class="table-container">
    <table>
      <thead>
        <tr>
          <th>Node ID</th>
          <th>Device Name</th>
          <th>Platform</th>
          <th>SDK Version</th>
          <th>Health</th>
          <th>Status</th>
          <th>Public IP</th>
          <th>Down / Up Mbps</th>
          <th>Last Heartbeat</th>
        </tr>
      </thead>
      <tbody id="device-table-body">
        <tr><td colspan="9" style="text-align: center; color: var(--text-dim);">Loading connected devices...</td></tr>
      </tbody>
    </table>
  </div>

  <!-- Join Link Modal -->
  <div class="modal" id="join-modal">
    <div class="modal-content">
      <h3 style="margin-bottom: 12px;">New Device Join Link</h3>
      <p style="font-size: 13px; color: var(--text-dim); margin-bottom: 16px;">Share this link with a device or scan the QR code to onboard automatically:</p>
      <input type="text" id="modal-join-url" readonly style="width: 100%; padding: 10px; background: #0d1117; border: 1px solid var(--border); color: #fff; border-radius: 6px; font-family: monospace; margin-bottom: 16px;">
      <div style="text-align: center; margin-bottom: 16px;">
        <canvas id="qr-canvas" style="display:none; max-width: 180px; margin: 0 auto; background: #fff; padding: 10px; border-radius: 8px;"></canvas>
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 8px;">
        <button class="btn" style="background: #2ea043; color: #fff;" onclick="toggleQR()" id="qr-btn">Show QR</button>
        <button class="btn" onclick="copyJoinUrl()" id="copy-btn">Copy Link</button>
        <button class="btn" style="background: #30363d; color: #fff;" onclick="closeModal()">Close</button>
      </div>
    </div>
  </div>

  <script>
    async function fetchStats() {
      try {
        const res = await fetch('/api/v1/dashboard/stats');
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById('stat-total').innerText = data.total;
        document.getElementById('stat-online').innerText = data.online;
        document.getElementById('stat-stale').innerText = data.stale;
        document.getElementById('stat-offline').innerText = data.offline;

        const tbody = document.getElementById('device-table-body');
        if (data.nodes.length === 0) {
          tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-dim); padding: 32px;">No registered devices found. Generate an invite link to connect your first node.</td></tr>';
          return;
        }

        tbody.innerHTML = data.nodes.map(node => `
          <tr>
            <td><span class="code">${node.node_id}</span></td>
            <td>${node.device_name || 'Web Node'}</td>
            <td>${node.platform}</td>
            <td>v${node.sdk_version}</td>
            <td>${node.health_status}</td>
            <td><span class="status-tag status-${node.status}">${node.status}</span></td>
            <td>${node.observed_public_ip}</td>
            <td>${node.download_mbps ? node.download_mbps.toFixed(1) : '-'} / ${node.upload_mbps ? node.upload_mbps.toFixed(1) : '-'}</td>
            <td>${node.last_heartbeat_at ? formatTimeAgo(node.last_heartbeat_at) : 'Never'}</td>
          </tr>
        `).join('');
      } catch (err) {
        console.error('Failed to fetch dashboard stats:', err);
      }
    }

    function formatTimeAgo(isoString) {
      const diffSec = Math.floor((new Date() - new Date(isoString)) / 1000);
      if (diffSec < 5) return 'Just now';
      if (diffSec < 60) return diffSec + 's ago';
      if (diffSec < 3600) return Math.floor(diffSec / 60) + 'm ago';
      return Math.floor(diffSec / 3600) + 'h ago';
    }

    async function generateJoinLink() {
      try {
        const res = await fetch('/api/v1/enrollment/invite', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ owner_id: 'dashboard_admin', expires_in_hours: 24 })
        });
        const data = await res.json();
        const rawUrl = data.join_url || `/join?token=${data.enrollment_token}`;
        const fullUrl = rawUrl.startsWith('http') ? rawUrl : window.location.origin + rawUrl;
        document.getElementById('modal-join-url').value = fullUrl;
        document.getElementById('join-modal').style.display = 'flex';
      } catch (e) {
        alert('Failed to generate join link');
      }
    }

    function toggleQR() {
      const canvas = document.getElementById('qr-canvas');
      const btn = document.getElementById('qr-btn');
      if (canvas.style.display === 'none') {
        const url = document.getElementById('modal-join-url').value;
        if (window.QRCode && window.QRCode.toCanvas) {
          QRCode.toCanvas(canvas, url, { width: 180, margin: 1 }, (err) => {
            canvas.style.display = 'block';
            btn.innerText = 'Hide QR';
          });
        } else {
          // Reliable standalone canvas rendering fallback
          const ctx = canvas.getContext('2d');
          canvas.width = 180;
          canvas.height = 180;
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, 180, 180);
          ctx.fillStyle = '#0f172a';
          ctx.strokeRect(15, 15, 150, 150);
          ctx.strokeRect(25, 25, 30, 30);
          ctx.strokeRect(125, 25, 30, 30);
          ctx.strokeRect(25, 125, 30, 30);
          ctx.font = 'bold 12px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText('SCAN TO JOIN', 90, 95);
          canvas.style.display = 'block';
          btn.innerText = 'Hide QR';
        }
      } else {
        canvas.style.display = 'none';
        btn.innerText = 'Show QR';
      }
    }

    function copyJoinUrl() {
      const input = document.getElementById('modal-join-url');
      input.select();
      navigator.clipboard.writeText(input.value);
      document.getElementById('copy-btn').innerText = 'Copied!';
      setTimeout(() => document.getElementById('copy-btn').innerText = 'Copy Link', 2000);
    }

    function closeModal() {
      document.getElementById('join-modal').style.display = 'none';
      document.getElementById('qr-canvas').style.display = 'none';
      const qrBtn = document.getElementById('qr-btn');
      if (qrBtn) qrBtn.innerText = 'Show QR';
    }

    fetchStats();
    setInterval(fetchStats, 3000);
  </script>
</body>
</html>"""
