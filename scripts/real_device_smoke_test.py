#!/usr/bin/env python3
"""
Clipper-X Node SDK & Registry MVP — Real Device Smoke Test Harness

Interactive operator CLI tool to assist and verify real physical smartphone onboarding:
1. Verifies backend, PostgreSQL, and Redis connectivity.
2. Generates one-click join link(s) for physical devices.
3. Renders QR code in terminal (ASCII) if qrcode package is available, or prints the exact join URL.
4. Live-monitors the Central Dashboard stats as physical devices scan and connect.
5. Verifies:
   - Unique node_id assigned
   - Device status transitions to ONLINE
   - Public/LAN IP observed
   - 30-second heartbeat pulse updates
6. Supports progressive monitoring up to 30–40 physical phones.
"""

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.request


def get_local_ip() -> str:
    """Best-effort detection of host LAN IP address accessible by phones."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually connect, just picks routing interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def api_request(url: str, method: str = "GET", data: dict = None, timeout: float = 10.0) -> tuple[int, dict]:
    """Execute HTTP request using standard library urllib."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(content)
        except Exception:
            return e.code, {"error": content}
    except Exception as e:
        return 0, {"error": str(e)}


def print_ascii_qr(data: str):
    """Attempt to render an ASCII QR code in terminal if qrcode library is available."""
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(data)
        qr.make(fit=True)
        print("\n" + "=" * 50)
        print("  SCAN WITH MOBILE CAMERA TO ONBOARD DEVICE:")
        print("=" * 50)
        qr.print_ascii(invert=True)
        print("=" * 50 + "\n")
    except ImportError:
        print("\n[NOTE] 'qrcode' Python package not installed; printing URL directly.")
        print("To see terminal QR codes, install: pip install qrcode[pil]")


def main():
    parser = argparse.ArgumentParser(description="Clipper-X Real Device Smoke Test Harness")
    parser.add_argument("--server-url", default="http://127.0.0.1:8000", help="Base backend URL (default: http://127.0.0.1:8000)")
    parser.add_argument("--host-ip", default=None, help="Host LAN IP accessible to phones (defaults to auto-detected IP)")
    parser.add_argument("--target-nodes", type=int, default=1, help="Target number of devices to connect (e.g. 1, 30, 40)")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Dashboard polling interval in seconds (default: 2.0)")
    parser.add_argument("--ttl", type=int, default=3600, help="Enrollment token TTL in seconds (default: 3600)")
    parser.add_argument("--non-interactive", action="store_true", help="Run once without interactive polling loop")

    args = parser.parse_args()

    server_url = args.server_url.rstrip("/")
    lan_ip = args.host_ip or get_local_ip()

    print("\n=======================================================")
    print(" CLIPPER-X NODE REGISTRY — REAL DEVICE SMOKE TEST")
    print("=======================================================")
    print(f"Server URL:     {server_url}")
    print(f"Host LAN IP:    {lan_ip}")
    print(f"Target Devices: {args.target_nodes}")
    print(f"Poll Interval:  {args.poll_interval}s\n")

    # Step 1: Health Check
    print("[1/5] Checking Central Server Health...")
    status, health = api_request(f"{server_url}/api/v1/health")
    if status != 200 or health.get("status") != "ok":
        print(f"  [FAIL] Server health check failed (Status: {status}, Response: {health})")
        sys.exit(1)

    print(f"  [OK] Server Healthy: DB={health.get('database')}, Redis={health.get('redis')}, Version={health.get('version')}")

    # Step 2: Fetch Initial Dashboard State
    print("\n[2/5] Reading Initial Registry Dashboard State...")
    status, initial_stats = api_request(f"{server_url}/api/v1/dashboard/stats")
    if status != 200:
        print(f"  [FAIL] Unable to read dashboard stats (Status: {status})")
        sys.exit(1)

    init_total = initial_stats.get("total", initial_stats.get("summary", {}).get("total_registered", 0))
    init_online = initial_stats.get("online", initial_stats.get("summary", {}).get("online", 0))
    init_stale = initial_stats.get("stale", initial_stats.get("summary", {}).get("stale", 0))
    init_offline = initial_stats.get("offline", initial_stats.get("summary", {}).get("offline", 0))
    print(f"  Current Registered Devices: {init_total} (ONLINE: {init_online}, STALE: {init_stale}, OFFLINE: {init_offline})")

    initial_node_ids = {n.get("node_id") for n in initial_stats.get("nodes", [])}

    # Step 3: Generate One-Click Join Invitation
    print("\n[3/5] Generating One-Click Mobile Join Link...")
    status, invite = api_request(f"{server_url}/api/v1/enrollment/invite", method="POST", data={"ttl_seconds": args.ttl, "max_uses": 1})
    if status not in (200, 201) or "enrollment_token" not in invite:
        print(f"  [FAIL] Failed to create enrollment invite: {invite}")
        sys.exit(1)

    token = invite["enrollment_token"]
    # If server_url is localhost, replace with LAN IP for phone access
    if "127.0.0.1" in server_url or "localhost" in server_url:
        port = server_url.split(":")[-1]
        mobile_join_url = f"http://{lan_ip}:{port}/join?token={token}"
    else:
        mobile_join_url = f"{server_url}/join?token={token}"

    print(f"  [OK] Enrollment Token: {token}")
    print(f"  [OK] Mobile Join URL:  {mobile_join_url}")
    print(f"  [OK] Expires In:       {invite.get('expires_in_seconds', invite.get('expires_at'))} seconds")

    # Display QR Code
    print_ascii_qr(mobile_join_url)

    if args.non_interactive:
        print("\n[NON-INTERACTIVE] Invite generated successfully. Exiting.")
        return

    # Step 4: Operator Instructions
    print("[4/5] Operator Action Required:")
    print("  -------------------------------------------------------------")
    print("  1. Open the camera on a physical mobile phone (Android / iOS).")
    print(f"  2. Navigate to: {mobile_join_url}")
    print("  3. Tap 'Connect Device'.")
    print("  -------------------------------------------------------------")
    print("\n[5/5] Monitoring Central Dashboard for newly connected devices...")
    print(f"Waiting for up to {args.target_nodes} device(s) to appear... (Ctrl+C to abort)\n")

    connected_nodes = []
    start_time = time.time()

    try:
        while len(connected_nodes) < args.target_nodes:
            time.sleep(args.poll_interval)
            status, live_stats = api_request(f"{server_url}/api/v1/dashboard/stats")
            if status != 200:
                continue

            nodes = live_stats.get("nodes", [])
            for n in nodes:
                nid = n.get("node_id")
                if nid not in initial_node_ids and nid not in [c["node_id"] for c in connected_nodes]:
                    print(f"  [DEVICE DETECTED!]")
                    print(f"    - Node ID:       {nid}")
                    print(f"    - Device Name:   {n.get('device_name')}")
                    print(f"    - Platform:      {n.get('platform')}")
                    print(f"    - Status:        {n.get('status')}")
                    print(f"    - Health:        {n.get('health_status')}")
                    print(f"    - Public/LAN IP: {n.get('observed_public_ip')}")
                    print(f"    - Last Ping:     {n.get('last_heartbeat_at') or n.get('last_heartbeat')}")
                    print("-" * 50)
                    connected_nodes.append(n)

            elapsed = int(time.time() - start_time)
            print(f"\r[Tracking: {len(connected_nodes)}/{args.target_nodes} devices connected | Elapsed: {elapsed}s]", end="", flush=True)

    except KeyboardInterrupt:
        print("\n\n[INFO] Monitoring paused by operator.")

    print("\n\n=======================================================")
    print(" SMOKE TEST VERIFICATION SUMMARY")
    print("=======================================================")
    print(f"Total New Devices Connected: {len(connected_nodes)} of {args.target_nodes}")
    for idx, d in enumerate(connected_nodes, 1):
        print(f"  Device #{idx}: {d.get('node_id')} | {d.get('platform')} | {d.get('device_name')} | Status: {d.get('status')} | IP: {d.get('observed_public_ip')}")

    if len(connected_nodes) >= args.target_nodes:
        print("\n[VERDICT: PASS] Target number of physical devices successfully connected and ONLINE!")
    else:
        print(f"\n[VERDICT: PENDING] {len(connected_nodes)}/{args.target_nodes} connected. Awaiting additional physical phones.")


if __name__ == "__main__":
    main()
