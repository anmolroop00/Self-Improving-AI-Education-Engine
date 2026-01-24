#!/bin/bash
# Daily Pipeline Runner Shell Wrapper
# This script is called by LaunchAgent and handles the Python environment properly.

# Change to project directory
cd "/Users/anmolrooprai/Desktop/Anmol/AntiGravity Workspace/Self Improving AI Education Engine"

# Set Python path
export PYTHONPATH="/Users/anmolrooprai/Desktop/Anmol/AntiGravity Workspace/Self Improving AI Education Engine"

# Use the user's Python (not system Python which has SIP restrictions)
/usr/bin/python3 scripts/run_daily.py "$@"
