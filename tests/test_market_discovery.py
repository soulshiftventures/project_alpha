"""
Tests for Real Market Discovery Engine

Tests discovery engine, pain point scanner, opportunity generator, and ranker.
"""

import pytest
from core.market_discovery import (
    MarketDiscoveryEngine,
    DiscoveryInput,
    DiscoveryResult,
    OpportunityCandidate,
)
from core.pain_point_scanner import PainPointScanner, PainPoint
from core.opportunity_generator import OpportunityGenerator, GenerationContext
from core.opportunity_ranker import OpportunityRanker, RankingWeights


# =============================================================================
# Pain Point Scanner Tests
# =============================================================================

def test_pain_point_scanner_initialization():
    """Test pain point scanner initializes with database"""
    scanner = PainPointScanner()
    assert len(scanner.pain_point_database) > 0


def test_scan_pain_points_no_filter():
    """Test scanning all pain points with no filter"""
    scanner = PainPointScanner()
    pain_points = scanner.scan_pain_points()
    assert len(pain_points) > 0


def test_scan_pain_points_industry_filter():
    """Test scanning pain points by industry"""
    scanner = PainPointScanner()
    pain_points = scanner.scan_pain_points(industry="operations")
    assert len(pain_points) > 0
    # Verify all returned points have operations in impact areas
    for pain_point in pain_points:
        assert any("operations" in area.lower() for area in pain_point.impact_areas)


def test_scan_pain_points_customer_filter():
    """Test scanning pain points by customer type"""
    scanner = PainPointScanner()
    pain_points = scanner.scan_pain_points(customer_type="managers")
    assert len(pain_points) > 0


def test_pain_point_scoring():
    """Test pain point score calculation"""
    scanner = PainPointScanner()
    pain_point = PainPoint(
        description="Test pain point",
        severity="high",
        frequency="frequent",
        impact_areas=["operations"],
        affected_personas=["managers"],
        current_solutions=["manual"],
        solution_gaps=["inefficient"],
        monetization_potential="high",
    )
    score = scanner.score_pain_point(pain_point)
    assert 0.0 <= score <= 1.0
    # High severity + high frequency + high monetization should score high
    assert score > 0.7


def test_pain_point_ranking():
    """Test pain points are ranked by severity and frequency"""
    scanner = PainPointScanner()
    pain_points = scanner.scan_pain_points()
    # First result should be high/critical severity
    assert pain_points[0].severity in ["high", "critical"]


# =============================================================================
# Opportunity Generator Tests
# =============================================================================

def test_opportunity_generator_from_pain_points():
    """Test generating opportunities from pain points"""
    generator = OpportunityGenerator()
    context = GenerationContext(
        industry="operations",
        customer_type="managers",
    )
    candidates = generator.generate_from_pain_points(context, max_candidates=3)
    assert len(candidates) == 3
    assert all(isinstance(c, OpportunityCandidate) for c in candidates)


def test_opportunity_generator_from_theme():
    """Test generating opportunities from theme"""
    generator = OpportunityGenerator()
    context = GenerationContext(customer_type="developers")
    candidates = generator.generate_from_theme("AI automation", context, max_candidates=3)
    assert len(candidates) == 3
    assert all("AI" in c.title or "automation" in c.title.lower() for c in candidates)


def test_opportunity_candidate_structure():
    """Test opportunity candidate has all required fields"""
    generator = OpportunityGenerator()
    context = GenerationContext(problem_area="data")  # Use "data" which matches pain points
    candidates = generator.generate_from_pain_points(context, max_candidates=1)
    assert len(candidates) > 0, "Should generate at least one candidate"
    candidate = candidates[0]

    assert candidate.candidate_id
    assert candidate.title
    assert candidate.pain_point
    assert candidate.target_customer
    assert candidate.urgency in ["low", "medium", "high", "critical"]
    assert candidate.monetization_clarity in ["unclear", "emerging", "proven"]
    assert len(candidate.execution_domains) > 0
    assert candidate.automation_potential in ["low", "medium", "high"]
    assert candidate.complexity in ["low", "medium", "high"]
    assert candidate.recommended_action
    assert 0.0 <= candidate.confidence <= 1.0
    assert candidate.discovered_via
    assert candidate.discovered_at
    assert isinstance(candidate.raw_inputs, dict)


# =============================================================================
# Opportunity Ranker Tests
# =============================================================================

def test_opportunity_ranker_initialization():
    """Test ranker initializes with default weights"""
    ranker = OpportunityRanker()
    assert ranker.weights is not None


def test_opportunity_ranker_custom_weights():
    """Test ranker with custom weights"""
    weights = RankingWeights(
        urgency=0.5,
        monetization_clarity=0.3,
        automation_potential=0.1,
        complexity=0.05,
        confidence=0.05,
    )
    ranker = OpportunityRanker(weights)
    assert ranker.weights.urgency == 0.5


def test_calculate_score():
    """Test score calculation for a candidate"""
    ranker = OpportunityRanker()
    candidate = OpportunityCandidate(
        candidate_id="test-1",
        title="Test Opportunity",
        pain_point="Test pain point",
        target_customer="Test customer",
        urgency="high",
        monetization_clarity="proven",
        execution_domains=["automation"],
        automation_potential="high",
        complexity="low",
        recommended_action="Test action",
        confidence=0.8,
        discovered_via="test",
        discovered_at="2024-01-01T00:00:00",
    )
    score = ranker.calculate_score(candidate)
    assert 0.0 <= score <= 1.0
    # Good candidate should score high
    assert score > 0.7


def test_rank_candidates():
    """Test ranking multiple candidates"""
    ranker = OpportunityRanker()
    candidates = [
        OpportunityCandidate(
            candidate_id="low",
            title="Low Priority",
            pain_point="Minor issue",
            target_customer="Niche",
            urgency="low",
            monetization_clarity="unclear",
            execution_domains=["misc"],
            automation_potential="low",
            complexity="high",
            recommended_action="Research",
            confidence=0.3,
            discovered_via="test",
            discovered_at="2024-01-01",
        ),
        OpportunityCandidate(
            candidate_id="high",
            title="High Priority",
            pain_point="Critical issue",
            target_customer="Enterprise",
            urgency="critical",
            monetization_clarity="proven",
            execution_domains=["automation"],
            automation_potential="high",
            complexity="low",
            recommended_action="Build MVP",
            confidence=0.9,
            discovered_via="test",
            discovered_at="2024-01-01",
        ),
    ]
    ranked = ranker.rank_candidates(candidates)
    # High priority should be first
    assert ranked[0].candidate_id == "high"
    assert ranked[1].candidate_id == "low"


def test_score_breakdown():
    """Test detailed score breakdown"""
    ranker = OpportunityRanker()
    candidate = OpportunityCandidate(
        candidate_id="test",
        title="Test",
        pain_point="Test",
        target_customer="Test",
        urgency="high",
        monetization_clarity="proven",
        execution_domains=["test"],
        automation_potential="medium",
        complexity="medium",
        recommended_action="Test",
        confidence=0.7,
        discovered_via="test",
        discovered_at="2024-01-01",
    )
    breakdown = ranker.get_score_breakdown(candidate)
    assert "urgency" in breakdown
    assert "monetization_clarity" in breakdown
    assert "automation_potential" in breakdown
    assert "complexity" in breakdown
    assert "confidence" in breakdown
    assert "overall" in breakdown


def test_filter_by_threshold():
    """Test filtering candidates by score threshold"""
    ranker = OpportunityRanker()
    candidates = [
        OpportunityCandidate(
            candidate_id=f"test-{i}",
            title=f"Opportunity {i}",
            pain_point="Test",
            target_customer="Test",
            urgency=["low", "medium", "high"][i % 3],
            monetization_clarity="proven",
            execution_domains=["test"],
            automation_potential="medium",
            complexity="medium",
            recommended_action="Test",
            confidence=0.5 + (i * 0.1),
            discovered_via="test",
            discovered_at="2024-01-01",
        )
        for i in range(5)
    ]
    filtered = ranker.filter_by_threshold(candidates, min_score=0.6)
    assert len(filtered) < len(candidates)


# =============================================================================
# Market Discovery Engine Tests
# =============================================================================

def test_discovery_engine_initialization():
    """Test discovery engine initializes"""
    engine = MarketDiscoveryEngine()
    assert engine.scan_history == []


def test_run_theme_scan():
    """Test running a theme scan"""
    engine = MarketDiscoveryEngine()
    discovery_input = DiscoveryInput(
        mode="theme_scan",
        theme="AI automation",
    )
    result = engine.run_discovery(discovery_input)
    assert isinstance(result, DiscoveryResult)
    assert result.mode == "theme_scan"
    assert result.total_candidates > 0
    assert len(result.candidates) == result.total_candidates


def test_run_pain_point_scan():
    """Test running a pain point scan"""
    engine = MarketDiscoveryEngine()
    discovery_input = DiscoveryInput(
        mode="pain_point_scan",
        problem_area="customer acquisition",
        customer_type="startups",
    )
    result = engine.run_discovery(discovery_input)
    assert result.mode == "pain_point_scan"
    assert result.total_candidates > 0


def test_run_industry_scan():
    """Test running an industry scan"""
    engine = MarketDiscoveryEngine()
    discovery_input = DiscoveryInput(
        mode="industry_scan",
        industry="healthcare",
    )
    result = engine.run_discovery(discovery_input)
    assert result.mode == "industry_scan"
    assert result.total_candidates > 0


def test_run_problem_exploration():
    """Test running problem exploration"""
    engine = MarketDiscoveryEngine()
    discovery_input = DiscoveryInput(
        mode="problem_exploration",
        problem_area="data quality",
    )
    result = engine.run_discovery(discovery_input)
    assert result.mode == "problem_exploration"
    assert result.total_candidates > 0


def test_discovery_result_structure():
    """Test discovery result has all required fields"""
    engine = MarketDiscoveryEngine()
    discovery_input = DiscoveryInput(mode="theme_scan", theme="test")
    result = engine.run_discovery(discovery_input)

    assert result.scan_id
    assert result.mode
    assert result.input_summary
    assert isinstance(result.candidates, list)
    assert result.total_candidates == len(result.candidates)
    assert result.scan_timestamp
    assert isinstance(result.metadata, dict)


def test_scan_history_tracking():
    """Test scan history is tracked"""
    engine = MarketDiscoveryEngine()
    discovery_input = DiscoveryInput(mode="theme_scan", theme="test")
    result = engine.run_discovery(discovery_input)

    assert len(engine.scan_history) == 1
    assert engine.scan_history[0].scan_id == result.scan_id


def test_get_scan_result():
    """Test retrieving a scan result by ID"""
    engine = MarketDiscoveryEngine()
    discovery_input = DiscoveryInput(mode="theme_scan", theme="test")
    result = engine.run_discovery(discovery_input)

    retrieved = engine.get_scan_result(result.scan_id)
    assert retrieved is not None
    assert retrieved.scan_id == result.scan_id


def test_get_scan_result_not_found():
    """Test retrieving non-existent scan returns None"""
    engine = MarketDiscoveryEngine()
    retrieved = engine.get_scan_result("nonexistent-id")
    assert retrieved is None


def test_invalid_discovery_mode():
    """Test invalid discovery mode raises error"""
    engine = MarketDiscoveryEngine()
    discovery_input = DiscoveryInput(mode="invalid_mode")
    with pytest.raises(ValueError):
        engine.run_discovery(discovery_input)


def test_input_summary_generation():
    """Test input summary is generated correctly"""
    engine = MarketDiscoveryEngine()
    discovery_input = DiscoveryInput(
        mode="pain_point_scan",
        problem_area="automation",
        customer_type="SMBs",
        industry="SaaS",
    )
    result = engine.run_discovery(discovery_input)
    summary = result.input_summary
    assert "automation" in summary.lower()
    assert "SMBs" in summary


# =============================================================================
# Integration Tests
# =============================================================================

def test_full_discovery_workflow():
    """Test complete discovery workflow from input to ranked results"""
    # 1. Run discovery
    engine = MarketDiscoveryEngine()
    discovery_input = DiscoveryInput(
        mode="pain_point_scan",
        problem_area="data management",
        customer_type="operations teams",
    )
    result = engine.run_discovery(discovery_input)

    # 2. Rank candidates
    ranker = OpportunityRanker()
    ranked_candidates = ranker.rank_candidates(result.candidates)

    # 3. Verify ranking worked
    assert len(ranked_candidates) == len(result.candidates)
    # Top candidate should have highest score
    top_score = ranker.calculate_score(ranked_candidates[0])
    second_score = ranker.calculate_score(ranked_candidates[1])
    assert top_score >= second_score


def test_discovery_modes_produce_different_candidates():
    """Test different discovery modes produce different results"""
    engine = MarketDiscoveryEngine()

    theme_result = engine.run_discovery(DiscoveryInput(mode="theme_scan", theme="automation"))
    pain_result = engine.run_discovery(DiscoveryInput(mode="pain_point_scan", problem_area="automation"))
    industry_result = engine.run_discovery(DiscoveryInput(mode="industry_scan", industry="software"))
    problem_result = engine.run_discovery(DiscoveryInput(mode="problem_exploration", problem_area="automation"))

    # All should produce candidates
    assert theme_result.total_candidates > 0
    assert pain_result.total_candidates > 0
    assert industry_result.total_candidates > 0
    assert problem_result.total_candidates > 0

    # Candidate IDs should be unique per mode
    theme_ids = {c.candidate_id for c in theme_result.candidates}
    pain_ids = {c.candidate_id for c in pain_result.candidates}
    assert not theme_ids.intersection(pain_ids)


def test_deterministic_ranking():
    """Test ranking is deterministic for same inputs"""
    ranker = OpportunityRanker()
    candidates = [
        OpportunityCandidate(
            candidate_id=f"test-{i}",
            title=f"Opportunity {i}",
            pain_point="Test",
            target_customer="Test",
            urgency="medium",
            monetization_clarity="emerging",
            execution_domains=["test"],
            automation_potential="medium",
            complexity="medium",
            recommended_action="Test",
            confidence=0.5,
            discovered_via="test",
            discovered_at="2024-01-01",
        )
        for i in range(3)
    ]

    # Rank twice
    ranked1 = ranker.rank_candidates(candidates.copy())
    ranked2 = ranker.rank_candidates(candidates.copy())

    # Order should be identical
    assert [c.candidate_id for c in ranked1] == [c.candidate_id for c in ranked2]
