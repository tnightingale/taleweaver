# Story Spring

Personalized audio stories for kids, powered by AI.

Parents enter their child's name, age, and interests. Story Spring writes a story with their kid as the protagonist, voices it with multiple characters, and delivers a downloadable MP3 with a **permanent shareable link** - all in about 2-3 minutes.

**Two modes:**
- **Custom Story** - pick a genre, describe your idea, and the kid is the hero
- **Historical Adventure** - pick from 20 real historical events (including Indian history); the kid is an invisible time-traveling observer

**Key features:**
- ✅ **AI-Generated Illustrations** - Optional synchronized illustrations with page turn animations (NEW!)
- ✅ Multi-voice narration with 4 distinct voices
- ✅ Background music mood matching
- ✅ Age-adaptive storytelling (3-12 years)
- ✅ **Permanent permalinks** - Share stories with compact URLs (e.g., `/s/a7x9k2mn`)
- ✅ Downloadable MP3 files
- ✅ Built on storytelling science (Story Spine structure, age-calibrated language)
- ✅ 7 curated art style presets (watercolor, classic storybook, modern flat, etc.)

## Deployment

### Production Deployment with Once

Story Spring is fully compatible with [Basecamp Once](https://github.com/basecamp/once) for easy self-hosting with automatic SSL, backups, and updates.

```bash
# On your server
curl https://get.once.com | sh

# When prompted, enter:
ghcr.io/yourusername/taleweaver:latest
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete deployment instructions.

## Quick Start (Local Development)

### Using an AI coding agent (recommended)

If you have an AI coding agent (Claude Code, Cursor, Windsurf, etc.), give it this prompt:

> Run `./setup.sh` in the terminal and follow the interactive prompts. It will ask me which LLM provider I want and for my API keys. After setup completes, run `./start.sh` to start the app.

That's it. The setup script handles everything.
![Screenshot 2026-03-04 at 10 40 20 AM](https://github.com/user-attachments/assets/fd200c58-0481-430b-b0ad-d9f8c95fc77d)

![Screenshot 2026-03-12 at 9 39 04 AM](https://github.com/user-attachments/assets/7e79c78c-d31c-49c6-b001-4ba8a578f1f1)

![Screenshot 2026-03-12 at 9 39 34 AM](https://github.com/user-attachments/assets/cb300d2e-b611-4a3f-8f16-2e01b729a5fa)



### Manual setup

**Prerequisites:** Python 3.9+, Node.js 18+, npm, ffmpeg

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/audio-story-creator.git
cd audio-story-creator

# 2. Run the interactive setup
./setup.sh
```

The setup script will:
1. Check that prerequisites are installed
2. Ask you to choose an LLM provider (Groq, OpenAI, or Anthropic)
3. Ask for your API keys
4. Install all dependencies
5. Ask if you want local-only or WiFi access
6. Generate a `start.sh` script

Then start the app:

```bash
./start.sh
```

Open http://localhost:5173 (or your LAN IP if you chose WiFi access).

## Supported LLM Providers

| Provider | Model | Cost | Notes |
|----------|-------|------|-------|
| **Groq** | Llama 3.3 70B | Free tier available | Fast inference, good quality. [Get key](https://console.groq.com/keys) |
| **OpenAI** | GPT-4o | Paid | High quality stories. [Get key](https://platform.openai.com/api-keys) |
| **Anthropic** | Claude Sonnet 4.5 | Paid | High quality stories. [Get key](https://console.anthropic.com/settings/keys) |

**ElevenLabs** is required for text-to-speech (all providers). Free tier gives ~10 minutes of audio per month. [Get key](https://elevenlabs.io/app/settings/api-keys)

## WiFi Access (phones and tablets)

During setup, choose option 2 ("Local WiFi") to make Story Spring accessible from any device on your network. The setup script auto-detects your local IP and configures everything.

Other devices can then open `http://<your-ip>:5173` in their browser.

## How It Works

```
[Parent Input] → [Story Writer] → [Script Splitter] → [Voice Synthesizer] → [Audio Stitcher] → [MP3]
                    (LLM)          (parse dialogue)     (ElevenLabs TTS)      (pydub + music)
```

1. **Story Writer** - LLM generates an age-appropriate story using storytelling science prompts
2. **Script Splitter** - parses the story into narrator/character segments, assigns voice types
3. **Voice Synthesizer** - ElevenLabs generates audio for each segment with different voices
4. **Audio Stitcher** - concatenates segments, adds pauses, mixes in mood-based background music

Jobs are async. The frontend polls for progress while the pipeline runs (~30-90 seconds).

## Project Structure

```
audio-story-creator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings (reads .env)
│   │   ├── routes/              # API endpoints
│   │   ├── graph/               # LangGraph pipeline + nodes
│   │   ├── models/              # Pydantic request/response models
│   │   ├── prompts/             # LLM prompt engineering
│   │   └── data/                # Genres, historical events, background music
│   ├── tests/                   # Backend tests (94 tests, 98% coverage)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # 3-screen flow (hero → craft → story)
│   │   ├── components/          # HeroScreen, CraftScreen, StoryScreen
│   │   └── api/client.ts        # API client
│   └── package.json
├── setup.sh                     # Interactive setup script
├── docker-compose.yml           # Docker deployment (optional)
└── README.md
```

## Running Tests

```bash
# Backend (94 tests, 98% coverage)
cd backend
source venv/bin/activate
python -m pytest tests/ -v

# Frontend (47 tests)
cd frontend
npm test
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/genres` | GET | List 7 story genres |
| `/api/historical-events` | GET | List 20 curated historical events |
| `/api/story/custom` | POST | Create a custom story |
| `/api/story/historical` | POST | Create a historical adventure |
| `/api/story/status/{job_id}` | GET | Poll job progress |
| `/api/story/audio/{job_id}` | GET | Download completed audio |

## Docker Deployment

```bash
# Make sure backend/.env exists (run setup.sh first)
docker compose up --build
```

Access at http://localhost (port 80).

## Configuration

All config lives in `backend/.env`. You can re-run `./setup.sh` at any time to reconfigure.

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | `groq`, `openai`, or `anthropic` |
| `GROQ_API_KEY` | Groq API key (if using Groq) |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI) |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Anthropic) |
| `ELEVENLABS_API_KEY` | ElevenLabs API key (required) |
| `NARRATOR_VOICE_ID` | ElevenLabs voice ID for narrator (default: Rachel) |
| `CHARACTER_MALE_VOICE_ID` | Voice ID for male characters (default: Antoni) |
| `CHARACTER_FEMALE_VOICE_ID` | Voice ID for female characters (default: Bella) |
| `CHARACTER_CHILD_VOICE_ID` | Voice ID for child characters (default: Jessie) |

Voice IDs come pre-configured with good defaults from the ElevenLabs voice library. You only need to change them if you want different voices.

### Customizing voices

1. Go to the [ElevenLabs Voice Library](https://elevenlabs.io/voice-library)
2. Browse or search for a voice you like, click on it
3. Click **Use Voice** to add it to your account
4. Go to [Your Voices](https://elevenlabs.io/app/voice-lab) (VoiceLab)
5. Click the voice, then copy the **Voice ID** from the bottom of the panel
6. Paste it into `backend/.env` for the relevant role (narrator, male, female, or child)

## Illustrations Feature (Optional)

Story Spring can generate AI-illustrated storybooks synchronized with audio playback!

**How it works:**
1. During story creation, choose from 7 curated art styles or write your own
2. AI generates 5-8 illustrations (one per Story Spine beat)
3. Illustrations display with 3D page turn animations as the story plays
4. Click scene markers to jump to different chapters
5. View illustrated transcript as a static storybook

**Art Styles:**
- Watercolor Dream, Classic Storybook, Modern Flat
- Whimsical Ink, Digital Fantasy, Vintage Fairy Tale
- Custom (write your own style prompt)

**Character Consistency:**
- Uses image-to-image technique to maintain character appearance
- First scene establishes character, subsequent scenes reference it

**Cost:** ~$0.30/story (Google Gemini 3.1 Flash Image)  
**Generation Time:** +25-40 seconds (runs parallel with voice synthesis)

**Setup:**
```bash
# Get Google AI API key at https://aistudio.google.com/app/apikey
ILLUSTRATION_PROVIDER=nanobanana2
GOOGLE_API_KEY=your-google-api-key
```

Set `ILLUSTRATION_PROVIDER=none` or leave `GOOGLE_API_KEY` blank to disable.

## Tech Stack

- **Backend:** Python, FastAPI, LangGraph, ElevenLabs TTS, pydub
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS 4, Framer Motion
- **LLM:** Groq (Llama 3.3) / OpenAI (GPT-4o) / Anthropic (Claude Sonnet 4.5)
- **Image Generation:** Google Gemini 3.1 Flash Image (NanoBanana 2) - optional

## License

[MIT](LICENSE)
