"""
Integration Policies for Project Alpha.

Defines governance policies for integration usage,
including approval requirements, risk classification,
and operational constraints.

ARCHITECTURE:
- Policy-based control of integration operations
- Risk classification (low, medium, high, critical)
- Approval workflow integration
- Audit logging for policy decisions
"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging

from core.approval_manager import ApprovalClass


logger = logging.getLogger(__name__)


class IntegrationRiskLevel(Enum):
    """Risk levels for integration operations."""
    LOW = "low"           # Read-only operations, no cost
    MEDIUM = "medium"     # Write operations, low cost
    HIGH = "high"         # Bulk operations, significant cost
    CRITICAL = "critical"  # Irreversible operations, high impact


class OperationCategory(Enum):
    """Categories of operations."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    BULK = "bulk"
    EXTERNAL_NOTIFY = "external_notify"
    COST_INCURRING = "cost_incurring"


@dataclass
class OperationPolicy:
    """
    Policy rules for a specific operation.

    Defines approval requirements and constraints.
    """

    operation: str
    connector: str
    risk_level: IntegrationRiskLevel
    categories: Set[OperationCategory] = field(default_factory=set)
    requires_approval: bool = False
    approval_class: ApprovalClass = ApprovalClass.REQUIRES_APPROVAL
    dry_run_required_first: bool = False
    max_batch_size: Optional[int] = None
    daily_limit: Optional[int] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation,
            "connector": self.connector,
            "risk_level": self.risk_level.value,
            "categories": [c.value for c in self.categories],
            "requires_approval": self.requires_approval,
            "approval_class": self.approval_class.value,
            "dry_run_required_first": self.dry_run_required_first,
            "max_batch_size": self.max_batch_size,
            "daily_limit": self.daily_limit,
            "notes": self.notes,
        }


@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""

    allowed: bool
    requires_approval: bool = False
    approval_class: Optional[ApprovalClass] = None
    risk_level: IntegrationRiskLevel = IntegrationRiskLevel.LOW
    reason: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allowed": self.allowed,
            "requires_approval": self.requires_approval,
            "approval_class": self.approval_class.value if self.approval_class else None,
            "risk_level": self.risk_level.value,
            "reason": self.reason,
            "constraints": self.constraints,
            "timestamp": self.timestamp.isoformat(),
        }


class IntegrationPolicyEngine:
    """
    Policy engine for integration governance.

    Evaluates operations against policies and
    determines approval requirements.
    """

    def __init__(self):
        self._policies: Dict[str, OperationPolicy] = {}
        self._usage_counts: Dict[str, Dict[str, int]] = {}  # connector -> operation -> count
        self._decisions: List[PolicyDecision] = []
        self._load_default_policies()

    def _load_default_policies(self) -> None:
        """Load default operation policies."""
        default_policies = [
            # Research Operations - Generally low risk
            OperationPolicy(
                operation="search",
                connector="tavily",
                risk_level=IntegrationRiskLevel.LOW,
                categories={OperationCategory.READ, OperationCategory.COST_INCURRING},
                requires_approval=False,
                daily_limit=1000,
            ),
            OperationPolicy(
                operation="extract",
                connector="tavily",
                risk_level=IntegrationRiskLevel.LOW,
                categories={OperationCategory.READ, OperationCategory.COST_INCURRING},
                requires_approval=False,
                daily_limit=500,
            ),
            OperationPolicy(
                operation="scrape",
                connector="firecrawl",
                risk_level=IntegrationRiskLevel.LOW,
                categories={OperationCategory.READ, OperationCategory.COST_INCURRING},
                requires_approval=False,
                daily_limit=500,
            ),
            OperationPolicy(
                operation="crawl",
                connector="firecrawl",
                risk_level=IntegrationRiskLevel.MEDIUM,
                categories={OperationCategory.READ, OperationCategory.COST_INCURRING},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
                max_batch_size=100,
                daily_limit=200,
            ),

            # Lead Generation - Medium to high risk due to cost
            OperationPolicy(
                operation="search_people",
                connector="apollo",
                risk_level=IntegrationRiskLevel.MEDIUM,
                categories={OperationCategory.READ, OperationCategory.COST_INCURRING},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
                max_batch_size=100,
                daily_limit=500,
            ),
            OperationPolicy(
                operation="search_organizations",
                connector="apollo",
                risk_level=IntegrationRiskLevel.MEDIUM,
                categories={OperationCategory.READ, OperationCategory.COST_INCURRING},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
                max_batch_size=100,
                daily_limit=500,
            ),
            OperationPolicy(
                operation="enrich_person",
                connector="apollo",
                risk_level=IntegrationRiskLevel.MEDIUM,
                categories={OperationCategory.READ, OperationCategory.COST_INCURRING},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
                daily_limit=100,
            ),
            OperationPolicy(
                operation="google_maps_search",
                connector="outscraper",
                risk_level=IntegrationRiskLevel.MEDIUM,
                categories={OperationCategory.READ, OperationCategory.COST_INCURRING},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
                max_batch_size=50,
                daily_limit=200,
            ),

            # CRM Operations - Writes need approval
            OperationPolicy(
                operation="list_contacts",
                connector="hubspot",
                risk_level=IntegrationRiskLevel.LOW,
                categories={OperationCategory.READ},
                requires_approval=False,
                daily_limit=5000,
            ),
            OperationPolicy(
                operation="get_contact",
                connector="hubspot",
                risk_level=IntegrationRiskLevel.LOW,
                categories={OperationCategory.READ},
                requires_approval=False,
            ),
            OperationPolicy(
                operation="create_contact",
                connector="hubspot",
                risk_level=IntegrationRiskLevel.MEDIUM,
                categories={OperationCategory.WRITE},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
                dry_run_required_first=True,
            ),
            OperationPolicy(
                operation="update_contact",
                connector="hubspot",
                risk_level=IntegrationRiskLevel.MEDIUM,
                categories={OperationCategory.WRITE},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
            ),
            OperationPolicy(
                operation="create_deal",
                connector="hubspot",
                risk_level=IntegrationRiskLevel.HIGH,
                categories={OperationCategory.WRITE},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
                dry_run_required_first=True,
            ),
            OperationPolicy(
                operation="update_deal",
                connector="hubspot",
                risk_level=IntegrationRiskLevel.HIGH,
                categories={OperationCategory.WRITE},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
            ),

            # Messaging - External notifications need approval
            OperationPolicy(
                operation="send_message",
                connector="telegram",
                risk_level=IntegrationRiskLevel.MEDIUM,
                categories={OperationCategory.EXTERNAL_NOTIFY},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
                daily_limit=100,
            ),
            OperationPolicy(
                operation="send_document",
                connector="telegram",
                risk_level=IntegrationRiskLevel.MEDIUM,
                categories={OperationCategory.EXTERNAL_NOTIFY},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
                daily_limit=50,
            ),
            OperationPolicy(
                operation="send_email",
                connector="sendgrid",
                risk_level=IntegrationRiskLevel.HIGH,
                categories={OperationCategory.EXTERNAL_NOTIFY, OperationCategory.COST_INCURRING},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
                daily_limit=50,
            ),
            OperationPolicy(
                operation="send_template",
                connector="sendgrid",
                risk_level=IntegrationRiskLevel.HIGH,
                categories={OperationCategory.EXTERNAL_NOTIFY, OperationCategory.COST_INCURRING},
                requires_approval=True,
                approval_class=ApprovalClass.REQUIRES_APPROVAL,
                daily_limit=50,
            ),
        ]

        for policy in default_policies:
            key = f"{policy.connector}:{policy.operation}"
            self._policies[key] = policy

    def register_policy(self, policy: OperationPolicy) -> None:
        """Register or update an operation policy."""
        key = f"{policy.connector}:{policy.operation}"
        self._policies[key] = policy

    def get_policy(
        self,
        connector: str,
        operation: str,
    ) -> Optional[OperationPolicy]:
        """Get policy for a connector operation."""
        key = f"{connector}:{operation}"
        return self._policies.get(key)

    def evaluate(
        self,
        connector: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        """
        Evaluate an operation against policies.

        Args:
            connector: Connector name
            operation: Operation name
            params: Operation parameters
            context: Additional context

        Returns:
            PolicyDecision with evaluation result
        """
        policy = self.get_policy(connector, operation)

        # No policy = default allow with warning
        if not policy:
            decision = PolicyDecision(
                allowed=True,
                risk_level=IntegrationRiskLevel.LOW,
                reason="No policy defined - default allow",
            )
            self._decisions.append(decision)
            return decision

        # Check daily limit
        if policy.daily_limit:
            today_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            usage_key = f"{connector}:{operation}:{today_key}"
            current_count = self._usage_counts.get(connector, {}).get(operation, 0)

            if current_count >= policy.daily_limit:
                decision = PolicyDecision(
                    allowed=False,
                    risk_level=policy.risk_level,
                    reason=f"Daily limit exceeded ({current_count}/{policy.daily_limit})",
                )
                self._decisions.append(decision)
                return decision

        # Check batch size
        constraints = {}
        if policy.max_batch_size and params:
            batch_params = ["limit", "per_page", "batch_size"]
            for param in batch_params:
                if param in params:
                    requested = params[param]
                    if requested > policy.max_batch_size:
                        constraints["max_batch_size"] = policy.max_batch_size
                        constraints["adjusted_from"] = requested

        # Build decision
        decision = PolicyDecision(
            allowed=True,
            requires_approval=policy.requires_approval,
            approval_class=policy.approval_class if policy.requires_approval else None,
            risk_level=policy.risk_level,
            reason=f"Policy: {policy.connector}:{policy.operation}",
            constraints=constraints,
        )

        if policy.dry_run_required_first:
            decision.constraints["dry_run_required_first"] = True

        self._decisions.append(decision)
        return decision

    def record_usage(self, connector: str, operation: str) -> None:
        """Record an operation usage for limit tracking."""
        if connector not in self._usage_counts:
            self._usage_counts[connector] = {}
        if operation not in self._usage_counts[connector]:
            self._usage_counts[connector][operation] = 0
        self._usage_counts[connector][operation] += 1

    def get_usage(self, connector: str, operation: str) -> int:
        """Get current usage count for an operation."""
        return self._usage_counts.get(connector, {}).get(operation, 0)

    def reset_daily_usage(self) -> None:
        """Reset all usage counts (call at midnight)."""
        self._usage_counts = {}

    def get_policies_for_connector(
        self, connector: str
    ) -> List[OperationPolicy]:
        """Get all policies for a connector."""
        return [
            policy for key, policy in self._policies.items()
            if policy.connector == connector
        ]

    def get_high_risk_operations(self) -> List[OperationPolicy]:
        """Get all high/critical risk operations."""
        return [
            policy for policy in self._policies.values()
            if policy.risk_level in (IntegrationRiskLevel.HIGH, IntegrationRiskLevel.CRITICAL)
        ]

    def get_operations_requiring_approval(self) -> List[OperationPolicy]:
        """Get all operations requiring approval."""
        return [
            policy for policy in self._policies.values()
            if policy.requires_approval
        ]

    def get_recent_decisions(self, limit: int = 100) -> List[PolicyDecision]:
        """Get recent policy decisions."""
        return self._decisions[-limit:]

    def get_summary(self) -> Dict[str, Any]:
        """Get policy engine summary."""
        by_risk = {level.value: 0 for level in IntegrationRiskLevel}
        by_connector = {}

        for policy in self._policies.values():
            by_risk[policy.risk_level.value] += 1
            if policy.connector not in by_connector:
                by_connector[policy.connector] = 0
            by_connector[policy.connector] += 1

        return {
            "total_policies": len(self._policies),
            "requiring_approval": len(self.get_operations_requiring_approval()),
            "high_risk": len(self.get_high_risk_operations()),
            "by_risk_level": by_risk,
            "by_connector": by_connector,
            "total_decisions": len(self._decisions),
        }


# Singleton instance
_integration_policy_engine: Optional[IntegrationPolicyEngine] = None


def get_integration_policy_engine() -> IntegrationPolicyEngine:
    """Get the global integration policy engine."""
    global _integration_policy_engine
    if _integration_policy_engine is None:
        _integration_policy_engine = IntegrationPolicyEngine()
    return _integration_policy_engine
