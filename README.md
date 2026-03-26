# Project Alpha

**AI-Powered Business Execution System with Multi-Stage Workflow Management**

## Location

```
/Users/krissanders/Desktop/project_alpha_working
```

## Quick Start (Operators)

```bash
# Navigate to project
cd /Users/krissanders/Desktop/project_alpha_working

# Run the system (one command)
./run.sh "your business idea"

# Verify everything works (one command)
./verify.sh
```

**Note:** This project runs in **simulator mode** by default. No API keys are required.
The built-in simulator handles all AI-related operations for testing and development.

## Alternative Commands

```bash
# Run integration verification only
python3 scripts/verify_system.py

# Run test suite only
python3 -m pytest tests/ -v
```

## Overview

Project Alpha is a **Business Execution Workflows** system that manages the complete lifecycle of AI-discovered business opportunities through 7 stages:

1. **DISCOVERED** - Initial opportunity identification
2. **VALIDATING** - Market and feasibility validation
3. **BUILDING** - Implementation and development
4. **SCALING** - Growth and expansion
5. **OPERATING** - Day-to-day management
6. **OPTIMIZING** - Performance tuning
7. **TERMINATED** - Graceful shutdown

## Architecture

### Primary Execution Engine
- **Claude/OpenAI** - Primary LLM execution (always works)

### Optional Enhancements
- **AI-Q** - Advanced reasoning (optional)
- **NemoClaw** - Sandbox validation (optional)
- **Zep** - Memory persistence (optional)
- **Simulator** - Built-in prediction engine (always available)

**All optional tools enhance but never block execution.**

## Project Structure

```
project_alpha_working/
├── main.py                    # Entry point
├── run.sh                     # One-command runner
├── verify.sh                  # One-command verification
├── core/                      # Core Python modules
│   ├── workflow_orchestrator.py
│   ├── stage_workflows.py
│   ├── portfolio_workflows.py
│   ├── workflow_validator.py
│   ├── lifecycle_manager.py
│   └── ai_client.py
├── agents/                    # Execution agents
│   └── execution/
├── tests/                     # Test suite
├── scripts/                   # Utility scripts
├── docs/                      # Documentation
└── project_alpha/             # Runtime state (gitignored)
    ├── businesses/
    ├── memory/
    └── tasks/
```

## Key Features

- **Multi-Business Portfolio Management** - Handle up to 5 concurrent businesses
- **7-Stage Lifecycle** - Complete business journey automation
- **5-Check Validation** - Pre-execution safety framework
- **Workflow Templates** - 8 pre-built workflow patterns
- **Tool Integration** - Optional AI-Q, NemoClaw, Zep enhancements
- **Built-in Simulator** - Always-available prediction engine

## Runtime State (What Changes When You Run)

When the system runs, it creates/modifies files in `project_alpha/`:

| Directory | Purpose | Committed? |
|-----------|---------|------------|
| `project_alpha/businesses/` | Active business portfolio state | No (gitignored) |
| `project_alpha/memory/` | Long-term memory storage | No (gitignored) |
| `project_alpha/tasks/` | Task queue and history | No (gitignored) |

**Source files** (committed):
- `core/` - All Python modules
- `tests/` - Test suite
- `scripts/` - Utility scripts
- `docs/` - Documentation

**To reset runtime state**, delete the `project_alpha/` subdirectories:
```bash
rm -rf project_alpha/businesses project_alpha/memory project_alpha/tasks
```

## Documentation

- **Quick Start**: `docs/QUICK_START.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Verification**: `docs/VERIFICATION.md`
- **System Summary**: `docs/SYSTEM_SUMMARY.md`

## Verification

Run the complete verification suite:

```bash
./verify.sh
```

Expected output: **7/7 checks passed**

## Requirements

- Python 3.8+
- pytest (for running tests): `pip install pytest`

### Optional (for live AI mode)
- Claude API key: set `ANTHROPIC_API_KEY` environment variable
- OpenAI API key: set `OPENAI_API_KEY` environment variable
- AI-Q, NemoClaw, Zep API keys for optional enhancements

**Without API keys, the system runs in simulator mode with full functionality.**

## Git Repository

- **Branch**: main
- **Remote**: Not configured (local only)

### What to Commit

**Commit these** (source code):
- `core/` - Core Python modules
- `agents/` - Execution agents
- `tests/` - Test suite
- `scripts/` - Utility scripts
- `docs/` - Documentation
- `main.py`, `run.sh`, `verify.sh` - Entry points
- `.gitignore` - Ignore rules

**Do NOT commit** (runtime state, gitignored):
- `project_alpha/` - All runtime state directories
- `__pycache__/` - Python bytecode
- `.pytest_cache/` - Test cache

## Verification

Expected results when running `./verify.sh`:
- Integration verification: **7/7 checks passed**
- Test suite: **55 tests passed**

## Support

- Issues: File an issue or check documentation in `docs/`
- Architecture Questions: See `docs/ARCHITECTURE.md`
- Quick Access: `cd /Users/krissanders/Desktop/project_alpha_working`
