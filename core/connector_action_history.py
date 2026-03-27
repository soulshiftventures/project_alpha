"""
Connector Action History for Project Alpha.

Provides query and retrieval interfaces for connector action execution history
with audit support and safe rendering of sensitive data.

ARCHITECTURE:
- Query interface for connector action executions
- Filter by connector, action, mode, status, related entities
- Safe summary generation with redaction
- Integration with state_store and history_query
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field
import logging

from core.state_store import StateStore, get_state_store
from core.safe_rendering import (
    safe_get,
    safe_format_datetime,
    safe_enum_value,
    safe_dict,
    safe_list,
)

logger = logging.getLogger(__name__)


@dataclass
class ConnectorActionFilter:
    """Filter criteria for connector action queries."""
    connector: Optional[str] = None
    action: Optional[str] = None
    mode: Optional[str] = None  # dry_run, live
    execution_status: Optional[str] = None
    job_id: Optional[str] = None
    plan_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    success: Optional[bool] = None
    limit: int = 100


@dataclass
class ConnectorActionSummary:
    """Summary of a connector action execution."""
    execution_id: str
    connector_name: str
    action_name: str
    timestamp: str
    mode: str
    success: bool
    execution_status: Optional[str] = None
    duration_ms: Optional[int] = None
    cost_class: Optional[str] = None
    approval_state: Optional[str] = None
    error_summary: Optional[str] = None

    # Related entities
    job_id: Optional[str] = None
    plan_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    approval_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "connector_name": self.connector_name,
            "action_name": self.action_name,
            "timestamp": self.timestamp,
            "mode": self.mode,
            "success": self.success,
            "execution_status": self.execution_status,
            "duration_ms": self.duration_ms,
            "cost_class": self.cost_class,
            "approval_state": self.approval_state,
            "error_summary": self.error_summary,
            "job_id": self.job_id,
            "plan_id": self.plan_id,
            "opportunity_id": self.opportunity_id,
            "approval_id": self.approval_id,
        }


class ConnectorActionHistory:
    """
    Query and retrieval interface for connector action execution history.

    Provides lifecycle management methods for connector actions including:
    - Recording action requests (approval_pending state)
    - Recording approval decisions (approved/denied states)
    - Recording execution starts (executing state)
    - Recording execution completions (completed/failed states)
    - Updating actions through lifecycle transitions
    """

    def __init__(self, state_store: Optional[StateStore] = None):
        """Initialize connector action history."""
        self._state_store = state_store or get_state_store()

    def get_recent_actions(
        self,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get recent connector action executions."""
        if not self._state_store or not self._state_store.is_initialized:
            return []

        return self._state_store.get_connector_executions(limit=limit)

    def get_action_by_id(
        self,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a connector action execution by ID."""
        if not self._state_store or not self._state_store.is_initialized:
            return None

        return self._state_store.get_connector_execution_by_id(execution_id)

    def query_actions(
        self,
        filter_criteria: ConnectorActionFilter,
    ) -> List[Dict[str, Any]]:
        """Query connector actions with filters."""
        if not self._state_store or not self._state_store.is_initialized:
            return []

        executions = self._state_store.get_connector_executions(
            connector_name=filter_criteria.connector,
            action_name=filter_criteria.action,
            mode=filter_criteria.mode,
            execution_status=filter_criteria.execution_status,
            job_id=filter_criteria.job_id,
            plan_id=filter_criteria.plan_id,
            opportunity_id=filter_criteria.opportunity_id,
            limit=filter_criteria.limit,
        )

        # Post-filter by success if specified
        if filter_criteria.success is not None:
            executions = [
                e for e in executions
                if safe_get(e, "success") == (1 if filter_criteria.success else 0)
            ]

        return executions

    def get_actions_by_connector(
        self,
        connector: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get all actions for a specific connector."""
        filter_criteria = ConnectorActionFilter(
            connector=connector,
            limit=limit,
        )
        return self.query_actions(filter_criteria)

    def get_actions_by_job(
        self,
        job_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all connector actions for a specific job."""
        filter_criteria = ConnectorActionFilter(
            job_id=job_id,
            limit=1000,
        )
        return self.query_actions(filter_criteria)

    def get_actions_by_plan(
        self,
        plan_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all connector actions for a specific plan."""
        filter_criteria = ConnectorActionFilter(
            plan_id=plan_id,
            limit=1000,
        )
        return self.query_actions(filter_criteria)

    def get_actions_by_opportunity(
        self,
        opportunity_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all connector actions for a specific opportunity."""
        filter_criteria = ConnectorActionFilter(
            opportunity_id=opportunity_id,
            limit=1000,
        )
        return self.query_actions(filter_criteria)

    def get_live_actions(
        self,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get all live-mode connector actions."""
        filter_criteria = ConnectorActionFilter(
            mode="live",
            limit=limit,
        )
        return self.query_actions(filter_criteria)

    def get_failed_actions(
        self,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get all failed connector actions."""
        filter_criteria = ConnectorActionFilter(
            success=False,
            limit=limit,
        )
        return self.query_actions(filter_criteria)

    def get_action_summary(
        self,
        execution_id: str,
    ) -> Optional[ConnectorActionSummary]:
        """Get a safe summary of a connector action execution."""
        execution = self.get_action_by_id(execution_id)
        if not execution:
            return None

        return ConnectorActionSummary(
            execution_id=safe_get(execution, "execution_id", "unknown"),
            connector_name=safe_get(execution, "connector_name", "unknown"),
            action_name=safe_get(execution, "action_name", "unknown"),
            timestamp=safe_get(execution, "timestamp", ""),
            mode=safe_get(execution, "mode", "unknown"),
            success=bool(safe_get(execution, "success", 0)),
            execution_status=safe_get(execution, "execution_status"),
            duration_ms=int(safe_get(execution, "duration_seconds", 0) * 1000) if safe_get(execution, "duration_seconds") else None,
            cost_class=safe_get(execution, "cost_class"),
            approval_state=safe_get(execution, "approval_state"),
            error_summary=safe_get(execution, "error_summary"),
            job_id=safe_get(execution, "job_id"),
            plan_id=safe_get(execution, "plan_id"),
            opportunity_id=safe_get(execution, "opportunity_id"),
            approval_id=safe_get(execution, "approval_id"),
        )

    def get_connector_stats(
        self,
        connector: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get statistics for connector action executions."""
        if connector:
            executions = self.get_actions_by_connector(connector, limit=1000)
        else:
            executions = self.get_recent_actions(limit=1000)

        total = len(executions)
        successful = sum(1 for e in executions if safe_get(e, "success"))
        failed = total - successful
        live_count = sum(1 for e in executions if safe_get(e, "mode") == "live")
        dry_run_count = sum(1 for e in executions if safe_get(e, "mode") == "dry_run")

        return {
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
            "live_executions": live_count,
            "dry_run_executions": dry_run_count,
            "connector": connector,
        }

    # =========================================================================
    # Lifecycle Management Methods
    # =========================================================================

    def record_action_requested(
        self,
        connector_name: str,
        action_name: str,
        mode: str = "dry_run",
        approval_state: str = "pending",
        request_summary: Optional[str] = None,
        job_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        opportunity_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        operator_decision_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Record a connector action request (approval_pending state).

        Args:
            connector_name: Name of connector
            action_name: Name of action
            mode: Execution mode (dry_run or live)
            approval_state: Approval state (pending, approved, denied)
            request_summary: Safe summary of request parameters
            job_id: Related job ID
            plan_id: Related plan ID
            opportunity_id: Related opportunity ID
            approval_id: Related approval ID
            operator_decision_ref: Operator decision reference
            metadata: Additional metadata

        Returns:
            execution_id if successful, None otherwise
        """
        if not self._state_store or not self._state_store.is_initialized:
            return None

        import uuid
        execution_id = f"ce_{uuid.uuid4().hex[:16]}"

        execution = {
            "execution_id": execution_id,
            "connector_name": connector_name,
            "action_name": action_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "success": 0,  # Not yet executed
            "execution_status": "requested",
            "approval_state": approval_state,
            "request_summary": request_summary,
            "job_id": job_id,
            "plan_id": plan_id,
            "opportunity_id": opportunity_id,
            "approval_id": approval_id,
            "operator_decision_ref": operator_decision_ref,
            "metadata": metadata or {},
        }

        saved = self._state_store.save_connector_execution(execution)
        return execution_id if saved else None

    def update_action_approval(
        self,
        execution_id: str,
        approval_state: str,
        approval_id: Optional[str] = None,
        operator_decision_ref: Optional[str] = None,
    ) -> bool:
        """
        Update approval state for a connector action.

        Args:
            execution_id: Execution ID
            approval_state: New approval state (approved, denied, blocked)
            approval_id: Related approval ID
            operator_decision_ref: Operator decision reference

        Returns:
            True if updated successfully
        """
        if not self._state_store or not self._state_store.is_initialized:
            return False

        execution = self._state_store.get_connector_execution_by_id(execution_id)
        if not execution:
            return False

        execution["approval_state"] = approval_state
        if approval_id:
            execution["approval_id"] = approval_id
        if operator_decision_ref:
            execution["operator_decision_ref"] = operator_decision_ref

        # Update execution status based on approval
        if approval_state == "denied" or approval_state == "blocked":
            execution["execution_status"] = "blocked"

        return self._state_store.save_connector_execution(execution)

    def record_action_executing(
        self,
        execution_id: str,
        mode: Optional[str] = None,
    ) -> bool:
        """
        Record that a connector action has started executing.

        Args:
            execution_id: Execution ID
            mode: Execution mode override (live or dry_run)

        Returns:
            True if updated successfully
        """
        if not self._state_store or not self._state_store.is_initialized:
            return False

        execution = self._state_store.get_connector_execution_by_id(execution_id)
        if not execution:
            return False

        execution["execution_status"] = "executing"
        if mode:
            execution["mode"] = mode

        return self._state_store.save_connector_execution(execution)

    def record_action_completed(
        self,
        execution_id: str,
        success: bool,
        response_summary: Optional[str] = None,
        error_summary: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        estimated_cost: Optional[float] = None,
        actual_cost: Optional[float] = None,
        cost_class: Optional[str] = None,
    ) -> bool:
        """
        Record completion of a connector action.

        Args:
            execution_id: Execution ID
            success: Whether execution succeeded
            response_summary: Safe summary of response data
            error_summary: Safe error message if failed
            duration_seconds: Execution duration
            estimated_cost: Estimated cost
            actual_cost: Actual cost
            cost_class: Cost classification

        Returns:
            True if updated successfully
        """
        if not self._state_store or not self._state_store.is_initialized:
            return False

        execution = self._state_store.get_connector_execution_by_id(execution_id)
        if not execution:
            return False

        execution["success"] = 1 if success else 0
        execution["execution_status"] = "completed" if success else "failed"
        execution["response_summary"] = response_summary
        execution["error_summary"] = error_summary

        if duration_seconds is not None:
            execution["duration_seconds"] = duration_seconds
        if estimated_cost is not None:
            execution["estimated_cost"] = estimated_cost
        if actual_cost is not None:
            execution["actual_cost"] = actual_cost
        if cost_class is not None:
            execution["cost_class"] = cost_class

        return self._state_store.save_connector_execution(execution)

    def update_action_status(
        self,
        execution_id: str,
        execution_status: str,
        error_summary: Optional[str] = None,
    ) -> bool:
        """
        Update execution status for a connector action.

        Args:
            execution_id: Execution ID
            execution_status: New status (requested, approval_pending, approved, denied, blocked, executing, completed, failed)
            error_summary: Optional error message

        Returns:
            True if updated successfully
        """
        if not self._state_store or not self._state_store.is_initialized:
            return False

        execution = self._state_store.get_connector_execution_by_id(execution_id)
        if not execution:
            return False

        execution["execution_status"] = execution_status
        if error_summary:
            execution["error_summary"] = error_summary

        return self._state_store.save_connector_execution(execution)


# Singleton instance
_connector_action_history: Optional[ConnectorActionHistory] = None


def get_connector_action_history() -> ConnectorActionHistory:
    """Get the global connector action history instance."""
    global _connector_action_history
    if _connector_action_history is None:
        _connector_action_history = ConnectorActionHistory()
    return _connector_action_history
