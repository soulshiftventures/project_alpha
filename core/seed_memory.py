"""
Seed Memory - Persistence for Seed Core learning.

Stores:
- Execution records (the fundamental learning data)
- Skill rankings (derived from execution records)
- Goals and decompositions
- Introspection snapshots

Uses existing Alpha persistence infrastructure where possible.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .seed_models import (
    Goal,
    GoalStatus,
    SkillExecutionRecord,
    SkillRanking,
    GoalDecomposition,
    OutcomeType,
)
from .state_store import StateStore, get_state_store

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class SeedMemory:
    """
    Memory layer for Seed Core.

    Persists execution records and learned rankings.
    Provides query interface for skill selection and learning.
    """

    def __init__(self, state_store: Optional[StateStore] = None):
        """
        Initialize Seed Memory.

        Args:
            state_store: Optional StateStore instance. Uses global if not provided.
        """
        self._state_store = state_store or get_state_store()
        self._initialized = False

        # In-memory caches for fast access
        self._rankings_cache: Dict[str, Dict[str, SkillRanking]] = {}  # goal_type -> skill_name -> ranking

    def initialize(self) -> bool:
        """Initialize memory layer."""
        try:
            if not self._state_store.is_initialized:
                logger.error("StateStore not initialized")
                return False

            # Ensure Seed Core tables exist
            self._ensure_tables()

            # Load rankings into cache
            self._load_rankings_cache()

            self._initialized = True
            logger.info("SeedMemory initialized")
            return True

        except Exception as e:
            logger.error(f"SeedMemory initialization failed: {e}")
            return False

    def _ensure_tables(self) -> None:
        """Ensure Seed Core tables exist in StateStore."""
        # Use existing state_store connection
        cursor = self._state_store._conn.cursor()

        # Execution records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seed_execution_records (
                execution_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                goal_type TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                outcome TEXT NOT NULL,
                quality_score REAL NOT NULL,
                timestamp TEXT NOT NULL,
                notes TEXT,
                selection_reason TEXT,
                success INTEGER NOT NULL,
                error_message TEXT,
                execution_context TEXT,
                result_data TEXT,
                approval_record_id TEXT
            )
        """)

        # Skill rankings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seed_skill_rankings (
                goal_type TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                total_executions INTEGER NOT NULL,
                successful_executions INTEGER NOT NULL,
                average_quality REAL NOT NULL,
                last_execution TEXT,
                success_rate REAL NOT NULL,
                confidence REAL NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (goal_type, skill_name)
            )
        """)

        # Goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seed_goals (
                goal_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                goal_type TEXT NOT NULL,
                status TEXT NOT NULL,
                parent_goal_id TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                metadata TEXT
            )
        """)

        # Goal decompositions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seed_goal_decompositions (
                decomposition_id TEXT PRIMARY KEY,
                parent_goal_id TEXT NOT NULL,
                sub_goal_ids TEXT NOT NULL,
                decomposition_strategy TEXT NOT NULL,
                created_at TEXT NOT NULL,
                notes TEXT
            )
        """)

        # Create indices for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_goal_type ON seed_execution_records(goal_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_skill_name ON seed_execution_records(skill_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_timestamp ON seed_execution_records(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_goals_status ON seed_goals(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_goals_type ON seed_goals(goal_type)")

        self._state_store._conn.commit()

    def _load_rankings_cache(self) -> None:
        """Load skill rankings into memory cache."""
        try:
            cursor = self._state_store._conn.cursor()
            cursor.execute("SELECT * FROM seed_skill_rankings")
            rows = cursor.fetchall()

            for row in rows:
                goal_type = row[0]
                skill_name = row[1]

                ranking = SkillRanking(
                    goal_type=goal_type,
                    skill_name=skill_name,
                    total_executions=row[2],
                    successful_executions=row[3],
                    average_quality=row[4],
                    last_execution=row[5],
                    success_rate=row[6],
                    confidence=row[7],
                    updated_at=row[8],
                )

                if goal_type not in self._rankings_cache:
                    self._rankings_cache[goal_type] = {}

                self._rankings_cache[goal_type][skill_name] = ranking

            logger.info(f"Loaded {len(rows)} skill rankings into cache")

        except Exception as e:
            logger.error(f"Failed to load rankings cache: {e}")

    # =========================================================================
    # Execution Record Operations
    # =========================================================================

    def save_execution_record(self, record: SkillExecutionRecord) -> bool:
        """Save a skill execution record and update rankings."""
        try:
            import json

            cursor = self._state_store._conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO seed_execution_records
                (execution_id, goal_id, goal_type, skill_name, outcome, quality_score,
                 timestamp, notes, selection_reason, success, error_message,
                 execution_context, result_data, approval_record_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.execution_id,
                record.goal_id,
                record.goal_type,
                record.skill_name,
                record.outcome.value,
                record.quality_score,
                record.timestamp,
                record.notes,
                record.selection_reason,
                1 if record.success else 0,
                record.error_message,
                json.dumps(record.execution_context),
                json.dumps(record.result_data),
                record.approval_record_id,
            ))

            self._state_store._conn.commit()

            # Update ranking
            self._update_ranking(record)

            return True

        except Exception as e:
            logger.error(f"Failed to save execution record: {e}")
            return False

    def get_execution_records(
        self,
        goal_type: Optional[str] = None,
        skill_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[SkillExecutionRecord]:
        """Get execution records with optional filtering."""
        try:
            import json

            cursor = self._state_store._conn.cursor()

            query = "SELECT * FROM seed_execution_records WHERE 1=1"
            params = []

            if goal_type:
                query += " AND goal_type = ?"
                params.append(goal_type)

            if skill_name:
                query += " AND skill_name = ?"
                params.append(skill_name)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            records = []
            for row in rows:
                records.append(SkillExecutionRecord(
                    execution_id=row[0],
                    goal_id=row[1],
                    goal_type=row[2],
                    skill_name=row[3],
                    outcome=OutcomeType(row[4]),
                    quality_score=row[5],
                    timestamp=row[6],
                    notes=row[7] or "",
                    selection_reason=row[8] or "",
                    success=bool(row[9]),
                    error_message=row[10],
                    execution_context=json.loads(row[11]) if row[11] else {},
                    result_data=json.loads(row[12]) if row[12] else {},
                    approval_record_id=row[13] if len(row) > 13 else None,
                ))

            return records

        except Exception as e:
            logger.error(f"Failed to get execution records: {e}")
            return []

    # =========================================================================
    # Skill Ranking Operations
    # =========================================================================

    def _update_ranking(self, record: SkillExecutionRecord) -> None:
        """Update skill ranking based on execution record."""
        try:
            goal_type = record.goal_type
            skill_name = record.skill_name

            # Get or create ranking
            if goal_type not in self._rankings_cache:
                self._rankings_cache[goal_type] = {}

            if skill_name not in self._rankings_cache[goal_type]:
                self._rankings_cache[goal_type][skill_name] = SkillRanking(
                    goal_type=goal_type,
                    skill_name=skill_name,
                )

            ranking = self._rankings_cache[goal_type][skill_name]
            ranking.update_from_execution(record)

            # Persist to database
            cursor = self._state_store._conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO seed_skill_rankings
                (goal_type, skill_name, total_executions, successful_executions,
                 average_quality, last_execution, success_rate, confidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ranking.goal_type,
                ranking.skill_name,
                ranking.total_executions,
                ranking.successful_executions,
                ranking.average_quality,
                ranking.last_execution,
                ranking.success_rate,
                ranking.confidence,
                ranking.updated_at,
            ))

            self._state_store._conn.commit()

        except Exception as e:
            logger.error(f"Failed to update ranking: {e}")

    def get_ranked_skills(self, goal_type: str, limit: int = 10) -> List[SkillRanking]:
        """
        Get skills ranked by learned performance for a goal type.

        Returns skills sorted by composite score (success rate + quality + confidence).
        """
        try:
            rankings = self._rankings_cache.get(goal_type, {})
            sorted_rankings = sorted(
                rankings.values(),
                key=lambda r: r.get_score(),
                reverse=True,
            )
            return sorted_rankings[:limit]

        except Exception as e:
            logger.error(f"Failed to get ranked skills: {e}")
            return []

    def get_all_rankings(self) -> Dict[str, List[SkillRanking]]:
        """Get all rankings grouped by goal type."""
        result = {}
        for goal_type, rankings in self._rankings_cache.items():
            result[goal_type] = list(rankings.values())
        return result

    # =========================================================================
    # Goal Operations
    # =========================================================================

    def save_goal(self, goal: Goal) -> bool:
        """Save a goal."""
        try:
            import json

            cursor = self._state_store._conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO seed_goals
                (goal_id, description, goal_type, status, parent_goal_id,
                 created_at, completed_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                goal.goal_id,
                goal.description,
                goal.goal_type,
                goal.status.value,
                goal.parent_goal_id,
                goal.created_at,
                goal.completed_at,
                json.dumps(goal.metadata),
            ))

            self._state_store._conn.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to save goal: {e}")
            return False

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        try:
            import json

            cursor = self._state_store._conn.cursor()
            cursor.execute("SELECT * FROM seed_goals WHERE goal_id = ?", (goal_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return Goal(
                goal_id=row[0],
                description=row[1],
                goal_type=row[2],
                status=GoalStatus(row[3]),
                parent_goal_id=row[4],
                created_at=row[5],
                completed_at=row[6],
                metadata=json.loads(row[7]) if row[7] else {},
            )

        except Exception as e:
            logger.error(f"Failed to get goal: {e}")
            return None

    def save_decomposition(self, decomposition: GoalDecomposition) -> bool:
        """Save a goal decomposition."""
        try:
            import json

            cursor = self._state_store._conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO seed_goal_decompositions
                (decomposition_id, parent_goal_id, sub_goal_ids, decomposition_strategy,
                 created_at, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                decomposition.decomposition_id,
                decomposition.parent_goal_id,
                json.dumps(decomposition.sub_goal_ids),
                decomposition.decomposition_strategy,
                decomposition.created_at,
                decomposition.notes,
            ))

            self._state_store._conn.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to save decomposition: {e}")
            return False

    # =========================================================================
    # Stats
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get Seed Memory statistics."""
        try:
            cursor = self._state_store._conn.cursor()

            # Count records
            cursor.execute("SELECT COUNT(*) FROM seed_execution_records")
            total_executions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM seed_skill_rankings")
            total_rankings = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM seed_goals")
            total_goals = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM seed_goal_decompositions")
            total_decompositions = cursor.fetchone()[0]

            # Successful executions
            cursor.execute("SELECT COUNT(*) FROM seed_execution_records WHERE success = 1")
            successful_executions = cursor.fetchone()[0]

            return {
                "initialized": self._initialized,
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "success_rate": successful_executions / total_executions if total_executions > 0 else 0.0,
                "total_rankings": total_rankings,
                "total_goals": total_goals,
                "total_decompositions": total_decompositions,
                "goal_types_learned": len(self._rankings_cache),
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}


# Singleton instance
_seed_memory: Optional[SeedMemory] = None


def get_seed_memory() -> SeedMemory:
    """Get the global Seed Memory instance."""
    global _seed_memory
    if _seed_memory is None:
        _seed_memory = SeedMemory()
    return _seed_memory


def initialize_seed_memory() -> SeedMemory:
    """Initialize and return the global Seed Memory instance."""
    memory = get_seed_memory()
    memory.initialize()
    return memory
