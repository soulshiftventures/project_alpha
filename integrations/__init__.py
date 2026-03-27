"""
Integrations Package for Project Alpha.

Provides connectors for external services and APIs.

ARCHITECTURE:
- BaseConnector: Abstract base class for all connectors
- ConnectorRegistry: Central registry for connector management
- Each connector implements: health_check(), dry_run(), execute()

SECURITY:
- Credentials are NEVER stored in connectors
- All secrets retrieved on-demand from SecretsManager
- Dry-run mode prevents unintended external calls
"""

from integrations.base import (
    BaseConnector,
    ConnectorStatus,
    ConnectorCategory,
    ConnectorResult,
    ConnectorError,
    RateLimitError,
    AuthenticationError,
    ConnectionError,
)

from integrations.registry import (
    ConnectorRegistry,
    get_connector_registry,
    register_connector,
    get_connector,
)

__all__ = [
    # Base classes
    "BaseConnector",
    "ConnectorStatus",
    "ConnectorCategory",
    "ConnectorResult",
    # Errors
    "ConnectorError",
    "RateLimitError",
    "AuthenticationError",
    "ConnectionError",
    # Registry
    "ConnectorRegistry",
    "get_connector_registry",
    "register_connector",
    "get_connector",
]
