#!/usr/bin/env bash

export PATH="/home/system/.local/bin:$PATH"
export LD_LIBRARY_PATH="/home/system/.local/lib:$LD_LIBRARY_PATH"

PGDATA="/home/system/.local/var/postgres_data"
LOG_DIR="/home/system/.local/var"

echo "[STOP] Stopping backend..."
if [ -f "$LOG_DIR/backend.pid" ]; then
    PID=$(cat "$LOG_DIR/backend.pid")
    kill "$PID" 2>/dev/null || true
    rm -f "$LOG_DIR/backend.pid"
fi
pkill -f "uvicorn backend.app.main:app" 2>/dev/null || true

echo "[STOP] Stopping Redis..."
if [ -f "$LOG_DIR/redis.pid" ]; then
    PID=$(cat "$LOG_DIR/redis.pid")
    kill "$PID" 2>/dev/null || true
    rm -f "$LOG_DIR/redis.pid"
fi
redis-cli -p 6379 shutdown 2>/dev/null || true
pkill -f "redis-server" 2>/dev/null || true

echo "[STOP] Stopping PostgreSQL..."
pg_ctl -D "$PGDATA" stop -m fast 2>/dev/null || true
pkill -f "postgres" 2>/dev/null || true

echo "✓ All services stopped."
