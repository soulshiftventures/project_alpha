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

# Full startup with readiness check
./run_full.sh

# Check system readiness
./check_ready.sh

# Start UI only
./run_ui.sh

# Verify everything works
./verify.sh
```

**Note:** This project runs in **simulator mode** by default. No API keys are required.
The built-in simulator handles all AI-related operations for testing and development.

## Deployment & First-Use Setup

### Readiness Check

Before running the system, verify readiness:

```bash
# Full readiness check
./check_ready.sh

# Quick check
./check_ready.sh --quick

# Include health status
./check_ready.sh --health

# JSON output (for automation)
./check_ready.sh --json
```

### Startup Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Full Startup** | `./run_full.sh` | Check readiness, initialize, start UI |
| **UI Only** | `./run_ui.sh` | Start operator interface only |
| **Skip Checks** | `./run_full.sh --skip-check` | Start without readiness check |
| **Debug Mode** | `./run_full.sh --debug` | Start with Flask debug mode |

### First-Use Checklist

1. **Create data directory:** `mkdir -p project_alpha/data`
2. **Copy environment template:** `cp .env.example .env`
3. **Configure credentials:** Edit `.env` with your API keys
4. **Install dependencies:** `pip install flask httpx`
5. **Run system:** `./run_full.sh`

### Key URLs

| URL | Purpose |
|-----|---------|
| http://localhost:5000 | Home - Outcome-Oriented Dashboard |
| http://localhost:5000/discover | **Discover - Market Discovery with Persistence & Enrichment** |
| http://localhost:5000/work-queue | Work - Unified Work Queue |
| http://localhost:5000/approvals | Approvals - Review Pending Actions |
| http://localhost:5000/events | History - Event Log |
| http://localhost:5000/admin | Admin - System Internals & Configuration |

### Dry-Run vs Live Mode

- **Dry-Run Mode:** Always available, no credentials required
- **Live Mode:** Requires credentials per connector

| Connector | Credentials Required | Live-Capable |
|-----------|---------------------|--------------|
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Yes |
| Tavily | `TAVILY_API_KEY` | Yes |
| SendGrid | `SENDGRID_API_KEY` | Yes |
| HubSpot | `HUBSPOT_API_KEY` | Yes |
| Firecrawl | `FIRECRAWL_API_KEY` | Yes |
| Apollo | `APOLLO_API_KEY` | Placeholder |

## Alternative Commands

```bash
# Run integration verification only
python3 scripts/verify_system.py

# Run test suite only
python3 -m pytest tests/ -v

# Run readiness check programmatically
PYTHONPATH=. python3 -c "from core.readiness_checker import check_readiness; print(check_readiness().to_dict())"
```

## Overview

Project Alpha is a **Domain-Neutral AI-Powered Execution System** that orchestrates work across multiple business and operational domains. The system manages complete execution lifecycles through 7 stages:

1. **DISCOVERED** - Initial opportunity identification
2. **VALIDATING** - Market and feasibility validation
3. **BUILDING** - Implementation and development
4. **SCALING** - Growth and expansion
5. **OPERATING** - Day-to-day management
6. **OPTIMIZING** - Performance tuning
7. **TERMINATED** - Graceful shutdown

### Execution Domains

Project Alpha supports **14 execution domains** for domain-neutral operation planning and skill selection:

**Knowledge & Strategy**
- **Research** - Market research, competitive intelligence, data gathering
- **Strategy** - Strategic planning, business strategy, decision analysis
- **Planning** - Project planning, resource allocation, coordination

**Product & Engineering**
- **Product** - Product development, feature planning, requirements
- **Engineering** - Software development, technical implementation
- **Validation** - Testing, QA, verification, quality assurance

**Operations & Execution**
- **Operations** - Day-to-day operations, process execution
- **Automation** - Workflow automation, process automation
- **Internal Admin** - Internal administration, housekeeping, maintenance

**Finance & Compliance**
- **Finance** - Financial planning, budgeting, accounting
- **Compliance** - Legal compliance, regulatory requirements, auditing

**Customer & Growth**
- **Growth** - Business growth, expansion, scaling, market development
- **Customer Support** - Customer service, support, relationship management

**Content & Communication**
- **Content** - Content creation, documentation, knowledge management

Goals submitted to the system are automatically classified into domains, affecting:
- **Skill Selection** - Domain-appropriate skills, commands, and connectors
- **Cost Estimation** - Domain-specific cost modifiers (0.6x to 1.3x)
- **Policy Enforcement** - Domain-based approval and budget rules
- **Execution Routing** - Domain-to-department workflow routing

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

### Persistent State Layer

The Persistent State Layer provides durable storage for all execution state using SQLite with WAL mode for concurrent access.

```
┌─────────────────────────────────────────────────────────────────┐
│ PERSISTENT STATE LAYER                                          │
│   state_store.py - SQLite storage with 9 tables                 │
│   persistence_manager.py - Lifecycle and recovery               │
│   history_query.py - Query interface for historical data        │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ APPROVALS        │ │ JOBS/PLANS       │ │ COST RECORDS     │
│ EVENTS           │ │ CREDENTIALS      │ │ BUDGETS          │
│ LIVE PROMOTIONS  │ │ CONNECTOR EXECS  │ │ HISTORY          │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

| Module | Purpose |
|--------|---------|
| `state_store.py` | SQLite storage with thread-safe operations |
| `persistence_manager.py` | Lifecycle management and startup recovery |
| `history_query.py` | Query filters, aggregation, and summaries |

### Cost Governance Layer

The Cost Governance Layer tracks, estimates, and enforces cost limits across all executions.

```
┌─────────────────────────────────────────────────────────────────┐
│ COST GOVERNANCE LAYER                                           │
│   cost_model.py - Estimation and classification                 │
│   cost_tracker.py - Record estimated/actual costs               │
│   budget_manager.py - Budget limits and enforcement             │
│   cost_policies.py - Policy rules for cost decisions            │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ COST ESTIMATION  │ │ BUDGET CHECKS    │ │ POLICY RULES     │
│ Per-connector    │ │ Global/Monthly   │ │ Cost class       │
│ Per-backend      │ │ Per-business     │ │ thresholds       │
│ Per-plan         │ │ Per-connector    │ │ External ops     │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

| Module | Purpose |
|--------|---------|
| `cost_model.py` | Cost estimation with 7 cost classes and domain-aware modifiers |
| `cost_tracker.py` | Track estimated vs actual costs |
| `budget_manager.py` | Budget enforcement with thresholds |
| `cost_policies.py` | Rule-based policy evaluation with domain filtering |
| `execution_domains.py` | Domain metadata, classification, and routing |

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
| `/costs` | Cost Overview - cost summaries, budgets, spend tracking |
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
- `GET /api/costs` - Cost summary
- `GET /api/costs/<business_id>` - Business cost detail
- `GET /api/budgets` - Budget status
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

### How Skills and Domains Affect Execution

When a request is orchestrated through the hierarchy:

1. **Domain Classification**: `chief_orchestrator` classifies the goal into an execution domain using keyword matching and role-based hints
2. **Skill Selection**: Relevant skills, commands, and agents are selected based on the classified domain
3. **Policy Evaluation**: Each selected skill is checked against domain-aware policies (`auto_allowed`, `requires_approval`, `blocked`)
4. **Execution Plan**: A structured `ExecutionPlan` is created with:
   - Primary execution domain
   - Selected skill bundle (skills, commands, agents)
   - Policy decisions for each item
   - Execution steps with domain routing
   - Domain-aware cost estimates
   - Approval status
5. **Domain Routing**: The plan routes to the appropriate department based on domain:
   - `research` → `dept_research` → `stage_workflows.execute_discovered_task()`
   - `strategy` → `dept_operations` → strategic planning workflows
   - `planning` → `dept_planning` → `planning_engine.execute()`
   - `product` → `dept_product` → `stage_workflows.execute_building_task()`
   - `engineering` → `dept_product` → engineering workflows
   - `validation` → `dept_validation` → `stage_workflows.execute_validating_task()`
   - `operations` → `dept_operations` → `stage_workflows.execute_operating_task()`
   - `automation` → `dept_automation` → automation workflows
   - `internal_admin` → `dept_operations` → administrative tasks
   - `finance` → `dept_operations` → financial workflows
   - `compliance` → `dept_operations` → compliance workflows
   - `growth` → `dept_growth` → `stage_workflows.execute_scaling_task()`
   - `customer_support` → `dept_growth` → support workflows
   - `content` → `dept_content` → content creation workflows
6. **Workflow Execution**: Real workflow modules execute with skill and domain context

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
│   ├── state_store.py         # Persistence: SQLite storage
│   ├── persistence_manager.py # Persistence: lifecycle and recovery
│   ├── history_query.py       # Persistence: query interface
│   ├── cost_model.py          # Cost: estimation and classification
│   ├── cost_tracker.py        # Cost: track estimated/actual
│   ├── budget_manager.py      # Cost: budget enforcement
│   ├── cost_policies.py       # Cost: policy rules
│   ├── execution_domains.py   # Domains: classification and metadata
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
│   ├── test_ui_layer.py       # Operator interface tests
│   ├── test_persistence_layer.py # Persistence layer tests
│   ├── test_cost_governance.py # Cost governance tests
│   └── test_execution_domains.py # Domain classification tests
├── scripts/                   # Utility scripts
├── docs/                      # Documentation
└── project_alpha/             # Runtime state (gitignored)
    ├── businesses/
    ├── memory/
    ├── tasks/
    └── logs/                  # Event logs
```

## Business Discovery Layer

Project Alpha includes a **Business Discovery Layer** that helps operators move from rough ideas, problems, interests, or opportunity spaces into structured, evaluated business opportunities.

### Discovery Capabilities

**Input Processing:**
- Accepts rough, ambiguous input about ideas, problems, opportunities, or curiosities
- No need for polished business plans - the system structures your thinking
- Supports exploration from problem spaces, market observations, or "what if" scenarios

**Opportunity Evaluation:**
Opportunities are scored across 12 dimensions:
- **Market Attractiveness** - Market size, growth, competition
- **Monetization Clarity** - How clear is the revenue path?
- **Startup Complexity** - How complex to start?
- **Technical Complexity** - Technical difficulty level
- **Capital Intensity** - Required upfront investment
- **Operational Burden** - Ongoing work requirements
- **Speed to Revenue** - How fast to first dollar?
- **Speed to Validation** - How fast to test hypothesis?
- **Risk Level** - Overall business risk
- **Automation Potential** - How automatable?
- **Scalability Potential** - Growth potential
- **Constraint Fit** - Fit with operator constraints

**Operator Constraints:**
Opportunities are evaluated against your actual situation:
- Maximum initial capital
- Monthly budget
- Available time per week
- Technical complexity tolerance
- Automation preference (hands-on vs hands-off)
- Risk tolerance
- Speed priority

**Recommendations:**
Each opportunity receives a clear recommendation:
- **Pursue Now** - High confidence, good fit, ready to execute
- **Validate First** - Needs testing before committing
- **Archive** - Interesting but not right now
- **Reject** - Poor fit or too risky

**Integration with Execution:**
Opportunities marked "pursue" can flow into the execution system:
- Classified into appropriate execution domains
- Skill selection based on opportunity characteristics
- Execution plans inherit opportunity context
- Cost tracking from opportunity through execution

### Discovery Workflow

```bash
# UI Interface
./run_ui.sh
# Visit http://localhost:5000/discover
# Run discovery scans → View candidates → Convert to opportunities

# Programmatic Interface with Live External Enrichment
from core.market_discovery import MarketDiscoveryEngine, DiscoveryInput

engine = MarketDiscoveryEngine(enable_external_enrichment=True)
discovery_input = DiscoveryInput(
    mode="theme_scan",
    theme="AI automation for small businesses"
)

# Run discovery with external market validation (requires Tavily/Firecrawl credentials)
result = engine.run_discovery(discovery_input, enrich=True)

# Check enrichment evidence
for candidate in result.candidates:
    if candidate.enrichment and candidate.enrichment["enriched"]:
        print(f"Candidate '{candidate.title}' enriched via {candidate.enrichment['signal_source']}")
        for evidence in candidate.enrichment["evidence"]:
            print(f"  - {evidence['source_type']}: {evidence['supporting_notes']}")
```

### Live External Enrichment

**Sprint: Live External Enrichment Integration**

Discovery candidates can now be enriched with real external market signals via Tavily and Firecrawl connectors.

**How it Works:**
1. Discovery scan runs and generates candidates using internal heuristics
2. If `enrich=True` and credentials are available, candidates are enriched with external signals
3. Tavily searches validate market demand and interest
4. Firecrawl scrapes industry sources for problem validation
5. Enrichment evidence is persisted with confidence adjustments

**Enrichment States:**
- `live_success` - External API executed successfully, signals obtained
- `credentials_missing` - Connector available but credentials not configured
- `live_failed` - External API call failed (e.g., rate limit, timeout)
- `skipped` - Enrichment attempted but no suitable data source
- `disabled` - Enrichment not requested
- `error` - Unexpected error during enrichment

**Safe Fallback:**
- If enrichment cannot run, discovery still works with internal signals only
- No external data is fabricated
- Clear evidence tracking shows what came from internal vs external sources

**Governance:**
- All credential gating remains intact
- Approval workflows still apply where configured
- Cost tracking includes external enrichment costs
- No secrets leaked in evidence or references

**UI Display:**
Enrichment evidence shown in discovery results including:
- Signal source (internal, hybrid, external_tavily, external_firecrawl)
- Enrichment status with visual badges
- Evidence items with signal strength, notes, and safe external references
- Confidence adjustments from external signals

### Discovery Modules

| Module | Purpose |
|--------|---------|
| `discovery_models.py` | Data structures for opportunities, constraints, scores |
| `idea_intake.py` | Converts rough text into structured hypotheses |
| `opportunity_scorer.py` | Deterministic multi-dimensional scoring |
| `opportunity_evaluator.py` | Generates recommendations and next steps |
| `discovery_pipeline.py` | End-to-end pipeline orchestration |
| `opportunity_registry.py` | Persistence and comparison |

### Discovery in Chief Orchestrator

The chief orchestrator detects discovery-mode requests and routes them through the discovery pipeline:

```
Request with discovery keywords (idea, opportunity, what if, should we build)
    ↓
Chief Orchestrator detects DISCOVERY_MODE
    ↓
Process through discovery_pipeline
    ↓
Save to opportunity_registry
    ↓
Return evaluated opportunities with scores and recommendations
```

**Discovery Keywords:**
- "idea", "business idea", "opportunity"
- "what if we", "should we build"
- "explore opportunity", "market opportunity"
- "new business", "potential business"

## Key Features

- **Business Discovery Layer** - Transform rough ideas into evaluated opportunities with scoring and recommendations
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
- **Operator Interface** - Lightweight local web UI for operator control with discovery page
- **Persistent State** - SQLite-based durable storage with recovery on restart
- **Cost Governance** - Estimation, tracking, budgets, and policy-based enforcement
- **Production Hardening** - Defensive rendering, safe data access, graceful degradation for missing data
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

### Connector Action Persistence + Audit (Sprint 17)

All connector-backed actions are now durably persisted with full audit trails and safe operator visibility:

- **Persistent Action Records** - Every connector action execution stored with:
  - Execution mode (dry-run/live), status, duration, cost
  - Approval state, approval ID, operator decision references
  - Linked job/plan/opportunity for full traceability
  - Safe request/response/error summaries (credentials redacted)

- **Connector Action History UI** - New operator interface pages:
  - List view with filters (connector, mode, status, related entities)
  - Detail view with safe summaries and related entity navigation
  - Statistics dashboard (success rates, live/dry-run breakdown)

- **Safe Rendering & Redaction** - Credential protection throughout:
  - Automatic redaction of API keys, tokens, secrets from all stored data
  - Safe request/response summaries for UI display
  - Error messages sanitized to prevent credential leaks

- **Query & Filter Support** - Flexible action history queries:
  - Filter by connector, action, mode, status
  - Filter by related job/plan/opportunity
  - Get live actions, failed actions, connector-specific stats

**Why This Matters:** Audit-first approach ensures operator visibility and accountability before expanding live connector execution. Every action is traceable, queryable, and safely rendered.

**Access:** Visit `/connector-actions` in the operator UI to view action history and details.

### Expanded Live Connector Coverage (Sprint 18)

The system now supports additional live-capable connector actions under the existing approval, credential, cost, policy, persistence, and audit systems:

**Newly Live-Capable Actions:**

| Connector | Action | Status | Notes |
|-----------|--------|--------|-------|
| **Tavily** | `search` | ✅ Live | AI-powered web search |
| **Tavily** | `extract` | ✅ Live | URL content extraction |
| **SendGrid** | `send_email` | ✅ Live | Transactional email send |
| **HubSpot** | `create_contact` | ✅ Live | CRM contact creation |
| **HubSpot** | `update_contact` | ✅ Live | CRM contact update |
| **Firecrawl** | `scrape` | ✅ Live | Single URL scraping |

**Still Dry-Run Only:**

| Connector | Action | Reason |
|-----------|--------|--------|
| SendGrid | `send_template` | Template ID validation needed |
| HubSpot | `list_contacts`, `get_contact` | Read ops kept as dry-run for safety |
| HubSpot | `create_deal`, `update_deal`, `list_deals` | Deal write ops pending |
| Firecrawl | `crawl`, `map` | Async job polling needed |
| Telegram | `send_document` | File handling needed |

**Governance:**
- All live actions remain gated by credentials, policies, and approval workflows
- Cost metadata attached to all executions
- Full audit trail with lifecycle persistence
- Safe output handling (credentials redacted)

**Approval Requirements:**
- Tavily search/extract: No approval required (research operations)
- SendGrid send_email: Requires standard approval (external notification)
- HubSpot create/update: Requires standard approval (CRM writes)
- Firecrawl scrape: No approval required (research operation)

### Recovery & Workflow Control (Sprint 19)

The system now provides complete operator recovery and workflow control capabilities for managing paused, blocked, and failed executions.

**New Modules:**

| Module | Purpose |
|--------|---------|
| `core/recovery_manager.py` | Central orchestration for resume, retry, rerun operations |
| `core/operator_actions.py` | Unified operator action interface with audit trail |

**Recovery Operations:**

| Operation | Description | Use Case |
|-----------|-------------|----------|
| **Resume** | Continue paused scenario from where it stopped | After approval granted |
| **Retry** | Re-attempt failed job/step/connector action | Transient failures |
| **Rerun** | Create fresh execution from plan/scenario | Start over with fixes |
| **Skip** | Continue scenario while skipping failed step | Non-critical failures |
| **Cancel** | Terminate running/paused scenario | Abort workflow |

**Blocker Visibility System:**

The system tracks what's blocking workflow progress:

| Blocker Type | Description | Resolution Action |
|--------------|-------------|-------------------|
| `approval_required` | Waiting for operator approval | Approve/deny request |
| `missing_credential` | Required credential not available | Add credential |
| `policy_blocked` | Policy rule prevents action | Modify policy or request |
| `budget_blocked` | Cost exceeds budget limits | Increase budget or modify request |
| `capacity_blocked` | System at capacity | Wait or scale resources |
| `runtime_unavailable` | Execution backend unavailable | Wait or switch backend |
| `live_mode_not_granted` | Action requires live mode approval | Grant live mode |
| `step_failed` | Scenario step execution failed | Retry, skip, or fix |
| `connector_failed` | Connector action failed | Retry or investigate |

**New UI Views:**

| Route | Description |
|-------|-------------|
| `/recovery` | Recovery dashboard with all pending items |
| `/recovery/paused` | Scenarios awaiting action |
| `/recovery/failed` | Failed jobs and actions |
| `/recovery/blockers` | Active blockers across all workflows |
| `/recovery/history` | Recovery action history |

**New API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/recovery/dashboard` | GET | Full recovery dashboard data |
| `/api/recovery/paused` | GET | Paused scenarios list |
| `/api/recovery/failed` | GET | Failed jobs list |
| `/api/recovery/blockers` | GET | Active blockers list |
| `/api/recovery/workflow-status` | GET | Workflow status for scenario/job |
| `/api/recovery/resume/scenario/<run_id>` | POST | Resume paused scenario |
| `/api/recovery/resume/approval/<approval_id>` | POST | Resume after approval |
| `/api/recovery/retry/job/<job_id>` | POST | Retry failed job |
| `/api/recovery/retry/connector/<execution_id>` | POST | Retry connector action |
| `/api/recovery/retry/step/<run_id>/<step_id>` | POST | Retry scenario step |
| `/api/recovery/rerun/plan/<plan_id>` | POST | Rerun execution plan |
| `/api/recovery/rerun/scenario/<run_id>` | POST | Rerun scenario |
| `/api/recovery/skip/step/<run_id>/<step_id>` | POST | Skip failed step |
| `/api/recovery/cancel/scenario/<run_id>` | POST | Cancel scenario |
| `/api/approvals/<id>/approve-with-resume` | POST | Approve and auto-resume |
| `/api/recovery/history` | GET | Recovery action history |

**Approval-to-Resume Flow:**

The system supports automatic workflow resumption after approval:

```
Scenario runs → Hits approval gate → Pauses with AWAITING_APPROVAL status
    ↓
Operator reviews in /approvals
    ↓
Operator approves with "auto_resume=true"
    ↓
System automatically resumes scenario from paused step
    ↓
Scenario continues execution
```

**Audit Trail:**

All recovery operations preserve full audit trail:
- Each resume/retry/rerun creates new records (never overwrites)
- Original failed/paused records preserved for history
- Operator ID and timestamp recorded for all actions
- Action history queryable via API and UI

**Access:** Visit `/recovery` in the operator UI to view and manage blocked workflows.

### Daily Operator Activation (Sprint 20)

The system now provides a streamlined daily operator experience with clear "what do I do next?" guidance and unified work queue.

**Enhanced Dashboard:**

The home dashboard now shows:
- **Attention Banner** - Quick visibility into items needing attention
- **Quick Action Cards** - One-click access to common operator tasks
- **Status Summary** - System health, active jobs, pending approvals, budget status
- **Needs Attention List** - Items requiring immediate operator action with guidance
- **Recent Activity** - Latest operator actions and system events

**Unified Work Queue:**

New `/work-queue` route combines all items needing attention into a single prioritized list:

| Queue Type | Source | Actions Available |
|------------|--------|-------------------|
| Pending Approvals | Approval workflow | Approve, Deny |
| Paused Scenarios | Scenario execution | Resume, Retry, Cancel |
| Failed Jobs | Job execution | Retry, Rerun Plan |
| Active Blockers | Various sources | Resolve, Skip |

**Next-Step Guidance:**

Each work queue item includes actionable guidance:
- **Recommendation** - Plain-language explanation of the situation
- **Primary Action** - Most likely resolution action
- **Secondary Actions** - Alternative actions if primary isn't suitable
- **Context** - Relevant details (risk level, retry count, timestamps)

**Navigation Improvements:**

- Dashboard link renamed for clarity
- Work Queue link prominently placed with attention badge
- Navigation organized by function (Operator Actions, Workflows, Resources, System)
- Visual dividers between navigation sections

**New Routes:**

| Route | Description |
|-------|-------------|
| `/work-queue` | Unified work queue view |
| `/work-queue/action/<id>` | Handle work queue item action |
| `/api/work-queue` | API: Get unified queue |
| `/api/attention-summary` | API: Get attention counts |
| `/api/quick-counts` | API: Get quick action counts |

**Service Layer Helpers:**

| Function | Purpose |
|----------|---------|
| `get_attention_summary()` | Aggregate all items needing attention |
| `get_unified_work_queue()` | Combine and prioritize queue items |
| `get_next_step_guidance()` | Generate actionable recommendations |
| `get_quick_action_counts()` | Count items by category |
| `get_operator_home_data()` | All dashboard data in one call |

**Access:** Visit `/` for the enhanced dashboard or `/work-queue` for the unified work queue.

### Operator Playbook & First-Run Templates (Sprint 21)

The system now provides guided onboarding with operator playbook, reusable workflow templates, and quick-start flows for common tasks.

**Operator Playbook:**

The playbook (`/playbook`) provides comprehensive operator guidance:
- **Getting Started** - First-time setup and system startup
- **Daily Workflow** - Morning checklist and routine tasks
- **Common Workflows** - Step-by-step guides for frequent operations
- **Dry-Run vs Live Mode** - Understanding execution modes
- **Recovery Procedures** - Handling errors and blocked workflows
- **Safety Guidelines** - Best practices and emergency procedures

**Workflow Templates:**

The template registry (`/templates`) provides reusable workflow definitions:

| Template | Category | Mode | Purpose |
|----------|----------|------|---------|
| `discovery_intake` | Discovery | Dry-Run | Submit new business ideas |
| `validation_first` | Research | Live-Capable | Validate opportunities before committing |
| `research_scenario` | Research | Live-Capable | Run market/competitor research |
| `notification_test` | Notification | Live-Capable | Test notification delivery |
| `crm_update` | CRM | Live-Capable | Create/update CRM contacts |
| `connector_health` | Maintenance | Read-Only | Check connector status |

**Quick-Start Flows:**

The quick-start page (`/quickstart`) provides guided step-by-step flows:
- **Start Discovery** - Submit first business idea
- **Run Research Scenario** - Execute research queries
- **Send Test Notification** - Test delivery channels
- **Review Approvals** - Process pending requests
- **Inspect Connector Health** - Verify external services
- **Resume Paused Work** - Handle blocked workflows

**First-Run Recommended Sequence:**

1. Check system readiness (`/readiness`)
2. Complete setup checklist (`/setup`)
3. Run connector health check (template)
4. Submit first discovery (`/discovery`)
5. Review dashboard (`/`)

**New Routes:**

| Route | Description |
|-------|-------------|
| `/playbook` | Operator playbook guide |
| `/quickstart` | Quick-start flows |
| `/templates` | Browse workflow templates |
| `/templates/<id>` | Template detail and launch |
| `/api/playbook` | API: Get playbook content |
| `/api/quickstart` | API: Get quick-start flows |
| `/api/templates` | API: List templates |
| `/api/templates/<id>` | API: Get template detail |
| `/api/templates/<id>/launch` | API: Launch template |
| `/api/templates/launches` | API: List template launches |

**Template Registry Module:**

| Class/Function | Purpose |
|----------------|---------|
| `TemplateRegistry` | Central registry for workflow templates |
| `WorkflowTemplate` | Template definition with inputs, steps, metadata |
| `TemplateInput` | Input field definition (text, select, etc.) |
| `TemplateStep` | Execution step with action type and parameters |
| `TemplateLaunch` | Record of template execution |
| `get_template_registry()` | Get singleton registry instance |

**Access:** Visit `/playbook` for operator guidance, `/templates` to browse templates, or `/quickstart` for guided flows.

