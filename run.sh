#!/bin/bash
# Project Alpha Runner Script
# Usage: ./project_alpha/run.sh [optional goal]

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Set PYTHONPATH to include parent directory
export PYTHONPATH="$PARENT_DIR:$PYTHONPATH"

# Run the main script
python3 "$SCRIPT_DIR/main.py" "$@"
