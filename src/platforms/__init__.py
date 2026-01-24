"""Platforms Package - Integration with social media platforms."""

from .youtube_client import YouTubeClient
from .instagram_client import InstagramClient

__all__ = [
    "YouTubeClient",
    "InstagramClient",
]
