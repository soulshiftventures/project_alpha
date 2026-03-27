"""
Tests for Cost Governance Layer.

Tests cover:
- Cost Model (estimation, classification)
- Cost Tracker (recording, aggregation)
- Budget Manager (limits, enforcement)
- Cost Policies (rules, evaluation)
- Integration with approval workflow
- Budget threshold behavior

SECURITY:
- Tests use mock values only
- No real credentials in test code
- No actual charges incurred
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


# =============================================================================
# Cost Model Tests
# =============================================================================

class TestCostClass:
    """Tests for CostClass enum."""

    def test_cost_class_values(self):
        """CostClass has all expected values."""
        from core.cost_model import CostClass

        assert CostClass.FREE.value == "free"
        assert CostClass.MINIMAL.value == "minimal"
        assert CostClass.LOW.value == "low"
        assert CostClass.MEDIUM.value == "medium"
        assert CostClass.HIGH.value == "high"
        assert CostClass.VERY_HIGH.value == "very_high"
        assert CostClass.UNKNOWN.value == "unknown"


class TestCostConfidence:
    """Tests for CostConfidence enum."""

    def test_cost_confidence_values(self):
        """CostConfidence has all expected values."""
        from core.cost_model import CostConfidence

        assert CostConfidence.EXACT.value == "exact"
        assert CostConfidence.HIGH.value == "high"
        assert CostConfidence.MEDIUM.value == "medium"
        assert CostConfidence.LOW.value == "low"
        assert CostConfidence.UNKNOWN.value == "unknown"


class TestCostEstimate:
    """Tests for CostEstimate dataclass."""

    def test_estimate_defaults(self):
        """CostEstimate has sensible defaults."""
        from core.cost_model import CostEstimate, CostClass, CostConfidence

        estimate = CostEstimate()

        assert estimate.amount == 0.0
        assert estimate.currency == "USD"
        assert estimate.cost_class == CostClass.UNKNOWN
        assert estimate.confidence == CostConfidence.UNKNOWN
        assert estimate.is_estimate is True

    def test_estimate_to_dict(self):
        """CostEstimate.to_dict() returns dictionary."""
        from core.cost_model import CostEstimate, CostClass, CostConfidence

        estimate = CostEstimate(
            amount=0.05,
            cost_class=CostClass.LOW,
            confidence=CostConfidence.MEDIUM,
        )

        data = estimate.to_dict()

        assert data["amount"] == 0.05
        assert data["cost_class"] == "low"
        assert data["confidence"] == "medium"

    def test_estimate_unknown_factory(self):
        """CostEstimate.unknown() creates unknown estimate."""
        from core.cost_model import CostEstimate, CostClass

        estimate = CostEstimate.unknown("Test unknown")

        assert estimate.amount == 0.0
        assert estimate.is_unknown is True
        assert estimate.cost_class == CostClass.UNKNOWN
        assert "unknown" in estimate.notes.lower() or "Test" in estimate.notes

    def test_estimate_free_factory(self):
        """CostEstimate.free() creates free estimate."""
        from core.cost_model import CostEstimate, CostClass, CostConfidence

        estimate = CostEstimate.free("Health check")

        assert estimate.amount == 0.0
        assert estimate.cost_class == CostClass.FREE
        assert estimate.confidence == CostConfidence.EXACT
        assert estimate.is_estimate is False

    def test_estimate_from_amount(self):
        """CostEstimate.from_amount() classifies correctly."""
        from core.cost_model import CostEstimate, CostClass

        # Free
        assert CostEstimate.from_amount(0).cost_class == CostClass.FREE

        # Minimal
        assert CostEstimate.from_amount(0.005).cost_class == CostClass.MINIMAL

        # Low
        assert CostEstimate.from_amount(0.05).cost_class == CostClass.LOW

        # Medium
        assert CostEstimate.from_amount(0.50).cost_class == CostClass.MEDIUM

        # High
        assert CostEstimate.from_amount(5.00).cost_class == CostClass.HIGH

        # Very High
        assert CostEstimate.from_amount(15.00).cost_class == CostClass.VERY_HIGH


class TestCostMetadata:
    """Tests for CostMetadata dataclass."""

    def test_metadata_creation(self):
        """CostMetadata can be created with required fields."""
        from core.cost_model import CostMetadata, CostClass

        metadata = CostMetadata(
            cost_id="cost_001",
            record_type="job",
            record_id="job_001",
            connector="hubspot",
            operation="create_contact",
            estimated_cost=0.01,
            cost_class=CostClass.MINIMAL,
        )

        assert metadata.cost_id == "cost_001"
        assert metadata.connector == "hubspot"
        assert metadata.estimated_cost == 0.01

    def test_metadata_get_effective_cost(self):
        """CostMetadata.get_effective_cost() returns best known cost."""
        from core.cost_model import CostMetadata

        # With estimated only
        metadata = CostMetadata(estimated_cost=0.05)
        assert metadata.get_effective_cost() == 0.05

        # With actual
        metadata.actual_cost = 0.03
        assert metadata.get_effective_cost() == 0.03

    def test_metadata_to_dict(self):
        """CostMetadata.to_dict() returns dictionary."""
        from core.cost_model import CostMetadata, CostClass, CostConfidence

        metadata = CostMetadata(
            cost_id="cost_002",
            record_type="connector",
            record_id="exec_001",
            connector="sendgrid",
            operation="send_email",
            estimated_cost=0.001,
            cost_class=CostClass.MINIMAL,
            confidence=CostConfidence.MEDIUM,
        )

        data = metadata.to_dict()

        assert data["cost_id"] == "cost_002"
        assert data["connector"] == "sendgrid"
        assert data["cost_class"] == "minimal"


class TestConnectorCostEstimates:
    """Tests for connector cost estimation functions."""

    def test_get_connector_cost_estimate_known(self):
        """Get cost estimate for known connector."""
        from core.cost_model import get_connector_cost_estimate, CostClass

        estimate = get_connector_cost_estimate("sendgrid", "send_email")

        assert estimate.amount > 0
        assert estimate.cost_class == CostClass.MINIMAL
        assert estimate.is_unknown is False

    def test_get_connector_cost_estimate_default(self):
        """Get default cost for connector without specific operation."""
        from core.cost_model import get_connector_cost_estimate

        estimate = get_connector_cost_estimate("hubspot", "unknown_operation")

        # Should return default for connector
        assert estimate.amount > 0 or estimate.is_unknown

    def test_get_connector_cost_estimate_unknown(self):
        """Get unknown cost for unknown connector."""
        from core.cost_model import get_connector_cost_estimate

        estimate = get_connector_cost_estimate("unknown_connector", "any_operation")

        assert estimate.is_unknown is True

    def test_get_backend_cost_estimate(self):
        """Get backend cost estimates."""
        from core.cost_model import get_backend_cost_estimate, CostClass

        # Local backends are free
        local = get_backend_cost_estimate("inline_local")
        assert local.cost_class == CostClass.FREE

        # Container has cost
        container = get_backend_cost_estimate("container")
        assert container.amount > 0


class TestPlanCostEstimation:
    """Tests for plan cost estimation."""

    def test_estimate_plan_cost_empty(self):
        """Estimate cost for empty plan."""
        from core.cost_model import estimate_plan_cost

        estimate = estimate_plan_cost([], "inline_local")

        assert estimate.amount == 0.0  # Free backend, no steps

    def test_estimate_plan_cost_with_steps(self):
        """Estimate cost for plan with steps."""
        from core.cost_model import estimate_plan_cost

        steps = [
            {"connector": "hubspot", "operation": "search"},
            {"connector": "hubspot", "operation": "create_contact"},
        ]

        estimate = estimate_plan_cost(steps, "inline_local")

        assert estimate.amount > 0
        assert "2 steps" in estimate.notes

    def test_estimate_plan_cost_with_unknown(self):
        """Estimate handles unknown connector costs."""
        from core.cost_model import estimate_plan_cost, CostConfidence

        steps = [
            {"connector": "known_connector", "operation": "any"},
            {"connector": "unknown_connector", "operation": "any"},
        ]

        estimate = estimate_plan_cost(steps, "inline_local")

        # Should indicate some unknown costs
        assert "unknown" in estimate.notes.lower() or estimate.confidence == CostConfidence.LOW


class TestCostHelpers:
    """Tests for cost helper functions."""

    def test_classify_cost(self):
        """classify_cost() works correctly."""
        from core.cost_model import classify_cost, CostClass

        assert classify_cost(0) == CostClass.FREE
        assert classify_cost(0.005) == CostClass.MINIMAL
        assert classify_cost(50) == CostClass.VERY_HIGH

    def test_is_high_cost(self):
        """is_high_cost() checks threshold."""
        from core.cost_model import is_high_cost

        assert is_high_cost(5.0, threshold=1.0) is True
        assert is_high_cost(0.5, threshold=1.0) is False

    def test_cost_requires_approval(self):
        """cost_requires_approval() checks threshold."""
        from core.cost_model import cost_requires_approval

        assert cost_requires_approval(1.0, approval_threshold=0.50) is True
        assert cost_requires_approval(0.25, approval_threshold=0.50) is False

    def test_cost_exceeds_budget(self):
        """cost_exceeds_budget() checks remaining."""
        from core.cost_model import cost_exceeds_budget

        assert cost_exceeds_budget(10.0, budget_remaining=5.0) is True
        assert cost_exceeds_budget(2.0, budget_remaining=5.0) is False


# =============================================================================
# Cost Tracker Tests
# =============================================================================

class TestCostSummary:
    """Tests for CostSummary dataclass."""

    def test_summary_defaults(self):
        """CostSummary has sensible defaults."""
        from core.cost_tracker import CostSummary

        summary = CostSummary()

        assert summary.total_estimated == 0.0
        assert summary.total_actual == 0.0
        assert summary.total_unknown == 0
        assert summary.record_count == 0

    def test_summary_total_effective(self):
        """CostSummary.total_effective property."""
        from core.cost_tracker import CostSummary

        # Actual takes precedence
        summary = CostSummary(total_estimated=10.0, total_actual=8.0)
        assert summary.total_effective == 8.0

        # Falls back to estimated
        summary2 = CostSummary(total_estimated=10.0, total_actual=0.0)
        assert summary2.total_effective == 10.0

    def test_summary_to_dict(self):
        """CostSummary.to_dict() returns dictionary."""
        from core.cost_tracker import CostSummary

        summary = CostSummary(
            total_estimated=5.0,
            total_actual=4.5,
            record_count=10,
            by_connector={"hubspot": 2.0, "sendgrid": 2.5},
        )

        data = summary.to_dict()

        assert data["total_estimated"] == 5.0
        assert data["record_count"] == 10
        assert "hubspot" in data["by_connector"]


class TestCostTracker:
    """Tests for CostTracker class."""

    @pytest.fixture
    def tracker(self):
        """Create CostTracker for testing."""
        from core.cost_tracker import CostTracker
        return CostTracker()

    def test_record_estimated_cost(self, tracker):
        """Record estimated cost successfully."""
        from core.cost_model import CostEstimate

        estimate = CostEstimate.from_amount(0.05)

        metadata = tracker.record_estimated_cost(
            record_type="job",
            record_id="job_001",
            estimate=estimate,
            connector="hubspot",
            operation="create_contact",
            business_id="biz_001",
        )

        assert metadata.cost_id.startswith("cost_")
        assert metadata.estimated_cost == 0.05
        assert metadata.connector == "hubspot"
        assert metadata.business_id == "biz_001"

    def test_record_actual_cost(self, tracker):
        """Update with actual cost."""
        from core.cost_model import CostEstimate

        estimate = CostEstimate.from_amount(0.05)

        metadata = tracker.record_estimated_cost(
            record_type="job",
            record_id="job_001",
            estimate=estimate,
        )

        updated = tracker.record_actual_cost(
            cost_id=metadata.cost_id,
            actual_amount=0.045,
            notes="Actual from billing",
        )

        assert updated is not None
        assert updated.actual_cost == 0.045
        assert updated.get_effective_cost() == 0.045

    def test_record_actual_cost_not_found(self, tracker):
        """Update non-existent cost returns None."""
        updated = tracker.record_actual_cost("nonexistent", 0.01)
        assert updated is None

    def test_record_connector_execution_cost(self, tracker):
        """Record connector execution cost."""
        metadata = tracker.record_connector_execution_cost(
            connector="sendgrid",
            operation="send_email",
            execution_id="exec_001",
            success=True,
            duration_seconds=1.5,
            business_id="biz_001",
        )

        assert metadata.record_type == "connector"
        assert metadata.connector == "sendgrid"
        assert metadata.metadata["success"] is True
        assert metadata.metadata["duration_seconds"] == 1.5

    def test_record_job_cost(self, tracker):
        """Record job cost."""
        metadata = tracker.record_job_cost(
            job_id="job_001",
            plan_id="plan_001",
            backend="inline_local",
            step_count=5,
            business_id="biz_001",
        )

        assert metadata.record_type == "job"
        assert metadata.job_id == "job_001"
        assert metadata.plan_id == "plan_001"

    def test_record_plan_cost(self, tracker):
        """Record plan cost."""
        steps = [
            {"connector": "hubspot", "operation": "search"},
            {"connector": "hubspot", "operation": "create_contact"},
        ]

        metadata = tracker.record_plan_cost(
            plan_id="plan_001",
            request_id="req_001",
            steps=steps,
            backend="inline_local",
        )

        assert metadata.record_type == "plan"
        assert metadata.plan_id == "plan_001"
        assert metadata.estimated_cost > 0

    def test_get_cost(self, tracker):
        """Get cost by ID."""
        from core.cost_model import CostEstimate

        metadata = tracker.record_estimated_cost(
            record_type="test",
            record_id="test_001",
            estimate=CostEstimate.from_amount(0.01),
        )

        retrieved = tracker.get_cost(metadata.cost_id)

        assert retrieved is not None
        assert retrieved.cost_id == metadata.cost_id

    def test_get_costs_for_job(self, tracker):
        """Get all costs for a job."""
        from core.cost_model import CostEstimate

        tracker.record_estimated_cost(
            record_type="job",
            record_id="job_001",
            estimate=CostEstimate.from_amount(0.01),
            job_id="job_001",
        )
        tracker.record_estimated_cost(
            record_type="connector",
            record_id="exec_001",
            estimate=CostEstimate.from_amount(0.005),
            job_id="job_001",
        )
        tracker.record_estimated_cost(
            record_type="connector",
            record_id="exec_002",
            estimate=CostEstimate.from_amount(0.005),
            job_id="job_002",  # Different job
        )

        job_costs = tracker.get_costs_for_job("job_001")

        assert len(job_costs) == 2

    def test_get_costs_for_business(self, tracker):
        """Get all costs for a business."""
        from core.cost_model import CostEstimate

        tracker.record_estimated_cost(
            record_type="plan",
            record_id="plan_001",
            estimate=CostEstimate.from_amount(0.05),
            business_id="biz_001",
        )
        tracker.record_estimated_cost(
            record_type="plan",
            record_id="plan_002",
            estimate=CostEstimate.from_amount(0.03),
            business_id="biz_002",
        )

        biz_costs = tracker.get_costs_for_business("biz_001")

        assert len(biz_costs) == 1
        assert biz_costs[0].business_id == "biz_001"

    def test_get_summary(self, tracker):
        """Get aggregated cost summary."""
        from core.cost_model import CostEstimate

        tracker.record_estimated_cost(
            record_type="connector",
            record_id="exec_001",
            estimate=CostEstimate.from_amount(0.01),
            connector="hubspot",
        )
        tracker.record_estimated_cost(
            record_type="connector",
            record_id="exec_002",
            estimate=CostEstimate.from_amount(0.02),
            connector="sendgrid",
        )

        summary = tracker.get_summary()

        assert summary.record_count == 2
        assert summary.total_estimated == 0.03
        assert "hubspot" in summary.by_connector
        assert "sendgrid" in summary.by_connector

    def test_get_total_estimated(self, tracker):
        """Get total estimated costs."""
        from core.cost_model import CostEstimate

        tracker.record_estimated_cost(
            record_type="test",
            record_id="test_001",
            estimate=CostEstimate.from_amount(0.10),
        )
        tracker.record_estimated_cost(
            record_type="test",
            record_id="test_002",
            estimate=CostEstimate.from_amount(0.15),
        )

        total = tracker.get_total_estimated()

        assert total == 0.25

    def test_project_operation_cost(self, tracker):
        """Project cost for future operations."""
        unit, total = tracker.project_operation_cost(
            connector="hubspot",
            operation="create_contact",
            count=10,
        )

        assert unit.amount > 0
        assert total == unit.amount * 10

    def test_clear_in_memory(self, tracker):
        """Clear in-memory costs."""
        from core.cost_model import CostEstimate

        tracker.record_estimated_cost(
            record_type="test",
            record_id="test_001",
            estimate=CostEstimate.from_amount(0.01),
        )

        count = tracker.clear_in_memory()

        assert count == 1
        assert tracker.get_total_estimated() == 0

    def test_get_stats(self, tracker):
        """Get tracker statistics."""
        from core.cost_model import CostEstimate

        tracker.record_estimated_cost(
            record_type="test",
            record_id="test_001",
            estimate=CostEstimate.from_amount(0.05),
            connector="hubspot",
        )

        stats = tracker.get_stats()

        assert stats["total_records"] == 1
        assert stats["total_estimated"] == 0.05
        assert "hubspot" in stats["by_connector"]


# =============================================================================
# Budget Manager Tests
# =============================================================================

class TestBudgetScope:
    """Tests for BudgetScope enum."""

    def test_budget_scope_values(self):
        """BudgetScope has all expected values."""
        from core.budget_manager import BudgetScope

        assert BudgetScope.GLOBAL.value == "global"
        assert BudgetScope.MONTHLY.value == "monthly"
        assert BudgetScope.BUSINESS.value == "business"
        assert BudgetScope.CONNECTOR.value == "connector"


class TestBudgetPolicyOutcome:
    """Tests for BudgetPolicyOutcome enum."""

    def test_outcome_values(self):
        """BudgetPolicyOutcome has all expected values."""
        from core.budget_manager import BudgetPolicyOutcome

        assert BudgetPolicyOutcome.ALLOWED.value == "allowed"
        assert BudgetPolicyOutcome.REQUIRES_APPROVAL.value == "requires_approval"
        assert BudgetPolicyOutcome.BLOCKED.value == "blocked"
        assert BudgetPolicyOutcome.WARNING.value == "warning"


class TestBudget:
    """Tests for Budget dataclass."""

    def test_budget_creation(self):
        """Budget can be created with required fields."""
        from core.budget_manager import Budget, BudgetScope

        budget = Budget(
            budget_id="budget_001",
            scope=BudgetScope.MONTHLY,
            scope_id="current",
            limit=100.0,
        )

        assert budget.budget_id == "budget_001"
        assert budget.limit == 100.0
        assert budget.spent == 0.0

    def test_budget_remaining(self):
        """Budget.remaining property works."""
        from core.budget_manager import Budget, BudgetScope

        budget = Budget(
            budget_id="budget_001",
            scope=BudgetScope.MONTHLY,
            limit=100.0,
            spent=30.0,
        )

        assert budget.remaining == 70.0

    def test_budget_utilization(self):
        """Budget.utilization property works."""
        from core.budget_manager import Budget, BudgetScope

        budget = Budget(
            budget_id="budget_001",
            scope=BudgetScope.MONTHLY,
            limit=100.0,
            spent=25.0,
        )

        assert budget.utilization == 0.25

    def test_budget_utilization_zero_limit(self):
        """Budget.utilization handles zero limit."""
        from core.budget_manager import Budget, BudgetScope

        budget = Budget(
            budget_id="budget_001",
            scope=BudgetScope.MONTHLY,
            limit=0.0,
        )

        assert budget.utilization == 0.0

    def test_budget_to_dict(self):
        """Budget.to_dict() returns dictionary."""
        from core.budget_manager import Budget, BudgetScope

        budget = Budget(
            budget_id="budget_001",
            scope=BudgetScope.CONNECTOR,
            scope_id="hubspot",
            limit=50.0,
            spent=10.0,
        )

        data = budget.to_dict()

        assert data["budget_id"] == "budget_001"
        assert data["scope"] == "connector"
        assert data["limit"] == 50.0
        assert data["remaining"] == 40.0


class TestBudgetManager:
    """Tests for BudgetManager class."""

    @pytest.fixture
    def manager(self):
        """Create BudgetManager for testing."""
        from core.budget_manager import BudgetManager, BudgetConfig

        config = BudgetConfig(
            global_monthly_limit=100.0,
            per_action_limit=10.0,
            per_job_limit=25.0,
            enable_blocking=False,
            require_approval_on_threshold=True,
        )
        mgr = BudgetManager(config)
        mgr.initialize()
        return mgr

    def test_initialize(self, manager):
        """BudgetManager initializes with default budgets."""
        budgets = manager.get_all_budgets()

        assert len(budgets) > 0
        assert manager.get_monthly_budget() is not None

    def test_check_budget_allowed(self, manager):
        """Budget check allows within budget."""
        from core.budget_manager import BudgetScope, BudgetPolicyOutcome

        result = manager.check_budget(
            projected_cost=5.0,
            scope=BudgetScope.MONTHLY,
            scope_id="current",
        )

        assert result.allowed is True
        assert result.outcome == BudgetPolicyOutcome.ALLOWED

    def test_check_budget_warning_threshold(self, manager):
        """Budget check warns at warning threshold."""
        from core.budget_manager import BudgetScope, BudgetPolicyOutcome

        # Set monthly budget spent to 78%
        monthly = manager.get_monthly_budget()
        monthly.spent = 78.0

        result = manager.check_budget(
            projected_cost=5.0,  # Would put at 83%
            scope=BudgetScope.MONTHLY,
            scope_id="current",
        )

        assert result.allowed is True
        assert result.outcome == BudgetPolicyOutcome.WARNING
        assert len(result.warnings) > 0

    def test_check_budget_approval_threshold(self, manager):
        """Budget check requires approval at approval threshold."""
        from core.budget_manager import BudgetScope, BudgetPolicyOutcome

        # Set monthly budget spent to 92%
        monthly = manager.get_monthly_budget()
        monthly.spent = 92.0

        result = manager.check_budget(
            projected_cost=5.0,  # Would put at 97%
            scope=BudgetScope.MONTHLY,
            scope_id="current",
        )

        assert result.allowed is False
        assert result.outcome == BudgetPolicyOutcome.REQUIRES_APPROVAL

    def test_check_budget_block_when_enabled(self):
        """Budget check blocks when blocking enabled."""
        from core.budget_manager import BudgetManager, BudgetConfig, BudgetScope, BudgetPolicyOutcome

        config = BudgetConfig(
            global_monthly_limit=100.0,
            enable_blocking=True,  # Enable blocking
        )
        mgr = BudgetManager(config)
        mgr.initialize()

        # Set budget to exhausted
        monthly = mgr.get_monthly_budget()
        monthly.spent = 100.0

        result = mgr.check_budget(
            projected_cost=5.0,  # Over 100%
            scope=BudgetScope.MONTHLY,
            scope_id="current",
        )

        assert result.allowed is False
        assert result.outcome == BudgetPolicyOutcome.BLOCKED

    def test_check_action_budget_over_limit(self, manager):
        """Per-action limit triggers approval."""
        from core.budget_manager import BudgetPolicyOutcome

        result = manager.check_action_budget(
            projected_cost=15.0,  # Over $10 per-action limit
            connector="hubspot",
        )

        assert result.allowed is False
        assert result.outcome == BudgetPolicyOutcome.REQUIRES_APPROVAL
        assert "per-action" in result.reason.lower()

    def test_check_action_budget_checks_connector(self, manager):
        """Action budget checks connector budget too."""
        from core.budget_manager import BudgetScope

        # Exhaust connector budget
        conn_budget = manager.get_budget(BudgetScope.CONNECTOR, "hubspot")
        if conn_budget:
            conn_budget.spent = conn_budget.limit * 0.98

        result = manager.check_action_budget(
            projected_cost=5.0,
            connector="hubspot",
        )

        # Should hit connector or monthly threshold
        assert len(result.warnings) > 0 or result.outcome.value != "allowed"

    def test_check_job_budget_over_limit(self, manager):
        """Per-job limit triggers approval."""
        from core.budget_manager import BudgetPolicyOutcome

        result = manager.check_job_budget(
            projected_cost=30.0,  # Over $25 per-job limit
        )

        assert result.allowed is False
        assert result.outcome == BudgetPolicyOutcome.REQUIRES_APPROVAL
        assert "job" in result.reason.lower()

    def test_record_spend(self, manager):
        """Record spend updates budget."""
        from core.budget_manager import BudgetScope

        initial_spent = manager.get_monthly_budget().spent

        manager.record_spend(
            amount=5.0,
            is_actual=True,
            scope=BudgetScope.MONTHLY,
            scope_id="current",
        )

        new_spent = manager.get_monthly_budget().spent
        assert new_spent == initial_spent + 5.0

    def test_record_spend_updates_connector(self, manager):
        """Record spend also updates connector budget."""
        from core.budget_manager import BudgetScope

        conn_budget = manager.get_budget(BudgetScope.CONNECTOR, "hubspot")
        initial = conn_budget.spent if conn_budget else 0

        manager.record_spend(
            amount=2.0,
            is_actual=False,
            scope=BudgetScope.MONTHLY,
            scope_id="current",
            connector="hubspot",
        )

        if conn_budget:
            assert conn_budget.spent == initial + 2.0

    def test_set_budget(self, manager):
        """Set or update budget."""
        from core.budget_manager import BudgetScope

        budget = manager.set_budget(
            scope=BudgetScope.BUSINESS,
            scope_id="biz_001",
            limit=200.0,
            warning_threshold=0.75,
        )

        assert budget.limit == 200.0
        assert budget.warning_threshold == 0.75

    def test_reset_budget(self, manager):
        """Reset budget spending."""
        from core.budget_manager import BudgetScope

        monthly = manager.get_monthly_budget()
        monthly.spent = 50.0

        result = manager.reset_budget(BudgetScope.MONTHLY, "current")

        assert result is True
        assert manager.get_monthly_budget().spent == 0.0

    def test_take_snapshot(self, manager):
        """Take budget snapshot."""
        from core.budget_manager import BudgetScope

        monthly = manager.get_monthly_budget()
        monthly.spent = 25.0

        snapshot = manager.take_snapshot(BudgetScope.MONTHLY, "current")

        assert snapshot is not None
        assert snapshot["snapshot_id"].startswith("bsnap_")
        assert snapshot["spent_total"] == 25.0
        assert snapshot["utilization_pct"] == 25.0

    def test_get_summary(self, manager):
        """Get budget manager summary."""
        summary = manager.get_summary()

        assert summary["initialized"] is True
        assert summary["budget_count"] > 0
        assert "monthly_remaining" in summary
        assert "config" in summary


# =============================================================================
# Cost Policies Tests
# =============================================================================

class TestCostPolicyOutcome:
    """Tests for CostPolicyOutcome enum."""

    def test_outcome_values(self):
        """CostPolicyOutcome has all expected values."""
        from core.cost_policies import CostPolicyOutcome

        assert CostPolicyOutcome.AUTO_ALLOWED.value == "auto_allowed"
        assert CostPolicyOutcome.REQUIRES_APPROVAL.value == "requires_approval"
        assert CostPolicyOutcome.BLOCKED.value == "blocked"


class TestCostPolicyRule:
    """Tests for CostPolicyRule dataclass."""

    def test_rule_creation(self):
        """CostPolicyRule can be created."""
        from core.cost_policies import CostPolicyRule, CostPolicyOutcome
        from core.cost_model import CostClass

        rule = CostPolicyRule(
            rule_id="test_rule",
            name="Test Rule",
            description="A test rule",
            connector_patterns=["hubspot"],
            cost_class_filter=[CostClass.HIGH],
            outcome=CostPolicyOutcome.REQUIRES_APPROVAL,
            priority=50,
        )

        assert rule.rule_id == "test_rule"
        assert rule.priority == 50

    def test_rule_to_dict(self):
        """CostPolicyRule.to_dict() returns dictionary."""
        from core.cost_policies import CostPolicyRule, CostPolicyOutcome

        rule = CostPolicyRule(
            rule_id="test_rule",
            name="Test Rule",
            description="A test rule",
            outcome=CostPolicyOutcome.AUTO_ALLOWED,
        )

        data = rule.to_dict()

        assert data["rule_id"] == "test_rule"
        assert data["outcome"] == "auto_allowed"


class TestCostPolicyResult:
    """Tests for CostPolicyResult dataclass."""

    def test_result_creation(self):
        """CostPolicyResult can be created."""
        from core.cost_policies import CostPolicyResult, CostPolicyOutcome
        from core.cost_model import CostClass

        result = CostPolicyResult(
            allowed=True,
            outcome=CostPolicyOutcome.AUTO_ALLOWED,
            reason="Test reason",
            projected_cost=0.05,
            cost_class=CostClass.LOW,
        )

        assert result.allowed is True
        assert result.projected_cost == 0.05

    def test_result_to_dict(self):
        """CostPolicyResult.to_dict() returns dictionary."""
        from core.cost_policies import CostPolicyResult, CostPolicyOutcome

        result = CostPolicyResult(
            allowed=False,
            outcome=CostPolicyOutcome.REQUIRES_APPROVAL,
            reason="Test reason",
            requires_approval=True,
            approval_reason="High cost",
        )

        data = result.to_dict()

        assert data["allowed"] is False
        assert data["requires_approval"] is True


class TestCostPolicyEngine:
    """Tests for CostPolicyEngine class."""

    @pytest.fixture
    def engine(self):
        """Create CostPolicyEngine for testing."""
        from core.cost_policies import CostPolicyEngine
        from core.budget_manager import BudgetManager, BudgetConfig

        # Create budget manager with permissive config
        budget_config = BudgetConfig(
            global_monthly_limit=1000.0,  # High limit for testing
            enable_blocking=False,
        )
        budget_mgr = BudgetManager(budget_config)
        budget_mgr.initialize()

        return CostPolicyEngine(budget_manager=budget_mgr)

    def test_default_rules_loaded(self, engine):
        """Default rules are loaded."""
        rules = engine.get_rules()

        assert len(rules) > 0
        # Should have very high cost rule
        rule_ids = [r.rule_id for r in rules]
        assert "cost_very_high" in rule_ids

    def test_evaluate_free_operation(self, engine):
        """Free operations are auto-allowed."""
        from core.cost_model import CostEstimate
        from core.cost_policies import CostPolicyOutcome

        estimate = CostEstimate.free("Health check")

        result = engine.evaluate(
            estimate=estimate,
            connector="hubspot",
            operation="health_check",
        )

        assert result.allowed is True
        assert result.outcome == CostPolicyOutcome.AUTO_ALLOWED

    def test_evaluate_very_high_cost(self, engine):
        """Very high cost requires approval."""
        from core.cost_model import CostEstimate
        from core.cost_policies import CostPolicyOutcome

        estimate = CostEstimate.from_amount(15.0)  # Very high

        result = engine.evaluate(
            estimate=estimate,
            connector="apollo",
            operation="bulk_enrich",
        )

        assert result.outcome == CostPolicyOutcome.REQUIRES_APPROVAL
        assert result.requires_approval is True

    def test_evaluate_normal_operation(self, engine):
        """Normal cost operations allowed."""
        from core.cost_model import CostEstimate
        from core.cost_policies import CostPolicyOutcome

        estimate = CostEstimate.from_amount(0.05)  # Low cost

        result = engine.evaluate(
            estimate=estimate,
            connector="hubspot",
            operation="search",
        )

        assert result.allowed is True
        assert result.outcome == CostPolicyOutcome.AUTO_ALLOWED

    def test_evaluate_unknown_cost(self, engine):
        """Unknown cost gets warning."""
        from core.cost_model import CostEstimate
        from core.cost_policies import CostPolicyOutcome

        estimate = CostEstimate.unknown()

        result = engine.evaluate(
            estimate=estimate,
            connector="unknown_connector",
            operation="unknown_op",
        )

        # Should be warning or allowed with warning
        assert result.allowed is True
        assert len(result.warnings) > 0 or result.outcome == CostPolicyOutcome.WARNING

    def test_evaluate_email_threshold(self, engine):
        """Email operations over threshold require approval."""
        from core.cost_model import CostEstimate
        from core.cost_policies import CostPolicyOutcome

        estimate = CostEstimate.from_amount(2.0)  # Over $1 email threshold

        result = engine.evaluate(
            estimate=estimate,
            connector="sendgrid",
            operation="send_bulk",
        )

        assert result.outcome == CostPolicyOutcome.REQUIRES_APPROVAL

    def test_evaluate_plan(self, engine):
        """Evaluate cost policies for a plan."""
        from core.cost_model import CostEstimate
        from core.cost_policies import CostPolicyOutcome

        plan_estimate = CostEstimate.from_amount(0.10)

        steps = [
            {"connector": "hubspot", "operation": "search"},
            {"connector": "hubspot", "operation": "create_contact"},
        ]

        result = engine.evaluate_plan(
            plan_estimate=plan_estimate,
            steps=steps,
        )

        assert result.allowed is True

    def test_evaluate_plan_over_job_limit(self):
        """Plan over job limit requires approval."""
        from core.cost_policies import CostPolicyEngine, CostPolicyOutcome
        from core.cost_model import CostEstimate
        from core.budget_manager import BudgetManager, BudgetConfig

        # Create budget manager with low job limit
        budget_config = BudgetConfig(
            global_monthly_limit=1000.0,
            per_job_limit=5.0,  # Low limit
            require_approval_on_threshold=True,
        )
        budget_mgr = BudgetManager(budget_config)
        budget_mgr.initialize()

        engine = CostPolicyEngine(budget_manager=budget_mgr)

        plan_estimate = CostEstimate.from_amount(10.0)  # Over $5 job limit

        result = engine.evaluate_plan(
            plan_estimate=plan_estimate,
            steps=[],
        )

        assert result.outcome == CostPolicyOutcome.REQUIRES_APPROVAL

    def test_add_rule(self, engine):
        """Add a new policy rule."""
        from core.cost_policies import CostPolicyRule, CostPolicyOutcome
        from core.cost_model import CostClass

        rule = CostPolicyRule(
            rule_id="custom_rule",
            name="Custom Rule",
            description="Block expensive custom operations",
            connector_patterns=["custom_connector"],
            outcome=CostPolicyOutcome.BLOCKED,
            priority=200,  # High priority
        )

        engine.add_rule(rule)

        # Should be first in list
        rules = engine.get_rules()
        assert rules[0].rule_id == "custom_rule"

    def test_remove_rule(self, engine):
        """Remove a policy rule."""
        initial_count = len(engine.get_rules())

        result = engine.remove_rule("cost_free")

        assert result is True
        assert len(engine.get_rules()) == initial_count - 1

    def test_get_summary(self, engine):
        """Get policy engine summary."""
        summary = engine.get_summary()

        assert summary["initialized"] is True
        assert summary["rule_count"] > 0
        assert "rules" in summary


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_check_operation_cost_policy(self):
        """check_operation_cost_policy convenience function."""
        from core.cost_policies import check_operation_cost_policy

        result = check_operation_cost_policy(
            connector="hubspot",
            operation="search",
            estimated_cost=0.01,
        )

        assert result.projected_cost == 0.01

    def test_check_plan_cost_policy(self):
        """check_plan_cost_policy convenience function."""
        from core.cost_policies import check_plan_cost_policy

        steps = [{"connector": "hubspot", "operation": "search"}]

        result = check_plan_cost_policy(
            plan_cost=0.05,
            steps=steps,
        )

        assert result.projected_cost == 0.05


# =============================================================================
# Singleton Tests
# =============================================================================

class TestSingletons:
    """Tests for singleton instances."""

    def test_get_cost_tracker_singleton(self):
        """get_cost_tracker returns singleton."""
        import core.cost_tracker

        # Reset singleton
        core.cost_tracker._cost_tracker = None

        t1 = core.cost_tracker.get_cost_tracker()
        t2 = core.cost_tracker.get_cost_tracker()

        assert t1 is t2

        # Clean up
        core.cost_tracker._cost_tracker = None

    def test_get_budget_manager_singleton(self):
        """get_budget_manager returns singleton."""
        import core.budget_manager

        # Reset singleton
        core.budget_manager._budget_manager = None

        m1 = core.budget_manager.get_budget_manager()
        m2 = core.budget_manager.get_budget_manager()

        assert m1 is m2

        # Clean up
        core.budget_manager._budget_manager = None

    def test_get_cost_policy_engine_singleton(self):
        """get_cost_policy_engine returns singleton."""
        import core.cost_policies

        # Reset singleton
        core.cost_policies._cost_policy_engine = None

        e1 = core.cost_policies.get_cost_policy_engine()
        e2 = core.cost_policies.get_cost_policy_engine()

        assert e1 is e2

        # Clean up
        core.cost_policies._cost_policy_engine = None


# =============================================================================
# Integration Tests
# =============================================================================

class TestCostGovernanceIntegration:
    """Integration tests for cost governance flow."""

    def test_full_cost_tracking_flow(self):
        """Test complete cost tracking flow."""
        from core.cost_tracker import CostTracker
        from core.cost_model import CostEstimate

        tracker = CostTracker()

        # 1. Record plan cost
        plan_steps = [
            {"connector": "hubspot", "operation": "search"},
            {"connector": "hubspot", "operation": "create_contact"},
        ]
        plan_metadata = tracker.record_plan_cost(
            plan_id="plan_flow_001",
            request_id="req_001",
            steps=plan_steps,
            backend="inline_local",
            business_id="biz_001",
        )

        assert plan_metadata.estimated_cost > 0

        # 2. Record job cost
        job_metadata = tracker.record_job_cost(
            job_id="job_flow_001",
            plan_id="plan_flow_001",
            backend="inline_local",
            step_count=2,
            business_id="biz_001",
            estimated_cost=plan_metadata.estimated_cost,
        )

        # 3. Record connector execution costs
        exec1 = tracker.record_connector_execution_cost(
            connector="hubspot",
            operation="search",
            execution_id="exec_001",
            success=True,
            duration_seconds=0.5,
            business_id="biz_001",
        )

        exec2 = tracker.record_connector_execution_cost(
            connector="hubspot",
            operation="create_contact",
            execution_id="exec_002",
            success=True,
            duration_seconds=1.2,
            business_id="biz_001",
        )

        # 4. Get summary for business
        summary = tracker.get_business_summary("biz_001")

        assert summary.record_count == 4  # plan + job + 2 connectors
        assert summary.total_estimated > 0
        assert "hubspot" in summary.by_connector

    def test_cost_policy_budget_integration(self):
        """Test cost policy with budget checking."""
        from core.cost_policies import CostPolicyEngine, CostPolicyOutcome
        from core.cost_model import CostEstimate
        from core.budget_manager import BudgetManager, BudgetConfig, BudgetScope

        # Set up budget at 90% utilization
        budget_config = BudgetConfig(
            global_monthly_limit=100.0,
            require_approval_on_threshold=True,
        )
        budget_mgr = BudgetManager(budget_config)
        budget_mgr.initialize()
        budget_mgr.get_monthly_budget().spent = 93.0  # 93% utilized

        engine = CostPolicyEngine(budget_manager=budget_mgr)

        # Use a LOW cost estimate with a non-high-risk connector
        # to test budget threshold triggering requires_approval
        estimate = CostEstimate.from_amount(3.0)  # Would be 96%

        result = engine.evaluate(
            estimate=estimate,
            connector="tavily",  # Not a high-risk connector
            operation="search",
        )

        # Should require approval due to budget threshold (96% > 95%)
        assert result.outcome == CostPolicyOutcome.REQUIRES_APPROVAL
        assert result.budget_check is not None
        assert result.budget_check.utilization_after > 0.95
