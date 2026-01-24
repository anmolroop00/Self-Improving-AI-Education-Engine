"""Video Composer using MoviePy.

Responsible for:
- Stitching multiple video clips together
- Synchronizing video with generated audio
- Adding looping backgrounds if needed
- Exporting in final platform-specific formats
"""

import logging
from pathlib import Path
from typing import List, Optional

# MoviePy v2.x compatibility
try:
    from moviepy import AudioFileClip, VideoFileClip, concatenate_videoclips
except ImportError:
    from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips

from ..config import settings

logger = logging.getLogger(__name__)


class VideoComposer:
    """Composes final videos by combining clips and audio.
    
    Handles:
    - Audio-video synchronization
    - Looping background logic (if clips are short)
    - Final export settings (resolution, FPS, bitrate)
    """
    
    def __init__(self):
        """Initialize the video composer."""
        self.output_dir = settings.final_output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def compose_video(
        self,
        audio_path: Path,
        video_paths: List[Path],
        output_filename: str,
        fps: int = 30,
        threads: int = 4,
    ) -> Optional[Path]:
        """Compose a final video from audio and video clips.
        
        Stragegy:
        1. Load audio and determine duration
        2. Load video clips
        3. Loop/repeat video clips to match audio duration
        4. Combine and export
        
        Args:
            audio_path: Path to the TTS audio file
            video_paths: List of paths to generated video clips
            output_filename: Name of the output file
            fps: Frames per second
            threads: Number of threads for rendering
            
        Returns:
            Path to the final exported video, or None if failed
        """
        try:
            logger.info(f"Composing video: {output_filename}")
            
            # Load audio
            audio_clip = AudioFileClip(str(audio_path))
            duration = audio_clip.duration
            logger.info(f"Audio duration: {duration:.2f}s")
            
            # Load video clips
            video_clips = []
            for path in video_paths:
                if path.exists():
                    clip = VideoFileClip(str(path))
                    # Resize if needed (e.g., to 1080x1920 for 9:16)
                    # For now assume Veo 3 output is correct size
                    video_clips.append(clip)
            
            if not video_clips:
                logger.error("No valid video clips found")
                return None
            
            # Determine how to arrange clips
            # Option 1: We have enough clips to cover duration
            # Option 2: We need to loop clips
            
            total_video_duration = sum(c.duration for c in video_clips)
            final_clips = []
            
            if total_video_duration >= duration:
                # We have enough video, just concatenate and trim
                final_clips = video_clips
            else:
                # We need to loop. Strategy: Play all clips in order, then loop the sequence
                logger.info(f"Video duration ({total_video_duration:.2f}s) < Audio ({duration:.2f}s). Looping clips.")
                
                current_duration = 0
                while current_duration < duration:
                    for clip in video_clips:
                        final_clips.append(clip)
                        current_duration += clip.duration
                        if current_duration >= duration:
                            break
            
            # Concatenate all video clips
            final_video = concatenate_videoclips(final_clips, method="compose")
            
            # Trim to exact audio duration (MoviePy v2 uses subclipped, v1 uses subclip)
            try:
                final_video = final_video.subclipped(0, duration)  # MoviePy v2
            except AttributeError:
                final_video = final_video.subclip(0, duration)  # MoviePy v1
            
            # Set audio (MoviePy v2 uses with_audio, v1 uses set_audio)
            try:
                final_video = final_video.with_audio(audio_clip)  # MoviePy v2
            except AttributeError:
                final_video = final_video.set_audio(audio_clip)  # MoviePy v1
            
            # Export
            output_path = self.output_dir / output_filename
            
            logger.info(f"Rendering to {output_path}...")
            final_video.write_videofile(
                str(output_path),
                fps=fps,
                codec="libx264",
                audio_codec="aac",
                threads=threads,
                logger=None,  # Suppress moviepy verbose output
                preset="medium"
            )
            
            # Close clips to release resources
            audio_clip.close()
            for clip in video_clips:
                clip.close()
                
            return output_path
            
        except Exception as e:
            logger.error(f"Video composition failed: {e}")
            return None
    
    def compose_with_looping_background(
        self,
        audio_path: Path,
        background_path: Path,
        output_filename: str,
    ) -> Optional[Path]:
        """Compose video with a single looping background.
        
        Args:
            audio_path: Path to TTS audio
            background_path: Path to background video
            output_filename: output filename
            
        Returns:
            Path to final video
        """
        try:
            logger.info(f"Composing with looping background: {output_filename}")
            
            audio_clip = AudioFileClip(str(audio_path))
            bg_clip = VideoFileClip(str(background_path))
            
            # Loop background to match audio duration
            final_video = bg_clip.loop(duration=audio_clip.duration)
            
            # Set audio (MoviePy v2 uses with_audio, v1 uses set_audio)
            try:
                final_video = final_video.with_audio(audio_clip)  # MoviePy v2
            except AttributeError:
                final_video = final_video.set_audio(audio_clip)  # MoviePy v1
            
            output_path = self.output_dir / output_filename
            
            final_video.write_videofile(
                str(output_path),
                fps=30,
                codec="libx264",
                audio_codec="aac",
                logger=None
            )
            
            audio_clip.close()
            bg_clip.close()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Looping composition failed: {e}")
            return None
