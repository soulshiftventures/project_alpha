"""
Tests for Live Connector Executions.

Verifies that connectors with live execution capability work correctly
with mocked httpx responses.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from integrations.connectors.telegram import TelegramConnector, HTTPX_AVAILABLE
from integrations.connectors.sendgrid import SendGridConnector
from integrations.connectors.tavily import TavilyConnector
from integrations.action_contracts import (
    ActionContract,
    ActionType,
    ActionExecutionMode,
    ActionApprovalLevel,
    ActionResult,
    ActionExecutionRequest,
    get_action_contract,
    get_live_capable_actions,
)
from integrations.base import ConnectorResult, ConnectorStatus


class TestTelegramLiveExecution:
    """Test Telegram connector with live execution."""

    def test_send_message_live_success(self):
        """Test successful live message send."""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not installed")

        connector = TelegramConnector()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": {
                "message_id": 12345,
                "chat": {"id": 123456789},
                "text": "Test message",
            }
        }

        # Mock credentials
        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_bot_token_123"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            # Mock policy engine
            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                # Mock httpx
                with patch("httpx.post", return_value=mock_response):
                    result = connector.execute(
                        operation="send_message",
                        params={
                            "chat_id": "123456789",
                            "text": "Test message",
                        },
                        dry_run=False,
                    )

        assert result.success
        assert result.data["message_id"] == 12345
        assert not result.dry_run

    def test_send_message_http_error(self):
        """Test HTTP error handling."""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not installed")

        connector = TelegramConnector()

        # Mock credentials
        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_bot_token_123"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            # Mock policy engine
            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                # Mock httpx with error
                with patch("httpx.post") as mock_post:
                    mock_post.side_effect = Exception("HTTPStatusError")

                    result = connector.execute(
                        operation="send_message",
                        params={
                            "chat_id": "123456789",
                            "text": "Test",
                        },
                        dry_run=False,
                    )

        assert not result.success
        assert result.error is not None

    def test_get_updates_live_success(self):
        """Test successful live get_updates."""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not installed")

        connector = TelegramConnector()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": [
                {"update_id": 1, "message": {"text": "Hello"}},
            ]
        }

        # Mock credentials
        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_bot_token_123"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            # Mock policy engine
            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                # Mock httpx
                with patch("httpx.get", return_value=mock_response):
                    result = connector.execute(
                        operation="get_updates",
                        params={"limit": 10},
                        dry_run=False,
                    )

        assert result.success
        assert len(result.data) == 1


class TestActionContracts:
    """Test action contract system."""

    def test_telegram_send_message_contract(self):
        """Test Telegram send_message contract registration."""
        contract = get_action_contract("telegram", "send_message")

        if HTTPX_AVAILABLE:
            assert contract is not None
            assert contract.action_type == ActionType.NOTIFICATION
            assert contract.supports_live
            assert contract.approval_level == ActionApprovalLevel.STANDARD
            assert "text" in contract.required_params

    def test_can_go_live_with_approval(self):
        """Test can_go_live logic with approval."""
        contract = ActionContract(
            action_name="test",
            connector="test",
            action_type=ActionType.NOTIFICATION,
            description="Test",
            supports_live=True,
            approval_level=ActionApprovalLevel.STANDARD,
        )

        can_go, reason = contract.can_go_live(
            has_credentials=True,
            has_approval=True,
            policy_allows=True,
        )

        assert can_go
        assert reason is None

    def test_cannot_go_live_without_credentials(self):
        """Test can_go_live blocks when credentials missing."""
        contract = ActionContract(
            action_name="test",
            connector="test",
            action_type=ActionType.NOTIFICATION,
            description="Test",
            supports_live=True,
        )

        can_go, reason = contract.can_go_live(
            has_credentials=False,
            has_approval=True,
            policy_allows=True,
        )

        assert not can_go
        assert "credentials" in reason.lower()

    def test_cannot_go_live_without_approval_for_destructive(self):
        """Test destructive actions require approval."""
        contract = ActionContract(
            action_name="test",
            connector="test",
            action_type=ActionType.DATA_DELETE,
            description="Test",
            supports_live=True,
            is_destructive=True,
        )

        can_go, reason = contract.can_go_live(
            has_credentials=True,
            has_approval=False,
            policy_allows=True,
        )

        assert not can_go
        assert "approval" in reason.lower()

    def test_get_live_capable_actions(self):
        """Test getting all live-capable actions."""
        live_actions = get_live_capable_actions()

        # Should have at least Telegram actions if httpx available
        if HTTPX_AVAILABLE:
            assert len(live_actions) >= 2
            assert any(a.connector == "telegram" for a in live_actions)


class TestActionResult:
    """Test ActionResult model."""

    def test_action_result_creation(self):
        """Test creating an ActionResult."""
        result = ActionResult(
            success=True,
            action_name="send_message",
            connector="telegram",
            execution_mode=ActionExecutionMode.LIVE_EXECUTED,
            data={"message_id": 123},
        )

        assert result.success
        assert result.action_name == "send_message"
        assert result.execution_mode == ActionExecutionMode.LIVE_EXECUTED

    def test_action_result_to_dict(self):
        """Test ActionResult serialization."""
        result = ActionResult(
            success=True,
            action_name="test",
            connector="test",
            execution_mode=ActionExecutionMode.LIVE_EXECUTED,
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["action_name"] == "test"
        assert result_dict["execution_mode"] == "live_executed"

    def test_action_result_from_connector_result(self):
        """Test creating ActionResult from ConnectorResult."""
        connector_result = ConnectorResult.success_result(
            data={"test": "data"},
            metadata={"key": "value"},
        )

        action_result = ActionResult.from_connector_result(
            connector_result=connector_result,
            action_name="test_action",
            connector="test_connector",
            execution_mode=ActionExecutionMode.LIVE_EXECUTED,
        )

        assert action_result.success
        assert action_result.data == {"test": "data"}
        assert action_result.action_name == "test_action"

    def test_action_result_mark_completed(self):
        """Test marking action as completed."""
        result = ActionResult(
            success=True,
            action_name="test",
            connector="test",
            execution_mode=ActionExecutionMode.LIVE_EXECUTED,
        )

        result.mark_completed()

        assert result.completed_at is not None
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 0


class TestActionExecutionRequest:
    """Test ActionExecutionRequest model."""

    def test_execution_request_creation(self):
        """Test creating an ActionExecutionRequest."""
        request = ActionExecutionRequest(
            action_name="send_message",
            connector="telegram",
            params={"text": "Hello"},
            request_live=True,
        )

        assert request.action_name == "send_message"
        assert request.connector == "telegram"
        assert request.request_live
        assert not request.force_dry_run

    def test_execution_request_to_dict(self):
        """Test ActionExecutionRequest serialization."""
        request = ActionExecutionRequest(
            action_name="test",
            connector="test",
            params={"key": "value"},
        )

        request_dict = request.to_dict()

        assert request_dict["action_name"] == "test"
        assert request_dict["connector"] == "test"
        assert request_dict["params"] == {"key": "value"}


class TestCredentialGating:
    """Test credential-based gating."""

    def test_unconfigured_credentials_block_execution(self):
        """Test that missing credentials block execution."""
        connector = TelegramConnector()

        # Execute without credentials should fail
        result = connector.execute(
            operation="send_message",
            params={"chat_id": "123", "text": "Test"},
            dry_run=False,
        )

        # Should return error due to missing credentials
        assert not result.success or result.error_type == "unconfigured"


class TestApprovalGating:
    """Test approval-based gating via integration_skill."""

    def test_approval_required_actions_identified(self):
        """Test that approval-required actions are properly identified."""
        telegram_contract = get_action_contract("telegram", "send_message")

        if telegram_contract:
            # send_message requires approval
            assert telegram_contract.approval_level in [
                ActionApprovalLevel.STANDARD,
                ActionApprovalLevel.ELEVATED,
                ActionApprovalLevel.ALWAYS,
            ]
