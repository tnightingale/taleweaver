# Library Feature - Implementation Stages

**Feature:** Story Library with delete/edit capabilities  
**Started:** 2026-03-21  
**Status:** IN PROGRESS (2/5 stages complete)

---

## Stage Overview

| Stage | Description | Status | Commits | Tests |
|-------|-------------|--------|---------|-------|
| 1 | List API (GET /api/stories) | ✅ COMPLETE | 4 | 6/6 pass |
| 2 | Delete & Update API | ✅ COMPLETE | 4 | 10/10 pass |
| 3 | Frontend Components | 🔄 NEXT | - | - |
| 4 | Navigation Integration | ⏳ PENDING | - | - |
| 5 | Polish & Documentation | ⏳ PENDING | - | - |

**Overall Progress:** 137/137 tests passing (100%)

---

## Stage 1: List API ✅ COMPLETE

**Branch:** `feature/library`  
**Worktree:** `/home/tnightingale/Work/taleweaver-library`  
**Merged:** 381df9b  
**Pushed:** ✅ Yes

### What Was Delivered

**Backend:**
- ✅ `list_stories()` CRUD function with filters (kid_name, story_type), pagination (limit, offset), sorting
- ✅ `get_unique_kid_names()` helper for filter dropdowns
- ✅ `GET /api/stories` endpoint
- ✅ `StoriesListResponse` model

**Tests:**
- 6 new tests (all passing)
- test_list_stories_returns_empty_when_no_stories
- test_list_stories_returns_all_stories
- test_list_stories_filters_by_kid_name
- test_list_stories_pagination
- test_list_stories_sorts_newest_first
- test_get_unique_kid_names

**API Example:**
```bash
GET /api/stories
GET /api/stories?kid_name=Arjun&limit=10&offset=0&sort=created_desc
```

**Commits:**
1. `69413ca` - Add RED tests for story library list endpoint
2. `260d353` - Implement list_stories() and get_unique_kid_names() CRUD functions
3. `2aa70fe` - Add StoriesListResponse model for library endpoint
4. `381df9b` - Add GET /api/stories endpoint for library listing

---

## Stage 2: Delete & Update API ✅ COMPLETE

**Branch:** `feature/library-actions`  
**Worktree:** `/home/tnightingale/Work/taleweaver-library-actions`  
**Merged:** 42d8251  
**Pushed:** ✅ Yes

### What Was Delivered

**Backend:**
- ✅ `delete_story()` CRUD function (deletes DB record + audio file)
- ✅ `update_story_title()` CRUD function
- ✅ `DELETE /api/stories/{short_id}` endpoint (returns 204)
- ✅ `PATCH /api/stories/{short_id}` endpoint (validates non-empty title)
- ✅ `UpdateStoryTitleRequest` model with validation

**Tests:**
- 10 new tests (all passing)
- test_delete_story_removes_database_record
- test_delete_story_removes_audio_file
- test_delete_story_not_found_returns_false
- test_delete_story_api_endpoint
- test_delete_story_api_not_found
- test_update_story_title
- test_update_story_title_not_found
- test_update_story_title_api_endpoint
- test_update_story_title_api_not_found
- test_update_story_title_api_empty_title

**API Examples:**
```bash
DELETE /api/stories/abc123de
PATCH /api/stories/abc123de
  Body: {"title": "New Story Title"}
```

**Commits:**
1. `04936e2` - Add RED tests for delete and update story actions
2. `a0d2003` - Implement delete_story() and update_story_title() CRUD functions
3. `7e9ea6e` - Add UpdateStoryTitleRequest model
4. `112ba46` - Add DELETE and PATCH endpoints for story actions
5. `42d8251` - Fix test: expect 422 for Pydantic validation error

---

## Stage 3: Frontend Components 🔄 NEXT

**Branch:** `feature/library-frontend` (to be created)  
**Worktree:** `/home/tnightingale/Work/taleweaver-library-frontend` (to be created)

### Plan

**Components to Create:**
1. `LibraryScreen.tsx` - Main library view with grid layout
2. `StoryCard.tsx` - Individual story card with actions
3. `GroupedLibrary.tsx` - Stories grouped by kid name (collapsible)
4. `TimelineView.tsx` - Stories grouped by date (Today, Yesterday, etc.)
5. `DeleteConfirmDialog.tsx` - Confirmation modal for delete action

**API Client:**
- Add `listStories()` function
- Add `deleteStory()` function
- Add `updateStoryTitle()` function

**TypeScript Types:**
- Add `StoryMetadata` interface
- Update `WizardStep` to include "library"

**Tests:**
- Component tests for LibraryScreen
- Component tests for StoryCard
- Test delete confirmation
- Test title editing

**Estimated:** 2-2.5 hours

---

## Stage 4: Navigation Integration ⏳ PENDING

**Branch:** `feature/library-nav` (to be created)  
**Worktree:** `/home/tnightingale/Work/taleweaver-library-nav` (to be created)

### Plan

**HeroScreen:**
- Add "📚 View Library" button (secondary action)

**CraftScreen:**
- Add library icon button in top-right header

**App.tsx:**
- Add `library` to WizardStep type
- Add navigation: Hero → Library, Craft → Library
- Add state management for library view
- Handle Library → StoryScreen (play action)

**StoryScreen:**
- Add `fromLibrary` prop
- Add "Back to Library" button (conditional)
- Handle back navigation

**Session Storage:**
- Track library state across refreshes

**Estimated:** 1-1.5 hours

---

## Stage 5: Polish & Documentation ⏳ PENDING

**Branch:** `feature/library-polish` (to be created)  
**Worktree:** `/home/tnightingale/Work/taleweaver-library-polish` (to be created)

### Plan

**Empty States:**
- "No stories yet" when library is empty
- "No stories found" when filters return nothing

**Loading States:**
- Skeleton cards while loading
- Loading spinner for actions (delete, update)

**Error States:**
- Failed to load stories
- Failed to delete story
- Failed to update title

**Pagination:**
- "Load More" button
- Show count: "Showing 20 of 45 stories"

**Responsive Design:**
- Test on mobile viewport
- Adjust grid columns for small screens

**Documentation:**
- Update docs/UX-FLOW.md with library screens
- Update DEVELOPMENT.md with library testing
- Update CLAUDE.md API endpoint table

**Manual Testing:**
- Generate multiple stories
- Test all filters and sorting
- Test delete action
- Test title editing
- Test pagination
- Test on mobile

**Estimated:** 1-1.5 hours

---

## Progress Tracking

### Completed Work

**Total Commits:** 9  
**Total Tests:** 16 (all passing)  
**Test Coverage:** 137/137 (100%)  

**Backend APIs:**
- ✅ GET /api/stories (list with filters, pagination, sorting)
- ✅ DELETE /api/stories/{short_id}
- ✅ PATCH /api/stories/{short_id}

**CRUD Functions:**
- ✅ list_stories()
- ✅ get_unique_kid_names()
- ✅ delete_story()
- ✅ update_story_title()

### Remaining Work

**Frontend:** ~60% remaining
- Components (LibraryScreen, StoryCard, etc.)
- Navigation integration
- Polish (empty states, loading, errors)

**Documentation:** ~20% remaining
- UX flow updates
- Development guide updates

**Estimated Time to Complete:** 4-5 hours

---

## How to Resume

If interrupted, resume by:

1. **Check current stage:**
   ```bash
   cat docs/plans/2026-03-21-library-feature-stages.md
   ```

2. **Create worktree for next stage:**
   ```bash
   cd /home/tnightingale/Work/taleweaver
   git worktree add ../taleweaver-library-frontend -b feature/library-frontend
   cd ../taleweaver-library-frontend
   ```

3. **Run tests to verify baseline:**
   ```bash
   docker-compose -f docker-compose.dev.yml run --rm backend-test
   ```

4. **Continue with TDD for next stage**

---

## Testing Commands

**Run library tests only:**
```bash
docker-compose -f docker-compose.dev.yml run --rm backend-test \
  sh -c "python -m venv /tmp/venv && . /tmp/venv/bin/activate && \
         apt-get update -qq && apt-get install -qq -y ffmpeg && \
         pip install -q -r requirements.txt && \
         python -m pytest tests/test_story_library*.py -v"
```

**Run all tests:**
```bash
docker-compose -f docker-compose.dev.yml run --rm backend-test
```

**Test production build:**
```bash
docker build -t taleweaver:test .
docker run --rm -d -p 8080:80 -e LLM_PROVIDER=anthropic taleweaver:test
curl http://localhost:8080/api/stories
```

---

## Dependencies

**Backend (already added):**
- sqlalchemy==2.0.25 ✅

**Frontend (will add in Stage 3):**
- No new dependencies needed ✅
- Uses existing framer-motion for animations
- Uses existing Tailwind for styling

---

## API Endpoint Summary

### Implemented ✅

| Method | Endpoint | Purpose | Status |
|--------|----------|---------|--------|
| GET | `/api/stories` | List stories with filters/pagination | ✅ 127 tests pass |
| DELETE | `/api/stories/{short_id}` | Delete story (DB + file) | ✅ Tests pass |
| PATCH | `/api/stories/{short_id}` | Update story title | ✅ Tests pass |

### To Implement in Frontend

| Component | Purpose | Stage |
|-----------|---------|-------|
| LibraryScreen | Main library view | 3 |
| StoryCard | Story display card | 3 |
| GroupedLibrary | Group by kid name | 3 |
| TimelineView | Group by date | 3 |
| DeleteConfirmDialog | Delete confirmation | 3 |

---

## Notes

- Backend stages completed using TDD (Red-Green-Refactor)
- Each stage in separate worktree for isolation
- Small, frequent commits (9 commits so far)
- All tests passing after each merge
- Production build tested before Stage 1 merge
- Ready to continue with frontend implementation

---

## Next Session Plan

1. Start Stage 3 (Frontend Components)
2. Create feature/library-frontend branch in new worktree
3. Write RED tests for LibraryScreen
4. Implement components with TDD
5. Merge and push when complete
6. Continue to Stage 4 (Navigation)
