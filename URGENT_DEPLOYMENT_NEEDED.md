# URGENT: Critical Fix Needs Deployment

**Date:** 2026-03-23 03:06 UTC  
**Status:** 🔴 CRITICAL FIX IN MAIN BUT NOT DEPLOYED

---

## Problem

**Production Server:**
- Running OLD image (March 22, 20:01 PDT)
- Has database connection churn bug
- **Causing server deadlocks and timeouts**
- Users cannot load pages, get "took too long to respond"

**Critical Fix:**
- ✅ In main branch (commit 40a5f91)
- ❌ NOT in Docker image
- ❌ NOT deployed to production

---

## Root Cause

**Missing CI/CD Pipeline:**
- GitHub Actions workflow exists (`.github/workflows/test.yml`)
- But only runs TESTS, doesn't build/push Docker images
- No automatic deployment to ghcr.io registry
- Once can only deploy images from registry

---

## Immediate Action Required

### Manual Build & Push (5 minutes)

```bash
# 1. Build Docker image
docker build -t ghcr.io/tnightingale/taleweaver:latest .

# 2. Push to registry
docker push ghcr.io/tnightingale/taleweaver:latest

# 3. Wait for Once auto-update (5 min)
# Or force update:
docker pull ghcr.io/tnightingale/taleweaver:latest
# Once will detect and deploy
```

---

## What the Fix Does

**Before (Current Production):**
- Creates 20+ database connections per job
- Connection exhaustion with concurrent jobs
- All workers deadlock
- Server completely unresponsive

**After (Main Branch - Not Deployed):**
- Reuses single database connection per job
- Eliminates 95% of connection churn
- Workers remain available
- Server responsive during generation

---

## Files Changed (Not Yet Deployed)

**Critical Commits Not in Production:**
1. `40a5f91` - Database connection churn fix (CRITICAL)
2. `3a4e9cf` - Progress display fixes
3. `98ba26c` - Voice resilience
4. All resilience work from today

**Currently Running:**
- March 22 code
- Before all resilience fixes
- Before database connection fix

---

## Verification After Deployment

```bash
# Check image has fix
docker run --rm ghcr.io/tnightingale/taleweaver:latest \
  grep -r 'state\["_db"\]' /app/backend/

# Should output: state["_db"] = db

# Check Once deployed it
docker ps | grep once-app-taleweaver
# Check image ID matches latest

# Test server
curl http://taleweaver.lan/up
# Should respond quickly (<100ms)
```

---

## Long-Term Solution

**Add Build/Deploy to CI:**

Create `.github/workflows/deploy.yml`:
```yaml
name: Build and Deploy

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:latest
```

---

**IMMEDIATE ACTION NEEDED: Build and push Docker image manually to deploy critical server fix!**
