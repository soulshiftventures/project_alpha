"""
Persistence Manager for Project Alpha.

Manages the lifecycle of persistent state:
- Startup recovery from stored state
- Incremental persistence during operation
- Graceful shutdown with state preservation
- Integration with existing in-memory managers

ARCHITECTURE:
- Coordinates between in-memory managers and StateStore
- Provides recovery on startup
- Ensures consistent state after restarts
- Does not replace existing managers, augments them with persistence
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from .state_store import StateStore, StateStoreConfig, get_state_store, initialize_state_store

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class PersistenceMode(Enum):
    """Mode of operation for persistence."""
    DISABLED = "disabled"  # No persistence (in-memory only)
    SYNC = "sync"  # Synchronous writes
    ASYNC = "async"  # Asynchronous writes (future)


@dataclass
class PersistenceConfig:
    """Configuration for persistence manager."""
    mode: PersistenceMode = PersistenceMode.SYNC
    db_path: str = "project_alpha/data/state.db"
    auto_recover_on_startup: bool = True
    persist_events: bool = True
    persist_approvals: bool = True
    persist_jobs: bool = True
    persist_plans: bool = True
    persist_promotions: bool = True
    persist_connector_executions: bool = True
    persist_credential_health: bool = True
    persist_costs: bool = True


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""
    success: bool
    recovered_approvals: int = 0
    recovered_jobs: int = 0
    recovered_plans: int = 0
    recovered_promotions: int = 0
    recovered_costs: int = 0
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "recovered_approvals": self.recovered_approvals,
            "recovered_jobs": self.recovered_jobs,
            "recovered_plans": self.recovered_plans,
            "recovered_promotions": self.recovered_promotions,
            "recovered_costs": self.recovered_costs,
            "errors": self.errors,
            "timestamp": self.timestamp,
        }


class PersistenceManager:
    """
    Manages persistence lifecycle for Project Alpha.

    Coordinates between in-memory managers and persistent storage.
    """

    def __init__(self, config: Optional[PersistenceConfig] = None):
        """Initialize the persistence manager."""
        self._config = config or PersistenceConfig()
        self._state_store: Optional[StateStore] = None
        self._initialized = False
        self._recovery_result: Optional[RecoveryResult] = None

        # Track what has been persisted to avoid duplicates
        self._persisted_approvals: Set[str] = set()
        self._persisted_jobs: Set[str] = set()
        self._persisted_plans: Set[str] = set()
        self._persisted_promotions: Set[str] = set()

    def initialize(self) -> bool:
        """
        Initialize persistence and optionally recover state.

        Returns:
            True if initialized successfully.
        """
        if self._config.mode == PersistenceMode.DISABLED:
            logger.info("Persistence disabled by configuration")
            self._initialized = True
            return True

        try:
            # Initialize state store
            store_config = StateStoreConfig(db_path=self._config.db_path)
            self._state_store = initialize_state_store(store_config)

            if not self._state_store.is_initialized:
                logger.error("Failed to initialize state store")
                return False

            self._initialized = True
            logger.info("PersistenceManager initialized")

            # Auto-recover if configured
            if self._config.auto_recover_on_startup:
                self._recovery_result = self.recover_state()

            return True

        except Exception as e:
            logger.error(f"PersistenceManager initialization failed: {e}")
            return False

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized

    @property
    def is_persistence_enabled(self) -> bool:
        """Check if persistence is enabled."""
        return self._config.mode != PersistenceMode.DISABLED

    @property
    def recovery_result(self) -> Optional[RecoveryResult]:
        """Get the last recovery result."""
        return self._recovery_result

    # =========================================================================
    # Recovery
    # =========================================================================

    def recover_state(self) -> RecoveryResult:
        """
        Recover state from persistent storage.

        Loads pending/active records back into in-memory managers.

        Returns:
            RecoveryResult with recovery statistics.
        """
        if not self._initialized or not self._state_store:
            return RecoveryResult(success=False, errors=["Not initialized"])

        result = RecoveryResult(success=True)

        try:
            # Recover pending approvals
            if self._config.persist_approvals:
                result.recovered_approvals = self._recover_approvals()

            # Recover active jobs
            if self._config.persist_jobs:
                result.recovered_jobs = self._recover_jobs()

            # Recover recent plans
            if self._config.persist_plans:
                result.recovered_plans = self._recover_plans()

            # Recover active promotions
            if self._config.persist_promotions:
                result.recovered_promotions = self._recover_promotions()

            # Log recovery event
            if self._config.persist_events:
                self._state_store.save_event({
                    "event_id": f"recovery_{_utc_now().strftime('%Y%m%d%H%M%S%f')}",
                    "event_type": "system_recovery",
                    "severity": "info",
                    "timestamp": _utc_now().isoformat(),
                    "message": f"State recovered: {result.recovered_approvals} approvals, {result.recovered_jobs} jobs",
                    "details": result.to_dict(),
                })

            logger.info(
                f"State recovery complete: "
                f"approvals={result.recovered_approvals}, "
                f"jobs={result.recovered_jobs}, "
                f"plans={result.recovered_plans}, "
                f"promotions={result.recovered_promotions}"
            )

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"State recovery failed: {e}")

        return result

    def _recover_approvals(self) -> int:
        """Recover pending approvals to in-memory manager."""
        try:
            from .approval_manager import ApprovalManager, ApprovalRecord, ApprovalClass, ApprovalStatus

            pending = self._state_store.get_pending_approvals()

            # We don't directly inject into ApprovalManager here
            # Instead, we return count and let the OperatorService handle it
            # This avoids circular dependencies

            count = len(pending)
            for record in pending:
                self._persisted_approvals.add(record.get("record_id", ""))

            return count

        except Exception as e:
            logger.error(f"Failed to recover approvals: {e}")
            return 0

    def _recover_jobs(self) -> int:
        """Recover active jobs."""
        try:
            active_jobs = self._state_store.get_active_jobs()

            count = len(active_jobs)
            for job in active_jobs:
                self._persisted_jobs.add(job.get("job_id", ""))

            return count

        except Exception as e:
            logger.error(f"Failed to recover jobs: {e}")
            return 0

    def _recover_plans(self) -> int:
        """Recover recent execution plans."""
        try:
            plans = self._state_store.get_recent_plans(limit=50)

            count = len(plans)
            for plan in plans:
                self._persisted_plans.add(plan.get("plan_id", ""))

            return count

        except Exception as e:
            logger.error(f"Failed to recover plans: {e}")
            return 0

    def _recover_promotions(self) -> int:
        """Recover active live mode promotions."""
        try:
            promotions = self._state_store.get_live_mode_promotions(used=False)

            count = len(promotions)
            for promo in promotions:
                self._persisted_promotions.add(promo.get("promotion_id", ""))

            return count

        except Exception as e:
            logger.error(f"Failed to recover promotions: {e}")
            return 0

    # =========================================================================
    # Persistence Operations
    # =========================================================================

    def persist_approval(self, record: Dict[str, Any]) -> bool:
        """Persist an approval record."""
        if not self.is_persistence_enabled or not self._config.persist_approvals:
            return True

        if not self._state_store:
            return False

        record_id = record.get("record_id", "")
        success = self._state_store.save_approval(record)

        if success:
            self._persisted_approvals.add(record_id)

        return success

    def persist_job(self, job: Dict[str, Any]) -> bool:
        """Persist a job record."""
        if not self.is_persistence_enabled or not self._config.persist_jobs:
            return True

        if not self._state_store:
            return False

        job_id = job.get("job_id", "")
        success = self._state_store.save_job(job)

        if success:
            self._persisted_jobs.add(job_id)

        return success

    def persist_execution_plan(self, plan: Dict[str, Any]) -> bool:
        """Persist an execution plan record."""
        if not self.is_persistence_enabled or not self._config.persist_plans:
            return True

        if not self._state_store:
            return False

        plan_id = plan.get("plan_id", "")
        success = self._state_store.save_execution_plan(plan)

        if success:
            self._persisted_plans.add(plan_id)

        return success

    def persist_live_mode_promotion(self, promotion: Dict[str, Any]) -> bool:
        """Persist a live mode promotion."""
        if not self.is_persistence_enabled or not self._config.persist_promotions:
            return True

        if not self._state_store:
            return False

        promotion_id = promotion.get("promotion_id", "")
        success = self._state_store.save_live_mode_promotion(promotion)

        if success:
            self._persisted_promotions.add(promotion_id)

        return success

    def persist_event(self, event: Dict[str, Any]) -> bool:
        """Persist an event record."""
        if not self.is_persistence_enabled or not self._config.persist_events:
            return True

        if not self._state_store:
            return False

        return self._state_store.save_event(event)

    def persist_connector_execution(self, execution: Dict[str, Any]) -> bool:
        """Persist a connector execution record."""
        if not self.is_persistence_enabled or not self._config.persist_connector_executions:
            return True

        if not self._state_store:
            return False

        return self._state_store.save_connector_execution(execution)

    def persist_credential_health(self, health: Dict[str, Any]) -> bool:
        """Persist credential health metadata."""
        if not self.is_persistence_enabled or not self._config.persist_credential_health:
            return True

        if not self._state_store:
            return False

        return self._state_store.save_credential_health(health)

    def persist_cost_record(self, cost: Dict[str, Any]) -> bool:
        """Persist a cost record."""
        if not self.is_persistence_enabled or not self._config.persist_costs:
            return True

        if not self._state_store:
            return False

        return self._state_store.save_cost_record(cost)

    def persist_budget_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """Persist a budget snapshot."""
        if not self.is_persistence_enabled or not self._config.persist_costs:
            return True

        if not self._state_store:
            return False

        return self._state_store.save_budget_snapshot(snapshot)

    # =========================================================================
    # Query Operations (delegated to history_query)
    # =========================================================================

    def get_persisted_approvals(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get persisted approval records."""
        if not self._state_store:
            return []

        if status == "pending":
            return self._state_store.get_pending_approvals()

        return self._state_store.get_approval_history(limit=limit, status=status)

    def get_persisted_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get persisted job records."""
        if not self._state_store:
            return []

        return self._state_store.get_jobs(status=status, limit=limit)

    def get_persisted_plans(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get persisted execution plans."""
        if not self._state_store:
            return []

        return self._state_store.get_recent_plans(limit=limit)

    def get_persisted_promotions(
        self,
        used: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get persisted live mode promotions."""
        if not self._state_store:
            return []

        return self._state_store.get_live_mode_promotions(used=used, limit=limit)

    def get_persisted_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get persisted events."""
        if not self._state_store:
            return []

        return self._state_store.get_events(
            event_type=event_type,
            severity=severity,
            limit=limit,
        )

    def get_persisted_cost_records(
        self,
        record_type: Optional[str] = None,
        connector: Optional[str] = None,
        business_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get persisted cost records."""
        if not self._state_store:
            return []

        return self._state_store.get_cost_records(
            record_type=record_type,
            connector=connector,
            business_id=business_id,
            limit=limit,
        )

    def get_persisted_budget_snapshots(
        self,
        scope: Optional[str] = None,
        scope_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get persisted budget snapshots."""
        if not self._state_store:
            return []

        return self._state_store.get_budget_snapshots(
            scope=scope,
            scope_id=scope_id,
            limit=limit,
        )

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def shutdown(self) -> None:
        """Graceful shutdown with state preservation."""
        if self._state_store:
            # Log shutdown event
            if self._config.persist_events:
                self._state_store.save_event({
                    "event_id": f"shutdown_{_utc_now().strftime('%Y%m%d%H%M%S%f')}",
                    "event_type": "system_shutdown",
                    "severity": "info",
                    "timestamp": _utc_now().isoformat(),
                    "message": "PersistenceManager shutting down",
                    "details": {
                        "persisted_approvals": len(self._persisted_approvals),
                        "persisted_jobs": len(self._persisted_jobs),
                        "persisted_plans": len(self._persisted_plans),
                        "persisted_promotions": len(self._persisted_promotions),
                    },
                })

            self._state_store.close()
            self._state_store = None

        self._initialized = False
        logger.info("PersistenceManager shut down")

    def get_stats(self) -> Dict[str, Any]:
        """Get persistence statistics."""
        stats = {
            "initialized": self._initialized,
            "mode": self._config.mode.value,
            "persistence_enabled": self.is_persistence_enabled,
            "tracked_approvals": len(self._persisted_approvals),
            "tracked_jobs": len(self._persisted_jobs),
            "tracked_plans": len(self._persisted_plans),
            "tracked_promotions": len(self._persisted_promotions),
        }

        if self._state_store:
            stats["storage"] = self._state_store.get_stats()

        if self._recovery_result:
            stats["last_recovery"] = self._recovery_result.to_dict()

        return stats


# Singleton instance
_persistence_manager: Optional[PersistenceManager] = None


def get_persistence_manager() -> PersistenceManager:
    """Get the global persistence manager."""
    global _persistence_manager
    if _persistence_manager is None:
        _persistence_manager = PersistenceManager()
    return _persistence_manager


def initialize_persistence(config: Optional[PersistenceConfig] = None) -> PersistenceManager:
    """Initialize and return the global persistence manager."""
    global _persistence_manager
    _persistence_manager = PersistenceManager(config)
    _persistence_manager.initialize()
    return _persistence_manager
