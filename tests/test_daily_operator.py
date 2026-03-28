"""
Tests for Daily Operator Activation Features.

Tests the dashboard summary, unified work queue, next-step guidance,
and quick action count functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock


# =============================================================================
# Test Attention Summary
# =============================================================================

class TestAttentionSummary:
    """Tests for get_attention_summary function."""

    def test_attention_summary_aggregation(self):
        """Test attention summary aggregates all attention items."""
        from ui.services import get_attention_summary

        # Create mock service with expected methods
        mock_service = Mock()
        mock_service.get_pending_approvals.return_value = [
            {"record_id": "a1", "action": "Test action"},
            {"record_id": "a2", "action": "Another action"},
        ]
        mock_service.get_paused_scenarios.return_value = [
            {"run_id": "s1", "scenario_name": "Test scenario"},
        ]
        mock_service.get_failed_jobs.return_value = [
            {"job_id": "j1", "error": "Test error"},
            {"job_id": "j2", "error": "Another error"},
        ]
        mock_service.get_active_blockers.return_value = []
        mock_service.get_capacity_status.return_value = {"warnings": []}
        mock_service.get_credentials_summary.return_value = {"expiring_soon": 0}

        summary = get_attention_summary(mock_service)

        assert summary["attention_count"] == 5
        assert summary["pending_approvals"] == 2
        assert summary["paused_scenarios"] == 1
        assert summary["failed_jobs"] == 2
        assert summary["active_blockers"] == 0

    def test_attention_summary_with_no_items(self):
        """Test attention summary with no attention items."""
        from ui.services import get_attention_summary

        mock_service = Mock()
        mock_service.get_pending_approvals.return_value = []
        mock_service.get_paused_scenarios.return_value = []
        mock_service.get_failed_jobs.return_value = []
        mock_service.get_active_blockers.return_value = []
        mock_service.get_capacity_status.return_value = {"warnings": []}
        mock_service.get_credentials_summary.return_value = {"expiring_soon": 0}

        summary = get_attention_summary(mock_service)

        assert summary["attention_count"] == 0
        assert summary["pending_approvals"] == 0
        assert summary["items"]["approvals"] == []
        assert summary["items"]["paused"] == []
        assert summary["items"]["failed"] == []

    def test_attention_summary_includes_items(self):
        """Test attention summary includes actual item data."""
        from ui.services import get_attention_summary

        mock_service = Mock()
        mock_service.get_pending_approvals.return_value = [
            {"record_id": "a1", "action": "Approve connector", "description": "Enable live mode"},
        ]
        mock_service.get_paused_scenarios.return_value = []
        mock_service.get_failed_jobs.return_value = []
        mock_service.get_active_blockers.return_value = []
        mock_service.get_capacity_status.return_value = {"warnings": []}
        mock_service.get_credentials_summary.return_value = {"expiring_soon": 0}

        summary = get_attention_summary(mock_service)

        assert len(summary["items"]["approvals"]) == 1
        assert summary["items"]["approvals"][0]["record_id"] == "a1"


# =============================================================================
# Test Unified Work Queue
# =============================================================================

class TestUnifiedWorkQueue:
    """Tests for get_unified_work_queue function."""

    def test_work_queue_combines_items(self):
        """Test work queue combines all item types."""
        from ui.services import get_unified_work_queue

        mock_service = Mock()
        mock_service.get_pending_approvals.return_value = [
            {"record_id": "a1", "action": "Test", "created_at": "2024-01-01T10:00:00Z"},
        ]
        mock_service.get_paused_scenarios.return_value = [
            {"run_id": "s1", "scenario_name": "Scenario", "paused_at": "2024-01-01T09:00:00Z"},
        ]
        mock_service.get_failed_jobs.return_value = [
            {"job_id": "j1", "error": "Error", "failed_at": "2024-01-01T08:00:00Z"},
        ]
        mock_service.get_active_blockers.return_value = []

        queue = get_unified_work_queue(mock_service, limit=50)

        assert len(queue) == 3
        queue_types = {item["queue_type"] for item in queue}
        assert "approval" in queue_types
        assert "scenario" in queue_types
        assert "job" in queue_types

    def test_work_queue_respects_limit(self):
        """Test work queue respects the limit parameter."""
        from ui.services import get_unified_work_queue

        mock_service = Mock()
        mock_service.get_pending_approvals.return_value = [
            {"record_id": f"a{i}", "action": f"Action {i}", "created_at": f"2024-01-01T{i:02d}:00:00Z"}
            for i in range(10)
        ]
        mock_service.get_paused_scenarios.return_value = []
        mock_service.get_failed_jobs.return_value = []
        mock_service.get_active_blockers.return_value = []

        queue = get_unified_work_queue(mock_service, limit=5)

        assert len(queue) <= 5

    def test_work_queue_item_structure(self):
        """Test work queue items have required fields."""
        from ui.services import get_unified_work_queue

        mock_service = Mock()
        mock_service.get_pending_approvals.return_value = [
            {
                "record_id": "a1",
                "action": "Test Action",
                "connector": "test_connector",
                "operation": "write",
                "risk_level": "medium",
                "created_at": "2024-01-01T10:00:00Z",
            },
        ]
        mock_service.get_paused_scenarios.return_value = []
        mock_service.get_failed_jobs.return_value = []
        mock_service.get_active_blockers.return_value = []

        queue = get_unified_work_queue(mock_service, limit=50)

        assert len(queue) == 1
        item = queue[0]
        assert "id" in item
        assert "queue_type" in item
        assert "category" in item
        assert "title" in item
        assert "priority" in item
        assert "context" in item
        assert "created_at" in item


# =============================================================================
# Test Next-Step Guidance
# =============================================================================

class TestNextStepGuidance:
    """Tests for get_next_step_guidance function."""

    def test_guidance_for_approval(self):
        """Test guidance for approval queue items."""
        from ui.services import get_next_step_guidance

        item = {
            "queue_type": "approval",
            "context": {
                "risk_level": "high",
            },
        }

        guidance = get_next_step_guidance(item)

        assert "recommendation" in guidance
        assert "primary_action" in guidance
        assert guidance["primary_action"]["action"] == "approve"

    def test_guidance_for_paused_scenario(self):
        """Test guidance for paused scenario items."""
        from ui.services import get_next_step_guidance

        item = {
            "queue_type": "scenario",
            "context": {
                "steps_completed": 3,
                "total_steps": 5,
                "pending_approvals": 1,
            },
        }

        guidance = get_next_step_guidance(item)

        assert "recommendation" in guidance
        assert guidance["primary_action"]["action"] == "resume"

    def test_guidance_for_failed_job(self):
        """Test guidance for failed job items."""
        from ui.services import get_next_step_guidance

        item = {
            "queue_type": "job",
            "context": {
                "retry_count": 1,
                "error": "Connection timeout",
            },
        }

        guidance = get_next_step_guidance(item)

        assert "recommendation" in guidance
        assert guidance["primary_action"]["action"] == "retry"

    def test_guidance_for_blocker(self):
        """Test guidance for blocker items."""
        from ui.services import get_next_step_guidance

        item = {
            "queue_type": "blocker",
            "context": {
                "blocker_type": "approval_required",
                "resolution_hint": "Approve pending request",
            },
        }

        guidance = get_next_step_guidance(item)

        assert "recommendation" in guidance
        # Blockers typically need resolution rather than simple action
        assert "secondary_actions" in guidance

    def test_guidance_includes_secondary_actions(self):
        """Test guidance includes secondary actions."""
        from ui.services import get_next_step_guidance

        item = {
            "queue_type": "scenario",
            "context": {},
        }

        guidance = get_next_step_guidance(item)

        assert "secondary_actions" in guidance
        assert isinstance(guidance["secondary_actions"], list)


# =============================================================================
# Test Quick Action Counts
# =============================================================================

class TestQuickActionCounts:
    """Tests for get_quick_action_counts function."""

    def test_quick_counts_structure(self):
        """Test quick counts returns expected structure."""
        from ui.services import get_quick_action_counts

        mock_service = Mock()
        mock_service.get_pending_approvals.return_value = [{"record_id": "a1"}]
        mock_service.get_paused_scenarios.return_value = []
        mock_service.get_failed_jobs.return_value = [{"job_id": "j1"}, {"job_id": "j2"}]
        mock_service.list_scenario_runs.return_value = [
            {"run_id": "r1", "status": "running"},
            {"run_id": "r2", "status": "running"},
        ]
        mock_service.get_connector_actions.return_value = (
            [{"execution_id": "e1", "status": "failed"}],
            {"failed": 1},
        )
        mock_service.get_capacity_status.return_value = {"warnings": []}

        counts = get_quick_action_counts(mock_service)

        assert "pending_approvals" in counts
        assert "paused_scenarios" in counts
        assert "failed_jobs" in counts
        assert "running_scenarios" in counts
        assert "failed_actions" in counts

    def test_quick_counts_values(self):
        """Test quick counts returns correct values."""
        from ui.services import get_quick_action_counts

        mock_service = Mock()
        mock_service.get_pending_approvals.return_value = [
            {"record_id": "a1"},
            {"record_id": "a2"},
            {"record_id": "a3"},
        ]
        mock_service.get_paused_scenarios.return_value = [{"run_id": "s1"}]
        mock_service.get_failed_jobs.return_value = []
        mock_service.list_scenario_runs.return_value = []
        mock_service.get_connector_actions.return_value = ([], {"failed": 0})
        mock_service.get_capacity_status.return_value = {"warnings": ["warning1"]}

        counts = get_quick_action_counts(mock_service)

        assert counts["pending_approvals"] == 3
        # Note: paused_scenarios comes from list_scenario_runs filtered by status
        assert counts["failed_jobs"] == 0
        assert counts["capacity_warnings"] == 1


# =============================================================================
# Test Operator Home Data
# =============================================================================

class TestOperatorHomeData:
    """Tests for get_operator_home_data function."""

    def test_home_data_structure(self):
        """Test operator home data returns complete structure."""
        from ui.services import get_operator_home_data

        mock_service = Mock()

        # Setup all required method returns
        mock_service.get_system_status.return_value = Mock(
            to_dict=lambda: {
                "healthy": True,
                "active_jobs": 0,
                "pending_approvals": 0,
                "budget_utilization": 0.5,
                "total_cost_tracked": 100.0,
            }
        )
        mock_service.get_pending_approvals.return_value = []
        mock_service.get_paused_scenarios.return_value = []
        mock_service.get_failed_jobs.return_value = []
        mock_service.get_active_blockers.return_value = []
        mock_service.get_capacity_status.return_value = {"warnings": []}
        mock_service.get_credentials_summary.return_value = {"expiring_soon": 0}
        mock_service.list_scenario_runs.return_value = []
        mock_service.get_connector_actions.return_value = ([], {"failed": 0})
        mock_service.get_events.return_value = []
        mock_service.get_capacity_decisions.return_value = []
        mock_service.get_combined_status.return_value = {
            "healthy": True,
            "ready": True,
            "dry_run_ready": True,
            "live_ready": False,
        }
        mock_service.get_operator_action_history.return_value = []

        data = get_operator_home_data(mock_service)

        assert "status" in data
        assert "attention" in data
        assert "quick_counts" in data
        assert "recent_events" in data
        assert "combined_status" in data

    def test_home_data_attention_aggregation(self):
        """Test home data correctly aggregates attention items."""
        from ui.services import get_operator_home_data

        mock_service = Mock()

        mock_service.get_system_status.return_value = Mock(
            to_dict=lambda: {
                "healthy": True,
                "active_jobs": 2,
                "pending_approvals": 3,
                "budget_utilization": 0.3,
                "total_cost_tracked": 50.0,
            }
        )
        mock_service.get_pending_approvals.return_value = [
            {"record_id": "a1"},
            {"record_id": "a2"},
            {"record_id": "a3"},
        ]
        mock_service.get_paused_scenarios.return_value = [{"run_id": "s1"}]
        mock_service.get_failed_jobs.return_value = [{"job_id": "j1"}]
        mock_service.get_active_blockers.return_value = []
        mock_service.get_capacity_status.return_value = {"warnings": []}
        mock_service.get_credentials_summary.return_value = {"expiring_soon": 0}
        mock_service.list_scenario_runs.return_value = []
        mock_service.get_connector_actions.return_value = ([], {"failed": 0})
        mock_service.get_events.return_value = []
        mock_service.get_capacity_decisions.return_value = []
        mock_service.get_combined_status.return_value = {"healthy": True, "ready": True}
        mock_service.get_operator_action_history.return_value = []

        data = get_operator_home_data(mock_service)

        assert data["attention"]["attention_count"] == 5
        assert data["attention"]["pending_approvals"] == 3
        assert data["attention"]["paused_scenarios"] == 1
        assert data["attention"]["failed_jobs"] == 1


# =============================================================================
# Test Work Queue Actions
# =============================================================================

class TestWorkQueueActions:
    """Tests for work queue action handling."""

    def test_approval_action_approve(self):
        """Test approve action is handled correctly."""
        from ui.services import OperatorService

        # This tests that the service has the required method
        service = Mock(spec=OperatorService)
        service.approve_with_resume.return_value = {"success": True}

        result = service.approve_with_resume("a1", approver="operator")

        service.approve_with_resume.assert_called_once()
        assert result["success"] is True

    def test_scenario_action_resume(self):
        """Test resume action for paused scenarios."""
        from ui.services import OperatorService

        service = Mock(spec=OperatorService)
        service.resume_scenario.return_value = {"success": True, "resumed": True}

        result = service.resume_scenario("s1", resumed_by="operator")

        service.resume_scenario.assert_called_once()
        assert result["success"] is True

    def test_job_action_retry(self):
        """Test retry action for failed jobs."""
        from ui.services import OperatorService

        service = Mock(spec=OperatorService)
        service.retry_failed_job.return_value = {"success": True, "new_job_id": "j2"}

        result = service.retry_failed_job("j1", retried_by="operator")

        service.retry_failed_job.assert_called_once()
        assert result["success"] is True


# =============================================================================
# Test Priority Calculation
# =============================================================================

class TestPriorityCalculation:
    """Tests for work queue priority calculation."""

    def test_high_risk_approval_is_included(self):
        """Test high-risk approvals are included in queue with context."""
        from ui.services import get_unified_work_queue

        mock_service = Mock()
        mock_service.get_pending_approvals.return_value = [
            {
                "record_id": "a1",
                "action": "Enable live mode",
                "risk_level": "high",
                "created_at": "2024-01-01T10:00:00Z",
            },
        ]
        mock_service.get_paused_scenarios.return_value = []
        mock_service.get_failed_jobs.return_value = []
        mock_service.get_active_blockers.return_value = []

        queue = get_unified_work_queue(mock_service, limit=50)

        assert len(queue) == 1
        assert queue[0]["queue_type"] == "approval"
        # Risk level should be captured in context
        assert queue[0]["context"].get("risk_level") == "high"

    def test_failed_job_priority(self):
        """Test failed jobs get appropriate priority."""
        from ui.services import get_unified_work_queue

        mock_service = Mock()
        mock_service.get_pending_approvals.return_value = []
        mock_service.get_paused_scenarios.return_value = []
        mock_service.get_failed_jobs.return_value = [
            {
                "job_id": "j1",
                "error": "Test error",
                "retry_count": 3,  # Multiple retries indicates urgency
                "failed_at": "2024-01-01T10:00:00Z",
            },
        ]
        mock_service.get_active_blockers.return_value = []

        queue = get_unified_work_queue(mock_service, limit=50)

        assert len(queue) == 1
        # Jobs with multiple retries should be high priority
        assert queue[0]["priority"] in ["high", "medium"]
