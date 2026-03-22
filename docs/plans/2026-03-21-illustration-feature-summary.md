# Story Illustrations Feature - Summary

**Quick Reference Guide**  
**Created:** 2026-03-21

---

## 🎯 What We're Building

AI-generated illustrations that display synchronized with story audio playback. Like an animated storybook that turns pages as the narrator speaks.

**Key Features:**
- 5-8 illustrations per story (following Story Spine narrative beats)
- 7 curated art style presets (watercolor, classic storybook, modern flat, etc.)
- Image-to-image consistency (characters look the same across all scenes)
- Page turn transitions (like flipping a physical book)
- Scene markers on seek bar for chapter navigation
- Optional feature (user can skip illustration generation)

---

## 📊 Quick Stats

| Metric | Value |
|--------|-------|
| **Cost per story** | ~$0.30 (8 images × $0.045) |
| **Generation time overhead** | +25-40 seconds |
| **Scene count** | 8 (custom) / 5 (historical) |
| **Aspect ratio** | 4:3 (traditional storybook) |
| **Image provider** | NanoBanana 2 (Google Gemini 3.1 Flash Image) |
| **Total estimated work** | 60-76 hours (1.5-2 weeks) |

---

## 🏗️ Architecture Overview

### Core Design Principles

1. **Decoupled** - Image generation and playback are completely independent
2. **Provider Pattern** - Easy to swap NanoBanana 2 for DALL-E or Flux
3. **Progressive Enhancement** - Stories work perfectly without illustrations
4. **Future-Ready** - Architecture supports regeneration and custom providers

### Data Flow

```
User selects art style
    ↓
Story Writer → Scene Analyzer → Script Splitter
                                      ↓
                    ┌─────────────────┴─────────────────┐
                    ↓                                    ↓
            Voice Synthesizer (TTS)          Illustration Generator
                    ↓                                    ↓
                    └─────────────────┬─────────────────┘
                                      ↓
                              Audio Stitcher
                                      ↓
                          Timestamp Calculator
                                      ↓
                    Save to DB (with scene_data JSON)
                                      ↓
                          Frontend renders player
```

### New Database Schema

```sql
ALTER TABLE stories ADD COLUMN art_style VARCHAR;
ALTER TABLE stories ADD COLUMN has_illustrations BOOLEAN DEFAULT FALSE;
ALTER TABLE stories ADD COLUMN scene_data JSON;
```

**scene_data structure:**
```json
{
  "scenes": [
    {
      "beat_index": 0,
      "beat_name": "Once upon a time",
      "text_excerpt": "Mia stood at the edge...",
      "illustration_prompt": "7-year-old girl with curly brown hair...",
      "timestamp_start": 0.0,
      "timestamp_end": 28.5,
      "image_url": "/storage/stories/{id}/scene_0.png",
      "generation_metadata": {...}
    }
  ],
  "art_style_prompt": "soft watercolor painting...",
  "character_description": "7-year-old girl, curly brown hair..."
}
```

---

## 📦 8 Implementation Stages

### Stage 1: Database Schema & Models (4-6 hours)
- Extend database with illustration columns
- Update TypedDict definitions (StoryState, Scene)
- Update API request/response models
- **Tests:** 5

### Stage 2: Art Style System & API (6-8 hours)
- Create 7 curated art style presets
- Build GET /api/art-styles endpoint
- **Tests:** 4

### Stage 3: Scene Analyzer Node (8-10 hours)
- LLM-powered Story Spine beat detection
- Extract character description for consistency
- Generate illustration prompts per scene
- **Tests:** 6

### Stage 4: Illustration Provider (10-12 hours)
- Abstract provider pattern (base class + factory)
- Implement NanoBanana 2 provider
- Image storage utilities
- Text-to-image (first scene) + image-to-image (consistency)
- **Tests:** 8

### Stage 5: Pipeline Integration (8-10 hours)
- Add scene_analyzer, illustration_generator, timestamp_calculator nodes
- Parallel execution: voice synthesis || illustration generation
- Update job status tracking
- Persist scene_data to database
- **Tests:** 6

### Stage 6: Frontend - Art Style Selector (6-8 hours)
- Art style selection UI (grid of preset cards)
- Custom prompt textarea option
- "Skip Illustrations" choice
- Integration into story creation flow

### Stage 7: Frontend - Illustrated Player (10-12 hours)
- Display illustrations synchronized with audio
- Page turn animation (framer-motion 3D flip)
- Scene markers on seek bar (clickable chapter navigation)
- Illustrated transcript view
- Responsive design (mobile/tablet/desktop)

### Stage 8: Testing & Polish (8-10 hours)
- End-to-end integration tests
- Error handling (graceful degradation if API fails)
- Performance optimization
- Manual testing on 3+ devices
- Documentation updates
- Cost monitoring

---

## 🎨 Art Style Presets

1. **Watercolor Dream** - Soft watercolor painting, gentle brush strokes
2. **Classic Storybook** - Traditional gouache, warm colors, detailed linework
3. **Modern Flat** - Bold colors, geometric shapes, Scandinavian minimalism
4. **Whimsical Ink** - Pen and ink with watercolor washes, playful style
5. **Digital Fantasy** - Vibrant fantasy art, detailed backgrounds, magical
6. **Vintage Fairy Tale** - 1960s nostalgic storybook, muted tones
7. **Custom** - User provides their own art style prompt

---

## 🔧 Technical Implementation Details

### Consistency Technique

**Problem:** How to keep the protagonist looking the same across 8 images?

**Solution:** Image-to-image chain
1. First scene: Pure text-to-image with full character + setting description
2. Scenes 2-8: Image-to-image mode using previous illustration as reference
   - NanoBanana 2's `imageUrls` parameter accepts reference images
   - Prompt focuses on new action/setting while maintaining character

### Parallel Execution

Voice synthesis and illustration generation run **simultaneously** to minimize time overhead:

```python
# LangGraph handles this automatically when both nodes depend on same parent
graph.add_edge("script_splitter", "voice_synthesizer")
graph.add_edge("script_splitter", "illustration_generator")

# Both complete before audio stitcher starts
graph.add_edge("voice_synthesizer", "audio_stitcher")
graph.add_edge("illustration_generator", "audio_stitcher")
```

### Timestamp Calculation

Since scenes are detected **before** audio is generated, timestamps are estimated:

1. Scene analyzer counts words per beat
2. After audio generation (when we know total duration):
   - Distribute time proportionally: `scene_duration = (word_count / total_words) × total_duration`
   - Calculate timestamp_start and timestamp_end for each scene

### Graceful Degradation

If illustration generation fails:
- Pipeline continues without images
- `has_illustrations = false` in database
- Error logged but story generation completes
- Frontend falls back to standard audio player

---

## 🚀 Getting Started

### Prerequisites

```bash
# Get NanoBanana 2 API key (or compatible provider)
# https://api.nanobananaapi.ai/

# Add to .env
ILLUSTRATION_PROVIDER=nanobanana2
NANOBANANA_API_KEY=your-api-key-here
ILLUSTRATION_ASPECT_RATIO=4:3
ILLUSTRATION_RESOLUTION=2K
```

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/illustrations-schema

# Run tests
docker compose run --rm backend-test

# Start dev servers
docker compose up app  # Backend + Frontend

# Manual testing
curl http://localhost:8000/api/art-styles
```

---

## 📈 Success Criteria

### Must Have (MVP)
- ✅ Stories generate successfully with illustrations
- ✅ Illustrations sync with audio playback
- ✅ Page turn animation smooth (60fps)
- ✅ All 29 tests passing
- ✅ No pipeline crashes due to illustration failures
- ✅ Generation time overhead <40 seconds
- ✅ Cost per story ~$0.30

### Nice to Have (Future)
- Preview first illustration while others generate
- Regenerate illustrations without re-generating audio
- Alternative providers (DALL-E, Flux, Stable Diffusion)
- Printable storybook PDF export

---

## 🎬 User Experience Flow

### Story Creation (with illustrations)

1. Parent configures story (kid name/age, genre, mood, length)
2. **NEW STEP:** Choose illustration style
   - Grid of 7 preset cards with previews
   - "Skip Illustrations" option
   - Custom prompt textarea
3. Story generates (shows progress):
   - "Writing the story..." (LLM)
   - "Analyzing story structure..." (scene detection)
   - "Preparing character voices..." (script splitting)
   - "Generating audio..." (TTS)
   - **NEW:** "Creating illustrations..." (parallel with TTS)
   - "Mixing the final track..." (audio stitching)
4. Story complete

### Playback (illustrated mode)

1. Large illustration displayed (4:3 aspect ratio)
2. Scene indicator: "Chapter 3 of 8: Because of that..."
3. Audio controls below illustration
4. Seek bar with 8 scene markers (clickable)
5. As audio plays, pages turn automatically at scene boundaries
6. Parent can click scene markers to jump chapters
7. Transcript view shows illustrated storybook format

---

## ⚠️ Key Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| NanoBanana API downtime | High | Retry logic, graceful degradation, continue without images |
| Character consistency issues | Medium | Image-to-image mode, character description in every prompt |
| Generation time too long | Medium | Parallel execution, 90s timeout, background jobs (future) |
| Cost overruns | Low | Cost monitoring, alerts, $0.30/story is acceptable |

---

## 📝 Next Steps

1. Review this plan with stakeholders
2. Create `feature/illustrations-schema` branch
3. Start Stage 1: Database Schema & Models
4. Follow the detailed plan in `2026-03-21-illustration-feature-plan.md`

---

## 📚 References

- **Detailed Plan:** `2026-03-21-illustration-feature-plan.md`
- **NanoBanana 2 API Docs:** https://docs.nanobananaapi.ai/
- **Provider Info:** https://evolink.ai/blog/how-to-use-nano-banana-2-api
- **Existing Features:** `2026-03-21-library-feature-stages.md` (for reference)
