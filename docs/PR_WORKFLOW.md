# Pull Request Workflow

**Last Updated:** 2026-03-22

---

## Overview

For the illustration feature (and future large features), we use **staged PRs** - one PR per stage or group of related stages. This allows for:
- ✅ Incremental code review (easier to review smaller chunks)
- ✅ Early feedback (catch issues before investing more time)
- ✅ Independent merging (stages can be approved/merged separately)
- ✅ Cleaner git history (logical groupings of changes)

---

## Workflow for Large Features

### 1. Planning Phase

```bash
# Create comprehensive implementation plan
docs/plans/YYYY-MM-DD-feature-name-plan.md       # Detailed plan
docs/plans/YYYY-MM-DD-feature-name-summary.md    # Quick reference
docs/plans/YYYY-MM-DD-feature-name-progress.md   # Progress tracking
```

### 2. Implementation Phase

Each stage or logical group of stages gets its own PR:

```bash
# Create feature branch with worktree
git checkout -b feature/feature-name-stage1
git worktree add ../taleweaver-feature-stage1 feature/feature-name-stage1
cd ../taleweaver-feature-stage1

# Implement stage(s)
# ... make changes ...
# ... commit frequently (small, logical commits) ...

# Run tests before pushing
COMPOSE_PROFILES=test docker compose -f docker-compose.dev.yml run --rm backend-test
# ✅ All tests must pass

# Push and create PR
git push -u origin feature/feature-name-stage1
gh pr create --title "Feature: Stage 1 & 2 - Description" --body "$(cat <<'EOF'
## Summary
Brief overview of what this PR accomplishes

## Changes
- Bullet list of main changes
- Include test count

## Test Results
X/X tests passing (100%)

## Next Steps
What comes after this PR
EOF
)"
```

### 3. Review & Merge Cycle

```bash
# After PR is approved and merged
git checkout main
git pull origin main

# Create next stage
git checkout -b feature/feature-name-stage3
# ... continue ...
```

---

## PR Grouping Guidelines

### Group into Single PR:
- **Foundation stages** (database schema + data structures)
- **API stages** (related endpoints)
- **Small stages** (<4 hours, <300 lines changed)
- **Dependent stages** (Stage B requires Stage A's code)

### Separate PRs:
- **Major integrations** (LangGraph pipeline changes)
- **Frontend work** (separate from backend)
- **Large stages** (>8 hours, >500 lines changed)
- **Independent stages** (can be reviewed/merged separately)

---

## Example: Illustration Feature PRs

### PR #1: Foundation (Stages 1 & 2) ← **CURRENT**
**Branch:** `feature/illustrations-schema`  
**Title:** "Illustration Feature: Foundation (Stages 1 & 2)"  
**Includes:**
- Stage 1: Database Schema & Models
- Stage 2: Art Style System & API
- Bonus: Test isolation fixes + CI

**Why grouped:** Both are data/schema foundations, small changes, work together

**Command to create PR:**
```bash
git push -u origin feature/illustrations-schema

gh pr create --title "Illustration Feature: Foundation (Stages 1 & 2)" --body "$(cat <<'EOF'
## Summary
Adds foundation for AI-generated story illustrations. Database schema, type definitions, art style presets, and test infrastructure.

## Changes

### Stage 1: Database Schema & Models
- Added illustration columns to Story model
- Created Scene TypedDict and updated StoryState
- Updated request/response models
- 9 new tests

### Stage 2: Art Style System & API
- 7 curated art style presets
- GET /api/art-styles endpoint
- 7 new tests

### Bonus: Test Infrastructure
- Fixed test isolation (conftest.py fixtures)
- Added GitHub Actions CI
- 146 → 153 tests, all passing

## Test Results
153/153 tests passing (100%)

## Files Changed
19 files: +1221 lines, -419 lines

## Next Steps
- Stage 3: Scene Analyzer Node (LLM beat detection)
- Stage 4: Illustration Provider (NanoBanana 2)
- Stage 5: Pipeline Integration
EOF
)"
```

### PR #2: Scene Analysis (Stage 3)
**Branch:** `feature/illustrations-scene-analyzer`  
**Title:** "Illustration Feature: Scene Analyzer (Stage 3)"  
**Includes:**
- Stage 3: Scene Analyzer Node

**Why separate:** Complex LLM integration, can be reviewed independently

### PR #3: Image Generation (Stages 4 & 5)
**Branch:** `feature/illustrations-pipeline`  
**Title:** "Illustration Feature: Image Generation & Pipeline (Stages 4 & 5)"  
**Includes:**
- Stage 4: Illustration Provider (NanoBanana 2)
- Stage 5: Pipeline Integration

**Why grouped:** Provider and pipeline integration are tightly coupled

### PR #4: Frontend (Stages 6 & 7)
**Branch:** `feature/illustrations-frontend`  
**Title:** "Illustration Feature: Frontend UI (Stages 6 & 7)"  
**Includes:**
- Stage 6: Art Style Selector
- Stage 7: Illustrated Story Player

**Why grouped:** Both frontend, can be reviewed together by frontend-focused reviewers

### PR #5: Polish & Testing (Stage 8)
**Branch:** `feature/illustrations-polish`  
**Title:** "Illustration Feature: Final Polish & Testing (Stage 8)"  
**Includes:**
- Stage 8: E2E testing, performance optimization, documentation

**Why separate:** Final validation, may need iteration based on testing results

---

## PR Best Practices

### Before Creating PR

```bash
# 1. Run all tests in Docker (REQUIRED)
COMPOSE_PROFILES=test docker compose -f docker-compose.dev.yml run --rm backend-test
# ✅ All tests must pass (146+ tests)
# ⚠️ DO NOT skip this - local tests may pass but Docker tests fail

# 2. Test production build (REQUIRED)
docker build -t taleweaver:test .
# ✅ Build must succeed
# ✅ No errors during image creation

# 3. Verify no uncommitted changes
git status
# ✅ No uncommitted changes
# ✅ All changes committed with clear messages

# 4. Push branch
git push -u origin feature/your-branch-name

# 5. Check CI status (REQUIRED after push)
gh pr checks  # Wait for CI to pass
# Or manually check: https://github.com/YOUR_ORG/taleweaver/actions
# ✅ CI must be green before creating/updating PR
# ⚠️ Fix any CI failures before proceeding
```

### During Development

```bash
# Run tests frequently (after each logical change)
COMPOSE_PROFILES=test docker compose -f docker-compose.dev.yml run --rm backend-test

# Run specific test file during active development
COMPOSE_PROFILES=test docker compose -f docker-compose.dev.yml run --rm backend-test \
  bash -c "python -m venv /tmp/venv && . /tmp/venv/bin/activate && \
           pip install -q -r requirements.txt && \
           apt-get update -qq && apt-get install -qq -y ffmpeg > /dev/null 2>&1 && \
           python -m pytest tests/test_your_new_file.py -v"

# Commit frequently (after each passing test or logical unit)
git add -A && git commit -m "Descriptive message"
```

### PR Title Format

```
<Feature Name>: <Stage Description> (Stage X)
```

Examples:
- ✅ "Illustration Feature: Foundation (Stages 1 & 2)"
- ✅ "Illustration Feature: Scene Analyzer (Stage 3)"
- ✅ "Library Feature: API Endpoints (Stage 1)"
- ❌ "Add illustrations" (too vague)
- ❌ "WIP changes" (not descriptive)

### PR Description Template

```markdown
## Summary
1-2 sentence overview

## Changes
- Bullet list of main changes
- Group by stage if multiple stages
- Include test count

## Test Results
X/X tests passing (100%)

## Files Changed
N files: +XXX lines, -XXX lines

## Next Steps (optional)
What comes after this PR
```

### Reviewing PRs

**For Reviewers:**
- Check that all tests pass (CI badge)
- Review commit history (should be clean, logical)
- Verify documentation is updated
- Test locally if needed

**For PR Author:**
- Respond to feedback promptly
- Make requested changes in new commits (don't force push)
- Update PR description if scope changes

---

## After PR is Merged

```bash
# Switch back to main
cd /home/tnightingale/Work/taleweaver
git checkout main
git pull origin main

# Remove merged worktree
git worktree remove ../taleweaver-feature-stage1

# Create next stage branch/worktree
git checkout -b feature/feature-name-stage3
git worktree add ../taleweaver-feature-stage3 feature/feature-name-stage3
cd ../taleweaver-feature-stage3

# Update progress tracker
# ... continue implementation ...
```

---

## Special Cases

### Hotfixes (No PR Needed)

```bash
# Critical bugs in production
git checkout -b hotfix/fix-description
# ... fix ...
git push origin hotfix/fix-description
# Merge directly or very quick PR review
```

### Documentation-Only Changes

```bash
# Small doc updates
git checkout -b docs/update-description
# ... update docs ...
git push origin docs/update-description
# Quick PR or direct merge
```

### Small Features (<2 hours)

```bash
# Single PR, no staging
git checkout -b feature/small-feature-name
# ... implement ...
# ... test ...
git push origin feature/small-feature-name
gh pr create --title "Add small feature"
```

---

## Current Feature Status

### Illustration Feature PRs

| PR | Branch | Status | Stages | Tests |
|----|--------|--------|--------|-------|
| #TBD | feature/illustrations-schema | 🟡 OPEN | 1, 2 | 153/153 ✅ |
| - | feature/illustrations-scene-analyzer | 🔵 NOT STARTED | 3 | - |
| - | feature/illustrations-pipeline | 🔵 NOT STARTED | 4, 5 | - |
| - | feature/illustrations-frontend | 🔵 NOT STARTED | 6, 7 | - |
| - | feature/illustrations-polish | 🔵 NOT STARTED | 8 | - |

---

## Commands Reference

```bash
# Create PR
gh pr create --title "Title" --body "Description"

# Check PR status
gh pr status

# View PR checks (CI)
gh pr checks

# Merge PR (after approval)
gh pr merge <number> --squash  # or --merge or --rebase

# List open PRs
gh pr list

# View PR diff
gh pr diff <number>
```

---

**Last Updated:** 2026-03-22  
**Applies To:** All large features with multiple stages
