"""
SendGrid Connector for Project Alpha.

Provides transactional email capabilities.

API Documentation: https://docs.sendgrid.com/api-reference/
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


logger = logging.getLogger(__name__)


class SendGridConnector(BaseConnector):
    """
    Connector for SendGrid email service.

    Supported operations:
    - send_email: Send a single email
    - send_template: Send using a dynamic template
    """

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
        Send a single email.

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

        # In real implementation:
        # import sendgrid
        # from sendgrid.helpers.mail import Mail
        # message = Mail(
        #     from_email=from_email,
        #     to_emails=to,
        #     subject=subject,
        #     plain_text_content=content if content_type == 'text/plain' else None,
        #     html_content=content if content_type == 'text/html' else None,
        # )
        # sg = sendgrid.SendGridAPIClient(api_key=api_key)
        # response = sg.send(message)

        return ConnectorResult.success_result(
            data={
                "status_code": 202,
                "to": to,
                "subject": subject,
                "from": from_email,
                "message": "Live API call would execute here",
            },
            metadata={
                "content_type": params.get("content_type", "text/plain"),
            },
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
