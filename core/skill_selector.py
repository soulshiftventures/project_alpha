"""
Skill Selector - Intelligent skill selection logic.

Selects the most appropriate skills, commands, and agents for a given task
based on keywords, categories, and relevance scoring.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Union
from enum import Enum

from .skill_registry import (
    SkillRegistry, SkillDefinition, SkillCategory,
    get_skill_registry, load_skills
)
from .command_registry import (
    CommandRegistry, CommandDefinition, CommandCategory,
    get_command_registry, load_commands
)
from .specialized_agent_registry import (
    SpecializedAgentRegistry, SpecializedAgentDefinition, AgentDomain,
    get_specialized_agent_registry, load_specialized_agents
)


class ToolType(Enum):
    """Types of tools that can be selected."""
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"


@dataclass
class ToolRecommendation:
    """A recommended tool with relevance score and rationale."""
    tool_type: ToolType
    name: str
    score: float  # 0.0 to 1.0
    rationale: str
    requires_approval: bool = False
    is_proactive: bool = False

    # The actual definition object
    definition: Union[SkillDefinition, CommandDefinition, SpecializedAgentDefinition, None] = None


@dataclass
class SelectionResult:
    """Result of skill selection for a task."""
    task_description: str
    recommendations: List[ToolRecommendation] = field(default_factory=list)
    primary_recommendation: Optional[ToolRecommendation] = None
    approval_required: bool = False
    confidence: float = 0.0  # Overall confidence in recommendations

    def get_skills(self) -> List[ToolRecommendation]:
        """Get only skill recommendations."""
        return [r for r in self.recommendations if r.tool_type == ToolType.SKILL]

    def get_commands(self) -> List[ToolRecommendation]:
        """Get only command recommendations."""
        return [r for r in self.recommendations if r.tool_type == ToolType.COMMAND]

    def get_agents(self) -> List[ToolRecommendation]:
        """Get only agent recommendations."""
        return [r for r in self.recommendations if r.tool_type == ToolType.AGENT]


class SkillSelector:
    """
    Intelligent skill selector that recommends appropriate tools for tasks.

    Searches across skills, commands, and specialized agents to find
    the best matches for a given task description.
    """

    def __init__(
        self,
        skill_registry: Optional[SkillRegistry] = None,
        command_registry: Optional[CommandRegistry] = None,
        agent_registry: Optional[SpecializedAgentRegistry] = None,
    ):
        """
        Initialize the skill selector.

        Args:
            skill_registry: Optional skill registry (uses global if not provided).
            command_registry: Optional command registry (uses global if not provided).
            agent_registry: Optional agent registry (uses global if not provided).
        """
        self._skill_registry = skill_registry
        self._command_registry = command_registry
        self._agent_registry = agent_registry
        self._loaded = False

    def load(self) -> bool:
        """
        Load all registries.

        Returns:
            True if all registries loaded successfully.
        """
        # Get or create registries
        if self._skill_registry is None:
            self._skill_registry = get_skill_registry()
        if self._command_registry is None:
            self._command_registry = get_command_registry()
        if self._agent_registry is None:
            self._agent_registry = get_specialized_agent_registry()

        # Load each registry
        skill_loaded = self._skill_registry.load() if not self._skill_registry.is_loaded else True
        command_loaded = self._command_registry.load() if not self._command_registry.is_loaded else True
        agent_loaded = self._agent_registry.load() if not self._agent_registry.is_loaded else True

        self._loaded = skill_loaded and command_loaded and agent_loaded
        return self._loaded

    @property
    def is_loaded(self) -> bool:
        """Check if all registries are loaded."""
        return self._loaded

    def select(
        self,
        task_description: str,
        include_skills: bool = True,
        include_commands: bool = True,
        include_agents: bool = True,
        max_recommendations: int = 5,
        min_score: float = 0.1,
    ) -> SelectionResult:
        """
        Select the best tools for a task.

        Args:
            task_description: Description of the task to accomplish.
            include_skills: Whether to include skills in recommendations.
            include_commands: Whether to include commands in recommendations.
            include_agents: Whether to include agents in recommendations.
            max_recommendations: Maximum number of recommendations to return.
            min_score: Minimum relevance score to include (0.0 to 1.0).

        Returns:
            SelectionResult with ranked recommendations.
        """
        if not self._loaded:
            self.load()

        all_recommendations: List[ToolRecommendation] = []

        # Search skills
        if include_skills and self._skill_registry:
            skill_matches = self._skill_registry.search(task_description, limit=max_recommendations)
            for skill in skill_matches:
                score = skill.keyword_score(task_description)
                if score >= min_score:
                    rec = ToolRecommendation(
                        tool_type=ToolType.SKILL,
                        name=skill.name,
                        score=score,
                        rationale=f"Matches task: {skill.description[:100]}",
                        requires_approval=skill.requires_approval,
                        is_proactive=skill.is_proactive,
                        definition=skill,
                    )
                    all_recommendations.append(rec)

        # Search commands
        if include_commands and self._command_registry:
            command_matches = self._command_registry.search(task_description, limit=max_recommendations)
            for cmd in command_matches:
                # Simple scoring for commands
                score = 0.5 if cmd.matches_query(task_description) else 0.0
                if task_description.lower() in cmd.purpose.lower():
                    score = 0.7
                if task_description.lower() in cmd.name.lower():
                    score = 0.8

                if score >= min_score:
                    rec = ToolRecommendation(
                        tool_type=ToolType.COMMAND,
                        name=cmd.name,
                        score=score,
                        rationale=f"Command: {cmd.purpose}",
                        requires_approval=cmd.requires_approval,
                        is_proactive=False,
                        definition=cmd,
                    )
                    all_recommendations.append(rec)

        # Search agents
        if include_agents and self._agent_registry:
            agent_matches = self._agent_registry.recommend_for_task(
                task_description, limit=max_recommendations
            )
            for agent in agent_matches:
                score = agent.relevance_score(task_description)
                if score >= min_score:
                    rec = ToolRecommendation(
                        tool_type=ToolType.AGENT,
                        name=agent.name,
                        score=score,
                        rationale=f"Expert in: {agent.expertise}",
                        requires_approval=False,
                        is_proactive=agent.is_proactive,
                        definition=agent,
                    )
                    all_recommendations.append(rec)

        # Sort by score descending
        all_recommendations.sort(key=lambda r: r.score, reverse=True)

        # Limit to max recommendations
        top_recommendations = all_recommendations[:max_recommendations]

        # Determine if approval is required
        approval_required = any(r.requires_approval for r in top_recommendations)

        # Calculate overall confidence
        confidence = top_recommendations[0].score if top_recommendations else 0.0

        # Get primary recommendation
        primary = top_recommendations[0] if top_recommendations else None

        return SelectionResult(
            task_description=task_description,
            recommendations=top_recommendations,
            primary_recommendation=primary,
            approval_required=approval_required,
            confidence=confidence,
        )

    def select_skill(self, query: str) -> Optional[SkillDefinition]:
        """
        Select the single best skill for a query.

        Args:
            query: Search query.

        Returns:
            The best matching skill, or None.
        """
        if not self._loaded:
            self.load()

        if self._skill_registry:
            matches = self._skill_registry.search(query, limit=1)
            return matches[0] if matches else None
        return None

    def select_command(self, query: str) -> Optional[CommandDefinition]:
        """
        Select the single best command for a query.

        Args:
            query: Search query.

        Returns:
            The best matching command, or None.
        """
        if not self._loaded:
            self.load()

        if self._command_registry:
            matches = self._command_registry.search(query, limit=1)
            return matches[0] if matches else None
        return None

    def select_agent(self, task_description: str) -> Optional[SpecializedAgentDefinition]:
        """
        Select the single best agent for a task.

        Args:
            task_description: Description of the task.

        Returns:
            The best matching agent, or None.
        """
        if not self._loaded:
            self.load()

        if self._agent_registry:
            matches = self._agent_registry.recommend_for_task(task_description, limit=1)
            return matches[0] if matches else None
        return None

    def get_proactive_tools(self) -> List[ToolRecommendation]:
        """
        Get all tools marked as proactive (should be suggested without explicit request).

        Returns:
            List of proactive tool recommendations.
        """
        if not self._loaded:
            self.load()

        recommendations = []

        # Proactive skills
        if self._skill_registry:
            for skill in self._skill_registry.get_proactive_skills():
                rec = ToolRecommendation(
                    tool_type=ToolType.SKILL,
                    name=skill.name,
                    score=1.0,
                    rationale=f"Proactive skill: {skill.description[:80]}",
                    is_proactive=True,
                    definition=skill,
                )
                recommendations.append(rec)

        # Proactive agents
        if self._agent_registry:
            for agent in self._agent_registry.get_proactive_agents():
                rec = ToolRecommendation(
                    tool_type=ToolType.AGENT,
                    name=agent.name,
                    score=1.0,
                    rationale=f"Proactive agent: {agent.expertise[:80]}",
                    is_proactive=True,
                    definition=agent,
                )
                recommendations.append(rec)

        return recommendations


# Singleton instance
_skill_selector: Optional[SkillSelector] = None


def get_skill_selector() -> SkillSelector:
    """Get the global skill selector instance."""
    global _skill_selector
    if _skill_selector is None:
        _skill_selector = SkillSelector()
    return _skill_selector


def select_tools_for_task(task_description: str, **kwargs) -> SelectionResult:
    """
    Convenience function to select tools for a task.

    Args:
        task_description: Description of the task.
        **kwargs: Additional arguments for select().

    Returns:
        SelectionResult with recommendations.
    """
    selector = get_skill_selector()
    if not selector.is_loaded:
        selector.load()
    return selector.select(task_description, **kwargs)
