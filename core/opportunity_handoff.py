"""
Opportunity Handoff for Project Alpha.

Handles transition from evaluated opportunities to execution planning.

ARCHITECTURE:
- HandoffMode: Pursue-now vs validate-first
- HandoffRecord: Full handoff tracking
- HandoffContext: Execution context from opportunity
- create_handoff: Main handoff orchestration

FLOW:
Opportunity (evaluated) → Handoff → Execution Plan → Governed Execution
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
import logging

from .discovery_models import (
    OpportunityRecord,
    OpportunityStatus,
    RecommendationAction,
    OperatorConstraints,
)
from .execution_plan import ExecutionDomain

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class HandoffMode(Enum):
    """Mode of opportunity handoff."""
    PURSUE_NOW = "pursue_now"           # Full execution path
    VALIDATE_FIRST = "validate_first"   # Validation-oriented path
    ARCHIVE = "archive"                 # Archive for later (no handoff)


class HandoffStatus(Enum):
    """Status of handoff."""
    PENDING = "pending"                 # Handoff created, not executed
    PLAN_CREATED = "plan_created"       # Execution plan generated
    EXECUTING = "executing"             # Execution in progress
    COMPLETED = "completed"             # Execution completed
    FAILED = "failed"                   # Handoff failed
    CANCELLED = "cancelled"             # Handoff cancelled


@dataclass
class HandoffContext:
    """
    Execution context derived from opportunity.

    Preserves key opportunity characteristics for execution planning.
    """
    opportunity_id: str
    opportunity_title: str

    # Discovery outputs to preserve
    target_audience: str
    problem_addressed: str
    proposed_solution: str
    monetization_path: str

    # Scoring signals for execution
    overall_score: float
    risk_level: float
    complexity_score: float              # Avg of startup + technical complexity
    speed_to_value: float                # Speed to revenue/validation
    automation_potential: float
    capital_sensitivity: float           # Capital intensity score

    # Domain and routing
    likely_domains: List[str]
    recommended_primary_domain: str

    # Operator constraints
    max_capital_available: float
    time_available_per_week: int
    risk_tolerance: str

    # Recommendation context
    recommendation_action: str
    recommendation_rationale: str
    next_steps: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "opportunity_title": self.opportunity_title,
            "target_audience": self.target_audience,
            "problem_addressed": self.problem_addressed,
            "proposed_solution": self.proposed_solution,
            "monetization_path": self.monetization_path,
            "overall_score": self.overall_score,
            "risk_level": self.risk_level,
            "complexity_score": self.complexity_score,
            "speed_to_value": self.speed_to_value,
            "automation_potential": self.automation_potential,
            "capital_sensitivity": self.capital_sensitivity,
            "likely_domains": self.likely_domains,
            "recommended_primary_domain": self.recommended_primary_domain,
            "max_capital_available": self.max_capital_available,
            "time_available_per_week": self.time_available_per_week,
            "risk_tolerance": self.risk_tolerance,
            "recommendation_action": self.recommendation_action,
            "recommendation_rationale": self.recommendation_rationale,
            "next_steps": self.next_steps,
            "warnings": self.warnings,
        }


@dataclass
class HandoffRecord:
    """
    Complete record of opportunity-to-execution handoff.

    Tracks the transition from evaluated opportunity to execution plan.
    """
    handoff_id: str
    opportunity_id: str
    mode: HandoffMode
    status: HandoffStatus

    # Handoff context
    handoff_context: HandoffContext

    # Execution linkage
    plan_id: Optional[str] = None
    job_ids: List[str] = field(default_factory=list)

    # Metadata
    created_by: str = "principal"
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    completed_at: Optional[datetime] = None

    # Notes and tracking
    operator_notes: str = ""
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "opportunity_id": self.opportunity_id,
            "mode": self.mode.value,
            "status": self.status.value,
            "handoff_context": self.handoff_context.to_dict(),
            "plan_id": self.plan_id,
            "job_ids": self.job_ids,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "operator_notes": self.operator_notes,
            "errors": self.errors,
        }


def create_handoff_context(
    opportunity: OpportunityRecord,
    constraints: Optional[OperatorConstraints] = None,
) -> HandoffContext:
    """
    Create handoff context from opportunity.

    Extracts and transforms opportunity data into execution-ready context.

    Args:
        opportunity: Opportunity record
        constraints: Optional operator constraints (uses snapshot if not provided)

    Returns:
        HandoffContext with execution signals
    """
    # Use provided constraints or snapshot
    if constraints is None and opportunity.operator_constraints_snapshot:
        constraints = OperatorConstraints.from_dict(
            opportunity.operator_constraints_snapshot
        )
    elif constraints is None:
        constraints = OperatorConstraints()  # Defaults

    # Calculate complexity score (average of startup and technical)
    complexity_score = (
        opportunity.score.startup_complexity +
        opportunity.score.technical_complexity
    ) / 2.0

    # Calculate speed to value (average of speed to revenue and validation)
    speed_to_value = (
        opportunity.score.speed_to_revenue +
        opportunity.score.speed_to_validation
    ) / 2.0

    # Determine recommended primary domain
    if opportunity.hypothesis.likely_domains:
        # Use first domain as primary
        recommended_primary_domain = opportunity.hypothesis.likely_domains[0]
    else:
        recommended_primary_domain = "unknown"

    return HandoffContext(
        opportunity_id=opportunity.opportunity_id,
        opportunity_title=opportunity.hypothesis.title,
        target_audience=opportunity.hypothesis.target_audience,
        problem_addressed=opportunity.hypothesis.problem_addressed,
        proposed_solution=opportunity.hypothesis.proposed_solution,
        monetization_path=opportunity.hypothesis.monetization_path.value,
        overall_score=opportunity.score.overall_score,
        risk_level=opportunity.score.risk_level,
        complexity_score=complexity_score,
        speed_to_value=speed_to_value,
        automation_potential=opportunity.score.automation_potential,
        capital_sensitivity=opportunity.score.capital_intensity,
        likely_domains=opportunity.hypothesis.likely_domains,
        recommended_primary_domain=recommended_primary_domain,
        max_capital_available=constraints.max_initial_capital,
        time_available_per_week=constraints.max_hours_per_week,
        risk_tolerance=constraints.risk_tolerance,
        recommendation_action=opportunity.recommendation.action.value,
        recommendation_rationale=opportunity.recommendation.rationale,
        next_steps=opportunity.recommendation.next_steps,
        warnings=opportunity.recommendation.warnings,
    )


def create_handoff(
    opportunity: OpportunityRecord,
    mode: HandoffMode,
    operator: str = "principal",
    notes: str = "",
) -> HandoffRecord:
    """
    Create handoff record from opportunity.

    Args:
        opportunity: Opportunity to hand off
        mode: Handoff mode (pursue/validate/archive)
        operator: Who is initiating handoff
        notes: Optional operator notes

    Returns:
        HandoffRecord ready for execution processing
    """
    handoff_id = f"handoff-{uuid.uuid4().hex[:12]}"

    # Create handoff context
    context = create_handoff_context(opportunity)

    # Set status based on mode
    status = HandoffStatus.COMPLETED if mode == HandoffMode.ARCHIVE else HandoffStatus.PENDING

    # Create handoff record
    handoff = HandoffRecord(
        handoff_id=handoff_id,
        opportunity_id=opportunity.opportunity_id,
        mode=mode,
        status=status,
        handoff_context=context,
        created_by=operator,
        operator_notes=notes,
        completed_at=_utc_now() if mode == HandoffMode.ARCHIVE else None,
    )

    logger.info(
        f"Created handoff {handoff_id} for opportunity {opportunity.opportunity_id} "
        f"in mode {mode.value} with status {status.value}"
    )

    return handoff


def determine_handoff_mode(opportunity: OpportunityRecord) -> HandoffMode:
    """
    Determine appropriate handoff mode based on recommendation.

    Args:
        opportunity: Opportunity record

    Returns:
        HandoffMode
    """
    recommendation = opportunity.recommendation.action

    if recommendation == RecommendationAction.PURSUE_NOW:
        return HandoffMode.PURSUE_NOW
    elif recommendation == RecommendationAction.VALIDATE_FIRST:
        return HandoffMode.VALIDATE_FIRST
    elif recommendation in [RecommendationAction.ARCHIVE, RecommendationAction.REJECT]:
        return HandoffMode.ARCHIVE
    else:
        # Default to validate first for unknown
        return HandoffMode.VALIDATE_FIRST
