"""
State Store for Project Alpha.

SQLite-based persistent storage for operational state that survives restarts.

PERSISTS:
- Approval records and decisions
- Live mode promotions
- Jobs and job status transitions
- Execution plans (metadata only, not secrets)
- Event logs
- Connector executions
- Credential health metadata (not secret values)
- Cost records

DOES NOT PERSIST:
- Secret values (handled by secrets_manager)
- Temporary in-flight state
- Session-only caches

ARCHITECTURE:
- Local SQLite file for deterministic, testable persistence
- Simple schema with JSON columns for flexibility
- No external dependencies
- Automatic schema migration
"""

import json
import os
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class RecordType(Enum):
    """Types of records stored."""
    APPROVAL = "approval"
    JOB = "job"
    EXECUTION_PLAN = "execution_plan"
    LIVE_MODE_PROMOTION = "live_mode_promotion"
    EVENT = "event"
    CONNECTOR_EXECUTION = "connector_execution"
    CREDENTIAL_HEALTH = "credential_health"
    COST_RECORD = "cost_record"
    BUDGET_SNAPSHOT = "budget_snapshot"
    OPPORTUNITY = "opportunity"
    HANDOFF = "handoff"


SCHEMA_VERSION = 1

CREATE_TABLES_SQL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Approval records
CREATE TABLE IF NOT EXISTS approvals (
    record_id TEXT PRIMARY KEY,
    request_id TEXT,
    policy_id TEXT,
    classification TEXT,
    status TEXT,
    action TEXT,
    requester TEXT,
    target_agent TEXT,
    request_type TEXT,
    description TEXT,
    priority TEXT,
    risk_level TEXT,
    rationale TEXT,
    decided_by TEXT,
    decided_at TEXT,
    created_at TEXT,
    resolved_at TEXT,
    plan_id TEXT,
    job_id TEXT,
    connector_name TEXT,
    operation TEXT,
    context_json TEXT,
    projected_cost REAL,
    cost_class TEXT
);

-- Jobs
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    plan_id TEXT,
    backend_type TEXT,
    status TEXT,
    priority TEXT,
    dispatched_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    worker_instance_id TEXT,
    retry_count INTEGER DEFAULT 0,
    error TEXT,
    total_steps INTEGER,
    completed_steps INTEGER,
    failed_steps INTEGER,
    duration_seconds REAL,
    estimated_cost REAL,
    actual_cost REAL,
    cost_class TEXT,
    options_json TEXT,
    result_json TEXT
);

-- Execution plans (metadata only)
CREATE TABLE IF NOT EXISTS execution_plans (
    plan_id TEXT PRIMARY KEY,
    request_id TEXT,
    objective TEXT,
    primary_domain TEXT,
    status TEXT,
    step_count INTEGER,
    created_at TEXT,
    completed_at TEXT,
    requires_approval INTEGER,
    selected_skills_json TEXT,
    selected_commands_json TEXT,
    selected_agents_json TEXT,
    backend_used TEXT,
    job_id TEXT,
    projected_cost REAL,
    actual_cost REAL,
    cost_class TEXT,
    policy_decisions_json TEXT
);

-- Live mode promotions
CREATE TABLE IF NOT EXISTS live_mode_promotions (
    promotion_id TEXT PRIMARY KEY,
    connector TEXT,
    operation TEXT,
    promoted_by TEXT,
    approval_id TEXT,
    risk_level TEXT,
    promoted_at TEXT,
    expires_at TEXT,
    used INTEGER DEFAULT 0,
    used_at TEXT,
    execution_cost REAL
);

-- Events (subset for persistence - recent important events)
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT,
    severity TEXT,
    timestamp TEXT,
    request_id TEXT,
    business_id TEXT,
    agent_id TEXT,
    layer TEXT,
    message TEXT,
    error TEXT,
    details_json TEXT,
    cost_related INTEGER DEFAULT 0
);

-- Connector executions (now: connector_action_executions)
CREATE TABLE IF NOT EXISTS connector_executions (
    execution_id TEXT PRIMARY KEY,
    connector_name TEXT NOT NULL,
    action_name TEXT NOT NULL,
    operation TEXT,
    timestamp TEXT NOT NULL,
    mode TEXT NOT NULL,
    success INTEGER NOT NULL,
    duration_seconds REAL,
    error TEXT,
    estimated_cost REAL,
    actual_cost REAL,
    cost_class TEXT,
    approval_state TEXT,
    approval_id TEXT,
    execution_status TEXT,
    job_id TEXT,
    plan_id TEXT,
    opportunity_id TEXT,
    request_summary TEXT,
    response_summary TEXT,
    error_summary TEXT,
    operator_decision_ref TEXT,
    params_json TEXT,
    result_summary TEXT,
    metadata_json TEXT
);

-- Credential health (metadata only, never stores secrets)
CREATE TABLE IF NOT EXISTS credential_health (
    credential_name TEXT PRIMARY KEY,
    connector TEXT,
    last_validated_at TEXT,
    valid INTEGER,
    expires_at TEXT,
    rotation_due_at TEXT,
    last_used_at TEXT,
    use_count INTEGER DEFAULT 0,
    health_status TEXT,
    metadata_json TEXT
);

-- Cost records
CREATE TABLE IF NOT EXISTS cost_records (
    cost_id TEXT PRIMARY KEY,
    record_type TEXT,
    record_id TEXT,
    timestamp TEXT,
    connector TEXT,
    operation TEXT,
    backend TEXT,
    business_id TEXT,
    plan_id TEXT,
    job_id TEXT,
    cost_class TEXT,
    estimated_cost REAL,
    actual_cost REAL,
    cost_unknown INTEGER DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    notes TEXT
);

-- Budget snapshots
CREATE TABLE IF NOT EXISTS budget_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    scope TEXT,
    scope_id TEXT,
    timestamp TEXT,
    period_start TEXT,
    period_end TEXT,
    budget_limit REAL,
    spent_total REAL,
    spent_estimated REAL,
    spent_actual REAL,
    remaining REAL,
    utilization_pct REAL,
    metadata_json TEXT
);

-- Opportunities (Business Discovery Layer)
CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id TEXT PRIMARY KEY,
    hypothesis_json TEXT NOT NULL,
    score_json TEXT NOT NULL,
    recommendation_json TEXT NOT NULL,
    status TEXT NOT NULL,
    operator_constraints_json TEXT,
    status_history_json TEXT,
    operator_notes TEXT,
    tags_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Opportunity Handoffs (Discovery-to-Execution Bridge)
CREATE TABLE IF NOT EXISTS handoffs (
    handoff_id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    context_json TEXT NOT NULL,
    plan_id TEXT,
    business_id TEXT,
    job_id TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    created_by TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id)
);

-- Capacity Limits Configuration
CREATE TABLE IF NOT EXISTS capacity_limits (
    dimension TEXT PRIMARY KEY,
    soft_limit INTEGER,
    hard_limit INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    updated_at TEXT NOT NULL
);

-- Capacity Decision History (Audit Trail)
CREATE TABLE IF NOT EXISTS capacity_decisions (
    decision_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    dimension TEXT NOT NULL,
    decision TEXT NOT NULL,
    current_count INTEGER NOT NULL,
    projected_count INTEGER NOT NULL,
    soft_limit INTEGER,
    hard_limit INTEGER,
    reason TEXT,
    business_id TEXT,
    opportunity_id TEXT,
    plan_id TEXT,
    job_id TEXT,
    runtime_backend TEXT,
    estimated_cost REAL,
    context_json TEXT
);

-- Scenario Runs (End-to-End Execution Scenarios)
CREATE TABLE IF NOT EXISTS scenario_runs (
    run_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    scenario_name TEXT NOT NULL,
    status TEXT NOT NULL,
    inputs_json TEXT NOT NULL,
    dry_run INTEGER NOT NULL DEFAULT 1,
    started_at TEXT,
    completed_at TEXT,
    duration_seconds REAL,
    step_results_json TEXT,
    total_steps INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    failed_steps INTEGER DEFAULT 0,
    skipped_steps INTEGER DEFAULT 0,
    final_output_json TEXT,
    error_message TEXT,
    triggered_by TEXT,
    plan_ids_json TEXT,
    job_ids_json TEXT,
    approval_ids_json TEXT,
    connector_execution_ids_json TEXT,
    opportunity_id TEXT,
    handoff_id TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
CREATE INDEX IF NOT EXISTS idx_approvals_created ON approvals(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_plan ON jobs(plan_id);
CREATE INDEX IF NOT EXISTS idx_plans_status ON execution_plans(status);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_cost_records_timestamp ON cost_records(timestamp);
CREATE INDEX IF NOT EXISTS idx_cost_records_type ON cost_records(record_type);
CREATE INDEX IF NOT EXISTS idx_connector_executions_connector ON connector_executions(connector_name);
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opportunities_created ON opportunities(created_at);
CREATE INDEX IF NOT EXISTS idx_handoffs_opportunity ON handoffs(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_handoffs_status ON handoffs(status);
CREATE INDEX IF NOT EXISTS idx_handoffs_plan ON handoffs(plan_id);
CREATE INDEX IF NOT EXISTS idx_capacity_decisions_timestamp ON capacity_decisions(timestamp);
CREATE INDEX IF NOT EXISTS idx_capacity_decisions_dimension ON capacity_decisions(dimension);
CREATE INDEX IF NOT EXISTS idx_capacity_decisions_decision ON capacity_decisions(decision);
CREATE INDEX IF NOT EXISTS idx_scenario_runs_scenario ON scenario_runs(scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_runs_status ON scenario_runs(status);
CREATE INDEX IF NOT EXISTS idx_scenario_runs_started ON scenario_runs(started_at);
"""


@dataclass
class StateStoreConfig:
    """Configuration for the state store."""
    db_path: str = "project_alpha/data/state.db"
    auto_vacuum: bool = True
    max_event_retention_days: int = 30
    max_events_stored: int = 10000


class StateStore:
    """
    SQLite-based persistent state storage.

    Thread-safe, deterministic, and testable.
    """

    def __init__(self, config: Optional[StateStoreConfig] = None):
        """Initialize the state store."""
        self._config = config or StateStoreConfig()
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize the database connection and schema.

        Returns:
            True if initialized successfully.
        """
        try:
            # Ensure directory exists
            db_dir = os.path.dirname(self._config.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            # Connect with threading mode
            self._conn = sqlite3.connect(
                self._config.db_path,
                check_same_thread=False,
                isolation_level=None,  # Autocommit for simplicity
            )
            self._conn.row_factory = sqlite3.Row

            # Enable foreign keys and WAL mode for better concurrency
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")

            # Create schema
            self._create_schema()

            self._initialized = True
            logger.info(f"StateStore initialized: {self._config.db_path}")
            return True

        except Exception as e:
            logger.error(f"StateStore initialization failed: {e}")
            return False

    def _create_schema(self) -> None:
        """Create database schema."""
        with self._lock:
            cursor = self._conn.cursor()

            # Execute schema creation
            cursor.executescript(CREATE_TABLES_SQL)

            # Check and update schema version
            cursor.execute(
                "SELECT MAX(version) FROM schema_version"
            )
            result = cursor.fetchone()
            current_version = result[0] if result[0] else 0

            if current_version < SCHEMA_VERSION:
                cursor.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, _utc_now().isoformat())
                )

            self._conn.commit()

    @property
    def is_initialized(self) -> bool:
        """Check if store is initialized."""
        return self._initialized

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            self._initialized = False

    # =========================================================================
    # Approval Records
    # =========================================================================

    def save_approval(self, record: Dict[str, Any]) -> bool:
        """Save or update an approval record."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO approvals (
                        record_id, request_id, policy_id, classification, status,
                        action, requester, target_agent, request_type, description,
                        priority, risk_level, rationale, decided_by, decided_at,
                        created_at, resolved_at, plan_id, job_id, connector_name,
                        operation, context_json, projected_cost, cost_class
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.get("record_id"),
                    record.get("request_id"),
                    record.get("policy_id"),
                    record.get("classification"),
                    record.get("status"),
                    record.get("action"),
                    record.get("requester"),
                    record.get("target_agent"),
                    record.get("request_type"),
                    record.get("description"),
                    record.get("priority"),
                    record.get("risk_level"),
                    record.get("rationale"),
                    record.get("decided_by"),
                    record.get("decided_at"),
                    record.get("created_at"),
                    record.get("resolved_at"),
                    record.get("plan_id"),
                    record.get("job_id"),
                    record.get("connector_name"),
                    record.get("operation"),
                    json.dumps(record.get("context", {})),
                    record.get("projected_cost"),
                    record.get("cost_class"),
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save approval: {e}")
                return False

    def get_approval(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get an approval record by ID."""
        if not self._initialized:
            return None

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM approvals WHERE record_id = ?", (record_id,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approval records."""
        if not self._initialized:
            return []

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM approvals WHERE status = 'pending' ORDER BY created_at DESC"
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_approval_history(
        self,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get approval history."""
        if not self._initialized:
            return []

        with self._lock:
            if status:
                cursor = self._conn.execute(
                    "SELECT * FROM approvals WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)
                )
            else:
                cursor = self._conn.execute(
                    "SELECT * FROM approvals ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Jobs
    # =========================================================================

    def save_job(self, job: Dict[str, Any]) -> bool:
        """Save or update a job record."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO jobs (
                        job_id, plan_id, backend_type, status, priority,
                        dispatched_at, started_at, completed_at, worker_instance_id,
                        retry_count, error, total_steps, completed_steps, failed_steps,
                        duration_seconds, estimated_cost, actual_cost, cost_class,
                        options_json, result_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.get("job_id"),
                    job.get("plan_id"),
                    job.get("backend_type"),
                    job.get("status"),
                    job.get("priority"),
                    job.get("dispatched_at"),
                    job.get("started_at"),
                    job.get("completed_at"),
                    job.get("worker_instance_id"),
                    job.get("retry_count", 0),
                    job.get("error"),
                    job.get("total_steps"),
                    job.get("completed_steps"),
                    job.get("failed_steps"),
                    job.get("duration_seconds"),
                    job.get("estimated_cost"),
                    job.get("actual_cost"),
                    job.get("cost_class"),
                    json.dumps(job.get("options", {})),
                    json.dumps(job.get("result", {})),
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save job: {e}")
                return False

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID."""
        if not self._initialized:
            return None

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def get_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get jobs with optional status filter."""
        if not self._initialized:
            return []

        with self._lock:
            if status:
                cursor = self._conn.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY dispatched_at DESC LIMIT ?",
                    (status, limit)
                )
            else:
                cursor = self._conn.execute(
                    "SELECT * FROM jobs ORDER BY dispatched_at DESC LIMIT ?",
                    (limit,)
                )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get jobs that are pending, running, or queued."""
        if not self._initialized:
            return []

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM jobs WHERE status IN ('pending', 'running', 'queued') ORDER BY dispatched_at DESC"
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Execution Plans
    # =========================================================================

    def save_execution_plan(self, plan: Dict[str, Any]) -> bool:
        """Save or update an execution plan record."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO execution_plans (
                        plan_id, request_id, objective, primary_domain, status,
                        step_count, created_at, completed_at, requires_approval,
                        selected_skills_json, selected_commands_json, selected_agents_json,
                        backend_used, job_id, projected_cost, actual_cost, cost_class,
                        policy_decisions_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plan.get("plan_id"),
                    plan.get("request_id"),
                    plan.get("objective"),
                    plan.get("primary_domain"),
                    plan.get("status"),
                    plan.get("step_count"),
                    plan.get("created_at"),
                    plan.get("completed_at"),
                    1 if plan.get("requires_approval") else 0,
                    json.dumps(plan.get("selected_skills", [])),
                    json.dumps(plan.get("selected_commands", [])),
                    json.dumps(plan.get("selected_agents", [])),
                    plan.get("backend_used"),
                    plan.get("job_id"),
                    plan.get("projected_cost"),
                    plan.get("actual_cost"),
                    plan.get("cost_class"),
                    json.dumps(plan.get("policy_decisions", {})),
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save execution plan: {e}")
                return False

    def get_execution_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get an execution plan by ID."""
        if not self._initialized:
            return None

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM execution_plans WHERE plan_id = ?", (plan_id,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def get_recent_plans(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent execution plans."""
        if not self._initialized:
            return []

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM execution_plans ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Live Mode Promotions
    # =========================================================================

    def save_live_mode_promotion(self, promotion: Dict[str, Any]) -> bool:
        """Save or update a live mode promotion."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO live_mode_promotions (
                        promotion_id, connector, operation, promoted_by, approval_id,
                        risk_level, promoted_at, expires_at, used, used_at, execution_cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    promotion.get("promotion_id"),
                    promotion.get("connector"),
                    promotion.get("operation"),
                    promotion.get("promoted_by"),
                    promotion.get("approval_id"),
                    promotion.get("risk_level"),
                    promotion.get("promoted_at"),
                    promotion.get("expires_at"),
                    1 if promotion.get("used") else 0,
                    promotion.get("used_at"),
                    promotion.get("execution_cost"),
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save live mode promotion: {e}")
                return False

    def get_live_mode_promotions(
        self,
        used: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get live mode promotions."""
        if not self._initialized:
            return []

        with self._lock:
            if used is not None:
                cursor = self._conn.execute(
                    "SELECT * FROM live_mode_promotions WHERE used = ? ORDER BY promoted_at DESC LIMIT ?",
                    (1 if used else 0, limit)
                )
            else:
                cursor = self._conn.execute(
                    "SELECT * FROM live_mode_promotions ORDER BY promoted_at DESC LIMIT ?",
                    (limit,)
                )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Events
    # =========================================================================

    def save_event(self, event: Dict[str, Any]) -> bool:
        """Save an event record."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO events (
                        event_id, event_type, severity, timestamp, request_id,
                        business_id, agent_id, layer, message, error,
                        details_json, cost_related
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.get("event_id"),
                    event.get("event_type"),
                    event.get("severity"),
                    event.get("timestamp"),
                    event.get("request_id"),
                    event.get("business_id"),
                    event.get("agent_id"),
                    event.get("layer"),
                    event.get("message"),
                    event.get("error"),
                    json.dumps(event.get("details", {})),
                    1 if event.get("cost_related") else 0,
                ))

                # Trim old events if needed
                self._trim_events()

                return True
            except Exception as e:
                logger.error(f"Failed to save event: {e}")
                return False

    def _trim_events(self) -> None:
        """Trim old events to maintain storage limits."""
        try:
            cursor = self._conn.execute("SELECT COUNT(*) FROM events")
            count = cursor.fetchone()[0]

            if count > self._config.max_events_stored:
                # Delete oldest events beyond limit
                self._conn.execute("""
                    DELETE FROM events WHERE event_id IN (
                        SELECT event_id FROM events
                        ORDER BY timestamp ASC
                        LIMIT ?
                    )
                """, (count - self._config.max_events_stored,))
        except Exception as e:
            logger.error(f"Failed to trim events: {e}")

    def get_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get events with optional filters."""
        if not self._initialized:
            return []

        with self._lock:
            query = "SELECT * FROM events WHERE 1=1"
            params = []

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            if severity:
                query += " AND severity = ?"
                params.append(severity)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Connector Executions
    # =========================================================================

    def save_connector_execution(self, execution: Dict[str, Any]) -> bool:
        """Save a connector action execution record with audit fields."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO connector_executions (
                        execution_id, connector_name, action_name, operation, timestamp, mode,
                        success, duration_seconds, error, estimated_cost, actual_cost,
                        cost_class, approval_state, approval_id, execution_status,
                        job_id, plan_id, opportunity_id,
                        request_summary, response_summary, error_summary,
                        operator_decision_ref, params_json, result_summary, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution.get("execution_id"),
                    execution.get("connector_name"),
                    execution.get("action_name", execution.get("operation")),
                    execution.get("operation"),
                    execution.get("timestamp"),
                    execution.get("mode"),
                    1 if execution.get("success") else 0,
                    execution.get("duration_seconds"),
                    execution.get("error"),
                    execution.get("estimated_cost"),
                    execution.get("actual_cost"),
                    execution.get("cost_class"),
                    execution.get("approval_state"),
                    execution.get("approval_id"),
                    execution.get("execution_status"),
                    execution.get("job_id"),
                    execution.get("plan_id"),
                    execution.get("opportunity_id"),
                    execution.get("request_summary"),
                    execution.get("response_summary"),
                    execution.get("error_summary"),
                    execution.get("operator_decision_ref"),
                    json.dumps(execution.get("params", {})),
                    execution.get("result_summary"),
                    json.dumps(execution.get("metadata", {})),
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save connector execution: {e}")
                return False

    def get_connector_executions(
        self,
        connector_name: Optional[str] = None,
        action_name: Optional[str] = None,
        mode: Optional[str] = None,
        execution_status: Optional[str] = None,
        job_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        opportunity_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get connector action executions with filtering."""
        if not self._initialized:
            return []

        with self._lock:
            query = "SELECT * FROM connector_executions WHERE 1=1"
            params = []

            if connector_name:
                query += " AND connector_name = ?"
                params.append(connector_name)

            if action_name:
                query += " AND action_name = ?"
                params.append(action_name)

            if mode:
                query += " AND mode = ?"
                params.append(mode)

            if execution_status:
                query += " AND execution_status = ?"
                params.append(execution_status)

            if job_id:
                query += " AND job_id = ?"
                params.append(job_id)

            if plan_id:
                query += " AND plan_id = ?"
                params.append(plan_id)

            if opportunity_id:
                query += " AND opportunity_id = ?"
                params.append(opportunity_id)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_connector_execution_by_id(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get a connector action execution by ID."""
        if not self._initialized:
            return None

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM connector_executions WHERE execution_id = ?",
                (execution_id,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    # =========================================================================
    # Credential Health
    # =========================================================================

    def save_credential_health(self, health: Dict[str, Any]) -> bool:
        """Save credential health metadata (never stores secrets)."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO credential_health (
                        credential_name, connector, last_validated_at, valid,
                        expires_at, rotation_due_at, last_used_at, use_count,
                        health_status, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    health.get("credential_name"),
                    health.get("connector"),
                    health.get("last_validated_at"),
                    1 if health.get("valid") else 0,
                    health.get("expires_at"),
                    health.get("rotation_due_at"),
                    health.get("last_used_at"),
                    health.get("use_count", 0),
                    health.get("health_status"),
                    json.dumps(health.get("metadata", {})),
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save credential health: {e}")
                return False

    def get_credential_health(
        self,
        credential_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get credential health records."""
        if not self._initialized:
            return []

        with self._lock:
            if credential_name:
                cursor = self._conn.execute(
                    "SELECT * FROM credential_health WHERE credential_name = ?",
                    (credential_name,)
                )
            else:
                cursor = self._conn.execute("SELECT * FROM credential_health")
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Cost Records
    # =========================================================================

    def save_cost_record(self, cost: Dict[str, Any]) -> bool:
        """Save a cost record."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO cost_records (
                        cost_id, record_type, record_id, timestamp, connector,
                        operation, backend, business_id, plan_id, job_id,
                        cost_class, estimated_cost, actual_cost, cost_unknown,
                        currency, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cost.get("cost_id"),
                    cost.get("record_type"),
                    cost.get("record_id"),
                    cost.get("timestamp"),
                    cost.get("connector"),
                    cost.get("operation"),
                    cost.get("backend"),
                    cost.get("business_id"),
                    cost.get("plan_id"),
                    cost.get("job_id"),
                    cost.get("cost_class"),
                    cost.get("estimated_cost"),
                    cost.get("actual_cost"),
                    1 if cost.get("cost_unknown") else 0,
                    cost.get("currency", "USD"),
                    cost.get("notes"),
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save cost record: {e}")
                return False

    def get_cost_records(
        self,
        record_type: Optional[str] = None,
        connector: Optional[str] = None,
        business_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get cost records with optional filters."""
        if not self._initialized:
            return []

        with self._lock:
            query = "SELECT * FROM cost_records WHERE 1=1"
            params = []

            if record_type:
                query += " AND record_type = ?"
                params.append(record_type)

            if connector:
                query += " AND connector = ?"
                params.append(connector)

            if business_id:
                query += " AND business_id = ?"
                params.append(business_id)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Budget Snapshots
    # =========================================================================
    # OPPORTUNITY OPERATIONS
    # =========================================================================

    def save_opportunity(
        self,
        opportunity_id: str,
        hypothesis_data: Dict[str, Any],
        score_data: Dict[str, Any],
        recommendation_data: Dict[str, Any],
        status: str,
        operator_constraints_snapshot: Optional[Dict[str, Any]] = None,
        status_history: Optional[List[Dict[str, Any]]] = None,
        operator_notes: str = "",
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Save or update an opportunity record."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                now = _utc_now().isoformat()

                # Check if opportunity exists
                cursor = self._conn.execute(
                    "SELECT created_at FROM opportunities WHERE opportunity_id = ?",
                    (opportunity_id,)
                )
                existing = cursor.fetchone()
                created_at = existing[0] if existing else now

                self._conn.execute("""
                    INSERT OR REPLACE INTO opportunities (
                        opportunity_id, hypothesis_json, score_json, recommendation_json,
                        status, operator_constraints_json, status_history_json,
                        operator_notes, tags_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    opportunity_id,
                    json.dumps(hypothesis_data),
                    json.dumps(score_data),
                    json.dumps(recommendation_data),
                    status,
                    json.dumps(operator_constraints_snapshot) if operator_constraints_snapshot else None,
                    json.dumps(status_history or []),
                    operator_notes,
                    json.dumps(tags or []),
                    created_at,
                    now,
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save opportunity: {e}")
                return False

    def get_opportunity(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        """Get an opportunity by ID."""
        if not self._initialized:
            return None

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM opportunities WHERE opportunity_id = ?",
                (opportunity_id,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def list_opportunities(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List opportunities with optional filtering."""
        if not self._initialized:
            return []

        with self._lock:
            query = "SELECT * FROM opportunities WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # HANDOFF OPERATIONS
    # =========================================================================

    def save_handoff(
        self,
        handoff_id: str,
        opportunity_id: str,
        mode: str,
        status: str,
        context_data: Dict[str, Any],
        plan_id: Optional[str] = None,
        business_id: Optional[str] = None,
        job_id: Optional[str] = None,
        created_by: str = "operator",
    ) -> bool:
        """Save or update a handoff record."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                now = _utc_now().isoformat()

                # Check if handoff exists
                cursor = self._conn.execute(
                    "SELECT created_at FROM handoffs WHERE handoff_id = ?",
                    (handoff_id,)
                )
                existing = cursor.fetchone()
                created_at = existing[0] if existing else now

                self._conn.execute("""
                    INSERT OR REPLACE INTO handoffs (
                        handoff_id, opportunity_id, mode, status, context_json,
                        plan_id, business_id, job_id, created_at, completed_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    handoff_id,
                    opportunity_id,
                    mode,
                    status,
                    json.dumps(context_data),
                    plan_id,
                    business_id,
                    job_id,
                    created_at,
                    now if status in ["completed", "cancelled"] else None,
                    created_by,
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save handoff: {e}")
                return False

    def get_handoff(self, handoff_id: str) -> Optional[Dict[str, Any]]:
        """Get a handoff by ID."""
        if not self._initialized:
            return None

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM handoffs WHERE handoff_id = ?",
                (handoff_id,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def get_handoffs_by_opportunity(
        self,
        opportunity_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all handoffs for an opportunity."""
        if not self._initialized:
            return []

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM handoffs WHERE opportunity_id = ? ORDER BY created_at DESC",
                (opportunity_id,)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def list_handoffs(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List handoffs with optional filtering."""
        if not self._initialized:
            return []

        with self._lock:
            query = "SELECT * FROM handoffs WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # =========================================================================

    def save_budget_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """Save a budget snapshot."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO budget_snapshots (
                        snapshot_id, scope, scope_id, timestamp, period_start,
                        period_end, budget_limit, spent_total, spent_estimated,
                        spent_actual, remaining, utilization_pct, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot.get("snapshot_id"),
                    snapshot.get("scope"),
                    snapshot.get("scope_id"),
                    snapshot.get("timestamp"),
                    snapshot.get("period_start"),
                    snapshot.get("period_end"),
                    snapshot.get("budget_limit"),
                    snapshot.get("spent_total"),
                    snapshot.get("spent_estimated"),
                    snapshot.get("spent_actual"),
                    snapshot.get("remaining"),
                    snapshot.get("utilization_pct"),
                    json.dumps(snapshot.get("metadata", {})),
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save budget snapshot: {e}")
                return False

    def get_budget_snapshots(
        self,
        scope: Optional[str] = None,
        scope_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get budget snapshots."""
        if not self._initialized:
            return []

        with self._lock:
            query = "SELECT * FROM budget_snapshots WHERE 1=1"
            params = []

            if scope:
                query += " AND scope = ?"
                params.append(scope)

            if scope_id:
                query += " AND scope_id = ?"
                params.append(scope_id)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a sqlite3.Row to a dictionary, parsing JSON fields."""
        if row is None:
            return {}

        d = dict(row)

        # Parse JSON fields
        json_fields = [
            "context_json", "options_json", "result_json", "details_json",
            "selected_skills_json", "selected_commands_json", "selected_agents_json",
            "policy_decisions_json", "metadata_json", "params_json",
            "hypothesis_json", "score_json", "recommendation_json",
            "operator_constraints_json", "status_history_json", "tags_json",
            "metadata_json", "inputs_json", "step_results_json", "final_output_json",
            "plan_ids_json", "job_ids_json", "approval_ids_json",
            "connector_execution_ids_json"
        ]

        for field in json_fields:
            if field in d and d[field]:
                try:
                    # Special handling for discovery/handoff fields to match expected names
                    if field == "hypothesis_json":
                        key = "hypothesis_data"
                    elif field == "score_json":
                        key = "score_data"
                    elif field == "recommendation_json":
                        key = "recommendation_data"
                    elif field == "operator_constraints_json":
                        key = "operator_constraints_snapshot"
                    elif field == "status_history_json":
                        key = "status_history"
                    elif field == "tags_json":
                        key = "tags"
                    elif field == "context_json" and "handoffs" in str(type(row)):
                        # For handoff records, keep as handoff_context
                        key = "handoff_context"
                    else:
                        key = field.replace("_json", "")

                    d[key] = json.loads(d[field])
                    del d[field]
                except (json.JSONDecodeError, TypeError):
                    pass

        return d

    # =========================================================================
    # Capacity Management Persistence
    # =========================================================================

    def save_capacity_limit(self, dimension: str, limit_config: Dict[str, Any]) -> bool:
        """Save or update capacity limit configuration."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO capacity_limits (
                        dimension, soft_limit, hard_limit, enabled, description, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    dimension,
                    limit_config.get("soft_limit"),
                    limit_config.get("hard_limit"),
                    1 if limit_config.get("enabled", True) else 0,
                    limit_config.get("description", ""),
                    _utc_now().isoformat()
                ))
                self._conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to save capacity limit: {e}")
                self._conn.rollback()
                return False

    def get_capacity_limit(self, dimension: str) -> Optional[Dict[str, Any]]:
        """Get capacity limit configuration for a dimension."""
        if not self._initialized:
            return None

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM capacity_limits WHERE dimension = ?",
                (dimension,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    def list_capacity_limits(self) -> List[Dict[str, Any]]:
        """List all capacity limits."""
        if not self._initialized:
            return []

        with self._lock:
            cursor = self._conn.execute("SELECT * FROM capacity_limits ORDER BY dimension")
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def save_capacity_decision(self, decision: Dict[str, Any]) -> bool:
        """Save a capacity decision to audit trail."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                import uuid
                decision_id = decision.get("decision_id", f"cap_dec_{uuid.uuid4().hex[:12]}")

                self._conn.execute("""
                    INSERT INTO capacity_decisions (
                        decision_id, timestamp, dimension, decision,
                        current_count, projected_count, soft_limit, hard_limit,
                        reason, business_id, opportunity_id, plan_id, job_id,
                        runtime_backend, estimated_cost, context_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    decision_id,
                    decision.get("timestamp", _utc_now().isoformat()),
                    decision.get("dimension"),
                    decision.get("decision"),
                    decision.get("current_count", 0),
                    decision.get("projected_count", 0),
                    decision.get("soft_limit"),
                    decision.get("hard_limit"),
                    decision.get("reason", ""),
                    decision.get("context", {}).get("business_id"),
                    decision.get("context", {}).get("opportunity_id"),
                    decision.get("context", {}).get("plan_id"),
                    decision.get("context", {}).get("job_id"),
                    decision.get("context", {}).get("runtime_backend"),
                    decision.get("context", {}).get("estimated_cost"),
                    json.dumps(decision.get("context", {}))
                ))
                self._conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to save capacity decision: {e}")
                self._conn.rollback()
                return False

    def list_capacity_decisions(
        self,
        dimension: Optional[str] = None,
        decision: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List capacity decisions with optional filtering."""
        if not self._initialized:
            return []

        with self._lock:
            query = "SELECT * FROM capacity_decisions WHERE 1=1"
            params = []

            if dimension:
                query += " AND dimension = ?"
                params.append(dimension)

            if decision:
                query += " AND decision = ?"
                params.append(decision)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # SCENARIO RUN OPERATIONS
    # =========================================================================

    def save_scenario_run(self, run: Dict[str, Any]) -> bool:
        """Save or update a scenario run record."""
        if not self._initialized:
            return False

        with self._lock:
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO scenario_runs (
                        run_id, scenario_id, scenario_name, status, inputs_json,
                        dry_run, started_at, completed_at, duration_seconds,
                        step_results_json, total_steps, completed_steps, failed_steps,
                        skipped_steps, final_output_json, error_message, triggered_by,
                        plan_ids_json, job_ids_json, approval_ids_json,
                        connector_execution_ids_json, opportunity_id, handoff_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run.get("run_id"),
                    run.get("scenario_id"),
                    run.get("scenario_name"),
                    run.get("status"),
                    json.dumps(run.get("inputs", {})),
                    1 if run.get("dry_run", True) else 0,
                    run.get("started_at"),
                    run.get("completed_at"),
                    run.get("duration_seconds"),
                    json.dumps(run.get("step_results", [])),
                    run.get("total_steps", 0),
                    run.get("completed_steps", 0),
                    run.get("failed_steps", 0),
                    run.get("skipped_steps", 0),
                    json.dumps(run.get("final_output", {})),
                    run.get("error_message"),
                    run.get("triggered_by"),
                    json.dumps(run.get("plan_ids", [])),
                    json.dumps(run.get("job_ids", [])),
                    json.dumps(run.get("approval_ids", [])),
                    json.dumps(run.get("connector_execution_ids", [])),
                    run.get("opportunity_id"),
                    run.get("handoff_id"),
                ))
                return True
            except Exception as e:
                logger.error(f"Failed to save scenario run: {e}")
                return False

    def get_scenario_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get a scenario run by ID."""
        if not self._initialized:
            return None

        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM scenario_runs WHERE run_id = ?",
                (run_id,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def list_scenario_runs(
        self,
        scenario_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List scenario runs with optional filtering."""
        if not self._initialized:
            return []

        with self._lock:
            query = "SELECT * FROM scenario_runs WHERE 1=1"
            params = []

            if scenario_id:
                query += " AND scenario_id = ?"
                params.append(scenario_id)

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)

            cursor = self._conn.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_scenario_run_stats(self) -> Dict[str, Any]:
        """Get statistics for scenario runs."""
        if not self._initialized:
            return {}

        with self._lock:
            try:
                # Total runs
                cursor = self._conn.execute("SELECT COUNT(*) FROM scenario_runs")
                total = cursor.fetchone()[0]

                # By status
                cursor = self._conn.execute(
                    "SELECT status, COUNT(*) FROM scenario_runs GROUP BY status"
                )
                by_status = {row[0]: row[1] for row in cursor.fetchall()}

                # By scenario
                cursor = self._conn.execute(
                    "SELECT scenario_id, COUNT(*) FROM scenario_runs GROUP BY scenario_id"
                )
                by_scenario = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "total_runs": total,
                    "by_status": by_status,
                    "by_scenario": by_scenario,
                }
            except Exception as e:
                logger.error(f"Failed to get scenario run stats: {e}")
                return {}

    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        if not self._initialized:
            return {"initialized": False}

        with self._lock:
            stats = {"initialized": True}

            tables = [
                "approvals", "jobs", "execution_plans", "live_mode_promotions",
                "events", "connector_executions", "credential_health",
                "cost_records", "budget_snapshots", "opportunities", "handoffs",
                "capacity_limits", "capacity_decisions", "scenario_runs"
            ]

            for table in tables:
                try:
                    cursor = self._conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]
                except Exception:
                    stats[f"{table}_count"] = 0

            # Get database file size
            try:
                stats["db_size_bytes"] = os.path.getsize(self._config.db_path)
            except Exception:
                stats["db_size_bytes"] = 0

            return stats


# Singleton instance
_state_store: Optional[StateStore] = None


def get_state_store() -> StateStore:
    """Get the global state store."""
    global _state_store
    if _state_store is None:
        _state_store = StateStore()
    return _state_store


def initialize_state_store(config: Optional[StateStoreConfig] = None) -> StateStore:
    """Initialize and return the global state store."""
    global _state_store
    _state_store = StateStore(config)
    _state_store.initialize()
    return _state_store
