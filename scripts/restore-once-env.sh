#!/bin/bash
# Restore Once environment variables for Taleweaver
# This shows you the docker run command with saved env vars

set -e

BACKUP_FILE="${1:-./once-env-backup.txt}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Environment variables from backup:"
echo "=================================="
cat "$BACKUP_FILE"
echo ""
echo "To deploy with these settings, use:"
echo ""
echo "docker run -d --name once-app-taleweaver \\"
echo "  --network once \\"
echo "  --label 'once={\"host\":\"taleweaver.lan\",\"image\":\"ghcr.io/tnightingale/taleweaver:latest\"}' \\"
echo "  -v once-taleweaver-storage:/storage \\"

while IFS= read -r line; do
    echo "  -e $line \\"
done < "$BACKUP_FILE"

echo "  ghcr.io/tnightingale/taleweaver:latest"
echo ""
echo "Then register with proxy:"
echo "CONTAINER_ID=\$(docker ps --filter \"name=once-app-taleweaver\" --format \"{{.ID}}\")"
echo "docker exec once-proxy kamal-proxy deploy taleweaver --host taleweaver.lan --target \$CONTAINER_ID"
