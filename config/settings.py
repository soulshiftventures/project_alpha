"""
Central Settings Management for Project Alpha.

Provides secure environment variable loading and configuration management.

SECURITY:
- All secrets are loaded from environment variables
- Never hardcode credentials
- Use RedactedString for sensitive values
"""

import os
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from config.redaction import RedactedString, redact_dict


def get_env(key: str, default: str = "") -> str:
    """
    Get an environment variable value.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        The environment variable value or default
    """
    return os.environ.get(key, default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get an environment variable as a boolean.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Boolean interpretation of the value
    """
    value = os.environ.get(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    return default


def get_env_int(key: str, default: int = 0) -> int:
    """
    Get an environment variable as an integer.

    Args:
        key: Environment variable name
        default: Default value if not set or invalid

    Returns:
        Integer value
    """
    value = os.environ.get(key, "")
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def require_env(key: str, hint: str = "") -> RedactedString:
    """
    Get a required environment variable as a RedactedString.

    Does not raise if missing - returns empty RedactedString.
    Caller should check .is_set() before using.

    Args:
        key: Environment variable name
        hint: Optional hint about the credential

    Returns:
        RedactedString wrapping the value
    """
    value = os.environ.get(key, "")
    return RedactedString(value, hint or key)


def is_env_set(key: str) -> bool:
    """
    Check if an environment variable is set and non-empty.

    Args:
        key: Environment variable name

    Returns:
        True if set and non-empty
    """
    value = os.environ.get(key, "")
    return bool(value.strip())


@dataclass
class Settings:
    """
    Central settings container for Project Alpha.

    All sensitive values are wrapped in RedactedString.
    """

    # Application mode
    environment: str = field(default_factory=lambda: get_env("PROJECT_ALPHA_ENV", "development"))
    debug_mode: bool = field(default_factory=lambda: get_env_bool("PROJECT_ALPHA_DEBUG", False))
    dry_run_default: bool = field(default_factory=lambda: get_env_bool("PROJECT_ALPHA_DRY_RUN", True))

    # AI API Keys (wrapped for safety)
    anthropic_api_key: RedactedString = field(
        default_factory=lambda: require_env("ANTHROPIC_API_KEY", "Anthropic Claude API")
    )
    openai_api_key: RedactedString = field(
        default_factory=lambda: require_env("OPENAI_API_KEY", "OpenAI API")
    )

    # Research/Search API Keys
    tavily_api_key: RedactedString = field(
        default_factory=lambda: require_env("TAVILY_API_KEY", "Tavily Search API")
    )
    firecrawl_api_key: RedactedString = field(
        default_factory=lambda: require_env("FIRECRAWL_API_KEY", "Firecrawl Web Extraction")
    )

    # Lead Generation API Keys
    apollo_api_key: RedactedString = field(
        default_factory=lambda: require_env("APOLLO_API_KEY", "Apollo.io Lead Generation")
    )
    outscraper_api_key: RedactedString = field(
        default_factory=lambda: require_env("OUTSCRAPER_API_KEY", "Outscraper Data Extraction")
    )

    # CRM API Keys
    hubspot_api_key: RedactedString = field(
        default_factory=lambda: require_env("HUBSPOT_API_KEY", "HubSpot CRM")
    )
    hubspot_portal_id: str = field(
        default_factory=lambda: get_env("HUBSPOT_PORTAL_ID", "")
    )

    # Messaging API Keys
    telegram_bot_token: RedactedString = field(
        default_factory=lambda: require_env("TELEGRAM_BOT_TOKEN", "Telegram Bot")
    )
    telegram_chat_id: str = field(
        default_factory=lambda: get_env("TELEGRAM_CHAT_ID", "")
    )
    sendgrid_api_key: RedactedString = field(
        default_factory=lambda: require_env("SENDGRID_API_KEY", "SendGrid Email")
    )
    sendgrid_from_email: str = field(
        default_factory=lambda: get_env("SENDGRID_FROM_EMAIL", "")
    )

    # Optional enhancement tools
    aiq_api_key: RedactedString = field(
        default_factory=lambda: require_env("AIQ_API_KEY", "AI-Q Reasoning")
    )
    nemoclaw_api_key: RedactedString = field(
        default_factory=lambda: require_env("NEMOCLAW_API_KEY", "NemoClaw Sandbox")
    )
    zep_api_key: RedactedString = field(
        default_factory=lambda: require_env("ZEP_API_KEY", "Zep Memory")
    )

    def get_configured_services(self) -> List[str]:
        """Return list of services that have credentials configured."""
        services = []

        if self.anthropic_api_key.is_set():
            services.append("anthropic")
        if self.openai_api_key.is_set():
            services.append("openai")
        if self.tavily_api_key.is_set():
            services.append("tavily")
        if self.firecrawl_api_key.is_set():
            services.append("firecrawl")
        if self.apollo_api_key.is_set():
            services.append("apollo")
        if self.outscraper_api_key.is_set():
            services.append("outscraper")
        if self.hubspot_api_key.is_set():
            services.append("hubspot")
        if self.telegram_bot_token.is_set():
            services.append("telegram")
        if self.sendgrid_api_key.is_set():
            services.append("sendgrid")
        if self.aiq_api_key.is_set():
            services.append("aiq")
        if self.nemoclaw_api_key.is_set():
            services.append("nemoclaw")
        if self.zep_api_key.is_set():
            services.append("zep")

        return services

    def get_missing_for_integration(self, integration: str) -> List[str]:
        """Return list of missing env vars for an integration."""
        requirements = {
            "tavily": ["TAVILY_API_KEY"],
            "firecrawl": ["FIRECRAWL_API_KEY"],
            "apollo": ["APOLLO_API_KEY"],
            "outscraper": ["OUTSCRAPER_API_KEY"],
            "hubspot": ["HUBSPOT_API_KEY"],
            "telegram": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
            "sendgrid": ["SENDGRID_API_KEY", "SENDGRID_FROM_EMAIL"],
        }

        required = requirements.get(integration, [])
        return [var for var in required if not is_env_set(var)]

    def to_safe_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation safe for logging."""
        return {
            "environment": self.environment,
            "debug_mode": self.debug_mode,
            "dry_run_default": self.dry_run_default,
            "configured_services": self.get_configured_services(),
            "anthropic_api_key": str(self.anthropic_api_key),
            "openai_api_key": str(self.openai_api_key),
            "tavily_api_key": str(self.tavily_api_key),
            "firecrawl_api_key": str(self.firecrawl_api_key),
            "apollo_api_key": str(self.apollo_api_key),
            "outscraper_api_key": str(self.outscraper_api_key),
            "hubspot_api_key": str(self.hubspot_api_key),
            "telegram_bot_token": str(self.telegram_bot_token),
            "sendgrid_api_key": str(self.sendgrid_api_key),
            "aiq_api_key": str(self.aiq_api_key),
            "nemoclaw_api_key": str(self.nemoclaw_api_key),
            "zep_api_key": str(self.zep_api_key),
        }


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.

    Returns:
        Settings singleton
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Force reload of settings from environment.

    Returns:
        Fresh Settings instance
    """
    global _settings
    _settings = Settings()
    return _settings
