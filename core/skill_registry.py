"""
Skill Registry - Load and normalize skills from external reference library.

Reads from the external AI_Tools_Reference folder (read-only).
Provides normalized skill definitions for use by the hierarchy system.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from pathlib import Path
from enum import Enum


class SkillCategory(Enum):
    """Skill categories based on external reference library."""
    AI_LLM = "ai_llm"
    LEAD_GENERATION = "lead_generation"
    PROJECT_MANAGEMENT = "project_management"
    EMAIL_COMMUNICATION = "email_communication"
    DOCUMENT_PROCESSING = "document_processing"
    WEB_AUTOMATION = "web_automation"
    PAYMENT_ECOMMERCE = "payment_ecommerce"
    SOCIAL_MEDIA = "social_media"
    DEVELOPMENT_TOOLS = "development_tools"
    TESTING_QA = "testing_qa"
    CONTENT_CREATION = "content_creation"
    SECURITY_COMPLIANCE = "security_compliance"
    ANALYTICS_DATA = "analytics_data"
    DESIGN_MEDIA = "design_media"
    WORKFLOW_AUTOMATION = "workflow_automation"
    LEGAL_COMPLIANCE = "legal_compliance"
    RESEARCH_LEARNING = "research_learning"
    BUSINESS_OPERATIONS = "business_operations"
    CUSTOMER_SUPPORT = "customer_support"
    MARKETING_ADVERTISING = "marketing_advertising"
    ARCHITECTURE_PLANNING = "architecture_planning"
    DEPLOYMENT_DEVOPS = "deployment_devops"
    GSD_SUITE = "gsd_suite"
    UNCATEGORIZED = "uncategorized"


@dataclass
class SkillDefinition:
    """Normalized skill definition."""
    name: str
    description: str
    path: str
    keywords: List[str] = field(default_factory=list)
    category: SkillCategory = SkillCategory.UNCATEGORIZED
    is_proactive: bool = False
    requires_approval: bool = False

    def matches_query(self, query: str) -> bool:
        """Check if skill matches a search query."""
        query_lower = query.lower()
        if query_lower in self.name.lower():
            return True
        if query_lower in self.description.lower():
            return True
        for keyword in self.keywords:
            if query_lower in keyword.lower():
                return True
        return False

    def keyword_score(self, query: str) -> float:
        """Score how well this skill matches a query (0.0 to 1.0)."""
        query_lower = query.lower()
        score = 0.0

        # Exact name match
        if query_lower == self.name.lower():
            return 1.0

        # Name contains query
        if query_lower in self.name.lower():
            score = max(score, 0.8)

        # Description contains query
        if query_lower in self.description.lower():
            score = max(score, 0.6)

        # Keyword matches
        for keyword in self.keywords:
            if query_lower == keyword.lower():
                score = max(score, 0.7)
            elif query_lower in keyword.lower():
                score = max(score, 0.4)

        return score


# Category detection patterns
CATEGORY_PATTERNS: Dict[SkillCategory, List[str]] = {
    SkillCategory.AI_LLM: ["anthropic", "openai", "perplexity", "claude", "gpt", "llm", "ai-ml"],
    SkillCategory.LEAD_GENERATION: ["apollo", "hubspot", "salesforce", "pipedrive", "zoho", "crm", "lead", "hunter"],
    SkillCategory.PROJECT_MANAGEMENT: ["asana", "trello", "jira", "monday", "clickup", "notion", "airtable"],
    SkillCategory.EMAIL_COMMUNICATION: ["gmail", "outlook", "sendgrid", "mailchimp", "email", "telegram", "slack", "discord", "twilio"],
    SkillCategory.DOCUMENT_PROCESSING: ["pdf", "docx", "document", "tabular"],
    SkillCategory.WEB_AUTOMATION: ["scraping", "selenium", "puppeteer", "beautiful-soup", "web-scraping"],
    SkillCategory.PAYMENT_ECOMMERCE: ["stripe", "paypal", "shopify", "woocommerce", "square", "payment", "invoice", "lemon-squeezy"],
    SkillCategory.SOCIAL_MEDIA: ["twitter", "facebook", "instagram", "linkedin", "tiktok", "youtube", "social"],
    SkillCategory.DEVELOPMENT_TOOLS: ["github", "gitlab", "bitbucket", "docker", "kubernetes", "aws", "azure", "gcp"],
    SkillCategory.TESTING_QA: ["test", "testing", "qa", "code-reviewer", "systematic-debugging"],
    SkillCategory.CONTENT_CREATION: ["content", "blog", "seo", "copywriting", "video-script"],
    SkillCategory.SECURITY_COMPLIANCE: ["security", "compliance", "vulnerability", "gdpr", "audit"],
    SkillCategory.ANALYTICS_DATA: ["analytics", "mixpanel", "amplitude", "tableau", "powerbi"],
    SkillCategory.DESIGN_MEDIA: ["figma", "canva", "adobe", "image", "video-editing", "design"],
    SkillCategory.WORKFLOW_AUTOMATION: ["n8n", "zapier", "make", "ifttt", "workflow"],
    SkillCategory.LEGAL_COMPLIANCE: ["legal", "contract", "assignation", "requete", "cph", "lawvable"],
    SkillCategory.RESEARCH_LEARNING: ["askgpt", "research", "academic", "notebooklm"],
    SkillCategory.BUSINESS_OPERATIONS: ["invoice-organizer", "expense", "bookkeeping", "hr", "recruitment"],
    SkillCategory.CUSTOMER_SUPPORT: ["zendesk", "intercom", "freshdesk", "help-scout"],
    SkillCategory.MARKETING_ADVERTISING: ["ads", "competitive-ads", "advertising", "marketing"],
    SkillCategory.ARCHITECTURE_PLANNING: ["systems-architect", "refactor-expert", "docs-writer", "api-documenter"],
    SkillCategory.DEPLOYMENT_DEVOPS: ["deploy", "ci-cd", "monitoring", "logging", "devops"],
    SkillCategory.GSD_SUITE: ["gsd-"],
}

# Skills that should be proactively suggested
PROACTIVE_SKILLS: Set[str] = {
    "code-reviewer",
    "security-auditor",
    "test-engineer",
    "performance-tuner",
    "docs-writer",
    "refactor-expert",
    "systems-architect",
    "systematic-debugging",
    "askgpt",
}

# Skills that require approval before use
APPROVAL_REQUIRED_SKILLS: Set[str] = {
    "stripe-automation",  # Financial operations
    "paypal-automation",
    "invoice-organizer",
    "deployment-automation",
    "ci-cd-automation",
    "security-audit",  # Security-related
    "gdpr-compliance-automation",
}


def detect_category(skill_name: str, description: str) -> SkillCategory:
    """Detect the category for a skill based on name and description."""
    text = f"{skill_name} {description}".lower()

    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if pattern in text:
                return category

    return SkillCategory.UNCATEGORIZED


class SkillRegistry:
    """
    Registry for loading and querying skills from external reference library.

    Reads from AI_Tools_Reference folder (read-only, no duplication).
    """

    # Default path to external reference library
    DEFAULT_REFERENCE_PATH = Path("/Users/krissanders/Desktop/AI_Tools_Reference")

    def __init__(self, reference_path: Optional[Path] = None):
        """
        Initialize the skill registry.

        Args:
            reference_path: Path to AI_Tools_Reference folder. Uses default if not provided.
        """
        self.reference_path = reference_path or self.DEFAULT_REFERENCE_PATH
        self._skills: Dict[str, SkillDefinition] = {}
        self._loaded = False
        self._load_error: Optional[str] = None

    def load(self) -> bool:
        """
        Load skills from the external reference library.

        Returns:
            True if loaded successfully, False otherwise.
        """
        skills_index_path = self.reference_path / "Skills" / "SKILLS_INDEX.json"

        if not skills_index_path.exists():
            self._load_error = f"Skills index not found: {skills_index_path}"
            self._loaded = False
            return False

        try:
            with open(skills_index_path, 'r', encoding='utf-8') as f:
                raw_skills = json.load(f)

            for raw_skill in raw_skills:
                name = raw_skill.get("name", "")
                description = raw_skill.get("description", "")
                path = raw_skill.get("path", name)
                keywords = raw_skill.get("keywords", [])

                # Clean up keywords (some have trailing punctuation)
                keywords = [k.strip().rstrip(",.;:") for k in keywords if k.strip()]

                # Detect category
                category = detect_category(name, description)

                # Check if proactive or requires approval
                is_proactive = name in PROACTIVE_SKILLS
                requires_approval = name in APPROVAL_REQUIRED_SKILLS

                skill = SkillDefinition(
                    name=name,
                    description=description,
                    path=path,
                    keywords=keywords,
                    category=category,
                    is_proactive=is_proactive,
                    requires_approval=requires_approval,
                )

                self._skills[name] = skill

            self._loaded = True
            self._load_error = None
            return True

        except json.JSONDecodeError as e:
            self._load_error = f"JSON parse error: {e}"
            self._loaded = False
            return False
        except Exception as e:
            self._load_error = f"Load error: {e}"
            self._loaded = False
            return False

    @property
    def is_loaded(self) -> bool:
        """Check if skills are loaded."""
        return self._loaded

    @property
    def load_error(self) -> Optional[str]:
        """Get the load error message if any."""
        return self._load_error

    @property
    def skill_count(self) -> int:
        """Get the number of loaded skills."""
        return len(self._skills)

    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        """Get a skill by exact name."""
        return self._skills.get(name)

    def search(self, query: str, limit: int = 10) -> List[SkillDefinition]:
        """
        Search for skills matching a query.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of matching skills, sorted by relevance.
        """
        if not self._loaded:
            return []

        # Score all skills
        scored = []
        for skill in self._skills.values():
            score = skill.keyword_score(query)
            if score > 0:
                scored.append((score, skill))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [skill for _, skill in scored[:limit]]

    def get_by_category(self, category: SkillCategory) -> List[SkillDefinition]:
        """Get all skills in a category."""
        return [s for s in self._skills.values() if s.category == category]

    def get_proactive_skills(self) -> List[SkillDefinition]:
        """Get all skills marked as proactive."""
        return [s for s in self._skills.values() if s.is_proactive]

    def get_approval_required_skills(self) -> List[SkillDefinition]:
        """Get all skills that require approval."""
        return [s for s in self._skills.values() if s.requires_approval]

    def list_categories(self) -> Dict[SkillCategory, int]:
        """List all categories with skill counts."""
        counts: Dict[SkillCategory, int] = {}
        for skill in self._skills.values():
            counts[skill.category] = counts.get(skill.category, 0) + 1
        return counts

    def all_skills(self) -> List[SkillDefinition]:
        """Get all loaded skills."""
        return list(self._skills.values())


# Singleton instance for global access
_skill_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get the global skill registry instance."""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry


def load_skills(reference_path: Optional[Path] = None) -> SkillRegistry:
    """
    Load skills from the external reference library.

    Args:
        reference_path: Optional custom path to reference library.

    Returns:
        The loaded SkillRegistry instance.
    """
    registry = get_skill_registry()
    if reference_path:
        registry.reference_path = reference_path
    registry.load()
    return registry
