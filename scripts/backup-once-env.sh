#!/bin/bash
# Backup Once environment variables for Taleweaver
# This extracts env vars from the running Once container and saves them

set -e

BACKUP_FILE="${1:-./once-env-backup.txt}"

echo "Backing up Once environment variables..."

# Find the taleweaver container
CONTAINER=$(docker ps -a --filter "name=once-app-taleweaver" --format "{{.ID}}" | head -1)

if [ -z "$CONTAINER" ]; then
    echo "❌ No taleweaver container found"
    echo "   Looking for any container with 'taleweaver' in the name..."
    CONTAINER=$(docker ps -a --filter "name=taleweaver" --format "{{.ID}}\t{{.Names}}")
    if [ -n "$CONTAINER" ]; then
        echo "   Found:"
        echo "$CONTAINER"
    fi
    exit 1
fi

echo "✓ Found container: $CONTAINER"

# Extract environment variables
echo "Extracting environment variables..."
docker inspect "$CONTAINER" --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E "^(LLM_PROVIDER|ANTHROPIC_API_KEY|ELEVENLABS_API_KEY|GROQ_API_KEY|OPENAI_API_KEY|NARRATOR_VOICE_ID|CHARACTER_)" > "$BACKUP_FILE"

echo "✓ Environment variables saved to: $BACKUP_FILE"
echo ""
echo "Contents:"
cat "$BACKUP_FILE" | sed 's/=.*/=***REDACTED***/g'
echo ""
echo "To restore, use: ./scripts/restore-once-env.sh $BACKUP_FILE"
