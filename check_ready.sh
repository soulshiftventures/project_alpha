#!/bin/bash
# =============================================================================
# Project Alpha - Readiness Check Script
# =============================================================================
#
# Usage:
#   ./check_ready.sh           # Run full readiness check
#   ./check_ready.sh --quick   # Quick readiness check
#   ./check_ready.sh --health  # Include health check
#   ./check_ready.sh --json    # Output as JSON
#
# Exit codes:
#   0 - Ready for dry-run at minimum
#   1 - Not ready (missing required components)
#   2 - Error during check
#
# =============================================================================

set -e

# Change to project root
cd "$(dirname "$0")"

# Parse arguments
QUICK_MODE=false
INCLUDE_HEALTH=false
JSON_OUTPUT=false

for arg in "$@"; do
    case $arg in
        --quick|-q)
            QUICK_MODE=true
            shift
            ;;
        --health|-h)
            INCLUDE_HEALTH=true
            shift
            ;;
        --json|-j)
            JSON_OUTPUT=true
            shift
            ;;
    esac
done

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found"
    exit 2
fi

if [ "$JSON_OUTPUT" = true ]; then
    # JSON output mode
    if [ "$QUICK_MODE" = true ]; then
        python3 << 'EOF'
import json
from core.readiness_checker import get_readiness_checker
checker = get_readiness_checker()
print(json.dumps(checker.check_quick(), indent=2))
EOF
    else
        python3 << 'EOF'
import json
from core.readiness_checker import get_readiness_checker
checker = get_readiness_checker()
report = checker.check_all()
print(json.dumps(report.to_dict(), indent=2))
EOF
    fi
else
    # Human-readable output
    echo ""
    echo "========================================"
    echo " Project Alpha - Readiness Check"
    echo "========================================"
    echo ""

    if [ "$QUICK_MODE" = true ]; then
        python3 << 'EOF'
import sys
from core.readiness_checker import get_readiness_checker

checker = get_readiness_checker()
status = checker.check_quick()

print(f"Status:         {status['status'].upper()}")
print(f"Ready:          {'YES' if status['ready'] else 'NO'}")
print(f"Dry-Run Ready:  {'YES' if status['dry_run_ready'] else 'NO'}")
print(f"Live Ready:     {'YES' if status['live_ready'] else 'NO'}")

if status['live_connectors']:
    print(f"Live Connectors: {', '.join(status['live_connectors'])}")

if status['missing_count'] > 0:
    print(f"\nMissing Components: {status['missing_count']}")

if not status['dry_run_ready']:
    sys.exit(1)
EOF
    else
        python3 << 'EOF'
import sys
from core.readiness_checker import get_readiness_checker

checker = get_readiness_checker()
report = checker.check_all()

# Overall status
print(f"Overall Status:  {report.overall_status.value.upper()}")
print(f"Dry-Run Ready:   {'YES' if report.dry_run_ready else 'NO'}")
print(f"Live Ready:      {'YES' if report.live_ready else 'NO'}")
print("")

# Components summary
ok_count = sum(1 for c in report.components if c.status.value == 'ok')
total_components = len(report.components)
print(f"Components: {ok_count}/{total_components} OK")

for comp in report.components:
    if comp.status.value != 'ok':
        icon = "!" if comp.required else "?"
        print(f"  [{icon}] {comp.name}: {comp.status.value} - {comp.message}")

print("")

# Connectors summary
live_count = sum(1 for c in report.connectors if c.live_ready)
total_connectors = len(report.connectors)
print(f"Connectors: {live_count}/{total_connectors} Live-Ready")

for conn in report.connectors:
    status = "LIVE" if conn.live_ready else ("DRY" if conn.dry_run_ready else "N/A")
    missing = f" (missing: {', '.join(conn.missing_credentials)})" if conn.missing_credentials else ""
    print(f"  [{status:4}] {conn.name}{missing}")

print("")

# Warnings
if report.warnings:
    print("Warnings:")
    for warning in report.warnings:
        print(f"  - {warning}")
    print("")

# Recommendations
if report.recommendations:
    print("Recommendations:")
    for rec in report.recommendations:
        print(f"  - {rec}")
    print("")

if not report.dry_run_ready:
    print("Result: NOT READY - Fix missing required components")
    sys.exit(1)
else:
    print("Result: READY for dry-run mode")
EOF
    fi

    # Include health check if requested
    if [ "$INCLUDE_HEALTH" = true ]; then
        echo ""
        echo "========================================"
        echo " Health Check"
        echo "========================================"
        echo ""

        python3 << 'EOF'
from core.health_monitor import get_health_monitor

monitor = get_health_monitor()
health = monitor.check_all()

print(f"Overall Health: {health.overall_status.value.upper()}")
print(f"Healthy: {health.healthy_count}, Degraded: {health.degraded_count}, Unhealthy: {health.unhealthy_count}")
print("")

for subsys in health.subsystems:
    icon = "OK" if subsys.status.value == 'healthy' else ("!!" if subsys.status.value == 'unhealthy' else "?")
    latency = f" ({subsys.latency_ms:.0f}ms)" if subsys.latency_ms else ""
    print(f"  [{icon:2}] {subsys.name:12} - {subsys.message}{latency}")
EOF
    fi

    echo ""
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "========================================"
fi
