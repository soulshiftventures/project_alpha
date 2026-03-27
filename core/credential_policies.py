"""
Credential Policies for Project Alpha.

Defines policies for credential access, usage limits, and security rules.

SECURITY RULES:
- All credential access is policy-controlled
- Sensitive operations require additional checks
- Rate limiting prevents abuse
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import defaultdict

from core.secrets_manager import SecretSensitivity
from config.redaction import REDACTION_MARKER


class PolicyDecision(Enum):
    """Result of a policy check."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    RATE_LIMITED = "rate_limited"


class PolicyViolationType(Enum):
    """Types of policy violations."""
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SENSITIVITY_MISMATCH = "sensitivity_mismatch"
    SCOPE_VIOLATION = "scope_violation"
    TIME_RESTRICTION = "time_restriction"
    MISSING_APPROVAL = "missing_approval"


@dataclass
class PolicyViolation:
    """Record of a policy violation."""

    violation_type: PolicyViolationType
    credential_name: str
    component: str
    operation: str
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    severity: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "violation_type": self.violation_type.value,
            "credential_name": self.credential_name,
            "component": self.component,
            "operation": self.operation,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
        }


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
            "requests_per_day": self.requests_per_day,
            "burst_limit": self.burst_limit,
        }


@dataclass
class CredentialPolicy:
    """
    Policy rules for a credential.

    Defines access rules, rate limits, and security requirements.
    """

    credential_name: str
    allowed_components: Set[str] = field(default_factory=set)
    allowed_operations: Set[str] = field(default_factory=set)
    min_sensitivity_clearance: SecretSensitivity = SecretSensitivity.LOW
    requires_approval_for: Set[str] = field(default_factory=set)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    time_restrictions: Optional[Dict[str, Any]] = None
    enabled: bool = True
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "credential_name": self.credential_name,
            "allowed_components": list(self.allowed_components),
            "allowed_operations": list(self.allowed_operations),
            "min_sensitivity_clearance": self.min_sensitivity_clearance.value,
            "requires_approval_for": list(self.requires_approval_for),
            "rate_limit": self.rate_limit.to_dict(),
            "time_restrictions": self.time_restrictions,
            "enabled": self.enabled,
            "notes": self.notes,
        }


class CredentialPolicyEngine:
    """
    Policy engine for credential access control.

    Evaluates access requests against defined policies.
    """

    def __init__(self):
        self._policies: Dict[str, CredentialPolicy] = {}
        self._violations: List[PolicyViolation] = []
        self._usage_counters: Dict[str, Dict[str, List[datetime]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._load_default_policies()

    def _load_default_policies(self) -> None:
        """Load default credential policies."""
        default_policies = [
            # AI APIs - higher rate limits
            CredentialPolicy(
                credential_name="anthropic_api_key",
                allowed_components={"ai_client", "chief_orchestrator"},
                allowed_operations={"*"},
                min_sensitivity_clearance=SecretSensitivity.MEDIUM,
                rate_limit=RateLimitConfig(
                    requests_per_minute=30,
                    requests_per_hour=500,
                    requests_per_day=5000,
                ),
            ),
            CredentialPolicy(
                credential_name="openai_api_key",
                allowed_components={"ai_client"},
                allowed_operations={"*"},
                min_sensitivity_clearance=SecretSensitivity.MEDIUM,
                rate_limit=RateLimitConfig(
                    requests_per_minute=30,
                    requests_per_hour=500,
                    requests_per_day=5000,
                ),
            ),

            # Research APIs - moderate limits
            CredentialPolicy(
                credential_name="tavily_api_key",
                allowed_components={"tavily_connector", "research_skill"},
                allowed_operations={"search", "extract"},
                min_sensitivity_clearance=SecretSensitivity.LOW,
                rate_limit=RateLimitConfig(
                    requests_per_minute=20,
                    requests_per_hour=200,
                    requests_per_day=1000,
                ),
            ),
            CredentialPolicy(
                credential_name="firecrawl_api_key",
                allowed_components={"firecrawl_connector", "research_skill"},
                allowed_operations={"scrape", "crawl"},
                min_sensitivity_clearance=SecretSensitivity.LOW,
                rate_limit=RateLimitConfig(
                    requests_per_minute=10,
                    requests_per_hour=100,
                    requests_per_day=500,
                ),
            ),

            # Lead Gen APIs - requires approval for bulk operations
            CredentialPolicy(
                credential_name="apollo_api_key",
                allowed_components={"apollo_connector", "lead_gen_skill"},
                allowed_operations={"search", "enrich", "bulk_search"},
                min_sensitivity_clearance=SecretSensitivity.MEDIUM,
                requires_approval_for={"bulk_search", "export"},
                rate_limit=RateLimitConfig(
                    requests_per_minute=10,
                    requests_per_hour=100,
                    requests_per_day=500,
                ),
            ),
            CredentialPolicy(
                credential_name="outscraper_api_key",
                allowed_components={"outscraper_connector", "lead_gen_skill"},
                allowed_operations={"search", "extract"},
                min_sensitivity_clearance=SecretSensitivity.MEDIUM,
                requires_approval_for={"bulk_extract"},
                rate_limit=RateLimitConfig(
                    requests_per_minute=5,
                    requests_per_hour=50,
                    requests_per_day=200,
                ),
            ),

            # CRM - requires approval for writes
            CredentialPolicy(
                credential_name="hubspot_api_key",
                allowed_components={"hubspot_connector", "crm_skill"},
                allowed_operations={"read", "create", "update", "delete"},
                min_sensitivity_clearance=SecretSensitivity.MEDIUM,
                requires_approval_for={"create", "update", "delete", "bulk_update"},
                rate_limit=RateLimitConfig(
                    requests_per_minute=20,
                    requests_per_hour=200,
                    requests_per_day=2000,
                ),
            ),

            # Messaging - requires approval for sends
            CredentialPolicy(
                credential_name="telegram_bot_token",
                allowed_components={"telegram_connector", "notification_skill"},
                allowed_operations={"send_message", "send_document"},
                min_sensitivity_clearance=SecretSensitivity.LOW,
                requires_approval_for={"send_message", "broadcast"},
                rate_limit=RateLimitConfig(
                    requests_per_minute=30,
                    requests_per_hour=200,
                    requests_per_day=1000,
                ),
            ),
            CredentialPolicy(
                credential_name="sendgrid_api_key",
                allowed_components={"sendgrid_connector", "email_skill"},
                allowed_operations={"send_email", "send_template"},
                min_sensitivity_clearance=SecretSensitivity.LOW,
                requires_approval_for={"send_email", "bulk_send"},
                rate_limit=RateLimitConfig(
                    requests_per_minute=10,
                    requests_per_hour=100,
                    requests_per_day=500,
                ),
            ),
        ]

        for policy in default_policies:
            self.register_policy(policy)

    def register_policy(self, policy: CredentialPolicy) -> None:
        """Register a credential policy."""
        self._policies[policy.credential_name] = policy

    def get_policy(self, credential_name: str) -> Optional[CredentialPolicy]:
        """Get policy for a credential."""
        return self._policies.get(credential_name)

    def _check_rate_limit(
        self,
        credential_name: str,
        component: str,
        policy: CredentialPolicy,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if rate limit allows the request.

        Returns:
            Tuple of (allowed, reason if denied)
        """
        key = f"{credential_name}:{component}"
        now = datetime.now(timezone.utc)
        timestamps = self._usage_counters[credential_name][component]

        # Clean old timestamps
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        timestamps = [t for t in timestamps if t > day_ago]
        self._usage_counters[credential_name][component] = timestamps

        # Check limits
        last_minute = [t for t in timestamps if t > minute_ago]
        last_hour = [t for t in timestamps if t > hour_ago]
        last_day = timestamps

        if len(last_minute) >= policy.rate_limit.requests_per_minute:
            return False, f"Rate limit exceeded: {policy.rate_limit.requests_per_minute}/min"

        if len(last_hour) >= policy.rate_limit.requests_per_hour:
            return False, f"Rate limit exceeded: {policy.rate_limit.requests_per_hour}/hour"

        if len(last_day) >= policy.rate_limit.requests_per_day:
            return False, f"Rate limit exceeded: {policy.rate_limit.requests_per_day}/day"

        return True, None

    def _record_usage(self, credential_name: str, component: str) -> None:
        """Record a usage timestamp for rate limiting."""
        now = datetime.now(timezone.utc)
        self._usage_counters[credential_name][component].append(now)

    def check_access(
        self,
        credential_name: str,
        component: str,
        operation: str,
        record_usage: bool = True,
    ) -> Tuple[PolicyDecision, Optional[str]]:
        """
        Check if access is allowed by policy.

        Args:
            credential_name: Credential to access
            component: Component requesting access
            operation: Operation being performed
            record_usage: Whether to record this for rate limiting

        Returns:
            Tuple of (decision, reason)
        """
        policy = self._policies.get(credential_name)

        # No policy = default allow (but log warning)
        if not policy:
            return PolicyDecision.ALLOW, "No policy defined"

        if not policy.enabled:
            return PolicyDecision.DENY, "Policy disabled"

        # Check component authorization
        if policy.allowed_components and component not in policy.allowed_components:
            violation = PolicyViolation(
                violation_type=PolicyViolationType.UNAUTHORIZED_ACCESS,
                credential_name=credential_name,
                component=component,
                operation=operation,
                reason=f"Component {component} not authorized",
                severity="high",
            )
            self._violations.append(violation)
            return PolicyDecision.DENY, f"Component {component} not authorized"

        # Check operation authorization
        if policy.allowed_operations and "*" not in policy.allowed_operations:
            if operation not in policy.allowed_operations:
                violation = PolicyViolation(
                    violation_type=PolicyViolationType.UNAUTHORIZED_ACCESS,
                    credential_name=credential_name,
                    component=component,
                    operation=operation,
                    reason=f"Operation {operation} not allowed",
                    severity="medium",
                )
                self._violations.append(violation)
                return PolicyDecision.DENY, f"Operation {operation} not allowed"

        # Check rate limit
        allowed, reason = self._check_rate_limit(credential_name, component, policy)
        if not allowed:
            violation = PolicyViolation(
                violation_type=PolicyViolationType.RATE_LIMIT_EXCEEDED,
                credential_name=credential_name,
                component=component,
                operation=operation,
                reason=reason,
                severity="low",
            )
            self._violations.append(violation)
            return PolicyDecision.RATE_LIMITED, reason

        # Check if approval required
        if operation in policy.requires_approval_for:
            return PolicyDecision.REQUIRE_APPROVAL, f"Operation {operation} requires approval"

        # Record usage for rate limiting
        if record_usage:
            self._record_usage(credential_name, component)

        return PolicyDecision.ALLOW, None

    def record_violation(self, violation: PolicyViolation) -> None:
        """Record a policy violation."""
        self._violations.append(violation)

        # Trim violations list if too large
        if len(self._violations) > 10000:
            self._violations = self._violations[-5000:]

    def get_violations(
        self,
        credential_name: Optional[str] = None,
        component: Optional[str] = None,
        violation_type: Optional[PolicyViolationType] = None,
        limit: int = 100,
    ) -> List[PolicyViolation]:
        """Get violations with optional filters."""
        filtered = self._violations

        if credential_name:
            filtered = [v for v in filtered if v.credential_name == credential_name]

        if component:
            filtered = [v for v in filtered if v.component == component]

        if violation_type:
            filtered = [v for v in filtered if v.violation_type == violation_type]

        return filtered[-limit:]

    def get_rate_limit_status(
        self, credential_name: str, component: str
    ) -> Dict[str, Any]:
        """Get current rate limit status for a credential/component."""
        policy = self._policies.get(credential_name)
        if not policy:
            return {"error": "No policy found"}

        now = datetime.now(timezone.utc)
        timestamps = self._usage_counters[credential_name][component]

        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        last_minute = len([t for t in timestamps if t > minute_ago])
        last_hour = len([t for t in timestamps if t > hour_ago])
        last_day = len([t for t in timestamps if t > day_ago])

        return {
            "credential_name": credential_name,
            "component": component,
            "limits": {
                "per_minute": policy.rate_limit.requests_per_minute,
                "per_hour": policy.rate_limit.requests_per_hour,
                "per_day": policy.rate_limit.requests_per_day,
            },
            "usage": {
                "last_minute": last_minute,
                "last_hour": last_hour,
                "last_day": last_day,
            },
            "remaining": {
                "this_minute": max(0, policy.rate_limit.requests_per_minute - last_minute),
                "this_hour": max(0, policy.rate_limit.requests_per_hour - last_hour),
                "this_day": max(0, policy.rate_limit.requests_per_day - last_day),
            },
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get policy engine summary."""
        total_policies = len(self._policies)
        enabled_policies = len([p for p in self._policies.values() if p.enabled])
        total_violations = len(self._violations)

        violations_by_type = {}
        for vtype in PolicyViolationType:
            count = len([v for v in self._violations if v.violation_type == vtype])
            violations_by_type[vtype.value] = count

        return {
            "total_policies": total_policies,
            "enabled_policies": enabled_policies,
            "total_violations": total_violations,
            "violations_by_type": violations_by_type,
        }


# Singleton instance
_policy_engine: Optional[CredentialPolicyEngine] = None


def get_policy_engine() -> CredentialPolicyEngine:
    """Get the global policy engine."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = CredentialPolicyEngine()
    return _policy_engine
