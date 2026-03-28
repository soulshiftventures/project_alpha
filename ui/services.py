"""
Service layer for UI backend access.

Provides clean interfaces to core modules for the operator interface.
Keeps route handlers thin and business logic centralized.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

# Safe rendering utilities
from core.safe_rendering import (
    safe_get,
    safe_format_datetime,
    safe_isoformat,
    safe_enum_value,
    safe_list,
    safe_dict,
    ensure_record_exists,
    safe_join_records,
)

# Core module imports
from core.chief_orchestrator import ChiefOrchestrator, OrchestrationResult
from core.runtime_manager import RuntimeManager, get_runtime_manager
from core.approval_manager import ApprovalManager, ApprovalClass, ApprovalRecord
from core.event_logger import EventLogger, Event, EventType, EventSeverity
from core.job_dispatcher import JobDispatcher, get_job_dispatcher, DispatchedJob
from core.execution_backends import BackendType, JobStatus
from core.execution_plan import ExecutionPlan, ExecutionStatus
from core.agent_contracts import AgentRequest, RequestStatus

# Cost and persistence imports
from core.cost_tracker import CostTracker, get_cost_tracker
from core.budget_manager import BudgetManager, get_budget_manager
from core.cost_policies import CostPolicyEngine, get_cost_policy_engine
from core.persistence_manager import PersistenceManager, get_persistence_manager
from core.history_query import HistoryQuery, get_history_query


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class SystemStatus:
    """Overall system status."""
    healthy: bool = True
    runtime_initialized: bool = False
    active_jobs: int = 0
    pending_approvals: int = 0
    available_backends: List[str] = field(default_factory=list)
    total_events: int = 0
    recent_errors: int = 0
    persistence_enabled: bool = False
    total_cost_tracked: float = 0.0
    budget_utilization: float = 0.0
    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessSummary:
    """Summary of a business/initiative."""
    business_id: str
    name: str
    stage: str
    status: str = "active"
    created_at: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GoalSubmission:
    """A goal/request submission from operator."""
    objective: str
    business_id: Optional[str] = None
    stage: Optional[str] = None
    priority: str = "medium"
    notes: Optional[str] = None
    requester: str = "principal"


class OperatorService:
    """
    Central service for operator interface operations.

    Aggregates access to all backend modules.
    """

    def __init__(
        self,
        orchestrator: Optional[ChiefOrchestrator] = None,
        runtime_manager: Optional[RuntimeManager] = None,
        approval_manager: Optional[ApprovalManager] = None,
        event_logger: Optional[EventLogger] = None,
        job_dispatcher: Optional[JobDispatcher] = None,
        cost_tracker: Optional[CostTracker] = None,
        budget_manager: Optional[BudgetManager] = None,
        persistence_manager: Optional[PersistenceManager] = None,
        history_query: Optional[HistoryQuery] = None,
    ):
        """Initialize the operator service."""
        self._orchestrator = orchestrator
        self._runtime_manager = runtime_manager
        self._approval_manager = approval_manager
        self._event_logger = event_logger
        self._job_dispatcher = job_dispatcher
        self._cost_tracker = cost_tracker
        self._budget_manager = budget_manager
        self._persistence_manager = persistence_manager
        self._history_query = history_query

        # Lazy initialization flags
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialize components."""
        if self._initialized:
            return

        if self._orchestrator is None:
            self._orchestrator = ChiefOrchestrator()

        if self._runtime_manager is None:
            self._runtime_manager = get_runtime_manager()
            if not self._runtime_manager.is_initialized:
                self._runtime_manager.initialize()

        if self._approval_manager is None:
            self._approval_manager = self._orchestrator.approval

        if self._event_logger is None:
            self._event_logger = self._orchestrator.logger

        if self._job_dispatcher is None:
            self._job_dispatcher = get_job_dispatcher()

        if self._cost_tracker is None:
            self._cost_tracker = get_cost_tracker()

        if self._budget_manager is None:
            self._budget_manager = get_budget_manager()

        if self._persistence_manager is None:
            self._persistence_manager = get_persistence_manager()

        if self._history_query is None:
            self._history_query = get_history_query()

        self._initialized = True

    # -------------------------------------------------------------------------
    # System Status
    # -------------------------------------------------------------------------

    def get_system_status(self) -> SystemStatus:
        """Get overall system status."""
        self._ensure_initialized()

        # Count active jobs
        active_jobs = len(self._job_dispatcher.list_jobs(status=JobStatus.RUNNING))

        # Count pending approvals
        pending_approvals = len(self._approval_manager.get_pending())

        # Get available backends
        backends = []
        if self._runtime_manager and self._runtime_manager.is_initialized:
            backend_list = self._runtime_manager.list_available_backends()
            backends = [b["type"] for b in backend_list]

        # Count events and errors
        total_events = len(self._event_logger._events)
        recent_errors = len(self._event_logger.get_errors(limit=10))

        # Cost and persistence info
        persistence_enabled = False
        if self._persistence_manager:
            persistence_enabled = self._persistence_manager.is_persistence_enabled

        total_cost_tracked = 0.0
        budget_utilization = 0.0
        if self._cost_tracker:
            cost_stats = self._cost_tracker.get_stats()
            total_cost_tracked = cost_stats.get("total_estimated", 0.0)
        if self._budget_manager:
            budget_summary = self._budget_manager.get_summary()
            budget_utilization = budget_summary.get("global_utilization", 0.0)

        return SystemStatus(
            healthy=True,
            runtime_initialized=self._runtime_manager.is_initialized if self._runtime_manager else False,
            active_jobs=active_jobs,
            pending_approvals=pending_approvals,
            available_backends=backends,
            total_events=total_events,
            recent_errors=recent_errors,
            persistence_enabled=persistence_enabled,
            total_cost_tracked=total_cost_tracked,
            budget_utilization=budget_utilization,
        )

    def get_runtime_stats(self) -> Dict[str, Any]:
        """Get runtime statistics."""
        self._ensure_initialized()

        if self._runtime_manager:
            return self._runtime_manager.get_stats()
        return {"initialized": False}

    # -------------------------------------------------------------------------
    # Portfolio Management
    # -------------------------------------------------------------------------

    def get_portfolio(self) -> List[BusinessSummary]:
        """Get list of businesses/initiatives."""
        self._ensure_initialized()

        # Try to get from portfolio workflows if available
        try:
            from core.portfolio_workflows import PortfolioWorkflows
            portfolio = PortfolioWorkflows()
            businesses = portfolio.get_all_businesses()

            return [
                BusinessSummary(
                    business_id=b.get("id", "unknown"),
                    name=b.get("opportunity", {}).get("idea", "Unnamed"),
                    stage=b.get("stage", "DISCOVERED"),
                    status="active" if b.get("stage") != "TERMINATED" else "terminated",
                    created_at=b.get("created_at"),
                    metrics=b.get("metrics", {}),
                )
                for b in businesses
            ]
        except Exception:
            # Return empty portfolio if not available
            return []

    def get_business(self, business_id: str) -> Optional[BusinessSummary]:
        """Get a specific business."""
        portfolio = self.get_portfolio()
        for b in portfolio:
            if b.business_id == business_id:
                return b
        return None

    # -------------------------------------------------------------------------
    # Goal Submission
    # -------------------------------------------------------------------------

    def submit_goal(self, submission: GoalSubmission) -> OrchestrationResult:
        """
        Submit a new goal/request to the orchestrator.

        Returns the orchestration result.
        """
        self._ensure_initialized()

        # Build business context if provided
        business = None
        if submission.business_id:
            business = {
                "id": submission.business_id,
                "stage": submission.stage or "DISCOVERED",
            }

        # Build context from notes
        context = {}
        if submission.notes:
            context["operator_notes"] = submission.notes

        # Orchestrate the goal
        result = self._orchestrator.orchestrate(
            objective=submission.objective,
            business=business,
            context=context,
            requester=submission.requester,
            priority=submission.priority,
        )

        return result

    def get_orchestration_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent orchestration history."""
        self._ensure_initialized()

        history = self._orchestrator.get_history(limit=limit)
        return [r.to_dict() for r in history]

    # -------------------------------------------------------------------------
    # Execution Plans
    # -------------------------------------------------------------------------

    def get_execution_plan(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get execution plan for a request."""
        self._ensure_initialized()

        result = self._orchestrator.get_result(request_id)
        if result and result.execution_plan:
            return {
                "plan": result.execution_plan.to_dict(),
                "selected_skills": result.selected_skills,
                "selected_commands": result.selected_commands,
                "selected_agents": result.selected_agents,
                "backend_used": result.backend_used,
                "job_id": result.job_id,
                "approval_required": result.skill_approval_required,
                "policy_decisions": result.skill_policy_decisions,
            }
        return None

    def get_recent_plans(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution plans."""
        self._ensure_initialized()

        history = self._orchestrator.get_history(limit=limit)
        plans = []
        for r in history:
            if r.execution_plan:
                plans.append({
                    "request_id": r.request_id,
                    "plan_id": r.execution_plan.plan_id,
                    "objective": r.execution_plan.objective[:100],
                    "domain": r.execution_plan.primary_domain.value,
                    "status": r.execution_plan.status.value,
                    "step_count": len(r.execution_plan.steps),
                    "backend": r.backend_used,
                    "success": r.success,
                })
        return plans

    # -------------------------------------------------------------------------
    # Approval Queue
    # -------------------------------------------------------------------------

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get items requiring approval."""
        self._ensure_initialized()

        pending = self._approval_manager.get_pending()
        return [
            {
                "record_id": r.record_id,
                "request_id": r.request_id,
                "action": r.action,
                "requester": r.requester,
                "classification": r.classification.value,
                "reason": r.reason or r.rationale,
                "created_at": r.created_at,
                "context": r.context,
                "request_type": r.request_type or "action",
                "description": r.description or r.action,
                "priority": r.priority,
                "risk_level": r.risk_level,
                "connector_name": r.connector_name,
                "operation": r.operation,
                "plan_id": r.plan_id,
                "job_id": r.job_id,
            }
            for r in pending
        ]

    def get_approval_detail(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an approval item."""
        self._ensure_initialized()

        # Check pending first
        for r in self._approval_manager.get_pending():
            if r.record_id == record_id:
                return self._build_approval_detail(r)

        # Check history
        for r in self._approval_manager.get_history(limit=1000):
            if r.record_id == record_id:
                return self._build_approval_detail(r)

        return None

    def _build_approval_detail(self, r) -> Dict[str, Any]:
        """Build detailed approval record dictionary with defensive handling."""
        try:
            detail = {
                "record_id": safe_get(r, "record_id", "unknown"),
                "request_id": safe_get(r, "request_id", "unknown"),
                "policy_id": safe_get(r, "policy_id", "none"),
                "action": safe_get(r, "action", "unknown"),
                "requester": safe_get(r, "requester", "unknown"),
                "target_agent": safe_get(r, "target_agent", "unknown"),
                "classification": safe_enum_value(safe_get(r, "classification"), "standard"),
                "status": safe_enum_value(safe_get(r, "status"), "pending"),
                "reason": safe_get(r, "reason") or safe_get(r, "rationale", "No reason provided"),
                "rationale": safe_get(r, "rationale", ""),
                "created_at": safe_get(r, "created_at"),
                "decided_by": safe_get(r, "decided_by"),
                "decided_at": safe_get(r, "decided_at"),
                "resolved_at": safe_get(r, "resolved_at"),
                "request_type": safe_get(r, "request_type", "action"),
                "description": safe_get(r, "description") or safe_get(r, "action", "No description"),
                "priority": safe_get(r, "priority", "normal"),
                "risk_level": safe_get(r, "risk_level", "unknown"),
                "context": safe_dict(safe_get(r, "context")),
                "connector_name": safe_get(r, "connector_name"),
                "operation": safe_get(r, "operation"),
                "plan_id": safe_get(r, "plan_id"),
                "job_id": safe_get(r, "job_id"),
                "approved": safe_get(r, "approved", False),
                "approved_by": safe_get(r, "approved_by"),
            }

            # Add related plan/job info if available - with safe handling
            plan_id = safe_get(r, "plan_id")
            if plan_id:
                try:
                    request_id = safe_get(r, "request_id")
                    if request_id:
                        plan = self.get_execution_plan(request_id)
                        if plan:
                            detail["related_plan"] = {
                                "plan_id": plan_id,
                                "step_count": len(safe_dict(safe_dict(plan).get("plan", {})).get("steps", [])),
                                "selected_skills": safe_list(safe_dict(plan).get("selected_skills")),
                            }
                except Exception:
                    # Silently skip plan info if it can't be retrieved
                    detail["related_plan_error"] = True

            return detail

        except Exception as e:
            # Return minimal record on error
            return {
                "record_id": safe_get(r, "record_id", "unknown") if r else "error",
                "error": f"Error building approval detail: {str(e)}",
                "_error_detail": True,
            }

    def approve_request(
        self,
        record_id: str,
        approver: str = "principal",
        rationale: str = "",
        execute_after: bool = False,
        promote_to_live: bool = False,
    ) -> Dict[str, Any]:
        """
        Approve a pending request.

        Args:
            record_id: Approval record ID
            approver: Who is approving
            rationale: Reason for approval
            execute_after: Whether to trigger execution
            promote_to_live: Whether to promote to live mode

        Returns:
            Result dictionary with status and any execution result
        """
        self._ensure_initialized()

        record = self._approval_manager.approve(record_id, approver, rationale)
        if not record:
            return {"success": False, "error": "Approval record not found"}

        # Log the approval
        self._event_logger.log_approval(
            request_id=record.request_id,
            approved=True,
            approver=approver,
            reason=rationale or "Approved by operator",
        )

        result = {
            "success": True,
            "record_id": record_id,
            "approved": True,
            "approver": approver,
        }

        # Handle live mode promotion if requested
        if promote_to_live and record.connector_name and record.operation:
            try:
                from core.live_mode_controller import get_live_mode_controller
                lmc = get_live_mode_controller()
                promotion = lmc.promote_to_live(
                    connector=record.connector_name,
                    operation=record.operation,
                    promoted_by=approver,
                    approval_id=record_id,
                )
                if promotion:
                    result["live_mode_promoted"] = True
                    result["promotion_id"] = promotion.promotion_id
                else:
                    result["live_mode_promoted"] = False
                    result["promotion_error"] = "Gate check failed"
            except Exception as e:
                result["promotion_error"] = str(e)

        return result

    def deny_request(
        self,
        record_id: str,
        reason: str,
        denier: str = "principal",
    ) -> Dict[str, Any]:
        """
        Deny a pending request.

        Args:
            record_id: Approval record ID
            reason: Reason for denial
            denier: Who is denying

        Returns:
            Result dictionary
        """
        self._ensure_initialized()

        record = self._approval_manager.deny(record_id, denier, reason)
        if not record:
            return {"success": False, "error": "Approval record not found"}

        # Log the denial
        self._event_logger.log_approval(
            request_id=record.request_id,
            approved=False,
            approver=denier,
            reason=reason,
        )

        return {
            "success": True,
            "record_id": record_id,
            "denied": True,
            "denier": denier,
            "reason": reason,
        }

    def get_approval_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get approval history."""
        self._ensure_initialized()

        history = self._approval_manager.get_history(limit=limit)
        return [
            {
                "record_id": r.record_id,
                "request_id": r.request_id,
                "action": r.action,
                "classification": r.classification.value,
                "status": r.status.value,
                "approved": r.approved,
                "approved_by": r.approved_by,
                "created_at": r.created_at,
                "resolved_at": r.resolved_at,
                "request_type": r.request_type or "action",
                "description": r.description or r.action[:50] if r.action else "",
            }
            for r in history
        ]

    # -------------------------------------------------------------------------
    # Job Monitor
    # -------------------------------------------------------------------------

    def get_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get jobs with optional status filter."""
        self._ensure_initialized()

        job_status = None
        if status:
            try:
                job_status = JobStatus(status)
            except ValueError:
                pass

        jobs = self._job_dispatcher.list_jobs(status=job_status)[:limit]

        return [
            {
                "job_id": j.job_id,
                "plan_id": j.plan_id,
                "backend": j.backend_type.value,
                "status": j.status.value,
                "priority": j.options.priority.name if j.options else "NORMAL",
                "dispatched_at": j.dispatched_at.isoformat() if j.dispatched_at else None,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "worker_id": j.worker_instance_id,
                "retry_count": j.retry_count,
                "error": j.error,
                "is_complete": j.is_complete,
            }
            for j in jobs
        ]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific job."""
        self._ensure_initialized()

        job = self._job_dispatcher.get_job(job_id)
        if job:
            result_dict = None
            if job.result:
                result_dict = {
                    "status": job.result.status.value,
                    "total_steps": job.result.total_steps,
                    "completed_steps": job.result.completed_steps,
                    "failed_steps": job.result.failed_steps,
                    "duration": job.result.duration_seconds,
                }

            return {
                "job_id": job.job_id,
                "plan_id": job.plan_id,
                "backend": job.backend_type.value,
                "status": job.status.value,
                "dispatched_at": job.dispatched_at.isoformat() if job.dispatched_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "worker_id": job.worker_instance_id,
                "error": job.error,
                "result": result_dict,
            }
        return None

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running job."""
        self._ensure_initialized()

        job = self._job_dispatcher.get_job(job_id)
        if not job:
            return {"success": False, "error": "Job not found"}

        if job.is_complete:
            return {"success": False, "error": "Job already complete"}

        success = self._job_dispatcher.cancel_job(job_id)

        if success:
            self._event_logger.log_job_cancelled(
                request_id=job.plan_id,
                job_id=job_id,
                reason="Cancelled by operator",
            )

        return {"success": success, "job_id": job_id}

    def retry_job(self, job_id: str) -> Dict[str, Any]:
        """
        Retry a failed job.

        Note: Full retry requires plan storage. This logs the request
        and returns metadata for manual retry handling.
        """
        self._ensure_initialized()

        job = self._job_dispatcher.get_job(job_id)
        if not job:
            return {"success": False, "error": "Job not found"}

        if job.status != JobStatus.FAILED:
            return {"success": False, "error": f"Job not failed (status: {job.status.value})"}

        # Log retry request
        self._event_logger.log_job_retry_requested(
            request_id=job.plan_id,
            job_id=job_id,
            requested_by="principal",
            reason="Retry requested by operator",
        )

        # Return metadata for retry - actual retry requires re-submitting the plan
        return {
            "success": True,
            "job_id": job_id,
            "plan_id": job.plan_id,
            "retry_logged": True,
            "note": "Plan must be resubmitted for execution",
        }

    def get_job_detail(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed job information including safe execution context."""
        self._ensure_initialized()

        try:
            job = self._job_dispatcher.get_job(job_id)
            if not job:
                return None

            result_dict = None
            if job.result:
                result_dict = {
                    "status": safe_enum_value(job.result.status, "unknown"),
                    "total_steps": safe_get(job.result, "total_steps", 0),
                    "completed_steps": safe_get(job.result, "completed_steps", 0),
                    "failed_steps": safe_get(job.result, "failed_steps", 0),
                    "duration": safe_get(job.result, "duration_seconds", 0),
                }

            detail = {
                "job_id": safe_get(job, "job_id", job_id),
                "plan_id": safe_get(job, "plan_id", "unknown"),
                "backend": safe_enum_value(safe_get(job, "backend_type"), "unknown"),
                "status": safe_enum_value(safe_get(job, "status"), "unknown"),
                "dispatched_at": safe_isoformat(safe_get(job, "dispatched_at")),
                "started_at": safe_isoformat(safe_get(job, "started_at")),
                "completed_at": safe_isoformat(safe_get(job, "completed_at")),
                "worker_id": safe_get(job, "worker_instance_id"),
                "error": safe_get(job, "error"),
                "result": result_dict,
                "retry_count": safe_get(job, "retry_count", 0),
                "can_retry": safe_get(job, "status") == JobStatus.FAILED,
                "can_cancel": safe_get(job, "status") in (JobStatus.PENDING, JobStatus.RUNNING, JobStatus.QUEUED),
                "is_complete": safe_get(job, "is_complete", False),
            }

            # Add options if available
            options = safe_get(job, "options")
            if options:
                detail["options"] = {
                    "strategy": safe_enum_value(safe_get(options, "strategy"), "default"),
                    "priority": safe_get(safe_get(options, "priority"), "name", "NORMAL"),
                    "timeout_seconds": safe_get(options, "timeout_seconds", 3600),
                    "max_retries": safe_get(options, "max_retries", 3),
                    "stop_on_failure": safe_get(options, "stop_on_failure", True),
                    "parallel_steps": safe_get(options, "parallel_steps", False),
                }

            return detail

        except Exception as e:
            # Return error indicator instead of None to distinguish from "not found"
            return {
                "job_id": job_id,
                "error": f"Error retrieving job detail: {str(e)}",
                "status": "error",
                "_error_detail": True,
            }

    def get_job_stats(self) -> Dict[str, Any]:
        """Get job statistics."""
        self._ensure_initialized()

        return self._job_dispatcher.get_stats()

    # -------------------------------------------------------------------------
    # Event Log
    # -------------------------------------------------------------------------

    def get_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get events with optional filters."""
        self._ensure_initialized()

        type_filter = None
        if event_type:
            try:
                type_filter = EventType(event_type)
            except ValueError:
                pass

        severity_filter = None
        if severity:
            try:
                severity_filter = EventSeverity(severity)
            except ValueError:
                pass

        events = self._event_logger.get_events(
            event_type=type_filter,
            severity=severity_filter,
            limit=limit,
        )

        return [e.to_dict() for e in events]

    def get_recent_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent decision events."""
        self._ensure_initialized()

        decisions = self._event_logger.get_decisions(limit=limit)
        return [d.to_dict() for d in decisions]

    def get_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent error events."""
        self._ensure_initialized()

        errors = self._event_logger.get_errors(limit=limit)
        return [e.to_dict() for e in errors]

    def get_event_counts(self) -> Dict[str, int]:
        """Get event counts by type."""
        self._ensure_initialized()

        return self._event_logger.count_by_type()

    # -------------------------------------------------------------------------
    # Available Backends
    # -------------------------------------------------------------------------

    def get_backends(self) -> List[Dict[str, Any]]:
        """Get available execution backends."""
        self._ensure_initialized()

        if self._runtime_manager and self._runtime_manager.is_initialized:
            return self._runtime_manager.list_available_backends()
        return []


    # -------------------------------------------------------------------------
    # Integrations
    # -------------------------------------------------------------------------

    def get_integrations_summary(self) -> Dict[str, Any]:
        """Get integration layer summary."""
        try:
            from core.integration_skill import get_integration_skill
            skill = get_integration_skill()
            return skill.get_summary()
        except Exception as e:
            return {"error": str(e), "connectors": {}, "policies": {}}

    def get_connectors(self) -> List[Dict[str, Any]]:
        """Get all connectors with status."""
        try:
            from core.integration_skill import get_integration_skill
            skill = get_integration_skill()
            return skill.get_available_connectors()
        except Exception:
            return []

    def get_connector_detail(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed info for a connector."""
        try:
            from core.integration_skill import get_integration_skill
            skill = get_integration_skill()
            return skill.get_connector_status(name)
        except Exception:
            return None

    def connector_health_check(self, name: str) -> Dict[str, Any]:
        """Run health check on a connector."""
        try:
            from core.integration_skill import get_integration_skill
            skill = get_integration_skill()
            result = skill.health_check(name)
            return result.to_dict()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def connector_health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Run health check on all connectors."""
        try:
            from core.integration_skill import get_integration_skill
            skill = get_integration_skill()
            return skill.health_check_all()
        except Exception:
            return {}

    # -------------------------------------------------------------------------
    # Credentials
    # -------------------------------------------------------------------------

    def get_credentials_summary(self) -> Dict[str, Any]:
        """Get credentials health summary."""
        try:
            from core.secrets_manager import get_secrets_manager
            manager = get_secrets_manager()
            return manager.get_health_summary()
        except Exception as e:
            return {"error": str(e)}

    def get_credential_list(self) -> List[Dict[str, Any]]:
        """Get list of all credentials with safe metadata."""
        try:
            from core.secrets_manager import get_secrets_manager
            manager = get_secrets_manager()
            secrets = []
            for name in manager.list_secrets():
                meta = manager.get_metadata(name)
                if meta:
                    secrets.append(meta.to_safe_dict())
            return secrets
        except Exception:
            return []

    def get_rotation_summary(self) -> Dict[str, Any]:
        """Get credential rotation summary."""
        try:
            from core.rotation_manager import get_rotation_manager
            manager = get_rotation_manager()
            return manager.get_summary()
        except Exception as e:
            return {"error": str(e)}

    def get_rotation_schedules(self) -> List[Dict[str, Any]]:
        """Get all rotation schedules."""
        try:
            from core.rotation_manager import get_rotation_manager
            manager = get_rotation_manager()
            return manager.get_all_schedules()
        except Exception:
            return []

    # -------------------------------------------------------------------------
    # Live Mode Control
    # -------------------------------------------------------------------------

    def get_live_mode_summary(self) -> Dict[str, Any]:
        """Get live mode controller summary."""
        try:
            from core.live_mode_controller import get_live_mode_controller
            controller = get_live_mode_controller()
            return controller.get_summary()
        except Exception as e:
            return {"error": str(e)}

    def check_live_mode_gate(
        self,
        connector: str,
        operation: str,
    ) -> Dict[str, Any]:
        """Check if an operation can be promoted to live mode."""
        try:
            from core.live_mode_controller import get_live_mode_controller
            controller = get_live_mode_controller()
            result = controller.check_live_mode_gate(
                connector=connector,
                operation=operation,
            )
            return result.to_dict()
        except Exception as e:
            return {"allowed": False, "error": str(e)}

    def promote_to_live(
        self,
        connector: str,
        operation: str,
        approval_id: Optional[str] = None,
        promoted_by: str = "principal",
    ) -> Dict[str, Any]:
        """
        Promote an operation to live mode.

        Requires policy and credential checks to pass.
        """
        try:
            from core.live_mode_controller import get_live_mode_controller
            controller = get_live_mode_controller()

            # Log the request
            self._event_logger.log_live_mode_promotion_requested(
                connector=connector,
                operation=operation,
                requested_by=promoted_by,
            )

            promotion = controller.promote_to_live(
                connector=connector,
                operation=operation,
                promoted_by=promoted_by,
                approval_id=approval_id,
            )

            if promotion:
                return {
                    "success": True,
                    "promotion_id": promotion.promotion_id,
                    "connector": connector,
                    "operation": operation,
                    "promoted_by": promoted_by,
                }
            else:
                return {
                    "success": False,
                    "connector": connector,
                    "operation": operation,
                    "error": "Gate check failed",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_active_promotions(self) -> List[Dict[str, Any]]:
        """Get list of active live mode promotions."""
        try:
            from core.live_mode_controller import get_live_mode_controller
            controller = get_live_mode_controller()
            promotions = controller.get_active_promotions()
            return [p.to_dict() for p in promotions]
        except Exception:
            return []

    def get_standing_approvals(self) -> Dict[str, str]:
        """Get all standing operation approvals."""
        try:
            from core.live_mode_controller import get_live_mode_controller
            controller = get_live_mode_controller()
            return controller.get_standing_approvals()
        except Exception:
            return {}

    # -------------------------------------------------------------------------
    # Plan Detail (Enhanced)
    # -------------------------------------------------------------------------

    def get_plan_detail(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed execution plan with all context."""
        self._ensure_initialized()

        result = self._orchestrator.get_result(request_id)
        if not result or not result.execution_plan:
            return None

        plan = result.execution_plan

        return {
            "request_id": request_id,
            "plan_id": plan.plan_id,
            "objective": plan.objective,
            "domain": plan.primary_domain.value,
            "status": plan.status.value,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,

            # Step information
            "step_count": len(plan.steps),
            "steps": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "description": s.description,
                    "domain": s.domain.value,
                    "status": s.status.value,
                }
                for s in plan.steps
            ],

            # Skill/agent selection
            "selected_skills": result.selected_skills,
            "selected_commands": result.selected_commands,
            "selected_agents": result.selected_agents,

            # Execution context
            "backend_used": result.backend_used,
            "job_id": result.job_id,

            # Approval status
            "approval_required": result.skill_approval_required,
            "policy_decisions": result.skill_policy_decisions,

            # Mode information
            "dry_run_mode": True,  # Default safe
            "live_execution_available": False,

            # Result
            "success": result.success,
            "error": result.error,
        }

    # -------------------------------------------------------------------------
    # Cost Governance
    # -------------------------------------------------------------------------

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary."""
        self._ensure_initialized()

        if self._cost_tracker:
            return self._cost_tracker.get_stats()
        return {"error": "Cost tracker not available"}

    def get_budget_summary(self) -> Dict[str, Any]:
        """Get budget status summary."""
        self._ensure_initialized()

        if self._budget_manager:
            return self._budget_manager.get_summary()
        return {"error": "Budget manager not available"}

    def get_budget_status(self, scope: str = "global", scope_id: Optional[str] = None) -> Dict[str, Any]:
        """Get budget status for a specific scope."""
        self._ensure_initialized()

        if self._budget_manager:
            return self._budget_manager.get_budget_status(scope, scope_id)
        return {"error": "Budget manager not available"}

    def get_cost_records(
        self,
        record_type: Optional[str] = None,
        connector: Optional[str] = None,
        business_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get cost records with optional filters."""
        self._ensure_initialized()

        if self._cost_tracker:
            costs = self._cost_tracker.get_costs(
                record_type=record_type,
                connector=connector,
                business_id=business_id,
                limit=limit,
            )
            return [c.to_dict() for c in costs]
        return []

    def get_cost_by_connector(self) -> Dict[str, float]:
        """Get cost aggregated by connector."""
        self._ensure_initialized()

        if self._history_query:
            aggregated = self._history_query.get_aggregated_costs()
            return aggregated.by_connector
        return {}

    def get_cost_by_business(self) -> Dict[str, float]:
        """Get cost aggregated by business."""
        self._ensure_initialized()

        if self._history_query:
            aggregated = self._history_query.get_aggregated_costs()
            return aggregated.by_business
        return {}

    def get_business_cost_detail(self, business_id: str) -> Dict[str, Any]:
        """Get detailed cost information for a business."""
        self._ensure_initialized()

        if self._history_query:
            return self._history_query.get_business_costs(business_id)
        return {"error": "History query not available"}

    def get_cost_policies(self) -> List[Dict[str, Any]]:
        """Get all cost policy rules."""
        try:
            engine = get_cost_policy_engine()
            rules = engine.get_rules()
            return [r.to_dict() for r in rules]
        except Exception as e:
            return [{"error": str(e)}]

    # -------------------------------------------------------------------------
    # Persistence & History
    # -------------------------------------------------------------------------

    def get_persistence_stats(self) -> Dict[str, Any]:
        """Get persistence manager statistics."""
        self._ensure_initialized()

        if self._persistence_manager:
            return self._persistence_manager.get_stats()
        return {"error": "Persistence manager not available"}

    def get_history_summary(self) -> Dict[str, Any]:
        """Get history query summary."""
        self._ensure_initialized()

        if self._history_query:
            summary = self._history_query.get_summary()
            return summary.to_dict()
        return {"error": "History query not available"}

    def get_approval_history_persisted(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get persisted approval history."""
        self._ensure_initialized()

        if self._persistence_manager:
            return self._persistence_manager.get_persisted_approvals(status=status, limit=limit)
        return []

    def get_job_history_persisted(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get persisted job history."""
        self._ensure_initialized()

        if self._persistence_manager:
            return self._persistence_manager.get_persisted_jobs(status=status, limit=limit)
        return []

    def get_plan_history_persisted(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get persisted execution plan history."""
        self._ensure_initialized()

        if self._persistence_manager:
            return self._persistence_manager.get_persisted_plans(limit=limit)
        return []

    def get_event_history_persisted(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get persisted event history."""
        self._ensure_initialized()

        if self._persistence_manager:
            return self._persistence_manager.get_persisted_events(
                event_type=event_type,
                severity=severity,
                limit=limit,
            )
        return []

    def get_cost_history_persisted(
        self,
        record_type: Optional[str] = None,
        connector: Optional[str] = None,
        business_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get persisted cost record history."""
        self._ensure_initialized()

        if self._persistence_manager:
            return self._persistence_manager.get_persisted_cost_records(
                record_type=record_type,
                connector=connector,
                business_id=business_id,
                limit=limit,
            )
        return []

    def get_budget_snapshots(
        self,
        scope: Optional[str] = None,
        scope_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get budget snapshots over time."""
        self._ensure_initialized()

        if self._persistence_manager:
            return self._persistence_manager.get_persisted_budget_snapshots(
                scope=scope,
                scope_id=scope_id,
                limit=limit,
            )
        return []

    def get_domain_summary(self) -> Dict[str, Any]:
        """
        Get execution domain summary.

        Returns domain metadata and classification capabilities.
        """
        try:
            from core.execution_domains import get_domain_summary
            return get_domain_summary()
        except ImportError:
            return {
                "total_domains": 0,
                "domains": [],
                "error": "Domain module not available"
            }

    # =========================================================================
    # DISCOVERY OPERATIONS
    # =========================================================================

    def process_discovery_input(
        self,
        raw_text: str,
        tags: Optional[List[str]] = None,
        submitted_by: str = "principal",
    ) -> List[Dict[str, Any]]:
        """
        Process discovery input and create opportunity records.

        Args:
            raw_text: Raw idea/problem/opportunity text
            tags: Optional tags
            submitted_by: Who submitted

        Returns:
            List of opportunity record dicts
        """
        from core.discovery_pipeline import process_discovery_input
        from core.discovery_models import OperatorConstraints
        from core.opportunity_registry import OpportunityRegistry
        from core.state_store import get_state_store

        # Use default constraints (could be customized per operator)
        constraints = OperatorConstraints()

        # Process through pipeline
        opportunity_records = process_discovery_input(
            raw_text=raw_text,
            constraints=constraints,
            submitted_by=submitted_by,
            tags=tags,
        )

        # Save to registry
        state_store = get_state_store()
        if not state_store.is_initialized:
            state_store.initialize()

        registry = OpportunityRegistry(state_store)

        result_dicts = []
        for record in opportunity_records:
            registry.save_opportunity(record)
            result_dicts.append(record.to_dict())

        return result_dicts

    def get_opportunities(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get opportunities with optional filtering.

        Args:
            status: Optional status filter
            limit: Maximum records

        Returns:
            List of opportunity dicts
        """
        from core.opportunity_registry import OpportunityRegistry
        from core.discovery_models import OpportunityStatus
        from core.state_store import get_state_store

        state_store = get_state_store()
        if not state_store.is_initialized:
            state_store.initialize()

        registry = OpportunityRegistry(state_store)

        status_enum = OpportunityStatus(status) if status else None
        opportunities = registry.list_opportunities(status=status_enum, limit=limit)

        return [opp.to_dict() for opp in opportunities]

    def get_opportunity(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get single opportunity by ID.

        Args:
            opportunity_id: Opportunity ID

        Returns:
            Opportunity dict or None
        """
        from core.opportunity_registry import OpportunityRegistry
        from core.state_store import get_state_store

        state_store = get_state_store()
        if not state_store.is_initialized:
            state_store.initialize()

        registry = OpportunityRegistry(state_store)
        opportunity = registry.get_opportunity(opportunity_id)

        return opportunity.to_dict() if opportunity else None

    def update_opportunity_status(
        self,
        opportunity_id: str,
        new_status: str,
        note: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Update opportunity status.

        Args:
            opportunity_id: Opportunity ID
            new_status: New status value
            note: Optional note

        Returns:
            Updated opportunity dict or None
        """
        from core.opportunity_registry import OpportunityRegistry
        from core.discovery_models import OpportunityStatus
        from core.state_store import get_state_store

        state_store = get_state_store()
        if not state_store.is_initialized:
            state_store.initialize()

        registry = OpportunityRegistry(state_store)
        status_enum = OpportunityStatus(new_status)

        opportunity = registry.update_status(
            opportunity_id=opportunity_id,
            new_status=status_enum,
            note=note,
        )

        return opportunity.to_dict() if opportunity else None

    def get_opportunity_stats(self) -> Dict[str, Any]:
        """
        Get opportunity summary statistics.

        Returns:
            Stats dict
        """
        from core.opportunity_registry import OpportunityRegistry
        from core.state_store import get_state_store

        state_store = get_state_store()
        if not state_store.is_initialized:
            state_store.initialize()

        registry = OpportunityRegistry(state_store)
        return registry.get_summary_stats()

    # =========================================================================
    # HANDOFF OPERATIONS
    # =========================================================================

    def create_handoff_from_opportunity(
        self,
        opportunity_id: str,
        mode: str,
        created_by: str = "principal",
    ) -> Optional[Dict[str, Any]]:
        """
        Create handoff from opportunity for execution.

        Args:
            opportunity_id: Opportunity ID
            mode: Handoff mode (pursue_now, validate_first, archive)
            created_by: Who initiated handoff

        Returns:
            Handoff dict with plan info or None
        """
        from core.opportunity_registry import OpportunityRegistry
        from core.opportunity_handoff import create_handoff, HandoffMode
        from core.opportunity_execution_mapper import map_to_execution_plan
        from core.state_store import get_state_store

        state_store = get_state_store()
        if not state_store.is_initialized:
            state_store.initialize()

        # Get opportunity
        registry = OpportunityRegistry(state_store)
        opportunity = registry.get_opportunity(opportunity_id)
        if not opportunity:
            return None

        # Parse mode
        try:
            mode_enum = HandoffMode(mode)
        except ValueError:
            return None

        # Create handoff record
        handoff = create_handoff(opportunity, mode_enum, created_by)

        # For pursue/validate modes, create execution plan
        plan = None
        if mode_enum in (HandoffMode.PURSUE_NOW, HandoffMode.VALIDATE_FIRST):
            plan = map_to_execution_plan(handoff)
            handoff.plan_id = plan.plan_id
            handoff.business_id = plan.business_id

        # Save handoff
        state_store.save_handoff(
            handoff_id=handoff.handoff_id,
            opportunity_id=handoff.opportunity_id,
            mode=handoff.mode.value,
            status=handoff.status.value,
            context_data=handoff.handoff_context.to_dict(),
            plan_id=handoff.plan_id,
            business_id=handoff.business_id,
            created_by=created_by,
        )

        # Update opportunity status
        if mode_enum == HandoffMode.PURSUE_NOW:
            registry.update_status(opportunity_id, "pursue", f"Handoff created: {handoff.handoff_id}")
        elif mode_enum == HandoffMode.VALIDATE_FIRST:
            registry.update_status(opportunity_id, "validate", f"Handoff created: {handoff.handoff_id}")
        elif mode_enum == HandoffMode.ARCHIVE:
            registry.update_status(opportunity_id, "archived", f"Archived via handoff: {handoff.handoff_id}")

        result = {
            "handoff_id": handoff.handoff_id,
            "opportunity_id": handoff.opportunity_id,
            "mode": handoff.mode.value,
            "status": handoff.status.value,
            "plan_id": handoff.plan_id,
            "business_id": handoff.business_id,
        }

        if plan:
            result["plan"] = {
                "plan_id": plan.plan_id,
                "objective": plan.objective,
                "stage": plan.stage,
                "primary_domain": plan.primary_domain.value,
                "step_count": len(plan.steps),
                "projected_capital": plan.projected_capital,
            }

        return result

    def get_handoff(self, handoff_id: str) -> Optional[Dict[str, Any]]:
        """
        Get handoff by ID.

        Args:
            handoff_id: Handoff ID

        Returns:
            Handoff dict or None
        """
        from core.state_store import get_state_store

        state_store = get_state_store()
        if not state_store.is_initialized:
            state_store.initialize()

        return state_store.get_handoff(handoff_id)

    def get_handoffs_for_opportunity(
        self,
        opportunity_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all handoffs for an opportunity.

        Args:
            opportunity_id: Opportunity ID

        Returns:
            List of handoff dicts
        """
        from core.state_store import get_state_store

        state_store = get_state_store()
        if not state_store.is_initialized:
            state_store.initialize()

        return state_store.get_handoffs_by_opportunity(opportunity_id)
    # =========================================================================
    # Capacity Management Methods
    # =========================================================================

    def get_capacity_status(self) -> Dict[str, Any]:
        """
        Get current capacity status across all dimensions.

        Returns:
            Capacity status dictionary with utilization and warnings
        """
        try:
            from core.capacity_manager import CapacityManager, CapacityDimension
            from core.capacity_policies import CapacityPolicies

            # Initialize capacity manager with state store
            policies = CapacityPolicies()
            capacity_manager = CapacityManager(
                capacity_policies=policies,
                state_store=self.state_store,
                budget_manager=self.budget_manager
            )

            # Load persisted limits from state store
            persisted_limits = self.state_store.list_capacity_limits()
            for limit_data in persisted_limits:
                dimension_str = limit_data.get("dimension")
                try:
                    dimension = CapacityDimension(dimension_str)
                    capacity_manager.set_limit(
                        dimension=dimension,
                        soft_limit=limit_data.get("soft_limit"),
                        hard_limit=limit_data.get("hard_limit"),
                        enabled=bool(limit_data.get("enabled", 1)),
                        description=limit_data.get("description", "")
                    )
                except ValueError:
                    pass

            return capacity_manager.get_capacity_status()

        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def get_capacity_policy_summary(self) -> Dict[str, Any]:
        """Get summary of capacity policies."""
        try:
            from core.capacity_policies import CapacityPolicies
            policies = CapacityPolicies()
            return policies.get_policy_summary()
        except Exception as e:
            return {"error": str(e)}

    def get_capacity_decisions(
        self,
        dimension: Optional[str] = None,
        decision: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent capacity decisions (audit trail).

        Args:
            dimension: Filter by dimension
            decision: Filter by decision type (allowed, warning, requires_approval, blocked)
            limit: Maximum number of decisions to return

        Returns:
            List of capacity decisions
        """
        try:
            return self.state_store.list_capacity_decisions(
                dimension=dimension,
                decision=decision,
                limit=limit
            )
        except Exception as e:
            return []

    def set_capacity_limit(
        self,
        dimension: str,
        soft_limit: Optional[int],
        hard_limit: Optional[int],
        enabled: bool = True,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Set or update capacity limit for a dimension.

        Args:
            dimension: Capacity dimension (businesses, opportunities, jobs, etc.)
            soft_limit: Warning threshold (None = unlimited)
            hard_limit: Blocking threshold (None = unlimited)
            enabled: Whether limit is enforced
            description: Human-readable description

        Returns:
            Result dictionary
        """
        try:
            limit_config = {
                "soft_limit": soft_limit,
                "hard_limit": hard_limit,
                "enabled": enabled,
                "description": description
            }

            success = self.state_store.save_capacity_limit(dimension, limit_config)

            return {
                "success": success,
                "dimension": dimension,
                "limit_config": limit_config
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # =========================================================================
    # SCENARIO OPERATIONS
    # =========================================================================

    def list_scenarios(
        self,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List available scenarios.

        Args:
            category: Optional category filter

        Returns:
            List of scenario definition dicts
        """
        from core.scenario_runner import get_scenario_runner
        runner = get_scenario_runner()
        return runner.list_scenarios(category=category)

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """
        Get scenario definition by ID.

        Args:
            scenario_id: Scenario ID

        Returns:
            Scenario definition dict or None
        """
        from core.scenario_runner import get_scenario_runner
        runner = get_scenario_runner()
        return runner.get_scenario(scenario_id)

    def get_scenario_summary(self) -> Dict[str, Any]:
        """
        Get summary of available scenarios.

        Returns:
            Summary dict with counts and categories
        """
        from core.scenario_runner import get_scenario_runner
        runner = get_scenario_runner()
        return runner.get_scenario_summary()

    def run_scenario(
        self,
        scenario_id: str,
        inputs: Dict[str, Any],
        dry_run: bool = True,
        triggered_by: str = "operator",
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a scenario.

        Args:
            scenario_id: Scenario ID to run
            inputs: Input values for scenario
            dry_run: If True, use dry-run mode for connectors
            triggered_by: Who triggered the run
            auto_approve: If True, auto-approve required approvals

        Returns:
            Scenario run dict with results
        """
        from core.scenario_runner import get_scenario_runner
        runner = get_scenario_runner()

        run = runner.run_scenario(
            scenario_id=scenario_id,
            inputs=inputs,
            dry_run=dry_run,
            triggered_by=triggered_by,
            auto_approve=auto_approve,
        )

        return run.to_dict()

    def get_scenario_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get scenario run by ID.

        Args:
            run_id: Scenario run ID

        Returns:
            Scenario run dict or None
        """
        from core.scenario_runner import get_scenario_runner
        runner = get_scenario_runner()
        return runner.get_run(run_id)

    def list_scenario_runs(
        self,
        scenario_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        List scenario runs with optional filtering.

        Args:
            scenario_id: Filter by scenario ID
            status: Filter by status
            limit: Maximum runs to return

        Returns:
            List of scenario run dicts
        """
        from core.scenario_runner import get_scenario_runner
        runner = get_scenario_runner()
        return runner.list_runs(
            scenario_id=scenario_id,
            status=status,
            limit=limit,
        )

    def get_scenario_run_stats(self) -> Dict[str, Any]:
        """
        Get scenario run statistics.

        Returns:
            Stats dict with totals and breakdowns
        """
        from core.scenario_runner import get_scenario_runner
        runner = get_scenario_runner()
        return runner.get_run_stats()

    # =========================================================================
    # RECOVERY & WORKFLOW CONTROL OPERATIONS
    # =========================================================================

    def get_operator_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive operator dashboard data.

        Returns all actionable items: pending approvals, paused scenarios,
        failed jobs, active blockers, and recent actions.
        """
        from core.operator_actions import get_operator_actions
        actions = get_operator_actions()
        return actions.get_operator_dashboard()

    def get_paused_scenarios(self) -> List[Dict[str, Any]]:
        """
        Get all scenarios that are paused/awaiting action.

        Returns scenarios with status awaiting_approval or partial,
        including their blockers and available actions.
        """
        from core.recovery_manager import get_recovery_manager
        manager = get_recovery_manager()
        return manager.get_paused_scenarios()

    def get_failed_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all failed jobs that can be retried.

        Returns jobs with status failed, including blockers
        and available retry/rerun actions.
        """
        from core.recovery_manager import get_recovery_manager
        manager = get_recovery_manager()
        return manager.get_failed_jobs()

    def get_active_blockers(
        self,
        scenario_run_id: Optional[str] = None,
        job_id: Optional[str] = None,
        blocker_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get active blockers with optional filters.

        Args:
            scenario_run_id: Filter by scenario run
            job_id: Filter by job
            blocker_type: Filter by blocker type

        Returns:
            List of active blocker dicts
        """
        from core.recovery_manager import get_recovery_manager, BlockerType
        manager = get_recovery_manager()

        type_enum = None
        if blocker_type:
            try:
                type_enum = BlockerType(blocker_type)
            except ValueError:
                pass

        blockers = manager.get_active_blockers(
            scenario_run_id=scenario_run_id,
            job_id=job_id,
            blocker_type=type_enum,
        )
        return [b.to_dict() for b in blockers]

    def get_workflow_status(
        self,
        scenario_run_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive workflow status for a scenario or job.

        Args:
            scenario_run_id: Scenario run to inspect
            job_id: Job to inspect

        Returns:
            Status dict with blockers, available actions, and history
        """
        from core.recovery_manager import get_recovery_manager
        manager = get_recovery_manager()
        return manager.get_workflow_status(
            scenario_run_id=scenario_run_id,
            job_id=job_id,
        )

    def resume_scenario(
        self,
        run_id: str,
        resumed_by: str = "operator",
        skip_failed: bool = False,
    ) -> Dict[str, Any]:
        """
        Resume a paused scenario.

        Args:
            run_id: ID of the scenario run to resume
            resumed_by: Who is resuming
            skip_failed: If True, skip failed steps and continue

        Returns:
            Result dict with outcome and new run ID if created
        """
        from core.operator_actions import get_operator_actions
        actions = get_operator_actions()
        result = actions.resume_scenario(
            run_id=run_id,
            performed_by=resumed_by,
            skip_failed=skip_failed,
        )
        return result.to_dict()

    def resume_after_approval(
        self,
        approval_id: str,
        resumed_by: str = "operator",
    ) -> Dict[str, Any]:
        """
        Resume workflow after an approval has been granted.

        This automatically finds and resumes any workflows
        that were waiting for this approval.

        Args:
            approval_id: ID of the approval that was granted
            resumed_by: Who granted the approval

        Returns:
            Result dict with outcome
        """
        from core.recovery_manager import get_recovery_manager
        manager = get_recovery_manager()
        result = manager.resume_after_approval(
            approval_id=approval_id,
            resumed_by=resumed_by,
        )
        return result.to_dict()

    def retry_failed_job(
        self,
        job_id: str,
        retried_by: str = "operator",
    ) -> Dict[str, Any]:
        """
        Retry a failed job.

        Creates a new job execution for the same plan.

        Args:
            job_id: ID of the job to retry
            retried_by: Who is retrying

        Returns:
            Result dict with outcome and new job ID if created
        """
        from core.operator_actions import get_operator_actions
        actions = get_operator_actions()
        result = actions.retry_job(
            job_id=job_id,
            performed_by=retried_by,
        )
        return result.to_dict()

    def retry_connector_action(
        self,
        execution_id: str,
        retried_by: str = "operator",
    ) -> Dict[str, Any]:
        """
        Retry a failed connector action.

        Args:
            execution_id: ID of the connector execution to retry
            retried_by: Who is retrying

        Returns:
            Result dict with outcome
        """
        from core.operator_actions import get_operator_actions
        actions = get_operator_actions()
        result = actions.retry_connector_action(
            execution_id=execution_id,
            performed_by=retried_by,
        )
        return result.to_dict()

    def retry_scenario_step(
        self,
        run_id: str,
        step_id: str,
        retried_by: str = "operator",
    ) -> Dict[str, Any]:
        """
        Retry a failed scenario step.

        Args:
            run_id: ID of the scenario run
            step_id: ID of the step to retry
            retried_by: Who is retrying

        Returns:
            Result dict with outcome and new run ID if created
        """
        from core.operator_actions import get_operator_actions
        actions = get_operator_actions()
        result = actions.retry_scenario_step(
            run_id=run_id,
            step_id=step_id,
            performed_by=retried_by,
        )
        return result.to_dict()

    def rerun_execution_plan(
        self,
        plan_id: str,
        triggered_by: str = "operator",
        dry_run: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Rerun a previously created execution plan.

        Creates a new plan and job, preserving audit trail.

        Args:
            plan_id: ID of the plan to rerun
            triggered_by: Who triggered the rerun
            dry_run: Override dry_run setting

        Returns:
            Result dict with outcome and new job ID
        """
        from core.operator_actions import get_operator_actions
        actions = get_operator_actions()
        result = actions.rerun_plan(
            plan_id=plan_id,
            performed_by=triggered_by,
            dry_run=dry_run,
        )
        return result.to_dict()

    def rerun_scenario(
        self,
        run_id: str,
        triggered_by: str = "operator",
        dry_run: Optional[bool] = None,
        new_inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Rerun a scenario with the same or modified inputs.

        Args:
            run_id: ID of the scenario run to base rerun on
            triggered_by: Who triggered the rerun
            dry_run: Override dry_run setting
            new_inputs: Optional modified inputs

        Returns:
            Result dict with outcome and new run ID
        """
        from core.operator_actions import get_operator_actions
        actions = get_operator_actions()
        result = actions.rerun_scenario(
            run_id=run_id,
            performed_by=triggered_by,
            dry_run=dry_run,
            new_inputs=new_inputs,
        )
        return result.to_dict()

    def skip_scenario_step(
        self,
        run_id: str,
        step_id: str,
        skipped_by: str = "operator",
        reason: str = "",
    ) -> Dict[str, Any]:
        """
        Skip a blocked/failed step and continue the scenario.

        Args:
            run_id: ID of the scenario run
            step_id: ID of the step to skip
            skipped_by: Who is skipping
            reason: Reason for skipping

        Returns:
            Result dict with outcome and new run ID
        """
        from core.operator_actions import get_operator_actions
        actions = get_operator_actions()
        result = actions.skip_step(
            run_id=run_id,
            step_id=step_id,
            performed_by=skipped_by,
            reason=reason,
        )
        return result.to_dict()

    def cancel_scenario_run(
        self,
        run_id: str,
        cancelled_by: str = "operator",
        reason: str = "",
    ) -> Dict[str, Any]:
        """
        Cancel a running scenario.

        Args:
            run_id: ID of the scenario run to cancel
            cancelled_by: Who is cancelling
            reason: Reason for cancellation

        Returns:
            Result dict with outcome
        """
        from core.operator_actions import get_operator_actions
        actions = get_operator_actions()
        result = actions.cancel_scenario(
            run_id=run_id,
            performed_by=cancelled_by,
            reason=reason,
        )
        return result.to_dict()

    def approve_with_resume(
        self,
        approval_id: str,
        approver: str = "operator",
        rationale: str = "",
        auto_resume: bool = True,
    ) -> Dict[str, Any]:
        """
        Approve a request and optionally auto-resume blocked workflows.

        Args:
            approval_id: ID of the approval to grant
            approver: Who is approving
            rationale: Reason for approval
            auto_resume: If True, automatically resume blocked workflows

        Returns:
            Result dict with approval and resume outcomes
        """
        from core.operator_actions import get_operator_actions
        actions = get_operator_actions()
        result = actions.approve(
            approval_id=approval_id,
            rationale=rationale,
            performed_by=approver,
            auto_resume=auto_resume,
        )
        return result.to_dict()

    def get_recovery_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent recovery operation history.

        Args:
            limit: Maximum records to return

        Returns:
            List of recovery operation results
        """
        from core.recovery_manager import get_recovery_manager
        manager = get_recovery_manager()
        return manager.get_recovery_history(limit=limit)

    def get_operator_action_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent operator action history.

        Args:
            limit: Maximum records to return

        Returns:
            List of operator action results
        """
        from core.operator_actions import get_operator_actions
        actions = get_operator_actions()
        return actions.get_action_history(limit=limit)

    # -------------------------------------------------------------------------
    # Connector Action History
    # -------------------------------------------------------------------------

    def get_connector_actions(
        self,
        connector: Optional[str] = None,
        mode: Optional[str] = None,
        status: Optional[str] = None,
        related_id: Optional[str] = None,
        limit: int = 100,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Get connector action execution history with statistics."""
        self._ensure_initialized()

        from core.connector_action_history import get_connector_action_history, ConnectorActionFilter
        history = get_connector_action_history()

        success_filter = None
        if status == "success":
            success_filter = True
        elif status == "failed":
            success_filter = False

        filter_criteria = ConnectorActionFilter(
            connector=connector,
            mode=mode,
            success=success_filter,
            job_id=related_id,
            plan_id=related_id,
            opportunity_id=related_id,
            limit=limit,
        )

        actions = history.query_actions(filter_criteria)
        stats = history.get_connector_stats(connector=connector)
        return actions, stats

    def get_connector_action_detail(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a connector action execution."""
        self._ensure_initialized()
        from core.connector_action_history import get_connector_action_history
        history = get_connector_action_history()
        return history.get_action_by_id(execution_id)

    def get_unique_connectors(self) -> List[str]:
        """Get list of unique connectors that have been executed."""
        self._ensure_initialized()
        from core.connector_action_history import get_connector_action_history
        history = get_connector_action_history()
        actions = history.get_recent_actions(limit=1000)
        connectors = set()
        for action in actions:
            connector_name = safe_get(action, "connector_name")
            if connector_name:
                connectors.add(connector_name)
        return sorted(list(connectors))

    # -------------------------------------------------------------------------
    # Readiness & Health
    # -------------------------------------------------------------------------

    def get_readiness_report(self) -> Dict[str, Any]:
        """Get full system readiness report."""
        from core.readiness_checker import get_readiness_checker
        checker = get_readiness_checker()
        report = checker.check_all()
        return report.to_dict()

    def get_readiness_quick(self) -> Dict[str, Any]:
        """Get quick readiness status."""
        from core.readiness_checker import get_readiness_checker
        checker = get_readiness_checker()
        return checker.check_quick()

    def get_health_report(self) -> Dict[str, Any]:
        """Get full system health report."""
        from core.health_monitor import get_health_monitor
        monitor = get_health_monitor()
        health = monitor.check_all()
        return health.to_dict()

    def get_health_quick(self) -> Dict[str, Any]:
        """Get quick health status."""
        from core.health_monitor import get_health_monitor
        monitor = get_health_monitor()
        return monitor.check_quick()

    def get_setup_checklist(self) -> Dict[str, Any]:
        """Get first-use setup checklist."""
        from core.startup_manager import get_startup_manager
        manager = get_startup_manager()
        checklist = manager.get_setup_checklist()
        return checklist.to_dict()

    def get_startup_instructions(self) -> List[str]:
        """Get operator startup instructions."""
        from core.startup_manager import get_startup_manager
        manager = get_startup_manager()
        return manager.get_startup_instructions()

    def run_startup(self, skip_health_check: bool = False) -> Dict[str, Any]:
        """Run system startup sequence."""
        from core.startup_manager import get_startup_manager
        manager = get_startup_manager()
        result = manager.startup(skip_health_check=skip_health_check)
        return result.to_dict()

    def get_connector_readiness(self) -> List[Dict[str, Any]]:
        """Get readiness status for all connectors."""
        from core.readiness_checker import get_readiness_checker
        checker = get_readiness_checker()
        report = checker.check_all()
        return [c.to_dict() for c in report.connectors]

    def get_combined_status(self) -> Dict[str, Any]:
        """Get combined readiness and health status."""
        readiness = self.get_readiness_quick()
        health = self.get_health_quick()
        return {
            "ready": readiness.get("ready", False),
            "readiness_status": readiness.get("status", "unknown"),
            "dry_run_ready": readiness.get("dry_run_ready", False),
            "live_ready": readiness.get("live_ready", False),
            "live_connectors": readiness.get("live_connectors", []),
            "healthy": health.get("healthy", False),
            "health_status": health.get("status", "unknown"),
            "healthy_subsystems": health.get("healthy_count", 0),
            "degraded_subsystems": health.get("degraded_count", 0),
            "unhealthy_subsystems": health.get("unhealthy_count", 0),
            "subsystems": health.get("subsystems", {}),
        }


# Singleton instance
_operator_service: Optional[OperatorService] = None


def get_operator_service() -> OperatorService:
    """Get the global operator service."""
    global _operator_service
    if _operator_service is None:
        _operator_service = OperatorService()
    return _operator_service


# =============================================================================
# DAILY OPERATOR ACTIVATION - Dashboard and Work Queue Methods
# =============================================================================
# These helper functions aggregate operator-facing data for the dashboard.


def get_attention_summary(service: OperatorService) -> Dict[str, Any]:
    """
    Get summary of items needing operator attention.

    Aggregates: pending approvals, paused scenarios, failed jobs,
    blocked items, retryable items, and capacity warnings.

    Returns:
        Attention summary dict with counts and items
    """
    # Get core attention items
    pending_approvals = service.get_pending_approvals()
    paused_scenarios = service.get_paused_scenarios()
    failed_jobs = service.get_failed_jobs()

    # Get active blockers
    try:
        blockers = service.get_active_blockers()
    except Exception:
        blockers = []

    # Get capacity warnings
    try:
        capacity = service.get_capacity_status()
        capacity_warnings = capacity.get("warnings", [])
    except Exception:
        capacity_warnings = []

    # Get credential warnings
    try:
        cred_summary = service.get_credentials_summary()
        expiring_creds = cred_summary.get("expiring_soon", 0)
        missing_creds = cred_summary.get("missing", 0)
    except Exception:
        expiring_creds = 0
        missing_creds = 0

    # Calculate total attention count
    attention_count = (
        len(pending_approvals)
        + len(paused_scenarios)
        + len(failed_jobs)
        + len(blockers)
        + (1 if expiring_creds > 0 else 0)
        + (1 if missing_creds > 0 else 0)
        + len(capacity_warnings)
    )

    return {
        "attention_count": attention_count,
        "pending_approvals": len(pending_approvals),
        "paused_scenarios": len(paused_scenarios),
        "failed_jobs": len(failed_jobs),
        "active_blockers": len(blockers),
        "expiring_credentials": expiring_creds,
        "missing_credentials": missing_creds,
        "capacity_warnings": len(capacity_warnings),
        "items": {
            "approvals": pending_approvals[:5],
            "paused": paused_scenarios[:5],
            "failed": failed_jobs[:5],
            "blockers": blockers[:5] if isinstance(blockers, list) else [],
        },
    }


def get_unified_work_queue(service: OperatorService, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get unified work queue combining all actionable items.

    Combines: pending approvals, paused scenarios, blocked actions,
    failed jobs, retryable items, resume-ready items.

    Items are sorted by priority and timestamp.

    Returns:
        List of work queue items
    """
    queue_items = []

    # Add pending approvals
    for approval in service.get_pending_approvals():
        queue_items.append({
            "queue_type": "approval",
            "priority": approval.get("priority", "normal"),
            "id": approval.get("record_id"),
            "title": approval.get("description", approval.get("action", "Pending Approval")),
            "status": "pending",
            "category": "Needs Approval",
            "created_at": approval.get("created_at"),
            "context": {
                "request_type": approval.get("request_type"),
                "connector": approval.get("connector_name"),
                "operation": approval.get("operation"),
                "risk_level": approval.get("risk_level"),
            },
            "actions": ["approve", "deny", "view_detail"],
        })

    # Add paused scenarios
    for scenario in service.get_paused_scenarios():
        queue_items.append({
            "queue_type": "scenario",
            "priority": "medium",
            "id": scenario.get("run_id"),
            "title": scenario.get("scenario_name", scenario.get("scenario_id", "Paused Scenario")),
            "status": scenario.get("status", "paused"),
            "category": "Paused",
            "created_at": scenario.get("started_at"),
            "context": {
                "steps_completed": scenario.get("steps_completed", 0),
                "total_steps": scenario.get("total_steps", 0),
                "blockers": scenario.get("blockers", []),
            },
            "actions": ["resume", "retry", "skip_step", "cancel", "view_detail"],
        })

    # Add failed jobs
    for job in service.get_failed_jobs():
        queue_items.append({
            "queue_type": "job",
            "priority": "high",
            "id": job.get("job_id"),
            "title": f"Failed: {job.get('plan_id', 'Job')}",
            "status": "failed",
            "category": "Failed",
            "created_at": job.get("completed_at") or job.get("dispatched_at"),
            "context": {
                "error": job.get("error"),
                "retry_count": job.get("retry_count", 0),
                "backend": job.get("backend"),
            },
            "actions": ["retry", "rerun_plan", "view_detail"],
        })

    # Add active blockers
    try:
        blockers = service.get_active_blockers()
        for blocker in blockers:
            if isinstance(blocker, dict):
                queue_items.append({
                    "queue_type": "blocker",
                    "priority": "high",
                    "id": blocker.get("blocker_id"),
                    "title": blocker.get("message", "Blocked"),
                    "status": "blocked",
                    "category": "Blocked",
                    "created_at": blocker.get("created_at"),
                    "context": {
                        "blocker_type": blocker.get("blocker_type"),
                        "related_id": blocker.get("related_id"),
                        "resolution_hint": blocker.get("resolution_hint"),
                    },
                    "actions": blocker.get("available_actions", ["view_detail"]),
                })
    except Exception:
        pass

    # Sort by priority (critical > high > medium > low) and timestamp
    priority_order = {"critical": 0, "high": 1, "medium": 2, "normal": 2, "low": 3}
    queue_items.sort(key=lambda x: (
        priority_order.get(x.get("priority", "normal"), 2),
        x.get("created_at") or "",
    ))

    return queue_items[:limit]


def get_next_step_guidance(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get actionable next-step guidance for a work queue item.

    Provides specific instructions based on item type and state.

    Returns:
        Guidance dict with recommendation and actions
    """
    queue_type = item.get("queue_type")
    status = item.get("status")
    context = item.get("context", {})

    guidance = {
        "recommendation": "",
        "primary_action": None,
        "secondary_actions": [],
        "explanation": "",
    }

    if queue_type == "approval":
        if context.get("risk_level") == "high":
            guidance["recommendation"] = "Review carefully before approving"
            guidance["explanation"] = "This is a high-risk action requiring careful review."
        else:
            guidance["recommendation"] = "Review and approve or deny"
            guidance["explanation"] = "Standard approval request awaiting your decision."
        guidance["primary_action"] = {"action": "approve", "label": "Approve"}
        guidance["secondary_actions"] = [
            {"action": "deny", "label": "Deny"},
            {"action": "view_detail", "label": "View Details"},
        ]

    elif queue_type == "scenario":
        blockers = context.get("blockers", [])
        if blockers:
            blocker_types = [b.get("type") if isinstance(b, dict) else str(b) for b in blockers]
            if "approval_required" in blocker_types:
                guidance["recommendation"] = "Approve pending action to continue"
                guidance["explanation"] = "Scenario waiting for approval. Approve the action to resume."
                guidance["primary_action"] = {"action": "approve_blocker", "label": "Go to Approval"}
            elif "missing_credential" in blocker_types:
                guidance["recommendation"] = "Add missing credential"
                guidance["explanation"] = "Scenario blocked on a missing credential."
                guidance["primary_action"] = {"action": "add_credential", "label": "Add Credential"}
            else:
                guidance["recommendation"] = "Resolve blockers or skip step"
                guidance["explanation"] = "Scenario has blockers that need resolution."
                guidance["primary_action"] = {"action": "view_detail", "label": "View Blockers"}
        else:
            guidance["recommendation"] = "Resume scenario execution"
            guidance["explanation"] = "Scenario is paused and ready to resume."
            guidance["primary_action"] = {"action": "resume", "label": "Resume"}
        guidance["secondary_actions"] = [
            {"action": "skip_step", "label": "Skip Failed Step"},
            {"action": "cancel", "label": "Cancel Scenario"},
        ]

    elif queue_type == "job":
        error = context.get("error", "")
        retry_count = context.get("retry_count", 0)
        if retry_count < 3:
            guidance["recommendation"] = "Retry the failed job"
            guidance["explanation"] = f"Job failed with error: {error[:100]}..."
            guidance["primary_action"] = {"action": "retry", "label": "Retry Job"}
        else:
            guidance["recommendation"] = "Review error and rerun plan"
            guidance["explanation"] = "Job failed multiple times. Consider reviewing the plan."
            guidance["primary_action"] = {"action": "rerun_plan", "label": "Rerun Plan"}
        guidance["secondary_actions"] = [
            {"action": "view_detail", "label": "View Error Details"},
        ]

    elif queue_type == "blocker":
        blocker_type = context.get("blocker_type", "")
        hint = context.get("resolution_hint", "")
        guidance["recommendation"] = hint or f"Resolve {blocker_type} blocker"
        guidance["explanation"] = f"Work blocked by: {blocker_type}"
        guidance["primary_action"] = {"action": "view_detail", "label": "View Details"}

    return guidance


def get_quick_action_counts(service: OperatorService) -> Dict[str, int]:
    """
    Get counts for quick action buttons.

    Returns counts for common operator actions.
    """
    # Get pending approvals count
    pending_approvals = len(service.get_pending_approvals())

    # Get active scenario runs
    try:
        scenario_runs = service.list_scenario_runs(limit=100)
        running_scenarios = len([r for r in scenario_runs if r.get("status") == "running"])
        paused_scenarios = len([r for r in scenario_runs if r.get("status") in ("paused", "awaiting_approval", "partial")])
    except Exception:
        running_scenarios = 0
        paused_scenarios = 0

    # Get job counts
    try:
        jobs = service.get_jobs(limit=100)
        active_jobs = len([j for j in jobs if j.get("status") in ("running", "pending", "queued")])
        failed_jobs = len([j for j in jobs if j.get("status") == "failed"])
    except Exception:
        active_jobs = 0
        failed_jobs = 0

    # Get connector actions needing review
    try:
        actions, _ = service.get_connector_actions(limit=50)
        recent_failed_actions = len([a for a in actions if not a.get("success")])
    except Exception:
        recent_failed_actions = 0

    # Get capacity warnings
    try:
        capacity = service.get_capacity_status()
        capacity_warnings = len(capacity.get("warnings", []))
    except Exception:
        capacity_warnings = 0

    return {
        "pending_approvals": pending_approvals,
        "running_scenarios": running_scenarios,
        "paused_scenarios": paused_scenarios,
        "active_jobs": active_jobs,
        "failed_jobs": failed_jobs,
        "failed_actions": recent_failed_actions,
        "capacity_warnings": capacity_warnings,
    }


def get_combined_status(service: OperatorService) -> Dict[str, Any]:
    """
    Get combined readiness and health status.

    Returns a dict with health information for admin views.
    """
    try:
        return service.get_combined_status()
    except Exception:
        return {
            "ready": True,
            "healthy": True,
            "dry_run_ready": True,
            "live_ready": False,
            "healthy_subsystems": 0,
            "degraded_subsystems": 0,
            "health_status": "unknown",
        }


def get_operator_home_data(service: OperatorService) -> Dict[str, Any]:
    """
    Get all data needed for the operator home/dashboard.

    Combines attention summary, quick actions, recent activity, and status.
    """
    # Get system status
    status = service.get_system_status()

    # Get attention summary
    attention = get_attention_summary(service)

    # Get quick action counts
    quick_counts = get_quick_action_counts(service)

    # Get recent events (filtered for important ones)
    recent_events = service.get_events(limit=10)

    # Get recent decisions
    recent_decisions = service.get_recent_decisions(limit=5)

    # Get combined readiness/health
    combined_status = get_combined_status(service)

    # Get recent operator actions
    try:
        recent_actions = service.get_operator_action_history(limit=5)
    except Exception:
        recent_actions = []

    return {
        "status": status.to_dict(),
        "attention": attention,
        "quick_counts": quick_counts,
        "recent_events": recent_events,
        "recent_decisions": recent_decisions,
        "combined_status": combined_status,
        "recent_actions": recent_actions,
    }


# =============================================================================
# End Daily Operator Activation Methods
# =============================================================================


# =============================================================================
# Template Registry and Playbook Methods
# =============================================================================

# Import template registry
from core.template_registry import (
    get_template_registry,
    TemplateRegistry,
    TemplateCategory,
    TemplateMode,
    TemplateComplexity,
    WorkflowTemplate,
    TemplateLaunch,
)


def get_playbook_content() -> Dict[str, Any]:
    """
    Get the operator playbook content for rendering.

    Returns structured playbook data including sections,
    quick reference, and common workflows.
    """
    return {
        "title": "Operator Playbook",
        "version": "1.0",
        "sections": [
            {
                "id": "getting-started",
                "title": "Getting Started",
                "summary": "First-time setup and system startup",
                "topics": [
                    {"name": "Verify Readiness", "route": "/readiness", "description": "Check all components are operational"},
                    {"name": "Setup Checklist", "route": "/setup", "description": "Complete first-use configuration"},
                    {"name": "Health Check", "route": "/health", "description": "Confirm subsystems are healthy"},
                ],
            },
            {
                "id": "daily-workflow",
                "title": "Daily Operator Workflow",
                "summary": "Morning checklist and routine tasks",
                "topics": [
                    {"name": "Dashboard", "route": "/", "description": "Review attention items and status"},
                    {"name": "Work Queue", "route": "/work-queue", "description": "Process items needing attention"},
                    {"name": "Approvals", "route": "/approvals", "description": "Review and approve pending actions"},
                    {"name": "Connector Health", "route": "/integrations", "description": "Verify external services"},
                    {"name": "Cost Review", "route": "/costs", "description": "Monitor budget utilization"},
                ],
            },
            {
                "id": "common-workflows",
                "title": "Common Workflows",
                "summary": "Step-by-step guides for frequent tasks",
                "topics": [
                    {"name": "Submit Discovery", "route": "/discovery", "description": "Enter new business idea"},
                    {"name": "Run Scenario", "route": "/scenarios", "description": "Execute a workflow template"},
                    {"name": "Approve Action", "route": "/approvals", "description": "Review and approve requests"},
                    {"name": "Resume Workflow", "route": "/recovery", "description": "Handle blocked/paused items"},
                    {"name": "Check Connectors", "route": "/integrations", "description": "Verify connector health"},
                ],
            },
            {
                "id": "modes",
                "title": "Dry-Run vs Live Mode",
                "summary": "Understanding execution modes",
                "topics": [
                    {"name": "Dry-Run Mode", "description": "Safe simulation - no external calls"},
                    {"name": "Live Mode", "description": "Real execution - requires approval and credentials"},
                    {"name": "Promotion", "description": "How to enable live mode for operations"},
                ],
            },
            {
                "id": "recovery",
                "title": "Recovery Procedures",
                "summary": "Handling errors and blocked workflows",
                "topics": [
                    {"name": "Paused Scenarios", "route": "/recovery/paused", "description": "Resume awaiting workflows"},
                    {"name": "Failed Jobs", "route": "/recovery/failed", "description": "Retry failed executions"},
                    {"name": "Active Blockers", "route": "/recovery/blockers", "description": "Resolve blocking issues"},
                    {"name": "Recovery History", "route": "/recovery/history", "description": "View past recovery actions"},
                ],
            },
            {
                "id": "safety",
                "title": "Safety Guidelines",
                "summary": "Best practices for safe operation",
                "topics": [
                    {"name": "Always Do", "description": "Start dry-run, review approvals, check health"},
                    {"name": "Never Do", "description": "Approve blindly, commit credentials, bypass approvals"},
                    {"name": "Emergency", "description": "Cancel running actions, review logs"},
                ],
            },
        ],
        "quick_reference": {
            "status_check": {"route": "/", "label": "Dashboard"},
            "work_queue": {"route": "/work-queue", "label": "Work Queue"},
            "approvals": {"route": "/approvals", "label": "Approvals"},
            "scenarios": {"route": "/scenarios", "label": "Scenarios"},
            "templates": {"route": "/templates", "label": "Templates"},
            "recovery": {"route": "/recovery", "label": "Recovery"},
        },
    }


def get_quickstart_flows() -> List[Dict[str, Any]]:
    """
    Get guided quick-start flows for common operations.

    Returns a list of quick-start flows with steps and routes.
    """
    return [
        {
            "id": "first-discovery",
            "name": "Start Discovery",
            "description": "Submit your first business idea or opportunity",
            "icon": "lightbulb",
            "steps": [
                {"name": "Go to Discovery", "route": "/discovery", "action": "navigate"},
                {"name": "Enter your idea in the intake form", "action": "input"},
                {"name": "Add optional tags", "action": "input"},
                {"name": "Submit and review the opportunity", "action": "submit"},
            ],
            "template_id": "discovery_intake",
            "estimated_time": "< 1 minute",
        },
        {
            "id": "run-research",
            "name": "Run Research Scenario",
            "description": "Execute market or competitor research",
            "icon": "search",
            "steps": [
                {"name": "Go to Scenarios", "route": "/scenarios", "action": "navigate"},
                {"name": "Select a research scenario", "action": "select"},
                {"name": "Enter your research query", "action": "input"},
                {"name": "Choose Dry-Run mode", "action": "select"},
                {"name": "Run and review results", "action": "submit"},
            ],
            "template_id": "research_scenario",
            "estimated_time": "1-2 minutes",
        },
        {
            "id": "test-notification",
            "name": "Send Test Notification",
            "description": "Test notification delivery via Telegram or Email",
            "icon": "bell",
            "steps": [
                {"name": "Go to Templates", "route": "/templates", "action": "navigate"},
                {"name": "Select Notification Test template", "action": "select"},
                {"name": "Choose channel (Telegram/Email)", "action": "select"},
                {"name": "Enter test message", "action": "input"},
                {"name": "Run in dry-run first, then live", "action": "submit"},
            ],
            "template_id": "notification_test",
            "estimated_time": "< 1 minute",
            "requires_credentials": True,
        },
        {
            "id": "review-approvals",
            "name": "Review Approvals",
            "description": "Process pending approval requests",
            "icon": "check-circle",
            "steps": [
                {"name": "Go to Approvals", "route": "/approvals", "action": "navigate"},
                {"name": "Review pending requests", "action": "review"},
                {"name": "Click to see details", "action": "click"},
                {"name": "Approve or Deny with rationale", "action": "submit"},
            ],
            "estimated_time": "Variable",
        },
        {
            "id": "check-health",
            "name": "Inspect Connector Health",
            "description": "Verify external service connections",
            "icon": "activity",
            "steps": [
                {"name": "Go to Integrations", "route": "/integrations", "action": "navigate"},
                {"name": "Review connector status cards", "action": "review"},
                {"name": "Click a connector for details", "action": "click"},
                {"name": "Run Health Check if needed", "action": "submit"},
            ],
            "template_id": "connector_health",
            "estimated_time": "< 1 minute",
        },
        {
            "id": "resume-work",
            "name": "Resume Paused Work",
            "description": "Handle blocked or paused workflows",
            "icon": "play",
            "steps": [
                {"name": "Go to Recovery", "route": "/recovery", "action": "navigate"},
                {"name": "Review paused scenarios and failed jobs", "action": "review"},
                {"name": "Identify the blocker", "action": "review"},
                {"name": "Take action: Resume, Retry, Skip, or Cancel", "action": "submit"},
            ],
            "estimated_time": "Variable",
        },
    ]


# Add template methods to OperatorService class
def _add_template_methods_to_service():
    """Add template-related methods to OperatorService."""

    def get_templates(
        self,
        category: Optional[str] = None,
        mode: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of available templates."""
        registry = get_template_registry()

        if search_query:
            templates = registry.search_templates(search_query)
        else:
            category_enum = TemplateCategory(category) if category else None
            mode_enum = TemplateMode(mode) if mode else None
            templates = registry.list_templates(category=category_enum, mode=mode_enum)

        return [t.to_dict() for t in templates]

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID."""
        registry = get_template_registry()
        template = registry.get_template(template_id)
        return template.to_dict() if template else None

    def get_template_summary(self) -> Dict[str, Any]:
        """Get summary of available templates."""
        registry = get_template_registry()
        return registry.get_template_summary()

    def launch_template(
        self,
        template_id: str,
        inputs: Dict[str, Any],
        dry_run: bool = True,
        launched_by: str = "operator",
    ) -> Optional[Dict[str, Any]]:
        """Launch a template with provided inputs."""
        registry = get_template_registry()
        launch = registry.launch_template(
            template_id=template_id,
            inputs=inputs,
            dry_run=dry_run,
            launched_by=launched_by,
        )
        if not launch:
            return None

        # Attempt to execute via scenario system if available
        template = registry.get_template(template_id)
        if template:
            try:
                # Map template to scenario execution
                scenario_id = f"template_{template_id}"

                # Check if a matching scenario exists
                scenario = self.get_scenario(scenario_id)
                if scenario:
                    result = self.run_scenario(
                        scenario_id=scenario_id,
                        inputs=inputs,
                        dry_run=dry_run,
                        triggered_by=launched_by,
                    )
                    if result:
                        registry.update_launch_status(
                            launch.launch_id,
                            status="running",
                            scenario_run_id=result.get("run_id"),
                        )
                else:
                    # No matching scenario - mark as simulation
                    registry.update_launch_status(
                        launch.launch_id,
                        status="completed",
                        result={
                            "message": "Template launched in simulation mode",
                            "inputs": inputs,
                            "dry_run": dry_run,
                            "steps_simulated": len(template.steps),
                        },
                    )
            except Exception as e:
                registry.update_launch_status(
                    launch.launch_id,
                    status="failed",
                    result={"error": str(e)},
                )

        return registry.get_launch(launch.launch_id).to_dict()

    def get_template_launch(self, launch_id: str) -> Optional[Dict[str, Any]]:
        """Get a template launch record."""
        registry = get_template_registry()
        launch = registry.get_launch(launch_id)
        return launch.to_dict() if launch else None

    def list_template_launches(
        self,
        template_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List template launches."""
        registry = get_template_registry()
        launches = registry.list_launches(
            template_id=template_id,
            status=status,
            limit=limit,
        )
        return [l.to_dict() for l in launches]

    # Add methods to OperatorService
    OperatorService.get_templates = get_templates
    OperatorService.get_template = get_template
    OperatorService.get_template_summary = get_template_summary
    OperatorService.launch_template = launch_template
    OperatorService.get_template_launch = get_template_launch
    OperatorService.list_template_launches = list_template_launches


# Initialize template methods
_add_template_methods_to_service()


# =============================================================================
# End Template Registry and Playbook Methods
# =============================================================================


# =============================================================================
# Market Discovery Engine Methods
# =============================================================================

from core.market_discovery import (
    MarketDiscoveryEngine,
    DiscoveryInput,
    DiscoveryResult,
    OpportunityCandidate,
    get_discovery_engine,
)
from core.opportunity_ranker import get_opportunity_ranker
from core.discovery_history import (
    get_discovery_history,
    CandidateStatus,
    SignalSource,
)


def run_discovery_scan(
    mode: str,
    market: Optional[str] = None,
    industry: Optional[str] = None,
    problem_area: Optional[str] = None,
    customer_type: Optional[str] = None,
    theme: Optional[str] = None,
    trend: Optional[str] = None,
    additional_context: Optional[str] = None,
    enrich: bool = False,
) -> Dict[str, Any]:
    """
    Run a market discovery scan with optional external enrichment

    Args:
        mode: Discovery mode (theme_scan, pain_point_scan, industry_scan, problem_exploration)
        market: Market/industry name
        industry: Industry name
        problem_area: Problem domain
        customer_type: Target customer type
        theme: Theme/trend
        trend: Trend name
        additional_context: Additional context
        enrich: Enable external signal enrichment (default: False)

    Returns:
        Discovery result as dictionary
    """
    discovery_input = DiscoveryInput(
        mode=mode,
        market=market,
        industry=industry,
        problem_area=problem_area,
        customer_type=customer_type,
        theme=theme,
        trend=trend,
        additional_context=additional_context,
    )

    engine = get_discovery_engine()
    result = engine.run_discovery(discovery_input, enrich=enrich)

    # Rank candidates
    ranker = get_opportunity_ranker()
    ranked_candidates = ranker.rank_candidates(result.candidates)

    # Update result with ranked candidates
    result.candidates = ranked_candidates

    # Persist to discovery history
    history = get_discovery_history()
    enriched = enrich or result.metadata.get("enriched", False)
    history.persist_scan(result, enriched=enriched)

    # Convert to dict
    return {
        "scan_id": result.scan_id,
        "mode": result.mode,
        "input_summary": result.input_summary,
        "candidates": [
            {
                "candidate_id": c.candidate_id,
                "title": c.title,
                "pain_point": c.pain_point,
                "target_customer": c.target_customer,
                "urgency": c.urgency,
                "monetization_clarity": c.monetization_clarity,
                "execution_domains": c.execution_domains,
                "automation_potential": c.automation_potential,
                "complexity": c.complexity,
                "recommended_action": c.recommended_action,
                "confidence": c.confidence,
                "discovered_via": c.discovered_via,
                "discovered_at": c.discovered_at,
            }
            for c in result.candidates
        ],
        "total_candidates": result.total_candidates,
        "scan_timestamp": result.scan_timestamp,
        "metadata": result.metadata,
    }


def get_discovery_scan_result(scan_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a discovery scan result from history

    Args:
        scan_id: Scan ID

    Returns:
        Discovery result as dictionary or None
    """
    history = get_discovery_history()
    record = history.get_scan(scan_id)

    if not record:
        # Fallback to engine for backward compatibility
        engine = get_discovery_engine()
        result = engine.get_scan_result(scan_id)
        if not result:
            return None

        return {
            "scan_id": result.scan_id,
            "mode": result.mode,
            "input_summary": result.input_summary,
            "candidates": [
                {
                    "candidate_id": c.candidate_id,
                    "title": c.title,
                    "pain_point": c.pain_point,
                    "target_customer": c.target_customer,
                    "urgency": c.urgency,
                    "monetization_clarity": c.monetization_clarity,
                    "execution_domains": c.execution_domains,
                    "automation_potential": c.automation_potential,
                    "complexity": c.complexity,
                    "recommended_action": c.recommended_action,
                    "confidence": c.confidence,
                    "discovered_via": c.discovered_via,
                    "discovered_at": c.discovered_at,
                }
                for c in result.candidates
            ],
            "total_candidates": result.total_candidates,
            "scan_timestamp": result.scan_timestamp,
            "metadata": result.metadata,
        }

    return record.to_dict()


def list_discovery_scans(limit: int = 10) -> List[Dict[str, Any]]:
    """
    List recent discovery scans from history

    Args:
        limit: Maximum number of scans to return

    Returns:
        List of discovery scan summaries
    """
    history = get_discovery_history()
    scans = history.list_scans(limit=limit)

    return [
        {
            "scan_id": scan.scan_id,
            "mode": scan.mode,
            "input_summary": scan.input_summary,
            "total_candidates": scan.total_candidates,
            "scan_timestamp": scan.scan_timestamp,
            "converted_count": scan.converted_count,
            "archived_count": scan.archived_count,
            "ignored_count": scan.ignored_count,
        }
        for scan in scans
    ]


def filter_discovery_scans(
    mode: Optional[str] = None,
    theme: Optional[str] = None,
    industry: Optional[str] = None,
    problem: Optional[str] = None,
    has_conversions: Optional[bool] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Filter discovery scans with advanced criteria

    Args:
        mode: Filter by discovery mode
        theme: Theme keyword search
        industry: Industry keyword search
        problem: Problem keyword search
        has_conversions: Filter by conversion status
        limit: Maximum results

    Returns:
        Filtered list of discovery scan summaries
    """
    history = get_discovery_history()
    scans = history.filter_scans(
        mode=mode,
        theme=theme,
        industry=industry,
        problem=problem,
        has_conversions=has_conversions,
        limit=limit,
    )

    return [
        {
            "scan_id": scan.scan_id,
            "mode": scan.mode,
            "input_summary": scan.input_summary,
            "total_candidates": scan.total_candidates,
            "scan_timestamp": scan.scan_timestamp,
            "converted_count": scan.converted_count,
            "archived_count": scan.archived_count,
            "ignored_count": scan.ignored_count,
        }
        for scan in scans
    ]


def get_discovery_candidate(candidate_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific discovery candidate with enrichment data

    Args:
        candidate_id: Candidate ID

    Returns:
        Enriched candidate data or None
    """
    history = get_discovery_history()
    candidate = history.get_candidate(candidate_id)

    if not candidate:
        return None

    return candidate.to_dict()


def convert_candidate_to_opportunity(
    candidate_id: str,
    opportunity_id: str,
) -> bool:
    """
    Mark a discovery candidate as converted to an opportunity

    Args:
        candidate_id: Candidate ID
        opportunity_id: Created opportunity ID

    Returns:
        True if successful
    """
    history = get_discovery_history()
    return history.mark_converted(candidate_id, opportunity_id)


def archive_candidate(candidate_id: str, reason: str) -> bool:
    """
    Archive a discovery candidate

    Args:
        candidate_id: Candidate ID
        reason: Reason for archiving

    Returns:
        True if successful
    """
    history = get_discovery_history()
    return history.mark_archived(candidate_id, reason)


def get_discovery_conversion_stats() -> Dict[str, Any]:
    """
    Get discovery conversion statistics

    Returns:
        Conversion metrics and statistics
    """
    history = get_discovery_history()
    return history.get_conversion_stats()


# Add discovery methods to OperatorService
def _add_discovery_methods_to_service():
    """Add discovery methods to OperatorService"""

    def run_discovery_scan_method(self, *args, **kwargs):
        return run_discovery_scan(*args, **kwargs)

    def get_discovery_scan_result_method(self, *args, **kwargs):
        return get_discovery_scan_result(*args, **kwargs)

    def list_discovery_scans_method(self, *args, **kwargs):
        return list_discovery_scans(*args, **kwargs)

    OperatorService.run_discovery_scan = run_discovery_scan_method
    OperatorService.get_discovery_scan_result = get_discovery_scan_result_method
    OperatorService.list_discovery_scans = list_discovery_scans_method


# Initialize discovery methods
_add_discovery_methods_to_service()


# =============================================================================
# End Market Discovery Engine Methods
# =============================================================================
