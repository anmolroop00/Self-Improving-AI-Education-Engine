"""YouTube Client wrapper for Data API v3.

Handles:
- Authentication (OAuth 2.0) with automatic token refresh
- Video uploading
- Analytics retrieval
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from ..config import settings
from ..rag.schemas import Platform, VideoPerformance

logger = logging.getLogger(__name__)


class YouTubeClient:
    """Client for interacting with YouTube Data API."""
    
    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ]
    
    def __init__(self):
        """Initialize YouTube client."""
        self._youtube = None
        self._analytics = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with YouTube API.
        
        Uses stored credentials with automatic refresh. Only opens browser
        for first-time authorization or if refresh token is revoked.
        """
        try:
            creds = None
            creds_path = Path(settings.youtube_credentials_file)
            
            # Try to load existing credentials
            if creds_path.exists():
                logger.info("Loading existing YouTube credentials...")
                creds = Credentials.from_authorized_user_file(str(creds_path), self.SCOPES)
            
            # Check if credentials need refresh or new login
            if creds and creds.expired and creds.refresh_token:
                # Token expired but we have refresh token - refresh silently!
                logger.info("Access token expired, refreshing automatically...")
                try:
                    creds.refresh(Request())
                    logger.info("Token refreshed successfully - no browser needed!")
                    
                    # Save refreshed credentials
                    with open(creds_path, "w") as f:
                        f.write(creds.to_json())
                    logger.info("Refreshed credentials saved")
                    
                except Exception as refresh_error:
                    logger.warning(f"Token refresh failed: {refresh_error}")
                    logger.info("Will need to re-authenticate via browser...")
                    creds = None  # Force new login
            
            elif not creds or not creds.valid:
                # No valid credentials at all - need browser login
                logger.info("No valid credentials found, starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.youtube_client_secrets_file,
                    self.SCOPES
                )
                creds = flow.run_local_server(port=0)
                
                # Save new credentials (includes refresh token)
                with open(creds_path, "w") as f:
                    f.write(creds.to_json())
                logger.info("New credentials saved with refresh token")
            
            else:
                logger.info("Using existing valid credentials")
            
            self._youtube = build("youtube", "v3", credentials=creds)
            self._analytics = build("youtubeAnalytics", "v2", credentials=creds)
            logger.info("YouTube API authenticated successfully")
            
        except Exception as e:
            logger.error(f"YouTube authentication failed: {e}")
            # Don't raise here to allow system to run in dry-run mode
    
    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: List[str],
        privacy_status: str = "private",
    ) -> Optional[str]:
        """Upload a video to YouTube.
        
        Args:
            video_path: Path to video file
            title: Video title (max 100 chars)
            description: Video description
            tags: List of tags
            privacy_status: private, public, or unlisted
            
        Returns:
            Video ID if successful, None otherwise
        """
        if not self._youtube:
            logger.warning("YouTube client not authenticated, skipping upload")
            return None
            
        try:
            logger.info(f"Uploading to YouTube: {title}")
            
            body = {
                "snippet": {
                    "title": title[:100],  # Max 100 chars
                    "description": description,
                    "tags": tags,
                    "categoryId": "27",  # Education
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": True,  # 5-year-old audience
                }
            }
            
            media = MediaFileUpload(
                str(video_path),
                chunksize=-1, 
                resumable=True
            )
            
            request = self._youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Uploaded {int(status.progress() * 100)}%")
            
            video_id = response.get("id")
            logger.info(f"Upload complete! Video ID: {video_id}")
            return video_id
            
        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            return None
            
    def get_video_performance(self, video_id: str) -> Optional[VideoPerformance]:
        """Get analytics for a specific video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            VideoPerformance object or None
        """
        if not self._analytics:
            return None
            
        try:
            # Basic stats from Data API
            stats_response = self._youtube.videos().list(
                part="statistics",
                id=video_id
            ).execute()
            
            if not stats_response.get("items"):
                return None
                
            stats = stats_response["items"][0]["statistics"]
            
            # TODO: Add Analytics API call for demographics and watch time
            # For now returning basic stats
            
            perf = VideoPerformance(
                id=f"yt_{video_id}_{datetime.now().strftime('%Y%m%d')}",
                lesson_id="todo",  # Needs to be linked by caller
                platform=Platform.YOUTUBE,
                platform_video_id=video_id,
                views=int(stats.get("viewCount", 0)),
                likes=int(stats.get("likeCount", 0)),
                comments=int(stats.get("commentCount", 0)),
                post_time=datetime.now(), # Approximate if unknown
                post_day_of_week=datetime.now().strftime("%A"),
            )
            perf.calculate_engagement_rate()
            
            return perf
            
        except Exception as e:
            logger.error(f"Failed to get YouTube stats: {e}")
            return None
    
    def set_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        """Set custom thumbnail for a video.
        
        Note: Requires verified YouTube account.
        
        Args:
            video_id: YouTube video ID
            thumbnail_path: Path to thumbnail image (JPEG, PNG, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._youtube:
            logger.warning("YouTube client not authenticated, skipping thumbnail")
            return False
            
        try:
            logger.info(f"Setting thumbnail for video {video_id}")
            
            media = MediaFileUpload(
                str(thumbnail_path),
                mimetype="image/png",
                resumable=True
            )
            
            self._youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()
            
            logger.info(f"Thumbnail set successfully for {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set thumbnail: {e}")
            return False
    
    def get_channel_stats(self) -> Dict:
        """Get channel statistics including subscriber count.
        
        Returns:
            Dict with subscribers, total_views, video_count
        """
        if not self._youtube:
            logger.warning("YouTube client not authenticated")
            return {"subscribers": 0, "total_views": 0, "video_count": 0}
        
        try:
            response = self._youtube.channels().list(
                part="statistics",
                mine=True
            ).execute()
            
            if response.get("items"):
                stats = response["items"][0]["statistics"]
                result = {
                    "subscribers": int(stats.get("subscriberCount", 0)),
                    "total_views": int(stats.get("viewCount", 0)),
                    "video_count": int(stats.get("videoCount", 0)),
                    "hidden_subscriber_count": stats.get("hiddenSubscriberCount", False),
                }
                logger.info(f"Channel stats: {result['subscribers']} subscribers")
                return result
                
            return {"subscribers": 0, "total_views": 0, "video_count": 0}
            
        except Exception as e:
            logger.error(f"Failed to get channel stats: {e}")
            return {"subscribers": 0, "total_views": 0, "video_count": 0}
    
    def get_video_analytics(self, video_id: str, days: int = 28) -> Dict:
        """Get detailed analytics for a video using YouTube Analytics API.
        
        Args:
            video_id: YouTube video ID
            days: Number of days to look back (default 28)
            
        Returns:
            Dict with watch_time, avg_view_duration, avg_view_percentage, demographics
        """
        if not self._analytics:
            logger.warning("YouTube Analytics not available")
            return {}
        
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Watch time and retention metrics
            response = self._analytics.reports().query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                metrics="estimatedMinutesWatched,averageViewDuration,averageViewPercentage",
                filters=f"video=={video_id}",
            ).execute()
            
            rows = response.get("rows", [[0, 0, 0]])
            watch_data = rows[0] if rows else [0, 0, 0]
            
            result = {
                "watch_time_minutes": watch_data[0] if len(watch_data) > 0 else 0,
                "avg_view_duration_seconds": watch_data[1] if len(watch_data) > 1 else 0,
                "avg_view_percentage": watch_data[2] if len(watch_data) > 2 else 0,
            }
            
            # Demographics (ageGroup, gender) - separate query
            try:
                demo_response = self._analytics.reports().query(
                    ids="channel==MINE",
                    startDate=start_date,
                    endDate=end_date,
                    metrics="views",
                    dimensions="ageGroup,gender",
                    filters=f"video=={video_id}",
                ).execute()
                result["demographics"] = demo_response.get("rows", [])
            except Exception as demo_error:
                logger.debug(f"Demographics not available: {demo_error}")
                result["demographics"] = []
            
            logger.info(f"Video {video_id} analytics: {result['watch_time_minutes']:.1f} min watched")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get video analytics: {e}")
            return {}

