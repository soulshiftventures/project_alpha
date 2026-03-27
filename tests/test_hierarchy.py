"""
Test suite for Project Alpha Hierarchy System
Tests all hierarchy modules: contracts, registry, council, board, orchestrator
"""

import pytest
import os
from typing import Dict, Any

# Set test environment before imports
os.environ["PROJECT_ALPHA_EVENT_LOG"] = "/tmp/test_events.jsonl"

from core.agent_contracts import (
    AgentRequest, AgentResponse, RequestStatus, AgentLayer,
    DecisionRecord, CouncilRecommendation, BoardVote,
    create_request, create_response
)
from core.agent_registry import AgentRegistry, AgentDefinition, AgentStatus
from core.hierarchy_definitions import (
    create_default_hierarchy, get_all_agents,
    get_principal_agents, get_executive_agents, get_council_agents,
    get_board_agents, get_csuite_agents, get_department_agents,
    LAYER_ORDER, get_layer_index, is_superior_layer,
    get_agents_for_capability, ALL_STAGES
)
from core.event_logger import EventLogger, EventType, EventSeverity
from core.approval_manager import ApprovalManager, ApprovalClass, ApprovalStatus
from core.council_manager import CouncilManager, CouncilSession
from core.decision_board import DecisionBoard, DecisionOption, DecisionSession
from core.chief_orchestrator import ChiefOrchestrator, RoutingDecision, OrchestrationResult


# ============================================================================
# Test Agent Contracts
# ============================================================================

class TestAgentContracts:
    """Tests for agent contract structures."""

    def test_create_request(self):
        """Test creating an agent request."""
        request = create_request(
            requester="principal",
            target_agent="ceo",
            objective="Evaluate business strategy",
            business_id="test_123",
            priority="high"
        )

        assert request.requester == "principal"
        assert request.target_agent == "ceo"
        assert request.objective == "Evaluate business strategy"
        assert request.business_id == "test_123"
        assert request.priority == "high"
        assert request.request_id is not None

    def test_create_response(self):
        """Test creating an agent response."""
        response = create_response(
            request_id="req_123",
            responder="ceo",
            status=RequestStatus.COMPLETED,
            result={"decision": "proceed"},
            confidence=0.85,
            rationale="Strong market signals"
        )

        assert response.request_id == "req_123"
        assert response.responder == "ceo"
        assert response.status == RequestStatus.COMPLETED
        assert response.result == {"decision": "proceed"}
        assert response.confidence == 0.85
        assert response.is_success()

    def test_request_to_dict(self):
        """Test request serialization."""
        request = create_request(
            requester="dept_research",
            target_agent="ceo",
            objective="Test objective"
        )
        data = request.to_dict()

        assert data["requester"] == "dept_research"
        assert data["target_agent"] == "ceo"
        assert "request_id" in data

    def test_response_to_dict(self):
        """Test response serialization."""
        response = create_response(
            request_id="req_456",
            responder="council_manager",
            status=RequestStatus.FAILED,
            errors=["Test error"]
        )
        data = response.to_dict()

        assert data["request_id"] == "req_456"
        assert data["status"] == "failed"
        assert data["errors"] == ["Test error"]

    def test_decision_record(self):
        """Test decision record creation."""
        record = DecisionRecord(
            request_id="req_789",
            decision_type="strategic",
            decision="Proceed with expansion",
            rationale="Market conditions favorable",
            confidence=0.8,
            decided_by="decision_board"
        )

        assert record.request_id == "req_789"
        assert record.decision == "Proceed with expansion"
        assert record.confidence == 0.8
        assert record.decided_by == "decision_board"

    def test_council_recommendation(self):
        """Test council recommendation structure."""
        rec = CouncilRecommendation(
            advisor_id="advisor_strategy",
            advisor_name="Strategy Advisor",
            recommendation="Focus on core market",
            confidence=0.9,
            reasoning="Strong competitive position",
            concerns=["Market volatility"]
        )

        assert rec.advisor_id == "advisor_strategy"
        assert rec.confidence == 0.9
        assert len(rec.concerns) == 1

    def test_board_vote(self):
        """Test board vote structure."""
        vote = BoardVote(
            voter_id="ceo",
            voter_name="CEO Agent",
            vote="approve",
            weight=1.5,
            rationale="Aligns with strategy"
        )

        assert vote.voter_id == "ceo"
        assert vote.vote == "approve"
        assert vote.weight == 1.5


# ============================================================================
# Test Agent Registry
# ============================================================================

class TestAgentRegistry:
    """Tests for agent registry."""

    def test_registry_creation(self):
        """Test creating empty registry."""
        registry = AgentRegistry()
        assert registry.count() == 0

    def test_register_agent(self):
        """Test registering an agent."""
        registry = AgentRegistry()
        agent = AgentDefinition(
            agent_id="test_agent",
            name="Test Agent",
            layer=AgentLayer.DEPARTMENT,
            role="Test role",
            capabilities=["test_cap"]
        )

        registry.register(agent)
        assert registry.count() == 1
        assert registry.get("test_agent") is not None

    def test_get_by_layer(self):
        """Test filtering agents by layer."""
        registry = AgentRegistry()

        agent1 = AgentDefinition(
            agent_id="dept_1",
            name="Dept 1",
            layer=AgentLayer.DEPARTMENT,
            role="Role 1"
        )
        agent2 = AgentDefinition(
            agent_id="csuite_1",
            name="C-Suite 1",
            layer=AgentLayer.C_SUITE,
            role="Role 2"
        )

        registry.register(agent1)
        registry.register(agent2)

        dept_agents = registry.get_by_layer(AgentLayer.DEPARTMENT)
        assert len(dept_agents) == 1
        assert dept_agents[0].agent_id == "dept_1"

    def test_get_by_capability(self):
        """Test filtering agents by capability."""
        registry = AgentRegistry()

        agent = AgentDefinition(
            agent_id="researcher",
            name="Researcher",
            layer=AgentLayer.DEPARTMENT,
            role="Research",
            capabilities=["market_research", "analysis"]
        )

        registry.register(agent)

        matches = registry.get_by_capability("market_research")
        assert len(matches) == 1
        assert matches[0].agent_id == "researcher"

    def test_unregister_agent(self):
        """Test removing an agent."""
        registry = AgentRegistry()
        agent = AgentDefinition(
            agent_id="temp_agent",
            name="Temp",
            layer=AgentLayer.DEPARTMENT,
            role="Temp"
        )

        registry.register(agent)
        assert registry.count() == 1

        result = registry.unregister("temp_agent")
        assert result is True
        assert registry.count() == 0

    def test_update_status(self):
        """Test updating agent status."""
        registry = AgentRegistry()
        agent = AgentDefinition(
            agent_id="status_test",
            name="Status Test",
            layer=AgentLayer.DEPARTMENT,
            role="Test"
        )

        registry.register(agent)
        assert registry.get("status_test").status == AgentStatus.ACTIVE

        registry.update_status("status_test", AgentStatus.SUSPENDED)
        assert registry.get("status_test").status == AgentStatus.SUSPENDED

    def test_count_by_layer(self):
        """Test counting agents per layer."""
        registry = create_default_hierarchy()
        counts = registry.count_by_layer()

        assert counts["principal"] == 1
        assert counts["executive"] == 1
        assert counts["c_suite"] == 5
        assert counts["department"] >= 8


# ============================================================================
# Test Hierarchy Definitions
# ============================================================================

class TestHierarchyDefinitions:
    """Tests for hierarchy definitions."""

    def test_all_stages_defined(self):
        """Test all lifecycle stages are defined."""
        assert len(ALL_STAGES) == 7
        assert "DISCOVERED" in ALL_STAGES
        assert "TERMINATED" in ALL_STAGES

    def test_create_default_hierarchy(self):
        """Test creating default hierarchy."""
        registry = create_default_hierarchy()
        assert registry.count() > 0

        # Check key agents exist
        assert registry.get("principal") is not None
        assert registry.get("chief_orchestrator") is not None
        assert registry.get("council_manager") is not None
        assert registry.get("decision_board") is not None
        assert registry.get("ceo") is not None

    def test_principal_agent(self):
        """Test principal agent definition."""
        agents = get_principal_agents()
        assert len(agents) == 1

        principal = agents[0]
        assert principal.agent_id == "principal"
        assert principal.layer == AgentLayer.PRINCIPAL
        assert "approve" in principal.capabilities

    def test_executive_agent(self):
        """Test executive agent definition."""
        agents = get_executive_agents()
        assert len(agents) == 1

        orchestrator = agents[0]
        assert orchestrator.agent_id == "chief_orchestrator"
        assert orchestrator.reports_to == "principal"

    def test_council_agents(self):
        """Test council agents."""
        agents = get_council_agents()
        assert len(agents) >= 4  # manager + advisors

        # Check council manager exists
        manager = next((a for a in agents if a.agent_id == "council_manager"), None)
        assert manager is not None

    def test_csuite_agents(self):
        """Test C-suite agents."""
        agents = get_csuite_agents()
        assert len(agents) == 5

        agent_ids = [a.agent_id for a in agents]
        assert "ceo" in agent_ids
        assert "coo" in agent_ids
        assert "cfo" in agent_ids
        assert "cto" in agent_ids
        assert "cmo" in agent_ids

    def test_department_agents(self):
        """Test department agents."""
        agents = get_department_agents()
        assert len(agents) >= 8

        agent_ids = [a.agent_id for a in agents]
        assert "dept_research" in agent_ids
        assert "dept_planning" in agent_ids
        assert "dept_product" in agent_ids

    def test_layer_order(self):
        """Test layer hierarchy order."""
        assert get_layer_index(AgentLayer.PRINCIPAL) < get_layer_index(AgentLayer.EXECUTIVE)
        assert get_layer_index(AgentLayer.EXECUTIVE) < get_layer_index(AgentLayer.C_SUITE)
        assert get_layer_index(AgentLayer.C_SUITE) < get_layer_index(AgentLayer.DEPARTMENT)

    def test_is_superior_layer(self):
        """Test layer superiority check."""
        assert is_superior_layer(AgentLayer.PRINCIPAL, AgentLayer.EXECUTIVE)
        assert is_superior_layer(AgentLayer.C_SUITE, AgentLayer.DEPARTMENT)
        assert not is_superior_layer(AgentLayer.DEPARTMENT, AgentLayer.C_SUITE)

    def test_capability_routing(self):
        """Test capability to agent routing."""
        research_agents = get_agents_for_capability("market_research")
        assert "dept_research" in research_agents

        planning_agents = get_agents_for_capability("strategic_planning")
        assert len(planning_agents) > 0


# ============================================================================
# Test Event Logger
# ============================================================================

class TestEventLogger:
    """Tests for event logger."""

    def test_log_event(self):
        """Test logging an event."""
        logger = EventLogger(log_file=None)

        event = logger.log(
            event_type=EventType.REQUEST_RECEIVED,
            message="Test event",
            agent_id="test_agent"
        )

        assert event.event_type == EventType.REQUEST_RECEIVED
        assert event.message == "Test event"

    def test_log_request_received(self):
        """Test logging request received."""
        logger = EventLogger(log_file=None)

        event = logger.log_request_received(
            request_id="req_123",
            agent_id="chief_orchestrator",
            objective="Test objective"
        )

        assert event.event_type == EventType.REQUEST_RECEIVED
        assert event.request_id == "req_123"

    def test_log_decision(self):
        """Test logging a decision."""
        logger = EventLogger(log_file=None)

        event = logger.log_decision(
            request_id="req_456",
            agent_id="decision_board",
            decision="Proceed",
            rationale="Good metrics",
            confidence=0.9
        )

        assert event.event_type == EventType.DECISION_MADE
        assert event.details["confidence"] == 0.9

    def test_get_events_filtered(self):
        """Test filtering events."""
        logger = EventLogger(log_file=None)

        logger.log(EventType.REQUEST_RECEIVED, "Event 1", agent_id="agent_1")
        logger.log(EventType.DECISION_MADE, "Event 2", agent_id="agent_2")
        logger.log(EventType.REQUEST_RECEIVED, "Event 3", agent_id="agent_1")

        events = logger.get_events(event_type=EventType.REQUEST_RECEIVED)
        assert len(events) == 2

        events = logger.get_events(agent_id="agent_1")
        assert len(events) == 2

    def test_get_errors(self):
        """Test getting error events."""
        logger = EventLogger(log_file=None)

        logger.log(EventType.REQUEST_RECEIVED, "Normal event")
        logger.log_error("Error occurred", "Test error", agent_id="agent_x")

        errors = logger.get_errors()
        assert len(errors) == 1

    def test_count_by_type(self):
        """Test counting events by type."""
        logger = EventLogger(log_file=None)

        logger.log(EventType.REQUEST_RECEIVED, "E1")
        logger.log(EventType.REQUEST_RECEIVED, "E2")
        logger.log(EventType.DECISION_MADE, "E3")

        counts = logger.count_by_type()
        assert counts["request_received"] == 2
        assert counts["decision_made"] == 1


# ============================================================================
# Test Approval Manager
# ============================================================================

class TestApprovalManager:
    """Tests for approval manager."""

    def test_auto_allowed_principal(self):
        """Test principal actions are auto-allowed."""
        manager = ApprovalManager()
        request = create_request(
            requester="principal",
            target_agent="ceo",
            objective="Set strategy"
        )

        classification, _ = manager.classify(request, "set_strategy", confidence=0.8)
        assert classification == ApprovalClass.AUTO_ALLOWED

    def test_critical_requires_approval(self):
        """Test critical priority requires approval."""
        manager = ApprovalManager()
        request = create_request(
            requester="ceo",
            target_agent="dept_product",
            objective="Critical change",
            priority="critical"
        )

        classification, _ = manager.classify(request, "critical_change", confidence=0.8)
        assert classification == ApprovalClass.REQUIRES_APPROVAL

    def test_termination_requires_approval(self):
        """Test termination actions require approval."""
        manager = ApprovalManager()
        request = create_request(
            requester="coo",
            target_agent="dept_operations",
            objective="Terminate process"
        )

        classification, _ = manager.classify(request, "terminate_business", confidence=0.8)
        assert classification == ApprovalClass.REQUIRES_APPROVAL

    def test_department_routine_auto_allowed(self):
        """Test routine department actions auto-allowed."""
        manager = ApprovalManager()
        request = create_request(
            requester="dept_research",
            target_agent="dept_research",
            objective="Execute analysis"
        )

        classification, _ = manager.classify(
            request, "execute_analysis", confidence=0.8,
            context={"layer": "department"}
        )
        assert classification == ApprovalClass.AUTO_ALLOWED

    def test_approval_workflow(self):
        """Test full approval workflow."""
        manager = ApprovalManager()
        request = create_request(
            requester="ceo",
            target_agent="decision_board",
            objective="Major change",
            priority="critical"
        )

        # Request approval
        classification, record = manager.check_and_process(
            request, "major_change", confidence=0.6
        )

        assert classification == ApprovalClass.REQUIRES_APPROVAL
        assert record is not None
        assert record.status == ApprovalStatus.PENDING

        # Approve it
        approved = manager.approve(record.record_id, "principal", "Approved by Kris")
        assert approved is not None
        assert approved.status == ApprovalStatus.APPROVED


# ============================================================================
# Test Council Manager
# ============================================================================

class TestCouncilManager:
    """Tests for council manager."""

    def test_convene_council(self):
        """Test convening a council session."""
        registry = create_default_hierarchy()
        council = CouncilManager(registry)

        request = create_request(
            requester="chief_orchestrator",
            target_agent="council_manager",
            objective="Evaluate strategy"
        )

        session = council.convene(request, "Strategy evaluation")
        assert session is not None
        assert session.topic == "Strategy evaluation"
        assert len(session.advisors_invited) > 0

    def test_gather_recommendations(self):
        """Test gathering advisor recommendations."""
        registry = create_default_hierarchy()
        council = CouncilManager(registry)

        request = create_request(
            requester="chief_orchestrator",
            target_agent="council_manager",
            objective="Evaluate expansion"
        )

        business = {
            "id": "biz_123",
            "stage": "VALIDATING",
            "metrics": {"validation_score": 0.6}
        }

        session = council.convene(request, "Expansion evaluation", context={"business": business})
        recommendations = council.gather_recommendations(session.session_id, business)

        assert len(recommendations) > 0

    def test_synthesize_recommendations(self):
        """Test synthesizing council recommendations."""
        registry = create_default_hierarchy()
        council = CouncilManager(registry)

        request = create_request(
            requester="chief_orchestrator",
            target_agent="council_manager",
            objective="Strategic direction"
        )

        business = {
            "id": "biz_456",
            "stage": "BUILDING",
            "metrics": {"validation_score": 0.8, "build_progress": 0.5}
        }

        session = council.convene(request, "Direction review", context={"business": business})
        council.gather_recommendations(session.session_id, business)
        synthesis = council.synthesize(session.session_id)

        assert synthesis is not None
        assert "final_recommendation" in synthesis
        assert "agreements" in synthesis
        assert "disagreements" in synthesis

    def test_council_response(self):
        """Test converting session to response."""
        registry = create_default_hierarchy()
        council = CouncilManager(registry)

        request = create_request(
            requester="chief_orchestrator",
            target_agent="council_manager",
            objective="Quick review"
        )

        session = council.convene(request, "Quick review")
        council.gather_recommendations(session.session_id)
        council.synthesize(session.session_id)

        completed_session = council.get_session(session.session_id)
        response = council.to_response(completed_session)

        assert response.status == RequestStatus.COMPLETED


# ============================================================================
# Test Decision Board
# ============================================================================

class TestDecisionBoard:
    """Tests for decision board."""

    def test_create_session(self):
        """Test creating a decision session."""
        registry = create_default_hierarchy()
        board = DecisionBoard(registry)

        request = create_request(
            requester="council_manager",
            target_agent="decision_board",
            objective="Decide direction"
        )

        session = board.create_session(request, "Direction decision")
        assert session is not None
        assert len(session.voters) > 0  # C-suite members

    def test_add_options(self):
        """Test adding options to a session."""
        registry = create_default_hierarchy()
        board = DecisionBoard(registry)

        request = create_request(
            requester="council_manager",
            target_agent="decision_board",
            objective="Choose path"
        )

        session = board.create_session(request, "Path selection")

        opt1 = board.add_option(
            session.session_id,
            "Option A",
            "Conservative approach",
            pros=["Low risk"],
            cons=["Slower growth"]
        )

        opt2 = board.add_option(
            session.session_id,
            "Option B",
            "Aggressive approach",
            pros=["Fast growth"],
            cons=["Higher risk"]
        )

        assert opt1 is not None
        assert opt2 is not None
        assert len(session.options) == 2

    def test_score_options(self):
        """Test scoring options."""
        registry = create_default_hierarchy()
        board = DecisionBoard(registry)

        request = create_request(
            requester="council_manager",
            target_agent="decision_board",
            objective="Score test"
        )

        business = {
            "stage": "BUILDING",
            "metrics": {"validation_score": 0.7, "build_progress": 0.4}
        }

        session = board.create_session(request, "Scoring test", context={"business": business})
        board.add_option(session.session_id, "Test Option", "For scoring")

        result = board.score_options(session.session_id, business)
        assert result is True

        session = board.get_session(session.session_id)
        assert session.options[0].overall_score > 0

    def test_cast_vote(self):
        """Test casting a vote."""
        registry = create_default_hierarchy()
        board = DecisionBoard(registry)

        request = create_request(
            requester="council_manager",
            target_agent="decision_board",
            objective="Vote test"
        )

        session = board.create_session(request, "Voting test")
        board.add_option(session.session_id, "Test Option", "For voting")

        vote = board.cast_vote(
            session.session_id,
            "ceo",
            "approve",
            rationale="Aligns with goals"
        )

        assert vote is not None
        assert vote.vote == "approve"

    def test_full_decision_workflow(self):
        """Test complete decision workflow."""
        registry = create_default_hierarchy()
        board = DecisionBoard(registry)

        request = create_request(
            requester="council_manager",
            target_agent="decision_board",
            objective="Full workflow test"
        )

        business = {
            "stage": "VALIDATING",
            "metrics": {"validation_score": 0.65}
        }

        # Create session
        session = board.create_session(request, "Full test", context={"business": business})

        # Add options
        board.add_option(session.session_id, "Option 1", "First choice")
        board.add_option(session.session_id, "Option 2", "Second choice")

        # Score
        board.score_options(session.session_id, business)

        # Vote
        board.auto_vote(session.session_id)

        # Decide
        decision = board.decide(session.session_id)

        assert decision is not None
        assert decision.decision != ""
        assert decision.confidence > 0

    def test_evaluate_single(self):
        """Test single recommendation evaluation."""
        registry = create_default_hierarchy()
        board = DecisionBoard(registry)

        request = create_request(
            requester="council_manager",
            target_agent="decision_board",
            objective="Evaluate recommendation"
        )

        business = {
            "stage": "BUILDING",
            "metrics": {"validation_score": 0.8, "build_progress": 0.6}
        }

        record, actions = board.evaluate_single(
            request,
            "Proceed with current approach",
            business
        )

        assert record is not None
        assert record.decision != ""
        assert len(actions) > 0


# ============================================================================
# Test Chief Orchestrator
# ============================================================================

class TestChiefOrchestrator:
    """Tests for chief orchestrator."""

    def test_orchestrator_creation(self):
        """Test creating orchestrator."""
        orchestrator = ChiefOrchestrator()

        assert orchestrator.registry is not None
        assert orchestrator.logger is not None
        assert orchestrator.council is not None
        assert orchestrator.board is not None

    def test_direct_execution_routing(self):
        """Test simple request routing."""
        orchestrator = ChiefOrchestrator()

        business = {
            "id": "biz_test",
            "stage": "OPERATING",
            "metrics": {"performance": 0.8}
        }

        result = orchestrator.orchestrate(
            objective="Execute routine operation",
            business=business,
            requester="coo"
        )

        assert result is not None
        assert result.success is True

    def test_council_routing(self):
        """Test strategic request routes to council."""
        orchestrator = ChiefOrchestrator()

        business = {
            "id": "biz_strat",
            "stage": "DISCOVERED",
            "metrics": {"validation_score": 0.3}
        }

        result = orchestrator.orchestrate(
            objective="Evaluate strategy and direction",
            business=business,
            requester="principal"
        )

        assert result is not None
        assert "council_manager" in result.execution_path or "decision_board" in result.execution_path

    def test_board_routing(self):
        """Test decision request routes to board."""
        orchestrator = ChiefOrchestrator()

        business = {
            "id": "biz_decide",
            "stage": "BUILDING",
            "metrics": {"build_progress": 0.5}
        }

        result = orchestrator.orchestrate(
            objective="Decide on next action",
            business=business,
            requester="ceo"
        )

        assert result is not None
        assert result.routing in [
            RoutingDecision.BOARD_DECISION,
            RoutingDecision.COUNCIL_ADVICE,
            RoutingDecision.C_SUITE_DELEGATION
        ]

    def test_critical_priority_handling(self):
        """Test critical priority gets proper handling."""
        orchestrator = ChiefOrchestrator()

        result = orchestrator.orchestrate(
            objective="Critical issue needs resolution",
            priority="critical",
            requester="principal"
        )

        assert result is not None
        # Critical should either require approval or go to board
        assert result.routing in [
            RoutingDecision.BOARD_DECISION,
            RoutingDecision.REQUIRES_APPROVAL
        ]

    def test_department_execution(self):
        """Test request routes to appropriate department."""
        orchestrator = ChiefOrchestrator()

        business = {
            "id": "biz_research",
            "stage": "VALIDATING",
            "metrics": {}
        }

        result = orchestrator.orchestrate(
            objective="Research market opportunity",
            business=business,
            requester="ceo"
        )

        assert result is not None
        assert result.success is True

    def test_orchestration_history(self):
        """Test orchestration history tracking."""
        orchestrator = ChiefOrchestrator()

        # Execute a few requests
        orchestrator.orchestrate("Request 1", requester="principal")
        orchestrator.orchestrate("Request 2", requester="ceo")

        history = orchestrator.get_history()
        assert len(history) >= 2

    def test_get_result_by_id(self):
        """Test retrieving result by request ID."""
        orchestrator = ChiefOrchestrator()

        result = orchestrator.orchestrate(
            objective="Trackable request",
            requester="principal"
        )

        retrieved = orchestrator.get_result(result.request_id)
        assert retrieved is not None
        assert retrieved.request_id == result.request_id


# ============================================================================
# Test Integration
# ============================================================================

class TestHierarchyIntegration:
    """Integration tests for hierarchy with existing workflow engine."""

    def test_hierarchy_components_connected(self):
        """Test all hierarchy components are connected."""
        orchestrator = ChiefOrchestrator()

        # Check registry has agents
        assert orchestrator.registry.count() > 0

        # Check council has registry
        advisors = orchestrator.council.get_advisors()
        assert len(advisors) > 0

        # Check board has registry
        members = orchestrator.board.get_board_members()
        assert len(members) > 0

    def test_full_workflow_through_hierarchy(self):
        """Test complete workflow from orchestrator through layers."""
        orchestrator = ChiefOrchestrator()

        business = {
            "id": "integration_test",
            "stage": "VALIDATING",
            "opportunity": {"idea": "Test business idea"},
            "metrics": {
                "validation_score": 0.5,
                "build_progress": 0.0,
                "performance": 0.0,
                "failure_count": 0
            }
        }

        # Strategic request should flow through council and board
        result = orchestrator.orchestrate(
            objective="Assess strategic options and decide direction",
            business=business,
            requester="principal",
            priority="high"
        )

        assert result is not None
        assert result.success is True
        assert len(result.execution_path) > 1  # Went through multiple layers

    def test_event_logging_through_orchestration(self):
        """Test events are logged during orchestration."""
        orchestrator = ChiefOrchestrator()

        # Clear any existing events
        orchestrator.logger.clear()

        result = orchestrator.orchestrate(
            objective="Test event logging",
            requester="principal"
        )

        events = orchestrator.logger.get_events()
        assert len(events) > 0  # Events were logged

    def test_approval_integration(self):
        """Test approval flow integration."""
        orchestrator = ChiefOrchestrator()

        # Add a strict policy
        from core.approval_manager import ApprovalPolicy
        orchestrator.approval.add_policy(ApprovalPolicy(
            policy_id="test_strict",
            name="Test Strict",
            description="Test policy",
            action_patterns=["strict_*"],
            classification=ApprovalClass.REQUIRES_APPROVAL,
            approvers=["principal"],
            priority=95
        ))

        result = orchestrator.orchestrate(
            objective="Execute strict action",
            requester="dept_operations"
        )

        # Result should be success or require approval based on routing
        assert result is not None

    def test_hierarchy_with_different_stages(self):
        """Test hierarchy handles different business stages."""
        orchestrator = ChiefOrchestrator()

        stages = ["DISCOVERED", "VALIDATING", "BUILDING", "SCALING", "OPERATING"]

        for stage in stages:
            business = {
                "id": f"stage_test_{stage}",
                "stage": stage,
                "metrics": {
                    "validation_score": 0.7,
                    "build_progress": 0.6,
                    "performance": 0.7
                }
            }

            result = orchestrator.orchestrate(
                objective="Process for stage",
                business=business,
                requester="ceo"
            )

            assert result is not None
            assert result.success is True, f"Failed for stage {stage}"
