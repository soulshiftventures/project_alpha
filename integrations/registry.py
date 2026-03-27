"""
Connector Registry for Project Alpha.

Central registry for managing all service connectors.

ARCHITECTURE:
- Single source of truth for all connectors
- Lazy loading of connector instances
- Health monitoring and status aggregation
"""

from typing import Any, Dict, List, Optional, Type
from datetime import datetime, timezone
import logging

from integrations.base import (
    BaseConnector,
    ConnectorStatus,
    ConnectorCategory,
    ConnectorResult,
)


logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Central registry for all service connectors.

    Provides:
    - Connector registration and lookup
    - Health monitoring
    - Status aggregation
    - Category-based filtering
    """

    def __init__(self):
        self._connector_classes: Dict[str, Type[BaseConnector]] = {}
        self._instances: Dict[str, BaseConnector] = {}
        self._last_health_check: Optional[datetime] = None

    def register_class(
        self,
        name: str,
        connector_class: Type[BaseConnector],
    ) -> None:
        """
        Register a connector class.

        Args:
            name: Connector name (lowercase)
            connector_class: The connector class (not instance)
        """
        self._connector_classes[name.lower()] = connector_class

    def register_instance(
        self,
        name: str,
        connector: BaseConnector,
    ) -> None:
        """
        Register a connector instance.

        Args:
            name: Connector name
            connector: Connector instance
        """
        self._instances[name.lower()] = connector

    def get(self, name: str) -> Optional[BaseConnector]:
        """
        Get a connector by name.

        Lazily instantiates if only class is registered.

        Args:
            name: Connector name

        Returns:
            Connector instance or None
        """
        name_lower = name.lower()

        # Return existing instance
        if name_lower in self._instances:
            return self._instances[name_lower]

        # Create from class if available
        if name_lower in self._connector_classes:
            try:
                connector = self._connector_classes[name_lower]()
                self._instances[name_lower] = connector
                return connector
            except Exception as e:
                logger.error(f"Failed to instantiate connector {name}: {e}")
                return None

        return None

    def get_all(self) -> List[BaseConnector]:
        """Get all registered connectors."""
        # Ensure all registered classes are instantiated
        for name in self._connector_classes:
            if name not in self._instances:
                self.get(name)

        return list(self._instances.values())

    def get_by_category(
        self, category: ConnectorCategory
    ) -> List[BaseConnector]:
        """Get connectors by category."""
        return [
            c for c in self.get_all()
            if c.category == category
        ]

    def get_by_status(
        self, status: ConnectorStatus
    ) -> List[BaseConnector]:
        """Get connectors by status."""
        return [
            c for c in self.get_all()
            if c.get_status() == status
        ]

    def get_ready(self) -> List[BaseConnector]:
        """Get all ready connectors."""
        return self.get_by_status(ConnectorStatus.READY)

    def get_unconfigured(self) -> List[BaseConnector]:
        """Get all unconfigured connectors."""
        return self.get_by_status(ConnectorStatus.UNCONFIGURED)

    def list_names(self) -> List[str]:
        """Get list of all registered connector names."""
        names = set(self._connector_classes.keys())
        names.update(self._instances.keys())
        return sorted(names)

    def is_registered(self, name: str) -> bool:
        """Check if a connector is registered."""
        name_lower = name.lower()
        return (
            name_lower in self._connector_classes or
            name_lower in self._instances
        )

    def health_check_all(self) -> Dict[str, ConnectorResult]:
        """
        Run health check on all connectors.

        Returns:
            Dict mapping connector name to health check result
        """
        results = {}

        for connector in self.get_all():
            try:
                results[connector.name] = connector.health_check()
            except Exception as e:
                results[connector.name] = ConnectorResult.error_result(
                    str(e),
                    error_type="health_check_failed",
                )

        self._last_health_check = datetime.now(timezone.utc)
        return results

    def get_summary(self) -> Dict[str, Any]:
        """Get registry summary."""
        connectors = self.get_all()

        by_status = {status.value: [] for status in ConnectorStatus}
        by_category = {cat.value: [] for cat in ConnectorCategory}

        for connector in connectors:
            status = connector.get_status()
            by_status[status.value].append(connector.name)
            by_category[connector.category.value].append(connector.name)

        return {
            "total": len(connectors),
            "ready": len(self.get_ready()),
            "unconfigured": len(self.get_unconfigured()),
            "by_status": by_status,
            "by_category": by_category,
            "last_health_check": (
                self._last_health_check.isoformat()
                if self._last_health_check else None
            ),
        }

    def get_status_report(self) -> List[Dict[str, Any]]:
        """Get status report for all connectors."""
        return [c.to_dict() for c in self.get_all()]

    def enable_connector(self, name: str) -> bool:
        """Enable a connector."""
        connector = self.get(name)
        if connector:
            connector.enable()
            return True
        return False

    def disable_connector(self, name: str) -> bool:
        """Disable a connector."""
        connector = self.get(name)
        if connector:
            connector.disable()
            return True
        return False


# Singleton instance
_connector_registry: Optional[ConnectorRegistry] = None


def get_connector_registry() -> ConnectorRegistry:
    """Get the global connector registry."""
    global _connector_registry
    if _connector_registry is None:
        _connector_registry = ConnectorRegistry()
        _register_default_connectors(_connector_registry)
    return _connector_registry


def _register_default_connectors(registry: ConnectorRegistry) -> None:
    """Register default connectors."""
    # Import and register connectors
    # These will be added as we implement each connector
    try:
        from integrations.connectors.tavily import TavilyConnector
        registry.register_class("tavily", TavilyConnector)
    except ImportError:
        pass

    try:
        from integrations.connectors.firecrawl import FirecrawlConnector
        registry.register_class("firecrawl", FirecrawlConnector)
    except ImportError:
        pass

    try:
        from integrations.connectors.apollo import ApolloConnector
        registry.register_class("apollo", ApolloConnector)
    except ImportError:
        pass

    try:
        from integrations.connectors.outscraper import OutscraperConnector
        registry.register_class("outscraper", OutscraperConnector)
    except ImportError:
        pass

    try:
        from integrations.connectors.hubspot import HubSpotConnector
        registry.register_class("hubspot", HubSpotConnector)
    except ImportError:
        pass

    try:
        from integrations.connectors.telegram import TelegramConnector
        registry.register_class("telegram", TelegramConnector)
    except ImportError:
        pass

    try:
        from integrations.connectors.sendgrid import SendGridConnector
        registry.register_class("sendgrid", SendGridConnector)
    except ImportError:
        pass


def register_connector(
    name: str,
    connector_class: Type[BaseConnector],
) -> None:
    """Convenience function to register a connector."""
    get_connector_registry().register_class(name, connector_class)


def get_connector(name: str) -> Optional[BaseConnector]:
    """Convenience function to get a connector."""
    return get_connector_registry().get(name)
