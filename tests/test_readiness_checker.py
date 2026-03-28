"""
Tests for Readiness Checker module.

Tests the system readiness verification functionality.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from core.readiness_checker import (
    ReadinessChecker,
    ReadinessStatus,
    ComponentStatus,
    ComponentCheck,
    ConnectorReadiness,
    ReadinessReport,
    get_readiness_checker,
    check_readiness,
    check_readiness_quick,
)


class TestReadinessStatus:
    """Tests for ReadinessStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert ReadinessStatus.READY.value == "ready"
        assert ReadinessStatus.PARTIAL.value == "partial"
        assert ReadinessStatus.NOT_READY.value == "not_ready"
        assert ReadinessStatus.ERROR.value == "error"


class TestComponentStatus:
    """Tests for ComponentStatus enum."""

    def test_component_status_values(self):
        """Test all component status values exist."""
        assert ComponentStatus.OK.value == "ok"
        assert ComponentStatus.MISSING.value == "missing"
        assert ComponentStatus.UNCONFIGURED.value == "unconfigured"
        assert ComponentStatus.DEGRADED.value == "degraded"
        assert ComponentStatus.ERROR.value == "error"
        assert ComponentStatus.NOT_APPLICABLE.value == "not_applicable"


class TestComponentCheck:
    """Tests for ComponentCheck dataclass."""

    def test_component_check_creation(self):
        """Test creating a component check."""
        check = ComponentCheck(
            name="test_component",
            status=ComponentStatus.OK,
            message="Component is healthy",
            required=True,
        )

        assert check.name == "test_component"
        assert check.status == ComponentStatus.OK
        assert check.message == "Component is healthy"
        assert check.required is True

    def test_component_check_to_dict(self):
        """Test serialization to dict."""
        check = ComponentCheck(
            name="test",
            status=ComponentStatus.DEGRADED,
            message="Degraded state",
            required=False,
            details={"key": "value"},
        )

        result = check.to_dict()

        assert result["name"] == "test"
        assert result["status"] == "degraded"
        assert result["message"] == "Degraded state"
        assert result["required"] is False
        assert result["details"]["key"] == "value"


class TestConnectorReadiness:
    """Tests for ConnectorReadiness dataclass."""

    def test_connector_readiness_creation(self):
        """Test creating connector readiness."""
        readiness = ConnectorReadiness(
            name="telegram",
            status=ComponentStatus.OK,
            dry_run_ready=True,
            live_ready=True,
        )

        assert readiness.name == "telegram"
        assert readiness.live_ready is True
        assert readiness.dry_run_ready is True

    def test_connector_readiness_with_missing_creds(self):
        """Test connector with missing credentials."""
        readiness = ConnectorReadiness(
            name="hubspot",
            status=ComponentStatus.UNCONFIGURED,
            dry_run_ready=True,
            live_ready=False,
            missing_credentials=["HUBSPOT_API_KEY"],
        )

        result = readiness.to_dict()

        assert result["name"] == "hubspot"
        assert result["live_ready"] is False
        assert "HUBSPOT_API_KEY" in result["missing_credentials"]


class TestReadinessReport:
    """Tests for ReadinessReport dataclass."""

    def test_report_creation(self):
        """Test creating a readiness report."""
        report = ReadinessReport(
            overall_status=ReadinessStatus.READY,
            dry_run_ready=True,
            live_ready=True,
        )

        assert report.overall_status == ReadinessStatus.READY
        assert report.dry_run_ready is True
        assert report.live_ready is True

    def test_report_to_dict(self):
        """Test serialization to dict."""
        report = ReadinessReport(
            overall_status=ReadinessStatus.PARTIAL,
            dry_run_ready=True,
            live_ready=False,
            warnings=["Some warning"],
            recommendations=["Some recommendation"],
        )

        result = report.to_dict()

        assert result["overall_status"] == "partial"
        assert result["dry_run_ready"] is True
        assert result["live_ready"] is False
        assert "Some warning" in result["warnings"]
        assert "Some recommendation" in result["recommendations"]


class TestReadinessChecker:
    """Tests for ReadinessChecker class."""

    def test_checker_initialization(self):
        """Test checker initializes correctly."""
        checker = ReadinessChecker()
        assert checker._project_root is not None

    def test_checker_with_custom_root(self):
        """Test checker with custom project root."""
        checker = ReadinessChecker(project_root="/custom/path")
        assert checker._project_root == "/custom/path"

    def test_check_all_returns_report(self):
        """Test check_all returns a report."""
        checker = ReadinessChecker()
        report = checker.check_all()

        assert isinstance(report, ReadinessReport)
        assert report.overall_status in ReadinessStatus
        assert isinstance(report.components, list)
        assert isinstance(report.connectors, list)

    def test_check_quick_returns_dict(self):
        """Test check_quick returns essential info."""
        checker = ReadinessChecker()
        result = checker.check_quick()

        assert isinstance(result, dict)
        assert "ready" in result
        assert "status" in result
        assert "dry_run_ready" in result
        assert "live_ready" in result

    def test_directory_checks(self):
        """Test directory existence checks."""
        checker = ReadinessChecker()
        report = checker.check_all()

        # Find directory checks
        dir_checks = [c for c in report.components if c.name.startswith("dir:")]
        assert len(dir_checks) > 0

        # Core directory should exist
        core_check = next((c for c in dir_checks if "core" in c.name), None)
        assert core_check is not None

    def test_file_checks(self):
        """Test file existence checks."""
        checker = ReadinessChecker()
        report = checker.check_all()

        # Find file checks
        file_checks = [c for c in report.components if c.name.startswith("file:")]
        assert len(file_checks) > 0

    def test_connector_checks(self):
        """Test connector readiness checks."""
        checker = ReadinessChecker()
        report = checker.check_all()

        assert len(report.connectors) > 0

        # All connectors should support dry-run
        for conn in report.connectors:
            assert conn.dry_run_ready is True

    def test_recommendations_generated(self):
        """Test recommendations are generated."""
        checker = ReadinessChecker()
        report = checker.check_all()

        assert isinstance(report.recommendations, list)
        assert len(report.recommendations) > 0

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test", "TELEGRAM_CHAT_ID": "123"})
    def test_connector_with_credentials(self):
        """Test connector with credentials configured."""
        # Reset singleton to pick up new env
        import core.readiness_checker as rc
        rc._readiness_checker = None

        checker = ReadinessChecker()
        report = checker.check_all()

        telegram = next((c for c in report.connectors if c.name == "telegram"), None)
        assert telegram is not None
        assert telegram.live_ready is True


class TestReadinessCheckerHelpers:
    """Tests for module-level helper functions."""

    def test_get_readiness_checker_singleton(self):
        """Test singleton pattern."""
        import core.readiness_checker as rc
        rc._readiness_checker = None  # Reset

        checker1 = get_readiness_checker()
        checker2 = get_readiness_checker()

        assert checker1 is checker2

    def test_check_readiness_convenience(self):
        """Test convenience function."""
        report = check_readiness()
        assert isinstance(report, ReadinessReport)

    def test_check_readiness_quick_convenience(self):
        """Test quick check convenience function."""
        result = check_readiness_quick()
        assert isinstance(result, dict)
        assert "ready" in result


class TestReadinessStatusDetermination:
    """Tests for status determination logic."""

    def test_status_ready_when_all_ok(self):
        """Test READY status when all components OK."""
        checker = ReadinessChecker()

        # Mock components all OK
        components = [
            ComponentCheck(name="test1", status=ComponentStatus.OK, required=True),
            ComponentCheck(name="test2", status=ComponentStatus.OK, required=True),
        ]

        # Mock connector with live ready
        connectors = [
            ConnectorReadiness(name="test", status=ComponentStatus.OK, live_ready=True),
        ]

        status = checker._determine_overall_status(components, connectors, [])
        assert status == ReadinessStatus.READY

    def test_status_not_ready_when_missing_required(self):
        """Test NOT_READY status when required components missing."""
        checker = ReadinessChecker()

        components = [
            ComponentCheck(name="test1", status=ComponentStatus.OK, required=True),
            ComponentCheck(name="test2", status=ComponentStatus.MISSING, required=True),
        ]

        connectors = []

        status = checker._determine_overall_status(components, connectors, ["test2"])
        assert status == ReadinessStatus.NOT_READY

    def test_status_error_when_component_error(self):
        """Test ERROR status when component has error."""
        checker = ReadinessChecker()

        components = [
            ComponentCheck(name="test1", status=ComponentStatus.ERROR, required=True),
        ]

        connectors = []

        status = checker._determine_overall_status(components, connectors, [])
        assert status == ReadinessStatus.ERROR

    def test_status_partial_when_degraded(self):
        """Test PARTIAL status when components degraded."""
        checker = ReadinessChecker()

        components = [
            ComponentCheck(name="test1", status=ComponentStatus.DEGRADED, required=True),
        ]

        connectors = [
            ConnectorReadiness(name="test", status=ComponentStatus.OK, live_ready=True),
        ]

        status = checker._determine_overall_status(components, connectors, [])
        assert status == ReadinessStatus.PARTIAL


class TestCredentialMapping:
    """Tests for connector credential mapping."""

    def test_connector_credentials_defined(self):
        """Test connector credentials are properly defined."""
        assert "telegram" in ReadinessChecker.CONNECTOR_CREDENTIALS
        assert "tavily" in ReadinessChecker.CONNECTOR_CREDENTIALS
        assert "sendgrid" in ReadinessChecker.CONNECTOR_CREDENTIALS
        assert "hubspot" in ReadinessChecker.CONNECTOR_CREDENTIALS
        assert "firecrawl" in ReadinessChecker.CONNECTOR_CREDENTIALS

    def test_live_capable_connectors_defined(self):
        """Test live-capable connectors are properly defined."""
        assert "telegram" in ReadinessChecker.LIVE_CAPABLE_CONNECTORS
        assert "tavily" in ReadinessChecker.LIVE_CAPABLE_CONNECTORS
        assert "sendgrid" in ReadinessChecker.LIVE_CAPABLE_CONNECTORS
        assert "hubspot" in ReadinessChecker.LIVE_CAPABLE_CONNECTORS
        assert "firecrawl" in ReadinessChecker.LIVE_CAPABLE_CONNECTORS
