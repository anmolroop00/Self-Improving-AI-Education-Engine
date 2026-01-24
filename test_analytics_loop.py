"""Test the Self-Improving Analytics Loop.

This script demonstrates the complete learning cycle:
1. Store lesson content with YouTube video ID in RAG
2. Fetch real-time analytics from YouTube
3. Run PerformanceAnalystAgent to identify patterns
4. Run StrategyOptimizerAgent to generate recommendations
5. Apply high-confidence changes

YouTube Video ID: 1y8oKKDjG7o
"""

import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.rag.memory_store import MemoryStore
from src.rag.schemas import (
    TopicPlan, 
    LessonContent, 
    VideoPerformance, 
    ContentStrategy,
    Platform,
    ScriptStyle,
)
from src.platforms.youtube_client import YouTubeClient
from src.agents.performance_analyst import PerformanceAnalystAgent
from src.agents.strategy_optimizer import StrategyOptimizerAgent
from src.config import settings
import logging

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
YOUTUBE_VIDEO_ID = "1y8oKKDjG7o"
TOPIC = "AI & Machine Learning"
SUBTOPIC = "How Neural Networks Learn"


def step1_store_lesson_in_rag(memory: MemoryStore) -> LessonContent:
    """Step 1: Store the lesson content with YouTube video ID."""
    print("\n" + "=" * 60)
    print("   📚 STEP 1: STORING LESSON IN RAG")
    print("=" * 60)
    
    # Create a topic plan if it doesn't exist
    existing_plan = memory.get_active_topic_plan()
    
    # Check if existing plan is valid (schema might have changed)
    if existing_plan and hasattr(existing_plan, 'main_topic'):
        plan = existing_plan
        print(f"   Using existing plan: {plan.main_topic}")
    else:
        if existing_plan:
            print("   ⚠️ Existing plan has incompatible schema, creating new one...")
        
        subtopics = [
            "How Neural Networks Learn",
            "What is Backpropagation",
            "Understanding Gradient Descent",
            "Activation Functions Explained",
            "Building Your First Neural Network",
        ]
        
        plan = TopicPlan(
            id=f"plan_{uuid4().hex[:8]}",
            main_topic=TOPIC,
            description="Learn AI and Machine Learning concepts explained simply for beginners",
            subtopics=subtopics,
            total_lessons=len(subtopics),
            current_index=0,
        )
        memory.save_topic_plan(plan)
        print(f"   Created topic plan: {plan.main_topic}")
    
    # Create the lesson content
    raw_script = "Neural networks learn just like you learn! Imagine you're learning to throw a ball into a basket. At first, you miss. But each time you throw, you adjust a little bit. That's exactly how a neural network learns - it makes guesses, sees how wrong it was, and adjusts its brain to do better next time!"
    clean_script = "Neural networks learn by adjusting weights through backpropagation, like a student getting feedback on wrong answers."
    
    lesson = LessonContent(
        id=f"lesson_{uuid4().hex[:8]}",
        topic_plan_id=plan.id,
        lesson_number=1,
        subtopic=SUBTOPIC,
        raw_script=raw_script,
        clean_script=clean_script,
        video_prompts=[
            "Abstract glowing neural network with colorful nodes pulsing with energy",
            "Floating 3D data points connecting with glowing lines forming a pattern",
        ],
        word_count=len(clean_script.split()),
        estimated_duration=len(clean_script.split()) / 2.5,  # ~2.5 words/sec
        youtube_title="How Neural Networks Learn: AI for Beginners (Lesson 1)",
        youtube_description="Ever wondered how Neural Networks actually LEARN?",
        youtube_hashtags=["AI", "MachineLearning", "NeuralNetworks", "LearnAI"],
    )
    
    # Store the youtube video ID as a metadata field
    lesson.final_video_path = f"youtube:{YOUTUBE_VIDEO_ID}"
    
    lesson_id = memory.save_lesson(lesson)
    print(f"   ✅ Lesson stored with ID: {lesson_id}")
    print(f"   ✅ YouTube Video ID: {YOUTUBE_VIDEO_ID}")
    
    # NOTE: We do NOT call update_topic_progress() here!
    # Only the full daily pipeline should advance the curriculum.
    # This test is just for demonstrating the analytics loop.
    
    return lesson


def step2_fetch_youtube_analytics(lesson: LessonContent) -> VideoPerformance:
    """Step 2: Fetch real-time analytics from YouTube."""
    print("\n" + "=" * 60)
    print("   📊 STEP 2: FETCHING YOUTUBE ANALYTICS")
    print("=" * 60)
    
    youtube = YouTubeClient()
    perf = youtube.get_video_performance(YOUTUBE_VIDEO_ID)
    
    if perf:
        # Link to lesson
        perf.lesson_id = lesson.id
        
        print(f"   Views: {perf.views}")
        print(f"   Likes: {perf.likes}")
        print(f"   Comments: {perf.comments}")
        print(f"   Engagement Rate: {perf.engagement_rate:.4f}")
        return perf
    else:
        # Video might be too new - create mock data for testing
        print("   ⚠️ Video too new for analytics, using initial data...")
        perf = VideoPerformance(
            id=f"perf_{uuid4().hex[:8]}",
            lesson_id=lesson.id,
            platform=Platform.YOUTUBE,
            platform_video_id=YOUTUBE_VIDEO_ID,
            views=0,
            likes=0,
            comments=0,
            post_time=datetime.now(),
            post_day_of_week=datetime.now().strftime("%A"),
        )
        perf.calculate_engagement_rate()
        return perf


def step3_store_performance(memory: MemoryStore, perf: VideoPerformance):
    """Step 3: Store performance data in RAG."""
    print("\n" + "=" * 60)
    print("   💾 STEP 3: STORING PERFORMANCE IN RAG")
    print("=" * 60)
    
    perf_id = memory.save_performance(perf)
    print(f"   ✅ Performance record saved: {perf_id}")
    
    # Also update hashtag performance
    for hashtag in ["AI", "MachineLearning", "NeuralNetworks", "LearnAI"]:
        memory.update_hashtag_performance(
            hashtag=hashtag,
            platform=Platform.YOUTUBE,
            views=perf.views,
            engagement=perf.likes + perf.comments,
        )
    print(f"   ✅ Hashtag performance updated")


def step4_analyze_performance(memory: MemoryStore):
    """Step 4: Run the Performance Analyst Agent."""
    print("\n" + "=" * 60)
    print("   🔍 STEP 4: ANALYZING PERFORMANCE")
    print("=" * 60)
    
    analyst = PerformanceAnalystAgent(memory=memory)
    analysis = analyst.analyze_performance(
        platform=Platform.YOUTUBE,
        days=30,
    )
    
    print(f"\n   📈 Analysis Results:")
    print(f"   Videos Analyzed: {analysis.videos_analyzed}")
    print(f"   Avg Views: {analysis.avg_views:.1f}")
    print(f"   Avg Engagement Rate: {analysis.avg_engagement_rate:.2%}")
    print(f"   Best Content Style: {analysis.best_content_style}")
    
    if analysis.insights:
        print(f"\n   💡 Key Insights:")
        for i, insight in enumerate(analysis.insights[:3], 1):
            print(f"   {i}. {insight.insight_type}: {insight.recommendation}")
    
    if analysis.areas_to_improve:
        print(f"\n   ⚠️ Areas to Improve:")
        for area in analysis.areas_to_improve[:3]:
            print(f"   - {area}")
    
    return analysis


def step5_optimize_strategy(memory: MemoryStore, analysis):
    """Step 5: Run the Strategy Optimizer Agent."""
    print("\n" + "=" * 60)
    print("   🎯 STEP 5: OPTIMIZING STRATEGY")
    print("=" * 60)
    
    # First, ensure we have a strategy
    current_strategy = memory.get_active_strategy()
    if not current_strategy:
        print("   Creating default strategy...")
        current_strategy = ContentStrategy(
            id=f"strategy_{uuid4().hex[:8]}",
            current_script_style=ScriptStyle.STORYTELLING,
            posting_times={"youtube": "16:00", "instagram": "18:00"},
            primary_hashtags={"youtube": ["AI", "MachineLearning", "Tech"]},
            engagement_hooks=["Did you know...", "Ever wondered..."],
        )
        memory.save_strategy(current_strategy)
        print(f"   ✅ Default strategy created")
    
    optimizer = StrategyOptimizerAgent(memory=memory)
    optimization = optimizer.optimize_strategy(analysis)
    
    print(f"\n   📋 Strategy Health: {optimization.overall_strategy_health}")
    print(f"   Current Strategy: {optimization.current_strategy_summary}")
    
    if optimization.recommendations:
        print(f"\n   💡 Recommendations:")
        for rec in optimization.recommendations[:3]:
            print(f"   [{rec.priority}] {rec.change_type}: {rec.current_value} → {rec.recommended_value}")
            print(f"       Confidence: {rec.confidence:.0%}")
            print(f"       Reason: {rec.rationale[:80]}...")
    
    if optimization.urgent_changes:
        print(f"\n   🚨 Urgent Changes:")
        for change in optimization.urgent_changes[:2]:
            print(f"   - {change}")
    
    # Apply high-confidence recommendations
    if optimization.recommendations:
        high_confidence = [r for r in optimization.recommendations if r.confidence >= 0.7]
        if high_confidence:
            print(f"\n   🔧 Applying {len(high_confidence)} high-confidence changes...")
            updated_strategy = optimizer.apply_recommendations(
                high_confidence, 
                apply_priority_threshold=3
            )
            print(f"   ✅ Strategy updated!")
    
    return optimization


def step6_show_rag_state(memory: MemoryStore):
    """Step 6: Show what's stored in RAG."""
    print("\n" + "=" * 60)
    print("   📁 STEP 6: RAG MEMORY STATE")
    print("=" * 60)
    
    # Get active plan
    plan = memory.get_active_topic_plan()
    if plan and hasattr(plan, 'main_topic'):
        print(f"\n   📚 Active Topic Plan:")
        print(f"   Topic: {plan.main_topic}")
        print(f"   Progress: {plan.current_index}/{plan.total_lessons} lessons")
        print(f"   Next: {plan.current_subtopic}")
    
    # Get performance history
    perfs = memory.get_performance_history(Platform.YOUTUBE, limit=5)
    if perfs:
        print(f"\n   📊 Recent Performance (last {len(perfs)} videos):")
        for p in perfs[:3]:
            print(f"   - {p.platform_video_id}: {p.views} views, {p.engagement_rate:.2%} engagement")
    
    # Get top hashtags
    top_hashtags = memory.get_top_hashtags(Platform.YOUTUBE, limit=5)
    if top_hashtags:
        print(f"\n   #️⃣ Top Performing Hashtags:")
        for h in top_hashtags[:5]:
            print(f"   - #{h.hashtag}: score {h.effectiveness_score:.1f}")
    
    # Get current strategy
    strategy = memory.get_active_strategy()
    if strategy:
        print(f"\n   🎯 Current Strategy:")
        print(f"   Script Style: {strategy.current_script_style}")
        print(f"   Posting Times: {strategy.posting_times}")


def main():
    """Run the complete self-improving loop test."""
    print("\n" + "=" * 60)
    print("   🔄 SELF-IMPROVING LOOP TEST")
    print("=" * 60)
    print(f"\n   YouTube Video: https://youtube.com/watch?v={YOUTUBE_VIDEO_ID}")
    print(f"   Topic: {TOPIC}")
    print(f"   Subtopic: {SUBTOPIC}")
    
    try:
        # Initialize memory store
        memory = MemoryStore()
        
        # Run the complete loop
        lesson = step1_store_lesson_in_rag(memory)
        perf = step2_fetch_youtube_analytics(lesson)
        step3_store_performance(memory, perf)
        analysis = step4_analyze_performance(memory)
        optimization = step5_optimize_strategy(memory, analysis)
        step6_show_rag_state(memory)
        
        # Summary
        print("\n" + "=" * 60)
        print("   🎉 SELF-IMPROVING LOOP COMPLETE!")
        print("=" * 60)
        print("\n   The system has:")
        print("   ✅ Stored lesson content with YouTube video ID")
        print("   ✅ Fetched real-time analytics")
        print("   ✅ Analyzed performance patterns")
        print("   ✅ Generated optimization recommendations")
        print("   ✅ Applied high-confidence changes")
        print("\n   Next lesson will use the updated strategy!")
        
    except Exception as e:
        logger.exception(f"Test failed: {e}")
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
