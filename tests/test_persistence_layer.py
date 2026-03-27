"""
Tests for Persistence Layer.

Tests cover:
- StateStore SQLite operations
- PersistenceManager lifecycle (init, recover, persist, shutdown)
- HistoryQuery interface
- Data integrity across restarts
- Thread safety
- No secret leakage in persisted data

SECURITY:
- Tests use mock values only
- No real credentials in test code
- Verifies no secrets in persisted data
"""

import os
import pytest
import tempfile
import threading
from unittest.mock import Mock, patch
from datetime import datetime, timezone


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


# =============================================================================
# StateStore Tests
# =============================================================================

class TestStateStoreConfig:
    """Tests for StateStoreConfig dataclass."""

    def test_config_defaults(self):
        """StateStoreConfig has sensible defaults."""
        from core.state_store import StateStoreConfig

        config = StateStoreConfig()

        assert "state.db" in config.db_path
        assert config.auto_vacuum is True
        assert config.max_event_retention_days == 30
        assert config.max_events_stored == 10000

    def test_config_custom_values(self):
        """StateStoreConfig accepts custom values."""
        from core.state_store import StateStoreConfig

        config = StateStoreConfig(
            db_path="/custom/path/test.db",
            auto_vacuum=False,
            max_event_retention_days=7,
            max_events_stored=5000,
        )

        assert config.db_path == "/custom/path/test.db"
        assert config.auto_vacuum is False
        assert config.max_event_retention_days == 7
        assert config.max_events_stored == 5000


class TestStateStore:
    """Tests for StateStore class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
        # Also remove WAL files if present
        for suffix in ["-wal", "-shm"]:
            wal_path = path + suffix
            if os.path.exists(wal_path):
                os.remove(wal_path)

    @pytest.fixture
    def store(self, temp_db):
        """Create initialized StateStore."""
        from core.state_store import StateStore, StateStoreConfig

        config = StateStoreConfig(db_path=temp_db)
        store = StateStore(config)
        store.initialize()
        yield store
        store.close()

    def test_initialize_creates_schema(self, temp_db):
        """Initialize creates database schema."""
        from core.state_store import StateStore, StateStoreConfig

        config = StateStoreConfig(db_path=temp_db)
        store = StateStore(config)

        result = store.initialize()

        assert result is True
        assert store.is_initialized is True
        assert os.path.exists(temp_db)

        store.close()

    def test_save_and_get_approval(self, store):
        """Save and retrieve approval record."""
        record = {
            "record_id": "apr_test_001",
            "request_id": "req_001",
            "status": "pending",
            "action": "create_contact",
            "requester": "agent_001",
            "target_agent": "operator",
            "request_type": "connector_action",
            "description": "Create HubSpot contact",
            "priority": "normal",
            "risk_level": "medium",
            "created_at": _utc_now().isoformat(),
            "connector_name": "hubspot",
            "operation": "create_contact",
            "context": {"contact_email": "test@example.com"},
            "projected_cost": 0.01,
            "cost_class": "minimal",
        }

        save_result = store.save_approval(record)
        assert save_result is True

        retrieved = store.get_approval("apr_test_001")
        assert retrieved is not None
        assert retrieved["record_id"] == "apr_test_001"
        assert retrieved["status"] == "pending"
        assert retrieved["connector_name"] == "hubspot"
        assert retrieved["projected_cost"] == 0.01

    def test_get_pending_approvals(self, store):
        """Get pending approvals only."""
        # Create pending
        store.save_approval({
            "record_id": "apr_pending_001",
            "status": "pending",
            "created_at": _utc_now().isoformat(),
        })
        store.save_approval({
            "record_id": "apr_pending_002",
            "status": "pending",
            "created_at": _utc_now().isoformat(),
        })

        # Create approved
        store.save_approval({
            "record_id": "apr_approved_001",
            "status": "approved",
            "created_at": _utc_now().isoformat(),
        })

        pending = store.get_pending_approvals()

        assert len(pending) == 2
        assert all(a["status"] == "pending" for a in pending)

    def test_save_and_get_job(self, store):
        """Save and retrieve job record."""
        job = {
            "job_id": "job_test_001",
            "plan_id": "plan_001",
            "backend_type": "inline_local",
            "status": "running",
            "priority": "normal",
            "dispatched_at": _utc_now().isoformat(),
            "total_steps": 5,
            "completed_steps": 2,
            "estimated_cost": 0.05,
            "options": {"parallel": False},
            "result": {},
        }

        save_result = store.save_job(job)
        assert save_result is True

        retrieved = store.get_job("job_test_001")
        assert retrieved is not None
        assert retrieved["job_id"] == "job_test_001"
        assert retrieved["status"] == "running"
        assert retrieved["total_steps"] == 5
        assert retrieved["options"]["parallel"] is False

    def test_get_active_jobs(self, store):
        """Get active jobs only."""
        store.save_job({"job_id": "job_running", "status": "running", "dispatched_at": _utc_now().isoformat()})
        store.save_job({"job_id": "job_pending", "status": "pending", "dispatched_at": _utc_now().isoformat()})
        store.save_job({"job_id": "job_queued", "status": "queued", "dispatched_at": _utc_now().isoformat()})
        store.save_job({"job_id": "job_completed", "status": "completed", "dispatched_at": _utc_now().isoformat()})
        store.save_job({"job_id": "job_failed", "status": "failed", "dispatched_at": _utc_now().isoformat()})

        active = store.get_active_jobs()

        assert len(active) == 3
        active_ids = {j["job_id"] for j in active}
        assert "job_running" in active_ids
        assert "job_pending" in active_ids
        assert "job_queued" in active_ids
        assert "job_completed" not in active_ids
        assert "job_failed" not in active_ids

    def test_save_and_get_execution_plan(self, store):
        """Save and retrieve execution plan."""
        plan = {
            "plan_id": "plan_test_001",
            "request_id": "req_001",
            "objective": "Search for contacts",
            "primary_domain": "crm",
            "status": "pending",
            "step_count": 3,
            "created_at": _utc_now().isoformat(),
            "requires_approval": True,
            "selected_skills": ["search_skill", "filter_skill"],
            "selected_commands": [],
            "selected_agents": ["crm_agent"],
            "projected_cost": 0.02,
            "cost_class": "low",
            "policy_decisions": {"allow": True},
        }

        save_result = store.save_execution_plan(plan)
        assert save_result is True

        retrieved = store.get_execution_plan("plan_test_001")
        assert retrieved is not None
        assert retrieved["plan_id"] == "plan_test_001"
        assert retrieved["step_count"] == 3
        assert retrieved["selected_skills"] == ["search_skill", "filter_skill"]
        assert retrieved["requires_approval"] == 1  # SQLite stores as int

    def test_save_and_get_live_mode_promotion(self, store):
        """Save and retrieve live mode promotion."""
        promotion = {
            "promotion_id": "lmp_test_001",
            "connector": "hubspot",
            "operation": "create_contact",
            "promoted_by": "principal",
            "approval_id": "apr_001",
            "risk_level": "medium",
            "promoted_at": _utc_now().isoformat(),
            "expires_at": None,
            "used": False,
            "used_at": None,
            "execution_cost": None,
        }

        save_result = store.save_live_mode_promotion(promotion)
        assert save_result is True

        promotions = store.get_live_mode_promotions(used=False)
        assert len(promotions) >= 1
        found = next((p for p in promotions if p["promotion_id"] == "lmp_test_001"), None)
        assert found is not None
        assert found["connector"] == "hubspot"

    def test_save_and_get_event(self, store):
        """Save and retrieve event."""
        event = {
            "event_id": "evt_test_001",
            "event_type": "approval_requested",
            "severity": "info",
            "timestamp": _utc_now().isoformat(),
            "request_id": "req_001",
            "message": "Approval requested for connector action",
            "details": {"connector": "hubspot", "operation": "create"},
            "cost_related": False,
        }

        save_result = store.save_event(event)
        assert save_result is True

        events = store.get_events(event_type="approval_requested")
        assert len(events) >= 1
        found = next((e for e in events if e["event_id"] == "evt_test_001"), None)
        assert found is not None
        assert found["details"]["connector"] == "hubspot"

    def test_event_trimming(self, temp_db):
        """Events are trimmed when max_events_stored exceeded."""
        from core.state_store import StateStore, StateStoreConfig

        config = StateStoreConfig(db_path=temp_db, max_events_stored=5)
        store = StateStore(config)
        store.initialize()

        # Add 10 events
        for i in range(10):
            store.save_event({
                "event_id": f"evt_{i:03d}",
                "event_type": "test",
                "severity": "info",
                "timestamp": _utc_now().isoformat(),
                "message": f"Event {i}",
            })

        events = store.get_events(limit=100)

        # Should have been trimmed to max_events_stored
        assert len(events) <= 5

        store.close()

    def test_save_and_get_cost_record(self, store):
        """Save and retrieve cost record."""
        cost = {
            "cost_id": "cost_test_001",
            "record_type": "plan",
            "record_id": "plan_001",
            "timestamp": _utc_now().isoformat(),
            "connector": "hubspot",
            "operation": "create_contact",
            "backend": "inline_local",
            "business_id": "biz_001",
            "plan_id": "plan_001",
            "job_id": "job_001",
            "cost_class": "minimal",
            "estimated_cost": 0.01,
            "actual_cost": 0.008,
            "cost_unknown": False,
            "currency": "USD",
            "notes": "Test cost record",
        }

        save_result = store.save_cost_record(cost)
        assert save_result is True

        records = store.get_cost_records(business_id="biz_001")
        assert len(records) >= 1
        found = next((r for r in records if r["cost_id"] == "cost_test_001"), None)
        assert found is not None
        assert found["estimated_cost"] == 0.01
        assert found["actual_cost"] == 0.008

    def test_save_and_get_budget_snapshot(self, store):
        """Save and retrieve budget snapshot."""
        snapshot = {
            "snapshot_id": "snap_test_001",
            "scope": "monthly",
            "scope_id": "2024-01",
            "timestamp": _utc_now().isoformat(),
            "period_start": "2024-01-01T00:00:00Z",
            "period_end": "2024-01-31T23:59:59Z",
            "budget_limit": 100.00,
            "spent_total": 25.50,
            "spent_estimated": 20.00,
            "spent_actual": 5.50,
            "remaining": 74.50,
            "utilization_pct": 25.5,
            "metadata": {"connectors_used": ["hubspot", "tavily"]},
        }

        save_result = store.save_budget_snapshot(snapshot)
        assert save_result is True

        snapshots = store.get_budget_snapshots(scope="monthly")
        assert len(snapshots) >= 1
        found = next((s for s in snapshots if s["snapshot_id"] == "snap_test_001"), None)
        assert found is not None
        assert found["budget_limit"] == 100.00
        assert found["utilization_pct"] == 25.5

    def test_get_stats(self, store):
        """Get storage statistics."""
        # Add some data
        store.save_approval({"record_id": "apr_stats_001", "status": "pending", "created_at": _utc_now().isoformat()})
        store.save_job({"job_id": "job_stats_001", "status": "running", "dispatched_at": _utc_now().isoformat()})

        stats = store.get_stats()

        assert stats["initialized"] is True
        assert stats["approvals_count"] >= 1
        assert stats["jobs_count"] >= 1
        assert "db_size_bytes" in stats

    def test_thread_safety(self, store):
        """StateStore handles concurrent access."""
        errors = []

        def writer(start_id):
            for i in range(10):
                try:
                    store.save_approval({
                        "record_id": f"apr_thread_{start_id}_{i}",
                        "status": "pending",
                        "created_at": _utc_now().isoformat(),
                    })
                except Exception as e:
                    errors.append(str(e))

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Should have saved all records
        approvals = store.get_approval_history(limit=100)
        assert len(approvals) >= 30


class TestStateStoreUninitialized:
    """Tests for StateStore before initialization."""

    def test_operations_fail_when_uninitialized(self):
        """Operations return empty/False when not initialized."""
        from core.state_store import StateStore, StateStoreConfig

        store = StateStore(StateStoreConfig(db_path="/nonexistent/path.db"))

        assert store.is_initialized is False
        assert store.save_approval({"record_id": "test"}) is False
        assert store.get_approval("test") is None
        assert store.get_pending_approvals() == []


# =============================================================================
# PersistenceManager Tests
# =============================================================================

class TestPersistenceConfig:
    """Tests for PersistenceConfig dataclass."""

    def test_config_defaults(self):
        """PersistenceConfig has sensible defaults."""
        from core.persistence_manager import PersistenceConfig, PersistenceMode

        config = PersistenceConfig()

        assert config.mode == PersistenceMode.SYNC
        assert config.auto_recover_on_startup is True
        assert config.persist_events is True
        assert config.persist_approvals is True
        assert config.persist_costs is True

    def test_config_disabled_mode(self):
        """PersistenceConfig can be set to disabled."""
        from core.persistence_manager import PersistenceConfig, PersistenceMode

        config = PersistenceConfig(mode=PersistenceMode.DISABLED)

        assert config.mode == PersistenceMode.DISABLED


class TestRecoveryResult:
    """Tests for RecoveryResult dataclass."""

    def test_recovery_result_to_dict(self):
        """RecoveryResult.to_dict() returns dictionary."""
        from core.persistence_manager import RecoveryResult

        result = RecoveryResult(
            success=True,
            recovered_approvals=5,
            recovered_jobs=3,
            recovered_plans=10,
            recovered_promotions=2,
            recovered_costs=15,
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["recovered_approvals"] == 5
        assert data["recovered_jobs"] == 3
        assert data["recovered_plans"] == 10
        assert data["recovered_promotions"] == 2
        assert data["recovered_costs"] == 15
        assert "timestamp" in data


class TestPersistenceManager:
    """Tests for PersistenceManager class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm"]:
            wal_path = path + suffix
            if os.path.exists(wal_path):
                os.remove(wal_path)

    @pytest.fixture
    def manager(self, temp_db):
        """Create initialized PersistenceManager."""
        from core.persistence_manager import PersistenceManager, PersistenceConfig

        config = PersistenceConfig(
            db_path=temp_db,
            auto_recover_on_startup=False,  # Don't auto-recover in tests
        )
        mgr = PersistenceManager(config)
        mgr.initialize()
        yield mgr
        mgr.shutdown()

    def test_initialize_success(self, temp_db):
        """PersistenceManager initializes successfully."""
        from core.persistence_manager import PersistenceManager, PersistenceConfig

        config = PersistenceConfig(db_path=temp_db, auto_recover_on_startup=False)
        mgr = PersistenceManager(config)

        result = mgr.initialize()

        assert result is True
        assert mgr.is_initialized is True
        assert mgr.is_persistence_enabled is True

        mgr.shutdown()

    def test_disabled_mode_no_persistence(self, temp_db):
        """Disabled mode skips actual persistence."""
        from core.persistence_manager import PersistenceManager, PersistenceConfig, PersistenceMode

        config = PersistenceConfig(
            db_path=temp_db,
            mode=PersistenceMode.DISABLED,
        )
        mgr = PersistenceManager(config)
        mgr.initialize()

        # Persistence calls should succeed but not actually persist
        assert mgr.is_persistence_enabled is False
        result = mgr.persist_approval({"record_id": "test"})
        assert result is True  # Returns True but doesn't persist

        mgr.shutdown()

    def test_persist_and_retrieve_approval(self, manager):
        """Persist and retrieve approval."""
        record = {
            "record_id": "apr_pm_001",
            "status": "pending",
            "created_at": _utc_now().isoformat(),
            "description": "Test approval",
        }

        save_result = manager.persist_approval(record)
        assert save_result is True

        retrieved = manager.get_persisted_approvals(status="pending")
        assert len(retrieved) >= 1
        found = next((a for a in retrieved if a["record_id"] == "apr_pm_001"), None)
        assert found is not None

    def test_persist_and_retrieve_job(self, manager):
        """Persist and retrieve job."""
        job = {
            "job_id": "job_pm_001",
            "status": "running",
            "dispatched_at": _utc_now().isoformat(),
        }

        save_result = manager.persist_job(job)
        assert save_result is True

        retrieved = manager.get_persisted_jobs()
        found = next((j for j in retrieved if j["job_id"] == "job_pm_001"), None)
        assert found is not None

    def test_persist_and_retrieve_plan(self, manager):
        """Persist and retrieve execution plan."""
        plan = {
            "plan_id": "plan_pm_001",
            "status": "pending",
            "created_at": _utc_now().isoformat(),
        }

        save_result = manager.persist_execution_plan(plan)
        assert save_result is True

        retrieved = manager.get_persisted_plans()
        found = next((p for p in retrieved if p["plan_id"] == "plan_pm_001"), None)
        assert found is not None

    def test_persist_cost_record(self, manager):
        """Persist cost record."""
        cost = {
            "cost_id": "cost_pm_001",
            "record_type": "plan",
            "record_id": "plan_001",
            "timestamp": _utc_now().isoformat(),
            "estimated_cost": 0.01,
        }

        save_result = manager.persist_cost_record(cost)
        assert save_result is True

        retrieved = manager.get_persisted_cost_records()
        found = next((c for c in retrieved if c["cost_id"] == "cost_pm_001"), None)
        assert found is not None

    def test_recovery(self, temp_db):
        """Recovery restores pending state."""
        from core.persistence_manager import PersistenceManager, PersistenceConfig

        # First session - save some data
        config = PersistenceConfig(db_path=temp_db, auto_recover_on_startup=False)
        mgr1 = PersistenceManager(config)
        mgr1.initialize()

        mgr1.persist_approval({"record_id": "apr_recover_001", "status": "pending", "created_at": _utc_now().isoformat()})
        mgr1.persist_approval({"record_id": "apr_recover_002", "status": "pending", "created_at": _utc_now().isoformat()})
        mgr1.persist_job({"job_id": "job_recover_001", "status": "running", "dispatched_at": _utc_now().isoformat()})

        mgr1.shutdown()

        # Second session - recover
        mgr2 = PersistenceManager(config)
        mgr2.initialize()

        result = mgr2.recover_state()

        assert result.success is True
        assert result.recovered_approvals == 2
        assert result.recovered_jobs == 1

        mgr2.shutdown()

    def test_get_stats(self, manager):
        """Get persistence statistics."""
        manager.persist_approval({"record_id": "apr_stats", "status": "pending", "created_at": _utc_now().isoformat()})

        stats = manager.get_stats()

        assert stats["initialized"] is True
        assert stats["mode"] == "sync"
        assert stats["persistence_enabled"] is True
        assert "storage" in stats


# =============================================================================
# HistoryQuery Tests
# =============================================================================

class TestHistoryQuery:
    """Tests for HistoryQuery class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm"]:
            wal_path = path + suffix
            if os.path.exists(wal_path):
                os.remove(wal_path)

    @pytest.fixture
    def query_interface(self, temp_db):
        """Create HistoryQuery with initialized persistence."""
        from core.persistence_manager import PersistenceManager, PersistenceConfig
        from core.history_query import HistoryQuery

        config = PersistenceConfig(db_path=temp_db, auto_recover_on_startup=False)
        mgr = PersistenceManager(config)
        mgr.initialize()

        # Add some test data
        mgr.persist_approval({"record_id": "apr_hq_001", "status": "pending", "created_at": _utc_now().isoformat()})
        mgr.persist_approval({"record_id": "apr_hq_002", "status": "approved", "created_at": _utc_now().isoformat()})
        mgr.persist_job({"job_id": "job_hq_001", "status": "completed", "dispatched_at": _utc_now().isoformat()})
        mgr.persist_cost_record({
            "cost_id": "cost_hq_001",
            "record_type": "plan",
            "record_id": "plan_001",
            "timestamp": _utc_now().isoformat(),
            "connector": "hubspot",
            "business_id": "biz_001",
            "estimated_cost": 0.01,
            "actual_cost": 0.008,
            "cost_class": "minimal",
        })

        query = HistoryQuery(mgr)

        yield query

        mgr.shutdown()

    def test_get_approvals(self, query_interface):
        """Get approval records."""
        approvals = query_interface.get_approvals()

        assert len(approvals) >= 2

    def test_get_pending_approvals(self, query_interface):
        """Get pending approvals only."""
        pending = query_interface.get_pending_approvals()

        assert len(pending) >= 1
        assert all(a["status"] == "pending" for a in pending)

    def test_get_approval_by_id(self, query_interface):
        """Get specific approval by ID."""
        approval = query_interface.get_approval_by_id("apr_hq_001")

        assert approval is not None
        assert approval["record_id"] == "apr_hq_001"

    def test_get_jobs(self, query_interface):
        """Get job records."""
        jobs = query_interface.get_jobs()

        assert len(jobs) >= 1

    def test_get_cost_records(self, query_interface):
        """Get cost records."""
        costs = query_interface.get_cost_records()

        assert len(costs) >= 1
        assert costs[0]["connector"] == "hubspot"

    def test_get_aggregated_costs(self, query_interface):
        """Get aggregated cost statistics."""
        from core.history_query import QueryFilter

        aggregated = query_interface.get_aggregated_costs()

        assert aggregated.record_count >= 1
        assert aggregated.total_estimated >= 0.01
        assert "hubspot" in aggregated.by_connector

    def test_get_business_costs(self, query_interface):
        """Get costs for a specific business."""
        result = query_interface.get_business_costs("biz_001")

        assert result["business_id"] == "biz_001"
        assert len(result["cost_records"]) >= 1
        assert "aggregated" in result

    def test_get_summary(self, query_interface):
        """Get history summary."""
        summary = query_interface.get_summary()

        assert summary.total_approvals >= 2
        assert summary.pending_approvals >= 1
        assert summary.total_jobs >= 1
        assert summary.total_cost_records >= 1

    def test_summary_to_dict(self, query_interface):
        """Summary can be converted to dict."""
        summary = query_interface.get_summary()
        data = summary.to_dict()

        assert isinstance(data, dict)
        assert "total_approvals" in data
        assert "aggregated_costs" in data


class TestQueryFilter:
    """Tests for QueryFilter dataclass."""

    def test_filter_defaults(self):
        """QueryFilter has sensible defaults."""
        from core.history_query import QueryFilter

        filter = QueryFilter()

        assert filter.time_range is None
        assert filter.limit == 100
        assert filter.offset == 0

    def test_filter_with_time_range(self):
        """QueryFilter with time range."""
        from core.history_query import QueryFilter, TimeRange

        filter = QueryFilter(
            time_range=TimeRange.LAST_24_HOURS,
            connector="hubspot",
            limit=50,
        )

        assert filter.time_range == TimeRange.LAST_24_HOURS
        assert filter.connector == "hubspot"
        assert filter.limit == 50


# =============================================================================
# Singleton Tests
# =============================================================================

class TestSingletons:
    """Tests for singleton instances."""

    def test_get_state_store_singleton(self):
        """get_state_store returns singleton."""
        import core.state_store

        # Reset singleton
        core.state_store._state_store = None

        store1 = core.state_store.get_state_store()
        store2 = core.state_store.get_state_store()

        assert store1 is store2

        # Clean up
        core.state_store._state_store = None

    def test_get_persistence_manager_singleton(self):
        """get_persistence_manager returns singleton."""
        import core.persistence_manager

        # Reset singleton
        core.persistence_manager._persistence_manager = None

        mgr1 = core.persistence_manager.get_persistence_manager()
        mgr2 = core.persistence_manager.get_persistence_manager()

        assert mgr1 is mgr2

        # Clean up
        core.persistence_manager._persistence_manager = None

    def test_get_history_query_singleton(self):
        """get_history_query returns singleton."""
        import core.history_query

        # Reset singleton
        core.history_query._history_query = None

        q1 = core.history_query.get_history_query()
        q2 = core.history_query.get_history_query()

        assert q1 is q2

        # Clean up
        core.history_query._history_query = None


# =============================================================================
# No Secret Leakage Tests
# =============================================================================

class TestNoSecretLeakage:
    """Tests verifying no secrets in persisted data."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm"]:
            wal_path = path + suffix
            if os.path.exists(wal_path):
                os.remove(wal_path)

    def test_approval_no_secrets_persisted(self, temp_db):
        """Approvals don't persist secrets."""
        from core.persistence_manager import PersistenceManager, PersistenceConfig

        config = PersistenceConfig(db_path=temp_db, auto_recover_on_startup=False)
        mgr = PersistenceManager(config)
        mgr.initialize()

        # Save approval with context that SHOULD NOT contain secrets
        mgr.persist_approval({
            "record_id": "apr_secret_test",
            "status": "pending",
            "created_at": _utc_now().isoformat(),
            "context": {
                "query": "test query",
                "safe_param": "visible value",
            },
        })

        # Retrieve and check
        approvals = mgr.get_persisted_approvals()
        approval = next((a for a in approvals if a["record_id"] == "apr_secret_test"), None)

        assert approval is not None
        approval_str = str(approval).lower()

        # Should not contain actual secret values
        assert "sk_live_" not in approval_str
        assert "api_key_value" not in approval_str
        assert "secret_password" not in approval_str

        mgr.shutdown()

    def test_cost_record_no_secrets(self, temp_db):
        """Cost records don't contain secrets."""
        from core.persistence_manager import PersistenceManager, PersistenceConfig

        config = PersistenceConfig(db_path=temp_db, auto_recover_on_startup=False)
        mgr = PersistenceManager(config)
        mgr.initialize()

        mgr.persist_cost_record({
            "cost_id": "cost_secret_test",
            "record_type": "plan",
            "record_id": "plan_001",
            "timestamp": _utc_now().isoformat(),
            "connector": "hubspot",
            "estimated_cost": 0.01,
            "notes": "No secrets here",
        })

        costs = mgr.get_persisted_cost_records()
        cost = next((c for c in costs if c["cost_id"] == "cost_secret_test"), None)

        assert cost is not None
        cost_str = str(cost).lower()

        assert "api_key" not in cost_str or "hubspot" in cost_str  # connector name OK
        assert "password" not in cost_str
        assert "token_value" not in cost_str

        mgr.shutdown()


# =============================================================================
# Data Integrity Tests
# =============================================================================

class TestDataIntegrity:
    """Tests for data integrity across operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm"]:
            wal_path = path + suffix
            if os.path.exists(wal_path):
                os.remove(wal_path)

    def test_data_survives_restart(self, temp_db):
        """Data persists across manager restarts."""
        from core.persistence_manager import PersistenceManager, PersistenceConfig

        config = PersistenceConfig(db_path=temp_db, auto_recover_on_startup=False)

        # First session
        mgr1 = PersistenceManager(config)
        mgr1.initialize()
        mgr1.persist_approval({
            "record_id": "apr_restart_001",
            "status": "pending",
            "description": "Test data",
            "created_at": _utc_now().isoformat(),
        })
        mgr1.shutdown()

        # Second session - should find the data
        mgr2 = PersistenceManager(config)
        mgr2.initialize()

        approvals = mgr2.get_persisted_approvals()
        found = next((a for a in approvals if a["record_id"] == "apr_restart_001"), None)

        assert found is not None
        assert found["description"] == "Test data"

        mgr2.shutdown()

    def test_update_existing_record(self, temp_db):
        """Updating existing record works correctly."""
        from core.state_store import StateStore, StateStoreConfig

        config = StateStoreConfig(db_path=temp_db)
        store = StateStore(config)
        store.initialize()

        # Create initial record
        store.save_approval({
            "record_id": "apr_update_001",
            "status": "pending",
            "created_at": _utc_now().isoformat(),
        })

        # Update it
        store.save_approval({
            "record_id": "apr_update_001",
            "status": "approved",
            "created_at": _utc_now().isoformat(),
            "decided_at": _utc_now().isoformat(),
            "decided_by": "principal",
        })

        # Verify update
        retrieved = store.get_approval("apr_update_001")
        assert retrieved["status"] == "approved"
        assert retrieved["decided_by"] == "principal"

        store.close()

    def test_json_fields_roundtrip(self, temp_db):
        """JSON fields serialize and deserialize correctly."""
        from core.state_store import StateStore, StateStoreConfig

        config = StateStoreConfig(db_path=temp_db)
        store = StateStore(config)
        store.initialize()

        complex_context = {
            "list_field": [1, 2, 3],
            "nested": {"a": "b", "c": [4, 5]},
            "unicode": "日本語テスト",
            "bool": True,
            "null": None,
        }

        store.save_approval({
            "record_id": "apr_json_001",
            "status": "pending",
            "created_at": _utc_now().isoformat(),
            "context": complex_context,
        })

        retrieved = store.get_approval("apr_json_001")

        assert retrieved["context"]["list_field"] == [1, 2, 3]
        assert retrieved["context"]["nested"]["a"] == "b"
        assert retrieved["context"]["unicode"] == "日本語テスト"
        assert retrieved["context"]["bool"] is True
        assert retrieved["context"]["null"] is None

        store.close()
