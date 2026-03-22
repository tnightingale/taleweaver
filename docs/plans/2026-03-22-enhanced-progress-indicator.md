# Enhanced Progress Indicator Feature

**Feature:** Detailed Progress Tracking with Progress Ring  
**Created:** 2026-03-22  
**Updated:** 2026-03-22 (added navigation persistence requirements)  
**Status:** 🔵 PLANNING  
**Estimated Time:** 6-8 hours (including navigation improvements)

---

## Overview

Add detailed progress tracking to story generation with a visual progress ring around the orb, progress percentage, and detailed status messages showing sub-progress within stages.

**User Preferences:**
- **Detail Level:** Option B - Progress bar + detailed message ("Generating illustration 3 of 8")
- **Visual Style:** Progress ring around existing orb animation

---

## Current Behavior

**Generation Screen Shows:**
- Color-cycling pulsing orb (animated)
- Single stage label: "Writing the story...", "Generating audio...", etc.
- Static subtitle: "This usually takes about a minute"
- No indication of progress within a stage
- No visibility into how many segments/illustrations are being processed

**User Pain Points:**
- Long waits without knowing what's happening (especially with illustrations)
- No sense of completion percentage
- Can't tell if it's stuck or just slow
- Illustration generation can take 5-10 minutes with no feedback
- **Can't navigate away during generation** - lose job ID if leaving page
- **No way to get back to in-progress job** - URL not bookmarkable/shareable
- **No "Recent Generations" list** to find in-progress jobs

---

## Proposed Solution

### Visual Design

**Layout:**
```
┌─────────────────────────────────────┐
│                                     │
│         ╔═══════════════╗          │
│         ║   Progress    ║          │
│         ║   Ring 75%    ║          │
│         ║   around orb  ║          │
│         ╚═══════════════╝          │
│                                     │
│    "Generating audio..."           │
│    75% complete                     │
│    Synthesizing segment 12 of 15   │
│                                     │
└─────────────────────────────────────┘
```

**Components:**
1. **Existing orb** - Keep color-cycling animation (no changes)
2. **Progress ring** - SVG circle that fills clockwise around orb (0-360°)
3. **Stage label** - Current stage name (existing, e.g., "Generating audio...")
4. **Progress percentage** - "75% complete"
5. **Detail message** - "Generating illustration 3 of 8", "Synthesizing segment 12 of 15"

---

## Context for Implementation

### Current System Overview

**Architecture:**
- LangGraph pipeline with 7 nodes (with illustrations) or 4 nodes (without)
- Job state stored in database (job_state table) - shared across gunicorn workers
- Polling: Frontend polls `/api/story/status/{job_id}` every 2 seconds
- Stages tracked in routes/story.py run_pipeline() function

**Key Files:**
- `backend/app/routes/story.py` - Job creation, status endpoint, run_pipeline
- `backend/app/graph/pipeline.py` - LangGraph node definitions
- `backend/app/graph/nodes/*.py` - Individual pipeline nodes
- `backend/app/db/models.py` - JobState model
- `frontend/src/routes/StoryRoute.tsx` - Polling and display logic
- `frontend/src/components/StoryScreen.tsx` - Generation UI

**How Progress Currently Works:**
1. Job created → `create_job_state(db, job_id, stages)`
2. Pipeline runs → `update_job_stage(db, job_id, next_stage)` after each node
3. Frontend polls → `get_job_status()` returns current_stage
4. Frontend displays → STAGE_LABELS[current_stage]

**What's Missing:**
- No sub-progress within stages (e.g., "segment 5 of 12")
- No overall percentage (0-100%)
- Progress updates not granular enough

---

## Implementation Plan

### Stage 1: Backend Progress Tracking (2-3 hours)

#### Backend Architecture

**Progress Weight Allocation:**
```python
STAGE_WEIGHTS = {
    # Without illustrations:
    "writing": 25,           # ~25%
    "splitting": 5,          # ~30%
    "synthesizing": 60,      # ~90%
    "stitching": 10,         # ~100%
    
    # With illustrations:
    "writing": 15,           # ~15%
    "analyzing_scenes": 5,   # ~20%
    "splitting": 5,          # ~25%
    "synthesizing": 30,      # ~55%
    "generating_illustrations": 30,  # ~85%
    "stitching": 10,         # ~95%
    "finalizing": 5,         # ~100%
}
```

**Progress Calculation:**
```
overall_progress = base_progress_for_stage + (sub_progress * stage_weight)

Example:
- Stage: synthesizing (base: 25%, weight: 30%)
- Sub-progress: segment 10 of 15 = 66.7%
- Overall: 25% + (0.667 * 30%) = 45%
```

#### Tasks

**1.1 Add Progress Fields to Job State**
- [ ] Add `progress` field to jobs dict (float, 0-100)
- [ ] Add `progress_detail` field to jobs dict (string)
- [ ] Initialize in create_custom_story: `jobs[job_id]["progress"] = 0`
- [ ] Initialize in create_historical_story: `jobs[job_id]["progress"] = 0`

**1.2 Define Stage Weights**
- [ ] Create `STAGE_WEIGHTS` dict in routes/story.py
- [ ] Create `STAGE_WEIGHTS_WITH_ILLUSTRATIONS` dict
- [ ] Helper function: `get_stage_weights(has_illustrations: bool)`
- [ ] Helper function: `calculate_base_progress(stage: str, weights: dict)`

**1.3 Update Progress on Stage Transitions**
- [ ] In run_pipeline, update progress when stage changes
- [ ] Calculate base progress from completed stages
- [ ] Set progress_detail to stage label
- [ ] Example: `jobs[job_id]["progress"] = 25.0`
- [ ] Example: `jobs[job_id]["progress_detail"] = "Preparing character voices..."`

**1.4 Add Progress to Voice Synthesizer Node**
- [ ] Import SessionLocal and update_job_progress from crud
- [ ] Get job_id from state (state["job_id"])
- [ ] In synthesis loop, update progress after each segment:
- [ ] **NOTE:** Voice synthesizer already has this partially implemented! Check existing code first.
  ```python
  if job_id in jobs:
      segment_progress = (i + 1) / len(segments)
      base_progress = calculate_base_progress("synthesizing", weights)
      stage_weight = weights["synthesizing"]
      jobs[job_id]["progress"] = base_progress + (segment_progress * stage_weight)
      jobs[job_id]["progress_detail"] = f"Synthesizing segment {i+1} of {len(segments)}"
  ```
- [ ] Handle job_id not in jobs (tests)

**1.5 Add Progress to Illustration Generator Node**
- [ ] Import SessionLocal and update_job_progress from crud
- [ ] Get job_id from state (already available: state["job_id"])
- [ ] In illustration loop, update progress after each image:
- [ ] **NOTE:** This may already be partially implemented. Check current code.
- [ ] **IMPORTANT:** Wrap database calls in try/except (don't fail generation on DB errors)
  ```python
  if job_id in jobs:
      image_progress = (i + 1) / len(scenes)
      base_progress = calculate_base_progress("generating_illustrations", weights)
      stage_weight = weights["generating_illustrations"]
      jobs[job_id]["progress"] = base_progress + (image_progress * stage_weight)
      jobs[job_id]["progress_detail"] = f"Generating illustration {i+1} of {len(scenes)}"
  ```

**1.6 Update JobStatusResponse**
- [ ] Add `progress: float = 0.0` to JobStatusResponse model
- [ ] Add `progress_detail: str = ""` to JobStatusResponse model
- [ ] Update get_job_status endpoint to return these fields:
  ```python
  return JobStatusResponse(
      progress=job.get("progress", 0.0),
      progress_detail=job.get("progress_detail", ""),
      # ... other fields
  )
  ```

**Tests:**
- [ ] Test progress starts at 0
- [ ] Test progress updates during synthesis
- [ ] Test progress updates during illustration generation
- [ ] Test progress reaches 100 on completion
- [ ] Test progress_detail messages are set correctly
- [ ] Test JobStatusResponse includes new fields

**Definition of Done:**
- ✅ Backend tracks progress 0-100% accurately
- ✅ Detailed messages show sub-progress (segment X of Y, image X of Y)
- ✅ API returns progress and progress_detail fields
- ✅ Tests pass
- ✅ Logging shows progress updates

**Files Modified:**
- `backend/app/routes/story.py` - Progress calculation logic
- `backend/app/graph/nodes/voice_synthesizer.py` - Segment progress
- `backend/app/graph/nodes/illustration_generator.py` - Image progress
- `backend/app/models/responses.py` - JobStatusResponse fields
- `backend/tests/test_story_progress.py` - NEW test file

---

### Stage 2: Frontend Progress Ring UI (2-3 hours)

#### Visual Specifications

**Progress Ring:**
- SVG circle, radius 70px (to wrap around 128px orb with padding)
- Stroke width: 6px
- Stroke color: Gradient purple-500 → blue-500
- Background circle: starlight/10 (inactive portion)
- Clockwise fill animation (0° = top, 360° = complete circle)
- Smooth transition (300ms ease-out)

**Typography:**
- Progress percentage: text-2xl, font-mono, text-glow
- Detail message: text-sm, text-starlight/60
- Stage label: Keep existing (text-xl, font-display, text-glow)

#### Tasks

**2.1 Update TypeScript Types**
- [ ] Update `JobStatusResponse` interface in types/index.ts
- [ ] Add `progress: number`
- [ ] Add `progress_detail: string`

**2.2 Update StoryRoute Polling**
- [ ] Add `const [progress, setProgress] = useState(0)`
- [ ] Add `const [progressDetail, setProgressDetail] = useState("")`
- [ ] In polling callback, extract from status:
  ```typescript
  if ("progress" in status) {
      setProgress(status.progress);
      setProgressDetail(status.progress_detail || "");
  }
  ```
- [ ] Pass to StoryScreen: `progress={progress}` and `progressDetail={progressDetail}`

**2.3 Create ProgressRing Component**
- [ ] Create `frontend/src/components/ProgressRing.tsx`
- [ ] Props interface:
  ```typescript
  interface Props {
      progress: number;  // 0-100
      size?: number;     // diameter in pixels (default 160)
      strokeWidth?: number;  // default 6
      children?: React.ReactNode;  // orb goes inside
  }
  ```
- [ ] SVG implementation:
  ```tsx
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;
  
  <svg width={size} height={size}>
      {/* Background circle */}
      <circle stroke="rgba(255,255,255,0.1)" ... />
      
      {/* Progress circle */}
      <motion.circle
          stroke="url(#gradient)"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.3, ease: "easeOut" }}
      />
      
      {/* Gradient def */}
      <defs>
          <linearGradient id="gradient">
              <stop offset="0%" stopColor="rgb(168,85,247)" />
              <stop offset="100%" stopColor="rgb(59,130,246)" />
          </linearGradient>
      </defs>
  </svg>
  
  {/* Orb centered inside */}
  <div className="absolute inset-0 flex items-center justify-center">
      {children}
  </div>
  ```
- [ ] Rotate SVG -90° so progress starts at top (12 o'clock position)
- [ ] Add subtle glow effect to progress stroke

**2.4 Update StoryScreen Generation View**
- [ ] Import ProgressRing component
- [ ] Wrap orb with ProgressRing:
  ```tsx
  <ProgressRing progress={progress}>
      <motion.div className="w-32 h-32 rounded-full orb-color-cycle" ... />
  </ProgressRing>
  ```
- [ ] Add progress percentage display:
  ```tsx
  <p className="text-2xl font-mono text-glow">
      {Math.round(progress)}%
  </p>
  ```
- [ ] Add progress detail display:
  ```tsx
  {progressDetail && (
      <p className="text-sm text-starlight/60 max-w-md text-center">
          {progressDetail}
      </p>
  )}
  ```
- [ ] Update Props interface to accept progress and progressDetail
- [ ] Adjust spacing to accommodate new elements

**2.5 Polish & Animation**
- [ ] Progress ring fills smoothly (no jumps)
- [ ] Percentage counts up (not instant update)
- [ ] Detail message fades in/out on change
- [ ] Orb animation continues unchanged
- [ ] Responsive design (smaller on mobile)

**Tests (Manual QA):**
- [ ] Test with non-illustrated story (4 stages)
- [ ] Test with illustrated story (7 stages)
- [ ] Verify progress reaches 100%
- [ ] Check detailed messages appear correctly
- [ ] Test on mobile (smaller screen)
- [ ] Verify smooth animations
- [ ] Check progress never goes backwards

**Definition of Done:**
- ✅ Progress ring animates from 0% to 100%
- ✅ Percentage displayed prominently
- ✅ Detailed messages show for long stages
- ✅ Visual polish matches existing design
- ✅ Works on desktop and mobile
- ✅ No layout shifts or jank

**Files Modified:**
- `frontend/src/types/index.ts` - JobStatusResponse
- `frontend/src/routes/StoryRoute.tsx` - Progress state
- `frontend/src/components/StoryScreen.tsx` - Props + progress display
- `frontend/src/components/ProgressRing.tsx` - NEW component

---

## Design Mockup (Text)

```
┌─────────────────────────────────────────┐
│                                         │
│              ┏━━━━━━━━┓                │
│           ┏━━┃  ╱╲    ┃━━┓             │
│         ┏━┃   ┃ (  )   ┃  ┃━┓           │ 
│        ┃  ┃   ┃  ╲╱    ┃  ┃ ┃          │ ← Progress ring (purple gradient)
│         ┗━┃   ┃ [ORB]  ┃  ┃━┛           │
│           ┗━━┃        ┃━━┛             │
│              ┗━━━━━━━━┛                │
│                                         │
│              75%                        │ ← Percentage
│                                         │
│        Generating audio...              │ ← Stage label
│                                         │
│     Synthesizing segment 12 of 15      │ ← Detail message
│                                         │
└─────────────────────────────────────────┘
```

---

## Example Progress Flow (Illustrated Story)

| Time | Stage | Progress | Detail Message |
|------|-------|----------|----------------|
| 0s | writing | 0% | "Writing your personalized story..." |
| 15s | writing | 15% | "Writing your personalized story..." |
| 15s | analyzing_scenes | 15% | "Analyzing story structure..." |
| 20s | analyzing_scenes | 20% | "Analyzing story structure..." |
| 20s | splitting | 20% | "Preparing character voices..." |
| 22s | splitting | 25% | "Preparing character voices..." |
| 22s | synthesizing | 25% | "Synthesizing segment 1 of 12..." |
| 28s | synthesizing | 30% | "Synthesizing segment 3 of 12..." |
| 45s | synthesizing | 45% | "Synthesizing segment 8 of 12..." |
| 55s | synthesizing | 55% | "Synthesizing segment 12 of 12..." |
| 55s | generating_illustrations | 55% | "Generating illustration 1 of 8..." |
| 70s | generating_illustrations | 63% | "Generating illustration 2 of 8..." |
| 120s | generating_illustrations | 85% | "Generating illustration 8 of 8..." |
| 120s | stitching | 85% | "Mixing the final track..." |
| 125s | stitching | 95% | "Mixing the final track..." |
| 125s | finalizing | 95% | "Adding final touches..." |
| 127s | done | 100% | "Complete!" |

---

## Technical Implementation Details

### Backend: Progress Tracking Logic

**File:** `backend/app/routes/story.py`

```python
# Stage weights (percentage of total time)
STAGE_WEIGHTS_NO_ILLUSTRATIONS = {
    "writing": 25,
    "splitting": 5,
    "synthesizing": 60,
    "stitching": 10,
}

STAGE_WEIGHTS_WITH_ILLUSTRATIONS = {
    "writing": 15,
    "analyzing_scenes": 5,
    "splitting": 5,
    "synthesizing": 30,
    "generating_illustrations": 30,
    "stitching": 10,
    "finalizing": 5,
}

def get_stage_weights(has_illustrations: bool) -> dict:
    return STAGE_WEIGHTS_WITH_ILLUSTRATIONS if has_illustrations else STAGE_WEIGHTS_NO_ILLUSTRATIONS

def calculate_base_progress(stage: str, weights: dict) -> float:
    """Calculate cumulative progress up to (but not including) current stage"""
    stage_order = list(weights.keys())
    if stage not in stage_order:
        return 0.0
    
    idx = stage_order.index(stage)
    return sum(weights[s] for s in stage_order[:idx])
```

**In run_pipeline:**
```python
has_illustrations = bool(state.get("art_style"))
stage_weights = get_stage_weights(has_illustrations)

async for event in pipeline.astream(state):
    for node_name in event:
        # Update progress when stage changes
        if node_name in NODE_TO_STAGE:
            stage = NODE_TO_STAGE[node_name]
            base_progress = calculate_base_progress(stage, stage_weights)
            jobs[job_id]["progress"] = base_progress
            jobs[job_id]["progress_detail"] = STAGE_LABELS.get(stage, "Processing...")
```

### Frontend: ProgressRing Component

**File:** `frontend/src/components/ProgressRing.tsx`

```tsx
interface Props {
  progress: number;  // 0-100
  size?: number;
  strokeWidth?: number;
  children?: React.ReactNode;
}

export default function ProgressRing({ 
  progress, 
  size = 160, 
  strokeWidth = 6,
  children 
}: Props) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;
  
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg 
        width={size} 
        height={size}
        className="transform -rotate-90"  // Start at top
      >
        {/* Background circle (inactive) */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={strokeWidth}
          fill="none"
        />
        
        {/* Progress circle (active) */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="url(#progress-gradient)"
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={circumference}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          strokeLinecap="round"
          style={{
            filter: "drop-shadow(0 0 8px rgba(168,85,247,0.6))"
          }}
        />
        
        {/* Gradient definition */}
        <defs>
          <linearGradient id="progress-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgb(168,85,247)" />
            <stop offset="100%" stopColor="rgb(59,130,246)" />
          </linearGradient>
        </defs>
      </svg>
      
      {/* Centered children (orb) */}
      <div className="absolute inset-0 flex items-center justify-center">
        {children}
      </div>
    </div>
  );
}
```

---

## Testing Plan

### Backend Testing

**Unit Tests:**
```python
def test_calculate_base_progress():
    weights = {"writing": 25, "splitting": 5, "synthesizing": 60}
    assert calculate_base_progress("writing", weights) == 0
    assert calculate_base_progress("splitting", weights) == 25
    assert calculate_base_progress("synthesizing", weights) == 30

def test_progress_updates_during_synthesis(test_client, test_db):
    # Create story, poll status, verify progress increases
    # Verify progress_detail shows "Synthesizing segment X of Y"
    pass

def test_progress_reaches_100_on_completion(test_client, test_db):
    # Create story, wait for completion
    # Verify final progress is 100.0
    pass
```

### Frontend Testing (Manual QA)

**Test Scenarios:**
1. **Short custom story (no illustrations):**
   - [ ] Progress ring fills smoothly
   - [ ] Percentage shown: 0% → 100%
   - [ ] Detail messages: "Synthesizing segment X of Y"
   - [ ] Completes in ~60 seconds

2. **Medium custom story with illustrations:**
   - [ ] Progress accounts for illustration time
   - [ ] Shows "Generating illustration X of 8"
   - [ ] Ring animation smooth throughout
   - [ ] Takes ~2-3 minutes, progress steady

3. **Historical story with illustrations:**
   - [ ] 5 illustrations tracked correctly
   - [ ] Progress weights correct for fewer images
   - [ ] Detail messages accurate

4. **Mobile responsiveness:**
   - [ ] Progress ring scales appropriately
   - [ ] Text remains readable
   - [ ] No layout overflow

---

## Success Criteria

- [ ] Users can see exact progress percentage at all times
- [ ] Detailed messages provide transparency (not stuck, just working)
- [ ] Progress ring provides clear visual feedback
- [ ] Long stages (synthesis, illustrations) show sub-progress
- [ ] Animation is smooth and professional
- [ ] Works for all story types (custom, historical, with/without illustrations)
- [ ] No performance impact (updates max once per second)

---

## Risks & Mitigations

**Risk 1: Progress updates too frequent (performance impact)**
- Mitigation: Throttle updates to max 1/second in node loops
- Mitigation: Only update when percentage changes by ≥1%

**Risk 2: Progress estimates inaccurate (some stages faster/slower)**
- Mitigation: Use empirical data from production logs
- Mitigation: Adjust weights after initial deployment
- Mitigation: Progress reaching 100% is most important (can adjust weights)

**Risk 3: Parallel stages (voice + illustrations) complicate progress**
- Mitigation: Show detail for whichever stage has updates
- Mitigation: Or show both: "Generating audio and illustrations (5 of 8)..."
- Mitigation: Test and iterate based on UX

---

## Future Enhancements

- **Estimated time remaining:** "About 45 seconds left..."
- **Step-by-step progress list:** Checkmarks for completed stages
- **Expandable details:** Click to see full progress log
- **Preview while generating:** Show title/genre while waiting
- **Cancel generation:** Add cancel button (requires backend support)

---

## Files Summary

**New Files:**
- `frontend/src/components/ProgressRing.tsx`
- `backend/tests/test_story_progress.py`

**Modified Files:**
- `backend/app/routes/story.py`
- `backend/app/graph/nodes/voice_synthesizer.py`
- `backend/app/graph/nodes/illustration_generator.py`
- `backend/app/models/responses.py`
- `frontend/src/types/index.ts`
- `frontend/src/routes/StoryRoute.tsx`
- `frontend/src/components/StoryScreen.tsx`

**Total:** 1 new frontend component, 1 new test file, 7 modified files

---

---

## Additional Requirements: Navigation Persistence

### Problem

**Current Limitation:**
- Users CANNOT navigate away during generation (5-10 min wait)
- If user leaves `/story/{jobId}` page, they lose the job ID
- No way to return to check on in-progress job
- URL is not shareable or bookmarkable during generation

**User Scenarios:**
1. User starts story generation → wants to do something else → can't leave page
2. User accidentally closes tab → loses job ID → can't find their story
3. Long generation (10 min) → user needs to multitask → stuck waiting

### Solution Required

**Add to Progress Indicator Implementation:**

#### 1. Persist In-Progress Jobs

**Store in localStorage:**
```typescript
// When job created
localStorage.setItem('taleweaver_active_job', JSON.stringify({
  jobId: job.job_id,
  startedAt: Date.now(),
  kidName: request.kid.name
}));

// Clear when complete or user creates new story
localStorage.removeItem('taleweaver_active_job');
```

#### 2. "Continue Watching" Link

**Add to navigation/hero screen:**
```tsx
// Check for active job on mount
const activeJob = localStorage.getItem('taleweaver_active_job');
if (activeJob) {
  const { jobId, startedAt } = JSON.parse(activeJob);
  const elapsed = Date.now() - startedAt;
  
  // If recent (< 30 min), show link
  if (elapsed < 30 * 60 * 1000) {
    return (
      <div className="glass-card p-4">
        <p>Story in progress...</p>
        <button onClick={() => navigate(`/story/${jobId}`)}>
          Continue Watching
        </button>
      </div>
    );
  }
}
```

#### 3. Recent Generations List

**Add to library or separate tab:**
- Show jobs from last 24 hours (from job_state table)
- Include status: processing, complete, failed
- Click to navigate to `/story/{jobId}`
- Auto-refresh processing jobs

**Query:**
```sql
SELECT job_id, status, current_stage, progress, title, created_at
FROM job_state
WHERE created_at > datetime('now', '-24 hours')
ORDER BY created_at DESC
LIMIT 10
```

#### 4. Make Job URLs Bookmarkable

**Ensure:**
- `/story/{jobId}` works for in-progress jobs (already does ✅)
- User can bookmark URL and return later
- Share URL with others (e.g., parent shares with partner)

**Implementation:**

**Frontend:**
- Save active job to localStorage on job creation
- Check localStorage on HeroRoute mount
- Show "Continue Watching" if active job exists
- Clear localStorage when job completes or user creates new

**Backend:**
- GET /api/jobs/recent endpoint (return jobs from last 24h)
- Cleanup old jobs from job_state (>24h and complete/failed)

**Tasks:**
- [ ] Add localStorage persistence in CraftRoute after job creation
- [ ] Add "Continue Watching" UI in HeroRoute
- [ ] Add GET /api/jobs/recent endpoint
- [ ] Add RecentJobs component (optional tab in library)
- [ ] Update cleanup to preserve jobs for 24h (not 1h)

**Estimated Additional Time:** +2 hours

---

**Estimated Time:** 6-8 hours (4-6 progress indicator + 2 navigation)  
**Priority:** Medium-High (UX improvement + safety)  
**Ready to Implement:** Yes
