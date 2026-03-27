"""
Skill Composer - Multi-skill composition and workflow orchestration.

Combines multiple skills, commands, and agents into coherent workflows
based on workflow patterns from the external reference library.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
from datetime import datetime

from .skill_registry import SkillDefinition, SkillCategory
from .command_registry import CommandDefinition, CommandCategory
from .specialized_agent_registry import SpecializedAgentDefinition, AgentDomain
from .skill_selector import (
    SkillSelector, SelectionResult, ToolRecommendation, ToolType,
    get_skill_selector
)
from .skill_policies import (
    PolicyResult, PolicyDecision, evaluate_skill_policy
)


class CompositionStrategy(Enum):
    """Strategy for composing multiple skills."""
    SEQUENTIAL = "sequential"      # Execute one after another
    PARALLEL = "parallel"          # Execute simultaneously
    CONDITIONAL = "conditional"    # Execute based on conditions
    PIPELINE = "pipeline"          # Output of one feeds into next


@dataclass
class CompositionStep:
    """A single step in a composed workflow."""
    step_number: int
    tool_type: ToolType
    tool_name: str
    description: str
    depends_on: List[int] = field(default_factory=list)  # Step numbers this depends on
    is_optional: bool = False
    policy_result: Optional[PolicyResult] = None

    @property
    def requires_approval(self) -> bool:
        """Check if this step requires approval."""
        if self.policy_result:
            return self.policy_result.decision == PolicyDecision.REQUIRES_APPROVAL
        return False

    @property
    def is_blocked(self) -> bool:
        """Check if this step is blocked."""
        if self.policy_result:
            return self.policy_result.decision == PolicyDecision.BLOCKED
        return False


@dataclass
class ComposedWorkflow:
    """A composed workflow combining multiple skills."""
    name: str
    description: str
    strategy: CompositionStrategy
    steps: List[CompositionStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    role_id: Optional[str] = None

    @property
    def step_count(self) -> int:
        """Get the number of steps."""
        return len(self.steps)

    @property
    def requires_any_approval(self) -> bool:
        """Check if any step requires approval."""
        return any(step.requires_approval for step in self.steps)

    @property
    def has_blocked_steps(self) -> bool:
        """Check if any step is blocked."""
        return any(step.is_blocked for step in self.steps)

    @property
    def executable_steps(self) -> List[CompositionStep]:
        """Get steps that can be executed (not blocked)."""
        return [step for step in self.steps if not step.is_blocked]

    def get_approval_required_steps(self) -> List[CompositionStep]:
        """Get steps that require approval."""
        return [step for step in self.steps if step.requires_approval]

    def get_blocked_steps(self) -> List[CompositionStep]:
        """Get blocked steps."""
        return [step for step in self.steps if step.is_blocked]


# Pre-defined workflow patterns based on WORKFLOW_PATTERNS.md
WORKFLOW_PATTERNS: Dict[str, Dict] = {
    "lead_generation_pipeline": {
        "name": "Lead Generation Pipeline",
        "description": "Apollo → Hunter → HubSpot → Analytics pipeline",
        "strategy": CompositionStrategy.SEQUENTIAL,
        "steps": [
            {"tool_type": ToolType.SKILL, "tool_name": "apollo-automation",
             "description": "Find leads in target industry"},
            {"tool_type": ToolType.SKILL, "tool_name": "hunter-automation",
             "description": "Enrich with additional emails"},
            {"tool_type": ToolType.SKILL, "tool_name": "hubspot-automation",
             "description": "Import leads to CRM"},
            {"tool_type": ToolType.SKILL, "tool_name": "mixpanel-automation",
             "description": "Set up tracking"},
        ],
    },
    "feature_development": {
        "name": "Feature Development",
        "description": "Design → Code → Test → Review → Deploy cycle",
        "strategy": CompositionStrategy.SEQUENTIAL,
        "steps": [
            {"tool_type": ToolType.AGENT, "tool_name": "systems-architect",
             "description": "Design the feature architecture"},
            {"tool_type": ToolType.AGENT, "tool_name": "test-engineer",
             "description": "Generate comprehensive tests"},
            {"tool_type": ToolType.AGENT, "tool_name": "code-reviewer",
             "description": "Review code quality"},
            {"tool_type": ToolType.AGENT, "tool_name": "security-auditor",
             "description": "Security audit"},
            {"tool_type": ToolType.AGENT, "tool_name": "docs-writer",
             "description": "Generate documentation"},
        ],
    },
    "bug_investigation": {
        "name": "Bug Investigation",
        "description": "Systematic debugging workflow",
        "strategy": CompositionStrategy.SEQUENTIAL,
        "steps": [
            {"tool_type": ToolType.AGENT, "tool_name": "root-cause-analyzer",
             "description": "Comprehensive RCA"},
            {"tool_type": ToolType.SKILL, "tool_name": "askgpt",
             "description": "Fresh perspective if stuck", "is_optional": True},
            {"tool_type": ToolType.AGENT, "tool_name": "test-engineer",
             "description": "Generate regression tests"},
            {"tool_type": ToolType.AGENT, "tool_name": "performance-tuner",
             "description": "Performance check", "is_optional": True},
        ],
    },
    "document_processing": {
        "name": "Document Processing Pipeline",
        "description": "Extract → Transform → Store workflow",
        "strategy": CompositionStrategy.SEQUENTIAL,
        "steps": [
            {"tool_type": ToolType.SKILL, "tool_name": "pdf-processing-anthropic",
             "description": "Extract data from PDFs"},
            {"tool_type": ToolType.SKILL, "tool_name": "n8n-workflow-patterns",
             "description": "Set up automation"},
        ],
    },
    "content_creation": {
        "name": "Content Creation Pipeline",
        "description": "Research → Write → Optimize → Distribute",
        "strategy": CompositionStrategy.SEQUENTIAL,
        "steps": [
            {"tool_type": ToolType.SKILL, "tool_name": "content-research-writer",
             "description": "Research and write content"},
            {"tool_type": ToolType.SKILL, "tool_name": "seo-automation",
             "description": "Optimize for SEO"},
        ],
    },
    "security_audit": {
        "name": "Security Audit Workflow",
        "description": "Scan → Analyze → Fix → Verify",
        "strategy": CompositionStrategy.SEQUENTIAL,
        "steps": [
            {"tool_type": ToolType.COMMAND, "tool_name": "security-vulnerability-scan",
             "description": "Scan for vulnerabilities"},
            {"tool_type": ToolType.AGENT, "tool_name": "security-auditor",
             "description": "Comprehensive audit"},
            {"tool_type": ToolType.COMMAND, "tool_name": "security-compliance-check",
             "description": "Compliance verification"},
            {"tool_type": ToolType.AGENT, "tool_name": "test-engineer",
             "description": "Add security tests"},
        ],
    },
    "code_quality": {
        "name": "Code Quality Review",
        "description": "Review → Refactor → Test → Document",
        "strategy": CompositionStrategy.SEQUENTIAL,
        "steps": [
            {"tool_type": ToolType.COMMAND, "tool_name": "quality-code-health",
             "description": "Assess code health"},
            {"tool_type": ToolType.COMMAND, "tool_name": "quality-debt-analysis",
             "description": "Analyze technical debt"},
            {"tool_type": ToolType.AGENT, "tool_name": "refactor-expert",
             "description": "Apply refactoring"},
            {"tool_type": ToolType.AGENT, "tool_name": "test-engineer",
             "description": "Update tests"},
        ],
    },
    "n8n_automation": {
        "name": "n8n Automation Setup",
        "description": "Design → Implement → Test → Deploy workflow automation",
        "strategy": CompositionStrategy.SEQUENTIAL,
        "steps": [
            {"tool_type": ToolType.SKILL, "tool_name": "n8n-workflow-patterns",
             "description": "Design workflow"},
            {"tool_type": ToolType.SKILL, "tool_name": "n8n-code-javascript",
             "description": "Implement transformations"},
            {"tool_type": ToolType.SKILL, "tool_name": "n8n-expression-syntax",
             "description": "Add expressions"},
        ],
    },
}


class SkillComposer:
    """
    Composes multiple skills into coherent workflows.

    Uses predefined patterns and dynamic composition based on task requirements.
    """

    def __init__(self, skill_selector: Optional[SkillSelector] = None):
        """
        Initialize the composer.

        Args:
            skill_selector: Optional skill selector (uses global if not provided).
        """
        self._skill_selector = skill_selector or get_skill_selector()
        self._patterns = dict(WORKFLOW_PATTERNS)
        self._loaded = False

    def load(self) -> bool:
        """Load composer resources."""
        try:
            if not self._skill_selector.is_loaded:
                self._skill_selector.load()
            self._loaded = True
            return True
        except Exception:
            self._loaded = False
            return False

    @property
    def is_loaded(self) -> bool:
        """Check if composer is loaded."""
        return self._loaded

    def get_pattern(self, pattern_name: str) -> Optional[Dict]:
        """Get a workflow pattern by name."""
        return self._patterns.get(pattern_name)

    def list_patterns(self) -> List[str]:
        """List available workflow patterns."""
        return list(self._patterns.keys())

    def compose_from_pattern(
        self,
        pattern_name: str,
        role_id: str = "principal_human",
    ) -> Optional[ComposedWorkflow]:
        """
        Create a workflow from a predefined pattern.

        Args:
            pattern_name: Name of the pattern.
            role_id: Role requesting the workflow.

        Returns:
            ComposedWorkflow or None if pattern not found.
        """
        pattern = self._patterns.get(pattern_name)
        if not pattern:
            return None

        steps = []
        for i, step_data in enumerate(pattern["steps"], start=1):
            # Evaluate policy for this step
            policy_result = evaluate_skill_policy(
                step_data["tool_name"],
                role_id,
                {"tool_type": step_data["tool_type"].value},
            )

            step = CompositionStep(
                step_number=i,
                tool_type=step_data["tool_type"],
                tool_name=step_data["tool_name"],
                description=step_data["description"],
                depends_on=[i - 1] if i > 1 else [],
                is_optional=step_data.get("is_optional", False),
                policy_result=policy_result,
            )
            steps.append(step)

        return ComposedWorkflow(
            name=pattern["name"],
            description=pattern["description"],
            strategy=pattern["strategy"],
            steps=steps,
            role_id=role_id,
        )

    def compose_dynamic(
        self,
        task_description: str,
        role_id: str = "principal_human",
        max_steps: int = 5,
        strategy: CompositionStrategy = CompositionStrategy.SEQUENTIAL,
    ) -> ComposedWorkflow:
        """
        Dynamically compose a workflow based on task description.

        Args:
            task_description: Description of what needs to be done.
            role_id: Role requesting the workflow.
            max_steps: Maximum number of steps.
            strategy: Composition strategy.

        Returns:
            ComposedWorkflow with recommended steps.
        """
        if not self._loaded:
            self.load()

        # Get tool recommendations
        selection = self._skill_selector.select(
            task_description,
            max_recommendations=max_steps,
        )

        steps = []
        for i, rec in enumerate(selection.recommendations, start=1):
            # Evaluate policy
            policy_result = evaluate_skill_policy(
                rec.name,
                role_id,
                {"tool_type": rec.tool_type.value},
            )

            step = CompositionStep(
                step_number=i,
                tool_type=rec.tool_type,
                tool_name=rec.name,
                description=rec.rationale,
                depends_on=[i - 1] if i > 1 and strategy == CompositionStrategy.SEQUENTIAL else [],
                is_optional=False,
                policy_result=policy_result,
            )
            steps.append(step)

        return ComposedWorkflow(
            name=f"Dynamic workflow for: {task_description[:50]}...",
            description=task_description,
            strategy=strategy,
            steps=steps,
            role_id=role_id,
        )

    def suggest_pattern(self, task_description: str) -> Optional[str]:
        """
        Suggest the best workflow pattern for a task.

        Args:
            task_description: Description of the task.

        Returns:
            Pattern name or None.
        """
        task_lower = task_description.lower()

        # Simple keyword matching
        if "lead" in task_lower or "apollo" in task_lower or "crm" in task_lower:
            return "lead_generation_pipeline"

        if "feature" in task_lower or "implement" in task_lower:
            return "feature_development"

        if "bug" in task_lower or "debug" in task_lower or "fix" in task_lower:
            return "bug_investigation"

        if "document" in task_lower or "pdf" in task_lower:
            return "document_processing"

        if "content" in task_lower or "write" in task_lower or "blog" in task_lower:
            return "content_creation"

        if "security" in task_lower or "audit" in task_lower or "vulnerability" in task_lower:
            return "security_audit"

        if "quality" in task_lower or "refactor" in task_lower or "debt" in task_lower:
            return "code_quality"

        if "n8n" in task_lower or "automation" in task_lower or "workflow" in task_lower:
            return "n8n_automation"

        return None

    def add_pattern(self, name: str, pattern: Dict) -> None:
        """Add a custom workflow pattern."""
        self._patterns[name] = pattern


# Singleton instance
_skill_composer: Optional[SkillComposer] = None


def get_skill_composer() -> SkillComposer:
    """Get the global skill composer."""
    global _skill_composer
    if _skill_composer is None:
        _skill_composer = SkillComposer()
    return _skill_composer


def compose_workflow(
    task_description: str,
    role_id: str = "principal_human",
    use_pattern: bool = True,
) -> ComposedWorkflow:
    """
    Compose a workflow for a task.

    Args:
        task_description: Description of the task.
        role_id: Role requesting the workflow.
        use_pattern: Try to match a predefined pattern first.

    Returns:
        ComposedWorkflow.
    """
    composer = get_skill_composer()
    if not composer.is_loaded:
        composer.load()

    if use_pattern:
        pattern_name = composer.suggest_pattern(task_description)
        if pattern_name:
            workflow = composer.compose_from_pattern(pattern_name, role_id)
            if workflow:
                return workflow

    return composer.compose_dynamic(task_description, role_id)
