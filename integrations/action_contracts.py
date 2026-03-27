"""
Connector Action Contracts for Project Alpha.

Defines clear contracts for connector-backed actions with live execution support.

ARCHITECTURE:
- ActionContract: Specification for connector actions
- ActionExecutionMode: DRY_RUN, LIVE_CAPABLE, LIVE_EXECUTED
- ActionResult: Detailed execution results with audit metadata
- Action-level approval and credential gating
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Categories of connector actions."""
    NOTIFICATION = "notification"         # Send messages, emails
    DATA_FETCH = "data_fetch"            # Retrieve data (read-only)
    DATA_CREATE = "data_create"          # Create records
    DATA_UPDATE = "data_update"          # Update existing records
    DATA_DELETE = "data_delete"          # Delete records (high risk)
    RESEARCH = "research"                # Web search, content extraction
    ANALYSIS = "analysis"                # Data analysis operations


class ActionExecutionMode(Enum):
    """Execution modes for connector actions."""
    UNAVAILABLE = "unavailable"          # Connector not configured
    DRY_RUN_ONLY = "dry_run_only"       # Only dry-run available
    LIVE_CAPABLE = "live_capable"        # Can go live if approved
    LIVE_EXECUTED = "live_executed"      # Actually executed live
    BLOCKED = "blocked"                  # Policy/credential block


class ActionApprovalLevel(Enum):
    """Approval requirements for actions."""
    NONE = "none"                        # No approval needed
    STANDARD = "standard"                # Normal approval flow
    ELEVATED = "elevated"                # Requires elevated approval
    ALWAYS = "always"                    # Always requires approval


@dataclass
class ActionContract:
    """
    Contract specification for a connector action.

    Defines what the action does, what it requires, and what it produces.
    """

    action_name: str                     # e.g., "send_message"
    connector: str                       # e.g., "telegram"
    action_type: ActionType
    description: str

    # Requirements
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    required_credentials: List[str] = field(default_factory=list)

    # Governance
    approval_level: ActionApprovalLevel = ActionApprovalLevel.NONE
    estimated_cost_class: str = "MINIMAL"  # Cost class from cost_model
    is_destructive: bool = False
    is_external: bool = False            # External outbound action

    # Live execution capability
    supports_live: bool = False          # Can this action execute live?
    live_implementation_status: str = "dry_run_only"  # dry_run_only, live_capable, fully_live

    # Expected output
    expected_output_schema: Optional[Dict[str, Any]] = None
    success_indicators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_name": self.action_name,
            "connector": self.connector,
            "action_type": self.action_type.value,
            "description": self.description,
            "required_params": self.required_params,
            "optional_params": self.optional_params,
            "required_credentials": self.required_credentials,
            "approval_level": self.approval_level.value,
            "estimated_cost_class": self.estimated_cost_class,
            "is_destructive": self.is_destructive,
            "is_external": self.is_external,
            "supports_live": self.supports_live,
            "live_implementation_status": self.live_implementation_status,
            "expected_output_schema": self.expected_output_schema,
            "success_indicators": self.success_indicators,
        }

    def can_go_live(
        self,
        has_credentials: bool,
        has_approval: bool,
        policy_allows: bool,
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if action can execute in live mode.

        Returns:
            Tuple of (can_go_live, reason_if_blocked)
        """
        if not self.supports_live:
            return False, "Action does not support live execution"

        if not has_credentials:
            return False, "Missing required credentials"

        if not policy_allows:
            return False, "Policy denies live execution"

        if self.approval_level == ActionApprovalLevel.ALWAYS and not has_approval:
            return False, "Action requires approval"

        if self.approval_level == ActionApprovalLevel.ELEVATED and not has_approval:
            return False, "Action requires elevated approval"

        if self.is_destructive and not has_approval:
            return False, "Destructive action requires approval"

        return True, None


@dataclass
class ActionResult:
    """
    Result of executing a connector action.

    Extends ConnectorResult with action-specific metadata.
    """

    success: bool
    action_name: str
    connector: str
    execution_mode: ActionExecutionMode

    # Result data
    data: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None

    # Audit metadata
    request_id: Optional[str] = None
    job_id: Optional[str] = None
    plan_id: Optional[str] = None
    approval_id: Optional[str] = None

    # Execution details
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[int] = None

    # Cost tracking
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None

    # Policy and governance
    approval_required: bool = False
    approval_granted: bool = False
    policy_decision: Optional[Dict[str, Any]] = None
    credential_issues: List[str] = field(default_factory=list)

    # Response metadata
    http_status_code: Optional[int] = None
    rate_limit_remaining: Optional[int] = None
    response_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "success": self.success,
            "action_name": self.action_name,
            "connector": self.connector,
            "execution_mode": self.execution_mode.value,
            "data": self.data,
            "error": self.error,
            "error_type": self.error_type,
            "request_id": self.request_id,
            "job_id": self.job_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "estimated_cost": self.estimated_cost,
            "actual_cost": self.actual_cost,
            "approval_required": self.approval_required,
            "approval_granted": self.approval_granted,
            "policy_decision": self.policy_decision,
            "credential_issues": self.credential_issues,
            "http_status_code": self.http_status_code,
            "rate_limit_remaining": self.rate_limit_remaining,
            "response_metadata": self.response_metadata,
        }

    @classmethod
    def from_connector_result(
        cls,
        connector_result: Any,  # ConnectorResult
        action_name: str,
        connector: str,
        execution_mode: ActionExecutionMode,
        **kwargs: Any,
    ) -> "ActionResult":
        """Create ActionResult from ConnectorResult."""
        return cls(
            success=connector_result.success,
            action_name=action_name,
            connector=connector,
            execution_mode=execution_mode,
            data=connector_result.data,
            error=connector_result.error,
            error_type=connector_result.error_type,
            request_id=connector_result.request_id,
            response_metadata=connector_result.metadata,
            **kwargs,
        )

    def mark_completed(self) -> None:
        """Mark action as completed and calculate execution time."""
        self.completed_at = datetime.now(timezone.utc)
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.execution_time_ms = int(delta.total_seconds() * 1000)


@dataclass
class ActionExecutionRequest:
    """Request to execute a connector action."""

    action_name: str
    connector: str
    params: Dict[str, Any] = field(default_factory=dict)

    # Execution control
    force_dry_run: bool = False          # Force dry-run even if live capable
    request_live: bool = False           # Request live execution

    # Context
    request_id: Optional[str] = None
    job_id: Optional[str] = None
    plan_id: Optional[str] = None
    approval_id: Optional[str] = None
    requester: str = "operator"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_name": self.action_name,
            "connector": self.connector,
            "params": self.params,
            "force_dry_run": self.force_dry_run,
            "request_live": self.request_live,
            "request_id": self.request_id,
            "job_id": self.job_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "requester": self.requester,
        }


# Registry of action contracts
_action_contracts: Dict[str, Dict[str, ActionContract]] = {}


def register_action_contract(contract: ActionContract) -> None:
    """Register an action contract."""
    if contract.connector not in _action_contracts:
        _action_contracts[contract.connector] = {}
    _action_contracts[contract.connector][contract.action_name] = contract


def get_action_contract(
    connector: str,
    action_name: str,
) -> Optional[ActionContract]:
    """Get an action contract."""
    return _action_contracts.get(connector, {}).get(action_name)


def get_contracts_for_connector(connector: str) -> List[ActionContract]:
    """Get all action contracts for a connector."""
    return list(_action_contracts.get(connector, {}).values())


def get_all_contracts() -> List[ActionContract]:
    """Get all registered action contracts."""
    contracts = []
    for connector_contracts in _action_contracts.values():
        contracts.extend(connector_contracts.values())
    return contracts


def get_live_capable_actions() -> List[ActionContract]:
    """Get all actions that support live execution."""
    return [c for c in get_all_contracts() if c.supports_live]
