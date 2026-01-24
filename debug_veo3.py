"""Debug Veo 3 API Response.

Inspect the actual response from Veo 3 API to understand the operation structure.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from google import genai
from google.genai import types
from src.config import settings
import time
import logging

# Enable verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Debug Veo 3 API response structure."""
    print("\n" + "=" * 60)
    print("   🔍 VEO 3 API DEBUG TEST")
    print("=" * 60)
    
    # Initialize client
    if settings.google_cloud_project:
        client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location
        )
    else:
        client = genai.Client(api_key=settings.google_api_key)
    
    print(f"\n📊 Client initialized")
    print(f"   Project: {settings.google_cloud_project}")
    print(f"   Location: {settings.google_cloud_location}")
    
    # Simple test prompt
    prompt = "A glowing blue sphere floating in space, 3D render, cinematic"
    
    print(f"\n📽️  Submitting video request...")
    print(f"   Prompt: {prompt}")
    
    try:
        # Make the API call
        operation = client.models.generate_videos(
            model="veo-3.0-generate-preview",
            prompt=prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio="9:16",
                duration_seconds=6,
                number_of_videos=1,
            ),
        )
        
        print(f"\n✅ API call successful!")
        print(f"\n🔍 Operation object inspection:")
        print(f"   Type: {type(operation)}")
        print(f"   Dir: {[attr for attr in dir(operation) if not attr.startswith('_')]}")
        
        # Check various attributes
        if hasattr(operation, 'name'):
            print(f"   Name: {operation.name}")
        if hasattr(operation, 'done'):
            print(f"   Done: {operation.done}")
        if hasattr(operation, 'result'):
            print(f"   Result type: {type(operation.result)}")
            print(f"   Result callable: {callable(operation.result)}")
        if hasattr(operation, 'metadata'):
            print(f"   Metadata: {operation.metadata}")
        if hasattr(operation, 'operation'):
            print(f"   Inner operation: {operation.operation}")
        
        # Check if it's a direct result
        if hasattr(operation, 'generated_videos'):
            print(f"\n🎥 Direct result - generated_videos: {operation.generated_videos}")
            if operation.generated_videos:
                for i, video in enumerate(operation.generated_videos):
                    print(f"   Video {i}: {video}")
        
        # Try to get the result with timeout
        print(f"\n⏳ Waiting for result (max 2 minutes for testing)...")
        start_time = time.time()
        
        if callable(operation.result):
            try:
                # Try calling with timeout
                result = operation.result(timeout=120)  # 2 minute timeout
                print(f"\n📦 Result received!")
                print(f"   Type: {type(result)}")
                print(f"   Dir: {[attr for attr in dir(result) if not attr.startswith('_')]}")
                
                if hasattr(result, 'generated_videos'):
                    print(f"   Generated videos: {result.generated_videos}")
                    if result.generated_videos:
                        video = result.generated_videos[0]
                        print(f"   First video type: {type(video)}")
                        if hasattr(video, 'video'):
                            print(f"   Video data type: {type(video.video)}")
                            if hasattr(video.video, 'data'):
                                print(f"   Video data length: {len(video.video.data)} bytes")
                                
                                # Save the video!
                                output_path = Path("output/video/debug_test.mp4")
                                output_path.parent.mkdir(parents=True, exist_ok=True)
                                with open(output_path, "wb") as f:
                                    f.write(video.video.data)
                                print(f"\n🎉 VIDEO SAVED: {output_path}")
            except Exception as e:
                print(f"\n❌ Error getting result: {e}")
                print(f"   Time elapsed: {time.time() - start_time:.1f}s")
        else:
            print(f"   Result is not callable: {operation.result}")
            
    except Exception as e:
        logger.exception(f"API call failed: {e}")
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
