"""
Discovery Pipeline for Project Alpha.

Orchestrates the full discovery flow from raw input to evaluated opportunity.

ARCHITECTURE:
- process_discovery_input: End-to-end pipeline
- Integrates intake, scoring, and evaluation
- Returns ready-to-use OpportunityRecord

FLOW:
1. Raw input → normalized hypotheses
2. Hypotheses → scored
3. Scored → evaluated and recommended
4. Package into OpportunityRecord
"""

from typing import List, Optional
import logging

from .discovery_models import (
    RawInput,
    OpportunityHypothesis,
    OpportunityScore,
    OpportunityRecommendation,
    OpportunityRecord,
    OperatorConstraints,
    OpportunityStatus,
    RecommendationAction,
)
from .idea_intake import intake_raw_input, normalize_to_hypotheses
from .opportunity_scorer import score_opportunity
from .opportunity_evaluator import evaluate_opportunity

logger = logging.getLogger(__name__)


def process_discovery_input(
    raw_text: str,
    constraints: OperatorConstraints,
    submitted_by: str = "principal",
    tags: Optional[List[str]] = None,
) -> List[OpportunityRecord]:
    """
    Process raw discovery input through complete pipeline.

    Args:
        raw_text: Raw idea/problem/opportunity text
        constraints: Operator constraints
        submitted_by: Who submitted this
        tags: Optional tags

    Returns:
        List of evaluated OpportunityRecord objects
    """
    logger.info(f"Processing discovery input from {submitted_by}")

    # Step 1: Intake raw input
    raw_input = intake_raw_input(
        raw_text=raw_text,
        submitted_by=submitted_by,
        tags=tags,
    )
    logger.info(f"Created raw input: {raw_input.input_id} (type: {raw_input.input_type.value})")

    # Step 2: Normalize to hypotheses
    hypotheses = normalize_to_hypotheses(raw_input)
    if not hypotheses:
        logger.warning("No hypotheses generated from input")
        return []

    logger.info(f"Generated {len(hypotheses)} hypothesis(es)")

    # Step 3: Score and evaluate each hypothesis
    opportunity_records = []

    for hypothesis in hypotheses:
        logger.info(f"Scoring hypothesis: {hypothesis.hypothesis_id}")

        # Score opportunity
        score = score_opportunity(hypothesis, constraints)
        logger.info(
            f"Scored {hypothesis.hypothesis_id}: "
            f"overall={score.overall_score:.2f}, "
            f"confidence={score.confidence:.2f}"
        )

        # Evaluate and recommend
        recommendation = evaluate_opportunity(hypothesis, score, constraints)
        logger.info(
            f"Recommendation for {hypothesis.hypothesis_id}: "
            f"{recommendation.action.value}"
        )

        # Determine initial status based on recommendation
        initial_status = _recommendation_to_status(recommendation.action)

        # Create opportunity record
        record = OpportunityRecord(
            opportunity_id=hypothesis.hypothesis_id,
            hypothesis=hypothesis,
            score=score,
            recommendation=recommendation,
            status=initial_status,
            operator_constraints_snapshot=constraints.to_dict(),
            tags=tags or [],
        )

        opportunity_records.append(record)

    logger.info(f"Pipeline complete: generated {len(opportunity_records)} opportunity record(s)")
    return opportunity_records


def rescore_opportunity(
    record: OpportunityRecord,
    constraints: OperatorConstraints,
) -> OpportunityRecord:
    """
    Rescore an existing opportunity with updated constraints.

    Args:
        record: Existing opportunity record
        constraints: Updated operator constraints

    Returns:
        Updated OpportunityRecord
    """
    logger.info(f"Rescoring opportunity: {record.opportunity_id}")

    # Rescore with new constraints
    new_score = score_opportunity(record.hypothesis, constraints)

    # Re-evaluate
    new_recommendation = evaluate_opportunity(
        record.hypothesis,
        new_score,
        constraints,
    )

    # Update record
    record.score = new_score
    record.recommendation = new_recommendation
    record.operator_constraints_snapshot = constraints.to_dict()

    # Update status if recommendation changed significantly
    new_status = _recommendation_to_status(new_recommendation.action)
    if new_status != record.status:
        record.update_status(new_status, "Rescored with updated constraints")

    logger.info(
        f"Rescored {record.opportunity_id}: "
        f"overall={new_score.overall_score:.2f}, "
        f"action={new_recommendation.action.value}"
    )

    return record


def _recommendation_to_status(action: RecommendationAction) -> OpportunityStatus:
    """Map recommendation action to initial opportunity status."""
    mapping = {
        RecommendationAction.PURSUE_NOW: OpportunityStatus.EVALUATED,
        RecommendationAction.VALIDATE_FIRST: OpportunityStatus.EVALUATED,
        RecommendationAction.ARCHIVE: OpportunityStatus.EVALUATED,
        RecommendationAction.REJECT: OpportunityStatus.EVALUATED,
    }
    return mapping.get(action, OpportunityStatus.EVALUATED)
