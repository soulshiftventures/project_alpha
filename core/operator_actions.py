"""
Operator Actions for Project Alpha.

Provides a unified surface for operator-driven recovery and workflow control actions.

ACTIONS PROVIDED:
- Approve/Deny: Grant or reject pending approvals
- Resume: Continue paused workflows after blockers are resolved
- Retry: Re-attempt failed operations
- Rerun: Re-execute completed operations with same/modified inputs
- Skip: Skip blocked steps and continue
- Inspect: View detailed blocker and workflow state
- Cancel: Abort running workflows

GATE PRESERVATION:
- All actions respect approval gates
- Cost/policy checks are enforced
- Credential validation is required
- Live mode rules apply

AUDIT TRAIL:
- All operator actions are logged
- Original records are preserved (never overwritten)
- Recovery operations create new records with lineage
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.recovery_manager import (
    RecoveryManager,
    RecoveryAction,
    RecoveryResult,
    BlockerType,
    Blocker,
    get_recovery_manager,
)

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class OperatorActionType(Enum):
    """Types of operator actions."""
    APPROVE = "approve"
    DENY = "deny"
    RESUME = "resume"
    RETRY = "retry"
    RERUN = "rerun"
    SKIP = "skip"
    INSPECT = "inspect"
    CANCEL = "cancel"


@dataclass
class OperatorActionResult:
    """Result of an operator action."""
    success: bool
    action_type: OperatorActionType
    message: str = ""
    error: Optional[str] = None

    # What was acted upon
    target_id: Optional[str] = None
    target_type: Optional[str] = None  # scenario_run, job, approval, etc.

    # Result data
    data: Dict[str, Any] = field(default_factory=dict)

    # For resume/retry/rerun, track new entities created
    new_run_id: Optional[str] = None
    new_job_id: Optional[str] = None

    # Audit
    performed_by: str = "operator"
    performed_at: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "action_type": self.action_type.value,
            "message": self.message,
            "error": self.error,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "data": self.data,
            "new_run_id": self.new_run_id,
            "new_job_id": self.new_job_id,
            "performed_by": self.performed_by,
            "performed_at": self.performed_at,
        }


class OperatorActions:
    """
    Unified interface for operator-driven workflow control.

    Provides high-level actions that coordinate across:
    - ApprovalManager for approval decisions
    - RecoveryManager for resume/retry/rerun
    - StateStore for persistence and audit
    - ScenarioRunner for scenario operations
    - RuntimeManager for job operations
    """

    def __init__(self, recovery_manager: Optional[RecoveryManager] = None):
        """Initialize operator actions."""
        self._recovery_manager = recovery_manager or get_recovery_manager()

        # Lazy-loaded components
        self._state_store = None
        self._approval_manager = None

        # Action history
        self._action_history: List[OperatorActionResult] = []

    def _get_state_store(self):
        """Lazy load state store."""
        if self._state_store is None:
            from core.state_store import get_state_store
            self._state_store = get_state_store()
        return self._state_store

    def _get_approval_manager(self):
        """Lazy load approval manager."""
        if self._approval_manager is None:
            try:
                from core.chief_orchestrator import ChiefOrchestrator
                orchestrator = ChiefOrchestrator()
                self._approval_manager = orchestrator.approval
            except Exception:
                from core.approval_manager import ApprovalManager
                self._approval_manager = ApprovalManager()
        return self._approval_manager

    def _log_action(self, result: OperatorActionResult) -> None:
        """Log an operator action."""
        self._action_history.append(result)
        logger.info(
            f"Operator action: {result.action_type.value} on {result.target_type}:{result.target_id} "
            f"by {result.performed_by} - {'success' if result.success else 'failed'}"
        )

    # =========================================================================
    # Approval Actions
    # =========================================================================

    def approve(
        self,
        approval_id: str,
        rationale: str = "",
        performed_by: str = "operator",
        auto_resume: bool = True,
    ) -> OperatorActionResult:
        """
        Approve a pending approval request.

        Args:
            approval_id: ID of the approval to grant
            rationale: Reason for approval
            performed_by: Who is approving
            auto_resume: If True, automatically resume blocked workflows

        Returns:
            OperatorActionResult with outcome
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.APPROVE,
            target_id=approval_id,
            target_type="approval",
            performed_by=performed_by,
            success=False,
        )

        try:
            state_store = self._get_state_store()
            approval_manager = self._get_approval_manager()

            # Get approval record
            approval = state_store.get_approval(approval_id)
            if not approval:
                result.error = f"Approval not found: {approval_id}"
                self._log_action(result)
                return result

            if approval.get("status") != "pending":
                result.error = f"Approval not pending: {approval.get('status')}"
                self._log_action(result)
                return result

            # Approve via approval manager
            approved = approval_manager.approve(
                record_id=approval_id,
                approver=performed_by,
                rationale=rationale,
            )

            if approved:
                # Update state store
                approval["status"] = "approved"
                approval["decided_by"] = performed_by
                approval["decided_at"] = _utc_now().isoformat()
                approval["resolved_at"] = approval["decided_at"]
                approval["rationale"] = rationale
                state_store.save_approval(approval)

                result.success = True
                result.message = f"Approved: {approval.get('description', approval_id)}"
                result.data = {"approval": approval}

                # Auto-resume blocked workflows
                if auto_resume:
                    resume_result = self._recovery_manager.resume_after_approval(
                        approval_id=approval_id,
                        resumed_by=performed_by,
                    )
                    result.data["resume_result"] = resume_result.to_dict()
                    result.new_run_id = resume_result.new_run_id
                    result.new_job_id = resume_result.new_job_id
            else:
                result.error = "Approval manager returned None"

        except Exception as e:
            logger.error(f"Approve action failed: {e}")
            result.error = str(e)

        self._log_action(result)
        return result

    def deny(
        self,
        approval_id: str,
        rationale: str = "",
        performed_by: str = "operator",
    ) -> OperatorActionResult:
        """
        Deny a pending approval request.

        Args:
            approval_id: ID of the approval to deny
            rationale: Reason for denial
            performed_by: Who is denying

        Returns:
            OperatorActionResult with outcome
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.DENY,
            target_id=approval_id,
            target_type="approval",
            performed_by=performed_by,
            success=False,
        )

        try:
            state_store = self._get_state_store()
            approval_manager = self._get_approval_manager()

            approval = state_store.get_approval(approval_id)
            if not approval:
                result.error = f"Approval not found: {approval_id}"
                self._log_action(result)
                return result

            if approval.get("status") != "pending":
                result.error = f"Approval not pending: {approval.get('status')}"
                self._log_action(result)
                return result

            # Deny via approval manager
            denied = approval_manager.deny(
                record_id=approval_id,
                denier=performed_by,
                rationale=rationale,
            )

            if denied:
                # Update state store
                approval["status"] = "denied"
                approval["decided_by"] = performed_by
                approval["decided_at"] = _utc_now().isoformat()
                approval["resolved_at"] = approval["decided_at"]
                approval["rationale"] = rationale
                state_store.save_approval(approval)

                result.success = True
                result.message = f"Denied: {approval.get('description', approval_id)}"
                result.data = {"approval": approval}

                # Mark related blockers as resolved with denial
                for blocker in self._recovery_manager.get_blockers_for_approval(approval_id):
                    blocker.resolved_at = _utc_now().isoformat()
                    blocker.resolved_by = performed_by
                    blocker.reason = f"Denied: {rationale}"
            else:
                result.error = "Denial failed"

        except Exception as e:
            logger.error(f"Deny action failed: {e}")
            result.error = str(e)

        self._log_action(result)
        return result

    # =========================================================================
    # Resume Actions
    # =========================================================================

    def resume_scenario(
        self,
        run_id: str,
        performed_by: str = "operator",
        skip_failed: bool = False,
    ) -> OperatorActionResult:
        """
        Resume a paused scenario.

        Args:
            run_id: ID of the scenario run to resume
            performed_by: Who is resuming
            skip_failed: If True, skip failed steps and continue

        Returns:
            OperatorActionResult with outcome
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.RESUME,
            target_id=run_id,
            target_type="scenario_run",
            performed_by=performed_by,
            success=False,
        )

        try:
            recovery_result = self._recovery_manager.resume_scenario(
                run_id=run_id,
                resumed_by=performed_by,
                skip_failed_step=skip_failed,
            )

            result.success = recovery_result.success
            result.message = recovery_result.message
            result.error = recovery_result.error
            result.new_run_id = recovery_result.new_run_id
            result.data = {"recovery_result": recovery_result.to_dict()}

        except Exception as e:
            logger.error(f"Resume scenario action failed: {e}")
            result.error = str(e)

        self._log_action(result)
        return result

    def resume_job(
        self,
        job_id: str,
        performed_by: str = "operator",
    ) -> OperatorActionResult:
        """
        Resume a paused job (typically via retry).

        Args:
            job_id: ID of the job to resume
            performed_by: Who is resuming

        Returns:
            OperatorActionResult with outcome
        """
        # Jobs are resumed via retry
        return self.retry_job(job_id=job_id, performed_by=performed_by)

    # =========================================================================
    # Retry Actions
    # =========================================================================

    def retry_job(
        self,
        job_id: str,
        performed_by: str = "operator",
        new_options: Optional[Dict[str, Any]] = None,
    ) -> OperatorActionResult:
        """
        Retry a failed job.

        Args:
            job_id: ID of the job to retry
            performed_by: Who is retrying
            new_options: Optional new dispatch options

        Returns:
            OperatorActionResult with outcome
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.RETRY,
            target_id=job_id,
            target_type="job",
            performed_by=performed_by,
            success=False,
        )

        try:
            recovery_result = self._recovery_manager.retry_job(
                job_id=job_id,
                retried_by=performed_by,
                new_options=new_options,
            )

            result.success = recovery_result.success
            result.message = recovery_result.message
            result.error = recovery_result.error
            result.new_job_id = recovery_result.new_job_id
            result.data = {"recovery_result": recovery_result.to_dict()}

        except Exception as e:
            logger.error(f"Retry job action failed: {e}")
            result.error = str(e)

        self._log_action(result)
        return result

    def retry_connector_action(
        self,
        execution_id: str,
        performed_by: str = "operator",
    ) -> OperatorActionResult:
        """
        Retry a failed connector action.

        Args:
            execution_id: ID of the connector execution to retry
            performed_by: Who is retrying

        Returns:
            OperatorActionResult with outcome
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.RETRY,
            target_id=execution_id,
            target_type="connector_execution",
            performed_by=performed_by,
            success=False,
        )

        try:
            recovery_result = self._recovery_manager.retry_connector_action(
                execution_id=execution_id,
                retried_by=performed_by,
            )

            result.success = recovery_result.success
            result.message = recovery_result.message
            result.error = recovery_result.error
            result.data = {"recovery_result": recovery_result.to_dict()}

        except Exception as e:
            logger.error(f"Retry connector action failed: {e}")
            result.error = str(e)

        self._log_action(result)
        return result

    def retry_scenario_step(
        self,
        run_id: str,
        step_id: str,
        performed_by: str = "operator",
    ) -> OperatorActionResult:
        """
        Retry a failed scenario step.

        Args:
            run_id: ID of the scenario run
            step_id: ID of the step to retry
            performed_by: Who is retrying

        Returns:
            OperatorActionResult with outcome
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.RETRY,
            target_id=f"{run_id}:{step_id}",
            target_type="scenario_step",
            performed_by=performed_by,
            success=False,
        )

        try:
            recovery_result = self._recovery_manager.retry_scenario_step(
                run_id=run_id,
                step_id=step_id,
                retried_by=performed_by,
            )

            result.success = recovery_result.success
            result.message = recovery_result.message
            result.error = recovery_result.error
            result.new_run_id = recovery_result.new_run_id
            result.data = {"recovery_result": recovery_result.to_dict()}

        except Exception as e:
            logger.error(f"Retry scenario step action failed: {e}")
            result.error = str(e)

        self._log_action(result)
        return result

    # =========================================================================
    # Rerun Actions
    # =========================================================================

    def rerun_plan(
        self,
        plan_id: str,
        performed_by: str = "operator",
        dry_run: Optional[bool] = None,
    ) -> OperatorActionResult:
        """
        Rerun an execution plan.

        Args:
            plan_id: ID of the plan to rerun
            performed_by: Who is triggering the rerun
            dry_run: Override dry_run setting

        Returns:
            OperatorActionResult with outcome
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.RERUN,
            target_id=plan_id,
            target_type="execution_plan",
            performed_by=performed_by,
            success=False,
        )

        try:
            recovery_result = self._recovery_manager.rerun_plan(
                plan_id=plan_id,
                triggered_by=performed_by,
                dry_run=dry_run,
            )

            result.success = recovery_result.success
            result.message = recovery_result.message
            result.error = recovery_result.error
            result.new_job_id = recovery_result.new_job_id
            result.data = {"recovery_result": recovery_result.to_dict()}

        except Exception as e:
            logger.error(f"Rerun plan action failed: {e}")
            result.error = str(e)

        self._log_action(result)
        return result

    def rerun_scenario(
        self,
        run_id: str,
        performed_by: str = "operator",
        dry_run: Optional[bool] = None,
        new_inputs: Optional[Dict[str, Any]] = None,
    ) -> OperatorActionResult:
        """
        Rerun a scenario.

        Args:
            run_id: ID of the scenario run to base rerun on
            performed_by: Who is triggering the rerun
            dry_run: Override dry_run setting
            new_inputs: Optional modified inputs

        Returns:
            OperatorActionResult with outcome
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.RERUN,
            target_id=run_id,
            target_type="scenario_run",
            performed_by=performed_by,
            success=False,
        )

        try:
            recovery_result = self._recovery_manager.rerun_scenario(
                run_id=run_id,
                triggered_by=performed_by,
                dry_run=dry_run,
                new_inputs=new_inputs,
            )

            result.success = recovery_result.success
            result.message = recovery_result.message
            result.error = recovery_result.error
            result.new_run_id = recovery_result.new_run_id
            result.data = {"recovery_result": recovery_result.to_dict()}

        except Exception as e:
            logger.error(f"Rerun scenario action failed: {e}")
            result.error = str(e)

        self._log_action(result)
        return result

    # =========================================================================
    # Skip Actions
    # =========================================================================

    def skip_step(
        self,
        run_id: str,
        step_id: str,
        performed_by: str = "operator",
        reason: str = "",
    ) -> OperatorActionResult:
        """
        Skip a blocked/failed step and continue the scenario.

        Args:
            run_id: ID of the scenario run
            step_id: ID of the step to skip
            performed_by: Who is skipping
            reason: Reason for skipping

        Returns:
            OperatorActionResult with outcome
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.SKIP,
            target_id=f"{run_id}:{step_id}",
            target_type="scenario_step",
            performed_by=performed_by,
            success=False,
        )

        try:
            # Resume scenario with skip_failed=True
            recovery_result = self._recovery_manager.resume_scenario(
                run_id=run_id,
                resumed_by=performed_by,
                skip_failed_step=True,
            )

            result.success = recovery_result.success
            result.message = f"Skipped step {step_id}: {reason}"
            result.error = recovery_result.error
            result.new_run_id = recovery_result.new_run_id
            result.data = {
                "recovery_result": recovery_result.to_dict(),
                "skipped_step": step_id,
                "skip_reason": reason,
            }

        except Exception as e:
            logger.error(f"Skip step action failed: {e}")
            result.error = str(e)

        self._log_action(result)
        return result

    # =========================================================================
    # Inspect Actions
    # =========================================================================

    def inspect_workflow(
        self,
        scenario_run_id: Optional[str] = None,
        job_id: Optional[str] = None,
        performed_by: str = "operator",
    ) -> OperatorActionResult:
        """
        Inspect workflow status and blockers.

        Args:
            scenario_run_id: Scenario run to inspect
            job_id: Job to inspect
            performed_by: Who is inspecting

        Returns:
            OperatorActionResult with workflow status data
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.INSPECT,
            target_id=scenario_run_id or job_id,
            target_type="scenario_run" if scenario_run_id else "job",
            performed_by=performed_by,
            success=True,
        )

        try:
            status = self._recovery_manager.get_workflow_status(
                scenario_run_id=scenario_run_id,
                job_id=job_id,
            )
            result.data = status
            result.message = "Workflow status retrieved"

        except Exception as e:
            logger.error(f"Inspect workflow action failed: {e}")
            result.success = False
            result.error = str(e)

        self._log_action(result)
        return result

    def inspect_blockers(
        self,
        blocker_type: Optional[BlockerType] = None,
        performed_by: str = "operator",
    ) -> OperatorActionResult:
        """
        Get all active blockers.

        Args:
            blocker_type: Optional filter by blocker type
            performed_by: Who is inspecting

        Returns:
            OperatorActionResult with blockers list
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.INSPECT,
            target_type="blockers",
            performed_by=performed_by,
            success=True,
        )

        try:
            blockers = self._recovery_manager.get_active_blockers(
                blocker_type=blocker_type,
            )
            result.data = {
                "blockers": [b.to_dict() for b in blockers],
                "count": len(blockers),
            }
            result.message = f"Found {len(blockers)} active blockers"

        except Exception as e:
            logger.error(f"Inspect blockers action failed: {e}")
            result.success = False
            result.error = str(e)

        self._log_action(result)
        return result

    # =========================================================================
    # Cancel Actions
    # =========================================================================

    def cancel_scenario(
        self,
        run_id: str,
        performed_by: str = "operator",
        reason: str = "",
    ) -> OperatorActionResult:
        """
        Cancel a running scenario.

        Args:
            run_id: ID of the scenario run to cancel
            performed_by: Who is cancelling
            reason: Reason for cancellation

        Returns:
            OperatorActionResult with outcome
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.CANCEL,
            target_id=run_id,
            target_type="scenario_run",
            performed_by=performed_by,
            success=False,
        )

        try:
            state_store = self._get_state_store()
            run = state_store.get_scenario_run(run_id)

            if not run:
                result.error = f"Scenario run not found: {run_id}"
                self._log_action(result)
                return result

            if run.get("status") in ["completed", "cancelled"]:
                result.error = f"Scenario cannot be cancelled from status: {run.get('status')}"
                self._log_action(result)
                return result

            # Update status
            run["status"] = "cancelled"
            run["completed_at"] = _utc_now().isoformat()
            run["error_message"] = f"Cancelled by {performed_by}: {reason}"
            state_store.save_scenario_run(run)

            result.success = True
            result.message = f"Cancelled scenario run: {run_id}"
            result.data = {"run": run, "reason": reason}

            # Resolve all blockers for this scenario
            for blocker in self._recovery_manager.get_active_blockers(scenario_run_id=run_id):
                self._recovery_manager.resolve_blocker(
                    blocker.blocker_id,
                    RecoveryAction.SKIP,
                    performed_by,
                )

        except Exception as e:
            logger.error(f"Cancel scenario action failed: {e}")
            result.error = str(e)

        self._log_action(result)
        return result

    def cancel_job(
        self,
        job_id: str,
        performed_by: str = "operator",
        reason: str = "",
    ) -> OperatorActionResult:
        """
        Cancel a running job.

        Args:
            job_id: ID of the job to cancel
            performed_by: Who is cancelling
            reason: Reason for cancellation

        Returns:
            OperatorActionResult with outcome
        """
        result = OperatorActionResult(
            action_type=OperatorActionType.CANCEL,
            target_id=job_id,
            target_type="job",
            performed_by=performed_by,
            success=False,
        )

        try:
            # Try to cancel via runtime manager
            from core.runtime_manager import get_runtime_manager
            runtime_manager = get_runtime_manager()

            cancelled = runtime_manager.cancel_job(job_id)

            if cancelled:
                # Update state store
                state_store = self._get_state_store()
                job = state_store.get_job(job_id)
                if job:
                    job["status"] = "cancelled"
                    job["completed_at"] = _utc_now().isoformat()
                    job["error"] = f"Cancelled by {performed_by}: {reason}"
                    state_store.save_job(job)

                result.success = True
                result.message = f"Cancelled job: {job_id}"
                result.data = {"reason": reason}

                # Resolve blockers
                for blocker in self._recovery_manager.get_active_blockers(job_id=job_id):
                    self._recovery_manager.resolve_blocker(
                        blocker.blocker_id,
                        RecoveryAction.SKIP,
                        performed_by,
                    )
            else:
                result.error = "Job could not be cancelled"

        except Exception as e:
            logger.error(f"Cancel job action failed: {e}")
            result.error = str(e)

        self._log_action(result)
        return result

    # =========================================================================
    # Dashboard Methods
    # =========================================================================

    def get_operator_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive operator dashboard data.

        Returns all actionable items for the operator.
        """
        try:
            return {
                "pending_approvals": self._recovery_manager.get_pending_approvals_with_context(),
                "paused_scenarios": self._recovery_manager.get_paused_scenarios(),
                "failed_jobs": self._recovery_manager.get_failed_jobs(),
                "active_blockers": [b.to_dict() for b in self._recovery_manager.get_active_blockers()],
                "recent_actions": [a.to_dict() for a in self._action_history[-20:]],
            }
        except Exception as e:
            logger.error(f"Get operator dashboard failed: {e}")
            return {"error": str(e)}

    def get_action_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent operator action history."""
        return [a.to_dict() for a in self._action_history[-limit:]]


# Singleton instance
_operator_actions: Optional[OperatorActions] = None


def get_operator_actions() -> OperatorActions:
    """Get the global operator actions interface."""
    global _operator_actions
    if _operator_actions is None:
        _operator_actions = OperatorActions()
    return _operator_actions
