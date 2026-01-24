"""Test YouTube-Only Pipeline.

This script tests the full content generation pipeline with YouTube only,
skipping Instagram publishing.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.orchestrator import Orchestrator
from src.production.tts_service import TTSService
from src.production.video_composer import VideoComposer
from src.platforms.youtube_client import YouTubeClient


def test_content_generation(topic: str = "Neural Networks"):
    """Test content generation (script + video prompts) without video production."""
    print(f"\n{'='*60}")
    print(f"🎬 Testing Content Generation for: {topic}")
    print(f"{'='*60}\n")
    
    orchestrator = Orchestrator()
    result = orchestrator.run_daily_pipeline(topic=topic, dry_run=True)
    
    if result.success:
        print("\n✅ Content generation successful!")
        print(f"   Lesson: {result.lesson.subtopic}")
        print(f"   Script words: {result.lesson.word_count}")
        print(f"   Estimated duration: {result.lesson.estimated_duration:.0f}s")
        print(f"   Video segments: {len(result.lesson.video_prompts)}")
        
        print("\n📝 Clean Script (what TTS will speak):")
        print("-" * 40)
        print(result.lesson.clean_script)
        print("-" * 40)
        
        print("\n🎥 Video Prompts for Veo 3:")
        for i, prompt in enumerate(result.lesson.video_prompts[:3], 1):
            print(f"   Segment {i}: {prompt[:80]}...")
        
        return result.lesson
    else:
        print(f"\n❌ Content generation failed: {result.error}")
        return None


def test_tts(script: str):
    """Test text-to-speech generation."""
    print(f"\n{'='*60}")
    print("🔊 Testing Text-to-Speech")
    print(f"{'='*60}\n")
    
    tts = TTSService.create()
    output_path = Path("output/audio/test_audio.mp3")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Using TTS provider: {type(tts).__name__}")
    print(f"Script length: {len(script)} characters")
    
    try:
        result_path = tts.synthesize(script, output_path)
        duration = tts.get_audio_duration(result_path)
        
        print(f"\n✅ Audio generated!")
        print(f"   Path: {result_path}")
        print(f"   Duration: {duration:.1f} seconds")
        
        return result_path
    except Exception as e:
        print(f"\n❌ TTS failed: {e}")
        return None


def test_youtube_auth():
    """Test YouTube authentication."""
    print(f"\n{'='*60}")
    print("📺 Testing YouTube Authentication")
    print(f"{'='*60}\n")
    
    credentials_file = os.getenv("YOUTUBE_CREDENTIALS_FILE", "youtube_credentials.json")
    
    if not Path(credentials_file).exists():
        print(f"❌ YouTube credentials not found: {credentials_file}")
        print("   Run: python setup_youtube_oauth.py")
        return False
    
    try:
        client = YouTubeClient()
        print("✅ YouTube API authenticated successfully!")
        return True
    except Exception as e:
        print(f"❌ YouTube auth failed: {e}")
        return False


def main():
    """Run the YouTube-only test pipeline."""
    print("\n" + "=" * 60)
    print("   AI Education Engine - YouTube Test Pipeline")
    print("=" * 60)
    
    # Step 1: Test content generation
    lesson = test_content_generation("What is Machine Learning")
    
    if not lesson:
        return
    
    # Step 2: Test TTS
    audio_path = test_tts(lesson.clean_script)
    
    # Step 3: Test YouTube auth
    youtube_ready = test_youtube_auth()
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Summary")
    print(f"{'='*60}")
    print(f"   Content Generation: {'✅' if lesson else '❌'}")
    print(f"   TTS Audio: {'✅' if audio_path else '❌'}")
    print(f"   YouTube Auth: {'✅' if youtube_ready else '❌'}")
    
    if lesson and audio_path and youtube_ready:
        print("\n🎉 All systems ready! You can run the full pipeline.")
        print("   Next: python -m src.main run --topic 'Your Topic'")
    else:
        print("\n⚠️  Some components need attention before full pipeline.")


if __name__ == "__main__":
    main()
