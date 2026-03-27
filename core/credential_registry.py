"""
Credential Registry for Project Alpha.

Maintains a registry of all credentials and their relationships
to components, services, and operations.

SECURITY RULES:
- This module NEVER stores actual credential values
- Only metadata and relationships are tracked
- Actual secrets are retrieved on-demand from environment
"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from core.secrets_manager import (
    SecretMetadata,
    SecretsManager,
    get_secrets_manager,
    SecretSensitivity,
)
from config.redaction import REDACTION_MARKER


class CredentialScope(Enum):
    """Scope of credential usage."""
    GLOBAL = "global"           # Can be used by any component
    SERVICE = "service"         # Restricted to specific service
    COMPONENT = "component"     # Restricted to specific component
    WORKFLOW = "workflow"       # Restricted to specific workflow


class CredentialUsageType(Enum):
    """Types of credential usage."""
    API_AUTHENTICATION = "api_authentication"
    DATABASE_CONNECTION = "database_connection"
    SERVICE_ACCOUNT = "service_account"
    WEBHOOK_SECRET = "webhook_secret"
    ENCRYPTION_KEY = "encryption_key"
    NOTIFICATION = "notification"


@dataclass
class CredentialUsageRecord:
    """Record of credential usage (for audit)."""

    credential_name: str
    component: str
    operation: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    error_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "credential_name": self.credential_name,
            "component": component,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_type": self.error_type,
            # Never include actual value
        }


@dataclass
class CredentialBinding:
    """
    Binding between a credential and a component/service.

    Tracks which components are authorized to use which credentials.
    """

    credential_name: str
    component: str
    scope: CredentialScope
    usage_type: CredentialUsageType
    required: bool = True
    description: str = ""
    granted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    granted_by: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "credential_name": self.credential_name,
            "component": self.component,
            "scope": self.scope.value,
            "usage_type": self.usage_type.value,
            "required": self.required,
            "description": self.description,
            "granted_at": self.granted_at.isoformat(),
            "granted_by": self.granted_by,
        }


class CredentialRegistry:
    """
    Registry for credential bindings and usage tracking.

    SECURITY:
    - No credential VALUES are stored here
    - Only metadata, bindings, and usage records
    - Actual retrieval delegated to SecretsManager
    """

    def __init__(self, secrets_manager: Optional[SecretsManager] = None):
        self._secrets_manager = secrets_manager or get_secrets_manager()
        self._bindings: Dict[str, List[CredentialBinding]] = {}
        self._usage_log: List[CredentialUsageRecord] = []
        self._authorized_components: Dict[str, Set[str]] = {}
        self._load_default_bindings()

    def _load_default_bindings(self) -> None:
        """Load default credential bindings."""
        default_bindings = [
            # AI Clients
            CredentialBinding(
                credential_name="anthropic_api_key",
                component="ai_client",
                scope=CredentialScope.COMPONENT,
                usage_type=CredentialUsageType.API_AUTHENTICATION,
                required=True,
                description="Primary AI reasoning engine",
            ),
            CredentialBinding(
                credential_name="anthropic_api_key",
                component="chief_orchestrator",
                scope=CredentialScope.COMPONENT,
                usage_type=CredentialUsageType.API_AUTHENTICATION,
                required=True,
                description="Orchestrator AI access",
            ),
            CredentialBinding(
                credential_name="openai_api_key",
                component="ai_client",
                scope=CredentialScope.COMPONENT,
                usage_type=CredentialUsageType.API_AUTHENTICATION,
                required=False,
                description="Alternative AI provider",
            ),

            # Research Connectors
            CredentialBinding(
                credential_name="tavily_api_key",
                component="tavily_connector",
                scope=CredentialScope.SERVICE,
                usage_type=CredentialUsageType.API_AUTHENTICATION,
                required=True,
                description="Web search API",
            ),
            CredentialBinding(
                credential_name="firecrawl_api_key",
                component="firecrawl_connector",
                scope=CredentialScope.SERVICE,
                usage_type=CredentialUsageType.API_AUTHENTICATION,
                required=True,
                description="Web scraping API",
            ),

            # Lead Generation Connectors
            CredentialBinding(
                credential_name="apollo_api_key",
                component="apollo_connector",
                scope=CredentialScope.SERVICE,
                usage_type=CredentialUsageType.API_AUTHENTICATION,
                required=True,
                description="B2B lead database",
            ),
            CredentialBinding(
                credential_name="outscraper_api_key",
                component="outscraper_connector",
                scope=CredentialScope.SERVICE,
                usage_type=CredentialUsageType.API_AUTHENTICATION,
                required=True,
                description="Business data extraction",
            ),

            # CRM
            CredentialBinding(
                credential_name="hubspot_api_key",
                component="hubspot_connector",
                scope=CredentialScope.SERVICE,
                usage_type=CredentialUsageType.API_AUTHENTICATION,
                required=True,
                description="CRM platform access",
            ),

            # Messaging
            CredentialBinding(
                credential_name="telegram_bot_token",
                component="telegram_connector",
                scope=CredentialScope.SERVICE,
                usage_type=CredentialUsageType.NOTIFICATION,
                required=True,
                description="Telegram bot notifications",
            ),
            CredentialBinding(
                credential_name="sendgrid_api_key",
                component="sendgrid_connector",
                scope=CredentialScope.SERVICE,
                usage_type=CredentialUsageType.NOTIFICATION,
                required=True,
                description="Email delivery service",
            ),
        ]

        for binding in default_bindings:
            self.register_binding(binding)

    def register_binding(self, binding: CredentialBinding) -> None:
        """
        Register a credential binding.

        Args:
            binding: CredentialBinding to register
        """
        if binding.credential_name not in self._bindings:
            self._bindings[binding.credential_name] = []

        self._bindings[binding.credential_name].append(binding)

        # Track authorized components
        if binding.credential_name not in self._authorized_components:
            self._authorized_components[binding.credential_name] = set()
        self._authorized_components[binding.credential_name].add(binding.component)

    def is_authorized(self, credential_name: str, component: str) -> bool:
        """
        Check if a component is authorized to use a credential.

        Args:
            credential_name: Name of the credential
            component: Component requesting access

        Returns:
            True if authorized
        """
        authorized = self._authorized_components.get(credential_name, set())
        return component in authorized

    def get_bindings_for_credential(self, credential_name: str) -> List[CredentialBinding]:
        """Get all bindings for a credential."""
        return self._bindings.get(credential_name, [])

    def get_bindings_for_component(self, component: str) -> List[CredentialBinding]:
        """Get all credential bindings for a component."""
        bindings = []
        for cred_bindings in self._bindings.values():
            for binding in cred_bindings:
                if binding.component == component:
                    bindings.append(binding)
        return bindings

    def get_required_credentials(self, component: str) -> List[str]:
        """Get list of required credentials for a component."""
        bindings = self.get_bindings_for_component(component)
        return [b.credential_name for b in bindings if b.required]

    def get_optional_credentials(self, component: str) -> List[str]:
        """Get list of optional credentials for a component."""
        bindings = self.get_bindings_for_component(component)
        return [b.credential_name for b in bindings if not b.required]

    def validate_component(self, component: str) -> Dict[str, Any]:
        """
        Validate that a component has all required credentials.

        Args:
            component: Component to validate

        Returns:
            Validation result
        """
        required = self.get_required_credentials(component)
        missing = []
        configured = []

        for cred_name in required:
            if self._secrets_manager.is_secret_configured(cred_name):
                configured.append(cred_name)
            else:
                missing.append(cred_name)

        return {
            "component": component,
            "valid": len(missing) == 0,
            "required": required,
            "configured": configured,
            "missing": missing,
        }

    def record_usage(
        self,
        credential_name: str,
        component: str,
        operation: str,
        success: bool = True,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Record credential usage for audit.

        Args:
            credential_name: Credential used
            component: Component that used it
            operation: Operation performed
            success: Whether operation succeeded
            error_type: Type of error if failed
        """
        record = CredentialUsageRecord(
            credential_name=credential_name,
            component=component,
            operation=operation,
            success=success,
            error_type=error_type,
        )
        self._usage_log.append(record)

        # Trim log if too large
        if len(self._usage_log) > 10000:
            self._usage_log = self._usage_log[-5000:]

    def get_usage_log(
        self,
        credential_name: Optional[str] = None,
        component: Optional[str] = None,
        limit: int = 100,
    ) -> List[CredentialUsageRecord]:
        """
        Get usage log with optional filters.

        Args:
            credential_name: Filter by credential
            component: Filter by component
            limit: Maximum records to return

        Returns:
            List of usage records
        """
        filtered = self._usage_log

        if credential_name:
            filtered = [r for r in filtered if r.credential_name == credential_name]

        if component:
            filtered = [r for r in filtered if r.component == component]

        return filtered[-limit:]

    def get_credentials_by_usage_type(
        self, usage_type: CredentialUsageType
    ) -> List[str]:
        """Get credentials by usage type."""
        credentials = set()
        for cred_name, bindings in self._bindings.items():
            for binding in bindings:
                if binding.usage_type == usage_type:
                    credentials.add(cred_name)
        return list(credentials)

    def get_components_using_credential(self, credential_name: str) -> List[str]:
        """Get all components authorized to use a credential."""
        return list(self._authorized_components.get(credential_name, set()))

    def get_summary(self) -> Dict[str, Any]:
        """Get registry summary."""
        total_credentials = len(self._bindings)
        total_bindings = sum(len(b) for b in self._bindings.values())
        total_components = len(set(
            binding.component
            for bindings in self._bindings.values()
            for binding in bindings
        ))

        by_usage_type = {}
        for usage_type in CredentialUsageType:
            creds = self.get_credentials_by_usage_type(usage_type)
            by_usage_type[usage_type.value] = len(creds)

        return {
            "total_credentials": total_credentials,
            "total_bindings": total_bindings,
            "total_components": total_components,
            "by_usage_type": by_usage_type,
            "usage_log_size": len(self._usage_log),
        }


# Singleton instance
_credential_registry: Optional[CredentialRegistry] = None


def get_credential_registry() -> CredentialRegistry:
    """Get the global credential registry."""
    global _credential_registry
    if _credential_registry is None:
        _credential_registry = CredentialRegistry()
    return _credential_registry
