# Story Illustrations Feature - Implementation Plan

**Feature:** AI-Generated Illustrations for Stories (NanoBanana 2 Integration)  
**Started:** 2026-03-21  
**Status:** 🔵 NOT STARTED

---

## Overview

Add AI-generated illustrations synchronized with story audio playback. Uses NanoBanana 2 (Google Gemini 3.1 Flash Image) to generate 5-8 illustrations per story corresponding to Story Spine narrative beats. Illustrations are optional (opt-out), with curated art style presets and image-to-image consistency.

**Key Design Principles:**
- ✅ **Decoupled Architecture**: Image generation and playback are independent
- ✅ **Provider Pattern**: Easy to swap image providers (NanoBanana 2 → DALL-E → Flux)
- ✅ **Progressive Enhancement**: Stories work perfectly without illustrations
- ✅ **Future-Ready**: Architecture supports regeneration and alternative playback modes

**User Decisions:**
- Scene count: Story Spine beats (8 custom, 5 historical)
- UI placement: Separate optional step after story config
- Default: Opt-out (illustrations enabled by default, user can skip)
- Aspect ratio: 4:3 (traditional storybook feel)
- Transitions: Page turn effect

**Cost Analysis:**
- Custom stories (8 scenes): $0.36/story
- Historical stories (5 scenes): $0.225/story
- Average: ~$0.30/story
- Generation time overhead: +25-40 seconds

---

## Stage Overview

| Stage | Description | Status | Estimated Time | Tests |
|-------|-------------|--------|----------------|-------|
| 1 | Database Schema & Models | 🔵 NOT STARTED | 4-6 hours | 5 tests |
| 2 | Art Style System & API | 🔵 NOT STARTED | 6-8 hours | 4 tests |
| 3 | Scene Analyzer Node | 🔵 NOT STARTED | 8-10 hours | 6 tests |
| 4 | Illustration Provider | 🔵 NOT STARTED | 10-12 hours | 8 tests |
| 5 | Pipeline Integration | 🔵 NOT STARTED | 8-10 hours | 6 tests |
| 6 | Frontend: Art Style Selector | 🔵 NOT STARTED | 6-8 hours | - |
| 7 | Frontend: Illustrated Player | 🔵 NOT STARTED | 10-12 hours | - |
| 8 | Testing & Polish | 🔵 NOT STARTED | 8-10 hours | - |

**Overall Progress:** 0/29 tests passing  
**Total Estimated Time:** 60-76 hours (1.5-2 weeks)

---

## Stage 1: Database Schema & Models 🔵 NOT STARTED

**Objective:** Extend database and type definitions to support illustration metadata

**Branch:** `feature/illustrations-schema`  
**Worktree:** TBD  
**Estimated Time:** 4-6 hours

### Tasks

#### Backend - Database
- [ ] Create migration: `add_illustration_fields.py`
  - [ ] Add `art_style` column (String, nullable)
  - [ ] Add `has_illustrations` column (Boolean, default=False)
  - [ ] Add `scene_data` column (JSON, nullable)
- [ ] Update `Story` model in `backend/app/db/models.py`
- [ ] Test migration (up and down)

#### Backend - Type Definitions
- [ ] Update `StoryState` TypedDict in `backend/app/graph/state.py`
  - [ ] Add `art_style: Optional[str]`
  - [ ] Add `scenes: Optional[list[Scene]]`
  - [ ] Add `character_description: Optional[str]`
- [ ] Create new `Scene` TypedDict in `backend/app/graph/state.py`
  - [ ] Fields: beat_index, beat_name, text_excerpt, illustration_prompt, timestamp_start, timestamp_end, word_count, image_path, image_url, generation_metadata
- [ ] Update request models in `backend/app/models/requests.py`
  - [ ] Add `art_style: Optional[str]` to CreateCustomStoryRequest
  - [ ] Add `art_style: Optional[str]` to CreateHistoricalStoryRequest
  - [ ] Add `custom_art_style_prompt: Optional[str]` to both
- [ ] Update response models in `backend/app/models/responses.py`
  - [ ] Create `SceneResponse` model
  - [ ] Add illustration fields to `JobCompleteResponse`
  - [ ] Add illustration fields to `StoryResponse`

#### Tests
- [ ] `test_migration_adds_illustration_columns` - Verify columns exist after migration
- [ ] `test_migration_rollback` - Verify clean rollback
- [ ] `test_story_model_with_illustrations` - Create story with scene_data JSON
- [ ] `test_scene_state_typeddict` - Validate Scene structure
- [ ] `test_api_models_serialization` - Ensure illustration fields serialize correctly

**Definition of Done:**
- ✅ Migration runs successfully (up and down)
- ✅ Story model can store scene_data JSON
- ✅ All type definitions updated
- ✅ 5/5 tests passing
- ✅ No breaking changes to existing functionality

**Files Modified:**
- `backend/app/db/models.py`
- `backend/app/graph/state.py`
- `backend/app/models/requests.py`
- `backend/app/models/responses.py`
- New: `backend/app/db/migrations/add_illustration_fields.py`
- New: `backend/tests/test_illustration_models.py`

---

## Stage 2: Art Style System & API 🔵 NOT STARTED

**Objective:** Create art style presets and API endpoint for frontend consumption

**Branch:** `feature/art-styles`  
**Worktree:** TBD  
**Estimated Time:** 6-8 hours

### Tasks

#### Backend - Art Styles Data
- [ ] Create `backend/app/data/art_styles.py`
  - [ ] Define `ART_STYLES` dictionary with 7 presets:
    - [ ] `watercolor_dream` - Soft watercolor painting
    - [ ] `classic_storybook` - Traditional gouache illustration
    - [ ] `modern_flat` - Bold flat design with geometric shapes
    - [ ] `whimsical_ink` - Pen and ink with watercolor washes
    - [ ] `digital_fantasy` - Vibrant digital fantasy art
    - [ ] `vintage_fairy_tale` - 1960s nostalgic storybook
    - [ ] `custom` - User provides own prompt
  - [ ] Each style includes: name, description, prompt, preview_url
- [ ] Create art style prompt templates for consistency

#### Backend - API Endpoint
- [ ] Add `GET /api/art-styles` endpoint in `backend/app/routes/config.py`
  - [ ] Return list of available art styles
  - [ ] Include id, name, description, preview_url for each
- [ ] Add response model `ArtStyleResponse` in `backend/app/models/responses.py`

#### Tests
- [ ] `test_art_styles_data_structure` - Validate ART_STYLES dictionary format
- [ ] `test_get_art_styles_endpoint` - Verify endpoint returns all styles
- [ ] `test_art_style_prompts_valid` - Ensure prompts are non-empty (except custom)
- [ ] `test_custom_style_allows_user_prompt` - Verify custom style handling

**Definition of Done:**
- ✅ 7 art style presets defined with quality prompts
- ✅ API endpoint returns art styles in consumable format
- ✅ 4/4 tests passing
- ✅ Documentation for each art style

**Files Modified:**
- `backend/app/routes/config.py`
- `backend/app/models/responses.py`
- New: `backend/app/data/art_styles.py`
- New: `backend/tests/test_art_styles.py`

**Optional (Future):**
- [ ] Generate preview images for each art style
- [ ] Store previews in `/storage/art-style-previews/`
- [ ] Update preview_url fields to point to actual images

---

## Stage 3: Scene Analyzer Node 🔵 NOT STARTED

**Objective:** LLM-powered scene detection and illustration prompt generation

**Branch:** `feature/scene-analyzer`  
**Worktree:** TBD  
**Estimated Time:** 8-10 hours

### Tasks

#### Backend - Prompt Engineering
- [ ] Create `backend/app/prompts/scene_analysis.py`
  - [ ] Write structured prompt for Story Spine beat detection
  - [ ] Include JSON output format specification
  - [ ] Add examples for custom vs historical stories
  - [ ] Handle edge cases (stories without clear beats)
- [ ] Create prompt for character description extraction
  - [ ] Extract protagonist's physical appearance
  - [ ] Focus on consistent details (hair, eyes, age, clothing)

#### Backend - Scene Analyzer Node
- [ ] Create `backend/app/graph/nodes/scene_analyzer.py`
  - [ ] Implement `scene_analyzer(state: StoryState) -> dict`
  - [ ] Call LLM with scene analysis prompt
  - [ ] Parse JSON response into Scene TypedDict list
  - [ ] Extract character description for consistency
  - [ ] Calculate word count per scene for timestamp estimation
  - [ ] Handle LLM parsing errors gracefully
- [ ] Add logging for scene detection results
- [ ] Validate scene count matches expected (8 custom, 5 historical)

#### Tests
- [ ] `test_scene_analyzer_custom_story` - Detects 8 Story Spine beats
- [ ] `test_scene_analyzer_historical_story` - Detects 5 narrative beats
- [ ] `test_scene_analyzer_extracts_character_description` - Character details captured
- [ ] `test_scene_analyzer_generates_illustration_prompts` - Prompts are detailed
- [ ] `test_scene_analyzer_invalid_json_handling` - Graceful error handling
- [ ] `test_scene_analyzer_word_count_distribution` - Word counts sum to story total

**Definition of Done:**
- ✅ Scene analyzer correctly identifies Story Spine beats (90%+ accuracy)
- ✅ Illustration prompts are detailed and visual
- ✅ Character description extracted consistently
- ✅ 6/6 tests passing
- ✅ Integration test with real story examples

**Files Modified:**
- New: `backend/app/graph/nodes/scene_analyzer.py`
- New: `backend/app/prompts/scene_analysis.py`
- New: `backend/tests/test_scene_analyzer.py`

**Validation Criteria:**
- Manual review of 5 generated scene breakdowns
- Illustration prompts should be 2-3 sentences minimum
- Character descriptions should include 3+ physical details

---

## Stage 4: Illustration Provider 🔵 NOT STARTED

**Objective:** Provider pattern for image generation (NanoBanana 2 implementation)

**Branch:** `feature/illustration-provider`  
**Worktree:** TBD  
**Estimated Time:** 10-12 hours

### Tasks

#### Backend - Provider Abstraction
- [ ] Create `backend/app/services/illustration/base.py`
  - [ ] Define `IllustrationProvider` abstract base class
  - [ ] Method: `generate_image(prompt, art_style, reference_image_url, **kwargs) -> bytes`
  - [ ] Method: `get_provider_info() -> dict` (for metadata)
- [ ] Create `backend/app/services/illustration/factory.py`
  - [ ] Implement `get_illustration_provider() -> IllustrationProvider`
  - [ ] Read `ILLUSTRATION_PROVIDER` env var (default: nanobanana2)
  - [ ] Return appropriate provider instance

#### Backend - NanoBanana 2 Provider
- [ ] Create `backend/app/services/illustration/nanobanana.py`
  - [ ] Implement `NanoBanana2Provider` class
  - [ ] API integration (POST to NanoBanana 2 endpoint)
  - [ ] Support text-to-image mode (first image)
  - [ ] Support image-to-image mode (subsequent images for consistency)
  - [ ] Handle async HTTP requests (httpx)
  - [ ] Task polling if API is async
  - [ ] Error handling (rate limits, timeouts, invalid prompts)
  - [ ] Respect resolution (2K), aspect ratio (4:3), format (PNG)
- [ ] Add retry logic with exponential backoff
- [ ] Add request/response logging

#### Backend - Image Storage
- [ ] Create utility functions in `backend/app/utils/storage.py`
  - [ ] `save_illustration(story_id: str, scene_index: int, image_bytes: bytes) -> str`
  - [ ] `get_illustration_url(story_id: str, scene_index: int) -> str`
  - [ ] `delete_story_illustrations(story_id: str) -> None`
- [ ] Store images at `/storage/stories/{story_id}/scene_{index}.png`

#### Environment Configuration
- [ ] Update `.env.example` with illustration provider settings
  - [ ] `ILLUSTRATION_PROVIDER=nanobanana2`
  - [ ] `NANOBANANA_API_KEY=`
  - [ ] `ILLUSTRATION_ASPECT_RATIO=4:3`
  - [ ] `ILLUSTRATION_RESOLUTION=2K`

#### Tests
- [ ] `test_nanobanana_provider_text_to_image` - Generate first image
- [ ] `test_nanobanana_provider_image_to_image` - Generate with reference
- [ ] `test_nanobanana_provider_error_handling` - Invalid API key
- [ ] `test_nanobanana_provider_timeout` - Handle slow response
- [ ] `test_illustration_storage` - Save and retrieve images
- [ ] `test_provider_factory` - Correct provider returned
- [ ] `test_provider_metadata` - Provider info accessible
- [ ] `test_image_consistency_chain` - Multiple images maintain style

**Definition of Done:**
- ✅ NanoBanana 2 provider generates images successfully
- ✅ Image-to-image consistency technique working
- ✅ Images stored with correct paths
- ✅ 8/8 tests passing (may need mocking for API calls)
- ✅ Error handling prevents pipeline crashes

**Files Modified:**
- New: `backend/app/services/illustration/base.py`
- New: `backend/app/services/illustration/nanobanana.py`
- New: `backend/app/services/illustration/factory.py`
- New: `backend/app/utils/storage.py`
- Modified: `backend/.env.example`
- New: `backend/tests/test_illustration_provider.py`

**Manual Testing Required:**
- Real API calls to NanoBanana 2 (smoke test)
- Visual inspection of generated images
- Consistency check across image sequence

---

## Stage 5: Pipeline Integration 🔵 NOT STARTED

**Objective:** Integrate illustration generation into LangGraph pipeline

**Branch:** `feature/pipeline-integration`  
**Worktree:** TBD  
**Estimated Time:** 8-10 hours

### Tasks

#### Backend - Illustration Generator Node
- [ ] Create `backend/app/graph/nodes/illustration_generator.py`
  - [ ] Implement `illustration_generator(state: StoryState) -> dict`
  - [ ] Check if art_style is set (skip if None)
  - [ ] Get illustration provider from factory
  - [ ] Get art style prompt from ART_STYLES
  - [ ] Handle custom art style prompts
  - [ ] Loop through scenes and generate images:
    - [ ] First scene: text-to-image (no reference)
    - [ ] Subsequent scenes: image-to-image (previous as reference)
  - [ ] Save images to storage
  - [ ] Update scene metadata with image paths and URLs
  - [ ] Add generation_metadata to each scene
- [ ] Add progress logging for illustration generation

#### Backend - Timestamp Calculator Node
- [ ] Create `backend/app/graph/nodes/timestamp_calculator.py`
  - [ ] Implement `timestamp_calculator(state: StoryState) -> dict`
  - [ ] Calculate timestamps based on word count distribution
  - [ ] Allocate proportional time to each scene
  - [ ] Update scene timestamp_start and timestamp_end
  - [ ] Handle edge cases (empty scenes, very short stories)

#### Backend - Pipeline Updates
- [ ] Update `backend/app/graph/pipeline.py`
  - [ ] Add `scene_analyzer` node
  - [ ] Add `illustration_generator` node
  - [ ] Add `timestamp_calculator` node
  - [ ] Update pipeline flow:
    - [ ] `story_writer` → `scene_analyzer` → `script_splitter`
    - [ ] `script_splitter` → (`voice_synthesizer` || `illustration_generator`)
    - [ ] Both → `audio_stitcher` → `timestamp_calculator` → END
  - [ ] Ensure parallel execution for voice + illustrations
- [ ] Update stage tracking in job status
  - [ ] Add "analyzing_scenes" stage
  - [ ] Add "generating_illustrations" stage

#### Backend - Story Creation Routes
- [ ] Update `POST /api/story/custom` to accept art_style
- [ ] Update `POST /api/story/historical` to accept art_style
- [ ] Handle custom_art_style_prompt if art_style="custom"
- [ ] Pass art_style to pipeline state

#### Backend - Story Persistence
- [ ] Update story saving logic in `backend/app/main.py`
  - [ ] Save art_style to database
  - [ ] Save scene_data JSON to database
  - [ ] Set has_illustrations flag
- [ ] Update story retrieval to include scene data
  - [ ] `GET /api/stories/{short_id}` returns scenes
  - [ ] `GET /s/{short_id}` returns scenes

#### Tests
- [ ] `test_illustration_generator_skips_when_no_art_style` - No images if art_style=None
- [ ] `test_illustration_generator_generates_all_scenes` - 8 images for custom story
- [ ] `test_timestamp_calculator_distributes_time` - Timestamps sum to duration
- [ ] `test_pipeline_with_illustrations` - End-to-end with illustrations
- [ ] `test_pipeline_without_illustrations` - End-to-end without (backward compat)
- [ ] `test_story_persistence_with_scenes` - Scene data saved to DB

**Definition of Done:**
- ✅ Pipeline generates stories with illustrations end-to-end
- ✅ Pipeline still works without illustrations (backward compatible)
- ✅ Scene timestamps accurate (±5% of actual audio)
- ✅ 6/6 tests passing
- ✅ Job status updates reflect illustration progress
- ✅ Story database records include scene_data

**Files Modified:**
- New: `backend/app/graph/nodes/illustration_generator.py`
- New: `backend/app/graph/nodes/timestamp_calculator.py`
- Modified: `backend/app/graph/pipeline.py`
- Modified: `backend/app/routes/story.py`
- Modified: `backend/app/main.py`
- New: `backend/tests/test_pipeline_with_illustrations.py`

**Performance Validation:**
- Measure end-to-end generation time (should be +25-40 seconds max)
- Verify parallel execution (illustrations don't block voice synthesis)
- Monitor memory usage (image bytes in state)

---

## Stage 6: Frontend - Art Style Selector 🔵 NOT STARTED

**Objective:** UI for parents to choose illustration style during story creation

**Branch:** `feature/art-style-selector-ui`  
**Worktree:** TBD  
**Estimated Time:** 6-8 hours

### Tasks

#### Frontend - Type Definitions
- [ ] Update `frontend/src/types/index.ts`
  - [ ] Add `ArtStyle` interface
  - [ ] Add `Scene` interface
  - [ ] Update `JobCompleteResponse` to include illustration fields
  - [ ] Update `StoryResponse` to include illustration fields

#### Frontend - API Client
- [ ] Update `frontend/src/api/client.ts`
  - [ ] Add `fetchArtStyles()` function
  - [ ] Update `createCustomStory()` to accept artStyle param
  - [ ] Update `createHistoricalStory()` to accept artStyle param

#### Frontend - Art Style Selector Component
- [ ] Create `frontend/src/components/ArtStyleSelector.tsx`
  - [ ] Fetch art styles from `/api/art-styles` on mount
  - [ ] Display styles in grid layout (2 cols mobile, 3 cols desktop)
  - [ ] Each style card shows:
    - [ ] Preview image (placeholder if not available)
    - [ ] Style name
    - [ ] Description
    - [ ] Selected indicator (glow effect)
  - [ ] "Skip Illustrations" option (art_style = null)
  - [ ] Custom style option with textarea for prompt
  - [ ] Handle loading and error states
  - [ ] Maintain selection state

#### Frontend - Integration into Story Creation Flow
- [ ] Update `frontend/src/routes/CraftRoute.tsx`
  - [ ] Add new step after genre/mood/length selection
  - [ ] "Choose Illustration Style (Optional)" heading
  - [ ] Render ArtStyleSelector component
  - [ ] Pass selected artStyle to story creation API call
  - [ ] Allow "Back" and "Skip" navigation
- [ ] Update progress indicator to show new step

#### Frontend - Styling
- [ ] Style art style cards with glassmorphism
- [ ] Hover effects (glow, scale)
- [ ] Selected state (border glow, checkmark)
- [ ] Responsive grid layout
- [ ] Accessible keyboard navigation

**Definition of Done:**
- ✅ Art style selector displays all presets
- ✅ User can select, deselect, and skip
- ✅ Custom prompt textarea functional
- ✅ Selection persists through navigation
- ✅ API sends art_style to backend
- ✅ Mobile and desktop responsive

**Files Modified:**
- Modified: `frontend/src/types/index.ts`
- Modified: `frontend/src/api/client.ts`
- New: `frontend/src/components/ArtStyleSelector.tsx`
- Modified: `frontend/src/routes/CraftRoute.tsx`

**Design Notes:**
- Art style cards should feel premium (high-quality previews in future)
- "Skip Illustrations" should be prominent but not default-selected
- Custom prompt textarea should have character counter (suggest 50-200 chars)

---

## Stage 7: Frontend - Illustrated Story Player 🔵 NOT STARTED

**Objective:** Display synchronized illustrations with page turn transitions

**Branch:** `feature/illustrated-player`  
**Worktree:** TBD  
**Estimated Time:** 10-12 hours

### Tasks

#### Frontend - Illustrated Player Component
- [ ] Create `frontend/src/components/IllustratedStoryPlayer.tsx`
  - [ ] Accept props: audioUrl, scenes, title, durationSeconds, transcript
  - [ ] Render current scene's illustration based on audio currentTime
  - [ ] Implement page turn transition effect (framer-motion)
  - [ ] Display scene indicator: "Chapter X of Y: [beat_name]"
  - [ ] Render audio controls (seek bar, play/pause, time display)
  - [ ] Add scene markers on seek bar (clickable)
  - [ ] Click marker to jump to scene
  - [ ] Handle missing illustrations gracefully (show placeholder or skip)
  - [ ] Fallback to standard player if no scenes

#### Frontend - Page Turn Animation
- [ ] Research/implement CSS 3D page turn effect
  - [ ] Use framer-motion for smooth transitions
  - [ ] Implement book-like flip animation
  - [ ] Add subtle shadow/depth for realism
  - [ ] Duration: 500-800ms per turn
- [ ] Trigger animation on scene change (based on timestamp)
- [ ] Allow manual page turn (click/swipe for next/prev scene)

#### Frontend - Scene Navigation
- [ ] Add scene markers to seek bar
  - [ ] Visual indicator at each scene's timestamp_start
  - [ ] Hover shows scene beat_name tooltip
  - [ ] Click marker to jump to scene timestamp
- [ ] Add next/previous scene buttons (optional)
- [ ] Keyboard shortcuts: Arrow keys for scene navigation

#### Frontend - Layout & Responsive Design
- [ ] Desktop layout:
  - [ ] Large illustration centered above player
  - [ ] 4:3 aspect ratio maintained
  - [ ] Scene indicator above illustration
  - [ ] Audio controls below illustration
- [ ] Mobile layout:
  - [ ] Full-width illustration
  - [ ] Vertically stacked layout
  - [ ] Touch-friendly controls
- [ ] Tablet optimization (medium breakpoint)

#### Frontend - Transcript Enhancement
- [ ] Split transcript by scenes
- [ ] Display illustration inline with each scene's text
- [ ] Scene headings ("Chapter 1: Once upon a time")
- [ ] Becomes readable illustrated storybook format
- [ ] Toggle between audio player and static transcript view

#### Frontend - Integration
- [ ] Update `frontend/src/components/StoryScreen.tsx`
  - [ ] Check if storyData has scenes and has_illustrations
  - [ ] Render IllustratedStoryPlayer if illustrations exist
  - [ ] Fallback to standard player if no illustrations
- [ ] Update `frontend/src/routes/StoryRoute.tsx` (if needed)
- [ ] Ensure permalink stories load illustrations correctly

#### Frontend - Loading & Error States
- [ ] Show loading placeholder while images load
- [ ] Progressive image loading (low-res → high-res blur-up)
- [ ] Handle missing image URLs gracefully
- [ ] Error state if image fails to load (show placeholder)

**Definition of Done:**
- ✅ Illustrations display synchronized with audio
- ✅ Page turn animation smooth and realistic
- ✅ Scene markers on seek bar functional
- ✅ Click marker jumps to scene
- ✅ Responsive on mobile, tablet, desktop
- ✅ Fallback to standard player works
- ✅ Transcript view shows illustrated storybook format

**Files Modified:**
- New: `frontend/src/components/IllustratedStoryPlayer.tsx`
- Modified: `frontend/src/components/StoryScreen.tsx`
- Modified: `frontend/src/routes/StoryRoute.tsx` (if needed)

**Design References:**
- Research CSS page turn effects (CodePen, framer-motion examples)
- Study children's storybook apps for inspiration (Epic!, Khan Academy Kids)
- Ensure accessibility (ARIA labels, keyboard nav, screen reader support)

---

## Stage 8: Testing & Polish 🔵 NOT STARTED

**Objective:** End-to-end testing, performance optimization, and UX polish

**Branch:** `feature/illustrations-polish`  
**Worktree:** TBD  
**Estimated Time:** 8-10 hours

### Tasks

#### Backend - Integration Testing
- [ ] Create end-to-end test: custom story with illustrations
  - [ ] POST story with art_style
  - [ ] Poll job status through all stages
  - [ ] Verify scene_data in response
  - [ ] Verify image files exist on disk
  - [ ] Verify timestamps calculated correctly
- [ ] Create end-to-end test: historical story with illustrations
- [ ] Test story without illustrations (art_style=null)
- [ ] Test custom art style prompt
- [ ] Load testing: Generate 5 stories in parallel
- [ ] Measure performance impact (time, memory, disk space)

#### Backend - Error Handling & Resilience
- [ ] Handle NanoBanana 2 API failures gracefully
  - [ ] If illustration generation fails, continue pipeline without images
  - [ ] Set has_illustrations=false and log error
  - [ ] Don't crash entire story generation
- [ ] Implement retry logic for transient failures
- [ ] Add timeout protection (max 90 seconds for all illustrations)
- [ ] Validate image file sizes (reject if > 10MB)
- [ ] Handle corrupted image responses

#### Frontend - Testing
- [ ] Manual testing on multiple devices:
  - [ ] Desktop (Chrome, Firefox, Safari)
  - [ ] Mobile (iOS Safari, Android Chrome)
  - [ ] Tablet (iPad, Android tablet)
- [ ] Test user flows:
  - [ ] Create story with watercolor_dream style
  - [ ] Create story with custom style prompt
  - [ ] Create story without illustrations (skip)
  - [ ] Play story with illustrations (verify sync)
  - [ ] Navigate scenes via markers
  - [ ] Read transcript (verify illustrated format)
- [ ] Test edge cases:
  - [ ] Very short story (2 minutes)
  - [ ] Very long story (5 minutes)
  - [ ] Missing image URLs (should show placeholder)
  - [ ] Slow network (progressive loading)

#### Performance Optimization
- [ ] Optimize image sizes (compress without quality loss)
- [ ] Implement lazy loading for illustrations
- [ ] Cache art styles in frontend (localStorage)
- [ ] Monitor backend memory usage during parallel generation
- [ ] Profile scene analyzer LLM call (optimize prompt if slow)
- [ ] Consider CDN for serving images (future enhancement)

#### UX Polish
- [ ] Add loading spinner during illustration generation
  - [ ] "Generating illustrations..." stage label
  - [ ] Optional: Show preview of first illustration while others generate
- [ ] Add animation when art style selected (subtle glow/scale)
- [ ] Improve page turn animation timing (natural feel)
- [ ] Add subtle audio cue on scene change (optional)
- [ ] Ensure all buttons/controls have hover states
- [ ] Add tooltips for scene markers
- [ ] Improve mobile touch targets (44x44px minimum)

#### Documentation
- [ ] Update `README.md` with illustration feature overview
- [ ] Update `DEVELOPMENT.md` with:
  - [ ] NanoBanana 2 API setup instructions
  - [ ] How to add new art style presets
  - [ ] How to implement alternative providers
- [ ] Add inline code comments for complex logic
- [ ] Document scene_data JSON structure
- [ ] Create architecture diagram (generation flow)

#### Cost Monitoring
- [ ] Add logging for illustration costs
  - [ ] Track number of images generated per story
  - [ ] Log provider used, resolution, aspect ratio
  - [ ] Calculate cost per story
- [ ] Create dashboard/script to monitor monthly costs
- [ ] Set up alerts if costs exceed threshold

**Definition of Done:**
- ✅ All 29 tests passing (backend)
- ✅ Manual testing complete on 3+ devices
- ✅ End-to-end user flow works flawlessly
- ✅ Error handling prevents pipeline crashes
- ✅ Performance within acceptable range (+25-40s)
- ✅ Documentation updated
- ✅ Cost monitoring in place

**Files Modified:**
- New: `backend/tests/test_illustrations_e2e.py`
- Modified: `README.md`
- Modified: `DEVELOPMENT.md`
- Modified: Various files for polish and optimization

---

## Future Enhancements (Not in Scope)

### Phase 2: Regeneration Support
- [ ] `POST /api/stories/{short_id}/regenerate-illustrations` endpoint
- [ ] Regenerate all illustrations with new art style
- [ ] Keep audio, scenes, transcript unchanged
- [ ] Update frontend to show "Regenerate Illustrations" button

### Phase 3: Partial Regeneration
- [ ] `POST /api/stories/{short_id}/regenerate-scene/{scene_index}` endpoint
- [ ] Regenerate single scene's illustration
- [ ] Useful if one image looks off

### Phase 4: Alternative Providers
- [ ] Implement DALL-E 3 provider
- [ ] Implement Flux provider
- [ ] Implement Stable Diffusion provider
- [ ] Add provider selection in admin settings

### Phase 5: Art Style Previews
- [ ] Generate preview images for each art style preset
- [ ] Store in `/storage/art-style-previews/`
- [ ] Display in art style selector

### Phase 6: Character Consistency Improvements
- [ ] Generate dedicated character reference sheet (3 angles)
- [ ] Use LoRA or fine-tuning for specific characters
- [ ] Allow parents to upload reference image of child

### Phase 7: Advanced Playback Modes
- [ ] Slideshow mode (auto-advance scenes with narration)
- [ ] Comic book mode (all scenes in scrollable grid)
- [ ] Printable storybook PDF export

---

## Risk Mitigation

### Risk 1: NanoBanana 2 API Reliability
**Impact:** High  
**Probability:** Medium  
**Mitigation:**
- Implement retry logic with exponential backoff
- Set generous timeouts (30s per image)
- Graceful degradation: continue without illustrations if API fails
- Monitor API status via provider health endpoint

### Risk 2: Image Generation Consistency
**Impact:** Medium  
**Probability:** Medium  
**Mitigation:**
- Use image-to-image mode with previous image as reference
- Include character description in every prompt
- Test with multiple stories and manual review
- Allow regeneration in future phase

### Risk 3: Performance Impact
**Impact:** Medium  
**Probability:** Low  
**Mitigation:**
- Run illustration generation in parallel with voice synthesis
- Set maximum timeout for illustration node (90s)
- Monitor memory usage (image bytes in state)
- Consider offloading to background job queue (future)

### Risk 4: Cost Overruns
**Impact:** Low  
**Probability:** Low  
**Mitigation:**
- Absorbing costs as agreed ($0.30/story is acceptable)
- Implement cost logging and monitoring
- Set up alerts if monthly costs exceed threshold
- Consider caching/reusing illustrations for similar prompts (future)

### Risk 5: UX Complexity
**Impact:** Low  
**Probability:** Low  
**Mitigation:**
- Make illustrations opt-out (enabled by default but skippable)
- Ensure fallback to standard player works seamlessly
- Extensive user testing before release
- Iterate based on parent feedback

---

## Success Metrics

### Technical Metrics
- [ ] 100% test coverage for new code
- [ ] Zero pipeline crashes due to illustration failures
- [ ] Illustration generation adds <40 seconds to total time
- [ ] Image consistency rated 7/10+ in manual review
- [ ] Page turn animation rated smooth (60fps)

### User Experience Metrics
- [ ] 80%+ of parents enable illustrations (opt-out validation)
- [ ] Average session time increases 20%+ with illustrations
- [ ] Zero critical bugs reported in first week
- [ ] Positive feedback from 5+ beta testers

### Business Metrics
- [ ] Average cost per story: $0.25-$0.35
- [ ] Monthly cost predictable and within budget
- [ ] Feature differentiates Taleweaver from competitors

---

## Notes & Decisions Log

### 2026-03-21 - Initial Planning
- **Decision:** Use Story Spine beats for scene count (8 custom, 5 historical)
  - Rationale: Aligns with existing narrative structure
- **Decision:** Art style selector as separate optional step
  - Rationale: Keeps main flow simple, emphasizes optional nature
- **Decision:** Opt-out (enabled by default)
  - Rationale: Showcase premium feature, easy to skip
- **Decision:** 4:3 aspect ratio
  - Rationale: Traditional storybook feel, works well on all devices
- **Decision:** Page turn transitions
  - Rationale: Mimics physical book experience, magical feel
- **Decision:** Provider pattern for image generation
  - Rationale: Flexibility to swap providers, future-proof architecture
- **Decision:** Decoupled generation/playback
  - Rationale: Enables future regeneration support, cleaner architecture
- **Decision:** Scene metadata in JSON column
  - Rationale: Flexible structure, no schema changes for new fields

---

## Progress Tracking

**Last Updated:** 2026-03-21  
**Current Stage:** Planning Complete  
**Next Steps:** Stage 1 - Database Schema & Models

**Overall Progress:**
- [ ] Stage 1: Database Schema & Models
- [ ] Stage 2: Art Style System & API
- [ ] Stage 3: Scene Analyzer Node
- [ ] Stage 4: Illustration Provider
- [ ] Stage 5: Pipeline Integration
- [ ] Stage 6: Frontend - Art Style Selector
- [ ] Stage 7: Frontend - Illustrated Player
- [ ] Stage 8: Testing & Polish

**Estimated Completion:** TBD (60-76 hours over 1.5-2 weeks)
