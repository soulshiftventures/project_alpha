"""
Runtime Manager - Central coordinator for execution backend selection and dispatch.

Accepts ExecutionPlan, chooses appropriate backend, dispatches execution,
and returns structured results. Integrates with policies, workers, and logging.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime

from .execution_plan import ExecutionPlan, ExecutionStatus
from .execution_backends import (
    ExecutionBackend,
    BackendType,
    JobResult,
    JobStatus,
    BackendCapabilities,
    InlineLocalBackend,
    QueueLocalBackend,
    StubContainerBackend,
    StubKubernetesBackend,
    create_backend,
    list_backends,
)
from .job_dispatcher import (
    JobDispatcher,
    DispatchedJob,
    DispatchOptions,
    DispatchStrategy,
    DispatchPriority,
    get_job_dispatcher,
)
from .worker_registry import (
    WorkerRegistry,
    WorkerType,
    get_worker_registry,
)


class BackendSelectionStrategy(Enum):
    """Strategy for selecting execution backend."""
    EXPLICIT = "explicit"  # Use explicitly specified backend
    AUTO = "auto"  # Auto-select based on plan characteristics
    PREFER_LOCAL = "prefer_local"  # Prefer local backends
    PREFER_PARALLEL = "prefer_parallel"  # Prefer backends with parallelism


@dataclass
class RuntimeConfig:
    """Configuration for the runtime manager."""
    default_backend: BackendType = BackendType.INLINE_LOCAL
    selection_strategy: BackendSelectionStrategy = BackendSelectionStrategy.AUTO
    enable_workers: bool = True
    enable_logging: bool = True
    default_timeout_seconds: int = 300
    max_retries: int = 0
    parallel_threshold: int = 3  # Use parallel backend if steps >= this


@dataclass
class RuntimeResult:
    """Result from runtime execution."""
    success: bool
    plan_id: str
    backend_type: BackendType
    job_result: Optional[JobResult] = None
    dispatched_job: Optional[DispatchedJob] = None
    execution_time_seconds: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def step_count(self) -> int:
        """Get total step count."""
        if self.job_result:
            return self.job_result.total_steps
        return 0

    @property
    def completed_steps(self) -> int:
        """Get completed step count."""
        if self.job_result:
            return self.job_result.completed_steps
        return 0


class RuntimeManager:
    """
    Central coordinator for execution runtime.

    Manages backend selection, job dispatch, and result handling.
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
        dispatcher: Optional[JobDispatcher] = None,
        worker_registry: Optional[WorkerRegistry] = None,
    ):
        """
        Initialize the runtime manager.

        Args:
            config: Runtime configuration.
            dispatcher: Job dispatcher to use.
            worker_registry: Worker registry to use.
        """
        self._config = config or RuntimeConfig()
        self._dispatcher = dispatcher or get_job_dispatcher()
        self._worker_registry = worker_registry or get_worker_registry()
        self._backends: Dict[BackendType, ExecutionBackend] = {}
        self._event_handlers: Dict[str, List[Callable]] = {
            "on_backend_selected": [],
            "on_execution_started": [],
            "on_execution_completed": [],
            "on_execution_failed": [],
        }
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize the runtime manager.

        Sets up default backends and workers.

        Returns:
            True if initialization successful.
        """
        try:
            # Initialize worker registry
            if self._config.enable_workers and not self._worker_registry.is_loaded:
                self._worker_registry.load()

            # Create and register default backends
            self._setup_default_backends()

            self._initialized = True
            return True
        except Exception:
            self._initialized = False
            return False

    def _setup_default_backends(self) -> None:
        """Set up default execution backends."""
        # Inline local backend
        inline = InlineLocalBackend()
        self._register_backend(inline)

        # Queue local backend
        queue = QueueLocalBackend(max_workers=4)
        self._register_backend(queue)

        # Container backend (scaffold)
        container = StubContainerBackend()
        self._register_backend(container)

        # Kubernetes backend (scaffold)
        k8s = StubKubernetesBackend()
        self._register_backend(k8s)

    def _register_backend(self, backend: ExecutionBackend) -> None:
        """Register a backend with both manager and dispatcher."""
        caps = backend.get_capabilities()
        self._backends[caps.backend_type] = backend
        self._dispatcher.register_backend(backend)

    @property
    def is_initialized(self) -> bool:
        """Check if runtime is initialized."""
        return self._initialized

    def register_event_handler(
        self,
        event: str,
        handler: Callable,
    ) -> None:
        """
        Register an event handler.

        Args:
            event: Event name.
            handler: Handler function.
        """
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)

    def _fire_event(self, event: str, *args, **kwargs) -> None:
        """Fire all handlers for an event."""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(*args, **kwargs)
            except Exception:
                pass

    def select_backend(
        self,
        plan: ExecutionPlan,
        explicit_backend: Optional[BackendType] = None,
    ) -> BackendType:
        """
        Select the best backend for a plan.

        Args:
            plan: ExecutionPlan to execute.
            explicit_backend: Explicitly requested backend.

        Returns:
            Selected BackendType.
        """
        # Explicit selection
        if explicit_backend:
            self._fire_event("on_backend_selected", plan, explicit_backend, "explicit")
            return explicit_backend

        strategy = self._config.selection_strategy

        if strategy == BackendSelectionStrategy.EXPLICIT:
            return self._config.default_backend

        if strategy == BackendSelectionStrategy.PREFER_LOCAL:
            # Always use local backends
            return BackendType.INLINE_LOCAL

        if strategy == BackendSelectionStrategy.PREFER_PARALLEL:
            # Use queue backend for parallel execution
            return BackendType.QUEUE_LOCAL

        # AUTO strategy - analyze plan
        return self._auto_select_backend(plan)

    def _auto_select_backend(self, plan: ExecutionPlan) -> BackendType:
        """Auto-select backend based on plan characteristics."""
        step_count = len(plan.steps)

        # Use queue backend for plans with many steps
        if step_count >= self._config.parallel_threshold:
            backend = BackendType.QUEUE_LOCAL
        else:
            backend = BackendType.INLINE_LOCAL

        self._fire_event("on_backend_selected", plan, backend, "auto")
        return backend

    def execute(
        self,
        plan: ExecutionPlan,
        backend_type: Optional[BackendType] = None,
        options: Optional[DispatchOptions] = None,
    ) -> RuntimeResult:
        """
        Execute an execution plan.

        Args:
            plan: ExecutionPlan to execute.
            backend_type: Specific backend to use (auto-selects if None).
            options: Dispatch options.

        Returns:
            RuntimeResult with execution outcome.
        """
        if not self._initialized:
            self.initialize()

        start_time = datetime.now()

        # Select backend
        selected_backend = self.select_backend(plan, backend_type)

        # Ensure backend exists
        if selected_backend not in self._backends:
            return RuntimeResult(
                success=False,
                plan_id=plan.plan_id,
                backend_type=selected_backend,
                error=f"Backend not available: {selected_backend.value}",
            )

        # Build dispatch options
        if options is None:
            options = DispatchOptions(
                strategy=DispatchStrategy.IMMEDIATE,
                timeout_seconds=self._config.default_timeout_seconds,
                max_retries=self._config.max_retries,
            )

        # Enable parallel for queue backend
        if selected_backend == BackendType.QUEUE_LOCAL:
            options.parallel_steps = True

        # Fire start event
        self._fire_event("on_execution_started", plan, selected_backend)

        try:
            # Dispatch to backend
            dispatched = self._dispatcher.dispatch(plan, selected_backend, options)

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Build result
            success = dispatched.status == JobStatus.COMPLETED

            result = RuntimeResult(
                success=success,
                plan_id=plan.plan_id,
                backend_type=selected_backend,
                job_result=dispatched.result,
                dispatched_job=dispatched,
                execution_time_seconds=execution_time,
                metadata={
                    "backend_is_scaffold": self._backends[selected_backend].get_capabilities().is_scaffold,
                },
            )

            # Fire completion event
            if success:
                self._fire_event("on_execution_completed", result)
            else:
                self._fire_event("on_execution_failed", result)

            return result

        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            result = RuntimeResult(
                success=False,
                plan_id=plan.plan_id,
                backend_type=selected_backend,
                execution_time_seconds=execution_time,
                error=str(e),
            )

            self._fire_event("on_execution_failed", result)
            return result

    def get_backend_capabilities(
        self,
        backend_type: BackendType,
    ) -> Optional[BackendCapabilities]:
        """
        Get capabilities for a backend.

        Args:
            backend_type: Backend type.

        Returns:
            BackendCapabilities if backend exists, None otherwise.
        """
        backend = self._backends.get(backend_type)
        if backend:
            return backend.get_capabilities()
        return None

    def list_available_backends(self) -> List[Dict[str, Any]]:
        """
        List all available backends with capabilities.

        Returns:
            List of backend info dictionaries.
        """
        results = []
        for backend_type, backend in self._backends.items():
            caps = backend.get_capabilities()
            results.append({
                "type": backend_type.value,
                "is_scaffold": caps.is_scaffold,
                "supports_parallel": caps.supports_parallel,
                "supports_retry": caps.supports_retry,
                "max_concurrent_jobs": caps.max_concurrent_jobs,
                "description": caps.description,
            })
        return results

    def get_job_status(self, job_id: str) -> Optional[DispatchedJob]:
        """
        Get status of a dispatched job.

        Args:
            job_id: Job ID.

        Returns:
            DispatchedJob if found, None otherwise.
        """
        return self._dispatcher.get_job(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job ID to cancel.

        Returns:
            True if cancelled, False otherwise.
        """
        return self._dispatcher.cancel_job(job_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get runtime statistics."""
        dispatcher_stats = self._dispatcher.get_stats()
        worker_stats = self._worker_registry.get_stats() if self._worker_registry.is_loaded else {}

        return {
            "initialized": self._initialized,
            "config": {
                "default_backend": self._config.default_backend.value,
                "selection_strategy": self._config.selection_strategy.value,
                "enable_workers": self._config.enable_workers,
                "parallel_threshold": self._config.parallel_threshold,
            },
            "backends": self.list_available_backends(),
            "dispatcher": dispatcher_stats,
            "workers": worker_stats,
        }

    def cleanup(self) -> None:
        """Clean up runtime resources."""
        for backend in self._backends.values():
            backend.cleanup()


# Singleton instance
_runtime_manager: Optional[RuntimeManager] = None


def get_runtime_manager() -> RuntimeManager:
    """Get the global runtime manager."""
    global _runtime_manager
    if _runtime_manager is None:
        _runtime_manager = RuntimeManager()
    return _runtime_manager


def execute_plan(
    plan: ExecutionPlan,
    backend_type: Optional[BackendType] = None,
    options: Optional[DispatchOptions] = None,
) -> RuntimeResult:
    """
    Execute an execution plan.

    Args:
        plan: ExecutionPlan to execute.
        backend_type: Specific backend to use (auto-selects if None).
        options: Dispatch options.

    Returns:
        RuntimeResult with execution outcome.
    """
    manager = get_runtime_manager()
    if not manager.is_initialized:
        manager.initialize()
    return manager.execute(plan, backend_type, options)


def get_available_backends() -> List[Dict[str, Any]]:
    """Get list of available backends."""
    manager = get_runtime_manager()
    if not manager.is_initialized:
        manager.initialize()
    return manager.list_available_backends()
