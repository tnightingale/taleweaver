# StoryForge v2 Design — Immersive Overhaul

## Overview

Redesign StoryForge with three goals:
1. **Story quality** — encode storytelling science into prompts for dramatically more engaging stories
2. **UI overhaul** — immersive fantasy theme with a 3-screen narrative flow replacing the 6-step wizard
3. **Audio enhancements** — female narrator voice + background music per mood

## The 3-Screen Flow

### Screen 1: "Who's the hero?"

Full-viewport dark background with animated floating particles (stars/sparkles).

- Kid's name input with glowing, pulsing text field
- Age selector as animated dial/slider with visual age indicators
- Optional details field (interests, personality)
- Story type toggle (Custom vs Historical) as two glowing orbs/portals
- Ambient animation throughout — feels like standing at the entrance to a magical realm

### Screen 2: "Craft the adventure"

Transitions in with a "portal opening" animation.

**Custom path:**
- Genre cards as floating, glowing artifacts (sword for adventure, wand for fantasy, etc.) with 3D tilt-on-hover
- Description textarea
- Mood selector — 4 options with visual icons: Exciting, Heartwarming, Funny, Mysterious
- Story length — Short / Medium / Long (maps to age-appropriate word counts)

**Historical path:**
- Event cards as "time portal windows" showing era-appropriate visual treatments
- Same mood/length selectors

### Screen 3: "The story unfolds"

**Generation phase:**
- Animated "quill writing" or glowing text appearance showing story title + teaser
- Progress as narrative journey: "Crafting the tale... Giving voices to characters... Weaving the audio..."

**Playback phase (seamless transition):**
- Waveform visualization
- Play/pause with glowing orb control
- Seek bar styled as a path through a landscape
- Download button
- Story title and summary displayed above player

## Story Quality — Prompt Engineering

### Story Spine Pre-Planning

Before writing prose, the LLM fills out a structured skeleton (internally):

```
Once upon a time...       [World + Character]
Every day...              [Status quo]
Until one day...          [Inciting incident]
Because of that...        [Consequence 1]
Because of that...        [Consequence 2]
Because of that...        [Consequence 3]
Until finally...          [Climax]
And ever since then...    [New normal]
```

### The Four Essential Questions (every story must answer)

1. Who do I care about and why?
2. What do they want (specific, concrete desire)?
3. What's stopping them?
4. What happens if they fail?

### Age-Calibrated Directives

**Ages 3-5:**
- Single protagonist, single problem, Rule of Three structure
- Repetitive refrain for listener participation
- Complete happy resolution, sensory language
- 500-800 words (~5-8 min audio)

**Ages 6-8:**
- Protagonist slightly older than listener
- Internal + external problem in parallel
- 2-3 try/fail cycles, humor, friend/ally dynamic
- Moral earned not stated
- 1000-1500 words (~10-15 min)

**Ages 9-12:**
- Ensemble characters with distinct voices
- Subplot mirroring main theme
- Moral complexity, protagonist makes mistakes with consequences
- Cliffhanger-style ending optional
- 1500-2500 words (~15-25 min)

### Audio-Specific Directives

- Hook in the first paragraph (action, sound, or question — never backstory)
- Vary sentence length for pacing (short = urgency, long = calm/wonder)
- Build sound into prose (onomatopoeia, sound-first scene openings)
- Show emotion through action, not narration
- Include one recurring refrain per story
- Include one listener-directed prediction prompt
- Leave deliberate imagination gaps in descriptions
- No deus ex machina — protagonist solves their own problem

### Mood Integration (new parent input)

- **Exciting:** Faster pacing, physical action, higher stakes
- **Heartwarming:** Focus on relationships, emotional connection, quiet moments of kindness
- **Funny:** Absurdist logic, puns for older kids, physical comedy for younger
- **Mysterious:** Sensory descriptions, unanswered questions, atmospheric tension

## Voice & Audio

- **Narrator voice → female** (update ElevenLabs voice ID)
- Character voices remain distinct (male, female, child) for dialogue
- **Background music:** One royalty-free ambient track per mood:
  - Exciting → orchestral/adventurous
  - Heartwarming → gentle piano/strings
  - Funny → playful/quirky
  - Mysterious → atmospheric/ethereal
- Mixed into final MP3 at ~15-20% of narration volume via pydub
- Fade in at start, continuous throughout, fade out at end

## Visual Design System

**Color palette:**
- Background: Deep navy → dark purple gradient (#0a0a1a → #1a0a2e)
- Primary accent: Ethereal blue-purple glow (#7c3aed, #a78bfa)
- Secondary accent: Warm gold/amber (#f59e0b, #fbbf24)
- Text: Off-white (#f0f0ff) with subtle glow on headings
- Cards/surfaces: Semi-transparent dark with backdrop blur (glassmorphism)

**Animation & Effects:**
- Floating star/sparkle particle system across all screens
- Portal opening/closing page transitions
- 3D tilt on hover for cards, glow border pulses
- Glowing focus states on inputs, text shimmer
- Gradient buttons with hover glow expansion
- Orbiting particles during generation loading

**Typography:**
- Display font with character for headings
- Clean sans-serif for body/inputs

**Responsive:** Mobile-first — must look great on phones.

## Expanded Historical Events Library

Current library has 6 events. Expand to ~20 well-researched events across diverse categories:

**Indian History (add ~5 more):**
- Ashoka's transformation after the Kalinga War (261 BCE)
- Chandragupta Maurya's rise to power
- Subhas Chandra Bose and the INA
- Dr. APJ Abdul Kalam and India's space program
- Bhagat Singh's act of defiance in the Central Assembly

**World History (add ~5 more):**
- Ancient Egypt — building the Great Pyramid
- Alexander the Great's campaign
- Leonardo da Vinci in Renaissance Florence
- Marie Curie's discovery of radium
- Rosa Parks and the Montgomery Bus Boycott

**Science & Exploration (add ~4 more):**
- Darwin's voyage on the Beagle
- Galileo's telescope and challenging the church
- The first expedition to the South Pole (Amundsen vs Scott)
- The invention of the printing press (Gutenberg)

Each event gets:
- Thoroughly researched key_facts (8-10 facts instead of current 5)
- Age-appropriate context notes
- Accurate dates, names, and sequence of events
- Cultural sensitivity review

## What's NOT Changing

- Backend framework (FastAPI)
- LangGraph pipeline structure (writer → splitter → synthesizer → stitcher)
- Job-based polling architecture
- API endpoint structure (may add fields but same routes)
- ElevenLabs TTS integration (just different voice ID for narrator)
- No accounts/persistence (still stateless v1)
