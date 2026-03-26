# Project Alpha - Verification Guide

## Quick Verification

Run the complete verification suite:

```bash
./verify.sh
```

Expected output:
- Integration verification: **7/7 checks passed**
- Test suite: **55 tests passed**

## What Gets Verified

### 1. Import Verification
Verifies all core modules can be imported:
- WorkflowOrchestrator
- StageWorkflows
- PortfolioWorkflows
- WorkflowValidator

### 2. Initialization Verification
Confirms all modules initialize without errors.

### 3. Tool Status Verification
Checks optional tool availability:
- AI-Q (optional)
- NemoClaw (optional)
- Zep (optional)
- Simulator (always available)

### 4. Stage Workflow Verification
Tests task generation for all 7 lifecycle stages:
- DISCOVERED
- VALIDATING
- BUILDING
- SCALING
- OPERATING
- OPTIMIZING
- TERMINATED

### 5. Portfolio Workflow Verification
Tests multi-business portfolio management.

### 6. Workflow Validation Verification
Tests the pre-execution validation framework.

### 7. Orchestrator Execution Verification
Tests end-to-end workflow execution.

## Manual Verification

```bash
# Run integration verification only
python3 scripts/verify_system.py

# Run test suite only
PYTHONPATH=. pytest tests/test_workflows.py -v
```

## Troubleshooting

If verification fails:
1. Ensure Python 3.8+ is installed
2. Install pytest: `pip install pytest`
3. Run from project root directory
4. Check that PYTHONPATH includes the project root
