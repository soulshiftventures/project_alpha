# Project Alpha - Sprint Handoff

## 1. Project

- **Name:** Project Alpha
- **Repo Path:** `/Users/krissanders/Desktop/project_alpha_working`
- **GitHub:** https://github.com/soulshiftventures/project_alpha.git
- **Current Tag:** v0.3.1

## 2. Current Verified Baseline

**Major Layers:**
- Agent Hierarchy (principal, executive, council, board, c-suite, departments)
- Skill Intelligence Layer (935 skills, 25 commands, 19 agents)
- Runtime Abstraction Layer (inline/queue local backends)
- Operator Interface Layer (Flask web UI with approval actions)
- Safe Live Integration Layer (connectors, credentials, policies)
- Approval Workflow Layer (execution triggering, live-mode promotion)

**Verify Commands:**
```bash
./verify.sh                    # 7/7 checks
PYTHONPATH=. pytest -q         # 391 tests
```

**Status:** All tests passing, baseline stable.

## 3. Current Live vs Dry-Run State

| Component | State |
|-----------|-------|
| Agent hierarchy | Simulator (no live LLM calls) |
| Skill selection/composition | Live logic, dry-run execution |
| Runtime backends | INLINE_LOCAL and QUEUE_LOCAL work; container/k8s are stubs |
| Connectors (Tavily, Apollo, HubSpot, etc.) | Scaffolded, dry-run by default |
| Credential management | Live (env-based secrets, rotation tracking) |
| Live mode promotion | Gated by policy, credentials, and approval |

**Approval Requirements:**
- Payment/e-commerce skills: requires_approval
- Security/compliance skills: requires_approval
- Deployment/devops skills: requires_approval
- High-risk connector operations: REQUIRES_APPROVAL policy
- Live mode execution: requires explicit promotion per-operation

## 4. Key Modules

| Module | Purpose |
|--------|---------|
| `core/chief_orchestrator.py` | Central request routing through hierarchy |
| `core/skill_selector.py` | Multi-source skill selection with scoring |
| `core/skill_composer.py` | Multi-skill workflow composition |
| `core/runtime_manager.py` | Backend selection and job dispatch |
| `core/integration_skill.py` | Bridges connectors to skill layer |
| `core/secrets_manager.py` | Credential storage with redaction |
| `core/credential_policies.py` | Rate limiting, expiration, validation |
| `core/integration_policies.py` | Connector approval and risk policies |
| `core/approval_workflow.py` | Workflow items with execution triggering |
| `core/live_mode_controller.py` | Governed live-mode promotion |
| `integrations/registry.py` | Connector registry and health checks |
| `ui/app.py` | Flask operator interface |
| `ui/services.py` | Service layer for UI actions |

## 5. Operator Interface

**Launch:**
```bash
./run_ui.sh
# or: PYTHONPATH=. python3 ui/app.py
```

**URL:** http://localhost:5000

**Routes:**
| Route | Purpose |
|-------|---------|
| `/` | System overview |
| `/portfolio` | Business portfolio |
| `/goals` | Submit requests |
| `/plans` | Execution plans |
| `/plans/<id>` | Plan detail with approval/execution info |
| `/approvals` | Approval queue |
| `/approvals/<id>` | Approval detail with approve/deny/promote actions |
| `/jobs` | Job monitor |
| `/jobs/<id>` | Job detail with retry/cancel actions |
| `/events` | Event log |
| `/backends` | Execution backends |
| `/integrations` | Connector status |
| `/credentials` | Credential health |

**New API Routes:**
| Route | Method | Purpose |
|-------|--------|---------|
| `/api/approvals/<id>` | GET | Approval detail JSON |
| `/api/live-mode/summary` | GET | Live mode status summary |
| `/api/live-mode/check` | POST | Check if operation can go live |
| `/api/live-mode/promote` | POST | Promote to live mode |
| `/api/live-mode/promotions` | GET | Active live promotions |
| `/api/live-mode/standing-approvals` | GET | Standing approval list |

## 6. Current Sprint Status

**Completed:** Approval Workflow + Real Operator Control

**Accomplished:**
- Approval workflow module (`core/approval_workflow.py`)
  - WorkflowItemContext with rich metadata
  - Approval/denial flow with callbacks
  - Execution triggering on approval
- Live mode controller (`core/live_mode_controller.py`)
  - Multi-gate checks (blocked operations, policy, credentials, approval)
  - Promotion records for live execution
  - Standing approvals for repeated operations
- Enhanced approval manager with execution linkage
- Extended event logger with 10+ new event types
- UI service layer with comprehensive actions:
  - approve_request with live promotion
  - deny_request with rationale
  - retry_job for failed jobs
  - cancel_job for running jobs
  - get_plan_detail with full context
  - get_job_detail with action flags
  - Live mode check and promotion APIs
- New templates:
  - approval_detail.html with approve/deny/promote UI
  - Enhanced job_detail.html with retry/cancel
  - Enhanced plan_detail.html with execution context
- Comprehensive tests (49 new tests for approval workflow)
- All 391 tests passing

**What This Sprint Enables:**
1. Operators can view pending approvals with full context (connector, operation, risk level)
2. Operators can approve or deny requests with rationale
3. Approved items can optionally be promoted to live mode per-operation
4. Failed jobs can be marked for retry
5. Running jobs can be cancelled
6. All actions are logged to the event system
7. Live mode requires: policy pass + credentials + approval
8. Blocked operations (delete_all, purge, etc.) are never allowed live

## 7. Live Mode Control Flow

```
Request → Policy Check → Credential Check → Approval Check → Live Mode Gate
                ↓              ↓                 ↓               ↓
           If denied,     If missing,      If required,    If all pass,
           block live     block live       wait approval   allow promotion
```

**Blocked Operations (never allowed live):**
- delete_all
- purge
- reset_database
- bulk_delete

**High-Risk Connectors (per-operation approval required):**
- sendgrid
- hubspot

## 8. Next Recommended Sprint

**Sprint:** Live Connector Activation

**Description:** Enable one connector (e.g., Tavily) for actual live API calls:
1. Configure credentials via environment
2. Test dry-run execution
3. Request approval for live execution
4. Promote specific operation to live
5. Execute real API call
6. Verify rate limiting and audit logging

## 9. Restart Instructions

```bash
cd /Users/krissanders/Desktop/project_alpha_working

# Verify baseline
./verify.sh
PYTHONPATH=. pytest -q

# Check git status
git status
git log --oneline -5

# Launch UI (optional)
./run_ui.sh
```

**First Actions for New Session:**
1. Run `./verify.sh` to confirm baseline (391 tests)
2. Read this file for current state
3. Check `/approvals` route in UI for approval queue
4. Review `core/approval_workflow.py` for workflow item handling
5. Review `core/live_mode_controller.py` for live promotion flow
6. Test approval flow: create approval → approve with promote_to_live → check promotion
