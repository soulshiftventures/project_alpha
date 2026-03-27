"""
Credential Rotation Manager for Project Alpha.

Tracks credential rotation schedules and alerts on upcoming/overdue rotations.

SECURITY RULES:
- This module NEVER handles actual credential values
- Only tracks rotation metadata and schedules
- Actual rotation is performed externally
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

from core.secrets_manager import (
    SecretMetadata,
    SecretsManager,
    get_secrets_manager,
    SecretSensitivity,
)
from config.redaction import REDACTION_MARKER


class RotationStatus(Enum):
    """Status of credential rotation."""
    CURRENT = "current"           # Recently rotated, not due
    DUE_SOON = "due_soon"         # Will be due within warning period
    OVERDUE = "overdue"           # Past rotation due date
    NEVER_ROTATED = "never_rotated"  # No rotation history
    UNKNOWN = "unknown"           # Status cannot be determined


class RotationUrgency(Enum):
    """Urgency level for rotation."""
    LOW = "low"           # More than 30 days until due
    MEDIUM = "medium"     # 7-30 days until due
    HIGH = "high"         # Less than 7 days until due
    CRITICAL = "critical"  # Overdue


@dataclass
class RotationSchedule:
    """
    Rotation schedule for a credential.

    Tracks when credentials should be rotated based on
    sensitivity and compliance requirements.
    """

    credential_name: str
    interval_days: int = 90
    warning_days: int = 14
    last_rotated: Optional[datetime] = None
    next_due: Optional[datetime] = None
    auto_alert: bool = True
    notes: str = ""

    def __post_init__(self):
        """Calculate next due date if last_rotated is set."""
        if self.last_rotated and not self.next_due:
            self.next_due = self.last_rotated + timedelta(days=self.interval_days)

    def get_status(self) -> RotationStatus:
        """Get current rotation status."""
        if not self.last_rotated:
            return RotationStatus.NEVER_ROTATED

        if not self.next_due:
            return RotationStatus.UNKNOWN

        now = datetime.now(timezone.utc)

        if now >= self.next_due:
            return RotationStatus.OVERDUE

        warning_date = self.next_due - timedelta(days=self.warning_days)
        if now >= warning_date:
            return RotationStatus.DUE_SOON

        return RotationStatus.CURRENT

    def get_urgency(self) -> RotationUrgency:
        """Get urgency level for rotation."""
        status = self.get_status()

        if status == RotationStatus.OVERDUE:
            return RotationUrgency.CRITICAL

        if status == RotationStatus.NEVER_ROTATED:
            return RotationUrgency.HIGH

        if not self.next_due:
            return RotationUrgency.LOW

        now = datetime.now(timezone.utc)
        days_until = (self.next_due - now).days

        if days_until < 7:
            return RotationUrgency.HIGH
        if days_until < 30:
            return RotationUrgency.MEDIUM

        return RotationUrgency.LOW

    def days_until_due(self) -> Optional[int]:
        """Get days until rotation is due."""
        if not self.next_due:
            return None

        now = datetime.now(timezone.utc)
        delta = self.next_due - now
        return delta.days

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "credential_name": self.credential_name,
            "interval_days": self.interval_days,
            "warning_days": self.warning_days,
            "last_rotated": self.last_rotated.isoformat() if self.last_rotated else None,
            "next_due": self.next_due.isoformat() if self.next_due else None,
            "status": self.get_status().value,
            "urgency": self.get_urgency().value,
            "days_until_due": self.days_until_due(),
            "auto_alert": self.auto_alert,
            "notes": self.notes,
        }


@dataclass
class RotationEvent:
    """Record of a rotation event."""

    credential_name: str
    event_type: str  # "rotated", "scheduled", "overdue_alert"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    performed_by: str = "system"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "credential_name": self.credential_name,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "performed_by": self.performed_by,
            "notes": self.notes,
        }


class RotationManager:
    """
    Manages credential rotation schedules and alerts.

    SECURITY:
    - Does NOT perform actual credential rotation
    - Only tracks schedules and generates alerts
    - Actual rotation is external to this system
    """

    def __init__(self, secrets_manager: Optional[SecretsManager] = None):
        self._secrets_manager = secrets_manager or get_secrets_manager()
        self._schedules: Dict[str, RotationSchedule] = {}
        self._events: List[RotationEvent] = []
        self._alert_callbacks: List[Callable[[str, RotationUrgency], None]] = []
        self._load_default_schedules()

    def _load_default_schedules(self) -> None:
        """Load default rotation schedules based on secret metadata."""
        for secret_name in self._secrets_manager.list_secrets():
            metadata = self._secrets_manager.get_metadata(secret_name)
            if metadata:
                # Determine interval based on sensitivity
                interval = self._get_interval_for_sensitivity(metadata.sensitivity)

                schedule = RotationSchedule(
                    credential_name=secret_name,
                    interval_days=interval,
                    warning_days=self._get_warning_days(interval),
                    last_rotated=metadata.last_rotated,
                    next_due=metadata.next_rotation_due,
                )
                self._schedules[secret_name] = schedule

    def _get_interval_for_sensitivity(self, sensitivity: SecretSensitivity) -> int:
        """Get rotation interval based on sensitivity."""
        intervals = {
            SecretSensitivity.LOW: 180,       # 6 months
            SecretSensitivity.MEDIUM: 90,     # 3 months
            SecretSensitivity.HIGH: 60,       # 2 months
            SecretSensitivity.CRITICAL: 30,   # 1 month
        }
        return intervals.get(sensitivity, 90)

    def _get_warning_days(self, interval: int) -> int:
        """Get warning days based on interval."""
        # Warning at 15% of interval, minimum 7 days
        return max(7, interval // 7)

    def register_schedule(self, schedule: RotationSchedule) -> None:
        """Register or update a rotation schedule."""
        self._schedules[schedule.credential_name] = schedule

    def get_schedule(self, credential_name: str) -> Optional[RotationSchedule]:
        """Get rotation schedule for a credential."""
        return self._schedules.get(credential_name)

    def record_rotation(
        self,
        credential_name: str,
        performed_by: str = "system",
        notes: str = "",
    ) -> None:
        """
        Record that a credential has been rotated.

        This updates the schedule but does NOT perform actual rotation.

        Args:
            credential_name: Credential that was rotated
            performed_by: Who performed the rotation
            notes: Additional notes
        """
        schedule = self._schedules.get(credential_name)
        if not schedule:
            # Create a new schedule
            schedule = RotationSchedule(credential_name=credential_name)
            self._schedules[credential_name] = schedule

        now = datetime.now(timezone.utc)
        schedule.last_rotated = now
        schedule.next_due = now + timedelta(days=schedule.interval_days)

        event = RotationEvent(
            credential_name=credential_name,
            event_type="rotated",
            performed_by=performed_by,
            notes=notes,
        )
        self._events.append(event)

    def register_alert_callback(
        self,
        callback: Callable[[str, RotationUrgency], None]
    ) -> None:
        """Register a callback for rotation alerts."""
        self._alert_callbacks.append(callback)

    def check_rotations(self) -> List[Dict[str, Any]]:
        """
        Check all credentials for rotation status.

        Returns list of credentials requiring attention.
        """
        alerts = []

        for cred_name, schedule in self._schedules.items():
            status = schedule.get_status()
            urgency = schedule.get_urgency()

            if urgency in (RotationUrgency.HIGH, RotationUrgency.CRITICAL):
                alert = {
                    "credential_name": cred_name,
                    "status": status.value,
                    "urgency": urgency.value,
                    "days_until_due": schedule.days_until_due(),
                    "last_rotated": schedule.last_rotated.isoformat() if schedule.last_rotated else None,
                }
                alerts.append(alert)

                # Trigger callbacks
                for callback in self._alert_callbacks:
                    try:
                        callback(cred_name, urgency)
                    except Exception:
                        pass  # Don't let callback errors break the check

        return alerts

    def get_overdue(self) -> List[str]:
        """Get list of overdue credentials."""
        return [
            name for name, schedule in self._schedules.items()
            if schedule.get_status() == RotationStatus.OVERDUE
        ]

    def get_due_soon(self) -> List[str]:
        """Get list of credentials due soon."""
        return [
            name for name, schedule in self._schedules.items()
            if schedule.get_status() == RotationStatus.DUE_SOON
        ]

    def get_never_rotated(self) -> List[str]:
        """Get list of credentials that have never been rotated."""
        return [
            name for name, schedule in self._schedules.items()
            if schedule.get_status() == RotationStatus.NEVER_ROTATED
        ]

    def get_events(
        self,
        credential_name: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[RotationEvent]:
        """Get rotation events with optional filters."""
        filtered = self._events

        if credential_name:
            filtered = [e for e in filtered if e.credential_name == credential_name]

        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]

        return filtered[-limit:]

    def get_summary(self) -> Dict[str, Any]:
        """Get rotation summary."""
        total = len(self._schedules)

        by_status = {}
        for status in RotationStatus:
            count = len([
                s for s in self._schedules.values()
                if s.get_status() == status
            ])
            by_status[status.value] = count

        by_urgency = {}
        for urgency in RotationUrgency:
            count = len([
                s for s in self._schedules.values()
                if s.get_urgency() == urgency
            ])
            by_urgency[urgency.value] = count

        overdue = self.get_overdue()
        due_soon = self.get_due_soon()

        health = "healthy"
        if len(overdue) > 0:
            health = "critical"
        elif len(due_soon) > 0:
            health = "warning"

        return {
            "total_credentials": total,
            "health": health,
            "by_status": by_status,
            "by_urgency": by_urgency,
            "overdue_count": len(overdue),
            "due_soon_count": len(due_soon),
            "event_count": len(self._events),
        }

    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """Get all rotation schedules."""
        return [schedule.to_dict() for schedule in self._schedules.values()]


# Singleton instance
_rotation_manager: Optional[RotationManager] = None


def get_rotation_manager() -> RotationManager:
    """Get the global rotation manager."""
    global _rotation_manager
    if _rotation_manager is None:
        _rotation_manager = RotationManager()
    return _rotation_manager
