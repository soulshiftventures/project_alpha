"""
Role-Skill Mappings - Maps hierarchy roles to recommended skills.

Defines which skills, commands, and agents are appropriate for each
role in the hierarchy system.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum

from .agent_contracts import AgentLayer
from .skill_registry import SkillCategory
from .command_registry import CommandCategory
from .specialized_agent_registry import AgentDomain


@dataclass
class RoleSkillMapping:
    """Mapping of skills and tools for a hierarchy role."""
    role_id: str
    role_name: str
    layer: AgentLayer

    # Allowed skill categories
    allowed_skill_categories: Set[SkillCategory] = field(default_factory=set)

    # Allowed command categories
    allowed_command_categories: Set[CommandCategory] = field(default_factory=set)

    # Allowed agent domains
    allowed_agent_domains: Set[AgentDomain] = field(default_factory=set)

    # Specific skill names this role can use
    allowed_skills: Set[str] = field(default_factory=set)

    # Specific skills this role CANNOT use (blocklist)
    blocked_skills: Set[str] = field(default_factory=set)

    # Skills this role should be proactively offered
    proactive_skills: Set[str] = field(default_factory=set)

    # Skills that require additional approval even if role has access
    approval_required_skills: Set[str] = field(default_factory=set)

    def can_use_skill(self, skill_name: str, category: SkillCategory) -> bool:
        """Check if this role can use a skill."""
        # Check blocklist first
        if skill_name in self.blocked_skills:
            return False

        # Check explicit allowlist
        if skill_name in self.allowed_skills:
            return True

        # Check category allowlist
        if category in self.allowed_skill_categories:
            return True

        return False

    def can_use_command(self, command_category: CommandCategory) -> bool:
        """Check if this role can use commands in a category."""
        return command_category in self.allowed_command_categories

    def can_use_agent(self, agent_domain: AgentDomain) -> bool:
        """Check if this role can invoke agents in a domain."""
        return agent_domain in self.allowed_agent_domains


# Default mappings for hierarchy roles
DEFAULT_ROLE_MAPPINGS: Dict[str, RoleSkillMapping] = {
    # Principal (Human) - Full access
    "principal_human": RoleSkillMapping(
        role_id="principal_human",
        role_name="Human Principal",
        layer=AgentLayer.PRINCIPAL,
        allowed_skill_categories=set(SkillCategory),  # All categories
        allowed_command_categories=set(CommandCategory),  # All categories
        allowed_agent_domains=set(AgentDomain),  # All domains
    ),

    # Executive Layer - Chief Orchestrator
    "chief_orchestrator": RoleSkillMapping(
        role_id="chief_orchestrator",
        role_name="Chief Orchestrator",
        layer=AgentLayer.EXECUTIVE,
        allowed_skill_categories={
            SkillCategory.WORKFLOW_AUTOMATION,
            SkillCategory.PROJECT_MANAGEMENT,
            SkillCategory.ANALYTICS_DATA,
        },
        allowed_command_categories={
            CommandCategory.GSD,
            CommandCategory.WORKFLOW,
            CommandCategory.OPERATIONS,
        },
        allowed_agent_domains={
            AgentDomain.GSD_SUITE,
            AgentDomain.ARCHITECTURE_DESIGN,
        },
        proactive_skills={"gsd-planner", "gsd-roadmapper"},
    ),

    # Council Layer - Strategic Advisors
    "council_strategy": RoleSkillMapping(
        role_id="council_strategy",
        role_name="Strategy Advisor",
        layer=AgentLayer.COUNCIL,
        allowed_skill_categories={
            SkillCategory.RESEARCH_LEARNING,
            SkillCategory.ANALYTICS_DATA,
            SkillCategory.BUSINESS_OPERATIONS,
        },
        allowed_command_categories={
            CommandCategory.QUALITY,
        },
        allowed_agent_domains={
            AgentDomain.ARCHITECTURE_DESIGN,
        },
        proactive_skills={"askgpt", "research-automation"},
    ),

    "council_risk": RoleSkillMapping(
        role_id="council_risk",
        role_name="Risk Advisor",
        layer=AgentLayer.COUNCIL,
        allowed_skill_categories={
            SkillCategory.SECURITY_COMPLIANCE,
            SkillCategory.LEGAL_COMPLIANCE,
        },
        allowed_command_categories={
            CommandCategory.SECURITY,
        },
        allowed_agent_domains={
            AgentDomain.SECURITY,
        },
        proactive_skills={"security-auditor", "compliance-anthropic"},
    ),

    "council_innovation": RoleSkillMapping(
        role_id="council_innovation",
        role_name="Innovation Advisor",
        layer=AgentLayer.COUNCIL,
        allowed_skill_categories={
            SkillCategory.AI_LLM,
            SkillCategory.CONTENT_CREATION,
            SkillCategory.RESEARCH_LEARNING,
        },
        allowed_command_categories={
            CommandCategory.DEVELOPMENT,
        },
        allowed_agent_domains={
            AgentDomain.ARCHITECTURE_DESIGN,
        },
        proactive_skills={"askgpt"},
    ),

    # C-Suite Layer
    "ceo": RoleSkillMapping(
        role_id="ceo",
        role_name="CEO",
        layer=AgentLayer.C_SUITE,
        allowed_skill_categories={
            SkillCategory.BUSINESS_OPERATIONS,
            SkillCategory.PROJECT_MANAGEMENT,
            SkillCategory.ANALYTICS_DATA,
        },
        allowed_command_categories={
            CommandCategory.GSD,
            CommandCategory.OPERATIONS,
        },
        allowed_agent_domains={
            AgentDomain.GSD_SUITE,
        },
    ),

    "cto": RoleSkillMapping(
        role_id="cto",
        role_name="CTO",
        layer=AgentLayer.C_SUITE,
        allowed_skill_categories={
            SkillCategory.DEVELOPMENT_TOOLS,
            SkillCategory.TESTING_QA,
            SkillCategory.DEPLOYMENT_DEVOPS,
            SkillCategory.ARCHITECTURE_PLANNING,
        },
        allowed_command_categories={
            CommandCategory.DEVELOPMENT,
            CommandCategory.TESTING,
            CommandCategory.PERFORMANCE,
            CommandCategory.QUALITY,
        },
        allowed_agent_domains={
            AgentDomain.ARCHITECTURE_DESIGN,
            AgentDomain.CODE_QUALITY,
            AgentDomain.TESTING,
            AgentDomain.PERFORMANCE,
        },
        proactive_skills={"systems-architect", "code-reviewer"},
    ),

    "cfo": RoleSkillMapping(
        role_id="cfo",
        role_name="CFO",
        layer=AgentLayer.C_SUITE,
        allowed_skill_categories={
            SkillCategory.PAYMENT_ECOMMERCE,
            SkillCategory.BUSINESS_OPERATIONS,
            SkillCategory.ANALYTICS_DATA,
        },
        allowed_command_categories=set(),
        allowed_agent_domains=set(),
        approval_required_skills={"stripe-automation", "paypal-automation", "invoice-organizer"},
    ),

    "coo": RoleSkillMapping(
        role_id="coo",
        role_name="COO",
        layer=AgentLayer.C_SUITE,
        allowed_skill_categories={
            SkillCategory.WORKFLOW_AUTOMATION,
            SkillCategory.PROJECT_MANAGEMENT,
            SkillCategory.BUSINESS_OPERATIONS,
        },
        allowed_command_categories={
            CommandCategory.OPERATIONS,
            CommandCategory.WORKFLOW,
        },
        allowed_agent_domains={
            AgentDomain.GSD_SUITE,
        },
    ),

    "cmo": RoleSkillMapping(
        role_id="cmo",
        role_name="CMO",
        layer=AgentLayer.C_SUITE,
        allowed_skill_categories={
            SkillCategory.MARKETING_ADVERTISING,
            SkillCategory.CONTENT_CREATION,
            SkillCategory.SOCIAL_MEDIA,
            SkillCategory.LEAD_GENERATION,
        },
        allowed_command_categories=set(),
        allowed_agent_domains=set(),
        proactive_skills={"content-research-writer", "seo-automation"},
    ),

    # Department Layer - Research
    "dept_research": RoleSkillMapping(
        role_id="dept_research",
        role_name="Research Department",
        layer=AgentLayer.DEPARTMENT,
        allowed_skill_categories={
            SkillCategory.RESEARCH_LEARNING,
            SkillCategory.WEB_AUTOMATION,
            SkillCategory.ANALYTICS_DATA,
        },
        allowed_command_categories=set(),
        allowed_agent_domains={
            AgentDomain.GSD_SUITE,
        },
        proactive_skills={"askgpt", "research-automation"},
    ),

    # Department Layer - Product
    "dept_product": RoleSkillMapping(
        role_id="dept_product",
        role_name="Product Department",
        layer=AgentLayer.DEPARTMENT,
        allowed_skill_categories={
            SkillCategory.PROJECT_MANAGEMENT,
            SkillCategory.DESIGN_MEDIA,
            SkillCategory.ANALYTICS_DATA,
        },
        allowed_command_categories={
            CommandCategory.DEVELOPMENT,
        },
        allowed_agent_domains={
            AgentDomain.ARCHITECTURE_DESIGN,
        },
    ),

    # Department Layer - Operations
    "dept_operations": RoleSkillMapping(
        role_id="dept_operations",
        role_name="Operations Department",
        layer=AgentLayer.DEPARTMENT,
        allowed_skill_categories={
            SkillCategory.WORKFLOW_AUTOMATION,
            SkillCategory.DEPLOYMENT_DEVOPS,
            SkillCategory.CUSTOMER_SUPPORT,
        },
        allowed_command_categories={
            CommandCategory.OPERATIONS,
        },
        allowed_agent_domains=set(),
    ),

    # Department Layer - Growth
    "dept_growth": RoleSkillMapping(
        role_id="dept_growth",
        role_name="Growth Department",
        layer=AgentLayer.DEPARTMENT,
        allowed_skill_categories={
            SkillCategory.LEAD_GENERATION,
            SkillCategory.MARKETING_ADVERTISING,
            SkillCategory.SOCIAL_MEDIA,
            SkillCategory.EMAIL_COMMUNICATION,
        },
        allowed_command_categories=set(),
        allowed_agent_domains=set(),
        proactive_skills={"apollo-automation", "hubspot-automation"},
    ),

    # Department Layer - Content
    "dept_content": RoleSkillMapping(
        role_id="dept_content",
        role_name="Content Department",
        layer=AgentLayer.DEPARTMENT,
        allowed_skill_categories={
            SkillCategory.CONTENT_CREATION,
            SkillCategory.DOCUMENT_PROCESSING,
            SkillCategory.DESIGN_MEDIA,
        },
        allowed_command_categories={
            CommandCategory.DOCUMENTATION,
        },
        allowed_agent_domains={
            AgentDomain.DOCUMENTATION,
        },
        proactive_skills={"content-research-writer", "docs-writer"},
    ),

    # Department Layer - Automation
    "dept_automation": RoleSkillMapping(
        role_id="dept_automation",
        role_name="Automation Department",
        layer=AgentLayer.DEPARTMENT,
        allowed_skill_categories={
            SkillCategory.WORKFLOW_AUTOMATION,
            SkillCategory.WEB_AUTOMATION,
        },
        allowed_command_categories={
            CommandCategory.WORKFLOW,
        },
        allowed_agent_domains=set(),
        proactive_skills={"n8n-workflow-patterns", "n8n-code-javascript"},
    ),

    # Department Layer - Validation
    "dept_validation": RoleSkillMapping(
        role_id="dept_validation",
        role_name="Validation Department",
        layer=AgentLayer.DEPARTMENT,
        allowed_skill_categories={
            SkillCategory.TESTING_QA,
            SkillCategory.SECURITY_COMPLIANCE,
        },
        allowed_command_categories={
            CommandCategory.TESTING,
            CommandCategory.SECURITY,
            CommandCategory.QUALITY,
        },
        allowed_agent_domains={
            AgentDomain.TESTING,
            AgentDomain.SECURITY,
            AgentDomain.CODE_QUALITY,
        },
        proactive_skills={"test-engineer", "security-auditor", "code-reviewer"},
    ),
}


class RoleSkillMappingRegistry:
    """Registry for role-skill mappings."""

    def __init__(self):
        """Initialize the registry with default mappings."""
        self._mappings: Dict[str, RoleSkillMapping] = {}
        self._loaded = False

    def load(self) -> bool:
        """Load default mappings."""
        try:
            self._mappings = dict(DEFAULT_ROLE_MAPPINGS)
            self._loaded = True
            return True
        except Exception:
            self._loaded = False
            return False

    @property
    def is_loaded(self) -> bool:
        """Check if mappings are loaded."""
        return self._loaded

    def get_mapping(self, role_id: str) -> Optional[RoleSkillMapping]:
        """Get mapping for a role."""
        return self._mappings.get(role_id)

    def get_mappings_by_layer(self, layer: AgentLayer) -> List[RoleSkillMapping]:
        """Get all mappings for a layer."""
        return [m for m in self._mappings.values() if m.layer == layer]

    def add_mapping(self, mapping: RoleSkillMapping) -> None:
        """Add or update a role mapping."""
        self._mappings[mapping.role_id] = mapping

    def get_roles_with_skill_access(self, skill_name: str, category: SkillCategory) -> List[str]:
        """Get all roles that can use a skill."""
        return [
            role_id for role_id, mapping in self._mappings.items()
            if mapping.can_use_skill(skill_name, category)
        ]

    def all_mappings(self) -> List[RoleSkillMapping]:
        """Get all mappings."""
        return list(self._mappings.values())


# Singleton instance
_mapping_registry: Optional[RoleSkillMappingRegistry] = None


def get_role_mapping_registry() -> RoleSkillMappingRegistry:
    """Get the global role mapping registry."""
    global _mapping_registry
    if _mapping_registry is None:
        _mapping_registry = RoleSkillMappingRegistry()
    return _mapping_registry


def load_role_mappings() -> RoleSkillMappingRegistry:
    """Load role mappings."""
    registry = get_role_mapping_registry()
    registry.load()
    return registry


def get_role_mapping(role_id: str) -> Optional[RoleSkillMapping]:
    """Get mapping for a role."""
    registry = get_role_mapping_registry()
    if not registry.is_loaded:
        registry.load()
    return registry.get_mapping(role_id)
