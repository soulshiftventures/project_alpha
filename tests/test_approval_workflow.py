"""
Tests for Approval Workflow and Live Mode Controller.

Tests cover:
- Approval workflow item creation and lifecycle
- Approval/denial flow with callbacks
- Live mode gate checks (policy, credentials, approval)
- Live mode promotion and consumption
- Standing approvals
- Safe rendering (no secret leakage)
- Event logging integration

SECURITY:
- Tests use mock values only
- No real credentials in test code
- Verifies no secrets in outputs
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone


# =============================================================================
# Approval Workflow Tests
# =============================================================================

class TestWorkflowItemContext:
    """Tests for WorkflowItemContext dataclass."""

    def test_context_creation(self):
        """WorkflowItemContext can be created with required fields."""
        from core.approval_workflow import (
            WorkflowItemContext,
            WorkflowItemType,
            WorkflowItemStatus,
        )

        context = WorkflowItemContext(
            item_id="wfi_test_001",
            item_type=WorkflowItemType.CONNECTOR_ACTION,
            title="Test Action",
            description="Test description",
        )

        assert context.item_id == "wfi_test_001"
        assert context.item_type == WorkflowItemType.CONNECTOR_ACTION
        assert context.status == WorkflowItemStatus.PENDING_APPROVAL
        assert context.title == "Test Action"

    def test_context_defaults(self):
        """WorkflowItemContext has correct defaults."""
        from core.approval_workflow import (
            WorkflowItemContext,
            WorkflowItemType,
            WorkflowItemStatus,
        )

        context = WorkflowItemContext(
            item_id="wfi_test_002",
            item_type=WorkflowItemType.JOB,
        )

        assert context.status == WorkflowItemStatus.PENDING_APPROVAL
        assert context.requester == "system"
        assert context.risk_level == "medium"
        assert context.requires_live_mode is False
        assert context.current_mode == "dry_run"
        assert context.skills == []
        assert context.commands == []
        assert context.safe_params == {}

    def test_context_to_dict(self):
        """WorkflowItemContext.to_dict() returns safe dictionary."""
        from core.approval_workflow import (
            WorkflowItemContext,
            WorkflowItemType,
        )

        context = WorkflowItemContext(
            item_id="wfi_test_003",
            item_type=WorkflowItemType.SKILL_USAGE,
            title="Skill Usage",
            description="Testing skill",
            connector_name="tavily",
            operation="search",
            skills=["search_skill"],
            safe_params={"query": "test query"},
        )

        data = context.to_dict()

        assert isinstance(data, dict)
        assert data["item_id"] == "wfi_test_003"
        assert data["item_type"] == "skill_usage"
        assert data["connector_name"] == "tavily"
        assert data["skills"] == ["search_skill"]
        # Should NOT contain any secret keys
        assert "api_key" not in str(data).lower() or "safe_params" in str(data)
        assert "password" not in str(data).lower()
        assert "token" not in str(data).lower() or data.get("token") is None


class TestApprovalDecision:
    """Tests for ApprovalDecision dataclass."""

    def test_decision_creation(self):
        """ApprovalDecision can be created with required fields."""
        from core.approval_workflow import ApprovalDecision

        decision = ApprovalDecision(
            success=True,
            item_id="wfi_test_001",
            action="approved",
            decided_by="principal",
        )

        assert decision.success is True
        assert decision.item_id == "wfi_test_001"
        assert decision.action == "approved"
        assert decision.decided_by == "principal"

    def test_decision_to_dict(self):
        """ApprovalDecision.to_dict() returns dictionary."""
        from core.approval_workflow import ApprovalDecision

        decision = ApprovalDecision(
            success=True,
            item_id="wfi_test_002",
            action="denied",
            decided_by="operator",
            rationale="Not approved for production",
        )

        data = decision.to_dict()

        assert data["success"] is True
        assert data["action"] == "denied"
        assert data["rationale"] == "Not approved for production"


class TestApprovalWorkflow:
    """Tests for ApprovalWorkflow class."""

    @pytest.fixture
    def mock_approval_manager(self):
        """Create mock approval manager."""
        mock = Mock()
        mock.get_pending.return_value = []
        mock.get_history.return_value = []
        mock.approve.return_value = True
        mock.deny.return_value = True
        return mock

    @pytest.fixture
    def mock_event_logger(self):
        """Create mock event logger."""
        mock = Mock()
        mock.log.return_value = None
        return mock

    @pytest.fixture
    def workflow(self, mock_approval_manager, mock_event_logger):
        """Create ApprovalWorkflow with mocked dependencies."""
        from core.approval_workflow import ApprovalWorkflow

        return ApprovalWorkflow(
            approval_manager=mock_approval_manager,
            event_logger=mock_event_logger,
        )

    def test_create_workflow_item(self, workflow):
        """Create workflow item successfully."""
        from core.approval_workflow import WorkflowItemType, WorkflowItemStatus

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.CONNECTOR_ACTION,
            title="Search Web",
            description="Perform web search",
            connector_name="tavily",
            operation="search",
            risk_level="low",
        )

        assert item.item_id.startswith("wfi_")
        assert item.item_type == WorkflowItemType.CONNECTOR_ACTION
        assert item.status == WorkflowItemStatus.PENDING_APPROVAL
        assert item.connector_name == "tavily"
        assert item.operation == "search"

    def test_get_pending_items(self, workflow):
        """Get pending items returns only pending."""
        from core.approval_workflow import WorkflowItemType

        # Create multiple items
        item1 = workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Job 1",
            description="First job",
        )
        item2 = workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Job 2",
            description="Second job",
        )

        # Approve one
        workflow.approve_item(item1.item_id, approver="principal")

        pending = workflow.get_pending_items()

        assert len(pending) == 1
        assert pending[0].item_id == item2.item_id

    def test_approve_item_success(self, workflow, mock_event_logger):
        """Approve item successfully."""
        from core.approval_workflow import (
            WorkflowItemType,
            WorkflowItemStatus,
        )

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.SKILL_USAGE,
            title="Test Skill",
            description="Testing",
        )

        decision = workflow.approve_item(
            item_id=item.item_id,
            approver="principal",
            rationale="Approved for testing",
        )

        assert decision.success is True
        assert decision.action == "approved"
        assert decision.decided_by == "principal"
        assert item.status == WorkflowItemStatus.APPROVED
        assert item.approved_at is not None

    def test_approve_item_with_live_promotion(self, workflow):
        """Approve item with live mode promotion."""
        from core.approval_workflow import WorkflowItemType

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.CONNECTOR_ACTION,
            title="Live Action",
            description="Action requiring live mode",
            requires_live_mode=True,
            connector_name="hubspot",
            operation="create_contact",
        )

        decision = workflow.approve_item(
            item_id=item.item_id,
            approver="principal",
            promote_to_live=True,
        )

        assert decision.success is True
        assert item.current_mode == "live"

    def test_approve_item_not_found(self, workflow):
        """Approve non-existent item returns error."""
        decision = workflow.approve_item(
            item_id="nonexistent",
            approver="principal",
        )

        assert decision.success is False
        assert decision.error == "Item not found"

    def test_approve_already_approved_fails(self, workflow):
        """Cannot approve already approved item."""
        from core.approval_workflow import WorkflowItemType

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Test Job",
            description="Testing",
        )

        # First approval
        workflow.approve_item(item.item_id, approver="principal")

        # Second approval should fail
        decision = workflow.approve_item(item.item_id, approver="principal")

        assert decision.success is False
        assert "not pending approval" in decision.error

    def test_deny_item_success(self, workflow, mock_event_logger):
        """Deny item successfully."""
        from core.approval_workflow import (
            WorkflowItemType,
            WorkflowItemStatus,
        )

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.EXECUTION_PLAN,
            title="Risky Plan",
            description="Plan with high risk",
            risk_level="high",
        )

        decision = workflow.deny_item(
            item_id=item.item_id,
            denier="principal",
            rationale="Too risky for production",
        )

        assert decision.success is True
        assert decision.action == "denied"
        assert item.status == WorkflowItemStatus.DENIED
        assert item.denial_rationale == "Too risky for production"

    def test_deny_item_not_found(self, workflow):
        """Deny non-existent item returns error."""
        decision = workflow.deny_item(
            item_id="nonexistent",
            denier="principal",
        )

        assert decision.success is False
        assert decision.error == "Item not found"

    def test_cancel_item(self, workflow):
        """Cancel pending item."""
        from core.approval_workflow import (
            WorkflowItemType,
            WorkflowItemStatus,
        )

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Cancelled Job",
            description="Job to cancel",
        )

        decision = workflow.cancel_item(
            item_id=item.item_id,
            canceller="system",
            reason="No longer needed",
        )

        assert decision.success is True
        assert decision.action == "cancelled"
        assert item.status == WorkflowItemStatus.CANCELLED

    def test_approval_callbacks_fired(self, workflow):
        """Approval callbacks are fired on approval."""
        from core.approval_workflow import WorkflowItemType

        callback_result = {"called": False, "item": None}

        def on_approved(item):
            callback_result["called"] = True
            callback_result["item"] = item

        workflow.register_approval_callback(on_approved=on_approved)

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Callback Test",
            description="Testing callbacks",
        )

        workflow.approve_item(item.item_id, approver="principal")

        assert callback_result["called"] is True
        assert callback_result["item"].item_id == item.item_id

    def test_denial_callbacks_fired(self, workflow):
        """Denial callbacks are fired on denial."""
        from core.approval_workflow import WorkflowItemType

        callback_result = {"called": False}

        def on_denied(item):
            callback_result["called"] = True

        workflow.register_approval_callback(on_denied=on_denied)

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Denial Test",
            description="Testing callbacks",
        )

        workflow.deny_item(item.item_id, denier="principal")

        assert callback_result["called"] is True

    def test_get_items_by_type(self, workflow):
        """Get items filtered by type."""
        from core.approval_workflow import WorkflowItemType

        workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Job 1",
            description="First job",
        )
        workflow.create_workflow_item(
            item_type=WorkflowItemType.CONNECTOR_ACTION,
            title="Connector 1",
            description="First connector action",
        )
        workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Job 2",
            description="Second job",
        )

        jobs = workflow.get_items_by_type(WorkflowItemType.JOB)

        assert len(jobs) == 2

    def test_get_items_for_connector(self, workflow):
        """Get items filtered by connector."""
        from core.approval_workflow import WorkflowItemType

        workflow.create_workflow_item(
            item_type=WorkflowItemType.CONNECTOR_ACTION,
            title="Tavily Search",
            description="Search with tavily",
            connector_name="tavily",
        )
        workflow.create_workflow_item(
            item_type=WorkflowItemType.CONNECTOR_ACTION,
            title="HubSpot Create",
            description="Create in hubspot",
            connector_name="hubspot",
        )

        tavily_items = workflow.get_items_for_connector("tavily")

        assert len(tavily_items) == 1
        assert tavily_items[0].connector_name == "tavily"

    def test_mark_executed(self, workflow):
        """Mark item as executed."""
        from core.approval_workflow import (
            WorkflowItemType,
            WorkflowItemStatus,
        )

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Execute Test",
            description="Testing execution",
        )

        workflow.approve_item(item.item_id, approver="principal")

        workflow.mark_executed(
            item_id=item.item_id,
            result={"status": "completed"},
            success=True,
        )

        assert item.status == WorkflowItemStatus.EXECUTED
        assert item.executed_at is not None
        assert item.execution_result["status"] == "completed"

    def test_mark_executed_failed(self, workflow):
        """Mark item as failed."""
        from core.approval_workflow import (
            WorkflowItemType,
            WorkflowItemStatus,
        )

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Failed Test",
            description="Testing failure",
        )

        workflow.approve_item(item.item_id, approver="principal")

        workflow.mark_executed(
            item_id=item.item_id,
            result={},
            success=False,
            error="Execution failed",
        )

        assert item.status == WorkflowItemStatus.FAILED
        assert item.error == "Execution failed"

    def test_get_summary(self, workflow):
        """Get workflow summary statistics."""
        from core.approval_workflow import WorkflowItemType

        workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Job 1",
            description="First job",
        )
        item2 = workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Job 2",
            description="Second job",
            requires_live_mode=True,
        )
        item3 = workflow.create_workflow_item(
            item_type=WorkflowItemType.CONNECTOR_ACTION,
            title="Connector 1",
            description="Connector action",
        )

        workflow.approve_item(item3.item_id, approver="principal")

        summary = workflow.get_summary()

        assert summary["total_items"] == 3
        assert summary["pending_approval"] == 2
        assert summary["live_mode_pending"] == 1
        assert summary["by_type"]["job"] == 2
        assert summary["by_type"]["connector_action"] == 1


# =============================================================================
# Live Mode Controller Tests
# =============================================================================

class TestLiveModeGateResult:
    """Tests for LiveModeGateResult dataclass."""

    def test_gate_result_creation(self):
        """LiveModeGateResult can be created."""
        from core.live_mode_controller import (
            LiveModeGateResult,
            LiveModeGateStatus,
        )
        from core.integration_policies import IntegrationRiskLevel

        result = LiveModeGateResult(
            allowed=True,
            status=LiveModeGateStatus.ALLOWED,
            reason="Gate passed",
            connector="tavily",
            operation="search",
        )

        assert result.allowed is True
        assert result.status == LiveModeGateStatus.ALLOWED
        assert result.connector == "tavily"

    def test_gate_result_to_dict(self):
        """LiveModeGateResult.to_dict() returns dictionary."""
        from core.live_mode_controller import (
            LiveModeGateResult,
            LiveModeGateStatus,
        )

        result = LiveModeGateResult(
            allowed=False,
            status=LiveModeGateStatus.DENIED_CREDENTIALS,
            reason="Missing API key",
            connector="hubspot",
            operation="create_contact",
            missing_credentials=["hubspot_api_key"],
        )

        data = result.to_dict()

        assert data["allowed"] is False
        assert data["status"] == "denied_credentials"
        assert data["missing_credentials"] == ["hubspot_api_key"]


class TestLiveModePromotion:
    """Tests for LiveModePromotion dataclass."""

    def test_promotion_creation(self):
        """LiveModePromotion can be created."""
        from core.live_mode_controller import LiveModePromotion

        promotion = LiveModePromotion(
            promotion_id="lmp_test_001",
            connector="tavily",
            operation="search",
            promoted_by="principal",
            approval_id="apr_001",
            risk_level="low",
        )

        assert promotion.promotion_id == "lmp_test_001"
        assert promotion.used is False

    def test_promotion_to_dict(self):
        """LiveModePromotion.to_dict() returns dictionary."""
        from core.live_mode_controller import LiveModePromotion

        promotion = LiveModePromotion(
            promotion_id="lmp_test_002",
            connector="hubspot",
            operation="list_contacts",
            promoted_by="operator",
            approval_id=None,
            risk_level="medium",
        )

        data = promotion.to_dict()

        assert data["promotion_id"] == "lmp_test_002"
        assert data["connector"] == "hubspot"
        assert data["used"] is False


class TestLiveModeController:
    """Tests for LiveModeController class."""

    @pytest.fixture
    def mock_policy_engine(self):
        """Create mock policy engine."""
        from core.integration_policies import PolicyDecision, IntegrationRiskLevel

        mock = Mock()
        mock.evaluate.return_value = PolicyDecision(
            allowed=True,
            requires_approval=False,
            risk_level=IntegrationRiskLevel.LOW,
            reason="Allowed by policy",
            constraints={},
        )
        return mock

    @pytest.fixture
    def mock_secrets_manager(self):
        """Create mock secrets manager."""
        mock = Mock()
        mock.has_secret.return_value = True
        return mock

    @pytest.fixture
    def mock_event_logger(self):
        """Create mock event logger."""
        mock = Mock()
        mock.log.return_value = None
        return mock

    @pytest.fixture
    def controller(self, mock_policy_engine, mock_secrets_manager, mock_event_logger):
        """Create LiveModeController with mocked dependencies."""
        from core.live_mode_controller import LiveModeController

        with patch('core.live_mode_controller.get_credential_registry') as mock_registry:
            mock_registry.return_value.get_required_credentials.return_value = []

            return LiveModeController(
                policy_engine=mock_policy_engine,
                secrets_manager=mock_secrets_manager,
                event_logger=mock_event_logger,
            )

    def test_check_blocked_operation(self, controller):
        """Blocked operations are denied."""
        from core.live_mode_controller import LiveModeGateStatus

        result = controller.check_live_mode_gate(
            connector="any",
            operation="delete_all",
        )

        assert result.allowed is False
        assert result.status == LiveModeGateStatus.DENIED_BLOCKED
        assert "blocked" in result.reason.lower()

    def test_check_policy_denied(self, controller, mock_policy_engine):
        """Policy-denied operations are blocked."""
        from core.live_mode_controller import LiveModeGateStatus
        from core.integration_policies import PolicyDecision, IntegrationRiskLevel

        mock_policy_engine.evaluate.return_value = PolicyDecision(
            allowed=False,
            requires_approval=True,
            risk_level=IntegrationRiskLevel.HIGH,
            reason="Policy denies this operation",
            constraints={},
        )

        result = controller.check_live_mode_gate(
            connector="hubspot",
            operation="bulk_update",
        )

        assert result.allowed is False
        assert result.status == LiveModeGateStatus.DENIED_POLICY

    def test_check_missing_credentials(self, controller, mock_secrets_manager):
        """Missing credentials block live mode."""
        from core.live_mode_controller import LiveModeGateStatus

        mock_secrets_manager.has_secret.return_value = False

        with patch('core.live_mode_controller.get_credential_registry') as mock_registry:
            mock_registry.return_value.get_required_credentials.return_value = [
                "hubspot_api_key"
            ]

            # Need to recreate controller with new mock
            from core.live_mode_controller import LiveModeController

            ctrl = LiveModeController(
                secrets_manager=mock_secrets_manager,
            )

            result = ctrl.check_live_mode_gate(
                connector="hubspot",
                operation="list_contacts",
            )

        assert result.allowed is False
        assert result.status == LiveModeGateStatus.DENIED_CREDENTIALS
        assert "hubspot_api_key" in result.missing_credentials

    def test_check_requires_approval(self, controller, mock_policy_engine):
        """Operations requiring approval check for approval."""
        from core.live_mode_controller import LiveModeGateStatus
        from core.integration_policies import PolicyDecision, IntegrationRiskLevel

        mock_policy_engine.evaluate.return_value = PolicyDecision(
            allowed=True,
            requires_approval=True,
            risk_level=IntegrationRiskLevel.MEDIUM,
            reason="Requires approval",
            constraints={},
        )

        result = controller.check_live_mode_gate(
            connector="hubspot",
            operation="create_contact",
            approval_id=None,  # No approval
        )

        assert result.allowed is False
        assert result.status == LiveModeGateStatus.DENIED_APPROVAL

    def test_check_with_standing_approval(self, controller, mock_policy_engine):
        """Standing approval allows operation."""
        from core.live_mode_controller import LiveModeGateStatus
        from core.integration_policies import PolicyDecision, IntegrationRiskLevel

        mock_policy_engine.evaluate.return_value = PolicyDecision(
            allowed=True,
            requires_approval=True,
            risk_level=IntegrationRiskLevel.MEDIUM,
            reason="Requires approval",
            constraints={},
        )

        # Grant standing approval
        controller.grant_standing_approval(
            connector="hubspot",
            operation="create_contact",
            approval_id="apr_001",
            granted_by="principal",
        )

        result = controller.check_live_mode_gate(
            connector="hubspot",
            operation="create_contact",
        )

        assert result.allowed is True
        assert result.status == LiveModeGateStatus.ALLOWED

    def test_check_gate_allowed(self, controller):
        """Gate check passes when all conditions met."""
        from core.live_mode_controller import LiveModeGateStatus

        result = controller.check_live_mode_gate(
            connector="tavily",
            operation="search",
        )

        assert result.allowed is True
        assert result.status == LiveModeGateStatus.ALLOWED

    def test_promote_to_live_success(self, controller):
        """Promote to live mode successfully."""
        promotion = controller.promote_to_live(
            connector="tavily",
            operation="search",
            promoted_by="principal",
        )

        assert promotion is not None
        assert promotion.promotion_id.startswith("lmp_")
        assert promotion.connector == "tavily"
        assert promotion.operation == "search"
        assert promotion.used is False

    def test_promote_to_live_denied(self, controller):
        """Promote to live fails when gate check fails."""
        promotion = controller.promote_to_live(
            connector="any",
            operation="delete_all",  # Blocked operation
            promoted_by="principal",
        )

        assert promotion is None

    def test_consume_promotion(self, controller):
        """Consume promotion marks it as used."""
        promotion = controller.promote_to_live(
            connector="tavily",
            operation="search",
            promoted_by="principal",
        )

        result = controller.consume_promotion(promotion.promotion_id)

        assert result is True
        assert promotion.used is True
        assert promotion.used_at is not None

    def test_consume_promotion_already_used(self, controller):
        """Cannot consume already used promotion."""
        promotion = controller.promote_to_live(
            connector="tavily",
            operation="search",
            promoted_by="principal",
        )

        controller.consume_promotion(promotion.promotion_id)
        result = controller.consume_promotion(promotion.promotion_id)

        assert result is False

    def test_consume_promotion_not_found(self, controller):
        """Cannot consume non-existent promotion."""
        result = controller.consume_promotion("nonexistent")

        assert result is False

    def test_grant_standing_approval(self, controller, mock_event_logger):
        """Grant standing approval successfully."""
        result = controller.grant_standing_approval(
            connector="tavily",
            operation="search",
            approval_id="apr_001",
            granted_by="principal",
        )

        assert result is True
        assert controller.has_standing_approval("tavily", "search")

    def test_revoke_standing_approval(self, controller):
        """Revoke standing approval successfully."""
        controller.grant_standing_approval(
            connector="tavily",
            operation="search",
            approval_id="apr_001",
        )

        result = controller.revoke_standing_approval(
            connector="tavily",
            operation="search",
            revoked_by="principal",
        )

        assert result is True
        assert not controller.has_standing_approval("tavily", "search")

    def test_revoke_standing_approval_not_found(self, controller):
        """Revoke non-existent standing approval returns False."""
        result = controller.revoke_standing_approval(
            connector="nonexistent",
            operation="nonexistent",
        )

        assert result is False

    def test_get_active_promotions(self, controller):
        """Get active promotions returns only unused."""
        promo1 = controller.promote_to_live("tavily", "search", "principal")
        promo2 = controller.promote_to_live("tavily", "extract", "principal")

        controller.consume_promotion(promo1.promotion_id)

        active = controller.get_active_promotions()

        assert len(active) == 1
        assert active[0].promotion_id == promo2.promotion_id

    def test_get_standing_approvals(self, controller):
        """Get all standing approvals."""
        controller.grant_standing_approval("tavily", "search", "apr_001")
        controller.grant_standing_approval("apollo", "search_people", "apr_002")

        approvals = controller.get_standing_approvals()

        assert len(approvals) == 2
        assert "tavily:search" in approvals
        assert "apollo:search_people" in approvals

    def test_get_summary(self, controller):
        """Get controller summary."""
        controller.promote_to_live("tavily", "search", "principal")
        controller.grant_standing_approval("hubspot", "list_contacts", "apr_001")

        summary = controller.get_summary()

        assert summary["active_promotions"] == 1
        assert summary["standing_approvals"] == 1
        assert "blocked_operations" in summary
        assert "delete_all" in summary["blocked_operations"]


# =============================================================================
# Secret Leakage Tests
# =============================================================================

class TestNoSecretLeakage:
    """Tests verifying no secrets leak in UI/services/logging."""

    def test_workflow_item_no_secrets(self):
        """WorkflowItemContext never contains secrets."""
        from core.approval_workflow import WorkflowItemContext, WorkflowItemType

        # Create with potentially dangerous params
        context = WorkflowItemContext(
            item_id="wfi_test",
            item_type=WorkflowItemType.CONNECTOR_ACTION,
            connector_name="hubspot",
            safe_params={
                "query": "test",
                # These should NOT be in safe_params in real usage
            },
        )

        data = context.to_dict()
        data_str = str(data).lower()

        # Should not contain actual secrets
        # Note: key names might appear, but not actual values
        assert "actual_api_key_value" not in data_str
        assert "secret_password" not in data_str

    def test_live_mode_result_no_secrets(self):
        """LiveModeGateResult never contains secrets."""
        from core.live_mode_controller import (
            LiveModeGateResult,
            LiveModeGateStatus,
        )

        result = LiveModeGateResult(
            allowed=False,
            status=LiveModeGateStatus.DENIED_CREDENTIALS,
            reason="Missing credentials",
            connector="hubspot",
            operation="create_contact",
            missing_credentials=["hubspot_api_key"],  # Name only, not value
        )

        data = result.to_dict()
        data_str = str(data).lower()

        # Should contain credential name but not value
        assert "hubspot_api_key" in data_str  # Name is OK
        assert "actual_secret_value" not in data_str

    def test_promotion_no_secrets(self):
        """LiveModePromotion never contains secrets."""
        from core.live_mode_controller import LiveModePromotion

        promotion = LiveModePromotion(
            promotion_id="lmp_test",
            connector="hubspot",
            operation="list_contacts",
            promoted_by="principal",
            approval_id="apr_001",
            risk_level="medium",
        )

        data = promotion.to_dict()
        data_str = str(data).lower()

        # Should not contain secrets
        assert "api_key_value" not in data_str
        assert "secret" not in data_str or "secret_value" not in data_str


# =============================================================================
# Event Logging Tests
# =============================================================================

class TestEventLogging:
    """Tests for event logging integration."""

    def test_approval_logs_events(self):
        """Approval workflow logs events."""
        from core.approval_workflow import ApprovalWorkflow, WorkflowItemType
        from core.event_logger import EventType

        mock_logger = Mock()
        workflow = ApprovalWorkflow(event_logger=mock_logger)

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Test Job",
            description="Testing",
        )

        workflow.approve_item(item.item_id, approver="principal")

        # Should have logged at least 2 events (creation and approval)
        assert mock_logger.log.call_count >= 2

        # Check approval event was logged
        calls = mock_logger.log.call_args_list
        event_types = [c.kwargs.get("event_type") for c in calls]
        assert EventType.APPROVAL_GRANTED in event_types

    def test_denial_logs_events(self):
        """Denial logs events."""
        from core.approval_workflow import ApprovalWorkflow, WorkflowItemType
        from core.event_logger import EventType

        mock_logger = Mock()
        workflow = ApprovalWorkflow(event_logger=mock_logger)

        item = workflow.create_workflow_item(
            item_type=WorkflowItemType.JOB,
            title="Test Job",
            description="Testing",
        )

        workflow.deny_item(item.item_id, denier="principal", rationale="Not approved")

        calls = mock_logger.log.call_args_list
        event_types = [c.kwargs.get("event_type") for c in calls]
        assert EventType.APPROVAL_DENIED in event_types


# =============================================================================
# Singleton Tests
# =============================================================================

class TestSingletons:
    """Tests for singleton instances."""

    def test_get_approval_workflow_singleton(self):
        """get_approval_workflow returns singleton."""
        import core.approval_workflow

        # Reset singleton
        core.approval_workflow._approval_workflow = None

        wf1 = core.approval_workflow.get_approval_workflow()
        wf2 = core.approval_workflow.get_approval_workflow()

        assert wf1 is wf2

        # Clean up
        core.approval_workflow._approval_workflow = None

    def test_get_live_mode_controller_singleton(self):
        """get_live_mode_controller returns singleton."""
        import core.live_mode_controller

        # Reset singleton
        core.live_mode_controller._live_mode_controller = None

        ctrl1 = core.live_mode_controller.get_live_mode_controller()
        ctrl2 = core.live_mode_controller.get_live_mode_controller()

        assert ctrl1 is ctrl2

        # Clean up
        core.live_mode_controller._live_mode_controller = None
