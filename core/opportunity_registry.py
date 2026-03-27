"""
Opportunity Registry for Project Alpha Discovery Layer.

Manages storage, retrieval, and comparison of business opportunities.

ARCHITECTURE:
- OpportunityRegistry: Main registry class
- Integrates with StateStore for persistence
- Supports CRUD operations
- Ranking and comparison
- Status transitions

PERSISTENCE:
- Stores in StateStore
- Does not store secrets
- Full opportunity lifecycle
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .discovery_models import (
    OpportunityRecord,
    OpportunityStatus,
    OpportunityHypothesis,
    OpportunityScore,
    OpportunityRecommendation,
)
from .state_store import StateStore

logger = logging.getLogger(__name__)


class OpportunityRegistry:
    """
    Registry for managing business opportunities.

    Handles storage, retrieval, ranking, and status transitions.
    """

    def __init__(self, state_store: StateStore):
        """
        Initialize registry.

        Args:
            state_store: StateStore for persistence
        """
        self.state_store = state_store

    def save_opportunity(self, record: OpportunityRecord) -> None:
        """
        Save or update an opportunity record.

        Args:
            record: OpportunityRecord to save
        """
        logger.info(f"Saving opportunity: {record.opportunity_id}")

        # Save to state store
        self.state_store.save_opportunity(
            opportunity_id=record.opportunity_id,
            hypothesis_data=record.hypothesis.to_dict(),
            score_data=record.score.to_dict(),
            recommendation_data=record.recommendation.to_dict(),
            status=record.status.value,
            operator_constraints_snapshot=record.operator_constraints_snapshot,
            status_history=record.status_history,
            operator_notes=record.operator_notes,
            tags=record.tags,
        )

        logger.info(f"Saved opportunity: {record.opportunity_id}")

    def get_opportunity(self, opportunity_id: str) -> Optional[OpportunityRecord]:
        """
        Get an opportunity by ID.

        Args:
            opportunity_id: Opportunity ID

        Returns:
            OpportunityRecord or None
        """
        data = self.state_store.get_opportunity(opportunity_id)
        if not data:
            return None

        return self._record_from_data(data)

    def list_opportunities(
        self,
        status: Optional[OpportunityStatus] = None,
        limit: int = 100,
    ) -> List[OpportunityRecord]:
        """
        List opportunities with optional filtering.

        Args:
            status: Optional status filter
            limit: Maximum records to return

        Returns:
            List of OpportunityRecord
        """
        status_value = status.value if status else None
        data_list = self.state_store.list_opportunities(
            status=status_value,
            limit=limit,
        )

        return [self._record_from_data(d) for d in data_list]

    def update_status(
        self,
        opportunity_id: str,
        new_status: OpportunityStatus,
        note: str = "",
    ) -> Optional[OpportunityRecord]:
        """
        Update opportunity status.

        Args:
            opportunity_id: Opportunity ID
            new_status: New status
            note: Optional note about status change

        Returns:
            Updated OpportunityRecord or None
        """
        record = self.get_opportunity(opportunity_id)
        if not record:
            logger.warning(f"Opportunity not found: {opportunity_id}")
            return None

        record.update_status(new_status, note)
        self.save_opportunity(record)

        logger.info(
            f"Updated {opportunity_id} status to {new_status.value}: {note}"
        )

        return record

    def add_note(
        self,
        opportunity_id: str,
        note: str,
    ) -> Optional[OpportunityRecord]:
        """
        Add operator note to opportunity.

        Args:
            opportunity_id: Opportunity ID
            note: Note to add

        Returns:
            Updated OpportunityRecord or None
        """
        record = self.get_opportunity(opportunity_id)
        if not record:
            return None

        # Append note
        if record.operator_notes:
            record.operator_notes += f"\n\n{note}"
        else:
            record.operator_notes = note

        self.save_opportunity(record)
        return record

    def rank_opportunities(
        self,
        status: Optional[OpportunityStatus] = None,
        limit: int = 100,
    ) -> List[OpportunityRecord]:
        """
        Get ranked list of opportunities by overall score.

        Args:
            status: Optional status filter
            limit: Maximum records to return

        Returns:
            List of OpportunityRecord sorted by score (descending)
        """
        opportunities = self.list_opportunities(status=status, limit=limit)

        # Sort by overall score (descending)
        ranked = sorted(
            opportunities,
            key=lambda r: r.score.overall_score,
            reverse=True,
        )

        return ranked

    def get_opportunities_by_tag(
        self,
        tag: str,
        limit: int = 100,
    ) -> List[OpportunityRecord]:
        """
        Get opportunities by tag.

        Args:
            tag: Tag to filter by
            limit: Maximum records

        Returns:
            List of OpportunityRecord
        """
        all_opportunities = self.list_opportunities(limit=limit)
        return [r for r in all_opportunities if tag in r.tags]

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for all opportunities.

        Returns:
            Dict with summary stats
        """
        all_opportunities = self.list_opportunities(limit=1000)

        if not all_opportunities:
            return {
                "total": 0,
                "by_status": {},
                "avg_score": 0.0,
                "top_scored": [],
            }

        # Count by status
        by_status = {}
        for record in all_opportunities:
            status = record.status.value
            by_status[status] = by_status.get(status, 0) + 1

        # Average score
        avg_score = sum(r.score.overall_score for r in all_opportunities) / len(all_opportunities)

        # Top 5 scored
        top_scored = sorted(
            all_opportunities,
            key=lambda r: r.score.overall_score,
            reverse=True,
        )[:5]

        top_scored_summary = [
            {
                "opportunity_id": r.opportunity_id,
                "title": r.hypothesis.title,
                "score": r.score.overall_score,
                "status": r.status.value,
            }
            for r in top_scored
        ]

        return {
            "total": len(all_opportunities),
            "by_status": by_status,
            "avg_score": round(avg_score, 2),
            "top_scored": top_scored_summary,
        }

    def _record_from_data(self, data: Dict[str, Any]) -> OpportunityRecord:
        """Reconstruct OpportunityRecord from stored data."""
        from .discovery_models import (
            OpportunityHypothesis,
            OpportunityScore,
            OpportunityRecommendation,
            MonetizationPath,
            RecommendationAction,
        )

        # Reconstruct hypothesis
        hyp_data = data["hypothesis_data"]
        hypothesis = OpportunityHypothesis(
            hypothesis_id=hyp_data["hypothesis_id"],
            title=hyp_data["title"],
            description=hyp_data["description"],
            target_audience=hyp_data["target_audience"],
            problem_addressed=hyp_data["problem_addressed"],
            proposed_solution=hyp_data["proposed_solution"],
            monetization_path=MonetizationPath(hyp_data["monetization_path"]),
            likely_domains=hyp_data.get("likely_domains", []),
            market_size_estimate=hyp_data.get("market_size_estimate", "unknown"),
            competition_level=hyp_data.get("competition_level", "unknown"),
            source_input_id=hyp_data.get("source_input_id"),
        )

        # Reconstruct score
        score_data = data["score_data"]
        score = OpportunityScore(
            opportunity_id=score_data["opportunity_id"],
            market_attractiveness=score_data["market_attractiveness"],
            monetization_clarity=score_data["monetization_clarity"],
            startup_complexity=score_data["startup_complexity"],
            technical_complexity=score_data["technical_complexity"],
            capital_intensity=score_data["capital_intensity"],
            operational_burden=score_data["operational_burden"],
            speed_to_revenue=score_data["speed_to_revenue"],
            speed_to_validation=score_data["speed_to_validation"],
            risk_level=score_data["risk_level"],
            automation_potential=score_data["automation_potential"],
            scalability_potential=score_data["scalability_potential"],
            constraint_fit=score_data["constraint_fit"],
            overall_score=score_data["overall_score"],
            confidence=score_data["confidence"],
            scoring_notes=score_data.get("scoring_notes", ""),
        )

        # Reconstruct recommendation
        rec_data = data["recommendation_data"]
        recommendation = OpportunityRecommendation(
            opportunity_id=rec_data["opportunity_id"],
            action=RecommendationAction(rec_data["action"]),
            rationale=rec_data["rationale"],
            confidence=rec_data["confidence"],
            next_steps=rec_data.get("next_steps", []),
            estimated_time_to_validate=rec_data.get("estimated_time_to_validate", "unknown"),
            estimated_cost_to_validate=rec_data.get("estimated_cost_to_validate", "unknown"),
            warnings=rec_data.get("warnings", []),
        )

        # Reconstruct record
        record = OpportunityRecord(
            opportunity_id=data["opportunity_id"],
            hypothesis=hypothesis,
            score=score,
            recommendation=recommendation,
            status=OpportunityStatus(data["status"]),
            operator_constraints_snapshot=data.get("operator_constraints_snapshot"),
            status_history=data.get("status_history", []),
            operator_notes=data.get("operator_notes", ""),
            tags=data.get("tags", []),
        )

        return record
