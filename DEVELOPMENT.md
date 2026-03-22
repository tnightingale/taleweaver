# Development Guide

**Quick Links:** [Standards](#standards) • [Workflows](#workflows) • [Testing](#testing) • [Pull Requests](#pull-requests) • [Database](#database-migrations) • [Docker](#docker) • [Git](#git)

**See also:** 
- [PR_WORKFLOW.md](./docs/PR_WORKFLOW.md) - Pull request guidelines
- [DATABASE_MIGRATIONS.md](./docs/DATABASE_MIGRATIONS.md) - Database migration strategy

---

## Standards

### Development Process (MUST FOLLOW)

**1. Worktrees - One per feature/stage**
```bash
git worktree add ../taleweaver-feature-name -b feature/feature-name
cd ../taleweaver-feature-name
# Work, commit, test
cd /path/to/taleweaver && git merge feature/feature-name && git push
```

**2. Commits - Small, frequent, logical**
- ✅ One logical change per commit
- ✅ Commit after every meaningful change (10-30 commits per feature)
- ❌ Never one big "Add entire feature" commit

**3. TDD - Red, Green, Refactor**
```bash
# Write failing test → Commit
# Implement feature → Commit  
# Refactor if needed → Commit
```

**4. Testing - ALWAYS before push**
```bash
COMPOSE_PROFILES=test docker compose -f docker-compose.dev.yml run --rm backend-test  # All 146 tests must pass
docker build -t taleweaver:test .                                                      # Build must succeed
docker run -d -p 8080:80 taleweaver:test                                              # Container must run
curl http://localhost:8080/up                                                          # Endpoints must work
```

**Note:** GitHub Actions CI runs tests automatically on push. Check status before merging:
```bash
gh pr checks  # If you have a PR
# Or check: https://github.com/YOUR_ORG/taleweaver/actions
```

**5. Docker - All tests/builds**
- Use `docker compose` for consistent Python 3.9 environment
- Never run tests locally (version mismatches)

**6. Documentation - Update with features**
- Update `CLAUDE.md` for API changes
- Update `README.md` for new features
- Create `docs/plans/YYYY-MM-DD-feature-stages.md` for complex features

**7. Large Features - Staged PRs**
- Break into logical stages (see [PR_WORKFLOW.md](./docs/PR_WORKFLOW.md))
- Create PR for each stage or group of related stages
- Each stage in separate worktree
- Track progress in stages document
- Example: Illustration feature has 5 PRs for 8 stages

### For Other Developers/Agents

**Before starting:**
```bash
git worktree list                              # Check active work
ls docs/plans/*-stages.md                     # Check ongoing features  
docker compose run --rm backend-test          # Verify baseline
```

**When working:**
- ✅ Create worktree (don't work in main)
- ✅ Follow TDD
- ✅ Commit frequently
- ✅ Test before merge
- ✅ Update docs

**DON'T:**
- ❌ Work in main branch
- ❌ Large commits
- ❌ Skip tests
- ❌ Push broken builds
- ❌ Modify other worktrees

---

## Workflows

### Quick Start

**Local development:**
```bash
# Backend: cd backend && uvicorn app.main:app --reload
# Frontend: cd frontend && npm run dev
```

**Production-like:**
```bash
docker compose up app  # Access at http://localhost
```

### Run Tests

```bash
# All tests
docker compose run --rm backend-test

# Specific tests
docker compose run --rm backend-test sh -c \
  ". /tmp/venv/bin/activate && pytest tests/test_specific.py -v"
```

### Add Feature (Example)

```bash
# 1. Create worktree
git worktree add ../taleweaver-new-feature -b feature/new-feature
cd ../taleweaver-new-feature

# 2. Create stages plan
cat > docs/plans/2026-03-XX-feature-stages.md << 'PLAN'
# Feature - Stages
Stage 1: Backend API (4 tasks)
Stage 2: Frontend UI (6 tasks)
Stage 3: Integration (3 tasks)
PLAN

# 3. For each stage:
#    - Write RED tests
#    - Implement GREEN
#    - Commit frequently
#    - Merge to main
#    - Create new worktree for next stage

# 4. Test production build
docker build -t taleweaver:test .

# 5. Merge final stage
cd /path/to/taleweaver
git merge feature/new-feature
git push origin main
```

### Feature Template

**Small feature (<2 hours):**
1. Create worktree
2. TDD implementation
3. Test build
4. Merge & push

**Large feature (>2 hours):**
1. Create stages plan document
2. For each stage:
   - Create separate worktree
   - TDD implementation
   - Merge & push
   - Update stages doc
3. Final testing & documentation

---

## Testing

### Backend Tests

```bash
# All tests (use this most often) - MUST pass before pushing
COMPOSE_PROFILES=test docker compose -f docker-compose.dev.yml run --rm backend-test

# Specific file
COMPOSE_PROFILES=test docker compose -f docker-compose.dev.yml run --rm backend-test sh -c \
  "python -m venv /tmp/venv && . /tmp/venv/bin/activate && \
   pip install -q -r requirements.txt && \
   apt-get update -qq && apt-get install -qq -y ffmpeg > /dev/null 2>&1 && \
   python -m pytest tests/test_story_library.py -v"
```

**Current test count:** 146 tests (must all pass before pushing)

**Test Isolation:**
- All tests use isolated database fixtures from `conftest.py`
- Each test gets a fresh temporary database (no state sharing)
- Use `test_db` fixture for database access
- Use `test_client` fixture for API endpoint testing

### Frontend Build

```bash
cd frontend
npm run build  # Must succeed before push
```

### Production Container

```bash
# Build
docker build -t taleweaver:test .

# Run
docker run --rm -d -p 8080:80 \
  -e LLM_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=test \
  -e ELEVENLABS_API_KEY=test \
  taleweaver:test

# Test endpoints
curl http://localhost:8080/up              # Health
curl http://localhost:8080/api/stories     # Library API
curl http://localhost:8080/                # Frontend

# Clean up
docker stop $(docker ps -q --filter ancestor=taleweaver:test)
```

---

## Database Migrations

**Auto-Migration System:**
- Migrations run automatically on container startup
- No manual SQL execution required
- Safe, idempotent, logged

**See:** [DATABASE_MIGRATIONS.md](./docs/DATABASE_MIGRATIONS.md) for complete guide

**Quick Reference:**

```bash
# Add new migration (edit this file)
backend/app/db/migrate.py

# Test locally
docker compose up app
# Check logs for: "✅ Created table: your_table"

# Deploy
git push origin main  # CI builds, Once auto-updates, migrations run

# Verify in production
once logs taleweaver | grep migration
```

**Current migrations:**
1. Illustration fields (art_style, has_illustrations, scene_data)
2. Job state table (job_state with indexes)

---

## Docker

### Docker Compose Services

```bash
# Production-like (default)
docker compose up app

# Development (auto-reload)
docker compose --profile dev up backend-dev frontend-dev

# Run tests
docker compose run --rm backend-test
```

### Volumes

- `taleweaver-storage` - Persistent data (database + audio)
- `backend-dev-venv`, `backend-test-venv` - Python environments
- `frontend-node-modules` - NPM dependencies

---

## Git

### Worktree Pattern

```bash
# List worktrees
git worktree list

# Create
git worktree add ../taleweaver-{feature} -b feature/{feature}

# Remove
git worktree remove ../taleweaver-{feature}
```

### Commit Pattern

```bash
# Stage-by-stage for large features
git add file1.py
git commit -m "Add function X"

git add file2.py  
git commit -m "Add test for X"

git add file3.py
git commit -m "Add API endpoint for X"
```

### Before Pushing

```bash
# 1. All tests pass
docker compose run --rm backend-test

# 2. Production build succeeds
docker build -t taleweaver:test .

# 3. Endpoints work
docker run -d -p 8080:80 taleweaver:test
curl http://localhost:8080/up

# 4. Push
git push origin main
```

---

## Building and Deploying

### Local Build

```bash
docker build -t taleweaver:test .
```

### GitHub Actions

Automatic on push to main:
- Builds multi-platform (amd64 + arm64)
- Runs tests
- Publishes to ghcr.io

Monitor: https://github.com/tnightingale/taleweaver/actions

### Once Deployment

```bash
# Update to latest
# Wait for GitHub Actions build to complete
# Then update via Once TUI or redeploy

# Backup env vars first
./scripts/backup-once-env.sh
```

---

## Common Tasks

### Add Backend Endpoint

```bash
# 1. Worktree
git worktree add ../taleweaver-endpoint -b feature/endpoint

# 2. RED test
# Edit tests/test_endpoint.py
docker compose run --rm backend-test  # Should fail
git commit -m "Add RED test"

# 3. GREEN implementation
# Edit app/routes/...
docker compose run --rm backend-test  # Should pass
git commit -m "Implement endpoint"

# 4. Test build
docker build -t taleweaver:test .

# 5. Merge
cd /path/to/taleweaver && git merge feature/endpoint && git push
```

### Add Frontend Component

```bash
# 1. Create component
# Edit frontend/src/components/NewComponent.tsx
git commit -m "Add NewComponent"

# 2. Test build
cd frontend && npm run build

# 3. Test in container
docker build -t taleweaver:test .

# 4. Push
git push origin main
```

### Fix Bug

```bash
# 1. Write test that reproduces bug (RED)
# 2. Fix bug (GREEN)
# 3. Verify test passes
# 4. Test production build
# 5. Commit & push
```

---

## Debugging

### Backend Logs

```bash
# Local
docker compose logs -f backend-dev

# Once deployment
docker logs $(docker ps -q --filter "name=once-app-taleweaver")
```

### Database Inspection

```bash
# In running container
docker exec -it $(docker ps -q --filter "name=once-app-taleweaver") \
  sqlite3 /storage/taleweaver.db

# List stories
sqlite> SELECT short_id, title, kid_name FROM stories ORDER BY created_at DESC LIMIT 10;
```

### API Testing

```bash
curl http://localhost/up                    # Health
curl http://localhost/api/status            # Config
curl http://localhost/api/stories           # Library
curl http://localhost/api/permalink/abc123  # Story metadata
```

---

## Project Structure

```
taleweaver/
├── backend/
│   ├── app/
│   │   ├── db/              # SQLAlchemy models, CRUD
│   │   ├── graph/           # LangGraph pipeline
│   │   ├── routes/          # FastAPI routes
│   │   └── main.py          # App entry, permalink routes
│   └── tests/               # 137 pytest tests
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── routes/          # Route wrappers
│   │   └── api/client.ts    # API calls
│   └── package.json
├── docs/plans/              # Implementation plans & stages
├── scripts/                 # Backup/restore scripts
├── Dockerfile               # Production build
└── docker-compose.dev.yml   # Dev environments
```

---

## Key Files

**Backend:**
- `app/main.py` - FastAPI app, permalink routes, library routes
- `app/routes/story.py` - Story generation endpoints
- `app/db/` - Database layer (models, CRUD)
- `app/graph/` - LangGraph story pipeline

**Frontend:**
- `src/App.tsx` - Router setup
- `src/routes/` - Route components (HeroRoute, CraftRoute, etc.)
- `src/components/` - UI components
- `src/api/client.ts` - API client

**Infrastructure:**
- `Dockerfile` - Production build (Caddy + FastAPI + Frontend)
- `docker-compose.dev.yml` - Dev/test environments
- `docker-entrypoint.sh` - Container startup
- `hooks/` - Once backup/restore

---

## Tips

- Use `docker compose run --rm backend-test` frequently
- Commit after every logical change
- Test production build before pushing
- Break large features into stages
- Update documentation as you go
- Keep worktrees short-lived (<1 day)

---

## Resources

- FastAPI: https://fastapi.tiangolo.com
- React Router: https://reactrouter.com
- LangGraph: https://langchain-ai.github.io/langgraph/
- Once: https://github.com/basecamp/once
