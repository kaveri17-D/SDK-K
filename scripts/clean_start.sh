#!/usr/bin/env bash
set -e

REPO_DIR="/home/system/Desktop/ClipSdk"
export PATH="/home/system/.local/bin:$PATH"
export LD_LIBRARY_PATH="/home/system/.local/lib:$LD_LIBRARY_PATH"

echo "===================================="
echo "CLEAN START: WIPING ALL STATE"
echo "===================================="

bash "$REPO_DIR/scripts/stop_services.sh"
sleep 1

PGDATA="/home/system/.local/var/postgres_data"
REDISDATA="/home/system/.local/var/redis_data"

echo "[CLEAN] Removing previous database and redis data..."
rm -rf "$PGDATA" "$REDISDATA"
rm -f /home/system/.local/var/*.log /home/system/.local/var/*.pid
rm -f /home/system/Desktop/ClipSdk/.clipper-x-state*.json

echo "[CLEAN] Re-initializing services..."
bash "$REPO_DIR/scripts/setup_services.sh"

echo "[CLEAN] Starting services and running migrations..."
bash "$REPO_DIR/scripts/start_services.sh"

echo "===================================="
echo "CLEAN START COMPLETE: ALL VERIFIED"
echo "===================================="
