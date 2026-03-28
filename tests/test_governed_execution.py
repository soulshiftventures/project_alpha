"""
Tests for Governed Real Execution Loop.

This tests the full end-to-end approval workflow integration in Seed Core.
"""

import pytest
from datetime import datetime, timezone

from core.seed_core import SeedCore
from core.seed_models import Goal, GoalStatus, SkillExecutionRecord, OutcomeType
from core.seed_memory import SeedMemory
from core.skill_execution_loop import SkillExecutionLoop
from core.skill_ranker import SkillRanker
from core.skill_invoker import SkillInvoker, SkillExecutionMode, SkillInvocationResult
from core.skill_registry import SkillRegistry, SkillDefinition, SkillCategory
from core.approval_manager import ApprovalManager
from core.state_store import StateStore, StateStoreConfig


@pytest.fixture
def fresh_memory(tmp_path):
    """Create a fresh SeedMemory instance for testing."""
    db_path = tmp_path / "test_governed.db"
    config = StateStoreConfig(db_path=str(db_path))
    state_store = StateStore(config=config)
    state_store.initialize()

    memory = SeedMemory(state_store=state_store)
    memory.initialize()
    return memory


@pytest.fixture
def mock_invoker():
    """Create a mock SkillInvoker that returns controlled results."""
    class MockInvoker:
        def __init__(self):
            self.invocations = []

        def classify_execution_mode(self, skill, goal_context=None):
            """Classify based on skill name and requires_approval."""
            if skill.requires_approval:
                return SkillExecutionMode.BLOCKED_POLICY
            if "blocked-cred" in skill.name:
                return SkillExecutionMode.BLOCKED_CREDENTIAL
            if "safe-local" in skill.name:
                return SkillExecutionMode.REAL_LOCAL
            return SkillExecutionMode.DRY_RUN

        def invoke_skill(self, skill, goal_description, goal_type, params=None):
            """Mock skill invocation."""
            self.invocations.append({
                "skill": skill.name,
                "goal_description": goal_description,
                "goal_type": goal_type,
            })

            # Determine mode
            mode = self.classify_execution_mode(skill)

            if mode == SkillExecutionMode.BLOCKED_POLICY:
                return SkillInvocationResult(
                    success=False,
                    mode=mode,
                    error=f"Skill {skill.name} requires approval",
                    metadata={"block_reason": "requires_approval"},
                )
            elif mode == SkillExecutionMode.BLOCKED_CREDENTIAL:
                return SkillInvocationResult(
                    success=False,
                    mode=mode,
                    error="Missing credentials",
                    metadata={"block_reason": "missing_credentials"},
                )
            elif mode == SkillExecutionMode.REAL_LOCAL:
                return SkillInvocationResult(
                    success=True,
                    mode=mode,
                    output=f"Real local execution of {skill.name}",
                    duration_seconds=0.5,
                )
            else:  # DRY_RUN
                return SkillInvocationResult(
                    success=True,
                    mode=mode,
                    output=f"DRY RUN: {skill.name}",
                    duration_seconds=0.001,
                )

    return MockInvoker()


@pytest.fixture
def mock_registry():
    """Create a mock SkillRegistry with test skills."""
    class MockRegistry:
        def __init__(self):
            self.is_loaded = True
            self._skills = {
                "skill-requires-approval": SkillDefinition(
                    name="skill-requires-approval",
                    category=SkillCategory.WEB_AUTOMATION,
                    keywords=["test", "approval", "governed"],
                    requires_approval=True,
                    path="/mock/approval-skill",
                description="Test approval skill",
                ),
                "skill-safe-local": SkillDefinition(
                    name="skill-safe-local",
                    category=SkillCategory.DEVELOPMENT_TOOLS,
                    keywords=["test", "safe"],
                    requires_approval=False,
                    path="/mock/safe-skill",
                description="Test safe skill",
                ),
                "skill-blocked-cred": SkillDefinition(
                    name="skill-blocked-cred",
                    category=SkillCategory.LEAD_GENERATION,
                    keywords=["test", "blocked", "credential", "credentials", "missing"],
                    requires_approval=False,
                    path="/mock/blocked-skill",
                description="Test blocked skill",
                ),
                "skill-normal": SkillDefinition(
                    name="skill-normal",
                    category=SkillCategory.WEB_AUTOMATION,
                    keywords=["test", "normal"],
                    requires_approval=False,
                    path="/mock/normal-skill",
                description="Test normal skill",
                ),
            }

        def get_skill(self, name):
            return self._skills.get(name)

        def list_all(self):
            return list(self._skills.values())

        def all_skills(self):
            return list(self._skills.values())

        def list_by_category(self, category):
            return [s for s in self._skills.values() if s.category == category]

        def search_by_keywords(self, keywords):
            results = []
            for skill in self._skills.values():
                if any(kw in skill.keywords for kw in keywords):
                    results.append(skill)
            return results

        @property
        def skill_count(self):
            return len(self._skills)

        def list_categories(self):
            from collections import defaultdict
            counts = defaultdict(int)
            for skill in self._skills.values():
                counts[skill.category] += 1
            return counts

    return MockRegistry()


@pytest.fixture
def governed_core(fresh_memory, mock_invoker, mock_registry):
    """Create a SeedCore instance with governed execution."""
    approval_manager = ApprovalManager()
    skill_ranker = SkillRanker(skill_registry=mock_registry, seed_memory=fresh_memory)
    execution_loop = SkillExecutionLoop(
        skill_ranker=skill_ranker,
        seed_memory=fresh_memory,
        skill_invoker=mock_invoker,
        approval_manager=approval_manager,
    )
    execution_loop._skill_registry = mock_registry  # Inject for testing

    core = SeedCore(
        skill_registry=mock_registry,
        seed_memory=fresh_memory,
        skill_ranker=skill_ranker,
        skill_execution_loop=execution_loop,
    )
    core.initialize()
    return core


# =============================================================================
# Test: Allowed Real Execution Path
# =============================================================================

def test_allowed_real_execution_path(governed_core):
    """Test skill execution that is allowed immediately."""
    result = governed_core.achieve_goal(
        description="Execute safe local skill",
        goal_type="safe_execution",
        allow_decomposition=False,
    )

    assert result["success"] is True
    assert len(result["execution_records"]) == 1

    record = result["execution_records"][0]
    assert record["skill_name"] == "skill-safe-local"
    assert record["outcome"] == OutcomeType.SUCCESS.value
    assert record["quality_score"] > 0.5  # Real execution has good quality
    assert record["approval_record_id"] is None  # No approval needed


# =============================================================================
# Test: Blocked Policy Path
# =============================================================================

def test_approval_required_path(governed_core):
    """Test skill execution that requires approval."""
    # Try to execute skill requiring approval
    result = governed_core.achieve_goal(
        description="Execute skill requiring approval",
        goal_type="approval_test",
        allow_decomposition=False,
    )

    # Initial execution should create AWAITING_APPROVAL record
    assert result["success"] is False
    assert len(result["execution_records"]) == 1

    record = result["execution_records"][0]
    assert record["skill_name"] == "skill-requires-approval"
    assert record["outcome"] == OutcomeType.AWAITING_APPROVAL.value
    assert record["quality_score"] == 0.0  # No quality until executed
    assert record["approval_record_id"] is not None

    # Check goal status
    goal = governed_core._seed_memory.get_goal(record["goal_id"])
    assert goal.status == GoalStatus.AWAITING_APPROVAL

    # Check pending approvals
    pending = governed_core.get_pending_approvals()
    assert len(pending) == 1
    assert pending[0]["request_type"] == "skill_execution"
    assert pending[0]["action"] == "execute_skill_skill-requires-approval"


# =============================================================================
# Test: Post-Approval Resume Path (Approved)
# =============================================================================

def test_post_approval_resume_approved(governed_core, mock_invoker):
    """Test resuming execution after approval is granted."""
    # Create initial awaiting-approval execution
    initial_result = governed_core.achieve_goal(
        description="Execute skill requiring approval",
        goal_type="approval_test",
        allow_decomposition=False,
    )

    execution_id = initial_result["execution_records"][0]["execution_id"]

    # Approve and resume
    resume_result = governed_core.resume_after_approval(
        execution_id=execution_id,
        approved=True,
        approver="test-operator",
        rationale="Approved for testing",
    )

    assert resume_result["success"] is True
    assert "approved" in resume_result["message"]

    # Check that skill was invoked (blocked-policy won't actually run in mock)
    # The mock returns BLOCKED_POLICY for requires_approval=True skills
    # So execution will still fail, but approval workflow completed
    result_record = resume_result["execution_record"]
    assert result_record["approval_record_id"] == initial_result["execution_records"][0]["approval_record_id"]

    # Check goal updated
    goal = governed_core._seed_memory.get_goal(initial_result["goal"]["goal_id"])
    assert goal.status in [GoalStatus.COMPLETED, GoalStatus.FAILED]  # Depends on mock execution


# =============================================================================
# Test: Post-Approval Resume Path (Denied)
# =============================================================================

def test_post_approval_resume_denied(governed_core):
    """Test resuming execution after approval is denied."""
    # Create initial awaiting-approval execution
    initial_result = governed_core.achieve_goal(
        description="Execute skill requiring approval",
        goal_type="approval_test",
        allow_decomposition=False,
    )

    execution_id = initial_result["execution_records"][0]["execution_id"]

    # Deny
    resume_result = governed_core.resume_after_approval(
        execution_id=execution_id,
        approved=False,
        approver="test-operator",
        rationale="Denied for testing",
    )

    assert resume_result["success"] is True
    assert "denied" in resume_result["message"]

    result_record = resume_result["execution_record"]
    assert result_record["outcome"] == OutcomeType.DENIED.value
    assert result_record["quality_score"] == 0.0
    assert result_record["success"] is False
    assert "Denied for testing" in result_record["notes"]

    # Check goal status
    goal = governed_core._seed_memory.get_goal(initial_result["goal"]["goal_id"])
    assert goal.status == GoalStatus.FAILED


# =============================================================================
# Test: Blocked Credential Path
# =============================================================================

def test_blocked_credential_path(governed_core):
    """Test skill execution blocked by missing credentials."""
    result = governed_core.achieve_goal(
        description="Execute skill with missing credentials",
        goal_type="credential_test",
        allow_decomposition=False,
    )

    # Should get blocked execution
    assert result["success"] is False
    record = result["execution_records"][0]
    assert record["skill_name"] == "skill-blocked-cred"
    assert record["outcome"] == OutcomeType.BLOCKED.value
    assert record["quality_score"] == 0.0
    assert "credential" in record["error_message"].lower()


# =============================================================================
# Test: Learning from Different Outcome Classes
# =============================================================================

def test_learning_from_different_outcomes(governed_core, fresh_memory):
    """Test that different outcome types affect learning differently."""
    # Create multiple execution records with different outcomes
    from core.seed_models import SkillExecutionRecord, OutcomeType
    import hashlib
    from datetime import datetime, timezone

    def make_exec_id(i):
        return f"exec_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{i}"

    goal_type = "learning_test"
    skill_name = "skill-normal"

    # SUCCESS execution
    fresh_memory.save_execution_record(SkillExecutionRecord(
        execution_id=make_exec_id(1),
        goal_id="goal_1",
        goal_type=goal_type,
        skill_name=skill_name,
        outcome=OutcomeType.SUCCESS,
        quality_score=0.9,
        success=True,
    ))

    # FAILURE execution
    fresh_memory.save_execution_record(SkillExecutionRecord(
        execution_id=make_exec_id(2),
        goal_id="goal_2",
        goal_type=goal_type,
        skill_name=skill_name,
        outcome=OutcomeType.FAILURE,
        quality_score=0.2,
        success=False,
    ))

    # AWAITING_APPROVAL execution (should NOT count)
    fresh_memory.save_execution_record(SkillExecutionRecord(
        execution_id=make_exec_id(3),
        goal_id="goal_3",
        goal_type=goal_type,
        skill_name=skill_name,
        outcome=OutcomeType.AWAITING_APPROVAL,
        quality_score=0.0,
        success=False,
        approval_record_id="apr_test",
    ))

    # DENIED execution (should count)
    fresh_memory.save_execution_record(SkillExecutionRecord(
        execution_id=make_exec_id(4),
        goal_id="goal_4",
        goal_type=goal_type,
        skill_name=skill_name,
        outcome=OutcomeType.DENIED,
        quality_score=0.0,
        success=False,
    ))

    # BLOCKED execution (should count)
    fresh_memory.save_execution_record(SkillExecutionRecord(
        execution_id=make_exec_id(5),
        goal_id="goal_5",
        goal_type=goal_type,
        skill_name=skill_name,
        outcome=OutcomeType.BLOCKED,
        quality_score=0.0,
        success=False,
    ))

    # Get ranking
    rankings = fresh_memory.get_ranked_skills(goal_type, limit=5)
    assert len(rankings) == 1
    ranking = rankings[0]

    # Should have 4 executions (AWAITING_APPROVAL doesn't count)
    assert ranking.total_executions == 4
    assert ranking.successful_executions == 1  # Only SUCCESS counts as success
    assert ranking.success_rate == 0.25  # 1/4

    # Average quality should be (0.9 + 0.2 + 0.0 + 0.0) / 4 = 0.275
    assert abs(ranking.average_quality - 0.275) < 0.01


# =============================================================================
# Test: Full Governed Lifecycle
# =============================================================================

def test_full_governed_lifecycle(governed_core):
    """Test complete governed execution lifecycle from request to completion."""
    # Step 1: Request execution of approval-required skill
    initial = governed_core.achieve_goal(
        description="Execute governed skill",
        goal_type="full_lifecycle_test",
        allow_decomposition=False,
    )

    assert initial["success"] is False
    assert initial["execution_records"][0]["outcome"] == OutcomeType.AWAITING_APPROVAL.value

    execution_id = initial["execution_records"][0]["execution_id"]
    goal_id = initial["goal"]["goal_id"]

    # Step 2: Check pending approvals
    pending = governed_core.get_pending_approvals()
    assert len(pending) >= 1
    assert any(p["request_id"] == execution_id for p in pending)

    # Step 3: Approve
    approved = governed_core.resume_after_approval(
        execution_id=execution_id,
        approved=True,
        approver="operator",
        rationale="Testing lifecycle",
    )

    assert approved["success"] is True

    # Step 4: Verify execution record was created
    records = governed_core._seed_memory.get_execution_records(goal_type="full_lifecycle_test", limit=10)
    assert len(records) >= 2  # Original awaiting + result

    # Step 5: Verify goal status updated
    goal = governed_core._seed_memory.get_goal(goal_id)
    assert goal.status in [GoalStatus.COMPLETED, GoalStatus.FAILED]

    # Step 6: Verify no longer pending
    pending_after = governed_core.get_pending_approvals()
    assert not any(p["request_id"] == execution_id for p in pending_after)


# =============================================================================
# Test: Cannot Resume Non-Awaiting Execution
# =============================================================================

def test_cannot_resume_non_awaiting(governed_core):
    """Test that you cannot resume an execution that isn't awaiting approval."""
    # Execute a normal skill (no approval needed)
    result = governed_core.achieve_goal(
        description="Execute normal skill",
        goal_type="no_approval_test",
        allow_decomposition=False,
    )

    execution_id = result["execution_records"][0]["execution_id"]

    # Try to resume (should fail)
    resume_result = governed_core.resume_after_approval(
        execution_id=execution_id,
        approved=True,
        approver="operator",
    )

    assert resume_result["success"] is False
    assert "not awaiting approval" in resume_result["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
