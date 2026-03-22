"""
Abstract base class for illustration providers
"""
from abc import ABC, abstractmethod
from typing import Optional


class IllustrationProvider(ABC):
    """
    Abstract base class for image generation providers.
    
    Allows easy swapping between providers (NanoBanana, DALL-E, Flux, etc.)
    """
    
    @abstractmethod
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
        Generate an image and return raw bytes.
        
        Args:
            prompt: Text description of the image to generate
            art_style: Style prompt suffix (e.g., "watercolor painting, children's book")
            reference_image_url: Optional reference image for consistency (image-to-image)
            aspect_ratio: Image aspect ratio (e.g., "4:3", "16:9", "1:1")
            resolution: Image resolution (e.g., "1K", "2K", "4K")
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Raw image bytes (PNG format)
            
        Raises:
            Exception: If image generation fails
        """
        pass
    
    @abstractmethod
    def get_provider_info(self) -> dict:
        """
        Get provider metadata (name, model, version, etc.)
        
        Returns:
            dict with provider information
        """
        pass
