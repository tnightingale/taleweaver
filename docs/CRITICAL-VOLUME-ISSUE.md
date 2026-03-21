# 🚨 CRITICAL: Volume Persistence Issue

**Problem:** Stories are being lost when the container is redeployed in Once.

**Root Cause:** Once creates a new volume for each deployment (e.g., `once-app-taleweaver.0aa21e`, `once-app-taleweaver.a8e8c1`, `once-app-taleweaver.a40d1a`) instead of reusing the same volume.

**Impact:** 
- ❌ All stories lost on redeploy
- ❌ Database reset on update
- ❌ Audio files deleted
- ❌ Library feature unusable

**Evidence:**
```bash
$ docker volume ls | grep taleweaver
once-app-taleweaver.0aa21e  # Old deployment
once-app-taleweaver.a8e8c1  # Another old deployment  
once-app-taleweaver.a40d1a  # Current deployment (empty)
```

---

## Immediate Workaround

**Manual volume migration before updates:**

```bash
# 1. Find current container and volume
CURRENT_CONTAINER=$(docker ps --filter "name=once-app-taleweaver" --format "{{.ID}}")
CURRENT_VOLUME=$(docker inspect $CURRENT_CONTAINER --format '{{range .Mounts}}{{if eq .Destination "/storage"}}{{.Name}}{{end}}{{end}}')

echo "Current volume: $CURRENT_VOLUME"

# 2. Before updating, backup the volume
docker run --rm -v $CURRENT_VOLUME:/source -v taleweaver-backup:/backup alpine cp -r /source/. /backup/

# 3. After update, restore to new volume
NEW_CONTAINER=$(docker ps --filter "name=once-app-taleweaver" --format "{{.ID}}")
NEW_VOLUME=$(docker inspect $NEW_CONTAINER --format '{{range .Mounts}}{{if eq .Destination "/storage"}}{{.Name}}{{end}}{{end}}')

docker stop $NEW_CONTAINER
docker run --rm -v taleweaver-backup:/backup -v $NEW_VOLUME:/target alpine cp -r /backup/. /target/
docker start $NEW_CONTAINER
```

---

## Permanent Solutions

### Option 1: Use Named Volume in Dockerfile (RECOMMENDED)

Modify deployment to use a consistent named volume instead of auto-generated ones.

**Problem:** Once controls volume creation, not the Dockerfile.

### Option 2: External Storage Path

Use a bind mount to a directory outside Docker volumes:

```dockerfile
# In docker-entrypoint.sh or docker-compose
-v /opt/taleweaver-storage:/storage
```

**Problem:** Requires manual setup, not portable.

### Option 3: Backup/Restore Hooks (Already Implemented!)

Our `/hooks/pre-backup` and `/hooks/post-restore` should handle this, but Once might not be calling them properly.

**Action:** Test if hooks are being called:

```bash
docker exec $(docker ps -q --filter "name=once-app-taleweaver") /hooks/pre-backup
docker exec $(docker ps -q --filter "name=once-app-taleweaver") ls -la /storage/backup-snapshot/
```

### Option 4: Once Configuration

Check if Once has a setting to persist volumes across deployments.

Looking at the Once source code, each app gets a unique volume suffix based on the container label. This seems intentional for isolation, but breaks our use case.

---

## Investigation Needed

**Check if your story is in an old volume:**

```bash
# Check all taleweaver volumes for stories
for vol in $(docker volume ls --format '{{.Name}}' | grep taleweaver); do
  echo "=== Checking $vol ==="
  docker run --rm -v $vol:/data python:3.9-slim python -c "
import sqlite3
try:
    conn = sqlite3.connect('/data/taleweaver.db')
    c = conn.cursor()
    c.execute('SELECT short_id, title, kid_name, created_at FROM stories ORDER BY created_at DESC LIMIT 3')
    results = c.fetchall()
    if results:
        print('Found stories:')
        for row in results:
            print(f'  {row[0]} - {row[1]} ({row[2]}) - {row[3]}')
    else:
        print('  (empty)')
except Exception as e:
    print(f'  Error: {e}')
" 2>/dev/null || echo "  (no database)"
done
```

---

## Recommended Action

1. **Immediate:** Find which volume has your story and manually copy it to the current volume
2. **Short-term:** Create a script to consolidate all volumes into one
3. **Long-term:** Investigate Once volume management or switch to manual Docker deployment with named volumes

---

## Volume Consolidation Script

```bash
#!/bin/bash
# Consolidate all taleweaver volumes into the current one

CURRENT=$(docker ps --filter "name=once-app-taleweaver" --format "{{.ID}}")
if [ -z "$CURRENT" ]; then
    echo "No taleweaver container running"
    exit 1
fi

CURRENT_VOL=$(docker inspect $CURRENT --format '{{range .Mounts}}{{if eq .Destination "/storage"}}{{.Name}}{{end}}{{end}}')
echo "Current volume: $CURRENT_VOL"

# Find all taleweaver volumes
for vol in $(docker volume ls --format '{{.Name}}' | grep "once-app-taleweaver" | grep -v "$CURRENT_VOL"); do
    echo "Checking $vol for data..."
    
    # Check if it has stories
    HAS_DATA=$(docker run --rm -v $vol:/data python:3.9-slim python -c "
import sqlite3
try:
    conn = sqlite3.connect('/data/taleweaver.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM stories')
    print(c.fetchone()[0])
except:
    print(0)
" 2>/dev/null)
    
    if [ "$HAS_DATA" -gt 0 ]; then
        echo "  Found $HAS_DATA stories in $vol"
        echo "  Merging to $CURRENT_VOL..."
        
        # Stop current container
        docker stop $CURRENT
        
        # Copy data
        docker run --rm \
            -v $vol:/source \
            -v $CURRENT_VOL:/target \
            alpine sh -c "cp -r /source/stories/* /target/stories/ 2>/dev/null || true; 
                          cp /source/taleweaver.db /target/taleweaver.db.merge 2>/dev/null || true"
        
        # Start container
        docker start $CURRENT
        
        echo "  ⚠️  Manual DB merge needed - both databases copied"
        echo "  $CURRENT_VOL/taleweaver.db (current)"
        echo "  $CURRENT_VOL/taleweaver.db.merge (old data)"
    fi
done
```

---

## Status

**Your story is likely lost** if it was in a previous container that used a different volume.

**Prevention:** We need to solve the volume persistence issue before the library is truly usable.

**Next steps:**
1. Run the investigation script to find if your story exists in any volume
2. Implement volume consolidation
3. Consider switching from Once to manual Docker deployment for better volume control
