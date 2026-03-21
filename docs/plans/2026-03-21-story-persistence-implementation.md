# Story Persistence with Compact Permalinks - Implementation Plan

**Date**: 2026-03-21  
**Branch**: `feature/story-persistence`  
**Approach**: Red-Green-Refactor TDD

## Design Decisions (Confirmed)

1. ✅ **Database**: SQLite at `/storage/taleweaver.db`
2. ✅ **Permalink format**: Compact `/s/{short_id}` (8 characters, e.g., `/s/a7X9k2Mn`)
3. ✅ **Scope**: Simple - just permalink access with copy button, no listing UI
4. ✅ **Storage**: Files in `/storage/stories/{story_id}/audio.mp3`
5. ✅ **Retention**: Permanent storage
6. ✅ **Frontend**: Show permalink on completion screen (no standalone viewer page)
7. ✅ **Copy feedback**: Button text change ("Copy Link" → "Copied!" for 2 seconds)
8. ✅ **Error handling**: Return 404 with "Audio file not found"
9. ✅ **Testing**: Full TDD with ~15 test cases
10. ✅ **Short ID**: `a-z0-9` (36 chars, case-insensitive, easy to communicate)

## Architecture Overview

### Database Schema (SQLite)

```sql
CREATE TABLE stories (
    id VARCHAR PRIMARY KEY,           -- UUID (job_id)
    short_id VARCHAR(8) UNIQUE,       -- Compact permalink ID
    title VARCHAR NOT NULL,
    kid_name VARCHAR NOT NULL,
    kid_age INTEGER NOT NULL,
    story_type VARCHAR NOT NULL,      -- 'custom' or 'historical'
    genre VARCHAR,                    -- For custom stories
    event_id VARCHAR,                 -- For historical stories
    mood VARCHAR,
    length VARCHAR,
    transcript TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    audio_path VARCHAR NOT NULL,
    created_at DATETIME NOT NULL
);

CREATE INDEX idx_short_id ON stories(short_id);
```

### File Structure

```
/storage/
├── taleweaver.db                 # SQLite database
├── stories/
│   ├── {uuid-1}/
│   │   └── audio.mp3
│   ├── {uuid-2}/
│   │   └── audio.mp3
│   └── ...
├── jobs/                         # Temporary (if needed)
└── music/                        # Background music
```

### API Endpoints

**New endpoints:**
- `GET /s/{short_id}` - Story metadata (title, duration, etc.)
- `GET /s/{short_id}/audio` - Stream audio file

**Existing endpoints (unchanged):**
- `POST /api/story/custom` - Create custom story
- `POST /api/story/historical` - Create historical story
- `GET /api/story/status/{job_id}` - Poll job status (now includes short_id)
- `GET /api/story/audio/{job_id}` - Get audio by job ID (backward compat)

### Response Models

**JobCompleteResponse** (modified):
```json
{
  "job_id": "uuid",
  "status": "complete",
  "title": "Story Title",
  "duration_seconds": 180,
  "audio_url": "/api/story/audio/{job_id}",
  "transcript": "Once upon a time...",
  "short_id": "a7x9k2mn",
  "permalink": "/s/a7x9k2mn"
}
```

**StoryResponse** (new):
```json
{
  "id": "uuid",
  "short_id": "a7x9k2mn",
  "title": "Story Title",
  "kid_name": "Arjun",
  "kid_age": 7,
  "story_type": "custom",
  "genre": "fantasy",
  "event_id": null,
  "transcript": "Once upon a time...",
  "duration_seconds": 180,
  "created_at": "2026-03-21T12:00:00",
  "permalink": "/s/a7x9k2mn",
  "audio_url": "/s/a7x9k2mn/audio"
}
```

## Implementation Phases

### Phase 1: Setup Worktree & Branch
- Create git worktree
- Create feature branch
- Add dependencies

### Phase 2: Database Layer (TDD)
- Write failing tests for CRUD operations
- Implement database models
- Implement CRUD functions
- Verify all tests pass

### Phase 3: Pipeline Integration (TDD)
- Write failing tests for story persistence
- Modify pipeline to save stories after completion
- Update response models
- Initialize database on app startup
- Verify all tests pass

### Phase 4: Permalink API (TDD)
- Write failing tests for permalink endpoints
- Implement GET /s/{short_id}
- Implement GET /s/{short_id}/audio
- Verify all tests pass

### Phase 5: Frontend (TDD)
- Write failing component tests
- Update TypeScript types
- Add permalink display to StoryScreen
- Add copy button with feedback
- Verify all tests pass

### Phase 6: Documentation & Cleanup
- Update CLAUDE.md
- Update README.md
- Add configuration
- Manual testing

### Phase 7: Merge & Deploy
- Create logical commits
- Merge to main
- Push to origin
- Verify deployment

## Backward Compatibility

- ✅ Existing `/api/story/audio/{job_id}` endpoints unchanged
- ✅ In-memory jobs continue to work during generation
- ✅ Frontend gracefully handles missing `short_id` in old jobs
- ✅ No breaking changes to existing API contracts

## Testing Strategy

### Backend Tests
- `test_story_persistence.py` - Database CRUD (unit tests)
- `test_story_persistence_integration.py` - Pipeline integration (integration tests)
- `test_story_permalink_routes.py` - API endpoints (API tests)

### Frontend Tests
- `StoryScreen.test.tsx` - Permalink display and copy (component tests)

### Manual Testing Checklist
- [ ] Generate custom story → verify permalink appears
- [ ] Copy permalink → paste in new browser → story loads
- [ ] Generate historical story → verify permalink works
- [ ] Old job URLs still work (backward compatibility)
- [ ] Database file created at `/storage/taleweaver.db`
- [ ] Audio files created at `/storage/stories/{id}/audio.mp3`
- [ ] Restart server → permalinks still work
- [ ] Delete audio file → API returns 404

## Risk Mitigation

**Disk Space:**
- Stories accumulate permanently
- Mitigation: User can manually clean up old stories from `/storage/stories/`
- Future: Could add retention policy or admin cleanup endpoint

**Short ID Collisions:**
- Extremely unlikely with 8 chars from 36-char alphabet (2.8 trillion combinations)
- Mitigation: Collision check in `generate_short_id()` function

**Audio File Corruption:**
- If manually deleted, API will fail
- Mitigation: Return 404 with clear error message

## Success Criteria

- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] Stories persist across server restarts
- [ ] Permalinks work for sharing
- [ ] Backward compatibility maintained
- [ ] No breaking changes to existing functionality
- [ ] Clean, well-documented code
- [ ] Git history with logical commits
