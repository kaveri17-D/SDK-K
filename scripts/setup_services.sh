#!/usr/bin/env bash
set -e

export PATH="/home/system/.local/bin:$PATH"
export LD_LIBRARY_PATH="/home/system/.local/lib:$LD_LIBRARY_PATH"

PGDATA="/home/system/.local/var/postgres_data"
REDISDATA="/home/system/.local/var/redis_data"

mkdir -p "/home/system/.local/var" "$REDISDATA"

if [ ! -d "$PGDATA" ] || [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "[SETUP] Initializing PostgreSQL cluster at $PGDATA..."
    rm -rf "$PGDATA"
    initdb -D "$PGDATA" --auth=trust -U postgres >/dev/null
    
    # Configure postgres to listen on 127.0.0.1:5432
    cat <<EOF >> "$PGDATA/postgresql.conf"
listen_addresses = '127.0.0.1'
port = 5432
unix_socket_directories = '/home/system/.local/var'
max_connections = 50
EOF
    echo "[SETUP] PostgreSQL initialized."
fi

# Create redis config if not exists
REDISCONF="/home/system/.local/etc/redis.conf"
mkdir -p "/home/system/.local/etc"
cat <<EOF > "$REDISCONF"
port 6379
bind 127.0.0.1
daemonize yes
pidfile /home/system/.local/var/redis.pid
dir $REDISDATA
logfile /home/system/.local/var/redis.log
save ""
EOF

echo "[SETUP] PostgreSQL and Redis configurations ready."
