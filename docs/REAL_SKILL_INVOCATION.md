# Real Skill Invocation - Seed Core Sprint 2

**Status**: ✅ COMPLETE - Real skill invocation wiring connected

**Date**: 2026-03-28

## What Was Built

Seed Core v1 now has **real skill invocation** connected. The execution loop is no longer a stub - it routes to actual skill execution where feasible.

## Execution Modes

Seed Core supports 6 distinct execution modes:

### 1. REAL_LOCAL ✅
**Safe local CLI-based invocation**

- Used for: Code review, testing, documentation, debugging
- Invocation: `claude skill <skill-name> --prompt "<description>"`
- Timeout: 30 seconds
- Failures: Gracefully handled with error capture

**Skills in this mode:**
- code-reviewer
- test-engineer
- systematic-debugging
- askgpt
- docs-writer
- api-documenter
- refactor-expert
- performance-tuner
- security-auditor
- All skills in TESTING_QA, DEVELOPMENT_TOOLS, ARCHITECTURE_PLANNING categories

### 2. CONNECTOR_BACKED ✅
**Real external API invocation via connectors**

- Used for: External service integrations (Apollo, Stripe, etc.)
- Invocation: Via IntegrationSkill → ConnectorRegistry → BaseConnector
- Governance: Policy checks, credential validation, approval workflows
- Tracking: Full audit trail via ConnectorActionHistory

**Skill-to-connector mappings:**
- apollo-automation → apollo
- hubspot-automation → hubspot
- stripe-automation → stripe
- sendgrid-automation → sendgrid
- twilio-automation → twilio
- asana-automation → asana
- notion-automation → notion

**Categories supporting connectors:**
- LEAD_GENERATION
- EMAIL_COMMUNICATION
- PAYMENT_ECOMMERCE
- PROJECT_MANAGEMENT

### 3. DRY_RUN ⚠️
**Simulated execution (fallback)**

- Used when: CLI not available, or no other path exists
- Outcome: Partial success (quality_score = 0.5)
- Purpose: Testing, development, safe fallback

### 4. BLOCKED_POLICY ❌
**Governance blocks**

- Used when: Skill requires approval
- Outcome: BLOCKED
- Quality score: 0.0
- Future: Will integrate with ApprovalManager

### 5. BLOCKED_CREDENTIAL ❌
**Missing credentials/config**

- Used when: Connector exists but not configured
- Outcome: BLOCKED
- Quality score: 0.0
- Action: User must configure connector

### 6. NOT_INVOKABLE ❌
**No invocation path**

- Used when: Skill exists but no execution method available
- Outcome: PARTIAL (skill exists, just can't invoke)
- Quality score: 0.3
- Purpose: Honest reporting of limitations

## Architecture

### New Module: `core/skill_invoker.py`

**Purpose**: Real skill invocation engine

**Key classes:**
- `SkillInvoker`: Main invocation engine
- `SkillExecutionMode`: Execution mode enum
- `SkillInvocationResult`: Result structure with metadata

**Key methods:**
- `classify_execution_mode()`: Determine execution mode for skill
- `invoke_skill()`: Execute skill with appropriate mode
- `_invoke_connector_backed()`: Route through IntegrationSkill
- `_invoke_local()`: Execute via CLI subprocess
- `_invoke_dry_run()`: Simulate execution

### Updated Module: `core/skill_execution_loop.py`

**Changes:**
- Added `SkillInvoker` dependency
- Replaced stub `_execute_skill()` with real invocation
- Added mode-to-outcome mapping
- Added quality score calculation
- Added detailed execution notes

**New helper methods:**
- `_map_mode_to_outcome()`: Map execution mode to outcome type
- `_calculate_quality_score()`: Calculate quality from invocation result
- `_build_execution_notes()`: Human-readable execution notes

## Learning Loop Now Complete

```
1. Goal submitted
   ↓
2. Rank skills by learned outcomes
   ↓
3. Select best skill
   ↓
4. Classify execution mode ✅ NEW
   ↓
5. Invoke skill (real or simulated) ✅ NEW
   ↓
6. Capture real outcome ✅ NEW
   - Success/failure
   - Duration
   - Output/error
   - Execution mode
   - Detailed metadata
   ↓
7. Calculate quality score ✅ NEW
   - REAL_LOCAL success: 0.9
   - CONNECTOR_BACKED success: 0.9
   - DRY_RUN: 0.5
   - Failures: 0.2
   - Blocked: 0.0
   ↓
8. Persist execution record
   ↓
9. Update skill rankings (automatic)
   ↓
10. Future executions use improved rankings
```

## Outcome Capture

Execution records now include:

**From SkillInvocationResult:**
- `success`: True/False
- `mode`: Execution mode used
- `output`: Stdout or response data
- `error`: Error message if failed
- `duration_seconds`: Actual execution time
- `exit_code`: CLI exit code (if applicable)
- `metadata`: Mode-specific context

**Mapped to SkillExecutionRecord:**
- `outcome`: SUCCESS, FAILURE, PARTIAL, BLOCKED
- `quality_score`: 0.0 to 1.0 (mode-dependent)
- `notes`: Human-readable execution summary
- `error_message`: Error details
- `execution_context`: Full execution metadata
- `result_data`: Output and invocation details

## What Works Now

### ✅ Real Local Execution
Skills like `code-reviewer`, `test-engineer`, `systematic-debugging` can be invoked via CLI if Claude Code is available.

### ✅ Connector-Backed Execution
Skills mapped to connectors (`apollo-automation`, `stripe-automation`, etc.) route through the full integration layer with:
- Policy checks
- Credential validation
- Live/dry-run mode selection
- Full audit trail

### ✅ Governance Respected
- Approval-required skills are blocked
- Credential checks prevent unauthorized execution
- Policy engine enforces rules

### ✅ Honest Reporting
- Skills with no path report NOT_INVOKABLE
- Dry runs marked as PARTIAL (simulated)
- Blocked executions clearly indicated

### ✅ Learning Works
- Real outcomes feed into ranking system
- Quality scores reflect actual execution results
- Selection improves with each execution

## What Still Doesn't Work

### ⚠️ Approval Workflow Integration
**Status**: Governance boundaries defined but not integrated

Skills marked `requires_approval` are blocked, but full approval workflow is not connected.

**What's needed:**
- Integration with `ApprovalManager`
- Request approval for blocked skills
- Wait for operator decision
- Execute on approval

### ⚠️ Majority of Skills Not Invokable
**Status**: Most skills fall into NOT_INVOKABLE mode

Out of 935 skills, only a small subset have real invocation paths:
- ~10 safe local skills (CLI-based)
- ~7 connector-backed skills (with mappings)
- Rest: NOT_INVOKABLE or DRY_RUN

**What's needed:**
- More skill-to-connector mappings
- More safe local skill classifications
- Possibly: Skill-specific execution templates

### ⚠️ Limited Goal-to-Operation Mapping
**Status**: Simple keyword-based heuristic

Goal descriptions are mapped to connector operations using keywords (search, create, update, etc.)

**What's needed:**
- More sophisticated goal parsing
- Operation selection based on context
- Connector-specific operation vocabulary

## Testing

### New Test Suite: `tests/test_skill_invoker.py`

**Coverage:**
- Execution mode classification (all 6 modes)
- Real invocation paths (local, connector-backed)
- Blocked paths (policy, credentials)
- Outcome capture and metadata
- Goal-to-operation mapping
- Timeout handling
- CLI not found fallback

**All tests passing.**

### Updated: `tests/test_seed_core.py`

**Changes:**
- Added mock `SkillInvoker` to fixtures
- Mock returns dry run results for stable tests
- All existing tests still pass

## Usage Example

```python
from core import initialize_seed_core

# Initialize Seed Core
core = initialize_seed_core()

# Achieve a goal (real execution will happen)
result = core.achieve_goal(
    description="Review the authentication module for security issues",
    goal_type="code_review",
)

# Check execution mode used
execution_record = result["execution_records"][0]
print(f"Mode: {execution_record['execution_context']['execution_mode']}")
print(f"Success: {execution_record['success']}")
print(f"Quality: {execution_record['quality_score']}")
print(f"Duration: {execution_record['execution_context']['duration_seconds']}s")
```

## Files Created/Changed

### Created
- `core/skill_invoker.py` (383 lines) - Real invocation engine
- `tests/test_skill_invoker.py` (441 lines) - Comprehensive invocation tests
- `docs/REAL_SKILL_INVOCATION.md` (this file)

### Modified
- `core/skill_execution_loop.py` - Wired in SkillInvoker, replaced stub
- `core/__init__.py` - Exported SkillInvoker and related types
- `tests/test_seed_core.py` - Updated fixtures for mock invoker
- `docs/CURRENT_SPRINT_HANDOFF.md` - Updated status
- `docs/SEED_CORE_V1.md` - Updated capabilities
- `README.md` - Updated with real invocation status

### Unchanged
- All existing Alpha infrastructure
- All existing connectors
- All existing policies
- All existing UI routes

## Next Steps

### 1. Expand Invokable Skill Coverage
**Priority**: P1

- Map more skills to connectors
- Classify more safe local skills
- Build skill-specific execution templates

### 2. Integrate Approval Workflow
**Priority**: P1

- Connect to `ApprovalManager`
- Request approval for blocked skills
- Implement approval wait logic

### 3. Improve Goal-to-Operation Mapping
**Priority**: P2

- Better goal parsing
- Connector-specific operation vocabularies
- Context-aware operation selection

### 4. Add Async Execution
**Priority**: P2

- Long-running skill support
- Progress callbacks
- Async result capture

## Success Metrics

✅ **Real execution paths work**: CLI and connector invocations succeed
✅ **Governance respected**: Blocked skills don't execute
✅ **Learning works**: Real outcomes feed into rankings
✅ **Tests comprehensive**: All execution modes tested
✅ **Documentation complete**: Clear explanation of what works/doesn't

**Seed Core v1 now executes real skills and learns from real outcomes.**

The foundation is solid. Next: expand coverage and integrate approval workflow.
