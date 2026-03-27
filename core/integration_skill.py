"""
Integration Skill - Bridge between skill layer and integration connectors.

Provides a unified interface for the skill selector and orchestrator
to use external service connectors through the standard skill interface.

ARCHITECTURE:
- Wraps connectors in skill-compatible interface
- Routes requests through policy engine
- Enforces dry-run vs live execution
- Reports connector status to skill selector
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging

from integrations.registry import get_connector_registry, ConnectorRegistry
from integrations.base import (
    BaseConnector,
    ConnectorStatus,
    ConnectorCategory,
    ConnectorResult,
)
from core.integration_policies import (
    get_integration_policy_engine,
    IntegrationPolicyEngine,
    IntegrationRiskLevel,
)
from core.credential_registry import get_credential_registry
from core.secrets_manager import get_secrets_manager
from config.settings import get_settings


logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution modes for integration operations."""
    DRY_RUN = "dry_run"
    LIVE = "live"
    APPROVAL_REQUIRED = "approval_required"


@dataclass
class IntegrationRequest:
    """Request to execute an integration operation."""

    connector: str
    operation: str
    params: Dict[str, Any] = field(default_factory=dict)
    dry_run: Optional[bool] = None  # None = use default from settings
    request_id: Optional[str] = None
    requester: str = "orchestrator"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connector": self.connector,
            "operation": self.operation,
            "params": self.params,
            "dry_run": self.dry_run,
            "request_id": self.request_id,
            "requester": self.requester,
        }


@dataclass
class IntegrationResponse:
    """Response from an integration operation."""

    success: bool
    connector: str
    operation: str
    mode: ExecutionMode
    data: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    policy_decision: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "connector": self.connector,
            "operation": self.operation,
            "mode": self.mode.value,
            "data": self.data,
            "error": self.error,
            "error_type": self.error_type,
            "policy_decision": self.policy_decision,
            "timestamp": self.timestamp.isoformat(),
        }


class IntegrationSkill:
    """
    Skill layer interface for external service integrations.

    Provides:
    - Unified interface for all connectors
    - Policy-based execution control
    - Dry-run vs live mode management
    - Status reporting for skill selector
    """

    def __init__(
        self,
        connector_registry: Optional[ConnectorRegistry] = None,
        policy_engine: Optional[IntegrationPolicyEngine] = None,
    ):
        self._connector_registry = connector_registry or get_connector_registry()
        self._policy_engine = policy_engine or get_integration_policy_engine()
        self._settings = get_settings()

    def get_available_connectors(self) -> List[Dict[str, Any]]:
        """Get list of available connectors with status."""
        connectors = self._connector_registry.get_all()
        return [c.to_dict() for c in connectors]

    def get_ready_connectors(self) -> List[str]:
        """Get names of connectors that are ready to use."""
        ready = self._connector_registry.get_ready()
        return [c.name for c in ready]

    def get_connectors_by_category(
        self, category: str
    ) -> List[Dict[str, Any]]:
        """Get connectors by category."""
        try:
            cat = ConnectorCategory(category)
            connectors = self._connector_registry.get_by_category(cat)
            return [c.to_dict() for c in connectors]
        except ValueError:
            return []

    def get_connector_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific connector."""
        connector = self._connector_registry.get(name)
        if connector:
            return connector.to_dict()
        return None

    def health_check(self, connector_name: str) -> ConnectorResult:
        """Run health check on a connector."""
        connector = self._connector_registry.get(connector_name)
        if not connector:
            return ConnectorResult.error_result(
                f"Connector not found: {connector_name}",
                error_type="not_found",
            )
        return connector.health_check()

    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Run health check on all connectors."""
        results = self._connector_registry.health_check_all()
        return {name: r.to_dict() for name, r in results.items()}

    def execute(self, request: IntegrationRequest) -> IntegrationResponse:
        """
        Execute an integration operation.

        Flow:
        1. Validate connector exists
        2. Check policy
        3. Determine execution mode (dry_run vs live)
        4. Execute via connector
        5. Return response
        """
        # Get connector
        connector = self._connector_registry.get(request.connector)
        if not connector:
            return IntegrationResponse(
                success=False,
                connector=request.connector,
                operation=request.operation,
                mode=ExecutionMode.DRY_RUN,
                error=f"Connector not found: {request.connector}",
                error_type="not_found",
            )

        # Check policy
        policy_decision = self._policy_engine.evaluate(
            connector=request.connector,
            operation=request.operation,
            params=request.params,
        )

        if not policy_decision.allowed:
            return IntegrationResponse(
                success=False,
                connector=request.connector,
                operation=request.operation,
                mode=ExecutionMode.DRY_RUN,
                error=policy_decision.reason,
                error_type="policy_denied",
                policy_decision=policy_decision.to_dict(),
            )

        # Determine execution mode
        dry_run = request.dry_run
        if dry_run is None:
            dry_run = self._settings.dry_run_default

        # If approval required, force dry-run unless explicitly live
        if policy_decision.requires_approval and dry_run is None:
            return IntegrationResponse(
                success=True,
                connector=request.connector,
                operation=request.operation,
                mode=ExecutionMode.APPROVAL_REQUIRED,
                data=None,
                policy_decision=policy_decision.to_dict(),
                error="Operation requires approval before live execution",
            )

        # Execute
        mode = ExecutionMode.DRY_RUN if dry_run else ExecutionMode.LIVE

        result = connector.execute(
            operation=request.operation,
            params=request.params,
            dry_run=dry_run,
            request_id=request.request_id,
        )

        # Record usage
        if result.success and not dry_run:
            self._policy_engine.record_usage(request.connector, request.operation)

        return IntegrationResponse(
            success=result.success,
            connector=request.connector,
            operation=request.operation,
            mode=mode,
            data=result.data,
            error=result.error,
            error_type=result.error_type,
            policy_decision=policy_decision.to_dict(),
        )

    def get_operations_for_connector(
        self, connector_name: str
    ) -> List[str]:
        """Get available operations for a connector."""
        connector = self._connector_registry.get(connector_name)
        if connector:
            return connector.get_operations()
        return []

    def get_summary(self) -> Dict[str, Any]:
        """Get integration skill summary."""
        registry_summary = self._connector_registry.get_summary()
        policy_summary = self._policy_engine.get_summary()

        return {
            "connectors": registry_summary,
            "policies": policy_summary,
            "default_dry_run": self._settings.dry_run_default,
            "configured_services": self._settings.get_configured_services(),
        }


# Singleton instance
_integration_skill: Optional[IntegrationSkill] = None


def get_integration_skill() -> IntegrationSkill:
    """Get the global integration skill."""
    global _integration_skill
    if _integration_skill is None:
        _integration_skill = IntegrationSkill()
    return _integration_skill
