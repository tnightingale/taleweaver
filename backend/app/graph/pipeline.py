from langgraph.graph import StateGraph, END

from app.graph.state import StoryState
from app.graph.nodes.story_writer import story_writer
from app.graph.nodes.scene_analyzer import scene_analyzer
from app.graph.nodes.script_splitter import script_splitter
from app.graph.nodes.voice_synthesizer import voice_synthesizer
from app.graph.nodes.illustration_generator import illustration_generator
from app.graph.nodes.cover_generator import cover_generator
from app.graph.nodes.audio_stitcher import audio_stitcher
from app.graph.nodes.timestamp_calculator import timestamp_calculator


def create_story_pipeline():
    graph = StateGraph(StoryState)

    # Add all nodes
    graph.add_node("story_writer", story_writer)
    graph.add_node("scene_analyzer", scene_analyzer)
    graph.add_node("script_splitter", script_splitter)
    graph.add_node("voice_synthesizer", voice_synthesizer)
    graph.add_node("illustration_generator", illustration_generator)
    graph.add_node("cover_generator", cover_generator)
    graph.add_node("audio_stitcher", audio_stitcher)
    graph.add_node("timestamp_calculator", timestamp_calculator)

    # Define pipeline flow
    graph.set_entry_point("story_writer")
    graph.add_edge("story_writer", "scene_analyzer")
    graph.add_edge("scene_analyzer", "script_splitter")

    # Parallel execution: voice synthesis, illustration generation, and cover generation
    graph.add_edge("script_splitter", "voice_synthesizer")
    graph.add_edge("script_splitter", "illustration_generator")
    graph.add_edge("script_splitter", "cover_generator")

    # All three must complete before audio stitching
    graph.add_edge("voice_synthesizer", "audio_stitcher")
    graph.add_edge("illustration_generator", "audio_stitcher")
    graph.add_edge("cover_generator", "audio_stitcher")

    # Calculate timestamps after we know total duration
    graph.add_edge("audio_stitcher", "timestamp_calculator")
    graph.add_edge("timestamp_calculator", END)

    return graph.compile()
