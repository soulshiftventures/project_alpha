"""
Capacity Manager for Project Alpha
Manages configurable capacity limits for portfolio scaling.
Replaces hardcoded limits with policy-driven capacity management.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class CapacityDecision(Enum):
    """Capacity decision outcomes."""
    ALLOWED = "allowed"
    WARNING = "warning"
    REQUIRES_APPROVAL = "requires_approval"
    BLOCKED = "blocked"


class CapacityDimension(Enum):
    """Dimensions tracked for capacity management."""
    BUSINESSES = "businesses"
    OPPORTUNITIES = "opportunities"
    JOBS = "jobs"
    PLANS = "plans"
    ACTIVE_OPERATIONS = "active_operations"


@dataclass
class CapacityLimit:
    """Represents a configurable capacity limit."""
    dimension: CapacityDimension
    soft_limit: Optional[int] = None  # Warning threshold (None = unlimited)
    hard_limit: Optional[int] = None  # Blocking threshold (None = unlimited)
    enabled: bool = True
    description: str = ""


@dataclass
class CapacityCheckContext:
    """Context for capacity check decisions."""
    dimension: CapacityDimension
    current_count: int
    requested_increment: int = 1
    business_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    plan_id: Optional[str] = None
    job_id: Optional[str] = None
    runtime_backend: Optional[str] = None
    estimated_cost: float = 0.0
    requires_approval: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapacityCheckResult:
    """Result of capacity check."""
    decision: CapacityDecision
    dimension: CapacityDimension
    current_count: int
    projected_count: int
    soft_limit: Optional[int]
    hard_limit: Optional[int]
    reason: str
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CapacityManager:
    """
    Manages configurable capacity limits across portfolio dimensions.

    Supports:
    - Soft limits (warnings)
    - Hard limits (blocking)
    - Unlimited mode (None limits)
    - Budget-aware capacity
    - Runtime-aware capacity
    - Domain-aware capacity
    - Operator overrides
    """

    def __init__(self, capacity_policies=None, state_store=None, budget_manager=None):
        """
        Initialize capacity manager.

        Args:
            capacity_policies: CapacityPolicies instance for policy evaluation
            state_store: StateStore instance for persistence
            budget_manager: BudgetManager instance for budget awareness
        """
        self.policies = capacity_policies
        self.state_store = state_store
        self.budget_manager = budget_manager

        # Default limits (can be overridden)
        self.limits: Dict[CapacityDimension, CapacityLimit] = {}
        self._init_default_limits()

        # Override tracking
        self.overrides: Dict[str, Dict[str, Any]] = {}

        # Capacity decision history
        self.decision_history: List[Dict] = []

    def _init_default_limits(self):
        """Initialize default capacity limits (all unlimited by default)."""
        for dimension in CapacityDimension:
            self.limits[dimension] = CapacityLimit(
                dimension=dimension,
                soft_limit=None,  # Unlimited
                hard_limit=None,  # Unlimited
                enabled=True,
                description=f"Default capacity limit for {dimension.value}"
            )

    def set_limit(
        self,
        dimension: CapacityDimension,
        soft_limit: Optional[int] = None,
        hard_limit: Optional[int] = None,
        enabled: bool = True,
        description: str = ""
    ):
        """
        Set or update capacity limit for a dimension.

        Args:
            dimension: Capacity dimension to configure
            soft_limit: Warning threshold (None = unlimited)
            hard_limit: Blocking threshold (None = unlimited)
            enabled: Whether limit is enforced
            description: Human-readable description
        """
        self.limits[dimension] = CapacityLimit(
            dimension=dimension,
            soft_limit=soft_limit,
            hard_limit=hard_limit,
            enabled=enabled,
            description=description or f"Capacity limit for {dimension.value}"
        )

        # Persist to state store if available
        if self.state_store:
            self._persist_limit(dimension)

    def get_limit(self, dimension: CapacityDimension) -> CapacityLimit:
        """Get capacity limit for a dimension."""
        return self.limits.get(dimension, CapacityLimit(dimension=dimension))

    def check_capacity(self, context: CapacityCheckContext) -> CapacityCheckResult:
        """
        Check if capacity is available for a given context.

        Args:
            context: Capacity check context

        Returns:
            CapacityCheckResult with decision and details
        """
        limit = self.limits.get(context.dimension)

        if not limit or not limit.enabled:
            # Capacity checks disabled for this dimension
            return CapacityCheckResult(
                decision=CapacityDecision.ALLOWED,
                dimension=context.dimension,
                current_count=context.current_count,
                projected_count=context.current_count + context.requested_increment,
                soft_limit=None,
                hard_limit=None,
                reason="Capacity checks disabled for this dimension"
            )

        projected_count = context.current_count + context.requested_increment
        warnings = []
        recommendations = []

        # Check hard limit first (blocking)
        if limit.hard_limit is not None and projected_count > limit.hard_limit:
            return CapacityCheckResult(
                decision=CapacityDecision.BLOCKED,
                dimension=context.dimension,
                current_count=context.current_count,
                projected_count=projected_count,
                soft_limit=limit.soft_limit,
                hard_limit=limit.hard_limit,
                reason=f"Hard limit reached: {context.current_count}/{limit.hard_limit} {context.dimension.value}",
                warnings=[f"Cannot exceed hard limit of {limit.hard_limit} {context.dimension.value}"],
                recommendations=[
                    f"Wait for existing {context.dimension.value} to complete",
                    "Consider increasing capacity limits",
                    "Review and terminate low-priority items"
                ]
            )

        # Check soft limit (warning)
        if limit.soft_limit is not None and projected_count > limit.soft_limit:
            warnings.append(f"Soft limit exceeded: {projected_count}/{limit.soft_limit} {context.dimension.value}")
            recommendations.append(f"Consider reviewing capacity before adding more {context.dimension.value}")

        # Budget-aware capacity check
        if self.budget_manager and context.estimated_cost > 0:
            budget_check = self._check_budget_capacity(context)
            if budget_check["blocked"]:
                return CapacityCheckResult(
                    decision=CapacityDecision.BLOCKED,
                    dimension=context.dimension,
                    current_count=context.current_count,
                    projected_count=projected_count,
                    soft_limit=limit.soft_limit,
                    hard_limit=limit.hard_limit,
                    reason=f"Budget capacity exceeded: {budget_check['reason']}",
                    warnings=[budget_check["reason"]],
                    recommendations=["Wait for budget reset or increase budget limits"]
                )
            elif budget_check["warning"]:
                warnings.append(budget_check["reason"])

        # Runtime-aware capacity check
        if context.runtime_backend:
            runtime_check = self._check_runtime_capacity(context)
            if runtime_check["blocked"]:
                return CapacityCheckResult(
                    decision=CapacityDecision.BLOCKED,
                    dimension=context.dimension,
                    current_count=context.current_count,
                    projected_count=projected_count,
                    soft_limit=limit.soft_limit,
                    hard_limit=limit.hard_limit,
                    reason=f"Runtime capacity exceeded: {runtime_check['reason']}",
                    warnings=[runtime_check["reason"]],
                    recommendations=["Wait for runtime capacity or use different backend"]
                )
            elif runtime_check["warning"]:
                warnings.append(runtime_check["reason"])

        # Policy-based capacity check
        if self.policies:
            policy_result = self.policies.evaluate_capacity(context)
            if policy_result.get("requires_approval"):
                return CapacityCheckResult(
                    decision=CapacityDecision.REQUIRES_APPROVAL,
                    dimension=context.dimension,
                    current_count=context.current_count,
                    projected_count=projected_count,
                    soft_limit=limit.soft_limit,
                    hard_limit=limit.hard_limit,
                    reason=policy_result.get("reason", "Capacity requires operator approval"),
                    warnings=warnings,
                    recommendations=policy_result.get("recommendations", [])
                )

        # Check if already requires approval from context
        if context.requires_approval:
            return CapacityCheckResult(
                decision=CapacityDecision.REQUIRES_APPROVAL,
                dimension=context.dimension,
                current_count=context.current_count,
                projected_count=projected_count,
                soft_limit=limit.soft_limit,
                hard_limit=limit.hard_limit,
                reason="Operation requires operator approval",
                warnings=warnings,
                recommendations=recommendations
            )

        # Determine final decision
        if warnings:
            decision = CapacityDecision.WARNING
            reason = "Capacity available with warnings"
        else:
            decision = CapacityDecision.ALLOWED
            reason = "Capacity available"

        result = CapacityCheckResult(
            decision=decision,
            dimension=context.dimension,
            current_count=context.current_count,
            projected_count=projected_count,
            soft_limit=limit.soft_limit,
            hard_limit=limit.hard_limit,
            reason=reason,
            warnings=warnings,
            recommendations=recommendations
        )

        # Record decision
        self._record_decision(context, result)

        return result

    def _check_budget_capacity(self, context: CapacityCheckContext) -> Dict[str, Any]:
        """Check budget-aware capacity constraints."""
        if not self.budget_manager:
            return {"blocked": False, "warning": False}

        # Check if adding this operation would exceed budget
        try:
            # This is a simplified check - real implementation would be more sophisticated
            global_budget = self.budget_manager.get_budget("GLOBAL")
            if global_budget:
                remaining = global_budget.limit - global_budget.spent
                if context.estimated_cost > remaining:
                    return {
                        "blocked": True,
                        "warning": False,
                        "reason": f"Insufficient budget: ${context.estimated_cost:.2f} needed, ${remaining:.2f} available"
                    }
                elif context.estimated_cost > remaining * 0.2:
                    return {
                        "blocked": False,
                        "warning": True,
                        "reason": f"Budget running low: ${remaining:.2f} remaining"
                    }
        except Exception:
            pass

        return {"blocked": False, "warning": False}

    def _check_runtime_capacity(self, context: CapacityCheckContext) -> Dict[str, Any]:
        """Check runtime backend capacity constraints."""
        # Simplified runtime capacity check
        # Real implementation would query runtime manager for backend availability

        # For now, just warn if using limited backends
        if context.runtime_backend in ["INLINE_LOCAL"]:
            return {
                "blocked": False,
                "warning": True,
                "reason": f"Using limited runtime backend: {context.runtime_backend}"
            }

        return {"blocked": False, "warning": False}

    def _record_decision(self, context: CapacityCheckContext, result: CapacityCheckResult):
        """Record capacity decision for audit trail."""
        decision_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dimension": context.dimension.value,
            "decision": result.decision.value,
            "current_count": context.current_count,
            "projected_count": result.projected_count,
            "reason": result.reason,
            "context": {
                "business_id": context.business_id,
                "opportunity_id": context.opportunity_id,
                "plan_id": context.plan_id,
                "job_id": context.job_id,
                "runtime_backend": context.runtime_backend,
                "estimated_cost": context.estimated_cost
            }
        }

        self.decision_history.append(decision_record)

        # Persist to state store if available
        if self.state_store:
            try:
                self.state_store.save_capacity_decision(decision_record)
            except AttributeError:
                # State store doesn't support capacity decisions yet
                pass

    def _persist_limit(self, dimension: CapacityDimension):
        """Persist capacity limit to state store."""
        if not self.state_store:
            return

        limit = self.limits.get(dimension)
        if limit:
            try:
                self.state_store.save_capacity_limit(dimension.value, {
                    "soft_limit": limit.soft_limit,
                    "hard_limit": limit.hard_limit,
                    "enabled": limit.enabled,
                    "description": limit.description
                })
            except AttributeError:
                # State store doesn't support capacity limits yet
                pass

    def get_capacity_status(self) -> Dict[str, Any]:
        """
        Get current capacity status across all dimensions.

        Returns:
            Dictionary with capacity status for all dimensions
        """
        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dimensions": {},
            "overall_utilization": 0.0,
            "warnings": [],
            "bottlenecks": []
        }

        total_utilization = 0.0
        dimension_count = 0

        for dimension, limit in self.limits.items():
            if not limit.enabled:
                continue

            # Get current count for this dimension
            current_count = self._get_current_count(dimension)

            # Calculate utilization
            utilization = 0.0
            if limit.hard_limit and limit.hard_limit > 0:
                utilization = current_count / limit.hard_limit
            elif limit.soft_limit and limit.soft_limit > 0:
                utilization = current_count / limit.soft_limit

            dimension_status = {
                "current_count": current_count,
                "soft_limit": limit.soft_limit,
                "hard_limit": limit.hard_limit,
                "utilization": round(utilization, 2),
                "mode": "unlimited" if limit.soft_limit is None and limit.hard_limit is None else "limited"
            }

            # Check for warnings
            if limit.soft_limit and current_count >= limit.soft_limit:
                status["warnings"].append(f"{dimension.value}: at or above soft limit")

            # Check for bottlenecks
            if limit.hard_limit and current_count >= limit.hard_limit * 0.9:
                status["bottlenecks"].append(f"{dimension.value}: near hard limit")

            status["dimensions"][dimension.value] = dimension_status

            if utilization > 0:
                total_utilization += utilization
                dimension_count += 1

        status["overall_utilization"] = round(
            total_utilization / max(dimension_count, 1),
            2
        )

        return status

    def _get_current_count(self, dimension: CapacityDimension) -> int:
        """Get current count for a capacity dimension."""
        if not self.state_store:
            return 0

        try:
            if dimension == CapacityDimension.BUSINESSES:
                # Count active businesses
                businesses = self.state_store.list_businesses()
                return len([b for b in businesses if b.get("stage") != "TERMINATED"])
            elif dimension == CapacityDimension.OPPORTUNITIES:
                opportunities = self.state_store.list_opportunities()
                return len([o for o in opportunities if o.get("status") != "archived"])
            elif dimension == CapacityDimension.JOBS:
                jobs = self.state_store.list_jobs()
                return len([j for j in jobs if j.get("status") in ["pending", "running"]])
            elif dimension == CapacityDimension.PLANS:
                plans = self.state_store.list_plans()
                return len([p for p in plans if p.get("status") not in ["completed", "cancelled"]])
            elif dimension == CapacityDimension.ACTIVE_OPERATIONS:
                # Sum of all active operations
                jobs = self.state_store.list_jobs()
                plans = self.state_store.list_plans()
                return (
                    len([j for j in jobs if j.get("status") in ["pending", "running"]]) +
                    len([p for p in plans if p.get("status") not in ["completed", "cancelled"]])
                )
        except (AttributeError, KeyError):
            pass

        return 0

    def set_override(
        self,
        override_id: str,
        dimension: CapacityDimension,
        reason: str,
        duration_minutes: Optional[int] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Set a capacity override (operator action).

        Args:
            override_id: Unique override identifier
            dimension: Dimension to override
            reason: Reason for override
            duration_minutes: How long override lasts (None = permanent)
            metadata: Additional override metadata
        """
        self.overrides[override_id] = {
            "dimension": dimension.value,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration_minutes": duration_minutes,
            "metadata": metadata or {}
        }

    def remove_override(self, override_id: str):
        """Remove a capacity override."""
        self.overrides.pop(override_id, None)

    def get_overrides(self) -> Dict[str, Dict]:
        """Get all active overrides."""
        return dict(self.overrides)
