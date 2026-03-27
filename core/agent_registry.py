"""
Agent Registry for Project Alpha
Central registry for all agents in the hierarchy system
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from core.agent_contracts import AgentLayer


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class AgentStatus(Enum):
    """Status of an agent in the registry."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


@dataclass
class AgentDefinition:
    """
    Definition of an agent in the system.

    Contains all metadata needed to route requests,
    check capabilities, and invoke the agent.
    """
    # Identity
    agent_id: str
    name: str
    layer: AgentLayer

    # Role and capabilities
    role: str  # Brief description of agent's role
    capabilities: List[str] = field(default_factory=list)
    allowed_stages: List[str] = field(default_factory=list)

    # Handler reference (callable or module path)
    handler_path: Optional[str] = None  # e.g., "core.stage_workflows.StageWorkflows"
    handler_method: Optional[str] = None  # e.g., "execute_discovered_task"

    # Relationships
    reports_to: Optional[str] = None  # agent_id of superior
    direct_reports: List[str] = field(default_factory=list)

    # Status
    status: AgentStatus = AgentStatus.ACTIVE

    # Metadata
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())
    updated_at: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["layer"] = self.layer.value
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentDefinition":
        """Create from dictionary."""
        if "layer" in data and isinstance(data["layer"], str):
            data["layer"] = AgentLayer(data["layer"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = AgentStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class AgentRegistry:
    """
    Central registry for all agents in the hierarchy.

    Provides:
    - Agent registration and lookup
    - Capability-based routing
    - Layer-based filtering
    - Handler resolution
    """

    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, AgentDefinition] = {}
        self._by_layer: Dict[AgentLayer, List[str]] = {layer: [] for layer in AgentLayer}
        self._by_capability: Dict[str, List[str]] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(self, agent: AgentDefinition) -> None:
        """
        Register an agent in the registry.

        Args:
            agent: AgentDefinition to register
        """
        agent_id = agent.agent_id

        # Store agent
        self._agents[agent_id] = agent

        # Index by layer
        if agent_id not in self._by_layer[agent.layer]:
            self._by_layer[agent.layer].append(agent_id)

        # Index by capabilities
        for capability in agent.capabilities:
            if capability not in self._by_capability:
                self._by_capability[capability] = []
            if agent_id not in self._by_capability[capability]:
                self._by_capability[capability].append(agent_id)

    def unregister(self, agent_id: str) -> bool:
        """
        Remove an agent from the registry.

        Args:
            agent_id: ID of agent to remove

        Returns:
            True if removed, False if not found
        """
        if agent_id not in self._agents:
            return False

        agent = self._agents[agent_id]

        # Remove from layer index
        if agent_id in self._by_layer[agent.layer]:
            self._by_layer[agent.layer].remove(agent_id)

        # Remove from capability index
        for capability in agent.capabilities:
            if capability in self._by_capability:
                if agent_id in self._by_capability[capability]:
                    self._by_capability[capability].remove(agent_id)

        # Remove from handlers
        if agent_id in self._handlers:
            del self._handlers[agent_id]

        # Remove agent
        del self._agents[agent_id]
        return True

    def get(self, agent_id: str) -> Optional[AgentDefinition]:
        """
        Get an agent by ID.

        Args:
            agent_id: ID of agent to retrieve

        Returns:
            AgentDefinition or None if not found
        """
        return self._agents.get(agent_id)

    def get_by_layer(self, layer: AgentLayer) -> List[AgentDefinition]:
        """
        Get all agents in a specific layer.

        Args:
            layer: AgentLayer to filter by

        Returns:
            List of agents in that layer
        """
        return [self._agents[aid] for aid in self._by_layer[layer] if aid in self._agents]

    def get_by_capability(self, capability: str) -> List[AgentDefinition]:
        """
        Get all agents with a specific capability.

        Args:
            capability: Capability to filter by

        Returns:
            List of agents with that capability
        """
        if capability not in self._by_capability:
            return []
        return [self._agents[aid] for aid in self._by_capability[capability] if aid in self._agents]

    def get_by_stage(self, stage: str) -> List[AgentDefinition]:
        """
        Get all agents allowed to operate in a specific stage.

        Args:
            stage: Business lifecycle stage

        Returns:
            List of agents allowed in that stage
        """
        return [
            agent for agent in self._agents.values()
            if stage in agent.allowed_stages or not agent.allowed_stages
        ]

    def get_active(self) -> List[AgentDefinition]:
        """
        Get all active agents.

        Returns:
            List of active agents
        """
        return [agent for agent in self._agents.values() if agent.status == AgentStatus.ACTIVE]

    def find_agents(
        self,
        layer: Optional[AgentLayer] = None,
        capability: Optional[str] = None,
        stage: Optional[str] = None,
        status: Optional[AgentStatus] = None
    ) -> List[AgentDefinition]:
        """
        Find agents matching multiple criteria.

        Args:
            layer: Filter by layer
            capability: Filter by capability
            stage: Filter by allowed stage
            status: Filter by status

        Returns:
            List of matching agents
        """
        results = list(self._agents.values())

        if layer is not None:
            results = [a for a in results if a.layer == layer]

        if capability is not None:
            results = [a for a in results if capability in a.capabilities]

        if stage is not None:
            results = [a for a in results if stage in a.allowed_stages or not a.allowed_stages]

        if status is not None:
            results = [a for a in results if a.status == status]

        return results

    def register_handler(self, agent_id: str, handler: Callable) -> bool:
        """
        Register a callable handler for an agent.

        Args:
            agent_id: ID of agent
            handler: Callable to handle requests

        Returns:
            True if registered, False if agent not found
        """
        if agent_id not in self._agents:
            return False
        self._handlers[agent_id] = handler
        return True

    def get_handler(self, agent_id: str) -> Optional[Callable]:
        """
        Get the handler for an agent.

        Args:
            agent_id: ID of agent

        Returns:
            Handler callable or None
        """
        return self._handlers.get(agent_id)

    def resolve_handler(self, agent_id: str) -> Optional[Callable]:
        """
        Resolve handler for an agent, attempting dynamic import if needed.

        Args:
            agent_id: ID of agent

        Returns:
            Handler callable or None
        """
        # Check cached handlers first
        if agent_id in self._handlers:
            return self._handlers[agent_id]

        # Try to resolve from handler_path
        agent = self._agents.get(agent_id)
        if not agent or not agent.handler_path:
            return None

        try:
            # Dynamic import
            parts = agent.handler_path.rsplit(".", 1)
            if len(parts) == 2:
                module_path, class_name = parts
                import importlib
                module = importlib.import_module(module_path)
                handler_class = getattr(module, class_name)

                # If handler_method is specified, get that method
                if agent.handler_method:
                    instance = handler_class()
                    handler = getattr(instance, agent.handler_method)
                    self._handlers[agent_id] = handler
                    return handler
                else:
                    # Return the class itself
                    self._handlers[agent_id] = handler_class
                    return handler_class
        except Exception:
            pass

        return None

    def get_reporting_chain(self, agent_id: str) -> List[str]:
        """
        Get the chain of command above an agent.

        Args:
            agent_id: ID of agent

        Returns:
            List of agent IDs from immediate superior to top
        """
        chain = []
        current = self._agents.get(agent_id)

        while current and current.reports_to:
            chain.append(current.reports_to)
            current = self._agents.get(current.reports_to)

        return chain

    def get_direct_reports(self, agent_id: str) -> List[AgentDefinition]:
        """
        Get all agents that report to this agent.

        Args:
            agent_id: ID of agent

        Returns:
            List of direct report agents
        """
        return [
            agent for agent in self._agents.values()
            if agent.reports_to == agent_id
        ]

    def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        Update an agent's status.

        Args:
            agent_id: ID of agent
            status: New status

        Returns:
            True if updated, False if agent not found
        """
        if agent_id not in self._agents:
            return False
        self._agents[agent_id].status = status
        self._agents[agent_id].updated_at = _utc_now().isoformat()
        return True

    def list_all(self) -> List[AgentDefinition]:
        """
        Get all registered agents.

        Returns:
            List of all agents
        """
        return list(self._agents.values())

    def count(self) -> int:
        """
        Get total number of registered agents.

        Returns:
            Count of agents
        """
        return len(self._agents)

    def count_by_layer(self) -> Dict[str, int]:
        """
        Get count of agents per layer.

        Returns:
            Dictionary of layer name to count
        """
        return {
            layer.value: len(agent_ids)
            for layer, agent_ids in self._by_layer.items()
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Export registry state as dictionary.

        Returns:
            Dictionary with all agents
        """
        return {
            "agents": {aid: agent.to_dict() for aid, agent in self._agents.items()},
            "count": self.count(),
            "by_layer": self.count_by_layer()
        }
