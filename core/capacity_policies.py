"""
Capacity Policies for Project Alpha
Policy-driven capacity evaluation and enforcement.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from core.capacity_manager import CapacityCheckContext, CapacityDimension, CapacityDecision


class CapacityPolicyPriority(Enum):
    """Policy evaluation priority."""
    CRITICAL = 100
    HIGH = 75
    MEDIUM = 50
    LOW = 25


@dataclass
class CapacityPolicyRule:
    """
    A capacity policy rule.

    Rules are evaluated in priority order to determine capacity decisions.
    """
    rule_id: str
    name: str
    priority: CapacityPolicyPriority
    dimension_filter: Optional[CapacityDimension] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    outcome: CapacityDecision = CapacityDecision.ALLOWED
    reason: str = ""
    recommendations: List[str] = field(default_factory=list)
    enabled: bool = True


class CapacityPolicies:
    """
    Manages capacity policy rules and evaluation.

    Provides policy-driven capacity enforcement with:
    - Priority-based rule evaluation
    - Dimension-specific policies
    - Cost-aware policies
    - Domain-aware policies
    - Runtime-aware policies
    """

    def __init__(self):
        """Initialize capacity policies."""
        self.rules: List[CapacityPolicyRule] = []
        self._init_default_rules()

    def _init_default_rules(self):
        """Initialize default capacity policy rules."""

        # Rule 1: Block extremely high-cost operations
        self.add_rule(CapacityPolicyRule(
            rule_id="high_cost_block",
            name="Block Very High Cost Operations",
            priority=CapacityPolicyPriority.CRITICAL,
            conditions={"min_cost": 100.0},
            outcome=CapacityDecision.BLOCKED,
            reason="Operation cost too high (>$100)",
            recommendations=[
                "Review operation cost estimate",
                "Consider breaking into smaller operations",
                "Request operator approval if necessary"
            ]
        ))

        # Rule 2: Require approval for high-cost operations
        self.add_rule(CapacityPolicyRule(
            rule_id="high_cost_approval",
            name="Require Approval for High Cost",
            priority=CapacityPolicyPriority.HIGH,
            conditions={"min_cost": 10.0},
            outcome=CapacityDecision.REQUIRES_APPROVAL,
            reason="High-cost operation requires approval (>$10)",
            recommendations=["Review cost estimate before proceeding"]
        ))

        # Rule 3: Warn on many concurrent businesses
        self.add_rule(CapacityPolicyRule(
            rule_id="business_capacity_warning",
            name="Warn on High Business Count",
            priority=CapacityPolicyPriority.MEDIUM,
            dimension_filter=CapacityDimension.BUSINESSES,
            conditions={"min_count": 8},
            outcome=CapacityDecision.WARNING,
            reason="High number of concurrent businesses (>8)",
            recommendations=[
                "Consider terminating low-priority businesses",
                "Review portfolio health and performance"
            ]
        ))

        # Rule 4: Warn on many concurrent jobs
        self.add_rule(CapacityPolicyRule(
            rule_id="job_capacity_warning",
            name="Warn on High Job Count",
            priority=CapacityPolicyPriority.MEDIUM,
            dimension_filter=CapacityDimension.JOBS,
            conditions={"min_count": 20},
            outcome=CapacityDecision.WARNING,
            reason="High number of concurrent jobs (>20)",
            recommendations=[
                "Wait for jobs to complete",
                "Consider runtime backend capacity"
            ]
        ))

        # Rule 5: Note - runtime checking disabled by default
        # Would block operations requiring unavailable runtimes in production
        # Commented out for now as runtime availability check is simplified
        # self.add_rule(CapacityPolicyRule(
        #     rule_id="runtime_unavailable",
        #     name="Block Unavailable Runtime",
        #     priority=CapacityPolicyPriority.HIGH,
        #     conditions={"runtime_available": False},
        #     outcome=CapacityDecision.BLOCKED,
        #     reason="Required runtime backend unavailable",
        #     recommendations=[
        #         "Wait for runtime to become available",
        #         "Use alternative runtime backend"
        #     ]
        # ))

    def add_rule(self, rule: CapacityPolicyRule):
        """
        Add a capacity policy rule.

        Args:
            rule: Policy rule to add
        """
        self.rules.append(rule)
        # Keep rules sorted by priority (highest first)
        self.rules.sort(key=lambda r: r.priority.value, reverse=True)

    def remove_rule(self, rule_id: str):
        """
        Remove a capacity policy rule.

        Args:
            rule_id: Rule ID to remove
        """
        self.rules = [r for r in self.rules if r.rule_id != rule_id]

    def get_rule(self, rule_id: str) -> Optional[CapacityPolicyRule]:
        """Get a rule by ID."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def evaluate_capacity(self, context: CapacityCheckContext) -> Dict[str, Any]:
        """
        Evaluate capacity policies for a given context.

        Args:
            context: Capacity check context

        Returns:
            Policy evaluation result with decision and recommendations
        """
        result = {
            "requires_approval": False,
            "blocked": False,
            "warnings": [],
            "recommendations": [],
            "reason": "",
            "matched_rules": []
        }

        # Evaluate rules in priority order
        for rule in self.rules:
            if not rule.enabled:
                continue

            # Check if rule applies to this dimension
            if rule.dimension_filter and rule.dimension_filter != context.dimension:
                continue

            # Check if rule conditions match
            if self._check_conditions(rule, context):
                result["matched_rules"].append(rule.rule_id)

                # Apply rule outcome
                if rule.outcome == CapacityDecision.BLOCKED:
                    result["blocked"] = True
                    result["reason"] = rule.reason
                    result["recommendations"].extend(rule.recommendations)
                    # Blocking rule stops evaluation
                    break
                elif rule.outcome == CapacityDecision.REQUIRES_APPROVAL:
                    result["requires_approval"] = True
                    result["reason"] = rule.reason
                    result["recommendations"].extend(rule.recommendations)
                    # Continue to check for blocking rules
                elif rule.outcome == CapacityDecision.WARNING:
                    result["warnings"].append(rule.reason)
                    result["recommendations"].extend(rule.recommendations)
                    # Continue evaluation

        return result

    def _check_conditions(self, rule: CapacityPolicyRule, context: CapacityCheckContext) -> bool:
        """
        Check if rule conditions match the context.

        Args:
            rule: Policy rule
            context: Capacity check context

        Returns:
            True if conditions match, False otherwise
        """
        conditions = rule.conditions

        # Check cost conditions
        if "min_cost" in conditions:
            if context.estimated_cost < conditions["min_cost"]:
                return False

        if "max_cost" in conditions:
            if context.estimated_cost > conditions["max_cost"]:
                return False

        # Check count conditions
        if "min_count" in conditions:
            if context.current_count < conditions["min_count"]:
                return False

        if "max_count" in conditions:
            if context.current_count > conditions["max_count"]:
                return False

        # Check runtime conditions
        if "runtime_available" in conditions:
            # Would check actual runtime availability
            # For now, simplified check
            if context.runtime_backend in ["CONTAINER", "KUBERNETES"]:
                # These are stub backends in current implementation
                if not conditions["runtime_available"]:
                    return True

        # Check approval requirement
        if "requires_approval" in conditions:
            if context.requires_approval != conditions["requires_approval"]:
                return False

        # Check business-specific conditions
        if "business_id" in conditions:
            if context.business_id != conditions["business_id"]:
                return False

        # All conditions matched
        return True

    def get_policy_summary(self) -> Dict[str, Any]:
        """
        Get summary of all capacity policies.

        Returns:
            Policy summary dictionary
        """
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "by_priority": {
                "critical": len([r for r in self.rules if r.priority == CapacityPolicyPriority.CRITICAL]),
                "high": len([r for r in self.rules if r.priority == CapacityPolicyPriority.HIGH]),
                "medium": len([r for r in self.rules if r.priority == CapacityPolicyPriority.MEDIUM]),
                "low": len([r for r in self.rules if r.priority == CapacityPolicyPriority.LOW])
            },
            "by_dimension": self._count_rules_by_dimension(),
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "priority": r.priority.name,
                    "dimension": r.dimension_filter.value if r.dimension_filter else "all",
                    "outcome": r.outcome.value,
                    "enabled": r.enabled
                }
                for r in self.rules
            ]
        }

    def _count_rules_by_dimension(self) -> Dict[str, int]:
        """Count rules by dimension filter."""
        counts = {
            "all": len([r for r in self.rules if r.dimension_filter is None])
        }

        for dimension in CapacityDimension:
            counts[dimension.value] = len([
                r for r in self.rules
                if r.dimension_filter == dimension
            ])

        return counts

    def enable_rule(self, rule_id: str):
        """Enable a policy rule."""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = True

    def disable_rule(self, rule_id: str):
        """Disable a policy rule."""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = False

    def set_rule_priority(self, rule_id: str, priority: CapacityPolicyPriority):
        """
        Update rule priority.

        Args:
            rule_id: Rule to update
            priority: New priority
        """
        rule = self.get_rule(rule_id)
        if rule:
            rule.priority = priority
            # Re-sort rules by priority
            self.rules.sort(key=lambda r: r.priority.value, reverse=True)
