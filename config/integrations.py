"""
Integration Configuration Management.

Defines integration configurations and validation.
"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from config.settings import get_settings, is_env_set


class IntegrationCategory(Enum):
    """Categories of integrations."""
    RESEARCH = "research"
    LEAD_GENERATION = "lead_generation"
    CRM = "crm"
    MESSAGING = "messaging"
    AUTOMATION = "automation"
    PAYMENTS = "payments"
    INFRASTRUCTURE = "infrastructure"
    AI_ENHANCEMENT = "ai_enhancement"


class IntegrationStatus(Enum):
    """Status of an integration."""
    AVAILABLE = "available"
    CONFIGURED = "configured"
    MISSING_CREDENTIALS = "missing_credentials"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class IntegrationConfig:
    """Configuration for a single integration."""

    name: str
    category: IntegrationCategory
    description: str
    required_env_vars: List[str]
    optional_env_vars: List[str] = field(default_factory=list)
    base_url: str = ""
    supports_dry_run: bool = True
    requires_approval: bool = False
    enabled: bool = True

    def get_status(self) -> IntegrationStatus:
        """Get current status based on configuration."""
        if not self.enabled:
            return IntegrationStatus.DISABLED

        missing = [var for var in self.required_env_vars if not is_env_set(var)]
        if missing:
            return IntegrationStatus.MISSING_CREDENTIALS

        return IntegrationStatus.CONFIGURED

    def get_missing_vars(self) -> List[str]:
        """Get list of missing required environment variables."""
        return [var for var in self.required_env_vars if not is_env_set(var)]

    def is_ready(self) -> bool:
        """Check if integration is ready to use."""
        return self.get_status() == IntegrationStatus.CONFIGURED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "required_env_vars": self.required_env_vars,
            "optional_env_vars": self.optional_env_vars,
            "base_url": self.base_url,
            "supports_dry_run": self.supports_dry_run,
            "requires_approval": self.requires_approval,
            "enabled": self.enabled,
            "status": self.get_status().value,
            "is_ready": self.is_ready(),
            "missing_vars": self.get_missing_vars(),
        }


# Registry of all known integrations
INTEGRATION_CONFIGS: Dict[str, IntegrationConfig] = {
    # Research/Search
    "tavily": IntegrationConfig(
        name="Tavily",
        category=IntegrationCategory.RESEARCH,
        description="AI-powered web search and research API",
        required_env_vars=["TAVILY_API_KEY"],
        base_url="https://api.tavily.com",
        supports_dry_run=True,
        requires_approval=False,
    ),
    "firecrawl": IntegrationConfig(
        name="Firecrawl",
        category=IntegrationCategory.RESEARCH,
        description="Web scraping and content extraction API",
        required_env_vars=["FIRECRAWL_API_KEY"],
        base_url="https://api.firecrawl.dev",
        supports_dry_run=True,
        requires_approval=False,
    ),

    # Lead Generation
    "apollo": IntegrationConfig(
        name="Apollo.io",
        category=IntegrationCategory.LEAD_GENERATION,
        description="B2B lead database and enrichment platform",
        required_env_vars=["APOLLO_API_KEY"],
        base_url="https://api.apollo.io/v1",
        supports_dry_run=True,
        requires_approval=True,  # Lead extraction can be costly
    ),
    "outscraper": IntegrationConfig(
        name="Outscraper",
        category=IntegrationCategory.LEAD_GENERATION,
        description="Google Maps and business data extraction",
        required_env_vars=["OUTSCRAPER_API_KEY"],
        base_url="https://api.outscraper.com",
        supports_dry_run=True,
        requires_approval=True,
    ),

    # CRM
    "hubspot": IntegrationConfig(
        name="HubSpot",
        category=IntegrationCategory.CRM,
        description="CRM platform for contacts, deals, and pipelines",
        required_env_vars=["HUBSPOT_API_KEY"],
        optional_env_vars=["HUBSPOT_PORTAL_ID"],
        base_url="https://api.hubapi.com",
        supports_dry_run=True,
        requires_approval=True,  # CRM writes need approval
    ),

    # Messaging
    "telegram": IntegrationConfig(
        name="Telegram",
        category=IntegrationCategory.MESSAGING,
        description="Telegram bot for notifications and alerts",
        required_env_vars=["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
        base_url="https://api.telegram.org",
        supports_dry_run=True,
        requires_approval=True,  # Outbound messages need approval
    ),
    "sendgrid": IntegrationConfig(
        name="SendGrid",
        category=IntegrationCategory.MESSAGING,
        description="Transactional email service",
        required_env_vars=["SENDGRID_API_KEY", "SENDGRID_FROM_EMAIL"],
        base_url="https://api.sendgrid.com/v3",
        supports_dry_run=True,
        requires_approval=True,  # Outbound emails need approval
    ),

    # AI Enhancement
    "anthropic": IntegrationConfig(
        name="Anthropic Claude",
        category=IntegrationCategory.AI_ENHANCEMENT,
        description="Claude AI for reasoning and generation",
        required_env_vars=["ANTHROPIC_API_KEY"],
        base_url="https://api.anthropic.com",
        supports_dry_run=False,
        requires_approval=False,
    ),
    "openai": IntegrationConfig(
        name="OpenAI",
        category=IntegrationCategory.AI_ENHANCEMENT,
        description="OpenAI GPT models",
        required_env_vars=["OPENAI_API_KEY"],
        base_url="https://api.openai.com/v1",
        supports_dry_run=False,
        requires_approval=False,
    ),
}


def get_integration_config(name: str) -> Optional[IntegrationConfig]:
    """
    Get configuration for a specific integration.

    Args:
        name: Integration name (lowercase)

    Returns:
        IntegrationConfig if found, None otherwise
    """
    return INTEGRATION_CONFIGS.get(name.lower())


def list_configured_integrations() -> List[str]:
    """
    Get list of integrations that are properly configured.

    Returns:
        List of integration names that are ready to use
    """
    return [
        name for name, config in INTEGRATION_CONFIGS.items()
        if config.is_ready()
    ]


def list_all_integrations() -> List[IntegrationConfig]:
    """
    Get list of all known integrations.

    Returns:
        List of all IntegrationConfig objects
    """
    return list(INTEGRATION_CONFIGS.values())


def get_integrations_by_category(category: IntegrationCategory) -> List[IntegrationConfig]:
    """
    Get integrations filtered by category.

    Args:
        category: The category to filter by

    Returns:
        List of matching IntegrationConfig objects
    """
    return [
        config for config in INTEGRATION_CONFIGS.values()
        if config.category == category
    ]


def validate_integration_config(name: str) -> Dict[str, Any]:
    """
    Validate configuration for an integration.

    Args:
        name: Integration name

    Returns:
        Validation result dictionary
    """
    config = get_integration_config(name)
    if not config:
        return {
            "valid": False,
            "error": f"Unknown integration: {name}",
            "name": name,
        }

    missing = config.get_missing_vars()
    status = config.get_status()

    return {
        "valid": status == IntegrationStatus.CONFIGURED,
        "name": config.name,
        "status": status.value,
        "missing_vars": missing,
        "requires_approval": config.requires_approval,
        "supports_dry_run": config.supports_dry_run,
    }


def get_integration_summary() -> Dict[str, Any]:
    """
    Get summary of all integration statuses.

    Returns:
        Dictionary with summary information
    """
    by_status = {status.value: [] for status in IntegrationStatus}
    by_category = {cat.value: [] for cat in IntegrationCategory}

    for name, config in INTEGRATION_CONFIGS.items():
        status = config.get_status()
        by_status[status.value].append(name)
        by_category[config.category.value].append(name)

    return {
        "total": len(INTEGRATION_CONFIGS),
        "configured": len(list_configured_integrations()),
        "by_status": by_status,
        "by_category": by_category,
    }
