"""
Tests for Business Discovery Layer.

Tests discovery modules, opportunity evaluation, and persistence.
"""

import pytest
from datetime import datetime

from core.discovery_models import (
    RawInput, OpportunityHypothesis, OpportunityScore, OpportunityRecommendation,
    OpportunityRecord, OperatorConstraints, InputType, OpportunityStatus,
    RecommendationAction, MonetizationPath,
)
from core.idea_intake import intake_raw_input, normalize_to_hypotheses
from core.opportunity_scorer import score_opportunity
from core.opportunity_evaluator import evaluate_opportunity
from core.discovery_pipeline import process_discovery_input, rescore_opportunity
from core.opportunity_registry import OpportunityRegistry
from core.state_store import StateStore, StateStoreConfig


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_state_store(tmp_path):
    """Create temporary state store for testing."""
    db_path = tmp_path / "test_state.db"
    config = StateStoreConfig(db_path=str(db_path))
    store = StateStore(config)
    store.initialize()
    yield store
    store.close()


@pytest.fixture
def default_constraints():
    """Default operator constraints for testing."""
    return OperatorConstraints()


@pytest.fixture
def sample_idea_text():
    """Sample business idea text."""
    return (
        "I want to build a SaaS tool that helps small businesses automate their "
        "customer outreach. The market is growing and there's demand for simple, "
        "affordable automation tools."
    )


# =============================================================================
# Idea Intake Tests
# =============================================================================

class TestIdeaIntake:
    """Tests for idea intake module."""

    def test_intake_raw_input(self):
        """Test creating raw input from text."""
        raw_input = intake_raw_input(
            raw_text="Build a marketplace for freelancers",
            submitted_by="test_user",
            tags=["marketplace", "freelance"],
        )

        assert raw_input.input_id.startswith("input-")
        assert raw_input.raw_text == "Build a marketplace for freelancers"
        assert raw_input.submitted_by == "test_user"
        assert "marketplace" in raw_input.tags

    def test_classify_input_type_idea(self):
        """Test input type classification for ideas."""
        raw_input = intake_raw_input("Build a platform for online courses")
        assert raw_input.input_type == InputType.IDEA

    def test_classify_input_type_problem(self):
        """Test input type classification for problems."""
        raw_input = intake_raw_input(
            "The problem is that small businesses struggle with accounting"
        )
        assert raw_input.input_type == InputType.PROBLEM

    def test_classify_input_type_opportunity(self):
        """Test input type classification for opportunities."""
        raw_input = intake_raw_input(
            "There's a growing market opportunity in remote work tools"
        )
        assert raw_input.input_type == InputType.OPPORTUNITY

    def test_normalize_to_hypotheses(self, sample_idea_text):
        """Test converting raw input to hypotheses."""
        raw_input = intake_raw_input(sample_idea_text)
        hypotheses = normalize_to_hypotheses(raw_input)

        assert len(hypotheses) > 0
        hypothesis = hypotheses[0]
        assert hypothesis.title
        assert hypothesis.target_audience
        assert hypothesis.monetization_path != MonetizationPath.UNCLEAR


# =============================================================================
# Opportunity Scoring Tests
# =============================================================================

class TestOpportunityScoring:
    """Tests for opportunity scoring."""

    @pytest.fixture
    def sample_hypothesis(self):
        """Sample opportunity hypothesis."""
        return OpportunityHypothesis(
            hypothesis_id="test-hyp-001",
            title="SaaS automation tool",
            description="Tool for automating customer outreach",
            target_audience="small business",
            problem_addressed="Manual outreach is time-consuming",
            proposed_solution="Automated email sequences",
            monetization_path=MonetizationPath.SUBSCRIPTION,
            likely_domains=["growth", "automation"],
            market_size_estimate="medium",
            competition_level="medium",
        )

    def test_score_opportunity(self, sample_hypothesis, default_constraints):
        """Test scoring an opportunity."""
        score = score_opportunity(sample_hypothesis, default_constraints)

        assert 0.0 <= score.overall_score <= 1.0
        assert 0.0 <= score.market_attractiveness <= 1.0
        assert 0.0 <= score.constraint_fit <= 1.0
        assert 0.0 <= score.confidence <= 1.0

    def test_subscription_monetization_clarity(self):
        """Test that subscription has high monetization clarity."""
        hypothesis = OpportunityHypothesis(
            hypothesis_id="test",
            title="Test",
            description="Test",
            target_audience="test",
            problem_addressed="test",
            proposed_solution="test",
            monetization_path=MonetizationPath.SUBSCRIPTION,
        )
        constraints = OperatorConstraints()
        score = score_opportunity(hypothesis, constraints)

        assert score.monetization_clarity > 0.7

    def test_constraint_fit_affects_score(self):
        """Test that operator constraints affect scoring."""
        # Test with an opportunity that strongly benefits from automation
        hypothesis = OpportunityHypothesis(
            hypothesis_id="test",
            title="Automated SaaS platform",
            description="Highly automatable business",
            target_audience="test",
            problem_addressed="test",
            proposed_solution="test",
            monetization_path=MonetizationPath.SUBSCRIPTION,
            likely_domains=["automation"],  # High automation potential
        )

        # High automation preference
        high_automation = OperatorConstraints(automation_preference="high")
        score_high_auto = score_opportunity(hypothesis, high_automation)

        # Low automation preference
        low_automation = OperatorConstraints(automation_preference="low")
        score_low_auto = score_opportunity(hypothesis, low_automation)

        # High automation preference should yield higher constraint fit for automatable opportunity
        assert score_high_auto.constraint_fit > score_low_auto.constraint_fit


# =============================================================================
# Opportunity Evaluation Tests
# =============================================================================

class TestOpportunityEvaluation:
    """Tests for opportunity evaluation."""

    @pytest.fixture
    def high_score_opportunity(self):
        """High-scoring opportunity."""
        return OpportunityScore(
            opportunity_id="test",
            market_attractiveness=0.9,
            monetization_clarity=0.9,
            startup_complexity=0.3,
            capital_intensity=0.2,
            operational_burden=0.3,
            speed_to_revenue=0.8,
            overall_score=0.80,
            confidence=0.8,
        )

    def test_evaluate_high_score_pursue(self, high_score_opportunity, default_constraints):
        """Test that high scores recommend pursue."""
        hypothesis = OpportunityHypothesis(
            hypothesis_id="test",
            title="Test",
            description="Test",
            target_audience="test",
            problem_addressed="test",
            proposed_solution="test",
            monetization_path=MonetizationPath.SUBSCRIPTION,
        )

        recommendation = evaluate_opportunity(
            hypothesis,
            high_score_opportunity,
            default_constraints,
        )

        assert recommendation.action == RecommendationAction.PURSUE_NOW
        assert len(recommendation.next_steps) > 0

    def test_evaluate_generates_warnings(self):
        """Test that evaluation generates appropriate warnings."""
        hypothesis = OpportunityHypothesis(
            hypothesis_id="test",
            title="Test",
            description="Test",
            target_audience="test",
            problem_addressed="test",
            proposed_solution="test",
            monetization_path=MonetizationPath.UNCLEAR,
            competition_level="high",
        )

        score = OpportunityScore(
            opportunity_id="test",
            monetization_clarity=0.2,
            risk_level=0.8,
            overall_score=0.5,
        )

        constraints = OperatorConstraints()
        recommendation = evaluate_opportunity(hypothesis, score, constraints)

        assert len(recommendation.warnings) > 0


# =============================================================================
# Discovery Pipeline Tests
# =============================================================================

class TestDiscoveryPipeline:
    """Tests for discovery pipeline."""

    def test_process_discovery_input_end_to_end(self, sample_idea_text, default_constraints):
        """Test full pipeline from raw text to opportunity records."""
        records = process_discovery_input(
            raw_text=sample_idea_text,
            constraints=default_constraints,
        )

        assert len(records) > 0
        record = records[0]

        assert record.opportunity_id
        assert record.hypothesis
        assert record.score
        assert record.recommendation
        assert record.status == OpportunityStatus.EVALUATED

    def test_rescore_opportunity(self, sample_idea_text, default_constraints):
        """Test rescoring with new constraints."""
        # Initial evaluation
        records = process_discovery_input(
            raw_text=sample_idea_text,
            constraints=default_constraints,
        )
        original_record = records[0]
        original_score = original_record.score.overall_score

        # Rescore with different constraints
        new_constraints = OperatorConstraints(
            automation_preference="low",
            hands_on_vs_hands_off="hands_on",
        )

        updated_record = rescore_opportunity(original_record, new_constraints)

        # Score should potentially differ
        assert updated_record.score is not None
        assert updated_record.operator_constraints_snapshot is not None


# =============================================================================
# Opportunity Registry Tests
# =============================================================================

class TestOpportunityRegistry:
    """Tests for opportunity registry and persistence."""

    def test_save_and_retrieve_opportunity(self, temp_state_store, default_constraints):
        """Test saving and retrieving opportunities."""
        registry = OpportunityRegistry(temp_state_store)

        # Create and save opportunity
        records = process_discovery_input(
            raw_text="Build a tool for project management",
            constraints=default_constraints,
        )
        record = records[0]
        registry.save_opportunity(record)

        # Retrieve
        retrieved = registry.get_opportunity(record.opportunity_id)

        assert retrieved is not None
        assert retrieved.opportunity_id == record.opportunity_id
        assert retrieved.hypothesis.title == record.hypothesis.title

    def test_list_opportunities(self, temp_state_store, default_constraints):
        """Test listing opportunities."""
        registry = OpportunityRegistry(temp_state_store)

        # Create multiple opportunities
        ideas = [
            "Build a SaaS tool",
            "Create a marketplace",
            "Start a consulting service",
        ]

        for idea in ideas:
            records = process_discovery_input(idea, default_constraints)
            for record in records:
                registry.save_opportunity(record)

        # List all
        all_opps = registry.list_opportunities(limit=100)
        assert len(all_opps) >= 3

    def test_update_status(self, temp_state_store, default_constraints):
        """Test updating opportunity status."""
        registry = OpportunityRegistry(temp_state_store)

        # Create opportunity
        records = process_discovery_input(
            raw_text="Build a mobile app",
            constraints=default_constraints,
        )
        record = records[0]
        registry.save_opportunity(record)

        # Update status
        updated = registry.update_status(
            record.opportunity_id,
            OpportunityStatus.PURSUE,
            note="Approved by principal",
        )

        assert updated is not None
        assert updated.status == OpportunityStatus.PURSUE
        assert len(updated.status_history) > 0

    def test_rank_opportunities(self, temp_state_store, default_constraints):
        """Test ranking opportunities by score."""
        registry = OpportunityRegistry(temp_state_store)

        # Create opportunities with varying quality
        ideas = [
            "Build a highly scalable SaaS platform with clear monetization",  # Likely high score
            "Unclear business idea without clear market",  # Likely low score
        ]

        for idea in ideas:
            records = process_discovery_input(idea, default_constraints)
            for record in records:
                registry.save_opportunity(record)

        # Rank
        ranked = registry.rank_opportunities(limit=100)

        assert len(ranked) >= 2
        # First should have higher or equal score than second
        assert ranked[0].score.overall_score >= ranked[1].score.overall_score

    def test_get_summary_stats(self, temp_state_store, default_constraints):
        """Test getting opportunity summary statistics."""
        registry = OpportunityRegistry(temp_state_store)

        # Create opportunities
        for i in range(5):
            records = process_discovery_input(
                f"Business idea {i}",
                default_constraints,
            )
            for record in records:
                registry.save_opportunity(record)

        stats = registry.get_summary_stats()

        assert stats["total"] >= 5
        assert "by_status" in stats
        assert "avg_score" in stats
        assert "top_scored" in stats


# =============================================================================
# Integration Tests
# =============================================================================

class TestDiscoveryIntegration:
    """Integration tests for discovery layer."""

    def test_discovery_to_persistence_flow(self, temp_state_store):
        """Test full flow from input to persistence."""
        constraints = OperatorConstraints(
            max_initial_capital=10000,
            automation_preference="high",
        )

        # Process input
        records = process_discovery_input(
            raw_text="Build an AI-powered automation tool for marketers with subscription pricing",
            constraints=constraints,
            submitted_by="principal",
            tags=["ai", "automation", "saas"],
        )

        assert len(records) > 0
        record = records[0]

        # Save to registry
        registry = OpportunityRegistry(temp_state_store)
        registry.save_opportunity(record)

        # Verify persistence
        retrieved = registry.get_opportunity(record.opportunity_id)
        assert retrieved is not None
        assert "ai" in retrieved.tags
        assert retrieved.hypothesis.monetization_path == MonetizationPath.SUBSCRIPTION

    def test_multiple_hypotheses_from_complex_input(self):
        """Test handling complex input that could generate multiple interpretations."""
        # Currently generates 1 hypothesis, but architecture supports multiple
        constraints = OperatorConstraints()

        records = process_discovery_input(
            raw_text=(
                "Freelancers struggle with invoicing and time tracking. "
                "Could build either a simple SaaS tool or a full platform marketplace."
            ),
            constraints=constraints,
        )

        # Should generate at least one hypothesis
        assert len(records) >= 1
        record = records[0]

        # Should capture the problem
        assert "freelancer" in record.hypothesis.target_audience.lower() or \
               "freelancer" in record.hypothesis.description.lower()
