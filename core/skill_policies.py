"""
Skill Policies - Policy-based skill usage classification and governance.

Classifies skill usage as auto_allowed, requires_approval, or blocked
based on skill characteristics, role permissions, and context.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Callable
from enum import Enum
from datetime import datetime

from .skill_registry import SkillDefinition, SkillCategory
from .command_registry import CommandDefinition, CommandCategory
from .specialized_agent_registry import SpecializedAgentDefinition, AgentDomain
from .role_skill_mappings import RoleSkillMapping, get_role_mapping


class PolicyDecision(Enum):
    """Possible policy decisions for skill usage."""
    AUTO_ALLOWED = "auto_allowed"
    REQUIRES_APPROVAL = "requires_approval"
    BLOCKED = "blocked"


class BlockReason(Enum):
    """Reasons a skill may be blocked."""
    ROLE_NOT_AUTHORIZED = "role_not_authorized"
    SKILL_BLOCKED_BY_POLICY = "skill_blocked_by_policy"
    CATEGORY_BLOCKED = "category_blocked"
    CONTEXT_INAPPROPRIATE = "context_inappropriate"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    EXPLICIT_BLOCKLIST = "explicit_blocklist"


@dataclass
class PolicyResult:
    """Result of policy evaluation."""
    decision: PolicyDecision
    skill_name: str
    role_id: str
    reason: str
    block_reason: Optional[BlockReason] = None
    requires_approval_from: Optional[str] = None  # Role that can approve
    evaluated_at: datetime = field(default_factory=datetime.now)

    @property
    def is_allowed(self) -> bool:
        """Check if the skill is allowed (with or without approval)."""
        return self.decision in (PolicyDecision.AUTO_ALLOWED, PolicyDecision.REQUIRES_APPROVAL)

    @property
    def is_blocked(self) -> bool:
        """Check if the skill is blocked."""
        return self.decision == PolicyDecision.BLOCKED


# Global blocklists
GLOBALLY_BLOCKED_SKILLS: Set[str] = {
    # No skills globally blocked by default
    # Add skills here that should never be used
}

# Skills that always require approval regardless of role
ALWAYS_REQUIRE_APPROVAL: Set[str] = {
    "stripe-automation",
    "paypal-automation",
    "deployment-automation",
    "ci-cd-automation",
    "security-audit",
}

# Categories that are sensitive and need extra scrutiny
SENSITIVE_CATEGORIES: Set[SkillCategory] = {
    SkillCategory.PAYMENT_ECOMMERCE,
    SkillCategory.SECURITY_COMPLIANCE,
    SkillCategory.DEPLOYMENT_DEVOPS,
}

# Command categories that require approval
SENSITIVE_COMMAND_CATEGORIES: Set[CommandCategory] = {
    CommandCategory.SECURITY,
    CommandCategory.OPERATIONS,
}


@dataclass
class SkillPolicy:
    """Policy definition for skill usage."""
    name: str
    description: str
    check: Callable[[str, str, Optional[Dict]], PolicyResult]
    priority: int = 0  # Higher priority policies evaluated first


class SkillPolicyEngine:
    """
    Engine for evaluating skill usage policies.

    Applies policies in priority order to determine if a skill can be used.
    """

    def __init__(self):
        """Initialize the policy engine."""
        self._policies: List[SkillPolicy] = []
        self._loaded = False

    def load(self) -> bool:
        """Load default policies."""
        try:
            self._policies = self._create_default_policies()
            self._policies.sort(key=lambda p: p.priority, reverse=True)
            self._loaded = True
            return True
        except Exception:
            self._loaded = False
            return False

    @property
    def is_loaded(self) -> bool:
        """Check if policies are loaded."""
        return self._loaded

    def _create_default_policies(self) -> List[SkillPolicy]:
        """Create the default policy set."""
        return [
            # Highest priority: Global blocklist
            SkillPolicy(
                name="global_blocklist",
                description="Block globally blocked skills",
                check=self._check_global_blocklist,
                priority=100,
            ),
            # Check role authorization
            SkillPolicy(
                name="role_authorization",
                description="Check if role is authorized for skill",
                check=self._check_role_authorization,
                priority=90,
            ),
            # Check if skill always requires approval
            SkillPolicy(
                name="always_require_approval",
                description="Skills that always need approval",
                check=self._check_always_require_approval,
                priority=80,
            ),
            # Check sensitive categories
            SkillPolicy(
                name="sensitive_category",
                description="Sensitive skill categories need approval",
                check=self._check_sensitive_category,
                priority=70,
            ),
            # Check role-specific approval requirements
            SkillPolicy(
                name="role_specific_approval",
                description="Role-specific approval requirements",
                check=self._check_role_specific_approval,
                priority=60,
            ),
            # Default allow (lowest priority)
            SkillPolicy(
                name="default_allow",
                description="Default to auto-allow if no other policy blocks",
                check=self._check_default_allow,
                priority=0,
            ),
        ]

    def _check_global_blocklist(
        self, skill_name: str, role_id: str, context: Optional[Dict]
    ) -> PolicyResult:
        """Check if skill is globally blocked."""
        if skill_name in GLOBALLY_BLOCKED_SKILLS:
            return PolicyResult(
                decision=PolicyDecision.BLOCKED,
                skill_name=skill_name,
                role_id=role_id,
                reason=f"Skill '{skill_name}' is globally blocked",
                block_reason=BlockReason.EXPLICIT_BLOCKLIST,
            )
        # Continue to next policy
        return None

    def _check_role_authorization(
        self, skill_name: str, role_id: str, context: Optional[Dict]
    ) -> PolicyResult:
        """Check if role is authorized to use skill."""
        mapping = get_role_mapping(role_id)

        if mapping is None:
            # Unknown role - block by default
            return PolicyResult(
                decision=PolicyDecision.BLOCKED,
                skill_name=skill_name,
                role_id=role_id,
                reason=f"Unknown role '{role_id}'",
                block_reason=BlockReason.ROLE_NOT_AUTHORIZED,
            )

        # Check if skill is in role's blocklist
        if skill_name in mapping.blocked_skills:
            return PolicyResult(
                decision=PolicyDecision.BLOCKED,
                skill_name=skill_name,
                role_id=role_id,
                reason=f"Skill '{skill_name}' is blocked for role '{role_id}'",
                block_reason=BlockReason.ROLE_NOT_AUTHORIZED,
            )

        # Get skill category from context if available
        category = context.get("category") if context else None

        # If we have category info, check category authorization
        if category and not mapping.can_use_skill(skill_name, category):
            return PolicyResult(
                decision=PolicyDecision.BLOCKED,
                skill_name=skill_name,
                role_id=role_id,
                reason=f"Role '{role_id}' not authorized for skill category",
                block_reason=BlockReason.CATEGORY_BLOCKED,
            )

        # Continue to next policy
        return None

    def _check_always_require_approval(
        self, skill_name: str, role_id: str, context: Optional[Dict]
    ) -> PolicyResult:
        """Check if skill always requires approval."""
        if skill_name in ALWAYS_REQUIRE_APPROVAL:
            return PolicyResult(
                decision=PolicyDecision.REQUIRES_APPROVAL,
                skill_name=skill_name,
                role_id=role_id,
                reason=f"Skill '{skill_name}' always requires approval",
                requires_approval_from="principal_human",
            )
        # Continue to next policy
        return None

    def _check_sensitive_category(
        self, skill_name: str, role_id: str, context: Optional[Dict]
    ) -> PolicyResult:
        """Check if skill is in a sensitive category."""
        category = context.get("category") if context else None

        if category and category in SENSITIVE_CATEGORIES:
            # Principal can auto-use sensitive skills
            mapping = get_role_mapping(role_id)
            if mapping and mapping.layer.value == "principal":
                return None  # Continue to next policy

            return PolicyResult(
                decision=PolicyDecision.REQUIRES_APPROVAL,
                skill_name=skill_name,
                role_id=role_id,
                reason=f"Skill in sensitive category '{category.value}'",
                requires_approval_from="principal_human",
            )

        # Continue to next policy
        return None

    def _check_role_specific_approval(
        self, skill_name: str, role_id: str, context: Optional[Dict]
    ) -> PolicyResult:
        """Check role-specific approval requirements."""
        mapping = get_role_mapping(role_id)

        if mapping and skill_name in mapping.approval_required_skills:
            return PolicyResult(
                decision=PolicyDecision.REQUIRES_APPROVAL,
                skill_name=skill_name,
                role_id=role_id,
                reason=f"Role '{role_id}' requires approval for skill '{skill_name}'",
                requires_approval_from="principal_human",
            )

        # Continue to next policy
        return None

    def _check_default_allow(
        self, skill_name: str, role_id: str, context: Optional[Dict]
    ) -> PolicyResult:
        """Default policy: allow if no other policy blocks."""
        return PolicyResult(
            decision=PolicyDecision.AUTO_ALLOWED,
            skill_name=skill_name,
            role_id=role_id,
            reason="No policy blocks usage",
        )

    def evaluate(
        self,
        skill_name: str,
        role_id: str,
        context: Optional[Dict] = None,
    ) -> PolicyResult:
        """
        Evaluate all policies for a skill usage request.

        Args:
            skill_name: Name of the skill to use.
            role_id: ID of the role requesting usage.
            context: Optional context dictionary with additional info.

        Returns:
            PolicyResult with the decision.
        """
        if not self._loaded:
            self.load()

        for policy in self._policies:
            result = policy.check(skill_name, role_id, context)
            if result is not None:
                return result

        # Should never reach here, but default to blocked
        return PolicyResult(
            decision=PolicyDecision.BLOCKED,
            skill_name=skill_name,
            role_id=role_id,
            reason="No policy matched (unexpected)",
            block_reason=BlockReason.SKILL_BLOCKED_BY_POLICY,
        )

    def add_policy(self, policy: SkillPolicy) -> None:
        """Add a custom policy."""
        self._policies.append(policy)
        self._policies.sort(key=lambda p: p.priority, reverse=True)

    def can_use_skill(
        self,
        skill_name: str,
        role_id: str,
        context: Optional[Dict] = None,
    ) -> bool:
        """Quick check if skill can be used (auto-allowed)."""
        result = self.evaluate(skill_name, role_id, context)
        return result.decision == PolicyDecision.AUTO_ALLOWED


# Singleton instance
_policy_engine: Optional[SkillPolicyEngine] = None


def get_policy_engine() -> SkillPolicyEngine:
    """Get the global policy engine."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = SkillPolicyEngine()
    return _policy_engine


def evaluate_skill_policy(
    skill_name: str,
    role_id: str,
    context: Optional[Dict] = None,
) -> PolicyResult:
    """
    Evaluate skill usage policy.

    Args:
        skill_name: Name of the skill.
        role_id: ID of the requesting role.
        context: Optional context.

    Returns:
        PolicyResult with decision.
    """
    engine = get_policy_engine()
    if not engine.is_loaded:
        engine.load()
    return engine.evaluate(skill_name, role_id, context)


def can_role_use_skill(
    skill_name: str,
    role_id: str,
    context: Optional[Dict] = None,
) -> bool:
    """Check if role can auto-use a skill."""
    result = evaluate_skill_policy(skill_name, role_id, context)
    return result.decision == PolicyDecision.AUTO_ALLOWED
