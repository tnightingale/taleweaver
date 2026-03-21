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

# Install system dependencies (ffmpeg for pydub, curl for Caddy install + healthcheck, gnupg for Caddy GPG key)
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
# - Uses handle blocks for explicit routing priority
# - /up and /api/* go to backend, everything else to frontend
RUN printf ':80 {\n\
    handle /up {\n\
        reverse_proxy localhost:8000\n\
    }\n\
    \n\
    handle /api/* {\n\
        reverse_proxy localhost:8000\n\
    }\n\
    \n\
    handle {\n\
        root * /app/frontend/dist\n\
        try_files {path} /index.html\n\
        file_server\n\
    }\n\
}\n' > /etc/caddy/Caddyfile

# Copy entrypoint and hook scripts
COPY docker-entrypoint.sh /docker-entrypoint.sh
COPY hooks/ /hooks/
RUN chmod +x /docker-entrypoint.sh /hooks/*

# Expose port 80 (Once requirement)
EXPOSE 80

# Health check endpoint: /up (Once requirement)
# Longer start-period to allow for initialization
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost/up || exit 1

# Use custom entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
