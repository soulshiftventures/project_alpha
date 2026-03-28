"""
Skill Ranker - Outcome-based skill selection for Seed Core.

Replaces pure keyword matching with learned rankings based on actual outcomes.

For a given goal type, ranks available skills by:
- Historical success rate
- Average quality of outcomes
- Confidence (sample size)
"""

import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .skill_registry import SkillDefinition, get_skill_registry
from .seed_memory import SeedMemory, get_seed_memory
from .seed_models import SkillRanking

logger = logging.getLogger(__name__)


@dataclass
class RankedSkill:
    """A skill with its learned ranking score."""
    skill: SkillDefinition
    ranking: Optional[SkillRanking]
    score: float  # Composite score for sorting
    selection_reason: str  # Why this skill was ranked here


class SkillRanker:
    """
    Ranks skills for goals using learned outcomes.

    Falls back to keyword matching for new goal types with no history.
    """

    def __init__(
        self,
        skill_registry = None,
        seed_memory: Optional[SeedMemory] = None,
    ):
        """
        Initialize the skill ranker.

        Args:
            skill_registry: SkillRegistry instance. Uses global if not provided.
            seed_memory: SeedMemory instance. Uses global if not provided.
        """
        self._skill_registry = skill_registry or get_skill_registry()
        self._seed_memory = seed_memory or get_seed_memory()

    def rank_skills_for_goal(
        self,
        goal_type: str,
        goal_description: str,
        limit: int = 5,
    ) -> List[RankedSkill]:
        """
        Rank skills for a goal using learned outcomes.

        For goal types with execution history:
        - Primary ranking from learned outcomes
        - Secondary keyword matching as tiebreaker

        For new goal types:
        - Keyword matching only
        - Create initial ranking on first execution

        Args:
            goal_type: Type of goal (e.g., "market_research")
            goal_description: Description of the goal
            limit: Maximum number of skills to return

        Returns:
            List of RankedSkill, sorted by score (best first)
        """
        # Get learned rankings for this goal type
        learned_rankings = self._seed_memory.get_ranked_skills(goal_type, limit=limit * 2)

        # Get all available skills
        if not self._skill_registry.is_loaded:
            self._skill_registry.load()

        all_skills = self._skill_registry.all_skills()

        # Build ranking
        ranked = []

        if learned_rankings:
            # Have history for this goal type - use learned rankings
            logger.info(f"Using learned rankings for goal_type={goal_type} ({len(learned_rankings)} skills)")

            # Create map of skill names to rankings
            ranking_map = {r.skill_name: r for r in learned_rankings}

            for skill in all_skills:
                ranking = ranking_map.get(skill.name)

                if ranking:
                    # Skill has execution history for this goal type
                    score = ranking.get_score()
                    reason = f"Learned: {ranking.total_executions} executions, {ranking.success_rate:.1%} success, {ranking.average_quality:.2f} quality"
                else:
                    # Skill exists but not tried for this goal type yet
                    # Use keyword matching as secondary signal
                    keyword_score = skill.keyword_score(goal_description)
                    if keyword_score > 0:
                        score = keyword_score * 0.3  # Lower than learned scores
                        reason = f"Keyword match: {keyword_score:.2f} (no execution history yet)"
                    else:
                        continue  # Skip skills with no relevance

                ranked.append(RankedSkill(
                    skill=skill,
                    ranking=ranking,
                    score=score,
                    selection_reason=reason,
                ))

        else:
            # No history for this goal type - use keyword matching
            logger.info(f"No learned rankings for goal_type={goal_type}, using keyword matching")

            for skill in all_skills:
                keyword_score = skill.keyword_score(goal_description)
                if keyword_score > 0:
                    ranked.append(RankedSkill(
                        skill=skill,
                        ranking=None,
                        score=keyword_score,
                        selection_reason=f"Keyword match: {keyword_score:.2f} (new goal type)",
                    ))

        # Sort by score descending
        ranked.sort(key=lambda r: r.score, reverse=True)

        return ranked[:limit]

    def get_best_skill(
        self,
        goal_type: str,
        goal_description: str,
    ) -> Optional[RankedSkill]:
        """
        Get the single best skill for a goal.

        Args:
            goal_type: Type of goal
            goal_description: Description of the goal

        Returns:
            The top-ranked skill, or None if no relevant skills found
        """
        ranked = self.rank_skills_for_goal(goal_type, goal_description, limit=1)
        return ranked[0] if ranked else None

    def explain_ranking(self, goal_type: str, limit: int = 10) -> List[dict]:
        """
        Get detailed ranking explanation for a goal type.

        Useful for debugging and understanding why skills are ranked as they are.

        Args:
            goal_type: Type of goal
            limit: Number of skills to explain

        Returns:
            List of dicts with skill name, ranking stats, and explanation
        """
        learned_rankings = self._seed_memory.get_ranked_skills(goal_type, limit=limit)

        explanations = []
        for ranking in learned_rankings:
            explanations.append({
                "skill_name": ranking.skill_name,
                "score": ranking.get_score(),
                "total_executions": ranking.total_executions,
                "success_rate": ranking.success_rate,
                "average_quality": ranking.average_quality,
                "confidence": ranking.confidence,
                "last_execution": ranking.last_execution,
                "explanation": (
                    f"Tried {ranking.total_executions} times with {ranking.success_rate:.1%} success. "
                    f"Average quality: {ranking.average_quality:.2f}. "
                    f"Confidence: {ranking.confidence:.2f}."
                ),
            })

        return explanations


# Singleton instance
_skill_ranker: Optional[SkillRanker] = None


def get_skill_ranker() -> SkillRanker:
    """Get the global SkillRanker instance."""
    global _skill_ranker
    if _skill_ranker is None:
        _skill_ranker = SkillRanker()
    return _skill_ranker
