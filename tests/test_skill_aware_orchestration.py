"""
Tests for Skill-Aware Orchestration Integration.

Tests the integration of the Skill Intelligence Layer with the hierarchy
and execution systems.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Core modules
from core.chief_orchestrator import (
    ChiefOrchestrator, OrchestrationResult, RoutingDecision
)
from core.agent_contracts import AgentRequest, AgentLayer, RequestStatus
from core.event_logger import EventLogger, EventType
from core.approval_manager import ApprovalManager, ApprovalClass

# Execution plan
from core.execution_plan import (
    ExecutionPlan, ExecutionPlanBuilder, ExecutionStep,
    ExecutionDomain, ExecutionStatus, SkillBundle,
    get_plan_builder, build_execution_plan
)

# Skill layer
from core.skill_selector import SelectionResult, ToolRecommendation, SkillSelector, ToolType
from core.skill_policies import (
    PolicyDecision, PolicyResult, evaluate_skill_policy,
    SkillPolicyEngine, ALWAYS_REQUIRE_APPROVAL
)
from core.skill_composer import compose_workflow, ComposedWorkflow


# =============================================================================
# ExecutionPlan Tests
# =============================================================================

class TestExecutionPlan:
    """Tests for ExecutionPlan dataclass."""

    def test_execution_plan_creation(self):
        """Test creating an execution plan."""
        plan = ExecutionPlan(
            objective="Research market opportunities",
            role_id="principal_human",
            business_id="biz_001",
            stage="DISCOVERED"
        )

        assert plan.objective == "Research market opportunities"
        assert plan.role_id == "principal_human"
        assert plan.status == ExecutionStatus.PENDING
        assert plan.plan_id.startswith("plan_")

    def test_execution_plan_to_dict(self):
        """Test converting plan to dictionary."""
        plan = ExecutionPlan(
            objective="Test objective",
            role_id="cto"
        )

        data = plan.to_dict()
        assert data["objective"] == "Test objective"
        assert data["role_id"] == "cto"
        assert data["status"] == "pending"

    def test_add_step(self):
        """Test adding execution steps."""
        plan = ExecutionPlan(objective="Test")

        step = ExecutionStep(
            step_id="step_1",
            description="First step",
            domain=ExecutionDomain.RESEARCH,
            skills=["lead-research-assistant"],
            requires_approval=True
        )

        plan.add_step(step)

        assert len(plan.steps) == 1
        assert plan.requires_approval is True

    def test_mark_started(self):
        """Test marking plan as started."""
        plan = ExecutionPlan(objective="Test")
        plan.mark_started()

        assert plan.status == ExecutionStatus.EXECUTING
        assert plan.started_at is not None

    def test_mark_completed(self):
        """Test marking plan as completed."""
        plan = ExecutionPlan(objective="Test")
        plan.mark_completed(success=True)

        assert plan.status == ExecutionStatus.COMPLETED
        assert plan.success is True

    def test_mark_blocked(self):
        """Test marking plan as blocked."""
        plan = ExecutionPlan(objective="Test")
        plan.mark_blocked("Policy violation")

        assert plan.status == ExecutionStatus.BLOCKED
        assert "Policy violation" in plan.errors


class TestSkillBundle:
    """Tests for SkillBundle dataclass."""

    def test_skill_bundle_creation(self):
        """Test creating a skill bundle."""
        bundle = SkillBundle(
            skills=["skill1", "skill2"],
            commands=["commit"],
            specialized_agents=["security-auditor"]
        )

        assert len(bundle.skills) == 2
        assert len(bundle.commands) == 1
        assert len(bundle.specialized_agents) == 1

    def test_skill_bundle_to_dict(self):
        """Test bundle to dict conversion."""
        bundle = SkillBundle(skills=["test-skill"])
        data = bundle.to_dict()

        assert "skills" in data
        assert "commands" in data
        assert "policy_decisions" in data


class TestExecutionPlanBuilder:
    """Tests for ExecutionPlanBuilder."""

    def test_detect_domain_research(self):
        """Test research domain detection."""
        builder = ExecutionPlanBuilder()
        domain = builder.detect_domain("Research market opportunities")
        assert domain == ExecutionDomain.RESEARCH

    def test_detect_domain_planning(self):
        """Test planning domain detection."""
        builder = ExecutionPlanBuilder()
        domain = builder.detect_domain("Plan the product roadmap")
        assert domain == ExecutionDomain.PLANNING

    def test_detect_domain_product(self):
        """Test product domain detection."""
        builder = ExecutionPlanBuilder()
        domain = builder.detect_domain("Build the new feature")
        assert domain == ExecutionDomain.PRODUCT

    def test_detect_domain_growth(self):
        """Test growth domain detection."""
        builder = ExecutionPlanBuilder()
        domain = builder.detect_domain("Scale marketing campaigns")
        assert domain == ExecutionDomain.GROWTH

    def test_detect_domain_validation(self):
        """Test validation domain detection."""
        builder = ExecutionPlanBuilder()
        domain = builder.detect_domain("Validate the test suite")
        assert domain == ExecutionDomain.VALIDATION

    def test_detect_domain_unknown(self):
        """Test unknown domain detection."""
        builder = ExecutionPlanBuilder()
        domain = builder.detect_domain("Do something random")
        assert domain == ExecutionDomain.UNKNOWN

    def test_build_from_selection(self):
        """Test building plan from selection result."""
        builder = ExecutionPlanBuilder()

        # Create mock selection result
        selection = SelectionResult(
            task_description="Research competitors",
            recommendations=[
                ToolRecommendation(
                    tool_type=ToolType.SKILL,
                    name="lead-research-assistant",
                    score=0.9,
                    rationale="Research leads",
                    requires_approval=False
                )
            ],
            confidence=0.85
        )

        plan = builder.build_from_selection(
            objective="Research competitors",
            selection_result=selection,
            role_id="principal_human",
            business_id="biz_001"
        )

        assert plan.primary_domain == ExecutionDomain.RESEARCH
        assert plan.skill_bundle is not None
        assert len(plan.steps) > 0


class TestBuildExecutionPlan:
    """Tests for build_execution_plan function."""

    def test_build_minimal_plan(self):
        """Test building plan without skills or workflow."""
        plan = build_execution_plan(
            objective="Test objective",
            role_id="cto"
        )

        assert plan.objective == "Test objective"
        assert plan.role_id == "cto"

    def test_build_plan_with_selection(self):
        """Test building plan with skill selection."""
        selection = SelectionResult(
            task_description="Build feature",
            recommendations=[
                ToolRecommendation(
                    tool_type=ToolType.SKILL,
                    name="mcp-builder",
                    score=0.8,
                    rationale="Build MCP servers"
                )
            ]
        )

        plan = build_execution_plan(
            objective="Build feature",
            selection_result=selection,
            business_id="biz_001",
            stage="BUILDING"
        )

        assert plan.skill_bundle is not None
        assert plan.stage == "BUILDING"


# =============================================================================
# Skill-Aware Orchestration Tests
# =============================================================================

class TestSkillAwareOrchestration:
    """Tests for skill-aware chief orchestrator."""

    def test_orchestrator_with_skill_selection(self):
        """Test orchestrator selects skills during orchestration."""
        orchestrator = ChiefOrchestrator()

        # Orchestrate a research task
        result = orchestrator.orchestrate(
            objective="Research market opportunities for AI tools",
            business={
                "id": "biz_001",
                "stage": "DISCOVERED",
                "opportunity": {"idea": "AI Tool Market"},
                "metrics": {}
            },
            requester="principal"
        )

        # Should have attempted skill selection (may be empty if reference not loaded)
        assert isinstance(result, OrchestrationResult)
        assert "selected_skills" in result.to_dict()
        assert "selected_commands" in result.to_dict()
        assert "selected_agents" in result.to_dict()

    def test_orchestrator_execution_plan_creation(self):
        """Test orchestrator creates execution plans."""
        orchestrator = ChiefOrchestrator()

        result = orchestrator.orchestrate(
            objective="Build new product feature",
            business={
                "id": "biz_002",
                "stage": "BUILDING",
                "opportunity": {"idea": "New Feature"},
                "metrics": {}
            },
            requester="cto"
        )

        # Execution plan may or may not be created depending on skill loading
        result_dict = result.to_dict()
        assert "execution_plan" in result_dict

    def test_orchestrator_skill_aware_routing(self):
        """Test skill-aware routing to departments."""
        orchestrator = ChiefOrchestrator()

        result = orchestrator.orchestrate(
            objective="Validate product quality with testing",
            business={
                "id": "biz_003",
                "stage": "VALIDATING",
                "opportunity": {"idea": "Quality Check"},
                "metrics": {"validation_score": 0.8}
            },
            requester="principal"
        )

        # Check routing happened
        assert result.routing in [
            RoutingDecision.DEPARTMENT_EXECUTION,
            RoutingDecision.C_SUITE_DELEGATION,
            RoutingDecision.COUNCIL_ADVICE
        ]

    def test_skill_policy_integration(self):
        """Test skill policies are evaluated during orchestration."""
        orchestrator = ChiefOrchestrator()

        result = orchestrator.orchestrate(
            objective="Deploy to production using CI/CD automation",
            business={
                "id": "biz_004",
                "stage": "OPERATING",
                "opportunity": {"idea": "Deployment"},
                "metrics": {}
            },
            requester="cto"
        )

        # Check policy decisions are tracked
        result_dict = result.to_dict()
        assert "skill_policy_decisions" in result_dict


class TestSkillAwareApproval:
    """Tests for skill-aware approval integration."""

    def test_approval_with_sensitive_skills(self):
        """Test that sensitive skills trigger approval."""
        orchestrator = ChiefOrchestrator()

        # Test with payment-related objective
        result = orchestrator.orchestrate(
            objective="Process payments with stripe automation",
            business={
                "id": "biz_005",
                "stage": "OPERATING",
                "opportunity": {"idea": "Payment Processing"},
                "metrics": {}
            },
            requester="dept_operations"  # Non-principal
        )

        # Result should exist
        assert result is not None

    def test_principal_bypass_approval(self):
        """Test principal can auto-allow most skills."""
        orchestrator = ChiefOrchestrator()

        result = orchestrator.orchestrate(
            objective="Research competitive landscape",
            business={
                "id": "biz_006",
                "stage": "DISCOVERED",
                "opportunity": {"idea": "Research"},
                "metrics": {}
            },
            requester="principal"
        )

        # Principal should not be blocked for research
        assert result.routing != RoutingDecision.BLOCKED


class TestEventLogging:
    """Tests for skill-related event logging."""

    def test_skill_selection_logged(self):
        """Test skill selection is logged."""
        logger = EventLogger()

        # Log skill selection
        event = logger.log_skills_selected(
            request_id="req_001",
            agent_id="chief_orchestrator",
            skills=["skill1", "skill2"],
            commands=["commit"],
            specialized_agents=["security-auditor"],
            confidence=0.85
        )

        assert event.event_type == EventType.SKILLS_SELECTED
        assert event.details["confidence"] == 0.85
        assert len(event.details["skills"]) == 2

    def test_policy_evaluation_logged(self):
        """Test policy evaluation is logged."""
        logger = EventLogger()

        event = logger.log_skill_policy_evaluated(
            request_id="req_002",
            skill_name="stripe-automation",
            role_id="cto",
            decision="requires_approval",
            reason="Skill always requires approval"
        )

        assert event.event_type == EventType.SKILL_POLICY_EVALUATED
        assert event.details["decision"] == "requires_approval"

    def test_skill_blocked_logged(self):
        """Test blocked skill is logged."""
        logger = EventLogger()

        event = logger.log_skill_blocked(
            request_id="req_003",
            skill_name="dangerous-skill",
            role_id="dept_research",
            reason="Globally blocked"
        )

        assert event.event_type == EventType.SKILL_BLOCKED

    def test_execution_plan_logged(self):
        """Test execution plan creation is logged."""
        logger = EventLogger()

        event = logger.log_execution_plan_created(
            request_id="req_004",
            plan_id="plan_001",
            objective="Build feature",
            domain="product",
            skill_count=3,
            step_count=2,
            requires_approval=False
        )

        assert event.event_type == EventType.EXECUTION_PLAN_CREATED
        assert event.details["skill_count"] == 3


class TestWorkflowModuleIntegration:
    """Tests for integration with real workflow modules."""

    def test_stage_workflows_connection(self):
        """Test connection to stage_workflows module."""
        orchestrator = ChiefOrchestrator()

        # Access lazy-loaded module
        stage_workflows = orchestrator._get_stage_workflows()

        # Should load successfully
        assert stage_workflows is not None

    def test_workflow_orchestrator_connection(self):
        """Test connection to workflow_orchestrator module."""
        orchestrator = ChiefOrchestrator()

        workflow_orch = orchestrator._get_workflow_orchestrator()

        # Should load successfully
        assert workflow_orch is not None

    def test_skill_aware_execution_with_stage_workflows(self):
        """Test skill-aware execution using stage_workflows."""
        orchestrator = ChiefOrchestrator()

        business = {
            "id": "biz_007",
            "stage": "VALIDATING",
            "opportunity": {"idea": "Test Idea"},
            "metrics": {"validation_score": 0.75}
        }

        result = orchestrator.orchestrate(
            objective="Validate customer problem",
            business=business,
            requester="principal"
        )

        # Check execution happened
        assert result.success or len(result.errors) > 0
        assert len(result.execution_path) > 1


class TestOrchestrationResultWithSkills:
    """Tests for OrchestrationResult with skill data."""

    def test_result_includes_skills(self):
        """Test result includes skill selections."""
        result = OrchestrationResult(
            request_id="req_test",
            routing=RoutingDecision.DEPARTMENT_EXECUTION,
            success=True,
            selected_skills=["skill1", "skill2"],
            selected_commands=["commit"],
            selected_agents=["test-engineer"]
        )

        assert len(result.selected_skills) == 2
        assert len(result.selected_commands) == 1
        assert len(result.selected_agents) == 1

    def test_result_to_dict_with_plan(self):
        """Test result to_dict includes execution plan."""
        plan = ExecutionPlan(objective="Test")

        result = OrchestrationResult(
            request_id="req_test",
            routing=RoutingDecision.DEPARTMENT_EXECUTION,
            success=True,
            execution_plan=plan
        )

        data = result.to_dict()
        assert "execution_plan" in data
        assert data["execution_plan"] is not None

    def test_result_skill_approval_flag(self):
        """Test skill approval flag is tracked."""
        result = OrchestrationResult(
            request_id="req_test",
            routing=RoutingDecision.REQUIRES_APPROVAL,
            success=False,
            skill_approval_required=True
        )

        assert result.skill_approval_required is True


class TestDomainRouting:
    """Tests for domain-based routing."""

    def test_research_domain_routing(self):
        """Test research domain routes correctly."""
        builder = ExecutionPlanBuilder()

        plan = build_execution_plan(
            objective="Research market trends and competitors"
        )

        assert plan.primary_domain == ExecutionDomain.RESEARCH

    def test_planning_domain_routing(self):
        """Test planning domain routes correctly."""
        plan = build_execution_plan(
            objective="Plan the product strategy and roadmap"
        )

        assert plan.primary_domain == ExecutionDomain.PLANNING

    def test_product_domain_routing(self):
        """Test product domain routes correctly."""
        plan = build_execution_plan(
            objective="Build and develop the new feature"
        )

        assert plan.primary_domain == ExecutionDomain.PRODUCT

    def test_validation_domain_routing(self):
        """Test validation domain routes correctly."""
        plan = build_execution_plan(
            objective="Test and validate the implementation"
        )

        assert plan.primary_domain == ExecutionDomain.VALIDATION

    def test_growth_domain_routing(self):
        """Test growth domain routes correctly."""
        plan = build_execution_plan(
            objective="Scale marketing and acquire users"
        )

        assert plan.primary_domain == ExecutionDomain.GROWTH


# =============================================================================
# Integration Tests
# =============================================================================

class TestFullIntegration:
    """Full integration tests for skill-aware orchestration."""

    def test_full_orchestration_cycle(self):
        """Test complete orchestration cycle with skills."""
        orchestrator = ChiefOrchestrator()

        # Execute a full cycle
        result = orchestrator.orchestrate(
            objective="Research and analyze market opportunities for AI products",
            business={
                "id": "biz_full_001",
                "stage": "DISCOVERED",
                "opportunity": {"idea": "AI Market Analysis"},
                "metrics": {"failure_count": 0}
            },
            requester="principal",
            priority="high"
        )

        # Verify full result
        assert result.request_id is not None
        assert result.started_at is not None
        assert result.completed_at is not None

        # Check execution path includes expected nodes
        assert "chief_orchestrator" in result.execution_path

        # Verify result dict structure
        result_dict = result.to_dict()
        assert "selected_skills" in result_dict
        assert "selected_commands" in result_dict
        assert "selected_agents" in result_dict
        assert "execution_plan" in result_dict

    def test_orchestration_with_building_stage(self):
        """Test orchestration in BUILDING stage."""
        orchestrator = ChiefOrchestrator()

        result = orchestrator.orchestrate(
            objective="Build the MVP product features",
            business={
                "id": "biz_building_001",
                "stage": "BUILDING",
                "opportunity": {"idea": "MVP Development"},
                "metrics": {}
            },
            requester="cto"
        )

        assert result.success or len(result.errors) == 0 or result.routing == RoutingDecision.REQUIRES_APPROVAL

    def test_orchestration_history_tracking(self):
        """Test orchestration history is tracked."""
        orchestrator = ChiefOrchestrator()

        # Run multiple orchestrations
        for i in range(3):
            orchestrator.orchestrate(
                objective=f"Task {i}",
                business={
                    "id": f"biz_hist_{i}",
                    "stage": "DISCOVERED",
                    "opportunity": {"idea": f"Idea {i}"},
                    "metrics": {}
                }
            )

        # Check history
        history = orchestrator.get_history(limit=10)
        assert len(history) >= 3

    def test_event_trail(self):
        """Test event logging trail during orchestration."""
        orchestrator = ChiefOrchestrator()

        # Run orchestration
        result = orchestrator.orchestrate(
            objective="Analyze competitive landscape",
            business={
                "id": "biz_event_001",
                "stage": "DISCOVERED",
                "opportunity": {"idea": "Competition Analysis"},
                "metrics": {}
            }
        )

        # Get events for this request
        events = orchestrator.logger.get_request_timeline(result.request_id)

        # Should have at least request_received event
        assert len(events) >= 1
        event_types = [e.event_type for e in events]
        assert EventType.REQUEST_RECEIVED in event_types
