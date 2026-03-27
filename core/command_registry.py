"""
Command Registry - Load and normalize commands from external reference library.

Commands are pre-built workflows that automate common development tasks.
Located externally at AI_Tools_Reference/Commands/COMMANDS_REFERENCE.md
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from pathlib import Path
from enum import Enum
import re


class CommandCategory(Enum):
    """Command categories based on external reference."""
    DEVELOPMENT = "development"
    DOCUMENTATION = "documentation"
    GSD = "gsd"
    OPERATIONS = "operations"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    SECURITY = "security"
    TESTING = "testing"
    WORKFLOW = "workflow"
    UNCATEGORIZED = "uncategorized"


@dataclass
class CommandDefinition:
    """Normalized command definition."""
    name: str
    purpose: str
    usage: str
    use_when: str
    category: CommandCategory = CommandCategory.UNCATEGORIZED
    triggers_skills: List[str] = field(default_factory=list)
    requires_approval: bool = False

    def matches_query(self, query: str) -> bool:
        """Check if command matches a search query."""
        query_lower = query.lower()
        return (
            query_lower in self.name.lower() or
            query_lower in self.purpose.lower() or
            query_lower in self.usage.lower() or
            query_lower in self.use_when.lower()
        )


# Built-in command definitions based on COMMANDS_REFERENCE.md
BUILTIN_COMMANDS: List[Dict] = [
    # Development
    {
        "name": "development-scaffold",
        "purpose": "Scaffold new project structures",
        "usage": "Quickly create boilerplate code and project structure",
        "use_when": "Starting a new project or module",
        "category": CommandCategory.DEVELOPMENT,
    },
    # Documentation
    {
        "name": "documentation-docs-gen",
        "purpose": "Generate documentation from code",
        "usage": "Automatically create docs from source code, comments, and type definitions",
        "use_when": "Need to document your codebase",
        "category": CommandCategory.DOCUMENTATION,
        "triggers_skills": ["docs-writer", "api-documenter"],
    },
    # GSD
    {
        "name": "gsd",
        "purpose": "Main GSD workflow orchestrator",
        "usage": "Comprehensive project planning and execution",
        "use_when": "Starting complex multi-phase projects",
        "category": CommandCategory.GSD,
        "triggers_skills": ["gsd-planner", "gsd-executor", "gsd-verifier"],
    },
    # Operations
    {
        "name": "operations-deploy-validate",
        "purpose": "Validate deployment configurations",
        "usage": "Check deployment configs before pushing to production",
        "use_when": "Before deploying to production",
        "category": CommandCategory.OPERATIONS,
        "requires_approval": True,
    },
    {
        "name": "operations-health-check",
        "purpose": "Check system health and dependencies",
        "usage": "Verify all services and dependencies are running correctly",
        "use_when": "Diagnosing system issues",
        "category": CommandCategory.OPERATIONS,
    },
    {
        "name": "operations-incident-response",
        "purpose": "Guide through incident response procedures",
        "usage": "Structured approach to handling production incidents",
        "use_when": "Production issues or outages occur",
        "category": CommandCategory.OPERATIONS,
        "requires_approval": True,
    },
    # Performance
    {
        "name": "performance-benchmark",
        "purpose": "Run performance benchmarks",
        "usage": "Measure and compare performance metrics",
        "use_when": "Optimizing code or comparing implementations",
        "category": CommandCategory.PERFORMANCE,
        "triggers_skills": ["performance-tuner"],
    },
    {
        "name": "performance-profile",
        "purpose": "Profile application performance",
        "usage": "Identify bottlenecks and performance issues",
        "use_when": "Application is slow or uses too many resources",
        "category": CommandCategory.PERFORMANCE,
        "triggers_skills": ["performance-tuner"],
    },
    # Quality
    {
        "name": "quality-code-health",
        "purpose": "Assess overall code health",
        "usage": "Get a comprehensive code quality report",
        "use_when": "Need to understand codebase quality status",
        "category": CommandCategory.QUALITY,
        "triggers_skills": ["code-reviewer", "refactor-expert"],
    },
    {
        "name": "quality-debt-analysis",
        "purpose": "Analyze technical debt",
        "usage": "Identify areas of technical debt and prioritize fixes",
        "use_when": "Planning refactoring or cleanup sprints",
        "category": CommandCategory.QUALITY,
        "triggers_skills": ["refactor-expert"],
    },
    # Security
    {
        "name": "security-audit",
        "purpose": "Comprehensive security audit",
        "usage": "Check for security vulnerabilities and best practices",
        "use_when": "Before releases or on a regular schedule",
        "category": CommandCategory.SECURITY,
        "triggers_skills": ["security-auditor"],
        "requires_approval": True,
    },
    {
        "name": "security-compliance-check",
        "purpose": "Verify compliance with security standards",
        "usage": "Check against OWASP, CWE, and other security frameworks",
        "use_when": "Need to ensure security compliance",
        "category": CommandCategory.SECURITY,
        "triggers_skills": ["security-auditor"],
    },
    {
        "name": "security-vulnerability-scan",
        "purpose": "Scan for known vulnerabilities",
        "usage": "Check dependencies and code for CVEs",
        "use_when": "Regular security maintenance",
        "category": CommandCategory.SECURITY,
        "triggers_skills": ["security-auditor"],
    },
    # Testing
    {
        "name": "testing-test-gen",
        "purpose": "Generate test cases automatically",
        "usage": "Create unit, integration, or e2e tests from code",
        "use_when": "Need test coverage for new or existing code",
        "category": CommandCategory.TESTING,
        "triggers_skills": ["test-engineer", "test-generator"],
    },
    # Workflow
    {
        "name": "workflow-add-to-todos",
        "purpose": "Add items to your todo list",
        "usage": "Quick way to add tasks",
        "use_when": "Planning or tracking tasks",
        "category": CommandCategory.WORKFLOW,
    },
    {
        "name": "workflow-check-todos",
        "purpose": "Review and manage todos",
        "usage": "Check status and update todo items",
        "use_when": "Need to see what's pending",
        "category": CommandCategory.WORKFLOW,
    },
    {
        "name": "workflow-create-prompt",
        "purpose": "Create reusable prompts",
        "usage": "Build prompt templates for common tasks",
        "use_when": "Want to standardize workflows",
        "category": CommandCategory.WORKFLOW,
    },
    {
        "name": "workflow-handoff-create",
        "purpose": "Create handoff documentation",
        "usage": "Document work for team handoffs",
        "use_when": "Handing off work to another developer",
        "category": CommandCategory.WORKFLOW,
        "triggers_skills": ["docs-writer"],
    },
    {
        "name": "workflow-prompt-create",
        "purpose": "Create custom prompt workflows",
        "usage": "Build multi-step prompt sequences",
        "use_when": "Automating repetitive prompting tasks",
        "category": CommandCategory.WORKFLOW,
    },
    {
        "name": "workflow-prompt-run",
        "purpose": "Execute saved prompt workflows",
        "usage": "Run pre-defined prompt sequences",
        "use_when": "Using saved automation workflows",
        "category": CommandCategory.WORKFLOW,
    },
    {
        "name": "workflow-review",
        "purpose": "Review code or documents systematically",
        "usage": "Structured review process",
        "use_when": "Code reviews or document reviews",
        "category": CommandCategory.WORKFLOW,
        "triggers_skills": ["code-reviewer"],
    },
    {
        "name": "workflow-run-prompt",
        "purpose": "Run a specific prompt workflow",
        "usage": "Execute named prompt workflows",
        "use_when": "Running saved automation",
        "category": CommandCategory.WORKFLOW,
    },
    {
        "name": "workflow-todo-add",
        "purpose": "Add tasks to workflow todos",
        "usage": "Track workflow-specific tasks",
        "use_when": "Managing workflow steps",
        "category": CommandCategory.WORKFLOW,
    },
    {
        "name": "workflow-todo-check",
        "purpose": "Check workflow todo status",
        "usage": "Review workflow task completion",
        "use_when": "Tracking workflow progress",
        "category": CommandCategory.WORKFLOW,
    },
    {
        "name": "workflow-whats-next",
        "purpose": "Suggest next steps in workflow",
        "usage": "Get AI suggestions for what to work on next",
        "use_when": "Unsure what to tackle next",
        "category": CommandCategory.WORKFLOW,
    },
]


class CommandRegistry:
    """
    Registry for loading and querying commands.

    Commands are pre-built workflows that automate common development tasks.
    """

    # Default path to external reference library
    DEFAULT_REFERENCE_PATH = Path("/Users/krissanders/Desktop/AI_Tools_Reference")

    def __init__(self, reference_path: Optional[Path] = None):
        """
        Initialize the command registry.

        Args:
            reference_path: Path to AI_Tools_Reference folder.
        """
        self.reference_path = reference_path or self.DEFAULT_REFERENCE_PATH
        self._commands: Dict[str, CommandDefinition] = {}
        self._loaded = False

    def load(self) -> bool:
        """
        Load commands. Uses built-in definitions by default.

        Returns:
            True if loaded successfully.
        """
        try:
            for cmd_data in BUILTIN_COMMANDS:
                cmd = CommandDefinition(
                    name=cmd_data["name"],
                    purpose=cmd_data["purpose"],
                    usage=cmd_data["usage"],
                    use_when=cmd_data["use_when"],
                    category=cmd_data.get("category", CommandCategory.UNCATEGORIZED),
                    triggers_skills=cmd_data.get("triggers_skills", []),
                    requires_approval=cmd_data.get("requires_approval", False),
                )
                self._commands[cmd.name] = cmd

            self._loaded = True
            return True

        except Exception:
            self._loaded = False
            return False

    @property
    def is_loaded(self) -> bool:
        """Check if commands are loaded."""
        return self._loaded

    @property
    def command_count(self) -> int:
        """Get the number of loaded commands."""
        return len(self._commands)

    def get_command(self, name: str) -> Optional[CommandDefinition]:
        """Get a command by exact name."""
        return self._commands.get(name)

    def search(self, query: str, limit: int = 10) -> List[CommandDefinition]:
        """
        Search for commands matching a query.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of matching commands.
        """
        if not self._loaded:
            return []

        matches = [cmd for cmd in self._commands.values() if cmd.matches_query(query)]
        return matches[:limit]

    def get_by_category(self, category: CommandCategory) -> List[CommandDefinition]:
        """Get all commands in a category."""
        return [cmd for cmd in self._commands.values() if cmd.category == category]

    def get_approval_required(self) -> List[CommandDefinition]:
        """Get all commands that require approval."""
        return [cmd for cmd in self._commands.values() if cmd.requires_approval]

    def list_categories(self) -> Dict[CommandCategory, int]:
        """List all categories with command counts."""
        counts: Dict[CommandCategory, int] = {}
        for cmd in self._commands.values():
            counts[cmd.category] = counts.get(cmd.category, 0) + 1
        return counts

    def all_commands(self) -> List[CommandDefinition]:
        """Get all loaded commands."""
        return list(self._commands.values())

    def get_commands_triggering_skill(self, skill_name: str) -> List[CommandDefinition]:
        """Get all commands that trigger a specific skill."""
        return [
            cmd for cmd in self._commands.values()
            if skill_name in cmd.triggers_skills
        ]


# Singleton instance
_command_registry: Optional[CommandRegistry] = None


def get_command_registry() -> CommandRegistry:
    """Get the global command registry instance."""
    global _command_registry
    if _command_registry is None:
        _command_registry = CommandRegistry()
    return _command_registry


def load_commands(reference_path: Optional[Path] = None) -> CommandRegistry:
    """
    Load commands from registry.

    Args:
        reference_path: Optional custom path to reference library.

    Returns:
        The loaded CommandRegistry instance.
    """
    registry = get_command_registry()
    if reference_path:
        registry.reference_path = reference_path
    registry.load()
    return registry
