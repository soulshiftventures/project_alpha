"""
Seed Core v1 - The Self-Improving Agent Core

This is the missing heart of the system.

What Seed Core v1 does:
1. Accept a real goal
2. Inspect available skills and system state
3. Select best skill based on learned outcomes
4. Execute that skill in a bounded way
5. Observe outcome quality
6. Persist the result
7. Improve future skill selection based on actual outcomes
8. Decompose goals into sub-goals when one skill is insufficient

What Seed Core is NOT:
- Not the old hierarchical orchestrator
- Not hardcoded role routing
- Not fake autonomous planning
- Not more generic subsystems

It's a small real learning core that gets better with each execution.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import hashlib

from .seed_models import Goal, GoalStatus, SkillExecutionRecord, OutcomeType
from .skill_execution_loop import SkillExecutionLoop, get_skill_execution_loop
from .skill_ranker import SkillRanker, get_skill_ranker
from .goal_decomposer import GoalDecomposer, get_goal_decomposer
from .seed_memory import SeedMemory, get_seed_memory, initialize_seed_memory
from .skill_registry import SkillRegistry, get_skill_registry

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def _generate_id(prefix: str, text: str) -> str:
    """Generate a deterministic ID from text."""
    hash_part = hashlib.md5(text.encode()).hexdigest()[:12]
    timestamp = _utc_now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}_{hash_part}"


class SeedCore:
    """
    The self-improving agent core.

    Minimal, honest, learning from real outcomes.
    """

    def __init__(
        self,
        skill_registry: Optional[SkillRegistry] = None,
        seed_memory: Optional[SeedMemory] = None,
        skill_ranker: Optional[SkillRanker] = None,
        skill_execution_loop: Optional[SkillExecutionLoop] = None,
        goal_decomposer: Optional[GoalDecomposer] = None,
    ):
        """
        Initialize Seed Core.

        Args:
            skill_registry: SkillRegistry instance. Uses global if not provided.
            seed_memory: SeedMemory instance. Uses global if not provided.
            skill_ranker: SkillRanker instance. Uses global if not provided.
            skill_execution_loop: SkillExecutionLoop instance. Uses global if not provided.
            goal_decomposer: GoalDecomposer instance. Uses global if not provided.
        """
        self._skill_registry = skill_registry or get_skill_registry()
        self._seed_memory = seed_memory or get_seed_memory()
        self._skill_ranker = skill_ranker or get_skill_ranker()
        self._execution_loop = skill_execution_loop or get_skill_execution_loop()
        self._goal_decomposer = goal_decomposer or get_goal_decomposer()

        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize Seed Core.

        Loads skills, initializes memory, ready for execution.

        Returns:
            True if initialized successfully
        """
        try:
            # Load skills
            if not self._skill_registry.is_loaded:
                success = self._skill_registry.load()
                if not success:
                    logger.error(f"Failed to load skills: {self._skill_registry.load_error}")
                    return False

            logger.info(f"Loaded {self._skill_registry.skill_count} skills")

            # Initialize memory
            if not self._seed_memory._initialized:
                success = self._seed_memory.initialize()
                if not success:
                    logger.error("Failed to initialize seed memory")
                    return False

            stats = self._seed_memory.get_stats()
            logger.info(f"Seed memory initialized: {stats}")

            self._initialized = True
            logger.info("Seed Core v1 initialized")
            return True

        except Exception as e:
            logger.error(f"Seed Core initialization failed: {e}")
            return False

    @property
    def is_initialized(self) -> bool:
        """Check if Seed Core is initialized."""
        return self._initialized

    # =========================================================================
    # Core Interface
    # =========================================================================

    def achieve_goal(
        self,
        description: str,
        goal_type: str,
        allow_decomposition: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Achieve a goal using Seed Core learning.

        This is the main entry point.

        Args:
            description: What to achieve
            goal_type: Type of goal (e.g., "market_research", "integration_setup")
            allow_decomposition: If True, decompose complex goals
            metadata: Optional metadata for the goal

        Returns:
            Dict with:
            - goal: Goal object
            - execution_records: List of execution records
            - success: Overall success
            - message: Human-readable outcome
        """
        if not self._initialized:
            return {
                "success": False,
                "message": "Seed Core not initialized",
            }

        # Create goal
        goal = Goal(
            goal_id=_generate_id("goal", description),
            description=description,
            goal_type=goal_type,
            status=GoalStatus.PENDING,
            metadata=metadata or {},
        )

        # Save goal
        self._seed_memory.save_goal(goal)

        logger.info(f"Starting goal: {goal.goal_id} - {description}")

        # Check if decomposition needed
        if allow_decomposition and self._goal_decomposer._needs_decomposition(goal):
            logger.info("Goal needs decomposition")
            return self._achieve_goal_with_decomposition(goal)
        else:
            logger.info("Attempting single-skill execution")
            return self._achieve_goal_single_skill(goal)

    def _achieve_goal_single_skill(self, goal: Goal) -> Dict[str, Any]:
        """Achieve a goal with a single skill execution."""
        goal.status = GoalStatus.IN_PROGRESS
        self._seed_memory.save_goal(goal)

        # Execute goal
        record = self._execution_loop.execute_goal(goal)

        # Build response
        return {
            "goal": goal.to_dict(),
            "execution_records": [record.to_dict()],
            "success": record.success,
            "message": (
                f"Goal completed with skill {record.skill_name}"
                if record.success
                else f"Goal failed: {record.error_message}"
            ),
        }

    def _achieve_goal_with_decomposition(self, goal: Goal) -> Dict[str, Any]:
        """Achieve a goal by decomposing into sub-goals."""
        # Decompose goal
        decomposition = self._goal_decomposer.decompose_goal(goal, strategy="sequential")

        if not decomposition:
            # Decomposition not possible, fall back to single execution
            logger.warning("Decomposition failed, falling back to single execution")
            return self._achieve_goal_single_skill(goal)

        # Mark parent goal as decomposed
        goal.status = GoalStatus.DECOMPOSED
        self._seed_memory.save_goal(goal)
        self._seed_memory.save_decomposition(decomposition)

        logger.info(f"Decomposed goal into {len(decomposition.sub_goal_ids)} sub-goals")

        # Extract sub-goals from metadata
        sub_goals_data = decomposition.metadata.get("sub_goals", [])
        if not sub_goals_data:
            return {
                "goal": goal.to_dict(),
                "success": False,
                "message": "Decomposition failed: no sub-goals created",
            }

        # Execute each sub-goal
        all_records = []
        all_success = True

        for sub_goal_data in sub_goals_data:
            sub_goal = Goal(
                goal_id=sub_goal_data["goal_id"],
                description=sub_goal_data["description"],
                goal_type=sub_goal_data["goal_type"],
                status=GoalStatus(sub_goal_data["status"]),
                parent_goal_id=sub_goal_data.get("parent_goal_id"),
                created_at=sub_goal_data["created_at"],
                metadata=sub_goal_data.get("metadata", {}),
            )

            # Execute sub-goal (no recursion - single skill per sub-goal)
            sub_result = self._achieve_goal_single_skill(sub_goal)
            all_records.extend(sub_result["execution_records"])

            if not sub_result["success"]:
                all_success = False
                logger.warning(f"Sub-goal failed: {sub_goal.goal_id}")
                # Continue with remaining sub-goals for now

        # Update parent goal status
        if all_success:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = _utc_now().isoformat()
        else:
            goal.status = GoalStatus.FAILED

        self._seed_memory.save_goal(goal)

        return {
            "goal": goal.to_dict(),
            "decomposition": decomposition.to_dict(),
            "execution_records": all_records,
            "success": all_success,
            "message": (
                f"Goal completed via decomposition ({len(all_records)} executions)"
                if all_success
                else f"Goal partially completed ({len(all_records)} executions, some failed)"
            ),
        }

    # =========================================================================
    # Introspection
    # =========================================================================

    def introspect(self) -> Dict[str, Any]:
        """
        Introspect current system state.

        Returns:
            Dict with:
            - skills_available: Number of skills
            - skills_by_category: Skill counts by category
            - memory_stats: Learning statistics
            - top_skills: Best-performing skills by goal type
        """
        if not self._initialized:
            return {"error": "Not initialized"}

        # Skill stats
        skills_available = self._skill_registry.skill_count
        skills_by_category = {
            cat.value: count
            for cat, count in self._skill_registry.list_categories().items()
        }

        # Memory stats
        memory_stats = self._seed_memory.get_stats()

        # Top skills by goal type
        all_rankings = self._seed_memory.get_all_rankings()
        top_skills = {}

        for goal_type, rankings in all_rankings.items():
            sorted_rankings = sorted(rankings, key=lambda r: r.get_score(), reverse=True)
            top_skills[goal_type] = [
                {
                    "skill_name": r.skill_name,
                    "score": r.get_score(),
                    "success_rate": r.success_rate,
                    "average_quality": r.average_quality,
                    "total_executions": r.total_executions,
                }
                for r in sorted_rankings[:5]
            ]

        return {
            "initialized": self._initialized,
            "skills_available": skills_available,
            "skills_by_category": skills_by_category,
            "memory_stats": memory_stats,
            "top_skills_by_goal_type": top_skills,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get Seed Core statistics."""
        return self.introspect()

    def explain_skill_selection(self, goal_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Explain why skills are ranked as they are for a goal type.

        Args:
            goal_type: Type of goal
            limit: Number of skills to explain

        Returns:
            List of skill explanations with rankings
        """
        return self._skill_ranker.explain_ranking(goal_type, limit=limit)

    # =========================================================================
    # Approval Workflow
    # =========================================================================

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """
        Get all pending approval requests.

        Returns:
            List of pending approval records with associated execution context
        """
        pending = self._execution_loop._approval_manager.get_pending()
        return [record.to_dict() for record in pending]

    def resume_after_approval(
        self,
        execution_id: str,
        approved: bool,
        approver: str = "operator",
        rationale: str = "",
    ) -> Dict[str, Any]:
        """
        Resume execution after approval decision.

        Args:
            execution_id: ID of the execution record awaiting approval
            approved: Whether the request was approved
            approver: Who made the decision
            rationale: Rationale for the decision

        Returns:
            Dict with:
            - success: Whether resume succeeded
            - execution_record: The resulting execution record
            - message: Human-readable outcome
        """
        if not self._initialized:
            return {
                "success": False,
                "message": "Seed Core not initialized",
            }

        # Retrieve the original execution record
        records = self._seed_memory.get_execution_records(limit=1000)
        original_record = None
        for record in records:
            if record.execution_id == execution_id:
                original_record = record
                break

        if not original_record:
            return {
                "success": False,
                "message": f"Execution record not found: {execution_id}",
            }

        if original_record.outcome != OutcomeType.AWAITING_APPROVAL:
            return {
                "success": False,
                "message": f"Execution record {execution_id} is not awaiting approval (status: {original_record.outcome.value})",
            }

        # Resume execution via execution loop
        try:
            result_record = self._execution_loop.resume_after_approval(
                execution_record=original_record,
                approved=approved,
                approver=approver,
                rationale=rationale,
            )

            action = "approved" if approved else "denied"
            return {
                "success": True,
                "execution_record": result_record.to_dict(),
                "message": (
                    f"Execution {action} and {'completed' if result_record.success else 'failed'}"
                    if approved
                    else f"Execution {action}"
                ),
            }

        except Exception as e:
            logger.error(f"Failed to resume execution {execution_id}: {e}")
            return {
                "success": False,
                "message": f"Failed to resume: {str(e)}",
            }


# Singleton instance
_seed_core: Optional[SeedCore] = None


def get_seed_core() -> SeedCore:
    """Get the global Seed Core instance."""
    global _seed_core
    if _seed_core is None:
        _seed_core = SeedCore()
    return _seed_core


def initialize_seed_core() -> SeedCore:
    """Initialize and return the global Seed Core instance."""
    core = get_seed_core()
    core.initialize()
    return core
