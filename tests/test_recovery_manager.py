"""
Tests for Recovery Manager.

Tests resume, retry, rerun operations and blocker visibility.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from core.recovery_manager import (
    RecoveryManager,
    RecoveryAction,
    RecoveryResult,
    RecoveryStatus,
    BlockerType,
    Blocker,
    get_recovery_manager,
)


class TestBlockerManagement:
    """Tests for blocker registration and tracking."""

    def test_register_blocker_approval_required(self):
        """Test registering an approval required blocker."""
        manager = RecoveryManager()

        blocker = manager.register_blocker(
            blocker_type=BlockerType.APPROVAL_REQUIRED,
            description="Approval needed for live mode",
            reason="Cost exceeds threshold",
            scenario_run_id="run_123",
            approval_id="appr_456",
        )

        assert blocker.blocker_id.startswith("blk_")
        assert blocker.blocker_type == BlockerType.APPROVAL_REQUIRED
        assert blocker.scenario_run_id == "run_123"
        assert blocker.approval_id == "appr_456"
        assert RecoveryAction.RESUME in blocker.available_actions

    def test_register_blocker_step_failed(self):
        """Test registering a failed step blocker."""
        manager = RecoveryManager()

        blocker = manager.register_blocker(
            blocker_type=BlockerType.STEP_FAILED,
            description="Step execution failed",
            reason="Connector timeout",
            scenario_run_id="run_123",
            step_id="step_2",
        )

        assert blocker.blocker_type == BlockerType.STEP_FAILED
        assert RecoveryAction.RETRY in blocker.available_actions
        assert RecoveryAction.SKIP in blocker.available_actions

    def test_register_blocker_budget_blocked(self):
        """Test registering a budget blocked blocker."""
        manager = RecoveryManager()

        blocker = manager.register_blocker(
            blocker_type=BlockerType.BUDGET_BLOCKED,
            description="Budget limit reached",
            reason="Monthly budget exhausted",
            job_id="job_789",
        )

        assert blocker.blocker_type == BlockerType.BUDGET_BLOCKED
        assert blocker.job_id == "job_789"
        assert RecoveryAction.RETRY in blocker.available_actions

    def test_resolve_blocker(self):
        """Test resolving a blocker."""
        manager = RecoveryManager()

        blocker = manager.register_blocker(
            blocker_type=BlockerType.APPROVAL_REQUIRED,
            description="Test blocker",
            reason="Testing",
        )

        result = manager.resolve_blocker(
            blocker_id=blocker.blocker_id,
            action=RecoveryAction.RESUME,
            resolved_by="operator",
        )

        assert result is True
        resolved = manager.get_blocker(blocker.blocker_id)
        assert resolved.resolved_at is not None
        assert resolved.resolved_by == "operator"
        assert resolved.resolution_action == RecoveryAction.RESUME

    def test_get_active_blockers(self):
        """Test getting active blockers with filters."""
        manager = RecoveryManager()

        # Register multiple blockers
        b1 = manager.register_blocker(
            blocker_type=BlockerType.APPROVAL_REQUIRED,
            description="Blocker 1",
            scenario_run_id="run_1",
        )
        b2 = manager.register_blocker(
            blocker_type=BlockerType.STEP_FAILED,
            description="Blocker 2",
            scenario_run_id="run_1",
        )
        b3 = manager.register_blocker(
            blocker_type=BlockerType.APPROVAL_REQUIRED,
            description="Blocker 3",
            scenario_run_id="run_2",
        )

        # Resolve one
        manager.resolve_blocker(b1.blocker_id, RecoveryAction.RESUME)

        # Get active blockers
        active = manager.get_active_blockers()
        assert len(active) == 2

        # Filter by scenario
        run1_blockers = manager.get_active_blockers(scenario_run_id="run_1")
        assert len(run1_blockers) == 1
        assert run1_blockers[0].blocker_id == b2.blocker_id

        # Filter by type
        approval_blockers = manager.get_active_blockers(
            blocker_type=BlockerType.APPROVAL_REQUIRED
        )
        assert len(approval_blockers) == 1
        assert approval_blockers[0].blocker_id == b3.blocker_id

    def test_blocker_to_dict(self):
        """Test blocker serialization."""
        manager = RecoveryManager()

        blocker = manager.register_blocker(
            blocker_type=BlockerType.MISSING_CREDENTIAL,
            description="API key missing",
            reason="Tavily API key not configured",
            connector_execution_id="exec_123",
        )

        d = blocker.to_dict()

        assert d["blocker_id"] == blocker.blocker_id
        assert d["blocker_type"] == "missing_credential"
        assert d["description"] == "API key missing"
        assert d["connector_execution_id"] == "exec_123"
        assert "resume" in d["available_actions"]


class TestResumeOperations:
    """Tests for resume functionality."""

    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    @patch("core.recovery_manager.RecoveryManager._get_scenario_runner")
    def test_resume_scenario_awaiting_approval(self, mock_runner, mock_store):
        """Test resuming a scenario that was awaiting approval."""
        manager = RecoveryManager()

        # Mock state store
        mock_state = Mock()
        mock_state.get_scenario_run.return_value = {
            "run_id": "run_123",
            "scenario_id": "test_scenario",
            "status": "awaiting_approval",
            "inputs": {"company": "Acme"},
            "dry_run": True,
            "step_results": [{"status": "completed"}],
        }
        mock_store.return_value = mock_state

        # Mock scenario runner
        mock_scenario_runner = Mock()
        mock_scenario = Mock()
        mock_scenario_runner.get_scenario.return_value = mock_scenario
        new_run = Mock()
        new_run.run_id = "run_456"
        new_run.status = Mock()
        new_run.status.value = "completed"
        mock_scenario_runner.run_scenario.return_value = new_run
        mock_runner.return_value = mock_scenario_runner

        result = manager.resume_scenario(
            run_id="run_123",
            resumed_by="operator",
        )

        assert result.success is True
        assert result.action == RecoveryAction.RESUME
        assert result.new_run_id == "run_456"
        assert "resumed" in result.message.lower()

    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    def test_resume_scenario_not_found(self, mock_store):
        """Test resuming a non-existent scenario."""
        manager = RecoveryManager()

        mock_state = Mock()
        mock_state.get_scenario_run.return_value = None
        mock_store.return_value = mock_state

        result = manager.resume_scenario(run_id="nonexistent")

        assert result.success is False
        assert "not found" in result.error.lower()

    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    def test_resume_scenario_wrong_status(self, mock_store):
        """Test resuming a scenario with wrong status."""
        manager = RecoveryManager()

        mock_state = Mock()
        mock_state.get_scenario_run.return_value = {
            "run_id": "run_123",
            "status": "completed",
        }
        mock_store.return_value = mock_state

        result = manager.resume_scenario(run_id="run_123")

        assert result.success is False
        assert "cannot be resumed" in result.error.lower()

    def test_register_approval_callback(self):
        """Test registering approval callbacks."""
        manager = RecoveryManager()
        callback_called = False

        def on_approved(approval_id, approval_data):
            nonlocal callback_called
            callback_called = True

        manager.register_approval_callback("appr_123", on_approved)

        # Verify callback is registered
        assert "appr_123" in manager._approval_callbacks

        # Unregister
        result = manager.unregister_approval_callback("appr_123")
        assert result is True
        assert "appr_123" not in manager._approval_callbacks


class TestRetryOperations:
    """Tests for retry functionality."""

    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    @patch("core.recovery_manager.RecoveryManager.rerun_plan")
    def test_retry_job_failed(self, mock_rerun, mock_store):
        """Test retrying a failed job."""
        manager = RecoveryManager()

        mock_state = Mock()
        mock_state.get_job.return_value = {
            "job_id": "job_123",
            "status": "failed",
            "plan_id": "plan_456",
            "error": "Timeout",
        }
        mock_state.get_execution_plan.return_value = {
            "plan_id": "plan_456",
            "objective": "Test",
        }
        mock_store.return_value = mock_state

        mock_rerun.return_value = RecoveryResult(
            success=True,
            action=RecoveryAction.RERUN,
            new_job_id="job_789",
            message="Reran plan",
        )

        result = manager.retry_job(
            job_id="job_123",
            retried_by="operator",
        )

        assert result.success is True
        assert result.action == RecoveryAction.RETRY
        mock_state.save_job.assert_called_once()

    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    def test_retry_job_not_failed(self, mock_store):
        """Test retrying a non-failed job."""
        manager = RecoveryManager()

        mock_state = Mock()
        mock_state.get_job.return_value = {
            "job_id": "job_123",
            "status": "running",
        }
        mock_store.return_value = mock_state

        result = manager.retry_job(job_id="job_123")

        assert result.success is False
        assert "cannot be retried" in result.error.lower()

    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    @patch("core.integration_skill.get_integration_skill")
    def test_retry_connector_action(self, mock_skill_getter, mock_store):
        """Test retrying a failed connector action."""
        manager = RecoveryManager()

        mock_state = Mock()
        mock_state.get_connector_execution_by_id.return_value = {
            "execution_id": "exec_123",
            "connector_name": "tavily",
            "action_name": "search",
            "params": {"query": "test"},
            "mode": "dry_run",
            "success": False,
        }
        mock_store.return_value = mock_state

        mock_skill = Mock()
        mock_skill.execute.return_value = {"success": True}
        mock_skill_getter.return_value = mock_skill

        result = manager.retry_connector_action(
            execution_id="exec_123",
            retried_by="operator",
        )

        assert result.success is True
        assert result.action == RecoveryAction.RETRY


class TestRerunOperations:
    """Tests for rerun functionality."""

    @patch("core.execution_plan.ExecutionPlan")
    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    @patch("core.recovery_manager.RecoveryManager._get_runtime_manager")
    def test_rerun_plan(self, mock_runtime, mock_store, mock_plan_class):
        """Test rerunning an execution plan."""
        manager = RecoveryManager()

        mock_state = Mock()
        mock_state.get_execution_plan.return_value = {
            "plan_id": "plan_123",
            "request_id": "req_456",
            "objective": "Test objective",
            "primary_domain": "research",
            "step_count": 3,
            "selected_skills": ["tavily.search"],
        }
        mock_store.return_value = mock_state

        # Mock ExecutionPlan class
        mock_plan = Mock()
        mock_plan.plan_id = "plan_new_123"
        mock_plan_class.return_value = mock_plan

        mock_rm = Mock()
        mock_rm.is_initialized = True
        runtime_result = Mock()
        runtime_result.success = True
        runtime_result.dispatched_job = Mock()
        runtime_result.dispatched_job.job_id = "new_job_123"
        mock_rm.execute.return_value = runtime_result
        mock_runtime.return_value = mock_rm

        result = manager.rerun_plan(
            plan_id="plan_123",
            triggered_by="operator",
        )

        assert result.success is True
        assert result.action == RecoveryAction.RERUN
        assert result.new_job_id == "new_job_123"

    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    @patch("core.recovery_manager.RecoveryManager._get_scenario_runner")
    def test_rerun_scenario(self, mock_runner, mock_store):
        """Test rerunning a scenario."""
        manager = RecoveryManager()

        mock_state = Mock()
        mock_state.get_scenario_run.return_value = {
            "run_id": "run_123",
            "scenario_id": "test_scenario",
            "inputs": {"company": "Acme"},
            "dry_run": True,
        }
        mock_store.return_value = mock_state

        mock_scenario_runner = Mock()
        new_run = Mock()
        new_run.run_id = "run_456"
        new_run.status = Mock()
        new_run.status.value = "completed"
        new_run.error_message = None
        mock_scenario_runner.run_scenario.return_value = new_run
        mock_runner.return_value = mock_scenario_runner

        result = manager.rerun_scenario(
            run_id="run_123",
            triggered_by="operator",
            new_inputs={"company": "NewCorp"},
        )

        assert result.success is True
        assert result.action == RecoveryAction.RERUN
        assert result.new_run_id == "run_456"


class TestVisibilityMethods:
    """Tests for blocker visibility and workflow status."""

    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    def test_get_paused_scenarios(self, mock_store):
        """Test getting paused scenarios."""
        manager = RecoveryManager()

        mock_state = Mock()
        mock_state.list_scenario_runs.side_effect = [
            [{"run_id": "run_1", "status": "awaiting_approval"}],
            [{"run_id": "run_2", "status": "partial"}],
        ]
        mock_store.return_value = mock_state

        paused = manager.get_paused_scenarios()

        assert len(paused) == 2
        assert paused[0]["run_id"] == "run_1"
        assert "blockers" in paused[0]
        assert "available_actions" in paused[0]

    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    def test_get_failed_jobs(self, mock_store):
        """Test getting failed jobs."""
        manager = RecoveryManager()

        mock_state = Mock()
        mock_state.get_jobs.return_value = [
            {"job_id": "job_1", "status": "failed"},
            {"job_id": "job_2", "status": "failed"},
        ]
        mock_store.return_value = mock_state

        failed = manager.get_failed_jobs()

        assert len(failed) == 2
        assert failed[0]["job_id"] == "job_1"
        assert "blockers" in failed[0]
        assert "available_actions" in failed[0]

    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    def test_get_pending_approvals_with_context(self, mock_store):
        """Test getting pending approvals with blocker context."""
        manager = RecoveryManager()

        # Register a blocker for an approval
        manager.register_blocker(
            blocker_type=BlockerType.APPROVAL_REQUIRED,
            description="Blocked by approval",
            approval_id="appr_123",
            scenario_run_id="run_456",
        )

        mock_state = Mock()
        mock_state.get_pending_approvals.return_value = [
            {"record_id": "appr_123", "status": "pending"},
        ]
        mock_store.return_value = mock_state

        pending = manager.get_pending_approvals_with_context()

        assert len(pending) == 1
        assert pending[0]["record_id"] == "appr_123"
        assert pending[0]["blocked_workflows"] == 1
        assert len(pending[0]["blockers"]) == 1

    @patch("core.recovery_manager.RecoveryManager._get_state_store")
    def test_get_workflow_status(self, mock_store):
        """Test getting comprehensive workflow status."""
        manager = RecoveryManager()

        # Register blockers
        manager.register_blocker(
            blocker_type=BlockerType.APPROVAL_REQUIRED,
            description="Test blocker",
            scenario_run_id="run_123",
        )

        mock_state = Mock()
        mock_state.get_scenario_run.return_value = {
            "run_id": "run_123",
            "status": "awaiting_approval",
            "scenario_id": "test",
        }
        mock_store.return_value = mock_state

        status = manager.get_workflow_status(scenario_run_id="run_123")

        assert "scenario" in status
        assert status["scenario"]["run_id"] == "run_123"
        assert len(status["blockers"]) == 1
        assert "resume" in status["available_actions"]


class TestRecoveryResult:
    """Tests for RecoveryResult dataclass."""

    def test_recovery_result_to_dict(self):
        """Test RecoveryResult serialization."""
        result = RecoveryResult(
            success=True,
            action=RecoveryAction.RESUME,
            scenario_run_id="run_123",
            message="Resumed successfully",
            new_run_id="run_456",
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["action"] == "resume"
        assert d["scenario_run_id"] == "run_123"
        assert d["message"] == "Resumed successfully"
        assert d["new_run_id"] == "run_456"


class TestSingleton:
    """Tests for singleton behavior."""

    def test_get_recovery_manager_singleton(self):
        """Test that get_recovery_manager returns singleton."""
        # Reset global
        import core.recovery_manager
        core.recovery_manager._recovery_manager = None

        manager1 = get_recovery_manager()
        manager2 = get_recovery_manager()

        assert manager1 is manager2
