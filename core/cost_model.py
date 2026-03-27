"""
Cost Model for Project Alpha.

Defines cost estimation, classification, and metadata structures.

ARCHITECTURE:
- CostClass: Classification of cost types (free, low, medium, high, unknown)
- CostEstimate: Estimated cost with confidence
- CostMetadata: Full cost information for an operation
- Connector/backend cost estimation functions

COST AWARENESS:
- Estimated costs are used when exact billing is unavailable
- Actual costs recorded when known
- Unknown costs clearly marked
- All cost values are in USD by default
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Import ExecutionDomain for domain-aware cost estimation
try:
    from .execution_plan import ExecutionDomain
except ImportError:
    ExecutionDomain = None  # Graceful fallback if circular import


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class CostClass(Enum):
    """Classification of cost levels."""
    FREE = "free"           # No cost
    MINIMAL = "minimal"     # < $0.01 per operation
    LOW = "low"             # $0.01 - $0.10
    MEDIUM = "medium"       # $0.10 - $1.00
    HIGH = "high"           # $1.00 - $10.00
    VERY_HIGH = "very_high" # > $10.00
    UNKNOWN = "unknown"     # Cost cannot be determined


class CostConfidence(Enum):
    """Confidence level of cost estimates."""
    EXACT = "exact"       # Known exact cost (from billing)
    HIGH = "high"         # Very reliable estimate
    MEDIUM = "medium"     # Reasonably reliable estimate
    LOW = "low"           # Rough estimate
    UNKNOWN = "unknown"   # Cannot estimate


@dataclass
class CostEstimate:
    """
    An estimated cost for an operation.

    Represents the projected or actual cost with confidence level.
    """
    amount: float = 0.0
    currency: str = "USD"
    cost_class: CostClass = CostClass.UNKNOWN
    confidence: CostConfidence = CostConfidence.UNKNOWN
    is_estimate: bool = True
    is_unknown: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount": self.amount,
            "currency": self.currency,
            "cost_class": self.cost_class.value,
            "confidence": self.confidence.value,
            "is_estimate": self.is_estimate,
            "is_unknown": self.is_unknown,
            "notes": self.notes,
        }

    @classmethod
    def unknown(cls, notes: str = "Cost cannot be determined") -> "CostEstimate":
        """Create an unknown cost estimate."""
        return cls(
            amount=0.0,
            cost_class=CostClass.UNKNOWN,
            confidence=CostConfidence.UNKNOWN,
            is_estimate=True,
            is_unknown=True,
            notes=notes,
        )

    @classmethod
    def free(cls, notes: str = "") -> "CostEstimate":
        """Create a free (zero cost) estimate."""
        return cls(
            amount=0.0,
            cost_class=CostClass.FREE,
            confidence=CostConfidence.EXACT,
            is_estimate=False,
            notes=notes,
        )

    @classmethod
    def from_amount(
        cls,
        amount: float,
        confidence: CostConfidence = CostConfidence.MEDIUM,
        notes: str = "",
    ) -> "CostEstimate":
        """Create estimate from an amount."""
        cost_class = cls._classify_amount(amount)
        return cls(
            amount=amount,
            cost_class=cost_class,
            confidence=confidence,
            is_estimate=confidence != CostConfidence.EXACT,
            notes=notes,
        )

    @staticmethod
    def _classify_amount(amount: float) -> CostClass:
        """Classify an amount into a cost class."""
        if amount <= 0:
            return CostClass.FREE
        elif amount < 0.01:
            return CostClass.MINIMAL
        elif amount < 0.10:
            return CostClass.LOW
        elif amount < 1.00:
            return CostClass.MEDIUM
        elif amount < 10.00:
            return CostClass.HIGH
        else:
            return CostClass.VERY_HIGH


@dataclass
class CostMetadata:
    """
    Full cost metadata for an operation.

    Tracks both estimated and actual costs with context.
    """
    cost_id: str = ""
    record_type: str = ""  # job, connector, plan, etc.
    record_id: str = ""
    timestamp: str = field(default_factory=lambda: _utc_now().isoformat())

    # Entity references
    connector: Optional[str] = None
    operation: Optional[str] = None
    backend: Optional[str] = None
    business_id: Optional[str] = None
    plan_id: Optional[str] = None
    job_id: Optional[str] = None

    # Cost values
    estimated_cost: float = 0.0
    actual_cost: Optional[float] = None
    cost_unknown: bool = False
    cost_class: CostClass = CostClass.UNKNOWN
    confidence: CostConfidence = CostConfidence.UNKNOWN
    currency: str = "USD"

    # Additional context
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cost_id": self.cost_id,
            "record_type": self.record_type,
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "connector": self.connector,
            "operation": self.operation,
            "backend": self.backend,
            "business_id": self.business_id,
            "plan_id": self.plan_id,
            "job_id": self.job_id,
            "estimated_cost": self.estimated_cost,
            "actual_cost": self.actual_cost,
            "cost_unknown": self.cost_unknown,
            "cost_class": self.cost_class.value,
            "confidence": self.confidence.value,
            "currency": self.currency,
            "notes": self.notes,
            "metadata": self.metadata,
        }

    def get_effective_cost(self) -> float:
        """Get the best known cost (actual if available, else estimated)."""
        if self.actual_cost is not None:
            return self.actual_cost
        return self.estimated_cost


# =============================================================================
# Connector Cost Estimates
# =============================================================================

# Default cost estimates by connector type
# These are estimates and should be updated based on actual usage patterns
CONNECTOR_COST_ESTIMATES: Dict[str, Dict[str, CostEstimate]] = {
    "sendgrid": {
        "default": CostEstimate.from_amount(0.001, CostConfidence.MEDIUM, "Email send cost"),
        "send_email": CostEstimate.from_amount(0.001, CostConfidence.MEDIUM, "Single email"),
        "send_template": CostEstimate.from_amount(0.001, CostConfidence.MEDIUM, "Template email"),
        "health_check": CostEstimate.free("Health check is free"),
    },
    "hubspot": {
        "default": CostEstimate.from_amount(0.005, CostConfidence.LOW, "HubSpot API call"),
        "create_contact": CostEstimate.from_amount(0.01, CostConfidence.LOW, "Create contact"),
        "update_contact": CostEstimate.from_amount(0.005, CostConfidence.LOW, "Update contact"),
        "search": CostEstimate.from_amount(0.002, CostConfidence.LOW, "Search operation"),
        "health_check": CostEstimate.free("Health check is free"),
    },
    "apollo": {
        "default": CostEstimate.from_amount(0.05, CostConfidence.LOW, "Apollo credit cost"),
        "search_people": CostEstimate.from_amount(0.10, CostConfidence.LOW, "People search"),
        "enrich": CostEstimate.from_amount(0.20, CostConfidence.LOW, "Data enrichment"),
        "health_check": CostEstimate.free("Health check is free"),
    },
    "instantly": {
        "default": CostEstimate.from_amount(0.002, CostConfidence.LOW, "Instantly email cost"),
        "send_campaign": CostEstimate.from_amount(0.05, CostConfidence.LOW, "Campaign batch"),
        "health_check": CostEstimate.free("Health check is free"),
    },
    "smartlead": {
        "default": CostEstimate.from_amount(0.003, CostConfidence.LOW, "SmartLead email cost"),
        "send_sequence": CostEstimate.from_amount(0.05, CostConfidence.LOW, "Sequence batch"),
        "health_check": CostEstimate.free("Health check is free"),
    },
}

# Backend cost estimates
BACKEND_COST_ESTIMATES: Dict[str, CostEstimate] = {
    "inline_local": CostEstimate.free("Local execution, no cloud cost"),
    "queue_local": CostEstimate.free("Local queue, no cloud cost"),
    "container": CostEstimate.from_amount(0.01, CostConfidence.LOW, "Container execution cost"),
    "kubernetes": CostEstimate.from_amount(0.05, CostConfidence.LOW, "K8s pod cost estimate"),
}


def get_connector_cost_estimate(
    connector: str,
    operation: str = "default",
) -> CostEstimate:
    """
    Get estimated cost for a connector operation.

    Args:
        connector: Connector name
        operation: Operation name

    Returns:
        CostEstimate for the operation
    """
    connector_costs = CONNECTOR_COST_ESTIMATES.get(connector, {})

    # Try specific operation first, then default
    if operation in connector_costs:
        return connector_costs[operation]
    elif "default" in connector_costs:
        return connector_costs["default"]

    # Unknown connector
    return CostEstimate.unknown(f"No cost data for connector: {connector}")


def get_backend_cost_estimate(backend: str) -> CostEstimate:
    """
    Get estimated cost for a backend.

    Args:
        backend: Backend type

    Returns:
        CostEstimate for the backend
    """
    return BACKEND_COST_ESTIMATES.get(
        backend,
        CostEstimate.unknown(f"No cost data for backend: {backend}")
    )


def estimate_plan_cost(
    steps: List[Dict[str, Any]],
    backend: str = "inline_local",
) -> CostEstimate:
    """
    Estimate total cost for an execution plan.

    Args:
        steps: List of plan steps
        backend: Backend type

    Returns:
        Aggregated cost estimate
    """
    total = 0.0
    unknown_count = 0
    confidence_levels = []

    # Backend base cost
    backend_cost = get_backend_cost_estimate(backend)
    if backend_cost.is_unknown:
        unknown_count += 1
    else:
        total += backend_cost.amount
        confidence_levels.append(backend_cost.confidence)

    # Estimate each step
    for step in steps:
        connector = step.get("connector")
        operation = step.get("operation", "default")

        if connector:
            step_cost = get_connector_cost_estimate(connector, operation)
            if step_cost.is_unknown:
                unknown_count += 1
            else:
                total += step_cost.amount
                confidence_levels.append(step_cost.confidence)

    # Determine overall confidence
    if unknown_count > 0:
        overall_confidence = CostConfidence.LOW
        if unknown_count > len(steps) / 2:
            overall_confidence = CostConfidence.UNKNOWN
    elif confidence_levels:
        # Use lowest confidence
        conf_order = [CostConfidence.UNKNOWN, CostConfidence.LOW, CostConfidence.MEDIUM, CostConfidence.HIGH, CostConfidence.EXACT]
        min_conf = min(confidence_levels, key=lambda c: conf_order.index(c))
        overall_confidence = min_conf
    else:
        overall_confidence = CostConfidence.UNKNOWN

    return CostEstimate.from_amount(
        amount=total,
        confidence=overall_confidence,
        notes=f"Estimated from {len(steps)} steps, {unknown_count} unknown costs",
    )


def estimate_job_cost(
    plan_cost: CostEstimate,
    retry_count: int = 0,
) -> CostEstimate:
    """
    Estimate job cost including potential retries.

    Args:
        plan_cost: Cost estimate for the plan
        retry_count: Number of allowed retries

    Returns:
        Job cost estimate
    """
    # Account for potential retry overhead
    base_cost = plan_cost.amount
    retry_factor = 1.0 + (retry_count * 0.5)  # Each retry could add 50%

    total = base_cost * retry_factor

    return CostEstimate.from_amount(
        amount=total,
        confidence=plan_cost.confidence,
        notes=f"Base: {base_cost:.4f}, retry factor: {retry_factor:.1f}",
    )


# =============================================================================
# Cost Classification Helpers
# =============================================================================

def classify_cost(amount: float) -> CostClass:
    """Classify a cost amount."""
    return CostEstimate._classify_amount(amount)


def is_high_cost(amount: float, threshold: float = 1.0) -> bool:
    """Check if a cost exceeds a threshold."""
    return amount >= threshold


def cost_requires_approval(
    amount: float,
    approval_threshold: float = 0.50,
) -> bool:
    """
    Check if a cost should require approval.

    Args:
        amount: Cost amount
        approval_threshold: Threshold for requiring approval

    Returns:
        True if approval should be required
    """
    return amount >= approval_threshold


def cost_exceeds_budget(
    amount: float,
    budget_remaining: float,
) -> bool:
    """
    Check if a cost would exceed remaining budget.

    Args:
        amount: Cost amount
        budget_remaining: Remaining budget

    Returns:
        True if cost exceeds budget
    """
    return amount > budget_remaining


def get_domain_cost_modifier(domain: Optional[str] = None) -> float:
    """
    Get cost modifier based on execution domain.

    Different domains may have different typical cost profiles.
    This provides a simple multiplier for domain-aware cost estimation.

    Args:
        domain: Domain name (from ExecutionDomain.value)

    Returns:
        Cost modifier (1.0 = baseline)
    """
    if not domain or not ExecutionDomain:
        return 1.0

    # Domain-specific cost modifiers
    # These reflect typical cost patterns for different domain operations
    domain_modifiers = {
        "research": 0.8,          # Research often uses free/low-cost tools
        "strategy": 1.0,          # Strategy is baseline
        "planning": 0.9,          # Planning mostly internal, low external cost
        "product": 1.0,           # Product development baseline
        "engineering": 1.1,       # Engineering may use paid tools/services
        "validation": 0.7,        # Testing often local/low cost
        "operations": 1.0,        # Operations baseline
        "automation": 0.8,        # Automation reduces long-term cost
        "internal_admin": 0.6,    # Internal admin very low cost
        "finance": 1.2,           # Finance operations may involve transaction costs
        "compliance": 1.1,        # Compliance may require paid services/audits
        "growth": 1.3,            # Growth/outreach typically higher cost
        "customer_support": 0.9,  # Support moderate cost
        "content": 0.8,           # Content creation lower external cost
        "unknown": 1.0,           # Unknown domain baseline
    }

    return domain_modifiers.get(domain, 1.0)


def estimate_domain_aware_cost(
    base_estimate: CostEstimate,
    domain: Optional[str] = None,
) -> CostEstimate:
    """
    Apply domain-specific cost modifier to a base estimate.

    Args:
        base_estimate: Base cost estimate
        domain: Domain name

    Returns:
        Adjusted cost estimate
    """
    if not domain or base_estimate.is_unknown:
        return base_estimate

    modifier = get_domain_cost_modifier(domain)

    if modifier == 1.0:
        return base_estimate

    adjusted_amount = base_estimate.amount * modifier
    adjusted_class = CostEstimate._classify_amount(adjusted_amount)

    return CostEstimate(
        amount=adjusted_amount,
        currency=base_estimate.currency,
        cost_class=adjusted_class,
        confidence=base_estimate.confidence,
        is_estimate=base_estimate.is_estimate,
        is_unknown=False,
        notes=f"{base_estimate.notes} (domain-adjusted: {domain})"
    )
