"""
Opportunity Ranker

Ranks opportunity candidates using weighted scoring.
"""

from typing import List, Dict, Any, Callable
from dataclasses import dataclass

from core.market_discovery import OpportunityCandidate


@dataclass
class RankingWeights:
    """Weights for ranking criteria"""
    urgency: float = 0.25
    monetization_clarity: float = 0.20
    automation_potential: float = 0.20
    complexity: float = 0.15  # Inverse: lower is better
    confidence: float = 0.20


class OpportunityRanker:
    """
    Ranks opportunity candidates using weighted scoring

    Uses deterministic scoring for testability.
    """

    def __init__(self, weights: RankingWeights = None):
        self.weights = weights or RankingWeights()

    def rank_candidates(
        self,
        candidates: List[OpportunityCandidate],
        sort_descending: bool = True
    ) -> List[OpportunityCandidate]:
        """
        Rank candidates by overall score

        Args:
            candidates: List of opportunity candidates
            sort_descending: Sort highest score first (default True)

        Returns:
            Sorted list of candidates
        """
        # Calculate score for each candidate
        scored_candidates = [
            (candidate, self.calculate_score(candidate))
            for candidate in candidates
        ]

        # Sort by score
        scored_candidates.sort(
            key=lambda x: x[1],
            reverse=sort_descending
        )

        return [candidate for candidate, score in scored_candidates]

    def calculate_score(self, candidate: OpportunityCandidate) -> float:
        """
        Calculate overall opportunity score (0.0-1.0)

        Weighted average of:
        - Urgency (25%)
        - Monetization clarity (20%)
        - Automation potential (20%)
        - Complexity (15%, inverse)
        - Confidence (20%)
        """
        urgency_score = self._score_urgency(candidate.urgency)
        monetization_score = self._score_monetization_clarity(candidate.monetization_clarity)
        automation_score = self._score_automation_potential(candidate.automation_potential)
        complexity_score = self._score_complexity(candidate.complexity)
        confidence_score = candidate.confidence

        overall_score = (
            urgency_score * self.weights.urgency +
            monetization_score * self.weights.monetization_clarity +
            automation_score * self.weights.automation_potential +
            complexity_score * self.weights.complexity +
            confidence_score * self.weights.confidence
        )

        return round(overall_score, 3)

    def get_score_breakdown(self, candidate: OpportunityCandidate) -> Dict[str, float]:
        """
        Get detailed score breakdown for a candidate

        Returns:
            Dictionary with component scores and overall score
        """
        urgency_score = self._score_urgency(candidate.urgency)
        monetization_score = self._score_monetization_clarity(candidate.monetization_clarity)
        automation_score = self._score_automation_potential(candidate.automation_potential)
        complexity_score = self._score_complexity(candidate.complexity)
        confidence_score = candidate.confidence
        overall_score = self.calculate_score(candidate)

        return {
            "urgency": urgency_score,
            "monetization_clarity": monetization_score,
            "automation_potential": automation_score,
            "complexity": complexity_score,
            "confidence": confidence_score,
            "overall": overall_score,
        }

    def filter_by_threshold(
        self,
        candidates: List[OpportunityCandidate],
        min_score: float = 0.5
    ) -> List[OpportunityCandidate]:
        """
        Filter candidates by minimum score threshold

        Args:
            candidates: List of candidates
            min_score: Minimum score (0.0-1.0)

        Returns:
            Filtered list of candidates meeting threshold
        """
        return [
            candidate
            for candidate in candidates
            if self.calculate_score(candidate) >= min_score
        ]

    def rank_by_criteria(
        self,
        candidates: List[OpportunityCandidate],
        criteria: str
    ) -> List[OpportunityCandidate]:
        """
        Rank candidates by a single criterion

        Args:
            candidates: List of candidates
            criteria: Criterion name (urgency, monetization_clarity, automation_potential, complexity, confidence)

        Returns:
            Sorted list of candidates
        """
        scoring_functions = {
            "urgency": lambda c: self._score_urgency(c.urgency),
            "monetization_clarity": lambda c: self._score_monetization_clarity(c.monetization_clarity),
            "automation_potential": lambda c: self._score_automation_potential(c.automation_potential),
            "complexity": lambda c: self._score_complexity(c.complexity),
            "confidence": lambda c: c.confidence,
        }

        if criteria not in scoring_functions:
            raise ValueError(f"Unknown criteria: {criteria}")

        score_func = scoring_functions[criteria]
        return sorted(candidates, key=score_func, reverse=True)

    def _score_urgency(self, urgency: str) -> float:
        """Score urgency level (0.0-1.0)"""
        urgency_map = {
            "critical": 1.0,
            "high": 0.75,
            "medium": 0.5,
            "low": 0.25,
        }
        return urgency_map.get(urgency.lower(), 0.5)

    def _score_monetization_clarity(self, clarity: str) -> float:
        """Score monetization clarity (0.0-1.0)"""
        clarity_map = {
            "proven": 1.0,
            "emerging": 0.6,
            "unclear": 0.2,
        }
        return clarity_map.get(clarity.lower(), 0.5)

    def _score_automation_potential(self, potential: str) -> float:
        """Score automation potential (0.0-1.0)"""
        potential_map = {
            "high": 1.0,
            "medium": 0.6,
            "low": 0.2,
        }
        return potential_map.get(potential.lower(), 0.5)

    def _score_complexity(self, complexity: str) -> float:
        """
        Score complexity (0.0-1.0, inverse)

        Lower complexity = higher score
        """
        complexity_map = {
            "low": 1.0,
            "medium": 0.6,
            "high": 0.2,
        }
        return complexity_map.get(complexity.lower(), 0.5)


# Global instance
_opportunity_ranker = None


def get_opportunity_ranker(weights: RankingWeights = None) -> OpportunityRanker:
    """Get global opportunity ranker instance"""
    global _opportunity_ranker
    if _opportunity_ranker is None:
        _opportunity_ranker = OpportunityRanker(weights)
    return _opportunity_ranker
