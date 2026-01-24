"""Display Generated Metadata - Direct Access Version.

Retrieves and displays the full generated metadata from the last pipeline run.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.rag.memory_store import MemoryStore
from src.agents.orchestrator import Orchestrator
from src.agents.metadata_optimizer import MetadataOptimizerAgent


def main():
    """Display metadata by running the optimizer directly."""
    print("\n" + "=" * 70)
    print("   📊 GENERATING & DISPLAYING FULL METADATA")
    print("=" * 70)
    
    memory = MemoryStore()
    optimizer = MetadataOptimizerAgent(memory=memory)
    
    # Generate fresh metadata for demo
    print("\n🔄 Generating optimized metadata for 'What is AI' lesson...\n")
    
    metadata = optimizer.optimize_metadata(
        topic="Artificial Intelligence",
        subtopic="What is AI and how does it learn?",
        script_summary="AI learns by looking at examples and finding patterns, just like how you learn to recognize animals by seeing many pictures of them.",
        lesson_number=1,
    )
    
    # Display YouTube Metadata
    print("=" * 70)
    print("📺 YOUTUBE METADATA")
    print("=" * 70)
    
    print(f"\n🎬 Title:")
    print(f"   {metadata.youtube_title}")
    
    print(f"\n📝 Description:")
    print("-" * 60)
    print(metadata.youtube_description)
    print("-" * 60)
    
    print(f"\n🏷️  Hashtags ({len(metadata.youtube_hashtags)}):")
    print(f"   {' '.join(f'#{tag}' for tag in metadata.youtube_hashtags)}")
    
    # Display Instagram Metadata
    print("\n" + "=" * 70)
    print("📸 INSTAGRAM METADATA")
    print("=" * 70)
    
    print(f"\n✨ Caption Title:")
    print(f"   {metadata.instagram_caption_title}")
    
    print(f"\n📝 Full Caption:")
    print("-" * 60)
    print(metadata.instagram_caption)
    print("-" * 60)
    
    print(f"\n🏷️  Hashtags ({len(metadata.instagram_hashtags)}):")
    # Display in groups of 5
    for i in range(0, len(metadata.instagram_hashtags), 5):
        row = metadata.instagram_hashtags[i:i+5]
        print(f"   {' '.join(f'#{tag}' for tag in row)}")
    
    # Display SEO & Engagement
    print("\n" + "=" * 70)
    print("🎯 SEO & ENGAGEMENT")
    print("=" * 70)
    
    print(f"\n🔑 Primary Keywords:")
    print(f"   {', '.join(metadata.primary_keywords)}")
    
    print(f"\n❓ Engagement Hook Question:")
    print(f"   {metadata.hook_question}")
    
    print(f"\n📣 Call to Action:")
    print(f"   {metadata.call_to_action}")
    
    print("\n" + "=" * 70)
    print("✅ Metadata optimization complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
