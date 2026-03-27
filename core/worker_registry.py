"""
Worker Registry - Registry for worker types, capabilities, and instances.

Manages worker definitions and active worker instances for execution backends.
Workers are the units that execute individual steps within backends.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable, Any
from enum import Enum
from datetime import datetime
import uuid
import threading


class WorkerType(Enum):
    """Types of workers available for execution."""
    GENERAL = "general"  # General-purpose worker
    RESEARCH = "research"  # Specialized for research tasks
    PLANNING = "planning"  # Specialized for planning tasks
    PRODUCT = "product"  # Specialized for product development
    OPERATIONS = "operations"  # Specialized for operations
    GROWTH = "growth"  # Specialized for growth/marketing
    AUTOMATION = "automation"  # Specialized for automation tasks
    VALIDATION = "validation"  # Specialized for validation
    CONTENT = "content"  # Specialized for content creation


class WorkerStatus(Enum):
    """Status of a worker instance."""
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerCapabilities:
    """Capabilities of a worker type."""
    worker_type: WorkerType
    domains: Set[str]  # Domains this worker can handle
    max_concurrent_steps: int = 1
    supports_retry: bool = False
    supports_timeout: bool = True
    default_timeout_seconds: int = 300
    description: str = ""


@dataclass
class WorkerDefinition:
    """Definition of a worker type."""
    worker_type: WorkerType
    capabilities: WorkerCapabilities
    handler: Optional[Callable] = None  # Step execution handler
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkerInstance:
    """An active worker instance."""
    instance_id: str
    worker_type: WorkerType
    status: WorkerStatus = WorkerStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    last_active_at: Optional[datetime] = None
    current_step_id: Optional[str] = None
    completed_steps: int = 0
    failed_steps: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        """Check if worker is available for work."""
        return self.status == WorkerStatus.IDLE

    @property
    def success_rate(self) -> float:
        """Calculate step success rate."""
        total = self.completed_steps + self.failed_steps
        if total == 0:
            return 1.0
        return self.completed_steps / total


class WorkerRegistry:
    """
    Registry for worker types and instances.

    Manages worker definitions and tracks active worker instances.
    """

    def __init__(self):
        """Initialize the worker registry."""
        self._definitions: Dict[WorkerType, WorkerDefinition] = {}
        self._instances: Dict[str, WorkerInstance] = {}
        self._lock = threading.Lock()
        self._loaded = False

    def load(self) -> bool:
        """Load default worker definitions."""
        try:
            self._register_default_workers()
            self._loaded = True
            return True
        except Exception:
            self._loaded = False
            return False

    @property
    def is_loaded(self) -> bool:
        """Check if registry is loaded."""
        return self._loaded

    def _register_default_workers(self) -> None:
        """Register the default worker types."""
        # Import here to avoid circular imports
        from .execution_plan import ExecutionDomain

        # General worker - handles any domain
        self.register_definition(WorkerDefinition(
            worker_type=WorkerType.GENERAL,
            capabilities=WorkerCapabilities(
                worker_type=WorkerType.GENERAL,
                domains={d.value for d in ExecutionDomain},
                max_concurrent_steps=1,
                supports_retry=True,
                supports_timeout=True,
                default_timeout_seconds=300,
                description="General-purpose worker for any domain",
            ),
        ))

        # Research worker
        self.register_definition(WorkerDefinition(
            worker_type=WorkerType.RESEARCH,
            capabilities=WorkerCapabilities(
                worker_type=WorkerType.RESEARCH,
                domains={"research"},
                max_concurrent_steps=2,
                supports_retry=True,
                supports_timeout=True,
                default_timeout_seconds=600,
                description="Specialized worker for research tasks",
            ),
        ))

        # Planning worker
        self.register_definition(WorkerDefinition(
            worker_type=WorkerType.PLANNING,
            capabilities=WorkerCapabilities(
                worker_type=WorkerType.PLANNING,
                domains={"planning"},
                max_concurrent_steps=1,
                supports_retry=True,
                supports_timeout=True,
                default_timeout_seconds=300,
                description="Specialized worker for planning tasks",
            ),
        ))

        # Product worker
        self.register_definition(WorkerDefinition(
            worker_type=WorkerType.PRODUCT,
            capabilities=WorkerCapabilities(
                worker_type=WorkerType.PRODUCT,
                domains={"product"},
                max_concurrent_steps=2,
                supports_retry=True,
                supports_timeout=True,
                default_timeout_seconds=600,
                description="Specialized worker for product development",
            ),
        ))

        # Operations worker
        self.register_definition(WorkerDefinition(
            worker_type=WorkerType.OPERATIONS,
            capabilities=WorkerCapabilities(
                worker_type=WorkerType.OPERATIONS,
                domains={"operations"},
                max_concurrent_steps=3,
                supports_retry=True,
                supports_timeout=True,
                default_timeout_seconds=300,
                description="Specialized worker for operations tasks",
            ),
        ))

        # Growth worker
        self.register_definition(WorkerDefinition(
            worker_type=WorkerType.GROWTH,
            capabilities=WorkerCapabilities(
                worker_type=WorkerType.GROWTH,
                domains={"growth"},
                max_concurrent_steps=2,
                supports_retry=True,
                supports_timeout=True,
                default_timeout_seconds=300,
                description="Specialized worker for growth/marketing tasks",
            ),
        ))

        # Automation worker
        self.register_definition(WorkerDefinition(
            worker_type=WorkerType.AUTOMATION,
            capabilities=WorkerCapabilities(
                worker_type=WorkerType.AUTOMATION,
                domains={"automation"},
                max_concurrent_steps=4,
                supports_retry=True,
                supports_timeout=True,
                default_timeout_seconds=120,
                description="Specialized worker for automation tasks",
            ),
        ))

        # Validation worker
        self.register_definition(WorkerDefinition(
            worker_type=WorkerType.VALIDATION,
            capabilities=WorkerCapabilities(
                worker_type=WorkerType.VALIDATION,
                domains={"validation"},
                max_concurrent_steps=2,
                supports_retry=True,
                supports_timeout=True,
                default_timeout_seconds=300,
                description="Specialized worker for validation tasks",
            ),
        ))

        # Content worker
        self.register_definition(WorkerDefinition(
            worker_type=WorkerType.CONTENT,
            capabilities=WorkerCapabilities(
                worker_type=WorkerType.CONTENT,
                domains={"content"},
                max_concurrent_steps=2,
                supports_retry=True,
                supports_timeout=True,
                default_timeout_seconds=300,
                description="Specialized worker for content creation",
            ),
        ))

    def register_definition(self, definition: WorkerDefinition) -> None:
        """
        Register a worker definition.

        Args:
            definition: Worker definition to register.
        """
        with self._lock:
            self._definitions[definition.worker_type] = definition

    def get_definition(self, worker_type: WorkerType) -> Optional[WorkerDefinition]:
        """
        Get a worker definition.

        Args:
            worker_type: Type of worker.

        Returns:
            WorkerDefinition if found, None otherwise.
        """
        return self._definitions.get(worker_type)

    def get_worker_for_domain(self, domain: str) -> Optional[WorkerType]:
        """
        Get the best worker type for a domain.

        Prefers specialized workers over general workers.

        Args:
            domain: Execution domain.

        Returns:
            Best WorkerType for the domain.
        """
        # First, look for specialized worker
        for worker_type, definition in self._definitions.items():
            if worker_type == WorkerType.GENERAL:
                continue
            if domain in definition.capabilities.domains:
                return worker_type

        # Fall back to general worker
        if WorkerType.GENERAL in self._definitions:
            return WorkerType.GENERAL

        return None

    def spawn_instance(
        self,
        worker_type: WorkerType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkerInstance]:
        """
        Spawn a new worker instance.

        Args:
            worker_type: Type of worker to spawn.
            metadata: Optional metadata for the instance.

        Returns:
            New WorkerInstance if successful, None otherwise.
        """
        if worker_type not in self._definitions:
            return None

        instance = WorkerInstance(
            instance_id=str(uuid.uuid4()),
            worker_type=worker_type,
            status=WorkerStatus.IDLE,
            metadata=metadata or {},
        )

        with self._lock:
            self._instances[instance.instance_id] = instance

        return instance

    def get_instance(self, instance_id: str) -> Optional[WorkerInstance]:
        """Get a worker instance by ID."""
        return self._instances.get(instance_id)

    def list_instances(
        self,
        worker_type: Optional[WorkerType] = None,
        status: Optional[WorkerStatus] = None,
    ) -> List[WorkerInstance]:
        """
        List worker instances with optional filtering.

        Args:
            worker_type: Filter by worker type.
            status: Filter by status.

        Returns:
            List of matching worker instances.
        """
        instances = list(self._instances.values())

        if worker_type:
            instances = [i for i in instances if i.worker_type == worker_type]

        if status:
            instances = [i for i in instances if i.status == status]

        return instances

    def get_available_instance(
        self,
        worker_type: WorkerType,
    ) -> Optional[WorkerInstance]:
        """
        Get an available worker instance of a type.

        Args:
            worker_type: Type of worker needed.

        Returns:
            Available WorkerInstance if found, None otherwise.
        """
        instances = self.list_instances(worker_type=worker_type, status=WorkerStatus.IDLE)
        return instances[0] if instances else None

    def update_instance_status(
        self,
        instance_id: str,
        status: WorkerStatus,
        step_id: Optional[str] = None,
    ) -> bool:
        """
        Update a worker instance status.

        Args:
            instance_id: Instance ID.
            status: New status.
            step_id: Current step ID if busy.

        Returns:
            True if updated, False if not found.
        """
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False

            instance.status = status
            instance.last_active_at = datetime.now()

            if status == WorkerStatus.BUSY and step_id:
                instance.current_step_id = step_id
            elif status == WorkerStatus.IDLE:
                instance.current_step_id = None

            return True

    def record_step_completion(
        self,
        instance_id: str,
        success: bool,
    ) -> bool:
        """
        Record step completion for a worker.

        Args:
            instance_id: Instance ID.
            success: Whether step succeeded.

        Returns:
            True if recorded, False if not found.
        """
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False

            if success:
                instance.completed_steps += 1
            else:
                instance.failed_steps += 1

            instance.last_active_at = datetime.now()
            return True

    def terminate_instance(self, instance_id: str) -> bool:
        """
        Terminate a worker instance.

        Args:
            instance_id: Instance ID to terminate.

        Returns:
            True if terminated, False if not found.
        """
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False

            instance.status = WorkerStatus.STOPPED
            return True

    def remove_instance(self, instance_id: str) -> bool:
        """
        Remove a worker instance from registry.

        Args:
            instance_id: Instance ID to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if instance_id in self._instances:
                del self._instances[instance_id]
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            total = len(self._instances)
            by_status = {}
            by_type = {}

            for instance in self._instances.values():
                status_key = instance.status.value
                by_status[status_key] = by_status.get(status_key, 0) + 1

                type_key = instance.worker_type.value
                by_type[type_key] = by_type.get(type_key, 0) + 1

            return {
                "total_definitions": len(self._definitions),
                "total_instances": total,
                "by_status": by_status,
                "by_type": by_type,
            }


# Singleton instance
_worker_registry: Optional[WorkerRegistry] = None


def get_worker_registry() -> WorkerRegistry:
    """Get the global worker registry."""
    global _worker_registry
    if _worker_registry is None:
        _worker_registry = WorkerRegistry()
    return _worker_registry


def get_worker_for_domain(domain: str) -> Optional[WorkerType]:
    """
    Get the best worker type for a domain.

    Args:
        domain: Execution domain.

    Returns:
        Best WorkerType for the domain.
    """
    registry = get_worker_registry()
    if not registry.is_loaded:
        registry.load()
    return registry.get_worker_for_domain(domain)
