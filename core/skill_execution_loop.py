"""
Skill Execution Loop - Core execution engine for Seed Core.

The fundamental learning loop:
1. Accept a goal
2. Rank skills by learned outcomes
3. Select and execute best skill
4. Capture outcome
5. Persist execution record
6. Update skill rankings

This is bounded, governed, and learns from real outcomes.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import hashlib

from .seed_models import (
    Goal,
    GoalStatus,
    SkillExecutionRecord,
    OutcomeType,
)
from .skill_ranker import SkillRanker, get_skill_ranker
from .seed_memory import SeedMemory, get_seed_memory
from .skill_registry import SkillDefinition
from .skill_invoker import SkillInvoker, get_skill_invoker, SkillExecutionMode
from .approval_manager import ApprovalManager, ApprovalRecord

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def _generate_id(prefix: str, text: str) -> str:
    """Generate a deterministic ID from text."""
    hash_part = hashlib.md5(text.encode()).hexdigest()[:12]
    timestamp = _utc_now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}_{hash_part}"


class SkillExecutionLoop:
    """
    Core execution loop for Seed Core.

    Executes skills, captures outcomes, learns from results.
    """

    def __init__(
        self,
        skill_ranker: Optional[SkillRanker] = None,
        seed_memory: Optional[SeedMemory] = None,
        skill_invoker: Optional[SkillInvoker] = None,
        approval_manager: Optional[ApprovalManager] = None,
    ):
        """
        Initialize the execution loop.

        Args:
            skill_ranker: SkillRanker instance. Uses global if not provided.
            seed_memory: SeedMemory instance. Uses global if not provided.
            skill_invoker: SkillInvoker instance. Uses global if not provided.
            approval_manager: ApprovalManager instance. Uses new instance if not provided.
        """
        self._skill_ranker = skill_ranker or get_skill_ranker()
        self._seed_memory = seed_memory or get_seed_memory()
        self._skill_invoker = skill_invoker or get_skill_invoker()
        self._approval_manager = approval_manager or ApprovalManager()
        self._skill_registry = None  # Can be injected for testing

    def execute_goal(
        self,
        goal: Goal,
        auto_select: bool = True,
        skill_name: Optional[str] = None,
    ) -> SkillExecutionRecord:
        """
        Execute a goal by selecting and running a skill.

        Args:
            goal: The goal to achieve
            auto_select: If True, automatically select best skill. If False, use skill_name.
            skill_name: Specific skill to use (if auto_select=False)

        Returns:
            SkillExecutionRecord capturing the outcome
        """
        logger.info(f"Executing goal: {goal.goal_id} - {goal.description}")

        # Select skill
        if auto_select:
            ranked_skill = self._skill_ranker.get_best_skill(
                goal_type=goal.goal_type,
                goal_description=goal.description,
            )

            if not ranked_skill:
                return self._create_failure_record(
                    goal=goal,
                    skill_name="none",
                    error_message="No relevant skills found for goal",
                    selection_reason="Auto-selection failed",
                )

            skill = ranked_skill.skill
            selection_reason = ranked_skill.selection_reason

        else:
            # Use specified skill
            if not skill_name:
                return self._create_failure_record(
                    goal=goal,
                    skill_name="none",
                    error_message="No skill specified",
                    selection_reason="Manual selection failed",
                )

            # Use injected registry if available (for testing), otherwise global
            if self._skill_registry:
                registry = self._skill_registry
            else:
                from .skill_registry import get_skill_registry
                registry = get_skill_registry()
                if not registry.is_loaded:
                    registry.load()

            skill = registry.get_skill(skill_name)
            if not skill:
                return self._create_failure_record(
                    goal=goal,
                    skill_name=skill_name,
                    error_message=f"Skill not found: {skill_name}",
                    selection_reason="Manual selection",
                )

            selection_reason = "Manual selection"

        logger.info(f"Selected skill: {skill.name} - {selection_reason}")

        # Check governance boundaries
        if skill.requires_approval:
            # Create approval request via ApprovalManager
            logger.info(f"Skill {skill.name} requires approval - requesting approval")
            return self._create_approval_request_record(
                goal=goal,
                skill=skill,
                selection_reason=selection_reason,
            )

        # Execute skill
        record = self._execute_skill(
            goal=goal,
            skill=skill,
            selection_reason=selection_reason,
        )

        # Persist execution record and update rankings
        success = self._seed_memory.save_execution_record(record)
        if success:
            logger.info(f"Execution record saved: {record.execution_id}")
        else:
            logger.error(f"Failed to save execution record: {record.execution_id}")

        # Update goal status
        if record.success:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = _utc_now().isoformat()
        else:
            goal.status = GoalStatus.FAILED

        self._seed_memory.save_goal(goal)

        return record

    def _execute_skill(
        self,
        goal: Goal,
        skill: SkillDefinition,
        selection_reason: str,
    ) -> SkillExecutionRecord:
        """
        Execute a skill for a goal.

        This is where actual skill invocation happens via SkillInvoker.

        Args:
            goal: The goal to achieve
            skill: The skill to execute
            selection_reason: Why this skill was selected

        Returns:
            SkillExecutionRecord with execution outcome
        """
        execution_id = _generate_id("exec", f"{goal.goal_id}_{skill.name}")

        # Invoke skill via SkillInvoker
        invocation_result = self._skill_invoker.invoke_skill(
            skill=skill,
            goal_description=goal.description,
            goal_type=goal.goal_type,
            params=goal.metadata.get("skill_params", {}),
        )

        # Map execution mode to outcome type
        outcome = self._map_mode_to_outcome(invocation_result.mode, invocation_result.success)

        # Calculate quality score from invocation result
        quality_score = self._calculate_quality_score(invocation_result)

        # Build execution context
        execution_context = {
            "skill_path": skill.path,
            "skill_category": skill.category.value,
            "is_proactive": skill.is_proactive,
            "requires_approval": skill.requires_approval,
            "execution_mode": invocation_result.mode.value,
            "duration_seconds": invocation_result.duration_seconds,
            "exit_code": invocation_result.exit_code,
        }
        execution_context.update(invocation_result.metadata)

        # Build result data
        result_data = {
            "invocation_mode": invocation_result.mode.value,
            "output": invocation_result.output,
            "timestamp": invocation_result.timestamp.isoformat(),
        }

        # Build notes
        notes = self._build_execution_notes(invocation_result)

        # Create execution record
        record = SkillExecutionRecord(
            execution_id=execution_id,
            goal_id=goal.goal_id,
            goal_type=goal.goal_type,
            skill_name=skill.name,
            outcome=outcome,
            quality_score=quality_score,
            notes=notes,
            selection_reason=selection_reason,
            success=invocation_result.success,
            error_message=invocation_result.error,
            execution_context=execution_context,
            result_data=result_data,
        )

        return record

    def _map_mode_to_outcome(
        self,
        mode: SkillExecutionMode,
        success: bool,
    ) -> OutcomeType:
        """Map execution mode and success to outcome type."""
        if mode == SkillExecutionMode.BLOCKED_POLICY:
            return OutcomeType.BLOCKED
        elif mode == SkillExecutionMode.BLOCKED_CREDENTIAL:
            return OutcomeType.BLOCKED
        elif mode == SkillExecutionMode.NOT_INVOKABLE:
            return OutcomeType.PARTIAL  # Partial because skill exists but can't invoke
        elif mode == SkillExecutionMode.DRY_RUN:
            return OutcomeType.PARTIAL  # Partial because simulated
        elif success:
            return OutcomeType.SUCCESS
        else:
            return OutcomeType.FAILURE

    def _calculate_quality_score(self, invocation_result) -> float:
        """Calculate quality score from invocation result."""
        if invocation_result.mode == SkillExecutionMode.BLOCKED_POLICY:
            return 0.0
        elif invocation_result.mode == SkillExecutionMode.BLOCKED_CREDENTIAL:
            return 0.0
        elif invocation_result.mode == SkillExecutionMode.NOT_INVOKABLE:
            return 0.3  # Skill exists but no path
        elif invocation_result.mode == SkillExecutionMode.DRY_RUN:
            return 0.5  # Neutral - simulated
        elif invocation_result.success:
            # Real execution succeeded
            # Could enhance with more sophisticated quality metrics
            return 0.9
        else:
            # Real execution failed
            return 0.2

    def _build_execution_notes(self, invocation_result) -> str:
        """Build human-readable notes from invocation result."""
        mode_str = invocation_result.mode.value.replace("_", " ").title()

        if invocation_result.success:
            note = f"{mode_str} execution completed successfully"
        else:
            note = f"{mode_str} execution failed"

        if invocation_result.error:
            note += f": {invocation_result.error}"

        if invocation_result.duration_seconds > 0:
            note += f" (duration: {invocation_result.duration_seconds:.2f}s)"

        return note

    def _create_failure_record(
        self,
        goal: Goal,
        skill_name: str,
        error_message: str,
        selection_reason: str,
    ) -> SkillExecutionRecord:
        """Create a failure execution record."""
        execution_id = _generate_id("exec", f"{goal.goal_id}_failure")

        return SkillExecutionRecord(
            execution_id=execution_id,
            goal_id=goal.goal_id,
            goal_type=goal.goal_type,
            skill_name=skill_name,
            outcome=OutcomeType.FAILURE,
            quality_score=0.0,
            notes="Execution failed before skill invocation",
            selection_reason=selection_reason,
            success=False,
            error_message=error_message,
        )

    def _create_approval_request_record(
        self,
        goal: Goal,
        skill: SkillDefinition,
        selection_reason: str,
    ) -> SkillExecutionRecord:
        """Create an execution record that requests approval."""
        execution_id = _generate_id("exec", f"{goal.goal_id}_approval")

        # Create approval record
        approval_record = ApprovalRecord(
            request_id=execution_id,
            policy_id="pol_skill_approval",
            action=f"execute_skill_{skill.name}",
            requester="seed_core",
            target_agent=skill.name,
            request_type="skill_execution",
            description=f"Execute skill '{skill.name}' for goal: {goal.description}",
            priority="medium",
            reason=f"Skill '{skill.name}' requires approval",
            context={
                "goal_id": goal.goal_id,
                "goal_type": goal.goal_type,
                "goal_description": goal.description,
                "skill_name": skill.name,
                "skill_category": skill.category.value,
            },
            risk_level="medium",
        )

        # Store in pending approvals
        self._approval_manager._pending_approvals[approval_record.record_id] = approval_record
        logger.info(f"Created approval request: {approval_record.record_id}")

        # Update goal status to awaiting approval
        goal.status = GoalStatus.AWAITING_APPROVAL
        self._seed_memory.save_goal(goal)

        # Create execution record with AWAITING_APPROVAL outcome
        record = SkillExecutionRecord(
            execution_id=execution_id,
            goal_id=goal.goal_id,
            goal_type=goal.goal_type,
            skill_name=skill.name,
            outcome=OutcomeType.AWAITING_APPROVAL,
            quality_score=0.0,  # No quality until execution happens
            notes=f"Awaiting approval to execute skill '{skill.name}'",
            selection_reason=selection_reason,
            success=False,  # Not executed yet
            error_message=None,
            execution_context={
                "skill_path": skill.path,
                "requires_approval": skill.requires_approval,
                "skill_category": skill.category.value,
            },
            approval_record_id=approval_record.record_id,
        )

        # Save the execution record (AWAITING_APPROVAL records need to be persisted)
        success = self._seed_memory.save_execution_record(record)
        if success:
            logger.info(f"Approval request execution record saved: {record.execution_id}")
        else:
            logger.error(f"Failed to save approval request execution record: {record.execution_id}")

        return record

    def resume_after_approval(
        self,
        execution_record: SkillExecutionRecord,
        approved: bool,
        approver: str,
        rationale: str = "",
    ) -> SkillExecutionRecord:
        """
        Resume execution after approval decision.

        Args:
            execution_record: Original execution record with AWAITING_APPROVAL outcome
            approved: Whether the request was approved
            approver: Who made the decision
            rationale: Rationale for the decision

        Returns:
            New SkillExecutionRecord with execution result or denial
        """
        if execution_record.outcome != OutcomeType.AWAITING_APPROVAL:
            logger.error(f"Cannot resume execution record {execution_record.execution_id} - not awaiting approval")
            raise ValueError("Cannot resume - execution record is not awaiting approval")

        if not execution_record.approval_record_id:
            logger.error(f"Cannot resume execution record {execution_record.execution_id} - no approval record ID")
            raise ValueError("Cannot resume - no approval record ID")

        # Update approval record
        if approved:
            self._approval_manager.approve(
                record_id=execution_record.approval_record_id,
                approver=approver,
                rationale=rationale,
            )
            logger.info(f"Approval granted for execution {execution_record.execution_id}")

            # Retrieve goal and skill
            goal = self._seed_memory.get_goal(execution_record.goal_id)
            if not goal:
                raise ValueError(f"Goal not found: {execution_record.goal_id}")

            # Use injected registry if available (for testing), otherwise global
            if self._skill_registry:
                registry = self._skill_registry
            else:
                from .skill_registry import get_skill_registry
                registry = get_skill_registry()
                if not registry.is_loaded:
                    registry.load()

            skill = registry.get_skill(execution_record.skill_name)
            if not skill:
                raise ValueError(f"Skill not found: {execution_record.skill_name}")

            # Update goal status back to in progress
            goal.status = GoalStatus.IN_PROGRESS
            self._seed_memory.save_goal(goal)

            # Execute the skill now that it's approved
            result_record = self._execute_skill(
                goal=goal,
                skill=skill,
                selection_reason=execution_record.selection_reason,
            )

            # Link to original approval
            result_record.approval_record_id = execution_record.approval_record_id

            # Save the new record
            self._seed_memory.save_execution_record(result_record)

            # Update goal status based on result
            if result_record.success:
                goal.status = GoalStatus.COMPLETED
                goal.completed_at = _utc_now().isoformat()
            else:
                goal.status = GoalStatus.FAILED

            self._seed_memory.save_goal(goal)

            return result_record

        else:
            # Approval denied
            self._approval_manager.deny(
                record_id=execution_record.approval_record_id,
                denier=approver,
                rationale=rationale,
            )
            logger.info(f"Approval denied for execution {execution_record.execution_id}")

            # Create denied execution record
            denied_record = SkillExecutionRecord(
                execution_id=_generate_id("exec", f"{execution_record.goal_id}_denied"),
                goal_id=execution_record.goal_id,
                goal_type=execution_record.goal_type,
                skill_name=execution_record.skill_name,
                outcome=OutcomeType.DENIED,
                quality_score=0.0,
                notes=f"Execution denied by {approver}: {rationale}",
                selection_reason=execution_record.selection_reason,
                success=False,
                error_message=f"Approval denied: {rationale}",
                execution_context=execution_record.execution_context.copy(),
                approval_record_id=execution_record.approval_record_id,
            )

            # Save denied record
            self._seed_memory.save_execution_record(denied_record)

            # Update goal status to failed
            goal = self._seed_memory.get_goal(execution_record.goal_id)
            if goal:
                goal.status = GoalStatus.FAILED
                self._seed_memory.save_goal(goal)

            return denied_record


# Singleton instance
_skill_execution_loop: Optional[SkillExecutionLoop] = None


def get_skill_execution_loop() -> SkillExecutionLoop:
    """Get the global SkillExecutionLoop instance."""
    global _skill_execution_loop
    if _skill_execution_loop is None:
        _skill_execution_loop = SkillExecutionLoop()
    return _skill_execution_loop
