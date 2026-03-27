"""
Service layer for UI backend access.

Provides clean interfaces to core modules for the operator interface.
Keeps route handlers thin and business logic centralized.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

# Core module imports
from core.chief_orchestrator import ChiefOrchestrator, OrchestrationResult
from core.runtime_manager import RuntimeManager, get_runtime_manager
from core.approval_manager import ApprovalManager, ApprovalClass, ApprovalRecord
from core.event_logger import EventLogger, Event, EventType, EventSeverity
from core.job_dispatcher import JobDispatcher, get_job_dispatcher, DispatchedJob
from core.execution_backends import BackendType, JobStatus
from core.execution_plan import ExecutionPlan, ExecutionStatus
from core.agent_contracts import AgentRequest, RequestStatus


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
    ):
        """Initialize the operator service."""
        self._orchestrator = orchestrator
        self._runtime_manager = runtime_manager
        self._approval_manager = approval_manager
        self._event_logger = event_logger
        self._job_dispatcher = job_dispatcher

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

        return SystemStatus(
            healthy=True,
            runtime_initialized=self._runtime_manager.is_initialized if self._runtime_manager else False,
            active_jobs=active_jobs,
            pending_approvals=pending_approvals,
            available_backends=backends,
            total_events=total_events,
            recent_errors=recent_errors,
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
                "reason": r.reason,
                "created_at": r.created_at,
                "context": r.context,
            }
            for r in pending
        ]

    def approve_request(self, record_id: str, approver: str = "principal") -> bool:
        """Approve a pending request."""
        self._ensure_initialized()

        return self._approval_manager.approve(record_id, approver)

    def deny_request(self, record_id: str, reason: str, denier: str = "principal") -> bool:
        """Deny a pending request."""
        self._ensure_initialized()

        return self._approval_manager.deny(record_id, denier, reason)

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
                "approved": r.approved,
                "approved_by": r.approved_by,
                "created_at": r.created_at,
                "resolved_at": r.resolved_at,
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

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        self._ensure_initialized()

        return self._job_dispatcher.cancel_job(job_id)

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


# Singleton instance
_operator_service: Optional[OperatorService] = None


def get_operator_service() -> OperatorService:
    """Get the global operator service."""
    global _operator_service
    if _operator_service is None:
        _operator_service = OperatorService()
    return _operator_service
