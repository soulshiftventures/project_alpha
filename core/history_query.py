"""
History Query Interface for Project Alpha.

Provides a clean query interface for accessing persisted operational records.
Supports filtering, pagination, aggregation, and cross-entity queries.

ARCHITECTURE:
- Delegates to PersistenceManager/StateStore for data access
- Provides high-level query methods for common use cases
- Supports time-range queries for cost analysis
- Aggregates data across related entities
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class TimeRange(Enum):
    """Predefined time ranges for queries."""
    LAST_HOUR = "last_hour"
    LAST_24_HOURS = "last_24_hours"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    THIS_MONTH = "this_month"
    CUSTOM = "custom"


@dataclass
class QueryFilter:
    """Filter parameters for history queries."""
    time_range: Optional[TimeRange] = None
    start_time: Optional[str] = None  # ISO format
    end_time: Optional[str] = None    # ISO format
    status: Optional[str] = None
    connector: Optional[str] = None
    business_id: Optional[str] = None
    plan_id: Optional[str] = None
    job_id: Optional[str] = None
    record_type: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    cost_class: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass
class AggregatedCosts:
    """Aggregated cost statistics."""
    total_estimated: float = 0.0
    total_actual: float = 0.0
    total_unknown_count: int = 0
    record_count: int = 0
    by_connector: Dict[str, float] = field(default_factory=dict)
    by_backend: Dict[str, float] = field(default_factory=dict)
    by_business: Dict[str, float] = field(default_factory=dict)
    by_cost_class: Dict[str, float] = field(default_factory=dict)
    period_start: Optional[str] = None
    period_end: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_estimated": self.total_estimated,
            "total_actual": self.total_actual,
            "total_unknown_count": self.total_unknown_count,
            "record_count": self.record_count,
            "by_connector": self.by_connector,
            "by_backend": self.by_backend,
            "by_business": self.by_business,
            "by_cost_class": self.by_cost_class,
            "period_start": self.period_start,
            "period_end": self.period_end,
        }


@dataclass
class HistorySummary:
    """Summary of historical records."""
    total_approvals: int = 0
    pending_approvals: int = 0
    approved_count: int = 0
    denied_count: int = 0
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_plans: int = 0
    total_promotions: int = 0
    used_promotions: int = 0
    total_events: int = 0
    error_events: int = 0
    total_cost_records: int = 0
    aggregated_costs: Optional[AggregatedCosts] = None
    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "total_approvals": self.total_approvals,
            "pending_approvals": self.pending_approvals,
            "approved_count": self.approved_count,
            "denied_count": self.denied_count,
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "total_plans": self.total_plans,
            "total_promotions": self.total_promotions,
            "used_promotions": self.used_promotions,
            "total_events": self.total_events,
            "error_events": self.error_events,
            "total_cost_records": self.total_cost_records,
            "timestamp": self.timestamp,
        }
        if self.aggregated_costs:
            result["aggregated_costs"] = self.aggregated_costs.to_dict()
        return result


class HistoryQuery:
    """
    Query interface for historical records.

    Provides convenient methods for accessing persisted data.
    """

    def __init__(self, persistence_manager=None):
        """Initialize the history query interface."""
        self._persistence_manager = persistence_manager
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Ensure persistence manager is available."""
        if self._initialized:
            return True

        if self._persistence_manager is None:
            try:
                from .persistence_manager import get_persistence_manager
                self._persistence_manager = get_persistence_manager()
                if not self._persistence_manager.is_initialized:
                    self._persistence_manager.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize persistence: {e}")
                return False

        self._initialized = True
        return True

    def _get_time_bounds(
        self,
        time_range: Optional[TimeRange],
        start_time: Optional[str],
        end_time: Optional[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert time range to start/end bounds."""
        if time_range is None or time_range == TimeRange.CUSTOM:
            return start_time, end_time

        now = _utc_now()

        if time_range == TimeRange.LAST_HOUR:
            start = now - timedelta(hours=1)
        elif time_range == TimeRange.LAST_24_HOURS:
            start = now - timedelta(hours=24)
        elif time_range == TimeRange.LAST_7_DAYS:
            start = now - timedelta(days=7)
        elif time_range == TimeRange.LAST_30_DAYS:
            start = now - timedelta(days=30)
        elif time_range == TimeRange.THIS_MONTH:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return start_time, end_time

        return start.isoformat(), now.isoformat()

    # =========================================================================
    # Approval Queries
    # =========================================================================

    def get_approvals(
        self,
        filter: Optional[QueryFilter] = None,
    ) -> List[Dict[str, Any]]:
        """Get approval records with optional filtering."""
        if not self._ensure_initialized():
            return []

        filter = filter or QueryFilter()

        return self._persistence_manager.get_persisted_approvals(
            status=filter.status,
            limit=filter.limit,
        )

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approvals."""
        if not self._ensure_initialized():
            return []

        return self._persistence_manager.get_persisted_approvals(status="pending")

    def get_approval_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific approval by ID."""
        if not self._ensure_initialized():
            return None

        approvals = self._persistence_manager.get_persisted_approvals(limit=1000)
        for approval in approvals:
            if approval.get("record_id") == record_id:
                return approval
        return None

    # =========================================================================
    # Job Queries
    # =========================================================================

    def get_jobs(
        self,
        filter: Optional[QueryFilter] = None,
    ) -> List[Dict[str, Any]]:
        """Get job records with optional filtering."""
        if not self._ensure_initialized():
            return []

        filter = filter or QueryFilter()

        return self._persistence_manager.get_persisted_jobs(
            status=filter.status,
            limit=filter.limit,
        )

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get jobs that are not yet complete."""
        if not self._ensure_initialized():
            return []

        all_jobs = self._persistence_manager.get_persisted_jobs(limit=500)
        active_statuses = {"pending", "running", "queued"}
        return [j for j in all_jobs if j.get("status") in active_statuses]

    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific job by ID."""
        if not self._ensure_initialized():
            return None

        jobs = self._persistence_manager.get_persisted_jobs(limit=1000)
        for job in jobs:
            if job.get("job_id") == job_id:
                return job
        return None

    # =========================================================================
    # Execution Plan Queries
    # =========================================================================

    def get_plans(
        self,
        filter: Optional[QueryFilter] = None,
    ) -> List[Dict[str, Any]]:
        """Get execution plan records."""
        if not self._ensure_initialized():
            return []

        filter = filter or QueryFilter()

        return self._persistence_manager.get_persisted_plans(limit=filter.limit)

    def get_plan_by_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific plan by ID."""
        if not self._ensure_initialized():
            return None

        plans = self._persistence_manager.get_persisted_plans(limit=500)
        for plan in plans:
            if plan.get("plan_id") == plan_id:
                return plan
        return None

    # =========================================================================
    # Live Mode Promotion Queries
    # =========================================================================

    def get_promotions(
        self,
        used: Optional[bool] = None,
        filter: Optional[QueryFilter] = None,
    ) -> List[Dict[str, Any]]:
        """Get live mode promotions."""
        if not self._ensure_initialized():
            return []

        filter = filter or QueryFilter()

        return self._persistence_manager.get_persisted_promotions(
            used=used,
            limit=filter.limit,
        )

    def get_active_promotions(self) -> List[Dict[str, Any]]:
        """Get unused promotions."""
        return self.get_promotions(used=False)

    # =========================================================================
    # Event Queries
    # =========================================================================

    def get_events(
        self,
        filter: Optional[QueryFilter] = None,
    ) -> List[Dict[str, Any]]:
        """Get event records with optional filtering."""
        if not self._ensure_initialized():
            return []

        filter = filter or QueryFilter()

        return self._persistence_manager.get_persisted_events(
            event_type=filter.event_type,
            severity=filter.severity,
            limit=filter.limit,
        )

    def get_error_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get error-severity events."""
        if not self._ensure_initialized():
            return []

        return self._persistence_manager.get_persisted_events(
            severity="error",
            limit=limit,
        )

    def get_cost_related_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events related to costs."""
        if not self._ensure_initialized():
            return []

        all_events = self._persistence_manager.get_persisted_events(limit=limit * 2)
        return [e for e in all_events if e.get("cost_related")][:limit]

    # =========================================================================
    # Cost Queries
    # =========================================================================

    def get_cost_records(
        self,
        filter: Optional[QueryFilter] = None,
    ) -> List[Dict[str, Any]]:
        """Get cost records with optional filtering."""
        if not self._ensure_initialized():
            return []

        filter = filter or QueryFilter()

        return self._persistence_manager.get_persisted_cost_records(
            record_type=filter.record_type,
            connector=filter.connector,
            business_id=filter.business_id,
            limit=filter.limit,
        )

    def get_aggregated_costs(
        self,
        filter: Optional[QueryFilter] = None,
    ) -> AggregatedCosts:
        """Get aggregated cost statistics."""
        if not self._ensure_initialized():
            return AggregatedCosts()

        filter = filter or QueryFilter()

        start, end = self._get_time_bounds(
            filter.time_range,
            filter.start_time,
            filter.end_time,
        )

        records = self._persistence_manager.get_persisted_cost_records(
            record_type=filter.record_type,
            connector=filter.connector,
            business_id=filter.business_id,
            limit=10000,  # Get more for aggregation
        )

        # Filter by time range if specified
        if start or end:
            filtered = []
            for r in records:
                ts = r.get("timestamp", "")
                if start and ts < start:
                    continue
                if end and ts > end:
                    continue
                filtered.append(r)
            records = filtered

        # Aggregate
        result = AggregatedCosts(
            period_start=start,
            period_end=end,
            record_count=len(records),
        )

        for r in records:
            est = r.get("estimated_cost") or 0.0
            act = r.get("actual_cost") or 0.0
            unknown = r.get("cost_unknown", False)

            result.total_estimated += est
            result.total_actual += act

            if unknown:
                result.total_unknown_count += 1

            # By connector
            conn = r.get("connector")
            if conn:
                result.by_connector[conn] = result.by_connector.get(conn, 0) + (act or est)

            # By backend
            backend = r.get("backend")
            if backend:
                result.by_backend[backend] = result.by_backend.get(backend, 0) + (act or est)

            # By business
            biz = r.get("business_id")
            if biz:
                result.by_business[biz] = result.by_business.get(biz, 0) + (act or est)

            # By cost class
            cc = r.get("cost_class")
            if cc:
                result.by_cost_class[cc] = result.by_cost_class.get(cc, 0) + (act or est)

        return result

    # =========================================================================
    # Budget Queries
    # =========================================================================

    def get_budget_snapshots(
        self,
        scope: Optional[str] = None,
        scope_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get budget snapshots."""
        if not self._ensure_initialized():
            return []

        return self._persistence_manager.get_persisted_budget_snapshots(
            scope=scope,
            scope_id=scope_id,
            limit=limit,
        )

    def get_latest_budget_snapshot(
        self,
        scope: str,
        scope_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent budget snapshot for a scope."""
        snapshots = self.get_budget_snapshots(
            scope=scope,
            scope_id=scope_id,
            limit=1,
        )
        return snapshots[0] if snapshots else None

    # =========================================================================
    # Cross-Entity Queries
    # =========================================================================

    def get_plan_with_job(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a plan along with its associated job."""
        plan = self.get_plan_by_id(plan_id)
        if not plan:
            return None

        job_id = plan.get("job_id")
        if job_id:
            job = self.get_job_by_id(job_id)
            plan["job"] = job

        return plan

    def get_job_with_costs(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job along with its cost records."""
        job = self.get_job_by_id(job_id)
        if not job:
            return None

        cost_filter = QueryFilter(job_id=job_id, limit=100)
        costs = self.get_cost_records(cost_filter)
        job["cost_records"] = costs

        return job

    def get_business_costs(
        self,
        business_id: str,
        time_range: Optional[TimeRange] = None,
    ) -> Dict[str, Any]:
        """Get all costs for a business."""
        filter = QueryFilter(
            business_id=business_id,
            time_range=time_range,
            limit=1000,
        )

        costs = self.get_cost_records(filter)
        aggregated = self.get_aggregated_costs(filter)

        return {
            "business_id": business_id,
            "cost_records": costs,
            "aggregated": aggregated.to_dict(),
        }

    def get_connector_costs(
        self,
        connector: str,
        time_range: Optional[TimeRange] = None,
    ) -> Dict[str, Any]:
        """Get all costs for a connector."""
        filter = QueryFilter(
            connector=connector,
            time_range=time_range,
            limit=1000,
        )

        costs = self.get_cost_records(filter)
        aggregated = self.get_aggregated_costs(filter)

        return {
            "connector": connector,
            "cost_records": costs,
            "aggregated": aggregated.to_dict(),
        }

    # =========================================================================
    # Summary
    # =========================================================================

    def get_summary(
        self,
        time_range: Optional[TimeRange] = None,
    ) -> HistorySummary:
        """Get a summary of all historical records."""
        if not self._ensure_initialized():
            return HistorySummary()

        summary = HistorySummary()

        # Approvals
        approvals = self._persistence_manager.get_persisted_approvals(limit=10000)
        summary.total_approvals = len(approvals)
        summary.pending_approvals = sum(1 for a in approvals if a.get("status") == "pending")
        summary.approved_count = sum(1 for a in approvals if a.get("status") == "approved")
        summary.denied_count = sum(1 for a in approvals if a.get("status") == "denied")

        # Jobs
        jobs = self._persistence_manager.get_persisted_jobs(limit=10000)
        summary.total_jobs = len(jobs)
        summary.completed_jobs = sum(1 for j in jobs if j.get("status") == "completed")
        summary.failed_jobs = sum(1 for j in jobs if j.get("status") == "failed")

        # Plans
        plans = self._persistence_manager.get_persisted_plans(limit=10000)
        summary.total_plans = len(plans)

        # Promotions
        promotions = self._persistence_manager.get_persisted_promotions(limit=10000)
        summary.total_promotions = len(promotions)
        summary.used_promotions = sum(1 for p in promotions if p.get("used"))

        # Events
        events = self._persistence_manager.get_persisted_events(limit=10000)
        summary.total_events = len(events)
        summary.error_events = sum(1 for e in events if e.get("severity") == "error")

        # Costs
        filter = QueryFilter(time_range=time_range)
        cost_records = self.get_cost_records(QueryFilter(limit=10000))
        summary.total_cost_records = len(cost_records)
        summary.aggregated_costs = self.get_aggregated_costs(filter)

        return summary


# Singleton instance
_history_query: Optional[HistoryQuery] = None


def get_history_query() -> HistoryQuery:
    """Get the global history query interface."""
    global _history_query
    if _history_query is None:
        _history_query = HistoryQuery()
    return _history_query
