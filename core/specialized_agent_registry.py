"""
Specialized Agent Registry - Load and normalize specialized agents from external reference.

Specialized agents are AI assistants with specific expertise and tools.
Located externally at AI_Tools_Reference/Agents/AGENTS_REFERENCE.md
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from pathlib import Path
from enum import Enum


class AgentDomain(Enum):
    """Agent domain categories based on external reference."""
    ARCHITECTURE_DESIGN = "architecture_design"
    CODE_QUALITY = "code_quality"
    DEBUGGING = "debugging"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    GSD_SUITE = "gsd_suite"
    UNCATEGORIZED = "uncategorized"


@dataclass
class SpecializedAgentDefinition:
    """Normalized specialized agent definition."""
    name: str
    expertise: str
    tools: List[str] = field(default_factory=list)
    use_when: List[str] = field(default_factory=list)
    domain: AgentDomain = AgentDomain.UNCATEGORIZED
    is_proactive: bool = False
    spawned_by: Optional[str] = None
    produces: Optional[str] = None

    def matches_query(self, query: str) -> bool:
        """Check if agent matches a search query."""
        query_lower = query.lower()
        if query_lower in self.name.lower():
            return True
        if query_lower in self.expertise.lower():
            return True
        for use_case in self.use_when:
            if query_lower in use_case.lower():
                return True
        return False

    def relevance_score(self, task_description: str) -> float:
        """Score how relevant this agent is for a task (0.0 to 1.0)."""
        task_lower = task_description.lower()
        score = 0.0

        # Check expertise match
        expertise_words = self.expertise.lower().split()
        for word in expertise_words:
            if len(word) > 3 and word in task_lower:
                score += 0.1

        # Check use_when match
        for use_case in self.use_when:
            use_lower = use_case.lower()
            if use_lower in task_lower or task_lower in use_lower:
                score += 0.3

        # Check name match
        if self.name.lower() in task_lower:
            score += 0.5

        return min(score, 1.0)


# Built-in agent definitions based on AGENTS_REFERENCE.md
BUILTIN_AGENTS: List[Dict] = [
    # Architecture & Design
    {
        "name": "systems-architect",
        "expertise": "System design, architecture patterns, scalability",
        "tools": ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "WebFetch", "Task"],
        "use_when": ["Designing new systems or features", "Evaluating architectural trade-offs",
                     "Planning technical strategy", "Reviewing system design"],
        "domain": AgentDomain.ARCHITECTURE_DESIGN,
        "is_proactive": True,
    },
    # Code Quality & Refactoring
    {
        "name": "refactor-expert",
        "expertise": "Clean code, SOLID principles, technical debt reduction",
        "tools": ["Read", "Edit", "Grep", "Glob", "Bash", "Task", "Skill"],
        "use_when": ["Refactoring legacy code", "Improving code architecture",
                     "Reducing technical debt", "Applying design patterns"],
        "domain": AgentDomain.CODE_QUALITY,
        "is_proactive": True,
    },
    {
        "name": "code-reviewer",
        "expertise": "Code style, patterns, bugs, security basics",
        "tools": ["Automatic code analysis"],
        "use_when": ["Files are modified, saved, or committed", "Need code quality feedback",
                     "Want best practices analysis"],
        "domain": AgentDomain.CODE_QUALITY,
        "is_proactive": True,
    },
    # Debugging & Problem Solving
    {
        "name": "gsd-debugger",
        "expertise": "Scientific debugging method, checkpoint management",
        "tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "WebSearch"],
        "use_when": ["Complex bugs requiring investigation", "Need systematic debugging approach",
                     "Performance issues", "Production incidents"],
        "domain": AgentDomain.DEBUGGING,
        "spawned_by": "/gsd:debug orchestrator",
    },
    {
        "name": "root-cause-analyzer",
        "expertise": "Deep RCA (Root Cause Analysis), minimal-impact fixes",
        "tools": ["Read", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
        "use_when": ["Complex bugs requiring deep investigation", "Performance issues",
                     "Production incidents", "Need comprehensive root cause analysis"],
        "domain": AgentDomain.DEBUGGING,
        "is_proactive": True,
    },
    # Security & Safety
    {
        "name": "security-auditor",
        "expertise": "Security vulnerability assessment, OWASP compliance, secure auth",
        "tools": ["Read", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
        "use_when": ["Security reviews needed", "Authentication flow implementation",
                     "Vulnerability analysis", "Compliance checking"],
        "domain": AgentDomain.SECURITY,
        "is_proactive": True,
    },
    {
        "name": "config-safety-reviewer",
        "expertise": "Production reliability, magic numbers, pool sizes, timeouts",
        "tools": ["Read", "Edit", "Grep", "Glob", "Bash", "Task", "Skill"],
        "use_when": ["Configuration changes", "Production safety reviews",
                     "Setting up connection pools", "Defining timeouts and limits"],
        "domain": AgentDomain.SECURITY,
        "is_proactive": True,
    },
    # Performance
    {
        "name": "performance-tuner",
        "expertise": "Profiling, optimization, bottleneck analysis, scalability",
        "tools": ["Read", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
        "use_when": ["Performance issues", "Bottleneck analysis",
                     "Optimization tasks", "Scalability improvements"],
        "domain": AgentDomain.PERFORMANCE,
        "is_proactive": True,
    },
    # Testing
    {
        "name": "test-engineer",
        "expertise": "Comprehensive testing, test creation, quality assurance",
        "tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
        "use_when": ["Need test generation", "Test coverage analysis",
                     "Quality assurance", "All testing levels (unit, integration, e2e)"],
        "domain": AgentDomain.TESTING,
        "is_proactive": True,
    },
    # Documentation
    {
        "name": "docs-writer",
        "expertise": "Technical documentation, API docs, user guides",
        "tools": ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "WebFetch", "Skill"],
        "use_when": ["Creating API documentation", "Writing user guides",
                     "Technical documentation needed", "Documentation for any project type"],
        "domain": AgentDomain.DOCUMENTATION,
        "is_proactive": True,
    },
    # GSD Suite
    {
        "name": "gsd-planner",
        "expertise": "Executable phase plans, task breakdown, dependency analysis",
        "tools": ["Read", "Write", "Bash", "Glob", "Grep", "WebFetch"],
        "use_when": ["Creating phase plans", "Breaking down complex tasks",
                     "Analyzing dependencies", "Goal-backward verification"],
        "domain": AgentDomain.GSD_SUITE,
        "spawned_by": "/gsd:plan-phase orchestrator",
    },
    {
        "name": "gsd-executor",
        "expertise": "Plan execution, atomic commits, deviation handling",
        "tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        "use_when": ["Executing GSD plans", "Need atomic commits",
                     "Checkpoint protocols", "State management"],
        "domain": AgentDomain.GSD_SUITE,
        "spawned_by": "execute-phase orchestrator or execute-plan command",
    },
    {
        "name": "gsd-verifier",
        "expertise": "Goal verification, codebase validation",
        "tools": ["Read", "Write", "Bash", "Grep", "Glob"],
        "use_when": ["Verifying phase completion", "Goal-backward analysis",
                     "Ensuring deliverables match promises"],
        "domain": AgentDomain.GSD_SUITE,
        "produces": "VERIFICATION.md report",
    },
    {
        "name": "gsd-phase-researcher",
        "expertise": "Phase implementation research",
        "tools": ["Read", "Write", "Bash", "Grep", "Glob", "WebSearch", "WebFetch"],
        "use_when": ["Researching implementation approaches", "Understanding phase requirements"],
        "domain": AgentDomain.GSD_SUITE,
        "spawned_by": "/gsd:plan-phase orchestrator",
        "produces": "RESEARCH.md for gsd-planner",
    },
    {
        "name": "gsd-plan-checker",
        "expertise": "Plan validation, goal-backward analysis",
        "tools": ["Read", "Bash", "Glob", "Grep"],
        "use_when": ["Verifying plan will achieve goals", "Quality checking plans before execution"],
        "domain": AgentDomain.GSD_SUITE,
        "spawned_by": "/gsd:plan-phase orchestrator",
    },
    {
        "name": "gsd-integration-checker",
        "expertise": "Cross-phase integration, E2E flow verification",
        "tools": ["Read", "Bash", "Grep", "Glob"],
        "use_when": ["Verifying phases connect properly", "End-to-end workflow validation"],
        "domain": AgentDomain.GSD_SUITE,
    },
    {
        "name": "gsd-roadmapper",
        "expertise": "Project roadmaps, phase breakdown, success criteria",
        "tools": ["Read", "Write", "Bash", "Glob", "Grep"],
        "use_when": ["Creating project roadmaps", "Phase breakdown needed",
                     "Requirement mapping", "Success criteria derivation"],
        "domain": AgentDomain.GSD_SUITE,
        "spawned_by": "/gsd:new-project orchestrator",
    },
    {
        "name": "gsd-research-synthesizer",
        "expertise": "Research synthesis, summary creation",
        "tools": ["Read", "Write", "Bash"],
        "use_when": ["Synthesizing research outputs", "Creating SUMMARY.md"],
        "domain": AgentDomain.GSD_SUITE,
        "spawned_by": "/gsd:new-project after 4 researcher agents complete",
    },
    {
        "name": "gsd-project-researcher",
        "expertise": "Domain ecosystem research",
        "tools": ["Read", "Write", "Bash", "Grep", "Glob", "WebSearch", "WebFetch"],
        "use_when": ["Researching domain before roadmap", "Understanding project ecosystem"],
        "domain": AgentDomain.GSD_SUITE,
        "spawned_by": "/gsd:new-project or /gsd:new-milestone",
        "produces": "Files in .planning/research/",
    },
    {
        "name": "gsd-codebase-mapper",
        "expertise": "Codebase analysis, structured documentation",
        "tools": ["Read", "Bash", "Grep", "Glob", "Write"],
        "use_when": ["Exploring codebase structure", "Writing analysis documents",
                     "Understanding architecture"],
        "domain": AgentDomain.GSD_SUITE,
        "spawned_by": "map-codebase with focus area",
    },
]


class SpecializedAgentRegistry:
    """
    Registry for loading and querying specialized agents.

    Specialized agents are AI assistants with specific expertise and tools.
    """

    # Default path to external reference library
    DEFAULT_REFERENCE_PATH = Path("/Users/krissanders/Desktop/AI_Tools_Reference")

    def __init__(self, reference_path: Optional[Path] = None):
        """
        Initialize the agent registry.

        Args:
            reference_path: Path to AI_Tools_Reference folder.
        """
        self.reference_path = reference_path or self.DEFAULT_REFERENCE_PATH
        self._agents: Dict[str, SpecializedAgentDefinition] = {}
        self._loaded = False

    def load(self) -> bool:
        """
        Load agents. Uses built-in definitions by default.

        Returns:
            True if loaded successfully.
        """
        try:
            for agent_data in BUILTIN_AGENTS:
                agent = SpecializedAgentDefinition(
                    name=agent_data["name"],
                    expertise=agent_data["expertise"],
                    tools=agent_data.get("tools", []),
                    use_when=agent_data.get("use_when", []),
                    domain=agent_data.get("domain", AgentDomain.UNCATEGORIZED),
                    is_proactive=agent_data.get("is_proactive", False),
                    spawned_by=agent_data.get("spawned_by"),
                    produces=agent_data.get("produces"),
                )
                self._agents[agent.name] = agent

            self._loaded = True
            return True

        except Exception:
            self._loaded = False
            return False

    @property
    def is_loaded(self) -> bool:
        """Check if agents are loaded."""
        return self._loaded

    @property
    def agent_count(self) -> int:
        """Get the number of loaded agents."""
        return len(self._agents)

    def get_agent(self, name: str) -> Optional[SpecializedAgentDefinition]:
        """Get an agent by exact name."""
        return self._agents.get(name)

    def search(self, query: str, limit: int = 10) -> List[SpecializedAgentDefinition]:
        """
        Search for agents matching a query.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of matching agents.
        """
        if not self._loaded:
            return []

        matches = [agent for agent in self._agents.values() if agent.matches_query(query)]
        return matches[:limit]

    def recommend_for_task(self, task_description: str, limit: int = 3) -> List[SpecializedAgentDefinition]:
        """
        Recommend agents for a task based on relevance scoring.

        Args:
            task_description: Description of the task.
            limit: Maximum number of recommendations.

        Returns:
            List of recommended agents, sorted by relevance.
        """
        if not self._loaded:
            return []

        # Score all agents
        scored = []
        for agent in self._agents.values():
            score = agent.relevance_score(task_description)
            if score > 0:
                scored.append((score, agent))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [agent for _, agent in scored[:limit]]

    def get_by_domain(self, domain: AgentDomain) -> List[SpecializedAgentDefinition]:
        """Get all agents in a domain."""
        return [agent for agent in self._agents.values() if agent.domain == domain]

    def get_proactive_agents(self) -> List[SpecializedAgentDefinition]:
        """Get all agents marked as proactive."""
        return [agent for agent in self._agents.values() if agent.is_proactive]

    def get_gsd_agents(self) -> List[SpecializedAgentDefinition]:
        """Get all GSD suite agents."""
        return self.get_by_domain(AgentDomain.GSD_SUITE)

    def list_domains(self) -> Dict[AgentDomain, int]:
        """List all domains with agent counts."""
        counts: Dict[AgentDomain, int] = {}
        for agent in self._agents.values():
            counts[agent.domain] = counts.get(agent.domain, 0) + 1
        return counts

    def all_agents(self) -> List[SpecializedAgentDefinition]:
        """Get all loaded agents."""
        return list(self._agents.values())


# Singleton instance
_agent_registry: Optional[SpecializedAgentRegistry] = None


def get_specialized_agent_registry() -> SpecializedAgentRegistry:
    """Get the global specialized agent registry instance."""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = SpecializedAgentRegistry()
    return _agent_registry


def load_specialized_agents(reference_path: Optional[Path] = None) -> SpecializedAgentRegistry:
    """
    Load specialized agents from registry.

    Args:
        reference_path: Optional custom path to reference library.

    Returns:
        The loaded SpecializedAgentRegistry instance.
    """
    registry = get_specialized_agent_registry()
    if reference_path:
        registry.reference_path = reference_path
    registry.load()
    return registry
