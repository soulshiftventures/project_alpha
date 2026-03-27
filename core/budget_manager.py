"""
Budget Manager for Project Alpha.

Provides configurable budget controls and enforcement.

ARCHITECTURE:
- Budget scopes: global, per-business, per-connector, per-job, per-action
- Policy outcomes: auto_allowed, requires_approval, blocked
- Threshold-based enforcement
- Persistence of budget snapshots

BUDGET ENFORCEMENT:
- Budgets are soft limits unless explicitly blocking
- High cost operations can require approval
- Budget exhaustion can block further execution
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from .cost_model import CostEstimate, CostClass, cost_requires_approval

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def _generate_snapshot_id() -> str:
    """Generate a unique snapshot ID."""
    return f"bsnap_{_utc_now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


class BudgetScope(Enum):
    """Scope of a budget."""
    GLOBAL = "global"          # System-wide budget
    MONTHLY = "monthly"        # Monthly budget period
    BUSINESS = "business"      # Per-business budget
    CONNECTOR = "connector"    # Per-connector budget
    BACKEND = "backend"        # Per-backend budget
    JOB = "job"                # Per-job limit
    ACTION = "action"          # Per-action limit


class BudgetPolicyOutcome(Enum):
    """Outcome of a budget policy check."""
    ALLOWED = "allowed"                    # Within budget, proceed
    REQUIRES_APPROVAL = "requires_approval"  # Over threshold, needs approval
    BLOCKED = "blocked"                    # Exceeds budget, cannot proceed
    WARNING = "warning"                    # Near threshold, proceed with warning


@dataclass
class Budget:
    """
    A budget definition.

    Defines spending limits for a scope.
    """
    budget_id: str
    scope: BudgetScope
    scope_id: Optional[str] = None  # ID within scope (e.g., business_id)
    limit: float = 0.0              # Budget limit
    currency: str = "USD"
    period_start: Optional[str] = None
    period_end: Optional[str] = None

    # Thresholds
    warning_threshold: float = 0.80   # 80% - trigger warning
    approval_threshold: float = 0.95  # 95% - require approval
    block_threshold: float = 1.0      # 100% - block execution

    # Tracking
    spent: float = 0.0
    spent_estimated: float = 0.0
    spent_actual: float = 0.0
    last_updated: str = field(default_factory=lambda: _utc_now().isoformat())

    @property
    def remaining(self) -> float:
        """Get remaining budget."""
        return max(0, self.limit - self.spent)

    @property
    def utilization(self) -> float:
        """Get budget utilization percentage."""
        if self.limit <= 0:
            return 0.0
        return min(1.0, self.spent / self.limit)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "budget_id": self.budget_id,
            "scope": self.scope.value,
            "scope_id": self.scope_id,
            "limit": self.limit,
            "currency": self.currency,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "warning_threshold": self.warning_threshold,
            "approval_threshold": self.approval_threshold,
            "block_threshold": self.block_threshold,
            "spent": self.spent,
            "spent_estimated": self.spent_estimated,
            "spent_actual": self.spent_actual,
            "remaining": self.remaining,
            "utilization": self.utilization,
            "last_updated": self.last_updated,
        }


@dataclass
class BudgetCheckResult:
    """Result of a budget check."""
    allowed: bool
    outcome: BudgetPolicyOutcome
    reason: str
    budget_id: Optional[str] = None
    scope: Optional[BudgetScope] = None
    projected_cost: float = 0.0
    budget_remaining: float = 0.0
    budget_limit: float = 0.0
    utilization_before: float = 0.0
    utilization_after: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "budget_id": self.budget_id,
            "scope": self.scope.value if self.scope else None,
            "projected_cost": self.projected_cost,
            "budget_remaining": self.budget_remaining,
            "budget_limit": self.budget_limit,
            "utilization_before": self.utilization_before,
            "utilization_after": self.utilization_after,
            "warnings": self.warnings,
        }


@dataclass
class BudgetConfig:
    """Configuration for budget manager."""
    # Default budgets (can be overridden)
    global_monthly_limit: float = 100.0  # $100/month default
    per_action_limit: float = 10.0       # $10 per single action
    per_job_limit: float = 25.0          # $25 per job

    # Per-connector defaults
    connector_limits: Dict[str, float] = field(default_factory=dict)

    # Thresholds
    default_warning_threshold: float = 0.80
    default_approval_threshold: float = 0.95

    # Enforcement
    enable_blocking: bool = False  # Start permissive
    require_approval_on_threshold: bool = True


class BudgetManager:
    """
    Manages budgets and spending limits.

    Provides configurable budget controls for affordability.
    """

    def __init__(
        self,
        config: Optional[BudgetConfig] = None,
        persistence_manager=None,
    ):
        """Initialize the budget manager."""
        self._config = config or BudgetConfig()
        self._persistence_manager = persistence_manager
        self._budgets: Dict[str, Budget] = {}
        self._initialized = False

        # Set up default connector limits
        if not self._config.connector_limits:
            self._config.connector_limits = {
                "sendgrid": 20.0,
                "hubspot": 30.0,
                "apollo": 50.0,
                "instantly": 20.0,
                "smartlead": 20.0,
            }

    def initialize(self) -> bool:
        """Initialize the budget manager with default budgets."""
        try:
            # Create global monthly budget
            self._create_budget(
                scope=BudgetScope.MONTHLY,
                scope_id="current",
                limit=self._config.global_monthly_limit,
            )

            # Create per-connector budgets
            for connector, limit in self._config.connector_limits.items():
                self._create_budget(
                    scope=BudgetScope.CONNECTOR,
                    scope_id=connector,
                    limit=limit,
                )

            self._initialized = True
            logger.info("BudgetManager initialized")
            return True

        except Exception as e:
            logger.error(f"BudgetManager initialization failed: {e}")
            return False

    def _ensure_initialized(self) -> None:
        """Ensure manager is initialized."""
        if not self._initialized:
            self.initialize()

    def _create_budget(
        self,
        scope: BudgetScope,
        scope_id: Optional[str],
        limit: float,
    ) -> Budget:
        """Create a new budget."""
        now = _utc_now()

        # Set period for monthly budgets
        period_start = None
        period_end = None
        if scope == BudgetScope.MONTHLY:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
            period_end = next_month.isoformat()

        budget_id = f"budget_{scope.value}_{scope_id or 'default'}"

        budget = Budget(
            budget_id=budget_id,
            scope=scope,
            scope_id=scope_id,
            limit=limit,
            period_start=period_start,
            period_end=period_end,
            warning_threshold=self._config.default_warning_threshold,
            approval_threshold=self._config.default_approval_threshold,
        )

        self._budgets[budget_id] = budget
        return budget

    # =========================================================================
    # Budget Checks
    # =========================================================================

    def check_budget(
        self,
        projected_cost: float,
        scope: BudgetScope = BudgetScope.MONTHLY,
        scope_id: Optional[str] = None,
    ) -> BudgetCheckResult:
        """
        Check if a projected cost is within budget.

        Args:
            projected_cost: Expected cost
            scope: Budget scope to check
            scope_id: ID within scope (e.g., connector name)

        Returns:
            BudgetCheckResult with outcome
        """
        self._ensure_initialized()

        # Find relevant budget
        budget_id = f"budget_{scope.value}_{scope_id or 'default'}"
        budget = self._budgets.get(budget_id)

        # If no specific budget, check global monthly
        if not budget and scope != BudgetScope.MONTHLY:
            budget_id = "budget_monthly_current"
            budget = self._budgets.get(budget_id)

        if not budget:
            # No budget defined - allow by default
            return BudgetCheckResult(
                allowed=True,
                outcome=BudgetPolicyOutcome.ALLOWED,
                reason="No budget defined for scope",
                projected_cost=projected_cost,
            )

        # Calculate utilization
        current_utilization = budget.utilization
        projected_total = budget.spent + projected_cost
        projected_utilization = projected_total / budget.limit if budget.limit > 0 else 0

        # Determine outcome based on thresholds
        allowed = True
        outcome = BudgetPolicyOutcome.ALLOWED
        reason = f"Within budget: {projected_utilization:.0%} of limit"
        warnings: List[str] = []

        # Check thresholds
        if projected_utilization >= budget.block_threshold:
            if self._config.enable_blocking:
                allowed = False
                outcome = BudgetPolicyOutcome.BLOCKED
                reason = f"Budget exhausted: {projected_utilization:.0%} of limit"
            else:
                allowed = True
                outcome = BudgetPolicyOutcome.WARNING
                reason = f"Budget exceeded but blocking disabled: {projected_utilization:.0%}"
                warnings.append("Budget limit exceeded - consider enabling blocking")

        elif projected_utilization >= budget.approval_threshold:
            if self._config.require_approval_on_threshold:
                allowed = False
                outcome = BudgetPolicyOutcome.REQUIRES_APPROVAL
                reason = f"Near budget limit: {projected_utilization:.0%} of limit"
            else:
                allowed = True
                outcome = BudgetPolicyOutcome.WARNING
                reason = f"Near budget limit: {projected_utilization:.0%}"
                warnings.append("Approaching budget limit")

        elif projected_utilization >= budget.warning_threshold:
            allowed = True
            outcome = BudgetPolicyOutcome.WARNING
            reason = f"Warning: {projected_utilization:.0%} of budget"
            warnings.append(f"Budget at {projected_utilization:.0%}")

        return BudgetCheckResult(
            allowed=allowed,
            outcome=outcome,
            reason=reason,
            budget_id=budget.budget_id,
            scope=budget.scope,
            projected_cost=projected_cost,
            budget_remaining=budget.remaining,
            budget_limit=budget.limit,
            utilization_before=current_utilization,
            utilization_after=projected_utilization,
            warnings=warnings,
        )

    def check_action_budget(
        self,
        projected_cost: float,
        connector: Optional[str] = None,
        business_id: Optional[str] = None,
    ) -> BudgetCheckResult:
        """
        Check budget for a single action.

        Checks per-action limit, connector limit, and global limit.

        Args:
            projected_cost: Expected cost
            connector: Connector name if applicable
            business_id: Business ID if applicable

        Returns:
            BudgetCheckResult with combined outcome
        """
        self._ensure_initialized()

        warnings = []

        # Check per-action limit
        if projected_cost > self._config.per_action_limit:
            return BudgetCheckResult(
                allowed=False,
                outcome=BudgetPolicyOutcome.REQUIRES_APPROVAL,
                reason=f"Cost ${projected_cost:.2f} exceeds per-action limit ${self._config.per_action_limit:.2f}",
                projected_cost=projected_cost,
            )

        # Check connector budget if applicable
        if connector:
            connector_check = self.check_budget(
                projected_cost,
                scope=BudgetScope.CONNECTOR,
                scope_id=connector,
            )
            if not connector_check.allowed:
                return connector_check
            warnings.extend(connector_check.warnings)

        # Check monthly budget
        monthly_check = self.check_budget(
            projected_cost,
            scope=BudgetScope.MONTHLY,
            scope_id="current",
        )

        # Combine warnings
        monthly_check.warnings.extend(warnings)

        return monthly_check

    def check_job_budget(
        self,
        projected_cost: float,
        business_id: Optional[str] = None,
    ) -> BudgetCheckResult:
        """
        Check budget for a job.

        Args:
            projected_cost: Expected job cost
            business_id: Business ID if applicable

        Returns:
            BudgetCheckResult
        """
        self._ensure_initialized()

        # Check per-job limit
        if projected_cost > self._config.per_job_limit:
            return BudgetCheckResult(
                allowed=False,
                outcome=BudgetPolicyOutcome.REQUIRES_APPROVAL,
                reason=f"Job cost ${projected_cost:.2f} exceeds limit ${self._config.per_job_limit:.2f}",
                projected_cost=projected_cost,
            )

        # Check global monthly
        return self.check_budget(
            projected_cost,
            scope=BudgetScope.MONTHLY,
            scope_id="current",
        )

    # =========================================================================
    # Budget Updates
    # =========================================================================

    def record_spend(
        self,
        amount: float,
        is_actual: bool = False,
        scope: BudgetScope = BudgetScope.MONTHLY,
        scope_id: Optional[str] = None,
        connector: Optional[str] = None,
    ) -> None:
        """
        Record spending against a budget.

        Args:
            amount: Amount spent
            is_actual: True if actual cost, False if estimated
            scope: Budget scope
            scope_id: ID within scope
            connector: Connector name (to also update connector budget)
        """
        self._ensure_initialized()

        # Update primary budget
        budget_id = f"budget_{scope.value}_{scope_id or 'default'}"
        budget = self._budgets.get(budget_id)

        if budget:
            budget.spent += amount
            if is_actual:
                budget.spent_actual += amount
            else:
                budget.spent_estimated += amount
            budget.last_updated = _utc_now().isoformat()

        # Also update connector budget if applicable
        if connector and scope != BudgetScope.CONNECTOR:
            conn_budget_id = f"budget_connector_{connector}"
            conn_budget = self._budgets.get(conn_budget_id)
            if conn_budget:
                conn_budget.spent += amount
                if is_actual:
                    conn_budget.spent_actual += amount
                else:
                    conn_budget.spent_estimated += amount
                conn_budget.last_updated = _utc_now().isoformat()

        # Always update monthly budget
        if scope != BudgetScope.MONTHLY:
            monthly_budget = self._budgets.get("budget_monthly_current")
            if monthly_budget:
                monthly_budget.spent += amount
                if is_actual:
                    monthly_budget.spent_actual += amount
                else:
                    monthly_budget.spent_estimated += amount
                monthly_budget.last_updated = _utc_now().isoformat()

    # =========================================================================
    # Budget Management
    # =========================================================================

    def set_budget(
        self,
        scope: BudgetScope,
        scope_id: Optional[str],
        limit: float,
        warning_threshold: float = 0.80,
        approval_threshold: float = 0.95,
    ) -> Budget:
        """
        Set or update a budget.

        Args:
            scope: Budget scope
            scope_id: ID within scope
            limit: Budget limit
            warning_threshold: Warning threshold
            approval_threshold: Approval threshold

        Returns:
            Updated Budget
        """
        self._ensure_initialized()

        budget_id = f"budget_{scope.value}_{scope_id or 'default'}"
        existing = self._budgets.get(budget_id)

        if existing:
            existing.limit = limit
            existing.warning_threshold = warning_threshold
            existing.approval_threshold = approval_threshold
            existing.last_updated = _utc_now().isoformat()
            return existing
        else:
            budget = self._create_budget(scope, scope_id, limit)
            budget.warning_threshold = warning_threshold
            budget.approval_threshold = approval_threshold
            return budget

    def get_budget(
        self,
        scope: BudgetScope,
        scope_id: Optional[str] = None,
    ) -> Optional[Budget]:
        """Get a specific budget."""
        self._ensure_initialized()
        budget_id = f"budget_{scope.value}_{scope_id or 'default'}"
        return self._budgets.get(budget_id)

    def get_all_budgets(self) -> List[Budget]:
        """Get all budgets."""
        self._ensure_initialized()
        return list(self._budgets.values())

    def get_monthly_budget(self) -> Optional[Budget]:
        """Get the current monthly budget."""
        return self.get_budget(BudgetScope.MONTHLY, "current")

    def reset_budget(
        self,
        scope: BudgetScope,
        scope_id: Optional[str] = None,
    ) -> bool:
        """Reset a budget's spending to zero."""
        self._ensure_initialized()

        budget_id = f"budget_{scope.value}_{scope_id or 'default'}"
        budget = self._budgets.get(budget_id)

        if budget:
            budget.spent = 0.0
            budget.spent_estimated = 0.0
            budget.spent_actual = 0.0
            budget.last_updated = _utc_now().isoformat()
            return True

        return False

    # =========================================================================
    # Budget Snapshots
    # =========================================================================

    def take_snapshot(
        self,
        scope: BudgetScope,
        scope_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Take a snapshot of a budget for persistence.

        Args:
            scope: Budget scope
            scope_id: ID within scope

        Returns:
            Snapshot dictionary
        """
        self._ensure_initialized()

        budget = self.get_budget(scope, scope_id)
        if not budget:
            return None

        snapshot = {
            "snapshot_id": _generate_snapshot_id(),
            "scope": budget.scope.value,
            "scope_id": budget.scope_id,
            "timestamp": _utc_now().isoformat(),
            "period_start": budget.period_start,
            "period_end": budget.period_end,
            "budget_limit": budget.limit,
            "spent_total": budget.spent,
            "spent_estimated": budget.spent_estimated,
            "spent_actual": budget.spent_actual,
            "remaining": budget.remaining,
            "utilization_pct": budget.utilization * 100,
            "metadata": {
                "warning_threshold": budget.warning_threshold,
                "approval_threshold": budget.approval_threshold,
            },
        }

        # Persist if available
        if self._persistence_manager:
            self._persistence_manager.persist_budget_snapshot(snapshot)

        return snapshot

    def take_all_snapshots(self) -> List[Dict[str, Any]]:
        """Take snapshots of all budgets."""
        snapshots = []
        for budget in self._budgets.values():
            snapshot = self.take_snapshot(budget.scope, budget.scope_id)
            if snapshot:
                snapshots.append(snapshot)
        return snapshots

    # =========================================================================
    # Summary and Stats
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """Get budget manager summary."""
        self._ensure_initialized()

        budgets_summary = []
        for budget in self._budgets.values():
            budgets_summary.append({
                "scope": budget.scope.value,
                "scope_id": budget.scope_id,
                "limit": budget.limit,
                "spent": budget.spent,
                "remaining": budget.remaining,
                "utilization": f"{budget.utilization:.0%}",
            })

        monthly = self.get_monthly_budget()

        return {
            "initialized": self._initialized,
            "budget_count": len(self._budgets),
            "budgets": budgets_summary,
            "monthly_remaining": monthly.remaining if monthly else 0,
            "monthly_utilization": f"{monthly.utilization:.0%}" if monthly else "N/A",
            "config": {
                "global_monthly_limit": self._config.global_monthly_limit,
                "per_action_limit": self._config.per_action_limit,
                "per_job_limit": self._config.per_job_limit,
                "enable_blocking": self._config.enable_blocking,
            },
        }


# Singleton instance
_budget_manager: Optional[BudgetManager] = None


def get_budget_manager() -> BudgetManager:
    """Get the global budget manager."""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = BudgetManager()
    return _budget_manager
