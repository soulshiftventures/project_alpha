"""
Chief Orchestrator for Project Alpha
Central coordinator under the principal, routes requests through the hierarchy
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from core.agent_contracts import (
    AgentRequest, AgentResponse, RequestStatus, AgentLayer,
    DecisionRecord, create_request, create_response
)
from core.agent_registry import AgentRegistry, AgentDefinition
from core.hierarchy_definitions import create_default_hierarchy, get_agents_for_capability
from core.event_logger import EventLogger, EventType, EventSeverity
from core.approval_manager import ApprovalManager, ApprovalClass
from core.council_manager import CouncilManager
from core.decision_board import DecisionBoard

# Skill Intelligence Layer imports
from core.skill_selector import SkillSelector, SelectionResult, get_skill_selector
from core.skill_policies import evaluate_skill_policy, PolicyDecision
from core.skill_composer import SkillComposer, compose_workflow, get_skill_composer
from core.role_skill_mappings import get_role_mapping, RoleSkillMapping
from core.execution_plan import (
    ExecutionPlan, ExecutionPlanBuilder, ExecutionStep,
    ExecutionDomain, ExecutionStatus, SkillBundle,
    get_plan_builder, build_execution_plan
)
from core.execution_domains import classify_goal_domain, get_domain_metadata

# Runtime Abstraction Layer imports
from core.runtime_manager import (
    RuntimeManager, RuntimeConfig, RuntimeResult,
    BackendSelectionStrategy, get_runtime_manager, execute_plan
)
from core.execution_backends import BackendType, JobStatus
from core.job_dispatcher import DispatchOptions, DispatchStrategy, DispatchPriority


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class RoutingDecision:
    """Enumeration of routing decisions."""
    DIRECT_EXECUTION = "direct_execution"
    COUNCIL_ADVICE = "council_advice"
    BOARD_DECISION = "board_decision"
    C_SUITE_DELEGATION = "c_suite_delegation"
    DEPARTMENT_EXECUTION = "department_execution"
    REQUIRES_APPROVAL = "requires_approval"
    BLOCKED = "blocked"


@dataclass
class OrchestrationResult:
    """Result of orchestrating a request through the hierarchy."""
    request_id: str
    routing: str  # RoutingDecision value
    success: bool

    # Response from handling agent
    response: Optional[AgentResponse] = None

    # Decision tracking
    decision_record: Optional[DecisionRecord] = None
    approval_record: Optional[Dict[str, Any]] = None

    # Execution details
    executed_by: List[str] = field(default_factory=list)
    execution_path: List[str] = field(default_factory=list)

    # Skill-aware execution plan
    execution_plan: Optional[ExecutionPlan] = None

    # Skill Intelligence Layer details
    selected_skills: List[str] = field(default_factory=list)
    selected_commands: List[str] = field(default_factory=list)
    selected_agents: List[str] = field(default_factory=list)
    skill_approval_required: bool = False
    skill_policy_decisions: List[Dict[str, Any]] = field(default_factory=list)

    # Runtime Abstraction Layer details
    runtime_result: Optional[Dict[str, Any]] = None
    backend_used: Optional[str] = None
    job_id: Optional[str] = None

    # Metadata
    started_at: str = field(default_factory=lambda: _utc_now().isoformat())
    completed_at: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "routing": self.routing,
            "success": self.success,
            "response": self.response.to_dict() if self.response else None,
            "decision_record": self.decision_record.to_dict() if self.decision_record else None,
            "approval_record": self.approval_record,
            "executed_by": self.executed_by,
            "execution_path": self.execution_path,
            "execution_plan": self.execution_plan.to_dict() if self.execution_plan else None,
            "selected_skills": self.selected_skills,
            "selected_commands": self.selected_commands,
            "selected_agents": self.selected_agents,
            "skill_approval_required": self.skill_approval_required,
            "skill_policy_decisions": self.skill_policy_decisions,
            "runtime_result": self.runtime_result,
            "backend_used": self.backend_used,
            "job_id": self.job_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "errors": self.errors
        }


class ChiefOrchestrator:
    """
    Central coordinator for the agent hierarchy.

    Responsibilities:
    - Route requests to appropriate layer/agent
    - Coordinate council, board, and c-suite
    - Handle approval workflows
    - Delegate to execution layer
    - Track orchestration results
    """

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        event_logger: Optional[EventLogger] = None,
        approval_manager: Optional[ApprovalManager] = None,
        council_manager: Optional[CouncilManager] = None,
        decision_board: Optional[DecisionBoard] = None
    ):
        """
        Initialize the chief orchestrator.

        Args:
            registry: Agent registry (creates default if not provided)
            event_logger: Event logger (creates new if not provided)
            approval_manager: Approval manager (creates new if not provided)
            council_manager: Council manager (creates new if not provided)
            decision_board: Decision board (creates new if not provided)
        """
        # Initialize registry
        self._registry = registry or create_default_hierarchy()

        # Initialize components
        self._logger = event_logger or EventLogger()
        self._approval = approval_manager or ApprovalManager()
        self._council = council_manager or CouncilManager(self._registry)
        self._board = decision_board or DecisionBoard(self._registry)

        # Ensure council and board have registry
        self._council.set_registry(self._registry)
        self._board.set_registry(self._registry)

        # Orchestration history
        self._history: List[OrchestrationResult] = []

        # Active orchestrations
        self._active: Dict[str, OrchestrationResult] = {}

        # Skill intelligence layer
        self._skill_selector: Optional[SkillSelector] = None
        self._skill_composer: Optional[SkillComposer] = None
        self._skills_loaded = False
        self._plan_builder: Optional[ExecutionPlanBuilder] = None

        # Workflow modules (lazy loaded)
        self._stage_workflows = None
        self._workflow_orchestrator = None

        # Runtime Abstraction Layer
        self._runtime_manager: Optional[RuntimeManager] = None
        self._runtime_initialized = False

    def orchestrate(
        self,
        objective: str,
        business: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        requester: str = "principal",
        priority: str = "medium"
    ) -> OrchestrationResult:
        """
        Main entry point: orchestrate a goal/request through the hierarchy.

        Now includes skill-aware orchestration that:
        - Selects relevant skills, commands, and agents
        - Evaluates policies for each selected item
        - Creates structured execution plans
        - Routes to appropriate handlers with skill context

        Args:
            objective: What needs to be accomplished
            business: Business context (optional)
            context: Additional context
            requester: Who is making the request
            priority: Request priority

        Returns:
            OrchestrationResult with full details including skill selections
        """
        # Create request
        request = create_request(
            requester=requester,
            target_agent="chief_orchestrator",
            objective=objective,
            business_id=business.get("id") if business else None,
            context=context or {},
            priority=priority
        )

        # Initialize result
        result = OrchestrationResult(
            request_id=request.request_id,
            routing="",
            success=False,
            execution_path=["chief_orchestrator"]
        )
        self._active[request.request_id] = result

        # Log receipt
        self._logger.log_request_received(
            request_id=request.request_id,
            agent_id="chief_orchestrator",
            objective=objective
        )

        try:
            # Step 1: Skill-aware selection
            stage = business.get("stage") if business else None
            role_id = self._map_requester_to_role(requester)

            execution_plan = self._create_skill_aware_execution_plan(
                request=request,
                objective=objective,
                business=business,
                role_id=role_id,
                result=result
            )
            result.execution_plan = execution_plan

            # Step 2: Check approval (including skill-based approval)
            classification, approval_record = self._check_approval_with_skills(
                request, business, execution_plan
            )
            result.approval_record = approval_record.to_dict() if approval_record else None

            if classification == ApprovalClass.BLOCKED:
                result.routing = RoutingDecision.BLOCKED
                result.errors.append("Request blocked by approval policy")
                if execution_plan:
                    execution_plan.mark_blocked("Blocked by approval policy")
                result.response = create_response(
                    request_id=request.request_id,
                    responder="chief_orchestrator",
                    status=RequestStatus.REJECTED,
                    errors=["Request blocked by policy"]
                )
                return self._finalize(result)

            if classification == ApprovalClass.REQUIRES_APPROVAL:
                result.routing = RoutingDecision.REQUIRES_APPROVAL
                if execution_plan:
                    execution_plan.status = ExecutionStatus.AWAITING_APPROVAL
                result.response = create_response(
                    request_id=request.request_id,
                    responder="chief_orchestrator",
                    status=RequestStatus.AWAITING_APPROVAL,
                    result={"approval_record_id": approval_record.record_id if approval_record else None}
                )
                return self._finalize(result)

            # Step 3: Determine routing
            routing = self._determine_routing(request, business)
            result.routing = routing
            if execution_plan:
                execution_plan.routing_decision = routing

            # Step 4: Execute based on routing (now skill-aware)
            if routing == "DISCOVERY_MODE":
                result = self._handle_discovery_mode(request, business, result)

            elif routing == RoutingDecision.DIRECT_EXECUTION:
                result = self._handle_direct_execution(request, business, result)

            elif routing == RoutingDecision.COUNCIL_ADVICE:
                result = self._handle_council_advice(request, business, result)

            elif routing == RoutingDecision.BOARD_DECISION:
                result = self._handle_board_decision(request, business, result)

            elif routing == RoutingDecision.C_SUITE_DELEGATION:
                result = self._handle_csuite_delegation(request, business, result)

            elif routing == RoutingDecision.DEPARTMENT_EXECUTION:
                result = self._handle_skill_aware_department_execution(
                    request, business, execution_plan, result
                )

        except Exception as e:
            result.errors.append(str(e))
            self._logger.log_error(
                message=f"Orchestration error: {str(e)}",
                error=str(e),
                request_id=request.request_id,
                agent_id="chief_orchestrator"
            )

        return self._finalize(result)

    def _map_requester_to_role(self, requester: str) -> str:
        """Map requester to a role ID."""
        role_mapping = {
            "principal": "principal_human",
            "ceo": "ceo",
            "coo": "coo",
            "cfo": "cfo",
            "cto": "cto",
            "cmo": "cmo",
        }
        return role_mapping.get(requester, "principal_human")

    def _create_skill_aware_execution_plan(
        self,
        request: AgentRequest,
        objective: str,
        business: Optional[Dict[str, Any]],
        role_id: str,
        result: OrchestrationResult
    ) -> Optional[ExecutionPlan]:
        """
        Create a skill-aware execution plan with domain classification.

        Classifies the goal into an execution domain, then selects relevant
        skills and creates a structured plan.
        """
        self._ensure_skills_loaded()

        if not self._skill_selector:
            return None

        # Classify goal into execution domain
        domain_context = {
            "role": role_id,
            "business_id": business.get("id") if business else None,
            "stage": business.get("stage") if business else None,
        }
        classified_domain = classify_goal_domain(objective, domain_context)

        # Log domain classification
        self._logger.log(
            event_type=EventType.REQUEST_ROUTED,
            message=f"Goal classified as {classified_domain.value} domain",
            severity=EventSeverity.INFO,
            agent_id="chief_orchestrator",
            request_id=request.request_id,
            details={
                "objective": objective[:100],
                "domain": classified_domain.value,
                "domain_metadata": get_domain_metadata(classified_domain).to_dict()
            }
        )

        # Select skills for the task (domain-aware in future enhancement)
        selection_result = self._skill_selector.select(
            objective,
            max_recommendations=5
        )

        # Populate result with selections
        from .skill_selector import ToolType
        for rec in selection_result.recommendations:
            if rec.tool_type == ToolType.SKILL:
                result.selected_skills.append(rec.name)
            elif rec.tool_type == ToolType.COMMAND:
                result.selected_commands.append(rec.name)
            elif rec.tool_type == ToolType.AGENT:
                result.selected_agents.append(rec.name)

        # Log skill selection
        self._logger.log_skills_selected(
            request_id=request.request_id,
            agent_id="chief_orchestrator",
            skills=result.selected_skills,
            commands=result.selected_commands,
            specialized_agents=result.selected_agents,
            confidence=selection_result.confidence
        )

        # Evaluate policies for each skill
        for skill in result.selected_skills:
            policy_result = evaluate_skill_policy(skill, role_id)
            result.skill_policy_decisions.append({
                "skill": skill,
                "decision": policy_result.decision.value,
                "reason": policy_result.reason
            })

            # Log policy evaluation
            self._logger.log_skill_policy_evaluated(
                request_id=request.request_id,
                skill_name=skill,
                role_id=role_id,
                decision=policy_result.decision.value,
                reason=policy_result.reason
            )

            if policy_result.decision == PolicyDecision.REQUIRES_APPROVAL:
                result.skill_approval_required = True
                self._logger.log_skill_approval_required(
                    request_id=request.request_id,
                    skill_name=skill,
                    role_id=role_id,
                    approver=policy_result.requires_approval_from or "principal_human"
                )
            elif policy_result.decision == PolicyDecision.BLOCKED:
                self._logger.log_skill_blocked(
                    request_id=request.request_id,
                    skill_name=skill,
                    role_id=role_id,
                    reason=policy_result.reason
                )

        # Build execution plan
        stage = business.get("stage") if business else None
        execution_plan = build_execution_plan(
            objective=objective,
            selection_result=selection_result,
            role_id=role_id,
            business_id=business.get("id") if business else None,
            stage=stage,
        )

        # Log plan creation
        skill_count = len(result.selected_skills) + len(result.selected_commands) + len(result.selected_agents)
        self._logger.log_execution_plan_created(
            request_id=request.request_id,
            plan_id=execution_plan.plan_id,
            objective=objective,
            domain=execution_plan.primary_domain.value,
            skill_count=skill_count,
            step_count=len(execution_plan.steps),
            requires_approval=execution_plan.requires_approval
        )

        return execution_plan

    def _check_approval_with_skills(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        execution_plan: Optional[ExecutionPlan]
    ) -> Tuple[ApprovalClass, Any]:
        """Check approval considering skill policies."""
        # First check standard approval
        context = {
            "layer": "executive",
            "stage": business.get("stage") if business else None
        }

        base_classification, approval_record = self._approval.check_and_process(
            request=request,
            action=f"orchestrate_{request.objective[:50]}",
            confidence=0.8,
            context=context
        )

        # If already blocked or requires approval, return that
        if base_classification != ApprovalClass.AUTO_ALLOWED:
            return base_classification, approval_record

        # Check if skill bundle requires approval
        if execution_plan and execution_plan.requires_approval:
            return ApprovalClass.REQUIRES_APPROVAL, approval_record

        return base_classification, approval_record

    def _check_approval(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]]
    ) -> Tuple[ApprovalClass, Any]:
        """Check if request requires approval."""
        context = {
            "layer": "executive",
            "stage": business.get("stage") if business else None
        }

        return self._approval.check_and_process(
            request=request,
            action=f"orchestrate_{request.objective[:50]}",
            confidence=0.8,  # High confidence for orchestrator
            context=context
        )

    def _determine_routing(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]]
    ) -> str:
        """
        Determine where to route the request.

        Routing logic:
        - Discovery mode (idea/opportunity evaluation) -> Discovery pipeline
        - Strategic/high-level objectives -> Council then Board
        - Operational requests -> C-Suite delegation
        - Task execution -> Department execution
        - Simple queries -> Direct execution
        """
        objective = request.objective.lower()
        priority = request.priority

        # Discovery mode detection
        # Use more specific phrases to avoid false positives
        discovery_keywords = [
            "business idea", "business opportunity", "evaluate opportunity",
            "new business", "what if we", "should we build",
            "explore opportunity", "potential business", "evaluate idea",
            "i have an idea", "rough idea", "opportunity space"
        ]
        if any(kw in objective for kw in discovery_keywords):
            return "DISCOVERY_MODE"

        # Critical priority always goes to board
        if priority == "critical":
            return RoutingDecision.BOARD_DECISION

        # Strategic keywords -> Council advice first
        strategic_keywords = [
            "strategy", "direction", "pivot", "major", "significant",
            "restructure", "transform", "evaluate", "assess"
        ]
        if any(kw in objective for kw in strategic_keywords):
            return RoutingDecision.COUNCIL_ADVICE

        # Decision keywords -> Board
        decision_keywords = [
            "decide", "choose", "select", "approve", "reject",
            "conflict", "resolve", "vote"
        ]
        if any(kw in objective for kw in decision_keywords):
            return RoutingDecision.BOARD_DECISION

        # Execution/operational keywords -> C-Suite or Department
        execution_keywords = [
            "execute", "run", "process", "build", "create",
            "analyze", "research", "plan", "validate"
        ]
        if any(kw in objective for kw in execution_keywords):
            # Check if we can route to specific department
            capability_match = self._find_capability_match(objective)
            if capability_match:
                return RoutingDecision.DEPARTMENT_EXECUTION
            else:
                return RoutingDecision.C_SUITE_DELEGATION

        # Stage-based routing
        if business:
            stage = business.get("stage", "")
            if stage in ["DISCOVERED", "VALIDATING"]:
                # Early stages need more strategic input
                return RoutingDecision.COUNCIL_ADVICE
            elif stage in ["BUILDING", "SCALING"]:
                # Active execution stages
                return RoutingDecision.C_SUITE_DELEGATION
            elif stage in ["OPERATING", "OPTIMIZING"]:
                # Operational stages
                return RoutingDecision.DEPARTMENT_EXECUTION

        # Default to C-Suite delegation
        return RoutingDecision.C_SUITE_DELEGATION

    def _find_capability_match(self, objective: str) -> Optional[str]:
        """Find a capability that matches the objective."""
        capability_keywords = {
            "research": "market_research",
            "plan": "strategic_planning",
            "build": "product_development",
            "market": "marketing_campaigns",
            "validate": "validation_testing",
            "automat": "process_automation"
        }

        for keyword, capability in capability_keywords.items():
            if keyword in objective.lower():
                agents = get_agents_for_capability(capability)
                if agents:
                    return capability
        return None

    def _handle_discovery_mode(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        result: OrchestrationResult
    ) -> OrchestrationResult:
        """
        Handle discovery-mode requests for business opportunity evaluation.

        Routes request through discovery pipeline to evaluate and recommend
        opportunities from rough ideas, problems, or curiosities.

        Args:
            request: Agent request
            business: Business context
            result: Orchestration result to update

        Returns:
            Updated orchestration result
        """
        from core.discovery_pipeline import process_discovery_input
        from core.discovery_models import OperatorConstraints
        from core.opportunity_registry import OpportunityRegistry
        from core.state_store import get_state_store

        self._logger.log_event(
            event_type=EventType.GENERAL,
            severity=EventSeverity.INFO,
            message=f"Discovery mode activated for request: {request.request_id}",
            request_id=request.request_id,
            agent_id="chief_orchestrator"
        )

        try:
            # Use default operator constraints
            # In production, could load from principal preferences
            constraints = OperatorConstraints()

            # Process through discovery pipeline
            opportunity_records = process_discovery_input(
                raw_text=request.objective,
                constraints=constraints,
                submitted_by=request.requester,
            )

            # Save to registry
            state_store = get_state_store()
            if not state_store.is_initialized:
                state_store.initialize()

            registry = OpportunityRegistry(state_store)

            saved_ids = []
            for record in opportunity_records:
                registry.save_opportunity(record)
                saved_ids.append(record.opportunity_id)

                self._logger.log_event(
                    event_type=EventType.GENERAL,
                    severity=EventSeverity.INFO,
                    message=f"Opportunity evaluated: {record.hypothesis.title}",
                    request_id=request.request_id,
                    agent_id="chief_orchestrator",
                    details={
                        "opportunity_id": record.opportunity_id,
                        "score": record.score.overall_score,
                        "recommendation": record.recommendation.action.value,
                    }
                )

            # Create success response
            result.success = True
            result.executed_by = ["chief_orchestrator", "discovery_pipeline"]
            result.response = create_response(
                request_id=request.request_id,
                responder="chief_orchestrator",
                status=RequestStatus.COMPLETED,
                result={
                    "mode": "discovery",
                    "opportunities_evaluated": len(opportunity_records),
                    "opportunity_ids": saved_ids,
                    "opportunities": [opp.to_dict() for opp in opportunity_records],
                }
            )

            self._logger.log_request_completed(
                request_id=request.request_id,
                agent_id="chief_orchestrator",
                result={"opportunities_evaluated": len(opportunity_records)}
            )

        except Exception as e:
            result.success = False
            result.errors.append(f"Discovery mode error: {str(e)}")
            result.response = create_response(
                request_id=request.request_id,
                responder="chief_orchestrator",
                status=RequestStatus.FAILED,
                errors=[f"Discovery processing failed: {str(e)}"]
            )

            self._logger.log_error(
                message=f"Discovery mode error: {str(e)}",
                error=str(e),
                request_id=request.request_id,
                agent_id="chief_orchestrator"
            )

        return result

    def _handle_direct_execution(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        result: OrchestrationResult
    ) -> OrchestrationResult:
        """Handle requests that can be executed directly."""
        result.execution_path.append("direct_execution")
        result.executed_by.append("chief_orchestrator")

        result.response = create_response(
            request_id=request.request_id,
            responder="chief_orchestrator",
            status=RequestStatus.COMPLETED,
            result={
                "action": "direct_execution",
                "objective": request.objective,
                "message": "Request processed directly by orchestrator"
            },
            confidence=0.9
        )
        result.success = True

        return result

    def _handle_council_advice(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        result: OrchestrationResult
    ) -> OrchestrationResult:
        """Handle requests that need council advice."""
        result.execution_path.append("council_manager")

        # Convene council
        session = self._council.convene(
            request=request,
            topic=request.objective,
            context={"business": business} if business else {}
        )

        # Gather recommendations
        self._council.gather_recommendations(session.session_id, business)

        # Synthesize
        synthesis = self._council.synthesize(session.session_id)

        if synthesis:
            result.executed_by.append("council_manager")

            # Now send to board for decision
            result = self._route_council_to_board(request, business, synthesis, result)
        else:
            result.errors.append("Council synthesis failed")
            result.response = create_response(
                request_id=request.request_id,
                responder="council_manager",
                status=RequestStatus.FAILED,
                errors=["Failed to synthesize council recommendations"]
            )

        return result

    def _route_council_to_board(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        synthesis: Dict[str, Any],
        result: OrchestrationResult
    ) -> OrchestrationResult:
        """Route council synthesis to board for decision."""
        result.execution_path.append("decision_board")

        # Create board session
        board_session = self._board.create_session(
            request=request,
            topic=request.objective,
            context={"business": business, "council_synthesis": synthesis}
        )

        # Add council recommendation as option
        self._board.add_options_from_council(board_session.session_id, synthesis)

        # Score options
        self._board.score_options(board_session.session_id, business)

        # Auto-vote (in a real system, this could be async)
        self._board.auto_vote(board_session.session_id)

        # Decide
        decision = self._board.decide(board_session.session_id)

        if decision:
            result.decision_record = decision
            result.executed_by.append("decision_board")

            board_session = self._board.get_session(board_session.session_id)
            result.response = self._board.to_response(board_session)
            result.success = True

            # Log decision
            self._logger.log_decision(
                request_id=request.request_id,
                agent_id="decision_board",
                decision=decision.decision,
                rationale=decision.rationale,
                confidence=decision.confidence
            )
        else:
            result.errors.append("Board decision failed")
            result.response = create_response(
                request_id=request.request_id,
                responder="decision_board",
                status=RequestStatus.FAILED,
                errors=["Board failed to reach decision"]
            )

        return result

    def _handle_board_decision(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        result: OrchestrationResult
    ) -> OrchestrationResult:
        """Handle requests that need board decision."""
        result.execution_path.append("decision_board")

        # Use single evaluation method
        decision, next_actions = self._board.evaluate_single(
            request=request,
            recommendation=request.objective,
            business=business or {},
            context=request.context
        )

        if decision:
            result.decision_record = decision
            result.executed_by.append("decision_board")
            result.success = True

            result.response = create_response(
                request_id=request.request_id,
                responder="decision_board",
                status=RequestStatus.COMPLETED,
                result={
                    "decision": decision.decision,
                    "rationale": decision.rationale,
                    "next_actions": next_actions
                },
                confidence=decision.confidence,
                rationale=decision.rationale
            )

            self._logger.log_decision(
                request_id=request.request_id,
                agent_id="decision_board",
                decision=decision.decision,
                rationale=decision.rationale,
                confidence=decision.confidence
            )
        else:
            result.errors.append("Board decision failed")

        return result

    def _handle_csuite_delegation(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        result: OrchestrationResult
    ) -> OrchestrationResult:
        """Handle requests delegated to C-Suite."""
        result.execution_path.append("c_suite")

        # Determine which C-suite agent should handle
        c_suite_agent = self._select_csuite_agent(request, business)

        if c_suite_agent:
            result.executed_by.append(c_suite_agent)

            self._logger.log_request_routed(
                request_id=request.request_id,
                from_agent="chief_orchestrator",
                to_agent=c_suite_agent,
                reason="C-Suite delegation based on objective"
            )

            # Delegate to department through C-suite
            result = self._delegate_to_department(request, business, c_suite_agent, result)
        else:
            # No specific C-suite agent, use CEO as default
            result.executed_by.append("ceo")
            result = self._delegate_to_department(request, business, "ceo", result)

        return result

    def _select_csuite_agent(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Select appropriate C-Suite agent for the request."""
        objective = request.objective.lower()

        # Map keywords to C-suite agents
        if any(kw in objective for kw in ["strategy", "direction", "vision", "priority"]):
            return "ceo"
        elif any(kw in objective for kw in ["operation", "process", "efficiency", "deliver"]):
            return "coo"
        elif any(kw in objective for kw in ["financial", "budget", "cost", "revenue", "roi"]):
            return "cfo"
        elif any(kw in objective for kw in ["technology", "architect", "technical", "system"]):
            return "cto"
        elif any(kw in objective for kw in ["market", "brand", "customer", "growth"]):
            return "cmo"

        # Stage-based selection
        if business:
            stage = business.get("stage", "")
            if stage in ["DISCOVERED", "VALIDATING"]:
                return "ceo"  # Strategic decisions
            elif stage in ["BUILDING"]:
                return "cto"  # Technical focus
            elif stage in ["SCALING"]:
                return "cmo"  # Growth focus
            elif stage in ["OPERATING", "OPTIMIZING"]:
                return "coo"  # Operations focus

        return None

    def _handle_department_execution(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        result: OrchestrationResult
    ) -> OrchestrationResult:
        """Handle requests executed by department agents."""
        result.execution_path.append("department")

        # Find appropriate department
        department_agent = self._select_department_agent(request, business)

        if department_agent:
            result.executed_by.append(department_agent)

            self._logger.log_request_routed(
                request_id=request.request_id,
                from_agent="chief_orchestrator",
                to_agent=department_agent,
                reason="Department execution"
            )

            # Execute via department (this would call existing workflow engine)
            result = self._execute_department_task(request, business, department_agent, result)
        else:
            result.errors.append("No suitable department found")

        return result

    def _select_department_agent(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Select appropriate department agent."""
        objective = request.objective.lower()

        # Map keywords to departments
        if any(kw in objective for kw in ["research", "discover", "analyze"]):
            return "dept_research"
        elif any(kw in objective for kw in ["plan", "strategy", "timeline"]):
            return "dept_planning"
        elif any(kw in objective for kw in ["build", "product", "develop", "feature"]):
            return "dept_product"
        elif any(kw in objective for kw in ["operate", "process", "deliver"]):
            return "dept_operations"
        elif any(kw in objective for kw in ["market", "growth", "acquire"]):
            return "dept_growth"
        elif any(kw in objective for kw in ["content", "message", "communicate"]):
            return "dept_content"
        elif any(kw in objective for kw in ["automat", "workflow", "efficien"]):
            return "dept_automation"
        elif any(kw in objective for kw in ["validate", "test", "quality"]):
            return "dept_validation"

        return None

    def _delegate_to_department(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        csuite_agent: str,
        result: OrchestrationResult
    ) -> OrchestrationResult:
        """Delegate from C-Suite to appropriate department."""
        # Get direct reports of C-suite agent
        agent_def = self._registry.get(csuite_agent)
        if agent_def and agent_def.direct_reports:
            dept_agent = agent_def.direct_reports[0]
            result.execution_path.append(dept_agent)
            result.executed_by.append(dept_agent)

            # Execute via department
            result = self._execute_department_task(request, business, dept_agent, result)
        else:
            # Fallback to direct department selection
            result = self._handle_department_execution(request, business, result)

        return result

    def _execute_department_task(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        department: str,
        result: OrchestrationResult
    ) -> OrchestrationResult:
        """
        Execute a task through a department agent.

        This is where the hierarchy connects to the existing workflow engine.
        """
        # Get department handler
        agent_def = self._registry.get(department)

        # For now, simulate successful execution
        # In full integration, this would call the actual handler
        result.response = create_response(
            request_id=request.request_id,
            responder=department,
            status=RequestStatus.COMPLETED,
            result={
                "action": "department_execution",
                "department": department,
                "objective": request.objective,
                "handler_path": agent_def.handler_path if agent_def else None,
                "message": f"Task executed by {department}"
            },
            confidence=0.85,
            rationale=f"Executed through department: {department}"
        )
        result.success = True

        # Log execution
        self._logger.log_task_execution(
            request_id=request.request_id,
            task_id=request.task_id or "orchestrated_task",
            agent_id=department,
            status="completed"
        )

        return result

    def _handle_skill_aware_department_execution(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        execution_plan: Optional[ExecutionPlan],
        result: OrchestrationResult
    ) -> OrchestrationResult:
        """
        Handle skill-aware department execution.

        Uses the execution plan to:
        - Route to appropriate department based on domain
        - Connect to real workflow modules (stage_workflows, etc)
        - Execute with skill context
        """
        result.execution_path.append("skill_aware_department")

        # Get domain from execution plan
        if execution_plan:
            domain = execution_plan.primary_domain
            execution_plan.mark_started()
        else:
            domain = ExecutionDomain.UNKNOWN

        # Map domain to department (domain-neutral routing)
        domain_to_dept = {
            # Knowledge & Strategy
            ExecutionDomain.RESEARCH: "dept_research",
            ExecutionDomain.STRATEGY: "dept_operations",  # Strategic planning routed to operations
            ExecutionDomain.PLANNING: "dept_planning",

            # Product & Engineering
            ExecutionDomain.PRODUCT: "dept_product",
            ExecutionDomain.ENGINEERING: "dept_product",  # Engineering routed to product dept
            ExecutionDomain.VALIDATION: "dept_validation",

            # Operations & Execution
            ExecutionDomain.OPERATIONS: "dept_operations",
            ExecutionDomain.AUTOMATION: "dept_automation",
            ExecutionDomain.INTERNAL_ADMIN: "dept_operations",

            # Finance & Compliance
            ExecutionDomain.FINANCE: "dept_operations",  # Finance routed to operations
            ExecutionDomain.COMPLIANCE: "dept_operations",  # Compliance routed to operations

            # Customer & Growth
            ExecutionDomain.GROWTH: "dept_growth",
            ExecutionDomain.CUSTOMER_SUPPORT: "dept_operations",  # Support routed to operations

            # Content & Communication
            ExecutionDomain.CONTENT: "dept_content",
        }

        department = domain_to_dept.get(domain)
        if not department:
            # Fall back to keyword-based selection
            department = self._select_department_agent(request, business)

        if department:
            result.executed_by.append(department)
            result.execution_path.append(department)

            self._logger.log_request_routed(
                request_id=request.request_id,
                from_agent="chief_orchestrator",
                to_agent=department,
                reason=f"Skill-aware routing via domain '{domain.value}'"
            )

            # Execute using real workflow modules
            result = self._execute_with_workflow_modules(
                request=request,
                business=business,
                department=department,
                execution_plan=execution_plan,
                result=result
            )
        else:
            result.errors.append("No suitable department found")
            if execution_plan:
                execution_plan.mark_completed(success=False)

        return result

    def _execute_with_runtime_manager(
        self,
        request: AgentRequest,
        execution_plan: ExecutionPlan,
        result: OrchestrationResult,
        backend_type: Optional[BackendType] = None
    ) -> RuntimeResult:
        """
        Execute plan through the Runtime Abstraction Layer.

        Uses the runtime manager to:
        - Select appropriate backend
        - Dispatch execution plan
        - Return structured results
        """
        self._ensure_runtime_initialized()

        if not self._runtime_manager:
            # Fallback: return a synthetic result
            return RuntimeResult(
                success=False,
                plan_id=execution_plan.plan_id,
                backend_type=BackendType.INLINE_LOCAL,
                error="Runtime manager not available"
            )

        # Build dispatch options based on request priority
        priority_map = {
            "low": DispatchPriority.LOW,
            "medium": DispatchPriority.NORMAL,
            "high": DispatchPriority.HIGH,
            "critical": DispatchPriority.CRITICAL,
        }

        options = DispatchOptions(
            strategy=DispatchStrategy.IMMEDIATE,
            priority=priority_map.get(request.priority, DispatchPriority.NORMAL),
            stop_on_failure=True,
            metadata={
                "request_id": request.request_id,
                "objective": request.objective[:100],
            }
        )

        # Log backend selection
        selected_backend = self._runtime_manager.select_backend(execution_plan, backend_type)
        self._logger.log_backend_selected(
            request_id=request.request_id,
            plan_id=execution_plan.plan_id,
            backend_type=selected_backend.value,
            selection_reason="auto" if not backend_type else "explicit"
        )

        # Execute through runtime manager
        runtime_result = self._runtime_manager.execute(
            plan=execution_plan,
            backend_type=backend_type,
            options=options
        )

        # Log job dispatch and completion
        if runtime_result.dispatched_job:
            self._logger.log_job_dispatched(
                request_id=request.request_id,
                job_id=runtime_result.dispatched_job.job_id,
                plan_id=execution_plan.plan_id,
                backend_type=runtime_result.backend_type.value,
                priority=options.priority.name
            )

            if runtime_result.success:
                self._logger.log_job_completed(
                    request_id=request.request_id,
                    job_id=runtime_result.dispatched_job.job_id,
                    backend_type=runtime_result.backend_type.value,
                    steps_completed=runtime_result.completed_steps,
                    steps_total=runtime_result.step_count,
                    execution_time_seconds=runtime_result.execution_time_seconds or 0.0
                )
            else:
                self._logger.log_job_failed(
                    request_id=request.request_id,
                    job_id=runtime_result.dispatched_job.job_id,
                    backend_type=runtime_result.backend_type.value,
                    error=runtime_result.error or "Unknown error",
                    steps_completed=runtime_result.completed_steps,
                    steps_total=runtime_result.step_count
                )

        # Update orchestration result with runtime info
        result.backend_used = runtime_result.backend_type.value
        if runtime_result.dispatched_job:
            result.job_id = runtime_result.dispatched_job.job_id
        result.runtime_result = {
            "success": runtime_result.success,
            "backend_type": runtime_result.backend_type.value,
            "execution_time_seconds": runtime_result.execution_time_seconds,
            "step_count": runtime_result.step_count,
            "completed_steps": runtime_result.completed_steps,
            "is_scaffold": runtime_result.metadata.get("backend_is_scaffold", False),
        }

        return runtime_result

    def _ensure_runtime_initialized(self) -> bool:
        """Ensure the runtime manager is initialized."""
        if self._runtime_initialized:
            return True

        try:
            self._runtime_manager = get_runtime_manager()
            if not self._runtime_manager.is_initialized:
                self._runtime_manager.initialize()

            # Log initialization
            backends = self._runtime_manager.list_available_backends()
            self._logger.log_runtime_initialized(
                backends=[b["type"] for b in backends],
                default_backend="inline_local",
                worker_count=0
            )

            self._runtime_initialized = True
            return True
        except Exception:
            self._runtime_initialized = False
            return False

    def _execute_with_workflow_modules(
        self,
        request: AgentRequest,
        business: Optional[Dict[str, Any]],
        department: str,
        execution_plan: Optional[ExecutionPlan],
        result: OrchestrationResult
    ) -> OrchestrationResult:
        """
        Execute using real workflow modules.

        Connects to stage_workflows and workflow_orchestrator.
        Now also routes through the Runtime Abstraction Layer when available.
        """
        # Try runtime manager execution first if execution plan exists
        if execution_plan and self._ensure_runtime_initialized():
            runtime_result = self._execute_with_runtime_manager(
                request=request,
                execution_plan=execution_plan,
                result=result
            )

            if runtime_result.success:
                # Runtime execution succeeded
                result.response = create_response(
                    request_id=request.request_id,
                    responder=department,
                    status=RequestStatus.COMPLETED,
                    result={
                        "action": "runtime_execution",
                        "department": department,
                        "domain": execution_plan.primary_domain.value,
                        "objective": request.objective,
                        "backend": runtime_result.backend_type.value,
                        "job_id": result.job_id,
                        "steps_completed": runtime_result.completed_steps,
                        "execution_time": runtime_result.execution_time_seconds,
                        "skills_used": result.selected_skills,
                        "message": f"Executed via {runtime_result.backend_type.value} backend"
                    },
                    confidence=0.90,
                    rationale=f"Runtime execution through {runtime_result.backend_type.value}"
                )
                result.success = True

                execution_plan.outputs.append({
                    "backend": runtime_result.backend_type.value,
                    "job_result": runtime_result.job_result.to_dict() if runtime_result.job_result else None
                })
                execution_plan.mark_completed(success=True)

                # Log completion
                self._logger.log_execution_plan_completed(
                    request_id=request.request_id,
                    plan_id=execution_plan.plan_id,
                    success=True,
                    steps_completed=runtime_result.completed_steps,
                    steps_total=runtime_result.step_count
                )

                return result

        # Fallback to direct workflow module execution
        # Lazy load workflow modules
        stage_workflows = self._get_stage_workflows()
        workflow_orchestrator = self._get_workflow_orchestrator()

        stage = business.get("stage") if business else None
        task_output = None

        # Build task from request
        task = {
            "task_id": request.task_id or f"task_{request.request_id[:8]}",
            "title": request.objective[:100],
            "description": request.objective,
            "priority": request.priority,
            "assigned_agent": department.replace("dept_", ""),
            "stage": stage or "DISCOVERED",
            "expected_output": "execution_result",
            # Include skill context
            "selected_skills": result.selected_skills,
            "selected_commands": result.selected_commands,
            "selected_agents": result.selected_agents,
        }

        try:
            if stage_workflows and stage:
                # Use stage-specific execution
                task_output = stage_workflows.execute_task(task, business or {
                    "id": request.business_id or "unknown",
                    "opportunity": {"idea": request.objective},
                    "stage": stage,
                    "metrics": {}
                })
            elif workflow_orchestrator and business:
                # Use workflow orchestrator for full workflow
                tasks = [task]
                workflow_result = workflow_orchestrator.execute_stage_workflow(
                    business=business,
                    stage=stage or "DISCOVERED",
                    tasks=tasks,
                    stage_workflows_module=stage_workflows
                )
                task_output = {
                    "status": workflow_result.get("status", "completed"),
                    "workflow_id": workflow_result.get("workflow_id"),
                    "outputs": workflow_result.get("outputs", [])
                }
            else:
                # Fallback to basic execution
                task_output = self._basic_task_execution(task, business)

            # Update result
            result.response = create_response(
                request_id=request.request_id,
                responder=department,
                status=RequestStatus.COMPLETED,
                result={
                    "action": "skill_aware_department_execution",
                    "department": department,
                    "domain": execution_plan.primary_domain.value if execution_plan else "unknown",
                    "objective": request.objective,
                    "task_output": task_output,
                    "skills_used": result.selected_skills,
                    "message": f"Task executed by {department} with skill context"
                },
                confidence=0.88,
                rationale=f"Skill-aware execution through {department}"
            )
            result.success = True

            if execution_plan:
                execution_plan.outputs.append(task_output or {})
                execution_plan.mark_completed(success=True)

                # Log completion
                self._logger.log_execution_plan_completed(
                    request_id=request.request_id,
                    plan_id=execution_plan.plan_id,
                    success=True,
                    steps_completed=len(execution_plan.steps),
                    steps_total=len(execution_plan.steps)
                )

        except Exception as e:
            result.errors.append(f"Workflow execution error: {str(e)}")
            result.response = create_response(
                request_id=request.request_id,
                responder=department,
                status=RequestStatus.FAILED,
                errors=[str(e)]
            )

            if execution_plan:
                execution_plan.errors.append(str(e))
                execution_plan.mark_completed(success=False)

        # Log execution
        self._logger.log_task_execution(
            request_id=request.request_id,
            task_id=task["task_id"],
            agent_id=department,
            status="completed" if result.success else "failed",
            result=task_output
        )

        return result

    def _get_stage_workflows(self):
        """Lazy load stage_workflows module."""
        if self._stage_workflows is None:
            try:
                from core.stage_workflows import StageWorkflows
                self._stage_workflows = StageWorkflows()
            except ImportError:
                self._stage_workflows = None
        return self._stage_workflows

    def _get_workflow_orchestrator(self):
        """Lazy load workflow_orchestrator module."""
        if self._workflow_orchestrator is None:
            try:
                from core.workflow_orchestrator import WorkflowOrchestrator
                self._workflow_orchestrator = WorkflowOrchestrator()
            except ImportError:
                self._workflow_orchestrator = None
        return self._workflow_orchestrator

    def _basic_task_execution(
        self,
        task: Dict[str, Any],
        business: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Basic task execution fallback."""
        return {
            "status": "success",
            "task_id": task.get("task_id"),
            "title": task.get("title"),
            "message": "Executed with basic handler",
            "business_id": business.get("id") if business else None,
            "skills_applied": task.get("selected_skills", [])
        }

    def _finalize(self, result: OrchestrationResult) -> OrchestrationResult:
        """Finalize an orchestration result."""
        result.completed_at = _utc_now().isoformat()

        # Move from active to history
        if result.request_id in self._active:
            del self._active[result.request_id]

        self._history.append(result)

        return result

    # Query methods

    def get_active(self) -> List[OrchestrationResult]:
        """Get all active orchestrations."""
        return list(self._active.values())

    def get_history(self, limit: int = 50) -> List[OrchestrationResult]:
        """Get recent orchestration history."""
        return self._history[-limit:]

    def get_result(self, request_id: str) -> Optional[OrchestrationResult]:
        """Get result by request ID."""
        if request_id in self._active:
            return self._active[request_id]
        for result in self._history:
            if result.request_id == request_id:
                return result
        return None

    # Component access

    @property
    def registry(self) -> AgentRegistry:
        """Get the agent registry."""
        return self._registry

    @property
    def logger(self) -> EventLogger:
        """Get the event logger."""
        return self._logger

    @property
    def approval(self) -> ApprovalManager:
        """Get the approval manager."""
        return self._approval

    @property
    def council(self) -> CouncilManager:
        """Get the council manager."""
        return self._council

    @property
    def board(self) -> DecisionBoard:
        """Get the decision board."""
        return self._board

    # Skill Intelligence Layer methods

    def _ensure_skills_loaded(self) -> bool:
        """Ensure skill layer is loaded."""
        if self._skills_loaded:
            return True

        try:
            self._skill_selector = get_skill_selector()
            self._skill_composer = get_skill_composer()

            # Try to load (won't fail if reference folder missing)
            self._skill_selector.load()
            self._skill_composer.load()
            self._skills_loaded = True
            return True
        except Exception:
            # Skills are optional - system works without them
            self._skills_loaded = False
            return False

    def recommend_skills_for_task(
        self,
        task_description: str,
        role_id: str = "principal_human",
        max_recommendations: int = 5
    ) -> SelectionResult:
        """
        Get skill recommendations for a task.

        Args:
            task_description: Description of the task.
            role_id: Role requesting the skills.
            max_recommendations: Maximum recommendations.

        Returns:
            SelectionResult with recommendations.
        """
        self._ensure_skills_loaded()

        if not self._skill_selector:
            return SelectionResult(
                task_description=task_description,
                recommendations=[],
                confidence=0.0
            )

        # Get raw recommendations
        result = self._skill_selector.select(
            task_description,
            max_recommendations=max_recommendations
        )

        # Filter by role policies
        filtered_recommendations = []
        for rec in result.recommendations:
            policy_result = evaluate_skill_policy(rec.name, role_id)
            if policy_result.decision != PolicyDecision.BLOCKED:
                # Update requires_approval from policy
                rec.requires_approval = (
                    policy_result.decision == PolicyDecision.REQUIRES_APPROVAL
                )
                filtered_recommendations.append(rec)

        result.recommendations = filtered_recommendations
        result.approval_required = any(r.requires_approval for r in filtered_recommendations)

        return result

    def compose_workflow_for_task(
        self,
        task_description: str,
        role_id: str = "principal_human"
    ):
        """
        Compose a workflow for a task.

        Args:
            task_description: Description of the task.
            role_id: Role requesting the workflow.

        Returns:
            ComposedWorkflow or None.
        """
        self._ensure_skills_loaded()

        if not self._skill_composer:
            return None

        return compose_workflow(task_description, role_id)

    def get_role_skills(self, role_id: str) -> Optional[RoleSkillMapping]:
        """
        Get skill mapping for a role.

        Args:
            role_id: The role ID.

        Returns:
            RoleSkillMapping or None.
        """
        return get_role_mapping(role_id)

    @property
    def skill_selector(self) -> Optional[SkillSelector]:
        """Get the skill selector."""
        self._ensure_skills_loaded()
        return self._skill_selector

    @property
    def skill_composer(self) -> Optional[SkillComposer]:
        """Get the skill composer."""
        self._ensure_skills_loaded()
        return self._skill_composer

    # Runtime Abstraction Layer properties

    @property
    def runtime_manager(self) -> Optional[RuntimeManager]:
        """Get the runtime manager."""
        self._ensure_runtime_initialized()
        return self._runtime_manager

    def execute_plan_with_backend(
        self,
        plan: ExecutionPlan,
        backend_type: Optional[BackendType] = None
    ) -> RuntimeResult:
        """
        Execute an execution plan through the runtime manager.

        Args:
            plan: ExecutionPlan to execute.
            backend_type: Specific backend to use (auto-selects if None).

        Returns:
            RuntimeResult with execution outcome.
        """
        self._ensure_runtime_initialized()

        if not self._runtime_manager:
            return RuntimeResult(
                success=False,
                plan_id=plan.plan_id,
                backend_type=backend_type or BackendType.INLINE_LOCAL,
                error="Runtime manager not available"
            )

        return self._runtime_manager.execute(plan, backend_type)

    def list_available_backends(self) -> List[Dict[str, Any]]:
        """List available execution backends."""
        self._ensure_runtime_initialized()

        if not self._runtime_manager:
            return []

        return self._runtime_manager.list_available_backends()

    def get_runtime_stats(self) -> Dict[str, Any]:
        """Get runtime statistics."""
        self._ensure_runtime_initialized()

        if not self._runtime_manager:
            return {"initialized": False}

        return self._runtime_manager.get_stats()
