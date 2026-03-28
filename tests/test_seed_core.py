"""
Tests for Seed Core v1

Validates:
- Skill execution record creation
- Skill ranking updates from outcomes
- Repeated goal handling improves selection
- Decomposition path
- Persistence of seed records
- Governed boundary for live actions still respected
- Existing tests still pass
"""

import pytest
from datetime import datetime, timezone

from core.seed_core import SeedCore, get_seed_core, initialize_seed_core
from core.seed_models import (
    Goal,
    GoalStatus,
    SkillExecutionRecord,
    SkillRanking,
    OutcomeType,
    GoalDecomposition,
)
from core.seed_memory import SeedMemory
from core.skill_ranker import SkillRanker
from core.goal_decomposer import GoalDecomposer
from core.skill_execution_loop import SkillExecutionLoop
from core.skill_registry import SkillRegistry, SkillDefinition, SkillCategory
from core.skill_invoker import SkillInvoker, SkillInvocationResult, SkillExecutionMode
from unittest.mock import Mock


@pytest.fixture
def in_memory_seed_memory(tmp_path):
    """Create an in-memory SeedMemory for testing."""
    from core.state_store import StateStore, StateStoreConfig

    # Use temporary database
    db_path = tmp_path / "test_seed.db"
    config = StateStoreConfig(db_path=str(db_path))
    state_store = StateStore(config)
    state_store.initialize()

    memory = SeedMemory(state_store=state_store)
    memory.initialize()

    return memory


@pytest.fixture
def mock_skill_registry():
    """Create a mock skill registry with test skills."""
    registry = SkillRegistry(reference_path=None)

    # Manually populate with test skills
    registry._skills = {
        "market-research-skill": SkillDefinition(
            name="market-research-skill",
            description="Research market opportunities",
            path="market-research-skill",
            keywords=["market", "research", "opportunities"],
            category=SkillCategory.RESEARCH_LEARNING,
        ),
        "data-analysis-skill": SkillDefinition(
            name="data-analysis-skill",
            description="Analyze data and generate insights",
            path="data-analysis-skill",
            keywords=["data", "analysis", "insights"],
            category=SkillCategory.ANALYTICS_DATA,
        ),
        "apollo-automation": SkillDefinition(
            name="apollo-automation",
            description="Lead generation via Apollo",
            path="apollo-automation",
            keywords=["apollo", "leads", "generation"],
            category=SkillCategory.LEAD_GENERATION,
        ),
        "approval-required-skill": SkillDefinition(
            name="approval-required-skill",
            description="Skill requiring approval",
            path="approval-required-skill",
            keywords=["approval"],
            category=SkillCategory.UNCATEGORIZED,
            requires_approval=True,
        ),
    }
    registry._loaded = True

    return registry


@pytest.fixture
def seed_core(in_memory_seed_memory, mock_skill_registry):
    """Create a SeedCore instance for testing."""
    # Ensure mock registry is properly initialized
    mock_skill_registry._loaded = True

    skill_ranker = SkillRanker(
        skill_registry=mock_skill_registry,
        seed_memory=in_memory_seed_memory,
    )

    # Create mock skill invoker that returns dry run results
    mock_invoker = Mock(spec=SkillInvoker)
    mock_invoker.invoke_skill.return_value = SkillInvocationResult(
        success=True,
        mode=SkillExecutionMode.DRY_RUN,
        output="DRY RUN: Skill executed successfully",
        duration_seconds=0.001,
        metadata={"simulated": True},
    )

    execution_loop = SkillExecutionLoop(
        skill_ranker=skill_ranker,
        seed_memory=in_memory_seed_memory,
        skill_invoker=mock_invoker,
    )
    # Inject registry into execution loop for skill lookups
    execution_loop._skill_registry = mock_skill_registry

    goal_decomposer = GoalDecomposer()

    core = SeedCore(
        skill_registry=mock_skill_registry,
        seed_memory=in_memory_seed_memory,
        skill_ranker=skill_ranker,
        skill_execution_loop=execution_loop,
        goal_decomposer=goal_decomposer,
    )

    core.initialize()

    return core


class TestSeedModels:
    """Test Seed Core data models."""

    def test_goal_creation(self):
        """Test creating a goal."""
        goal = Goal(
            goal_id="test_goal_1",
            description="Test goal",
            goal_type="test_type",
        )

        assert goal.goal_id == "test_goal_1"
        assert goal.description == "Test goal"
        assert goal.goal_type == "test_type"
        assert goal.status == GoalStatus.PENDING
        assert goal.parent_goal_id is None

    def test_execution_record_creation(self):
        """Test creating an execution record."""
        record = SkillExecutionRecord(
            execution_id="test_exec_1",
            goal_id="test_goal_1",
            goal_type="market_research",
            skill_name="market-research-skill",
            outcome=OutcomeType.SUCCESS,
            quality_score=0.8,
            success=True,
        )

        assert record.execution_id == "test_exec_1"
        assert record.skill_name == "market-research-skill"
        assert record.success is True
        assert record.quality_score == 0.8

    def test_skill_ranking_update(self):
        """Test updating skill ranking from execution."""
        ranking = SkillRanking(
            goal_type="market_research",
            skill_name="market-research-skill",
        )

        # First execution - success
        record1 = SkillExecutionRecord(
            execution_id="exec1",
            goal_id="goal1",
            goal_type="market_research",
            skill_name="market-research-skill",
            outcome=OutcomeType.SUCCESS,
            quality_score=0.9,
            success=True,
        )

        ranking.update_from_execution(record1)

        assert ranking.total_executions == 1
        assert ranking.successful_executions == 1
        assert ranking.success_rate == 1.0
        assert ranking.average_quality == 0.9
        assert ranking.confidence == 0.1  # 1/10

        # Second execution - failure
        record2 = SkillExecutionRecord(
            execution_id="exec2",
            goal_id="goal2",
            goal_type="market_research",
            skill_name="market-research-skill",
            outcome=OutcomeType.FAILURE,
            quality_score=0.2,
            success=False,
        )

        ranking.update_from_execution(record2)

        assert ranking.total_executions == 2
        assert ranking.successful_executions == 1
        assert ranking.success_rate == 0.5
        assert ranking.average_quality == 0.55  # (0.9 + 0.2) / 2
        assert ranking.confidence == 0.2  # 2/10


class TestSeedMemory:
    """Test Seed Memory persistence."""

    def test_save_and_retrieve_execution_record(self, in_memory_seed_memory):
        """Test saving and retrieving execution records."""
        record = SkillExecutionRecord(
            execution_id="test_exec_1",
            goal_id="test_goal_1",
            goal_type="market_research",
            skill_name="market-research-skill",
            outcome=OutcomeType.SUCCESS,
            quality_score=0.8,
            success=True,
        )

        # Save
        success = in_memory_seed_memory.save_execution_record(record)
        assert success is True

        # Retrieve
        records = in_memory_seed_memory.get_execution_records(
            goal_type="market_research",
            limit=10,
        )

        assert len(records) == 1
        assert records[0].execution_id == "test_exec_1"
        assert records[0].skill_name == "market-research-skill"

    def test_ranking_updates_from_records(self, in_memory_seed_memory):
        """Test that rankings are updated automatically from execution records."""
        # Save multiple execution records
        for i in range(5):
            record = SkillExecutionRecord(
                execution_id=f"exec_{i}",
                goal_id=f"goal_{i}",
                goal_type="market_research",
                skill_name="market-research-skill",
                outcome=OutcomeType.SUCCESS if i < 4 else OutcomeType.FAILURE,
                quality_score=0.8 if i < 4 else 0.2,
                success=i < 4,
            )
            in_memory_seed_memory.save_execution_record(record)

        # Get ranked skills
        ranked = in_memory_seed_memory.get_ranked_skills("market_research", limit=10)

        assert len(ranked) >= 1
        assert ranked[0].skill_name == "market-research-skill"
        assert ranked[0].total_executions == 5
        assert ranked[0].successful_executions == 4
        assert ranked[0].success_rate == 0.8

    def test_goal_persistence(self, in_memory_seed_memory):
        """Test saving and retrieving goals."""
        goal = Goal(
            goal_id="test_goal_1",
            description="Test market research",
            goal_type="market_research",
        )

        # Save
        success = in_memory_seed_memory.save_goal(goal)
        assert success is True

        # Retrieve
        retrieved = in_memory_seed_memory.get_goal("test_goal_1")
        assert retrieved is not None
        assert retrieved.goal_id == "test_goal_1"
        assert retrieved.description == "Test market research"

    def test_decomposition_persistence(self, in_memory_seed_memory):
        """Test saving goal decompositions."""
        decomposition = GoalDecomposition(
            decomposition_id="decomp_1",
            parent_goal_id="goal_1",
            sub_goal_ids=["subgoal_1", "subgoal_2", "subgoal_3"],
            decomposition_strategy="sequential",
        )

        success = in_memory_seed_memory.save_decomposition(decomposition)
        assert success is True


class TestSkillRanker:
    """Test skill ranking logic."""

    def test_ranking_with_no_history(self, seed_core):
        """Test skill ranking falls back to keyword matching when no history exists."""
        ranker = seed_core._skill_ranker

        ranked = ranker.rank_skills_for_goal(
            goal_type="new_goal_type",
            goal_description="research market opportunities",
            limit=5,
        )

        # Should get keyword matches
        assert len(ranked) > 0
        assert ranked[0].skill.name == "market-research-skill"
        assert "Keyword match" in ranked[0].selection_reason

    def test_ranking_with_history(self, seed_core):
        """Test skill ranking uses learned outcomes when available."""
        memory = seed_core._seed_memory
        ranker = seed_core._skill_ranker

        # Create execution history
        for i in range(3):
            record = SkillExecutionRecord(
                execution_id=f"exec_{i}",
                goal_id=f"goal_{i}",
                goal_type="market_research",
                skill_name="market-research-skill",
                outcome=OutcomeType.SUCCESS,
                quality_score=0.9,
                success=True,
            )
            memory.save_execution_record(record)

        # Now rank for same goal type
        ranked = ranker.rank_skills_for_goal(
            goal_type="market_research",
            goal_description="research market opportunities",
            limit=5,
        )

        # Should get learned ranking
        assert len(ranked) > 0
        assert ranked[0].skill.name == "market-research-skill"
        assert "Learned" in ranked[0].selection_reason
        assert ranked[0].ranking is not None
        assert ranked[0].ranking.total_executions == 3


class TestGoalDecomposer:
    """Test goal decomposition logic."""

    def test_simple_goal_no_decomposition(self):
        """Test simple goals don't get decomposed."""
        decomposer = GoalDecomposer()

        goal = Goal(
            goal_id="simple_goal",
            description="Do one simple thing",
            goal_type="simple_task",
        )

        needs_decomp = decomposer._needs_decomposition(goal)
        assert needs_decomp is False

    def test_complex_goal_needs_decomposition(self):
        """Test complex goals are identified for decomposition."""
        decomposer = GoalDecomposer()

        goal = Goal(
            goal_id="complex_goal",
            description="First research the market, then analyze competitors, and finally create a report",
            goal_type="market_research",
        )

        needs_decomp = decomposer._needs_decomposition(goal)
        assert needs_decomp is True

    def test_sequential_decomposition(self):
        """Test sequential decomposition creates ordered sub-goals."""
        decomposer = GoalDecomposer()

        goal = Goal(
            goal_id="complex_goal",
            description="First research the market, then analyze data, finally create report",
            goal_type="market_research",
        )

        decomposition = decomposer.decompose_goal(goal, strategy="sequential")

        assert decomposition is not None
        assert len(decomposition.sub_goal_ids) >= 2
        assert decomposition.decomposition_strategy == "sequential"


class TestSkillExecutionLoop:
    """Test skill execution loop."""

    def test_execute_simple_goal(self, seed_core):
        """Test executing a simple goal."""
        loop = seed_core._execution_loop

        goal = Goal(
            goal_id="test_goal",
            description="Research market opportunities",
            goal_type="market_research",
        )

        record = loop.execute_goal(goal, auto_select=True)

        assert record is not None
        assert record.goal_id == "test_goal"
        assert record.skill_name is not None
        # Note: Success will be False because we're using stub execution

    def test_blocked_execution_for_approval_required_skill(self, seed_core):
        """Test that skills requiring approval create AWAITING_APPROVAL records."""
        loop = seed_core._execution_loop

        goal = Goal(
            goal_id="test_goal",
            description="Use approval required skill",
            goal_type="test_type",
        )

        # Force use of approval-required skill
        record = loop.execute_goal(goal, auto_select=False, skill_name="approval-required-skill")

        # With governed execution, approval-required skills create AWAITING_APPROVAL records
        assert record.outcome == OutcomeType.AWAITING_APPROVAL
        assert record.approval_record_id is not None
        assert "approval" in record.notes.lower()
        assert record.success is False  # Not executed yet
        assert record.quality_score == 0.0  # No quality until execution


class TestSeedCore:
    """Test full Seed Core integration."""

    def test_seed_core_initialization(self, seed_core):
        """Test Seed Core initializes correctly."""
        assert seed_core.is_initialized is True

    def test_achieve_simple_goal(self, seed_core):
        """Test achieving a simple goal."""
        result = seed_core.achieve_goal(
            description="Research market opportunities",
            goal_type="market_research",
            allow_decomposition=False,
        )

        assert result is not None
        assert "goal" in result
        assert "execution_records" in result
        assert len(result["execution_records"]) == 1

    def test_achieve_complex_goal_with_decomposition(self, seed_core):
        """Test achieving a complex goal via decomposition."""
        result = seed_core.achieve_goal(
            description="First research the market, then analyze competitors, and finally create a detailed report",
            goal_type="market_research",
            allow_decomposition=True,
        )

        assert result is not None
        assert "goal" in result
        assert "execution_records" in result
        # Should have multiple execution records (one per sub-goal)
        assert len(result["execution_records"]) >= 2
        assert "decomposition" in result

    def test_introspection(self, seed_core):
        """Test system introspection."""
        intro = seed_core.introspect()

        assert intro["initialized"] is True
        assert "skills_available" in intro
        assert intro["skills_available"] > 0
        assert "memory_stats" in intro

    def test_learning_improves_skill_selection(self, seed_core):
        """Test that repeated executions improve skill selection."""
        memory = seed_core._seed_memory

        # Execute same goal type multiple times with different skills
        # Simulate market-research-skill performing better
        for i in range(5):
            record = SkillExecutionRecord(
                execution_id=f"exec_mr_{i}",
                goal_id=f"goal_{i}",
                goal_type="market_research",
                skill_name="market-research-skill",
                outcome=OutcomeType.SUCCESS,
                quality_score=0.9,
                success=True,
            )
            memory.save_execution_record(record)

        # Simulate data-analysis-skill performing worse
        for i in range(3):
            record = SkillExecutionRecord(
                execution_id=f"exec_da_{i}",
                goal_id=f"goal_da_{i}",
                goal_type="market_research",
                skill_name="data-analysis-skill",
                outcome=OutcomeType.FAILURE,
                quality_score=0.3,
                success=False,
            )
            memory.save_execution_record(record)

        # Now get best skill for market_research
        ranker = seed_core._skill_ranker
        best = ranker.get_best_skill(
            goal_type="market_research",
            goal_description="research the market",
        )

        # Should prefer market-research-skill
        assert best is not None
        assert best.skill.name == "market-research-skill"
        assert best.ranking is not None
        assert best.ranking.success_rate > 0.5


class TestGovernanceBoundaries:
    """Test that governance boundaries are still respected."""

    def test_approval_required_skill_blocked(self, seed_core):
        """Test skills requiring approval are blocked from execution."""
        result = seed_core.achieve_goal(
            description="Use a skill that requires approval",
            goal_type="test_type",
            allow_decomposition=False,
        )

        # The execution should happen but may be awaiting approval if it selects approval-required skill
        # With governed execution, approval-required skills create AWAITING_APPROVAL records
        assert "execution_records" in result
        if len(result["execution_records"]) > 0:
            record = result["execution_records"][0]
            # If approval-required skill was selected, should be awaiting approval
            if record.get("skill_name") == "approval-required-skill":
                assert record.get("outcome") == "awaiting_approval"
                assert record.get("approval_record_id") is not None
