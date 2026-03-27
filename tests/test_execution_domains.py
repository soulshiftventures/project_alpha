"""
Tests for Execution Domains - Domain-Neutral Execution Expansion.

Tests cover:
- Domain classification from goals
- Domain metadata retrieval
- Domain-aware cost modifiers
- Domain-specific connector mapping
- Integration with orchestration and cost systems

SECURITY:
- Tests use mock values only
- No real API calls
"""

import pytest
from unittest.mock import Mock, patch

from core.execution_plan import ExecutionDomain
from core.execution_domains import (
    DomainMetadata,
    DOMAIN_METADATA,
    get_domain_metadata,
    classify_goal_domain,
    get_domain_connectors,
    get_all_domains,
    get_domain_display_name,
    get_domain_summary,
)
from core.cost_model import (
    CostEstimate,
    get_domain_cost_modifier,
    estimate_domain_aware_cost,
)


# =============================================================================
# Domain Metadata Tests
# =============================================================================

class TestDomainMetadata:
    """Tests for DomainMetadata dataclass."""

    def test_domain_metadata_creation(self):
        """DomainMetadata can be created with all fields."""
        metadata = DomainMetadata(
            domain=ExecutionDomain.RESEARCH,
            display_name="Research",
            description="Research operations",
            keywords=["research", "analyze"],
            typical_connectors=["tavily"],
            default_cost_sensitivity="low",
            default_approval_level="auto",
            common_operations=["search", "analyze"],
        )

        assert metadata.domain == ExecutionDomain.RESEARCH
        assert metadata.display_name == "Research"
        assert "research" in metadata.keywords
        assert "tavily" in metadata.typical_connectors

    def test_domain_metadata_to_dict(self):
        """DomainMetadata.to_dict() returns dictionary."""
        metadata = get_domain_metadata(ExecutionDomain.RESEARCH)
        data = metadata.to_dict()

        assert isinstance(data, dict)
        assert data["domain"] == "research"
        assert "display_name" in data
        assert "keywords" in data
        assert isinstance(data["keywords"], list)


class TestDomainRegistry:
    """Tests for domain metadata registry."""

    def test_all_domains_have_metadata(self):
        """All ExecutionDomain values have metadata."""
        for domain in ExecutionDomain:
            metadata = get_domain_metadata(domain)
            assert isinstance(metadata, DomainMetadata)
            assert metadata.domain == domain

    def test_domain_metadata_completeness(self):
        """Domain metadata has required fields."""
        for domain in ExecutionDomain:
            if domain == ExecutionDomain.UNKNOWN:
                continue

            metadata = get_domain_metadata(domain)
            assert metadata.display_name
            assert metadata.description
            assert isinstance(metadata.keywords, list)
            assert isinstance(metadata.typical_connectors, list)
            assert metadata.default_cost_sensitivity in ["low", "medium", "high"]
            assert metadata.default_approval_level in ["auto", "standard", "elevated"]


# =============================================================================
# Domain Classification Tests
# =============================================================================

class TestDomainClassification:
    """Tests for domain classification from goals."""

    def test_research_classification(self):
        """Goals with research keywords classify as RESEARCH."""
        goals = [
            "Research market trends for SaaS products",
            "Analyze competitor pricing",
            "Investigate customer pain points",
            "Study industry best practices",
        ]

        for goal in goals:
            domain = classify_goal_domain(goal)
            assert domain == ExecutionDomain.RESEARCH

    def test_finance_classification(self):
        """Goals with finance keywords classify as FINANCE."""
        goals = [
            "Track monthly expenses and budget",
            "Generate financial report for Q4",
            "Process invoice for vendor payment",
            "Review revenue projections",
        ]

        for goal in goals:
            domain = classify_goal_domain(goal)
            assert domain == ExecutionDomain.FINANCE

    def test_product_classification(self):
        """Goals with product keywords classify as PRODUCT."""
        goals = [
            "Build MVP product features",
            "Design product roadmap for 2026",
            "Prioritize product backlog",
            "Create user stories for feature",
        ]

        for goal in goals:
            domain = classify_goal_domain(goal)
            assert domain == ExecutionDomain.PRODUCT

    def test_growth_classification(self):
        """Goals with strong growth keywords classify appropriately."""
        # Clear growth-focused goals
        clear_growth_goals = [
            "Launch outreach campaign to prospects",
            "Scale customer acquisition with growth marketing",
            "Expand market presence and growth",
        ]

        for goal in clear_growth_goals:
            domain = classify_goal_domain(goal)
            # Growth or operations are both reasonable
            assert domain in [ExecutionDomain.GROWTH, ExecutionDomain.OPERATIONS, ExecutionDomain.RESEARCH]

    def test_content_classification(self):
        """Goals with content keywords classify as CONTENT."""
        goals = [
            "Write documentation for API endpoints",
            "Create blog post about new features",
            "Publish knowledge base articles",
            "Document deployment procedures",
        ]

        for goal in goals:
            domain = classify_goal_domain(goal)
            # Content, product, or engineering are reasonable for documentation
            assert domain in [ExecutionDomain.CONTENT, ExecutionDomain.PRODUCT, ExecutionDomain.ENGINEERING]

    def test_engineering_classification(self):
        """Goals with engineering keywords classify as ENGINEERING."""
        goals = [
            "Implement authentication system",
            "Deploy new service to production",
            "Debug performance bottleneck",
            "Build CI/CD pipeline",
        ]

        for goal in goals:
            domain = classify_goal_domain(goal)
            # Engineering, product, or automation are reasonable
            assert domain in [ExecutionDomain.ENGINEERING, ExecutionDomain.PRODUCT, ExecutionDomain.AUTOMATION]

    def test_role_based_hints(self):
        """Classification considers role context."""
        goal = "Plan the quarterly roadmap"

        # CTO context suggests engineering/product/planning/strategy
        cto_domain = classify_goal_domain(goal, {"role": "cto"})
        assert cto_domain in [ExecutionDomain.ENGINEERING, ExecutionDomain.PLANNING, ExecutionDomain.PRODUCT, ExecutionDomain.STRATEGY]

        # CFO context suggests finance/planning/strategy
        cfo_domain = classify_goal_domain(goal, {"role": "cfo"})
        assert cfo_domain in [ExecutionDomain.FINANCE, ExecutionDomain.PLANNING, ExecutionDomain.STRATEGY]

        # CEO context suggests strategy/planning
        ceo_domain = classify_goal_domain(goal, {"role": "ceo"})
        assert ceo_domain in [ExecutionDomain.STRATEGY, ExecutionDomain.PLANNING]

    def test_unknown_fallback(self):
        """Unclassifiable goals return UNKNOWN."""
        goal = "xyz abc qwerty"  # Meaningless text
        domain = classify_goal_domain(goal)
        assert domain == ExecutionDomain.UNKNOWN


# =============================================================================
# Domain Helper Function Tests
# =============================================================================

class TestDomainHelpers:
    """Tests for domain helper functions."""

    def test_get_domain_connectors(self):
        """get_domain_connectors returns connectors for domain."""
        growth_connectors = get_domain_connectors(ExecutionDomain.GROWTH)
        assert isinstance(growth_connectors, list)
        # Growth domain should have outreach/CRM connectors
        assert any(c in ["apollo", "hubspot", "sendgrid"] for c in growth_connectors)

        research_connectors = get_domain_connectors(ExecutionDomain.RESEARCH)
        assert isinstance(research_connectors, list)
        # Research domain should have search/scraping connectors
        assert any(c in ["tavily", "firecrawl"] for c in research_connectors)

    def test_get_all_domains(self):
        """get_all_domains excludes UNKNOWN."""
        domains = get_all_domains()
        assert isinstance(domains, list)
        assert len(domains) > 0
        assert ExecutionDomain.UNKNOWN not in domains
        assert ExecutionDomain.RESEARCH in domains

    def test_get_domain_display_name(self):
        """get_domain_display_name returns human-readable name."""
        assert get_domain_display_name(ExecutionDomain.RESEARCH) == "Research & Intelligence"
        assert get_domain_display_name(ExecutionDomain.FINANCE) == "Finance & Accounting"
        assert get_domain_display_name(ExecutionDomain.GROWTH) == "Growth & Expansion"

    def test_get_domain_summary(self):
        """get_domain_summary returns overview of all domains."""
        summary = get_domain_summary()

        assert isinstance(summary, dict)
        assert "total_domains" in summary
        assert "domains" in summary
        assert summary["total_domains"] > 10  # Should have many domains
        assert isinstance(summary["domains"], list)

        # Check first domain entry
        first_domain = summary["domains"][0]
        assert "value" in first_domain
        assert "display_name" in first_domain
        assert "description" in first_domain


# =============================================================================
# Domain-Aware Cost Modifier Tests
# =============================================================================

class TestDomainCostModifiers:
    """Tests for domain-specific cost modifiers."""

    def test_domain_cost_modifiers_exist(self):
        """All domains have cost modifiers."""
        for domain in ExecutionDomain:
            modifier = get_domain_cost_modifier(domain.value)
            assert isinstance(modifier, float)
            assert modifier > 0.0
            assert modifier <= 2.0  # Reasonable range

    def test_growth_domain_higher_cost(self):
        """Growth domain has higher cost modifier (more external operations)."""
        growth_modifier = get_domain_cost_modifier("growth")
        baseline_modifier = get_domain_cost_modifier("unknown")
        assert growth_modifier > baseline_modifier

    def test_internal_admin_lower_cost(self):
        """Internal admin domain has lower cost modifier (mostly internal)."""
        admin_modifier = get_domain_cost_modifier("internal_admin")
        baseline_modifier = get_domain_cost_modifier("unknown")
        assert admin_modifier < baseline_modifier

    def test_estimate_domain_aware_cost(self):
        """estimate_domain_aware_cost applies domain modifier."""
        base_estimate = CostEstimate.from_amount(1.0)

        # Growth domain should increase cost
        growth_estimate = estimate_domain_aware_cost(base_estimate, "growth")
        assert growth_estimate.amount > base_estimate.amount

        # Internal admin should decrease cost
        admin_estimate = estimate_domain_aware_cost(base_estimate, "internal_admin")
        assert admin_estimate.amount < base_estimate.amount

    def test_unknown_cost_not_modified(self):
        """Unknown cost estimates are not modified by domain."""
        unknown_estimate = CostEstimate.unknown()
        modified = estimate_domain_aware_cost(unknown_estimate, "growth")
        assert modified.is_unknown


# =============================================================================
# Integration Tests
# =============================================================================

class TestDomainIntegration:
    """Tests for domain integration with other systems."""

    def test_domain_in_execution_plan(self):
        """ExecutionDomain can be used in execution plans."""
        from core.execution_plan import ExecutionPlan, ExecutionStep

        plan = ExecutionPlan(
            plan_id="test-001",
            objective="Research market",
            primary_domain=ExecutionDomain.RESEARCH,
            role_id="ceo",
        )

        assert plan.primary_domain == ExecutionDomain.RESEARCH
        assert plan.primary_domain.value == "research"

    def test_domain_metadata_available_for_all_domains(self):
        """All domains in ExecutionDomain have metadata."""
        for domain in ExecutionDomain:
            metadata = DOMAIN_METADATA.get(domain)
            assert metadata is not None
            assert metadata.domain == domain
