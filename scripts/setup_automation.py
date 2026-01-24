#!/usr/bin/env python3
"""Setup and Manage Automation.

This script sets up and manages the macOS LaunchAgent for automated
content production.

Commands:
    python3 scripts/setup_automation.py install   # Install LaunchAgents
    python3 scripts/setup_automation.py uninstall # Remove LaunchAgents
    python3 scripts/setup_automation.py status    # Check status
    python3 scripts/setup_automation.py start     # Start scheduler
    python3 scripts/setup_automation.py stop      # Stop scheduler
    python3 scripts/setup_automation.py logs      # View recent logs

Configuration:
    Set DAILY_HOUR and DAILY_MINUTE in .env to customize pipeline time
    Default: 10:00 AM daily
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# LaunchAgent configuration
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
DAILY_PLIST = LAUNCH_AGENTS_DIR / "com.ai-education-engine.daily.plist"
OPTIMIZATION_PLIST = LAUNCH_AGENTS_DIR / "com.ai-education-engine.optimization.plist"

# Default schedule - can be overridden by strategy
DEFAULT_DAILY_HOUR = 10
DEFAULT_DAILY_MINUTE = 0
DEFAULT_OPTIMIZATION_HOUR = 18
DEFAULT_OPTIMIZATION_MINUTE = 0


def get_python_path() -> str:
    """Get the path to python3."""
    result = subprocess.run(['which', 'python3'], capture_output=True, text=True)
    return result.stdout.strip() or '/usr/bin/python3'


def create_daily_plist(hour: int = DEFAULT_DAILY_HOUR, minute: int = DEFAULT_DAILY_MINUTE) -> str:
    """Create the daily pipeline LaunchAgent plist content."""
    script_path = PROJECT_ROOT / "scripts" / "run_daily.sh"
    log_path = PROJECT_ROOT / "logs" / "launchd_daily.log"
    error_path = PROJECT_ROOT / "logs" / "launchd_daily_error.log"
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ai-education-engine.daily</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{script_path}</string>
    </array>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    
    <key>WorkingDirectory</key>
    <string>{PROJECT_ROOT}</string>
    
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    
    <key>StandardErrorPath</key>
    <string>{error_path}</string>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
'''


def create_optimization_plist(hour: int = DEFAULT_OPTIMIZATION_HOUR, 
                              minute: int = DEFAULT_OPTIMIZATION_MINUTE) -> str:
    """Create the optimization cycle LaunchAgent plist content."""
    script_path = PROJECT_ROOT / "scripts" / "run_optimization.sh"
    log_path = PROJECT_ROOT / "logs" / "launchd_optimization.log"
    error_path = PROJECT_ROOT / "logs" / "launchd_optimization_error.log"
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ai-education-engine.optimization</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{script_path}</string>
    </array>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    
    <key>WorkingDirectory</key>
    <string>{PROJECT_ROOT}</string>
    
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    
    <key>StandardErrorPath</key>
    <string>{error_path}</string>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
'''


def install():
    """Install LaunchAgents."""
    print("🔧 Installing LaunchAgents...")
    
    # Create logs directory
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    
    # Create LaunchAgents directory if needed
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get schedule from strategy if available
    daily_hour = DEFAULT_DAILY_HOUR
    daily_minute = DEFAULT_DAILY_MINUTE
    
    try:
        from src.rag.memory_store import MemoryStore
        memory = MemoryStore()
        strategy = memory.get_active_strategy()
        if strategy and strategy.posting_times.get('youtube'):
            time_str = strategy.posting_times['youtube']
            if ':' in time_str:
                daily_hour, daily_minute = map(int, time_str.split(':')[:2])
                print(f"   Using strategy posting time: {daily_hour}:{daily_minute:02d}")
    except Exception as e:
        print(f"   Using default time: {daily_hour}:{daily_minute:02d}")
    
    # Write daily plist
    daily_content = create_daily_plist(daily_hour, daily_minute)
    with open(DAILY_PLIST, 'w') as f:
        f.write(daily_content)
    print(f"   ✅ Created {DAILY_PLIST.name}")
    
    # Write optimization plist
    opt_content = create_optimization_plist()
    with open(OPTIMIZATION_PLIST, 'w') as f:
        f.write(opt_content)
    print(f"   ✅ Created {OPTIMIZATION_PLIST.name}")
    
    # Load the agents
    print("\n📦 Loading LaunchAgents...")
    subprocess.run(['launchctl', 'load', str(DAILY_PLIST)], capture_output=True)
    subprocess.run(['launchctl', 'load', str(OPTIMIZATION_PLIST)], capture_output=True)
    
    print("\n✅ Installation complete!")
    print(f"\n📅 Schedule:")
    print(f"   Daily Pipeline: {daily_hour}:{daily_minute:02d} every day")
    print(f"   Optimization: {DEFAULT_OPTIMIZATION_HOUR}:{DEFAULT_OPTIMIZATION_MINUTE:02d} every day")
    print(f"\n💡 Commands:")
    print(f"   Check status: python3 scripts/setup_automation.py status")
    print(f"   View logs:    python3 scripts/setup_automation.py logs")
    print(f"   Run now:      python3 scripts/run_daily.py --force")


def uninstall():
    """Uninstall LaunchAgents."""
    print("🗑️  Uninstalling LaunchAgents...")
    
    # Unload agents
    if DAILY_PLIST.exists():
        subprocess.run(['launchctl', 'unload', str(DAILY_PLIST)], capture_output=True)
        DAILY_PLIST.unlink()
        print(f"   ✅ Removed {DAILY_PLIST.name}")
    
    if OPTIMIZATION_PLIST.exists():
        subprocess.run(['launchctl', 'unload', str(OPTIMIZATION_PLIST)], capture_output=True)
        OPTIMIZATION_PLIST.unlink()
        print(f"   ✅ Removed {OPTIMIZATION_PLIST.name}")
    
    print("\n✅ Uninstallation complete!")


def status():
    """Check LaunchAgent status."""
    print("📊 LaunchAgent Status")
    print("-" * 50)
    
    # Check if plists exist
    daily_installed = DAILY_PLIST.exists()
    opt_installed = OPTIMIZATION_PLIST.exists()
    
    print(f"Daily Pipeline:  {'✅ Installed' if daily_installed else '❌ Not installed'}")
    print(f"Optimization:    {'✅ Installed' if opt_installed else '❌ Not installed'}")
    
    # Check if loaded
    result = subprocess.run(['launchctl', 'list'], capture_output=True, text=True)
    
    daily_running = 'com.ai-education-engine.daily' in result.stdout
    opt_running = 'com.ai-education-engine.optimization' in result.stdout
    
    print(f"\nDaily Loaded:    {'✅ Yes' if daily_running else '❌ No'}")
    print(f"Optimization:    {'✅ Yes' if opt_running else '❌ No'}")
    
    # Show schedule
    if daily_installed:
        print(f"\n📅 Schedule (from plist):")
        try:
            import plistlib
            with open(DAILY_PLIST, 'rb') as f:
                plist = plistlib.load(f)
                interval = plist.get('StartCalendarInterval', {})
                h = interval.get('Hour', '?')
                m = interval.get('Minute', '?')
                print(f"   Daily Pipeline: {h}:{m:02d}" if isinstance(m, int) else f"   Daily: {h}:{m}")
        except:
            pass
    
    # Show recent runs
    print(f"\n📝 Recent Runs:")
    history_file = PROJECT_ROOT / "output" / "run_history.json"
    if history_file.exists():
        try:
            import json
            with open(history_file) as f:
                history = json.load(f)
                runs = history.get('runs', [])[-5:]
                for run in reversed(runs):
                    status_icon = '✅' if run.get('success') else '❌'
                    print(f"   {status_icon} {run.get('timestamp', '?')[:16]} - {run.get('lesson_title', 'Unknown')[:40]}")
        except:
            pass
    else:
        print("   No runs recorded yet")


def start():
    """Start the LaunchAgents."""
    print("▶️  Starting LaunchAgents...")
    subprocess.run(['launchctl', 'load', str(DAILY_PLIST)], capture_output=True)
    subprocess.run(['launchctl', 'load', str(OPTIMIZATION_PLIST)], capture_output=True)
    print("✅ Started!")


def stop():
    """Stop the LaunchAgents."""
    print("⏹️  Stopping LaunchAgents...")
    subprocess.run(['launchctl', 'unload', str(DAILY_PLIST)], capture_output=True)
    subprocess.run(['launchctl', 'unload', str(OPTIMIZATION_PLIST)], capture_output=True)
    print("✅ Stopped!")


def logs():
    """View recent logs."""
    log_dir = PROJECT_ROOT / "logs"
    
    print("📋 Recent Logs")
    print("=" * 60)
    
    # Find most recent log files
    log_files = sorted(log_dir.glob("pipeline_*.log"), reverse=True)[:3]
    
    if not log_files:
        print("No logs found")
        return
    
    for log_file in log_files:
        print(f"\n--- {log_file.name} ---")
        try:
            with open(log_file) as f:
                lines = f.readlines()[-20:]  # Last 20 lines
                for line in lines:
                    print(line.rstrip())
        except Exception as e:
            print(f"Error reading: {e}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    commands = {
        'install': install,
        'uninstall': uninstall,
        'status': status,
        'start': start,
        'stop': stop,
        'logs': logs,
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        print(f"Available commands: {', '.join(commands.keys())}")
        sys.exit(1)


if __name__ == "__main__":
    main()
