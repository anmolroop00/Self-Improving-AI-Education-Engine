"""Instagram Client wrapper for Graph API.

Handles:
- Authentication (Long-lived tokens)
- Reels publishing (2-step container process)
- Insights retrieval
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

from ..config import settings
from ..rag.schemas import Platform, VideoPerformance

logger = logging.getLogger(__name__)


class InstagramClient:
    """Client for interacting with Instagram Graph API."""
    
    BASE_URL = "https://graph.facebook.com/v19.0"
    
    def __init__(self):
        """Initialize Instagram client."""
        self.access_token = settings.instagram_access_token
        self.user_id = settings.instagram_user_id
        
        if not self.access_token or not self.user_id:
            logger.warning("Instagram credentials missing")
    
    def upload_reel(
        self,
        video_url: str,
        caption: str,
        cover_url: Optional[str] = None,
    ) -> Optional[str]:
        """Upload a Reel to Instagram.
        
        Args:
            video_url: Publicly accessible URL of the video (REQUIRED by Graph API)
            caption: Post caption with hashtags
            cover_url: Optional cover image URL
            
        Returns:
            Media ID if successful, None otherwise
        """
        if not self.access_token or not self.user_id:
            return None
            
        try:
            logger.info("Initializing Reel upload session...")
            
            # Step 1: Create Container
            url = f"{self.BASE_URL}/{self.user_id}/media"
            payload = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": self.access_token,
                "share_to_feed": True,
            }
            
            if cover_url:
                payload["cover_url"] = cover_url
                
            response = requests.post(url, data=payload)
            result = response.json()
            
            if "error" in result:
                logger.error(f"Instagram container creation error: {result['error']}")
                return None
                
            container_id = result["id"]
            logger.info(f"Container created: {container_id}")
            
            # Step 2: Check status and wait for upload
            if not self._wait_for_container(container_id):
                return None
            
            # Step 3: Publish container
            logger.info("Publishing Reel...")
            publish_url = f"{self.BASE_URL}/{self.user_id}/media_publish"
            publish_payload = {
                "creation_id": container_id,
                "access_token": self.access_token,
            }
            
            pub_response = requests.post(publish_url, data=publish_payload)
            pub_result = pub_response.json()
            
            if "error" in pub_result:
                logger.error(f"Instagram publish error: {pub_result['error']}")
                return None
                
            media_id = pub_result["id"]
            logger.info(f"Reel published! Media ID: {media_id}")
            return media_id
            
        except Exception as e:
            logger.error(f"Instagram upload failed: {e}")
            return None
    
    def _wait_for_container(self, container_id: str, timeout: int = 300) -> bool:
        """Wait for video container to be ready."""
        url = f"{self.BASE_URL}/{container_id}"
        params = {
            "fields": "status_code,status",
            "access_token": self.access_token
        }
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = requests.get(url, params=params)
            status = response.json()
            
            state = status.get("status_code")
            logger.debug(f"Container status: {state}")
            
            if state == "FINISHED":
                return True
            elif state == "ERROR":
                logger.error("Container processing failed")
                return False
                
            time.sleep(10)
            
        logger.error("Container wait timeout")
        return False
        
    def get_media_insights(self, media_id: str) -> Optional[VideoPerformance]:
        """Get insights for a specific media item.
        
        Args:
            media_id: Instagram media ID
            
        Returns:
            VideoPerformance object
        """
        # Implementation to fetch insights using fields=insights.metric(views,likes,comments)
        # For now, placeholder
        return None
