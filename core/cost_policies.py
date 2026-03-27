"""
Cost Policies for Project Alpha.

Provides cost-based policy decisions that integrate with the approval workflow.

ARCHITECTURE:
- CostPolicy: Defines rules for cost-based decisions
- Integrates with BudgetManager for budget checks
- Returns policy outcomes compatible with approval system
- Extends existing policy framework with cost awareness

POLICY OUTCOMES:
- auto_allowed: Cost is acceptable, proceed
- requires_approval: Cost needs human approval
- blocked: Cost exceeds policy limits
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from .cost_model import CostEstimate, CostClass, CostConfidence
from .budget_manager import (
    BudgetManager,
    BudgetCheckResult,
    BudgetPolicyOutcome,
    BudgetScope,
    get_budget_manager,
)

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class CostPolicyOutcome(Enum):
    """Outcome of a cost policy evaluation."""
    AUTO_ALLOWED = "auto_allowed"
    REQUIRES_APPROVAL = "requires_approval"
    BLOCKED = "blocked"
    WARNING = "warning"


@dataclass
class CostPolicyRule:
    """
    A single cost policy rule with domain-aware matching.

    Rules are evaluated in priority order; first match wins.
    Supports domain-based filtering for domain-neutral operations.
    """
    rule_id: str
    name: str
    description: str

    # Matching criteria
    connector_patterns: List[str] = field(default_factory=list)  # ["sendgrid", "hubspot"]
    operation_patterns: List[str] = field(default_factory=list)  # ["send_*", "create_*"]
    cost_class_filter: List[CostClass] = field(default_factory=list)  # [HIGH, VERY_HIGH]
    domain_filter: List[str] = field(default_factory=list)  # ["growth", "finance"] - empty = all domains

    # Thresholds (in USD)
    min_cost_threshold: float = 0.0  # Rule applies if cost >= this
    max_cost_threshold: float = float("inf")  # Rule applies if cost <= this

    # Outcome
    outcome: CostPolicyOutcome = CostPolicyOutcome.AUTO_ALLOWED

    # Additional conditions
    check_budget: bool = True  # Also check budget constraints
    require_confidence: Optional[CostConfidence] = None  # Minimum confidence required

    # Priority (higher = checked first)
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "connector_patterns": self.connector_patterns,
            "operation_patterns": self.operation_patterns,
            "cost_class_filter": [c.value for c in self.cost_class_filter],
            "domain_filter": self.domain_filter,
            "min_cost_threshold": self.min_cost_threshold,
            "max_cost_threshold": self.max_cost_threshold,
            "outcome": self.outcome.value,
            "check_budget": self.check_budget,
            "priority": self.priority,
        }


@dataclass
class CostPolicyResult:
    """Result of a cost policy evaluation."""
    allowed: bool
    outcome: CostPolicyOutcome
    reason: str
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    projected_cost: float = 0.0
    cost_class: Optional[CostClass] = None
    budget_check: Optional[BudgetCheckResult] = None
    warnings: List[str] = field(default_factory=list)
    requires_approval: bool = False
    approval_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "projected_cost": self.projected_cost,
            "cost_class": self.cost_class.value if self.cost_class else None,
            "budget_check": self.budget_check.to_dict() if self.budget_check else None,
            "warnings": self.warnings,
            "requires_approval": self.requires_approval,
            "approval_reason": self.approval_reason,
        }


class CostPolicyEngine:
    """
    Engine for evaluating cost policies.

    Provides cost-based policy decisions for the approval workflow.
    """

    def __init__(self, budget_manager: Optional[BudgetManager] = None):
        """Initialize the cost policy engine."""
        self._budget_manager = budget_manager
        self._rules: List[CostPolicyRule] = []
        self._initialized = False

        # Load default rules
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default cost policy rules."""
        # Rule: Very high cost operations require approval
        self._rules.append(CostPolicyRule(
            rule_id="cost_very_high",
            name="Very High Cost Approval",
            description="Operations with very high cost require approval",
            cost_class_filter=[CostClass.VERY_HIGH],
            outcome=CostPolicyOutcome.REQUIRES_APPROVAL,
            priority=100,
        ))

        # Rule: High cost external operations require approval
        self._rules.append(CostPolicyRule(
            rule_id="cost_high_external",
            name="High Cost External Approval",
            description="High cost external operations require approval",
            connector_patterns=["apollo", "hubspot"],
            cost_class_filter=[CostClass.HIGH],
            outcome=CostPolicyOutcome.REQUIRES_APPROVAL,
            priority=90,
        ))

        # Rule: Email sends over threshold require approval
        self._rules.append(CostPolicyRule(
            rule_id="cost_email_threshold",
            name="Email Cost Threshold",
            description="Email operations over $1 require approval",
            connector_patterns=["sendgrid", "instantly", "smartlead"],
            min_cost_threshold=1.0,
            outcome=CostPolicyOutcome.REQUIRES_APPROVAL,
            priority=80,
        ))

        # Rule: Unknown cost operations get warning
        self._rules.append(CostPolicyRule(
            rule_id="cost_unknown",
            name="Unknown Cost Warning",
            description="Operations with unknown cost get warning",
            cost_class_filter=[CostClass.UNKNOWN],
            outcome=CostPolicyOutcome.WARNING,
            priority=70,
        ))

        # Rule: Free operations are always allowed
        self._rules.append(CostPolicyRule(
            rule_id="cost_free",
            name="Free Operations Auto-Allow",
            description="Free operations are always allowed",
            cost_class_filter=[CostClass.FREE],
            outcome=CostPolicyOutcome.AUTO_ALLOWED,
            check_budget=False,  # No need to check budget for free ops
            priority=60,
        ))

        # Rule: Default auto-allow for low/medium cost
        self._rules.append(CostPolicyRule(
            rule_id="cost_default",
            name="Default Cost Policy",
            description="Default policy for standard cost operations",
            outcome=CostPolicyOutcome.AUTO_ALLOWED,
            priority=0,
        ))

        # Sort by priority
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        self._initialized = True

    def _ensure_initialized(self) -> None:
        """Ensure manager is available."""
        if self._budget_manager is None:
            self._budget_manager = get_budget_manager()
            if not self._budget_manager._initialized:
                self._budget_manager.initialize()

    def _matches_rule(
        self,
        rule: CostPolicyRule,
        connector: Optional[str],
        operation: Optional[str],
        estimate: CostEstimate,
    ) -> bool:
        """Check if an operation matches a rule."""
        # Check connector patterns
        if rule.connector_patterns:
            if not connector or connector not in rule.connector_patterns:
                # Check for wildcard patterns
                matched = False
                for pattern in rule.connector_patterns:
                    if pattern.endswith("*") and connector and connector.startswith(pattern[:-1]):
                        matched = True
                        break
                if not matched:
                    return False

        # Check operation patterns
        if rule.operation_patterns:
            if not operation:
                return False
            matched = False
            for pattern in rule.operation_patterns:
                if pattern == operation:
                    matched = True
                    break
                if pattern.endswith("*") and operation.startswith(pattern[:-1]):
                    matched = True
                    break
                if pattern.startswith("*") and operation.endswith(pattern[1:]):
                    matched = True
                    break
            if not matched:
                return False

        # Check cost class filter
        if rule.cost_class_filter:
            if estimate.cost_class not in rule.cost_class_filter:
                return False

        # Check cost thresholds
        if estimate.amount < rule.min_cost_threshold:
            return False
        if estimate.amount > rule.max_cost_threshold:
            return False

        # Check confidence requirement
        if rule.require_confidence:
            conf_order = [
                CostConfidence.UNKNOWN, CostConfidence.LOW,
                CostConfidence.MEDIUM, CostConfidence.HIGH, CostConfidence.EXACT
            ]
            if conf_order.index(estimate.confidence) < conf_order.index(rule.require_confidence):
                return False

        return True

    def evaluate(
        self,
        estimate: CostEstimate,
        connector: Optional[str] = None,
        operation: Optional[str] = None,
        business_id: Optional[str] = None,
    ) -> CostPolicyResult:
        """
        Evaluate cost policies for an operation.

        Args:
            estimate: Cost estimate for the operation
            connector: Connector name if applicable
            operation: Operation name if applicable
            business_id: Business ID if applicable

        Returns:
            CostPolicyResult with policy decision
        """
        self._ensure_initialized()

        # Find matching rule
        matched_rule = None
        for rule in self._rules:
            if self._matches_rule(rule, connector, operation, estimate):
                matched_rule = rule
                break

        if not matched_rule:
            # Should not happen with default rule, but handle anyway
            return CostPolicyResult(
                allowed=True,
                outcome=CostPolicyOutcome.AUTO_ALLOWED,
                reason="No matching cost policy",
                projected_cost=estimate.amount,
                cost_class=estimate.cost_class,
            )

        # Determine outcome from rule
        allowed = True
        outcome = matched_rule.outcome
        reason = "Allowed by policy"
        requires_approval = False
        approval_reason = ""
        warnings: List[str] = []

        if matched_rule.outcome == CostPolicyOutcome.BLOCKED:
            allowed = False
            outcome = CostPolicyOutcome.BLOCKED
            reason = f"Blocked by policy: {matched_rule.name}"

        elif matched_rule.outcome == CostPolicyOutcome.REQUIRES_APPROVAL:
            allowed = False
            outcome = CostPolicyOutcome.REQUIRES_APPROVAL
            requires_approval = True
            reason = f"Requires approval: {matched_rule.description}"
            approval_reason = matched_rule.description

        elif matched_rule.outcome == CostPolicyOutcome.WARNING:
            allowed = True
            outcome = CostPolicyOutcome.WARNING
            reason = f"Warning: {matched_rule.description}"
            warnings.append(matched_rule.description)

        else:
            allowed = True
            outcome = CostPolicyOutcome.AUTO_ALLOWED
            reason = "Allowed by policy"

        result = CostPolicyResult(
            allowed=allowed,
            outcome=outcome,
            reason=reason,
            rule_id=matched_rule.rule_id,
            rule_name=matched_rule.name,
            projected_cost=estimate.amount,
            cost_class=estimate.cost_class,
            warnings=warnings,
            requires_approval=requires_approval,
            approval_reason=approval_reason,
        )

        # Return early for blocked rules
        if matched_rule.outcome == CostPolicyOutcome.BLOCKED:
            return result

        # Check budget if required
        if matched_rule.check_budget and result.allowed:
            budget_check = self._budget_manager.check_action_budget(
                projected_cost=estimate.amount,
                connector=connector,
                business_id=business_id,
            )

            result.budget_check = budget_check
            result.warnings.extend(budget_check.warnings)

            # Budget can override policy outcome
            if not budget_check.allowed:
                result.allowed = False
                if budget_check.outcome == BudgetPolicyOutcome.BLOCKED:
                    result.outcome = CostPolicyOutcome.BLOCKED
                    result.reason = budget_check.reason
                elif budget_check.outcome == BudgetPolicyOutcome.REQUIRES_APPROVAL:
                    result.outcome = CostPolicyOutcome.REQUIRES_APPROVAL
                    result.requires_approval = True
                    result.reason = budget_check.reason
                    result.approval_reason = budget_check.reason

        return result

    def evaluate_plan(
        self,
        plan_estimate: CostEstimate,
        steps: List[Dict[str, Any]],
        business_id: Optional[str] = None,
    ) -> CostPolicyResult:
        """
        Evaluate cost policies for an execution plan.

        Args:
            plan_estimate: Total cost estimate
            steps: Plan steps
            business_id: Business ID if applicable

        Returns:
            CostPolicyResult for the plan
        """
        self._ensure_initialized()

        # Evaluate overall plan cost
        result = self.evaluate(
            estimate=plan_estimate,
            connector=None,
            operation=None,
            business_id=business_id,
        )

        # Check job budget
        job_check = self._budget_manager.check_job_budget(
            projected_cost=plan_estimate.amount,
            business_id=business_id,
        )

        if result.budget_check is None:
            result.budget_check = job_check

        # Job budget can override
        if not job_check.allowed and result.allowed:
            result.allowed = False
            if job_check.outcome == BudgetPolicyOutcome.BLOCKED:
                result.outcome = CostPolicyOutcome.BLOCKED
                result.reason = job_check.reason
            elif job_check.outcome == BudgetPolicyOutcome.REQUIRES_APPROVAL:
                result.outcome = CostPolicyOutcome.REQUIRES_APPROVAL
                result.requires_approval = True
                result.reason = job_check.reason
                result.approval_reason = job_check.reason

        result.warnings.extend(job_check.warnings)

        return result

    # =========================================================================
    # Rule Management
    # =========================================================================

    def add_rule(self, rule: CostPolicyRule) -> None:
        """Add a new policy rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        for i, rule in enumerate(self._rules):
            if rule.rule_id == rule_id:
                del self._rules[i]
                return True
        return False

    def get_rules(self) -> List[CostPolicyRule]:
        """Get all policy rules."""
        return self._rules.copy()

    def get_rule(self, rule_id: str) -> Optional[CostPolicyRule]:
        """Get a specific rule by ID."""
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    # =========================================================================
    # Summary
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """Get policy engine summary."""
        return {
            "initialized": self._initialized,
            "rule_count": len(self._rules),
            "rules": [r.to_dict() for r in self._rules],
        }


# Singleton instance
_cost_policy_engine: Optional[CostPolicyEngine] = None


def get_cost_policy_engine() -> CostPolicyEngine:
    """Get the global cost policy engine."""
    global _cost_policy_engine
    if _cost_policy_engine is None:
        _cost_policy_engine = CostPolicyEngine()
    return _cost_policy_engine


# =============================================================================
# Convenience Functions
# =============================================================================

def check_operation_cost_policy(
    connector: str,
    operation: str,
    estimated_cost: float,
    business_id: Optional[str] = None,
) -> CostPolicyResult:
    """
    Check cost policy for an operation.

    Convenience function for quick policy checks.

    Args:
        connector: Connector name
        operation: Operation name
        estimated_cost: Estimated cost
        business_id: Business ID if applicable

    Returns:
        CostPolicyResult
    """
    engine = get_cost_policy_engine()
    estimate = CostEstimate.from_amount(estimated_cost)
    return engine.evaluate(
        estimate=estimate,
        connector=connector,
        operation=operation,
        business_id=business_id,
    )


def check_plan_cost_policy(
    plan_cost: float,
    steps: List[Dict[str, Any]],
    business_id: Optional[str] = None,
) -> CostPolicyResult:
    """
    Check cost policy for an execution plan.

    Args:
        plan_cost: Total estimated plan cost
        steps: Plan steps
        business_id: Business ID if applicable

    Returns:
        CostPolicyResult
    """
    engine = get_cost_policy_engine()
    estimate = CostEstimate.from_amount(plan_cost)
    return engine.evaluate_plan(
        plan_estimate=estimate,
        steps=steps,
        business_id=business_id,
    )
