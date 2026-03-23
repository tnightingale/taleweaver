"""
NanoBanana 2 (Google Gemini 3.1 Flash Image) provider implementation
"""
import logging
import os
from typing import Optional
from io import BytesIO
import base64

import google.generativeai as genai
from PIL import Image

from app.services.illustration.base import IllustrationProvider

logger = logging.getLogger(__name__)


class NanoBanana2Provider(IllustrationProvider):
    """
    NanoBanana 2 illustration provider using Google's Gemini 3.1 Flash Image model.
    
    Uses google-generativeai Python client for image generation.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize NanoBanana 2 provider.
        
        Args:
            api_key: Google AI API key (defaults to GOOGLE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        # Configure genai
        genai.configure(api_key=self.api_key)
        self.model_id = "gemini-3.1-flash-image-preview"
        self.model = genai.GenerativeModel(model_name=self.model_id)
        
        logger.info(f"NanoBanana2Provider initialized with model: {self.model_id}")
    
    async def generate_image(
        self,
        prompt: str,
        art_style: str,
        reference_image_url: Optional[str] = None,
        aspect_ratio: str = "4:3",
        resolution: str = "2K",
        **kwargs
    ) -> bytes:
        """
        Generate image using NanoBanana 2 (Gemini 3.1 Flash Image).
        
        Args:
            prompt: Scene description
            art_style: Style prompt to append
            reference_image_url: Optional reference for consistency (image-to-image)
            aspect_ratio: "1:1", "4:3", "16:9", etc.
            resolution: "1K", "2K", or "4K"
            
        Returns:
            Raw PNG image bytes
        """
        # Combine prompt with art style
        full_prompt = f"{prompt}, {art_style}" if art_style else prompt
        
        logger.info(f"🎨 Generating image with NanoBanana 2 (aspect_ratio={aspect_ratio})")
        logger.debug(f"   Prompt: {full_prompt[:200]}...")
        if reference_image_url:
            logger.debug(f"   Reference image: {reference_image_url}")
        
        import asyncio

        IMAGE_TIMEOUT = 60  # seconds per API call
        MAX_ATTEMPTS = 2    # retry once on "no image" response

        try:
            generation_config = {}

            if reference_image_url:
                logger.warning("Reference image support not yet implemented, using text-to-image")

            for attempt in range(MAX_ATTEMPTS):
                # Timeout prevents hanging indefinitely on slow/unresponsive API
                response = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.model.generate_content(
                            full_prompt,
                            generation_config=generation_config
                        )
                    ),
                    timeout=IMAGE_TIMEOUT,
                )

                # Extract image from response
                if hasattr(response, 'parts'):
                    for part in response.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            image_data = part.inline_data.data

                            if isinstance(image_data, str):
                                image_bytes = base64.b64decode(image_data)
                            else:
                                image_bytes = image_data

                            try:
                                img = Image.open(BytesIO(image_bytes))
                                img_byte_arr = BytesIO()
                                img.save(img_byte_arr, format='PNG')
                                png_bytes = img_byte_arr.getvalue()
                                logger.info(f"Image generated successfully ({len(png_bytes)} bytes)")
                                return png_bytes
                            except Exception:
                                logger.info(f"Image generated successfully ({len(image_bytes)} bytes)")
                                return image_bytes

                # No image in response — retry if we have attempts left
                if attempt < MAX_ATTEMPTS - 1:
                    logger.warning(f"No image in Gemini response (attempt {attempt + 1}/{MAX_ATTEMPTS}), retrying...")
                    continue

            raise Exception(f"No image found in Gemini response after {MAX_ATTEMPTS} attempts")

        except asyncio.TimeoutError:
            logger.error(f"Gemini API call timed out after {IMAGE_TIMEOUT}s")
            raise

        except Exception as e:
            # Enhanced error logging for debugging
            logger.exception(f"❌ NanoBanana 2 image generation failed")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Error message: {str(e)}")
            logger.error(f"   Prompt length: {len(full_prompt)} chars")
            logger.error(f"   Model: {self.model_id}")
            if reference_image_url:
                logger.error(f"   Reference image: {reference_image_url}")
            
            # Check for specific error types
            error_msg = str(e).lower()
            if "quota" in error_msg or "limit exceeded" in error_msg:
                logger.error(f"   🔴 QUOTA ERROR - Google Gemini quota exceeded")
            elif "429" in error_msg or "rate limit" in error_msg:
                logger.error(f"   🔴 RATE LIMIT - Too many requests to Google API")
            elif "401" in error_msg or "403" in error_msg or "auth" in error_msg:
                logger.error(f"   🔴 AUTH ERROR - Check GOOGLE_API_KEY environment variable")
            
            raise  # Re-raise with context
    
    def get_provider_info(self) -> dict:
        """Get provider metadata"""
        return {
            "name": "NanoBanana 2",
            "provider": "Google Gemini",
            "model": self.model_id,
            "version": "3.1-flash-image-preview"
        }
