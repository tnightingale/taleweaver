# Auto-Scrolling Transcript Feature

**Feature:** Sentence-Level Synchronized Transcript with Auto-Scroll  
**Created:** 2026-03-22  
**Status:** 🔵 PLANNING  
**Estimated Time:** 6-8 hours

---

## Overview

Add synchronized transcript that highlights and auto-scrolls to the current sentence as audio plays. Uses existing script segments for timing, provides subtle highlighting, and is toggleable.

**User Preferences:**
- **Sync Approach:** Option C - Sentence-level sync (uses existing segments)
- **Visibility:** Toggleable (can show/hide, default hidden)
- **Highlight Style:** Subtle (light glow on current sentence)

---

## Current Behavior

**Standard Player:**
- Transcript toggle button (show/hide)
- Full transcript in static scrollable div
- No synchronization with audio
- No indication of current position

**Illustrated Player:**
- Transcript shows scene-by-scene with illustrations
- Static, no audio sync
- Toggle show/hide

**User Pain Points:**
- No way to follow along with audio
- Helpful for kids learning to read
- Parents want to see where audio is in the story
- Useful for accessibility (deaf/hard of hearing can read along)

---

## Proposed Solution

### Visual Design

**Layout (Illustrated Player):**
```
┌────────────────────────────────────────┐
│  [Illustration with page turn]         │
│                                        │
│  Chapter 3 of 8: Because of that...   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  [Audio controls + seek bar]          │
│                                        │
│  [Show Transcript] button              │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ 📖 Transcript (Following Along)  │ │
│  │                                  │ │
│  │ Once upon a time, Mia lived...  │ │ ← dim
│  │                                  │ │
│  │ Every day she would explore...  │ │ ← dim
│  │                                  │ │
│  │ ✨ Until one day, she found a   │ │ ← HIGHLIGHTED (glow)
│  │    mysterious door...            │ │
│  │                                  │ │
│  │ Because of that, she stepped... │ │ ← dim
│  │                                  │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘
```

**Highlight Style:**
- Current sentence: text-white, subtle text-glow, scale: 1.02
- Other sentences: text-starlight/60, scale: 1.0
- Smooth transition between highlights (300ms)
- Auto-scroll to keep highlighted sentence centered

---

## Implementation Plan

### Stage 1: Backend Segment Timing (3-4 hours)

#### Architecture

**Goal:** Calculate timestamp for each script segment (sentence) based on audio duration.

**Current State:**
- `script_splitter` creates segments with speaker + text
- `voice_synthesizer` generates audio for each segment
- `audio_stitcher` combines audio but doesn't track timing
- No segment timestamps stored

**Solution:**
Add `segment_timings` to StoryState and persist to database.

#### Tasks

**1.1 Update StoryState**
- [ ] Add `segment_timings: Optional[list[dict]]` to StoryState TypedDict
- [ ] Structure: `[{"text": "...", "speaker": "...", "start": 0.0, "end": 5.2}, ...]`

**1.2 Create Segment Timing Calculator**
- [ ] Create new node: `backend/app/graph/nodes/segment_timer.py`
- [ ] Function: `segment_timer(state: StoryState) -> dict`
- [ ] Calculate timing based on audio segment lengths:
  ```python
  from pydub import AudioSegment
  
  segment_timings = []
  current_time = 0.0
  
  for segment, audio_bytes in zip(segments, audio_segments):
      audio = AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")
      duration = len(audio) / 1000.0  # Convert ms to seconds
      
      segment_timings.append({
          "text": segment["text"],
          "speaker": segment["speaker"],
          "start": round(current_time, 2),
          "end": round(current_time + duration, 2)
      })
      current_time += duration
  
  return {"segment_timings": segment_timings}
  ```
- [ ] Handle edge cases (empty segments, very short audio)

**1.3 Integrate into Pipeline**
- [ ] Add segment_timer node to pipeline
- [ ] Place after audio_stitcher, before timestamp_calculator
- [ ] Flow: `audio_stitcher → segment_timer → timestamp_calculator`
- [ ] Or merge into timestamp_calculator (both calculate timings)

**1.4 Update Story Persistence**
- [ ] Add `segment_timings` to scene_data JSON in database:
  ```python
  scene_data = {
      "scenes": final_state["scenes"],
      "segment_timings": final_state.get("segment_timings"),  # NEW
      "art_style_prompt": state.get("art_style"),
      "character_description": final_state.get("character_description"),
  }
  ```
- [ ] Update save_story to accept segment_timings
- [ ] Store in scene_data JSON (flexible schema)

**1.5 Update API Responses**
- [ ] Add `segment_timings` to JobCompleteResponse
- [ ] Add `segment_timings` to StoryResponse
- [ ] Return segment_timings from /api/permalink/{short_id}
- [ ] Return segment_timings from /api/stories

**Tests:**
- [ ] Test segment_timer calculates correct timestamps
- [ ] Test timestamps sum to total duration (±1 second)
- [ ] Test segment_timings persisted to database
- [ ] Test API returns segment_timings
- [ ] Test with various numbers of segments (5, 15, 30)

**Definition of Done:**
- ✅ Each segment has accurate start/end timestamps
- ✅ Timestamps based on actual audio duration (not estimates)
- ✅ Persisted in database
- ✅ Returned by API endpoints
- ✅ Tests passing

**Files Modified:**
- `backend/app/graph/state.py` - Add segment_timings field
- `backend/app/graph/nodes/segment_timer.py` - NEW node
- `backend/app/graph/pipeline.py` - Add segment_timer node
- `backend/app/routes/story.py` - Persist segment_timings
- `backend/app/models/responses.py` - Add to responses
- `backend/tests/test_segment_timer.py` - NEW tests

---

### Stage 2: Frontend Synchronized Transcript (3-4 hours)

#### Component Design

**SynchronizedTranscript Component:**
- Receives: `segments` (with timings), `currentTime` (from audio)
- Displays: List of sentences with highlighting
- Auto-scrolls: Current sentence to center of view
- Toggleable: Show/hide button

#### Tasks

**2.1 Update TypeScript Types**
- [ ] Add SegmentTiming interface:
  ```typescript
  interface SegmentTiming {
      text: string;
      speaker: string;
      start: number;
      end: number;
  }
  ```
- [ ] Add `segment_timings?: SegmentTiming[]` to JobCompleteResponse
- [ ] Add `segment_timings?: SegmentTiming[]` to StoryMetadata

**2.2 Create SynchronizedTranscript Component**
- [ ] Create `frontend/src/components/SynchronizedTranscript.tsx`
- [ ] Props:
  ```typescript
  interface Props {
      segments: SegmentTiming[];
      currentTime: number;
      isVisible: boolean;
      onToggle: () => void;
  }
  ```
- [ ] Calculate current segment index based on currentTime
- [ ] Use refs for each segment for scrollIntoView
- [ ] Highlight current segment with subtle glow
- [ ] Auto-scroll when segment changes
- [ ] Render segments in scrollable container

**2.3 Implement Auto-Scroll Logic**
- [ ] Create ref array: `const segmentRefs = useRef<(HTMLDivElement | null)[]>([])`
- [ ] Find current segment: 
  ```typescript
  const currentIndex = segments.findIndex(
      s => currentTime >= s.start && currentTime < s.end
  );
  ```
- [ ] Scroll when index changes:
  ```typescript
  useEffect(() => {
      if (currentIndex >= 0 && segmentRefs.current[currentIndex]) {
          segmentRefs.current[currentIndex]?.scrollIntoView({
              behavior: 'smooth',
              block: 'center'
          });
      }
  }, [currentIndex]);
  ```

**2.4 Implement Subtle Highlighting**
- [ ] Current segment styles:
  ```tsx
  className={currentIndex === i ? 
      "text-white text-glow transition-all duration-300 scale-102" : 
      "text-starlight/60 transition-all duration-300"
  }
  ```
- [ ] Add subtle background glow for current segment
- [ ] Smooth transitions between segments (300ms)
- [ ] Speaker indicator (for multi-voice stories)

**2.5 Integrate into Players**
- [ ] Update IllustratedStoryPlayer:
  - [ ] Add `showTranscript` state
  - [ ] Pass segment_timings to SynchronizedTranscript
  - [ ] Pass currentTime from audio element
  - [ ] Replace static transcript with SynchronizedTranscript
  - [ ] Keep scene-based structure (show segment within current scene)
- [ ] Update standard StoryScreen player:
  - [ ] Add SynchronizedTranscript for non-illustrated stories
  - [ ] Same logic, no scene grouping

**2.6 Layout Options**
- [ ] **Option A:** Transcript below player (always visible if toggled)
- [ ] **Option B:** Transcript in side panel (desktop) / bottom (mobile)
- [ ] **Option C:** Transcript overlays bottom of screen (like subtitles)
- [ ] Start with Option A (simpler), can enhance later

**2.7 Mobile Responsiveness**
- [ ] Transcript scrollable on mobile (max-height with overflow)
- [ ] Font size appropriate for mobile
- [ ] Touch-friendly (can tap to jump to segment)
- [ ] Collapsible to save screen space

**Tests (Manual QA):**
- [ ] Test highlighting accuracy (within ±0.5 seconds)
- [ ] Test auto-scroll keeps current sentence visible
- [ ] Test toggle show/hide works
- [ ] Test with different story lengths (short, medium, long)
- [ ] Test with various segment counts (5, 15, 30 segments)
- [ ] Test on mobile devices
- [ ] Test with illustrated vs standard player
- [ ] Verify no performance issues (smooth 60fps)

**Definition of Done:**
- ✅ Transcript highlights current sentence accurately
- ✅ Auto-scrolls smoothly to keep sentence in view
- ✅ Toggleable (can show/hide)
- ✅ Subtle highlighting (not distracting)
- ✅ Works for both illustrated and standard players
- ✅ Mobile responsive
- ✅ No layout jank or flickering

**Files Modified:**
- `frontend/src/types/index.ts` - SegmentTiming interface
- `frontend/src/components/SynchronizedTranscript.tsx` - NEW component
- `frontend/src/components/IllustratedStoryPlayer.tsx` - Integration
- `frontend/src/components/StoryScreen.tsx` - Integration for standard player
- `frontend/src/components/StandalonePlayer.tsx` - Pass segment_timings

---

## Alternative Implementation (Simpler)

If segment-level timing proves complex, can use scene-level timing (already exists):

**Simplified Approach:**
- Use existing scene timestamps from illustrations
- Highlight entire scene's text while it's playing
- Still provides "follow along" benefit
- Much simpler (2-3 hours instead of 6-8)
- Only works for illustrated stories

**Trade-off:** Less granular (scene vs sentence) but faster to implement.

---

## Success Criteria

- [ ] User can read along as story plays
- [ ] Highlighting is accurate (within ±1 second)
- [ ] Auto-scroll is smooth and keeps current text visible
- [ ] Toggle on/off works reliably
- [ ] Doesn't interfere with audio playback
- [ ] Works on all devices (desktop, tablet, mobile)
- [ ] Improves reading experience for kids
- [ ] Accessibility benefit for hearing-impaired

---

## Risks & Mitigations

**Risk 1: Segment timing inaccurate (TTS duration vs actual)**
- Mitigation: Calculate from actual audio file lengths (pydub)
- Mitigation: Test with real stories and adjust if needed
- Mitigation: ±1 second accuracy acceptable

**Risk 2: Auto-scroll too aggressive (distracting)**
- Mitigation: Use 'smooth' scroll behavior
- Mitigation: Only scroll if current segment not in view
- Mitigation: Center alignment (not top or bottom)

**Risk 3: Performance impact (too many DOM updates)**
- Mitigation: Only update on segment change (not every timeupdate)
- Mitigation: Use React.memo for segment components
- Mitigation: Throttle currentTime updates

**Risk 4: Works poorly with music/sound effects**
- Mitigation: Timing based on voice segments only (music is background)
- Mitigation: Test and verify accuracy

---

## User Experience Flow

### Initial State
- Transcript toggle button visible
- Transcript hidden by default
- User clicks "Show Transcript"

### During Playback
1. Transcript expands below player
2. First sentence highlighted (subtle glow)
3. As audio plays, highlighting moves sentence by sentence
4. View auto-scrolls to keep highlighted sentence in center
5. User can manually scroll (auto-scroll resumes on next segment change)
6. User can click "Hide Transcript" to collapse

### Benefits
- Educational: Kids can follow along and learn to read
- Accessibility: Deaf/hard of hearing can read the story
- Parental control: Parents can see story content
- Engagement: Visual + audio learning

---

## Future Enhancements

- **Click to jump:** Tap a sentence to jump audio to that timestamp
- **Speed controls:** Slower playback for early readers
- **Font size controls:** Larger text for accessibility
- **Word-level highlighting:** True karaoke mode (requires more work)
- **Dual language:** Show translation below each sentence
- **Downloadable transcript:** PDF export with timestamps

---

## Files Summary

**New Backend Files:**
- `backend/app/graph/nodes/segment_timer.py` - Timing calculator
- `backend/tests/test_segment_timer.py` - Tests

**New Frontend Files:**
- `frontend/src/components/SynchronizedTranscript.tsx` - Main component

**Modified Backend:**
- `backend/app/graph/state.py` - Add segment_timings
- `backend/app/graph/pipeline.py` - Add segment_timer node
- `backend/app/routes/story.py` - Persist segment_timings
- `backend/app/models/responses.py` - Add to API responses

**Modified Frontend:**
- `frontend/src/types/index.ts` - SegmentTiming interface
- `frontend/src/components/IllustratedStoryPlayer.tsx` - Integration
- `frontend/src/components/StoryScreen.tsx` - Integration

**Total:** 2 new components, 2 new test files, 8 modified files

---

## Implementation Stages

### Stage 1: Backend Timing (3-4 hours)
- Add segment_timer node
- Calculate timestamps from audio files
- Persist to database
- Update API responses
- Write tests

### Stage 2: Frontend Component (3-4 hours)
- Create SynchronizedTranscript component
- Implement highlighting logic
- Add auto-scroll
- Integrate into players
- Manual QA

---

## Testing Plan

### Backend Tests

```python
def test_segment_timer_calculates_timestamps():
    # Given segments with audio
    # When segment_timer runs
    # Then each segment has start/end timestamps
    pass

def test_timestamps_sum_to_total_duration():
    # Verify all segment durations sum to final audio duration
    # Allow ±1 second tolerance
    pass

def test_segment_timings_persisted_to_database():
    # Create story
    # Verify scene_data contains segment_timings
    pass
```

### Frontend Tests (Manual QA)

**Test Scenarios:**
1. **Short story (5 segments):**
   - [ ] All segments highlighted at correct times
   - [ ] Auto-scroll smooth
   - [ ] Highlighting transitions clean

2. **Long story (20+ segments):**
   - [ ] Scroll performance good
   - [ ] Current segment always visible
   - [ ] No lag or jank

3. **Illustrated story:**
   - [ ] Segments highlighted within current scene
   - [ ] Works with page turn animations
   - [ ] No conflicts with scene changes

4. **Mobile device:**
   - [ ] Transcript readable (font size)
   - [ ] Scroll container appropriate height
   - [ ] Toggle button accessible
   - [ ] No horizontal overflow

5. **Edge cases:**
   - [ ] Very short segments (<1 second)
   - [ ] Very long segments (>10 seconds)
   - [ ] Rapid segment changes
   - [ ] User manual scroll during playback

---

## Success Criteria

- [ ] Segment highlighting accurate (within ±1 second)
- [ ] Auto-scroll smooth and centered
- [ ] Toggle works reliably
- [ ] Subtle highlighting (not distracting from story)
- [ ] No performance impact on audio playback
- [ ] Works on desktop and mobile
- [ ] Improves reading experience for kids
- [ ] Parents report positive feedback

---

## Design Details

### Highlighting Style (Subtle)

**Current Segment:**
```css
.current-segment {
    color: white;
    text-shadow: 0 0 20px rgba(168, 85, 247, 0.6);
    transform: scale(1.02);
    font-weight: 500;
    transition: all 300ms ease-out;
}
```

**Other Segments:**
```css
.other-segment {
    color: rgba(255, 255, 255, 0.6);
    transform: scale(1.0);
    transition: all 300ms ease-out;
}
```

**Container:**
```css
.transcript-container {
    max-height: 400px;
    overflow-y: auto;
    padding: 1.5rem;
    scroll-behavior: smooth;
}
```

### Scroll Behavior

**Auto-Scroll Trigger:**
- Only when currentSegmentIndex changes
- Not on every timeUpdate (too frequent)
- Smooth scroll with `block: 'center'`

**User Manual Scroll:**
- User can scroll manually
- Auto-scroll doesn't interrupt if user is scrolling
- Detect user scroll: `isUserScrolling` state (debounced)
- Resume auto-scroll after 3 seconds of no user interaction

---

## Estimated Effort Breakdown

| Task | Time | Notes |
|------|------|-------|
| Backend: segment_timer node | 2 hours | Calculate timestamps from audio |
| Backend: Pipeline integration | 1 hour | Add node, persist data |
| Backend: API updates | 0.5 hour | Return segment_timings |
| Backend: Tests | 0.5 hour | 3-4 tests |
| Frontend: SynchronizedTranscript | 2 hours | Component with highlighting |
| Frontend: Auto-scroll logic | 1 hour | scrollIntoView + smooth behavior |
| Frontend: Integration | 1 hour | Both players |
| Frontend: Manual QA | 1 hour | Test scenarios |
| **Total** | **6-8 hours** | |

---

## Priority & Dependencies

**Priority:** Medium (UX enhancement, educational value)  
**Dependencies:** 
- Requires illustration feature (for scene_data structure) ✅ Already merged
- No other blockers

**Can implement immediately after:**
- Enhanced progress indicator (or in parallel)

---

## Accessibility Benefits

- 🦻 **Hearing-impaired users** can read along
- 👶 **Early readers** can follow text while listening
- 🌍 **Language learners** can see words while hearing pronunciation
- 👨‍👩‍👧 **Parents** can monitor story content in real-time

---

**Estimated Time:** 6-8 hours (3-4 backend + 3-4 frontend)  
**Priority:** Medium (educational + accessibility value)  
**Ready to Implement:** Yes (after progress indicator or in parallel)
