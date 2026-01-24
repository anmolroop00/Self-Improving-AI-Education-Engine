#!/usr/bin/env python3
"""Quick Status Check.

Shows the current state of the AI Education Engine.

Usage:
    python3 scripts/check_status.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("\n" + "=" * 60)
    print("   🤖 AI EDUCATION ENGINE STATUS")
    print("=" * 60)
    
    try:
        from src.rag.memory_store import MemoryStore
        from src.rag.schemas import Platform
        
        memory = MemoryStore()
        
        # Curriculum status
        plan = memory.get_active_topic_plan()
        if plan and hasattr(plan, 'main_topic'):
            print(f"\n📚 Curriculum: {plan.main_topic}")
            print(f"   Progress: {plan.current_index}/{plan.total_lessons} lessons")
            print(f"   Next: {plan.current_subtopic}")
        else:
            print("\n📚 Curriculum: No active plan")
        
        # Strategy status
        strategy = memory.get_active_strategy()
        if strategy:
            print(f"\n🎯 Strategy:")
            print(f"   Style: {strategy.current_script_style.value}")
            print(f"   Posting: {strategy.posting_times}")
        else:
            print("\n🎯 Strategy: Not configured")
        
        # Recent performance
        perfs = memory.get_performance_history(Platform.YOUTUBE, limit=5)
        if perfs:
            print(f"\n📊 Recent Videos:")
            for p in perfs[:3]:
                print(f"   - {p.platform_video_id}: {p.views} views, {p.engagement_rate:.2%} engagement")
        
        # Run history
        history_file = PROJECT_ROOT / "output" / "run_history.json"
        if history_file.exists():
            with open(history_file) as f:
                history = json.load(f)
                runs = history.get("runs", [])
                if runs:
                    last_run = runs[-1]
                    print(f"\n🕐 Last Run:")
                    status = "✅ Success" if last_run.get("success") else "❌ Failed"
                    print(f"   {status} at {last_run.get('timestamp', 'Unknown')[:16]}")
                    if last_run.get("video_id"):
                        print(f"   Video: https://youtube.com/watch?v={last_run['video_id']}")
        
        # Collection stats
        stats = memory.get_collection_stats()
        print(f"\n💾 RAG Memory:")
        for name, count in stats.items():
            print(f"   {name}: {count} items")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print()


if __name__ == "__main__":
    main()
