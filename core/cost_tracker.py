"""
Cost Tracker for Project Alpha.

Tracks estimated and actual costs across all operations.

ARCHITECTURE:
- Records cost metadata for jobs, connectors, plans
- Persists to state store for restart safety
- Provides cost aggregation and reporting
- Integrates with budget manager for enforcement

COST TYPES:
- Estimated: Projected cost before execution
- Actual: Known cost after execution (when available)
- Unknown: Cost that cannot be determined
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from .cost_model import (
    CostClass,
    CostConfidence,
    CostEstimate,
    CostMetadata,
    get_connector_cost_estimate,
    get_backend_cost_estimate,
    estimate_plan_cost,
)

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def _generate_cost_id() -> str:
    """Generate a unique cost record ID."""
    return f"cost_{_utc_now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


@dataclass
class CostSummary:
    """Summary of costs over a period."""
    total_estimated: float = 0.0
    total_actual: float = 0.0
    total_unknown: int = 0
    record_count: int = 0
    by_connector: Dict[str, float] = field(default_factory=dict)
    by_backend: Dict[str, float] = field(default_factory=dict)
    by_business: Dict[str, float] = field(default_factory=dict)
    by_cost_class: Dict[str, int] = field(default_factory=dict)
    period_start: Optional[str] = None
    period_end: Optional[str] = None

    @property
    def total_effective(self) -> float:
        """Get total effective cost (actual where known, else estimated)."""
        return self.total_actual if self.total_actual > 0 else self.total_estimated

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_estimated": self.total_estimated,
            "total_actual": self.total_actual,
            "total_unknown": self.total_unknown,
            "total_effective": self.total_effective,
            "record_count": self.record_count,
            "by_connector": self.by_connector,
            "by_backend": self.by_backend,
            "by_business": self.by_business,
            "by_cost_class": self.by_cost_class,
            "period_start": self.period_start,
            "period_end": self.period_end,
        }


class CostTracker:
    """
    Tracks costs across all operations.

    Records cost metadata and provides aggregation capabilities.
    """

    def __init__(self, persistence_manager=None):
        """Initialize the cost tracker."""
        self._persistence_manager = persistence_manager
        self._in_memory_costs: List[CostMetadata] = []
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialize persistence manager."""
        if self._initialized:
            return

        if self._persistence_manager is None:
            try:
                from .persistence_manager import get_persistence_manager
                self._persistence_manager = get_persistence_manager()
            except Exception as e:
                logger.warning(f"Persistence not available: {e}")

        self._initialized = True

    # =========================================================================
    # Cost Recording
    # =========================================================================

    def record_estimated_cost(
        self,
        record_type: str,
        record_id: str,
        estimate: CostEstimate,
        connector: Optional[str] = None,
        operation: Optional[str] = None,
        backend: Optional[str] = None,
        business_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> CostMetadata:
        """
        Record an estimated cost.

        Args:
            record_type: Type of record (job, plan, connector, etc.)
            record_id: ID of the record
            estimate: Cost estimate
            connector: Connector name if applicable
            operation: Operation name if applicable
            backend: Backend type if applicable
            business_id: Business ID if applicable
            plan_id: Plan ID if applicable
            job_id: Job ID if applicable

        Returns:
            CostMetadata record
        """
        self._ensure_initialized()

        cost = CostMetadata(
            cost_id=_generate_cost_id(),
            record_type=record_type,
            record_id=record_id,
            estimated_cost=estimate.amount,
            cost_unknown=estimate.is_unknown,
            cost_class=estimate.cost_class,
            confidence=estimate.confidence,
            currency=estimate.currency,
            connector=connector,
            operation=operation,
            backend=backend,
            business_id=business_id,
            plan_id=plan_id,
            job_id=job_id,
            notes=estimate.notes,
        )

        # Store in memory
        self._in_memory_costs.append(cost)

        # Persist if available
        if self._persistence_manager:
            self._persistence_manager.persist_cost_record(cost.to_dict())

        logger.debug(f"Recorded estimated cost: {cost.cost_id} = ${estimate.amount:.4f}")

        return cost

    def record_actual_cost(
        self,
        cost_id: str,
        actual_amount: float,
        notes: str = "",
    ) -> Optional[CostMetadata]:
        """
        Update a cost record with actual known cost.

        Args:
            cost_id: ID of cost record to update
            actual_amount: Actual cost amount
            notes: Additional notes

        Returns:
            Updated CostMetadata or None if not found
        """
        self._ensure_initialized()

        # Find in memory
        for cost in self._in_memory_costs:
            if cost.cost_id == cost_id:
                cost.actual_cost = actual_amount
                cost.notes = notes if notes else cost.notes

                # Update persistence
                if self._persistence_manager:
                    self._persistence_manager.persist_cost_record(cost.to_dict())

                logger.debug(f"Updated actual cost: {cost_id} = ${actual_amount:.4f}")
                return cost

        return None

    def record_connector_execution_cost(
        self,
        connector: str,
        operation: str,
        execution_id: str,
        success: bool,
        duration_seconds: float,
        business_id: Optional[str] = None,
    ) -> CostMetadata:
        """
        Record cost for a connector execution.

        Args:
            connector: Connector name
            operation: Operation name
            execution_id: Execution ID
            success: Whether execution succeeded
            duration_seconds: Execution duration
            business_id: Business ID if applicable

        Returns:
            CostMetadata record
        """
        # Get estimate for this connector/operation
        estimate = get_connector_cost_estimate(connector, operation)

        # Record the cost
        cost = self.record_estimated_cost(
            record_type="connector",
            record_id=execution_id,
            estimate=estimate,
            connector=connector,
            operation=operation,
            business_id=business_id,
        )

        # Add execution metadata
        cost.metadata["duration_seconds"] = duration_seconds
        cost.metadata["success"] = success

        return cost

    def record_job_cost(
        self,
        job_id: str,
        plan_id: str,
        backend: str,
        step_count: int,
        business_id: Optional[str] = None,
        estimated_cost: Optional[float] = None,
    ) -> CostMetadata:
        """
        Record cost for a job execution.

        Args:
            job_id: Job ID
            plan_id: Plan ID
            backend: Backend type
            step_count: Number of steps
            business_id: Business ID if applicable
            estimated_cost: Pre-calculated estimate if available

        Returns:
            CostMetadata record
        """
        if estimated_cost is not None:
            estimate = CostEstimate.from_amount(
                estimated_cost,
                CostConfidence.MEDIUM,
                f"Job with {step_count} steps",
            )
        else:
            # Calculate from backend
            backend_estimate = get_backend_cost_estimate(backend)
            # Scale by step count for rough estimate
            amount = backend_estimate.amount * max(1, step_count)
            estimate = CostEstimate.from_amount(
                amount,
                backend_estimate.confidence,
                f"Job on {backend} with {step_count} steps",
            )

        return self.record_estimated_cost(
            record_type="job",
            record_id=job_id,
            estimate=estimate,
            backend=backend,
            business_id=business_id,
            plan_id=plan_id,
            job_id=job_id,
        )

    def record_plan_cost(
        self,
        plan_id: str,
        request_id: str,
        steps: List[Dict[str, Any]],
        backend: str = "inline_local",
        business_id: Optional[str] = None,
    ) -> CostMetadata:
        """
        Record cost for an execution plan.

        Args:
            plan_id: Plan ID
            request_id: Request ID
            steps: Plan steps
            backend: Backend type
            business_id: Business ID if applicable

        Returns:
            CostMetadata record
        """
        estimate = estimate_plan_cost(steps, backend)

        return self.record_estimated_cost(
            record_type="plan",
            record_id=plan_id,
            estimate=estimate,
            backend=backend,
            business_id=business_id,
            plan_id=plan_id,
        )

    # =========================================================================
    # Cost Queries
    # =========================================================================

    def get_cost(self, cost_id: str) -> Optional[CostMetadata]:
        """Get a cost record by ID."""
        for cost in self._in_memory_costs:
            if cost.cost_id == cost_id:
                return cost
        return None

    def get_costs_for_record(
        self,
        record_type: str,
        record_id: str,
    ) -> List[CostMetadata]:
        """Get all cost records for a specific record."""
        return [
            c for c in self._in_memory_costs
            if c.record_type == record_type and c.record_id == record_id
        ]

    def get_costs_for_job(self, job_id: str) -> List[CostMetadata]:
        """Get all cost records for a job."""
        return [c for c in self._in_memory_costs if c.job_id == job_id]

    def get_costs_for_plan(self, plan_id: str) -> List[CostMetadata]:
        """Get all cost records for a plan."""
        return [c for c in self._in_memory_costs if c.plan_id == plan_id]

    def get_costs_for_business(self, business_id: str) -> List[CostMetadata]:
        """Get all cost records for a business."""
        return [c for c in self._in_memory_costs if c.business_id == business_id]

    def get_costs_for_connector(self, connector: str) -> List[CostMetadata]:
        """Get all cost records for a connector."""
        return [c for c in self._in_memory_costs if c.connector == connector]

    def get_recent_costs(self, limit: int = 100) -> List[CostMetadata]:
        """Get most recent cost records."""
        return list(reversed(self._in_memory_costs[-limit:]))

    # =========================================================================
    # Cost Aggregation
    # =========================================================================

    def get_summary(
        self,
        costs: Optional[List[CostMetadata]] = None,
    ) -> CostSummary:
        """
        Get aggregated cost summary.

        Args:
            costs: Costs to aggregate (defaults to all in-memory)

        Returns:
            CostSummary with aggregated data
        """
        if costs is None:
            costs = self._in_memory_costs

        summary = CostSummary(record_count=len(costs))

        for cost in costs:
            # Totals
            summary.total_estimated += cost.estimated_cost
            if cost.actual_cost is not None:
                summary.total_actual += cost.actual_cost
            if cost.cost_unknown:
                summary.total_unknown += 1

            # By connector
            if cost.connector:
                effective = cost.actual_cost if cost.actual_cost else cost.estimated_cost
                summary.by_connector[cost.connector] = (
                    summary.by_connector.get(cost.connector, 0) + effective
                )

            # By backend
            if cost.backend:
                effective = cost.actual_cost if cost.actual_cost else cost.estimated_cost
                summary.by_backend[cost.backend] = (
                    summary.by_backend.get(cost.backend, 0) + effective
                )

            # By business
            if cost.business_id:
                effective = cost.actual_cost if cost.actual_cost else cost.estimated_cost
                summary.by_business[cost.business_id] = (
                    summary.by_business.get(cost.business_id, 0) + effective
                )

            # By cost class
            cc = cost.cost_class.value
            summary.by_cost_class[cc] = summary.by_cost_class.get(cc, 0) + 1

        # Set period bounds
        if costs:
            timestamps = [c.timestamp for c in costs if c.timestamp]
            if timestamps:
                summary.period_start = min(timestamps)
                summary.period_end = max(timestamps)

        return summary

    def get_connector_summary(self, connector: str) -> CostSummary:
        """Get cost summary for a specific connector."""
        costs = self.get_costs_for_connector(connector)
        return self.get_summary(costs)

    def get_business_summary(self, business_id: str) -> CostSummary:
        """Get cost summary for a specific business."""
        costs = self.get_costs_for_business(business_id)
        return self.get_summary(costs)

    def get_total_estimated(self) -> float:
        """Get total estimated costs."""
        return sum(c.estimated_cost for c in self._in_memory_costs)

    def get_total_actual(self) -> float:
        """Get total actual costs (where known)."""
        return sum(c.actual_cost or 0 for c in self._in_memory_costs)

    def get_total_effective(self) -> float:
        """Get total effective cost (actual where known, else estimated)."""
        return sum(c.get_effective_cost() for c in self._in_memory_costs)

    # =========================================================================
    # Cost Projection
    # =========================================================================

    def project_operation_cost(
        self,
        connector: str,
        operation: str,
        count: int = 1,
    ) -> Tuple[CostEstimate, float]:
        """
        Project cost for future operations.

        Args:
            connector: Connector name
            operation: Operation name
            count: Number of operations

        Returns:
            Tuple of (unit estimate, total projected)
        """
        unit_estimate = get_connector_cost_estimate(connector, operation)
        total = unit_estimate.amount * count
        return unit_estimate, total

    def project_plan_cost(
        self,
        steps: List[Dict[str, Any]],
        backend: str = "inline_local",
    ) -> CostEstimate:
        """
        Project cost for a plan.

        Args:
            steps: Plan steps
            backend: Backend type

        Returns:
            Cost estimate
        """
        return estimate_plan_cost(steps, backend)

    # =========================================================================
    # Stats and Lifecycle
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        summary = self.get_summary()

        return {
            "total_records": len(self._in_memory_costs),
            "total_estimated": summary.total_estimated,
            "total_actual": summary.total_actual,
            "total_unknown": summary.total_unknown,
            "by_connector": summary.by_connector,
            "by_backend": summary.by_backend,
            "by_cost_class": summary.by_cost_class,
            "persistence_available": self._persistence_manager is not None,
        }

    def clear_in_memory(self) -> int:
        """Clear in-memory costs (persisted data retained)."""
        count = len(self._in_memory_costs)
        self._in_memory_costs = []
        return count


# Singleton instance
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
