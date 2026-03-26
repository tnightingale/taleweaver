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

# Start huey background worker (processes story generation jobs)
# -k process: isolated process per task (memory doesn't leak into API)
# -w 1: one concurrent story at a time (controls peak memory)
echo "⚙️ Starting huey background worker..."
huey_consumer app.jobs.huey_app.huey \
  -k process \
  -w ${HUEY_WORKERS:-1} \
  --logfile /dev/stdout \
  &
HUEY_PID=$!

# Start gunicorn (serves API + frontend static assets on port 80)
# No background tasks in gunicorn — those run in huey above.
# Timeout 120s is plenty for API requests (no long-running generation).
echo "🚀 Starting Gunicorn on port 80..."
gunicorn app.main:app \
  --workers ${GUNICORN_WORKERS:-4} \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:80 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  &
GUNICORN_PID=$!

# Forward SIGTERM to both processes on container stop.
# Without this, only PID 1 (this shell) gets the signal —
# gunicorn and huey would be orphaned until SIGKILL.
shutdown() {
    echo "🛑 Shutting down..."
    kill -TERM $GUNICORN_PID $HUEY_PID 2>/dev/null
    wait $GUNICORN_PID $HUEY_PID 2>/dev/null
}
trap shutdown TERM INT

# Wait for either process to exit. If one crashes, stop both.
wait -n $GUNICORN_PID $HUEY_PID
EXIT_CODE=$?
echo "⚠️ Process exited with code $EXIT_CODE, shutting down..."
shutdown
exit $EXIT_CODE
