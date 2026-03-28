"""
Health Monitor for Project Alpha.

Monitors health and status of major subsystems:
- Persistence layer
- Runtime backends
- Approval system
- Capacity management
- Connectors
- UI/Service layer

ARCHITECTURE:
- Provides health checks for each subsystem
- Aggregates health into system-wide status
- Does not expose secrets or sensitive data
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class SubsystemHealth:
    """Health status for a single subsystem."""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "details": self.details,
            "checked_at": self.checked_at,
        }


@dataclass
class SystemHealth:
    """Aggregated system health report."""
    overall_status: HealthStatus
    subsystems: List[SubsystemHealth] = field(default_factory=list)
    healthy_count: int = 0
    degraded_count: int = 0
    unhealthy_count: int = 0
    unknown_count: int = 0
    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "subsystems": [s.to_dict() for s in self.subsystems],
            "healthy_count": self.healthy_count,
            "degraded_count": self.degraded_count,
            "unhealthy_count": self.unhealthy_count,
            "unknown_count": self.unknown_count,
            "timestamp": self.timestamp,
        }


class HealthMonitor:
    """
    Central health monitor for Project Alpha.

    Checks health of all major subsystems and provides
    aggregated status reports.
    """

    def __init__(self):
        """Initialize the health monitor."""
        self._last_check: Optional[SystemHealth] = None

    def check_all(self) -> SystemHealth:
        """
        Check health of all subsystems.

        Returns:
            Complete system health report
        """
        import time
        subsystems = []

        # Check each subsystem
        start = time.time()
        subsystems.append(self._check_persistence())
        subsystems.append(self._check_runtime())
        subsystems.append(self._check_approvals())
        subsystems.append(self._check_capacity())
        subsystems.append(self._check_connectors())
        subsystems.append(self._check_services())
        subsystems.append(self._check_recovery())

        # Count statuses
        healthy = sum(1 for s in subsystems if s.status == HealthStatus.HEALTHY)
        degraded = sum(1 for s in subsystems if s.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for s in subsystems if s.status == HealthStatus.UNHEALTHY)
        unknown = sum(1 for s in subsystems if s.status == HealthStatus.UNKNOWN)

        # Determine overall status
        if unhealthy > 0:
            overall = HealthStatus.UNHEALTHY
        elif degraded > 0:
            overall = HealthStatus.DEGRADED
        elif unknown > 0 and healthy == 0:
            overall = HealthStatus.UNKNOWN
        else:
            overall = HealthStatus.HEALTHY

        health = SystemHealth(
            overall_status=overall,
            subsystems=subsystems,
            healthy_count=healthy,
            degraded_count=degraded,
            unhealthy_count=unhealthy,
            unknown_count=unknown,
        )

        self._last_check = health
        return health

    def _check_persistence(self) -> SubsystemHealth:
        """Check persistence layer health."""
        import time
        start = time.time()

        try:
            from core.persistence_manager import get_persistence_manager

            pm = get_persistence_manager()
            latency = (time.time() - start) * 1000

            if pm.is_persistence_enabled:
                return SubsystemHealth(
                    name="persistence",
                    status=HealthStatus.HEALTHY,
                    message="Persistence enabled and operational",
                    latency_ms=latency,
                    details={
                        "enabled": True,
                        "mode": pm._config.mode.value if pm._config else "unknown",
                    },
                )
            else:
                return SubsystemHealth(
                    name="persistence",
                    status=HealthStatus.DEGRADED,
                    message="Persistence disabled (in-memory only)",
                    latency_ms=latency,
                    details={"enabled": False},
                )
        except Exception as e:
            return SubsystemHealth(
                name="persistence",
                status=HealthStatus.UNHEALTHY,
                message=f"Persistence check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _check_runtime(self) -> SubsystemHealth:
        """Check runtime backend health."""
        import time
        start = time.time()

        try:
            from core.runtime_manager import get_runtime_manager

            rm = get_runtime_manager()
            latency = (time.time() - start) * 1000

            if rm.is_initialized:
                backends = rm.list_available_backends()
                return SubsystemHealth(
                    name="runtime",
                    status=HealthStatus.HEALTHY,
                    message=f"{len(backends)} backends available",
                    latency_ms=latency,
                    details={
                        "initialized": True,
                        "backend_count": len(backends),
                        "backends": [b["type"] for b in backends],
                    },
                )
            else:
                return SubsystemHealth(
                    name="runtime",
                    status=HealthStatus.DEGRADED,
                    message="Runtime not initialized",
                    latency_ms=latency,
                    details={"initialized": False},
                )
        except Exception as e:
            return SubsystemHealth(
                name="runtime",
                status=HealthStatus.UNHEALTHY,
                message=f"Runtime check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _check_approvals(self) -> SubsystemHealth:
        """Check approval system health."""
        import time
        start = time.time()

        try:
            from core.approval_manager import ApprovalManager

            am = ApprovalManager()
            pending = am.get_pending()
            latency = (time.time() - start) * 1000

            return SubsystemHealth(
                name="approvals",
                status=HealthStatus.HEALTHY,
                message=f"{len(pending)} pending approvals",
                latency_ms=latency,
                details={
                    "pending_count": len(pending),
                    "operational": True,
                },
            )
        except Exception as e:
            return SubsystemHealth(
                name="approvals",
                status=HealthStatus.UNHEALTHY,
                message=f"Approval check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _check_capacity(self) -> SubsystemHealth:
        """Check capacity management health."""
        import time
        start = time.time()

        try:
            from core.capacity_manager import get_capacity_manager

            cm = get_capacity_manager()
            status = cm.get_status()
            latency = (time.time() - start) * 1000

            utilization = status.get("global_utilization", 0)
            if utilization > 0.9:
                health_status = HealthStatus.DEGRADED
                message = f"High capacity utilization: {utilization:.1%}"
            else:
                health_status = HealthStatus.HEALTHY
                message = f"Capacity utilization: {utilization:.1%}"

            return SubsystemHealth(
                name="capacity",
                status=health_status,
                message=message,
                latency_ms=latency,
                details={
                    "utilization": utilization,
                    "active_reservations": status.get("active_reservations", 0),
                },
            )
        except Exception as e:
            return SubsystemHealth(
                name="capacity",
                status=HealthStatus.UNHEALTHY,
                message=f"Capacity check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _check_connectors(self) -> SubsystemHealth:
        """Check connector registry health."""
        import time
        start = time.time()

        try:
            from integrations.registry import get_connector_registry

            registry = get_connector_registry()
            summary = registry.get_summary()
            latency = (time.time() - start) * 1000

            ready = summary.get("ready", 0)
            total = summary.get("total", 0)
            unconfigured = summary.get("unconfigured", 0)

            if ready == 0 and total > 0:
                health_status = HealthStatus.DEGRADED
                message = f"No connectors ready (0/{total})"
            elif unconfigured > 0:
                health_status = HealthStatus.DEGRADED
                message = f"{ready}/{total} connectors ready, {unconfigured} unconfigured"
            else:
                health_status = HealthStatus.HEALTHY
                message = f"{ready}/{total} connectors ready"

            return SubsystemHealth(
                name="connectors",
                status=health_status,
                message=message,
                latency_ms=latency,
                details={
                    "total": total,
                    "ready": ready,
                    "unconfigured": unconfigured,
                },
            )
        except Exception as e:
            return SubsystemHealth(
                name="connectors",
                status=HealthStatus.UNHEALTHY,
                message=f"Connector check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _check_services(self) -> SubsystemHealth:
        """Check service layer health."""
        import time
        start = time.time()

        try:
            from ui.services import get_operator_service

            service = get_operator_service()
            status = service.get_system_status()
            latency = (time.time() - start) * 1000

            if status.healthy:
                return SubsystemHealth(
                    name="services",
                    status=HealthStatus.HEALTHY,
                    message="Service layer operational",
                    latency_ms=latency,
                    details={
                        "healthy": True,
                        "active_jobs": status.active_jobs,
                        "pending_approvals": status.pending_approvals,
                    },
                )
            else:
                return SubsystemHealth(
                    name="services",
                    status=HealthStatus.DEGRADED,
                    message="Service layer degraded",
                    latency_ms=latency,
                    details={"healthy": False},
                )
        except Exception as e:
            return SubsystemHealth(
                name="services",
                status=HealthStatus.UNHEALTHY,
                message=f"Service check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _check_recovery(self) -> SubsystemHealth:
        """Check recovery manager health."""
        import time
        start = time.time()

        try:
            from core.recovery_manager import get_recovery_manager

            rm = get_recovery_manager()
            paused = rm.get_paused_scenarios()
            failed = rm.get_failed_jobs()
            blockers = rm.get_active_blockers()
            latency = (time.time() - start) * 1000

            if len(blockers) > 5:
                health_status = HealthStatus.DEGRADED
                message = f"Many active blockers: {len(blockers)}"
            else:
                health_status = HealthStatus.HEALTHY
                message = f"Recovery operational"

            return SubsystemHealth(
                name="recovery",
                status=health_status,
                message=message,
                latency_ms=latency,
                details={
                    "paused_scenarios": len(paused),
                    "failed_jobs": len(failed),
                    "active_blockers": len(blockers),
                },
            )
        except Exception as e:
            return SubsystemHealth(
                name="recovery",
                status=HealthStatus.UNHEALTHY,
                message=f"Recovery check failed: {str(e)}",
                details={"error": str(e)},
            )

    def check_quick(self) -> Dict[str, Any]:
        """
        Quick health check returning essential status.

        Returns:
            Dict with essential health information
        """
        health = self.check_all()

        return {
            "healthy": health.overall_status == HealthStatus.HEALTHY,
            "status": health.overall_status.value,
            "healthy_count": health.healthy_count,
            "degraded_count": health.degraded_count,
            "unhealthy_count": health.unhealthy_count,
            "subsystems": {
                s.name: s.status.value for s in health.subsystems
            },
        }

    def get_last_check(self) -> Optional[SystemHealth]:
        """Get the last health check result."""
        return self._last_check


# Singleton instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


def check_health() -> SystemHealth:
    """Convenience function to check system health."""
    return get_health_monitor().check_all()


def check_health_quick() -> Dict[str, Any]:
    """Convenience function for quick health check."""
    return get_health_monitor().check_quick()
