"""
Configuration Layer for Project Alpha.

Provides secure environment variable loading, secret redaction,
and integration configuration management.

SECURITY WARNING:
- Never commit real secrets to the repository
- Use environment variables for all credentials
- Always redact secrets in logs and debug output
"""

from config.settings import (
    Settings,
    get_settings,
    get_env,
    get_env_bool,
    get_env_int,
    require_env,
    is_env_set,
)
from config.redaction import (
    redact_value,
    redact_dict,
    redact_url,
    RedactedString,
    REDACTION_MARKER,
)
from config.integrations import (
    IntegrationConfig,
    get_integration_config,
    list_configured_integrations,
    validate_integration_config,
)

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    "get_env",
    "get_env_bool",
    "get_env_int",
    "require_env",
    "is_env_set",
    # Redaction
    "redact_value",
    "redact_dict",
    "redact_url",
    "RedactedString",
    "REDACTION_MARKER",
    # Integrations
    "IntegrationConfig",
    "get_integration_config",
    "list_configured_integrations",
    "validate_integration_config",
]
