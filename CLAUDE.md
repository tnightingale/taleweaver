# Audio Story Creator for Kids — Taleweaver

> **For developers/agents:** See [DEVELOPMENT.md](./DEVELOPMENT.md) for complete development standards, workflows, and processes. Follow those guidelines for all development work.

## What This Is

A web app where parents create personalized audio stories for their kids. Two modes:
1. **Custom Story** — parent picks a genre + writes a short description. The kid is the protagonist.
2. **Historical Adventure** — parent picks from 20 curated historical events (including Indian history). The kid is a silent time-traveling observer (preserves historical accuracy).

Stories are age-adaptive (3-12 years), use multi-voice narration (narrator + character voices), include mood-based background music, and download as MP3.

## Tech Stack

- **Backend**: Python 3.9+, FastAPI, LangGraph, huey (SQLite-backed background jobs), ElevenLabs TTS
- **Frontend**: React 19, Vite, TypeScript, Tailwind CSS 4, framer-motion
- **LLM**: Claude Haiku (default), also supports Groq and OpenAI (configurable via `LLM_PROVIDER` env var)
- **TTS**: ElevenLabs with 4 pre-configured voices (narrator [Rachel/female], male, female, child)
- **Audio processing**: pydub (requires ffmpeg) — stitches voice segments + mood-based background music
- **Fonts**: Google Fonts — Cinzel (display headings) + Inter (body text)

## Project Structure

```
taleweaver/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, permalink routes, library routes
│   │   ├── db/              # SQLAlchemy models, CRUD operations
│   │   ├── graph/           # LangGraph pipeline (story generation)
│   │   ├── jobs/            # huey background tasks (story generation worker)
│   │   ├── routes/          # API routes (config, story)
│   │   ├── models/          # Pydantic models (requests, responses)
│   │   ├── data/            # Genres, historical events, music
│   │   └── prompts/         # Story generation prompts
│   │   ├── services/        # External providers (illustration/Gemini)
│   │   ├── utils/           # Storage helpers (illustrations, temp audio)
│   └── tests/               # 203 pytest tests
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Router setup
│   │   ├── routes/          # Route components (Hero, Craft, Story, Library)
│   │   ├── components/      # UI components
│   │   └── api/client.ts    # API calls
│   └── package.json
├── docs/plans/              # Implementation plans & stage tracking
├── scripts/                 # Backup/restore scripts
├── Dockerfile               # Production build
└── docker-compose.dev.yml   # Dev/test environments
```

## Quick Start

**Production-like (recommended):**
```bash
docker compose up app  # http://localhost
```

**Local development:**
```bash
# Backend: cd backend && uvicorn app.main:app --reload
# Frontend: cd frontend && npm run dev
```

**Run tests:**
```bash
COMPOSE_PROFILES=test docker compose -f docker-compose.dev.yml run --rm backend-test
```

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/genres` | GET | List story genres |
| `/api/historical-events` | GET | List curated historical events (20) |
| `/api/story/custom` | POST | Create custom story job (accepts mood + length) |
| `/api/story/historical` | POST | Create historical story job (accepts mood + length) |
| `/api/story/status/{job_id}` | GET | Poll job progress (now includes short_id) |
| `/api/story/audio/{job_id}` | GET | Download completed audio (temporary, for active jobs) |
| `/api/stories` | GET | List all stories with filters/pagination (library) |
| `/api/stories/{short_id}` | DELETE | Delete story (DB record + audio file) |
| `/api/stories/{short_id}` | PATCH | Update story title |
| `/s/{short_id}` | GET | Get story metadata by permalink (permanent) |
| `/s/{short_id}/audio` | GET | Stream audio by permalink (permanent) |

## LangGraph Pipeline

```
[Input] → [Story Writer] → [Scene Analyzer] → [Script Splitter] → ┬─[Voice Synthesizer]──────┬→ [Audio Stitcher] → [Timestamp Calculator] → [Output]
                                                                    └─[Illustration Generator]─┘
```

- Jobs run in a **huey background worker process** (not in gunicorn) — POST returns `job_id`, frontend polls `/status/{job_id}` every 2 seconds
- Job queue is persisted to SQLite (`/storage/huey.db`) — survives server crashes and restarts
- Job progress is tracked in `job_state` table — shared between huey worker and gunicorn API
- Stories are permanent with compact permalinks (e.g., `/s/a7x9k2mn`)
- Typical generation time: 20-90 seconds depending on story length
- Audio stitcher mixes mood-based background music under narration
- Failed jobs can be retried via `/api/story/retry/{job_id}` — re-enqueues in huey
- Voice synthesis and illustration generation run **in parallel** (LangGraph fan-out)
- Illustration generator uses Google Gemini with 60s timeout per image and auto-retry

## Storage Structure

Stories are permanently stored:

```
/storage/
├── taleweaver.db              # SQLite database (WAL mode for multi-process access)
├── huey.db                    # huey job queue (SQLite-backed, separate from app DB)
├── stories/
│   ├── {uuid-1}/
│   │   ├── audio.mp3          # Generated MP3 file
│   │   ├── scene_0.png        # Illustration images (if art_style selected)
│   │   ├── scene_1.png
│   │   └── ...
│   └── ...
├── temp/                       # Temporary audio segments (for resume capability)
└── music/                      # Background music files
```

**Database schema:**
- Story metadata (title, kid name/age, genre/event, mood, length)
- Compact short_id (8 chars, a-z0-9) for permalinks
- Transcript and duration
- File path reference to audio MP3
- Art style, illustration data (scene_data JSON with image URLs)
- Creation timestamp

**Permalinks:**
- Format: `/s/{short_id}` (e.g., `/s/a7x9k2mn`)
- Permanent, shareable URLs
- No authentication required

## Key Design Decisions

- **Kid as silent observer** in historical stories to preserve accuracy
- **Age-adaptive content**: ages 3-5 get simple/short stories (~200-300 words), 6-8 moderate (~400-600), 9-12 rich/complex (~700-1000)
- **Multi-voice narration**: script splitter assigns voice types (narrator/male/female/child) based on character names
- **Female narrator voice** (Rachel) as the default narrator
- **Mood and length controls**: exciting/heartwarming/funny/mysterious moods; short/medium/long lengths
- **Background music mixing**: audio stitcher layers mood-matched music under the narrated story
- **Storytelling-science prompts**: Story Spine structure, age-calibrated directives, audio-specific storytelling rules
- **Job-based polling** instead of streaming — generation takes too long for a single request
- **huey background workers** — story generation runs in a separate process from the API, surviving crashes and restarts
- **SQLite WAL mode** — enables concurrent access from gunicorn (reads) + huey worker (writes)
- **Audio writes directly to disk** — audio_stitcher writes MP3 to filesystem, not through memory
- **3-screen immersive UI**: dark fantasy theme with glassmorphism, particle effects, and glow effects (replaces v1 6-step wizard)
- **CORS allows all origins** for LAN access

## Environment Variables

```
LLM_PROVIDER=anthropic          # anthropic, groq, or openai
ANTHROPIC_API_KEY=               # Required if using anthropic
GROQ_API_KEY=                    # Required if using groq
OPENAI_API_KEY=                  # Required if using openai
ELEVENLABS_API_KEY=              # Always required for TTS
NARRATOR_VOICE_ID=               # ElevenLabs voice IDs (Rachel/female for narrator)
CHARACTER_MALE_VOICE_ID=
CHARACTER_FEMALE_VOICE_ID=
CHARACTER_CHILD_VOICE_ID=
GOOGLE_API_KEY=                  # Required for illustration generation (Gemini)
GUNICORN_WORKERS=4               # API workers (default 4, API-only since huey handles generation)
HUEY_WORKERS=1                   # Background story generation workers (default 1)
```

## Future Ideas

- User accounts / authentication
- Edge TTS (free alternative to ElevenLabs)
- QR code sharing
- Content moderation
- Rate limiting
- PostgreSQL migration (enables oban-py for enterprise job orchestration)
