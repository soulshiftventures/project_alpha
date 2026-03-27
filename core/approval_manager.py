"""
Approval Manager for Project Alpha
Policy-based classification and approval routing
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from core.agent_contracts import AgentRequest, AgentResponse, RequestStatus, AgentLayer


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ApprovalClass(Enum):
    """Classification of actions for approval routing."""
    AUTO_ALLOWED = "auto_allowed"  # No approval needed
    REQUIRES_APPROVAL = "requires_approval"  # Needs explicit approval
    BLOCKED = "blocked"  # Not allowed under current policy


class ApprovalStatus(Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"


@dataclass
class ApprovalPolicy:
    """
    A single approval policy rule.

    Policies are evaluated in order; first match wins.
    """
    policy_id: str
    name: str
    description: str

    # Matching criteria
    action_patterns: List[str] = field(default_factory=list)  # e.g., ["create_*", "delete_*"]
    agent_patterns: List[str] = field(default_factory=list)  # e.g., ["dept_*"]
    layer_filter: Optional[List[str]] = None  # e.g., ["c_suite", "department"]
    stage_filter: Optional[List[str]] = None  # e.g., ["BUILDING", "SCALING"]
    priority_filter: Optional[List[str]] = None  # e.g., ["critical", "high"]

    # Classification
    classification: ApprovalClass = ApprovalClass.AUTO_ALLOWED

    # If requires approval, who can approve
    approvers: List[str] = field(default_factory=list)  # agent_ids or "principal"

    # Conditions
    requires_rationale: bool = False
    max_confidence_for_auto: float = 0.0  # Auto-approve if confidence > this
    min_confidence_required: float = 0.0  # Block if confidence < this

    # Priority (higher = checked first)
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["classification"] = self.classification.value
        return data


@dataclass
class ApprovalRecord:
    """Record of an approval decision."""
    record_id: str = field(default_factory=lambda: f"apr_{_utc_now().strftime('%Y%m%d%H%M%S%f')}")
    request_id: str = ""
    policy_id: str = ""

    # Classification result
    classification: ApprovalClass = ApprovalClass.AUTO_ALLOWED
    status: ApprovalStatus = ApprovalStatus.PENDING

    # Decision details
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    rationale: str = ""

    # Request context
    action: str = ""
    requester: str = ""
    target_agent: str = ""

    # Enhanced context for UI display
    request_type: str = ""  # Type of request (skill, connector, job, etc.)
    description: str = ""   # Human-readable description
    priority: str = "medium"  # Request priority
    reason: str = ""  # Why approval is needed
    context: Dict[str, Any] = field(default_factory=dict)  # Additional safe context

    # Related entity IDs
    plan_id: Optional[str] = None
    job_id: Optional[str] = None
    connector_name: Optional[str] = None
    operation: Optional[str] = None

    # Risk classification
    risk_level: str = "medium"

    # Timing
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())
    expires_at: Optional[str] = None
    resolved_at: Optional[str] = None

    # For compatibility with UI
    approved: Optional[bool] = None
    approved_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["classification"] = self.classification.value
        data["status"] = self.status.value
        return data


class ApprovalManager:
    """
    Manages approval policies and routing.

    Provides:
    - Policy-based classification of actions
    - Approval request tracking
    - Auto-approval based on confidence thresholds
    - Approval status querying
    """

    def __init__(self):
        """Initialize the approval manager."""
        self._policies: List[ApprovalPolicy] = []
        self._pending_approvals: Dict[str, ApprovalRecord] = {}
        self._approval_history: List[ApprovalRecord] = []

        # Load default policies
        self._load_default_policies()

    def _load_default_policies(self) -> None:
        """Load default approval policies."""
        # Policy: Principal actions are always auto-allowed
        self._policies.append(ApprovalPolicy(
            policy_id="pol_principal_auto",
            name="Principal Auto-Allow",
            description="Actions from principal are auto-allowed",
            agent_patterns=["principal"],
            classification=ApprovalClass.AUTO_ALLOWED,
            priority=100
        ))

        # Policy: Critical priority requires approval
        self._policies.append(ApprovalPolicy(
            policy_id="pol_critical_approval",
            name="Critical Priority Approval",
            description="Critical priority actions require board approval",
            priority_filter=["critical"],
            classification=ApprovalClass.REQUIRES_APPROVAL,
            approvers=["decision_board", "principal"],
            requires_rationale=True,
            priority=90
        ))

        # Policy: Termination actions require approval
        self._policies.append(ApprovalPolicy(
            policy_id="pol_termination_approval",
            name="Termination Approval",
            description="Termination actions require C-suite approval",
            action_patterns=["terminate_*", "shutdown_*", "delete_*"],
            classification=ApprovalClass.REQUIRES_APPROVAL,
            approvers=["ceo", "coo", "principal"],
            requires_rationale=True,
            priority=80
        ))

        # Policy: High-confidence executive actions are auto-allowed
        self._policies.append(ApprovalPolicy(
            policy_id="pol_executive_high_conf",
            name="Executive High Confidence",
            description="Executive actions with high confidence auto-allowed",
            layer_filter=["executive", "c_suite"],
            classification=ApprovalClass.AUTO_ALLOWED,
            max_confidence_for_auto=0.8,
            priority=70
        ))

        # Policy: Department routine actions auto-allowed
        self._policies.append(ApprovalPolicy(
            policy_id="pol_dept_routine",
            name="Department Routine",
            description="Routine department actions auto-allowed",
            layer_filter=["department"],
            action_patterns=["execute_*", "process_*", "analyze_*"],
            classification=ApprovalClass.AUTO_ALLOWED,
            priority=60
        ))

        # Policy: Strategic changes require board approval
        self._policies.append(ApprovalPolicy(
            policy_id="pol_strategic_approval",
            name="Strategic Changes",
            description="Strategic changes require board approval",
            action_patterns=["change_strategy_*", "pivot_*", "major_*"],
            classification=ApprovalClass.REQUIRES_APPROVAL,
            approvers=["decision_board"],
            requires_rationale=True,
            priority=50
        ))

        # Policy: Default auto-allow for unmatched (low priority)
        self._policies.append(ApprovalPolicy(
            policy_id="pol_default_auto",
            name="Default Auto-Allow",
            description="Default policy for unmatched actions",
            classification=ApprovalClass.AUTO_ALLOWED,
            priority=0
        ))

        # Sort policies by priority (highest first)
        self._policies.sort(key=lambda p: p.priority, reverse=True)

    def add_policy(self, policy: ApprovalPolicy) -> None:
        """
        Add a new approval policy.

        Args:
            policy: ApprovalPolicy to add
        """
        self._policies.append(policy)
        self._policies.sort(key=lambda p: p.priority, reverse=True)

    def remove_policy(self, policy_id: str) -> bool:
        """
        Remove a policy by ID.

        Args:
            policy_id: ID of policy to remove

        Returns:
            True if removed, False if not found
        """
        for i, policy in enumerate(self._policies):
            if policy.policy_id == policy_id:
                del self._policies[i]
                return True
        return False

    def classify(
        self,
        request: AgentRequest,
        action: str,
        confidence: float = 0.0,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[ApprovalClass, ApprovalPolicy]:
        """
        Classify an action according to policies.

        Args:
            request: The agent request
            action: Action being performed
            confidence: Confidence level of the action
            context: Additional context

        Returns:
            Tuple of (ApprovalClass, matching ApprovalPolicy)
        """
        context = context or {}

        for policy in self._policies:
            if self._matches_policy(request, action, confidence, policy, context):
                # Check confidence-based auto-approval
                if (policy.classification == ApprovalClass.REQUIRES_APPROVAL and
                    policy.max_confidence_for_auto > 0 and
                    confidence >= policy.max_confidence_for_auto):
                    # High confidence overrides approval requirement
                    return ApprovalClass.AUTO_ALLOWED, policy

                # Check minimum confidence
                if (policy.min_confidence_required > 0 and
                    confidence < policy.min_confidence_required):
                    # Low confidence blocks the action
                    return ApprovalClass.BLOCKED, policy

                return policy.classification, policy

        # Should never reach here due to default policy
        return ApprovalClass.AUTO_ALLOWED, self._policies[-1]

    def _matches_policy(
        self,
        request: AgentRequest,
        action: str,
        confidence: float,
        policy: ApprovalPolicy,
        context: Dict[str, Any]
    ) -> bool:
        """Check if a request matches a policy."""
        # Check action patterns
        if policy.action_patterns:
            if not self._matches_patterns(action, policy.action_patterns):
                return False

        # Check agent patterns
        if policy.agent_patterns:
            if not self._matches_patterns(request.requester, policy.agent_patterns):
                return False

        # Check layer filter
        if policy.layer_filter:
            layer = context.get("layer", "")
            if layer not in policy.layer_filter:
                return False

        # Check stage filter
        if policy.stage_filter:
            stage = context.get("stage", "")
            if stage not in policy.stage_filter:
                return False

        # Check priority filter
        if policy.priority_filter:
            if request.priority not in policy.priority_filter:
                return False

        return True

    def _matches_patterns(self, value: str, patterns: List[str]) -> bool:
        """Check if a value matches any pattern (supports * wildcard)."""
        for pattern in patterns:
            if pattern == "*":
                return True
            if pattern.endswith("*"):
                if value.startswith(pattern[:-1]):
                    return True
            elif pattern.startswith("*"):
                if value.endswith(pattern[1:]):
                    return True
            elif pattern == value:
                return True
        return False

    def request_approval(
        self,
        request: AgentRequest,
        action: str,
        policy: ApprovalPolicy,
        rationale: str = ""
    ) -> ApprovalRecord:
        """
        Create an approval request.

        Args:
            request: The original agent request
            action: Action requiring approval
            policy: Policy that triggered approval requirement
            rationale: Reason for the action

        Returns:
            ApprovalRecord tracking the request
        """
        record = ApprovalRecord(
            request_id=request.request_id,
            policy_id=policy.policy_id,
            classification=ApprovalClass.REQUIRES_APPROVAL,
            status=ApprovalStatus.PENDING,
            action=action,
            requester=request.requester,
            target_agent=request.target_agent,
            rationale=rationale
        )

        self._pending_approvals[record.record_id] = record
        return record

    def approve(
        self,
        record_id: str,
        approver: str,
        rationale: str = ""
    ) -> Optional[ApprovalRecord]:
        """
        Approve a pending request.

        Args:
            record_id: ID of approval record
            approver: Agent/principal approving
            rationale: Reason for approval

        Returns:
            Updated ApprovalRecord or None if not found
        """
        if record_id not in self._pending_approvals:
            return None

        record = self._pending_approvals[record_id]
        record.status = ApprovalStatus.APPROVED
        record.decided_by = approver
        record.decided_at = _utc_now().isoformat()
        record.resolved_at = record.decided_at
        record.approved = True
        record.approved_by = approver
        if rationale:
            record.rationale = rationale

        # Move to history
        self._approval_history.append(record)
        del self._pending_approvals[record_id]

        return record

    def deny(
        self,
        record_id: str,
        denier: str,
        rationale: str = ""
    ) -> Optional[ApprovalRecord]:
        """
        Deny a pending request.

        Args:
            record_id: ID of approval record
            denier: Agent/principal denying
            rationale: Reason for denial

        Returns:
            Updated ApprovalRecord or None if not found
        """
        if record_id not in self._pending_approvals:
            return None

        record = self._pending_approvals[record_id]
        record.status = ApprovalStatus.DENIED
        record.decided_by = denier
        record.decided_at = _utc_now().isoformat()
        record.resolved_at = record.decided_at
        record.approved = False
        record.approved_by = denier
        if rationale:
            record.rationale = rationale

        # Move to history
        self._approval_history.append(record)
        del self._pending_approvals[record_id]

        return record

    def auto_approve(
        self,
        request: AgentRequest,
        action: str,
        policy: ApprovalPolicy
    ) -> ApprovalRecord:
        """
        Create an auto-approval record.

        Args:
            request: The agent request
            action: Action being auto-approved
            policy: Policy that allowed auto-approval

        Returns:
            ApprovalRecord with auto-approved status
        """
        record = ApprovalRecord(
            request_id=request.request_id,
            policy_id=policy.policy_id,
            classification=ApprovalClass.AUTO_ALLOWED,
            status=ApprovalStatus.AUTO_APPROVED,
            decided_by="system",
            decided_at=_utc_now().isoformat(),
            action=action,
            requester=request.requester,
            target_agent=request.target_agent,
            rationale=f"Auto-approved by policy: {policy.name}"
        )

        self._approval_history.append(record)
        return record

    def get_pending(self) -> List[ApprovalRecord]:
        """Get all pending approval requests."""
        return list(self._pending_approvals.values())

    def get_pending_for_approver(self, approver: str) -> List[ApprovalRecord]:
        """Get pending approvals that a specific agent can approve."""
        results = []
        for record in self._pending_approvals.values():
            policy = self._get_policy(record.policy_id)
            if policy and (approver in policy.approvers or approver == "principal"):
                results.append(record)
        return results

    def _get_policy(self, policy_id: str) -> Optional[ApprovalPolicy]:
        """Get a policy by ID."""
        for policy in self._policies:
            if policy.policy_id == policy_id:
                return policy
        return None

    def get_history(
        self,
        request_id: Optional[str] = None,
        status: Optional[ApprovalStatus] = None,
        limit: int = 100
    ) -> List[ApprovalRecord]:
        """
        Get approval history with filters.

        Args:
            request_id: Filter by request ID
            status: Filter by status
            limit: Maximum records to return

        Returns:
            List of matching approval records
        """
        results = self._approval_history

        if request_id is not None:
            results = [r for r in results if r.request_id == request_id]

        if status is not None:
            results = [r for r in results if r.status == status]

        return results[-limit:]

    def list_policies(self) -> List[ApprovalPolicy]:
        """Get all registered policies."""
        return self._policies.copy()

    def check_and_process(
        self,
        request: AgentRequest,
        action: str,
        confidence: float = 0.0,
        context: Optional[Dict[str, Any]] = None,
        rationale: str = ""
    ) -> tuple[ApprovalClass, Optional[ApprovalRecord]]:
        """
        Convenience method to classify and process an action.

        Returns:
            Tuple of (classification, approval_record if created)
        """
        classification, policy = self.classify(request, action, confidence, context)

        if classification == ApprovalClass.AUTO_ALLOWED:
            record = self.auto_approve(request, action, policy)
            return classification, record
        elif classification == ApprovalClass.REQUIRES_APPROVAL:
            record = self.request_approval(request, action, policy, rationale)
            return classification, record
        else:  # BLOCKED
            record = ApprovalRecord(
                request_id=request.request_id,
                policy_id=policy.policy_id,
                classification=ApprovalClass.BLOCKED,
                status=ApprovalStatus.DENIED,
                decided_by="system",
                decided_at=_utc_now().isoformat(),
                action=action,
                requester=request.requester,
                target_agent=request.target_agent,
                rationale=f"Blocked by policy: {policy.name}"
            )
            self._approval_history.append(record)
            return classification, record
