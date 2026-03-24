"""
Tests for Illustration Provider (Stage 4)
TDD: RED tests first
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from io import BytesIO
import tempfile
import shutil
from PIL import Image

from app.services.illustration.base import IllustrationProvider
from app.services.illustration.nanobanana import NanoBanana2Provider
from app.services.illustration.factory import get_illustration_provider
from app.utils.storage import save_illustration, get_illustration_url, delete_story_illustrations, illustration_exists


def test_nanobanana_provider_initializes_with_api_key():
    """NanoBanana2Provider should initialize with API key"""
    provider = NanoBanana2Provider(api_key="test-key")
    assert provider.api_key == "test-key"
    assert provider.model_id == "gemini-3.1-flash-image-preview"


def test_nanobanana_provider_requires_api_key():
    """NanoBanana2Provider should raise error if no API key"""
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        NanoBanana2Provider(api_key=None)


@pytest.mark.asyncio
async def test_nanobanana_provider_text_to_image():
    """NanoBanana2Provider should generate image from text prompt"""
    # Create a simple 1x1 PNG image
    from PIL import Image
    from io import BytesIO
    img = Image.new('RGB', (1, 1), color='red')
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    fake_png_bytes = img_buffer.getvalue()
    
    # Mock inline_data with image bytes
    mock_inline_data = MagicMock()
    mock_inline_data.data = fake_png_bytes
    
    mock_part = MagicMock()
    mock_part.inline_data = mock_inline_data
    
    mock_response = MagicMock()
    mock_response.parts = [mock_part]
    
    mock_model = MagicMock()
    mock_model.generate_content = MagicMock(return_value=mock_response)
    
    with patch("app.services.illustration.nanobanana.genai.configure"):
        with patch("app.services.illustration.nanobanana.genai.GenerativeModel", return_value=mock_model):
            provider = NanoBanana2Provider(api_key="test-key")
            
            result = await provider.generate_image(
                prompt="A magical forest scene",
                art_style="watercolor painting, children's book",
                aspect_ratio="4:3",
                resolution="2K"
            )
            
            assert isinstance(result, bytes)
            assert len(result) > 0


@pytest.mark.asyncio
async def test_nanobanana_provider_image_to_image():
    """NanoBanana2Provider should support reference images for consistency"""
    from PIL import Image
    from io import BytesIO
    img = Image.new('RGB', (1, 1), color='blue')
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    fake_png_bytes = img_buffer.getvalue()
    
    mock_inline_data = MagicMock()
    mock_inline_data.data = fake_png_bytes
    
    mock_part = MagicMock()
    mock_part.inline_data = mock_inline_data
    
    mock_response = MagicMock()
    mock_response.parts = [mock_part]
    
    mock_model = MagicMock()
    mock_model.generate_content = MagicMock(return_value=mock_response)
    
    with patch("app.services.illustration.nanobanana.genai.configure"):
        with patch("app.services.illustration.nanobanana.genai.GenerativeModel", return_value=mock_model):
            provider = NanoBanana2Provider(api_key="test-key")
            
            result = await provider.generate_image(
                prompt="Same character in a different scene",
                art_style="watercolor painting",
                reference_image_url="/storage/stories/test/scene_0.png"
            )
            
            assert isinstance(result, bytes)


@pytest.mark.asyncio
async def test_nanobanana_provider_error_handling():
    """NanoBanana2Provider should raise exception on API errors"""
    mock_model = MagicMock()
    mock_model.generate_content = MagicMock(side_effect=Exception("API Error"))

    with patch("app.services.illustration.nanobanana.genai.configure"):
        with patch("app.services.illustration.nanobanana.genai.GenerativeModel", return_value=mock_model):
            provider = NanoBanana2Provider(api_key="test-key")

            with pytest.raises(Exception, match="API Error"):
                await provider.generate_image(
                    prompt="Test prompt",
                    art_style="test style"
                )


@pytest.mark.asyncio
async def test_nanobanana_retries_on_timeout():
    """NanoBanana2Provider should retry on timeout and succeed on later attempt"""
    import asyncio

    # Create a real image for the success response
    img = Image.new('RGB', (1, 1), color='green')
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    fake_png = img_buffer.getvalue()

    mock_inline_data = MagicMock()
    mock_inline_data.data = fake_png
    mock_part = MagicMock()
    mock_part.inline_data = mock_inline_data
    mock_success_response = MagicMock()
    mock_success_response.parts = [mock_part]

    call_count = [0]

    def mock_generate(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] <= 2:
            # Simulate a blocking call that will be timed out
            import time
            time.sleep(200)  # Will be cancelled by wait_for
        return mock_success_response

    mock_model = MagicMock()
    mock_model.generate_content = mock_generate

    with patch("app.services.illustration.nanobanana.genai.configure"):
        with patch("app.services.illustration.nanobanana.genai.GenerativeModel", return_value=mock_model):
            provider = NanoBanana2Provider(api_key="test-key")

            # Patch timeouts/backoff to be very short for testing
            with patch.object(provider, 'generate_image', wraps=provider.generate_image):
                import app.services.illustration.nanobanana as nb_module
                # We can't easily patch locals, so we'll use a different approach:
                # Just test with short timeout by patching asyncio.wait_for
                original_wait_for = asyncio.wait_for

                call_idx = [0]
                async def mock_wait_for(coro, timeout):
                    call_idx[0] += 1
                    if call_idx[0] <= 2:
                        # Cancel the coroutine and raise timeout
                        coro.close()
                        raise asyncio.TimeoutError()
                    return await original_wait_for(coro, timeout=5)

                with patch("app.services.illustration.nanobanana.asyncio.wait_for", side_effect=mock_wait_for):
                    with patch("app.services.illustration.nanobanana.asyncio.sleep", new_callable=AsyncMock):
                        result = await provider.generate_image(
                            prompt="Test prompt",
                            art_style="test style",
                        )

                assert isinstance(result, bytes)
                assert len(result) > 0
                assert call_idx[0] == 3  # 2 timeouts + 1 success


@pytest.mark.asyncio
async def test_nanobanana_fails_after_max_attempts():
    """NanoBanana2Provider should fail after exhausting all retry attempts"""
    import asyncio

    mock_model = MagicMock()
    mock_model.generate_content = MagicMock(return_value=MagicMock(parts=[]))

    with patch("app.services.illustration.nanobanana.genai.configure"):
        with patch("app.services.illustration.nanobanana.genai.GenerativeModel", return_value=mock_model):
            provider = NanoBanana2Provider(api_key="test-key")

            # Mock wait_for to always timeout
            async def always_timeout(coro, timeout):
                # Cancel the awaitable properly (Future vs coroutine)
                if hasattr(coro, 'close'):
                    coro.close()
                elif hasattr(coro, 'cancel'):
                    coro.cancel()
                raise asyncio.TimeoutError()

            with patch("app.services.illustration.nanobanana.asyncio.wait_for", side_effect=always_timeout):
                with patch("app.services.illustration.nanobanana.asyncio.sleep", new_callable=AsyncMock):
                    with pytest.raises(asyncio.TimeoutError):
                        await provider.generate_image(
                            prompt="Test prompt",
                            art_style="test style",
                        )


@pytest.mark.asyncio
async def test_nanobanana_auth_error_not_retried():
    """NanoBanana2Provider should NOT retry auth/quota errors"""
    mock_model = MagicMock()
    mock_model.generate_content = MagicMock(side_effect=Exception("401 Unauthorized"))

    with patch("app.services.illustration.nanobanana.genai.configure"):
        with patch("app.services.illustration.nanobanana.genai.GenerativeModel", return_value=mock_model):
            provider = NanoBanana2Provider(api_key="test-key")

            with pytest.raises(Exception, match="401 Unauthorized"):
                await provider.generate_image(
                    prompt="Test prompt",
                    art_style="test style",
                )

            # Should have been called only once (no retry)
            assert mock_model.generate_content.call_count == 1


def test_provider_factory_returns_nanobanana():
    """Factory should return NanoBanana2Provider when configured"""
    with patch.dict("os.environ", {"ILLUSTRATION_PROVIDER": "nanobanana2", "GOOGLE_API_KEY": "test-key"}):
        with patch("app.services.illustration.nanobanana.genai.configure"):
            with patch("app.services.illustration.nanobanana.genai.GenerativeModel"):
                provider = get_illustration_provider()
                assert isinstance(provider, NanoBanana2Provider)


def test_provider_factory_raises_on_missing_api_key():
    """Factory should raise error if API key missing"""
    with patch.dict("os.environ", {"ILLUSTRATION_PROVIDER": "nanobanana2", "GOOGLE_API_KEY": ""}):
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            get_illustration_provider()


def test_provider_factory_raises_on_unknown_provider():
    """Factory should raise error for unknown provider"""
    with patch.dict("os.environ", {"ILLUSTRATION_PROVIDER": "unknown", "GOOGLE_API_KEY": "test"}):
        with pytest.raises(ValueError, match="Unknown illustration provider"):
            get_illustration_provider()


def test_provider_get_info():
    """Provider should return metadata"""
    with patch("app.services.illustration.nanobanana.genai.configure"):
        with patch("app.services.illustration.nanobanana.genai.GenerativeModel"):
            provider = NanoBanana2Provider(api_key="test-key")
            info = provider.get_provider_info()
            
            assert "name" in info
            assert "provider" in info
            assert "model" in info
            assert info["name"] == "NanoBanana 2"


def test_save_illustration_creates_file():
    """save_illustration should write image bytes to filesystem"""
    test_dir = Path(tempfile.mkdtemp())
    
    try:
        # Mock settings.storage_path
        with patch("app.utils.storage.settings") as mock_settings:
            mock_settings.storage_path = test_dir
            
            image_bytes = b"fake-png-data"
            path = save_illustration("test-story-123", 0, image_bytes)
            
            # Verify file created
            assert Path(path).exists()
            assert Path(path).read_bytes() == image_bytes
            assert "scene_0.png" in path
    
    finally:
        shutil.rmtree(test_dir)


def test_get_illustration_url():
    """get_illustration_url should return correct URL format"""
    url = get_illustration_url("test-story-456", 2)
    assert url == "/storage/stories/test-story-456/scene_2.png"


def test_delete_story_illustrations():
    """delete_story_illustrations should remove all scene images"""
    test_dir = Path(tempfile.mkdtemp())
    
    try:
        with patch("app.utils.storage.settings") as mock_settings:
            mock_settings.storage_path = test_dir
            
            # Create test illustrations
            story_id = "test-story-789"
            save_illustration(story_id, 0, b"scene0")
            save_illustration(story_id, 1, b"scene1")
            save_illustration(story_id, 2, b"scene2")
            
            # Delete them
            deleted_count = delete_story_illustrations(story_id)
            
            assert deleted_count == 3
            # Verify files are gone
            story_dir = test_dir / "stories" / story_id
            assert len(list(story_dir.glob("scene_*.png"))) == 0
    
    finally:
        shutil.rmtree(test_dir)


def test_illustration_exists():
    """illustration_exists should check if file exists"""
    test_dir = Path(tempfile.mkdtemp())
    
    try:
        with patch("app.utils.storage.settings") as mock_settings:
            mock_settings.storage_path = test_dir
            
            story_id = "test-story-exists"
            
            # Before creating
            assert illustration_exists(story_id, 0) is False
            
            # After creating
            save_illustration(story_id, 0, b"test")
            assert illustration_exists(story_id, 0) is True
            
            # Non-existent scene
            assert illustration_exists(story_id, 99) is False
    
    finally:
        shutil.rmtree(test_dir)
