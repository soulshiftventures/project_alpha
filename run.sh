#!/bin/bash
# Project Alpha Runner Script
# Usage: ./run.sh [optional goal]
#
# This script runs the Project Alpha system in simulator mode.
# No API keys are required - the built-in simulator handles all AI calls.

set -e

# Get the script directory (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set PYTHONPATH to include project root for imports
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

echo "========================================"
echo " Project Alpha - Business Lifecycle Engine"
echo " Running in simulator mode (no API required)"
echo "========================================"
echo ""

# Run the main script
python3 "$SCRIPT_DIR/main.py" "$@"
