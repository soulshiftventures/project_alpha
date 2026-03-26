#!/bin/bash
# Project Alpha Verification Script
# Usage: ./verify.sh
#
# Runs both Phase 5 verification and the full test suite.
# All tests run in simulator mode - no API keys required.

set -e

# Get the script directory (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set PYTHONPATH to include project root for imports
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

echo ""
echo "========================================"
echo " Project Alpha - Verification Suite"
echo "========================================"
echo ""

# Track results
PHASE5_RESULT=0
TESTS_RESULT=0

# Step 1: Run Phase 5 verification
echo "Step 1: Running Phase 5 integration verification..."
echo "--------"
python3 "$SCRIPT_DIR/scripts/verify_phase5.py" || PHASE5_RESULT=$?
echo ""

# Step 2: Run pytest suite
echo "Step 2: Running test suite..."
echo "--------"
python3 -m pytest "$SCRIPT_DIR/tests/" -v --tb=short || TESTS_RESULT=$?
echo ""

# Summary
echo "========================================"
echo " VERIFICATION SUMMARY"
echo "========================================"
echo ""

if [ $PHASE5_RESULT -eq 0 ]; then
    echo "  ✓ Phase 5 verification: PASSED (7/7 checks)"
else
    echo "  ✗ Phase 5 verification: FAILED"
fi

if [ $TESTS_RESULT -eq 0 ]; then
    echo "  ✓ Test suite: PASSED"
else
    echo "  ✗ Test suite: FAILED"
fi

echo ""

# Exit with error if either failed
if [ $PHASE5_RESULT -ne 0 ] || [ $TESTS_RESULT -ne 0 ]; then
    echo "Some verifications failed. Check output above for details."
    exit 1
fi

echo "All verifications passed!"
exit 0
