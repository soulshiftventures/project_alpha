"""
Skill Invoker - Real skill invocation wiring for Seed Core.

This module provides the actual execution paths for skills, connecting
Seed Core's learning loop to real skill invocation where feasible.

Execution modes supported:
- NOT_INVOKABLE: Skill exists but no invocation path available
- DRY_RUN: Simulated/mock execution (safe for testing)
- REAL_LOCAL: Real local invocation (CLI commands, safe operations)
- CONNECTOR_BACKED: Real external API invocation via connectors
- BLOCKED_POLICY: Blocked by governance policy
- BLOCKED_CREDENTIAL: Blocked by missing credentials/config
"""

import logging
import subprocess
import json
from typing import Any, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
import time

from .skill_registry import SkillDefinition, SkillCategory
from .integration_skill import (
    IntegrationSkill,
    get_integration_skill,
    IntegrationRequest,
    ExecutionMode as IntegrationExecutionMode,
)

logger = logging.getLogger(__name__)


class SkillExecutionMode(Enum):
    """Execution modes for skill invocation."""
    NOT_INVOKABLE = "not_invokable"
    DRY_RUN = "dry_run"
    REAL_LOCAL = "real_local"
    CONNECTOR_BACKED = "connector_backed"
    BLOCKED_POLICY = "blocked_policy"
    BLOCKED_CREDENTIAL = "blocked_credential"


@dataclass
class SkillInvocationResult:
    """Result of a skill invocation attempt."""

    success: bool
    mode: SkillExecutionMode
    output: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    exit_code: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "mode": self.mode.value,
            "output": self.output,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "exit_code": self.exit_code,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


# Skill categories that can be invoked via connectors
CONNECTOR_BACKED_CATEGORIES = {
    SkillCategory.LEAD_GENERATION,
    SkillCategory.EMAIL_COMMUNICATION,
    SkillCategory.PAYMENT_ECOMMERCE,
    SkillCategory.PROJECT_MANAGEMENT,
}

# Skills that are safe for local CLI invocation (internal/read-only operations)
SAFE_LOCAL_SKILLS = {
    "code-reviewer",
    "test-engineer",
    "systematic-debugging",
    "askgpt",
    "docs-writer",
    "api-documenter",
    "refactor-expert",
    "performance-tuner",
    "security-auditor",
}

# Skills with explicit connector mappings
SKILL_TO_CONNECTOR_MAP = {
    "apollo-automation": "apollo",
    "hubspot-automation": "hubspot",
    "stripe-automation": "stripe",
    "sendgrid-automation": "sendgrid",
    "twilio-automation": "twilio",
    "asana-automation": "asana",
    "notion-automation": "notion",
}


class SkillInvoker:
    """
    Real skill invocation engine.

    Determines execution mode for each skill and invokes where feasible.
    """

    def __init__(self, integration_skill: Optional[IntegrationSkill] = None):
        """
        Initialize the skill invoker.

        Args:
            integration_skill: IntegrationSkill instance for connector-backed execution
        """
        self._integration_skill = integration_skill or get_integration_skill()

    def classify_execution_mode(
        self,
        skill: SkillDefinition,
        goal_context: Optional[Dict[str, Any]] = None,
    ) -> SkillExecutionMode:
        """
        Classify which execution mode is appropriate for a skill.

        Args:
            skill: The skill to classify
            goal_context: Optional context about the goal

        Returns:
            The appropriate execution mode
        """
        # Check policy blocks first
        if skill.requires_approval:
            return SkillExecutionMode.BLOCKED_POLICY

        # Check if connector-backed
        if skill.name in SKILL_TO_CONNECTOR_MAP:
            connector_name = SKILL_TO_CONNECTOR_MAP[skill.name]
            # Check if connector is available
            connector_status = self._integration_skill.get_connector_status(connector_name)
            if connector_status and connector_status.get("status") == "ready":
                return SkillExecutionMode.CONNECTOR_BACKED
            else:
                return SkillExecutionMode.BLOCKED_CREDENTIAL

        # Check if category supports connector invocation
        if skill.category in CONNECTOR_BACKED_CATEGORIES:
            # Category supports connectors but no explicit mapping
            return SkillExecutionMode.BLOCKED_CREDENTIAL

        # Check if safe for local invocation
        if skill.name in SAFE_LOCAL_SKILLS:
            return SkillExecutionMode.REAL_LOCAL

        # Check for CLI-based skills (testing, development tools)
        if skill.category in {
            SkillCategory.TESTING_QA,
            SkillCategory.DEVELOPMENT_TOOLS,
            SkillCategory.ARCHITECTURE_PLANNING,
        }:
            return SkillExecutionMode.REAL_LOCAL

        # Default: not invokable (no path available)
        return SkillExecutionMode.NOT_INVOKABLE

    def invoke_skill(
        self,
        skill: SkillDefinition,
        goal_description: str,
        goal_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> SkillInvocationResult:
        """
        Invoke a skill with the appropriate execution mode.

        Args:
            skill: The skill to invoke
            goal_description: Description of the goal
            goal_type: Type of goal
            params: Optional parameters for the skill

        Returns:
            SkillInvocationResult with execution outcome
        """
        params = params or {}

        # Classify execution mode
        mode = self.classify_execution_mode(skill)

        logger.info(f"Invoking skill {skill.name} with mode {mode.value}")

        # Route to appropriate execution method
        if mode == SkillExecutionMode.CONNECTOR_BACKED:
            return self._invoke_connector_backed(skill, goal_description, goal_type, params)
        elif mode == SkillExecutionMode.REAL_LOCAL:
            return self._invoke_local(skill, goal_description, goal_type, params)
        elif mode == SkillExecutionMode.BLOCKED_POLICY:
            return SkillInvocationResult(
                success=False,
                mode=mode,
                error=f"Skill {skill.name} requires approval - execution blocked",
                metadata={"block_reason": "requires_approval"},
            )
        elif mode == SkillExecutionMode.BLOCKED_CREDENTIAL:
            return SkillInvocationResult(
                success=False,
                mode=mode,
                error=f"Skill {skill.name} requires connector setup/credentials",
                metadata={"block_reason": "missing_credentials"},
            )
        elif mode == SkillExecutionMode.NOT_INVOKABLE:
            return SkillInvocationResult(
                success=False,
                mode=mode,
                error=f"Skill {skill.name} has no invocation path available",
                metadata={"block_reason": "no_invocation_path"},
            )
        else:
            # Fallback: dry run
            return self._invoke_dry_run(skill, goal_description, goal_type, params)

    def _invoke_connector_backed(
        self,
        skill: SkillDefinition,
        goal_description: str,
        goal_type: str,
        params: Dict[str, Any],
    ) -> SkillInvocationResult:
        """Invoke a skill via external connector."""
        connector_name = SKILL_TO_CONNECTOR_MAP.get(skill.name)
        if not connector_name:
            return SkillInvocationResult(
                success=False,
                mode=SkillExecutionMode.CONNECTOR_BACKED,
                error=f"No connector mapping for skill {skill.name}",
            )

        # Map goal to connector operation
        operation = self._map_goal_to_operation(goal_type, goal_description, skill.name)

        # Execute via integration skill
        start_time = time.time()
        try:
            request = IntegrationRequest(
                connector=connector_name,
                operation=operation,
                params=params,
                dry_run=False,  # Real execution
                requester="seed_core",
            )

            response = self._integration_skill.execute(request)
            duration = time.time() - start_time

            return SkillInvocationResult(
                success=response.success,
                mode=SkillExecutionMode.CONNECTOR_BACKED,
                output=json.dumps(response.data) if response.data else None,
                error=response.error,
                duration_seconds=duration,
                metadata={
                    "connector": connector_name,
                    "operation": operation,
                    "response_mode": response.mode.value,
                    "policy_decision": response.policy_decision,
                },
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Connector invocation failed: {e}")
            return SkillInvocationResult(
                success=False,
                mode=SkillExecutionMode.CONNECTOR_BACKED,
                error=str(e),
                duration_seconds=duration,
                metadata={"connector": connector_name, "operation": operation},
            )

    def _invoke_local(
        self,
        skill: SkillDefinition,
        goal_description: str,
        goal_type: str,
        params: Dict[str, Any],
    ) -> SkillInvocationResult:
        """Invoke a skill via local CLI (Claude Code Skill tool)."""
        # For now, use a bounded safe approach:
        # Try to invoke via Claude CLI if available

        start_time = time.time()
        try:
            # Construct safe CLI invocation
            # Use subprocess with timeout for safety
            cmd = ["claude", "skill", skill.name, "--prompt", goal_description]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
            )

            duration = time.time() - start_time

            return SkillInvocationResult(
                success=result.returncode == 0,
                mode=SkillExecutionMode.REAL_LOCAL,
                output=result.stdout if result.returncode == 0 else None,
                error=result.stderr if result.returncode != 0 else None,
                duration_seconds=duration,
                exit_code=result.returncode,
                metadata={
                    "command": " ".join(cmd),
                    "invocation_type": "cli",
                },
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return SkillInvocationResult(
                success=False,
                mode=SkillExecutionMode.REAL_LOCAL,
                error="Skill invocation timed out (30s)",
                duration_seconds=duration,
                metadata={"timeout": True},
            )
        except FileNotFoundError:
            # Claude CLI not available, fall back to dry run
            logger.warning("Claude CLI not found, falling back to dry run")
            return self._invoke_dry_run(skill, goal_description, goal_type, params)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Local skill invocation failed: {e}")
            return SkillInvocationResult(
                success=False,
                mode=SkillExecutionMode.REAL_LOCAL,
                error=str(e),
                duration_seconds=duration,
            )

    def _invoke_dry_run(
        self,
        skill: SkillDefinition,
        goal_description: str,
        goal_type: str,
        params: Dict[str, Any],
    ) -> SkillInvocationResult:
        """Perform a dry run (simulation) of skill execution."""
        # Dry run: simulate execution without real invocation
        return SkillInvocationResult(
            success=True,
            mode=SkillExecutionMode.DRY_RUN,
            output=f"DRY RUN: Would invoke {skill.name} for goal: {goal_description}",
            duration_seconds=0.001,
            metadata={
                "simulated": True,
                "skill_category": skill.category.value,
            },
        )

    def _map_goal_to_operation(
        self,
        goal_type: str,
        goal_description: str,
        skill_name: str,
    ) -> str:
        """
        Map goal type and description to connector operation.

        This is a simple heuristic that can be improved with more context.
        """
        goal_desc_lower = goal_description.lower()

        # Simple keyword-based mapping
        if "search" in goal_desc_lower or "find" in goal_desc_lower:
            return "search"
        elif "create" in goal_desc_lower or "add" in goal_desc_lower:
            return "create"
        elif "update" in goal_desc_lower or "modify" in goal_desc_lower:
            return "update"
        elif "delete" in goal_desc_lower or "remove" in goal_desc_lower:
            return "delete"
        elif "list" in goal_desc_lower or "get" in goal_desc_lower:
            return "list"
        else:
            # Default operation
            return "execute"


# Singleton instance
_skill_invoker: Optional[SkillInvoker] = None


def get_skill_invoker() -> SkillInvoker:
    """Get the global SkillInvoker instance."""
    global _skill_invoker
    if _skill_invoker is None:
        _skill_invoker = SkillInvoker()
    return _skill_invoker
