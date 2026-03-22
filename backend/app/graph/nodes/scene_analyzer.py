"""
Scene Analyzer Node - Extracts Story Spine beats for illustration generation
"""
import logging
import json
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.llm import get_llm
from app.graph.state import StoryState, Scene
from app.prompts.scene_analysis import build_scene_analysis_prompt

logger = logging.getLogger(__name__)


async def scene_analyzer(state: StoryState) -> dict:
    """
    Analyze story text to identify Story Spine beats and generate illustration prompts.
    
    Returns:
        dict with 'scenes' (list of Scene dicts) and 'character_description' (str)
    """
    # Skip if no art style selected (user chose not to generate illustrations)
    if not state.get("art_style"):
        logger.info("No art style selected - skipping scene analysis")
        return {"scenes": None, "character_description": None}
    
    llm = get_llm()
    
    logger.info(f"Analyzing story for illustration beats (type: {state['story_type']})")
    
    prompt = build_scene_analysis_prompt(
        story_text=state["story_text"],
        title=state["title"],
        kid_name=state["kid_name"],
        kid_age=state["kid_age"],
        story_type=state["story_type"],
    )
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a scene analysis expert. Output only valid JSON."),
            HumanMessage(content=prompt),
        ])
        
        response_text = response.content.strip()
        
        # Strip markdown code blocks if LLM wrapped JSON
        if response_text.startswith("```"):
            # Remove ```json or ``` at start
            lines = response_text.split('\n')
            lines = lines[1:] if lines[0].startswith("```") else lines
            # Remove ``` at end
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = '\n'.join(lines)
        
        # Parse JSON response
        analysis = json.loads(response_text)
        
        # Validate structure
        if "scenes" not in analysis or "character_description" not in analysis:
            raise ValueError("Missing required fields in scene analysis response")
        
        scenes = analysis["scenes"]
        character_description = analysis["character_description"]
        
        # Validate scene count
        expected_count = 8 if state["story_type"] == "custom" else 5
        if len(scenes) != expected_count:
            logger.warning(f"Expected {expected_count} scenes, got {len(scenes)}. Adjusting...")
            # If too many, take first N; if too few, we'll work with what we have
            scenes = scenes[:expected_count]
        
        # Convert to Scene TypedDict format and add missing fields
        formatted_scenes: list[Scene] = []
        for scene in scenes:
            formatted_scene: Scene = {
                "beat_index": scene["beat_index"],
                "beat_name": scene["beat_name"],
                "text_excerpt": scene["text_excerpt"],
                "illustration_prompt": scene["illustration_prompt"],
                "timestamp_start": 0.0,  # Will be calculated after audio generation
                "timestamp_end": 0.0,
                "word_count": scene.get("word_count", 100),  # Default if missing
                "image_path": None,
                "image_url": None,
                "generation_metadata": None,
            }
            formatted_scenes.append(formatted_scene)
        
        logger.info(f"Scene analysis complete: {len(formatted_scenes)} beats identified")
        logger.info(f"Character description: {character_description}")
        
        return {
            "scenes": formatted_scenes,
            "character_description": character_description,
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse scene analysis JSON: {e}")
        logger.error(f"Response text: {response_text[:500]}")
        # Return None - illustration generation will be skipped
        return {"scenes": None, "character_description": None, "error": f"Scene analysis failed: invalid JSON"}
    
    except Exception as e:
        logger.error(f"Scene analysis failed: {e}")
        # Return None - illustration generation will be skipped
        return {"scenes": None, "character_description": None, "error": f"Scene analysis failed: {str(e)}"}
