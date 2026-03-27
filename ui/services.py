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
        """Build detailed approval record dictionary."""
        detail = {
            "record_id": r.record_id,
            "request_id": r.request_id,
            "policy_id": r.policy_id,
            "action": r.action,
            "requester": r.requester,
            "target_agent": r.target_agent,
            "classification": r.classification.value,
            "status": r.status.value,
            "reason": r.reason or r.rationale,
            "rationale": r.rationale,
            "created_at": r.created_at,
            "decided_by": r.decided_by,
            "decided_at": r.decided_at,
            "resolved_at": r.resolved_at,
            "request_type": r.request_type or "action",
            "description": r.description or r.action,
            "priority": r.priority,
            "risk_level": r.risk_level,
            "context": r.context,
            "connector_name": r.connector_name,
            "operation": r.operation,
            "plan_id": r.plan_id,
            "job_id": r.job_id,
            "approved": r.approved,
            "approved_by": r.approved_by,
        }

        # Add related plan/job info if available
        if r.plan_id:
            plan = self.get_execution_plan(r.request_id)
            if plan:
                detail["related_plan"] = {
                    "plan_id": r.plan_id,
                    "step_count": len(plan.get("plan", {}).get("steps", [])),
                    "selected_skills": plan.get("selected_skills", []),
                }

        return detail

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

        job = self._job_dispatcher.get_job(job_id)
        if not job:
            return None

        result_dict = None
        if job.result:
            result_dict = {
                "status": job.result.status.value,
                "total_steps": job.result.total_steps,
                "completed_steps": job.result.completed_steps,
                "failed_steps": job.result.failed_steps,
                "duration": job.result.duration_seconds,
            }

        detail = {
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
            "retry_count": job.retry_count,
            "can_retry": job.status == JobStatus.FAILED,
            "can_cancel": job.status in (JobStatus.PENDING, JobStatus.RUNNING, JobStatus.QUEUED),
            "is_complete": job.is_complete,
        }

        # Add options if available
        if job.options:
            detail["options"] = {
                "strategy": job.options.strategy.value,
                "priority": job.options.priority.name,
                "timeout_seconds": job.options.timeout_seconds,
                "max_retries": job.options.max_retries,
                "stop_on_failure": job.options.stop_on_failure,
                "parallel_steps": job.options.parallel_steps,
            }

        return detail

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


# Singleton instance
_operator_service: Optional[OperatorService] = None


def get_operator_service() -> OperatorService:
    """Get the global operator service."""
    global _operator_service
    if _operator_service is None:
        _operator_service = OperatorService()
    return _operator_service
