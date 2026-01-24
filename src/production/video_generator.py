"""Video Generator using Google Veo 3.

Generates video clips from text prompts using the Veo 3 API.
Handles async operations and multiple segment generation.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import List, Literal, Optional
from uuid import uuid4

# Fix for nested event loops (allows async calls from sync contexts)
import nest_asyncio
nest_asyncio.apply()

from google import genai
from google.genai import types

from ..config import settings

logger = logging.getLogger(__name__)


class VideoGenerator:
    """Generates video clips using Google Veo 3.
    
    Veo 3 generates short clips (4-8 seconds) that can be
    stitched together for longer videos.
    """
    
    # Veo 3 model name
    MODEL_NAME = "veo-3.0-generate-preview"
    
    # Supported durations
    SUPPORTED_DURATIONS = [4, 6, 8]
    
    # Polling configuration
    POLL_INTERVAL = 5  # seconds
    MAX_POLL_TIME = 600  # 10 minutes max wait
    
    async def _init_client(self):
        """Initialize the Gemini client (async safe)."""
        if settings.google_cloud_project:
             self._client = genai.Client(
                vertexai=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location
            )
        else:
            self._client = genai.Client(api_key=settings.google_api_key)
            
    def __init__(self):
        """Initialize the video generator.
        
        Note: Client initialization is handled lazily or needs to be careful about async context.
        For now doing synchronous init as the client creation is lightweight.
        """
        if settings.google_cloud_project:
             self._client = genai.Client(
                vertexai=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location
            )
        else:
            self._client = genai.Client(api_key=settings.google_api_key)
            
        logger.info(f"Video generator initialized with model {self.MODEL_NAME}")
    
    async def generate_clip(
        self,
        prompt: str,
        duration: Literal[4, 6, 8] = 8,
        aspect_ratio: Literal["9:16", "16:9"] = "9:16",
        output_dir: Optional[Path] = None,
        generate_audio: bool = False,
    ) -> Optional[Path]:
        """Generate a single video clip.
        
        Args:
            prompt: Detailed prompt for the video
            duration: Duration in seconds (4, 6, or 8)
            aspect_ratio: Video aspect ratio
            output_dir: Directory to save the video
            generate_audio: Whether to generate audio with the video
            
        Returns:
            Path to the generated video, or None if failed
        """
        if duration not in self.SUPPORTED_DURATIONS:
            logger.warning(f"Duration {duration} not supported, using 8 seconds")
            duration = 8
        
        output_dir = output_dir or settings.video_clips_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating video clip: {prompt[:50]}...")
        
        try:
            # Submit video generation request
            # generateAudio is REQUIRED for Veo 3 models
            operation = self._client.models.generate_videos(
                model=self.MODEL_NAME,
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio=aspect_ratio,
                    duration_seconds=duration,
                    number_of_videos=1,
                    generate_audio=generate_audio,
                ),
            )
            
            logger.info(f"Video generation submitted, operation: {operation.name if hasattr(operation, 'name') else 'unknown'}")
            
            # Poll for completion using client.operations.get()
            video_path = await self._poll_for_completion(operation, output_dir)
            
            return video_path
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def _poll_for_completion(
        self,
        operation,
        output_dir: Path,
    ) -> Optional[Path]:
        """Poll for video generation completion using the correct SDK pattern.
        
        Args:
            operation: The GenerateVideosOperation to poll
            output_dir: Directory to save the video
            
        Returns:
            Path to the generated video, or None if failed
        """
        start_time = time.time()
        poll_count = 0
        
        while time.time() - start_time < self.MAX_POLL_TIME:
            poll_count += 1
            
            try:
                # Check if operation is done
                if hasattr(operation, 'done') and operation.done:
                    logger.info(f"Video generation completed after {poll_count} polls")
                    
                    # Get the result
                    result = operation.result if not callable(operation.result) else operation.result
                    
                    if result and hasattr(result, 'generated_videos') and result.generated_videos:
                        video = result.generated_videos[0]
                        video_path = output_dir / f"clip_{uuid4().hex[:8]}.mp4"
                        
                        # The video object has 'uri' and 'video_bytes' attributes directly
                        # Check for GCS URI first, then raw bytes
                        if hasattr(video, 'uri') and video.uri:
                            # Download from GCS
                            logger.info(f"Downloading video from GCS: {video.uri}")
                            video_path = await self._download_from_gcs(video.uri, video_path)
                        elif hasattr(video, 'video_bytes') and video.video_bytes:
                            # Save raw bytes
                            with open(video_path, "wb") as f:
                                f.write(video.video_bytes)
                            logger.info(f"Video saved to {video_path} from raw bytes")
                        elif hasattr(video, 'video') and video.video:
                            # Fallback: check nested video object
                            if hasattr(video.video, 'uri') and video.video.uri:
                                logger.info(f"Downloading video from nested GCS: {video.video.uri}")
                                video_path = await self._download_from_gcs(video.video.uri, video_path)
                            elif hasattr(video.video, 'video_bytes') and video.video.video_bytes:
                                with open(video_path, "wb") as f:
                                    f.write(video.video.video_bytes)
                                logger.info(f"Video saved to {video_path}")
                            else:
                                logger.error(f"Nested video object has no uri or video_bytes: {dir(video.video)}")
                                return None
                        else:
                            logger.error(f"Video object has no recognized video data. Available attrs: {[a for a in dir(video) if not a.startswith('_')]}")
                            return None
                        
                        return video_path
                        
                        return video_path
                    else:
                        logger.warning(f"Generation completed but no videos returned. Result: {result}")
                        return None
                
                # Not done yet - poll for updated operation status
                logger.debug(f"Poll {poll_count}: Video generation in progress...")
                
                # Use client.operations.get() to poll for updated status
                operation = self._client.operations.get(operation)
                
                # Wait before polling again
                await asyncio.sleep(self.POLL_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error polling for completion: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return None
        
        logger.error(f"Video generation timed out after {self.MAX_POLL_TIME}s ({poll_count} polls)")
        return None
    
    async def _download_from_gcs(self, gcs_uri: str, local_path: Path) -> Optional[Path]:
        """Download a video from Google Cloud Storage.
        
        Args:
            gcs_uri: GCS URI (gs://bucket/path)
            local_path: Local path to save the file
            
        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            from google.cloud import storage
            
            # Parse GCS URI
            # Format: gs://bucket-name/path/to/file
            gcs_uri = gcs_uri.replace("gs://", "")
            bucket_name = gcs_uri.split("/")[0]
            blob_path = "/".join(gcs_uri.split("/")[1:])
            
            # Download the file
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.download_to_filename(str(local_path))
            
            logger.info(f"Downloaded video to {local_path}")
            return local_path
            
        except ImportError:
            logger.error("google-cloud-storage not installed. Run: pip install google-cloud-storage")
            return None
        except Exception as e:
            logger.error(f"Failed to download from GCS: {e}")
            return None
    
    def generate_clip_sync(
        self,
        prompt: str,
        duration: Literal[4, 6, 8] = 8,
        aspect_ratio: Literal["9:16", "16:9"] = "9:16",
        output_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """Synchronous wrapper for generate_clip.
        
        Args:
            prompt: Detailed prompt for the video
            duration: Duration in seconds (4, 6, or 8)
            aspect_ratio: Video aspect ratio
            output_dir: Directory to save the video
            
        Returns:
            Path to the generated video, or None if failed
        """
        # nest_asyncio.apply() allows asyncio.run() even with existing event loops
        return asyncio.run(self.generate_clip(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            output_dir=output_dir,
        ))
    
    async def generate_multiple_clips(
        self,
        prompts: List[str],
        durations: Optional[List[int]] = None,
        aspect_ratio: Literal["9:16", "16:9"] = "9:16",
        output_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Generate multiple video clips concurrently.
        
        Args:
            prompts: List of prompts for each clip
            durations: List of durations (defaults to 8s each)
            aspect_ratio: Video aspect ratio
            output_dir: Directory to save videos
            
        Returns:
            List of paths to generated videos
        """
        output_dir = output_dir or settings.video_clips_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default durations
        if durations is None:
            durations = [8] * len(prompts)
        
        logger.info(f"Generating {len(prompts)} video clips...")
        
        # Generate all clips concurrently
        tasks = [
            self.generate_clip(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                output_dir=output_dir,
            )
            for prompt, duration in zip(prompts, durations)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Filter out None results
        videos = [r for r in results if r is not None]
        
        logger.info(f"Successfully generated {len(videos)}/{len(prompts)} clips")
        return videos
    
    def generate_multiple_clips_sync(
        self,
        prompts: List[str],
        durations: Optional[List[int]] = None,
        aspect_ratio: Literal["9:16", "16:9"] = "9:16",
        output_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Synchronous wrapper for generate_multiple_clips.
        
        Args:
            prompts: List of prompts for each clip
            durations: List of durations
            aspect_ratio: Video aspect ratio
            output_dir: Directory to save videos
            
        Returns:
            List of paths to generated videos
        """
        # nest_asyncio.apply() allows asyncio.run() even with existing event loops
        return asyncio.run(self.generate_multiple_clips(
            prompts=prompts,
            durations=durations,
            aspect_ratio=aspect_ratio,
            output_dir=output_dir,
        ))
    
    def generate_looping_background(
        self,
        concept: str,
        duration: int = 8,
        aspect_ratio: Literal["9:16", "16:9"] = "9:16",
        output_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """Generate a seamless looping background video.
        
        Useful as an alternative to multiple clips - play a looping
        background while audio narration runs.
        
        Args:
            concept: Type of background (data_flow, neural_pulses, etc.)
            duration: Duration in seconds
            aspect_ratio: Video aspect ratio
            output_dir: Directory to save video
            
        Returns:
            Path to the generated video, or None if failed
        """
        from ..agents.video_prompt_engineer import LoopingBackgroundPromptGenerator
        
        prompt = LoopingBackgroundPromptGenerator.get_looping_prompt(concept)
        
        return self.generate_clip_sync(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            output_dir=output_dir,
        )
