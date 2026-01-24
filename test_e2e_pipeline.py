"""End-to-End Pipeline Test: Compose + Metadata + YouTube Upload.

This script:
1. Composes a final video from existing audio and video files
2. Generates optimized metadata (title, description, hashtags)
3. Uploads to YouTube (as private by default)
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.production.video_composer import VideoComposer
from src.agents.metadata_optimizer import MetadataOptimizerAgent
from src.platforms.youtube_client import YouTubeClient
from src.config import settings
import logging

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Configuration for this test
TEST_CONFIG = {
    "topic": "AI & Machine Learning",
    "subtopic": "How Neural Networks Learn",
    "script_summary": "Neural networks learn by adjusting weights through backpropagation, like a student getting feedback on wrong answers.",
    "lesson_number": 1,
}


def step1_compose_video() -> Path:
    """Step 1: Compose final video from audio + video clips."""
    print("\n" + "=" * 60)
    print("   📹 STEP 1: COMPOSING VIDEO")
    print("=" * 60)
    
    # Use existing files
    audio_dir = Path("output/audio")
    video_dir = Path("output/video")
    
    # Get the first audio file
    audio_files = list(audio_dir.glob("lesson_*.mp3"))
    if not audio_files:
        raise FileNotFoundError("No audio files found in output/audio")
    
    audio_path = audio_files[0]
    print(f"   Audio: {audio_path}")
    
    # Get all video clips
    video_paths = list(video_dir.glob("*.mp4"))
    if not video_paths:
        raise FileNotFoundError("No video clips found in output/video")
    
    print(f"   Videos: {[str(p) for p in video_paths]}")
    
    # Compose the video
    composer = VideoComposer()
    final_video = composer.compose_video(
        audio_path=audio_path,
        video_paths=video_paths,
        output_filename="test_e2e_final.mp4",
        fps=30,
    )
    
    if not final_video:
        raise RuntimeError("Video composition failed")
    
    print(f"\n   ✅ Final video: {final_video}")
    return final_video


def step2_generate_metadata() -> dict:
    """Step 2: Generate optimized metadata with AI."""
    print("\n" + "=" * 60)
    print("   🏷️  STEP 2: GENERATING METADATA")
    print("=" * 60)
    
    optimizer = MetadataOptimizerAgent()
    metadata = optimizer.optimize_metadata(
        topic=TEST_CONFIG["topic"],
        subtopic=TEST_CONFIG["subtopic"],
        script_summary=TEST_CONFIG["script_summary"],
        lesson_number=TEST_CONFIG["lesson_number"],
    )
    
    print(f"\n   📊 Generated Metadata:")
    print(f"   Title: {metadata.youtube_title}")
    print(f"   Description: {metadata.youtube_description[:100]}...")
    print(f"   Hashtags: {metadata.youtube_hashtags[:5]}...")
    print(f"   Hook Question: {metadata.hook_question}")
    print(f"   CTA: {metadata.call_to_action}")
    
    return {
        "title": metadata.youtube_title,
        "description": metadata.youtube_description,
        "tags": metadata.youtube_hashtags,
        "hook": metadata.hook_question,
        "cta": metadata.call_to_action,
    }


def step3_upload_to_youtube(video_path: Path, metadata: dict) -> str:
    """Step 3: Upload to YouTube."""
    print("\n" + "=" * 60)
    print("   📤 STEP 3: UPLOADING TO YOUTUBE")
    print("=" * 60)
    
    # Build full description with hook and CTA
    full_description = f"""{metadata['hook']}

{metadata['description']}

{metadata['cta']}

---
#{' #'.join(metadata['tags'][:15])}
"""
    
    print(f"\n   📝 Upload Details:")
    print(f"   Title: {metadata['title']}")
    print(f"   Video: {video_path}")
    print(f"   Privacy: private (for testing)")
    
    # Initialize YouTube client and upload
    youtube = YouTubeClient()
    video_id = youtube.upload_video(
        video_path=video_path,
        title=metadata['title'],
        description=full_description,
        tags=metadata['tags'][:15],  # YouTube allows ~15 tags
        privacy_status="private",  # Keep private for testing
    )
    
    if not video_id:
        raise RuntimeError("YouTube upload failed - check authentication")
    
    print(f"\n   ✅ Video uploaded!")
    print(f"   Video ID: {video_id}")
    print(f"   URL: https://youtube.com/watch?v={video_id}")
    
    return video_id


def main():
    """Run the complete end-to-end test."""
    print("\n" + "=" * 60)
    print("   🚀 END-TO-END PIPELINE TEST")
    print("=" * 60)
    print(f"\n   Topic: {TEST_CONFIG['topic']}")
    print(f"   Subtopic: {TEST_CONFIG['subtopic']}")
    
    try:
        # Step 1: Compose video
        final_video = step1_compose_video()
        
        # Step 2: Generate metadata
        metadata = step2_generate_metadata()
        
        # Step 3: Upload to YouTube
        video_id = step3_upload_to_youtube(final_video, metadata)
        
        # Summary
        print("\n" + "=" * 60)
        print("   🎉 PIPELINE COMPLETE!")
        print("=" * 60)
        print(f"   Final Video: {final_video}")
        print(f"   YouTube URL: https://youtube.com/watch?v={video_id}")
        print("\n   Next steps:")
        print("   1. Check video at the URL above")
        print("   2. Make it public when ready")
        print("   3. Monitor analytics with get_video_performance()")
        
    except FileNotFoundError as e:
        print(f"\n❌ Missing files: {e}")
        print("   Run test_veo3_only.py first to generate video clips")
        
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
