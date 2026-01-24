#!/usr/bin/env python3
"""Development Mode Test Runner.

Run this script to test new features safely without affecting production data.
Automatically sets DEV mode which:
- Uses separate ChromaDB database (./data/chromadb_dev)
- Uses separate output directory (./output_dev)
- Defaults to dry_run (no actual YouTube uploads)
- Uses a test curriculum

Usage:
    python3 scripts/run_dev.py                    # Run with dry_run (default)
    python3 scripts/run_dev.py --no-dry-run      # Actually generate video
    python3 scripts/run_dev.py --feature thumbnails  # Test specific feature
"""

import sys
import os
from pathlib import Path

# Force development mode BEFORE importing anything else
os.environ["ENV_MODE"] = "development"

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
from datetime import datetime
from uuid import uuid4

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DevRunner")


def show_environment():
    """Display current environment settings."""
    from src.config import settings
    
    print("\n" + "=" * 60)
    print("   🔧 DEVELOPMENT MODE")
    print("=" * 60)
    
    summary = settings.get_env_summary()
    print(f"\n   Environment: {summary['mode'].upper()}")
    print(f"   ChromaDB: {summary['chromadb_dir']}")
    print(f"   Output: {summary['output_dir']}")
    print(f"   Dry Run Default: {summary['dry_run_default']}")
    
    print(f"\n   Feature Flags:")
    for name, enabled in summary['features'].items():
        status = '✅ ON' if enabled else '❌ OFF'
        print(f"   - {name}: {status}")
    
    print()


def ensure_test_curriculum():
    """Create a test curriculum for development."""
    from src.rag.memory_store import MemoryStore
    from src.rag.schemas import TopicPlan
    
    memory = MemoryStore()
    
    # Check if dev curriculum exists
    plan = memory.get_active_topic_plan()
    if plan and hasattr(plan, 'main_topic'):
        print(f"   Using existing dev curriculum: {plan.main_topic}")
        print(f"   Progress: {plan.current_index}/{plan.total_lessons}")
        return memory, plan
    
    # Create test curriculum
    print("   Creating test curriculum for development...")
    test_subtopics = [
        "Test Lesson 1: Introduction",
        "Test Lesson 2: Basic Concepts",
        "Test Lesson 3: Advanced Topics",
    ]
    
    plan = TopicPlan(
        id=f"dev_plan_{uuid4().hex[:8]}",
        main_topic="Development Test Topic",
        description="Test curriculum for feature development",
        subtopics=test_subtopics,
        total_lessons=len(test_subtopics),
        current_index=0,
    )
    memory.save_topic_plan(plan)
    print(f"   Created: {plan.main_topic} ({plan.total_lessons} lessons)")
    
    return memory, plan


def run_dev_pipeline(dry_run: bool = True, test_feature: str = None):
    """Run the pipeline in development mode."""
    from src.agents.orchestrator import Orchestrator
    
    show_environment()
    
    print("-" * 60)
    print("   📚 SETTING UP DEV ENVIRONMENT")
    print("-" * 60)
    
    memory, plan = ensure_test_curriculum()
    
    print(f"\n   Next lesson: {plan.current_subtopic}")
    print(f"   Dry run: {dry_run}")
    if test_feature:
        print(f"   Testing feature: {test_feature}")
    
    print("\n" + "-" * 60)
    print("   🎬 RUNNING DEV PIPELINE")
    print("-" * 60)
    
    orchestrator = Orchestrator(memory=memory)
    
    # Run pipeline
    result = orchestrator.run_daily_pipeline(dry_run=dry_run)
    
    print("\n" + "-" * 60)
    print("   📊 RESULTS")
    print("-" * 60)
    
    if result.success:
        print(f"   ✅ Pipeline completed: {result.stage_reached}")
        if result.lesson:
            print(f"   Lesson: {result.lesson.subtopic}")
            print(f"   Words: {result.lesson.word_count}")
        if result.final_video_path:
            print(f"   Video: {result.final_video_path}")
    else:
        print(f"   ❌ Pipeline failed at: {result.stage_reached}")
        print(f"   Error: {result.error}")
    
    print("\n" + "=" * 60)
    print("   💡 Note: This ran in DEV mode")
    print("   - Production data is UNTOUCHED")
    print("   - No YouTube upload (unless --no-dry-run)")
    print("=" * 60 + "\n")
    
    return result


def main():
    """Main entry point for dev runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Development mode test runner")
    parser.add_argument(
        "--no-dry-run", 
        action="store_true",
        help="Actually generate video (still uses dev database)"
    )
    parser.add_argument(
        "--feature",
        type=str,
        help="Enable a specific feature for testing (e.g., thumbnails)"
    )
    parser.add_argument(
        "--env-only",
        action="store_true",
        help="Just show environment info, don't run pipeline"
    )
    
    args = parser.parse_args()
    
    # Enable feature if specified
    if args.feature:
        feature_env = f"FEATURE_{args.feature.upper()}"
        os.environ[feature_env] = "true"
        logger.info(f"Enabled feature: {args.feature}")
    
    if args.env_only:
        show_environment()
        return
    
    dry_run = not args.no_dry_run
    run_dev_pipeline(dry_run=dry_run, test_feature=args.feature)


if __name__ == "__main__":
    main()
