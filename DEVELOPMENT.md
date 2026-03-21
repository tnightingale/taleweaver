# Development Guide

This guide covers development workflows, testing strategies, and deployment procedures for Taleweaver.

## Table of Contents

- [Quick Start](#quick-start)
- [Development Workflows](#development-workflows)
- [Testing](#testing)
- [Docker Compose Environments](#docker-compose-environments)
- [Git Workflow](#git-workflow)
- [Building and Deploying](#building-and-deploying)

---

## Quick Start

### Local Development (Fastest)

```bash
# Terminal 1: Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Production-like Environment (Recommended)

Test exactly how it will run in Once deployment:

```bash
# Build and run complete stack (Caddy + FastAPI + Frontend)
docker compose up app

# Access at http://localhost
```

This matches the Once deployment environment exactly.

---

## Development Workflows

### Active Development with Auto-reload

Use the dev profile for hot-reloading during development:

```bash
# Start backend + frontend with auto-reload
docker compose --profile dev up backend-dev frontend-dev

# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

### Testing Changes Before Deployment

Always test with the production-like container before deploying:

```bash
# Build fresh image
docker compose build app

# Run production-like stack
docker compose up app

# Test at http://localhost
# Verify:
# - Health check: curl http://localhost/up
# - API: curl http://localhost/api/status
# - Frontend: open http://localhost in browser
# - Permalinks: create a story, verify /s/{short_id} works
```

---

## Testing

### Run All Tests

```bash
# Using docker-compose (recommended - consistent Python 3.9 environment)
docker compose run --rm backend-test

# Or using Docker directly
docker run --rm -v $(pwd)/backend:/app -w /app python:3.9-slim \
  sh -c "apt-get update -qq && apt-get install -qq -y ffmpeg && \
         pip install -q -r requirements.txt && \
         python -m pytest tests/ -v"
```

### Run Specific Tests

```bash
# Database persistence tests
docker compose run --rm backend-test \
  sh -c "python -m venv /tmp/venv && . /tmp/venv/bin/activate && \
         apt-get update -qq && apt-get install -qq -y ffmpeg && \
         pip install -q -r requirements.txt && \
         python -m pytest tests/test_story_persistence*.py -v"

# Permalink API tests
docker compose run --rm backend-test \
  sh -c "python -m venv /tmp/venv && . /tmp/venv/bin/activate && \
         apt-get update -qq && apt-get install -qq -y ffmpeg && \
         pip install -q -r requirements.txt && \
         python -m pytest tests/test_story_permalink*.py -v"

# Single test
docker compose run --rm backend-test \
  sh -c "python -m venv /tmp/venv && . /tmp/venv/bin/activate && \
         apt-get update -qq && apt-get install -qq -y ffmpeg && \
         pip install -q -r requirements.txt && \
         python -m pytest tests/test_story_routes.py::test_create_custom_story_returns_job -v"
```

### Test Coverage

Current test coverage:
- **121 tests** across 15 test files
- Database persistence (10 tests)
- Permalink API (5 tests)
- Integration tests (4 tests)
- Pipeline, prompts, audio stitching, voice synthesis
- Route handlers and models

---

## Docker Compose Environments

### Service Profiles

**Default (no profile):**
- `app` - Production-like single container (Caddy + FastAPI + Frontend)
- `backend-test` - Test runner

**`dev` profile:**
- `backend-dev` - Backend with auto-reload
- `frontend-dev` - Frontend with hot-reload

**`test` profile:**
- `backend-test` - On-demand test runner

### Commands

```bash
# Production-like (default)
docker compose up app

# Development mode
docker compose --profile dev up backend-dev frontend-dev

# Run tests
docker compose run --rm backend-test

# Or run specific test profile
docker compose --profile test run backend-test
```

### Volumes

- `taleweaver-storage` - Persistent data (database + audio files)
- `backend-dev-venv` - Python virtual environment (dev mode)
- `backend-test-venv` - Test environment dependencies
- `frontend-node-modules` - Frontend dependencies (dev mode)

---

## Git Workflow

### Feature Development with Worktrees

For larger features, use git worktrees to isolate changes:

```bash
# Create worktree for new feature
cd /path/to/taleweaver
git worktree add ../taleweaver-feature-name -b feature/feature-name

# Work in the worktree
cd ../taleweaver-feature-name
# ... make changes, commit frequently ...

# Test in the worktree
docker compose run --rm backend-test

# Merge when ready
cd /path/to/taleweaver
git checkout main
git merge feature/feature-name
git push origin main

# Clean up worktree
git worktree remove ../taleweaver-feature-name
```

### Commit Guidelines

- **Small, frequent commits** - Each commit should be a single unit of work
- **Descriptive messages** - Clear, concise descriptions of what changed
- **Test before committing** - Ensure tests pass locally
- **Logical grouping** - Group related changes together

**Example commit flow:**
```bash
git add backend/app/db/models.py
git commit -m "Add Story model for database persistence"

git add backend/app/db/crud.py
git commit -m "Implement CRUD operations for stories"

git add backend/tests/test_story_persistence.py
git commit -m "Add tests for story persistence"
```

### Test-Driven Development (TDD)

Follow Red-Green-Refactor cycle:

1. **RED** - Write failing test
2. **GREEN** - Implement minimum code to pass
3. **REFACTOR** - Clean up if needed
4. **COMMIT** - Commit each phase

**Example TDD workflow:**
```bash
# 1. RED: Write failing test
# Edit tests/test_new_feature.py
docker compose run --rm backend-test  # Should fail
git add tests/test_new_feature.py
git commit -m "Add RED test for new feature"

# 2. GREEN: Implement feature
# Edit app/new_feature.py
docker compose run --rm backend-test  # Should pass
git add app/new_feature.py
git commit -m "Implement new feature"

# 3. REFACTOR (if needed)
# Clean up code
docker compose run --rm backend-test  # Should still pass
git add app/new_feature.py
git commit -m "Refactor new feature for clarity"
```

---

## Building and Deploying

### Local Docker Build

Always test the production build locally before pushing:

```bash
# Build the production image
docker build -t taleweaver:test .

# Test it
docker run --rm -d -p 8080:80 \
  -e LLM_PROVIDER=anthropic \
  -e ANTHROPIC_API_KEY=test \
  -e ELEVENLABS_API_KEY=test \
  taleweaver:test

# Verify
curl http://localhost:8080/up
curl http://localhost:8080/api/status
curl http://localhost:8080/s/notfound  # Should return 404 JSON

# Clean up
docker stop $(docker ps -q --filter ancestor=taleweaver:test)
```

### GitHub Actions CI/CD

On push to `main`, GitHub Actions automatically:
1. Builds multi-platform images (amd64 + arm64)
2. Runs all tests
3. Publishes to `ghcr.io/tnightingale/taleweaver:latest`

Monitor builds: https://github.com/tnightingale/taleweaver/actions

### Once Deployment

#### Initial Deploy

```bash
once deploy ghcr.io/tnightingale/taleweaver:latest --host taleweaver.lan
```

Then configure environment variables through the Once TUI.

#### Updating to Latest Version

After GitHub Actions builds a new image:

```bash
# Option 1: Using Once TUI
once
# Select app, press 'u' for update

# Option 2: Redeploy (if Once doesn't manage it)
docker exec once-proxy kamal-proxy remove taleweaver.{id}
once deploy ghcr.io/tnightingale/taleweaver:latest --host taleweaver.lan
```

#### Backup Environment Variables

Before updating (to preserve API keys if deployment fails):

```bash
./scripts/backup-once-env.sh
```

This saves your configuration to `once-env-backup.txt`.

To restore later:
```bash
./scripts/restore-once-env.sh
```

---

## Common Tasks

### Add a New Feature

1. **Create worktree** (for larger features)
   ```bash
   git worktree add ../taleweaver-new-feature -b feature/new-feature
   cd ../taleweaver-new-feature
   ```

2. **Write RED tests**
   ```bash
   # Add tests to backend/tests/test_new_feature.py
   docker compose run --rm backend-test  # Verify they fail
   git add backend/tests/test_new_feature.py
   git commit -m "Add RED tests for new feature"
   ```

3. **Implement GREEN**
   ```bash
   # Implement feature
   docker compose run --rm backend-test  # Verify they pass
   git add backend/app/...
   git commit -m "Implement new feature"
   ```

4. **Test production build**
   ```bash
   docker build -t taleweaver:test .
   docker run --rm -d -p 8080:80 -e LLM_PROVIDER=anthropic taleweaver:test
   # Test at http://localhost:8080
   ```

5. **Merge and deploy**
   ```bash
   cd /path/to/taleweaver
   git checkout main
   git merge feature/new-feature
   git push origin main
   # Wait for GitHub Actions, then update Once
   ```

### Fix a Bug

1. **Write RED test** that reproduces the bug
2. **Implement fix** to make test GREEN
3. **Test locally** with docker compose
4. **Commit and push**

### Update Dependencies

```bash
# Backend
cd backend
# Edit requirements.txt
docker compose run --rm backend-test  # Verify tests still pass

# Frontend
cd frontend
# Edit package.json
npm install
npm run build  # Verify build succeeds

# Test production build
docker build -t taleweaver:test .

# Commit
git add backend/requirements.txt frontend/package.json frontend/package-lock.json
git commit -m "Update dependencies"
```

---

## Troubleshooting

### Tests Failing Locally

```bash
# Clean volumes and rebuild
docker compose down -v
docker compose build --no-cache backend-test
docker compose run --rm backend-test
```

### Production Build Fails

```bash
# Check frontend build
cd frontend
npm run build

# Check backend dependencies
cd backend
pip install -r requirements.txt

# Test Docker build with verbose output
docker build -t taleweaver:debug . --progress=plain
```

### Once Deployment Issues

```bash
# Check container logs
docker logs $(docker ps -q --filter "name=once-app-taleweaver")

# Check proxy logs
docker logs once-proxy --tail 50

# Verify image is latest
docker pull ghcr.io/tnightingale/taleweaver:latest
docker images ghcr.io/tnightingale/taleweaver:latest
```

### Environment Variables Lost in Once

```bash
# Restore from backup
./scripts/restore-once-env.sh

# Or manually redeploy with env vars (shows the command)
```

---

## Project Structure for Developers

```
taleweaver/
├── backend/
│   ├── app/
│   │   ├── db/                    # Database layer (SQLAlchemy)
│   │   ├── graph/                 # LangGraph pipeline
│   │   ├── models/                # Pydantic models
│   │   ├── routes/                # FastAPI routes
│   │   └── prompts/               # Story generation prompts
│   ├── tests/                     # 121 tests (pytest)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/            # React components
│   │   ├── api/                   # API client
│   │   └── types/                 # TypeScript types
│   └── package.json
├── scripts/
│   ├── backup-once-env.sh         # Backup Once env vars
│   └── restore-once-env.sh        # Restore Once env vars
├── docker-compose.dev.yml         # Development environments
├── Dockerfile                     # Production build
└── docs/plans/                    # Implementation plans
```

---

## Development Best Practices

### Before Pushing

1. ✅ Run tests: `docker compose run --rm backend-test`
2. ✅ Test production build: `docker build -t taleweaver:test .`
3. ✅ Verify TypeScript compiles: `cd frontend && npm run build`
4. ✅ Check for obvious errors
5. ✅ Commit frequently with clear messages

### Feature Development

- Use **TDD** for new features (Red-Green-Refactor)
- Write **tests first**, then implement
- Keep commits **small and focused**
- Test in **production-like environment** before merging
- Update **documentation** as you go

### Code Review Checklist

Before merging to main:
- [ ] All tests pass (121/121)
- [ ] Production build succeeds
- [ ] Frontend TypeScript compiles
- [ ] Documentation updated (if needed)
- [ ] No API keys or secrets in code
- [ ] Backward compatibility maintained
- [ ] Git history is clean with logical commits

---

## Deployment Checklist

### Pre-deployment

1. ✅ All tests pass locally
2. ✅ Production Docker build succeeds
3. ✅ Changes pushed to GitHub
4. ✅ GitHub Actions build completes successfully
5. ✅ **Backup Once environment variables**: `./scripts/backup-once-env.sh`

### Deployment

1. Wait for GitHub Actions to complete
2. Update Once deployment
3. Verify app health: `curl http://taleweaver.lan/api/status`
4. Test a story generation
5. Verify permalinks work

### Post-deployment

1. Monitor logs for errors
2. Test story generation with different configurations
3. Verify permalinks are being created
4. Check database: `/storage/taleweaver.db` exists
5. Check storage: `/storage/stories/{id}/audio.mp3` files created

---

## Environment Variables

### Required for Development

```bash
# Backend (.env or docker-compose environment)
LLM_PROVIDER=anthropic  # or groq, openai
ANTHROPIC_API_KEY=your-key-here
ELEVENLABS_API_KEY=your-key-here
STORAGE_PATH=./storage  # Local dev storage
```

### Required for Production (Once)

Set through Once TUI or backup scripts:
- `LLM_PROVIDER`
- `ANTHROPIC_API_KEY` (or `GROQ_API_KEY` / `OPENAI_API_KEY`)
- `ELEVENLABS_API_KEY`

### Backup Your Once Config

```bash
# Save settings before any deployment changes
./scripts/backup-once-env.sh

# Creates: once-env-backup.txt (keep this safe!)
```

---

## Key Files for Development

### Backend

- `app/main.py` - FastAPI app, health checks, permalink routes
- `app/routes/story.py` - Story generation endpoints
- `app/db/` - Database models and CRUD operations
- `app/graph/pipeline.py` - LangGraph story generation pipeline
- `app/prompts/` - Story generation prompts

### Frontend

- `src/App.tsx` - Main app flow and state management
- `src/components/StoryScreen.tsx` - Story playback and permalink display
- `src/components/CraftScreen.tsx` - Story creation UI
- `src/api/client.ts` - API client for backend

### Infrastructure

- `Dockerfile` - Production build (multi-stage)
- `docker-compose.dev.yml` - Development environments
- `docker-entrypoint.sh` - Container initialization
- `hooks/` - Once backup/restore hooks

---

## Database

### Schema

SQLite database at `/storage/taleweaver.db`:

```sql
CREATE TABLE stories (
    id VARCHAR PRIMARY KEY,
    short_id VARCHAR(8) UNIQUE,
    title VARCHAR,
    kid_name VARCHAR,
    kid_age INTEGER,
    story_type VARCHAR,
    genre VARCHAR,
    event_id VARCHAR,
    mood VARCHAR,
    length VARCHAR,
    transcript TEXT,
    duration_seconds INTEGER,
    audio_path VARCHAR,
    created_at DATETIME
);
```

### Inspecting Data

```bash
# Connect to database in running container
docker exec -it $(docker ps -q --filter "name=once-app-taleweaver") \
  sqlite3 /storage/taleweaver.db

# List all stories
sqlite> SELECT short_id, title, kid_name, created_at FROM stories ORDER BY created_at DESC LIMIT 10;

# Count stories
sqlite> SELECT COUNT(*) FROM stories;

# Exit
sqlite> .quit
```

---

## Performance Testing

### Story Generation

Test story generation end-to-end:

```bash
# Create custom story
curl -X POST http://localhost/api/story/custom \
  -H "Content-Type: application/json" \
  -d '{
    "kid": {"name": "Test", "age": 7},
    "genre": "fantasy",
    "description": "A magical adventure"
  }'

# Poll status
curl http://localhost/api/story/status/{job_id}

# Download audio
curl http://localhost/api/story/audio/{job_id} -o story.mp3

# Access via permalink
curl http://localhost/s/{short_id}
```

### Load Testing

```bash
# Generate multiple stories concurrently
for i in {1..5}; do
  curl -X POST http://localhost/api/story/custom \
    -H "Content-Type: application/json" \
    -d "{\"kid\":{\"name\":\"Kid$i\",\"age\":7},\"genre\":\"fantasy\",\"description\":\"Test\"}" &
done
wait
```

---

## Debugging

### Backend Logs

```bash
# Running container
docker logs -f $(docker ps -q --filter "name=once-app-taleweaver")

# Production-like compose
docker compose logs -f app

# Dev mode
docker compose --profile dev logs -f backend-dev
```

### Database Issues

```bash
# Check if database exists
docker exec $(docker ps -q --filter "name=once-app-taleweaver") \
  ls -la /storage/taleweaver.db

# Check table schema
docker exec $(docker ps -q --filter "name=once-app-taleweaver") \
  sqlite3 /storage/taleweaver.db ".schema stories"
```

### API Debugging

```bash
# Check all endpoints
curl http://localhost/up              # Health check
curl http://localhost/api/health      # API health
curl http://localhost/api/status      # Config status
curl http://localhost/api/genres      # List genres
curl http://localhost/s/notfound      # Should return 404 JSON
```

---

## Tips

### Faster Iteration

- Use `docker compose --profile dev` for hot-reload during active development
- Use `docker compose up app` to test production environment
- Run `docker compose run --rm backend-test` frequently to catch regressions early

### Clean Slate

```bash
# Remove all containers, volumes, and images
docker compose down -v
docker system prune -a
docker compose build --no-cache
```

### Working with Multiple Branches

Git worktrees let you have multiple branches checked out simultaneously:

```bash
/Work/taleweaver              # main branch
/Work/taleweaver-feature-a    # feature/feature-a branch
/Work/taleweaver-bugfix       # bugfix/issue-123 branch
```

Each can have its own docker-compose instance running different versions!

---

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **Once Docs**: https://github.com/basecamp/once
- **ElevenLabs API**: https://elevenlabs.io/docs
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org

---

## Getting Help

If you encounter issues:

1. Check logs: `docker logs $(docker ps -q --filter "name=taleweaver")`
2. Run tests: `docker compose run --rm backend-test`
3. Verify environment: `curl http://localhost/api/status`
4. Check GitHub Issues: https://github.com/tnightingale/taleweaver/issues
