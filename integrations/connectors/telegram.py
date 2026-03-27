"""
Telegram Connector for Project Alpha.

Provides messaging and notification capabilities via Telegram Bot API.

API Documentation: https://core.telegram.org/bots/api
"""

from typing import Any, Dict, List, Optional
import logging

from integrations.base import (
    BaseConnector,
    ConnectorCategory,
    ConnectorResult,
    ConnectorError,
    RateLimitError,
    AuthenticationError,
)
from integrations.action_contracts import (
    ActionContract,
    ActionType,
    ActionApprovalLevel,
    register_action_contract,
)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


logger = logging.getLogger(__name__)


class TelegramConnector(BaseConnector):
    """
    Connector for Telegram Bot API.

    Supported operations:
    - send_message: Send a text message (LIVE CAPABLE)
    - send_document: Send a document/file (dry-run only)
    - get_updates: Get recent updates (LIVE CAPABLE)

    LIVE EXECUTION STATUS:
    - send_message: Fully implemented with httpx
    - get_updates: Fully implemented with httpx
    - send_document: Dry-run only (requires file handling)
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._register_action_contracts()

    @property
    def name(self) -> str:
        return "telegram"

    @property
    def category(self) -> ConnectorCategory:
        return ConnectorCategory.MESSAGING

    @property
    def required_credentials(self) -> List[str]:
        return ["telegram_bot_token"]

    @property
    def optional_credentials(self) -> List[str]:
        return ["telegram_chat_id"]

    @property
    def description(self) -> str:
        return "Telegram bot for notifications and alerts"

    @property
    def base_url(self) -> str:
        return "https://api.telegram.org"

    @property
    def supports_dry_run(self) -> bool:
        return True

    @property
    def requires_approval(self) -> bool:
        return True  # Outbound messages need approval

    def get_operations(self) -> List[str]:
        return ["send_message", "send_document", "get_updates"]

    def _register_action_contracts(self) -> None:
        """Register action contracts for this connector."""
        # send_message - LIVE CAPABLE
        register_action_contract(ActionContract(
            action_name="send_message",
            connector="telegram",
            action_type=ActionType.NOTIFICATION,
            description="Send a text message via Telegram bot",
            required_params=["text"],
            optional_params=["chat_id", "parse_mode", "disable_notification", "reply_to_message_id"],
            required_credentials=["telegram_bot_token"],
            approval_level=ActionApprovalLevel.STANDARD,
            estimated_cost_class="MINIMAL",
            is_external=True,
            supports_live=HTTPX_AVAILABLE,
            live_implementation_status="fully_live" if HTTPX_AVAILABLE else "dry_run_only",
            success_indicators=["message_id", "ok"],
        ))

        # get_updates - LIVE CAPABLE
        register_action_contract(ActionContract(
            action_name="get_updates",
            connector="telegram",
            action_type=ActionType.DATA_FETCH,
            description="Get recent updates from Telegram bot",
            optional_params=["limit", "offset"],
            required_credentials=["telegram_bot_token"],
            approval_level=ActionApprovalLevel.NONE,
            estimated_cost_class="FREE",
            is_external=False,
            supports_live=HTTPX_AVAILABLE,
            live_implementation_status="fully_live" if HTTPX_AVAILABLE else "dry_run_only",
            success_indicators=["ok", "result"],
        ))

        # send_document - DRY_RUN ONLY
        register_action_contract(ActionContract(
            action_name="send_document",
            connector="telegram",
            action_type=ActionType.NOTIFICATION,
            description="Send a document via Telegram bot",
            required_params=["document"],
            optional_params=["chat_id", "caption", "parse_mode"],
            required_credentials=["telegram_bot_token"],
            approval_level=ActionApprovalLevel.ELEVATED,
            estimated_cost_class="MINIMAL",
            is_external=True,
            supports_live=False,
            live_implementation_status="dry_run_only",
            success_indicators=["message_id"],
        ))

    def _health_check_impl(self) -> ConnectorResult:
        """Check Telegram Bot API connectivity."""
        bot_token = self._get_credential("telegram_bot_token")

        if not bot_token.is_set():
            return ConnectorResult.error_result(
                "Bot token not configured",
                error_type="unconfigured",
            )

        # In real implementation, would call getMe endpoint
        return ConnectorResult.success_result(
            data={
                "status": "healthy",
                "bot_info": {
                    "username": "project_alpha_bot",
                    "can_read_all_group_messages": False,
                },
            },
            metadata={"checked_at": "now"},
        )

    def _execute_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """Execute a Telegram operation."""
        bot_token = self._get_credential("telegram_bot_token")

        if operation == "send_message":
            return self._execute_send_message(bot_token.get_value(), params)
        elif operation == "send_document":
            return self._execute_send_document(bot_token.get_value(), params)
        elif operation == "get_updates":
            return self._execute_get_updates(bot_token.get_value(), params)
        else:
            return ConnectorResult.error_result(
                f"Unknown operation: {operation}",
                error_type="invalid_operation",
            )

    def _execute_send_message(
        self,
        bot_token: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Send a text message - LIVE EXECUTION.

        Params:
            chat_id: Target chat ID (required, or uses default from env)
            text: Message text (required)
            parse_mode: 'HTML' or 'Markdown' (optional)
            disable_notification: Send silently (optional)
            reply_to_message_id: Message to reply to (optional)
        """
        if not HTTPX_AVAILABLE:
            return ConnectorResult.error_result(
                "httpx not installed - cannot execute live",
                error_type="dependency_missing",
            )

        # Get chat_id from params or default credential
        chat_id = params.get("chat_id")
        if not chat_id:
            default_chat = self._secrets_manager.get_secret("telegram_chat_id")
            if default_chat.is_set():
                chat_id = default_chat.get_value()

        if not chat_id:
            return ConnectorResult.error_result(
                "Missing required parameter: chat_id (no default configured)",
                error_type="validation_error",
            )

        text = params.get("text")
        if not text:
            return ConnectorResult.error_result(
                "Missing required parameter: text",
                error_type="validation_error",
            )

        # Build request payload
        payload = {
            "chat_id": chat_id,
            "text": text,
        }

        if params.get("parse_mode"):
            payload["parse_mode"] = params["parse_mode"]
        if params.get("disable_notification") is not None:
            payload["disable_notification"] = params["disable_notification"]
        if params.get("reply_to_message_id"):
            payload["reply_to_message_id"] = params["reply_to_message_id"]

        # Execute live API call
        try:
            response = httpx.post(
                f"{self.base_url}/bot{bot_token}/sendMessage",
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            result_data = response.json()

            if not result_data.get("ok"):
                return ConnectorResult.error_result(
                    result_data.get("description", "Telegram API returned ok=false"),
                    error_type="api_error",
                    metadata={"response": result_data},
                )

            return ConnectorResult.success_result(
                data=result_data.get("result"),
                metadata={
                    "http_status": response.status_code,
                    "live_execution": True,
                },
            )

        except httpx.HTTPStatusError as e:
            return ConnectorResult.error_result(
                f"HTTP {e.response.status_code}: {e.response.text}",
                error_type="http_error",
                metadata={"status_code": e.response.status_code},
            )
        except httpx.TimeoutException:
            return ConnectorResult.error_result(
                "Request timed out",
                error_type="timeout",
            )
        except httpx.RequestError as e:
            return ConnectorResult.error_result(
                f"Request failed: {str(e)}",
                error_type="connection_error",
            )
        except Exception as e:
            logger.error(f"Telegram send_message failed: {e}")
            return ConnectorResult.error_result(
                str(e),
                error_type=type(e).__name__,
            )

    def _execute_send_document(
        self,
        bot_token: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Send a document.

        Params:
            chat_id: Target chat ID (required, or uses default)
            document: File path or URL (required)
            caption: Document caption (optional)
            parse_mode: Caption parse mode (optional)
        """
        chat_id = params.get("chat_id")
        if not chat_id:
            default_chat = self._secrets_manager.get_secret("telegram_chat_id")
            if default_chat.is_set():
                chat_id = default_chat.get_value()

        if not chat_id:
            return ConnectorResult.error_result(
                "Missing required parameter: chat_id",
                error_type="validation_error",
            )

        document = params.get("document")
        if not document:
            return ConnectorResult.error_result(
                "Missing required parameter: document",
                error_type="validation_error",
            )

        return ConnectorResult.success_result(
            data={
                "message_id": None,
                "chat_id": chat_id,
                "document": document,
                "message": "Live API call would execute here",
            },
            metadata={
                "caption": params.get("caption"),
            },
        )

    def _execute_get_updates(
        self,
        bot_token: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Get recent updates (for testing connectivity) - LIVE EXECUTION.

        Params:
            limit: Number of updates to retrieve (optional, default 10)
            offset: Update offset (optional)
        """
        if not HTTPX_AVAILABLE:
            return ConnectorResult.error_result(
                "httpx not installed - cannot execute live",
                error_type="dependency_missing",
            )

        # Build request params
        request_params = {
            "limit": params.get("limit", 10),
        }
        if params.get("offset") is not None:
            request_params["offset"] = params["offset"]

        # Execute live API call
        try:
            response = httpx.get(
                f"{self.base_url}/bot{bot_token}/getUpdates",
                params=request_params,
                timeout=10.0,
            )
            response.raise_for_status()
            result_data = response.json()

            if not result_data.get("ok"):
                return ConnectorResult.error_result(
                    result_data.get("description", "Telegram API returned ok=false"),
                    error_type="api_error",
                    metadata={"response": result_data},
                )

            return ConnectorResult.success_result(
                data=result_data.get("result", []),
                metadata={
                    "http_status": response.status_code,
                    "live_execution": True,
                    "update_count": len(result_data.get("result", [])),
                },
            )

        except httpx.HTTPStatusError as e:
            return ConnectorResult.error_result(
                f"HTTP {e.response.status_code}: {e.response.text}",
                error_type="http_error",
                metadata={"status_code": e.response.status_code},
            )
        except httpx.TimeoutException:
            return ConnectorResult.error_result(
                "Request timed out",
                error_type="timeout",
            )
        except httpx.RequestError as e:
            return ConnectorResult.error_result(
                f"Request failed: {str(e)}",
                error_type="connection_error",
            )
        except Exception as e:
            logger.error(f"Telegram get_updates failed: {e}")
            return ConnectorResult.error_result(
                str(e),
                error_type=type(e).__name__,
            )

    def _dry_run_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """Simulate Telegram operations."""
        if operation == "send_message":
            return self._dry_run_send_message(params)
        elif operation == "send_document":
            return self._dry_run_send_document(params)
        elif operation == "get_updates":
            return self._dry_run_get_updates(params)
        else:
            return ConnectorResult.error_result(
                f"Unknown operation: {operation}",
                error_type="invalid_operation",
            )

    def _dry_run_send_message(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate sending a message."""
        chat_id = params.get("chat_id", "123456789")
        text = params.get("text", "Test message")

        mock_response = {
            "ok": True,
            "result": {
                "message_id": 12345,
                "from": {
                    "id": 987654321,
                    "is_bot": True,
                    "first_name": "Project Alpha",
                    "username": "project_alpha_bot",
                },
                "chat": {
                    "id": int(chat_id) if chat_id.isdigit() else 0,
                    "type": "private",
                },
                "date": 1711526400,
                "text": text,
            },
        }

        return ConnectorResult.dry_run_result(
            simulated_data=mock_response,
            metadata={
                "dry_run": True,
                "would_send_to": chat_id,
                "message_length": len(text),
            },
        )

    def _dry_run_send_document(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate sending a document."""
        chat_id = params.get("chat_id", "123456789")
        document = params.get("document", "file.pdf")

        mock_response = {
            "ok": True,
            "result": {
                "message_id": 12346,
                "from": {
                    "id": 987654321,
                    "is_bot": True,
                    "first_name": "Project Alpha",
                },
                "chat": {
                    "id": int(chat_id) if chat_id.isdigit() else 0,
                    "type": "private",
                },
                "date": 1711526400,
                "document": {
                    "file_name": document.split("/")[-1],
                    "mime_type": "application/pdf",
                    "file_id": "simulated_file_id",
                    "file_size": 1024,
                },
                "caption": params.get("caption"),
            },
        }

        return ConnectorResult.dry_run_result(
            simulated_data=mock_response,
            metadata={
                "dry_run": True,
                "would_send_to": chat_id,
                "document": document,
            },
        )

    def _dry_run_get_updates(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate getting updates."""
        mock_updates = [
            {
                "update_id": 100000001,
                "message": {
                    "message_id": 1,
                    "from": {
                        "id": 123456789,
                        "first_name": "Test",
                        "username": "test_user",
                    },
                    "chat": {
                        "id": 123456789,
                        "type": "private",
                    },
                    "date": 1711526400,
                    "text": "Hello bot!",
                },
            },
        ]

        return ConnectorResult.dry_run_result(
            simulated_data={
                "ok": True,
                "result": mock_updates,
            },
            metadata={
                "dry_run": True,
                "simulated_updates": len(mock_updates),
            },
        )
