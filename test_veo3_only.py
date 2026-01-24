"""Test Veo 3 Video Generation with Fixed SDK Pattern.

Standalone test with 2 video clips and 10-minute timeout.
Uses the correct SDK polling pattern: client.operations.get()
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.production.video_generator import VideoGenerator
from src.config import settings
import logging

# Enable verbose logging (DEBUG level to see polling messages)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test prompts (short, simple prompts for faster generation)
TEST_PROMPTS = [
    "Abstract glowing neural network with colorful nodes pulsing with energy, dark background, vertical format, cinematic quality, smooth animation.",
    "Floating 3D data points connecting with glowing lines forming a pattern, neon colors on black background, vertical format, smooth camera movement.",
]


def main():
    """Test video generation with 2 clips."""
    print("\n" + "=" * 60)
    print("   🎥 VEO 3 VIDEO GENERATION TEST (FIXED SDK)")
    print("=" * 60)
    print(f"\n📊 Test Configuration:")
    print(f"   - Number of clips: {len(TEST_PROMPTS)}")
    print(f"   - Max wait time: 10 minutes per clip")
    print(f"   - Output directory: {settings.video_clips_dir}")
    print(f"   - Using correct SDK polling: client.operations.get()")
    
    print("\n⏳ Starting video generation (this may take 5-10 minutes per clip)...")
    
    try:
        generator = VideoGenerator()
        
        # Generate clips one at a time for testing
        results = []
        for i, prompt in enumerate(TEST_PROMPTS, 1):
            print(f"\n📽️  Generating clip {i}/{len(TEST_PROMPTS)}...")
            print(f"   Prompt: {prompt[:60]}...")
            
            video_path = generator.generate_clip_sync(
                prompt=prompt,
                duration=6,  # Use 6 seconds for faster testing
                aspect_ratio="9:16",  # Vertical for Shorts/Reels
            )
            
            if video_path:
                print(f"   ✅ Video saved: {video_path}")
                results.append(video_path)
            else:
                print(f"   ❌ Video generation failed or timed out")
        
        # Summary
        print("\n" + "=" * 60)
        print("   📊 RESULTS SUMMARY")
        print("=" * 60)
        print(f"   Generated: {len(results)}/{len(TEST_PROMPTS)} clips")
        
        if results:
            print("\n   📁 Generated Files:")
            for path in results:
                print(f"      - {path}")
            print("\n🎉 Video generation test PASSED!")
        else:
            print("\n⚠️  No videos were generated.")
            print("   Check the debug logs above for details.")
    
    except Exception as e:
        logger.exception(f"Test failed: {e}")
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
