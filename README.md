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

### Agent Hierarchy

Project Alpha implements a layered agent hierarchy for coordinated decision-making:

```
┌─────────────────────────────────────────────────────────────────┐
│ PRINCIPAL LAYER - Human operator (Kris) with final authority   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ EXECUTIVE LAYER - chief_orchestrator                           │
│   Central coordinator, routes requests through hierarchy        │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ COUNCIL LAYER    │ │ BOARD LAYER      │ │ C-SUITE LAYER    │
│ council_manager  │ │ decision_board   │ │ CEO, COO, CFO    │
│ + 3 advisors     │ │ Options/Voting   │ │ CTO, CMO         │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ DEPARTMENT LAYER                                                │
│   research, planning, product, operations, growth,              │
│   content, automation, validation                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ EXECUTION SUBSTRATE                                             │
│   Existing workflow engine: stage_workflows, portfolio_workflows│
│   workflow_orchestrator, lifecycle_manager, validation          │
└─────────────────────────────────────────────────────────────────┘
```

### Hierarchy Modules

| Module | Purpose |
|--------|---------|
| `agent_contracts.py` | Standard request/response structures for all agent interactions |
| `agent_registry.py` | Central registry for all agents with capability lookup |
| `hierarchy_definitions.py` | Default hierarchy layers and built-in agent definitions |
| `event_logger.py` | Structured logging for orchestration and decisions |
| `approval_manager.py` | Policy-based classification (auto_allowed, requires_approval, blocked) |
| `council_manager.py` | Coordinates strategic advisors, gathers recommendations |
| `decision_board.py` | Evaluates options, resolves conflicts, selects direction |
| `chief_orchestrator.py` | Central entry point, routes through hierarchy layers |

### Skill Intelligence Layer

The Skill Intelligence Layer enables hierarchy roles and execution agents to select, recommend, combine, and govern real Claude Code skills, commands, and specialized agents.

```
┌─────────────────────────────────────────────────────────────────┐
│ EXTERNAL REFERENCE LIBRARY (read-only)                          │
│   ~/Desktop/AI_Tools_Reference/                                 │
│   └── Skills (935), Commands (25), Agents (19)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ SKILL REGISTRIES                                                │
│   skill_registry.py - Load/normalize 935 skills                 │
│   command_registry.py - Load/normalize 25 commands              │
│   specialized_agent_registry.py - Load/normalize 19 agents      │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ SKILL SELECTOR   │ │ ROLE MAPPINGS    │ │ SKILL POLICIES   │
│ Multi-source     │ │ Role→Skill maps  │ │ auto_allowed/    │
│ selection logic  │ │ per layer        │ │ requires_approval│
└──────────────────┘ └──────────────────┘ │ /blocked         │
              │               │           └──────────────────┘
              └───────────────┼───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ EXECUTION PLAN                                                  │
│   execution_plan.py - Structured plans with steps and bundles   │
│   SkillBundle, ExecutionStep, ExecutionPlan dataclasses        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────��────────────────────────────────────────────┐
│ SKILL COMPOSER                                                  │
│   Multi-skill composition, workflow patterns                    │
│   8+ pre-built patterns (feature_dev, security_audit, etc.)     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ SKILL-AWARE EXECUTION                                           │
│   chief_orchestrator → execution_plan → workflow modules        │
│   Routes to stage_workflows, workflow_orchestrator              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ RUNTIME ABSTRACTION LAYER                                       │
│   runtime_manager.py - Backend selection and dispatch           │
│   execution_backends.py - Interchangeable execution backends    │
│   job_dispatcher.py - Job lifecycle management                  │
│   worker_registry.py - Worker type management                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ OPERATOR INTERFACE LAYER                                        │
│   ui/app.py - Flask web interface for operator control          │
│   ui/services.py - Service layer for backend access             │
│   Templates for all views (home, portfolio, goals, etc.)        │
└─────────────────────────────────────────────────────────────────┘
```

| Module | Purpose |
|--------|---------|
| `skill_registry.py` | Load and normalize 935 skills from external reference |
| `command_registry.py` | Load and normalize 25 pre-built commands |
| `specialized_agent_registry.py` | Load and normalize 19 specialized agents |
| `skill_selector.py` | Multi-source skill selection with scoring |
| `role_skill_mappings.py` | Map hierarchy roles to allowed skills |
| `skill_policies.py` | Policy-based skill governance (auto/approval/blocked) |
| `skill_composer.py` | Multi-skill composition with workflow patterns |
| `execution_plan.py` | Structured execution plans with skill bundles |

### Runtime Abstraction Layer

The Runtime Abstraction Layer provides interchangeable execution backends for running execution plans. This allows the system to run locally now and later support containerized and Kubernetes-style execution without redesigning the system.

```
┌─────────────────────────────────────────────────────────────────┐
│ EXECUTION PLAN (from Skill Layer)                               │
│   ExecutionPlan with steps, skill bundle, domain routing        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ RUNTIME MANAGER                                                 │
│   Accepts ExecutionPlan, selects backend, dispatches jobs       │
│   Auto-selection based on plan characteristics                  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ INLINE_LOCAL     │ │ QUEUE_LOCAL      │ │ CONTAINER/K8S    │
│ Synchronous      │ │ Thread pool      │ │ Scaffold backends│
│ Single-threaded  │ │ Parallel steps   │ │ Future-ready     │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ JOB DISPATCHER                                                  │
│   Job lifecycle: create, submit, track, complete                │
│   Callbacks for job events                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ WORKER REGISTRY                                                 │
│   Worker types: general, research, planning, product, etc.      │
│   Worker instances with status tracking                         │
└─────────────────────────────────────────────────────────────────┘
```

| Module | Purpose |
|--------|---------|
| `runtime_manager.py` | Central coordinator for backend selection and job dispatch |
| `execution_backends.py` | Backend interface and 4 implementations |
| `job_dispatcher.py` | Job lifecycle management across backends |
| `worker_registry.py` | Worker type definitions and instance tracking |

### Operator Interface Layer

The Operator Interface Layer provides a lightweight local web interface for operator control of Project Alpha.

```
┌─────────────────────────────────────────────────────────────────┐
│ OPERATOR INTERFACE                                              │
│   Flask web app with HTML views and JSON API                    │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ HTML VIEWS       │ │ SERVICE LAYER    │ │ JSON API         │
│ home, portfolio, │ │ OperatorService  │ │ /api/* endpoints │
│ goals, plans,    │ │ Unified backend  │ │ Programmatic     │
│ approvals, jobs, │ │ access           │ │ access           │
│ events, backends │ │                  │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND INTEGRATION                                             │
│   chief_orchestrator, runtime_manager, approval_manager,        │
│   event_logger, job_dispatcher                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Module | Purpose |
|--------|---------|
| `ui/app.py` | Flask application with all routes |
| `ui/services.py` | Service layer for clean backend access |
| `ui/templates/` | HTML templates for all views |
| `ui/static/` | CSS styling |

#### Running the Operator Interface

```bash
# Quick start
./run_ui.sh

# Or directly with Python
PYTHONPATH=. python3 ui/app.py

# With debug mode
./run_ui.sh --debug

# On custom port
PORT=8080 ./run_ui.sh
```

Then visit http://localhost:5000

#### Available Views

| Route | Description |
|-------|-------------|
| `/` | System Overview - status, recent events, quick actions |
| `/portfolio` | Portfolio View - list businesses and initiatives |
| `/goals` | Goal Submission - submit requests to the system |
| `/plans` | Execution Plans - view and track plans |
| `/approvals` | Approval Queue - review and approve pending requests |
| `/jobs` | Job Monitor - track running and completed jobs |
| `/events` | Event Log - system events and activity |
| `/backends` | Backends - available execution backends |

#### API Endpoints

All views have corresponding JSON API endpoints at `/api/*`:
- `GET /api/status` - System status
- `GET /api/portfolio` - Portfolio list
- `POST /api/goals` - Submit goal
- `GET /api/plans` - List plans
- `GET /api/approvals` - Pending approvals
- `POST /api/approvals/<id>/approve` - Approve request
- `POST /api/approvals/<id>/deny` - Deny request
- `GET /api/jobs` - List jobs
- `GET /api/events` - List events
- `GET /api/backends` - List backends

### Execution Backends

| Backend | Type | Description |
|---------|------|-------------|
| `InlineLocalBackend` | Production | Synchronous in-process execution |
| `QueueLocalBackend` | Production | Thread pool with parallel step execution |
| `StubContainerBackend` | Scaffold | Future container-based execution |
| `StubKubernetesBackend` | Scaffold | Future Kubernetes job execution |

**Note:** Container and Kubernetes backends are scaffolds that return deterministic structured results. They are ready for future infrastructure work but do not execute actual containers or K8s jobs.

### Backend Auto-Selection

The runtime manager automatically selects backends based on plan characteristics:
- **Small plans (< 3 steps)**: Uses `INLINE_LOCAL` for simplicity
- **Large plans (≥ 3 steps)**: Uses `QUEUE_LOCAL` for parallelism
- **Explicit selection**: Any backend can be requested directly

### Event Logging for Runtime

The event logger tracks all runtime activities:
- `RUNTIME_INITIALIZED` - Runtime manager initialized
- `BACKEND_SELECTED` - Backend chosen for execution
- `JOB_DISPATCHED` - Job submitted to backend
- `JOB_STARTED` / `JOB_COMPLETED` / `JOB_FAILED` - Job lifecycle
- `STEP_STARTED` / `STEP_COMPLETED` / `STEP_FAILED` - Step lifecycle
- `WORKER_SPAWNED` / `WORKER_ASSIGNED` / `WORKER_RELEASED` - Worker events

### How Skills Affect Execution

When a request is orchestrated through the hierarchy:

1. **Skill Selection**: `chief_orchestrator` selects relevant skills, commands, and agents for the task
2. **Policy Evaluation**: Each selected skill is checked against policies (`auto_allowed`, `requires_approval`, `blocked`)
3. **Execution Plan**: A structured `ExecutionPlan` is created with:
   - Selected skill bundle (skills, commands, agents)
   - Policy decisions for each item
   - Execution steps with domain routing
   - Approval status
4. **Domain Routing**: The plan routes to the appropriate department based on domain:
   - `research` → `dept_research` → `stage_workflows.execute_discovered_task()`
   - `planning` → `dept_planning` → `planning_engine.execute()`
   - `product` → `dept_product` → `stage_workflows.execute_building_task()`
   - `validation` → `dept_validation` → `stage_workflows.execute_validating_task()`
   - `growth` → `dept_growth` → `stage_workflows.execute_scaling_task()`
   - `operations` → `dept_operations` → `stage_workflows.execute_operating_task()`
5. **Workflow Execution**: Real workflow modules execute with skill context

### Approval Policies

Skills are classified into three categories:

| Policy | Description | Example Skills |
|--------|-------------|----------------|
| `auto_allowed` | Can be used immediately | Most research, documentation skills |
| `requires_approval` | Needs principal approval | `stripe-automation`, `deployment-automation` |
| `blocked` | Cannot be used by role | Globally blocked or role-restricted |

Sensitive categories that always require approval:
- Payment & E-commerce
- Security & Compliance
- Deployment & DevOps

### Event Logging for Skills

The event logger tracks all skill-related activities:
- `SKILLS_SELECTED` - Skills, commands, agents selected for task
- `SKILL_POLICY_EVALUATED` - Policy decision for each skill
- `SKILL_BLOCKED` - Skill blocked by policy
- `SKILL_APPROVAL_REQUIRED` - Skill requires approval
- `WORKFLOW_COMPOSED` - Multi-skill workflow created
- `EXECUTION_PLAN_CREATED` - Structured plan created
- `EXECUTION_PLAN_COMPLETED` - Plan execution finished

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
├── run_ui.sh                  # Operator interface launcher
├── verify.sh                  # One-command verification
├── core/                      # Core Python modules
│   ├── chief_orchestrator.py  # Hierarchy: central coordinator
│   ├── council_manager.py     # Hierarchy: strategic advisors
│   ├── decision_board.py      # Hierarchy: decision resolution
│   ├── agent_registry.py      # Hierarchy: agent registry
│   ├── agent_contracts.py     # Hierarchy: request/response contracts
│   ├── hierarchy_definitions.py # Hierarchy: layer/agent definitions
│   ├── event_logger.py        # Hierarchy: structured logging
│   ├── approval_manager.py    # Hierarchy: policy-based approvals
│   ├── skill_registry.py      # Skills: load 935 skills from reference
│   ├── command_registry.py    # Skills: load 25 commands
│   ├── specialized_agent_registry.py # Skills: load 19 agents
│   ├── skill_selector.py      # Skills: multi-source selection
│   ├── role_skill_mappings.py # Skills: role to skill mappings
│   ├── skill_policies.py      # Skills: usage governance
│   ├── skill_composer.py      # Skills: workflow composition
│   ├── execution_plan.py      # Skills: structured execution plans
│   ├── runtime_manager.py     # Runtime: backend selection and dispatch
│   ├── execution_backends.py  # Runtime: interchangeable backends
│   ├── job_dispatcher.py      # Runtime: job lifecycle management
│   ├── worker_registry.py     # Runtime: worker type management
│   ├── workflow_orchestrator.py # Execution engine
├── ui/                        # Operator Interface
│   ├── __init__.py            # Package init
│   ├── app.py                 # Flask application
│   ├── services.py            # Service layer
│   ├── templates/             # HTML templates
│   └── static/                # CSS/JS assets
│   ├── stage_workflows.py
│   ├── portfolio_workflows.py
│   ├── workflow_validator.py
│   ├── lifecycle_manager.py
│   └── ai_client.py
├── agents/                    # Execution agents
│   └── execution/
├── tests/                     # Test suite
│   ├── test_workflows.py      # Workflow engine tests (55 tests)
│   ├── test_hierarchy.py      # Hierarchy system tests (58 tests)
│   ├── test_skill_layer.py    # Skill layer tests
│   ├── test_skill_aware_orchestration.py # Skill-aware orchestration tests
│   ├── test_runtime_layer.py  # Runtime abstraction layer tests
│   └── test_ui_layer.py       # Operator interface tests
├── scripts/                   # Utility scripts
├── docs/                      # Documentation
└── project_alpha/             # Runtime state (gitignored)
    ├── businesses/
    ├── memory/
    ├── tasks/
    └── logs/                  # Event logs
```

## Key Features

- **Agent Hierarchy** - Layered command structure with principal, executive, council, board, c-suite, and department agents
- **Multi-Business Portfolio Management** - Handle up to 5 concurrent businesses
- **7-Stage Lifecycle** - Complete business journey automation
- **5-Check Validation** - Pre-execution safety framework
- **Workflow Templates** - 8 pre-built workflow patterns
- **Policy-Based Approvals** - Auto-allow, require-approval, or block based on policies
- **Structured Decision Making** - Council recommendations + board voting
- **Skill Intelligence** - 935 skills, 25 commands, 19 agents with policy governance
- **Workflow Composition** - 8 pre-built workflow patterns for common tasks
- **Runtime Abstraction** - Interchangeable backends (local, container, Kubernetes scaffolds)
- **Operator Interface** - Lightweight local web UI for operator control
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
