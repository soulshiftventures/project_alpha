"""
Secrets Manager for Project Alpha.

Provides secure secret retrieval, validation, and redaction.

SECURITY RULES:
- Never store actual secrets in the repository
- Never log or display secret values
- Always use redaction when outputting credential metadata
- Secrets are retrieved from environment variables only
"""

import os
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from config.redaction import RedactedString, REDACTION_MARKER, redact_dict


class SecretBackend(Enum):
    """Supported secret storage backends."""
    ENVIRONMENT = "environment"
    # Future: VAULT = "vault"
    # Future: AWS_SECRETS = "aws_secrets"
    # Future: GCP_SECRETS = "gcp_secrets"


class SecretSensitivity(Enum):
    """Sensitivity levels for secrets."""
    LOW = "low"           # Non-critical, e.g., feature flags
    MEDIUM = "medium"     # Important but not catastrophic if leaked
    HIGH = "high"         # Critical credentials, API keys
    CRITICAL = "critical"  # Root/admin credentials, encryption keys


@dataclass
class SecretMetadata:
    """
    Metadata about a secret (NOT the secret itself).

    This class stores information ABOUT secrets for tracking,
    rotation management, and validation purposes.
    The actual secret value is never stored here.
    """

    name: str
    service: str
    purpose: str
    env_var: str
    backend: SecretBackend = SecretBackend.ENVIRONMENT
    sensitivity: SecretSensitivity = SecretSensitivity.HIGH
    required_by: List[str] = field(default_factory=list)
    last_rotated: Optional[datetime] = None
    next_rotation_due: Optional[datetime] = None
    rotation_interval_days: int = 90
    notes: str = ""

    def is_configured(self) -> bool:
        """Check if the secret is configured in the environment."""
        return bool(os.environ.get(self.env_var, "").strip())

    def get_status(self) -> str:
        """Get current status of this secret."""
        if not self.is_configured():
            return "missing"
        if self.is_rotation_due():
            return "rotation_due"
        return "ok"

    def is_rotation_due(self) -> bool:
        """Check if rotation is due."""
        if not self.next_rotation_due:
            return False
        return datetime.now(timezone.utc) >= self.next_rotation_due

    def to_safe_dict(self) -> Dict[str, Any]:
        """Convert to dictionary WITHOUT exposing the secret value."""
        return {
            "name": self.name,
            "service": self.service,
            "purpose": self.purpose,
            "env_var": self.env_var,
            "backend": self.backend.value,
            "sensitivity": self.sensitivity.value,
            "required_by": self.required_by,
            "is_configured": self.is_configured(),
            "status": self.get_status(),
            "last_rotated": self.last_rotated.isoformat() if self.last_rotated else None,
            "next_rotation_due": self.next_rotation_due.isoformat() if self.next_rotation_due else None,
            "rotation_interval_days": self.rotation_interval_days,
            # Never include actual value
            "value": REDACTION_MARKER,
        }


class SecretsManager:
    """
    Central manager for secret retrieval and validation.

    SECURITY:
    - Secrets are ONLY retrieved from environment variables
    - Secret values are NEVER stored in memory longer than needed
    - All output methods use redaction
    """

    def __init__(self):
        self._metadata_registry: Dict[str, SecretMetadata] = {}
        self._load_default_secrets()

    def _load_default_secrets(self) -> None:
        """Load metadata for known secrets."""
        default_secrets = [
            # AI APIs
            SecretMetadata(
                name="anthropic_api_key",
                service="Anthropic",
                purpose="Claude AI API access",
                env_var="ANTHROPIC_API_KEY",
                sensitivity=SecretSensitivity.HIGH,
                required_by=["ai_client", "chief_orchestrator"],
            ),
            SecretMetadata(
                name="openai_api_key",
                service="OpenAI",
                purpose="GPT model API access",
                env_var="OPENAI_API_KEY",
                sensitivity=SecretSensitivity.HIGH,
                required_by=["ai_client"],
            ),

            # Research/Search
            SecretMetadata(
                name="tavily_api_key",
                service="Tavily",
                purpose="Web search and research API",
                env_var="TAVILY_API_KEY",
                sensitivity=SecretSensitivity.MEDIUM,
                required_by=["tavily_connector"],
            ),
            SecretMetadata(
                name="firecrawl_api_key",
                service="Firecrawl",
                purpose="Web scraping and extraction",
                env_var="FIRECRAWL_API_KEY",
                sensitivity=SecretSensitivity.MEDIUM,
                required_by=["firecrawl_connector"],
            ),

            # Lead Generation
            SecretMetadata(
                name="apollo_api_key",
                service="Apollo.io",
                purpose="B2B lead database access",
                env_var="APOLLO_API_KEY",
                sensitivity=SecretSensitivity.HIGH,
                required_by=["apollo_connector"],
            ),
            SecretMetadata(
                name="outscraper_api_key",
                service="Outscraper",
                purpose="Business data extraction",
                env_var="OUTSCRAPER_API_KEY",
                sensitivity=SecretSensitivity.HIGH,
                required_by=["outscraper_connector"],
            ),

            # CRM
            SecretMetadata(
                name="hubspot_api_key",
                service="HubSpot",
                purpose="CRM platform access",
                env_var="HUBSPOT_API_KEY",
                sensitivity=SecretSensitivity.HIGH,
                required_by=["hubspot_connector"],
            ),

            # Messaging
            SecretMetadata(
                name="telegram_bot_token",
                service="Telegram",
                purpose="Bot API for notifications",
                env_var="TELEGRAM_BOT_TOKEN",
                sensitivity=SecretSensitivity.HIGH,
                required_by=["telegram_connector"],
            ),
            SecretMetadata(
                name="sendgrid_api_key",
                service="SendGrid",
                purpose="Transactional email sending",
                env_var="SENDGRID_API_KEY",
                sensitivity=SecretSensitivity.HIGH,
                required_by=["sendgrid_connector"],
            ),

            # Enhancement tools
            SecretMetadata(
                name="aiq_api_key",
                service="AI-Q",
                purpose="Advanced reasoning enhancement",
                env_var="AIQ_API_KEY",
                sensitivity=SecretSensitivity.MEDIUM,
                required_by=["ai_client"],
            ),
            SecretMetadata(
                name="nemoclaw_api_key",
                service="NemoClaw",
                purpose="Sandbox validation",
                env_var="NEMOCLAW_API_KEY",
                sensitivity=SecretSensitivity.MEDIUM,
                required_by=["ai_client"],
            ),
            SecretMetadata(
                name="zep_api_key",
                service="Zep",
                purpose="Memory persistence",
                env_var="ZEP_API_KEY",
                sensitivity=SecretSensitivity.MEDIUM,
                required_by=["ai_client"],
            ),
        ]

        for secret in default_secrets:
            self._metadata_registry[secret.name] = secret

    def register_secret(self, metadata: SecretMetadata) -> None:
        """
        Register metadata for a secret.

        Args:
            metadata: SecretMetadata describing the secret
        """
        self._metadata_registry[metadata.name] = metadata

    def get_secret(self, name: str) -> RedactedString:
        """
        Get a secret value wrapped in RedactedString.

        Args:
            name: Secret name (from metadata registry)

        Returns:
            RedactedString wrapping the secret value
        """
        metadata = self._metadata_registry.get(name)
        if not metadata:
            return RedactedString("", f"unknown:{name}")

        value = os.environ.get(metadata.env_var, "")
        return RedactedString(value, metadata.service)

    def get_secret_for_service(self, service: str) -> RedactedString:
        """
        Get secret by service name.

        Args:
            service: Service name (case-insensitive)

        Returns:
            RedactedString wrapping the secret value
        """
        service_lower = service.lower()
        for metadata in self._metadata_registry.values():
            if metadata.service.lower() == service_lower:
                return self.get_secret(metadata.name)
        return RedactedString("", f"unknown:{service}")

    def is_secret_configured(self, name: str) -> bool:
        """
        Check if a secret is configured.

        Args:
            name: Secret name

        Returns:
            True if configured and non-empty
        """
        metadata = self._metadata_registry.get(name)
        if not metadata:
            return False
        return metadata.is_configured()

    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        """
        Get metadata for a secret.

        Args:
            name: Secret name

        Returns:
            SecretMetadata if found
        """
        return self._metadata_registry.get(name)

    def list_secrets(self) -> List[str]:
        """Get list of all registered secret names."""
        return list(self._metadata_registry.keys())

    def list_configured_secrets(self) -> List[str]:
        """Get list of secrets that are configured."""
        return [
            name for name, meta in self._metadata_registry.items()
            if meta.is_configured()
        ]

    def list_missing_secrets(self) -> List[str]:
        """Get list of secrets that are NOT configured."""
        return [
            name for name, meta in self._metadata_registry.items()
            if not meta.is_configured()
        ]

    def get_secrets_for_component(self, component: str) -> List[SecretMetadata]:
        """
        Get secrets required by a component.

        Args:
            component: Component name

        Returns:
            List of SecretMetadata required by the component
        """
        return [
            meta for meta in self._metadata_registry.values()
            if component in meta.required_by
        ]

    def validate_secrets_for_component(self, component: str) -> Dict[str, Any]:
        """
        Validate that all required secrets for a component are configured.

        Args:
            component: Component name

        Returns:
            Validation result dictionary
        """
        required = self.get_secrets_for_component(component)
        missing = [meta.name for meta in required if not meta.is_configured()]

        return {
            "component": component,
            "valid": len(missing) == 0,
            "required_count": len(required),
            "configured_count": len(required) - len(missing),
            "missing": missing,
        }

    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get health summary of all secrets.

        Returns:
            Summary dictionary (without secret values)
        """
        total = len(self._metadata_registry)
        configured = len(self.list_configured_secrets())
        missing = self.list_missing_secrets()
        rotation_due = [
            name for name, meta in self._metadata_registry.items()
            if meta.is_rotation_due()
        ]

        by_status = {"ok": [], "missing": [], "rotation_due": []}
        for name, meta in self._metadata_registry.items():
            status = meta.get_status()
            by_status[status].append(name)

        by_sensitivity = {level.value: [] for level in SecretSensitivity}
        for name, meta in self._metadata_registry.items():
            by_sensitivity[meta.sensitivity.value].append(name)

        return {
            "total": total,
            "configured": configured,
            "missing_count": len(missing),
            "rotation_due_count": len(rotation_due),
            "by_status": by_status,
            "by_sensitivity": by_sensitivity,
            # Don't include actual secret names in missing list for safety
            "health": "healthy" if not missing else "degraded",
        }

    def to_safe_dict(self) -> Dict[str, Any]:
        """
        Get safe dictionary representation of all secrets.

        Returns:
            Dictionary with redacted values
        """
        return {
            name: meta.to_safe_dict()
            for name, meta in self._metadata_registry.items()
        }


# Singleton instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def get_secret(name: str) -> RedactedString:
    """Convenience function to get a secret."""
    return get_secrets_manager().get_secret(name)


def is_secret_configured(name: str) -> bool:
    """Convenience function to check if secret is configured."""
    return get_secrets_manager().is_secret_configured(name)
