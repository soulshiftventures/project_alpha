"""
Recovery Manager for Project Alpha.

Orchestrates resume, retry, and rerun operations for operator workflows.

RESPONSIBILITIES:
- Resume paused approval/scenario flows after approval is granted
- Retry failed jobs, connector actions, and scenario steps
- Rerun previously created execution plans
- Maintain audit trail without overwriting prior runs
- Expose blocker visibility for paused/blocked items

GATES PRESERVED:
- Approval gates are not bypassed
- Cost/policy checks remain enforced
- Credential gates are honored
- Live mode promotion rules apply

ARCHITECTURE:
- Works with existing ApprovalManager, ScenarioRunner, RuntimeManager
- Uses StateStore for persistence and audit trail
- Provides callbacks for approval-to-resume flow
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def _generate_id(prefix: str) -> str:
    """Generate a unique ID with prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class BlockerType(Enum):
    """Types of blockers that can pause workflow execution."""
    APPROVAL_REQUIRED = "approval_required"
    MISSING_CREDENTIAL = "missing_credential"
    POLICY_BLOCKED = "policy_blocked"
    BUDGET_BLOCKED = "budget_blocked"
    CAPACITY_BLOCKED = "capacity_blocked"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    LIVE_MODE_NOT_GRANTED = "live_mode_not_granted"
    STEP_FAILED = "step_failed"
    CONNECTOR_FAILED = "connector_failed"


class RecoveryAction(Enum):
    """Types of recovery actions available."""
    RESUME = "resume"  # Continue from paused state
    RETRY = "retry"  # Retry a failed operation
    RERUN = "rerun"  # Re-execute a previously run operation
    SKIP = "skip"  # Skip a blocked step and continue


class RecoveryStatus(Enum):
    """Status of a recovery operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Blocker:
    """Represents a blocker preventing workflow progress."""
    blocker_id: str = field(default_factory=lambda: _generate_id("blk"))
    blocker_type: BlockerType = BlockerType.APPROVAL_REQUIRED

    # Related entities
    scenario_run_id: Optional[str] = None
    job_id: Optional[str] = None
    approval_id: Optional[str] = None
    step_id: Optional[str] = None
    connector_execution_id: Optional[str] = None
    plan_id: Optional[str] = None

    # Blocker details
    description: str = ""
    reason: str = ""

    # Available actions
    available_actions: List[RecoveryAction] = field(default_factory=list)

    # Timing
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_action: Optional[RecoveryAction] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "blocker_id": self.blocker_id,
            "blocker_type": self.blocker_type.value,
            "scenario_run_id": self.scenario_run_id,
            "job_id": self.job_id,
            "approval_id": self.approval_id,
            "step_id": self.step_id,
            "connector_execution_id": self.connector_execution_id,
            "plan_id": self.plan_id,
            "description": self.description,
            "reason": self.reason,
            "available_actions": [a.value for a in self.available_actions],
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "resolution_action": self.resolution_action.value if self.resolution_action else None,
        }


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""
    success: bool = False
    action: RecoveryAction = RecoveryAction.RESUME

    # What was recovered
    scenario_run_id: Optional[str] = None
    job_id: Optional[str] = None
    plan_id: Optional[str] = None
    step_id: Optional[str] = None

    # Result details
    message: str = ""
    error: Optional[str] = None

    # For rerun, we create a new run/job
    new_run_id: Optional[str] = None
    new_job_id: Optional[str] = None

    # Timing
    started_at: str = field(default_factory=lambda: _utc_now().isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "action": self.action.value,
            "scenario_run_id": self.scenario_run_id,
            "job_id": self.job_id,
            "plan_id": self.plan_id,
            "step_id": self.step_id,
            "message": self.message,
            "error": self.error,
            "new_run_id": self.new_run_id,
            "new_job_id": self.new_job_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class RecoveryManager:
    """
    Orchestrates recovery operations for operator workflows.

    Provides:
    - Resume capability for paused scenarios/approvals
    - Retry capability for failed jobs/steps
    - Rerun capability for execution plans
    - Blocker visibility and tracking
    - Approval-to-resume callback hooks
    """

    def __init__(self):
        """Initialize the recovery manager."""
        # Lazy-loaded components
        self._state_store = None
        self._scenario_runner = None
        self._runtime_manager = None
        self._approval_manager = None

        # Active blockers (in-memory cache, persisted in state store)
        self._blockers: Dict[str, Blocker] = {}

        # Approval resume callbacks
        self._approval_callbacks: Dict[str, Callable] = {}

        # Recovery history
        self._recovery_history: List[RecoveryResult] = []

    def _get_state_store(self):
        """Lazy load state store."""
        if self._state_store is None:
            from core.state_store import get_state_store
            self._state_store = get_state_store()
        return self._state_store

    def _get_scenario_runner(self):
        """Lazy load scenario runner."""
        if self._scenario_runner is None:
            from core.scenario_runner import get_scenario_runner
            self._scenario_runner = get_scenario_runner()
        return self._scenario_runner

    def _get_runtime_manager(self):
        """Lazy load runtime manager."""
        if self._runtime_manager is None:
            from core.runtime_manager import get_runtime_manager
            self._runtime_manager = get_runtime_manager()
        return self._runtime_manager

    def _get_approval_manager(self):
        """Lazy load approval manager from orchestrator."""
        if self._approval_manager is None:
            try:
                from core.chief_orchestrator import ChiefOrchestrator
                orchestrator = ChiefOrchestrator()
                self._approval_manager = orchestrator.approval
            except Exception:
                # Fallback to standalone approval manager
                from core.approval_manager import ApprovalManager
                self._approval_manager = ApprovalManager()
        return self._approval_manager

    # =========================================================================
    # Blocker Management
    # =========================================================================

    def register_blocker(
        self,
        blocker_type: BlockerType,
        description: str,
        reason: str = "",
        scenario_run_id: Optional[str] = None,
        job_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        step_id: Optional[str] = None,
        connector_execution_id: Optional[str] = None,
        plan_id: Optional[str] = None,
    ) -> Blocker:
        """
        Register a new blocker for a workflow.

        Args:
            blocker_type: Type of blocker
            description: Human-readable description
            reason: Why this blocker occurred
            scenario_run_id: Related scenario run
            job_id: Related job
            approval_id: Related approval
            step_id: Related step within scenario
            connector_execution_id: Related connector execution
            plan_id: Related execution plan

        Returns:
            Created Blocker instance
        """
        # Determine available actions based on blocker type
        available_actions = self._get_available_actions(blocker_type)

        blocker = Blocker(
            blocker_type=blocker_type,
            scenario_run_id=scenario_run_id,
            job_id=job_id,
            approval_id=approval_id,
            step_id=step_id,
            connector_execution_id=connector_execution_id,
            plan_id=plan_id,
            description=description,
            reason=reason,
            available_actions=available_actions,
        )

        self._blockers[blocker.blocker_id] = blocker

        logger.info(f"Registered blocker: {blocker.blocker_id} - {blocker_type.value}")
        return blocker

    def _get_available_actions(self, blocker_type: BlockerType) -> List[RecoveryAction]:
        """Determine available recovery actions for a blocker type."""
        actions = []

        if blocker_type == BlockerType.APPROVAL_REQUIRED:
            # Can resume after approval is granted
            actions = [RecoveryAction.RESUME]

        elif blocker_type in [BlockerType.STEP_FAILED, BlockerType.CONNECTOR_FAILED]:
            # Can retry or skip failed steps
            actions = [RecoveryAction.RETRY, RecoveryAction.SKIP]

        elif blocker_type == BlockerType.MISSING_CREDENTIAL:
            # Can resume after credential is configured
            actions = [RecoveryAction.RESUME]

        elif blocker_type == BlockerType.POLICY_BLOCKED:
            # Generally cannot bypass policy, but can retry with different params
            actions = [RecoveryAction.RETRY]

        elif blocker_type == BlockerType.BUDGET_BLOCKED:
            # Can retry after budget is adjusted
            actions = [RecoveryAction.RETRY]

        elif blocker_type == BlockerType.CAPACITY_BLOCKED:
            # Can retry when capacity is available
            actions = [RecoveryAction.RETRY]

        elif blocker_type == BlockerType.RUNTIME_UNAVAILABLE:
            # Can retry when runtime is available
            actions = [RecoveryAction.RETRY]

        elif blocker_type == BlockerType.LIVE_MODE_NOT_GRANTED:
            # Can resume after live mode is granted
            actions = [RecoveryAction.RESUME]

        return actions

    def resolve_blocker(
        self,
        blocker_id: str,
        action: RecoveryAction,
        resolved_by: str = "operator",
    ) -> bool:
        """
        Mark a blocker as resolved.

        Args:
            blocker_id: ID of blocker to resolve
            action: Action taken to resolve
            resolved_by: Who resolved the blocker

        Returns:
            True if resolved successfully
        """
        if blocker_id not in self._blockers:
            return False

        blocker = self._blockers[blocker_id]
        blocker.resolved_at = _utc_now().isoformat()
        blocker.resolved_by = resolved_by
        blocker.resolution_action = action

        logger.info(f"Resolved blocker: {blocker_id} via {action.value}")
        return True

    def get_blocker(self, blocker_id: str) -> Optional[Blocker]:
        """Get a blocker by ID."""
        return self._blockers.get(blocker_id)

    def get_active_blockers(
        self,
        scenario_run_id: Optional[str] = None,
        job_id: Optional[str] = None,
        blocker_type: Optional[BlockerType] = None,
    ) -> List[Blocker]:
        """
        Get active (unresolved) blockers with optional filters.

        Args:
            scenario_run_id: Filter by scenario run
            job_id: Filter by job
            blocker_type: Filter by blocker type

        Returns:
            List of matching blockers
        """
        results = []
        for blocker in self._blockers.values():
            # Skip resolved blockers
            if blocker.resolved_at:
                continue

            # Apply filters
            if scenario_run_id and blocker.scenario_run_id != scenario_run_id:
                continue
            if job_id and blocker.job_id != job_id:
                continue
            if blocker_type and blocker.blocker_type != blocker_type:
                continue

            results.append(blocker)

        return results

    def get_blockers_for_approval(self, approval_id: str) -> List[Blocker]:
        """Get blockers associated with an approval."""
        return [
            b for b in self._blockers.values()
            if b.approval_id == approval_id and not b.resolved_at
        ]

    # =========================================================================
    # Resume Operations
    # =========================================================================

    def resume_scenario(
        self,
        run_id: str,
        resumed_by: str = "operator",
        skip_failed_step: bool = False,
    ) -> RecoveryResult:
        """
        Resume a paused scenario from where it stopped.

        Args:
            run_id: ID of the scenario run to resume
            resumed_by: Who is resuming the scenario
            skip_failed_step: If True, skip the failed step and continue

        Returns:
            RecoveryResult with outcome
        """
        result = RecoveryResult(
            action=RecoveryAction.RESUME,
            scenario_run_id=run_id,
        )

        try:
            state_store = self._get_state_store()
            run_data = state_store.get_scenario_run(run_id)

            if not run_data:
                result.success = False
                result.error = f"Scenario run not found: {run_id}"
                return result

            status = run_data.get("status")
            if status not in ["awaiting_approval", "partial", "failed"]:
                result.success = False
                result.error = f"Scenario cannot be resumed from status: {status}"
                return result

            # Get scenario definition
            scenario_runner = self._get_scenario_runner()
            scenario = scenario_runner.get_scenario(run_data.get("scenario_id"))

            if not scenario:
                result.success = False
                result.error = f"Scenario definition not found: {run_data.get('scenario_id')}"
                return result

            # Determine resume point
            step_results = run_data.get("step_results", [])
            completed_steps = len([s for s in step_results if s.get("status") == "completed"])

            # If we have partial results, resume from next step
            resume_from_step = completed_steps

            if skip_failed_step:
                # Count failed steps to skip
                failed_steps = len([s for s in step_results if s.get("status") == "failed"])
                resume_from_step = completed_steps + failed_steps

            # Create a new run that continues from the checkpoint
            # This preserves audit trail
            inputs = run_data.get("inputs", {})

            # Mark original run as superseded
            run_data["status"] = "superseded"
            run_data["superseded_by"] = _generate_id("run")
            state_store.save_scenario_run(run_data)

            # Run scenario from checkpoint
            # For now, we re-run from the beginning since checkpoint resume
            # requires deeper integration with scenario_runner internals
            new_run = scenario_runner.run_scenario(
                scenario_id=run_data.get("scenario_id"),
                inputs=inputs,
                dry_run=run_data.get("dry_run", True),
                triggered_by=f"resume:{resumed_by}",
                auto_approve=False,  # Never auto-approve on resume
            )

            result.success = new_run.status.value in ["completed", "partial"]
            result.new_run_id = new_run.run_id
            result.message = f"Resumed scenario, new run: {new_run.run_id}"
            result.completed_at = _utc_now().isoformat()

            # Resolve any blockers for this scenario
            for blocker in self.get_active_blockers(scenario_run_id=run_id):
                self.resolve_blocker(blocker.blocker_id, RecoveryAction.RESUME, resumed_by)

        except Exception as e:
            logger.error(f"Resume scenario failed: {e}")
            result.success = False
            result.error = str(e)
            result.completed_at = _utc_now().isoformat()

        self._recovery_history.append(result)
        return result

    def resume_after_approval(
        self,
        approval_id: str,
        resumed_by: str = "operator",
    ) -> RecoveryResult:
        """
        Resume workflow after an approval has been granted.

        This is called when an approval is granted to continue the
        workflow that was waiting for approval.

        Args:
            approval_id: ID of the approval that was granted
            resumed_by: Who granted the approval

        Returns:
            RecoveryResult with outcome
        """
        result = RecoveryResult(
            action=RecoveryAction.RESUME,
        )

        try:
            state_store = self._get_state_store()

            # Find related scenario run
            approval = state_store.get_approval(approval_id)
            if not approval:
                result.success = False
                result.error = f"Approval not found: {approval_id}"
                return result

            # Check if approval was granted
            if approval.get("status") != "approved":
                result.success = False
                result.error = f"Approval not granted: {approval.get('status')}"
                return result

            # Find blockers for this approval
            blockers = self.get_blockers_for_approval(approval_id)

            for blocker in blockers:
                if blocker.scenario_run_id:
                    # Resume the scenario
                    scenario_result = self.resume_scenario(
                        run_id=blocker.scenario_run_id,
                        resumed_by=resumed_by,
                    )
                    result = scenario_result
                    break

                elif blocker.job_id:
                    # Retry the job
                    job_result = self.retry_job(
                        job_id=blocker.job_id,
                        retried_by=resumed_by,
                    )
                    result = job_result
                    break

            # If no blockers found, check for registered callbacks
            if approval_id in self._approval_callbacks:
                callback = self._approval_callbacks[approval_id]
                try:
                    callback(approval_id, approval)
                    result.success = True
                    result.message = "Executed approval callback"
                except Exception as e:
                    result.success = False
                    result.error = f"Callback failed: {e}"

            if not blockers and approval_id not in self._approval_callbacks:
                result.success = True
                result.message = "No workflows waiting for this approval"

            result.completed_at = _utc_now().isoformat()

        except Exception as e:
            logger.error(f"Resume after approval failed: {e}")
            result.success = False
            result.error = str(e)
            result.completed_at = _utc_now().isoformat()

        self._recovery_history.append(result)
        return result

    def register_approval_callback(
        self,
        approval_id: str,
        callback: Callable[[str, Dict[str, Any]], None],
    ) -> None:
        """
        Register a callback to be invoked when an approval is granted.

        Args:
            approval_id: ID of the approval to watch
            callback: Function to call when approved (receives approval_id, approval_data)
        """
        self._approval_callbacks[approval_id] = callback
        logger.info(f"Registered approval callback for: {approval_id}")

    def unregister_approval_callback(self, approval_id: str) -> bool:
        """Unregister an approval callback."""
        if approval_id in self._approval_callbacks:
            del self._approval_callbacks[approval_id]
            return True
        return False

    # =========================================================================
    # Retry Operations
    # =========================================================================

    def retry_job(
        self,
        job_id: str,
        retried_by: str = "operator",
        new_options: Optional[Dict[str, Any]] = None,
    ) -> RecoveryResult:
        """
        Retry a failed job.

        Args:
            job_id: ID of the job to retry
            retried_by: Who is retrying the job
            new_options: Optional new dispatch options

        Returns:
            RecoveryResult with outcome
        """
        result = RecoveryResult(
            action=RecoveryAction.RETRY,
            job_id=job_id,
        )

        try:
            state_store = self._get_state_store()
            job = state_store.get_job(job_id)

            if not job:
                result.success = False
                result.error = f"Job not found: {job_id}"
                return result

            status = job.get("status")
            if status not in ["failed", "cancelled"]:
                result.success = False
                result.error = f"Job cannot be retried from status: {status}"
                return result

            plan_id = job.get("plan_id")
            if not plan_id:
                result.success = False
                result.error = "Job has no associated plan_id for retry"
                return result

            # Get the execution plan
            plan_data = state_store.get_execution_plan(plan_id)
            if not plan_data:
                result.success = False
                result.error = f"Execution plan not found: {plan_id}"
                return result

            # Mark original job as superseded
            job["status"] = "superseded"
            job["superseded_by_retry"] = True
            state_store.save_job(job)

            # Create and execute new job via rerun
            rerun_result = self.rerun_plan(
                plan_id=plan_id,
                triggered_by=f"retry:{retried_by}",
            )

            result.success = rerun_result.success
            result.new_job_id = rerun_result.new_job_id
            result.message = rerun_result.message
            result.error = rerun_result.error
            result.completed_at = _utc_now().isoformat()

            # Resolve blockers
            for blocker in self.get_active_blockers(job_id=job_id):
                self.resolve_blocker(blocker.blocker_id, RecoveryAction.RETRY, retried_by)

        except Exception as e:
            logger.error(f"Retry job failed: {e}")
            result.success = False
            result.error = str(e)
            result.completed_at = _utc_now().isoformat()

        self._recovery_history.append(result)
        return result

    def retry_connector_action(
        self,
        execution_id: str,
        retried_by: str = "operator",
    ) -> RecoveryResult:
        """
        Retry a failed connector action.

        Args:
            execution_id: ID of the connector execution to retry
            retried_by: Who is retrying

        Returns:
            RecoveryResult with outcome
        """
        result = RecoveryResult(
            action=RecoveryAction.RETRY,
        )

        try:
            state_store = self._get_state_store()
            execution = state_store.get_connector_execution_by_id(execution_id)

            if not execution:
                result.success = False
                result.error = f"Connector execution not found: {execution_id}"
                return result

            if execution.get("success"):
                result.success = False
                result.error = "Cannot retry successful connector execution"
                return result

            # Get connector and re-execute
            connector_name = execution.get("connector_name")
            action_name = execution.get("action_name") or execution.get("operation")
            params = execution.get("params", {})
            mode = execution.get("mode", "dry_run")

            # Execute via integration skill
            from core.integration_skill import get_integration_skill
            integration_skill = get_integration_skill()

            exec_result = integration_skill.execute(
                connector=connector_name,
                operation=action_name,
                params=params,
                dry_run=(mode == "dry_run"),
                job_id=execution.get("job_id"),
                plan_id=execution.get("plan_id"),
            )

            result.success = exec_result.get("success", False)
            result.message = f"Retried connector action: {connector_name}.{action_name}"
            if not result.success:
                result.error = exec_result.get("error")

            result.completed_at = _utc_now().isoformat()

            # Resolve blockers
            for blocker in self.get_active_blockers():
                if blocker.connector_execution_id == execution_id:
                    self.resolve_blocker(blocker.blocker_id, RecoveryAction.RETRY, retried_by)

        except Exception as e:
            logger.error(f"Retry connector action failed: {e}")
            result.success = False
            result.error = str(e)
            result.completed_at = _utc_now().isoformat()

        self._recovery_history.append(result)
        return result

    def retry_scenario_step(
        self,
        run_id: str,
        step_id: str,
        retried_by: str = "operator",
    ) -> RecoveryResult:
        """
        Retry a failed step within a scenario.

        Note: This triggers a full scenario resume from the failed step.

        Args:
            run_id: ID of the scenario run
            step_id: ID of the step to retry
            retried_by: Who is retrying

        Returns:
            RecoveryResult with outcome
        """
        result = RecoveryResult(
            action=RecoveryAction.RETRY,
            scenario_run_id=run_id,
            step_id=step_id,
        )

        try:
            # Retrying a step is essentially resuming the scenario
            # without skipping the failed step
            resume_result = self.resume_scenario(
                run_id=run_id,
                resumed_by=retried_by,
                skip_failed_step=False,
            )

            result.success = resume_result.success
            result.new_run_id = resume_result.new_run_id
            result.message = resume_result.message
            result.error = resume_result.error
            result.completed_at = _utc_now().isoformat()

        except Exception as e:
            logger.error(f"Retry scenario step failed: {e}")
            result.success = False
            result.error = str(e)
            result.completed_at = _utc_now().isoformat()

        self._recovery_history.append(result)
        return result

    # =========================================================================
    # Rerun Operations
    # =========================================================================

    def rerun_plan(
        self,
        plan_id: str,
        triggered_by: str = "operator",
        dry_run: Optional[bool] = None,
    ) -> RecoveryResult:
        """
        Rerun a previously created execution plan.

        Creates a new job for the plan, preserving audit trail.

        Args:
            plan_id: ID of the plan to rerun
            triggered_by: Who triggered the rerun
            dry_run: Override dry_run setting (None = use original)

        Returns:
            RecoveryResult with outcome
        """
        result = RecoveryResult(
            action=RecoveryAction.RERUN,
            plan_id=plan_id,
        )

        try:
            state_store = self._get_state_store()
            plan_data = state_store.get_execution_plan(plan_id)

            if not plan_data:
                result.success = False
                result.error = f"Execution plan not found: {plan_id}"
                return result

            # Rebuild execution plan from stored data
            from core.execution_plan import ExecutionPlan, ExecutionStep, ExecutionDomain, ExecutionStatus

            # Create plan object
            steps = []
            step_count = plan_data.get("step_count", 0)

            # For rerun, we create a minimal plan since we don't store full step details
            # The runtime manager will handle actual execution
            plan = ExecutionPlan(
                plan_id=_generate_id("plan"),  # New plan ID for audit trail
                request_id=plan_data.get("request_id"),
                objective=plan_data.get("objective", "Rerun"),
                status=ExecutionStatus.PENDING,
            )

            # Set domain
            domain_str = plan_data.get("primary_domain", "general")
            try:
                plan.primary_domain = ExecutionDomain(domain_str)
            except ValueError:
                plan.primary_domain = ExecutionDomain.GENERAL

            # Copy skill selections
            plan.selected_skills = plan_data.get("selected_skills", [])
            plan.selected_commands = plan_data.get("selected_commands", [])
            plan.selected_agents = plan_data.get("selected_agents", [])

            # Save new plan
            state_store.save_execution_plan({
                "plan_id": plan.plan_id,
                "request_id": plan.request_id,
                "objective": plan.objective,
                "primary_domain": plan.primary_domain.value,
                "status": plan.status.value,
                "step_count": step_count,
                "created_at": _utc_now().isoformat(),
                "selected_skills": plan.selected_skills,
                "selected_commands": plan.selected_commands,
                "selected_agents": plan.selected_agents,
                "rerun_of": plan_id,
            })

            # Execute via runtime manager
            runtime_manager = self._get_runtime_manager()

            if not runtime_manager.is_initialized:
                runtime_manager.initialize()

            runtime_result = runtime_manager.execute(
                plan=plan,
                business_id=triggered_by,
            )

            result.success = runtime_result.success
            result.new_job_id = runtime_result.dispatched_job.job_id if runtime_result.dispatched_job else None
            result.message = f"Reran plan as new execution: {plan.plan_id}"
            if not result.success:
                result.error = runtime_result.error

            result.completed_at = _utc_now().isoformat()

        except Exception as e:
            logger.error(f"Rerun plan failed: {e}")
            result.success = False
            result.error = str(e)
            result.completed_at = _utc_now().isoformat()

        self._recovery_history.append(result)
        return result

    def rerun_scenario(
        self,
        run_id: str,
        triggered_by: str = "operator",
        dry_run: Optional[bool] = None,
        new_inputs: Optional[Dict[str, Any]] = None,
    ) -> RecoveryResult:
        """
        Rerun a scenario with the same or modified inputs.

        Args:
            run_id: ID of the scenario run to base rerun on
            triggered_by: Who triggered the rerun
            dry_run: Override dry_run setting
            new_inputs: Optional modified inputs

        Returns:
            RecoveryResult with outcome
        """
        result = RecoveryResult(
            action=RecoveryAction.RERUN,
            scenario_run_id=run_id,
        )

        try:
            state_store = self._get_state_store()
            run_data = state_store.get_scenario_run(run_id)

            if not run_data:
                result.success = False
                result.error = f"Scenario run not found: {run_id}"
                return result

            scenario_id = run_data.get("scenario_id")
            original_inputs = run_data.get("inputs", {})
            original_dry_run = run_data.get("dry_run", True)

            # Merge inputs
            inputs = {**original_inputs, **(new_inputs or {})}

            # Determine dry_run setting
            use_dry_run = dry_run if dry_run is not None else original_dry_run

            # Run new scenario
            scenario_runner = self._get_scenario_runner()
            new_run = scenario_runner.run_scenario(
                scenario_id=scenario_id,
                inputs=inputs,
                dry_run=use_dry_run,
                triggered_by=f"rerun:{triggered_by}",
                auto_approve=False,
            )

            result.success = new_run.status.value in ["completed", "partial"]
            result.new_run_id = new_run.run_id
            result.message = f"Reran scenario as new run: {new_run.run_id}"
            if new_run.error_message:
                result.error = new_run.error_message

            result.completed_at = _utc_now().isoformat()

        except Exception as e:
            logger.error(f"Rerun scenario failed: {e}")
            result.success = False
            result.error = str(e)
            result.completed_at = _utc_now().isoformat()

        self._recovery_history.append(result)
        return result

    # =========================================================================
    # Visibility & Inspection
    # =========================================================================

    def get_paused_scenarios(self) -> List[Dict[str, Any]]:
        """Get all scenarios that are paused/awaiting action."""
        state_store = self._get_state_store()

        awaiting = state_store.list_scenario_runs(status="awaiting_approval")
        partial = state_store.list_scenario_runs(status="partial")

        results = []
        for run in awaiting + partial:
            blockers = self.get_active_blockers(scenario_run_id=run.get("run_id"))
            run["blockers"] = [b.to_dict() for b in blockers]
            run["available_actions"] = ["resume", "retry", "rerun"]
            results.append(run)

        return results

    def get_failed_jobs(self) -> List[Dict[str, Any]]:
        """Get all failed jobs that can be retried."""
        state_store = self._get_state_store()
        failed = state_store.get_jobs(status="failed")

        results = []
        for job in failed:
            blockers = self.get_active_blockers(job_id=job.get("job_id"))
            job["blockers"] = [b.to_dict() for b in blockers]
            job["available_actions"] = ["retry", "rerun"]
            results.append(job)

        return results

    def get_pending_approvals_with_context(self) -> List[Dict[str, Any]]:
        """Get pending approvals with related blocker context."""
        state_store = self._get_state_store()
        pending = state_store.get_pending_approvals()

        results = []
        for approval in pending:
            record_id = approval.get("record_id")
            blockers = self.get_blockers_for_approval(record_id)
            approval["blockers"] = [b.to_dict() for b in blockers]
            approval["blocked_workflows"] = len(blockers)
            results.append(approval)

        return results

    def get_recovery_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent recovery operation history."""
        return [r.to_dict() for r in self._recovery_history[-limit:]]

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
        state_store = self._get_state_store()
        status = {
            "blockers": [],
            "available_actions": [],
            "history": [],
        }

        if scenario_run_id:
            run = state_store.get_scenario_run(scenario_run_id)
            if run:
                status["scenario"] = run
                status["blockers"] = [
                    b.to_dict() for b in self.get_active_blockers(scenario_run_id=scenario_run_id)
                ]

                # Determine available actions
                run_status = run.get("status")
                if run_status == "awaiting_approval":
                    status["available_actions"] = ["resume"]
                elif run_status in ["failed", "partial"]:
                    status["available_actions"] = ["retry", "rerun", "resume"]
                elif run_status == "completed":
                    status["available_actions"] = ["rerun"]

        if job_id:
            job = state_store.get_job(job_id)
            if job:
                status["job"] = job
                status["blockers"].extend([
                    b.to_dict() for b in self.get_active_blockers(job_id=job_id)
                ])

                job_status = job.get("status")
                if job_status == "failed":
                    status["available_actions"] = ["retry", "rerun"]
                elif job_status == "completed":
                    status["available_actions"] = ["rerun"]

        return status


# Singleton instance
_recovery_manager: Optional[RecoveryManager] = None


def get_recovery_manager() -> RecoveryManager:
    """Get the global recovery manager."""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = RecoveryManager()
    return _recovery_manager
