"""
Execution Backends - Interchangeable execution backends for running execution plans.

Provides a clean backend interface with multiple implementations:
- InlineLocalBackend: Direct synchronous execution in-process
- QueueLocalBackend: Queue-based local execution with worker pool
- StubContainerBackend: Scaffold for future container-based execution
- StubKubernetesBackend: Scaffold for future Kubernetes execution

All backends accept ExecutionPlan and return structured JobResult.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
from datetime import datetime
import uuid
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, Future


class BackendType(Enum):
    """Types of execution backends."""
    INLINE_LOCAL = "inline_local"
    QUEUE_LOCAL = "queue_local"
    CONTAINER = "container"
    KUBERNETES = "kubernetes"


class JobStatus(Enum):
    """Status of a job in the execution pipeline."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class StepResult:
    """Result of executing a single execution step."""
    step_id: str
    step_name: str
    status: JobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate step duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_success(self) -> bool:
        """Check if step completed successfully."""
        return self.status == JobStatus.COMPLETED


@dataclass
class JobResult:
    """Result of executing an entire execution plan."""
    job_id: str
    plan_id: str
    backend_type: BackendType
    status: JobStatus
    step_results: List[StepResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate total job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_success(self) -> bool:
        """Check if job completed successfully."""
        return self.status == JobStatus.COMPLETED and self.failed_steps == 0

    @property
    def success_rate(self) -> float:
        """Calculate step success rate."""
        if self.total_steps == 0:
            return 0.0
        return self.completed_steps / self.total_steps


@dataclass
class BackendCapabilities:
    """Capabilities and constraints of a backend."""
    backend_type: BackendType
    supports_parallel: bool = False
    supports_retry: bool = False
    supports_timeout: bool = False
    supports_cancellation: bool = False
    max_concurrent_jobs: int = 1
    max_concurrent_steps: int = 1
    supports_persistence: bool = False
    is_scaffold: bool = False  # True for stub backends
    description: str = ""


class ExecutionBackend(ABC):
    """
    Abstract base class for execution backends.

    All backends must implement execute() and get_capabilities().
    """

    @abstractmethod
    def execute(self, plan: Any, context: Optional[Dict[str, Any]] = None) -> JobResult:
        """
        Execute an execution plan.

        Args:
            plan: ExecutionPlan to execute.
            context: Optional execution context with runtime parameters.

        Returns:
            JobResult with execution outcome.
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> BackendCapabilities:
        """
        Get backend capabilities.

        Returns:
            BackendCapabilities describing what this backend supports.
        """
        pass

    @abstractmethod
    def get_status(self, job_id: str) -> Optional[JobResult]:
        """
        Get status of a running or completed job.

        Args:
            job_id: ID of the job to check.

        Returns:
            JobResult if job exists, None otherwise.
        """
        pass

    def cancel(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: ID of the job to cancel.

        Returns:
            True if cancelled, False if not cancellable.
        """
        return False  # Default: not supported

    def cleanup(self) -> None:
        """Clean up backend resources."""
        pass


class InlineLocalBackend(ExecutionBackend):
    """
    Direct synchronous execution in the current process.

    Executes steps sequentially, blocking until completion.
    Best for simple, fast operations that don't need parallelism.
    """

    def __init__(self):
        """Initialize the inline backend."""
        self._jobs: Dict[str, JobResult] = {}
        self._step_handlers: Dict[str, Callable] = {}

    def register_step_handler(self, domain: str, handler: Callable) -> None:
        """
        Register a handler function for a domain.

        Args:
            domain: Domain name (e.g., "research", "planning").
            handler: Callable that executes steps for this domain.
        """
        self._step_handlers[domain] = handler

    def execute(self, plan: Any, context: Optional[Dict[str, Any]] = None) -> JobResult:
        """Execute plan synchronously."""
        job_id = str(uuid.uuid4())
        started_at = datetime.now()

        # Import here to avoid circular imports
        from .execution_plan import ExecutionPlan, ExecutionStep, ExecutionStatus

        # Validate plan
        if not isinstance(plan, ExecutionPlan):
            return JobResult(
                job_id=job_id,
                plan_id="unknown",
                backend_type=BackendType.INLINE_LOCAL,
                status=JobStatus.FAILED,
                error="Invalid plan type - expected ExecutionPlan",
                started_at=started_at,
                completed_at=datetime.now(),
            )

        result = JobResult(
            job_id=job_id,
            plan_id=plan.plan_id,
            backend_type=BackendType.INLINE_LOCAL,
            status=JobStatus.RUNNING,
            started_at=started_at,
            total_steps=len(plan.steps),
        )

        self._jobs[job_id] = result

        # Execute each step sequentially
        for step in plan.steps:
            step_result = self._execute_step(step, context)
            result.step_results.append(step_result)

            if step_result.is_success:
                result.completed_steps += 1
            else:
                result.failed_steps += 1
                # Stop on first failure for inline backend
                if context and context.get("stop_on_failure", True):
                    break

        # Finalize result
        result.completed_at = datetime.now()
        result.status = (
            JobStatus.COMPLETED if result.failed_steps == 0 else JobStatus.FAILED
        )

        self._jobs[job_id] = result
        return result

    def _execute_step(
        self, step: Any, context: Optional[Dict[str, Any]]
    ) -> StepResult:
        """Execute a single step."""
        started_at = datetime.now()

        try:
            # Get handler for domain
            domain = step.domain.value if hasattr(step.domain, "value") else str(step.domain)
            handler = self._step_handlers.get(domain)

            if handler:
                output = handler(step, context)
            else:
                # Default: return step info as output
                output = {
                    "step_id": step.step_id,
                    "description": step.description,
                    "domain": domain,
                    "executed": True,
                    "handler": "default",
                }

            return StepResult(
                step_id=step.step_id,
                step_name=step.description,
                status=JobStatus.COMPLETED,
                started_at=started_at,
                completed_at=datetime.now(),
                output=output,
            )

        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                step_name=step.description,
                status=JobStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(),
                error=str(e),
            )

    def get_capabilities(self) -> BackendCapabilities:
        """Return inline backend capabilities."""
        return BackendCapabilities(
            backend_type=BackendType.INLINE_LOCAL,
            supports_parallel=False,
            supports_retry=False,
            supports_timeout=False,
            supports_cancellation=False,
            max_concurrent_jobs=1,
            max_concurrent_steps=1,
            supports_persistence=False,
            is_scaffold=False,
            description="Direct synchronous execution in current process",
        )

    def get_status(self, job_id: str) -> Optional[JobResult]:
        """Get job status."""
        return self._jobs.get(job_id)


class QueueLocalBackend(ExecutionBackend):
    """
    Queue-based local execution with worker pool.

    Supports parallel step execution within a job using a thread pool.
    Good for I/O-bound operations that benefit from concurrency.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize the queue backend.

        Args:
            max_workers: Maximum number of concurrent workers.
        """
        self._max_workers = max_workers
        self._jobs: Dict[str, JobResult] = {}
        self._step_handlers: Dict[str, Callable] = {}
        self._executor: Optional[ThreadPoolExecutor] = None
        self._job_queue: queue.Queue = queue.Queue()
        self._running = False
        self._lock = threading.Lock()

    def register_step_handler(self, domain: str, handler: Callable) -> None:
        """Register a handler function for a domain."""
        self._step_handlers[domain] = handler

    def start(self) -> None:
        """Start the worker pool."""
        if not self._running:
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
            self._running = True

    def stop(self) -> None:
        """Stop the worker pool."""
        if self._running and self._executor:
            self._executor.shutdown(wait=True)
            self._running = False

    def execute(self, plan: Any, context: Optional[Dict[str, Any]] = None) -> JobResult:
        """Execute plan with parallel step execution."""
        # Ensure executor is running
        if not self._running:
            self.start()

        job_id = str(uuid.uuid4())
        started_at = datetime.now()

        # Import here to avoid circular imports
        from .execution_plan import ExecutionPlan

        # Validate plan
        if not isinstance(plan, ExecutionPlan):
            return JobResult(
                job_id=job_id,
                plan_id="unknown",
                backend_type=BackendType.QUEUE_LOCAL,
                status=JobStatus.FAILED,
                error="Invalid plan type - expected ExecutionPlan",
                started_at=started_at,
                completed_at=datetime.now(),
            )

        result = JobResult(
            job_id=job_id,
            plan_id=plan.plan_id,
            backend_type=BackendType.QUEUE_LOCAL,
            status=JobStatus.RUNNING,
            started_at=started_at,
            total_steps=len(plan.steps),
        )

        with self._lock:
            self._jobs[job_id] = result

        # Check if parallel execution is requested
        parallel = context.get("parallel", False) if context else False

        if parallel and self._executor:
            # Submit all steps to executor
            futures: List[Future] = []
            for step in plan.steps:
                future = self._executor.submit(self._execute_step, step, context)
                futures.append(future)

            # Collect results
            for future in futures:
                try:
                    step_result = future.result()
                    result.step_results.append(step_result)
                    if step_result.is_success:
                        result.completed_steps += 1
                    else:
                        result.failed_steps += 1
                except Exception as e:
                    result.failed_steps += 1
                    result.step_results.append(
                        StepResult(
                            step_id="unknown",
                            step_name="unknown",
                            status=JobStatus.FAILED,
                            error=str(e),
                        )
                    )
        else:
            # Sequential execution
            for step in plan.steps:
                step_result = self._execute_step(step, context)
                result.step_results.append(step_result)
                if step_result.is_success:
                    result.completed_steps += 1
                else:
                    result.failed_steps += 1

        # Finalize result
        result.completed_at = datetime.now()
        result.status = (
            JobStatus.COMPLETED if result.failed_steps == 0 else JobStatus.FAILED
        )

        with self._lock:
            self._jobs[job_id] = result

        return result

    def _execute_step(
        self, step: Any, context: Optional[Dict[str, Any]]
    ) -> StepResult:
        """Execute a single step."""
        started_at = datetime.now()

        try:
            domain = step.domain.value if hasattr(step.domain, "value") else str(step.domain)
            handler = self._step_handlers.get(domain)

            if handler:
                output = handler(step, context)
            else:
                output = {
                    "step_id": step.step_id,
                    "description": step.description,
                    "domain": domain,
                    "executed": True,
                    "handler": "default",
                }

            return StepResult(
                step_id=step.step_id,
                step_name=step.description,
                status=JobStatus.COMPLETED,
                started_at=started_at,
                completed_at=datetime.now(),
                output=output,
            )

        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                step_name=step.description,
                status=JobStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(),
                error=str(e),
            )

    def get_capabilities(self) -> BackendCapabilities:
        """Return queue backend capabilities."""
        return BackendCapabilities(
            backend_type=BackendType.QUEUE_LOCAL,
            supports_parallel=True,
            supports_retry=False,
            supports_timeout=False,
            supports_cancellation=False,
            max_concurrent_jobs=self._max_workers,
            max_concurrent_steps=self._max_workers,
            supports_persistence=False,
            is_scaffold=False,
            description=f"Queue-based execution with {self._max_workers} workers",
        )

    def get_status(self, job_id: str) -> Optional[JobResult]:
        """Get job status."""
        with self._lock:
            return self._jobs.get(job_id)

    def cleanup(self) -> None:
        """Clean up executor resources."""
        self.stop()


class StubContainerBackend(ExecutionBackend):
    """
    Scaffold backend for future container-based execution.

    This is a structural scaffold that returns deterministic results.
    It demonstrates the interface for container execution without
    requiring actual container infrastructure.

    Future implementation would:
    - Build container images for execution steps
    - Run containers with resource limits
    - Stream logs and metrics
    - Support container orchestration
    """

    def __init__(self, container_runtime: str = "docker"):
        """
        Initialize the container backend scaffold.

        Args:
            container_runtime: Container runtime to use (docker, podman, etc.).
        """
        self._container_runtime = container_runtime
        self._jobs: Dict[str, JobResult] = {}

    def execute(self, plan: Any, context: Optional[Dict[str, Any]] = None) -> JobResult:
        """
        Execute plan using container scaffold.

        Returns deterministic results simulating container execution.
        """
        job_id = str(uuid.uuid4())
        started_at = datetime.now()

        # Import here to avoid circular imports
        from .execution_plan import ExecutionPlan

        # Validate plan
        if not isinstance(plan, ExecutionPlan):
            return JobResult(
                job_id=job_id,
                plan_id="unknown",
                backend_type=BackendType.CONTAINER,
                status=JobStatus.FAILED,
                error="Invalid plan type - expected ExecutionPlan",
                started_at=started_at,
                completed_at=datetime.now(),
                metadata={"scaffold": True, "runtime": self._container_runtime},
            )

        result = JobResult(
            job_id=job_id,
            plan_id=plan.plan_id,
            backend_type=BackendType.CONTAINER,
            status=JobStatus.RUNNING,
            started_at=started_at,
            total_steps=len(plan.steps),
            metadata={
                "scaffold": True,
                "runtime": self._container_runtime,
                "note": "Container backend is a scaffold - no actual containers executed",
            },
        )

        self._jobs[job_id] = result

        # Generate scaffold results for each step
        for step in plan.steps:
            domain = step.domain.value if hasattr(step.domain, "value") else str(step.domain)

            step_result = StepResult(
                step_id=step.step_id,
                step_name=step.description,
                status=JobStatus.COMPLETED,
                started_at=datetime.now(),
                completed_at=datetime.now(),
                output={
                    "scaffold": True,
                    "container_image": f"project-alpha/{domain}:latest",
                    "container_id": f"scaffold-{step.step_id[:8]}",
                    "exit_code": 0,
                    "logs": f"[SCAFFOLD] Would execute step: {step.description}",
                },
                metrics={
                    "cpu_seconds": 0.0,
                    "memory_mb": 0.0,
                    "scaffold": True,
                },
            )
            result.step_results.append(step_result)
            result.completed_steps += 1

        # Finalize result
        result.completed_at = datetime.now()
        result.status = JobStatus.COMPLETED

        self._jobs[job_id] = result
        return result

    def get_capabilities(self) -> BackendCapabilities:
        """Return container backend capabilities."""
        return BackendCapabilities(
            backend_type=BackendType.CONTAINER,
            supports_parallel=True,
            supports_retry=True,
            supports_timeout=True,
            supports_cancellation=True,
            max_concurrent_jobs=10,
            max_concurrent_steps=10,
            supports_persistence=True,
            is_scaffold=True,
            description=f"Container execution scaffold using {self._container_runtime} (not yet implemented)",
        )

    def get_status(self, job_id: str) -> Optional[JobResult]:
        """Get job status."""
        return self._jobs.get(job_id)


class StubKubernetesBackend(ExecutionBackend):
    """
    Scaffold backend for future Kubernetes execution.

    This is a structural scaffold that returns deterministic results.
    It demonstrates the interface for Kubernetes execution without
    requiring actual cluster infrastructure.

    Future implementation would:
    - Create Kubernetes Jobs for execution steps
    - Support resource requests/limits
    - Handle pod scheduling and affinity
    - Stream logs from pods
    - Support namespaces and RBAC
    """

    def __init__(
        self,
        namespace: str = "project-alpha",
        kubeconfig: Optional[str] = None,
    ):
        """
        Initialize the Kubernetes backend scaffold.

        Args:
            namespace: Kubernetes namespace for jobs.
            kubeconfig: Path to kubeconfig file.
        """
        self._namespace = namespace
        self._kubeconfig = kubeconfig
        self._jobs: Dict[str, JobResult] = {}

    def execute(self, plan: Any, context: Optional[Dict[str, Any]] = None) -> JobResult:
        """
        Execute plan using Kubernetes scaffold.

        Returns deterministic results simulating Kubernetes job execution.
        """
        job_id = str(uuid.uuid4())
        started_at = datetime.now()

        # Import here to avoid circular imports
        from .execution_plan import ExecutionPlan

        # Validate plan
        if not isinstance(plan, ExecutionPlan):
            return JobResult(
                job_id=job_id,
                plan_id="unknown",
                backend_type=BackendType.KUBERNETES,
                status=JobStatus.FAILED,
                error="Invalid plan type - expected ExecutionPlan",
                started_at=started_at,
                completed_at=datetime.now(),
                metadata={"scaffold": True, "namespace": self._namespace},
            )

        result = JobResult(
            job_id=job_id,
            plan_id=plan.plan_id,
            backend_type=BackendType.KUBERNETES,
            status=JobStatus.RUNNING,
            started_at=started_at,
            total_steps=len(plan.steps),
            metadata={
                "scaffold": True,
                "namespace": self._namespace,
                "kubeconfig": self._kubeconfig or "~/.kube/config",
                "note": "Kubernetes backend is a scaffold - no actual jobs executed",
            },
        )

        self._jobs[job_id] = result

        # Generate scaffold results for each step
        for i, step in enumerate(plan.steps):
            domain = step.domain.value if hasattr(step.domain, "value") else str(step.domain)
            job_name = f"pa-{domain}-{step.step_id[:8]}"

            step_result = StepResult(
                step_id=step.step_id,
                step_name=step.description,
                status=JobStatus.COMPLETED,
                started_at=datetime.now(),
                completed_at=datetime.now(),
                output={
                    "scaffold": True,
                    "k8s_job_name": job_name,
                    "namespace": self._namespace,
                    "pod_name": f"{job_name}-{i:04d}",
                    "node": "scaffold-node-1",
                    "exit_code": 0,
                    "logs": f"[SCAFFOLD] Would create K8s Job: {job_name}",
                },
                metrics={
                    "cpu_request": "100m",
                    "memory_request": "128Mi",
                    "cpu_limit": "500m",
                    "memory_limit": "512Mi",
                    "scaffold": True,
                },
            )
            result.step_results.append(step_result)
            result.completed_steps += 1

        # Finalize result
        result.completed_at = datetime.now()
        result.status = JobStatus.COMPLETED

        self._jobs[job_id] = result
        return result

    def get_capabilities(self) -> BackendCapabilities:
        """Return Kubernetes backend capabilities."""
        return BackendCapabilities(
            backend_type=BackendType.KUBERNETES,
            supports_parallel=True,
            supports_retry=True,
            supports_timeout=True,
            supports_cancellation=True,
            max_concurrent_jobs=100,
            max_concurrent_steps=50,
            supports_persistence=True,
            is_scaffold=True,
            description=f"Kubernetes execution scaffold in namespace '{self._namespace}' (not yet implemented)",
        )

    def get_status(self, job_id: str) -> Optional[JobResult]:
        """Get job status."""
        return self._jobs.get(job_id)


# Backend registry for easy lookup
_BACKEND_REGISTRY: Dict[BackendType, type] = {
    BackendType.INLINE_LOCAL: InlineLocalBackend,
    BackendType.QUEUE_LOCAL: QueueLocalBackend,
    BackendType.CONTAINER: StubContainerBackend,
    BackendType.KUBERNETES: StubKubernetesBackend,
}


def get_backend_class(backend_type: BackendType) -> type:
    """
    Get the backend class for a backend type.

    Args:
        backend_type: Type of backend.

    Returns:
        Backend class.

    Raises:
        ValueError: If backend type is unknown.
    """
    if backend_type not in _BACKEND_REGISTRY:
        raise ValueError(f"Unknown backend type: {backend_type}")
    return _BACKEND_REGISTRY[backend_type]


def create_backend(backend_type: BackendType, **kwargs) -> ExecutionBackend:
    """
    Create a backend instance.

    Args:
        backend_type: Type of backend to create.
        **kwargs: Backend-specific configuration.

    Returns:
        Configured backend instance.
    """
    backend_class = get_backend_class(backend_type)
    return backend_class(**kwargs)


def list_backends() -> List[Dict[str, Any]]:
    """
    List all available backends with their capabilities.

    Returns:
        List of backend info dictionaries.
    """
    backends = []
    for backend_type, backend_class in _BACKEND_REGISTRY.items():
        instance = backend_class()
        caps = instance.get_capabilities()
        backends.append({
            "type": backend_type.value,
            "class": backend_class.__name__,
            "is_scaffold": caps.is_scaffold,
            "supports_parallel": caps.supports_parallel,
            "description": caps.description,
        })
    return backends
