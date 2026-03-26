# syntax=docker/dockerfile:1
# Multi-stage build for Story Spring - Once-compatible deployment
# Serves frontend + backend on port 80 via Gunicorn (FastAPI serves static assets directly)

# ============================================================================
# Stage 1a: Frontend base (Node + npm deps installed)
# Shared by both tests and production build to avoid reinstalling every run.
# ============================================================================
FROM node:20-slim AS frontend-base

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy source (needed by both test and build)
COPY frontend/ ./

# ============================================================================
# Stage 1b: Build frontend static assets (production bundle)
# ============================================================================
FROM frontend-base AS frontend-build

RUN npm run build

# ============================================================================
# Stage 2: Backend base (Python + ffmpeg + pip deps)
# Shared by both tests and production to avoid reinstalling every run.
# ============================================================================
FROM python:3.9-slim AS backend-base

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 3: Final production image
# ============================================================================
FROM backend-base AS production

# Install curl for health check (not needed for tests)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

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
