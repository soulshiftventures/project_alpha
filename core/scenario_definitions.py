"""
Scenario Definitions for Project Alpha.

Defines named end-to-end execution scenarios that prove Project Alpha
can move through multiple layers of the system coherently.

SCENARIOS:
1. Research Scenario - Web research via Tavily/Firecrawl
2. Notification Scenario - Notification delivery via SendGrid/Telegram
3. CRM Scenario - Contact management via HubSpot
4. Discovery-to-Validation Scenario - Full opportunity lifecycle

Each scenario:
- Has named steps with clear execution paths
- Specifies which connectors/skills are used
- Supports dry-run vs live-capable execution
- Records step-by-step results
- Integrates with approval workflow where relevant
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import uuid


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class ScenarioStatus(Enum):
    """Status of a scenario run."""
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class StepStatus(Enum):
    """Status of a scenario step."""
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class StepType(Enum):
    """Type of scenario step."""
    SKILL_SELECTION = "skill_selection"
    PLAN_CREATION = "plan_creation"
    APPROVAL_REQUEST = "approval_request"
    CONNECTOR_ACTION = "connector_action"
    ORCHESTRATOR_CALL = "orchestrator_call"
    DISCOVERY_INTAKE = "discovery_intake"
    HANDOFF_CREATION = "handoff_creation"
    PERSISTENCE_CHECK = "persistence_check"
    VALIDATION = "validation"


class ScenarioCategory(Enum):
    """Category of scenario."""
    RESEARCH = "research"
    NOTIFICATION = "notification"
    CRM = "crm"
    DISCOVERY = "discovery"
    END_TO_END = "end_to_end"


@dataclass
class ScenarioStep:
    """Definition of a single step in a scenario."""
    step_id: str
    name: str
    description: str
    step_type: StepType
    required: bool = True
    requires_approval: bool = False
    requires_live_mode: bool = False
    connector: Optional[str] = None
    operation: Optional[str] = None
    expected_outcome: Optional[str] = None
    input_mapping: Optional[Dict[str, str]] = None  # Maps from scenario inputs
    output_keys: Optional[List[str]] = None  # Keys to extract from result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "step_type": self.step_type.value,
            "required": self.required,
            "requires_approval": self.requires_approval,
            "requires_live_mode": self.requires_live_mode,
            "connector": self.connector,
            "operation": self.operation,
            "expected_outcome": self.expected_outcome,
            "input_mapping": self.input_mapping,
            "output_keys": self.output_keys,
        }


@dataclass
class ScenarioDefinition:
    """Definition of a named scenario."""
    scenario_id: str
    name: str
    description: str
    category: ScenarioCategory
    steps: List[ScenarioStep]
    required_inputs: List[str]
    optional_inputs: List[str] = field(default_factory=list)
    default_inputs: Dict[str, Any] = field(default_factory=dict)
    dry_run_capable: bool = True
    live_capable: bool = True
    requires_approval_by_default: bool = False
    estimated_duration_seconds: int = 60
    connectors_used: List[str] = field(default_factory=list)
    proof_points: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "steps": [s.to_dict() for s in self.steps],
            "required_inputs": self.required_inputs,
            "optional_inputs": self.optional_inputs,
            "default_inputs": self.default_inputs,
            "dry_run_capable": self.dry_run_capable,
            "live_capable": self.live_capable,
            "requires_approval_by_default": self.requires_approval_by_default,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "connectors_used": self.connectors_used,
            "proof_points": self.proof_points,
            "step_count": len(self.steps),
        }


@dataclass
class StepResult:
    """Result of executing a scenario step."""
    step_id: str
    status: StepStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    approval_id: Optional[str] = None
    connector_execution_id: Optional[str] = None
    plan_id: Optional[str] = None
    job_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "approval_id": self.approval_id,
            "connector_execution_id": self.connector_execution_id,
            "plan_id": self.plan_id,
            "job_id": self.job_id,
        }


@dataclass
class ScenarioRun:
    """Record of a scenario execution run."""
    run_id: str
    scenario_id: str
    scenario_name: str
    status: ScenarioStatus
    inputs: Dict[str, Any]
    dry_run: bool = True
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    step_results: List[StepResult] = field(default_factory=list)
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    final_output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    triggered_by: str = "operator"

    # Related entity IDs for audit trail
    plan_ids: List[str] = field(default_factory=list)
    job_ids: List[str] = field(default_factory=list)
    approval_ids: List[str] = field(default_factory=list)
    connector_execution_ids: List[str] = field(default_factory=list)
    opportunity_id: Optional[str] = None
    handoff_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "status": self.status.value,
            "inputs": self.inputs,
            "dry_run": self.dry_run,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "step_results": [r.to_dict() for r in self.step_results],
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "final_output": self.final_output,
            "error_message": self.error_message,
            "triggered_by": self.triggered_by,
            "plan_ids": self.plan_ids,
            "job_ids": self.job_ids,
            "approval_ids": self.approval_ids,
            "connector_execution_ids": self.connector_execution_ids,
            "opportunity_id": self.opportunity_id,
            "handoff_id": self.handoff_id,
        }


# =============================================================================
# SCENARIO DEFINITIONS
# =============================================================================

def create_research_scenario() -> ScenarioDefinition:
    """
    Research Scenario: Perform web research using Tavily.

    Proves:
    - Skill selection for research tasks
    - Execution plan creation
    - Connector action execution (Tavily search)
    - Result persistence
    - History visibility
    """
    return ScenarioDefinition(
        scenario_id="scenario_research",
        name="Research Scenario",
        description="Perform AI-powered web research using Tavily search",
        category=ScenarioCategory.RESEARCH,
        steps=[
            ScenarioStep(
                step_id="research_step_1",
                name="Skill Selection",
                description="Select appropriate skills for research objective",
                step_type=StepType.SKILL_SELECTION,
                expected_outcome="Research skills identified",
            ),
            ScenarioStep(
                step_id="research_step_2",
                name="Plan Creation",
                description="Create execution plan for research task",
                step_type=StepType.PLAN_CREATION,
                expected_outcome="Execution plan created",
                output_keys=["plan_id", "step_count"],
            ),
            ScenarioStep(
                step_id="research_step_3",
                name="Tavily Search",
                description="Execute web search via Tavily connector",
                step_type=StepType.CONNECTOR_ACTION,
                connector="tavily",
                operation="search",
                input_mapping={"query": "research_query"},
                expected_outcome="Search results returned",
                output_keys=["results", "result_count"],
            ),
            ScenarioStep(
                step_id="research_step_4",
                name="Persistence Check",
                description="Verify results persisted to history",
                step_type=StepType.PERSISTENCE_CHECK,
                expected_outcome="Connector action persisted",
            ),
        ],
        required_inputs=["research_query"],
        optional_inputs=["max_results", "search_depth"],
        default_inputs={"max_results": 5, "search_depth": "basic"},
        dry_run_capable=True,
        live_capable=True,
        connectors_used=["tavily"],
        proof_points=[
            "Skill selection works for research objective",
            "Execution plan created from skill selection",
            "Tavily connector executed (dry-run or live)",
            "Connector action persisted to history",
        ],
    )


def create_notification_scenario() -> ScenarioDefinition:
    """
    Notification Scenario: Send notification via SendGrid email.

    Proves:
    - Skill selection for notification tasks
    - Approval workflow for external actions
    - Connector action with approval gating
    - Email delivery (dry-run or live)
    - Audit trail
    """
    return ScenarioDefinition(
        scenario_id="scenario_notification",
        name="Notification Scenario",
        description="Send email notification via SendGrid",
        category=ScenarioCategory.NOTIFICATION,
        steps=[
            ScenarioStep(
                step_id="notify_step_1",
                name="Skill Selection",
                description="Select notification skill",
                step_type=StepType.SKILL_SELECTION,
                expected_outcome="Email skill identified",
            ),
            ScenarioStep(
                step_id="notify_step_2",
                name="Plan Creation",
                description="Create execution plan for notification",
                step_type=StepType.PLAN_CREATION,
                expected_outcome="Execution plan created",
                output_keys=["plan_id"],
            ),
            ScenarioStep(
                step_id="notify_step_3",
                name="Approval Request",
                description="Request approval for external email send",
                step_type=StepType.APPROVAL_REQUEST,
                requires_approval=True,
                expected_outcome="Approval requested and resolved",
                output_keys=["approval_id", "approved"],
            ),
            ScenarioStep(
                step_id="notify_step_4",
                name="SendGrid Email",
                description="Send email via SendGrid connector",
                step_type=StepType.CONNECTOR_ACTION,
                connector="sendgrid",
                operation="send_email",
                requires_approval=True,
                requires_live_mode=True,
                input_mapping={
                    "to_email": "recipient_email",
                    "subject": "email_subject",
                    "content": "email_body",
                },
                expected_outcome="Email sent (or simulated in dry-run)",
                output_keys=["message_id", "sent"],
            ),
            ScenarioStep(
                step_id="notify_step_5",
                name="Persistence Check",
                description="Verify notification action persisted",
                step_type=StepType.PERSISTENCE_CHECK,
                expected_outcome="Action persisted to history",
            ),
        ],
        required_inputs=["recipient_email", "email_subject", "email_body"],
        optional_inputs=["from_email"],
        default_inputs={},
        dry_run_capable=True,
        live_capable=True,
        requires_approval_by_default=True,
        connectors_used=["sendgrid"],
        proof_points=[
            "Notification skill selected",
            "Approval workflow triggered for external action",
            "SendGrid connector executed with proper gating",
            "Full audit trail recorded",
        ],
    )


def create_crm_scenario() -> ScenarioDefinition:
    """
    CRM Scenario: Create/update contact in HubSpot.

    Proves:
    - CRM skill selection
    - Data creation approval workflow
    - HubSpot connector execution
    - Contact creation/update
    - Persistence of CRM actions
    """
    return ScenarioDefinition(
        scenario_id="scenario_crm",
        name="CRM Scenario",
        description="Create or update a contact in HubSpot CRM",
        category=ScenarioCategory.CRM,
        steps=[
            ScenarioStep(
                step_id="crm_step_1",
                name="Skill Selection",
                description="Select CRM management skill",
                step_type=StepType.SKILL_SELECTION,
                expected_outcome="CRM skill identified",
            ),
            ScenarioStep(
                step_id="crm_step_2",
                name="Plan Creation",
                description="Create execution plan for CRM operation",
                step_type=StepType.PLAN_CREATION,
                expected_outcome="Execution plan created",
                output_keys=["plan_id"],
            ),
            ScenarioStep(
                step_id="crm_step_3",
                name="Approval Request",
                description="Request approval for CRM data write",
                step_type=StepType.APPROVAL_REQUEST,
                requires_approval=True,
                expected_outcome="Approval requested and resolved",
                output_keys=["approval_id", "approved"],
            ),
            ScenarioStep(
                step_id="crm_step_4",
                name="HubSpot Create Contact",
                description="Create contact in HubSpot",
                step_type=StepType.CONNECTOR_ACTION,
                connector="hubspot",
                operation="create_contact",
                requires_approval=True,
                requires_live_mode=True,
                input_mapping={
                    "email": "contact_email",
                    "firstname": "contact_firstname",
                    "lastname": "contact_lastname",
                    "company": "contact_company",
                },
                expected_outcome="Contact created (or simulated in dry-run)",
                output_keys=["contact_id", "created"],
            ),
            ScenarioStep(
                step_id="crm_step_5",
                name="Persistence Check",
                description="Verify CRM action persisted",
                step_type=StepType.PERSISTENCE_CHECK,
                expected_outcome="Action persisted to history",
            ),
        ],
        required_inputs=["contact_email", "contact_firstname", "contact_lastname"],
        optional_inputs=["contact_company", "contact_phone"],
        default_inputs={},
        dry_run_capable=True,
        live_capable=True,
        requires_approval_by_default=True,
        connectors_used=["hubspot"],
        proof_points=[
            "CRM skill selected",
            "Approval workflow for data write",
            "HubSpot connector executed",
            "Contact creation persisted",
        ],
    )


def create_discovery_to_validation_scenario() -> ScenarioDefinition:
    """
    Discovery-to-Validation Scenario: Full opportunity lifecycle.

    Proves:
    - Discovery intake processing
    - Opportunity scoring and recommendation
    - Handoff creation
    - Validation research execution
    - Multi-layer orchestration
    """
    return ScenarioDefinition(
        scenario_id="scenario_discovery_validation",
        name="Discovery-to-Validation Scenario",
        description="Process discovery input through validation research",
        category=ScenarioCategory.DISCOVERY,
        steps=[
            ScenarioStep(
                step_id="disc_step_1",
                name="Discovery Intake",
                description="Process raw discovery input into opportunity",
                step_type=StepType.DISCOVERY_INTAKE,
                expected_outcome="Opportunity record created",
                output_keys=["opportunity_id", "hypothesis", "score"],
            ),
            ScenarioStep(
                step_id="disc_step_2",
                name="Handoff Creation",
                description="Create handoff for validation mode",
                step_type=StepType.HANDOFF_CREATION,
                expected_outcome="Handoff to validation created",
                output_keys=["handoff_id", "mode", "plan_id"],
            ),
            ScenarioStep(
                step_id="disc_step_3",
                name="Plan Creation",
                description="Create validation execution plan",
                step_type=StepType.PLAN_CREATION,
                expected_outcome="Validation plan created",
                output_keys=["plan_id", "objective"],
            ),
            ScenarioStep(
                step_id="disc_step_4",
                name="Validation Research",
                description="Execute validation research via Tavily",
                step_type=StepType.CONNECTOR_ACTION,
                connector="tavily",
                operation="search",
                input_mapping={"query": "validation_query"},
                expected_outcome="Validation research results",
                output_keys=["results", "validation_findings"],
            ),
            ScenarioStep(
                step_id="disc_step_5",
                name="Persistence Check",
                description="Verify all entities persisted",
                step_type=StepType.PERSISTENCE_CHECK,
                expected_outcome="Opportunity, handoff, plan, actions persisted",
            ),
            ScenarioStep(
                step_id="disc_step_6",
                name="Validation Summary",
                description="Generate validation summary from results",
                step_type=StepType.VALIDATION,
                expected_outcome="Validation summary generated",
                output_keys=["validation_summary", "recommendation"],
            ),
        ],
        required_inputs=["discovery_text"],
        optional_inputs=["tags", "validation_query"],
        default_inputs={},
        dry_run_capable=True,
        live_capable=True,
        connectors_used=["tavily"],
        proof_points=[
            "Discovery intake creates scored opportunity",
            "Handoff correctly routes to validation",
            "Validation plan created from handoff",
            "Research connector executes validation",
            "All entities persisted with relationships",
            "End-to-end audit trail complete",
        ],
    )


# =============================================================================
# SCENARIO REGISTRY
# =============================================================================

class ScenarioRegistry:
    """Registry of available scenarios."""

    def __init__(self):
        """Initialize the scenario registry."""
        self._scenarios: Dict[str, ScenarioDefinition] = {}
        self._register_builtin_scenarios()

    def _register_builtin_scenarios(self) -> None:
        """Register all built-in scenarios."""
        scenarios = [
            create_research_scenario(),
            create_notification_scenario(),
            create_crm_scenario(),
            create_discovery_to_validation_scenario(),
        ]
        for scenario in scenarios:
            self._scenarios[scenario.scenario_id] = scenario

    def get_scenario(self, scenario_id: str) -> Optional[ScenarioDefinition]:
        """Get a scenario by ID."""
        return self._scenarios.get(scenario_id)

    def list_scenarios(
        self,
        category: Optional[ScenarioCategory] = None,
    ) -> List[ScenarioDefinition]:
        """List available scenarios."""
        scenarios = list(self._scenarios.values())
        if category:
            scenarios = [s for s in scenarios if s.category == category]
        return scenarios

    def get_scenario_ids(self) -> List[str]:
        """Get all scenario IDs."""
        return list(self._scenarios.keys())

    def register_scenario(self, scenario: ScenarioDefinition) -> None:
        """Register a custom scenario."""
        self._scenarios[scenario.scenario_id] = scenario

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of available scenarios."""
        by_category: Dict[str, List[str]] = {}
        for scenario in self._scenarios.values():
            cat = scenario.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(scenario.name)

        return {
            "total_scenarios": len(self._scenarios),
            "by_category": by_category,
            "scenario_ids": list(self._scenarios.keys()),
        }


# Singleton registry
_scenario_registry: Optional[ScenarioRegistry] = None


def get_scenario_registry() -> ScenarioRegistry:
    """Get the global scenario registry."""
    global _scenario_registry
    if _scenario_registry is None:
        _scenario_registry = ScenarioRegistry()
    return _scenario_registry
