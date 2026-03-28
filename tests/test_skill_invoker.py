"""
Tests for Skill Invoker - Real skill invocation wiring.

Tests cover:
- Execution mode classification
- Real invocation paths (dry run, local, connector-backed)
- Blocked paths (policy, credentials)
- Outcome capture and metadata
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from core.skill_invoker import (
    SkillInvoker,
    SkillExecutionMode,
    SkillInvocationResult,
    SAFE_LOCAL_SKILLS,
    SKILL_TO_CONNECTOR_MAP,
)
from core.skill_registry import SkillDefinition, SkillCategory
from core.integration_skill import IntegrationResponse, ExecutionMode as IntegrationExecutionMode


@pytest.fixture
def mock_integration_skill():
    """Create a mock IntegrationSkill."""
    return Mock()


@pytest.fixture
def invoker(mock_integration_skill):
    """Create a SkillInvoker with mocked integration."""
    return SkillInvoker(integration_skill=mock_integration_skill)


@pytest.fixture
def safe_local_skill():
    """Create a safe local skill definition."""
    return SkillDefinition(
        name="code-reviewer",
        description="Review code for quality and best practices",
        path="/path/to/code-reviewer",
        keywords=["review", "code", "quality"],
        category=SkillCategory.TESTING_QA,
        is_proactive=True,
        requires_approval=False,
    )


@pytest.fixture
def connector_backed_skill():
    """Create a connector-backed skill definition."""
    return SkillDefinition(
        name="apollo-automation",
        description="Automate Apollo lead generation",
        path="/path/to/apollo-automation",
        keywords=["apollo", "leads", "sales"],
        category=SkillCategory.LEAD_GENERATION,
        is_proactive=False,
        requires_approval=False,
    )


@pytest.fixture
def approval_required_skill():
    """Create a skill requiring approval."""
    return SkillDefinition(
        name="stripe-automation",
        description="Automate Stripe payment operations",
        path="/path/to/stripe-automation",
        keywords=["stripe", "payment", "financial"],
        category=SkillCategory.PAYMENT_ECOMMERCE,
        is_proactive=False,
        requires_approval=True,
    )


@pytest.fixture
def not_invokable_skill():
    """Create a skill with no invocation path."""
    return SkillDefinition(
        name="unknown-skill",
        description="Some skill with no invocation path",
        path="/path/to/unknown",
        keywords=["unknown"],
        category=SkillCategory.UNCATEGORIZED,
        is_proactive=False,
        requires_approval=False,
    )


class TestExecutionModeClassification:
    """Test execution mode classification logic."""

    def test_blocked_policy_for_approval_required(self, invoker, approval_required_skill):
        """Skills requiring approval should be classified as BLOCKED_POLICY."""
        mode = invoker.classify_execution_mode(approval_required_skill)
        assert mode == SkillExecutionMode.BLOCKED_POLICY

    def test_connector_backed_with_ready_connector(
        self, invoker, mock_integration_skill, connector_backed_skill
    ):
        """Skills with ready connectors should be CONNECTOR_BACKED."""
        mock_integration_skill.get_connector_status.return_value = {
            "status": "ready"
        }
        mode = invoker.classify_execution_mode(connector_backed_skill)
        assert mode == SkillExecutionMode.CONNECTOR_BACKED

    def test_blocked_credential_with_missing_connector(
        self, invoker, mock_integration_skill, connector_backed_skill
    ):
        """Skills with missing connectors should be BLOCKED_CREDENTIAL."""
        mock_integration_skill.get_connector_status.return_value = {
            "status": "not_configured"
        }
        mode = invoker.classify_execution_mode(connector_backed_skill)
        assert mode == SkillExecutionMode.BLOCKED_CREDENTIAL

    def test_real_local_for_safe_skills(self, invoker, safe_local_skill):
        """Safe local skills should be REAL_LOCAL."""
        mode = invoker.classify_execution_mode(safe_local_skill)
        assert mode == SkillExecutionMode.REAL_LOCAL

    def test_not_invokable_by_default(self, invoker, not_invokable_skill):
        """Skills without invocation path should be NOT_INVOKABLE."""
        mode = invoker.classify_execution_mode(not_invokable_skill)
        assert mode == SkillExecutionMode.NOT_INVOKABLE


class TestRealInvocationPaths:
    """Test actual skill invocation paths."""

    def test_blocked_policy_returns_error(self, invoker, approval_required_skill):
        """Blocked skills should return error result."""
        result = invoker.invoke_skill(
            approval_required_skill,
            "Test payment processing",
            "payment_processing",
        )

        assert not result.success
        assert result.mode == SkillExecutionMode.BLOCKED_POLICY
        assert "requires approval" in result.error.lower()

    def test_blocked_credential_returns_error(
        self, invoker, mock_integration_skill, connector_backed_skill
    ):
        """Skills with missing credentials should return error."""
        mock_integration_skill.get_connector_status.return_value = None

        result = invoker.invoke_skill(
            connector_backed_skill,
            "Find leads in SaaS",
            "lead_generation",
        )

        assert not result.success
        assert result.mode == SkillExecutionMode.BLOCKED_CREDENTIAL
        assert "credentials" in result.error.lower()

    def test_not_invokable_returns_error(self, invoker, not_invokable_skill):
        """Not invokable skills should return error result."""
        result = invoker.invoke_skill(
            not_invokable_skill,
            "Do something unknown",
            "unknown_goal",
        )

        assert not result.success
        assert result.mode == SkillExecutionMode.NOT_INVOKABLE
        assert "no invocation path" in result.error.lower()

    def test_connector_backed_invocation_success(
        self, invoker, mock_integration_skill, connector_backed_skill
    ):
        """Successful connector-backed invocation."""
        # Mock connector status
        mock_integration_skill.get_connector_status.return_value = {
            "status": "ready"
        }

        # Mock successful execution
        mock_integration_skill.execute.return_value = IntegrationResponse(
            success=True,
            connector="apollo",
            operation="search",
            mode=IntegrationExecutionMode.LIVE,
            data={"leads": [{"name": "Test Lead", "company": "Test Corp"}]},
        )

        result = invoker.invoke_skill(
            connector_backed_skill,
            "Search for SaaS leads",
            "lead_generation",
        )

        assert result.success
        assert result.mode == SkillExecutionMode.CONNECTOR_BACKED
        assert result.output is not None
        assert result.error is None
        assert "apollo" in result.metadata["connector"]

    def test_connector_backed_invocation_failure(
        self, invoker, mock_integration_skill, connector_backed_skill
    ):
        """Failed connector-backed invocation."""
        mock_integration_skill.get_connector_status.return_value = {
            "status": "ready"
        }

        mock_integration_skill.execute.return_value = IntegrationResponse(
            success=False,
            connector="apollo",
            operation="search",
            mode=IntegrationExecutionMode.LIVE,
            error="API rate limit exceeded",
        )

        result = invoker.invoke_skill(
            connector_backed_skill,
            "Search for SaaS leads",
            "lead_generation",
        )

        assert not result.success
        assert result.mode == SkillExecutionMode.CONNECTOR_BACKED
        assert "rate limit" in result.error.lower()

    @patch("subprocess.run")
    def test_local_invocation_success(self, mock_run, invoker, safe_local_skill):
        """Successful local CLI invocation."""
        # Mock successful subprocess
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Code review completed successfully",
            stderr="",
        )

        result = invoker.invoke_skill(
            safe_local_skill,
            "Review authentication module",
            "code_review",
        )

        assert result.success
        assert result.mode == SkillExecutionMode.REAL_LOCAL
        assert result.exit_code == 0
        assert "successfully" in result.output.lower()

    @patch("subprocess.run")
    def test_local_invocation_failure(self, mock_run, invoker, safe_local_skill):
        """Failed local CLI invocation."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error: File not found",
        )

        result = invoker.invoke_skill(
            safe_local_skill,
            "Review authentication module",
            "code_review",
        )

        assert not result.success
        assert result.mode == SkillExecutionMode.REAL_LOCAL
        assert result.exit_code == 1
        assert "not found" in result.error.lower()

    @patch("subprocess.run")
    def test_local_invocation_timeout(self, mock_run, invoker, safe_local_skill):
        """Local invocation with timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=30)

        result = invoker.invoke_skill(
            safe_local_skill,
            "Review authentication module",
            "code_review",
        )

        assert not result.success
        assert result.mode == SkillExecutionMode.REAL_LOCAL
        assert "timed out" in result.error.lower()
        assert result.metadata.get("timeout") is True

    @patch("subprocess.run")
    def test_local_invocation_cli_not_found(self, mock_run, invoker, safe_local_skill):
        """Local invocation when CLI not available falls back to dry run."""
        mock_run.side_effect = FileNotFoundError("claude: command not found")

        result = invoker.invoke_skill(
            safe_local_skill,
            "Review authentication module",
            "code_review",
        )

        # Should fall back to dry run
        assert result.mode == SkillExecutionMode.DRY_RUN
        assert result.metadata.get("simulated") is True


class TestOutcomeCapture:
    """Test outcome capture and metadata."""

    def test_result_to_dict_serialization(self):
        """SkillInvocationResult should serialize to dict."""
        result = SkillInvocationResult(
            success=True,
            mode=SkillExecutionMode.REAL_LOCAL,
            output="Test output",
            duration_seconds=1.234,
            exit_code=0,
            metadata={"test": "data"},
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["mode"] == "real_local"
        assert result_dict["output"] == "Test output"
        assert result_dict["duration_seconds"] == 1.234
        assert result_dict["exit_code"] == 0
        assert result_dict["metadata"]["test"] == "data"
        assert "timestamp" in result_dict

    def test_captures_duration(self, invoker, mock_integration_skill, connector_backed_skill):
        """Invocation should capture execution duration."""
        mock_integration_skill.get_connector_status.return_value = {"status": "ready"}
        mock_integration_skill.execute.return_value = IntegrationResponse(
            success=True,
            connector="apollo",
            operation="search",
            mode=IntegrationExecutionMode.LIVE,
            data={"test": "data"},
        )

        result = invoker.invoke_skill(
            connector_backed_skill,
            "Test goal",
            "test_type",
        )

        assert result.duration_seconds > 0

    def test_captures_detailed_metadata(
        self, invoker, mock_integration_skill, connector_backed_skill
    ):
        """Invocation should capture detailed metadata."""
        mock_integration_skill.get_connector_status.return_value = {"status": "ready"}
        mock_integration_skill.execute.return_value = IntegrationResponse(
            success=True,
            connector="apollo",
            operation="search",
            mode=IntegrationExecutionMode.LIVE,
            data={"test": "data"},
            policy_decision={"allowed": True, "reason": "Test"},
        )

        result = invoker.invoke_skill(
            connector_backed_skill,
            "Test goal",
            "test_type",
        )

        assert "connector" in result.metadata
        assert "operation" in result.metadata
        assert "policy_decision" in result.metadata


class TestGoalToOperationMapping:
    """Test goal to connector operation mapping."""

    def test_maps_search_keywords(self, invoker):
        """Should map search-related goals to search operation."""
        op = invoker._map_goal_to_operation(
            "lead_generation", "Find leads in technology sector", "apollo-automation"
        )
        assert op == "search"

    def test_maps_create_keywords(self, invoker):
        """Should map create-related goals to create operation."""
        op = invoker._map_goal_to_operation(
            "project_setup", "Create new project workspace", "asana-automation"
        )
        assert op == "create"

    def test_maps_update_keywords(self, invoker):
        """Should map update-related goals to update operation."""
        op = invoker._map_goal_to_operation(
            "project_update", "Update project status", "notion-automation"
        )
        assert op == "update"

    def test_default_operation(self, invoker):
        """Should use execute as default operation."""
        op = invoker._map_goal_to_operation(
            "unknown_type", "Do something generic", "unknown-skill"
        )
        assert op == "execute"
