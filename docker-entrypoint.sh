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
caddy start --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1

# Give Caddy a moment to start
sleep 2

# Start FastAPI backend server
echo "🚀 Starting FastAPI backend on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
