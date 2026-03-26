# Quick Start Guide

## Overview

Project Alpha is an AI-powered business lifecycle engine that manages multiple businesses through their complete lifecycle using workflow orchestration.

## Running the System

### One Command
```bash
./run.sh "your business idea"
```

### What You'll See
```
======================================================================
 PROJECT ALPHA - BUSINESS LIFECYCLE ENGINE
 Continuous Portfolio Management System
 Integrated Workflow Orchestration
======================================================================

Workflow Tool Status:
  AI-Q:      Not Available
  NemoClaw:  Not Available
  Zep:       Not Available
  Simulator: Available

BUSINESS LIFECYCLE ENGINE - Starting Continuous Operation
```

## Core Features

- **Workflow Orchestration**: Intelligent task execution with tool integration
- **Pre-Execution Validation**: 5-check safety framework before task execution
- **Portfolio Management**: Automated health analysis and rebalancing every 5 cycles
- **Tool Integration**: AI-Q, NemoClaw, Zep, and Simulator support

## Key Modules

| Module | Purpose |
|--------|---------|
| `workflow_orchestrator.py` | Central orchestration engine |
| `stage_workflows.py` | Stage-specific workflow definitions |
| `portfolio_workflows.py` | Portfolio-level management |
| `workflow_validator.py` | Pre-execution validation system |

## Tool Integration (Optional)

### AI-Q - Intelligent Task Reasoning
```bash
export AIQ_API_KEY="your-api-key"
```

### NemoClaw - Sandboxed Execution
```bash
pip install nemoclaw
```

### Zep - Long-term Memory
```bash
export ZEP_API_KEY="your-api-key"
```

### Simulator - Built-in (Always Active)
No configuration required. Provides pre-execution confidence scoring and risk assessment.

## System Behavior

### Every Cycle
1. Discovers new opportunities
2. Generates tasks using stage workflows
3. Validates before execution
4. Executes with tool integration
5. Updates business metrics

### Every 5 Cycles - Portfolio Review
```
======================================================================
PORTFOLIO REVIEW
======================================================================

  Businesses Analyzed: 3
  Portfolio Health: concentrated
  Diversification: 0.43

  Recommendations:
    - Consider balancing across lifecycle stages
```

## Verification

### Quick Check
```bash
./verify.sh
```

### Run Tests
```bash
PYTHONPATH=. pytest tests/test_workflows.py -q
```

## Troubleshooting

### Issue: "ModuleNotFoundError"
**Solution**: Run from project root with PYTHONPATH:
```bash
PYTHONPATH=. python3 main.py "your idea"
```
Or use the run script:
```bash
./run.sh "your idea"
```

### Issue: "Validation failed"
**Solution**: Check business metrics meet stage requirements:
- VALIDATING: no special requirements
- BUILDING: validation_score >= 0.5
- SCALING: build_progress >= 0.7
- OPERATING: performance >= 0.6

### Issue: Tools not available
**Solution**: This is expected and normal. Tools are optional. The system works perfectly with the built-in simulator alone.

## Documentation

- `docs/SYSTEM_SUMMARY.md` - System overview
- `docs/VERIFICATION.md` - Verification details
- `docs/ARCHITECTURE.md` - Architecture documentation

## Summary

The system is production-ready with:
- Workflow orchestration
- Pre-execution validation
- Portfolio reviews every 5 cycles
- Tool integration with graceful fallback
- Full backward compatibility

**The system works perfectly without optional tools.**
