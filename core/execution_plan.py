"""
Execution Plan - Structured execution plans that include skills, commands, and agents.

Execution plans bridge the skill intelligence layer with the workflow execution engine,
providing structured plans that include:
- Selected skills, commands, and specialized agents
- Execution paths and handlers
- Approval status and policy decisions
- Integration with real workflow modules
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from enum import Enum

from .skill_selector import SelectionResult, ToolRecommendation
from .skill_policies import PolicyResult, PolicyDecision
from .skill_composer import ComposedWorkflow, CompositionStep


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ExecutionDomain(Enum):
    """
    Domain categories for execution routing.

    Project Alpha supports multiple business and operational domains,
    enabling domain-neutral execution planning and skill selection.
    """
    # Knowledge & Strategy
    RESEARCH = "research"                    # Market research, competitive intelligence, data gathering
    STRATEGY = "strategy"                    # Strategic planning, business strategy, decision analysis
    PLANNING = "planning"                    # Project planning, roadmapping, resource allocation

    # Product & Engineering
    PRODUCT = "product"                      # Product development, feature planning, requirements
    ENGINEERING = "engineering"              # Software development, technical implementation
    VALIDATION = "validation"                # Testing, QA, validation, verification

    # Operations & Execution
    OPERATIONS = "operations"                # Day-to-day operations, process execution
    AUTOMATION = "automation"                # Workflow automation, process automation
    INTERNAL_ADMIN = "internal_admin"        # Internal administration, housekeeping

    # Finance & Compliance
    FINANCE = "finance"                      # Financial planning, budgeting, accounting
    COMPLIANCE = "compliance"                # Legal compliance, regulatory, auditing

    # Customer & Growth
    GROWTH = "growth"                        # Business growth, expansion, scaling
    CUSTOMER_SUPPORT = "customer_support"    # Customer service, support, success

    # Content & Communication
    CONTENT = "content"                      # Content creation, documentation, knowledge management

    # Fallback
    UNKNOWN = "unknown"                      # Unclassified or multi-domain


class ExecutionStatus(Enum):
    """Status of execution plan."""
    PENDING = "pending"
    APPROVED = "approved"
    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SkillBundle:
    """Bundle of selected skills, commands, and agents for execution."""
    skills: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    specialized_agents: List[str] = field(default_factory=list)

    # Policy evaluation results
    policy_results: List[PolicyResult] = field(default_factory=list)

    # Aggregated status
    has_blocked_items: bool = False
    requires_approval: bool = False
    approval_items: List[str] = field(default_factory=list)
    auto_allowed_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "skills": self.skills,
            "commands": self.commands,
            "specialized_agents": self.specialized_agents,
            "has_blocked_items": self.has_blocked_items,
            "requires_approval": self.requires_approval,
            "approval_items": self.approval_items,
            "auto_allowed_items": self.auto_allowed_items,
            "policy_decisions": [
                {
                    "skill": pr.skill_name,
                    "decision": pr.decision.value,
                    "reason": pr.reason
                }
                for pr in self.policy_results
            ]
        }


@dataclass
class ExecutionStep:
    """A single step in an execution plan."""
    step_id: str
    description: str
    domain: ExecutionDomain

    # Skills involved in this step
    skills: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    specialized_agent: Optional[str] = None

    # Execution target
    handler_module: Optional[str] = None  # e.g., "stage_workflows"
    handler_method: Optional[str] = None  # e.g., "execute_validating_task"
    department_agent: Optional[str] = None  # e.g., "dept_research"

    # Status
    status: ExecutionStatus = ExecutionStatus.PENDING
    requires_approval: bool = False

    # Results
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "description": self.description,
            "domain": self.domain.value,
            "skills": self.skills,
            "commands": self.commands,
            "specialized_agent": self.specialized_agent,
            "handler_module": self.handler_module,
            "handler_method": self.handler_method,
            "department_agent": self.department_agent,
            "status": self.status.value,
            "requires_approval": self.requires_approval,
            "output": self.output,
            "error": self.error,
        }


@dataclass
class ExecutionPlan:
    """
    Structured execution plan for hierarchy-driven requests.

    Combines skill selection, policy evaluation, and workflow routing
    into a single actionable plan.
    """
    plan_id: str = field(default_factory=lambda: f"plan_{_utc_now().strftime('%Y%m%d%H%M%S%f')}")

    # Request context
    objective: str = ""
    role_id: str = "principal_human"
    business_id: Optional[str] = None
    stage: Optional[str] = None

    # Domain classification
    primary_domain: ExecutionDomain = ExecutionDomain.UNKNOWN

    # Skill bundle
    skill_bundle: Optional[SkillBundle] = None

    # Execution steps
    steps: List[ExecutionStep] = field(default_factory=list)

    # Composed workflow (if available)
    composed_workflow: Optional[ComposedWorkflow] = None

    # Status
    status: ExecutionStatus = ExecutionStatus.PENDING
    requires_approval: bool = False
    approval_status: Optional[str] = None  # "pending", "approved", "denied"

    # Routing info
    routing_decision: Optional[str] = None  # e.g., "department_execution"
    execution_path: List[str] = field(default_factory=list)

    # Timing
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Results
    success: bool = False
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "objective": self.objective,
            "role_id": self.role_id,
            "business_id": self.business_id,
            "stage": self.stage,
            "primary_domain": self.primary_domain.value,
            "skill_bundle": self.skill_bundle.to_dict() if self.skill_bundle else None,
            "steps": [s.to_dict() for s in self.steps],
            "composed_workflow": self.composed_workflow.to_dict() if self.composed_workflow else None,
            "status": self.status.value,
            "requires_approval": self.requires_approval,
            "approval_status": self.approval_status,
            "routing_decision": self.routing_decision,
            "execution_path": self.execution_path,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "success": self.success,
            "outputs": self.outputs,
            "errors": self.errors,
        }

    def add_step(self, step: ExecutionStep) -> None:
        """Add an execution step."""
        self.steps.append(step)
        if step.requires_approval:
            self.requires_approval = True

    def mark_started(self) -> None:
        """Mark the plan as started."""
        self.status = ExecutionStatus.EXECUTING
        self.started_at = _utc_now().isoformat()

    def mark_completed(self, success: bool = True) -> None:
        """Mark the plan as completed."""
        self.status = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED
        self.completed_at = _utc_now().isoformat()
        self.success = success

    def mark_blocked(self, reason: str) -> None:
        """Mark the plan as blocked."""
        self.status = ExecutionStatus.BLOCKED
        self.errors.append(reason)


class ExecutionPlanBuilder:
    """
    Builder for creating execution plans from skill selections and workflows.
    """

    # Domain detection keywords
    DOMAIN_KEYWORDS = {
        ExecutionDomain.RESEARCH: ["research", "discover", "analyze", "study", "investigate", "explore"],
        ExecutionDomain.PLANNING: ["plan", "strategy", "roadmap", "design", "architect", "schedule"],
        ExecutionDomain.PRODUCT: ["build", "develop", "product", "feature", "implement", "code"],
        ExecutionDomain.OPERATIONS: ["operate", "maintain", "monitor", "deploy", "infrastructure"],
        ExecutionDomain.GROWTH: ["market", "growth", "acquire", "scale", "advertise", "campaign"],
        ExecutionDomain.AUTOMATION: ["automate", "workflow", "integrate", "optimize", "pipeline"],
        ExecutionDomain.VALIDATION: ["validate", "test", "verify", "quality", "qa", "check"],
        ExecutionDomain.CONTENT: ["content", "write", "document", "blog", "copy", "message"],
    }

    # Domain to department mapping
    DOMAIN_TO_DEPARTMENT = {
        ExecutionDomain.RESEARCH: "dept_research",
        ExecutionDomain.PLANNING: "dept_planning",
        ExecutionDomain.PRODUCT: "dept_product",
        ExecutionDomain.OPERATIONS: "dept_operations",
        ExecutionDomain.GROWTH: "dept_growth",
        ExecutionDomain.AUTOMATION: "dept_automation",
        ExecutionDomain.VALIDATION: "dept_validation",
        ExecutionDomain.CONTENT: "dept_content",
    }

    # Domain to handler mapping
    DOMAIN_TO_HANDLER = {
        ExecutionDomain.RESEARCH: ("stage_workflows", "execute_discovered_task"),
        ExecutionDomain.PLANNING: ("planning_engine", "execute"),
        ExecutionDomain.PRODUCT: ("stage_workflows", "execute_building_task"),
        ExecutionDomain.OPERATIONS: ("stage_workflows", "execute_operating_task"),
        ExecutionDomain.GROWTH: ("stage_workflows", "execute_scaling_task"),
        ExecutionDomain.AUTOMATION: ("workflow_orchestrator", "execute_stage_workflow"),
        ExecutionDomain.VALIDATION: ("stage_workflows", "execute_validating_task"),
        ExecutionDomain.CONTENT: ("stage_workflows", "execute_building_task"),
    }

    def __init__(self):
        """Initialize the builder."""
        pass

    def detect_domain(self, objective: str) -> ExecutionDomain:
        """Detect the primary domain from the objective."""
        objective_lower = objective.lower()

        domain_scores: Dict[ExecutionDomain, int] = {}

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in objective_lower)
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores, key=domain_scores.get)

        return ExecutionDomain.UNKNOWN

    def build_from_selection(
        self,
        objective: str,
        selection_result: SelectionResult,
        role_id: str = "principal_human",
        business_id: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> ExecutionPlan:
        """
        Build an execution plan from a skill selection result.

        Args:
            objective: The objective to accomplish.
            selection_result: Result from skill selection.
            role_id: Role making the request.
            business_id: Business context.
            stage: Lifecycle stage.

        Returns:
            ExecutionPlan ready for execution.
        """
        # Detect domain
        domain = self.detect_domain(objective)

        # Create skill bundle from recommendations
        skill_bundle = self._create_skill_bundle(selection_result, role_id)

        # Create execution plan
        plan = ExecutionPlan(
            objective=objective,
            role_id=role_id,
            business_id=business_id,
            stage=stage,
            primary_domain=domain,
            skill_bundle=skill_bundle,
            requires_approval=skill_bundle.requires_approval,
        )

        # Add execution step
        step = self._create_execution_step(
            objective=objective,
            domain=domain,
            skill_bundle=skill_bundle,
            stage=stage,
        )
        plan.add_step(step)

        # Set routing
        plan.execution_path.append("chief_orchestrator")
        if domain != ExecutionDomain.UNKNOWN:
            plan.execution_path.append(self.DOMAIN_TO_DEPARTMENT.get(domain, "unknown"))

        return plan

    def build_from_workflow(
        self,
        objective: str,
        workflow: ComposedWorkflow,
        role_id: str = "principal_human",
        business_id: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> ExecutionPlan:
        """
        Build an execution plan from a composed workflow.

        Args:
            objective: The objective.
            workflow: Composed workflow from skill composer.
            role_id: Role making the request.
            business_id: Business context.
            stage: Lifecycle stage.

        Returns:
            ExecutionPlan with workflow steps.
        """
        # Detect domain
        domain = self.detect_domain(objective)

        # Create plan
        plan = ExecutionPlan(
            objective=objective,
            role_id=role_id,
            business_id=business_id,
            stage=stage,
            primary_domain=domain,
            composed_workflow=workflow,
            requires_approval=workflow.requires_any_approval,
        )

        # Create steps from workflow
        for i, workflow_step in enumerate(workflow.steps):
            step = ExecutionStep(
                step_id=f"step_{i+1}_{workflow_step.skill_name}",
                description=workflow_step.description or f"Execute {workflow_step.skill_name}",
                domain=self._skill_to_domain(workflow_step.skill_name),
                skills=[workflow_step.skill_name],
                requires_approval=workflow_step.policy_result.decision == PolicyDecision.REQUIRES_APPROVAL if workflow_step.policy_result else False,
                status=ExecutionStatus.BLOCKED if workflow_step.policy_result and workflow_step.policy_result.is_blocked else ExecutionStatus.PENDING,
            )

            # Set handler
            handler = self.DOMAIN_TO_HANDLER.get(step.domain)
            if handler:
                step.handler_module, step.handler_method = handler

            plan.add_step(step)

        plan.execution_path.append("chief_orchestrator")
        plan.execution_path.append("skill_composer")

        return plan

    def _create_skill_bundle(
        self,
        selection_result: SelectionResult,
        role_id: str,
    ) -> SkillBundle:
        """Create a skill bundle from selection result."""
        bundle = SkillBundle()

        # Import ToolType here to avoid circular dependency
        from .skill_selector import ToolType

        for rec in selection_result.recommendations:
            # Import here to avoid circular dependency
            from .skill_policies import evaluate_skill_policy, PolicyDecision

            # Evaluate policy for each skill
            policy_result = evaluate_skill_policy(rec.name, role_id)
            bundle.policy_results.append(policy_result)

            # Use tool_type attribute instead of source
            if rec.tool_type == ToolType.SKILL:
                bundle.skills.append(rec.name)
            elif rec.tool_type == ToolType.COMMAND:
                bundle.commands.append(rec.name)
            elif rec.tool_type == ToolType.AGENT:
                bundle.specialized_agents.append(rec.name)

            # Track policy decisions
            if policy_result.decision == PolicyDecision.BLOCKED:
                bundle.has_blocked_items = True
            elif policy_result.decision == PolicyDecision.REQUIRES_APPROVAL:
                bundle.requires_approval = True
                bundle.approval_items.append(rec.name)
            else:
                bundle.auto_allowed_items.append(rec.name)

        return bundle

    def _create_execution_step(
        self,
        objective: str,
        domain: ExecutionDomain,
        skill_bundle: SkillBundle,
        stage: Optional[str],
    ) -> ExecutionStep:
        """Create an execution step from a skill bundle."""
        step = ExecutionStep(
            step_id=f"step_1_{domain.value}",
            description=objective[:100],
            domain=domain,
            skills=skill_bundle.skills,
            commands=skill_bundle.commands,
            specialized_agent=skill_bundle.specialized_agents[0] if skill_bundle.specialized_agents else None,
            department_agent=self.DOMAIN_TO_DEPARTMENT.get(domain),
            requires_approval=skill_bundle.requires_approval,
        )

        # Set handler based on stage if available
        if stage:
            step.handler_module = "stage_workflows"
            step.handler_method = f"execute_{stage.lower()}_task"
        else:
            handler = self.DOMAIN_TO_HANDLER.get(domain)
            if handler:
                step.handler_module, step.handler_method = handler

        return step

    def _skill_to_domain(self, skill_name: str) -> ExecutionDomain:
        """Map a skill name to a domain."""
        skill_lower = skill_name.lower()

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in skill_lower for kw in keywords):
                return domain

        return ExecutionDomain.UNKNOWN


# Singleton builder
_plan_builder: Optional[ExecutionPlanBuilder] = None


def get_plan_builder() -> ExecutionPlanBuilder:
    """Get the global execution plan builder."""
    global _plan_builder
    if _plan_builder is None:
        _plan_builder = ExecutionPlanBuilder()
    return _plan_builder


def build_execution_plan(
    objective: str,
    selection_result: Optional[SelectionResult] = None,
    workflow: Optional[ComposedWorkflow] = None,
    role_id: str = "principal_human",
    business_id: Optional[str] = None,
    stage: Optional[str] = None,
) -> ExecutionPlan:
    """
    Build an execution plan from skills or workflow.

    Args:
        objective: The objective to accomplish.
        selection_result: Skill selection result (optional).
        workflow: Composed workflow (optional).
        role_id: Role making the request.
        business_id: Business context.
        stage: Lifecycle stage.

    Returns:
        ExecutionPlan ready for execution.
    """
    builder = get_plan_builder()

    if workflow:
        return builder.build_from_workflow(
            objective=objective,
            workflow=workflow,
            role_id=role_id,
            business_id=business_id,
            stage=stage,
        )
    elif selection_result:
        return builder.build_from_selection(
            objective=objective,
            selection_result=selection_result,
            role_id=role_id,
            business_id=business_id,
            stage=stage,
        )
    else:
        # Create minimal plan without skills
        return ExecutionPlan(
            objective=objective,
            role_id=role_id,
            business_id=business_id,
            stage=stage,
            primary_domain=builder.detect_domain(objective),
        )
