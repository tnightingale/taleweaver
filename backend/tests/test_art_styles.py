"""
Tests for Art Style System (Stage 2)
Tests verify art style presets and API endpoint
"""
import pytest
from pathlib import Path
import yaml


def test_art_styles_yaml_exists():
    """art_styles.yaml file should exist in data directory"""
    data_dir = Path(__file__).parent.parent / "app" / "data"
    art_styles_file = data_dir / "art_styles.yaml"
    assert art_styles_file.exists(), "art_styles.yaml should exist"


def test_art_styles_data_structure():
    """Art styles YAML should have correct structure"""
    data_dir = Path(__file__).parent.parent / "app" / "data"
    with open(data_dir / "art_styles.yaml") as f:
        art_styles = yaml.safe_load(f)
    
    assert isinstance(art_styles, list), "Art styles should be a list"
    assert len(art_styles) > 0, "Should have at least one art style"
    
    # Verify structure of each style
    for style in art_styles:
        assert "id" in style, "Each style should have an id"
        assert "name" in style, "Each style should have a name"
        assert "description" in style, "Each style should have a description"
        assert "prompt" in style, "Each style should have a prompt field"
        
        # Validate types
        assert isinstance(style["id"], str), "id should be string"
        assert isinstance(style["name"], str), "name should be string"
        assert isinstance(style["description"], str), "description should be string"
        assert style["prompt"] is None or isinstance(style["prompt"], str), "prompt should be string or null"


def test_art_style_prompts_valid():
    """All art styles except 'custom' should have non-empty prompts"""
    data_dir = Path(__file__).parent.parent / "app" / "data"
    with open(data_dir / "art_styles.yaml") as f:
        art_styles = yaml.safe_load(f)
    
    for style in art_styles:
        if style["id"] == "custom":
            # Custom style should have null prompt (user provides their own)
            assert style["prompt"] is None, "Custom style prompt should be null"
        else:
            # All other styles should have non-empty prompts
            assert style["prompt"], f"Style '{style['id']}' should have a prompt"
            assert len(style["prompt"]) > 20, f"Style '{style['id']}' prompt should be descriptive (>20 chars)"


def test_custom_style_allows_user_prompt():
    """Custom style should exist and allow user-provided prompts"""
    data_dir = Path(__file__).parent.parent / "app" / "data"
    with open(data_dir / "art_styles.yaml") as f:
        art_styles = yaml.safe_load(f)
    
    # Find custom style
    custom_style = next((s for s in art_styles if s["id"] == "custom"), None)
    assert custom_style is not None, "Should have a 'custom' style option"
    assert custom_style["prompt"] is None, "Custom style should not have a predefined prompt"
    assert "custom" in custom_style["name"].lower(), "Custom style name should indicate customization"


def test_get_art_styles_endpoint(test_client):
    """GET /api/art-styles returns all available art styles"""
    response = test_client.get("/api/art-styles")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list), "Should return a list"
    assert len(data) >= 7, "Should have at least 7 art styles (6 presets + custom)"
    
    # Verify structure of first style
    style = data[0]
    assert "id" in style
    assert "name" in style
    assert "description" in style
    assert "prompt" in style
    
    # Verify we have the expected styles
    style_ids = [s["id"] for s in data]
    assert "watercolor_dream" in style_ids
    assert "classic_storybook" in style_ids
    assert "modern_flat" in style_ids
    assert "whimsical_ink" in style_ids
    assert "digital_fantasy" in style_ids
    assert "vintage_fairy_tale" in style_ids
    assert "custom" in style_ids


def test_art_styles_have_unique_ids():
    """All art style IDs should be unique"""
    data_dir = Path(__file__).parent.parent / "app" / "data"
    with open(data_dir / "art_styles.yaml") as f:
        art_styles = yaml.safe_load(f)
    
    ids = [s["id"] for s in art_styles]
    assert len(ids) == len(set(ids)), "Art style IDs should be unique"


def test_art_styles_have_meaningful_descriptions():
    """All art styles should have helpful descriptions"""
    data_dir = Path(__file__).parent.parent / "app" / "data"
    with open(data_dir / "art_styles.yaml") as f:
        art_styles = yaml.safe_load(f)
    
    for style in art_styles:
        # Description should be at least 10 characters
        assert len(style["description"]) >= 10, f"Style '{style['id']}' should have meaningful description"
        
        # Name should be title case or similar
        assert style["name"][0].isupper(), f"Style '{style['id']}' name should start with capital"
