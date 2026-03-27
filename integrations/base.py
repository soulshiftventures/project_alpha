"""
Base Connector Infrastructure for Project Alpha.

Defines the abstract base class and common utilities for all connectors.

ARCHITECTURE:
- Every connector inherits from BaseConnector
- Common interface: name, category, health_check(), dry_run(), execute()
- Automatic credential retrieval via SecretsManager
- Policy-based access control via CredentialPolicyEngine
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging

from core.secrets_manager import get_secrets_manager, SecretsManager
from core.credential_policies import (
    get_policy_engine,
    CredentialPolicyEngine,
    PolicyDecision,
)
from core.credential_registry import (
    get_credential_registry,
    CredentialRegistry,
)
from config.redaction import RedactedString, REDACTION_MARKER


logger = logging.getLogger(__name__)


class ConnectorStatus(Enum):
    """Status of a connector."""
    READY = "ready"                     # Configured and operational
    UNCONFIGURED = "unconfigured"       # Missing credentials
    ERROR = "error"                     # Configuration or runtime error
    RATE_LIMITED = "rate_limited"       # Temporarily rate limited
    DISABLED = "disabled"               # Manually disabled


class ConnectorCategory(Enum):
    """Categories of connectors."""
    RESEARCH = "research"
    LEAD_GENERATION = "lead_generation"
    CRM = "crm"
    MESSAGING = "messaging"
    AUTOMATION = "automation"
    PAYMENTS = "payments"
    INFRASTRUCTURE = "infrastructure"
    AI_ENHANCEMENT = "ai_enhancement"


class ConnectorError(Exception):
    """Base exception for connector errors."""

    def __init__(self, message: str, connector: str, recoverable: bool = True):
        self.message = message
        self.connector = connector
        self.recoverable = recoverable
        super().__init__(message)


class AuthenticationError(ConnectorError):
    """Raised when authentication fails."""

    def __init__(self, connector: str, message: str = "Authentication failed"):
        super().__init__(message, connector, recoverable=False)


class RateLimitError(ConnectorError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        connector: str,
        retry_after: Optional[int] = None,
        message: str = "Rate limit exceeded"
    ):
        self.retry_after = retry_after
        super().__init__(message, connector, recoverable=True)


class ConnectionError(ConnectorError):
    """Raised when connection fails."""

    def __init__(self, connector: str, message: str = "Connection failed"):
        super().__init__(message, connector, recoverable=True)


@dataclass
class ConnectorResult:
    """
    Result of a connector operation.

    Standardizes responses from all connectors.
    """

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dry_run: bool = False
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_type": self.error_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "dry_run": self.dry_run,
            "request_id": self.request_id,
        }

    @classmethod
    def success_result(
        cls,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> "ConnectorResult":
        """Create a success result."""
        return cls(
            success=True,
            data=data,
            metadata=metadata or {},
            dry_run=dry_run,
        )

    @classmethod
    def error_result(
        cls,
        error: str,
        error_type: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ConnectorResult":
        """Create an error result."""
        return cls(
            success=False,
            error=error,
            error_type=error_type,
            metadata=metadata or {},
        )

    @classmethod
    def dry_run_result(
        cls,
        simulated_data: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ConnectorResult":
        """Create a dry-run result."""
        return cls(
            success=True,
            data=simulated_data,
            metadata=metadata or {},
            dry_run=True,
        )


class BaseConnector(ABC):
    """
    Abstract base class for all external service connectors.

    SUBCLASSES MUST IMPLEMENT:
    - name (property)
    - category (property)
    - required_credentials (property)
    - _health_check_impl()
    - _execute_impl()
    - _dry_run_impl()

    SECURITY:
    - Never store credentials in instance variables
    - Always retrieve credentials on-demand
    - Use policy engine for access control
    """

    def __init__(
        self,
        secrets_manager: Optional[SecretsManager] = None,
        policy_engine: Optional[CredentialPolicyEngine] = None,
        credential_registry: Optional[CredentialRegistry] = None,
    ):
        self._secrets_manager = secrets_manager or get_secrets_manager()
        self._policy_engine = policy_engine or get_policy_engine()
        self._credential_registry = credential_registry or get_credential_registry()
        self._enabled = True
        self._last_health_check: Optional[datetime] = None
        self._cached_status: Optional[ConnectorStatus] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Connector name (e.g., 'tavily', 'apollo')."""
        pass

    @property
    @abstractmethod
    def category(self) -> ConnectorCategory:
        """Connector category."""
        pass

    @property
    @abstractmethod
    def required_credentials(self) -> List[str]:
        """List of required credential names."""
        pass

    @property
    def optional_credentials(self) -> List[str]:
        """List of optional credential names."""
        return []

    @property
    def description(self) -> str:
        """Human-readable description."""
        return f"{self.name} connector"

    @property
    def base_url(self) -> str:
        """Base URL for API calls (override in subclass)."""
        return ""

    @property
    def supports_dry_run(self) -> bool:
        """Whether this connector supports dry-run mode."""
        return True

    @property
    def requires_approval(self) -> bool:
        """Whether operations require approval."""
        return False

    def is_enabled(self) -> bool:
        """Check if connector is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable the connector."""
        self._enabled = True

    def disable(self) -> None:
        """Disable the connector."""
        self._enabled = False

    def _get_credential(self, name: str) -> RedactedString:
        """
        Get a credential value.

        SECURITY: Returns RedactedString to prevent accidental exposure.
        """
        return self._secrets_manager.get_secret(name)

    def _check_policy(self, operation: str) -> tuple[bool, Optional[str]]:
        """
        Check if operation is allowed by policy.

        Returns:
            Tuple of (allowed, reason if denied)
        """
        for cred_name in self.required_credentials:
            decision, reason = self._policy_engine.check_access(
                credential_name=cred_name,
                component=f"{self.name}_connector",
                operation=operation,
                record_usage=False,  # Don't count policy checks
            )

            if decision == PolicyDecision.DENY:
                return False, reason
            if decision == PolicyDecision.RATE_LIMITED:
                return False, reason
            if decision == PolicyDecision.REQUIRE_APPROVAL:
                return False, f"Operation {operation} requires approval"

        return True, None

    def _record_usage(self, operation: str, success: bool) -> None:
        """Record credential usage for audit."""
        for cred_name in self.required_credentials:
            self._credential_registry.record_usage(
                credential_name=cred_name,
                component=f"{self.name}_connector",
                operation=operation,
                success=success,
            )

    def get_status(self) -> ConnectorStatus:
        """Get current connector status."""
        if not self._enabled:
            return ConnectorStatus.DISABLED

        # Check if credentials are configured
        for cred_name in self.required_credentials:
            if not self._secrets_manager.is_secret_configured(cred_name):
                return ConnectorStatus.UNCONFIGURED

        # Use cached status if recent
        if self._cached_status and self._last_health_check:
            age = datetime.now(timezone.utc) - self._last_health_check
            if age.total_seconds() < 300:  # 5 minutes
                return self._cached_status

        return ConnectorStatus.READY

    def health_check(self) -> ConnectorResult:
        """
        Perform a health check.

        Returns:
            ConnectorResult with health status
        """
        if not self._enabled:
            return ConnectorResult.error_result(
                "Connector disabled",
                error_type="disabled",
            )

        # Check credentials first
        missing = []
        for cred_name in self.required_credentials:
            if not self._secrets_manager.is_secret_configured(cred_name):
                missing.append(cred_name)

        if missing:
            self._cached_status = ConnectorStatus.UNCONFIGURED
            return ConnectorResult.error_result(
                f"Missing credentials: {', '.join(missing)}",
                error_type="unconfigured",
            )

        # Check policy
        allowed, reason = self._check_policy("health_check")
        if not allowed:
            return ConnectorResult.error_result(
                f"Policy denied: {reason}",
                error_type="policy_denied",
            )

        # Perform actual health check
        try:
            result = self._health_check_impl()
            self._last_health_check = datetime.now(timezone.utc)

            if result.success:
                self._cached_status = ConnectorStatus.READY
            else:
                self._cached_status = ConnectorStatus.ERROR

            return result

        except Exception as e:
            self._cached_status = ConnectorStatus.ERROR
            logger.error(f"Health check failed for {self.name}: {e}")
            return ConnectorResult.error_result(
                str(e),
                error_type=type(e).__name__,
            )

    @abstractmethod
    def _health_check_impl(self) -> ConnectorResult:
        """
        Implement the actual health check logic.

        Subclasses should:
        1. Make a lightweight API call to verify connectivity
        2. Return success with API status info
        3. Not modify any data
        """
        pass

    def execute(
        self,
        operation: str,
        params: Dict[str, Any],
        dry_run: bool = False,
        request_id: Optional[str] = None,
    ) -> ConnectorResult:
        """
        Execute an operation.

        Args:
            operation: Operation name
            params: Operation parameters
            dry_run: If True, simulate without actual API call
            request_id: Optional request tracking ID

        Returns:
            ConnectorResult with operation result
        """
        if not self._enabled:
            return ConnectorResult.error_result(
                "Connector disabled",
                error_type="disabled",
            )

        # Check credentials
        missing = []
        for cred_name in self.required_credentials:
            if not self._secrets_manager.is_secret_configured(cred_name):
                missing.append(cred_name)

        if missing:
            return ConnectorResult.error_result(
                f"Missing credentials: {', '.join(missing)}",
                error_type="unconfigured",
            )

        # Check policy
        allowed, reason = self._check_policy(operation)
        if not allowed:
            self._record_usage(operation, False)
            return ConnectorResult.error_result(
                f"Policy denied: {reason}",
                error_type="policy_denied",
            )

        # Execute (dry run or real)
        try:
            if dry_run:
                result = self._dry_run_impl(operation, params)
            else:
                result = self._execute_impl(operation, params)

            result.request_id = request_id
            self._record_usage(operation, result.success)
            return result

        except RateLimitError as e:
            self._cached_status = ConnectorStatus.RATE_LIMITED
            self._record_usage(operation, False)
            return ConnectorResult.error_result(
                str(e),
                error_type="rate_limit",
                metadata={"retry_after": e.retry_after},
            )

        except AuthenticationError as e:
            self._record_usage(operation, False)
            return ConnectorResult.error_result(
                str(e),
                error_type="authentication",
            )

        except ConnectionError as e:
            self._record_usage(operation, False)
            return ConnectorResult.error_result(
                str(e),
                error_type="connection",
            )

        except Exception as e:
            logger.error(f"Execute failed for {self.name}.{operation}: {e}")
            self._record_usage(operation, False)
            return ConnectorResult.error_result(
                str(e),
                error_type=type(e).__name__,
            )

    @abstractmethod
    def _execute_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Implement the actual operation execution.

        Subclasses should:
        1. Validate params for the operation
        2. Make the API call
        3. Transform response to ConnectorResult
        """
        pass

    @abstractmethod
    def _dry_run_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Implement dry-run simulation.

        Subclasses should:
        1. Validate params
        2. Return simulated response matching real API structure
        3. Mark result as dry_run=True
        """
        pass

    def get_operations(self) -> List[str]:
        """Get list of supported operations."""
        return []

    def to_dict(self) -> Dict[str, Any]:
        """Convert connector info to dictionary."""
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "status": self.get_status().value,
            "enabled": self._enabled,
            "base_url": self.base_url,
            "supports_dry_run": self.supports_dry_run,
            "requires_approval": self.requires_approval,
            "required_credentials": self.required_credentials,
            "optional_credentials": self.optional_credentials,
            "operations": self.get_operations(),
        }
