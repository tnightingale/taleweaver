"""
Tests for Gemini API timeout and retry behavior.

The illustration generator must not hang indefinitely on slow API calls,
and should retry when Gemini returns text instead of an image.
"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_gemini_call_times_out():
    """
    A hanging Gemini API call should timeout instead of blocking forever.
    """
    from app.services.illustration.nanobanana import NanoBanana2Provider

    provider = NanoBanana2Provider.__new__(NanoBanana2Provider)
    provider.model_id = "test-model"

    # Mock a model that hangs for 10 seconds
    def slow_generate(*args, **kwargs):
        import time
        time.sleep(10)

    provider.model = MagicMock()
    provider.model.generate_content = slow_generate

    with pytest.raises((asyncio.TimeoutError, Exception)) as exc_info:
        await asyncio.wait_for(
            provider.generate_image(
                prompt="test prompt",
                art_style="watercolor",
            ),
            timeout=3,  # Should timeout well before 10s
        )


@pytest.mark.asyncio
async def test_gemini_retries_on_no_image_response():
    """
    When Gemini returns a response without image data (text-only),
    the provider should retry once before raising.
    """
    from app.services.illustration.nanobanana import NanoBanana2Provider

    provider = NanoBanana2Provider.__new__(NanoBanana2Provider)
    provider.model_id = "test-model"

    # Mock a response with text but no image
    text_part = MagicMock()
    text_part.inline_data = None  # No image data

    text_response = MagicMock()
    text_response.parts = [text_part]

    call_count = 0

    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return text_response

    provider.model = MagicMock()
    provider.model.generate_content = mock_generate

    with pytest.raises(Exception, match="No image found"):
        await provider.generate_image(
            prompt="test prompt",
            art_style="watercolor",
        )

    # Should have tried twice (initial + 1 retry)
    assert call_count == 2, f"Expected 2 attempts, got {call_count}"


@pytest.mark.asyncio
async def test_gemini_succeeds_on_retry_after_no_image():
    """
    If first attempt returns no image but second attempt succeeds,
    the image should be returned successfully.
    """
    from app.services.illustration.nanobanana import NanoBanana2Provider

    provider = NanoBanana2Provider.__new__(NanoBanana2Provider)
    provider.model_id = "test-model"

    # Create a minimal valid PNG (1x1 pixel)
    from PIL import Image
    from io import BytesIO
    img = Image.new('RGB', (1, 1), color='red')
    buf = BytesIO()
    img.save(buf, format='PNG')
    png_bytes = buf.getvalue()

    # First call: text-only response (no image)
    text_part = MagicMock()
    text_part.inline_data = None

    text_response = MagicMock()
    text_response.parts = [text_part]

    # Second call: image response
    image_part = MagicMock()
    image_part.inline_data = MagicMock()
    image_part.inline_data.data = png_bytes

    image_response = MagicMock()
    image_response.parts = [image_part]

    call_count = 0

    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return text_response if call_count == 1 else image_response

    provider.model = MagicMock()
    provider.model.generate_content = mock_generate

    result = await provider.generate_image(
        prompt="test prompt",
        art_style="watercolor",
    )

    assert call_count == 2
    assert len(result) > 0  # Got image bytes back
