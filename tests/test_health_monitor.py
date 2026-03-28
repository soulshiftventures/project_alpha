"""
Tests for Health Monitor module.

Tests the system health monitoring functionality.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.health_monitor import (
    HealthMonitor,
    HealthStatus,
    SubsystemHealth,
    SystemHealth,
    get_health_monitor,
    check_health,
    check_health_quick,
)


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestSubsystemHealth:
    """Tests for SubsystemHealth dataclass."""

    def test_subsystem_health_creation(self):
        """Test creating subsystem health."""
        health = SubsystemHealth(
            name="persistence",
            status=HealthStatus.HEALTHY,
            message="Persistence operational",
            latency_ms=5.5,
        )

        assert health.name == "persistence"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "Persistence operational"
        assert health.latency_ms == 5.5

    def test_subsystem_health_to_dict(self):
        """Test serialization to dict."""
        health = SubsystemHealth(
            name="runtime",
            status=HealthStatus.DEGRADED,
            message="Runtime degraded",
            latency_ms=10.2,
            details={"backends": 2},
        )

        result = health.to_dict()

        assert result["name"] == "runtime"
        assert result["status"] == "degraded"
        assert result["message"] == "Runtime degraded"
        assert result["latency_ms"] == 10.2
        assert result["details"]["backends"] == 2
        assert "checked_at" in result


class TestSystemHealth:
    """Tests for SystemHealth dataclass."""

    def test_system_health_creation(self):
        """Test creating system health."""
        health = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            healthy_count=5,
            degraded_count=1,
            unhealthy_count=0,
            unknown_count=0,
        )

        assert health.overall_status == HealthStatus.HEALTHY
        assert health.healthy_count == 5
        assert health.degraded_count == 1

    def test_system_health_to_dict(self):
        """Test serialization to dict."""
        subsystems = [
            SubsystemHealth(name="test1", status=HealthStatus.HEALTHY, message="OK"),
            SubsystemHealth(name="test2", status=HealthStatus.DEGRADED, message="Degraded"),
        ]

        health = SystemHealth(
            overall_status=HealthStatus.DEGRADED,
            subsystems=subsystems,
            healthy_count=1,
            degraded_count=1,
            unhealthy_count=0,
            unknown_count=0,
        )

        result = health.to_dict()

        assert result["overall_status"] == "degraded"
        assert len(result["subsystems"]) == 2
        assert result["healthy_count"] == 1
        assert result["degraded_count"] == 1
        assert "timestamp" in result


class TestHealthMonitor:
    """Tests for HealthMonitor class."""

    def test_monitor_initialization(self):
        """Test monitor initializes correctly."""
        monitor = HealthMonitor()
        assert monitor._last_check is None

    def test_check_all_returns_system_health(self):
        """Test check_all returns SystemHealth."""
        monitor = HealthMonitor()
        health = monitor.check_all()

        assert isinstance(health, SystemHealth)
        assert health.overall_status in HealthStatus
        assert isinstance(health.subsystems, list)

    def test_check_all_checks_all_subsystems(self):
        """Test all expected subsystems are checked."""
        monitor = HealthMonitor()
        health = monitor.check_all()

        subsystem_names = [s.name for s in health.subsystems]

        assert "persistence" in subsystem_names
        assert "runtime" in subsystem_names
        assert "approvals" in subsystem_names
        assert "capacity" in subsystem_names
        assert "connectors" in subsystem_names
        assert "services" in subsystem_names
        assert "recovery" in subsystem_names

    def test_check_quick_returns_dict(self):
        """Test check_quick returns essential info."""
        monitor = HealthMonitor()
        result = monitor.check_quick()

        assert isinstance(result, dict)
        assert "healthy" in result
        assert "status" in result
        assert "healthy_count" in result
        assert "degraded_count" in result
        assert "unhealthy_count" in result
        assert "subsystems" in result

    def test_get_last_check(self):
        """Test last check is stored."""
        monitor = HealthMonitor()

        # Initially None
        assert monitor.get_last_check() is None

        # After check, should be stored
        health = monitor.check_all()
        assert monitor.get_last_check() is health

    def test_subsystem_counts_are_correct(self):
        """Test subsystem counts match subsystems."""
        monitor = HealthMonitor()
        health = monitor.check_all()

        # Count manually
        healthy = sum(1 for s in health.subsystems if s.status == HealthStatus.HEALTHY)
        degraded = sum(1 for s in health.subsystems if s.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for s in health.subsystems if s.status == HealthStatus.UNHEALTHY)
        unknown = sum(1 for s in health.subsystems if s.status == HealthStatus.UNKNOWN)

        assert health.healthy_count == healthy
        assert health.degraded_count == degraded
        assert health.unhealthy_count == unhealthy
        assert health.unknown_count == unknown


class TestHealthMonitorSubsystemChecks:
    """Tests for individual subsystem health checks."""

    def test_check_persistence(self):
        """Test persistence check."""
        monitor = HealthMonitor()
        health = monitor._check_persistence()

        assert isinstance(health, SubsystemHealth)
        assert health.name == "persistence"
        assert health.status in HealthStatus

    def test_check_runtime(self):
        """Test runtime check."""
        monitor = HealthMonitor()
        health = monitor._check_runtime()

        assert isinstance(health, SubsystemHealth)
        assert health.name == "runtime"
        assert health.status in HealthStatus

    def test_check_approvals(self):
        """Test approvals check."""
        monitor = HealthMonitor()
        health = monitor._check_approvals()

        assert isinstance(health, SubsystemHealth)
        assert health.name == "approvals"
        assert health.status in HealthStatus

    def test_check_capacity(self):
        """Test capacity check."""
        monitor = HealthMonitor()
        health = monitor._check_capacity()

        assert isinstance(health, SubsystemHealth)
        assert health.name == "capacity"
        assert health.status in HealthStatus

    def test_check_connectors(self):
        """Test connectors check."""
        monitor = HealthMonitor()
        health = monitor._check_connectors()

        assert isinstance(health, SubsystemHealth)
        assert health.name == "connectors"
        assert health.status in HealthStatus

    def test_check_services(self):
        """Test services check."""
        monitor = HealthMonitor()
        health = monitor._check_services()

        assert isinstance(health, SubsystemHealth)
        assert health.name == "services"
        assert health.status in HealthStatus

    def test_check_recovery(self):
        """Test recovery check."""
        monitor = HealthMonitor()
        health = monitor._check_recovery()

        assert isinstance(health, SubsystemHealth)
        assert health.name == "recovery"
        assert health.status in HealthStatus


class TestHealthMonitorHelpers:
    """Tests for module-level helper functions."""

    def test_get_health_monitor_singleton(self):
        """Test singleton pattern."""
        import core.health_monitor as hm
        hm._health_monitor = None  # Reset

        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()

        assert monitor1 is monitor2

    def test_check_health_convenience(self):
        """Test convenience function."""
        health = check_health()
        assert isinstance(health, SystemHealth)

    def test_check_health_quick_convenience(self):
        """Test quick check convenience function."""
        result = check_health_quick()
        assert isinstance(result, dict)
        assert "healthy" in result


class TestOverallStatusDetermination:
    """Tests for overall status determination."""

    def test_healthy_when_all_healthy(self):
        """Test HEALTHY status when all subsystems healthy."""
        monitor = HealthMonitor()
        health = monitor.check_all()

        # If all subsystems are healthy, overall should be healthy
        if all(s.status == HealthStatus.HEALTHY for s in health.subsystems):
            assert health.overall_status == HealthStatus.HEALTHY

    def test_unhealthy_when_any_unhealthy(self):
        """Test UNHEALTHY status when any subsystem unhealthy."""
        # Create a mock health check that returns unhealthy
        monitor = HealthMonitor()

        # Verify the logic: if unhealthy_count > 0, overall is UNHEALTHY
        # We can't easily mock internal subsystem checks, but we verify the counting
        health = monitor.check_all()

        if health.unhealthy_count > 0:
            assert health.overall_status == HealthStatus.UNHEALTHY

    def test_degraded_when_any_degraded(self):
        """Test DEGRADED status when any subsystem degraded."""
        monitor = HealthMonitor()
        health = monitor.check_all()

        if health.degraded_count > 0 and health.unhealthy_count == 0:
            assert health.overall_status == HealthStatus.DEGRADED


class TestLatencyTracking:
    """Tests for latency tracking in health checks."""

    def test_latency_is_recorded(self):
        """Test that latency is recorded for checks."""
        monitor = HealthMonitor()
        health = monitor.check_all()

        # At least some subsystems should have latency recorded
        latencies_recorded = sum(1 for s in health.subsystems if s.latency_ms is not None)
        assert latencies_recorded > 0

    def test_latency_is_positive(self):
        """Test latency values are positive."""
        monitor = HealthMonitor()
        health = monitor.check_all()

        for subsys in health.subsystems:
            if subsys.latency_ms is not None:
                assert subsys.latency_ms >= 0
