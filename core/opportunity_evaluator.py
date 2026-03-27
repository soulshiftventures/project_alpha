"""
Opportunity Evaluator for Project Alpha Discovery Layer.

Generates recommendations and next-step guidance based on opportunity scores.

ARCHITECTURE:
- evaluate_opportunity: Main evaluation function
- Recommendation generation based on scores and constraints
- Next-step planning
- Warning generation

DETERMINISTIC:
- Rule-based recommendation logic
- Clear thresholds
- Testable
"""

from typing import List, Tuple
import logging

from .discovery_models import (
    OpportunityHypothesis,
    OpportunityScore,
    OpportunityRecommendation,
    OperatorConstraints,
    RecommendationAction,
)

logger = logging.getLogger(__name__)


# Recommendation thresholds
PURSUE_NOW_THRESHOLD = 0.70          # Overall score >= 0.70
VALIDATE_FIRST_THRESHOLD = 0.50      # Overall score >= 0.50
ARCHIVE_THRESHOLD = 0.40             # Overall score >= 0.40
# Below 0.40 = reject


def evaluate_opportunity(
    hypothesis: OpportunityHypothesis,
    score: OpportunityScore,
    constraints: OperatorConstraints,
) -> OpportunityRecommendation:
    """
    Evaluate opportunity and generate recommendation.

    Args:
        hypothesis: Opportunity hypothesis
        score: Opportunity score
        constraints: Operator constraints

    Returns:
        OpportunityRecommendation with action and guidance
    """
    # Determine recommended action
    action, rationale = _determine_action(score, constraints)

    # Generate next steps
    next_steps = _generate_next_steps(action, hypothesis, score)

    # Estimate validation time/cost
    time_estimate = _estimate_validation_time(hypothesis, score)
    cost_estimate = _estimate_validation_cost(hypothesis, score)

    # Generate warnings
    warnings = _generate_warnings(hypothesis, score, constraints)

    # Confidence in recommendation
    confidence = _calculate_recommendation_confidence(score)

    return OpportunityRecommendation(
        opportunity_id=hypothesis.hypothesis_id,
        action=action,
        rationale=rationale,
        confidence=confidence,
        next_steps=next_steps,
        estimated_time_to_validate=time_estimate,
        estimated_cost_to_validate=cost_estimate,
        warnings=warnings,
    )


def _determine_action(
    score: OpportunityScore,
    constraints: OperatorConstraints,
) -> Tuple[RecommendationAction, str]:
    """
    Determine recommended action based on score.

    Returns:
        (action, rationale) tuple
    """
    overall = score.overall_score

    # High score and good fit = pursue now
    if overall >= PURSUE_NOW_THRESHOLD and score.constraint_fit >= 0.6:
        return (
            RecommendationAction.PURSUE_NOW,
            f"Strong opportunity (score: {overall:.2f}) with good constraint fit"
        )

    # Good score but needs validation
    if overall >= VALIDATE_FIRST_THRESHOLD:
        # Check if high risk or uncertainty
        if score.risk_level > 0.6 or score.confidence < 0.6:
            return (
                RecommendationAction.VALIDATE_FIRST,
                f"Good opportunity (score: {overall:.2f}) but higher risk/uncertainty - validate first"
            )
        else:
            return (
                RecommendationAction.PURSUE_NOW,
                f"Good opportunity (score: {overall:.2f}) - proceed with caution"
            )

    # Moderate score = archive for later
    if overall >= ARCHIVE_THRESHOLD:
        return (
            RecommendationAction.ARCHIVE,
            f"Moderate opportunity (score: {overall:.2f}) - archive for later consideration"
        )

    # Low score = reject
    return (
        RecommendationAction.REJECT,
        f"Low opportunity score ({overall:.2f}) - not recommended"
    )


def _generate_next_steps(
    action: RecommendationAction,
    hypothesis: OpportunityHypothesis,
    score: OpportunityScore,
) -> List[str]:
    """Generate actionable next steps based on recommendation."""
    steps = []

    if action == RecommendationAction.PURSUE_NOW:
        steps.append("Review opportunity details and confirm alignment")
        steps.append("Define initial execution plan")
        steps.append("Identify required resources and skills")

        # Add domain-specific steps
        if "growth" in hypothesis.likely_domains:
            steps.append("Define target audience and initial outreach strategy")
        if "product" in hypothesis.likely_domains:
            steps.append("Create MVP specification")

        steps.append("Set initial success metrics")

    elif action == RecommendationAction.VALIDATE_FIRST:
        steps.append("Define validation hypothesis")
        steps.append("Identify validation method (survey, landing page, manual test)")

        # Add specific validation steps based on weaknesses
        if score.market_attractiveness < 0.5:
            steps.append("Validate market demand and willingness to pay")
        if score.monetization_clarity < 0.5:
            steps.append("Test monetization approach with target audience")
        if score.technical_complexity > 0.7:
            steps.append("Validate technical feasibility")

        steps.append("Set validation success criteria")
        steps.append("Execute validation test")
        steps.append("Review results and decide: pursue, iterate, or abandon")

    elif action == RecommendationAction.ARCHIVE:
        steps.append("Document opportunity for future reference")
        steps.append("Set review reminder (quarterly or when circumstances change)")
        steps.append("Identify what would need to change to make this attractive")

    elif action == RecommendationAction.REJECT:
        steps.append("Document rejection rationale")
        steps.append("Identify key issues preventing pursuit")
        steps.append("Consider if any variation could address issues")

    return steps


def _estimate_validation_time(
    hypothesis: OpportunityHypothesis,
    score: OpportunityScore,
) -> str:
    """Estimate time to validate opportunity."""
    # Fast validation (< 1 week)
    if score.speed_to_validation > 0.7:
        return "1-3 days"

    # Medium validation (1-2 weeks)
    if score.speed_to_validation > 0.5:
        return "1-2 weeks"

    # Slow validation (weeks to months)
    if score.technical_complexity > 0.7:
        return "3-4 weeks"

    return "2-3 weeks"


def _estimate_validation_cost(
    hypothesis: OpportunityHypothesis,
    score: OpportunityScore,
) -> str:
    """Estimate cost to validate opportunity."""
    # Low cost validation
    if score.capital_intensity < 0.3:
        return "low ($0-$100)"

    # Medium cost validation
    if score.capital_intensity < 0.6:
        return "medium ($100-$500)"

    # High cost validation
    return "high ($500+)"


def _generate_warnings(
    hypothesis: OpportunityHypothesis,
    score: OpportunityScore,
    constraints: OperatorConstraints,
) -> List[str]:
    """Generate warnings about potential issues."""
    warnings = []

    # Capital warnings
    if score.capital_intensity > 0.7 and constraints.max_initial_capital < 5000:
        warnings.append("High capital requirements may exceed available budget")

    # Operational burden warnings
    if score.operational_burden > 0.7 and constraints.hands_on_vs_hands_off == "hands_off":
        warnings.append("High operational burden conflicts with hands-off preference")

    # Time commitment warnings
    if score.operational_burden > 0.7 and constraints.max_hours_per_week < 20:
        warnings.append("May require more time than available")

    # Risk warnings
    if score.risk_level > 0.7:
        warnings.append("High risk opportunity - consider careful validation")

    # Competition warnings
    if hypothesis.competition_level == "high":
        warnings.append("High competition - differentiation will be critical")

    # Monetization warnings
    if score.monetization_clarity < 0.4:
        warnings.append("Unclear monetization path - validate revenue model early")

    # Constraint fit warnings
    if score.constraint_fit < 0.4:
        warnings.append("Poor fit with current constraints - may require changes")

    # Technical complexity warnings
    if score.technical_complexity > 0.7 and constraints.technical_complexity_tolerance == "low":
        warnings.append("High technical complexity may exceed comfort level")

    return warnings


def _calculate_recommendation_confidence(score: OpportunityScore) -> float:
    """Calculate confidence in recommendation."""
    # Base confidence on scoring confidence
    confidence = score.confidence

    # Reduce confidence if scores are borderline
    if 0.45 <= score.overall_score <= 0.55:
        confidence *= 0.8  # Less confident in borderline cases

    # Reduce confidence if high risk
    if score.risk_level > 0.7:
        confidence *= 0.9

    return max(0.0, min(1.0, confidence))
