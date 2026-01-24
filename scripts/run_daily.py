#!/usr/bin/env python3
"""Production Daily Pipeline Runner.

This script runs the complete content production pipeline:
1. Checks if we already ran today (prevents duplicates)
2. Generates a new lesson video
3. Uploads to YouTube
4. Logs the result
5. Sends macOS notification

Usage:
    python3 scripts/run_daily.py
    python3 scripts/run_daily.py --force  # Run even if already ran today
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Optional
import subprocess

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"pipeline_{date.today().isoformat()}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DailyPipeline")


# Run history file
RUN_HISTORY_FILE = PROJECT_ROOT / "output" / "run_history.json"


def send_notification(title: str, message: str, sound: bool = True):
    """Send a macOS notification."""
    try:
        sound_cmd = '-sound default' if sound else ''
        script = f'display notification "{message}" with title "{title}" {sound_cmd}'
        subprocess.run(['osascript', '-e', script], capture_output=True)
        logger.info(f"Notification sent: {title}")
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")


def load_run_history() -> dict:
    """Load run history from file."""
    if RUN_HISTORY_FILE.exists():
        try:
            with open(RUN_HISTORY_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"runs": []}


def save_run_history(history: dict):
    """Save run history to file."""
    RUN_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RUN_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2, default=str)


def already_ran_today() -> bool:
    """Check if pipeline already ran today."""
    history = load_run_history()
    today = date.today().isoformat()
    
    for run in history.get("runs", []):
        if run.get("date") == today and run.get("success"):
            return True
    return False


def record_run(success: bool, video_id: Optional[str] = None, 
               lesson_title: Optional[str] = None, error: Optional[str] = None):
    """Record a pipeline run."""
    history = load_run_history()
    
    run_record = {
        "date": date.today().isoformat(),
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "video_id": video_id,
        "lesson_title": lesson_title,
        "error": error,
    }
    
    history["runs"].append(run_record)
    history["runs"] = history["runs"][-100:]  # Keep last 100 runs
    
    save_run_history(history)


def run_pipeline(force: bool = False) -> bool:
    """Run the daily content pipeline."""
    
    # Check if already ran today
    if not force and already_ran_today():
        logger.info("Pipeline already ran successfully today. Use --force to run again.")
        send_notification(
            "AI Education Engine", 
            "Pipeline already ran today - skipped",
            sound=False
        )
        return True
    
    logger.info("=" * 60)
    logger.info("Starting Daily Content Pipeline")
    logger.info("=" * 60)
    
    send_notification("AI Education Engine", "Starting daily pipeline...")
    
    try:
        # Import here to avoid slow startup when just checking status
        from src.rag.memory_store import MemoryStore
        from src.agents.orchestrator import Orchestrator
        from src.platforms.youtube_client import YouTubeClient
        from src.rag.schemas import Platform, VideoPerformance
        from uuid import uuid4
        
        # Initialize
        memory = MemoryStore()
        orchestrator = Orchestrator(memory=memory)
        
        # Get current lesson info
        plan = memory.get_active_topic_plan()
        if not plan:
            raise Exception("No active topic plan found!")
        
        lesson_title = plan.current_subtopic
        logger.info(f"Generating: {lesson_title}")
        
        # Run the pipeline
        result = orchestrator.run_daily_pipeline(dry_run=False)
        
        if not result.success:
            raise Exception(f"Pipeline failed at stage: {result.stage_reached}. Error: {result.error}")
        
        logger.info(f"Pipeline completed! Stage: {result.stage_reached}")
        
        # Upload to YouTube if video was produced
        video_id = None
        if result.final_video_path:
            logger.info("Uploading to YouTube...")
            youtube = YouTubeClient()
            
            description = f"""
{result.lesson.youtube_description or 'Learn AI with us!'}

#{' #'.join(result.lesson.youtube_hashtags[:10])}

Made with the Self-Improving AI Education Engine 🤖
"""
            
            video_id = youtube.upload_video(
                video_path=Path(result.final_video_path),
                title=result.lesson.youtube_title or f"AI Lesson: {result.lesson.subtopic}",
                description=description,
                tags=result.lesson.youtube_hashtags[:15],
                privacy_status="private",  # Start as private - manually make public
            )
            
            if video_id:
                logger.info(f"Video uploaded! ID: {video_id}")
                logger.info(f"URL: https://youtube.com/watch?v={video_id}")
                
                # Store performance record
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
        
        # Record success
        record_run(
            success=True,
            video_id=video_id,
            lesson_title=lesson_title,
        )
        
        # Send success notification
        send_notification(
            "AI Education Engine ✅", 
            f"Published: {lesson_title}\nVideo ID: {video_id or 'N/A'}",
        )
        
        # Send email notification if enabled
        try:
            from src.services.notification_service import get_notification_service
            email_service = get_notification_service()
            if email_service.is_enabled:
                thumbnail_generated = hasattr(result.lesson, 'thumbnail_path') and result.lesson.thumbnail_path
                email_service.send_success_notification(
                    lesson_title=lesson_title,
                    video_id=video_id,
                    thumbnail_generated=thumbnail_generated,
                )
        except Exception as email_err:
            logger.warning(f"Failed to send email notification: {email_err}")
        
        logger.info("=" * 60)
        logger.info("Pipeline completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        
        record_run(
            success=False,
            error=str(e),
        )
        
        send_notification(
            "AI Education Engine ❌", 
            f"Pipeline failed: {str(e)[:100]}",
        )
        
        # Send failure email notification if enabled
        try:
            from src.services.notification_service import get_notification_service
            email_service = get_notification_service()
            if email_service.is_enabled:
                # Read last few lines of log for context
                log_excerpt = None
                try:
                    with open(log_file) as f:
                        log_excerpt = "\n".join(f.readlines()[-20:])
                except:
                    pass
                email_service.send_failure_notification(
                    error=str(e),
                    stage="pipeline",
                    log_excerpt=log_excerpt,
                )
        except Exception as email_err:
            logger.warning(f"Failed to send email notification: {email_err}")
        
        return False


def main():
    """Main entry point."""
    force = "--force" in sys.argv
    
    if force:
        logger.info("Force mode enabled - running even if already ran today")
    
    success = run_pipeline(force=force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
