# Project Alpha - System Summary

## Overview

Project Alpha is an AI-powered business lifecycle engine that manages multiple businesses through their complete lifecycle using workflow orchestration.

## Core Components

### Workflow Orchestrator (`core/workflow_orchestrator.py`)
Central execution engine with optional tool integration:
- AI-Q for advanced reasoning
- NemoClaw for sandbox validation
- Zep for memory persistence
- Built-in Simulator (always available)

### Stage Workflows (`core/stage_workflows.py`)
Defines tasks and execution logic for all 7 lifecycle stages:
1. DISCOVERED - Market research, competitive analysis
2. VALIDATING - Problem validation, pricing research
3. BUILDING - Architecture design, implementation
4. SCALING - Marketing, infrastructure scaling
5. OPERATING - Monitoring, revenue optimization
6. OPTIMIZING - Bottleneck analysis, cost optimization
7. TERMINATED - Final reports, lessons learned

### Portfolio Workflows (`core/portfolio_workflows.py`)
Manages up to 5 concurrent businesses with:
- Intelligent task prioritization
- Load balancing
- Portfolio-level health monitoring

### Workflow Validator (`core/workflow_validator.py`)
Pre-execution safety framework with 5-check validation.

## Running the System

```bash
# One command to run
./run.sh "your business idea"

# One command to verify
./verify.sh
```

## Architecture Principles

1. **Graceful Degradation** - Optional tools enhance but never block execution
2. **Simulator Always Available** - Built-in fallback for all AI operations
3. **Multi-Business Support** - Handle up to 5 concurrent businesses
4. **Validation First** - All tasks validated before execution
5. **Tool Integration** - Pluggable enhancement system

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point |
| `run.sh` | One-command runner |
| `verify.sh` | One-command verification |
| `core/` | All Python modules |
| `tests/` | Test suite |
| `scripts/` | Utility scripts |
