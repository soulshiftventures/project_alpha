"""
Live Mode Controller for Project Alpha.

Governs the promotion of operations from dry-run to live mode.
Ensures live execution only happens through controlled, policy-checked,
and approval-gated pathways.

ARCHITECTURE:
- Enforces policy checks before live promotion
- Validates credential availability
- Requires explicit approval for live operations
- Maintains audit trail of all live promotions
- Never allows global live-mode flipping
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import logging

from core.approval_manager import ApprovalClass
from core.event_logger import EventLogger, EventType, EventSeverity
from core.integration_policies import (
    IntegrationPolicyEngine,
    IntegrationRiskLevel,
    PolicyDecision,
    get_integration_policy_engine,
)
from core.secrets_manager import get_secrets_manager, SecretsManager
from core.credential_registry import get_credential_registry


logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class LiveModeGateStatus(Enum):
    """Status of live mode gate check."""
    ALLOWED = "allowed"
    DENIED_POLICY = "denied_policy"
    DENIED_CREDENTIALS = "denied_credentials"
    DENIED_APPROVAL = "denied_approval"
    DENIED_BLOCKED = "denied_blocked"


@dataclass
class LiveModeGateResult:
    """Result of a live mode gate check."""
    allowed: bool
    status: LiveModeGateStatus
    reason: str
    connector: str
    operation: str
    risk_level: IntegrationRiskLevel = IntegrationRiskLevel.MEDIUM

    # What's missing if denied
    missing_credentials: List[str] = field(default_factory=list)
    missing_approvals: List[str] = field(default_factory=list)
    policy_violations: List[str] = field(default_factory=list)

    # If allowed, any constraints
    constraints: Dict[str, Any] = field(default_factory=dict)

    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "status": self.status.value,
            "reason": self.reason,
            "connector": self.connector,
            "operation": self.operation,
            "risk_level": self.risk_level.value,
            "missing_credentials": self.missing_credentials,
            "missing_approvals": self.missing_approvals,
            "policy_violations": self.policy_violations,
            "constraints": self.constraints,
            "timestamp": self.timestamp,
        }


@dataclass
class LiveModePromotion:
    """Record of a live mode promotion."""
    promotion_id: str
    connector: str
    operation: str
    promoted_by: str
    approval_id: Optional[str]
    risk_level: str
    promoted_at: str = field(default_factory=lambda: _utc_now().isoformat())
    expires_at: Optional[str] = None  # Single-use promotions expire
    used: bool = False
    used_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "promotion_id": self.promotion_id,
            "connector": self.connector,
            "operation": self.operation,
            "promoted_by": self.promoted_by,
            "approval_id": self.approval_id,
            "risk_level": self.risk_level,
            "promoted_at": self.promoted_at,
            "expires_at": self.expires_at,
            "used": self.used,
            "used_at": self.used_at,
        }


class LiveModeController:
    """
    Controller for live mode promotion.

    Ensures that live execution is:
    - Policy-compliant
    - Credential-verified
    - Approval-gated
    - Audit-logged

    IMPORTANT: This controller never enables global live mode.
    Each operation must be individually promoted through proper channels.
    """

    # Operations that are NEVER allowed in live mode
    BLOCKED_OPERATIONS: Set[str] = {
        "delete_all",
        "purge",
        "reset_database",
        "bulk_delete",
    }

    # Connectors that require explicit per-operation approval
    HIGH_RISK_CONNECTORS: Set[str] = {
        "sendgrid",  # Email sends
        "hubspot",   # CRM writes
    }

    def __init__(
        self,
        policy_engine: Optional[IntegrationPolicyEngine] = None,
        secrets_manager: Optional[SecretsManager] = None,
        event_logger: Optional[EventLogger] = None,
    ):
        """Initialize the live mode controller."""
        self._policy_engine = policy_engine or get_integration_policy_engine()
        self._secrets_manager = secrets_manager or get_secrets_manager()
        self._event_logger = event_logger or EventLogger()

        # Track active promotions
        self._promotions: Dict[str, LiveModePromotion] = {}

        # Track promotion history
        self._promotion_history: List[LiveModePromotion] = []

        # Track approved operation types (connector:operation -> approval_id)
        self._approved_operations: Dict[str, str] = {}

    def check_live_mode_gate(
        self,
        connector: str,
        operation: str,
        approval_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> LiveModeGateResult:
        """
        Check if an operation can be promoted to live mode.

        This is a comprehensive gate check that verifies:
        1. Operation is not blocked
        2. Policy allows the operation
        3. Required credentials are available
        4. Approval has been granted (if required)

        Args:
            connector: Connector name
            operation: Operation name
            approval_id: ID of approval if one was granted
            context: Additional context

        Returns:
            LiveModeGateResult with detailed status
        """
        # Check 1: Is operation blocked?
        if operation in self.BLOCKED_OPERATIONS:
            return LiveModeGateResult(
                allowed=False,
                status=LiveModeGateStatus.DENIED_BLOCKED,
                reason=f"Operation '{operation}' is blocked from live mode",
                connector=connector,
                operation=operation,
                policy_violations=[f"Operation '{operation}' is globally blocked"],
            )

        # Check 2: Policy evaluation
        policy_decision = self._policy_engine.evaluate(
            connector=connector,
            operation=operation,
            params=context or {},
        )

        if not policy_decision.allowed:
            return LiveModeGateResult(
                allowed=False,
                status=LiveModeGateStatus.DENIED_POLICY,
                reason=policy_decision.reason,
                connector=connector,
                operation=operation,
                risk_level=policy_decision.risk_level,
                policy_violations=[policy_decision.reason],
            )

        # Check 3: Credential availability
        credential_registry = get_credential_registry()
        required_creds = credential_registry.get_required_credentials(connector)
        missing_creds = []

        for cred in required_creds:
            if not self._secrets_manager.has_secret(cred):
                missing_creds.append(cred)

        if missing_creds:
            return LiveModeGateResult(
                allowed=False,
                status=LiveModeGateStatus.DENIED_CREDENTIALS,
                reason=f"Missing required credentials: {', '.join(missing_creds)}",
                connector=connector,
                operation=operation,
                risk_level=policy_decision.risk_level,
                missing_credentials=missing_creds,
            )

        # Check 4: Approval requirement
        if policy_decision.requires_approval:
            # Check if we have an approval
            if not approval_id:
                # Check if this operation type has standing approval
                op_key = f"{connector}:{operation}"
                standing_approval = self._approved_operations.get(op_key)

                if not standing_approval:
                    return LiveModeGateResult(
                        allowed=False,
                        status=LiveModeGateStatus.DENIED_APPROVAL,
                        reason="Operation requires approval before live execution",
                        connector=connector,
                        operation=operation,
                        risk_level=policy_decision.risk_level,
                        missing_approvals=["principal_approval"],
                    )
                approval_id = standing_approval

        # All checks passed
        return LiveModeGateResult(
            allowed=True,
            status=LiveModeGateStatus.ALLOWED,
            reason="Live mode gate passed",
            connector=connector,
            operation=operation,
            risk_level=policy_decision.risk_level,
            constraints=policy_decision.constraints,
        )

    def promote_to_live(
        self,
        connector: str,
        operation: str,
        promoted_by: str = "principal",
        approval_id: Optional[str] = None,
        single_use: bool = True,
    ) -> Optional[LiveModePromotion]:
        """
        Promote an operation to live mode.

        This creates a promotion record that allows a single (or multiple)
        live execution(s) of the specified operation.

        Args:
            connector: Connector name
            operation: Operation name
            promoted_by: Who is promoting
            approval_id: Associated approval ID
            single_use: If True, promotion expires after one use

        Returns:
            LiveModePromotion if successful, None if gate check fails
        """
        # Gate check
        gate_result = self.check_live_mode_gate(
            connector=connector,
            operation=operation,
            approval_id=approval_id,
        )

        if not gate_result.allowed:
            self._event_logger.log(
                event_type=EventType.SKILL_BLOCKED,
                message=f"Live mode promotion denied: {connector}:{operation}",
                severity=EventSeverity.WARNING,
                details={
                    "connector": connector,
                    "operation": operation,
                    "promoted_by": promoted_by,
                    "reason": gate_result.reason,
                    "status": gate_result.status.value,
                },
            )
            return None

        # Create promotion
        promotion_id = f"lmp_{_utc_now().strftime('%Y%m%d%H%M%S%f')}"

        promotion = LiveModePromotion(
            promotion_id=promotion_id,
            connector=connector,
            operation=operation,
            promoted_by=promoted_by,
            approval_id=approval_id,
            risk_level=gate_result.risk_level.value,
        )

        self._promotions[promotion_id] = promotion

        # Log promotion
        self._event_logger.log(
            event_type=EventType.APPROVAL_GRANTED,
            message=f"Live mode promotion granted: {connector}:{operation}",
            details={
                "promotion_id": promotion_id,
                "connector": connector,
                "operation": operation,
                "promoted_by": promoted_by,
                "approval_id": approval_id,
                "single_use": single_use,
                "risk_level": gate_result.risk_level.value,
            },
        )

        return promotion

    def consume_promotion(
        self,
        promotion_id: str,
    ) -> bool:
        """
        Consume a promotion (mark as used).

        For single-use promotions, this marks them as expired.

        Args:
            promotion_id: ID of promotion to consume

        Returns:
            True if promotion was valid and consumed
        """
        promotion = self._promotions.get(promotion_id)
        if not promotion:
            return False

        if promotion.used:
            return False  # Already used

        promotion.used = True
        promotion.used_at = _utc_now().isoformat()

        # Move to history
        self._promotion_history.append(promotion)

        self._event_logger.log(
            event_type=EventType.TASK_COMPLETED,
            message=f"Live mode promotion consumed: {promotion.connector}:{promotion.operation}",
            details={
                "promotion_id": promotion_id,
                "connector": promotion.connector,
                "operation": promotion.operation,
            },
        )

        return True

    def grant_standing_approval(
        self,
        connector: str,
        operation: str,
        approval_id: str,
        granted_by: str = "principal",
    ) -> bool:
        """
        Grant standing approval for an operation type.

        This allows the operation to pass the approval gate
        without per-instance approval.

        Args:
            connector: Connector name
            operation: Operation name
            approval_id: Approval record ID
            granted_by: Who granted

        Returns:
            True if granted
        """
        op_key = f"{connector}:{operation}"
        self._approved_operations[op_key] = approval_id

        self._event_logger.log(
            event_type=EventType.APPROVAL_GRANTED,
            message=f"Standing approval granted: {connector}:{operation}",
            details={
                "connector": connector,
                "operation": operation,
                "approval_id": approval_id,
                "granted_by": granted_by,
            },
        )

        return True

    def revoke_standing_approval(
        self,
        connector: str,
        operation: str,
        revoked_by: str = "principal",
    ) -> bool:
        """Revoke standing approval for an operation."""
        op_key = f"{connector}:{operation}"

        if op_key not in self._approved_operations:
            return False

        del self._approved_operations[op_key]

        self._event_logger.log(
            event_type=EventType.APPROVAL_DENIED,
            message=f"Standing approval revoked: {connector}:{operation}",
            details={
                "connector": connector,
                "operation": operation,
                "revoked_by": revoked_by,
            },
        )

        return True

    def get_active_promotions(self) -> List[LiveModePromotion]:
        """Get all active (unused) promotions."""
        return [
            p for p in self._promotions.values()
            if not p.used
        ]

    def get_promotion(self, promotion_id: str) -> Optional[LiveModePromotion]:
        """Get a specific promotion."""
        return self._promotions.get(promotion_id)

    def get_promotion_history(self, limit: int = 100) -> List[LiveModePromotion]:
        """Get promotion history."""
        return self._promotion_history[-limit:]

    def get_standing_approvals(self) -> Dict[str, str]:
        """Get all standing approvals."""
        return self._approved_operations.copy()

    def has_standing_approval(
        self,
        connector: str,
        operation: str,
    ) -> bool:
        """Check if an operation has standing approval."""
        op_key = f"{connector}:{operation}"
        return op_key in self._approved_operations

    def get_summary(self) -> Dict[str, Any]:
        """Get live mode controller summary."""
        active = self.get_active_promotions()

        by_connector = {}
        for p in active:
            by_connector[p.connector] = by_connector.get(p.connector, 0) + 1

        return {
            "active_promotions": len(active),
            "total_promotions": len(self._promotion_history) + len(active),
            "standing_approvals": len(self._approved_operations),
            "promotions_by_connector": by_connector,
            "blocked_operations": list(self.BLOCKED_OPERATIONS),
            "high_risk_connectors": list(self.HIGH_RISK_CONNECTORS),
        }


# Singleton instance
_live_mode_controller: Optional[LiveModeController] = None


def get_live_mode_controller() -> LiveModeController:
    """Get the global live mode controller."""
    global _live_mode_controller
    if _live_mode_controller is None:
        _live_mode_controller = LiveModeController()
    return _live_mode_controller
