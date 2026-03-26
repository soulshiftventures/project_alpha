#!/bin/bash
# Project Alpha Verification Script
# Usage: ./verify.sh
#
# Runs both integration verification and the full test suite.
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
INTEGRATION_RESULT=0
TESTS_RESULT=0

# Step 1: Run integration verification
echo "Step 1: Running integration verification..."
echo "--------"
python3 "$SCRIPT_DIR/scripts/verify_system.py" || INTEGRATION_RESULT=$?
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

if [ $INTEGRATION_RESULT -eq 0 ]; then
    echo "  ✓ Integration verification: PASSED (7/7 checks)"
else
    echo "  ✗ Integration verification: FAILED"
fi

if [ $TESTS_RESULT -eq 0 ]; then
    echo "  ✓ Test suite: PASSED"
else
    echo "  ✗ Test suite: FAILED"
fi

echo ""

# Exit with error if either failed
if [ $INTEGRATION_RESULT -ne 0 ] || [ $TESTS_RESULT -ne 0 ]; then
    echo "Some verifications failed. Check output above for details."
    exit 1
fi

echo "All verifications passed!"
exit 0
