#!/bin/bash
# =============================================================================
# Project Alpha - Operator Interface Launcher
# =============================================================================
#
# Usage:
#   ./run_ui.sh           # Start on default port 5000
#   ./run_ui.sh --debug   # Start in debug mode
#   PORT=8080 ./run_ui.sh # Start on custom port
#
# =============================================================================

set -e

# Change to project root
cd "$(dirname "$0")"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found"
    exit 1
fi

# Check for Flask
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Flask not found. Installing..."
    pip3 install flask
fi

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"

# Set debug mode if requested
if [[ "$1" == "--debug" ]] || [[ "$1" == "-d" ]]; then
    export FLASK_DEBUG=1
    echo "Debug mode enabled"
fi

# Set port (default 5000)
PORT="${PORT:-5000}"
export PORT

# Run the app
echo "Starting Project Alpha Operator Interface..."
python3 ui/app.py
