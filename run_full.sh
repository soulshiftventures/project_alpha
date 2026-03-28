#!/bin/bash
# =============================================================================
# Project Alpha - Full System Startup
# =============================================================================
#
# Usage:
#   ./run_full.sh           # Check readiness and start system
#   ./run_full.sh --skip-check  # Skip readiness check
#   ./run_full.sh --debug   # Start in debug mode
#
# =============================================================================

set -e

# Change to project root
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo " Project Alpha - Full System Startup"
echo "========================================"
echo ""

# Parse arguments
SKIP_CHECK=false
DEBUG_MODE=false

for arg in "$@"; do
    case $arg in
        --skip-check)
            SKIP_CHECK=true
            shift
            ;;
        --debug|-d)
            DEBUG_MODE=true
            shift
            ;;
    esac
done

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found"
    exit 1
fi

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"

# Step 1: Create required directories
echo "Step 1: Ensuring directories exist..."
mkdir -p project_alpha/data
echo "  Done."
echo ""

# Step 2: Run readiness check (unless skipped)
if [ "$SKIP_CHECK" = false ]; then
    echo "Step 2: Running readiness check..."
    echo "--------"

    python3 << 'EOF'
import sys
from core.readiness_checker import get_readiness_checker

checker = get_readiness_checker()
report = checker.check_all()

print(f"  Overall Status: {report.overall_status.value.upper()}")
print(f"  Dry-Run Ready:  {'YES' if report.dry_run_ready else 'NO'}")
print(f"  Live Ready:     {'YES' if report.live_ready else 'NO'}")

if report.missing_required:
    print(f"\n  Missing Required:")
    for item in report.missing_required:
        print(f"    - {item}")

if report.warnings:
    print(f"\n  Warnings:")
    for warning in report.warnings[:3]:
        print(f"    - {warning}")

live_connectors = [c.name for c in report.connectors if c.live_ready]
if live_connectors:
    print(f"\n  Live-Ready Connectors: {', '.join(live_connectors)}")

if not report.dry_run_ready:
    print("\n  ERROR: System is not ready for dry-run mode.")
    print("  Please fix the missing required components.")
    sys.exit(1)

print("\n  Readiness check passed!")
EOF

    READY_RESULT=$?
    if [ $READY_RESULT -ne 0 ]; then
        echo ""
        echo "Readiness check failed. Fix issues before starting."
        exit 1
    fi
    echo ""
else
    echo "Step 2: Skipping readiness check (--skip-check)"
    echo ""
fi

# Step 3: Run startup sequence
echo "Step 3: Running startup sequence..."
echo "--------"

python3 << 'EOF'
import sys
from core.startup_manager import get_startup_manager

manager = get_startup_manager()
result = manager.startup(skip_health_check=False)

print(f"  Startup Status: {result.phase.value.upper()}")
print(f"  Total Duration: {result.total_duration_ms:.1f}ms")

for step in result.steps:
    status_icon = "OK" if step.success else "FAILED"
    print(f"    [{status_icon}] {step.name}: {step.message}")

if result.errors:
    print(f"\n  Errors:")
    for error in result.errors:
        print(f"    - {error}")

if result.warnings:
    print(f"\n  Warnings:")
    for warning in result.warnings[:3]:
        print(f"    - {warning}")

if not result.success:
    print("\n  Startup failed. Check errors above.")
    sys.exit(1)

print("\n  Startup completed successfully!")
EOF

STARTUP_RESULT=$?
if [ $STARTUP_RESULT -ne 0 ]; then
    echo ""
    echo "Startup sequence failed."
    exit 1
fi
echo ""

# Step 4: Start the UI
echo "Step 4: Starting Operator Interface..."
echo "========================================"

# Set debug mode if requested
if [ "$DEBUG_MODE" = true ]; then
    export FLASK_DEBUG=1
    echo "  Debug mode enabled"
fi

# Set port (default 5000)
PORT="${PORT:-5000}"
export PORT

echo ""
echo "  Starting server on http://localhost:${PORT}"
echo ""
echo "  Key Routes:"
echo "    /             - System Overview"
echo "    /readiness    - System Readiness"
echo "    /health       - System Health"
echo "    /setup        - First-Use Setup"
echo ""
echo "  Press Ctrl+C to stop."
echo "========================================"
echo ""

python3 ui/app.py
