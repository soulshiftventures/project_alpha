"""
Startup Manager for Project Alpha.

Manages system startup, initialization, and first-use setup:
- Clean startup path for full system
- Initialize all required components
- Create necessary directories
- Validate configuration
- Provide guided setup flow

ARCHITECTURE:
- Coordinates startup of all subsystems
- Ensures proper initialization order
- Provides setup guidance for first-time users
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class StartupPhase(Enum):
    """Startup phases."""
    NOT_STARTED = "not_started"
    CHECKING_ENVIRONMENT = "checking_environment"
    CREATING_DIRECTORIES = "creating_directories"
    INITIALIZING_PERSISTENCE = "initializing_persistence"
    INITIALIZING_RUNTIME = "initializing_runtime"
    INITIALIZING_SERVICES = "initializing_services"
    CHECKING_HEALTH = "checking_health"
    COMPLETED = "completed"
    FAILED = "failed"


class SetupStatus(Enum):
    """First-use setup status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NEEDS_CONFIGURATION = "needs_configuration"


@dataclass
class StartupStep:
    """Result of a single startup step."""
    name: str
    phase: StartupPhase
    success: bool
    message: str = ""
    duration_ms: float = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "phase": self.phase.value,
            "success": self.success,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "details": self.details,
        }


@dataclass
class StartupResult:
    """Complete startup result."""
    success: bool
    phase: StartupPhase
    steps: List[StartupStep] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_duration_ms: float = 0
    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "phase": self.phase.value,
            "steps": [s.to_dict() for s in self.steps],
            "errors": self.errors,
            "warnings": self.warnings,
            "total_duration_ms": self.total_duration_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class SetupChecklist:
    """First-use setup checklist."""
    status: SetupStatus
    items: List[Dict[str, Any]] = field(default_factory=list)
    completed_count: int = 0
    total_count: int = 0
    next_step: Optional[str] = None
    instructions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "items": self.items,
            "completed_count": self.completed_count,
            "total_count": self.total_count,
            "next_step": self.next_step,
            "instructions": self.instructions,
        }


class StartupManager:
    """
    Central startup manager for Project Alpha.

    Coordinates system startup and provides guided setup.
    """

    # Required directories to create
    REQUIRED_DIRS = [
        "project_alpha/data",
    ]

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the startup manager.

        Args:
            project_root: Root directory of the project.
        """
        self._project_root = project_root or self._detect_project_root()
        self._startup_result: Optional[StartupResult] = None
        self._is_started = False

    def _detect_project_root(self) -> str:
        """Detect the project root directory."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)

        if os.path.exists(os.path.join(parent_dir, "core")) and \
           os.path.exists(os.path.join(parent_dir, "ui")):
            return parent_dir

        return os.getcwd()

    def startup(self, skip_health_check: bool = False) -> StartupResult:
        """
        Run full system startup.

        Args:
            skip_health_check: Skip final health check if True

        Returns:
            Complete startup result
        """
        import time
        start_time = time.time()

        steps = []
        errors = []
        warnings = []
        current_phase = StartupPhase.NOT_STARTED

        # Phase 1: Check environment
        current_phase = StartupPhase.CHECKING_ENVIRONMENT
        step = self._check_environment()
        steps.append(step)
        if not step.success:
            errors.extend(step.details.get("errors", []))

        # Phase 2: Create directories
        current_phase = StartupPhase.CREATING_DIRECTORIES
        step = self._create_directories()
        steps.append(step)
        if not step.success:
            errors.append(step.message)

        # Phase 3: Initialize persistence
        current_phase = StartupPhase.INITIALIZING_PERSISTENCE
        step = self._initialize_persistence()
        steps.append(step)
        if not step.success:
            warnings.append(f"Persistence: {step.message}")

        # Phase 4: Initialize runtime
        current_phase = StartupPhase.INITIALIZING_RUNTIME
        step = self._initialize_runtime()
        steps.append(step)
        if not step.success:
            errors.append(step.message)
            # Runtime is critical, stop here
            return StartupResult(
                success=False,
                phase=StartupPhase.FAILED,
                steps=steps,
                errors=errors,
                warnings=warnings,
                total_duration_ms=(time.time() - start_time) * 1000,
            )

        # Phase 5: Initialize services
        current_phase = StartupPhase.INITIALIZING_SERVICES
        step = self._initialize_services()
        steps.append(step)
        if not step.success:
            warnings.append(f"Services: {step.message}")

        # Phase 6: Health check
        if not skip_health_check:
            current_phase = StartupPhase.CHECKING_HEALTH
            step = self._run_health_check()
            steps.append(step)
            if not step.success:
                warnings.append(f"Health: {step.message}")

        # Determine overall success
        critical_failures = [s for s in steps if not s.success and s.phase in (
            StartupPhase.CHECKING_ENVIRONMENT,
            StartupPhase.INITIALIZING_RUNTIME,
        )]

        success = len(critical_failures) == 0
        final_phase = StartupPhase.COMPLETED if success else StartupPhase.FAILED

        self._startup_result = StartupResult(
            success=success,
            phase=final_phase,
            steps=steps,
            errors=errors,
            warnings=warnings,
            total_duration_ms=(time.time() - start_time) * 1000,
        )

        self._is_started = success
        return self._startup_result

    def _check_environment(self) -> StartupStep:
        """Check environment readiness."""
        import time
        start = time.time()

        try:
            from core.readiness_checker import get_readiness_checker

            checker = get_readiness_checker(self._project_root)
            report = checker.check_all()

            duration = (time.time() - start) * 1000

            if report.dry_run_ready:
                return StartupStep(
                    name="check_environment",
                    phase=StartupPhase.CHECKING_ENVIRONMENT,
                    success=True,
                    message=f"Environment ready ({report.overall_status.value})",
                    duration_ms=duration,
                    details={
                        "status": report.overall_status.value,
                        "dry_run_ready": report.dry_run_ready,
                        "live_ready": report.live_ready,
                    },
                )
            else:
                return StartupStep(
                    name="check_environment",
                    phase=StartupPhase.CHECKING_ENVIRONMENT,
                    success=False,
                    message=f"Environment not ready: {', '.join(report.missing_required)}",
                    duration_ms=duration,
                    details={
                        "status": report.overall_status.value,
                        "missing": report.missing_required,
                        "errors": report.missing_required,
                    },
                )
        except Exception as e:
            return StartupStep(
                name="check_environment",
                phase=StartupPhase.CHECKING_ENVIRONMENT,
                success=False,
                message=f"Environment check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _create_directories(self) -> StartupStep:
        """Create required directories."""
        import time
        start = time.time()

        created = []
        errors = []

        for dir_path in self.REQUIRED_DIRS:
            full_path = os.path.join(self._project_root, dir_path)
            if not os.path.exists(full_path):
                try:
                    os.makedirs(full_path, exist_ok=True)
                    created.append(dir_path)
                except Exception as e:
                    errors.append(f"Failed to create {dir_path}: {str(e)}")

        duration = (time.time() - start) * 1000

        if errors:
            return StartupStep(
                name="create_directories",
                phase=StartupPhase.CREATING_DIRECTORIES,
                success=False,
                message=f"Failed to create directories: {', '.join(errors)}",
                duration_ms=duration,
                details={"created": created, "errors": errors},
            )

        return StartupStep(
            name="create_directories",
            phase=StartupPhase.CREATING_DIRECTORIES,
            success=True,
            message=f"Created {len(created)} directories" if created else "All directories exist",
            duration_ms=duration,
            details={"created": created},
        )

    def _initialize_persistence(self) -> StartupStep:
        """Initialize persistence layer."""
        import time
        start = time.time()

        try:
            from core.persistence_manager import get_persistence_manager

            pm = get_persistence_manager()
            if not pm._initialized:
                pm.initialize()

            duration = (time.time() - start) * 1000

            return StartupStep(
                name="initialize_persistence",
                phase=StartupPhase.INITIALIZING_PERSISTENCE,
                success=True,
                message="Persistence initialized",
                duration_ms=duration,
                details={"enabled": pm.is_persistence_enabled},
            )
        except Exception as e:
            return StartupStep(
                name="initialize_persistence",
                phase=StartupPhase.INITIALIZING_PERSISTENCE,
                success=False,
                message=f"Persistence initialization failed: {str(e)}",
                details={"error": str(e)},
            )

    def _initialize_runtime(self) -> StartupStep:
        """Initialize runtime backends."""
        import time
        start = time.time()

        try:
            from core.runtime_manager import get_runtime_manager

            rm = get_runtime_manager()
            if not rm.is_initialized:
                rm.initialize()

            backends = rm.list_available_backends()
            duration = (time.time() - start) * 1000

            return StartupStep(
                name="initialize_runtime",
                phase=StartupPhase.INITIALIZING_RUNTIME,
                success=True,
                message=f"Runtime initialized with {len(backends)} backends",
                duration_ms=duration,
                details={
                    "initialized": True,
                    "backends": [b["type"] for b in backends],
                },
            )
        except Exception as e:
            return StartupStep(
                name="initialize_runtime",
                phase=StartupPhase.INITIALIZING_RUNTIME,
                success=False,
                message=f"Runtime initialization failed: {str(e)}",
                details={"error": str(e)},
            )

    def _initialize_services(self) -> StartupStep:
        """Initialize service layer."""
        import time
        start = time.time()

        try:
            from ui.services import get_operator_service

            service = get_operator_service()
            service._ensure_initialized()
            duration = (time.time() - start) * 1000

            return StartupStep(
                name="initialize_services",
                phase=StartupPhase.INITIALIZING_SERVICES,
                success=True,
                message="Services initialized",
                duration_ms=duration,
                details={"initialized": True},
            )
        except Exception as e:
            return StartupStep(
                name="initialize_services",
                phase=StartupPhase.INITIALIZING_SERVICES,
                success=False,
                message=f"Service initialization failed: {str(e)}",
                details={"error": str(e)},
            )

    def _run_health_check(self) -> StartupStep:
        """Run health check after startup."""
        import time
        start = time.time()

        try:
            from core.health_monitor import get_health_monitor, HealthStatus

            monitor = get_health_monitor()
            health = monitor.check_all()
            duration = (time.time() - start) * 1000

            success = health.overall_status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)

            return StartupStep(
                name="health_check",
                phase=StartupPhase.CHECKING_HEALTH,
                success=success,
                message=f"Health check: {health.overall_status.value}",
                duration_ms=duration,
                details={
                    "status": health.overall_status.value,
                    "healthy": health.healthy_count,
                    "degraded": health.degraded_count,
                    "unhealthy": health.unhealthy_count,
                },
            )
        except Exception as e:
            return StartupStep(
                name="health_check",
                phase=StartupPhase.CHECKING_HEALTH,
                success=False,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e)},
            )

    def get_setup_checklist(self) -> SetupChecklist:
        """
        Get first-use setup checklist.

        Returns:
            Setup checklist with status and instructions
        """
        items = []
        completed = 0

        # Check 1: Data directory
        data_dir = os.path.join(self._project_root, "project_alpha/data")
        data_exists = os.path.isdir(data_dir)
        items.append({
            "name": "data_directory",
            "label": "Data directory exists",
            "completed": data_exists,
            "required": True,
            "action": "mkdir -p project_alpha/data" if not data_exists else None,
        })
        if data_exists:
            completed += 1

        # Check 2: Database initialized
        db_exists = os.path.isfile(os.path.join(data_dir, "state.db"))
        items.append({
            "name": "database",
            "label": "Database initialized",
            "completed": db_exists,
            "required": False,
            "action": "Run the system once to initialize" if not db_exists else None,
        })
        if db_exists:
            completed += 1

        # Check 3: Flask available
        try:
            import flask
            flask_ok = True
        except ImportError:
            flask_ok = False
        items.append({
            "name": "flask",
            "label": "Flask installed",
            "completed": flask_ok,
            "required": True,
            "action": "pip install flask" if not flask_ok else None,
        })
        if flask_ok:
            completed += 1

        # Check 4: httpx available (for live execution)
        try:
            import httpx
            httpx_ok = True
        except ImportError:
            httpx_ok = False
        items.append({
            "name": "httpx",
            "label": "httpx installed (for live execution)",
            "completed": httpx_ok,
            "required": False,
            "action": "pip install httpx" if not httpx_ok else None,
        })
        if httpx_ok:
            completed += 1

        # Check 5: At least one connector configured
        connector_configured = False
        from core.readiness_checker import ReadinessChecker
        for connector, creds in ReadinessChecker.CONNECTOR_CREDENTIALS.items():
            if all(os.environ.get(c, "").strip() for c in creds):
                connector_configured = True
                break
        items.append({
            "name": "connector_credentials",
            "label": "At least one connector configured",
            "completed": connector_configured,
            "required": False,
            "action": "Configure credentials in .env (copy from .env.example)" if not connector_configured else None,
        })
        if connector_configured:
            completed += 1

        # Determine status
        required_complete = all(
            item["completed"] for item in items if item["required"]
        )

        if completed == len(items):
            status = SetupStatus.COMPLETED
            next_step = None
        elif required_complete:
            status = SetupStatus.NEEDS_CONFIGURATION
            next_step = next(
                (item["name"] for item in items if not item["completed"]),
                None
            )
        else:
            status = SetupStatus.IN_PROGRESS
            next_step = next(
                (item["name"] for item in items if item["required"] and not item["completed"]),
                None
            )

        # Generate instructions
        instructions = [
            "1. Ensure all required items are completed",
            "2. Copy .env.example to .env and configure credentials",
            "3. Run ./run_ui.sh to start the operator interface",
            "4. Visit http://localhost:5000 to access the dashboard",
        ]

        return SetupChecklist(
            status=status,
            items=items,
            completed_count=completed,
            total_count=len(items),
            next_step=next_step,
            instructions=instructions,
        )

    def get_startup_instructions(self) -> List[str]:
        """Get operator startup instructions."""
        return [
            "# Project Alpha Startup Instructions",
            "",
            "## Quick Start",
            "1. Run: ./run_full.sh",
            "   - This checks readiness and starts the UI",
            "",
            "## Manual Start",
            "1. Check readiness: ./check_ready.sh",
            "2. Start UI: ./run_ui.sh",
            "",
            "## First-Time Setup",
            "1. Create data directory: mkdir -p project_alpha/data",
            "2. Copy environment template: cp .env.example .env",
            "3. Edit .env with your credentials",
            "4. Install dependencies: pip install flask httpx",
            "5. Run: ./run_full.sh",
            "",
            "## Verification",
            "- Run: ./verify.sh",
            "- Run: PYTHONPATH=. pytest -q",
            "",
            "## Access",
            "- UI: http://localhost:5000",
            "- Readiness: http://localhost:5000/readiness",
            "- Health: http://localhost:5000/health",
        ]

    @property
    def is_started(self) -> bool:
        """Check if system has been started successfully."""
        return self._is_started

    def get_last_startup(self) -> Optional[StartupResult]:
        """Get the last startup result."""
        return self._startup_result


# Singleton instance
_startup_manager: Optional[StartupManager] = None


def get_startup_manager(project_root: Optional[str] = None) -> StartupManager:
    """Get the global startup manager instance."""
    global _startup_manager
    if _startup_manager is None:
        _startup_manager = StartupManager(project_root)
    return _startup_manager


def run_startup(skip_health_check: bool = False) -> StartupResult:
    """Convenience function to run system startup."""
    return get_startup_manager().startup(skip_health_check)


def get_setup_checklist() -> SetupChecklist:
    """Convenience function to get setup checklist."""
    return get_startup_manager().get_setup_checklist()
