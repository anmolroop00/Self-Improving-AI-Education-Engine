"""Full Daily Pipeline Test.

This runs the complete end-to-end content production pipeline:
1. Get next lesson from curriculum (RAG memory)
2. Generate script with AI
3. Sanitize script for TTS
4. Generate video prompts
5. Create TTS audio
6. Generate Veo 3 video clips
7. Compose final video (audio + video)
8. Generate optimized metadata
9. Upload to YouTube

This demonstrates the full self-improving AI education engine!
"""

import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.orchestrator import Orchestrator, PipelineResult
from src.rag.memory_store import MemoryStore
from src.rag.schemas import TopicPlan, Platform
from src.platforms.youtube_client import YouTubeClient
from src.agents.metadata_optimizer import MetadataOptimizerAgent
import logging

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def ensure_topic_plan(memory: MemoryStore) -> TopicPlan:
    """Ensure we have an active topic plan."""
    plan = memory.get_active_topic_plan()
    
    if plan and hasattr(plan, 'main_topic'):
        print(f"   Using existing plan: {plan.main_topic}")
        print(f"   Progress: {plan.current_index}/{plan.total_lessons}")
        print(f"   Next lesson: {plan.current_subtopic}")
        return plan
    
    # Create a new topic plan if none exists
    print("   Creating new topic plan...")
    subtopics = [
        "What is Artificial Intelligence?",
        "How Computers Learn from Data",
        "Neural Networks: Digital Brains",
        "Teaching AI to See: Computer Vision",
        "Teaching AI to Talk: Natural Language",
        "AI Making Decisions: Reinforcement Learning",
        "AI Creating Art: Generative Models",
        "AI in Your Pocket: Everyday Applications",
    ]
    
    plan = TopicPlan(
        id=f"plan_{uuid4().hex[:8]}",
        main_topic="Artificial Intelligence for Kids",
        description="Fun and simple AI concepts explained for young learners",
        subtopics=subtopics,
        total_lessons=len(subtopics),
        current_index=0,
    )
    memory.save_topic_plan(plan)
    print(f"   Created: {plan.main_topic} ({plan.total_lessons} lessons)")
    return plan


def run_full_pipeline():
    """Run the complete daily content production pipeline."""
    print("\n" + "=" * 70)
    print("   🚀 FULL DAILY PIPELINE")
    print("   Self-Improving AI Education Engine")
    print("=" * 70)
    print(f"\n   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize memory and orchestrator
        print("\n" + "-" * 70)
        print("   📚 STEP 1: INITIALIZING SYSTEM")
        print("-" * 70)
        
        memory = MemoryStore()
        plan = ensure_topic_plan(memory)
        
        orchestrator = Orchestrator(memory=memory)
        print("   ✅ Orchestrator initialized")
        
        # Run the daily pipeline
        print("\n" + "-" * 70)
        print("   🎬 STEP 2: RUNNING DAILY PIPELINE")
        print("-" * 70)
        print(f"   Topic: {plan.main_topic}")
        print(f"   Subtopic: {plan.current_subtopic}")
        print("\n   ⏳ This will take several minutes...")
        print("   - Script generation (~10s)")
        print("   - TTS audio (~5s)")
        print("   - Veo 3 video generation (~2-3 min per clip)")
        print("   - Video composition (~30s)")
        print("   - Metadata generation (~5s)")
        print("   - YouTube upload (~10s)")
        
        # Run the pipeline (not dry_run to actually produce video)
        result: PipelineResult = orchestrator.run_daily_pipeline(
            topic=None,  # Use current curriculum
            dry_run=False,  # Actually produce the video
        )
        
        # Check results
        print("\n" + "-" * 70)
        print("   📊 STEP 3: PIPELINE RESULTS")
        print("-" * 70)
        
        if result.success:
            print(f"   ✅ SUCCESS!")
            print(f"   Stage reached: {result.stage_reached}")
            
            if result.lesson:
                print(f"\n   📝 Lesson Details:")
                print(f"   - Subtopic: {result.lesson.subtopic}")
                print(f"   - Word count: {result.lesson.word_count}")
                print(f"   - Duration: {result.lesson.estimated_duration:.1f}s")
                
                if result.lesson.youtube_title:
                    print(f"\n   🏷️  Metadata:")
                    print(f"   - Title: {result.lesson.youtube_title}")
                    print(f"   - Hashtags: {result.lesson.youtube_hashtags[:5]}")
            
            if result.final_video_path:
                print(f"\n   🎥 Final Video:")
                print(f"   - Path: {result.final_video_path}")
                
                # Upload to YouTube
                print("\n" + "-" * 70)
                print("   📤 STEP 4: UPLOADING TO YOUTUBE")
                print("-" * 70)
                
                youtube = YouTubeClient()
                
                # Build description
                description = f"""
{result.lesson.youtube_description or 'Learn about AI in this fun video!'}

---
#{' #'.join(result.lesson.youtube_hashtags[:10])}

Made with the Self-Improving AI Education Engine 🤖
"""
                
                video_id = youtube.upload_video(
                    video_path=Path(result.final_video_path),
                    title=result.lesson.youtube_title or f"AI Lesson: {result.lesson.subtopic}",
                    description=description,
                    tags=result.lesson.youtube_hashtags[:15],
                    privacy_status="private",  # Keep private for review
                )
                
                if video_id:
                    print(f"   ✅ Video uploaded!")
                    print(f"   Video ID: {video_id}")
                    print(f"   URL: https://youtube.com/watch?v={video_id}")
                    
                    # Store the video ID in the lesson
                    result.lesson.final_video_path = f"youtube:{video_id}"
                    memory.save_lesson(result.lesson)
                    
                    # Store initial performance record
                    from src.rag.schemas import VideoPerformance
                    perf = VideoPerformance(
                        id=f"perf_{uuid4().hex[:8]}",
                        lesson_id=result.lesson.id,
                        platform=Platform.YOUTUBE,
                        platform_video_id=video_id,
                        views=0,
                        likes=0,
                        comments=0,
                        post_time=datetime.now(),
                        post_day_of_week=datetime.now().strftime("%A"),
                    )
                    memory.save_performance(perf)
                    print("   ✅ Performance tracking initialized")
                else:
                    print("   ⚠️ YouTube upload failed")
            else:
                print("   ⚠️ No final video was produced")
        else:
            print(f"   ❌ Pipeline failed at stage: {result.stage_reached}")
            print(f"   Error: {result.error}")
        
        # Summary
        print("\n" + "=" * 70)
        print("   🎉 PIPELINE COMPLETE!")
        print("=" * 70)
        print(f"\n   Ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show what's next
        updated_plan = memory.get_active_topic_plan()
        if updated_plan and hasattr(updated_plan, 'current_subtopic'):
            print(f"\n   📚 Next lesson: {updated_plan.current_subtopic}")
            print(f"   Progress: {updated_plan.current_index}/{updated_plan.total_lessons}")
        
        return result
        
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        print(f"\n❌ Error: {e}")
        return None


if __name__ == "__main__":
    result = run_full_pipeline()
