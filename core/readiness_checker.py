"""
Readiness Checker for Project Alpha.

Verifies system readiness for operation:
- Required files and directories
- Database availability
- Credential/config completeness by connector
- Dry-run vs live readiness
- Runtime/backend readiness

SECURITY:
- Never exposes secret values
- Reports missing pieces without revealing sensitive data
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class ReadinessStatus(Enum):
    """Overall readiness status."""
    READY = "ready"
    PARTIAL = "partial"
    NOT_READY = "not_ready"
    ERROR = "error"


class ComponentStatus(Enum):
    """Individual component status."""
    OK = "ok"
    MISSING = "missing"
    UNCONFIGURED = "unconfigured"
    DEGRADED = "degraded"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ComponentCheck:
    """Result of checking a single component."""
    name: str
    status: ComponentStatus
    message: str = ""
    required: bool = True
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "required": self.required,
            "details": self.details,
        }


@dataclass
class ConnectorReadiness:
    """Readiness status for a specific connector."""
    name: str
    status: ComponentStatus
    dry_run_ready: bool = True
    live_ready: bool = False
    missing_credentials: List[str] = field(default_factory=list)
    missing_config: List[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "dry_run_ready": self.dry_run_ready,
            "live_ready": self.live_ready,
            "missing_credentials": self.missing_credentials,
            "missing_config": self.missing_config,
            "message": self.message,
        }


@dataclass
class ReadinessReport:
    """Complete system readiness report."""
    overall_status: ReadinessStatus
    dry_run_ready: bool = True
    live_ready: bool = False
    components: List[ComponentCheck] = field(default_factory=list)
    connectors: List[ConnectorReadiness] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "dry_run_ready": self.dry_run_ready,
            "live_ready": self.live_ready,
            "components": [c.to_dict() for c in self.components],
            "connectors": [c.to_dict() for c in self.connectors],
            "missing_required": self.missing_required,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
        }


class ReadinessChecker:
    """
    Central readiness checker for Project Alpha.

    Checks all system components and reports readiness status
    without exposing sensitive information.
    """

    # Required directories relative to project root
    REQUIRED_DIRS = [
        "core",
        "ui",
        "integrations",
        "config",
        "project_alpha",
    ]

    # Required files relative to project root
    REQUIRED_FILES = [
        "core/__init__.py",
        "ui/__init__.py",
        "ui/app.py",
        "ui/services.py",
        "integrations/__init__.py",
        "integrations/registry.py",
    ]

    # Optional but recommended directories
    OPTIONAL_DIRS = [
        "project_alpha/data",
        "tests",
        "docs",
    ]

    # Connector credential requirements
    CONNECTOR_CREDENTIALS = {
        "telegram": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
        "tavily": ["TAVILY_API_KEY"],
        "sendgrid": ["SENDGRID_API_KEY"],
        "hubspot": ["HUBSPOT_API_KEY"],
        "firecrawl": ["FIRECRAWL_API_KEY"],
        "apollo": ["APOLLO_API_KEY"],
        "outscraper": ["OUTSCRAPER_API_KEY"],
    }

    # Connectors that support live execution
    LIVE_CAPABLE_CONNECTORS = {
        "telegram", "tavily", "sendgrid", "hubspot", "firecrawl"
    }

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the readiness checker.

        Args:
            project_root: Root directory of the project.
                         If None, attempts to auto-detect.
        """
        self._project_root = project_root or self._detect_project_root()

    def _detect_project_root(self) -> str:
        """Detect the project root directory."""
        # Try to find from current file location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)

        # Verify it looks like project root
        if os.path.exists(os.path.join(parent_dir, "core")) and \
           os.path.exists(os.path.join(parent_dir, "ui")):
            return parent_dir

        # Fallback to current working directory
        return os.getcwd()

    def check_all(self) -> ReadinessReport:
        """
        Run all readiness checks.

        Returns:
            Complete readiness report
        """
        components = []
        connectors = []
        warnings = []
        recommendations = []

        # Check directories
        components.extend(self._check_directories())

        # Check files
        components.extend(self._check_files())

        # Check database
        components.append(self._check_database())

        # Check runtime
        components.append(self._check_runtime())

        # Check Python dependencies
        components.append(self._check_dependencies())

        # Check connectors
        connectors = self._check_connectors()

        # Determine missing required
        missing_required = [
            c.name for c in components
            if c.required and c.status != ComponentStatus.OK
        ]

        # Generate warnings
        for comp in components:
            if comp.status == ComponentStatus.DEGRADED:
                warnings.append(f"{comp.name}: {comp.message}")

        for conn in connectors:
            if conn.missing_credentials:
                warnings.append(
                    f"Connector '{conn.name}' missing credentials for live mode"
                )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            components, connectors, missing_required
        )

        # Determine overall status
        overall_status = self._determine_overall_status(
            components, connectors, missing_required
        )

        # Determine dry-run/live readiness
        dry_run_ready = all(
            c.status in (ComponentStatus.OK, ComponentStatus.DEGRADED, ComponentStatus.NOT_APPLICABLE)
            for c in components if c.required
        )

        live_ready = dry_run_ready and any(
            c.live_ready for c in connectors
        )

        return ReadinessReport(
            overall_status=overall_status,
            dry_run_ready=dry_run_ready,
            live_ready=live_ready,
            components=components,
            connectors=connectors,
            missing_required=missing_required,
            warnings=warnings,
            recommendations=recommendations,
        )

    def _check_directories(self) -> List[ComponentCheck]:
        """Check required directories exist."""
        checks = []

        for dir_name in self.REQUIRED_DIRS:
            dir_path = os.path.join(self._project_root, dir_name)
            if os.path.isdir(dir_path):
                checks.append(ComponentCheck(
                    name=f"dir:{dir_name}",
                    status=ComponentStatus.OK,
                    message=f"Directory exists",
                    required=True,
                ))
            else:
                checks.append(ComponentCheck(
                    name=f"dir:{dir_name}",
                    status=ComponentStatus.MISSING,
                    message=f"Required directory not found: {dir_name}",
                    required=True,
                ))

        for dir_name in self.OPTIONAL_DIRS:
            dir_path = os.path.join(self._project_root, dir_name)
            if os.path.isdir(dir_path):
                checks.append(ComponentCheck(
                    name=f"dir:{dir_name}",
                    status=ComponentStatus.OK,
                    message=f"Optional directory exists",
                    required=False,
                ))
            else:
                checks.append(ComponentCheck(
                    name=f"dir:{dir_name}",
                    status=ComponentStatus.MISSING,
                    message=f"Optional directory not found (will be created if needed)",
                    required=False,
                ))

        return checks

    def _check_files(self) -> List[ComponentCheck]:
        """Check required files exist."""
        checks = []

        for file_name in self.REQUIRED_FILES:
            file_path = os.path.join(self._project_root, file_name)
            if os.path.isfile(file_path):
                checks.append(ComponentCheck(
                    name=f"file:{file_name}",
                    status=ComponentStatus.OK,
                    message=f"File exists",
                    required=True,
                ))
            else:
                checks.append(ComponentCheck(
                    name=f"file:{file_name}",
                    status=ComponentStatus.MISSING,
                    message=f"Required file not found: {file_name}",
                    required=True,
                ))

        return checks

    def _check_database(self) -> ComponentCheck:
        """Check database availability."""
        # Check for data directory
        data_dir = os.path.join(self._project_root, "project_alpha", "data")
        db_path = os.path.join(data_dir, "state.db")

        if os.path.isfile(db_path):
            return ComponentCheck(
                name="database",
                status=ComponentStatus.OK,
                message="Database file exists",
                required=False,
                details={"path": db_path, "exists": True},
            )
        elif os.path.isdir(data_dir):
            return ComponentCheck(
                name="database",
                status=ComponentStatus.DEGRADED,
                message="Data directory exists but no database yet (will be created on first use)",
                required=False,
                details={"path": db_path, "exists": False, "dir_exists": True},
            )
        else:
            return ComponentCheck(
                name="database",
                status=ComponentStatus.DEGRADED,
                message="Data directory not found (will be created on first use)",
                required=False,
                details={"path": db_path, "exists": False, "dir_exists": False},
            )

    def _check_runtime(self) -> ComponentCheck:
        """Check runtime backend readiness."""
        try:
            from core.runtime_manager import get_runtime_manager
            from core.execution_backends import BackendType

            runtime = get_runtime_manager()
            if runtime.is_initialized:
                backends = runtime.list_available_backends()
                return ComponentCheck(
                    name="runtime",
                    status=ComponentStatus.OK,
                    message=f"Runtime initialized with {len(backends)} backends",
                    required=True,
                    details={"initialized": True, "backends": [b["type"] for b in backends]},
                )
            else:
                # Try to initialize
                runtime.initialize()
                backends = runtime.list_available_backends()
                return ComponentCheck(
                    name="runtime",
                    status=ComponentStatus.OK,
                    message=f"Runtime initialized on check with {len(backends)} backends",
                    required=True,
                    details={"initialized": True, "backends": [b["type"] for b in backends]},
                )
        except Exception as e:
            return ComponentCheck(
                name="runtime",
                status=ComponentStatus.ERROR,
                message=f"Runtime check failed: {str(e)}",
                required=True,
                details={"error": str(e)},
            )

    def _check_dependencies(self) -> ComponentCheck:
        """Check Python dependencies."""
        missing = []
        optional_missing = []

        # Required dependencies
        required_deps = ["flask"]
        for dep in required_deps:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)

        # Optional dependencies (for live execution)
        optional_deps = ["httpx"]
        for dep in optional_deps:
            try:
                __import__(dep)
            except ImportError:
                optional_missing.append(dep)

        if missing:
            return ComponentCheck(
                name="dependencies",
                status=ComponentStatus.MISSING,
                message=f"Missing required: {', '.join(missing)}",
                required=True,
                details={"missing_required": missing, "missing_optional": optional_missing},
            )
        elif optional_missing:
            return ComponentCheck(
                name="dependencies",
                status=ComponentStatus.DEGRADED,
                message=f"Optional deps missing (live execution limited): {', '.join(optional_missing)}",
                required=True,
                details={"missing_required": [], "missing_optional": optional_missing},
            )
        else:
            return ComponentCheck(
                name="dependencies",
                status=ComponentStatus.OK,
                message="All dependencies available",
                required=True,
                details={"missing_required": [], "missing_optional": []},
            )

    def _check_connectors(self) -> List[ConnectorReadiness]:
        """Check connector readiness."""
        connectors = []

        for connector_name, cred_vars in self.CONNECTOR_CREDENTIALS.items():
            missing_creds = []
            for var in cred_vars:
                if not os.environ.get(var, "").strip():
                    missing_creds.append(var)

            is_live_capable = connector_name in self.LIVE_CAPABLE_CONNECTORS
            live_ready = is_live_capable and len(missing_creds) == 0

            if missing_creds:
                status = ComponentStatus.UNCONFIGURED
                message = f"Missing credentials for live mode"
            else:
                status = ComponentStatus.OK
                message = "Fully configured" if is_live_capable else "Configured (dry-run only)"

            connectors.append(ConnectorReadiness(
                name=connector_name,
                status=status,
                dry_run_ready=True,  # All connectors support dry-run
                live_ready=live_ready,
                missing_credentials=missing_creds,
                message=message,
            ))

        return connectors

    def _generate_recommendations(
        self,
        components: List[ComponentCheck],
        connectors: List[ConnectorReadiness],
        missing_required: List[str],
    ) -> List[str]:
        """Generate recommendations based on check results."""
        recommendations = []

        if missing_required:
            recommendations.append(
                "Fix required components before running the system"
            )

        # Check for data directory
        data_dir_check = next(
            (c for c in components if c.name == "dir:project_alpha/data"),
            None
        )
        if data_dir_check and data_dir_check.status == ComponentStatus.MISSING:
            recommendations.append(
                "Create data directory: mkdir -p project_alpha/data"
            )

        # Check for optional dependencies
        deps_check = next(
            (c for c in components if c.name == "dependencies"),
            None
        )
        if deps_check and deps_check.details.get("missing_optional"):
            recommendations.append(
                f"Install optional deps for live execution: pip install {' '.join(deps_check.details['missing_optional'])}"
            )

        # Check for unconfigured connectors
        unconfigured = [c for c in connectors if not c.live_ready]
        if unconfigured:
            recommendations.append(
                "Configure connector credentials in .env for live execution"
            )

        if not recommendations:
            recommendations.append("System is ready for operation")

        return recommendations

    def _determine_overall_status(
        self,
        components: List[ComponentCheck],
        connectors: List[ConnectorReadiness],
        missing_required: List[str],
    ) -> ReadinessStatus:
        """Determine overall system readiness status."""
        # Check for errors
        has_errors = any(
            c.status == ComponentStatus.ERROR for c in components
        )
        if has_errors:
            return ReadinessStatus.ERROR

        # Check for missing required
        if missing_required:
            return ReadinessStatus.NOT_READY

        # Check for degraded components
        has_degraded = any(
            c.status == ComponentStatus.DEGRADED for c in components
        )

        # Check for unconfigured connectors
        all_unconfigured = all(
            not c.live_ready for c in connectors
        )

        if has_degraded or all_unconfigured:
            return ReadinessStatus.PARTIAL

        return ReadinessStatus.READY

    def check_quick(self) -> Dict[str, Any]:
        """
        Quick readiness check returning essential status.

        Returns:
            Dict with essential readiness information
        """
        report = self.check_all()

        return {
            "ready": report.overall_status == ReadinessStatus.READY,
            "status": report.overall_status.value,
            "dry_run_ready": report.dry_run_ready,
            "live_ready": report.live_ready,
            "missing_count": len(report.missing_required),
            "warning_count": len(report.warnings),
            "live_connectors": [
                c.name for c in report.connectors if c.live_ready
            ],
        }


# Singleton instance
_readiness_checker: Optional[ReadinessChecker] = None


def get_readiness_checker(project_root: Optional[str] = None) -> ReadinessChecker:
    """Get the global readiness checker instance."""
    global _readiness_checker
    if _readiness_checker is None:
        _readiness_checker = ReadinessChecker(project_root)
    return _readiness_checker


def check_readiness() -> ReadinessReport:
    """Convenience function to check system readiness."""
    return get_readiness_checker().check_all()


def check_readiness_quick() -> Dict[str, Any]:
    """Convenience function for quick readiness check."""
    return get_readiness_checker().check_quick()
