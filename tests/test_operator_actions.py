"""
Tests for Operator Actions.

Tests the unified operator action interface for workflow control.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from core.operator_actions import (
    OperatorActions,
    OperatorActionType,
    OperatorActionResult,
    get_operator_actions,
)
from core.recovery_manager import (
    RecoveryManager,
    RecoveryAction,
    RecoveryResult,
    BlockerType,
)


class TestApprovalActions:
    """Tests for approve/deny actions."""

    @patch("core.operator_actions.OperatorActions._get_state_store")
    @patch("core.operator_actions.OperatorActions._get_approval_manager")
    def test_approve_action(self, mock_approval, mock_store):
        """Test approving a pending request."""
        manager = RecoveryManager()
        actions = OperatorActions(recovery_manager=manager)

        mock_state = Mock()
        mock_state.get_approval.return_value = {
            "record_id": "appr_123",
            "status": "pending",
            "request_id": "req_456",
            "description": "Test approval",
        }
        mock_store.return_value = mock_state

        mock_approval_mgr = Mock()
        mock_approval_mgr.approve.return_value = True
        mock_approval.return_value = mock_approval_mgr

        result = actions.approve(
            approval_id="appr_123",
            rationale="Approved for testing",
            performed_by="operator",
            auto_resume=False,
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.APPROVE
        mock_state.save_approval.assert_called_once()

    @patch("core.operator_actions.OperatorActions._get_state_store")
    @patch("core.operator_actions.OperatorActions._get_approval_manager")
    def test_approve_not_found(self, mock_approval, mock_store):
        """Test approving a non-existent approval."""
        manager = RecoveryManager()
        actions = OperatorActions(recovery_manager=manager)

        mock_state = Mock()
        mock_state.get_approval.return_value = None
        mock_store.return_value = mock_state

        result = actions.approve(
            approval_id="nonexistent",
            performed_by="operator",
        )

        assert result.success is False
        assert "not found" in result.error.lower()

    @patch("core.operator_actions.OperatorActions._get_state_store")
    @patch("core.operator_actions.OperatorActions._get_approval_manager")
    def test_deny_action(self, mock_approval, mock_store):
        """Test denying a pending request."""
        manager = RecoveryManager()
        actions = OperatorActions(recovery_manager=manager)

        mock_state = Mock()
        mock_state.get_approval.return_value = {
            "record_id": "appr_123",
            "status": "pending",
            "request_id": "req_456",
        }
        mock_store.return_value = mock_state

        mock_approval_mgr = Mock()
        mock_approval_mgr.deny.return_value = True
        mock_approval.return_value = mock_approval_mgr

        result = actions.deny(
            approval_id="appr_123",
            rationale="Not needed",
            performed_by="operator",
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.DENY
        mock_state.save_approval.assert_called_once()


class TestResumeActions:
    """Tests for resume actions."""

    def test_resume_scenario_action(self):
        """Test resume scenario action."""
        mock_manager = Mock(spec=RecoveryManager)
        mock_manager.resume_scenario.return_value = RecoveryResult(
            success=True,
            action=RecoveryAction.RESUME,
            scenario_run_id="run_123",
            new_run_id="run_456",
            message="Resumed successfully",
        )

        actions = OperatorActions(recovery_manager=mock_manager)

        result = actions.resume_scenario(
            run_id="run_123",
            performed_by="operator",
            skip_failed=False,
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.RESUME
        assert result.new_run_id == "run_456"
        mock_manager.resume_scenario.assert_called_once_with(
            run_id="run_123",
            resumed_by="operator",
            skip_failed_step=False,
        )


class TestRetryActions:
    """Tests for retry actions."""

    def test_retry_job_action(self):
        """Test retry job action."""
        mock_manager = Mock(spec=RecoveryManager)
        mock_manager.retry_job.return_value = RecoveryResult(
            success=True,
            action=RecoveryAction.RETRY,
            job_id="job_123",
            new_job_id="job_456",
            message="Retried successfully",
        )

        actions = OperatorActions(recovery_manager=mock_manager)

        result = actions.retry_job(
            job_id="job_123",
            performed_by="operator",
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.RETRY
        assert result.new_job_id == "job_456"

    def test_retry_connector_action(self):
        """Test retry connector action."""
        mock_manager = Mock(spec=RecoveryManager)
        mock_manager.retry_connector_action.return_value = RecoveryResult(
            success=True,
            action=RecoveryAction.RETRY,
            message="Connector action retried",
        )

        actions = OperatorActions(recovery_manager=mock_manager)

        result = actions.retry_connector_action(
            execution_id="exec_123",
            performed_by="operator",
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.RETRY

    def test_retry_scenario_step_action(self):
        """Test retry scenario step action."""
        mock_manager = Mock(spec=RecoveryManager)
        mock_manager.retry_scenario_step.return_value = RecoveryResult(
            success=True,
            action=RecoveryAction.RETRY,
            scenario_run_id="run_123",
            step_id="step_2",
            new_run_id="run_456",
            message="Step retried",
        )

        actions = OperatorActions(recovery_manager=mock_manager)

        result = actions.retry_scenario_step(
            run_id="run_123",
            step_id="step_2",
            performed_by="operator",
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.RETRY
        assert result.target_id == "run_123:step_2"


class TestRerunActions:
    """Tests for rerun actions."""

    def test_rerun_plan_action(self):
        """Test rerun plan action."""
        mock_manager = Mock(spec=RecoveryManager)
        mock_manager.rerun_plan.return_value = RecoveryResult(
            success=True,
            action=RecoveryAction.RERUN,
            plan_id="plan_123",
            new_job_id="job_456",
            message="Plan rerun",
        )

        actions = OperatorActions(recovery_manager=mock_manager)

        result = actions.rerun_plan(
            plan_id="plan_123",
            performed_by="operator",
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.RERUN
        assert result.new_job_id == "job_456"

    def test_rerun_scenario_action(self):
        """Test rerun scenario action."""
        mock_manager = Mock(spec=RecoveryManager)
        mock_manager.rerun_scenario.return_value = RecoveryResult(
            success=True,
            action=RecoveryAction.RERUN,
            scenario_run_id="run_123",
            new_run_id="run_456",
            message="Scenario rerun",
        )

        actions = OperatorActions(recovery_manager=mock_manager)

        result = actions.rerun_scenario(
            run_id="run_123",
            performed_by="operator",
            new_inputs={"company": "NewCorp"},
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.RERUN
        assert result.new_run_id == "run_456"


class TestSkipActions:
    """Tests for skip actions."""

    def test_skip_step_action(self):
        """Test skip step action."""
        mock_manager = Mock(spec=RecoveryManager)
        mock_manager.resume_scenario.return_value = RecoveryResult(
            success=True,
            action=RecoveryAction.RESUME,
            scenario_run_id="run_123",
            new_run_id="run_456",
            message="Resumed with skip",
        )

        actions = OperatorActions(recovery_manager=mock_manager)

        result = actions.skip_step(
            run_id="run_123",
            step_id="step_2",
            performed_by="operator",
            reason="Not needed",
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.SKIP
        mock_manager.resume_scenario.assert_called_once_with(
            run_id="run_123",
            resumed_by="operator",
            skip_failed_step=True,
        )


class TestInspectActions:
    """Tests for inspect actions."""

    def test_inspect_workflow(self):
        """Test inspect workflow action."""
        mock_manager = Mock(spec=RecoveryManager)
        mock_manager.get_workflow_status.return_value = {
            "scenario": {"run_id": "run_123", "status": "awaiting_approval"},
            "blockers": [{"blocker_type": "approval_required"}],
            "available_actions": ["resume"],
        }

        actions = OperatorActions(recovery_manager=mock_manager)

        result = actions.inspect_workflow(
            scenario_run_id="run_123",
            performed_by="operator",
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.INSPECT
        assert "scenario" in result.data

    def test_inspect_blockers(self):
        """Test inspect blockers action."""
        mock_manager = Mock(spec=RecoveryManager)
        mock_manager.get_active_blockers.return_value = [
            Mock(to_dict=lambda: {"blocker_type": "approval_required"}),
            Mock(to_dict=lambda: {"blocker_type": "step_failed"}),
        ]

        actions = OperatorActions(recovery_manager=mock_manager)

        result = actions.inspect_blockers(
            performed_by="operator",
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.INSPECT
        assert result.data["count"] == 2


class TestCancelActions:
    """Tests for cancel actions."""

    @patch("core.operator_actions.OperatorActions._get_state_store")
    def test_cancel_scenario(self, mock_store):
        """Test cancel scenario action."""
        mock_manager = Mock(spec=RecoveryManager)
        mock_manager.get_active_blockers.return_value = []
        mock_manager.resolve_blocker = Mock()

        mock_state = Mock()
        mock_state.get_scenario_run.return_value = {
            "run_id": "run_123",
            "status": "running",
        }
        mock_store.return_value = mock_state

        actions = OperatorActions(recovery_manager=mock_manager)

        result = actions.cancel_scenario(
            run_id="run_123",
            performed_by="operator",
            reason="No longer needed",
        )

        assert result.success is True
        assert result.action_type == OperatorActionType.CANCEL
        mock_state.save_scenario_run.assert_called_once()

    @patch("core.operator_actions.OperatorActions._get_state_store")
    def test_cancel_completed_scenario_fails(self, mock_store):
        """Test that cancelling completed scenario fails."""
        mock_manager = Mock(spec=RecoveryManager)

        mock_state = Mock()
        mock_state.get_scenario_run.return_value = {
            "run_id": "run_123",
            "status": "completed",
        }
        mock_store.return_value = mock_state

        actions = OperatorActions(recovery_manager=mock_manager)

        result = actions.cancel_scenario(
            run_id="run_123",
            performed_by="operator",
        )

        assert result.success is False
        assert "cannot be cancelled" in result.error.lower()


class TestOperatorDashboard:
    """Tests for operator dashboard."""

    def test_get_operator_dashboard(self):
        """Test getting operator dashboard."""
        mock_manager = Mock(spec=RecoveryManager)
        mock_manager.get_pending_approvals_with_context.return_value = [
            {"record_id": "appr_1", "blocked_workflows": 1}
        ]
        mock_manager.get_paused_scenarios.return_value = [
            {"run_id": "run_1", "status": "awaiting_approval"}
        ]
        mock_manager.get_failed_jobs.return_value = [
            {"job_id": "job_1", "status": "failed"}
        ]
        mock_manager.get_active_blockers.return_value = [
            Mock(to_dict=lambda: {"blocker_type": "approval_required"})
        ]

        actions = OperatorActions(recovery_manager=mock_manager)

        dashboard = actions.get_operator_dashboard()

        assert "pending_approvals" in dashboard
        assert "paused_scenarios" in dashboard
        assert "failed_jobs" in dashboard
        assert "active_blockers" in dashboard
        assert "recent_actions" in dashboard

    def test_get_action_history(self):
        """Test getting action history."""
        mock_manager = Mock(spec=RecoveryManager)
        actions = OperatorActions(recovery_manager=mock_manager)

        # Perform some actions to build history
        mock_manager.resume_scenario.return_value = RecoveryResult(
            success=True,
            action=RecoveryAction.RESUME,
            message="Test",
        )

        actions.resume_scenario("run_123", "operator")

        history = actions.get_action_history(limit=10)

        assert len(history) == 1
        assert history[0]["action_type"] == "resume"


class TestOperatorActionResult:
    """Tests for OperatorActionResult dataclass."""

    def test_result_to_dict(self):
        """Test result serialization."""
        result = OperatorActionResult(
            success=True,
            action_type=OperatorActionType.APPROVE,
            message="Approved",
            target_id="appr_123",
            target_type="approval",
            performed_by="operator",
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["action_type"] == "approve"
        assert d["message"] == "Approved"
        assert d["target_id"] == "appr_123"
        assert d["performed_by"] == "operator"


class TestSingleton:
    """Tests for singleton behavior."""

    def test_get_operator_actions_singleton(self):
        """Test that get_operator_actions returns singleton."""
        # Reset global
        import core.operator_actions
        core.operator_actions._operator_actions = None

        actions1 = get_operator_actions()
        actions2 = get_operator_actions()

        assert actions1 is actions2
