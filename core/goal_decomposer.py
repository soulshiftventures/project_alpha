"""
Goal Decomposer - Break complex goals into sub-goals for Seed Core.

When a single skill is insufficient, decompose the goal into smaller sub-goals
that can each be achieved with one skill execution.

Keeps decomposition simple and deterministic initially.
No fake autonomous planning - just practical goal breakdown.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone
import hashlib

from .seed_models import Goal, GoalStatus, GoalDecomposition

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def _generate_id(prefix: str, text: str) -> str:
    """Generate a deterministic ID from text."""
    hash_part = hashlib.md5(text.encode()).hexdigest()[:12]
    timestamp = _utc_now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}_{hash_part}"


class GoalDecomposer:
    """
    Decomposes complex goals into achievable sub-goals.

    Strategies:
    - Sequential: Break goal into ordered steps
    - Parallel: Break goal into independent sub-tasks
    - Hierarchical: Multi-level decomposition
    """

    def decompose_goal(
        self,
        goal: Goal,
        strategy: str = "sequential",
    ) -> Optional[GoalDecomposition]:
        """
        Decompose a goal into sub-goals.

        Args:
            goal: The goal to decompose
            strategy: Decomposition strategy ("sequential", "parallel", "hierarchical")

        Returns:
            GoalDecomposition with sub-goals, or None if decomposition not needed
        """
        # Determine if decomposition is needed
        if not self._needs_decomposition(goal):
            logger.info(f"Goal {goal.goal_id} does not need decomposition")
            return None

        # Apply strategy
        if strategy == "sequential":
            return self._decompose_sequential(goal)
        elif strategy == "parallel":
            return self._decompose_parallel(goal)
        elif strategy == "hierarchical":
            return self._decompose_hierarchical(goal)
        else:
            logger.warning(f"Unknown decomposition strategy: {strategy}")
            return self._decompose_sequential(goal)

    def _needs_decomposition(self, goal: Goal) -> bool:
        """
        Determine if a goal needs decomposition.

        Simple heuristic:
        - Long descriptions suggest complex goals
        - Certain goal types are known to be complex
        - Explicit decomposition markers in description
        """
        description = goal.description.lower()

        # Check for explicit decomposition markers
        markers = [
            "and then",
            "after that",
            "first",
            "second",
            "third",
            "finally",
            "multiple",
            "several",
        ]

        for marker in markers:
            if marker in description:
                return True

        # Check goal type patterns
        complex_goal_types = {
            "market_research",
            "integration_setup",
            "system_migration",
            "data_pipeline",
            "multi_step_workflow",
        }

        if goal.goal_type in complex_goal_types:
            return True

        # Check description length (rough heuristic)
        if len(description) > 200:
            return True

        return False

    def _decompose_sequential(self, goal: Goal) -> GoalDecomposition:
        """
        Decompose into sequential sub-goals.

        Identifies explicit steps or creates logical sequence.
        """
        description = goal.description

        # Try to extract explicit steps
        sub_goal_descriptions = self._extract_steps(description)

        if not sub_goal_descriptions:
            # Fall back to simple 3-step pattern
            sub_goal_descriptions = self._create_default_steps(goal)

        # Create sub-goals
        sub_goals = []
        for i, sub_desc in enumerate(sub_goal_descriptions):
            sub_goal = Goal(
                goal_id=_generate_id("subgoal", f"{goal.goal_id}_{i}"),
                description=sub_desc,
                goal_type=goal.goal_type,  # Inherit type
                status=GoalStatus.PENDING,
                parent_goal_id=goal.goal_id,
                metadata={
                    "step_number": i + 1,
                    "total_steps": len(sub_goal_descriptions),
                    "decomposition_strategy": "sequential",
                },
            )
            sub_goals.append(sub_goal)

        # Create decomposition record
        decomposition = GoalDecomposition(
            decomposition_id=_generate_id("decomp", goal.goal_id),
            parent_goal_id=goal.goal_id,
            sub_goal_ids=[sg.goal_id for sg in sub_goals],
            decomposition_strategy="sequential",
            notes=f"Decomposed into {len(sub_goals)} sequential steps",
        )

        # Store sub-goals in metadata for now (caller should persist properly)
        decomposition.metadata = {"sub_goals": [sg.to_dict() for sg in sub_goals]}

        return decomposition

    def _decompose_parallel(self, goal: Goal) -> GoalDecomposition:
        """
        Decompose into parallel sub-goals.

        Identifies independent tasks that can run concurrently.
        """
        description = goal.description

        # Try to extract parallel tasks (look for "and" patterns)
        sub_goal_descriptions = self._extract_parallel_tasks(description)

        if not sub_goal_descriptions:
            # Fall back to default
            sub_goal_descriptions = self._create_default_steps(goal)

        # Create sub-goals
        sub_goals = []
        for i, sub_desc in enumerate(sub_goal_descriptions):
            sub_goal = Goal(
                goal_id=_generate_id("subgoal", f"{goal.goal_id}_{i}"),
                description=sub_desc,
                goal_type=goal.goal_type,
                status=GoalStatus.PENDING,
                parent_goal_id=goal.goal_id,
                metadata={
                    "task_number": i + 1,
                    "total_tasks": len(sub_goal_descriptions),
                    "decomposition_strategy": "parallel",
                },
            )
            sub_goals.append(sub_goal)

        decomposition = GoalDecomposition(
            decomposition_id=_generate_id("decomp", goal.goal_id),
            parent_goal_id=goal.goal_id,
            sub_goal_ids=[sg.goal_id for sg in sub_goals],
            decomposition_strategy="parallel",
            notes=f"Decomposed into {len(sub_goals)} parallel tasks",
        )

        decomposition.metadata = {"sub_goals": [sg.to_dict() for sg in sub_goals]}

        return decomposition

    def _decompose_hierarchical(self, goal: Goal) -> GoalDecomposition:
        """
        Multi-level decomposition.

        For now, just alias to sequential. Future: true hierarchy.
        """
        return self._decompose_sequential(goal)

    def _extract_steps(self, description: str) -> List[str]:
        """
        Extract explicit steps from description.

        Looks for patterns like:
        - "1. step one 2. step two"
        - "First X, then Y, finally Z"
        - "Step 1: X Step 2: Y"
        """
        import re

        steps = []

        # Pattern 1: Numbered lists "1. X 2. Y"
        numbered = re.findall(r'\d+\.\s*([^.\d]+(?:\.|$))', description)
        if numbered:
            steps = [s.strip().rstrip('.') for s in numbered]
            return steps

        # Pattern 2: "First X, then Y, finally Z"
        sequence_markers = [
            (r'first[,:]?\s*([^,;]+)', 1),
            (r'then[,:]?\s*([^,;]+)', 2),
            (r'(?:finally|lastly)[,:]?\s*([^,;]+)', 3),
        ]

        for pattern, order in sequence_markers:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                steps.append((order, match.group(1).strip()))

        if steps:
            steps.sort(key=lambda x: x[0])
            return [s[1] for s in steps]

        # Pattern 3: Sentences with "and then" or "after that"
        sentences = re.split(r'(?:and then|after that|next)', description, flags=re.IGNORECASE)
        if len(sentences) > 1:
            return [s.strip() for s in sentences if s.strip()]

        return []

    def _extract_parallel_tasks(self, description: str) -> List[str]:
        """
        Extract parallel tasks from description.

        Looks for "X and Y and Z" patterns or comma-separated lists.
        """
        import re

        # Split on "and" or commas
        tasks = re.split(r'\s+and\s+|,\s*', description)

        if len(tasks) > 1:
            return [t.strip() for t in tasks if t.strip()]

        return []

    def _create_default_steps(self, goal: Goal) -> List[str]:
        """
        Create default 3-step breakdown for any goal.

        Generic but functional decomposition:
        1. Prepare / Research
        2. Execute / Implement
        3. Verify / Complete
        """
        goal_desc = goal.description

        return [
            f"Prepare and research for: {goal_desc}",
            f"Execute main task: {goal_desc}",
            f"Verify and complete: {goal_desc}",
        ]


# Singleton instance
_goal_decomposer: Optional[GoalDecomposer] = None


def get_goal_decomposer() -> GoalDecomposer:
    """Get the global GoalDecomposer instance."""
    global _goal_decomposer
    if _goal_decomposer is None:
        _goal_decomposer = GoalDecomposer()
    return _goal_decomposer
