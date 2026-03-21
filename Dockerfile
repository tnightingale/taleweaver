# syntax=docker/dockerfile:1
# Multi-stage build for Taleweaver - Once-compatible deployment
# Serves frontend + backend on port 80 via Caddy reverse proxy

# ============================================================================
# Stage 1: Build frontend static assets
# ============================================================================
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Build production bundle
COPY frontend/ ./
RUN npm run build

# ============================================================================
# Stage 2: Final production image
# ============================================================================
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (ffmpeg for pydub, curl and gnupg for Caddy install)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        ca-certificates \
        debian-keyring \
        debian-archive-keyring \
        apt-transport-https \
        gnupg && \
    rm -rf /var/lib/apt/lists/*

# Install Caddy web server
RUN curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg && \
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list && \
    apt-get update && \
    apt-get install -y caddy && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ ./

# Copy frontend build from previous stage
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Create storage directories for Once compatibility
# Once mounts a volume to /storage for persistent data
RUN mkdir -p /storage/jobs /storage/music

# Copy default background music to storage
# This serves as the default; can be overridden by mounting custom music
COPY backend/app/data/music /app/default-music

# Create Caddyfile for reverse proxy
# - Serves frontend static files from /app/frontend/dist
# - Proxies /api/* requests to FastAPI backend on :8000
# - Uses try_files to support SPA routing (all routes -> index.html)
RUN printf ':80 {\n\
    root * /app/frontend/dist\n\
    reverse_proxy /api/* localhost:8000\n\
    file_server\n\
    try_files {path} /index.html\n\
}\n' > /etc/caddy/Caddyfile

# Copy entrypoint and hook scripts
COPY docker-entrypoint.sh /docker-entrypoint.sh
COPY hooks/ /hooks/
RUN chmod +x /docker-entrypoint.sh /hooks/*

# Expose port 80 (Once requirement)
EXPOSE 80

# Health check endpoint: /up (Once requirement)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost/up || exit 1

# Use custom entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
