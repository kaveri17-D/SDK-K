#!/usr/bin/env bash
set -e

REPO_DIR="/home/system/Desktop/ClipSdk"
export PATH="/home/system/.local/bin:$PATH"
export LD_LIBRARY_PATH="/home/system/.local/lib:$LD_LIBRARY_PATH"
export PYTHONPATH="$REPO_DIR"

PGDATA="/home/system/.local/var/postgres_data"
REDISCONF="/home/system/.local/etc/redis.conf"
LOG_DIR="/home/system/.local/var"
mkdir -p "$LOG_DIR"

# Ensure services are initialized
bash "$REPO_DIR/scripts/setup_services.sh"

# Start PostgreSQL if not already running
if ! pg_isready -h 127.0.0.1 -p 5432 -U postgres >/dev/null 2>&1; then
    echo "[START] Starting PostgreSQL on port 5432..."
    pg_ctl -D "$PGDATA" -l "$LOG_DIR/postgres.log" start
    sleep 2
    # Create clipper_x database if needed
    createdb -h 127.0.0.1 -p 5432 -U postgres clipper_x 2>/dev/null || true
fi

# Start Redis if not already running
if ! redis-cli -p 6379 ping >/dev/null 2>&1; then
    echo "[START] Starting Redis on port 6379..."
    redis-server "$REDISCONF"
    sleep 1
fi

echo "[CHECK] Verifying dependency health..."
pg_isready -h 127.0.0.1 -p 5432 -U postgres
redis-cli -p 6379 ping

echo "[MIGRATE] Running Alembic migrations..."
cd "$REPO_DIR"
DATABASE_URL="postgresql+asyncpg://postgres@127.0.0.1:5432/clipper_x" \
SYNC_DATABASE_URL="postgresql://postgres@127.0.0.1:5432/clipper_x" \
alembic -c backend/alembic.ini upgrade head

# Start FastAPI backend if not running
if ! curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
    echo "[START] Starting Clipper-X FastAPI Backend on http://127.0.0.1:8000..."
    DATABASE_URL="postgresql+asyncpg://postgres@127.0.0.1:5432/clipper_x" \
    SYNC_DATABASE_URL="postgresql://postgres@127.0.0.1:5432/clipper_x" \
    REDIS_URL="redis://127.0.0.1:6379/0" \
    NODE_TOKEN_SECRET="clipper_x_production_token_secret_replace_in_prod" \
    HEARTBEAT_INTERVAL_SECONDS=5 \
    STALE_AFTER_SECONDS=15 \
    OFFLINE_AFTER_SECONDS=30 \
    OFFLINE_CHECK_INTERVAL_SECONDS=2 \
    BANDWIDTH_TEST_SIZE_MB=5 \
    BANDWIDTH_MAX_UPLOAD_MB=10 \
    nohup uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$LOG_DIR/backend.pid"
    
    # Wait for backend to be healthy
    for i in {1..20}; do
        if curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done
fi

echo "[HEALTH] Backend health response:"
curl -s http://127.0.0.1:8000/api/v1/health | python3 -m json.tool
echo "✓ All services are UP and HEALTHY."
