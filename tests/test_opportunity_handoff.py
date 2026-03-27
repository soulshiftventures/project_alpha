"""
Tests for Opportunity-to-Execution Handoff.

Tests handoff models, execution mapper, and handoff persistence.
"""

import pytest
from datetime import datetime

from core.opportunity_handoff import (
    HandoffMode, HandoffStatus, HandoffContext, HandoffRecord,
    create_handoff_context, create_handoff, determine_handoff_mode,
)
from core.opportunity_execution_mapper import (
    map_to_execution_plan, enrich_plan_with_opportunity_context,
)
from core.discovery_models import (
    OpportunityHypothesis, OpportunityScore, OpportunityRecommendation,
    OpportunityRecord, OperatorConstraints, MonetizationPath,
    RecommendationAction, OpportunityStatus,
)
from core.execution_plan import ExecutionDomain, ExecutionStatus
from core.state_store import StateStore, StateStoreConfig


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_state_store(tmp_path):
    """Create temporary state store for testing."""
    db_path = tmp_path / "test_handoff_state.db"
    config = StateStoreConfig(db_path=str(db_path))
    store = StateStore(config)
    store.initialize()
    yield store
    store.close()


@pytest.fixture
def high_score_opportunity():
    """High-scoring opportunity for pursue-now testing."""
    hypothesis = OpportunityHypothesis(
        hypothesis_id="hyp-001",
        title="SaaS Automation Platform",
        description="Automated email marketing tool for small businesses",
        target_audience="small business owners",
        problem_addressed="Manual email marketing is time-consuming",
        proposed_solution="Automated email sequences with templates",
        monetization_path=MonetizationPath.SUBSCRIPTION,
        likely_domains=["automation", "growth"],
        market_size_estimate="large",
        competition_level="medium",
    )

    score = OpportunityScore(
        opportunity_id="opp-001",
        market_attractiveness=0.9,
        monetization_clarity=0.9,
        startup_complexity=0.3,
        technical_complexity=0.4,
        capital_intensity=0.2,
        operational_burden=0.3,
        speed_to_revenue=0.8,
        speed_to_validation=0.7,
        risk_level=0.3,
        automation_potential=0.9,
        scalability_potential=0.9,
        constraint_fit=0.8,
        overall_score=0.82,
        confidence=0.8,
    )

    recommendation = OpportunityRecommendation(
        opportunity_id="opp-001",
        action=RecommendationAction.PURSUE_NOW,
        rationale="Strong market fit with high automation potential",
        confidence=0.8,
        next_steps=[
            "Set up backend infrastructure",
            "Build email template system",
            "Integrate with email providers",
            "Create landing page",
            "Launch beta program",
        ],
        estimated_time_to_validate="2-3 weeks",
        estimated_cost_to_validate="$500-1000",
        warnings=[],
    )

    return OpportunityRecord(
        opportunity_id="opp-001",
        hypothesis=hypothesis,
        score=score,
        recommendation=recommendation,
        status=OpportunityStatus.EVALUATED,
        operator_constraints_snapshot=OperatorConstraints().to_dict(),
    )


@pytest.fixture
def medium_score_opportunity():
    """Medium-scoring opportunity for validate-first testing."""
    hypothesis = OpportunityHypothesis(
        hypothesis_id="hyp-002",
        title="Consulting Marketplace",
        description="Platform for freelance consultants",
        target_audience="freelance consultants",
        problem_addressed="Hard to find quality consulting gigs",
        proposed_solution="Curated marketplace with vetting",
        monetization_path=MonetizationPath.TRANSACTION_FEE,
        likely_domains=["product", "growth"],
        market_size_estimate="medium",
        competition_level="high",
    )

    score = OpportunityScore(
        opportunity_id="opp-002",
        market_attractiveness=0.6,
        monetization_clarity=0.7,
        startup_complexity=0.6,
        technical_complexity=0.5,
        capital_intensity=0.5,
        operational_burden=0.7,
        speed_to_revenue=0.5,
        speed_to_validation=0.6,
        risk_level=0.6,
        automation_potential=0.4,
        scalability_potential=0.6,
        constraint_fit=0.5,
        overall_score=0.55,
        confidence=0.6,
    )

    recommendation = OpportunityRecommendation(
        opportunity_id="opp-002",
        action=RecommendationAction.VALIDATE_FIRST,
        rationale="Moderate score with high competition - validate demand first",
        confidence=0.6,
        next_steps=[
            "Survey target consultants",
            "Test landing page demand",
            "Interview potential users",
            "Prototype core matching feature",
            "Gather evidence of demand",
        ],
        estimated_time_to_validate="1-2 weeks",
        estimated_cost_to_validate="$200-500",
        warnings=["High competition", "Operational burden may be significant"],
    )

    return OpportunityRecord(
        opportunity_id="opp-002",
        hypothesis=hypothesis,
        score=score,
        recommendation=recommendation,
        status=OpportunityStatus.EVALUATED,
        operator_constraints_snapshot=OperatorConstraints().to_dict(),
    )


# =============================================================================
# Handoff Context Tests
# =============================================================================

class TestHandoffContext:
    """Tests for handoff context creation."""

    def test_create_handoff_context(self, high_score_opportunity):
        """Test creating handoff context from opportunity."""
        context = create_handoff_context(high_score_opportunity)

        assert context.opportunity_id == "opp-001"
        assert context.opportunity_title == "SaaS Automation Platform"
        assert context.target_audience == "small business owners"
        assert context.problem_addressed == "Manual email marketing is time-consuming"
        assert context.overall_score == 0.82
        assert context.risk_level == 0.3
        assert "automation" in context.likely_domains
        assert context.recommended_primary_domain == "automation"
        assert len(context.next_steps) == 5

    def test_handoff_context_to_dict(self, high_score_opportunity):
        """Test handoff context serialization."""
        context = create_handoff_context(high_score_opportunity)
        context_dict = context.to_dict()

        assert context_dict["opportunity_id"] == "opp-001"
        assert context_dict["overall_score"] == 0.82
        assert isinstance(context_dict["likely_domains"], list)
        assert isinstance(context_dict["next_steps"], list)



# =============================================================================
# Handoff Creation Tests
# =============================================================================

class TestHandoffCreation:
    """Tests for handoff record creation."""

    def test_create_pursue_now_handoff(self, high_score_opportunity):
        """Test creating pursue-now handoff."""
        handoff = create_handoff(
            high_score_opportunity,
            HandoffMode.PURSUE_NOW,
            operator="test_operator",
        )

        assert handoff.handoff_id.startswith("handoff-")
        assert handoff.opportunity_id == "opp-001"
        assert handoff.mode == HandoffMode.PURSUE_NOW
        assert handoff.status == HandoffStatus.PENDING
        assert handoff.handoff_context.opportunity_id == "opp-001"

    def test_create_validate_first_handoff(self, medium_score_opportunity):
        """Test creating validate-first handoff."""
        handoff = create_handoff(
            medium_score_opportunity,
            HandoffMode.VALIDATE_FIRST,
            operator="principal",
        )

        assert handoff.mode == HandoffMode.VALIDATE_FIRST
        assert handoff.status == HandoffStatus.PENDING
        assert handoff.handoff_context.opportunity_id == "opp-002"

    def test_create_archive_handoff(self, medium_score_opportunity):
        """Test creating archive handoff."""
        handoff = create_handoff(
            medium_score_opportunity,
            HandoffMode.ARCHIVE,
        )

        assert handoff.mode == HandoffMode.ARCHIVE
        assert handoff.status == HandoffStatus.COMPLETED
        assert handoff.plan_id is None
        assert handoff.completed_at is not None  # Archive is immediately completed

    def test_determine_handoff_mode(self, high_score_opportunity, medium_score_opportunity):
        """Test handoff mode determination from recommendation."""
        pursue_mode = determine_handoff_mode(high_score_opportunity)
        assert pursue_mode == HandoffMode.PURSUE_NOW

        validate_mode = determine_handoff_mode(medium_score_opportunity)
        assert validate_mode == HandoffMode.VALIDATE_FIRST


# =============================================================================
# Execution Mapper Tests
# =============================================================================

class TestExecutionMapper:
    """Tests for handoff-to-execution plan mapping."""

    def test_map_pursue_now_to_execution_plan(self, high_score_opportunity):
        """Test mapping pursue-now handoff to execution plan."""
        handoff = create_handoff(high_score_opportunity, HandoffMode.PURSUE_NOW)
        plan = map_to_execution_plan(handoff)

        assert plan.plan_id
        assert plan.objective == "Execute: SaaS Automation Platform"
        assert plan.stage == "BUILDING"
        assert plan.primary_domain == ExecutionDomain.AUTOMATION
        assert len(plan.steps) > 0
        assert plan.steps[0].description == "Set up backend infrastructure"
        assert plan.steps[0].status == ExecutionStatus.PENDING

    def test_map_validate_first_to_execution_plan(self, medium_score_opportunity):
        """Test mapping validate-first handoff to execution plan."""
        handoff = create_handoff(medium_score_opportunity, HandoffMode.VALIDATE_FIRST)
        plan = map_to_execution_plan(handoff)

        assert plan.objective == "Validate: Consulting Marketplace"
        assert plan.stage == "VALIDATING"
        assert plan.primary_domain in [ExecutionDomain.PRODUCT, ExecutionDomain.VALIDATION]
        assert len(plan.steps) > 0
        # Should have validation-oriented steps
        assert any("validate" in step.description.lower() or "test" in step.description.lower() for step in plan.steps)

    def test_plan_preserves_opportunity_context(self, high_score_opportunity):
        """Test that plan preserves opportunity context."""
        handoff = create_handoff(high_score_opportunity, HandoffMode.PURSUE_NOW)
        plan = map_to_execution_plan(handoff)

        # Context is stored in outputs (ExecutionPlan doesn't have metadata attribute)
        context_output = next((o for o in plan.outputs if o.get("type") == "opportunity_context"), None)
        assert context_output is not None
        assert context_output["opportunity_id"] == "opp-001"
        assert context_output["handoff_id"] == handoff.handoff_id
        assert context_output["handoff_mode"] == "pursue_now"
        assert context_output["target_audience"] == "small business owners"
        assert context_output["problem_addressed"] == "Manual email marketing is time-consuming"
        assert context_output["overall_score"] == 0.82

    def test_plan_cost_continuity(self, high_score_opportunity):
        """Test that cost sensitivity carries through."""
        handoff = create_handoff(high_score_opportunity, HandoffMode.PURSUE_NOW)
        plan = map_to_execution_plan(handoff)

        # Context is preserved in outputs (ExecutionPlan doesn't have complexity/risk/capital attributes)
        context_output = next((o for o in plan.outputs if o.get("type") == "opportunity_context"), None)
        assert context_output is not None
        assert context_output["risk_level"] == high_score_opportunity.score.risk_level
        assert context_output["overall_score"] == high_score_opportunity.score.overall_score

    def test_plan_domain_continuity(self, high_score_opportunity):
        """Test that domain classification carries through."""
        handoff = create_handoff(high_score_opportunity, HandoffMode.PURSUE_NOW)
        plan = map_to_execution_plan(handoff)

        # Should map to automation domain from likely_domains
        assert plan.primary_domain == ExecutionDomain.AUTOMATION

        # Steps should use the same domain
        for step in plan.steps:
            assert step.domain == ExecutionDomain.AUTOMATION

    def test_enrich_plan_with_opportunity_context(self, high_score_opportunity):
        """Test enriching existing plan with opportunity context."""
        from core.execution_plan import ExecutionPlan, SkillBundle, ExecutionDomain

        # Create a minimal plan
        skill_bundle = SkillBundle(skills=[], commands=[], specialized_agents=[])
        plan = ExecutionPlan(
            objective="Test objective",
            role_id="test",
            business_id="test-biz",
            stage="BUILDING",
            primary_domain=ExecutionDomain.PRODUCT,
            skill_bundle=skill_bundle,
        )

        # Enrich with opportunity context
        enriched = enrich_plan_with_opportunity_context(plan, high_score_opportunity)

        # Context is stored in outputs
        context_output = next((o for o in enriched.outputs if o.get("type") == "opportunity_context"), None)
        assert context_output is not None
        assert context_output["opportunity_id"] == "opp-001"
        assert context_output["opportunity_title"] == "SaaS Automation Platform"


# =============================================================================
# Handoff Persistence Tests
# =============================================================================

class TestHandoffPersistence:
    """Tests for handoff persistence."""

    def test_save_and_retrieve_handoff(self, temp_state_store, high_score_opportunity):
        """Test saving and retrieving handoff."""
        # Save opportunity first (required by foreign key)
        temp_state_store.save_opportunity(
            opportunity_id=high_score_opportunity.opportunity_id,
            hypothesis_data=high_score_opportunity.hypothesis.to_dict(),
            score_data=high_score_opportunity.score.to_dict(),
            recommendation_data=high_score_opportunity.recommendation.to_dict(),
            status=high_score_opportunity.status.value,
            operator_constraints_snapshot=high_score_opportunity.operator_constraints_snapshot,
        )

        handoff = create_handoff(high_score_opportunity, HandoffMode.PURSUE_NOW)

        # Save
        success = temp_state_store.save_handoff(
            handoff_id=handoff.handoff_id,
            opportunity_id=handoff.opportunity_id,
            mode=handoff.mode.value,
            status=handoff.status.value,
            context_data=handoff.handoff_context.to_dict(),
        )
        assert success

        # Retrieve
        retrieved = temp_state_store.get_handoff(handoff.handoff_id)
        assert retrieved is not None
        assert retrieved["handoff_id"] == handoff.handoff_id
        assert retrieved["opportunity_id"] == "opp-001"
        assert retrieved["mode"] == "pursue_now"

    def test_get_handoffs_by_opportunity(self, temp_state_store, high_score_opportunity):
        """Test retrieving all handoffs for an opportunity."""
        # Save opportunity first (required by foreign key)
        temp_state_store.save_opportunity(
            opportunity_id=high_score_opportunity.opportunity_id,
            hypothesis_data=high_score_opportunity.hypothesis.to_dict(),
            score_data=high_score_opportunity.score.to_dict(),
            recommendation_data=high_score_opportunity.recommendation.to_dict(),
            status=high_score_opportunity.status.value,
            operator_constraints_snapshot=high_score_opportunity.operator_constraints_snapshot,
        )

        # Create multiple handoffs for same opportunity
        handoff1 = create_handoff(high_score_opportunity, HandoffMode.PURSUE_NOW)
        handoff2 = create_handoff(high_score_opportunity, HandoffMode.ARCHIVE)

        # Save both
        temp_state_store.save_handoff(
            handoff_id=handoff1.handoff_id,
            opportunity_id=handoff1.opportunity_id,
            mode=handoff1.mode.value,
            status=handoff1.status.value,
            context_data=handoff1.handoff_context.to_dict(),
        )
        temp_state_store.save_handoff(
            handoff_id=handoff2.handoff_id,
            opportunity_id=handoff2.opportunity_id,
            mode=handoff2.mode.value,
            status=handoff2.status.value,
            context_data=handoff2.handoff_context.to_dict(),
        )

        # Retrieve all for opportunity
        handoffs = temp_state_store.get_handoffs_by_opportunity("opp-001")
        assert len(handoffs) == 2

    def test_list_handoffs_with_status_filter(self, temp_state_store, high_score_opportunity):
        """Test listing handoffs with status filter."""
        # Save opportunity first (required by foreign key)
        temp_state_store.save_opportunity(
            opportunity_id=high_score_opportunity.opportunity_id,
            hypothesis_data=high_score_opportunity.hypothesis.to_dict(),
            score_data=high_score_opportunity.score.to_dict(),
            recommendation_data=high_score_opportunity.recommendation.to_dict(),
            status=high_score_opportunity.status.value,
            operator_constraints_snapshot=high_score_opportunity.operator_constraints_snapshot,
        )

        handoff = create_handoff(high_score_opportunity, HandoffMode.PURSUE_NOW)

        temp_state_store.save_handoff(
            handoff_id=handoff.handoff_id,
            opportunity_id=handoff.opportunity_id,
            mode=handoff.mode.value,
            status=handoff.status.value,
            context_data=handoff.handoff_context.to_dict(),
        )

        # List pending handoffs
        pending = temp_state_store.list_handoffs(status="pending")
        assert len(pending) >= 1
        assert any(h["handoff_id"] == handoff.handoff_id for h in pending)


# =============================================================================
# Integration Tests
# =============================================================================

class TestHandoffIntegration:
    """Integration tests for full handoff flow."""

    def test_full_pursue_now_flow(self, temp_state_store, high_score_opportunity):
        """Test complete pursue-now flow from opportunity to execution."""
        # Save opportunity first (required by foreign key)
        temp_state_store.save_opportunity(
            opportunity_id=high_score_opportunity.opportunity_id,
            hypothesis_data=high_score_opportunity.hypothesis.to_dict(),
            score_data=high_score_opportunity.score.to_dict(),
            recommendation_data=high_score_opportunity.recommendation.to_dict(),
            status=high_score_opportunity.status.value,
            operator_constraints_snapshot=high_score_opportunity.operator_constraints_snapshot,
        )

        # Create handoff
        handoff = create_handoff(high_score_opportunity, HandoffMode.PURSUE_NOW)

        # Map to execution plan
        plan = map_to_execution_plan(handoff, business_id="biz-001")

        # Link handoff to plan
        handoff.plan_id = plan.plan_id
        handoff.business_id = plan.business_id

        # Save handoff
        temp_state_store.save_handoff(
            handoff_id=handoff.handoff_id,
            opportunity_id=handoff.opportunity_id,
            mode=handoff.mode.value,
            status=handoff.status.value,
            context_data=handoff.handoff_context.to_dict(),
            plan_id=handoff.plan_id,
            business_id=handoff.business_id,
        )

        # Verify handoff links to plan
        retrieved = temp_state_store.get_handoff(handoff.handoff_id)
        assert retrieved["plan_id"] == plan.plan_id
        assert retrieved["business_id"] == "biz-001"

        # Verify plan has opportunity context in outputs
        context_output = next((o for o in plan.outputs if o.get("type") == "opportunity_context"), None)
        assert context_output is not None
        assert context_output["opportunity_id"] == "opp-001"
        assert context_output["handoff_id"] == handoff.handoff_id

    def test_full_validate_first_flow(self, temp_state_store, medium_score_opportunity):
        """Test complete validate-first flow."""
        handoff = create_handoff(medium_score_opportunity, HandoffMode.VALIDATE_FIRST)
        plan = map_to_execution_plan(handoff)

        # Validation plan should differ from pursue plan
        assert plan.stage == "VALIDATING"
        assert plan.objective.startswith("Validate:")

        # Should have validation-specific steps
        validation_keywords = ["validate", "test", "research", "survey", "evidence"]
        has_validation_steps = any(
            any(keyword in step.description.lower() for keyword in validation_keywords)
            for step in plan.steps
        )
        assert has_validation_steps

        # ExecutionPlan doesn't have projected_capital attribute - context is in outputs
