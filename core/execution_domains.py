"""
Execution Domains - Domain classification and metadata for Project Alpha.

Provides domain-aware classification, routing, and policy management to support
domain-neutral execution across multiple business and operational areas.

ARCHITECTURE:
- DomainMetadata: Rich metadata for each execution domain
- Domain classification from goals/requests
- Domain-aware skill/connector mapping
- Domain-specific cost and policy profiles
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum

from .execution_plan import ExecutionDomain


@dataclass
class DomainMetadata:
    """
    Metadata and configuration for an execution domain.

    Defines characteristics, capabilities, and defaults for each domain.
    """
    domain: ExecutionDomain
    display_name: str
    description: str

    # Keywords for classification
    keywords: List[str] = field(default_factory=list)

    # Typical connectors/integrations used in this domain
    typical_connectors: List[str] = field(default_factory=list)

    # Default cost sensitivity (affects policy thresholds)
    default_cost_sensitivity: str = "medium"  # low, medium, high

    # Default approval requirement
    default_approval_level: str = "standard"  # auto, standard, elevated

    # Common operations in this domain
    common_operations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "domain": self.domain.value,
            "display_name": self.display_name,
            "description": self.description,
            "keywords": self.keywords,
            "typical_connectors": self.typical_connectors,
            "default_cost_sensitivity": self.default_cost_sensitivity,
            "default_approval_level": self.default_approval_level,
            "common_operations": self.common_operations,
        }


# Domain metadata registry
DOMAIN_METADATA: Dict[ExecutionDomain, DomainMetadata] = {
    ExecutionDomain.RESEARCH: DomainMetadata(
        domain=ExecutionDomain.RESEARCH,
        display_name="Research & Intelligence",
        description="Market research, competitive intelligence, data gathering, and analysis",
        keywords=["research", "analyze", "investigate", "study", "intel", "competitive", "market", "data", "insights"],
        typical_connectors=["tavily", "firecrawl", "outscraper", "apollo"],
        default_cost_sensitivity="low",
        default_approval_level="auto",
        common_operations=["search", "scrape", "analyze", "gather", "compile"],
    ),

    ExecutionDomain.STRATEGY: DomainMetadata(
        domain=ExecutionDomain.STRATEGY,
        display_name="Strategy & Decision",
        description="Strategic planning, business strategy, decision analysis, and roadmapping",
        keywords=["strategy", "strategic", "decision", "analysis", "plan", "roadmap", "direction", "prioritize"],
        typical_connectors=[],
        default_cost_sensitivity="medium",
        default_approval_level="standard",
        common_operations=["analyze", "evaluate", "plan", "recommend", "prioritize"],
    ),

    ExecutionDomain.PLANNING: DomainMetadata(
        domain=ExecutionDomain.PLANNING,
        display_name="Planning & Coordination",
        description="Project planning, resource allocation, scheduling, and coordination",
        keywords=["plan", "schedule", "coordinate", "allocate", "organize", "timeline", "milestone"],
        typical_connectors=[],
        default_cost_sensitivity="low",
        default_approval_level="auto",
        common_operations=["plan", "schedule", "coordinate", "track", "organize"],
    ),

    ExecutionDomain.PRODUCT: DomainMetadata(
        domain=ExecutionDomain.PRODUCT,
        display_name="Product Development",
        description="Product development, feature planning, requirements, and product management",
        keywords=["product", "feature", "requirement", "mvp", "roadmap", "backlog", "user story"],
        typical_connectors=[],
        default_cost_sensitivity="medium",
        default_approval_level="standard",
        common_operations=["design", "build", "spec", "prioritize", "release"],
    ),

    ExecutionDomain.ENGINEERING: DomainMetadata(
        domain=ExecutionDomain.ENGINEERING,
        display_name="Engineering & Development",
        description="Software development, technical implementation, and infrastructure",
        keywords=["code", "develop", "implement", "deploy", "deployment", "engineer", "technical", "software", "debug", "ci/cd", "pipeline"],
        typical_connectors=[],
        default_cost_sensitivity="medium",
        default_approval_level="standard",
        common_operations=["code", "build", "test", "deploy", "debug"],
    ),

    ExecutionDomain.VALIDATION: DomainMetadata(
        domain=ExecutionDomain.VALIDATION,
        display_name="Testing & Validation",
        description="Testing, QA, validation, verification, and quality assurance",
        keywords=["test", "validate", "verify", "qa", "quality", "check", "audit"],
        typical_connectors=[],
        default_cost_sensitivity="low",
        default_approval_level="auto",
        common_operations=["test", "verify", "validate", "check", "audit"],
    ),

    ExecutionDomain.OPERATIONS: DomainMetadata(
        domain=ExecutionDomain.OPERATIONS,
        display_name="Operations & Execution",
        description="Day-to-day operations, process execution, and operational management",
        keywords=["operate", "execute", "run", "manage", "process", "workflow", "routine"],
        typical_connectors=[],
        default_cost_sensitivity="medium",
        default_approval_level="standard",
        common_operations=["execute", "manage", "monitor", "maintain", "optimize"],
    ),

    ExecutionDomain.AUTOMATION: DomainMetadata(
        domain=ExecutionDomain.AUTOMATION,
        display_name="Automation & Workflows",
        description="Workflow automation, process automation, and integration",
        keywords=["automate", "workflow", "trigger", "integrate", "script", "batch"],
        typical_connectors=[],
        default_cost_sensitivity="low",
        default_approval_level="auto",
        common_operations=["automate", "trigger", "schedule", "integrate", "batch"],
    ),

    ExecutionDomain.INTERNAL_ADMIN: DomainMetadata(
        domain=ExecutionDomain.INTERNAL_ADMIN,
        display_name="Internal Administration",
        description="Internal administration, housekeeping, maintenance, and support tasks",
        keywords=["admin", "internal", "housekeeping", "maintenance", "cleanup", "support"],
        typical_connectors=[],
        default_cost_sensitivity="low",
        default_approval_level="auto",
        common_operations=["cleanup", "maintain", "archive", "backup", "organize"],
    ),

    ExecutionDomain.FINANCE: DomainMetadata(
        domain=ExecutionDomain.FINANCE,
        display_name="Finance & Accounting",
        description="Financial planning, budgeting, accounting, and financial management",
        keywords=["finance", "financial", "budget", "accounting", "invoice", "payment", "revenue", "expense", "expenses"],
        typical_connectors=["stripe"],
        default_cost_sensitivity="high",
        default_approval_level="elevated",
        common_operations=["invoice", "track", "reconcile", "report", "forecast"],
    ),

    ExecutionDomain.COMPLIANCE: DomainMetadata(
        domain=ExecutionDomain.COMPLIANCE,
        display_name="Compliance & Legal",
        description="Legal compliance, regulatory requirements, auditing, and governance",
        keywords=["compliance", "legal", "regulatory", "audit", "gdpr", "policy", "governance"],
        typical_connectors=[],
        default_cost_sensitivity="high",
        default_approval_level="elevated",
        common_operations=["audit", "verify", "report", "document", "review"],
    ),

    ExecutionDomain.GROWTH: DomainMetadata(
        domain=ExecutionDomain.GROWTH,
        display_name="Growth & Expansion",
        description="Business growth, expansion, scaling, and market development",
        keywords=["growth", "scale", "expand", "acquire", "lead", "leads", "prospect", "prospects", "outreach", "sales", "marketing", "campaign", "acquisition"],
        typical_connectors=["apollo", "instantly", "smartlead", "hubspot", "sendgrid"],
        default_cost_sensitivity="medium",
        default_approval_level="standard",
        common_operations=["prospect", "outreach", "qualify", "nurture", "convert"],
    ),

    ExecutionDomain.CUSTOMER_SUPPORT: DomainMetadata(
        domain=ExecutionDomain.CUSTOMER_SUPPORT,
        display_name="Customer Support",
        description="Customer service, support, success, and relationship management",
        keywords=["support", "customer", "service", "help", "issue", "ticket", "success"],
        typical_connectors=["hubspot", "telegram", "sendgrid"],
        default_cost_sensitivity="low",
        default_approval_level="auto",
        common_operations=["respond", "resolve", "track", "escalate", "follow-up"],
    ),

    ExecutionDomain.CONTENT: DomainMetadata(
        domain=ExecutionDomain.CONTENT,
        display_name="Content & Documentation",
        description="Content creation, documentation, knowledge management, and communication",
        keywords=["content", "document", "documentation", "write", "blog", "publish", "knowledge", "article", "guide"],
        typical_connectors=[],
        default_cost_sensitivity="low",
        default_approval_level="auto",
        common_operations=["write", "edit", "publish", "document", "organize"],
    ),

    ExecutionDomain.UNKNOWN: DomainMetadata(
        domain=ExecutionDomain.UNKNOWN,
        display_name="Unclassified",
        description="Unclassified or multi-domain operations",
        keywords=[],
        typical_connectors=[],
        default_cost_sensitivity="medium",
        default_approval_level="standard",
        common_operations=[],
    ),
}


def get_domain_metadata(domain: ExecutionDomain) -> DomainMetadata:
    """Get metadata for a domain."""
    return DOMAIN_METADATA.get(domain, DOMAIN_METADATA[ExecutionDomain.UNKNOWN])


def classify_goal_domain(goal: str, context: Optional[Dict] = None) -> ExecutionDomain:
    """
    Classify a goal or request into an execution domain.

    Uses keyword matching and context to determine the most appropriate domain.

    Args:
        goal: Goal or request description
        context: Optional context with hints (role, business_id, etc.)

    Returns:
        ExecutionDomain classification
    """
    goal_lower = goal.lower()

    # Score each domain based on keyword matches
    scores: Dict[ExecutionDomain, int] = {}

    for domain, metadata in DOMAIN_METADATA.items():
        if domain == ExecutionDomain.UNKNOWN:
            continue

        score = 0
        for keyword in metadata.keywords:
            if keyword in goal_lower:
                score += 1

        if score > 0:
            scores[domain] = score

    # Use context hints if available
    if context:
        role = context.get("role", "").lower()

        # Role-based hints
        if role in ["cfo", "finance"]:
            scores[ExecutionDomain.FINANCE] = scores.get(ExecutionDomain.FINANCE, 0) + 2
        elif role in ["cto", "engineer"]:
            scores[ExecutionDomain.ENGINEERING] = scores.get(ExecutionDomain.ENGINEERING, 0) + 2
        elif role in ["cmo", "marketing"]:
            scores[ExecutionDomain.GROWTH] = scores.get(ExecutionDomain.GROWTH, 0) + 1
            scores[ExecutionDomain.CONTENT] = scores.get(ExecutionDomain.CONTENT, 0) + 1
        elif role in ["coo", "operations"]:
            scores[ExecutionDomain.OPERATIONS] = scores.get(ExecutionDomain.OPERATIONS, 0) + 2
        elif role in ["ceo", "principal"]:
            scores[ExecutionDomain.STRATEGY] = scores.get(ExecutionDomain.STRATEGY, 0) + 2

    # Return domain with highest score
    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]

    return ExecutionDomain.UNKNOWN


def get_domain_connectors(domain: ExecutionDomain) -> List[str]:
    """Get typical connectors for a domain."""
    metadata = get_domain_metadata(domain)
    return metadata.typical_connectors


def get_all_domains() -> List[ExecutionDomain]:
    """Get all execution domains except UNKNOWN."""
    return [d for d in ExecutionDomain if d != ExecutionDomain.UNKNOWN]


def get_domain_display_name(domain: ExecutionDomain) -> str:
    """Get display name for a domain."""
    return get_domain_metadata(domain).display_name


def get_domain_summary() -> Dict:
    """Get summary of all domains for UI/reporting."""
    return {
        "total_domains": len(DOMAIN_METADATA) - 1,  # Exclude UNKNOWN
        "domains": [
            {
                "value": domain.value,
                "display_name": metadata.display_name,
                "description": metadata.description,
            }
            for domain, metadata in DOMAIN_METADATA.items()
            if domain != ExecutionDomain.UNKNOWN
        ]
    }
