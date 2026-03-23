#!/bin/bash
set -e

echo "🎭 Starting Taleweaver..."

# Initialize storage directories if they don't exist
mkdir -p /storage/jobs
mkdir -p /storage/music

# Copy default background music if storage/music is empty
if [ ! "$(ls -A /storage/music)" ]; then
    echo "📦 Initializing background music library..."
    cp -r /app/default-music/* /storage/music/
fi

# Start Caddy web server in background
echo "🌐 Starting Caddy web server on port 80..."
caddy start --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 || {
    echo "❌ Failed to start Caddy. Checking logs..."
    cat /var/log/caddy/* 2>/dev/null || echo "No Caddy logs available"
    exit 1
}

# Give Caddy a moment to start
sleep 3

# Verify Caddy is running
if ! caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile; then
    echo "❌ Caddy config validation failed"
    exit 1
fi

# Start FastAPI backend server with gunicorn for production
echo "🚀 Starting FastAPI backend on port 8000..."
# Use gunicorn with uvicorn workers for concurrent request handling.
# 2 workers: each story generation can peak at ~100-200MB, so 2 workers
# keeps memory under control on small VPS/Once instances while still
# allowing concurrent story generation. Background tasks (asyncio.create_task)
# run on the worker's event loop — blocking work is offloaded to thread pools.
# Timeout set to 600s (10 min) for long-running story generation.
exec gunicorn app.main:app \
  --workers ${GUNICORN_WORKERS:-2} \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 600 \
  --access-logfile - \
  --error-logfile -
