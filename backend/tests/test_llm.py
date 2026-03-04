from unittest.mock import patch
from app.graph.llm import get_llm


def test_get_llm_groq():
    with patch("app.graph.llm.settings") as mock_settings:
        mock_settings.llm_provider = "groq"
        mock_settings.groq_api_key = "test-key"
        llm = get_llm()
        assert llm is not None


def test_get_llm_openai():
    with patch("app.graph.llm.settings") as mock_settings:
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test-key"
        llm = get_llm()
        assert llm is not None


def test_get_llm_anthropic_uses_sonnet():
    with patch("app.graph.llm.settings") as mock_settings:
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_api_key = "test-key"
        llm = get_llm()
        assert llm is not None
        assert "sonnet" in llm.model


def test_get_llm_has_max_tokens():
    with patch("app.graph.llm.settings") as mock_settings:
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_api_key = "test-key"
        llm = get_llm()
        assert llm.max_tokens == 8192


def test_get_llm_invalid_provider():
    with patch("app.graph.llm.settings") as mock_settings:
        mock_settings.llm_provider = "invalid"
        try:
            get_llm()
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "invalid" in str(e).lower()
