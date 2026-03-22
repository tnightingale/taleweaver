"""
Prompts for Scene Analysis - extracting Story Spine beats for illustration generation
"""


def build_scene_analysis_prompt(story_text: str, title: str, kid_name: str, kid_age: int, story_type: str) -> str:
    """
    Build prompt to analyze story and extract Story Spine beats for illustration.
    
    Returns structured JSON with scene metadata including illustration prompts.
    """
    
    num_beats = 8 if story_type == "custom" else 5
    beat_structure = """
Expected Story Spine beats for CUSTOM stories (8 beats):
1. Once upon a time... (world + character + normal)
2. Every day... (routine/status quo)
3. Until one day... (inciting incident)
4. Because of that... (first consequence)
5. Because of that... (second consequence)
6. Because of that... (third consequence)
7. Until finally... (climax)
8. And ever since then... (new normal)
""" if story_type == "custom" else """
Expected narrative beats for HISTORICAL stories (5 beats):
1. Transport (time travel observer arrives)
2. Buildup (events leading to the historical moment)
3. Key Moment (the main historical event)
4. Aftermath (immediate consequences)
5. Return (observer returns, reflection)
"""
    
    return f"""You are analyzing a children's audio story to identify key narrative beats for illustration generation.

STORY TO ANALYZE:
Title: {title}
Protagonist: {kid_name}, age {kid_age}
Story Type: {story_type}

{beat_structure}

FULL STORY TEXT:
{story_text}

---

YOUR TASK:

1. Identify the {num_beats} Story Spine beats in the story above
2. For each beat, find the MOST VISUAL moment (action, setting, character emotion)
3. Extract the protagonist's physical description from the story (hair color, eye color, age, clothing, distinguishing features)
4. Generate detailed illustration prompts for each beat that:
   - Describe the specific scene/moment
   - Include character positions and actions
   - Describe the setting/background
   - Capture the emotional tone
   - Are 2-4 sentences long

IMPORTANT FOR ILLUSTRATION CONSISTENCY:
- The protagonist should be described the same way in every scene
- Use consistent physical details (if {kid_name} has curly brown hair in beat 1, use that in all beats)
- Focus on ACTIONS and SETTINGS that change, not character appearance

OUTPUT FORMAT (valid JSON only, no markdown):
{{
  "character_description": "Brief physical description of {kid_name} for consistency across all illustrations (age, hair, eyes, clothing, key features)",
  "scenes": [
    {{
      "beat_index": 0,
      "beat_name": "Once upon a time",
      "text_excerpt": "First 1-3 sentences from this beat in the story",
      "illustration_prompt": "Detailed 2-4 sentence visual description of the scene. Example: 'A curious 7-year-old girl with curly brown hair and green eyes wearing a yellow raincoat stands at the edge of an enchanted forest at twilight. Glowing fireflies dance between ancient oak trees. The girl holds a worn leather map and looks excited but slightly nervous. Misty purple light filters through the canopy.'",
      "word_count": 85
    }},
    {{
      "beat_index": 1,
      "beat_name": "Every day",
      "text_excerpt": "First 1-3 sentences from this beat",
      "illustration_prompt": "Detailed visual description...",
      "word_count": 92
    }}
    // ... continue for all {num_beats} beats
  ]
}}

RULES:
- Output ONLY valid JSON (no markdown code blocks, no explanatory text)
- Exactly {num_beats} scenes
- word_count should represent approximate words in that beat section
- All word_count values should sum to roughly the total story word count
- illustration_prompt must be detailed enough for image generation AI
- character_description should capture ONLY physical appearance, not personality
"""


def build_character_extraction_prompt(story_text: str, kid_name: str) -> str:
    """
    Fallback prompt to extract just character description if scene analysis fails.
    """
    return f"""Extract the physical description of {kid_name} from this story.

STORY:
{story_text}

Output a single sentence describing {kid_name}'s physical appearance (age, hair color, eye color, clothing, notable features).
Include only visual details that would help an illustrator draw consistent character art.

Example output:
"A 7-year-old girl with curly brown hair, green eyes, wearing a yellow raincoat and red boots"

Output (plain text, no JSON):
"""
