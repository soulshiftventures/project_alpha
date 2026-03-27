"""
Event Logger for Project Alpha
Structured logging for orchestration, decisions, approvals, and executions
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class EventType(Enum):
    """Types of events that can be logged."""
    # Orchestration events
    REQUEST_RECEIVED = "request_received"
    REQUEST_ROUTED = "request_routed"
    REQUEST_COMPLETED = "request_completed"
    REQUEST_FAILED = "request_failed"

    # Decision events
    DECISION_STARTED = "decision_started"
    DECISION_MADE = "decision_made"
    DECISION_ESCALATED = "decision_escalated"

    # Approval events
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_AUTO = "approval_auto"

    # Execution events
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Agent events
    AGENT_ACTIVATED = "agent_activated"
    AGENT_DEACTIVATED = "agent_deactivated"
    AGENT_ERROR = "agent_error"

    # Council events
    COUNCIL_CONVENED = "council_convened"
    RECOMMENDATION_SUBMITTED = "recommendation_submitted"
    COUNCIL_SYNTHESIS = "council_synthesis"

    # Board events
    BOARD_VOTE_STARTED = "board_vote_started"
    BOARD_VOTE_CAST = "board_vote_cast"
    BOARD_DECISION = "board_decision"

    # Skill Intelligence Layer events
    SKILLS_SELECTED = "skills_selected"
    SKILL_POLICY_EVALUATED = "skill_policy_evaluated"
    SKILL_BLOCKED = "skill_blocked"
    SKILL_APPROVAL_REQUIRED = "skill_approval_required"
    WORKFLOW_COMPOSED = "workflow_composed"
    EXECUTION_PLAN_CREATED = "execution_plan_created"
    EXECUTION_PLAN_STARTED = "execution_plan_started"
    EXECUTION_PLAN_COMPLETED = "execution_plan_completed"

    # Runtime Abstraction Layer events
    RUNTIME_INITIALIZED = "runtime_initialized"
    BACKEND_SELECTED = "backend_selected"
    JOB_DISPATCHED = "job_dispatched"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    WORKER_SPAWNED = "worker_spawned"
    WORKER_ASSIGNED = "worker_assigned"
    WORKER_RELEASED = "worker_released"

    # System events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    ERROR = "error"


class EventSeverity(Enum):
    """Severity levels for events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Event:
    """
    A single logged event.

    Captures all relevant context for audit trails,
    debugging, and learning from outcomes.
    """
    # Identification
    event_id: str = field(default_factory=lambda: f"evt_{_utc_now().strftime('%Y%m%d%H%M%S%f')}")
    event_type: EventType = EventType.REQUEST_RECEIVED
    severity: EventSeverity = EventSeverity.INFO

    # Timing
    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())

    # Context
    request_id: Optional[str] = None
    business_id: Optional[str] = None
    agent_id: Optional[str] = None
    layer: Optional[str] = None

    # Content
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    # Error tracking
    error: Optional[str] = None
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create from dictionary."""
        if "event_type" in data and isinstance(data["event_type"], str):
            data["event_type"] = EventType(data["event_type"])
        if "severity" in data and isinstance(data["severity"], str):
            data["severity"] = EventSeverity(data["severity"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class EventLogger:
    """
    Central event logging system for the hierarchy.

    Provides:
    - Structured event recording
    - Query by type, agent, request
    - Persistence to file
    - In-memory buffer for performance
    """

    def __init__(self, log_file: Optional[str] = None, max_buffer_size: int = 1000):
        """
        Initialize the event logger.

        Args:
            log_file: Optional path to persist events
            max_buffer_size: Maximum events to keep in memory
        """
        self._events: List[Event] = []
        self._max_buffer_size = max_buffer_size

        # Set log file path
        if log_file is None:
            log_file = os.environ.get(
                "PROJECT_ALPHA_EVENT_LOG",
                "project_alpha/logs/events.jsonl"
            )
        self._log_file = log_file
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        """Ensure log directory exists."""
        if self._log_file:
            log_dir = os.path.dirname(self._log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

    def log(
        self,
        event_type: EventType,
        message: str,
        severity: EventSeverity = EventSeverity.INFO,
        request_id: Optional[str] = None,
        business_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        layer: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Event:
        """
        Log an event.

        Args:
            event_type: Type of event
            message: Human-readable message
            severity: Event severity level
            request_id: Related request ID
            business_id: Related business ID
            agent_id: Agent that generated the event
            layer: Hierarchy layer
            details: Additional details dictionary
            error: Error message if any

        Returns:
            The logged Event
        """
        event = Event(
            event_type=event_type,
            severity=severity,
            message=message,
            request_id=request_id,
            business_id=business_id,
            agent_id=agent_id,
            layer=layer,
            details=details or {},
            error=error
        )

        # Add to buffer
        self._events.append(event)

        # Trim buffer if needed
        if len(self._events) > self._max_buffer_size:
            self._events = self._events[-self._max_buffer_size:]

        # Persist to file
        self._persist_event(event)

        return event

    def _persist_event(self, event: Event) -> None:
        """Persist a single event to file."""
        if not self._log_file:
            return

        try:
            with open(self._log_file, "a") as f:
                f.write(event.to_json() + "\n")
        except Exception:
            pass  # Fail silently for logging

    # Convenience methods for common event types

    def log_request_received(
        self,
        request_id: str,
        agent_id: str,
        objective: str,
        **kwargs
    ) -> Event:
        """Log a request received event."""
        return self.log(
            event_type=EventType.REQUEST_RECEIVED,
            message=f"Request received: {objective[:100]}",
            request_id=request_id,
            agent_id=agent_id,
            details={"objective": objective, **kwargs}
        )

    def log_request_routed(
        self,
        request_id: str,
        from_agent: str,
        to_agent: str,
        reason: str
    ) -> Event:
        """Log a request routed event."""
        return self.log(
            event_type=EventType.REQUEST_ROUTED,
            message=f"Request routed from {from_agent} to {to_agent}",
            request_id=request_id,
            agent_id=from_agent,
            details={"from": from_agent, "to": to_agent, "reason": reason}
        )

    def log_decision(
        self,
        request_id: str,
        agent_id: str,
        decision: str,
        rationale: str,
        confidence: float
    ) -> Event:
        """Log a decision made event."""
        return self.log(
            event_type=EventType.DECISION_MADE,
            message=f"Decision made: {decision[:100]}",
            request_id=request_id,
            agent_id=agent_id,
            details={
                "decision": decision,
                "rationale": rationale,
                "confidence": confidence
            }
        )

    def log_approval(
        self,
        request_id: str,
        approved: bool,
        approver: str,
        reason: str
    ) -> Event:
        """Log an approval event."""
        event_type = EventType.APPROVAL_GRANTED if approved else EventType.APPROVAL_DENIED
        return self.log(
            event_type=event_type,
            message=f"Approval {'granted' if approved else 'denied'} by {approver}",
            request_id=request_id,
            agent_id=approver,
            details={"approved": approved, "reason": reason}
        )

    def log_task_execution(
        self,
        request_id: str,
        task_id: str,
        agent_id: str,
        status: str,
        result: Optional[Dict] = None
    ) -> Event:
        """Log a task execution event."""
        event_type = EventType.TASK_COMPLETED if status == "completed" else EventType.TASK_FAILED
        return self.log(
            event_type=event_type,
            message=f"Task {task_id} {status}",
            request_id=request_id,
            agent_id=agent_id,
            details={"task_id": task_id, "status": status, "result": result or {}}
        )

    def log_error(
        self,
        message: str,
        error: str,
        request_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        stack_trace: Optional[str] = None
    ) -> Event:
        """Log an error event."""
        event = Event(
            event_type=EventType.ERROR,
            severity=EventSeverity.ERROR,
            message=message,
            request_id=request_id,
            agent_id=agent_id,
            error=error,
            stack_trace=stack_trace
        )
        self._events.append(event)
        self._persist_event(event)
        return event

    # Query methods

    def get_events(
        self,
        event_type: Optional[EventType] = None,
        request_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        severity: Optional[EventSeverity] = None,
        since: Optional[str] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Query events with filters.

        Args:
            event_type: Filter by event type
            request_id: Filter by request ID
            agent_id: Filter by agent ID
            severity: Filter by severity
            since: Filter events after this ISO timestamp
            limit: Maximum events to return

        Returns:
            List of matching events
        """
        results = self._events

        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]

        if request_id is not None:
            results = [e for e in results if e.request_id == request_id]

        if agent_id is not None:
            results = [e for e in results if e.agent_id == agent_id]

        if severity is not None:
            results = [e for e in results if e.severity == severity]

        if since is not None:
            results = [e for e in results if e.timestamp >= since]

        return results[-limit:]

    def get_request_timeline(self, request_id: str) -> List[Event]:
        """
        Get all events for a specific request in chronological order.

        Args:
            request_id: Request ID to query

        Returns:
            List of events for that request
        """
        events = [e for e in self._events if e.request_id == request_id]
        return sorted(events, key=lambda e: e.timestamp)

    def get_agent_activity(self, agent_id: str, limit: int = 50) -> List[Event]:
        """
        Get recent activity for a specific agent.

        Args:
            agent_id: Agent ID to query
            limit: Maximum events to return

        Returns:
            List of events for that agent
        """
        events = [e for e in self._events if e.agent_id == agent_id]
        return events[-limit:]

    def get_errors(self, limit: int = 50) -> List[Event]:
        """
        Get recent error events.

        Args:
            limit: Maximum events to return

        Returns:
            List of error events
        """
        errors = [
            e for e in self._events
            if e.severity in [EventSeverity.ERROR, EventSeverity.CRITICAL]
        ]
        return errors[-limit:]

    def get_decisions(self, limit: int = 50) -> List[Event]:
        """
        Get recent decision events.

        Args:
            limit: Maximum events to return

        Returns:
            List of decision events
        """
        decision_types = [
            EventType.DECISION_MADE,
            EventType.BOARD_DECISION,
            EventType.COUNCIL_SYNTHESIS
        ]
        decisions = [e for e in self._events if e.event_type in decision_types]
        return decisions[-limit:]

    def count_by_type(self) -> Dict[str, int]:
        """
        Get count of events by type.

        Returns:
            Dictionary of event type to count
        """
        counts: Dict[str, int] = {}
        for event in self._events:
            type_name = event.event_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    def clear(self) -> None:
        """Clear all events from memory (file persists)."""
        self._events = []

    def export(self) -> List[Dict[str, Any]]:
        """Export all events as list of dictionaries."""
        return [e.to_dict() for e in self._events]

    # Skill Intelligence Layer logging methods

    def log_skills_selected(
        self,
        request_id: str,
        agent_id: str,
        skills: List[str],
        commands: List[str],
        specialized_agents: List[str],
        confidence: float = 0.0
    ) -> Event:
        """Log skills, commands, and agents selected for a task."""
        return self.log(
            event_type=EventType.SKILLS_SELECTED,
            message=f"Selected {len(skills)} skills, {len(commands)} commands, {len(specialized_agents)} agents",
            request_id=request_id,
            agent_id=agent_id,
            details={
                "skills": skills,
                "commands": commands,
                "specialized_agents": specialized_agents,
                "confidence": confidence
            }
        )

    def log_skill_policy_evaluated(
        self,
        request_id: str,
        skill_name: str,
        role_id: str,
        decision: str,
        reason: str
    ) -> Event:
        """Log a skill policy evaluation."""
        severity = EventSeverity.WARNING if decision == "blocked" else EventSeverity.INFO
        return self.log(
            event_type=EventType.SKILL_POLICY_EVALUATED,
            message=f"Policy evaluation for '{skill_name}': {decision}",
            severity=severity,
            request_id=request_id,
            agent_id=role_id,
            details={
                "skill_name": skill_name,
                "role_id": role_id,
                "decision": decision,
                "reason": reason
            }
        )

    def log_skill_blocked(
        self,
        request_id: str,
        skill_name: str,
        role_id: str,
        reason: str
    ) -> Event:
        """Log a blocked skill."""
        return self.log(
            event_type=EventType.SKILL_BLOCKED,
            message=f"Skill blocked: {skill_name}",
            severity=EventSeverity.WARNING,
            request_id=request_id,
            agent_id=role_id,
            details={
                "skill_name": skill_name,
                "role_id": role_id,
                "reason": reason
            }
        )

    def log_skill_approval_required(
        self,
        request_id: str,
        skill_name: str,
        role_id: str,
        approver: str
    ) -> Event:
        """Log when a skill requires approval."""
        return self.log(
            event_type=EventType.SKILL_APPROVAL_REQUIRED,
            message=f"Skill requires approval: {skill_name}",
            request_id=request_id,
            agent_id=role_id,
            details={
                "skill_name": skill_name,
                "role_id": role_id,
                "required_approver": approver
            }
        )

    def log_workflow_composed(
        self,
        request_id: str,
        agent_id: str,
        pattern_name: str,
        step_count: int,
        requires_approval: bool
    ) -> Event:
        """Log workflow composition."""
        return self.log(
            event_type=EventType.WORKFLOW_COMPOSED,
            message=f"Workflow composed from pattern '{pattern_name}' with {step_count} steps",
            request_id=request_id,
            agent_id=agent_id,
            details={
                "pattern_name": pattern_name,
                "step_count": step_count,
                "requires_approval": requires_approval
            }
        )

    def log_execution_plan_created(
        self,
        request_id: str,
        plan_id: str,
        objective: str,
        domain: str,
        skill_count: int,
        step_count: int,
        requires_approval: bool
    ) -> Event:
        """Log execution plan creation."""
        return self.log(
            event_type=EventType.EXECUTION_PLAN_CREATED,
            message=f"Execution plan created: {plan_id}",
            request_id=request_id,
            details={
                "plan_id": plan_id,
                "objective": objective[:100],
                "domain": domain,
                "skill_count": skill_count,
                "step_count": step_count,
                "requires_approval": requires_approval
            }
        )

    def log_execution_plan_completed(
        self,
        request_id: str,
        plan_id: str,
        success: bool,
        steps_completed: int,
        steps_total: int
    ) -> Event:
        """Log execution plan completion."""
        event_type = EventType.EXECUTION_PLAN_COMPLETED
        severity = EventSeverity.INFO if success else EventSeverity.WARNING
        return self.log(
            event_type=event_type,
            message=f"Execution plan {'completed' if success else 'failed'}: {plan_id}",
            severity=severity,
            request_id=request_id,
            details={
                "plan_id": plan_id,
                "success": success,
                "steps_completed": steps_completed,
                "steps_total": steps_total
            }
        )

    # Runtime Abstraction Layer logging methods

    def log_runtime_initialized(
        self,
        backends: List[str],
        default_backend: str,
        worker_count: int
    ) -> Event:
        """Log runtime initialization."""
        return self.log(
            event_type=EventType.RUNTIME_INITIALIZED,
            message=f"Runtime initialized with {len(backends)} backends",
            details={
                "backends": backends,
                "default_backend": default_backend,
                "worker_count": worker_count
            }
        )

    def log_backend_selected(
        self,
        request_id: str,
        plan_id: str,
        backend_type: str,
        selection_reason: str
    ) -> Event:
        """Log backend selection for a plan."""
        return self.log(
            event_type=EventType.BACKEND_SELECTED,
            message=f"Backend selected: {backend_type}",
            request_id=request_id,
            details={
                "plan_id": plan_id,
                "backend_type": backend_type,
                "selection_reason": selection_reason
            }
        )

    def log_job_dispatched(
        self,
        request_id: str,
        job_id: str,
        plan_id: str,
        backend_type: str,
        priority: str
    ) -> Event:
        """Log job dispatch."""
        return self.log(
            event_type=EventType.JOB_DISPATCHED,
            message=f"Job dispatched: {job_id}",
            request_id=request_id,
            details={
                "job_id": job_id,
                "plan_id": plan_id,
                "backend_type": backend_type,
                "priority": priority
            }
        )

    def log_job_started(
        self,
        request_id: str,
        job_id: str,
        backend_type: str,
        step_count: int
    ) -> Event:
        """Log job start."""
        return self.log(
            event_type=EventType.JOB_STARTED,
            message=f"Job started: {job_id} with {step_count} steps",
            request_id=request_id,
            details={
                "job_id": job_id,
                "backend_type": backend_type,
                "step_count": step_count
            }
        )

    def log_job_completed(
        self,
        request_id: str,
        job_id: str,
        backend_type: str,
        steps_completed: int,
        steps_total: int,
        execution_time_seconds: float
    ) -> Event:
        """Log job completion."""
        return self.log(
            event_type=EventType.JOB_COMPLETED,
            message=f"Job completed: {job_id}",
            request_id=request_id,
            details={
                "job_id": job_id,
                "backend_type": backend_type,
                "steps_completed": steps_completed,
                "steps_total": steps_total,
                "execution_time_seconds": execution_time_seconds
            }
        )

    def log_job_failed(
        self,
        request_id: str,
        job_id: str,
        backend_type: str,
        error: str,
        steps_completed: int,
        steps_total: int
    ) -> Event:
        """Log job failure."""
        return self.log(
            event_type=EventType.JOB_FAILED,
            message=f"Job failed: {job_id}",
            severity=EventSeverity.ERROR,
            request_id=request_id,
            error=error,
            details={
                "job_id": job_id,
                "backend_type": backend_type,
                "steps_completed": steps_completed,
                "steps_total": steps_total
            }
        )

    def log_job_cancelled(
        self,
        request_id: str,
        job_id: str,
        reason: str
    ) -> Event:
        """Log job cancellation."""
        return self.log(
            event_type=EventType.JOB_CANCELLED,
            message=f"Job cancelled: {job_id}",
            severity=EventSeverity.WARNING,
            request_id=request_id,
            details={
                "job_id": job_id,
                "reason": reason
            }
        )

    def log_step_started(
        self,
        request_id: str,
        job_id: str,
        step_id: str,
        step_name: str,
        domain: str
    ) -> Event:
        """Log step start."""
        return self.log(
            event_type=EventType.STEP_STARTED,
            message=f"Step started: {step_name}",
            request_id=request_id,
            details={
                "job_id": job_id,
                "step_id": step_id,
                "step_name": step_name,
                "domain": domain
            }
        )

    def log_step_completed(
        self,
        request_id: str,
        job_id: str,
        step_id: str,
        step_name: str,
        duration_seconds: float
    ) -> Event:
        """Log step completion."""
        return self.log(
            event_type=EventType.STEP_COMPLETED,
            message=f"Step completed: {step_name}",
            request_id=request_id,
            details={
                "job_id": job_id,
                "step_id": step_id,
                "step_name": step_name,
                "duration_seconds": duration_seconds
            }
        )

    def log_step_failed(
        self,
        request_id: str,
        job_id: str,
        step_id: str,
        step_name: str,
        error: str
    ) -> Event:
        """Log step failure."""
        return self.log(
            event_type=EventType.STEP_FAILED,
            message=f"Step failed: {step_name}",
            severity=EventSeverity.ERROR,
            request_id=request_id,
            error=error,
            details={
                "job_id": job_id,
                "step_id": step_id,
                "step_name": step_name
            }
        )

    def log_worker_spawned(
        self,
        worker_id: str,
        worker_type: str,
        capabilities: List[str]
    ) -> Event:
        """Log worker spawn."""
        return self.log(
            event_type=EventType.WORKER_SPAWNED,
            message=f"Worker spawned: {worker_id}",
            agent_id=worker_id,
            details={
                "worker_id": worker_id,
                "worker_type": worker_type,
                "capabilities": capabilities
            }
        )

    def log_worker_assigned(
        self,
        request_id: str,
        worker_id: str,
        job_id: str,
        step_id: str
    ) -> Event:
        """Log worker assignment to a step."""
        return self.log(
            event_type=EventType.WORKER_ASSIGNED,
            message=f"Worker {worker_id} assigned to step {step_id}",
            request_id=request_id,
            agent_id=worker_id,
            details={
                "worker_id": worker_id,
                "job_id": job_id,
                "step_id": step_id
            }
        )

    def log_worker_released(
        self,
        request_id: str,
        worker_id: str,
        job_id: str,
        success: bool
    ) -> Event:
        """Log worker release."""
        return self.log(
            event_type=EventType.WORKER_RELEASED,
            message=f"Worker {worker_id} released",
            request_id=request_id,
            agent_id=worker_id,
            details={
                "worker_id": worker_id,
                "job_id": job_id,
                "completed_successfully": success
            }
        )
