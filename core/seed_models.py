"""
Seed Core Models - Data structures for the self-improving agent core.

These models capture the learning loop:
- Goal representation
- Skill execution outcomes
- Learned rankings
- Decomposed goal trees
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class GoalStatus(Enum):
    """Status of a goal."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DECOMPOSED = "decomposed"  # Goal was broken into sub-goals
    AWAITING_APPROVAL = "awaiting_approval"  # Waiting for operator approval


class OutcomeType(Enum):
    """Type of execution outcome."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    BLOCKED = "blocked"  # Could not execute due to governance/policy (permanent block)
    AWAITING_APPROVAL = "awaiting_approval"  # Waiting for approval to execute
    DENIED = "denied"  # Approval was denied


@dataclass
class Goal:
    """
    Represents a goal to be achieved.

    Can be a top-level goal or a sub-goal.
    """
    goal_id: str
    description: str
    goal_type: str  # e.g., "market_research", "integration_setup", "data_analysis"
    status: GoalStatus = GoalStatus.PENDING
    parent_goal_id: Optional[str] = None  # For sub-goals
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "goal_type": self.goal_type,
            "status": self.status.value,
            "parent_goal_id": self.parent_goal_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


@dataclass
class SkillExecutionRecord:
    """
    Record of a single skill execution attempt.

    This is the fundamental learning primitive - each execution
    teaches the system which skills work well for which goals.
    """
    execution_id: str
    goal_id: str
    goal_type: str
    skill_name: str
    outcome: OutcomeType
    quality_score: float  # 0.0 to 1.0
    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())
    notes: str = ""
    execution_context: Dict[str, Any] = field(default_factory=dict)

    # Why this skill was selected (for analysis)
    selection_reason: str = ""

    # Outcome details
    success: bool = False
    error_message: Optional[str] = None
    result_data: Dict[str, Any] = field(default_factory=dict)

    # Approval tracking (for governed execution)
    approval_record_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "goal_id": self.goal_id,
            "goal_type": self.goal_type,
            "skill_name": self.skill_name,
            "outcome": self.outcome.value,
            "quality_score": self.quality_score,
            "timestamp": self.timestamp,
            "notes": self.notes,
            "execution_context": self.execution_context,
            "selection_reason": self.selection_reason,
            "success": self.success,
            "error_message": self.error_message,
            "result_data": self.result_data,
            "approval_record_id": self.approval_record_id,
        }


@dataclass
class SkillRanking:
    """
    Learned ranking for a skill on a specific goal type.

    Updated incrementally as execution records accumulate.
    """
    goal_type: str
    skill_name: str
    total_executions: int = 0
    successful_executions: int = 0
    average_quality: float = 0.0
    last_execution: Optional[str] = None

    # Derived metrics
    success_rate: float = 0.0  # successful / total
    confidence: float = 0.0  # Based on sample size

    # Metadata
    updated_at: str = field(default_factory=lambda: _utc_now().isoformat())

    def update_from_execution(self, record: SkillExecutionRecord) -> None:
        """
        Update ranking based on a new execution record.

        Different outcome types affect ranking differently:
        - SUCCESS/FAILURE: Normal learning (counts as execution)
        - PARTIAL: Counts as execution but with lower quality
        - BLOCKED: Counts as execution but with 0 quality (permanent policy block)
        - AWAITING_APPROVAL: Does NOT count until resolved (pending state)
        - DENIED: Counts as execution with 0 quality (operator decision)
        """
        # AWAITING_APPROVAL doesn't count until resolved
        if record.outcome == OutcomeType.AWAITING_APPROVAL:
            return

        # All other outcomes count as executions
        self.total_executions += 1
        if record.success:
            self.successful_executions += 1

        # Update rolling average quality
        self.average_quality = (
            (self.average_quality * (self.total_executions - 1) + record.quality_score)
            / self.total_executions
        )

        # Update success rate
        self.success_rate = self.successful_executions / self.total_executions

        # Confidence increases with sample size (capped at 1.0)
        self.confidence = min(1.0, self.total_executions / 10.0)

        self.last_execution = record.timestamp
        self.updated_at = _utc_now().isoformat()

    def get_score(self) -> float:
        """
        Get composite score for ranking.

        Combines success rate, quality, and confidence.
        Higher is better.
        """
        # Weight success rate and quality equally, then multiply by confidence
        base_score = (self.success_rate * 0.5) + (self.average_quality * 0.5)
        return base_score * self.confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_type": self.goal_type,
            "skill_name": self.skill_name,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "average_quality": self.average_quality,
            "last_execution": self.last_execution,
            "success_rate": self.success_rate,
            "confidence": self.confidence,
            "updated_at": self.updated_at,
        }


@dataclass
class GoalDecomposition:
    """
    Record of a goal being decomposed into sub-goals.

    Tracks the decomposition strategy and sub-goal hierarchy.
    """
    decomposition_id: str
    parent_goal_id: str
    sub_goal_ids: List[str] = field(default_factory=list)
    decomposition_strategy: str = "default"  # Strategy used to decompose
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decomposition_id": self.decomposition_id,
            "parent_goal_id": self.parent_goal_id,
            "sub_goal_ids": self.sub_goal_ids,
            "decomposition_strategy": self.decomposition_strategy,
            "created_at": self.created_at,
            "notes": self.notes,
        }
