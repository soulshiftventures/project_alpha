# Seed Core v1 - Self-Improving Agent Core

## What Seed Core v1 Is

Seed Core v1 is the **minimal self-improving agent core** that learns from actual skill execution outcomes.

It is the missing heart of the system - the real learning loop that was needed.

## What Seed Core v1 Can Do Now

### 1. Accept Real Goals
- Create goal records with type, description, metadata
- Track goal lifecycle (pending → in_progress → completed/failed)
- Persist goals for recovery and analysis

### 2. Inspect Available Skills
- Load 935+ skills from external reference library
- Categorize skills by domain
- Query skills by keyword or category
- Identify proactive and approval-required skills

### 3. Select Skills Based on Learned Outcomes
- **For new goal types**: Fall back to keyword matching
- **For goal types with history**: Rank skills by:
  - Success rate (historical % of successful executions)
  - Average quality score (0.0 to 1.0)
  - Confidence (based on sample size)
- Explain ranking decisions for debugging

### 4. Execute Skills in Bounded Way
- Execute selected skill for goal
- Respect governance boundaries (approval-required skills are blocked)
- Capture execution context and metadata

### 5. Observe Outcome Quality
- Record success/failure
- Capture quality score (0.0 to 1.0)
- Store error messages and notes
- Preserve selection reasoning

### 6. Persist Results
- Save execution records to SQLite database
- Update skill rankings automatically
- Track goal status and completion
- Maintain decomposition records

### 7. Improve Future Skill Selection
- **Learn from outcomes**: Better-performing skills get ranked higher
- **Confidence grows with sample size**: More executions = higher confidence
- **Quality matters**: Average quality contributes to ranking score
- **Composite scoring**: Combines success rate, quality, and confidence

### 8. Decompose Complex Goals
- Detect complex goals (multiple steps, explicit markers)
- Break into sequential or parallel sub-goals
- Execute each sub-goal with one skill
- Aggregate results to parent goal

## What Seed Core v1 Still Cannot Do

### 1. Real Skill Invocation ✅ COMPLETE
**Status**: CONNECTED - Real invocation wiring implemented

Execution loop now invokes skills via multiple execution modes:
- REAL_LOCAL: CLI-based invocation for safe local operations
- CONNECTOR_BACKED: External API invocation via connectors
- DRY_RUN: Simulated execution (fallback)
- BLOCKED_POLICY: Governance blocks
- BLOCKED_CREDENTIAL: Missing credentials/config
- NOT_INVOKABLE: No invocation path available

**See**: `docs/REAL_SKILL_INVOCATION.md` for details

### 2. Live Action Execution
**Status**: Governance boundaries defined but not fully enforced

Skills marked as `requires_approval` are blocked, but full approval workflow integration is not complete.

**What's needed**: Integration with existing `ApprovalManager` and live mode promotion system

### 3. Multi-Level Decomposition
**Status**: Basic sequential/parallel decomposition only

Decomposition creates sub-goals but does not recursively decompose them.

**What's needed**: Hierarchical decomposition with depth limits

### 4. Advanced Goal Types
**Status**: Goal type is a string, no schema validation

Any string can be a goal type. No predefined taxonomy.

**What's needed**: Goal type registry, validation, recommended decomposition strategies per type

### 5. Skill Recommendation
**Status**: Ranks skills but doesn't proactively suggest them

Seed Core waits for goals to be submitted. It doesn't scan context and suggest relevant skills.

**What's needed**: Context-aware skill recommendation engine

### 6. Transfer Learning
**Status**: Each goal type learns independently

No transfer of learning between similar goal types.

**What's needed**: Goal type similarity, cross-type learning, skill embeddings

## Architecture

### Core Modules

| Module | Purpose | Status |
|--------|---------|--------|
| `seed_core.py` | Main interface, orchestration | ✅ Complete |
| `seed_models.py` | Data models (Goal, SkillExecutionRecord, etc.) | ✅ Complete |
| `seed_memory.py` | Persistence layer (SQLite) | ✅ Complete |
| `skill_execution_loop.py` | Execution engine | ⚠️ STUB (interface defined, invocation not connected) |
| `skill_ranker.py` | Outcome-based ranking | ✅ Complete |
| `goal_decomposer.py` | Goal decomposition | ✅ Complete (basic) |

### Data Flow

```
User submits goal
    ↓
Seed Core accepts goal
    ↓
Check if decomposition needed
    ↓
If complex: Decompose into sub-goals
    ↓
For each (sub-)goal:
    Rank skills by learned outcomes
        ↓
    Select best skill
        ↓
    Check governance (approval required?)
        ↓
    Execute skill [STUB]
        ↓
    Capture outcome (success, quality, notes)
        ↓
    Persist execution record
        ↓
    Update skill rankings
        ↓
    Update goal status
```

### Learning Loop

```
Execution Record → Update Ranking → Better Future Selection

Ranking Score = (Success Rate × 0.5 + Average Quality × 0.5) × Confidence

Where:
- Success Rate = successful_executions / total_executions
- Average Quality = rolling average of quality scores
- Confidence = min(1.0, total_executions / 10.0)
```

## Relationship to Project Alpha

Seed Core **replaces conceptually**:
- `chief_orchestrator.py` (hardcoded hierarchy brain)
- `hierarchy_definitions.py` (static role definitions)
- `role_skill_mappings.py` (hardcoded skill routing)
- `scenario_definitions.py` (template-based scenarios)

Seed Core **reuses from Alpha**:
- `state_store.py` (SQLite persistence)
- `persistence_manager.py` (lifecycle management)
- `skill_registry.py` (skill loading)
- `approval_manager.py` (governance - integration pending)
- `connector_action_history.py` (live action tracking)

Seed Core **ignores**:
- Old orchestration logic (not dependent)
- Fixed hierarchy patterns
- Static templates
- Hardcoded role assignments

## Usage

### Basic Usage

```python
from core import initialize_seed_core

# Initialize
core = initialize_seed_core()

# Achieve a goal
result = core.achieve_goal(
    description="Research market opportunities for SaaS products",
    goal_type="market_research",
    allow_decomposition=True,
)

print(result["message"])
print(f"Executions: {len(result['execution_records'])}")
```

### Inspecting Learning

```python
# Get system stats
stats = core.introspect()
print(f"Skills available: {stats['skills_available']}")
print(f"Total executions: {stats['memory_stats']['total_executions']}")
print(f"Success rate: {stats['memory_stats']['success_rate']:.1%}")

# Explain skill rankings for a goal type
explanations = core.explain_skill_selection("market_research", limit=5)
for exp in explanations:
    print(f"{exp['skill_name']}: {exp['explanation']}")
```

### Direct Memory Access

```python
from core import get_seed_memory

memory = get_seed_memory()
memory.initialize()

# Get execution history
records = memory.get_execution_records(goal_type="market_research", limit=20)

# Get ranked skills
rankings = memory.get_ranked_skills("market_research", limit=10)
for r in rankings:
    print(f"{r.skill_name}: score={r.get_score():.3f}, success={r.success_rate:.1%}")
```

## Testing

Comprehensive tests in `tests/test_seed_core.py`:

```bash
# Run Seed Core tests
PYTHONPATH=. pytest tests/test_seed_core.py -v

# Run all tests
PYTHONPATH=. pytest -q
```

Test coverage:
- ✅ Data model creation and updates
- ✅ Persistence (execution records, rankings, goals, decompositions)
- ✅ Skill ranking (keyword fallback, learned outcomes)
- ✅ Goal decomposition (detection, sequential, parallel)
- ✅ Execution loop (simple goals, complex goals, approval blocking)
- ✅ Learning improvement (repeated execution improves selection)
- ✅ Introspection and stats

## Governance

Seed Core **respects existing governance boundaries**:

1. **Skills requiring approval**: Blocked from execution
   - Marked with `requires_approval=True`
   - Execution creates `BLOCKED` outcome record
   - Future integration: Full approval workflow

2. **Live mode promotion**: Not yet integrated
   - Execution is currently stub (no real API calls)
   - When connected: Will respect live mode policies

3. **Credential policies**: Not yet enforced
   - Skills don't execute yet
   - When connected: Will check credential availability

4. **Cost tracking**: Interface exists
   - Execution context captured
   - When connected: Will log costs via existing tracker

## Future Roadmap

### Phase 1: Make It Real (Current Gap)
- [ ] Connect skill execution to actual invocation system
- [ ] Integrate approval workflow for live actions
- [ ] Real outcome capture (not stub)
- [ ] Test with actual skill executions

### Phase 2: Make It Smart
- [ ] Transfer learning between similar goal types
- [ ] Goal type taxonomy and validation
- [ ] Multi-level decomposition with recursion
- [ ] Context-aware skill recommendation

### Phase 3: Make It Autonomous
- [ ] Auto-suggest skills based on system state
- [ ] Proactive goal generation from observations
- [ ] Self-optimization (A/B test strategies)
- [ ] Meta-learning (learn how to learn better)

## Why Seed Core Matters

**Before Seed Core:**
- Skill selection was pure keyword matching
- No learning from outcomes
- Static, hardcoded routing
- No improvement over time

**With Seed Core v1:**
- Skills are ranked by actual performance
- System learns which skills work for which goals
- Selection improves with every execution
- Bounded, testable, honest

**This is the foundation for real autonomy.**

Not fake planning. Not hardcoded hierarchy. Real learning from real outcomes.

## Migration Guide

If you're using old Alpha orchestration:

```python
# OLD (hardcoded hierarchy)
from core.chief_orchestrator import ChiefOrchestrator
orchestrator = ChiefOrchestrator()
result = orchestrator.execute_scenario(scenario_name="market_research")

# NEW (learned outcomes)
from core import initialize_seed_core
core = initialize_seed_core()
result = core.achieve_goal(
    description="Research market opportunities",
    goal_type="market_research",
)
```

Key differences:
- No scenario templates
- No role assignments
- No hardcoded hierarchy
- Just goals, skills, and learned outcomes

## Technical Details

### Database Schema

Seed Core adds 4 tables to StateStore:

**seed_execution_records**
- Fundamental learning data
- Every skill execution creates one record
- Drives ranking updates

**seed_skill_rankings**
- Derived from execution records
- Cached in memory for fast access
- Updated automatically on new executions

**seed_goals**
- Goal lifecycle tracking
- Status: pending → in_progress → completed/failed/decomposed
- Parent-child relationships for decomposition

**seed_goal_decompositions**
- Decomposition strategy tracking
- Sub-goal ID lists
- Metadata for sub-goal details

### Performance

- **Skill ranking**: O(n) where n = skills with history for goal type
- **Execution record save**: O(1) database write
- **Decomposition**: O(k) where k = number of sub-goals created
- **Memory overhead**: Rankings cached in-memory, ~1KB per ranking

### Limitations

1. **No HNSW/vector search**: Uses keyword matching for new goal types
2. **SQLite only**: No distributed storage yet
3. **No async**: Synchronous execution only
4. **Single-threaded**: No parallel sub-goal execution yet
5. **No skill chaining**: One skill per (sub-)goal only

## Support

- **Code**: `/Users/krissanders/Desktop/project_alpha_working/core/seed_*.py`
- **Tests**: `/Users/krissanders/Desktop/project_alpha_working/tests/test_seed_core.py`
- **Docs**: This file

For issues or questions about Seed Core, check test cases first - they demonstrate all capabilities.
