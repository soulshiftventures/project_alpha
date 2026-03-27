"""
Agent Contracts for Project Alpha
Standard request/response structures for all agent interactions
"""

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class RequestStatus(Enum):
    """Status values for agent requests."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_APPROVAL = "awaiting_approval"
    REJECTED = "rejected"


class AgentLayer(Enum):
    """Hierarchy layers in the agent system."""
    PRINCIPAL = "principal"
    EXECUTIVE = "executive"
    COUNCIL = "council"
    BOARD = "board"
    C_SUITE = "c_suite"
    DEPARTMENT = "department"
    EXECUTION = "execution"


@dataclass
class AgentRequest:
    """
    Standard request structure for agent interactions.

    All agent requests flow through this contract to ensure
    consistent tracking, routing, and governance.
    """
    # Identification
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    business_id: Optional[str] = None
    task_id: Optional[str] = None

    # Routing
    requester: str = ""  # Agent or layer making the request
    target_agent: str = ""  # Agent or layer to handle the request

    # Content
    objective: str = ""  # What needs to be accomplished
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    priority: str = "medium"  # low, medium, high, critical
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())
    deadline: Optional[str] = None

    # Parent tracking for chain of command
    parent_request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentRequest":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AgentResponse:
    """
    Standard response structure for agent interactions.

    All agent responses use this contract for consistent
    result handling and decision tracking.
    """
    # Identification (linked to request)
    request_id: str = ""
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Response source
    responder: str = ""  # Agent that produced this response

    # Status
    status: RequestStatus = RequestStatus.PENDING

    # Result
    result: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0  # 0.0 to 1.0

    # Errors
    errors: List[str] = field(default_factory=list)

    # Metadata
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())
    processing_time_ms: float = 0.0

    # Decision tracking
    rationale: str = ""  # Why this decision was made
    alternatives_considered: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentResponse":
        """Create from dictionary."""
        if "status" in data and isinstance(data["status"], str):
            data["status"] = RequestStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.status == RequestStatus.COMPLETED and not self.errors


@dataclass
class DecisionRecord:
    """
    Structured record of a decision made by the hierarchy.

    Used for governance, audit trails, and learning from outcomes.
    """
    # Identification
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""

    # Decision content
    decision_type: str = ""  # e.g., "strategic", "operational", "approval"
    decision: str = ""  # The actual decision made
    rationale: str = ""  # Why this decision was made

    # Context
    options_considered: List[Dict[str, Any]] = field(default_factory=list)
    selected_option_index: int = -1

    # Confidence and scores
    confidence: float = 0.0
    scores: Dict[str, float] = field(default_factory=dict)

    # Chain of command
    decided_by: str = ""  # Agent/layer that made the decision
    approved_by: Optional[str] = None  # If approval was required

    # Timing
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())

    # Outcome tracking (filled in later)
    outcome: Optional[str] = None
    outcome_recorded_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionRecord":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CouncilRecommendation:
    """
    Recommendation from a council advisor.

    Used by council_manager to collect and synthesize advisor input.
    """
    advisor_id: str = ""
    advisor_name: str = ""

    recommendation: str = ""
    confidence: float = 0.0

    reasoning: str = ""
    supporting_evidence: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)

    created_at: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BoardVote:
    """
    Vote from a board member on a decision.

    Used by decision_board for collective decision-making.
    """
    voter_id: str = ""
    voter_name: str = ""

    vote: str = ""  # "approve", "reject", "abstain"
    weight: float = 1.0  # Voting weight

    rationale: str = ""
    conditions: List[str] = field(default_factory=list)  # Conditions for approval

    created_at: str = field(default_factory=lambda: _utc_now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


def create_request(
    requester: str,
    target_agent: str,
    objective: str,
    business_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    constraints: Optional[Dict[str, Any]] = None,
    priority: str = "medium",
    parent_request_id: Optional[str] = None
) -> AgentRequest:
    """
    Factory function to create a standard agent request.

    Args:
        requester: Agent or layer making the request
        target_agent: Agent or layer to handle the request
        objective: What needs to be accomplished
        business_id: Optional business context
        context: Additional context dictionary
        constraints: Constraints on execution
        priority: Request priority
        parent_request_id: Parent request for tracking chains

    Returns:
        AgentRequest instance
    """
    return AgentRequest(
        requester=requester,
        target_agent=target_agent,
        objective=objective,
        business_id=business_id,
        context=context or {},
        constraints=constraints or {},
        priority=priority,
        parent_request_id=parent_request_id
    )


def create_response(
    request_id: str,
    responder: str,
    status: RequestStatus,
    result: Optional[Dict[str, Any]] = None,
    confidence: float = 0.0,
    rationale: str = "",
    errors: Optional[List[str]] = None
) -> AgentResponse:
    """
    Factory function to create a standard agent response.

    Args:
        request_id: ID of the request being responded to
        responder: Agent that produced this response
        status: Response status
        result: Result dictionary
        confidence: Confidence level 0.0-1.0
        rationale: Explanation of the result
        errors: List of error messages if any

    Returns:
        AgentResponse instance
    """
    return AgentResponse(
        request_id=request_id,
        responder=responder,
        status=status,
        result=result or {},
        confidence=confidence,
        rationale=rationale,
        errors=errors or []
    )
