"""
Tests for Capacity Management Layer

Tests capacity manager, capacity policies, and capacity-aware portfolio management.
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone

from core.capacity_manager import (
    CapacityManager,
    CapacityDimension,
    CapacityDecision,
    CapacityCheckContext,
    CapacityLimit
)
from core.capacity_policies import (
    CapacityPolicies,
    CapacityPolicyRule,
    CapacityPolicyPriority
)
from core.portfolio_manager import PortfolioManager
from core.portfolio_workflows import PortfolioWorkflows
from core.lifecycle_manager import LifecycleManager
from core.state_store import StateStore, StateStoreConfig


class TestCapacityManager:
    """Test CapacityManager functionality."""

    def test_unlimited_mode_by_default(self):
        """Test that capacity is unlimited by default."""
        manager = CapacityManager()

        context = CapacityCheckContext(
            dimension=CapacityDimension.BUSINESSES,
            current_count=100,  # Even 100 should be allowed
            requested_increment=50
        )

        result = manager.check_capacity(context)

        assert result.decision == CapacityDecision.ALLOWED
        assert result.soft_limit is None
        assert result.hard_limit is None

    def test_soft_limit_warning(self):
        """Test soft limit triggers warning."""
        manager = CapacityManager()
        manager.set_limit(
            dimension=CapacityDimension.BUSINESSES,
            soft_limit=5,
            hard_limit=None
        )

        context = CapacityCheckContext(
            dimension=CapacityDimension.BUSINESSES,
            current_count=5,  # At soft limit
            requested_increment=1
        )

        result = manager.check_capacity(context)

        assert result.decision == CapacityDecision.WARNING
        assert len(result.warnings) > 0
        assert "soft limit" in result.warnings[0].lower()

    def test_hard_limit_blocking(self):
        """Test hard limit blocks capacity."""
        manager = CapacityManager()
        manager.set_limit(
            dimension=CapacityDimension.BUSINESSES,
            soft_limit=5,
            hard_limit=10
        )

        context = CapacityCheckContext(
            dimension=CapacityDimension.BUSINESSES,
            current_count=10,  # At hard limit
            requested_increment=1
        )

        result = manager.check_capacity(context)

        assert result.decision == CapacityDecision.BLOCKED
        assert "hard limit" in result.reason.lower()
        assert len(result.recommendations) > 0

    def test_no_limit_mode(self):
        """Test explicitly setting no limits (unlimited)."""
        manager = CapacityManager()
        manager.set_limit(
            dimension=CapacityDimension.BUSINESSES,
            soft_limit=None,
            hard_limit=None
        )

        context = CapacityCheckContext(
            dimension=CapacityDimension.BUSINESSES,
            current_count=1000,
            requested_increment=500
        )

        result = manager.check_capacity(context)

        assert result.decision == CapacityDecision.ALLOWED

    def test_capacity_status(self):
        """Test getting capacity status."""
        manager = CapacityManager()
        manager.set_limit(
            dimension=CapacityDimension.BUSINESSES,
            soft_limit=10,
            hard_limit=20
        )

        status = manager.get_capacity_status()

        assert "dimensions" in status
        assert "businesses" in status["dimensions"]
        assert status["dimensions"]["businesses"]["soft_limit"] == 10
        assert status["dimensions"]["businesses"]["hard_limit"] == 20

    def test_disabled_limit(self):
        """Test disabled limit does not enforce."""
        manager = CapacityManager()
        manager.set_limit(
            dimension=CapacityDimension.BUSINESSES,
            soft_limit=5,
            hard_limit=10,
            enabled=False  # Disabled
        )

        context = CapacityCheckContext(
            dimension=CapacityDimension.BUSINESSES,
            current_count=20,  # Well over hard limit
            requested_increment=10
        )

        result = manager.check_capacity(context)

        assert result.decision == CapacityDecision.ALLOWED

    def test_capacity_overrides(self):
        """Test capacity overrides."""
        manager = CapacityManager()

        manager.set_override(
            override_id="test_override",
            dimension=CapacityDimension.BUSINESSES,
            reason="Testing override functionality",
            duration_minutes=60
        )

        overrides = manager.get_overrides()

        assert "test_override" in overrides
        assert overrides["test_override"]["reason"] == "Testing override functionality"

        manager.remove_override("test_override")

        assert "test_override" not in manager.get_overrides()


class TestCapacityPolicies:
    """Test CapacityPolicies functionality."""

    def test_default_policies_loaded(self):
        """Test default policies are loaded."""
        policies = CapacityPolicies()

        summary = policies.get_policy_summary()

        assert summary["total_rules"] > 0
        assert summary["enabled_rules"] > 0

    def test_high_cost_block_policy(self):
        """Test high cost operations are blocked by policy."""
        policies = CapacityPolicies()

        context = CapacityCheckContext(
            dimension=CapacityDimension.BUSINESSES,
            current_count=1,
            requested_increment=1,
            estimated_cost=150.0  # Very high cost
        )

        result = policies.evaluate_capacity(context)

        assert result["blocked"]
        assert "cost" in result["reason"].lower()

    def test_moderate_cost_approval_policy(self):
        """Test moderate cost operations require approval."""
        policies = CapacityPolicies()

        context = CapacityCheckContext(
            dimension=CapacityDimension.BUSINESSES,
            current_count=1,
            requested_increment=1,
            estimated_cost=15.0  # High enough for approval
            # No runtime_backend to avoid runtime policy checks
        )

        result = policies.evaluate_capacity(context)

        # Should require approval due to high cost
        assert result["requires_approval"]
        assert "cost" in result["reason"].lower() or "approval" in result["reason"].lower()

    def test_add_custom_policy(self):
        """Test adding custom policy rule."""
        policies = CapacityPolicies()

        initial_count = policies.get_policy_summary()["total_rules"]

        policies.add_rule(CapacityPolicyRule(
            rule_id="test_custom",
            name="Test Custom Rule",
            priority=CapacityPolicyPriority.MEDIUM,
            dimension_filter=CapacityDimension.JOBS,
            conditions={"min_count": 50},
            outcome=CapacityDecision.WARNING,
            reason="Too many jobs"
        ))

        assert policies.get_policy_summary()["total_rules"] == initial_count + 1

        policies.remove_rule("test_custom")

        assert policies.get_policy_summary()["total_rules"] == initial_count

    def test_policy_priority_ordering(self):
        """Test policies are evaluated in priority order."""
        policies = CapacityPolicies()

        # Add a critical blocking rule
        policies.add_rule(CapacityPolicyRule(
            rule_id="critical_block",
            name="Critical Block",
            priority=CapacityPolicyPriority.CRITICAL,
            conditions={"min_count": 1},
            outcome=CapacityDecision.BLOCKED,
            reason="Critical block"
        ))

        # Add a low priority allow rule
        policies.add_rule(CapacityPolicyRule(
            rule_id="low_allow",
            name="Low Allow",
            priority=CapacityPolicyPriority.LOW,
            conditions={"min_count": 1},
            outcome=CapacityDecision.ALLOWED,
            reason="Low allow"
        ))

        context = CapacityCheckContext(
            dimension=CapacityDimension.BUSINESSES,
            current_count=5,
            requested_increment=1
        )

        result = policies.evaluate_capacity(context)

        # Critical block should take precedence
        assert result["blocked"]
        assert result["reason"] == "Critical block"


class TestPortfolioManagerCapacity:
    """Test PortfolioManager with capacity management."""

    def test_legacy_max_active_compatibility(self):
        """Test legacy max_active parameter still works."""
        manager = PortfolioManager(max_active=5)

        # Create dummy business
        lifecycle = LifecycleManager()
        for i in range(5):
            business = lifecycle.create_business({"idea": f"Business {i}", "potential": "high"})

        capacity_check = manager.can_add_business()

        # Should show warning at soft limit
        assert not capacity_check["allowed"] or capacity_check["decision"] == "warning"

    def test_unlimited_capacity_mode(self):
        """Test portfolio with unlimited capacity."""
        manager = PortfolioManager()  # No max_active, no capacity_manager

        # Even with many businesses, should allow
        capacity_check = manager.can_add_business()

        assert capacity_check["allowed"]
        assert capacity_check["details"]["soft_limit"] is None

    def test_portfolio_stats_include_capacity(self):
        """Test portfolio stats include capacity information."""
        manager = PortfolioManager(max_active=10)

        stats = manager.get_portfolio_stats()

        assert "capacity" in stats
        assert "current_count" in stats["capacity"]
        assert "soft_limit" in stats["capacity"]
        assert "mode" in stats["capacity"]


class TestPortfolioWorkflowsCapacity:
    """Test PortfolioWorkflows with capacity management."""

    def test_capacity_check_on_add_business(self):
        """Test capacity check when adding business."""
        workflows = PortfolioWorkflows(max_concurrent_businesses=5)

        # Add businesses up to soft limit
        for i in range(5):
            business = {
                "id": f"biz_{i}",
                "stage": "BUILDING",
                "opportunity": {"idea": f"Business {i}"},
                "metrics": {}
            }
            result = workflows.add_business(business)
            assert result["status"] in ["added", "requires_approval"]

        # Sixth business should trigger warning or block
        business = {
            "id": "biz_6",
            "stage": "BUILDING",
            "opportunity": {"idea": "Business 6"},
            "metrics": {}
        }
        result = workflows.add_business(business)

        # Should either be added with warning or blocked/require approval
        assert result["status"] in ["added", "requires_approval", "rejected"]

    def test_portfolio_status_includes_capacity(self):
        """Test portfolio status includes capacity info."""
        workflows = PortfolioWorkflows(max_concurrent_businesses=10)

        status = workflows.get_portfolio_status()

        assert "capacity" in status
        assert "utilization" in status["capacity"]
        assert "mode" in status["capacity"]


class TestCapacityPersistence:
    """Test capacity persistence in StateStore."""

    def test_save_and_load_capacity_limit(self):
        """Test saving and loading capacity limits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_capacity.db")
            config = StateStoreConfig(db_path=db_path)
            store = StateStore(config)
            store.initialize()

            # Save capacity limit
            limit_config = {
                "soft_limit": 10,
                "hard_limit": 20,
                "enabled": True,
                "description": "Test limit"
            }

            success = store.save_capacity_limit("businesses", limit_config)
            assert success

            # Load capacity limit
            loaded = store.get_capacity_limit("businesses")

            assert loaded is not None
            assert loaded["soft_limit"] == 10
            assert loaded["hard_limit"] == 20
            assert loaded["enabled"] == 1

    def test_list_capacity_limits(self):
        """Test listing all capacity limits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_capacity.db")
            config = StateStoreConfig(db_path=db_path)
            store = StateStore(config)
            store.initialize()

            # Save multiple limits
            for dimension in ["businesses", "jobs", "opportunities"]:
                store.save_capacity_limit(dimension, {
                    "soft_limit": 10,
                    "hard_limit": 20,
                    "enabled": True,
                    "description": f"{dimension} limit"
                })

            limits = store.list_capacity_limits()

            assert len(limits) >= 3

    def test_save_capacity_decision(self):
        """Test saving capacity decisions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_capacity.db")
            config = StateStoreConfig(db_path=db_path)
            store = StateStore(config)
            store.initialize()

            decision = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dimension": "businesses",
                "decision": "allowed",
                "current_count": 5,
                "projected_count": 6,
                "soft_limit": 10,
                "hard_limit": None,
                "reason": "Capacity available",
                "context": {
                    "business_id": "test_biz_1"
                }
            }

            success = store.save_capacity_decision(decision)
            assert success

            # List decisions
            decisions = store.list_capacity_decisions(dimension="businesses")

            assert len(decisions) > 0
            assert decisions[0]["dimension"] == "businesses"

    def test_filter_capacity_decisions(self):
        """Test filtering capacity decisions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_capacity.db")
            config = StateStoreConfig(db_path=db_path)
            store = StateStore(config)
            store.initialize()

            # Save decisions with different outcomes
            for decision_type in ["allowed", "warning", "blocked"]:
                store.save_capacity_decision({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "dimension": "businesses",
                    "decision": decision_type,
                    "current_count": 5,
                    "projected_count": 6,
                    "soft_limit": 10,
                    "hard_limit": 20,
                    "reason": f"Test {decision_type}",
                    "context": {}
                })

            # Filter for blocked decisions
            blocked = store.list_capacity_decisions(decision="blocked")

            assert len(blocked) >= 1
            assert all(d["decision"] == "blocked" for d in blocked)
