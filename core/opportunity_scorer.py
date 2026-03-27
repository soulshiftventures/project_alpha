"""
Opportunity Scorer for Project Alpha Discovery Layer.

Deterministic, testable scoring of opportunities across multiple dimensions.

ARCHITECTURE:
- score_opportunity: Main scoring function
- Dimension-specific scoring functions
- Constraint-aware scoring
- Composite score calculation

DETERMINISTIC:
- All scores 0.0 to 1.0
- Weighted heuristics
- No AI pretense
- Testable logic
"""

from typing import Dict, Optional, Tuple
import logging

from .discovery_models import (
    OpportunityHypothesis,
    OpportunityScore,
    OperatorConstraints,
    MonetizationPath,
)

logger = logging.getLogger(__name__)


# Scoring weights for composite score
SCORE_WEIGHTS = {
    "market_attractiveness": 0.15,
    "monetization_clarity": 0.15,
    "startup_complexity": -0.10,  # Negative: lower is better
    "technical_complexity": -0.05,
    "capital_intensity": -0.10,
    "operational_burden": -0.05,
    "speed_to_revenue": 0.15,
    "speed_to_validation": 0.10,
    "risk_level": -0.10,
    "automation_potential": 0.10,
    "scalability_potential": 0.10,
    "constraint_fit": 0.15,
}


def score_opportunity(
    hypothesis: OpportunityHypothesis,
    constraints: OperatorConstraints,
) -> OpportunityScore:
    """
    Score an opportunity across multiple dimensions.

    Args:
        hypothesis: Opportunity hypothesis to score
        constraints: Operator constraints

    Returns:
        OpportunityScore with all dimension scores
    """
    # Market dimension scores
    market_attractiveness = _score_market_attractiveness(hypothesis)
    monetization_clarity = _score_monetization_clarity(hypothesis)

    # Execution difficulty scores (0.0 = easy, 1.0 = hard)
    startup_complexity = _score_startup_complexity(hypothesis)
    technical_complexity = _score_technical_complexity(hypothesis)
    capital_intensity = _score_capital_intensity(hypothesis, constraints)
    operational_burden = _score_operational_burden(hypothesis)

    # Speed and risk scores
    speed_to_revenue = _score_speed_to_revenue(hypothesis)
    speed_to_validation = _score_speed_to_validation(hypothesis)
    risk_level = _score_risk_level(hypothesis)

    # Potential scores
    automation_potential = _score_automation_potential(hypothesis)
    scalability_potential = _score_scalability_potential(hypothesis)

    # Constraint fit score
    constraint_fit = _score_constraint_fit(hypothesis, constraints)

    # Calculate composite score
    overall_score = _calculate_composite_score(
        market_attractiveness=market_attractiveness,
        monetization_clarity=monetization_clarity,
        startup_complexity=startup_complexity,
        technical_complexity=technical_complexity,
        capital_intensity=capital_intensity,
        operational_burden=operational_burden,
        speed_to_revenue=speed_to_revenue,
        speed_to_validation=speed_to_validation,
        risk_level=risk_level,
        automation_potential=automation_potential,
        scalability_potential=scalability_potential,
        constraint_fit=constraint_fit,
    )

    # Confidence in scoring (based on data completeness)
    confidence = _calculate_confidence(hypothesis)

    scoring_notes = _generate_scoring_notes(hypothesis, constraints)

    return OpportunityScore(
        opportunity_id=hypothesis.hypothesis_id,
        market_attractiveness=market_attractiveness,
        monetization_clarity=monetization_clarity,
        startup_complexity=startup_complexity,
        technical_complexity=technical_complexity,
        capital_intensity=capital_intensity,
        operational_burden=operational_burden,
        speed_to_revenue=speed_to_revenue,
        speed_to_validation=speed_to_validation,
        risk_level=risk_level,
        automation_potential=automation_potential,
        scalability_potential=scalability_potential,
        constraint_fit=constraint_fit,
        overall_score=overall_score,
        confidence=confidence,
        scoring_notes=scoring_notes,
    )


def _score_market_attractiveness(hypothesis: OpportunityHypothesis) -> float:
    """Score market attractiveness (0.0 - 1.0)."""
    score = 0.5  # Baseline

    # Market size factor
    if hypothesis.market_size_estimate == "large":
        score += 0.3
    elif hypothesis.market_size_estimate == "medium":
        score += 0.1
    elif hypothesis.market_size_estimate == "small":
        score -= 0.1

    # Competition factor (inverse)
    if hypothesis.competition_level == "low":
        score += 0.2
    elif hypothesis.competition_level == "medium":
        score += 0.0
    elif hypothesis.competition_level == "high":
        score -= 0.2

    return max(0.0, min(1.0, score))


def _score_monetization_clarity(hypothesis: OpportunityHypothesis) -> float:
    """Score monetization clarity (0.0 - 1.0)."""
    clarity_scores = {
        MonetizationPath.UNCLEAR: 0.2,
        MonetizationPath.HYBRID: 0.5,
        MonetizationPath.SUBSCRIPTION: 0.9,  # Clear, recurring
        MonetizationPath.TRANSACTION_FEE: 0.8,
        MonetizationPath.SERVICE: 0.7,
        MonetizationPath.ONE_TIME_SALE: 0.6,
        MonetizationPath.LICENSING: 0.7,
        MonetizationPath.AFFILIATE: 0.6,
        MonetizationPath.ADVERTISING: 0.5,  # Harder to monetize
    }
    return clarity_scores.get(hypothesis.monetization_path, 0.5)


def _score_startup_complexity(hypothesis: OpportunityHypothesis) -> float:
    """Score startup complexity (0.0 = simple, 1.0 = complex)."""
    score = 0.5  # Baseline

    # Service-based usually simpler to start
    if hypothesis.monetization_path == MonetizationPath.SERVICE:
        score -= 0.2
    # Subscription/platform more complex
    elif hypothesis.monetization_path == MonetizationPath.SUBSCRIPTION:
        score += 0.2

    # Multiple domains = more complex
    if len(hypothesis.likely_domains) > 2:
        score += 0.1

    return max(0.0, min(1.0, score))


def _score_technical_complexity(hypothesis: OpportunityHypothesis) -> float:
    """Score technical complexity (0.0 = simple, 1.0 = complex)."""
    score = 0.5  # Baseline

    # Domain-based complexity
    technical_domains = ["engineering", "product", "automation"]
    non_technical_domains = ["content", "research", "customer_support"]

    tech_count = sum(1 for d in hypothesis.likely_domains if d in technical_domains)
    non_tech_count = sum(1 for d in hypothesis.likely_domains if d in non_technical_domains)

    if tech_count > non_tech_count:
        score += 0.2
    elif non_tech_count > tech_count:
        score -= 0.2

    return max(0.0, min(1.0, score))


def _score_capital_intensity(
    hypothesis: OpportunityHypothesis,
    constraints: OperatorConstraints
) -> float:
    """Score capital intensity (0.0 = low capital, 1.0 = high capital)."""
    score = 0.5  # Baseline

    # Service-based typically lower capital
    if hypothesis.monetization_path == MonetizationPath.SERVICE:
        score -= 0.3
    # Platform/subscription higher capital
    elif hypothesis.monetization_path == MonetizationPath.SUBSCRIPTION:
        score += 0.2

    # Adjust based on operator constraints
    # If operator has low budget, penalize capital-intensive opportunities
    if constraints.max_initial_capital < 1000:
        if score > 0.5:
            score += 0.1  # Increase penalty for high capital

    return max(0.0, min(1.0, score))


def _score_operational_burden(hypothesis: OpportunityHypothesis) -> float:
    """Score operational burden (0.0 = low burden, 1.0 = high burden)."""
    score = 0.5  # Baseline

    # Service-based typically higher burden
    if hypothesis.monetization_path == MonetizationPath.SERVICE:
        score += 0.3
    # Affiliate/advertising lower burden
    elif hypothesis.monetization_path in [MonetizationPath.AFFILIATE, MonetizationPath.ADVERTISING]:
        score -= 0.2

    # Customer support domain = higher burden
    if "customer_support" in hypothesis.likely_domains:
        score += 0.2

    return max(0.0, min(1.0, score))


def _score_speed_to_revenue(hypothesis: OpportunityHypothesis) -> float:
    """Score speed to revenue (0.0 = slow, 1.0 = fast)."""
    score = 0.5  # Baseline

    # Service and one-time sales are fastest
    if hypothesis.monetization_path in [MonetizationPath.SERVICE, MonetizationPath.ONE_TIME_SALE]:
        score += 0.3
    # Subscription/platform slower
    elif hypothesis.monetization_path == MonetizationPath.SUBSCRIPTION:
        score -= 0.2

    return max(0.0, min(1.0, score))


def _score_speed_to_validation(hypothesis: OpportunityHypothesis) -> float:
    """Score speed to validation (0.0 = slow, 1.0 = fast)."""
    score = 0.5  # Baseline

    # Simple services can be validated quickly
    if hypothesis.monetization_path == MonetizationPath.SERVICE:
        score += 0.3
    # Research/content domains validate quickly
    if any(d in hypothesis.likely_domains for d in ["research", "content"]):
        score += 0.2

    return max(0.0, min(1.0, score))


def _score_risk_level(hypothesis: OpportunityHypothesis) -> float:
    """Score risk level (0.0 = low risk, 1.0 = high risk)."""
    score = 0.5  # Baseline

    # High competition = higher risk
    if hypothesis.competition_level == "high":
        score += 0.2
    elif hypothesis.competition_level == "low":
        score -= 0.2

    # Unclear monetization = higher risk
    if hypothesis.monetization_path == MonetizationPath.UNCLEAR:
        score += 0.2

    return max(0.0, min(1.0, score))


def _score_automation_potential(hypothesis: OpportunityHypothesis) -> float:
    """Score automation potential (0.0 = low, 1.0 = high)."""
    score = 0.5  # Baseline

    # Automation domain = high potential
    if "automation" in hypothesis.likely_domains:
        score += 0.3

    # Service-based = lower automation potential
    if hypothesis.monetization_path == MonetizationPath.SERVICE:
        score -= 0.2

    return max(0.0, min(1.0, score))


def _score_scalability_potential(hypothesis: OpportunityHypothesis) -> float:
    """Score scalability potential (0.0 = low, 1.0 = high)."""
    score = 0.5  # Baseline

    # Subscription/platform = high scalability
    if hypothesis.monetization_path == MonetizationPath.SUBSCRIPTION:
        score += 0.3
    # Service = low scalability
    elif hypothesis.monetization_path == MonetizationPath.SERVICE:
        score -= 0.3

    return max(0.0, min(1.0, score))


def _score_constraint_fit(
    hypothesis: OpportunityHypothesis,
    constraints: OperatorConstraints
) -> float:
    """Score fit with operator constraints (0.0 = poor fit, 1.0 = perfect fit)."""
    score = 0.5  # Baseline

    # Budget fit
    capital_score = _score_capital_intensity(hypothesis, constraints)
    if capital_score > 0.7 and constraints.max_initial_capital < 5000:
        score -= 0.2  # High capital need, low budget = poor fit

    # Automation preference fit
    automation_score = _score_automation_potential(hypothesis)
    if constraints.automation_preference == "high":
        score += (automation_score - 0.5) * 0.3  # Reward high automation

    # Operational burden vs hands-off preference
    burden_score = _score_operational_burden(hypothesis)
    if constraints.hands_on_vs_hands_off == "hands_off" and burden_score > 0.6:
        score -= 0.2  # High burden, hands-off preference = poor fit

    # Speed priority fit
    speed_score = _score_speed_to_revenue(hypothesis)
    if constraints.speed_priority == "high":
        score += (speed_score - 0.5) * 0.3  # Reward fast revenue

    # Domain preference fit
    if constraints.preferred_domains:
        domain_match = any(d in hypothesis.likely_domains for d in constraints.preferred_domains)
        if domain_match:
            score += 0.2

    if constraints.avoided_domains:
        domain_avoid = any(d in hypothesis.likely_domains for d in constraints.avoided_domains)
        if domain_avoid:
            score -= 0.3

    return max(0.0, min(1.0, score))


def _calculate_composite_score(**dimension_scores) -> float:
    """Calculate weighted composite score from dimension scores."""
    total_score = 0.0

    for dimension, score in dimension_scores.items():
        weight = SCORE_WEIGHTS.get(dimension, 0.0)
        total_score += score * weight

    # Normalize to 0.0 - 1.0 range
    # Current weights sum to 1.0, so no additional normalization needed
    return max(0.0, min(1.0, total_score + 0.5))  # +0.5 to center around 0.5


def _calculate_confidence(hypothesis: OpportunityHypothesis) -> float:
    """Calculate confidence in scoring based on data completeness."""
    confidence = 0.5  # Baseline

    # Clear monetization increases confidence
    if hypothesis.monetization_path != MonetizationPath.UNCLEAR:
        confidence += 0.2

    # Known market size increases confidence
    if hypothesis.market_size_estimate != "unknown":
        confidence += 0.1

    # Known competition increases confidence
    if hypothesis.competition_level != "unknown":
        confidence += 0.1

    # Clear target audience increases confidence
    if "not specified" not in hypothesis.target_audience.lower():
        confidence += 0.1

    return max(0.0, min(1.0, confidence))


def _generate_scoring_notes(
    hypothesis: OpportunityHypothesis,
    constraints: OperatorConstraints
) -> str:
    """Generate human-readable scoring notes."""
    notes = []

    # Market notes
    if hypothesis.market_size_estimate == "large":
        notes.append("Large market opportunity")
    elif hypothesis.market_size_estimate == "small":
        notes.append("Niche market")

    # Competition notes
    if hypothesis.competition_level == "high":
        notes.append("High competition")
    elif hypothesis.competition_level == "low":
        notes.append("Low competition space")

    # Monetization notes
    if hypothesis.monetization_path == MonetizationPath.UNCLEAR:
        notes.append("Monetization path unclear")

    # Constraint fit notes
    capital_score = _score_capital_intensity(hypothesis, constraints)
    if capital_score > 0.7:
        notes.append("High capital requirements")

    return "; ".join(notes) if notes else "Standard opportunity profile"
