"""
Discovery Models for Project Alpha.

Data structures for Business Discovery Layer that supports moving from
rough ideas, problems, interests, or opportunity spaces into structured
business opportunities.

ARCHITECTURE:
- RawInput: Unstructured idea/problem/opportunity intake
- OperatorConstraints: Principal's preferences and limitations
- OpportunityHypothesis: Structured opportunity representation
- OpportunityScore: Multi-dimensional evaluation score
- OpportunityRecommendation: Actionable next-step guidance
- OpportunityRecord: Full persisted opportunity with history

DETERMINISTIC:
- All scoring is deterministic and testable
- No fake deep intelligence claims
- Uses heuristics and weighted scoring
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class InputType(Enum):
    """Type of raw input received."""
    IDEA = "idea"                           # Rough business idea
    PROBLEM = "problem"                     # Problem/pain point observed
    OPPORTUNITY = "opportunity"             # Market opportunity space
    CURIOSITY = "curiosity"                 # Interest/niche exploration
    HYBRID = "hybrid"                       # Mixed or unclear


class OpportunityStatus(Enum):
    """Lifecycle status of opportunity."""
    DRAFT = "draft"                         # Being evaluated
    EVALUATED = "evaluated"                 # Scored and recommended
    PURSUE = "pursue"                       # Approved to pursue
    VALIDATE = "validate"                   # Needs validation first
    ARCHIVED = "archived"                   # Saved for later
    REJECTED = "rejected"                   # Not worth pursuing


class RecommendationAction(Enum):
    """Recommended next action for opportunity."""
    PURSUE_NOW = "pursue_now"               # High confidence, good fit
    VALIDATE_FIRST = "validate_first"       # Needs validation/testing
    ARCHIVE = "archive"                     # Interesting but not now
    REJECT = "reject"                       # Poor fit or too risky


class MonetizationPath(Enum):
    """How opportunity generates revenue."""
    SUBSCRIPTION = "subscription"           # Recurring subscription
    ONE_TIME_SALE = "one_time_sale"        # One-time purchase
    TRANSACTION_FEE = "transaction_fee"    # Fee per transaction
    ADVERTISING = "advertising"             # Ad-based revenue
    AFFILIATE = "affiliate"                 # Affiliate commissions
    LICENSING = "licensing"                 # License/royalty
    SERVICE = "service"                     # Service delivery
    HYBRID = "hybrid"                       # Multiple paths
    UNCLEAR = "unclear"                     # Not yet defined


@dataclass
class OperatorConstraints:
    """
    Principal's constraints and preferences that influence opportunity scoring.

    These constraints ensure opportunities are evaluated against the operator's
    actual situation, not just theoretical attractiveness.
    """
    # Financial constraints
    max_initial_capital: float = 5000.0        # Max upfront investment
    monthly_budget: float = 500.0              # Monthly operating budget
    target_monthly_revenue: float = 10000.0    # Revenue goal

    # Time/energy constraints
    max_hours_per_week: int = 20               # Available time
    energy_level: str = "medium"               # low, medium, high
    technical_complexity_tolerance: str = "medium"  # low, medium, high

    # Preferences
    automation_preference: str = "high"        # low, medium, high
    hands_on_vs_hands_off: str = "hands_off"  # hands_on, balanced, hands_off
    risk_tolerance: str = "medium"             # low, medium, high
    speed_priority: str = "high"               # low, medium, high (speed to revenue)

    # Domain preferences (can prefer or avoid certain domains)
    preferred_domains: List[str] = field(default_factory=list)
    avoided_domains: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_initial_capital": self.max_initial_capital,
            "monthly_budget": self.monthly_budget,
            "target_monthly_revenue": self.target_monthly_revenue,
            "max_hours_per_week": self.max_hours_per_week,
            "energy_level": self.energy_level,
            "technical_complexity_tolerance": self.technical_complexity_tolerance,
            "automation_preference": self.automation_preference,
            "hands_on_vs_hands_off": self.hands_on_vs_hands_off,
            "risk_tolerance": self.risk_tolerance,
            "speed_priority": self.speed_priority,
            "preferred_domains": self.preferred_domains,
            "avoided_domains": self.avoided_domains,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperatorConstraints":
        return cls(
            max_initial_capital=data.get("max_initial_capital", 5000.0),
            monthly_budget=data.get("monthly_budget", 500.0),
            target_monthly_revenue=data.get("target_monthly_revenue", 10000.0),
            max_hours_per_week=data.get("max_hours_per_week", 20),
            energy_level=data.get("energy_level", "medium"),
            technical_complexity_tolerance=data.get("technical_complexity_tolerance", "medium"),
            automation_preference=data.get("automation_preference", "high"),
            hands_on_vs_hands_off=data.get("hands_on_vs_hands_off", "hands_off"),
            risk_tolerance=data.get("risk_tolerance", "medium"),
            speed_priority=data.get("speed_priority", "high"),
            preferred_domains=data.get("preferred_domains", []),
            avoided_domains=data.get("avoided_domains", []),
        )


@dataclass
class RawInput:
    """
    Raw, unstructured input from operator about an idea, problem, or opportunity.

    Supports rough, ambiguous input - the system normalizes this into
    structured opportunities.
    """
    input_id: str
    input_type: InputType
    raw_text: str
    submitted_by: str = "principal"
    submitted_at: datetime = field(default_factory=_utc_now)
    tags: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_id": self.input_id,
            "input_type": self.input_type.value,
            "raw_text": self.raw_text,
            "submitted_by": self.submitted_by,
            "submitted_at": self.submitted_at.isoformat(),
            "tags": self.tags,
            "context": self.context,
        }


@dataclass
class OpportunityHypothesis:
    """
    Structured opportunity hypothesis derived from raw input.

    Represents a coherent business opportunity with defined audience,
    problem, and monetization path.
    """
    hypothesis_id: str
    title: str
    description: str

    # Core opportunity elements
    target_audience: str                        # Who is this for?
    problem_addressed: str                      # What problem does this solve?
    proposed_solution: str                      # How does this solve it?
    monetization_path: MonetizationPath         # How does this make money?

    # Opportunity characteristics
    likely_domains: List[str] = field(default_factory=list)  # execution domains
    market_size_estimate: str = "unknown"       # small, medium, large, unknown
    competition_level: str = "unknown"          # low, medium, high, unknown

    # Derived from input
    source_input_id: Optional[str] = None
    created_at: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "title": self.title,
            "description": self.description,
            "target_audience": self.target_audience,
            "problem_addressed": self.problem_addressed,
            "proposed_solution": self.proposed_solution,
            "monetization_path": self.monetization_path.value,
            "likely_domains": self.likely_domains,
            "market_size_estimate": self.market_size_estimate,
            "competition_level": self.competition_level,
            "source_input_id": self.source_input_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class OpportunityScore:
    """
    Multi-dimensional score for an opportunity.

    Uses practical dimensions that affect startup success.
    All scores are 0.0 to 1.0, deterministically calculated.
    """
    opportunity_id: str

    # Market attractiveness (0.0 - 1.0)
    market_attractiveness: float = 0.5          # Based on size, growth, competition
    monetization_clarity: float = 0.5           # How clear is revenue path?

    # Execution difficulty (0.0 - 1.0, lower is easier)
    startup_complexity: float = 0.5             # How complex to start?
    technical_complexity: float = 0.5           # How technical?
    capital_intensity: float = 0.5              # How much capital needed?
    operational_burden: float = 0.5             # How much ongoing work?

    # Speed and risk (0.0 - 1.0)
    speed_to_revenue: float = 0.5               # How fast to first dollar?
    speed_to_validation: float = 0.5            # How fast to test hypothesis?
    risk_level: float = 0.5                     # Overall risk (lower is better)

    # Fit with operator (0.0 - 1.0)
    automation_potential: float = 0.5           # How automatable?
    scalability_potential: float = 0.5          # How scalable?
    constraint_fit: float = 0.5                 # Fit with operator constraints

    # Overall composite score (0.0 - 1.0)
    overall_score: float = 0.5
    confidence: float = 0.5                     # Confidence in scoring (0.0 - 1.0)

    # Metadata
    scored_at: datetime = field(default_factory=_utc_now)
    scoring_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "market_attractiveness": self.market_attractiveness,
            "monetization_clarity": self.monetization_clarity,
            "startup_complexity": self.startup_complexity,
            "technical_complexity": self.technical_complexity,
            "capital_intensity": self.capital_intensity,
            "operational_burden": self.operational_burden,
            "speed_to_revenue": self.speed_to_revenue,
            "speed_to_validation": self.speed_to_validation,
            "risk_level": self.risk_level,
            "automation_potential": self.automation_potential,
            "scalability_potential": self.scalability_potential,
            "constraint_fit": self.constraint_fit,
            "overall_score": self.overall_score,
            "confidence": self.confidence,
            "scored_at": self.scored_at.isoformat(),
            "scoring_notes": self.scoring_notes,
        }


@dataclass
class OpportunityRecommendation:
    """
    Actionable recommendation for an opportunity.

    Clear next-step guidance based on score and constraints.
    """
    opportunity_id: str
    action: RecommendationAction
    rationale: str
    confidence: float = 0.5                     # Confidence in recommendation

    # Next steps
    next_steps: List[str] = field(default_factory=list)
    estimated_time_to_validate: str = "unknown"  # hours, days, weeks
    estimated_cost_to_validate: str = "unknown"  # low, medium, high

    # Warnings/concerns
    warnings: List[str] = field(default_factory=list)

    recommended_at: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "action": self.action.value,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "next_steps": self.next_steps,
            "estimated_time_to_validate": self.estimated_time_to_validate,
            "estimated_cost_to_validate": self.estimated_cost_to_validate,
            "warnings": self.warnings,
            "recommended_at": self.recommended_at.isoformat(),
        }


@dataclass
class OpportunityRecord:
    """
    Full persisted opportunity record with score, recommendation, and history.

    This is the complete record stored in the opportunity registry.
    """
    opportunity_id: str
    hypothesis: OpportunityHypothesis
    score: OpportunityScore
    recommendation: OpportunityRecommendation
    status: OpportunityStatus

    # Operator context
    operator_constraints_snapshot: Optional[Dict[str, Any]] = None

    # History tracking
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    status_history: List[Dict[str, Any]] = field(default_factory=list)

    # Notes and context
    operator_notes: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "hypothesis": self.hypothesis.to_dict(),
            "score": self.score.to_dict(),
            "recommendation": self.recommendation.to_dict(),
            "status": self.status.value,
            "operator_constraints_snapshot": self.operator_constraints_snapshot,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status_history": self.status_history,
            "operator_notes": self.operator_notes,
            "tags": self.tags,
        }

    def update_status(self, new_status: OpportunityStatus, note: str = "") -> None:
        """Update status and record in history."""
        old_status = self.status
        self.status = new_status
        self.updated_at = _utc_now()

        self.status_history.append({
            "from_status": old_status.value,
            "to_status": new_status.value,
            "changed_at": self.updated_at.isoformat(),
            "note": note,
        })
