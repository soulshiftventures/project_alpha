"""
Job Dispatcher - Job lifecycle management for execution plans.

Manages job creation, submission, tracking, and completion across backends.
Provides a unified interface for dispatching execution plans to backends.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
import uuid
import threading

from .execution_backends import (
    ExecutionBackend,
    BackendType,
    JobResult,
    JobStatus,
    StepResult,
)
from .worker_registry import (
    WorkerRegistry,
    WorkerType,
    WorkerInstance,
    WorkerStatus,
    get_worker_registry,
)


class DispatchStrategy(Enum):
    """Strategy for dispatching jobs to backends."""
    IMMEDIATE = "immediate"  # Execute immediately on submission
    QUEUED = "queued"  # Queue for later execution
    SCHEDULED = "scheduled"  # Schedule for specific time
    RETRY_ON_FAILURE = "retry_on_failure"  # Retry failed steps


class DispatchPriority(Enum):
    """Priority levels for job dispatch."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class DispatchOptions:
    """Options for job dispatch."""
    strategy: DispatchStrategy = DispatchStrategy.IMMEDIATE
    priority: DispatchPriority = DispatchPriority.NORMAL
    timeout_seconds: Optional[int] = None
    max_retries: int = 0
    stop_on_failure: bool = True
    parallel_steps: bool = False
    worker_type: Optional[WorkerType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatchedJob:
    """A job that has been dispatched for execution."""
    job_id: str
    plan_id: str
    backend_type: BackendType
    options: DispatchOptions
    status: JobStatus = JobStatus.PENDING
    dispatched_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[JobResult] = None
    worker_instance_id: Optional[str] = None
    retry_count: int = 0
    error: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        """Check if job has completed (success or failure)."""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.TIMEOUT,
        )

    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status == JobStatus.FAILED
            and self.options.strategy == DispatchStrategy.RETRY_ON_FAILURE
            and self.retry_count < self.options.max_retries
        )


class JobDispatcher:
    """
    Dispatcher for managing job lifecycle across backends.

    Handles job creation, submission, tracking, and completion.
    """

    def __init__(self, worker_registry: Optional[WorkerRegistry] = None):
        """
        Initialize the job dispatcher.

        Args:
            worker_registry: Worker registry to use (defaults to global).
        """
        self._worker_registry = worker_registry or get_worker_registry()
        self._jobs: Dict[str, DispatchedJob] = {}
        self._backends: Dict[BackendType, ExecutionBackend] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            "on_job_started": [],
            "on_job_completed": [],
            "on_job_failed": [],
            "on_step_completed": [],
        }
        self._lock = threading.Lock()

    def register_backend(self, backend: ExecutionBackend) -> None:
        """
        Register an execution backend.

        Args:
            backend: Backend to register.
        """
        caps = backend.get_capabilities()
        with self._lock:
            self._backends[caps.backend_type] = backend

    def get_backend(self, backend_type: BackendType) -> Optional[ExecutionBackend]:
        """
        Get a registered backend.

        Args:
            backend_type: Type of backend.

        Returns:
            Backend if registered, None otherwise.
        """
        return self._backends.get(backend_type)

    def list_backends(self) -> List[BackendType]:
        """List all registered backend types."""
        return list(self._backends.keys())

    def register_callback(
        self,
        event: str,
        callback: Callable,
    ) -> None:
        """
        Register a callback for job events.

        Args:
            event: Event name (on_job_started, on_job_completed, etc.).
            callback: Callback function.
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _fire_callbacks(self, event: str, *args, **kwargs) -> None:
        """Fire all callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception:
                pass  # Don't let callback errors break dispatch

    def dispatch(
        self,
        plan: Any,
        backend_type: BackendType,
        options: Optional[DispatchOptions] = None,
    ) -> DispatchedJob:
        """
        Dispatch an execution plan to a backend.

        Args:
            plan: ExecutionPlan to dispatch.
            backend_type: Backend to use.
            options: Dispatch options.

        Returns:
            DispatchedJob tracking the execution.
        """
        options = options or DispatchOptions()

        # Create dispatched job record
        job_id = str(uuid.uuid4())
        plan_id = getattr(plan, "plan_id", "unknown")

        dispatched = DispatchedJob(
            job_id=job_id,
            plan_id=plan_id,
            backend_type=backend_type,
            options=options,
            status=JobStatus.PENDING,
        )

        with self._lock:
            self._jobs[job_id] = dispatched

        # Get backend
        backend = self._backends.get(backend_type)
        if not backend:
            dispatched.status = JobStatus.FAILED
            dispatched.error = f"Backend not registered: {backend_type.value}"
            dispatched.completed_at = datetime.now()
            return dispatched

        # Assign worker if using worker registry
        if options.worker_type and self._worker_registry.is_loaded:
            worker = self._worker_registry.get_available_instance(options.worker_type)
            if worker:
                dispatched.worker_instance_id = worker.instance_id
                self._worker_registry.update_instance_status(
                    worker.instance_id, WorkerStatus.BUSY
                )

        # Execute based on strategy
        if options.strategy == DispatchStrategy.IMMEDIATE:
            return self._execute_immediate(dispatched, plan, backend, options)
        elif options.strategy == DispatchStrategy.QUEUED:
            dispatched.status = JobStatus.QUEUED
            # Queue execution would be handled by a separate worker
            return dispatched
        else:
            return self._execute_immediate(dispatched, plan, backend, options)

    def _execute_immediate(
        self,
        dispatched: DispatchedJob,
        plan: Any,
        backend: ExecutionBackend,
        options: DispatchOptions,
    ) -> DispatchedJob:
        """Execute a job immediately."""
        dispatched.status = JobStatus.RUNNING
        dispatched.started_at = datetime.now()

        self._fire_callbacks("on_job_started", dispatched)

        try:
            # Build execution context
            context = {
                "stop_on_failure": options.stop_on_failure,
                "parallel": options.parallel_steps,
                "timeout": options.timeout_seconds,
                **options.metadata,
            }

            # Execute on backend
            result = backend.execute(plan, context)

            dispatched.result = result
            dispatched.status = result.status
            dispatched.completed_at = datetime.now()

            # Fire completion callbacks
            if result.status == JobStatus.COMPLETED:
                self._fire_callbacks("on_job_completed", dispatched)
            else:
                self._fire_callbacks("on_job_failed", dispatched)

                # Check for retry
                if dispatched.can_retry:
                    dispatched.retry_count += 1
                    return self._execute_immediate(dispatched, plan, backend, options)

        except Exception as e:
            dispatched.status = JobStatus.FAILED
            dispatched.error = str(e)
            dispatched.completed_at = datetime.now()
            self._fire_callbacks("on_job_failed", dispatched)

        # Release worker
        if dispatched.worker_instance_id:
            self._worker_registry.update_instance_status(
                dispatched.worker_instance_id, WorkerStatus.IDLE
            )
            success = dispatched.status == JobStatus.COMPLETED
            self._worker_registry.record_step_completion(
                dispatched.worker_instance_id, success
            )

        with self._lock:
            self._jobs[dispatched.job_id] = dispatched

        return dispatched

    def get_job(self, job_id: str) -> Optional[DispatchedJob]:
        """
        Get a dispatched job by ID.

        Args:
            job_id: Job ID.

        Returns:
            DispatchedJob if found, None otherwise.
        """
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        backend_type: Optional[BackendType] = None,
    ) -> List[DispatchedJob]:
        """
        List jobs with optional filtering.

        Args:
            status: Filter by status.
            backend_type: Filter by backend type.

        Returns:
            List of matching jobs.
        """
        jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        if backend_type:
            jobs = [j for j in jobs if j.backend_type == backend_type]

        return jobs

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job ID to cancel.

        Returns:
            True if cancelled, False otherwise.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.is_complete:
                return False  # Already complete

            # Try to cancel on backend
            backend = self._backends.get(job.backend_type)
            if backend:
                backend.cancel(job_id)

            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()

            # Release worker
            if job.worker_instance_id:
                self._worker_registry.update_instance_status(
                    job.worker_instance_id, WorkerStatus.IDLE
                )

            return True

    def retry_job(self, job_id: str) -> Optional[DispatchedJob]:
        """
        Retry a failed job.

        Args:
            job_id: Job ID to retry.

        Returns:
            New DispatchedJob for retry, None if not retryable.
        """
        job = self._jobs.get(job_id)
        if not job or job.status != JobStatus.FAILED:
            return None

        if not job.can_retry:
            return None

        # Get the original plan from the result
        # In a real implementation, we'd store the plan reference
        return None  # Retry requires plan storage

    def get_stats(self) -> Dict[str, Any]:
        """Get dispatcher statistics."""
        with self._lock:
            total = len(self._jobs)
            by_status = {}
            by_backend = {}

            for job in self._jobs.values():
                status_key = job.status.value
                by_status[status_key] = by_status.get(status_key, 0) + 1

                backend_key = job.backend_type.value
                by_backend[backend_key] = by_backend.get(backend_key, 0) + 1

            completed = by_status.get("completed", 0)
            failed = by_status.get("failed", 0)
            total_finished = completed + failed

            return {
                "total_jobs": total,
                "by_status": by_status,
                "by_backend": by_backend,
                "registered_backends": len(self._backends),
                "success_rate": completed / total_finished if total_finished > 0 else 0.0,
            }

    def cleanup_completed(self, older_than_seconds: int = 3600) -> int:
        """
        Clean up completed jobs older than specified time.

        Args:
            older_than_seconds: Age threshold in seconds.

        Returns:
            Number of jobs cleaned up.
        """
        cutoff = datetime.now()
        cleaned = 0

        with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job.is_complete and job.completed_at:
                    age = (cutoff - job.completed_at).total_seconds()
                    if age > older_than_seconds:
                        to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]
                cleaned += 1

        return cleaned


# Singleton instance
_job_dispatcher: Optional[JobDispatcher] = None


def get_job_dispatcher() -> JobDispatcher:
    """Get the global job dispatcher."""
    global _job_dispatcher
    if _job_dispatcher is None:
        _job_dispatcher = JobDispatcher()
    return _job_dispatcher


def dispatch_plan(
    plan: Any,
    backend_type: BackendType,
    options: Optional[DispatchOptions] = None,
) -> DispatchedJob:
    """
    Dispatch an execution plan to a backend.

    Args:
        plan: ExecutionPlan to dispatch.
        backend_type: Backend to use.
        options: Dispatch options.

    Returns:
        DispatchedJob tracking the execution.
    """
    dispatcher = get_job_dispatcher()
    return dispatcher.dispatch(plan, backend_type, options)
