"""
Comprehensive tests for the End-to-End Scenario Execution system.

Tests cover:
- Scenario definitions and registry
- Scenario runner execution flow
- State persistence of scenario runs
- Step type execution handlers
- Dry-run vs live execution modes
- UI service integration
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

# Import scenario modules
from core.scenario_definitions import (
    ScenarioDefinition,
    ScenarioStep,
    ScenarioRun,
    StepResult,
    ScenarioStatus,
    StepStatus,
    StepType,
    ScenarioCategory,
    ScenarioRegistry,
    get_scenario_registry,
    create_research_scenario,
    create_notification_scenario,
    create_crm_scenario,
    create_discovery_to_validation_scenario,
)
from core.scenario_runner import ScenarioRunner
from core.state_store import StateStore, StateStoreConfig


class TestScenarioDefinitions:
    """Tests for scenario definition models and enums."""

    def test_step_type_enum_values(self):
        """Verify all step types are defined."""
        assert StepType.SKILL_SELECTION.value == "skill_selection"
        assert StepType.PLAN_CREATION.value == "plan_creation"
        assert StepType.APPROVAL_REQUEST.value == "approval_request"
        assert StepType.CONNECTOR_ACTION.value == "connector_action"
        assert StepType.DISCOVERY_INTAKE.value == "discovery_intake"
        assert StepType.HANDOFF_CREATION.value == "handoff_creation"
        assert StepType.PERSISTENCE_CHECK.value == "persistence_check"
        assert StepType.VALIDATION.value == "validation"

    def test_scenario_status_enum_values(self):
        """Verify all scenario statuses are defined."""
        assert ScenarioStatus.PENDING.value == "pending"
        assert ScenarioStatus.RUNNING.value == "running"
        assert ScenarioStatus.COMPLETED.value == "completed"
        assert ScenarioStatus.FAILED.value == "failed"
        assert ScenarioStatus.CANCELLED.value == "cancelled"

    def test_step_status_enum_values(self):
        """Verify all step statuses are defined."""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.SKIPPED.value == "skipped"

    def test_scenario_category_enum_values(self):
        """Verify all scenario categories are defined."""
        assert ScenarioCategory.RESEARCH.value == "research"
        assert ScenarioCategory.NOTIFICATION.value == "notification"
        assert ScenarioCategory.CRM.value == "crm"
        assert ScenarioCategory.DISCOVERY.value == "discovery"

    def test_scenario_step_creation(self):
        """Test creating a scenario step."""
        step = ScenarioStep(
            step_id="test_step_1",
            name="Test Step",
            description="A test step",
            step_type=StepType.SKILL_SELECTION,
            expected_outcome="Skills identified",
        )
        assert step.step_id == "test_step_1"
        assert step.name == "Test Step"
        assert step.step_type == StepType.SKILL_SELECTION
        assert step.connector is None
        assert step.operation is None
        assert step.expected_outcome == "Skills identified"

    def test_scenario_step_with_connector(self):
        """Test creating a step with connector info."""
        step = ScenarioStep(
            step_id="connector_step",
            name="Connector Step",
            description="A connector step",
            step_type=StepType.CONNECTOR_ACTION,
            connector="tavily",
            operation="search",
        )
        assert step.connector == "tavily"
        assert step.operation == "search"

    def test_scenario_definition_creation(self):
        """Test creating a scenario definition."""
        steps = [
            ScenarioStep(
                step_id="s1",
                name="Step 1",
                description="First step",
                step_type=StepType.SKILL_SELECTION,
            )
        ]
        scenario = ScenarioDefinition(
            scenario_id="test_scenario",
            name="Test Scenario",
            description="A test scenario",
            category=ScenarioCategory.RESEARCH,
            steps=steps,
            required_inputs=["query"],
            connectors_used=["tavily"],
            estimated_duration_seconds=60,
            requires_approval_by_default=True,
        )
        assert scenario.scenario_id == "test_scenario"
        assert scenario.name == "Test Scenario"
        assert len(scenario.steps) == 1
        assert scenario.requires_approval_by_default is True

    def test_scenario_definition_to_dict(self):
        """Test scenario definition serialization."""
        scenario = create_research_scenario()
        data = scenario.to_dict()

        assert data["scenario_id"] == "scenario_research"
        assert data["name"] == "Research Scenario"
        assert "steps" in data
        assert len(data["steps"]) > 0
        assert "tavily" in data["connectors_used"]

    def test_step_result_creation(self):
        """Test creating a step result."""
        result = StepResult(
            step_id="step_1",
            status=StepStatus.COMPLETED,
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=1.5,
            output_data={"result": "success"},
        )
        assert result.step_id == "step_1"
        assert result.status == StepStatus.COMPLETED
        assert result.duration_seconds == 1.5
        assert result.error_message is None

    def test_step_result_with_error(self):
        """Test step result with error."""
        result = StepResult(
            step_id="step_1",
            status=StepStatus.FAILED,
            error_message="Connection timeout",
        )
        assert result.status == StepStatus.FAILED
        assert result.error_message == "Connection timeout"

    def test_scenario_run_creation(self):
        """Test creating a scenario run."""
        run = ScenarioRun(
            run_id="run_123",
            scenario_id="scenario_research",
            scenario_name="Research Scenario",
            status=ScenarioStatus.PENDING,
            dry_run=True,
            inputs={"query": "test"},
            triggered_by="operator",
        )
        assert run.run_id == "run_123"
        assert run.dry_run is True
        assert run.status == ScenarioStatus.PENDING
        assert len(run.step_results) == 0

    def test_scenario_run_to_dict(self):
        """Test scenario run serialization."""
        run = ScenarioRun(
            run_id="run_456",
            scenario_id="scenario_crm",
            scenario_name="CRM Scenario",
            status=ScenarioStatus.COMPLETED,
            dry_run=False,
            inputs={"contact_email": "test@example.com"},
            triggered_by="system",
        )
        run.step_results.append(
            StepResult(
                step_id="step_1",
                status=StepStatus.COMPLETED,
            )
        )

        data = run.to_dict()
        assert data["run_id"] == "run_456"
        assert data["status"] == "completed"
        assert len(data["step_results"]) == 1


class TestScenarioRegistry:
    """Tests for the scenario registry."""

    def test_registry_function_returns_registry(self):
        """Verify get_scenario_registry returns a ScenarioRegistry."""
        registry = get_scenario_registry()
        assert isinstance(registry, ScenarioRegistry)

    def test_registry_has_default_scenarios(self):
        """Verify default scenarios are registered."""
        registry = get_scenario_registry()
        scenarios = registry.list_scenarios()

        scenario_ids = [s.scenario_id for s in scenarios]
        assert "scenario_research" in scenario_ids
        assert "scenario_notification" in scenario_ids
        assert "scenario_crm" in scenario_ids
        assert "scenario_discovery_validation" in scenario_ids

    def test_registry_get_scenario(self):
        """Test getting a specific scenario."""
        registry = get_scenario_registry()
        scenario = registry.get_scenario("scenario_research")

        assert scenario is not None
        assert scenario.name == "Research Scenario"
        assert scenario.category == ScenarioCategory.RESEARCH

    def test_registry_get_nonexistent_scenario(self):
        """Test getting a scenario that doesn't exist."""
        registry = get_scenario_registry()
        scenario = registry.get_scenario("nonexistent")
        assert scenario is None

    def test_registry_list_by_category(self):
        """Test listing scenarios by category."""
        registry = get_scenario_registry()

        research_scenarios = registry.list_scenarios(category=ScenarioCategory.RESEARCH)
        assert len(research_scenarios) >= 1
        assert all(s.category == ScenarioCategory.RESEARCH for s in research_scenarios)

    def test_registry_register_custom_scenario(self):
        """Test registering a custom scenario."""
        registry = get_scenario_registry()

        custom = ScenarioDefinition(
            scenario_id="custom_test_scenario",
            name="Custom Test",
            description="A custom test scenario",
            category=ScenarioCategory.RESEARCH,
            steps=[],
            required_inputs=[],
            connectors_used=[],
        )
        registry.register_scenario(custom)

        retrieved = registry.get_scenario("custom_test_scenario")
        assert retrieved is not None
        assert retrieved.name == "Custom Test"

        # Clean up
        if "custom_test_scenario" in registry._scenarios:
            del registry._scenarios["custom_test_scenario"]

    def test_registry_get_summary(self):
        """Test getting registry summary."""
        registry = get_scenario_registry()
        summary = registry.get_summary()

        assert "total_scenarios" in summary
        assert summary["total_scenarios"] >= 4
        assert "by_category" in summary


class TestBuiltInScenarios:
    """Tests for the four built-in scenarios."""

    def test_research_scenario_structure(self):
        """Test research scenario has correct structure."""
        scenario = create_research_scenario()

        assert scenario.scenario_id == "scenario_research"
        assert scenario.category == ScenarioCategory.RESEARCH
        assert "research_query" in scenario.required_inputs
        assert "tavily" in scenario.connectors_used
        assert len(scenario.steps) >= 3

    def test_research_scenario_steps(self):
        """Test research scenario step types."""
        scenario = create_research_scenario()
        step_types = [s.step_type for s in scenario.steps]

        assert StepType.SKILL_SELECTION in step_types
        assert StepType.PLAN_CREATION in step_types
        assert StepType.CONNECTOR_ACTION in step_types

    def test_notification_scenario_structure(self):
        """Test notification scenario has correct structure."""
        scenario = create_notification_scenario()

        assert scenario.scenario_id == "scenario_notification"
        assert scenario.category == ScenarioCategory.NOTIFICATION
        assert "recipient_email" in scenario.required_inputs
        assert "sendgrid" in scenario.connectors_used
        assert scenario.requires_approval_by_default is True

    def test_notification_scenario_has_approval_step(self):
        """Test notification scenario includes approval step."""
        scenario = create_notification_scenario()
        step_types = [s.step_type for s in scenario.steps]

        assert StepType.APPROVAL_REQUEST in step_types

    def test_crm_scenario_structure(self):
        """Test CRM scenario has correct structure."""
        scenario = create_crm_scenario()

        assert scenario.scenario_id == "scenario_crm"
        assert scenario.category == ScenarioCategory.CRM
        assert "contact_email" in scenario.required_inputs
        assert "hubspot" in scenario.connectors_used

    def test_crm_scenario_has_hubspot_step(self):
        """Test CRM scenario uses HubSpot connector."""
        scenario = create_crm_scenario()

        hubspot_steps = [s for s in scenario.steps if s.connector == "hubspot"]
        assert len(hubspot_steps) >= 1

    def test_discovery_to_validation_scenario_structure(self):
        """Test discovery-to-validation scenario has correct structure."""
        scenario = create_discovery_to_validation_scenario()

        assert scenario.scenario_id == "scenario_discovery_validation"
        assert scenario.category == ScenarioCategory.DISCOVERY
        assert "discovery_text" in scenario.required_inputs

    def test_discovery_scenario_is_multi_step(self):
        """Test discovery scenario has multiple complex steps."""
        scenario = create_discovery_to_validation_scenario()

        assert len(scenario.steps) >= 5
        step_types = [s.step_type for s in scenario.steps]

        # Should have discovery, validation, and handoff steps
        assert StepType.DISCOVERY_INTAKE in step_types
        assert StepType.VALIDATION in step_types


class TestScenarioRunner:
    """Tests for the scenario runner execution engine."""

    @pytest.fixture
    def state_store(self, tmp_path):
        """Create a state store for testing."""
        db_path = str(tmp_path / "test_runner.db")
        config = StateStoreConfig(db_path=db_path)
        store = StateStore(config)
        store.initialize()
        return store

    @pytest.fixture
    def runner(self, state_store):
        """Create a scenario runner with test state store."""
        return ScenarioRunner(state_store=state_store)

    def test_runner_initialization(self, runner):
        """Test runner initializes correctly."""
        assert runner._state_store is not None
        assert runner._registry is not None

    def test_runner_list_scenarios(self, runner):
        """Test runner can list scenarios."""
        scenarios = runner.list_scenarios()
        assert len(scenarios) >= 4

    def test_runner_get_scenario(self, runner):
        """Test runner can get a scenario."""
        scenario = runner.get_scenario("scenario_research")
        assert scenario is not None
        assert scenario["name"] == "Research Scenario"

    def test_runner_dry_run_mode(self, runner):
        """Test runner executes in dry-run mode."""
        result = runner.run_scenario(
            scenario_id="scenario_research",
            inputs={"research_query": "test query"},
            dry_run=True,
            triggered_by="test",
        )

        assert result is not None
        assert result.dry_run is True
        assert result.status in [ScenarioStatus.COMPLETED, ScenarioStatus.FAILED, ScenarioStatus.PARTIAL]

    def test_runner_creates_run_id(self, runner):
        """Test runner generates unique run IDs."""
        result = runner.run_scenario(
            scenario_id="scenario_research",
            inputs={"research_query": "test"},
            dry_run=True,
        )

        assert result.run_id is not None
        assert result.run_id.startswith("run_")

    def test_runner_tracks_step_results(self, runner):
        """Test runner tracks step execution results."""
        result = runner.run_scenario(
            scenario_id="scenario_research",
            inputs={"research_query": "AI research"},
            dry_run=True,
        )

        assert len(result.step_results) > 0
        for step_result in result.step_results:
            assert step_result.step_id is not None
            assert step_result.status in [
                StepStatus.COMPLETED, StepStatus.FAILED,
                StepStatus.SKIPPED, StepStatus.AWAITING_APPROVAL
            ]

    def test_runner_persists_run(self, runner, state_store):
        """Test runner persists run to state store."""
        result = runner.run_scenario(
            scenario_id="scenario_research",
            inputs={"research_query": "persistence test"},
            dry_run=True,
        )

        # Verify run was saved
        saved_run = state_store.get_scenario_run(result.run_id)
        assert saved_run is not None
        assert saved_run["scenario_id"] == "scenario_research"

    def test_runner_records_timestamps(self, runner):
        """Test runner records start and completion timestamps."""
        result = runner.run_scenario(
            scenario_id="scenario_research",
            inputs={"research_query": "timestamp test"},
            dry_run=True,
        )

        assert result.started_at is not None
        assert result.completed_at is not None

    def test_runner_calculates_duration(self, runner):
        """Test runner calculates execution duration."""
        result = runner.run_scenario(
            scenario_id="scenario_research",
            inputs={"research_query": "duration test"},
            dry_run=True,
        )

        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0

    def test_runner_handles_missing_scenario(self, runner):
        """Test runner handles missing scenario gracefully."""
        result = runner.run_scenario(
            scenario_id="nonexistent",
            inputs={},
            dry_run=True,
        )

        assert result.status == ScenarioStatus.FAILED
        assert "not found" in result.error_message.lower()

    def test_runner_validates_required_inputs(self, runner):
        """Test runner validates required inputs."""
        result = runner.run_scenario(
            scenario_id="scenario_research",
            inputs={},  # Missing research_query
            dry_run=True,
        )

        assert result.status == ScenarioStatus.FAILED
        assert "missing" in result.error_message.lower()


class TestScenarioPersistence:
    """Tests for scenario run persistence in state store."""

    @pytest.fixture
    def state_store(self, tmp_path):
        """Create a state store with test database."""
        db_path = str(tmp_path / "test_persistence.db")
        config = StateStoreConfig(db_path=db_path)
        store = StateStore(config)
        store.initialize()
        return store

    def test_save_scenario_run(self, state_store):
        """Test saving a scenario run."""
        run = ScenarioRun(
            run_id="test_run_001",
            scenario_id="scenario_research",
            scenario_name="Research Scenario",
            status=ScenarioStatus.COMPLETED,
            dry_run=True,
            inputs={"query": "test"},
            triggered_by="test_user",
        )

        state_store.save_scenario_run(run.to_dict())

        retrieved = state_store.get_scenario_run("test_run_001")
        assert retrieved is not None
        assert retrieved["scenario_id"] == "scenario_research"

    def test_get_scenario_run_not_found(self, state_store):
        """Test getting a non-existent run."""
        result = state_store.get_scenario_run("nonexistent")
        assert result is None

    def test_list_scenario_runs(self, state_store):
        """Test listing scenario runs."""
        # Create multiple runs
        for i in range(3):
            run = ScenarioRun(
                run_id=f"list_test_{i}",
                scenario_id="scenario_research",
                scenario_name="Research Scenario",
                status=ScenarioStatus.COMPLETED,
                dry_run=True,
                inputs={"query": f"test {i}"},
                triggered_by="test",
            )
            state_store.save_scenario_run(run.to_dict())

        runs = state_store.list_scenario_runs()
        assert len(runs) >= 3

    def test_list_scenario_runs_by_scenario(self, state_store):
        """Test filtering runs by scenario ID."""
        # Create runs for different scenarios
        for i, scenario_id in enumerate(["scenario_research", "scenario_crm"]):
            run = ScenarioRun(
                run_id=f"filter_test_{i}_{scenario_id}",
                scenario_id=scenario_id,
                scenario_name=f"{scenario_id} Scenario",
                status=ScenarioStatus.COMPLETED,
                dry_run=True,
                inputs={},
                triggered_by="test",
            )
            state_store.save_scenario_run(run.to_dict())

        research_runs = state_store.list_scenario_runs(scenario_id="scenario_research")
        assert all(r["scenario_id"] == "scenario_research" for r in research_runs)

    def test_list_scenario_runs_by_status(self, state_store):
        """Test filtering runs by status."""
        for i, status in enumerate([ScenarioStatus.COMPLETED, ScenarioStatus.FAILED]):
            run = ScenarioRun(
                run_id=f"status_test_{i}_{status.value}",
                scenario_id="scenario_research",
                scenario_name="Research Scenario",
                status=status,
                dry_run=True,
                inputs={},
                triggered_by="test",
            )
            state_store.save_scenario_run(run.to_dict())

        completed_runs = state_store.list_scenario_runs(status="completed")
        assert all(r["status"] == "completed" for r in completed_runs)

    def test_list_scenario_runs_with_limit(self, state_store):
        """Test limiting number of returned runs."""
        for i in range(10):
            run = ScenarioRun(
                run_id=f"limit_test_{i}",
                scenario_id="scenario_research",
                scenario_name="Research Scenario",
                status=ScenarioStatus.COMPLETED,
                dry_run=True,
                inputs={},
                triggered_by="test",
            )
            state_store.save_scenario_run(run.to_dict())

        runs = state_store.list_scenario_runs(limit=5)
        assert len(runs) == 5

    def test_scenario_run_stats(self, state_store):
        """Test getting scenario run statistics."""
        # Create runs with different statuses
        statuses = [
            ScenarioStatus.COMPLETED,
            ScenarioStatus.COMPLETED,
            ScenarioStatus.FAILED,
            ScenarioStatus.RUNNING,
        ]
        for i, status in enumerate(statuses):
            run = ScenarioRun(
                run_id=f"stats_test_{i}",
                scenario_id="scenario_research",
                scenario_name="Research Scenario",
                status=status,
                dry_run=True,
                inputs={},
                triggered_by="test",
            )
            state_store.save_scenario_run(run.to_dict())

        stats = state_store.get_scenario_run_stats()
        assert stats["total_runs"] >= 4
        assert stats["by_status"].get("completed", 0) >= 2
        assert stats["by_status"].get("failed", 0) >= 1

    def test_scenario_run_preserves_step_results(self, state_store):
        """Test that step results are preserved in persistence."""
        run = ScenarioRun(
            run_id="step_results_test",
            scenario_id="scenario_research",
            scenario_name="Research Scenario",
            status=ScenarioStatus.COMPLETED,
            dry_run=True,
            inputs={"query": "test"},
            triggered_by="test",
        )
        run.step_results = [
            StepResult(
                step_id="step_1",
                status=StepStatus.COMPLETED,
                output_data={"result": "success"},
            ),
            StepResult(
                step_id="step_2",
                status=StepStatus.FAILED,
                error_message="Test error",
            ),
        ]

        state_store.save_scenario_run(run.to_dict())

        retrieved = state_store.get_scenario_run("step_results_test")
        assert len(retrieved["step_results"]) == 2
        assert retrieved["step_results"][0]["status"] == "completed"
        assert retrieved["step_results"][1]["error_message"] == "Test error"


class TestScenarioStepExecution:
    """Tests for scenario execution with auto-approve."""

    @pytest.fixture
    def state_store(self, tmp_path):
        """Create a state store for testing."""
        db_path = str(tmp_path / "step_test.db")
        config = StateStoreConfig(db_path=db_path)
        store = StateStore(config)
        store.initialize()
        return store

    @pytest.fixture
    def runner(self, state_store):
        """Create a scenario runner."""
        return ScenarioRunner(state_store=state_store)

    def test_research_scenario_completes_dry_run(self, runner):
        """Test research scenario completes in dry-run."""
        result = runner.run_scenario(
            scenario_id="scenario_research",
            inputs={"research_query": "AI trends 2024"},
            dry_run=True,
            auto_approve=True,
        )

        assert result.status in [ScenarioStatus.COMPLETED, ScenarioStatus.PARTIAL]
        assert result.completed_steps > 0

    def test_notification_scenario_with_auto_approve(self, runner):
        """Test notification scenario with auto-approve."""
        result = runner.run_scenario(
            scenario_id="scenario_notification",
            inputs={
                "recipient_email": "test@example.com",
                "email_subject": "Test Subject",
                "email_body": "Test body content",
            },
            dry_run=True,
            auto_approve=True,
        )

        assert result.status in [ScenarioStatus.COMPLETED, ScenarioStatus.PARTIAL]

    def test_crm_scenario_dry_run(self, runner):
        """Test CRM scenario in dry-run mode."""
        result = runner.run_scenario(
            scenario_id="scenario_crm",
            inputs={
                "contact_email": "contact@example.com",
                "contact_firstname": "John",
                "contact_lastname": "Doe",
            },
            dry_run=True,
            auto_approve=True,
        )

        assert result.status in [ScenarioStatus.COMPLETED, ScenarioStatus.PARTIAL]

    def test_discovery_scenario_dry_run(self, runner):
        """Test discovery-to-validation scenario in dry-run."""
        result = runner.run_scenario(
            scenario_id="scenario_discovery_validation",
            inputs={"discovery_text": "New market opportunity for AI services"},
            dry_run=True,
            auto_approve=True,
        )

        assert result.status in [ScenarioStatus.COMPLETED, ScenarioStatus.PARTIAL]
        assert result.completed_steps > 0


class TestScenarioEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def state_store(self, tmp_path):
        """Create a state store for testing."""
        db_path = str(tmp_path / "edge_test.db")
        config = StateStoreConfig(db_path=db_path)
        store = StateStore(config)
        store.initialize()
        return store

    @pytest.fixture
    def runner(self, state_store):
        """Create a scenario runner."""
        return ScenarioRunner(state_store=state_store)

    def test_extra_inputs_are_accepted(self, runner):
        """Test that extra inputs beyond required are accepted."""
        result = runner.run_scenario(
            scenario_id="scenario_research",
            inputs={
                "research_query": "test",
                "extra_param": "should be accepted",
            },
            dry_run=True,
        )

        assert result is not None
        assert "extra_param" in result.inputs

    def test_triggered_by_defaults_to_operator(self, runner):
        """Test that triggered_by defaults to operator."""
        result = runner.run_scenario(
            scenario_id="scenario_research",
            inputs={"research_query": "default trigger test"},
            dry_run=True,
        )

        assert result.triggered_by == "operator"

    def test_run_id_uniqueness(self, runner):
        """Test that each run gets a unique ID."""
        run_ids = set()
        for _ in range(5):
            result = runner.run_scenario(
                scenario_id="scenario_research",
                inputs={"research_query": "unique id test"},
                dry_run=True,
            )
            run_ids.add(result.run_id)

        assert len(run_ids) == 5

    def test_scenario_run_stats(self, runner):
        """Test getting run statistics."""
        # Run a couple of scenarios
        runner.run_scenario(
            scenario_id="scenario_research",
            inputs={"research_query": "stats test 1"},
            dry_run=True,
        )
        runner.run_scenario(
            scenario_id="scenario_research",
            inputs={"research_query": "stats test 2"},
            dry_run=True,
        )

        stats = runner.get_run_stats()
        assert "total_runs" in stats
        assert stats["total_runs"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
