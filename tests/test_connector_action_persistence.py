"""
Tests for Connector Action Persistence + Audit.

Verifies:
- Connector action execution persistence
- Query and filter functionality
- Safe rendering and redaction
- UI service integration
"""

import pytest
from datetime import datetime, timezone
from core.state_store import StateStore, StateStoreConfig
from core.connector_action_history import ConnectorActionHistory, ConnectorActionFilter
from core.safe_rendering import (
    redact_sensitive_fields,
    safe_connector_request_summary,
    safe_connector_response_summary,
    safe_connector_error_summary,
)


@pytest.fixture
def temp_state_store(tmp_path):
    """Temporary state store for testing."""
    db_path = str(tmp_path / "test_state.db")
    config = StateStoreConfig(db_path=db_path)
    store = StateStore(config)
    store.initialize()
    yield store
    store.close()


@pytest.fixture
def connector_history(temp_state_store):
    """Connector action history instance."""
    return ConnectorActionHistory(state_store=temp_state_store)


class TestConnectorActionPersistence:
    """Test connector action execution persistence."""

    def test_save_connector_execution_with_audit_fields(self, temp_state_store):
        """Test saving connector execution with audit fields."""
        execution = {
            "execution_id": "exec_test_001",
            "connector_name": "telegram",
            "action_name": "send_message",
            "operation": "send_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "live",
            "success": True,
            "duration_seconds": 1.5,
            "estimated_cost": 0.001,
            "actual_cost": 0.0012,
            "cost_class": "MINIMAL",
            "approval_state": "approved",
            "approval_id": "appr_001",
            "execution_status": "completed",
            "job_id": "job_001",
            "plan_id": "plan_001",
            "opportunity_id": "opp_001",
            "request_summary": "Send message: Hello",
            "response_summary": "\u2713 Success, message_id=12345",
            "error_summary": None,
            "operator_decision_ref": "operator_001",
            "params": {"text": "Hello", "chat_id": "123"},
            "metadata": {"live_execution": True},
        }

        success = temp_state_store.save_connector_execution(execution)
        assert success

        # Retrieve and verify
        retrieved = temp_state_store.get_connector_execution_by_id("exec_test_001")
        assert retrieved is not None
        assert retrieved["connector_name"] == "telegram"
        assert retrieved["action_name"] == "send_message"
        assert retrieved["mode"] == "live"
        assert retrieved["success"] == 1
        assert retrieved["approval_state"] == "approved"
        assert retrieved["job_id"] == "job_001"

    def test_query_connector_executions_by_connector(self, temp_state_store):
        """Test querying by connector name."""
        # Save multiple executions
        for i in range(5):
            temp_state_store.save_connector_execution({
                "execution_id": f"exec_{i}",
                "connector_name": "telegram" if i < 3 else "sendgrid",
                "action_name": "send_message",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mode": "dry_run",
                "success": True,
            })

        telegram_actions = temp_state_store.get_connector_executions(
            connector_name="telegram"
        )
        assert len(telegram_actions) == 3

        sendgrid_actions = temp_state_store.get_connector_executions(
            connector_name="sendgrid"
        )
        assert len(sendgrid_actions) == 2

    def test_query_connector_executions_by_mode(self, temp_state_store):
        """Test querying by execution mode."""
        temp_state_store.save_connector_execution({
            "execution_id": "exec_live",
            "connector_name": "telegram",
            "action_name": "send_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "live",
            "success": True,
        })
        temp_state_store.save_connector_execution({
            "execution_id": "exec_dry",
            "connector_name": "telegram",
            "action_name": "send_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "dry_run",
            "success": True,
        })

        live_actions = temp_state_store.get_connector_executions(mode="live")
        assert len(live_actions) == 1
        assert live_actions[0]["execution_id"] == "exec_live"

        dry_actions = temp_state_store.get_connector_executions(mode="dry_run")
        assert len(dry_actions) == 1
        assert dry_actions[0]["execution_id"] == "exec_dry"

    def test_query_connector_executions_by_related_entities(self, temp_state_store):
        """Test querying by job/plan/opportunity IDs."""
        temp_state_store.save_connector_execution({
            "execution_id": "exec_job",
            "connector_name": "telegram",
            "action_name": "send_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "live",
            "success": True,
            "job_id": "job_123",
        })
        temp_state_store.save_connector_execution({
            "execution_id": "exec_plan",
            "connector_name": "telegram",
            "action_name": "send_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "live",
            "success": True,
            "plan_id": "plan_456",
        })

        job_actions = temp_state_store.get_connector_executions(job_id="job_123")
        assert len(job_actions) == 1
        assert job_actions[0]["execution_id"] == "exec_job"

        plan_actions = temp_state_store.get_connector_executions(plan_id="plan_456")
        assert len(plan_actions) == 1
        assert plan_actions[0]["execution_id"] == "exec_plan"


class TestConnectorActionHistory:
    """Test connector action history module."""

    def test_get_recent_actions(self, connector_history, temp_state_store):
        """Test retrieving recent actions."""
        for i in range(10):
            temp_state_store.save_connector_execution({
                "execution_id": f"exec_{i}",
                "connector_name": "telegram",
                "action_name": "send_message",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mode": "dry_run",
                "success": True,
            })

        recent = connector_history.get_recent_actions(limit=5)
        assert len(recent) == 5

    def test_get_action_by_id(self, connector_history, temp_state_store):
        """Test retrieving action by ID."""
        temp_state_store.save_connector_execution({
            "execution_id": "exec_specific",
            "connector_name": "telegram",
            "action_name": "send_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "live",
            "success": True,
        })

        action = connector_history.get_action_by_id("exec_specific")
        assert action is not None
        assert action["execution_id"] == "exec_specific"

    def test_query_actions_with_filter(self, connector_history, temp_state_store):
        """Test querying actions with filter criteria."""
        temp_state_store.save_connector_execution({
            "execution_id": "exec_filtered",
            "connector_name": "telegram",
            "action_name": "send_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "live",
            "success": True,
            "job_id": "job_123",
        })
        temp_state_store.save_connector_execution({
            "execution_id": "exec_other",
            "connector_name": "sendgrid",
            "action_name": "send_email",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "dry_run",
            "success": False,
        })

        filter_criteria = ConnectorActionFilter(
            connector="telegram",
            mode="live",
            success=True,
        )
        actions = connector_history.query_actions(filter_criteria)
        assert len(actions) == 1
        assert actions[0]["execution_id"] == "exec_filtered"

    def test_get_connector_stats(self, connector_history, temp_state_store):
        """Test getting connector statistics."""
        # Create mix of successful and failed actions
        # i % 3 != 0 means: 0 fails, 1 success, 2 success, 3 fails, 4 success, 5 success, 6 fails, 7 success, 8 success, 9 fails
        # So: 0,3,6,9 fail (4 failures), 1,2,4,5,7,8 success (6 successes)
        for i in range(10):
            temp_state_store.save_connector_execution({
                "execution_id": f"exec_{i}",
                "connector_name": "telegram",
                "action_name": "send_message",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mode": "live" if i < 3 else "dry_run",
                "success": i % 3 != 0,
            })

        stats = connector_history.get_connector_stats(connector="telegram")
        assert stats["total_executions"] == 10
        assert stats["successful"] == 6
        assert stats["failed"] == 4
        assert 55.0 < stats["success_rate"] < 65.0
        assert stats["live_executions"] == 3
        assert stats["dry_run_executions"] == 7


class TestSafeRendering:
    """Test safe rendering and redaction."""

    def test_redact_sensitive_fields(self):
        """Test redaction of sensitive fields."""
        data = {
            "text": "Hello world",
            "api_key": "secret_key_123",
            "token": "bearer_token_456",
            "chat_id": "123456",
        }

        redacted = redact_sensitive_fields(data)
        assert redacted["text"] == "Hello world"
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["token"] == "***REDACTED***"
        assert redacted["chat_id"] == "123456"

    def test_redact_nested_fields(self):
        """Test redaction of nested dictionaries."""
        data = {
            "params": {
                "text": "Hello",
                "credentials": {
                    "api_key": "secret",
                    "user": "test",
                }
            }
        }

        redacted = redact_sensitive_fields(data)
        assert redacted["params"]["text"] == "Hello"
        # "credentials" key contains "credential" so whole dict redacted
        assert redacted["params"]["credentials"] == "***REDACTED***"

    def test_safe_connector_request_summary(self):
        """Test safe request summary generation."""
        params = {
            "text": "Hello world",
            "chat_id": "123456",
            "api_key": "secret",
        }

        summary = safe_connector_request_summary(params)
        assert "Hello world" in summary
        assert "123456" in summary
        assert "***REDACTED***" in summary
        assert "secret" not in summary

    def test_safe_connector_response_summary_success(self):
        """Test safe response summary for success."""
        response = {
            "ok": True,
            "result": {
                "message_id": 12345,
                "text": "Hello",
            }
        }

        summary = safe_connector_response_summary(response, success=True)
        assert "\u2713 Success" in summary
        assert "ok=True" in summary

    def test_safe_connector_response_summary_failure(self):
        """Test safe response summary for failure."""
        response = {
            "error": "API error",
            "description": "Invalid token",
        }

        summary = safe_connector_response_summary(response, success=False)
        assert "\u2717 Failed" in summary

    def test_safe_connector_error_summary(self):
        """Test safe error summary generation."""
        error = "Connection failed: invalid api_key=secret_123"

        summary = safe_connector_error_summary(error)
        assert "contains sensitive information" in summary
        assert "secret_123" not in summary

    def test_safe_connector_error_summary_safe(self):
        """Test error summary with no secrets."""
        error = "Connection timeout after 30 seconds"

        summary = safe_connector_error_summary(error)
        assert "Connection timeout" in summary


class TestIntegration:
    """Integration tests for connector action persistence."""

    def test_full_persistence_workflow(self, connector_history, temp_state_store):
        """Test full workflow: save -> query -> retrieve -> stats."""
        # Save action
        execution = {
            "execution_id": "exec_integration",
            "connector_name": "telegram",
            "action_name": "send_message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "live",
            "success": True,
            "duration_seconds": 1.2,
            "cost_class": "MINIMAL",
            "approval_state": "approved",
            "job_id": "job_001",
            "request_summary": "text=Hello, chat_id=123",
            "response_summary": "\u2713 Success, message_id=12345",
        }
        temp_state_store.save_connector_execution(execution)

        # Query
        actions = connector_history.get_actions_by_connector("telegram")
        assert len(actions) >= 1

        # Retrieve
        action = connector_history.get_action_by_id("exec_integration")
        assert action is not None
        assert action["success"] == 1

        # Stats
        stats = connector_history.get_connector_stats(connector="telegram")
        assert stats["total_executions"] >= 1
        assert stats["live_executions"] >= 1
