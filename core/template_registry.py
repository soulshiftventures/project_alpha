"""
Template Registry - First-run workflow templates for operators.

Provides reusable workflow templates that operators can browse, inspect,
and launch. Templates define common workflows with prefilled defaults.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import uuid


class TemplateCategory(Enum):
    """Categories for organizing templates."""
    DISCOVERY = "discovery"
    RESEARCH = "research"
    NOTIFICATION = "notification"
    CRM = "crm"
    MAINTENANCE = "maintenance"
    INTEGRATION = "integration"


class TemplateMode(Enum):
    """Execution mode capabilities for templates."""
    DRY_RUN_ONLY = "dry_run_only"
    LIVE_CAPABLE = "live_capable"
    READ_ONLY = "read_only"


class TemplateComplexity(Enum):
    """Complexity level for templates."""
    SIMPLE = "simple"      # Single action, few inputs
    MODERATE = "moderate"  # Multi-step, some configuration
    ADVANCED = "advanced"  # Complex workflow, many options


@dataclass
class TemplateInput:
    """Input field definition for a template."""
    name: str
    label: str
    input_type: str = "text"  # text, textarea, select, number, email, url
    required: bool = True
    default_value: str = ""
    placeholder: str = ""
    help_text: str = ""
    options: List[str] = field(default_factory=list)  # For select type
    validation_pattern: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TemplateStep:
    """Step definition for template execution."""
    step_id: str
    name: str
    description: str
    action_type: str  # connector, approval, validation, notification
    connector: Optional[str] = None
    operation: Optional[str] = None
    parameters_mapping: Dict[str, str] = field(default_factory=dict)  # input_name -> param_name
    requires_approval: bool = False
    skip_on_dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowTemplate:
    """
    Workflow template definition.

    Templates provide reusable, operator-friendly workflows with
    predefined steps, inputs, and defaults.
    """
    template_id: str
    name: str
    description: str
    category: TemplateCategory
    mode: TemplateMode
    complexity: TemplateComplexity

    # Inputs the operator needs to provide
    inputs: List[TemplateInput] = field(default_factory=list)

    # Steps to execute
    steps: List[TemplateStep] = field(default_factory=list)

    # Metadata
    version: str = "1.0.0"
    author: str = "system"
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # UI hints
    icon: str = "play"
    estimated_duration: str = "< 1 minute"
    prerequisites: List[str] = field(default_factory=list)

    # Behavior
    requires_live_credentials: bool = False
    auto_approve: bool = False

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["category"] = self.category.value
        result["mode"] = self.mode.value
        result["complexity"] = self.complexity.value
        return result


@dataclass
class TemplateLaunch:
    """Record of a template being launched."""
    launch_id: str
    template_id: str
    inputs: Dict[str, Any]
    dry_run: bool
    launched_by: str
    launched_at: str
    status: str = "pending"  # pending, running, completed, failed
    scenario_run_id: Optional[str] = None
    job_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TemplateRegistry:
    """
    Registry for workflow templates.

    Manages template definitions and provides methods to list,
    search, and launch templates.
    """

    def __init__(self):
        self._templates: Dict[str, WorkflowTemplate] = {}
        self._launches: Dict[str, TemplateLaunch] = {}
        self._register_default_templates()

    def _register_default_templates(self) -> None:
        """Register the default first-run templates."""

        # 1. Discovery Intake Template
        discovery_intake = WorkflowTemplate(
            template_id="discovery_intake",
            name="Discovery Intake",
            description="Submit a new business idea or opportunity for evaluation.",
            category=TemplateCategory.DISCOVERY,
            mode=TemplateMode.DRY_RUN_ONLY,
            complexity=TemplateComplexity.SIMPLE,
            inputs=[
                TemplateInput(
                    name="idea",
                    label="Business Idea",
                    input_type="textarea",
                    required=True,
                    placeholder="Describe your business idea, problem, or opportunity...",
                    help_text="Enter the core concept you want to explore",
                ),
                TemplateInput(
                    name="tags",
                    label="Tags",
                    input_type="text",
                    required=False,
                    placeholder="e.g., saas, b2b, automation",
                    help_text="Comma-separated tags for categorization",
                ),
                TemplateInput(
                    name="priority",
                    label="Priority",
                    input_type="select",
                    required=False,
                    default_value="medium",
                    options=["low", "medium", "high"],
                    help_text="How urgent is this opportunity?",
                ),
            ],
            steps=[
                TemplateStep(
                    step_id="s1",
                    name="Parse Input",
                    description="Extract structured data from the idea description",
                    action_type="validation",
                ),
                TemplateStep(
                    step_id="s2",
                    name="Score Opportunity",
                    description="Evaluate the opportunity using scoring criteria",
                    action_type="validation",
                ),
                TemplateStep(
                    step_id="s3",
                    name="Create Record",
                    description="Create opportunity record in the registry",
                    action_type="validation",
                ),
            ],
            tags=["discovery", "intake", "first-run"],
            icon="lightbulb",
            estimated_duration="< 30 seconds",
            prerequisites=["None - this template works immediately"],
        )

        # 2. Validation-First Opportunity Template
        validation_first = WorkflowTemplate(
            template_id="validation_first",
            name="Validation-First Opportunity",
            description="Research and validate an opportunity before committing resources.",
            category=TemplateCategory.RESEARCH,
            mode=TemplateMode.LIVE_CAPABLE,
            complexity=TemplateComplexity.MODERATE,
            inputs=[
                TemplateInput(
                    name="opportunity_id",
                    label="Opportunity ID",
                    input_type="text",
                    required=True,
                    placeholder="opp_...",
                    help_text="ID of an existing opportunity to validate",
                ),
                TemplateInput(
                    name="research_depth",
                    label="Research Depth",
                    input_type="select",
                    required=False,
                    default_value="standard",
                    options=["quick", "standard", "comprehensive"],
                    help_text="How thorough should the validation be?",
                ),
            ],
            steps=[
                TemplateStep(
                    step_id="s1",
                    name="Load Opportunity",
                    description="Fetch the opportunity record",
                    action_type="validation",
                ),
                TemplateStep(
                    step_id="s2",
                    name="Market Research",
                    description="Research the market landscape",
                    action_type="connector",
                    connector="tavily",
                    operation="search",
                    parameters_mapping={"opportunity_id": "query_context"},
                ),
                TemplateStep(
                    step_id="s3",
                    name="Update Status",
                    description="Update opportunity with research findings",
                    action_type="validation",
                ),
            ],
            tags=["validation", "research", "opportunity"],
            icon="search",
            estimated_duration="1-2 minutes",
            prerequisites=["Existing opportunity record", "Tavily credentials (for live mode)"],
            requires_live_credentials=True,
        )

        # 3. Research Scenario Template
        research_scenario = WorkflowTemplate(
            template_id="research_scenario",
            name="Research Scenario",
            description="Run market or competitor research on a topic.",
            category=TemplateCategory.RESEARCH,
            mode=TemplateMode.LIVE_CAPABLE,
            complexity=TemplateComplexity.SIMPLE,
            inputs=[
                TemplateInput(
                    name="query",
                    label="Research Query",
                    input_type="textarea",
                    required=True,
                    placeholder="What do you want to research?",
                    help_text="Enter your research question or topic",
                ),
                TemplateInput(
                    name="max_results",
                    label="Max Results",
                    input_type="number",
                    required=False,
                    default_value="10",
                    help_text="Maximum number of results to return",
                ),
            ],
            steps=[
                TemplateStep(
                    step_id="s1",
                    name="Execute Search",
                    description="Search for information using Tavily",
                    action_type="connector",
                    connector="tavily",
                    operation="search",
                    parameters_mapping={"query": "query", "max_results": "max_results"},
                ),
                TemplateStep(
                    step_id="s2",
                    name="Process Results",
                    description="Extract and format research findings",
                    action_type="validation",
                ),
            ],
            tags=["research", "search", "tavily"],
            icon="globe",
            estimated_duration="30 seconds - 1 minute",
            prerequisites=["Tavily API key for live mode"],
            requires_live_credentials=True,
        )

        # 4. Notification Test Template
        notification_test = WorkflowTemplate(
            template_id="notification_test",
            name="Notification Test",
            description="Test notification delivery via Telegram or Email.",
            category=TemplateCategory.NOTIFICATION,
            mode=TemplateMode.LIVE_CAPABLE,
            complexity=TemplateComplexity.SIMPLE,
            inputs=[
                TemplateInput(
                    name="channel",
                    label="Notification Channel",
                    input_type="select",
                    required=True,
                    default_value="telegram",
                    options=["telegram", "email"],
                    help_text="Which channel to test",
                ),
                TemplateInput(
                    name="message",
                    label="Test Message",
                    input_type="textarea",
                    required=True,
                    default_value="Test notification from Project Alpha",
                    placeholder="Your test message...",
                    help_text="Message to send",
                ),
                TemplateInput(
                    name="recipient",
                    label="Recipient",
                    input_type="text",
                    required=False,
                    placeholder="Optional: Override default recipient",
                    help_text="Leave blank to use default configured recipient",
                ),
            ],
            steps=[
                TemplateStep(
                    step_id="s1",
                    name="Validate Channel",
                    description="Check channel configuration",
                    action_type="validation",
                ),
                TemplateStep(
                    step_id="s2",
                    name="Send Notification",
                    description="Send the test message",
                    action_type="connector",
                    connector="telegram",  # Dynamic based on channel
                    operation="send_message",
                    parameters_mapping={"message": "text", "recipient": "chat_id"},
                    requires_approval=True,
                    skip_on_dry_run=True,
                ),
                TemplateStep(
                    step_id="s3",
                    name="Verify Delivery",
                    description="Confirm delivery status",
                    action_type="validation",
                ),
            ],
            tags=["notification", "telegram", "email", "test"],
            icon="bell",
            estimated_duration="< 30 seconds",
            prerequisites=[
                "Telegram: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID",
                "Email: SENDGRID_API_KEY, SENDGRID_FROM_EMAIL",
            ],
            requires_live_credentials=True,
        )

        # 5. CRM Update Template
        crm_update = WorkflowTemplate(
            template_id="crm_update",
            name="CRM Update",
            description="Create or update a contact in HubSpot CRM.",
            category=TemplateCategory.CRM,
            mode=TemplateMode.LIVE_CAPABLE,
            complexity=TemplateComplexity.MODERATE,
            inputs=[
                TemplateInput(
                    name="action",
                    label="Action",
                    input_type="select",
                    required=True,
                    default_value="create",
                    options=["create", "update"],
                    help_text="Create new contact or update existing",
                ),
                TemplateInput(
                    name="email",
                    label="Email",
                    input_type="email",
                    required=True,
                    placeholder="contact@example.com",
                    help_text="Contact email address",
                ),
                TemplateInput(
                    name="first_name",
                    label="First Name",
                    input_type="text",
                    required=False,
                    placeholder="John",
                ),
                TemplateInput(
                    name="last_name",
                    label="Last Name",
                    input_type="text",
                    required=False,
                    placeholder="Doe",
                ),
                TemplateInput(
                    name="company",
                    label="Company",
                    input_type="text",
                    required=False,
                    placeholder="Acme Inc",
                ),
            ],
            steps=[
                TemplateStep(
                    step_id="s1",
                    name="Validate Input",
                    description="Validate contact data",
                    action_type="validation",
                ),
                TemplateStep(
                    step_id="s2",
                    name="CRM Operation",
                    description="Create or update contact in HubSpot",
                    action_type="connector",
                    connector="hubspot",
                    operation="create_contact",  # Dynamic based on action
                    parameters_mapping={
                        "email": "email",
                        "first_name": "firstname",
                        "last_name": "lastname",
                        "company": "company",
                    },
                    requires_approval=True,
                    skip_on_dry_run=True,
                ),
                TemplateStep(
                    step_id="s3",
                    name="Confirm Result",
                    description="Verify CRM record was created/updated",
                    action_type="validation",
                ),
            ],
            tags=["crm", "hubspot", "contact"],
            icon="users",
            estimated_duration="< 30 seconds",
            prerequisites=["HUBSPOT_API_KEY for live mode"],
            requires_live_credentials=True,
        )

        # 6. Connector Health Check Template
        connector_health = WorkflowTemplate(
            template_id="connector_health",
            name="Connector Health Check",
            description="Check the health status of all configured connectors.",
            category=TemplateCategory.MAINTENANCE,
            mode=TemplateMode.READ_ONLY,
            complexity=TemplateComplexity.SIMPLE,
            inputs=[
                TemplateInput(
                    name="connector_filter",
                    label="Filter Connectors",
                    input_type="select",
                    required=False,
                    default_value="all",
                    options=["all", "telegram", "tavily", "sendgrid", "hubspot", "firecrawl"],
                    help_text="Check specific connector or all",
                ),
            ],
            steps=[
                TemplateStep(
                    step_id="s1",
                    name="Load Connectors",
                    description="Get list of configured connectors",
                    action_type="validation",
                ),
                TemplateStep(
                    step_id="s2",
                    name="Run Health Checks",
                    description="Execute health check on each connector",
                    action_type="validation",
                ),
                TemplateStep(
                    step_id="s3",
                    name="Generate Report",
                    description="Compile health check results",
                    action_type="validation",
                ),
            ],
            tags=["health", "maintenance", "connectors"],
            icon="activity",
            estimated_duration="< 30 seconds",
            prerequisites=["None - works with any configuration"],
        )

        # Register all templates
        for template in [
            discovery_intake,
            validation_first,
            research_scenario,
            notification_test,
            crm_update,
            connector_health,
        ]:
            self._templates[template.template_id] = template

    def register_template(self, template: WorkflowTemplate) -> None:
        """Register a new template."""
        self._templates[template.template_id] = template

    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        mode: Optional[TemplateMode] = None,
        complexity: Optional[TemplateComplexity] = None,
    ) -> List[WorkflowTemplate]:
        """List templates with optional filters."""
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.category == category]
        if mode:
            templates = [t for t in templates if t.mode == mode]
        if complexity:
            templates = [t for t in templates if t.complexity == complexity]

        return sorted(templates, key=lambda t: t.name)

    def search_templates(self, query: str) -> List[WorkflowTemplate]:
        """Search templates by name, description, or tags."""
        query_lower = query.lower()
        results = []

        for template in self._templates.values():
            if (
                query_lower in template.name.lower()
                or query_lower in template.description.lower()
                or any(query_lower in tag.lower() for tag in template.tags)
            ):
                results.append(template)

        return sorted(results, key=lambda t: t.name)

    def get_template_summary(self) -> Dict[str, Any]:
        """Get summary of available templates."""
        templates = list(self._templates.values())

        by_category = {}
        for category in TemplateCategory:
            count = len([t for t in templates if t.category == category])
            if count > 0:
                by_category[category.value] = count

        by_mode = {}
        for mode in TemplateMode:
            count = len([t for t in templates if t.mode == mode])
            if count > 0:
                by_mode[mode.value] = count

        by_complexity = {}
        for complexity in TemplateComplexity:
            count = len([t for t in templates if t.complexity == complexity])
            if count > 0:
                by_complexity[complexity.value] = count

        return {
            "total": len(templates),
            "by_category": by_category,
            "by_mode": by_mode,
            "by_complexity": by_complexity,
            "live_capable": len([t for t in templates if t.mode == TemplateMode.LIVE_CAPABLE]),
            "requires_credentials": len([t for t in templates if t.requires_live_credentials]),
        }

    def launch_template(
        self,
        template_id: str,
        inputs: Dict[str, Any],
        dry_run: bool = True,
        launched_by: str = "operator",
    ) -> Optional[TemplateLaunch]:
        """
        Launch a template with provided inputs.

        Returns a TemplateLaunch record that can be used to track execution.
        """
        template = self.get_template(template_id)
        if not template:
            return None

        # Validate required inputs
        for input_def in template.inputs:
            if input_def.required and input_def.name not in inputs:
                if not input_def.default_value:
                    return None  # Missing required input

        # Apply defaults
        final_inputs = {}
        for input_def in template.inputs:
            if input_def.name in inputs:
                final_inputs[input_def.name] = inputs[input_def.name]
            elif input_def.default_value:
                final_inputs[input_def.name] = input_def.default_value

        # Create launch record
        launch = TemplateLaunch(
            launch_id=f"launch_{uuid.uuid4().hex[:12]}",
            template_id=template_id,
            inputs=final_inputs,
            dry_run=dry_run,
            launched_by=launched_by,
            launched_at=datetime.now(timezone.utc).isoformat(),
            status="pending",
        )

        self._launches[launch.launch_id] = launch
        return launch

    def get_launch(self, launch_id: str) -> Optional[TemplateLaunch]:
        """Get a launch record by ID."""
        return self._launches.get(launch_id)

    def update_launch_status(
        self,
        launch_id: str,
        status: str,
        scenario_run_id: Optional[str] = None,
        job_id: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[TemplateLaunch]:
        """Update the status of a launch."""
        launch = self._launches.get(launch_id)
        if not launch:
            return None

        launch.status = status
        if scenario_run_id:
            launch.scenario_run_id = scenario_run_id
        if job_id:
            launch.job_id = job_id
        if result:
            launch.result = result

        return launch

    def list_launches(
        self,
        template_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[TemplateLaunch]:
        """List template launches with optional filters."""
        launches = list(self._launches.values())

        if template_id:
            launches = [l for l in launches if l.template_id == template_id]
        if status:
            launches = [l for l in launches if l.status == status]

        # Sort by launch time, most recent first
        launches.sort(key=lambda l: l.launched_at, reverse=True)

        return launches[:limit]


# Singleton instance
_template_registry: Optional[TemplateRegistry] = None


def get_template_registry() -> TemplateRegistry:
    """Get the global template registry."""
    global _template_registry
    if _template_registry is None:
        _template_registry = TemplateRegistry()
    return _template_registry


# Convenience functions
def list_templates(
    category: Optional[str] = None,
    mode: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List templates as dictionaries."""
    registry = get_template_registry()

    category_enum = TemplateCategory(category) if category else None
    mode_enum = TemplateMode(mode) if mode else None

    templates = registry.list_templates(category=category_enum, mode=mode_enum)
    return [t.to_dict() for t in templates]


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Get a template by ID as dictionary."""
    registry = get_template_registry()
    template = registry.get_template(template_id)
    return template.to_dict() if template else None


def launch_template(
    template_id: str,
    inputs: Dict[str, Any],
    dry_run: bool = True,
    launched_by: str = "operator",
) -> Optional[Dict[str, Any]]:
    """Launch a template and return the launch record."""
    registry = get_template_registry()
    launch = registry.launch_template(
        template_id=template_id,
        inputs=inputs,
        dry_run=dry_run,
        launched_by=launched_by,
    )
    return launch.to_dict() if launch else None
