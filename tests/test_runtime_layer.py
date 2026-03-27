"""
Tests for the Runtime Abstraction Layer.

Tests execution backends, worker registry, job dispatcher, and runtime manager.
"""

import pytest
from datetime import datetime

# Execution backends tests
from core.execution_backends import (
    BackendType, JobStatus, StepResult, JobResult, BackendCapabilities,
    ExecutionBackend, InlineLocalBackend, QueueLocalBackend,
    StubContainerBackend, StubKubernetesBackend,
    get_backend_class, create_backend, list_backends
)

# Worker registry tests
from core.worker_registry import (
    WorkerType, WorkerStatus, WorkerCapabilities, WorkerDefinition, WorkerInstance,
    WorkerRegistry, get_worker_registry, get_worker_for_domain
)

# Job dispatcher tests
from core.job_dispatcher import (
    DispatchStrategy, DispatchPriority, DispatchOptions, DispatchedJob,
    JobDispatcher, get_job_dispatcher, dispatch_plan
)

# Runtime manager tests
from core.runtime_manager import (
    BackendSelectionStrategy, RuntimeConfig, RuntimeResult,
    RuntimeManager, get_runtime_manager, execute_plan, get_available_backends
)

# Execution plan for testing
from core.execution_plan import (
    ExecutionPlan, ExecutionStep, ExecutionDomain, ExecutionStatus, SkillBundle
)


# =============================================================================
# Execution Backends Tests
# =============================================================================

class TestBackendTypes:
    """Tests for backend type enums and structures."""

    def test_backend_type_values(self):
        """Test backend type enum values."""
        assert BackendType.INLINE_LOCAL.value == "inline_local"
        assert BackendType.QUEUE_LOCAL.value == "queue_local"
        assert BackendType.CONTAINER.value == "container"
        assert BackendType.KUBERNETES.value == "kubernetes"

    def test_job_status_values(self):
        """Test job status enum values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"

    def test_step_result_creation(self):
        """Test StepResult dataclass."""
        result = StepResult(
            step_id="step-1",
            step_name="Test Step",
            status=JobStatus.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            output={"key": "value"}
        )
        assert result.step_id == "step-1"
        assert result.is_success
        assert result.duration_seconds is not None

    def test_step_result_failed(self):
        """Test failed step result."""
        result = StepResult(
            step_id="step-2",
            step_name="Failed Step",
            status=JobStatus.FAILED,
            error="Something went wrong"
        )
        assert not result.is_success
        assert result.error == "Something went wrong"

    def test_job_result_creation(self):
        """Test JobResult dataclass."""
        result = JobResult(
            job_id="job-1",
            plan_id="plan-1",
            backend_type=BackendType.INLINE_LOCAL,
            status=JobStatus.COMPLETED,
            total_steps=5,
            completed_steps=5
        )
        assert result.job_id == "job-1"
        assert result.is_success
        assert result.success_rate == 1.0

    def test_job_result_partial_failure(self):
        """Test job result with partial failures."""
        result = JobResult(
            job_id="job-2",
            plan_id="plan-2",
            backend_type=BackendType.QUEUE_LOCAL,
            status=JobStatus.FAILED,
            total_steps=5,
            completed_steps=3,
            failed_steps=2
        )
        assert not result.is_success
        assert result.success_rate == 0.6


class TestInlineLocalBackend:
    """Tests for InlineLocalBackend."""

    def test_backend_creation(self):
        """Test inline backend creation."""
        backend = InlineLocalBackend()
        assert backend is not None

    def test_backend_capabilities(self):
        """Test inline backend capabilities."""
        backend = InlineLocalBackend()
        caps = backend.get_capabilities()

        assert caps.backend_type == BackendType.INLINE_LOCAL
        assert caps.supports_parallel is False
        assert caps.is_scaffold is False
        assert caps.max_concurrent_jobs == 1

    def test_execute_simple_plan(self):
        """Test executing a simple plan."""
        backend = InlineLocalBackend()

        # Create a simple plan
        plan = ExecutionPlan(
            plan_id="test-plan-1",
            objective="Test objective",
            primary_domain=ExecutionDomain.RESEARCH,
            steps=[
                ExecutionStep(
                    step_id="step-1",
                    description="First step",
                    domain=ExecutionDomain.RESEARCH
                )
            ]
        )

        result = backend.execute(plan)

        assert result.job_id is not None
        assert result.plan_id == "test-plan-1"
        assert result.status == JobStatus.COMPLETED
        assert result.completed_steps == 1

    def test_execute_invalid_plan(self):
        """Test executing invalid input."""
        backend = InlineLocalBackend()
        result = backend.execute("not a plan")

        assert result.status == JobStatus.FAILED
        assert "Invalid plan type" in result.error

    def test_get_status(self):
        """Test getting job status."""
        backend = InlineLocalBackend()

        plan = ExecutionPlan(
            plan_id="test-plan-status",
            objective="Test",
            primary_domain=ExecutionDomain.PLANNING
        )

        result = backend.execute(plan)
        status = backend.get_status(result.job_id)

        assert status is not None
        assert status.job_id == result.job_id


class TestQueueLocalBackend:
    """Tests for QueueLocalBackend."""

    def test_backend_creation(self):
        """Test queue backend creation."""
        backend = QueueLocalBackend(max_workers=2)
        assert backend is not None
        backend.cleanup()

    def test_backend_capabilities(self):
        """Test queue backend capabilities."""
        backend = QueueLocalBackend(max_workers=4)
        caps = backend.get_capabilities()

        assert caps.backend_type == BackendType.QUEUE_LOCAL
        assert caps.supports_parallel is True
        assert caps.max_concurrent_steps == 4
        backend.cleanup()

    def test_execute_plan_sequential(self):
        """Test sequential execution."""
        backend = QueueLocalBackend()

        plan = ExecutionPlan(
            plan_id="test-queue-seq",
            objective="Queue test",
            primary_domain=ExecutionDomain.PRODUCT,
            steps=[
                ExecutionStep(step_id="s1", description="Step 1", domain=ExecutionDomain.PRODUCT),
                ExecutionStep(step_id="s2", description="Step 2", domain=ExecutionDomain.PRODUCT),
            ]
        )

        result = backend.execute(plan, context={"parallel": False})

        assert result.status == JobStatus.COMPLETED
        assert result.completed_steps == 2
        backend.cleanup()

    def test_execute_plan_parallel(self):
        """Test parallel execution."""
        backend = QueueLocalBackend(max_workers=2)

        plan = ExecutionPlan(
            plan_id="test-queue-par",
            objective="Parallel test",
            primary_domain=ExecutionDomain.AUTOMATION,
            steps=[
                ExecutionStep(step_id="p1", description="Par 1", domain=ExecutionDomain.AUTOMATION),
                ExecutionStep(step_id="p2", description="Par 2", domain=ExecutionDomain.AUTOMATION),
            ]
        )

        result = backend.execute(plan, context={"parallel": True})

        assert result.status == JobStatus.COMPLETED
        assert result.completed_steps == 2
        backend.cleanup()


class TestStubContainerBackend:
    """Tests for StubContainerBackend."""

    def test_backend_creation(self):
        """Test container backend scaffold creation."""
        backend = StubContainerBackend(container_runtime="docker")
        assert backend is not None

    def test_is_scaffold(self):
        """Test that container backend is marked as scaffold."""
        backend = StubContainerBackend()
        caps = backend.get_capabilities()

        assert caps.is_scaffold is True
        assert caps.supports_parallel is True

    def test_execute_returns_scaffold_results(self):
        """Test that execution returns scaffold results."""
        backend = StubContainerBackend()

        plan = ExecutionPlan(
            plan_id="container-test",
            objective="Container test",
            primary_domain=ExecutionDomain.VALIDATION,
            steps=[
                ExecutionStep(step_id="c1", description="Container step", domain=ExecutionDomain.VALIDATION)
            ]
        )

        result = backend.execute(plan)

        assert result.status == JobStatus.COMPLETED
        assert result.metadata.get("scaffold") is True
        assert "container" in result.metadata.get("note", "").lower()


class TestStubKubernetesBackend:
    """Tests for StubKubernetesBackend."""

    def test_backend_creation(self):
        """Test Kubernetes backend scaffold creation."""
        backend = StubKubernetesBackend(namespace="test-ns")
        assert backend is not None

    def test_is_scaffold(self):
        """Test that K8s backend is marked as scaffold."""
        backend = StubKubernetesBackend()
        caps = backend.get_capabilities()

        assert caps.is_scaffold is True
        assert caps.max_concurrent_jobs == 100

    def test_execute_returns_k8s_scaffold_results(self):
        """Test that execution returns K8s scaffold results."""
        backend = StubKubernetesBackend(namespace="project-alpha")

        plan = ExecutionPlan(
            plan_id="k8s-test",
            objective="K8s test",
            primary_domain=ExecutionDomain.OPERATIONS,
            steps=[
                ExecutionStep(step_id="k1", description="K8s step", domain=ExecutionDomain.OPERATIONS)
            ]
        )

        result = backend.execute(plan)

        assert result.status == JobStatus.COMPLETED
        assert result.metadata.get("scaffold") is True
        assert result.metadata.get("namespace") == "project-alpha"


class TestBackendFactory:
    """Tests for backend factory functions."""

    def test_get_backend_class(self):
        """Test getting backend class."""
        assert get_backend_class(BackendType.INLINE_LOCAL) == InlineLocalBackend
        assert get_backend_class(BackendType.QUEUE_LOCAL) == QueueLocalBackend

    def test_create_backend(self):
        """Test creating backend instance."""
        backend = create_backend(BackendType.INLINE_LOCAL)
        assert isinstance(backend, InlineLocalBackend)

    def test_list_backends(self):
        """Test listing all backends."""
        backends = list_backends()
        assert len(backends) == 4
        assert any(b["type"] == "inline_local" for b in backends)
        assert any(b["is_scaffold"] for b in backends)


# =============================================================================
# Worker Registry Tests
# =============================================================================

class TestWorkerTypes:
    """Tests for worker type enums."""

    def test_worker_type_values(self):
        """Test worker type enum values."""
        assert WorkerType.GENERAL.value == "general"
        assert WorkerType.RESEARCH.value == "research"
        assert WorkerType.PRODUCT.value == "product"

    def test_worker_status_values(self):
        """Test worker status enum values."""
        assert WorkerStatus.IDLE.value == "idle"
        assert WorkerStatus.BUSY.value == "busy"
        assert WorkerStatus.STOPPED.value == "stopped"


class TestWorkerRegistry:
    """Tests for WorkerRegistry."""

    def test_registry_creation(self):
        """Test registry creation."""
        registry = WorkerRegistry()
        assert registry is not None
        assert not registry.is_loaded

    def test_load_default_workers(self):
        """Test loading default worker definitions."""
        registry = WorkerRegistry()
        success = registry.load()

        assert success
        assert registry.is_loaded

    def test_get_definition(self):
        """Test getting worker definition."""
        registry = WorkerRegistry()
        registry.load()

        definition = registry.get_definition(WorkerType.GENERAL)
        assert definition is not None
        assert definition.worker_type == WorkerType.GENERAL

    def test_get_worker_for_domain(self):
        """Test finding worker for domain."""
        registry = WorkerRegistry()
        registry.load()

        worker_type = registry.get_worker_for_domain("research")
        assert worker_type == WorkerType.RESEARCH

        # Unknown domain falls back to general
        worker_type = registry.get_worker_for_domain("unknown")
        assert worker_type == WorkerType.GENERAL

    def test_spawn_instance(self):
        """Test spawning worker instance."""
        registry = WorkerRegistry()
        registry.load()

        instance = registry.spawn_instance(WorkerType.RESEARCH)

        assert instance is not None
        assert instance.worker_type == WorkerType.RESEARCH
        assert instance.is_available

    def test_update_instance_status(self):
        """Test updating worker status."""
        registry = WorkerRegistry()
        registry.load()

        instance = registry.spawn_instance(WorkerType.PLANNING)
        success = registry.update_instance_status(
            instance.instance_id, WorkerStatus.BUSY, "step-123"
        )

        assert success
        updated = registry.get_instance(instance.instance_id)
        assert updated.status == WorkerStatus.BUSY
        assert updated.current_step_id == "step-123"

    def test_list_instances(self):
        """Test listing instances."""
        registry = WorkerRegistry()
        registry.load()

        registry.spawn_instance(WorkerType.RESEARCH)
        registry.spawn_instance(WorkerType.PLANNING)

        all_instances = registry.list_instances()
        assert len(all_instances) == 2

        research_only = registry.list_instances(worker_type=WorkerType.RESEARCH)
        assert len(research_only) == 1

    def test_get_stats(self):
        """Test getting registry stats."""
        registry = WorkerRegistry()
        registry.load()

        registry.spawn_instance(WorkerType.GENERAL)
        stats = registry.get_stats()

        assert stats["total_instances"] == 1
        assert "by_type" in stats


class TestWorkerRegistrySingleton:
    """Tests for worker registry singleton."""

    def test_get_worker_registry(self):
        """Test getting global registry."""
        registry = get_worker_registry()
        assert registry is not None

    def test_get_worker_for_domain_function(self):
        """Test standalone function."""
        worker_type = get_worker_for_domain("operations")
        assert worker_type in [WorkerType.OPERATIONS, WorkerType.GENERAL]


# =============================================================================
# Job Dispatcher Tests
# =============================================================================

class TestDispatchOptions:
    """Tests for dispatch options."""

    def test_default_options(self):
        """Test default dispatch options."""
        options = DispatchOptions()

        assert options.strategy == DispatchStrategy.IMMEDIATE
        assert options.priority == DispatchPriority.NORMAL
        assert options.stop_on_failure is True

    def test_custom_options(self):
        """Test custom dispatch options."""
        options = DispatchOptions(
            strategy=DispatchStrategy.QUEUED,
            priority=DispatchPriority.HIGH,
            max_retries=3
        )

        assert options.strategy == DispatchStrategy.QUEUED
        assert options.max_retries == 3


class TestJobDispatcher:
    """Tests for JobDispatcher."""

    def test_dispatcher_creation(self):
        """Test dispatcher creation."""
        dispatcher = JobDispatcher()
        assert dispatcher is not None

    def test_register_backend(self):
        """Test registering backend."""
        dispatcher = JobDispatcher()
        backend = InlineLocalBackend()

        dispatcher.register_backend(backend)

        assert BackendType.INLINE_LOCAL in dispatcher.list_backends()

    def test_dispatch_plan(self):
        """Test dispatching a plan."""
        dispatcher = JobDispatcher()
        backend = InlineLocalBackend()
        dispatcher.register_backend(backend)

        plan = ExecutionPlan(
            plan_id="dispatch-test",
            objective="Dispatch test",
            primary_domain=ExecutionDomain.CONTENT
        )

        dispatched = dispatcher.dispatch(plan, BackendType.INLINE_LOCAL)

        assert dispatched.job_id is not None
        assert dispatched.status == JobStatus.COMPLETED

    def test_dispatch_without_backend(self):
        """Test dispatching without registered backend."""
        dispatcher = JobDispatcher()

        plan = ExecutionPlan(
            plan_id="no-backend-test",
            objective="No backend",
            primary_domain=ExecutionDomain.GROWTH
        )

        dispatched = dispatcher.dispatch(plan, BackendType.INLINE_LOCAL)

        assert dispatched.status == JobStatus.FAILED
        assert "not registered" in dispatched.error

    def test_get_job(self):
        """Test getting dispatched job."""
        dispatcher = JobDispatcher()
        dispatcher.register_backend(InlineLocalBackend())

        plan = ExecutionPlan(
            plan_id="get-job-test",
            objective="Get job",
            primary_domain=ExecutionDomain.VALIDATION
        )

        dispatched = dispatcher.dispatch(plan, BackendType.INLINE_LOCAL)
        retrieved = dispatcher.get_job(dispatched.job_id)

        assert retrieved is not None
        assert retrieved.job_id == dispatched.job_id

    def test_list_jobs(self):
        """Test listing jobs."""
        dispatcher = JobDispatcher()
        dispatcher.register_backend(InlineLocalBackend())

        plan1 = ExecutionPlan(plan_id="list-1", objective="Test 1", primary_domain=ExecutionDomain.RESEARCH)
        plan2 = ExecutionPlan(plan_id="list-2", objective="Test 2", primary_domain=ExecutionDomain.PLANNING)

        dispatcher.dispatch(plan1, BackendType.INLINE_LOCAL)
        dispatcher.dispatch(plan2, BackendType.INLINE_LOCAL)

        all_jobs = dispatcher.list_jobs()
        assert len(all_jobs) == 2

    def test_get_stats(self):
        """Test getting dispatcher stats."""
        dispatcher = JobDispatcher()
        dispatcher.register_backend(InlineLocalBackend())

        plan = ExecutionPlan(plan_id="stats-test", objective="Stats", primary_domain=ExecutionDomain.AUTOMATION)
        dispatcher.dispatch(plan, BackendType.INLINE_LOCAL)

        stats = dispatcher.get_stats()
        assert stats["total_jobs"] == 1
        assert stats["registered_backends"] == 1


# =============================================================================
# Runtime Manager Tests
# =============================================================================

class TestRuntimeConfig:
    """Tests for runtime configuration."""

    def test_default_config(self):
        """Test default runtime config."""
        config = RuntimeConfig()

        assert config.default_backend == BackendType.INLINE_LOCAL
        assert config.selection_strategy == BackendSelectionStrategy.AUTO
        assert config.enable_workers is True

    def test_custom_config(self):
        """Test custom config."""
        config = RuntimeConfig(
            default_backend=BackendType.QUEUE_LOCAL,
            parallel_threshold=5
        )

        assert config.default_backend == BackendType.QUEUE_LOCAL
        assert config.parallel_threshold == 5


class TestRuntimeManager:
    """Tests for RuntimeManager."""

    def test_manager_creation(self):
        """Test runtime manager creation."""
        manager = RuntimeManager()
        assert manager is not None
        assert not manager.is_initialized

    def test_initialize(self):
        """Test runtime initialization."""
        manager = RuntimeManager()
        success = manager.initialize()

        assert success
        assert manager.is_initialized

    def test_select_backend_auto(self):
        """Test automatic backend selection."""
        manager = RuntimeManager()
        manager.initialize()

        # Small plan -> inline
        small_plan = ExecutionPlan(
            plan_id="small",
            objective="Small plan",
            primary_domain=ExecutionDomain.RESEARCH,
            steps=[ExecutionStep(step_id="s1", description="Step", domain=ExecutionDomain.RESEARCH)]
        )

        selected = manager.select_backend(small_plan)
        assert selected == BackendType.INLINE_LOCAL

        # Large plan -> queue
        large_plan = ExecutionPlan(
            plan_id="large",
            objective="Large plan",
            primary_domain=ExecutionDomain.PRODUCT,
            steps=[
                ExecutionStep(step_id=f"s{i}", description=f"Step {i}", domain=ExecutionDomain.PRODUCT)
                for i in range(5)
            ]
        )

        selected = manager.select_backend(large_plan)
        assert selected == BackendType.QUEUE_LOCAL

    def test_select_backend_explicit(self):
        """Test explicit backend selection."""
        manager = RuntimeManager()
        manager.initialize()

        plan = ExecutionPlan(plan_id="explicit", objective="Test", primary_domain=ExecutionDomain.VALIDATION)

        selected = manager.select_backend(plan, explicit_backend=BackendType.CONTAINER)
        assert selected == BackendType.CONTAINER

    def test_execute_plan(self):
        """Test executing a plan."""
        manager = RuntimeManager()
        manager.initialize()

        plan = ExecutionPlan(
            plan_id="execute-test",
            objective="Execute test",
            primary_domain=ExecutionDomain.OPERATIONS,
            steps=[ExecutionStep(step_id="e1", description="Execute", domain=ExecutionDomain.OPERATIONS)]
        )

        result = manager.execute(plan)

        assert result.success
        assert result.plan_id == "execute-test"
        assert result.execution_time_seconds is not None

    def test_execute_with_specific_backend(self):
        """Test executing with specific backend."""
        manager = RuntimeManager()
        manager.initialize()

        plan = ExecutionPlan(
            plan_id="specific-backend",
            objective="Specific test",
            primary_domain=ExecutionDomain.CONTENT
        )

        result = manager.execute(plan, backend_type=BackendType.QUEUE_LOCAL)

        assert result.backend_type == BackendType.QUEUE_LOCAL

    def test_list_available_backends(self):
        """Test listing available backends."""
        manager = RuntimeManager()
        manager.initialize()

        backends = manager.list_available_backends()

        assert len(backends) == 4
        assert any(b["type"] == "inline_local" for b in backends)
        assert any(b["type"] == "kubernetes" for b in backends)

    def test_get_backend_capabilities(self):
        """Test getting backend capabilities."""
        manager = RuntimeManager()
        manager.initialize()

        caps = manager.get_backend_capabilities(BackendType.INLINE_LOCAL)

        assert caps is not None
        assert caps.backend_type == BackendType.INLINE_LOCAL

    def test_get_stats(self):
        """Test getting runtime stats."""
        manager = RuntimeManager()
        manager.initialize()

        stats = manager.get_stats()

        assert stats["initialized"] is True
        assert "backends" in stats
        assert "config" in stats


class TestRuntimeManagerSingleton:
    """Tests for runtime manager singleton functions."""

    def test_get_runtime_manager(self):
        """Test getting global runtime manager."""
        manager = get_runtime_manager()
        assert manager is not None

    def test_execute_plan_function(self):
        """Test standalone execute function."""
        plan = ExecutionPlan(
            plan_id="standalone-execute",
            objective="Standalone test",
            primary_domain=ExecutionDomain.GROWTH
        )

        result = execute_plan(plan)
        assert result is not None

    def test_get_available_backends_function(self):
        """Test standalone list backends function."""
        backends = get_available_backends()
        assert len(backends) >= 4


# =============================================================================
# Integration Tests
# =============================================================================

class TestRuntimeIntegration:
    """Integration tests for runtime layer."""

    def test_full_execution_flow(self):
        """Test complete execution flow through all layers."""
        # Create plan
        plan = ExecutionPlan(
            plan_id="integration-test",
            objective="Full integration test",
            primary_domain=ExecutionDomain.RESEARCH,
            skill_bundle=SkillBundle(
                skills=["market-research", "competitor-analysis"],
                commands=[],
                specialized_agents=[]
            ),
            steps=[
                ExecutionStep(step_id="i1", description="Research step", domain=ExecutionDomain.RESEARCH),
                ExecutionStep(step_id="i2", description="Analysis step", domain=ExecutionDomain.RESEARCH),
            ]
        )

        # Execute via runtime manager
        manager = RuntimeManager()
        manager.initialize()

        result = manager.execute(plan)

        assert result.success
        assert result.completed_steps == 2
        assert result.job_result is not None

    def test_scaffold_backend_execution(self):
        """Test execution through scaffold backends."""
        plan = ExecutionPlan(
            plan_id="scaffold-test",
            objective="Scaffold backend test",
            primary_domain=ExecutionDomain.AUTOMATION,
            steps=[
                ExecutionStep(step_id="sc1", description="Scaffold step", domain=ExecutionDomain.AUTOMATION)
            ]
        )

        manager = RuntimeManager()
        manager.initialize()

        # Execute on container scaffold
        result = manager.execute(plan, backend_type=BackendType.CONTAINER)

        assert result.success
        assert result.metadata.get("backend_is_scaffold") is True

        # Execute on K8s scaffold
        result = manager.execute(plan, backend_type=BackendType.KUBERNETES)

        assert result.success
        assert result.metadata.get("backend_is_scaffold") is True

    def test_worker_assignment_flow(self):
        """Test worker assignment during execution."""
        registry = WorkerRegistry()
        registry.load()

        # Spawn a worker
        worker = registry.spawn_instance(WorkerType.RESEARCH)
        assert worker.is_available

        # Simulate assignment
        registry.update_instance_status(worker.instance_id, WorkerStatus.BUSY, "step-1")
        assert not registry.get_instance(worker.instance_id).is_available

        # Simulate completion
        registry.record_step_completion(worker.instance_id, success=True)
        registry.update_instance_status(worker.instance_id, WorkerStatus.IDLE)

        updated = registry.get_instance(worker.instance_id)
        assert updated.is_available
        assert updated.completed_steps == 1
