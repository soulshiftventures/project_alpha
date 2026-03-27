"""
Approval Workflow for Project Alpha.

Enhanced approval workflow that connects approval decisions to execution flow,
enabling governed transition from pending/dry-run to live execution.

ARCHITECTURE:
- Links approval records to execution plans and jobs
- Supports approval-gated execution flow
- Manages the lifecycle of approval-required actions
- Provides hooks for live-mode promotion
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import logging

from core.approval_manager import (
    ApprovalManager,
    ApprovalClass,
    ApprovalStatus,
    ApprovalRecord,
    ApprovalPolicy,
)
from core.event_logger import EventLogger, EventType, EventSeverity


logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class WorkflowItemType(Enum):
    """Types of items that can require approval."""
    EXECUTION_PLAN = "execution_plan"
    JOB = "job"
    CONNECTOR_ACTION = "connector_action"
    SKILL_USAGE = "skill_usage"
    LIVE_MODE_PROMOTION = "live_mode_promotion"


class WorkflowItemStatus(Enum):
    """Status of a workflow item."""
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DENIED = "denied"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowItemContext:
    """
    Context for an item requiring approval.

    Contains all information needed to display and execute
    the item after approval.
    """
    item_id: str
    item_type: WorkflowItemType
    status: WorkflowItemStatus = WorkflowItemStatus.PENDING_APPROVAL

    # Display information
    title: str = ""
    description: str = ""
    requester: str = "system"

    # Approval context
    approval_record_id: Optional[str] = None
    risk_level: str = "medium"
    requires_live_mode: bool = False

    # Related entities (IDs only, no secrets)
    plan_id: Optional[str] = None
    job_id: Optional[str] = None
    connector_name: Optional[str] = None
    operation: Optional[str] = None

    # Skill/command context
    skills: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    specialized_agents: List[str] = field(default_factory=list)

    # Safe display data (never contains secrets)
    safe_params: Dict[str, Any] = field(default_factory=dict)
    policy_decisions: Dict[str, Any] = field(default_factory=dict)

    # Execution mode
    current_mode: str = "dry_run"  # dry_run | pending_live | live
    target_mode: str = "dry_run"

    # Timestamps
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())
    approved_at: Optional[str] = None
    executed_at: Optional[str] = None

    # Result tracking
    execution_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    denial_rationale: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for UI display."""
        return {
            "item_id": self.item_id,
            "item_type": self.item_type.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "requester": self.requester,
            "approval_record_id": self.approval_record_id,
            "risk_level": self.risk_level,
            "requires_live_mode": self.requires_live_mode,
            "plan_id": self.plan_id,
            "job_id": self.job_id,
            "connector_name": self.connector_name,
            "operation": self.operation,
            "skills": self.skills,
            "commands": self.commands,
            "specialized_agents": self.specialized_agents,
            "safe_params": self.safe_params,
            "policy_decisions": self.policy_decisions,
            "current_mode": self.current_mode,
            "target_mode": self.target_mode,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "executed_at": self.executed_at,
            "execution_result": self.execution_result,
            "error": self.error,
            "denial_rationale": self.denial_rationale,
        }


@dataclass
class ApprovalDecision:
    """Result of processing an approval decision."""
    success: bool
    item_id: str
    action: str  # approved | denied | cancelled
    decided_by: str
    rationale: str = ""
    execution_triggered: bool = False
    execution_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "item_id": self.item_id,
            "action": self.action,
            "decided_by": self.decided_by,
            "rationale": self.rationale,
            "execution_triggered": self.execution_triggered,
            "execution_result": self.execution_result,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class ApprovalWorkflow:
    """
    Manages the approval workflow for execution control.

    Connects approval decisions to actual execution,
    enabling governed transition from pending to live mode.
    """

    def __init__(
        self,
        approval_manager: Optional[ApprovalManager] = None,
        event_logger: Optional[EventLogger] = None,
    ):
        """Initialize the approval workflow."""
        self._approval_manager = approval_manager or ApprovalManager()
        self._event_logger = event_logger or EventLogger()

        # Track workflow items (in-memory for now)
        self._items: Dict[str, WorkflowItemContext] = {}

        # Execution callbacks (registered by other modules)
        self._on_approved_callbacks: List[Callable[[WorkflowItemContext], None]] = []
        self._on_denied_callbacks: List[Callable[[WorkflowItemContext], None]] = []

    def register_approval_callback(
        self,
        on_approved: Optional[Callable[[WorkflowItemContext], None]] = None,
        on_denied: Optional[Callable[[WorkflowItemContext], None]] = None,
    ) -> None:
        """Register callbacks for approval decisions."""
        if on_approved:
            self._on_approved_callbacks.append(on_approved)
        if on_denied:
            self._on_denied_callbacks.append(on_denied)

    def create_workflow_item(
        self,
        item_type: WorkflowItemType,
        title: str,
        description: str,
        requester: str = "system",
        risk_level: str = "medium",
        requires_live_mode: bool = False,
        plan_id: Optional[str] = None,
        job_id: Optional[str] = None,
        connector_name: Optional[str] = None,
        operation: Optional[str] = None,
        skills: Optional[List[str]] = None,
        commands: Optional[List[str]] = None,
        specialized_agents: Optional[List[str]] = None,
        safe_params: Optional[Dict[str, Any]] = None,
        policy_decisions: Optional[Dict[str, Any]] = None,
        target_mode: str = "dry_run",
    ) -> WorkflowItemContext:
        """
        Create a new workflow item requiring approval.

        Args:
            item_type: Type of item
            title: Display title
            description: Description for operator
            requester: Who requested the action
            risk_level: Risk classification
            requires_live_mode: Whether this needs live mode
            plan_id: Related execution plan ID
            job_id: Related job ID
            connector_name: Related connector
            operation: Specific operation
            skills: Related skills
            commands: Related commands
            specialized_agents: Related agents
            safe_params: Safe-to-display parameters (no secrets)
            policy_decisions: Policy evaluation results
            target_mode: Intended execution mode

        Returns:
            WorkflowItemContext for the created item
        """
        item_id = f"wfi_{_utc_now().strftime('%Y%m%d%H%M%S%f')}"

        item = WorkflowItemContext(
            item_id=item_id,
            item_type=item_type,
            status=WorkflowItemStatus.PENDING_APPROVAL,
            title=title,
            description=description,
            requester=requester,
            risk_level=risk_level,
            requires_live_mode=requires_live_mode,
            plan_id=plan_id,
            job_id=job_id,
            connector_name=connector_name,
            operation=operation,
            skills=skills or [],
            commands=commands or [],
            specialized_agents=specialized_agents or [],
            safe_params=safe_params or {},
            policy_decisions=policy_decisions or {},
            current_mode="dry_run",
            target_mode=target_mode,
        )

        self._items[item_id] = item

        # Log event
        self._event_logger.log(
            event_type=EventType.APPROVAL_REQUESTED,
            message=f"Approval requested: {title}",
            details={
                "item_id": item_id,
                "item_type": item_type.value,
                "risk_level": risk_level,
                "requires_live_mode": requires_live_mode,
                "connector": connector_name,
                "operation": operation,
            },
        )

        return item

    def get_pending_items(self) -> List[WorkflowItemContext]:
        """Get all items pending approval."""
        return [
            item for item in self._items.values()
            if item.status == WorkflowItemStatus.PENDING_APPROVAL
        ]

    def get_item(self, item_id: str) -> Optional[WorkflowItemContext]:
        """Get a specific workflow item."""
        return self._items.get(item_id)

    def get_items_by_type(
        self, item_type: WorkflowItemType
    ) -> List[WorkflowItemContext]:
        """Get items by type."""
        return [
            item for item in self._items.values()
            if item.item_type == item_type
        ]

    def get_items_for_plan(self, plan_id: str) -> List[WorkflowItemContext]:
        """Get all workflow items for an execution plan."""
        return [
            item for item in self._items.values()
            if item.plan_id == plan_id
        ]

    def get_items_for_connector(
        self, connector_name: str
    ) -> List[WorkflowItemContext]:
        """Get all workflow items for a connector."""
        return [
            item for item in self._items.values()
            if item.connector_name == connector_name
        ]

    def approve_item(
        self,
        item_id: str,
        approver: str = "principal",
        rationale: str = "",
        execute_now: bool = False,
        promote_to_live: bool = False,
    ) -> ApprovalDecision:
        """
        Approve a workflow item.

        Args:
            item_id: ID of item to approve
            approver: Who is approving
            rationale: Reason for approval
            execute_now: Whether to trigger execution immediately
            promote_to_live: Whether to promote to live mode

        Returns:
            ApprovalDecision with result
        """
        item = self._items.get(item_id)
        if not item:
            return ApprovalDecision(
                success=False,
                item_id=item_id,
                action="approved",
                decided_by=approver,
                error="Item not found",
            )

        if item.status != WorkflowItemStatus.PENDING_APPROVAL:
            return ApprovalDecision(
                success=False,
                item_id=item_id,
                action="approved",
                decided_by=approver,
                error=f"Item not pending approval (status: {item.status.value})",
            )

        # Update item status
        item.status = WorkflowItemStatus.APPROVED
        item.approved_at = _utc_now().isoformat()

        # Handle live mode promotion if requested
        if promote_to_live and item.requires_live_mode:
            item.current_mode = "live"

        # Log approval event
        self._event_logger.log(
            event_type=EventType.APPROVAL_GRANTED,
            message=f"Approval granted: {item.title}",
            details={
                "item_id": item_id,
                "approver": approver,
                "rationale": rationale,
                "promote_to_live": promote_to_live,
                "execute_now": execute_now,
            },
        )

        # Fire callbacks
        for callback in self._on_approved_callbacks:
            try:
                callback(item)
            except Exception as e:
                logger.error(f"Approval callback error: {e}")

        decision = ApprovalDecision(
            success=True,
            item_id=item_id,
            action="approved",
            decided_by=approver,
            rationale=rationale,
        )

        # Trigger execution if requested
        if execute_now:
            exec_result = self._trigger_execution(item)
            decision.execution_triggered = True
            decision.execution_result = exec_result

        return decision

    def deny_item(
        self,
        item_id: str,
        denier: str = "principal",
        rationale: str = "",
    ) -> ApprovalDecision:
        """
        Deny a workflow item.

        Args:
            item_id: ID of item to deny
            denier: Who is denying
            rationale: Reason for denial

        Returns:
            ApprovalDecision with result
        """
        item = self._items.get(item_id)
        if not item:
            return ApprovalDecision(
                success=False,
                item_id=item_id,
                action="denied",
                decided_by=denier,
                error="Item not found",
            )

        if item.status != WorkflowItemStatus.PENDING_APPROVAL:
            return ApprovalDecision(
                success=False,
                item_id=item_id,
                action="denied",
                decided_by=denier,
                error=f"Item not pending approval (status: {item.status.value})",
            )

        # Update item status
        item.status = WorkflowItemStatus.DENIED
        item.denial_rationale = rationale

        # Log denial event
        self._event_logger.log(
            event_type=EventType.APPROVAL_DENIED,
            message=f"Approval denied: {item.title}",
            severity=EventSeverity.WARNING,
            details={
                "item_id": item_id,
                "denier": denier,
                "rationale": rationale,
            },
        )

        # Fire callbacks
        for callback in self._on_denied_callbacks:
            try:
                callback(item)
            except Exception as e:
                logger.error(f"Denial callback error: {e}")

        return ApprovalDecision(
            success=True,
            item_id=item_id,
            action="denied",
            decided_by=denier,
            rationale=rationale,
        )

    def cancel_item(
        self,
        item_id: str,
        canceller: str = "system",
        reason: str = "",
    ) -> ApprovalDecision:
        """Cancel a pending workflow item."""
        item = self._items.get(item_id)
        if not item:
            return ApprovalDecision(
                success=False,
                item_id=item_id,
                action="cancelled",
                decided_by=canceller,
                error="Item not found",
            )

        item.status = WorkflowItemStatus.CANCELLED

        return ApprovalDecision(
            success=True,
            item_id=item_id,
            action="cancelled",
            decided_by=canceller,
            rationale=reason,
        )

    def _trigger_execution(
        self, item: WorkflowItemContext
    ) -> Dict[str, Any]:
        """
        Trigger execution of an approved item.

        This is a placeholder that returns execution metadata.
        The actual execution is handled by the runtime manager.
        """
        item.executed_at = _utc_now().isoformat()
        item.status = WorkflowItemStatus.EXECUTED

        result = {
            "item_id": item.item_id,
            "executed_at": item.executed_at,
            "mode": item.current_mode,
            "triggered": True,
        }

        item.execution_result = result

        # Log execution triggered
        self._event_logger.log(
            event_type=EventType.TASK_STARTED,
            message=f"Execution triggered: {item.title}",
            details={
                "item_id": item.item_id,
                "mode": item.current_mode,
                "plan_id": item.plan_id,
                "job_id": item.job_id,
            },
        )

        return result

    def mark_executed(
        self,
        item_id: str,
        result: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Mark a workflow item as executed."""
        item = self._items.get(item_id)
        if not item:
            return

        item.executed_at = _utc_now().isoformat()
        item.status = (
            WorkflowItemStatus.EXECUTED if success
            else WorkflowItemStatus.FAILED
        )
        item.execution_result = result
        item.error = error

    def get_history(
        self,
        limit: int = 100,
        status: Optional[WorkflowItemStatus] = None,
        item_type: Optional[WorkflowItemType] = None,
    ) -> List[WorkflowItemContext]:
        """Get workflow item history with optional filters."""
        items = list(self._items.values())

        if status:
            items = [i for i in items if i.status == status]

        if item_type:
            items = [i for i in items if i.item_type == item_type]

        # Sort by created_at descending
        items.sort(key=lambda x: x.created_at, reverse=True)

        return items[:limit]

    def get_summary(self) -> Dict[str, Any]:
        """Get workflow summary statistics."""
        items = list(self._items.values())

        by_status = {}
        by_type = {}

        for item in items:
            status_key = item.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1

            type_key = item.item_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

        pending = len([i for i in items if i.status == WorkflowItemStatus.PENDING_APPROVAL])
        live_mode_pending = len([
            i for i in items
            if i.status == WorkflowItemStatus.PENDING_APPROVAL
            and i.requires_live_mode
        ])

        return {
            "total_items": len(items),
            "pending_approval": pending,
            "live_mode_pending": live_mode_pending,
            "by_status": by_status,
            "by_type": by_type,
        }


# Singleton instance
_approval_workflow: Optional[ApprovalWorkflow] = None


def get_approval_workflow() -> ApprovalWorkflow:
    """Get the global approval workflow."""
    global _approval_workflow
    if _approval_workflow is None:
        _approval_workflow = ApprovalWorkflow()
    return _approval_workflow
