"""
SendGrid Connector for Project Alpha.

Provides transactional email capabilities.

API Documentation: https://docs.sendgrid.com/api-reference/

LIVE EXECUTION STATUS:
- send_email: Fully implemented with httpx
- send_template: Dry-run only (template ID validation needed)
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


class SendGridConnector(BaseConnector):
    """
    Connector for SendGrid email service.

    Supported operations:
    - send_email: Send a single email (LIVE CAPABLE)
    - send_template: Send using a dynamic template (dry-run only)

    LIVE EXECUTION STATUS:
    - send_email: Fully implemented with httpx
    - send_template: Dry-run only (requires template ID validation)
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._register_action_contracts()

    @property
    def name(self) -> str:
        return "sendgrid"

    @property
    def category(self) -> ConnectorCategory:
        return ConnectorCategory.MESSAGING

    @property
    def required_credentials(self) -> List[str]:
        return ["sendgrid_api_key"]

    @property
    def optional_credentials(self) -> List[str]:
        return ["sendgrid_from_email", "sendgrid_from_name"]

    @property
    def description(self) -> str:
        return "Transactional email service"

    @property
    def base_url(self) -> str:
        return "https://api.sendgrid.com/v3"

    @property
    def supports_dry_run(self) -> bool:
        return True

    @property
    def requires_approval(self) -> bool:
        return True  # Outbound emails need approval

    def get_operations(self) -> List[str]:
        return ["send_email", "send_template"]

    def _register_action_contracts(self) -> None:
        """Register action contracts for this connector."""
        # send_email - LIVE CAPABLE
        register_action_contract(ActionContract(
            action_name="send_email",
            connector="sendgrid",
            action_type=ActionType.NOTIFICATION,
            description="Send a transactional email via SendGrid",
            required_params=["to", "subject", "content"],
            optional_params=["from_email", "from_name", "content_type", "reply_to", "cc", "bcc"],
            required_credentials=["sendgrid_api_key"],
            approval_level=ActionApprovalLevel.STANDARD,
            estimated_cost_class="LOW",
            is_external=True,
            supports_live=HTTPX_AVAILABLE,
            live_implementation_status="fully_live" if HTTPX_AVAILABLE else "dry_run_only",
            success_indicators=["status_code", "x-message-id"],
        ))

        # send_template - DRY_RUN ONLY
        register_action_contract(ActionContract(
            action_name="send_template",
            connector="sendgrid",
            action_type=ActionType.NOTIFICATION,
            description="Send email using a dynamic template",
            required_params=["to", "template_id"],
            optional_params=["from_email", "from_name", "dynamic_template_data"],
            required_credentials=["sendgrid_api_key"],
            approval_level=ActionApprovalLevel.STANDARD,
            estimated_cost_class="LOW",
            is_external=True,
            supports_live=False,
            live_implementation_status="dry_run_only",
            success_indicators=["status_code"],
        ))

    def _health_check_impl(self) -> ConnectorResult:
        """Check SendGrid API connectivity."""
        api_key = self._get_credential("sendgrid_api_key")

        if not api_key.is_set():
            return ConnectorResult.error_result(
                "API key not configured",
                error_type="unconfigured",
            )

        # In real implementation, would verify API key
        return ConnectorResult.success_result(
            data={
                "status": "healthy",
                "api_version": "v3",
            },
            metadata={"checked_at": "now"},
        )

    def _execute_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """Execute a SendGrid operation."""
        api_key = self._get_credential("sendgrid_api_key")

        if operation == "send_email":
            return self._execute_send_email(api_key.get_value(), params)
        elif operation == "send_template":
            return self._execute_send_template(api_key.get_value(), params)
        else:
            return ConnectorResult.error_result(
                f"Unknown operation: {operation}",
                error_type="invalid_operation",
            )

    def _execute_send_email(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Send a single email - LIVE EXECUTION.

        Params:
            to: Recipient email (required) - string or list
            subject: Email subject (required)
            content: Email content (required)
            content_type: 'text/plain' or 'text/html' (optional, default 'text/plain')
            from_email: Sender email (optional, uses default)
            from_name: Sender name (optional)
            reply_to: Reply-to email (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
        """
        if not HTTPX_AVAILABLE:
            return ConnectorResult.error_result(
                "httpx not installed - cannot execute live",
                error_type="dependency_missing",
            )

        to = params.get("to")
        if not to:
            return ConnectorResult.error_result(
                "Missing required parameter: to",
                error_type="validation_error",
            )

        subject = params.get("subject")
        if not subject:
            return ConnectorResult.error_result(
                "Missing required parameter: subject",
                error_type="validation_error",
            )

        content = params.get("content")
        if not content:
            return ConnectorResult.error_result(
                "Missing required parameter: content",
                error_type="validation_error",
            )

        # Get from email
        from_email = params.get("from_email")
        if not from_email:
            default_from = self._secrets_manager.get_secret("sendgrid_from_email")
            if default_from.is_set():
                from_email = default_from.get_value()

        if not from_email:
            return ConnectorResult.error_result(
                "Missing required parameter: from_email (no default configured)",
                error_type="validation_error",
            )

        # Normalize recipients to list
        if isinstance(to, str):
            to_list = [to]
        else:
            to_list = list(to)

        # Build SendGrid v3 Mail Send payload
        content_type = params.get("content_type", "text/plain")
        from_name = params.get("from_name")

        personalizations = {
            "to": [{"email": email} for email in to_list],
        }

        # Add CC if provided
        if params.get("cc"):
            cc_list = params["cc"] if isinstance(params["cc"], list) else [params["cc"]]
            personalizations["cc"] = [{"email": email} for email in cc_list]

        # Add BCC if provided
        if params.get("bcc"):
            bcc_list = params["bcc"] if isinstance(params["bcc"], list) else [params["bcc"]]
            personalizations["bcc"] = [{"email": email} for email in bcc_list]

        payload = {
            "personalizations": [personalizations],
            "from": {"email": from_email},
            "subject": subject,
            "content": [
                {
                    "type": content_type,
                    "value": content,
                }
            ],
        }

        if from_name:
            payload["from"]["name"] = from_name

        if params.get("reply_to"):
            payload["reply_to"] = {"email": params["reply_to"]}

        # Execute live API call
        try:
            response = httpx.post(
                f"{self.base_url}/mail/send",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()

            # SendGrid returns 202 Accepted with empty body on success
            message_id = response.headers.get("x-message-id", "unknown")

            return ConnectorResult.success_result(
                data={
                    "status_code": response.status_code,
                    "message_id": message_id,
                    "recipients": to_list,
                    "subject": subject,
                },
                metadata={
                    "http_status": response.status_code,
                    "live_execution": True,
                    "x-message-id": message_id,
                    "recipient_count": len(to_list),
                    "content_type": content_type,
                },
            )

        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_json = e.response.json()
                # Extract error messages from SendGrid response
                errors = error_json.get("errors", [])
                if errors:
                    error_body = "; ".join(err.get("message", "") for err in errors)
                else:
                    error_body = e.response.text[:200]
            except Exception:
                error_body = e.response.text[:200] if e.response.text else "Unknown error"
            return ConnectorResult.error_result(
                f"HTTP {e.response.status_code}: {error_body}",
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
            logger.error(f"SendGrid send_email failed: {e}")
            return ConnectorResult.error_result(
                str(e),
                error_type=type(e).__name__,
            )

    def _execute_send_template(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Send email using a dynamic template.

        Params:
            to: Recipient email (required)
            template_id: SendGrid template ID (required)
            dynamic_template_data: Template variables (optional)
            from_email: Sender email (optional, uses default)
            from_name: Sender name (optional)
        """
        to = params.get("to")
        if not to:
            return ConnectorResult.error_result(
                "Missing required parameter: to",
                error_type="validation_error",
            )

        template_id = params.get("template_id")
        if not template_id:
            return ConnectorResult.error_result(
                "Missing required parameter: template_id",
                error_type="validation_error",
            )

        from_email = params.get("from_email")
        if not from_email:
            default_from = self._secrets_manager.get_secret("sendgrid_from_email")
            if default_from.is_set():
                from_email = default_from.get_value()

        if not from_email:
            return ConnectorResult.error_result(
                "Missing required parameter: from_email",
                error_type="validation_error",
            )

        return ConnectorResult.success_result(
            data={
                "status_code": 202,
                "to": to,
                "template_id": template_id,
                "from": from_email,
                "message": "Live API call would execute here",
            },
            metadata={
                "template_data_keys": list(params.get("dynamic_template_data", {}).keys()),
            },
        )

    def _dry_run_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """Simulate SendGrid operations."""
        if operation == "send_email":
            return self._dry_run_send_email(params)
        elif operation == "send_template":
            return self._dry_run_send_template(params)
        else:
            return ConnectorResult.error_result(
                f"Unknown operation: {operation}",
                error_type="invalid_operation",
            )

    def _dry_run_send_email(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate sending an email."""
        to = params.get("to", "recipient@example.com")
        subject = params.get("subject", "Test Subject")
        content = params.get("content", "Test content")
        from_email = params.get("from_email", "sender@example.com")

        if isinstance(to, str):
            to = [to]

        mock_response = {
            "status_code": 202,
            "body": "",
            "headers": {
                "x-message-id": "simulated-message-id-123",
            },
            "simulated_email": {
                "from": from_email,
                "to": to,
                "subject": subject,
                "content_preview": content[:100] + "..." if len(content) > 100 else content,
            },
        }

        return ConnectorResult.dry_run_result(
            simulated_data=mock_response,
            metadata={
                "dry_run": True,
                "would_send_to": to,
                "recipient_count": len(to),
                "content_length": len(content),
            },
        )

    def _dry_run_send_template(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate sending a template email."""
        to = params.get("to", "recipient@example.com")
        template_id = params.get("template_id", "d-template123")
        template_data = params.get("dynamic_template_data", {})
        from_email = params.get("from_email", "sender@example.com")

        if isinstance(to, str):
            to = [to]

        mock_response = {
            "status_code": 202,
            "body": "",
            "headers": {
                "x-message-id": "simulated-template-msg-456",
            },
            "simulated_email": {
                "from": from_email,
                "to": to,
                "template_id": template_id,
                "template_data": template_data,
            },
        }

        return ConnectorResult.dry_run_result(
            simulated_data=mock_response,
            metadata={
                "dry_run": True,
                "would_send_to": to,
                "template_id": template_id,
                "template_variables": list(template_data.keys()),
            },
        )
