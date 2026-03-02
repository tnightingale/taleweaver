# Taleweaver v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform StoryForge into Taleweaver — an immersive fantasy-themed audio story creator with science-backed story prompts, a 3-screen narrative flow, background music, and a female narrator voice.

**Architecture:** The frontend gets a complete visual overhaul (dark fantasy theme, particles, animations, 3-screen flow with new inputs). The backend gets rewritten prompts encoding storytelling science, a new background music mixing step in the audio pipeline, updated request models for mood/length, expanded historical events, and a narrator voice change.

**Tech Stack:** React 19, TypeScript, Tailwind CSS 4, Vite, FastAPI, LangGraph, ElevenLabs TTS, pydub

---

### Task 1: Rename StoryForge to Taleweaver across the codebase

**Files:**
- Modify: `frontend/src/App.tsx:87-91` (header text)
- Modify: `frontend/index.html:7` (page title)
- Modify: `backend/app/main.py:6` (FastAPI title)
- Modify: `CLAUDE.md:1` (project title)

**Step 1: Update frontend App.tsx header**

In `frontend/src/App.tsx`, change:
```tsx
<h1 className="text-4xl font-extrabold text-purple-800">
  StoryForge
</h1>
<p className="text-gray-500 mt-1">Magical audio stories for kids</p>
```
to:
```tsx
<h1 className="text-4xl font-extrabold text-purple-800">
  Taleweaver
</h1>
<p className="text-gray-500 mt-1">Magical audio stories for kids</p>
```

**Step 2: Update page title**

In `frontend/index.html`, change `<title>frontend</title>` to `<title>Taleweaver</title>`.

**Step 3: Update backend app title**

In `backend/app/main.py`, change:
```python
app = FastAPI(title="Audio Story Creator")
```
to:
```python
app = FastAPI(title="Taleweaver")
```

**Step 4: Update CLAUDE.md title**

Change the first line of `CLAUDE.md` from:
```
# Audio Story Creator for Kids — StoryForge
```
to:
```
# Audio Story Creator for Kids — Taleweaver
```

**Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/index.html backend/app/main.py CLAUDE.md
git commit -m "chore: rename StoryForge to Taleweaver"
```

---

### Task 2: Add mood and length fields to backend request models

**Files:**
- Modify: `backend/app/models/requests.py`
- Modify: `backend/app/graph/state.py`
- Modify: `backend/app/routes/story.py:56-80` (custom route state init)
- Test: `backend/tests/test_models.py`

**Step 1: Write failing tests for new request fields**

Add to `backend/tests/test_models.py`:
```python
def test_custom_story_request_with_mood_and_length():
    req = CustomStoryRequest(
        kid=KidProfile(name="Ava", age=7),
        genre="adventure",
        description="A quest for a golden feather",
        mood="exciting",
        length="medium",
    )
    assert req.mood == "exciting"
    assert req.length == "medium"


def test_custom_story_request_mood_defaults_to_none():
    req = CustomStoryRequest(
        kid=KidProfile(name="Ava", age=7),
        genre="adventure",
        description="A quest",
    )
    assert req.mood is None
    assert req.length is None
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_models.py::test_custom_story_request_with_mood_and_length -v`
Expected: FAIL — `mood` field not accepted

**Step 3: Add mood and length to CustomStoryRequest**

In `backend/app/models/requests.py`, change `CustomStoryRequest`:
```python
class CustomStoryRequest(BaseModel):
    kid: KidProfile
    genre: str
    description: str
    mood: Optional[str] = None      # exciting, heartwarming, funny, mysterious
    length: Optional[str] = None    # short, medium, long
```

**Step 4: Add mood and length to StoryState**

In `backend/app/graph/state.py`, add to `StoryState`:
```python
class StoryState(TypedDict):
    # Input
    kid_name: str
    kid_age: int
    kid_details: str
    story_type: str
    genre: Optional[str]
    description: Optional[str]
    event_id: Optional[str]
    event_data: Optional[dict]
    mood: Optional[str]
    length: Optional[str]

    # Pipeline outputs
    story_text: str
    title: str
    segments: list[Segment]
    audio_segments: list[bytes]
    final_audio: bytes
    duration_seconds: int
    error: Optional[str]
```

**Step 5: Pass mood and length through story routes**

In `backend/app/routes/story.py`, in `create_custom_story`, add to the state dict:
```python
"mood": request.mood,
"length": request.length,
```

In `create_historical_story`, add:
```python
"mood": None,
"length": None,
```

**Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add backend/app/models/requests.py backend/app/graph/state.py backend/app/routes/story.py backend/tests/test_models.py
git commit -m "feat: add mood and length fields to story request models"
```

---

### Task 3: Rewrite custom story prompts with storytelling science

**Files:**
- Modify: `backend/app/prompts/custom_story.py` (complete rewrite)
- Test: `backend/tests/test_prompts.py`

**Step 1: Write failing tests for new prompt features**

Add to `backend/tests/test_prompts.py`:
```python
def test_custom_prompt_includes_story_spine():
    prompt = build_custom_story_prompt(
        name="Ava", age=7, details="", genre="adventure",
        description="A quest", mood=None, length=None,
    )
    assert "Once upon a time" in prompt
    assert "Until one day" in prompt
    assert "Because of that" in prompt
    assert "Until finally" in prompt


def test_custom_prompt_includes_emotional_arc():
    prompt = build_custom_story_prompt(
        name="Ava", age=7, details="", genre="adventure",
        description="A quest", mood=None, length=None,
    )
    assert "fail" in prompt.lower() or "struggle" in prompt.lower()
    assert "all is lost" in prompt.lower() or "darkest moment" in prompt.lower()


def test_custom_prompt_includes_audio_directives():
    prompt = build_custom_story_prompt(
        name="Ava", age=7, details="", genre="adventure",
        description="A quest", mood=None, length=None,
    )
    assert "hook" in prompt.lower() or "first paragraph" in prompt.lower()
    assert "sentence length" in prompt.lower() or "pacing" in prompt.lower()


def test_custom_prompt_mood_exciting():
    prompt = build_custom_story_prompt(
        name="Ava", age=7, details="", genre="adventure",
        description="A quest", mood="exciting", length=None,
    )
    assert "exciting" in prompt.lower() or "action" in prompt.lower()


def test_custom_prompt_length_short():
    prompt = build_custom_story_prompt(
        name="Ava", age=5, details="", genre="bedtime",
        description="A sleepy bear", mood=None, length="short",
    )
    assert "500" in prompt or "short" in prompt.lower()
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_prompts.py::test_custom_prompt_includes_story_spine -v`
Expected: FAIL — `build_custom_story_prompt` doesn't accept mood/length params

**Step 3: Rewrite custom_story.py**

Replace the entire contents of `backend/app/prompts/custom_story.py` with:

```python
from typing import Optional


def _word_count_guide(age: int, length: Optional[str]) -> str:
    """Return word count and duration target based on age and requested length."""
    # Base ranges by age
    ranges = {
        "young": {"short": (300, 400, 3, 4), "medium": (500, 700, 5, 7), "long": (700, 900, 7, 9)},
        "mid": {"short": (500, 700, 5, 7), "medium": (900, 1200, 9, 12), "long": (1200, 1500, 12, 15)},
        "older": {"short": (700, 1000, 7, 10), "medium": (1200, 1800, 12, 18), "long": (1800, 2500, 18, 25)},
    }
    age_key = "young" if age <= 5 else "mid" if age <= 8 else "older"
    length_key = length if length in ("short", "medium", "long") else "medium"
    lo, hi, min_dur, max_dur = ranges[age_key][length_key]
    return f"The story should be {lo}-{hi} words ({min_dur}-{max_dur} minutes when read aloud)."


def _age_directives(age: int) -> str:
    if age <= 5:
        return """AGE GROUP 3-5 — PRESCHOOL LISTENER:
- Use simple words and short sentences. Vocabulary a 4-year-old would understand.
- Single protagonist, single problem, Rule of Three structure (try once, try twice, succeed on third).
- Include a repetitive refrain or catchphrase the listener can anticipate and "say along."
- Complete, happy resolution. No ambiguity. The problem is fully solved.
- Sensory language: describe sounds, textures, smells vividly.
- Keep the emotional stakes gentle and concrete (e.g., "the bunny can't find home").
- Adults can be present but the child/creature protagonist solves the problem."""
    elif age <= 8:
        return """AGE GROUP 6-8 — EARLY READER:
- Use moderate vocabulary appropriate for early readers. Introduce 2-3 interesting new words naturally.
- Make the protagonist 1-2 years older than the target child (aspirational).
- Two parallel problems: one external (the quest/adventure) and one internal (an emotion or character flaw).
- Include 2-3 try/fail cycles — the protagonist must struggle before succeeding.
- Include a friend or ally character — the "buddy" dynamic.
- Humor: physical comedy, silly situations, light wordplay.
- Moral is earned through the story, NEVER stated explicitly. No "and the lesson is..." endings.
- Stakes should feel real to a child: friendship, fairness, belonging, not being believed."""
    else:
        return """AGE GROUP 9-12 — INDEPENDENT LISTENER:
- Use rich, detailed language with complex sentence structures. Don't shy from challenging vocabulary.
- Include an ensemble of 2-3 characters with distinct personalities and voices.
- Main plot + a subplot that mirrors or contrasts the main theme.
- Protagonist makes real mistakes with real consequences. No perfect heroes.
- Moral complexity: not everything is clearly right or wrong. Trust the listener to draw conclusions.
- DO NOT moralize or spell out the lesson — this age group rejects being talked down to.
- Stakes can be significant: loyalty, identity, injustice, real danger (age-appropriate).
- A cliffhanger-style or open-reflection ending is acceptable."""


def _mood_directives(mood: Optional[str]) -> str:
    moods = {
        "exciting": """MOOD — EXCITING:
- Fast pacing with short, punchy sentences during action scenes.
- Physical action: running, climbing, dodging, racing against time.
- Higher stakes and more urgent problems.
- Frequent scene changes to maintain momentum.""",
        "heartwarming": """MOOD — HEARTWARMING:
- Focus on relationships: friendship, family bonds, acts of kindness.
- Include quiet, tender moments between characters.
- Emotional connection is the core of the story.
- The resolution should feel earned through empathy and understanding.""",
        "funny": """MOOD — FUNNY:
- Absurdist logic: "what if" scenarios taken to ridiculous extremes.
- Physical comedy and silly situations for younger kids.
- Wordplay, puns, and ironic situations for older kids.
- Characters can be lovably ridiculous.""",
        "mysterious": """MOOD — MYSTERIOUS:
- Rich sensory descriptions: shadows, echoes, strange silences.
- Unanswered questions that pull the listener forward.
- Atmospheric tension — something feels slightly off.
- Delayed reveals: describe sounds before showing what caused them.""",
    }
    if mood and mood in moods:
        return moods[mood]
    return ""


def build_custom_story_prompt(
    name: str, age: int, details: str, genre: str, description: str,
    mood: Optional[str] = None, length: Optional[str] = None,
) -> str:
    age_guide = _age_directives(age)
    word_count = _word_count_guide(age, length)
    mood_guide = _mood_directives(mood)

    return f"""You are a world-class children's audio storyteller. Your stories captivate, move, and stay with listeners.

STORY REQUEST:
- Protagonist: a child named {name}, age {age}
- Genre: {genre}
- Concept: {description}

CHILD'S DETAILS (weave naturally into the story if provided):
{details if details else "No additional details."}

---

STEP 1 — PLAN THE STORY SKELETON (do this internally before writing):

Fill out this structure in your mind before drafting:
- Once upon a time... [World + character + what's normal]
- Every day... [The protagonist's routine / status quo]
- Until one day... [The inciting incident that disrupts everything]
- Because of that... [First consequence — things change]
- Because of that... [Second consequence — stakes rise]
- Because of that... [Third consequence — approaching the crisis]
- Until finally... [The climax — the protagonist faces the biggest challenge]
- And ever since then... [The new normal — what changed]

Before writing, answer these four questions:
1. Who do I care about and WHY? (Give {name} a specific, concrete desire)
2. What does {name} want? (Not generic "be happy" — something tangible)
3. What's stopping them? (A real obstacle, not easily overcome)
4. What happens if they fail? (Real stakes the listener can feel)

STEP 2 — WRITE THE STORY following these rules:

{age_guide}

{word_count}

{mood_guide}

AUDIO STORYTELLING RULES (critical — this will be read aloud):
- Hook in the FIRST PARAGRAPH. Start with action, a sound, or an unresolved question. NEVER open with backstory or description.
- Vary sentence length deliberately: short sentences for urgency and action, longer flowing sentences for calm, wonder, or reflection.
- Build sound into the prose: use onomatopoeia ("CRASH", "whispered", "crackled"), sound-first scene openings, and described silence as a dramatic beat.
- Show emotion through ACTION, not narration. Write "her hands went cold" not "she was afraid." Write "he kicked the dirt" not "he was frustrated."
- Include ONE recurring refrain or catchphrase that appears at least 3 times in the story.
- Include ONE moment where the narrator addresses the listener: "And what do you think happened next?" or "Can you guess what was inside?"
- Leave deliberate gaps in visual descriptions — let the listener's imagination fill in details.
- The protagonist must FAIL at least once before succeeding. Effort is more compelling than effortless success.
- Include an "all is lost" moment — the darkest point before the turn. Scale to age group.
- NO deus ex machina. The protagonist solves their own problem through their own action or growth.
- Coincidences can create problems but NEVER solve them.
- Give {name} at least one authentic flaw a child would recognize (impatience, jealousy, fear of embarrassment, wanting to quit).

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
TITLE: [A creative, evocative title]
STORY:
[Your story text. Use dialogue with character names formatted as: CharacterName: "dialogue text"]"""
```

**Step 4: Update existing tests to pass new params**

In `backend/tests/test_prompts.py`, update existing `build_custom_story_prompt` calls to include `mood=None, length=None` parameters.

**Step 5: Run all prompt tests**

Run: `cd backend && python -m pytest tests/test_prompts.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add backend/app/prompts/custom_story.py backend/tests/test_prompts.py
git commit -m "feat: rewrite custom story prompts with storytelling science"
```

---

### Task 4: Rewrite historical story prompts with storytelling science

**Files:**
- Modify: `backend/app/prompts/historical_story.py` (complete rewrite)
- Test: `backend/tests/test_prompts.py`

**Step 1: Write failing tests**

Add to `backend/tests/test_prompts.py`:
```python
def test_historical_prompt_includes_audio_directives():
    event = {"title": "Moon Landing", "figure": "Neil Armstrong", "year": 1969, "key_facts": ["Fact 1"]}
    prompt = build_historical_story_prompt(
        name="Ava", age=7, details="", event_data=event,
        mood=None, length=None,
    )
    assert "hook" in prompt.lower() or "first paragraph" in prompt.lower()
    assert "sentence length" in prompt.lower() or "pacing" in prompt.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_prompts.py::test_historical_prompt_includes_audio_directives -v`
Expected: FAIL

**Step 3: Rewrite historical_story.py**

Replace the entire contents of `backend/app/prompts/historical_story.py`:

```python
from typing import Optional


def _word_count_guide(age: int, length: Optional[str]) -> str:
    ranges = {
        "young": {"short": (300, 400, 3, 4), "medium": (500, 700, 5, 7), "long": (700, 900, 7, 9)},
        "mid": {"short": (500, 700, 5, 7), "medium": (900, 1200, 9, 12), "long": (1200, 1500, 12, 15)},
        "older": {"short": (700, 1000, 7, 10), "medium": (1200, 1800, 12, 18), "long": (1800, 2500, 18, 25)},
    }
    age_key = "young" if age <= 5 else "mid" if age <= 8 else "older"
    length_key = length if length in ("short", "medium", "long") else "medium"
    lo, hi, min_dur, max_dur = ranges[age_key][length_key]
    return f"The story should be {lo}-{hi} words ({min_dur}-{max_dur} minutes when read aloud)."


def _age_directives(age: int) -> str:
    if age <= 5:
        return """AGE GROUP 3-5:
- Use very simple words and short sentences.
- Focus on what the child SEES and HEARS — concrete sensory details.
- Keep the historical context simple. One or two key facts, explained gently.
- The time-travel framing should feel magical and safe.
- Include a repetitive refrain about the time-travel experience."""
    elif age <= 8:
        return """AGE GROUP 6-8:
- Moderate vocabulary. Explain historical terms in kid-friendly language.
- Include the emotional dimension: how the historical figures FELT.
- Let the child observer have an emotional reaction to what they witness.
- 2-3 key historical facts woven naturally into the narrative.
- Include a moment of wonder or awe at witnessing history."""
    else:
        return """AGE GROUP 9-12:
- Rich, detailed language. Don't shy from historical complexity.
- Explore the motivations and conflicts of historical figures.
- Include context: why this event mattered, what was at stake.
- The child observer can reflect on what they're seeing — what it means.
- All key facts must be included accurately.
- Moral complexity is welcome — history is rarely simple."""


def build_historical_story_prompt(
    name: str, age: int, details: str, event_data: dict,
    mood: Optional[str] = None, length: Optional[str] = None,
) -> str:
    age_guide = _age_directives(age)
    word_count = _word_count_guide(age, length)
    facts = "\n".join(f"- {f}" for f in event_data["key_facts"])

    return f"""You are a world-class children's audio storyteller who specializes in historically accurate, vivid time-travel stories.

STORY REQUEST:
- Observer: {name} (age {age}), a child magically transported back in time
- {name} is an INVISIBLE, silent observer. They watch but do NOT change history.

CHILD'S DETAILS:
{details if details else "No additional details."}

HISTORICAL EVENT:
Title: {event_data["title"]}
Historical Figure: {event_data["figure"]}
Year: {event_data["year"]}

KEY FACTS (you MUST include ALL of these accurately):
{facts}

---

STEP 1 — PLAN (do this internally before writing):

Structure the story as a journey:
1. {name} is transported — describe the arrival (sights, sounds, smells of the era)
2. {name} witnesses the buildup — tension rises as events unfold
3. The key moment — the climax of the historical event
4. {name} sees the aftermath — the impact and meaning
5. {name} returns home — changed by what they witnessed

Answer: What makes this event EMOTIONALLY compelling for a child? What will {name} FEEL watching it?

STEP 2 — WRITE THE STORY:

{age_guide}

{word_count}

HISTORICAL ACCURACY RULES:
- You MUST be historically accurate. Do NOT invent events that didn't happen.
- All key facts listed above MUST appear in the story.
- Historical figures must speak and act consistently with the historical record.
- {name} NEVER interacts with, speaks to, or is noticed by historical figures.

AUDIO STORYTELLING RULES:
- Hook in the FIRST PARAGRAPH — start with the moment of time travel. Sights, sounds, disorientation.
- Vary sentence length: short sentences for dramatic moments, longer for awe and wonder.
- Build sound into the prose: the sounds of the era, the voices, the environment.
- Show emotion through action, not narration.
- Include ONE recurring refrain about the time-travel experience (e.g., "and {name} watched, invisible, as history unfolded").
- Include ONE moment addressing the listener: "Imagine standing there..."
- Make the experience VIVID and IMMERSIVE — describe what {name} sees, hears, smells, and feels.

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
TITLE: [A creative, evocative title]
STORY:
[Your story text. Use dialogue with character names formatted as: CharacterName: "dialogue text"]"""
```

**Step 4: Update existing tests to pass mood/length params**

Update all existing `build_historical_story_prompt` calls in tests to include `mood=None, length=None`.

**Step 5: Run all prompt tests**

Run: `cd backend && python -m pytest tests/test_prompts.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add backend/app/prompts/historical_story.py backend/tests/test_prompts.py
git commit -m "feat: rewrite historical story prompts with storytelling science"
```

---

### Task 5: Update story_writer node to pass mood and length to prompts

**Files:**
- Modify: `backend/app/graph/nodes/story_writer.py`
- Test: `backend/tests/test_story_writer.py`

**Step 1: Update story_writer.py**

In `backend/app/graph/nodes/story_writer.py`, update the prompt calls:

```python
async def story_writer(state: StoryState) -> dict:
    llm = get_llm()

    if state["story_type"] == "custom":
        prompt = build_custom_story_prompt(
            name=state["kid_name"],
            age=state["kid_age"],
            details=state["kid_details"],
            genre=state["genre"],
            description=state["description"],
            mood=state.get("mood"),
            length=state.get("length"),
        )
    else:
        prompt = build_historical_story_prompt(
            name=state["kid_name"],
            age=state["kid_age"],
            details=state["kid_details"],
            event_data=state["event_data"],
            mood=state.get("mood"),
            length=state.get("length"),
        )

    response = await llm.ainvoke([
        SystemMessage(content="You are a children's storyteller. Follow the instructions exactly."),
        HumanMessage(content=prompt),
    ])

    text = response.content
    title = ""
    story_text = text

    if "TITLE:" in text and "STORY:" in text:
        parts = text.split("STORY:", 1)
        title_part = parts[0]
        story_text = parts[1].strip()
        title = title_part.replace("TITLE:", "").strip()

    return {"story_text": story_text, "title": title}
```

**Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_story_writer.py -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add backend/app/graph/nodes/story_writer.py
git commit -m "feat: pass mood and length to story prompts in writer node"
```

---

### Task 6: Add background music mixing to audio stitcher

**Files:**
- Create: `backend/app/data/music/` directory (4 royalty-free ambient tracks)
- Modify: `backend/app/graph/nodes/audio_stitcher.py`
- Modify: `backend/app/graph/state.py` (add mood to state if not already)
- Test: `backend/tests/test_audio_stitcher.py`

**Step 1: Source and add background music files**

Create `backend/app/data/music/` directory. Add 4 royalty-free MP3 tracks (~2 min each, loopable):
- `exciting.mp3` — orchestral/adventurous
- `heartwarming.mp3` — gentle piano/strings
- `funny.mp3` — playful/quirky
- `mysterious.mp3` — atmospheric/ethereal
- `default.mp3` — neutral ambient (used when no mood selected)

These should be sourced from royalty-free libraries (e.g., Pixabay Music, FreePD). Keep file sizes small (~1-2 MB each).

**Step 2: Write failing test**

Add to `backend/tests/test_audio_stitcher.py`:
```python
@pytest.mark.asyncio
async def test_mixes_background_music_when_mood_provided():
    # Create a simple test audio segment
    segment = AudioSegment.silent(duration=2000)
    buf = io.BytesIO()
    segment.export(buf, format="mp3")
    test_audio = buf.getvalue()

    state = {
        "audio_segments": [test_audio],
        "mood": "exciting",
    }

    result = await audio_stitcher(state)
    assert len(result["final_audio"]) > 0
    assert result["duration_seconds"] >= 2
```

**Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_audio_stitcher.py::test_mixes_background_music_when_mood_provided -v`
Expected: FAIL — `audio_stitcher` doesn't accept mood

**Step 4: Implement background music mixing**

Replace `backend/app/graph/nodes/audio_stitcher.py`:

```python
import io
from pathlib import Path

from pydub import AudioSegment

from app.graph.state import StoryState

PAUSE_MS = 500
MUSIC_DIR = Path(__file__).parent.parent / "data" / "music"
MUSIC_VOLUME_DB = -18  # Mix music ~15-20% of narration volume


def _load_background_music(mood: str | None, target_duration_ms: int) -> AudioSegment | None:
    """Load and loop background music to match story duration."""
    mood_key = mood if mood in ("exciting", "heartwarming", "funny", "mysterious") else "default"
    music_path = MUSIC_DIR / f"{mood_key}.mp3"

    if not music_path.exists():
        return None

    music = AudioSegment.from_mp3(str(music_path))
    # Loop music to cover the full story duration
    loops_needed = (target_duration_ms // len(music)) + 1
    looped = music * loops_needed
    # Trim to exact duration with fade out
    trimmed = looped[:target_duration_ms]
    trimmed = trimmed.fade_in(2000).fade_out(3000)
    return trimmed + MUSIC_VOLUME_DB


async def audio_stitcher(state: StoryState) -> dict:
    pause = AudioSegment.silent(duration=PAUSE_MS)
    combined = AudioSegment.empty()

    for i, audio_bytes in enumerate(state["audio_segments"]):
        segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
        combined += segment
        if i < len(state["audio_segments"]) - 1:
            combined += pause

    # Mix background music if available
    mood = state.get("mood")
    bg_music = _load_background_music(mood, len(combined))
    if bg_music is not None:
        combined = combined.overlay(bg_music)

    buf = io.BytesIO()
    combined.export(buf, format="mp3")
    final_bytes = buf.getvalue()
    duration_seconds = int(len(combined) / 1000)

    return {"final_audio": final_bytes, "duration_seconds": duration_seconds}
```

**Step 5: Run all audio stitcher tests**

Run: `cd backend && python -m pytest tests/test_audio_stitcher.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add backend/app/graph/nodes/audio_stitcher.py backend/app/data/music/ backend/tests/test_audio_stitcher.py
git commit -m "feat: add background music mixing to audio stitcher"
```

---

### Task 7: Change narrator voice to female

**Files:**
- Modify: `backend/app/config.py:8` (default voice ID)
- Modify: `backend/.env.example`

**Step 1: Update default narrator voice ID**

In `backend/app/config.py`, change:
```python
narrator_voice_id: str = "pNInz6obpgDQGcFmaJgB"
```
to a female ElevenLabs voice. Use Rachel (calm, warm female narrator):
```python
narrator_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
```

**Step 2: Update .env.example**

Update the comment and default in `backend/.env.example`:
```
# ElevenLabs Voice IDs (find at https://elevenlabs.io/app/voice-library)
NARRATOR_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

**Step 3: Commit**

```bash
git add backend/app/config.py backend/.env.example
git commit -m "feat: switch narrator to female voice (Rachel)"
```

---

### Task 8: Expand historical events library

**Files:**
- Modify: `backend/app/data/historical_events.yaml`
- Modify: `backend/tests/test_config_routes.py` (update count assertion)

**Step 1: Research and add new events**

Add the following well-researched events to `backend/app/data/historical_events.yaml`, bringing the total from 6 to ~20. Each event must have 8-10 accurate key_facts.

**Indian History additions:**
- Ashoka's transformation after Kalinga War (261 BCE)
- Chandragupta Maurya's rise to power (322 BCE)
- Subhas Chandra Bose and the INA (1943)
- Dr. APJ Abdul Kalam and India's first satellite launch (1980)
- Bhagat Singh's act of defiance (1929)

**World History additions:**
- Building the Great Pyramid of Giza (~2560 BCE)
- Alexander the Great's campaign (334 BCE)
- Leonardo da Vinci in Renaissance Florence (~1500)
- Marie Curie's discovery of radium (1898)
- Rosa Parks and the Montgomery Bus Boycott (1955)

**Science & Exploration additions:**
- Darwin's voyage on the Beagle (1831)
- Galileo's telescope and challenging the church (1610)
- Amundsen reaches the South Pole (1911)
- Gutenberg invents the printing press (~1440)

Each event follows the existing YAML format with `id`, `title`, `figure`, `year`, `summary`, `key_facts` (8-10 facts), and `thumbnail`.

**Step 2: Update test assertion**

In `backend/tests/test_config_routes.py`, update the genre/event count assertions:
```python
def test_get_historical_events():
    response = client.get("/api/historical-events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 20  # Updated from 6
```

**Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_config_routes.py -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add backend/app/data/historical_events.yaml backend/tests/test_config_routes.py
git commit -m "feat: expand historical events library from 6 to 20 events"
```

---

### Task 9: Update API client and TypeScript types for mood/length

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

**Step 1: Add mood and length to types**

In `frontend/src/types/index.ts`, add:
```typescript
export type StoryMood = "exciting" | "heartwarming" | "funny" | "mysterious";
export type StoryLength = "short" | "medium" | "long";
```

Update `WizardStep` type:
```typescript
export type WizardStep =
  | "hero"
  | "craft"
  | "story";
```

**Step 2: Update API client**

In `frontend/src/api/client.ts`, update `createCustomStory`:
```typescript
export async function createCustomStory(
  kid: KidProfile,
  genre: string,
  description: string,
  mood?: string,
  length?: string,
): Promise<JobCreatedResponse> {
  const res = await fetch(`${BASE}/story/custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kid, genre, description, mood, length }),
  });
  return res.json();
}
```

**Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add mood and length to frontend types and API client"
```

---

### Task 10: Install frontend animation dependencies

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install framer-motion for animations**

```bash
cd frontend && npm install framer-motion
```

**Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add framer-motion for UI animations"
```

---

### Task 11: Create the visual design system (CSS foundation)

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/index.html` (add Google Font)

**Step 1: Add Google Font to index.html**

In `frontend/index.html`, add inside `<head>`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

Update `<title>` to `Taleweaver` if not done already.

**Step 2: Create the design system in index.css**

Replace `frontend/src/index.css`:

```css
@import "tailwindcss";

@theme {
  --color-void: #0a0a1a;
  --color-abyss: #1a0a2e;
  --color-mystic: #7c3aed;
  --color-ethereal: #a78bfa;
  --color-glow: #c4b5fd;
  --color-gold: #f59e0b;
  --color-gold-light: #fbbf24;
  --color-starlight: #f0f0ff;
  --color-mist: rgba(255, 255, 255, 0.06);
  --color-glass: rgba(255, 255, 255, 0.08);
  --color-glass-border: rgba(255, 255, 255, 0.12);

  --font-display: "Cinzel", serif;
  --font-body: "Inter", sans-serif;
}

body {
  font-family: var(--font-body);
  background: linear-gradient(135deg, var(--color-void) 0%, var(--color-abyss) 100%);
  color: var(--color-starlight);
  min-height: 100vh;
  overflow-x: hidden;
}

/* Glowing text */
.text-glow {
  text-shadow: 0 0 20px rgba(167, 139, 250, 0.5), 0 0 40px rgba(167, 139, 250, 0.2);
}

.text-glow-gold {
  text-shadow: 0 0 20px rgba(245, 158, 11, 0.5), 0 0 40px rgba(245, 158, 11, 0.2);
}

/* Glass card */
.glass-card {
  background: var(--color-glass);
  border: 1px solid var(--color-glass-border);
  backdrop-filter: blur(12px);
  border-radius: 1rem;
}

.glass-card:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(167, 139, 250, 0.3);
}

/* Glowing input */
.glow-input {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--color-starlight);
  border-radius: 0.75rem;
  padding: 0.75rem 1rem;
  transition: all 0.3s ease;
}

.glow-input:focus {
  outline: none;
  border-color: var(--color-ethereal);
  box-shadow: 0 0 15px rgba(167, 139, 250, 0.3), 0 0 30px rgba(167, 139, 250, 0.1);
}

.glow-input::placeholder {
  color: rgba(240, 240, 255, 0.3);
}

/* Primary button with glow */
.btn-glow {
  background: linear-gradient(135deg, var(--color-mystic), #6d28d9);
  color: white;
  font-weight: 600;
  padding: 0.75rem 2rem;
  border-radius: 0.75rem;
  transition: all 0.3s ease;
  position: relative;
}

.btn-glow:hover {
  box-shadow: 0 0 20px rgba(124, 58, 237, 0.5), 0 0 40px rgba(124, 58, 237, 0.2);
  transform: translateY(-1px);
}

.btn-glow:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

/* Particle canvas container */
.particles-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

/* Ensure content sits above particles */
.content-layer {
  position: relative;
  z-index: 1;
}
```

**Step 3: Commit**

```bash
git add frontend/src/index.css frontend/index.html
git commit -m "feat: create immersive fantasy design system with glass, glow, and dark theme"
```

---

### Task 12: Create particle background component

**Files:**
- Create: `frontend/src/components/ParticleBackground.tsx`

**Step 1: Create the particle system**

Create `frontend/src/components/ParticleBackground.tsx`:

```tsx
import { useEffect, useRef } from "react";

interface Particle {
  x: number;
  y: number;
  size: number;
  speedX: number;
  speedY: number;
  opacity: number;
  twinkleSpeed: number;
  twinkleOffset: number;
}

export default function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    const particles: Particle[] = [];
    const PARTICLE_COUNT = 60;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    const createParticle = (): Particle => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2.5 + 0.5,
      speedX: (Math.random() - 0.5) * 0.3,
      speedY: (Math.random() - 0.5) * 0.3 - 0.1,
      opacity: Math.random() * 0.6 + 0.2,
      twinkleSpeed: Math.random() * 0.02 + 0.01,
      twinkleOffset: Math.random() * Math.PI * 2,
    });

    const init = () => {
      resize();
      particles.length = 0;
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push(createParticle());
      }
    };

    const animate = (time: number) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (const p of particles) {
        p.x += p.speedX;
        p.y += p.speedY;

        // Wrap around
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;

        const twinkle = Math.sin(time * p.twinkleSpeed + p.twinkleOffset) * 0.3 + 0.7;
        const alpha = p.opacity * twinkle;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(196, 181, 253, ${alpha})`;
        ctx.fill();

        // Glow effect
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * 3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(167, 139, 250, ${alpha * 0.15})`;
        ctx.fill();
      }

      animationId = requestAnimationFrame(animate);
    };

    init();
    animationId = requestAnimationFrame(animate);
    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="particles-container"
      aria-hidden="true"
    />
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/ParticleBackground.tsx
git commit -m "feat: add floating particle background component"
```

---

### Task 13: Rebuild App.tsx with 3-screen flow

**Files:**
- Modify: `frontend/src/App.tsx` (complete rewrite)

**Step 1: Rewrite App.tsx**

This is a complete rewrite. The new App.tsx has 3 screens (hero, craft, story) with framer-motion page transitions, the particle background, and the new state for mood/length. Use the `@frontend-design` skill for the visual implementation.

Key changes:
- Import `AnimatePresence` and `motion` from `framer-motion`
- Import `ParticleBackground`
- Replace 6 wizard steps with 3: `"hero"`, `"craft"`, `"story"`
- Add state for `storyType`, `mood`, `length`
- Wrap each screen in `motion.div` with fade/slide transitions
- Dark header with Cinzel font and glow effect
- Remove old step-based routing, use new 3-screen flow

```tsx
import { useCallback, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { KidProfile, StoryMood, StoryLength, StoryType, WizardStep } from "./types";
import HeroScreen from "./components/HeroScreen";
import CraftScreen from "./components/CraftScreen";
import StoryScreen from "./components/StoryScreen";
import ParticleBackground from "./components/ParticleBackground";
import {
  createCustomStory,
  createHistoricalStory,
  pollJobStatus,
  getAudioUrl,
} from "./api/client";

const pageVariants = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: "easeOut" } },
  exit: { opacity: 0, scale: 1.04, transition: { duration: 0.3, ease: "easeIn" } },
};

export default function App() {
  const [step, setStep] = useState<WizardStep>("hero");
  const [kidProfile, setKidProfile] = useState<KidProfile | null>(null);
  const [storyType, setStoryType] = useState<StoryType>("custom");
  const [mood, setMood] = useState<StoryMood | undefined>();
  const [length, setLength] = useState<StoryLength | undefined>();
  const [currentStage, setCurrentStage] = useState("writing");
  const [storyTitle, setStoryTitle] = useState("");
  const [storyDuration, setStoryDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState("");
  const [error, setError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const startPolling = useCallback((jobId: string) => {
    setIsGenerating(true);
    setCurrentStage("writing");

    pollingRef.current = setInterval(async () => {
      try {
        const status = await pollJobStatus(jobId);
        if (status.status === "complete" && "title" in status) {
          clearInterval(pollingRef.current);
          setStoryTitle(status.title);
          setStoryDuration(status.duration_seconds);
          setAudioUrl(getAudioUrl(jobId));
          setIsGenerating(false);
        } else if (status.status === "failed") {
          clearInterval(pollingRef.current);
          setError("Something went wrong. Please try again.");
          setIsGenerating(false);
        } else if ("current_stage" in status) {
          setCurrentStage(status.current_stage);
        }
      } catch {
        clearInterval(pollingRef.current);
        setError("Connection lost. Please try again.");
        setIsGenerating(false);
      }
    }, 2000);
  }, []);

  const handleCreateStory = async (genre: string, description: string) => {
    if (!kidProfile) return;
    setError("");
    setStep("story");
    const job = await createCustomStory(kidProfile, genre, description, mood, length);
    startPolling(job.job_id);
  };

  const handleHistoricalStory = async (eventId: string) => {
    if (!kidProfile) return;
    setError("");
    setStep("story");
    const job = await createHistoricalStory(kidProfile, eventId);
    startPolling(job.job_id);
  };

  const handleCreateAnother = () => {
    setStep("craft");
    setStoryTitle("");
    setStoryDuration(0);
    setAudioUrl("");
    setError("");
    setIsGenerating(false);
  };

  return (
    <div className="min-h-screen">
      <ParticleBackground />

      <div className="content-layer min-h-screen flex flex-col">
        <header className="py-8 text-center">
          <h1 className="text-4xl md:text-5xl font-display font-bold text-glow tracking-wide text-ethereal">
            Taleweaver
          </h1>
          <p className="text-starlight/40 mt-2 text-sm tracking-widest uppercase">
            Where stories come alive
          </p>
        </header>

        <main className="flex-1 px-4 pb-16">
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-lg mx-auto mb-6 p-4 glass-card border-red-500/30 text-red-300 text-center"
            >
              {error}
            </motion.div>
          )}

          <AnimatePresence mode="wait">
            {step === "hero" && (
              <motion.div key="hero" variants={pageVariants} initial="initial" animate="animate" exit="exit">
                <HeroScreen
                  onSubmit={(profile, type) => {
                    setKidProfile(profile);
                    setStoryType(type);
                    setStep("craft");
                  }}
                />
              </motion.div>
            )}

            {step === "craft" && (
              <motion.div key="craft" variants={pageVariants} initial="initial" animate="animate" exit="exit">
                <CraftScreen
                  storyType={storyType}
                  mood={mood}
                  length={length}
                  onMoodChange={setMood}
                  onLengthChange={setLength}
                  onSubmitCustom={handleCreateStory}
                  onSubmitHistorical={handleHistoricalStory}
                  onBack={() => setStep("hero")}
                  onTypeChange={setStoryType}
                />
              </motion.div>
            )}

            {step === "story" && (
              <motion.div key="story" variants={pageVariants} initial="initial" animate="animate" exit="exit">
                <StoryScreen
                  isGenerating={isGenerating}
                  currentStage={currentStage}
                  title={storyTitle}
                  audioUrl={audioUrl}
                  durationSeconds={storyDuration}
                  onCreateAnother={handleCreateAnother}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: rewrite App.tsx with 3-screen flow and framer-motion transitions"
```

---

### Task 14: Build Screen 1 — HeroScreen component

**Files:**
- Create: `frontend/src/components/HeroScreen.tsx`

**Step 1: Build HeroScreen**

This combines the kid profile form + story type selector into one immersive screen. Use the `@frontend-design` skill for visual polish.

The component should include:
- Kid name input (glowing)
- Age selector (animated slider or visual selector)
- Optional details in a collapsible "Personalize" section
- Story type selection as two glowing orb/portal buttons at the bottom
- All using glass-card, glow-input, and btn-glow CSS classes
- Framer-motion animations on mount for each section

Props: `onSubmit: (profile: KidProfile, type: StoryType) => void`

**Step 2: Commit**

```bash
git add frontend/src/components/HeroScreen.tsx
git commit -m "feat: add HeroScreen component — kid profile + story type selection"
```

---

### Task 15: Build Screen 2 — CraftScreen component

**Files:**
- Create: `frontend/src/components/CraftScreen.tsx`

**Step 1: Build CraftScreen**

This screen combines genre/event selection with mood and length selectors. Use the `@frontend-design` skill.

For **Custom** path:
- Genre cards as glowing glass cards with 3D tilt hover (use framer-motion `whileHover`)
- Description textarea with glow-input styling
- Mood selector: 4 glass cards with icons (Exciting ⚡, Heartwarming 💛, Funny 😄, Mysterious 🔮)
- Length selector: 3 options (Short, Medium, Long) as pill buttons

For **Historical** path:
- Event cards as "time portal" glass cards with year badges
- Same mood/length selectors

Tab toggle at top to switch between Custom and Historical.

Props:
```typescript
interface Props {
  storyType: StoryType;
  mood?: StoryMood;
  length?: StoryLength;
  onMoodChange: (mood: StoryMood | undefined) => void;
  onLengthChange: (length: StoryLength | undefined) => void;
  onSubmitCustom: (genre: string, description: string) => void;
  onSubmitHistorical: (eventId: string) => void;
  onBack: () => void;
  onTypeChange: (type: StoryType) => void;
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/CraftScreen.tsx
git commit -m "feat: add CraftScreen component — genre/event + mood/length selection"
```

---

### Task 16: Build Screen 3 — StoryScreen component

**Files:**
- Create: `frontend/src/components/StoryScreen.tsx`

**Step 1: Build StoryScreen**

This screen handles both the generation animation AND the audio player. Use the `@frontend-design` skill.

**Generation phase** (when `isGenerating` is true):
- Animated orb/portal in the center with orbiting particles
- Stage labels appearing with typewriter effect
- Progress indicators as glowing dots

**Playback phase** (when `isGenerating` is false and `audioUrl` is set):
- Story title with glow effect
- Custom audio player with:
  - Waveform-style seek bar (styled range input or custom SVG)
  - Large play/pause button as a glowing orb
  - Time display
- Download and "Create Another" buttons with glass styling

Props:
```typescript
interface Props {
  isGenerating: boolean;
  currentStage: string;
  title: string;
  audioUrl: string;
  durationSeconds: number;
  onCreateAnother: () => void;
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/StoryScreen.tsx
git commit -m "feat: add StoryScreen component — generation animation + audio player"
```

---

### Task 17: Clean up old components

**Files:**
- Delete: `frontend/src/components/KidProfileForm.tsx`
- Delete: `frontend/src/components/StoryTypeSelector.tsx`
- Delete: `frontend/src/components/CustomStoryForm.tsx`
- Delete: `frontend/src/components/HistoricalEventPicker.tsx`
- Delete: `frontend/src/components/GeneratingScreen.tsx`
- Delete: `frontend/src/components/AudioPlayer.tsx`

**Step 1: Remove old components**

```bash
cd frontend/src/components
rm KidProfileForm.tsx StoryTypeSelector.tsx CustomStoryForm.tsx HistoricalEventPicker.tsx GeneratingScreen.tsx AudioPlayer.tsx
```

**Step 2: Verify build**

```bash
cd frontend && npm run build
```
Expected: Build succeeds with no import errors.

**Step 3: Commit**

```bash
git add -u frontend/src/components/
git commit -m "chore: remove old wizard components replaced by 3-screen flow"
```

---

### Task 18: Update CLAUDE.md with v2 architecture

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update the project documentation**

Update `CLAUDE.md` to reflect:
- New name (Taleweaver)
- 3-screen flow instead of 6-step wizard
- New components (HeroScreen, CraftScreen, StoryScreen, ParticleBackground)
- Mood and length parameters
- Background music feature
- Female narrator voice
- Expanded historical events (20 events)
- framer-motion dependency
- Updated frontend component list

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for Taleweaver v2 architecture"
```

---

### Task 19: End-to-end smoke test

**Step 1: Run backend tests**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/ -v
```
Expected: ALL tests pass.

**Step 2: Run frontend build**

```bash
cd frontend && npm run build
```
Expected: Build succeeds with no errors.

**Step 3: Manual smoke test**

Start both servers and verify:
1. App loads with dark fantasy theme and floating particles
2. Screen 1: Can enter kid profile and select story type
3. Screen 2: Can pick genre/event, mood, and length
4. Screen 3: Generation animation plays, then audio player appears
5. Audio plays with background music mixed in
6. Download works
7. "Create Another" returns to Screen 2

**Step 4: Commit any fixes found during smoke test**
