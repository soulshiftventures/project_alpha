"""
Tests for Live Connector Action Instrumentation.

Verifies that connector actions are automatically persisted during execution flows.
"""

import pytest
from datetime import datetime, timezone

from core.connector_action_history import ConnectorActionHistory
from core.approval_workflow import (
    ApprovalWorkflow,
    WorkflowItemType,
    WorkflowItemStatus,
)
from core.integration_skill import IntegrationSkill, IntegrationRequest
from core.state_store import get_state_store


@pytest.fixture
def state_store():
    """Create an initialized state store."""
    store = get_state_store()
    if not store.is_initialized:
        store.initialize()
    return store


@pytest.fixture
def connector_action_history(state_store):
    """Create connector action history."""
    return ConnectorActionHistory(state_store)


@pytest.fixture
def approval_workflow(state_store, connector_action_history):
    """Create approval workflow with connector action history."""
    return ApprovalWorkflow(connector_action_history=connector_action_history)


def test_connector_action_lifecycle_methods(connector_action_history):
    """Test lifecycle update methods exist and work."""
    # Record action requested
    exec_id = connector_action_history.record_action_requested(
        connector_name="test_connector",
        action_name="send_message",
        mode="dry_run",
        approval_state="pending",
        request_summary="Test message",
        job_id="job_123",
        plan_id="plan_456",
    )

    assert exec_id is not None

    # Update approval
    result = connector_action_history.update_action_approval(
        execution_id=exec_id,
        approval_state="approved",
        approval_id="approval_789",
    )
    assert result is True

    # Record executing
    result = connector_action_history.record_action_executing(
        execution_id=exec_id,
        mode="live",
    )
    assert result is True

    # Record completed
    result = connector_action_history.record_action_completed(
        execution_id=exec_id,
        success=True,
        response_summary="Message sent successfully",
        duration_seconds=1.5,
    )
    assert result is True

    # Verify final state via state store
    from core.state_store import get_state_store
    store = get_state_store()
    if not store.is_initialized:
        store.initialize()

    action = store.get_connector_execution_by_id(exec_id)
    assert action is not None
    assert action["connector_name"] == "test_connector"
    assert action["action_name"] == "send_message"
    assert action["approval_state"] == "approved"
    assert action["execution_status"] == "completed"
    assert action["mode"] == "live"
    assert action["success"] == 1


def test_approval_workflow_persists_connector_action(approval_workflow, connector_action_history):
    """Test that approval workflow creates connector action records."""
    # Create connector action workflow item
    item = approval_workflow.create_workflow_item(
        item_type=WorkflowItemType.CONNECTOR_ACTION,
        title="Send Telegram Message",
        description="Send notification via Telegram",
        connector_name="telegram",
        operation="send_message",
        target_mode="live",
        requires_live_mode=True,
    )

    # Verify workflow item created
    assert item.item_id is not None
    assert item.connector_name == "telegram"
    assert item.operation == "send_message"

    # Verify connector action record created
    exec_id = approval_workflow.get_execution_id(item.item_id)
    assert exec_id is not None

    from core.state_store import get_state_store
    store = get_state_store()
    action = store.get_connector_execution_by_id(exec_id)
    assert action is not None
    assert action["connector_name"] == "telegram"
    assert action["action_name"] == "send_message"
    assert action["approval_state"] == "pending"
    assert action["execution_status"] == "requested"


def test_approval_workflow_updates_on_approval(approval_workflow, connector_action_history):
    """Test that approving a workflow item updates connector action record."""
    # Create connector action workflow item
    item = approval_workflow.create_workflow_item(
        item_type=WorkflowItemType.CONNECTOR_ACTION,
        title="Send Telegram Message",
        description="Send notification via Telegram",
        connector_name="telegram",
        operation="send_message",
    )

    exec_id = approval_workflow.get_execution_id(item.item_id)
    assert exec_id is not None

    # Approve the item
    decision = approval_workflow.approve_item(
        item_id=item.item_id,
        approver="principal",
        rationale="Approved for testing",
    )

    assert decision.success is True
    assert decision.action == "approved"

    # Verify connector action updated
    from core.state_store import get_state_store
    store = get_state_store()
    action = store.get_connector_execution_by_id(exec_id)
    assert action["approval_state"] == "approved"


def test_approval_workflow_updates_on_denial(approval_workflow, connector_action_history):
    """Test that denying a workflow item updates connector action record."""
    # Create connector action workflow item
    item = approval_workflow.create_workflow_item(
        item_type=WorkflowItemType.CONNECTOR_ACTION,
        title="Send Telegram Message",
        description="Send notification via Telegram",
        connector_name="telegram",
        operation="send_message",
    )

    exec_id = approval_workflow.get_execution_id(item.item_id)
    assert exec_id is not None

    # Deny the item
    decision = approval_workflow.deny_item(
        item_id=item.item_id,
        denier="principal",
        rationale="Not authorized",
    )

    assert decision.success is True
    assert decision.action == "denied"

    # Verify connector action updated
    from core.state_store import get_state_store
    store = get_state_store()
    action = store.get_connector_execution_by_id(exec_id)
    assert action["approval_state"] == "denied"
    assert action["execution_status"] == "blocked"
    assert "Not authorized" in (action.get("error_summary") or "")


def test_approval_workflow_updates_on_execution(approval_workflow, connector_action_history):
    """Test that marking item as executed updates connector action record."""
    # Create connector action workflow item
    item = approval_workflow.create_workflow_item(
        item_type=WorkflowItemType.CONNECTOR_ACTION,
        title="Send Telegram Message",
        description="Send notification via Telegram",
        connector_name="telegram",
        operation="send_message",
    )

    exec_id = approval_workflow.get_execution_id(item.item_id)
    assert exec_id is not None

    # Approve first
    approval_workflow.approve_item(item.item_id, "principal")

    # Mark as executed
    approval_workflow.mark_executed(
        item_id=item.item_id,
        result={"message_id": "12345"},
        success=True,
    )

    # Verify connector action updated
    from core.state_store import get_state_store
    store = get_state_store()
    action = store.get_connector_execution_by_id(exec_id)
    assert action["execution_status"] == "completed"
    assert action["success"] == 1


def test_blocked_action_persistence():
    """Test that blocked actions are persisted with correct state."""
    history = ConnectorActionHistory()

    # Record blocked action
    exec_id = history.record_action_requested(
        connector_name="restricted_api",
        action_name="delete_all",
        mode="dry_run",
        approval_state="blocked",
        request_summary="Blocked by policy",
    )

    assert exec_id is not None

    # Update as blocked
    history.update_action_status(
        execution_id=exec_id,
        execution_status="blocked",
        error_summary="Operation not permitted by policy",
    )

    # Verify
    from core.state_store import get_state_store
    store = get_state_store()
    action = store.get_connector_execution_by_id(exec_id)
    assert action["approval_state"] == "blocked"
    assert action["execution_status"] == "blocked"


def test_dry_run_execution_persistence():
    """Test that dry-run executions are persisted."""
    history = ConnectorActionHistory()

    # Record dry-run action
    exec_id = history.record_action_requested(
        connector_name="telegram",
        action_name="send_message",
        mode="dry_run",
        approval_state="auto_allowed",
        request_summary="Dry-run test",
    )

    assert exec_id is not None

    # Execute in dry-run
    history.record_action_executing(exec_id, mode="dry_run")
    history.record_action_completed(
        execution_id=exec_id,
        success=True,
        response_summary="Would send message (dry-run)",
    )

    # Verify
    from core.state_store import get_state_store
    store = get_state_store()
    action = store.get_connector_execution_by_id(exec_id)
    assert action["mode"] == "dry_run"
    assert action["execution_status"] == "completed"
    assert action["success"] == 1


def test_failed_execution_persistence():
    """Test that failed executions are persisted with error details."""
    history = ConnectorActionHistory()

    exec_id = history.record_action_requested(
        connector_name="telegram",
        action_name="send_message",
        mode="live",
        approval_state="approved",
    )

    history.record_action_executing(exec_id, mode="live")
    history.record_action_completed(
        execution_id=exec_id,
        success=False,
        error_summary="Invalid token",
    )

    # Verify
    from core.state_store import get_state_store
    store = get_state_store()
    action = store.get_connector_execution_by_id(exec_id)
    assert action["execution_status"] == "failed"
    assert action["success"] == 0
    assert action["error_summary"] == "Invalid token"


def test_link_to_job_and_plan():
    """Test that connector actions can be linked to jobs and plans."""
    history = ConnectorActionHistory()

    exec_id = history.record_action_requested(
        connector_name="telegram",
        action_name="send_message",
        job_id="job_abc123",
        plan_id="plan_def456",
        opportunity_id="opp_ghi789",
    )

    # Verify links
    from core.state_store import get_state_store
    store = get_state_store()
    action = store.get_connector_execution_by_id(exec_id)
    assert action["job_id"] == "job_abc123"
    assert action["plan_id"] == "plan_def456"
    assert action["opportunity_id"] == "opp_ghi789"


def test_query_by_connector():
    """Test querying actions by connector."""
    history = ConnectorActionHistory()

    # Create multiple actions
    history.record_action_requested("telegram", "send_message")
    history.record_action_requested("telegram", "get_updates")
    history.record_action_requested("slack", "post_message")

    # Query telegram actions
    telegram_actions = history.get_actions_by_connector("telegram", limit=10)
    assert len(telegram_actions) >= 2
    assert all(a["connector_name"] == "telegram" for a in telegram_actions)


def test_query_by_plan():
    """Test querying actions by plan ID."""
    history = ConnectorActionHistory()

    plan_id = "plan_test_123"

    # Create actions for plan
    history.record_action_requested(
        "telegram", "send_message", plan_id=plan_id
    )
    history.record_action_requested(
        "slack", "post_message", plan_id=plan_id
    )

    # Query by plan
    actions = history.get_actions_by_plan(plan_id)
    assert len(actions) >= 2
    assert all(a["plan_id"] == plan_id for a in actions)


def test_non_connector_workflow_items_dont_create_actions(approval_workflow, connector_action_history):
    """Test that non-connector workflow items don't create connector action records."""
    # Create a non-connector workflow item
    item = approval_workflow.create_workflow_item(
        item_type=WorkflowItemType.EXECUTION_PLAN,
        title="Execute Plan",
        description="Execute an execution plan",
    )

    # Verify no connector action created
    exec_id = approval_workflow.get_execution_id(item.item_id)
    assert exec_id is None
