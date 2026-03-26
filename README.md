# Project Alpha - Phase 5

**AI-Powered Business Execution System with Multi-Stage Workflow Management**

## Quick Start

```bash
# Navigate to project
cd ~/Desktop/project_alpha

# Run Phase 5 system
python3 main.py "your business idea"

# Verify installation
python3 scripts/verify_phase5.py

# Run tests
python3 -m pytest tests/ -v
```

## What is Phase 5?

Phase 5 is the **Business Execution Workflows** system that manages the complete lifecycle of AI-discovered business opportunities through 7 stages:

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
project_alpha/
├── main.py                    # Entry point
├── core/                      # Phase 5 core modules
│   ├── workflow_orchestrator.py
│   ├── stage_workflows.py
│   ├── portfolio_workflows.py
│   ├── workflow_validator.py
│   └── lifecycle_manager.py
├── agents/                    # Execution agents
│   └── execution/
├── docs/                      # Documentation
│   ├── ARCHITECTURE_FIX.md
│   ├── PHASE5_VERIFICATION.md
│   └── LOCATION_INFO.md
├── tests/                     # Test suite
└── scripts/                   # Utility scripts
```

## Key Features

✅ **Multi-Business Portfolio Management** - Handle up to 5 concurrent businesses
✅ **7-Stage Lifecycle** - Complete business journey automation
✅ **5-Check Validation** - Pre-execution safety framework
✅ **Workflow Templates** - 8 pre-built workflow patterns
✅ **Tool Integration** - Optional AI-Q, NemoClaw, Zep enhancements
✅ **Built-in Simulator** - Always-available prediction engine

## Documentation

- **Quick Start**: `docs/QUICK_START_PHASE5.md`
- **Architecture**: `docs/ARCHITECTURE_FIX.md`
- **Verification**: `docs/PHASE5_VERIFICATION.md`
- **Phase Summary**: `docs/PHASE_5_SUMMARY.md`

## Verification

Run the complete verification suite:

```bash
python3 scripts/verify_phase5.py
```

Expected output: **7/7 checks passed**

## Requirements

- Python 3.8+
- Claude/OpenAI API key (set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`)
- Optional: AI-Q, NemoClaw, Zep API keys for enhancements

## Git Repository

This is a local git repository:
- **Branch**: main
- **Commits**: 4 commits
- **Remote**: Not configured (local only)

## Support

- Issues: File an issue or check documentation in `docs/`
- Architecture Questions: See `docs/ARCHITECTURE_FIX.md`
- Quick Access: Use `pa` alias or `cd ~/Desktop/project_alpha`
