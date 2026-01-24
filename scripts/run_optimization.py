#!/usr/bin/env python3
"""Optimization Cycle Runner.

This script runs the analytics and optimization cycle:
1. Fetches YouTube analytics for recent videos
2. Runs PerformanceAnalystAgent
3. Runs StrategyOptimizerAgent
4. Updates strategy in RAG
5. Logs insights

Should run daily, ideally 24h after video publication.

Usage:
    python3 scripts/run_optimization.py
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
import subprocess

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"optimization_{date.today().isoformat()}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Optimization")


def send_notification(title: str, message: str, sound: bool = False):
    """Send a macOS notification."""
    try:
        sound_cmd = '-sound default' if sound else ''
        script = f'display notification "{message}" with title "{title}" {sound_cmd}'
        subprocess.run(['osascript', '-e', script], capture_output=True)
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")


def run_optimization():
    """Run the optimization cycle."""
    logger.info("=" * 60)
    logger.info("Starting Optimization Cycle")
    logger.info("=" * 60)
    
    try:
        from src.rag.memory_store import MemoryStore
        from src.rag.schemas import Platform, VideoPerformance
        from src.platforms.youtube_client import YouTubeClient
        from src.agents.performance_analyst import PerformanceAnalystAgent
        from src.agents.strategy_optimizer import StrategyOptimizerAgent
        
        memory = MemoryStore()
        
        # Step 1: Get recent videos and fetch analytics
        logger.info("📊 Fetching YouTube analytics...")
        performances = memory.get_performance_history(Platform.YOUTUBE, limit=10)
        
        if not performances:
            logger.info("No performance records found. Skipping optimization.")
            return True
        
        youtube = YouTubeClient()
        updated_count = 0
        
        for perf in performances:
            try:
                # Fetch latest stats from YouTube
                updated = youtube.get_video_performance(perf.platform_video_id)
                if updated:
                    # Update the record
                    perf.views = updated.views
                    perf.likes = updated.likes
                    perf.comments = updated.comments
                    perf.calculate_engagement_rate()
                    memory.save_performance(perf)
                    updated_count += 1
                    logger.info(f"   Updated {perf.platform_video_id}: {perf.views} views, {perf.engagement_rate:.2%} engagement")
            except Exception as e:
                logger.warning(f"   Failed to update {perf.platform_video_id}: {e}")
        
        logger.info(f"   Updated {updated_count} videos")
        
        # Step 2: Run Performance Analysis
        logger.info("\n🔍 Running Performance Analysis...")
        analyst = PerformanceAnalystAgent(memory=memory)
        analysis = analyst.analyze_performance(
            platform=Platform.YOUTUBE,
            days=30,
        )
        
        logger.info(f"   Videos analyzed: {analysis.videos_analyzed}")
        logger.info(f"   Avg views: {analysis.avg_views:.0f}")
        logger.info(f"   Avg engagement: {analysis.avg_engagement_rate:.2%}")
        logger.info(f"   Best style: {analysis.best_content_style}")
        
        # Log insights
        if analysis.insights:
            logger.info("\n   💡 Insights:")
            for insight in analysis.insights[:3]:
                logger.info(f"   - {insight.insight_type}: {insight.recommendation[:100]}")
        
        # Step 3: Run Strategy Optimization
        logger.info("\n🎯 Running Strategy Optimization...")
        optimizer = StrategyOptimizerAgent(memory=memory)
        optimization = optimizer.optimize_strategy(analysis)
        
        logger.info(f"   Strategy health: {optimization.overall_strategy_health}")
        
        # Apply high-confidence changes
        if optimization.recommendations:
            high_confidence = [r for r in optimization.recommendations if r.confidence >= 0.7]
            if high_confidence:
                logger.info(f"\n   🔧 Applying {len(high_confidence)} high-confidence changes...")
                optimizer.apply_recommendations(high_confidence, apply_priority_threshold=3)
                logger.info("   Strategy updated!")
        
        # Log recommendations
        if optimization.recommendations:
            logger.info("\n   📋 Recommendations:")
            for rec in optimization.recommendations[:3]:
                logger.info(f"   [{rec.priority}] {rec.change_type}: {rec.rationale[:80]}...")
        
        # Send summary notification
        summary = f"Analyzed {analysis.videos_analyzed} videos, {len(optimization.recommendations)} recommendations"
        send_notification("AI Engine: Optimization Complete", summary)
        
        logger.info("\n" + "=" * 60)
        logger.info("Optimization cycle completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.exception(f"Optimization failed: {e}")
        send_notification("AI Engine: Optimization Failed", str(e)[:100])
        return False


def main():
    """Main entry point."""
    success = run_optimization()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
