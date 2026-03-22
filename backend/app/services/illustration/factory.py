"""
Factory for creating illustration providers
"""
import os
import logging

from app.services.illustration.base import IllustrationProvider
from app.services.illustration.nanobanana import NanoBanana2Provider

logger = logging.getLogger(__name__)


def get_illustration_provider() -> IllustrationProvider:
    """
    Get configured illustration provider based on environment variables.
    
    Returns:
        IllustrationProvider instance
        
    Raises:
        ValueError: If provider is unknown or not configured
    """
    provider_name = os.getenv("ILLUSTRATION_PROVIDER", "nanobanana2").lower()
    
    logger.info(f"Creating illustration provider: {provider_name}")
    
    if provider_name == "nanobanana2":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable required for NanoBanana 2")
        return NanoBanana2Provider(api_key=api_key)
    
    elif provider_name == "none" or provider_name == "":
        raise ValueError("Illustration provider disabled (ILLUSTRATION_PROVIDER=none)")
    
    else:
        raise ValueError(f"Unknown illustration provider: {provider_name}")
