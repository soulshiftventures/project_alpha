"""
Tests for the Skill Intelligence Layer.

Tests skill registry, command registry, specialized agent registry,
skill selector, role mappings, policies, and composer.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Skill Registry tests
from core.skill_registry import (
    SkillRegistry, SkillDefinition, SkillCategory,
    get_skill_registry, load_skills, detect_category,
    PROACTIVE_SKILLS, APPROVAL_REQUIRED_SKILLS
)

# Command Registry tests
from core.command_registry import (
    CommandRegistry, CommandDefinition, CommandCategory,
    get_command_registry, load_commands, BUILTIN_COMMANDS
)

# Specialized Agent Registry tests
from core.specialized_agent_registry import (
    SpecializedAgentRegistry, SpecializedAgentDefinition, AgentDomain,
    get_specialized_agent_registry, load_specialized_agents, BUILTIN_AGENTS
)

# Skill Selector tests
from core.skill_selector import (
    SkillSelector, SelectionResult, ToolRecommendation, ToolType,
    get_skill_selector, select_tools_for_task
)

# Role Skill Mappings tests
from core.role_skill_mappings import (
    RoleSkillMapping, RoleSkillMappingRegistry,
    get_role_mapping_registry, get_role_mapping, load_role_mappings,
    DEFAULT_ROLE_MAPPINGS
)

# Skill Policies tests
from core.skill_policies import (
    SkillPolicyEngine, PolicyResult, PolicyDecision, BlockReason,
    get_policy_engine, evaluate_skill_policy, can_role_use_skill,
    GLOBALLY_BLOCKED_SKILLS, ALWAYS_REQUIRE_APPROVAL
)

# Skill Composer tests
from core.skill_composer import (
    SkillComposer, ComposedWorkflow, CompositionStep, CompositionStrategy,
    get_skill_composer, compose_workflow, WORKFLOW_PATTERNS
)

# Hierarchy integration
from core.agent_contracts import AgentLayer


# =============================================================================
# Skill Registry Tests
# =============================================================================

class TestSkillDefinition:
    """Tests for SkillDefinition dataclass."""

    def test_skill_definition_creation(self):
        """Test creating a skill definition."""
        skill = SkillDefinition(
            name="test-skill",
            description="A test skill",
            path="test-skill",
            keywords=["test", "skill"],
            category=SkillCategory.TESTING_QA
        )
        assert skill.name == "test-skill"
        assert skill.description == "A test skill"
        assert skill.category == SkillCategory.TESTING_QA

    def test_matches_query(self):
        """Test skill matching against queries."""
        skill = SkillDefinition(
            name="apollo-automation",
            description="Lead generation with Apollo",
            path="apollo-automation",
            keywords=["lead", "crm", "sales"]
        )

        assert skill.matches_query("apollo")
        assert skill.matches_query("lead")
        assert skill.matches_query("crm")
        assert not skill.matches_query("unrelated")

    def test_keyword_score(self):
        """Test keyword scoring."""
        skill = SkillDefinition(
            name="stripe-automation",
            description="Payment processing with Stripe",
            path="stripe-automation",
            keywords=["payment", "billing", "subscription"]
        )

        # Exact name match should score highest
        assert skill.keyword_score("stripe-automation") == 1.0

        # Name contains query
        assert skill.keyword_score("stripe") >= 0.8

        # Description match
        assert skill.keyword_score("payment") > 0

        # No match
        assert skill.keyword_score("unrelated") == 0.0


class TestSkillRegistry:
    """Tests for SkillRegistry class."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = SkillRegistry()
        assert not registry.is_loaded
        assert registry.skill_count == 0

    def test_load_without_file(self):
        """Test loading when file doesn't exist."""
        registry = SkillRegistry(reference_path=Path("/nonexistent"))
        result = registry.load()
        assert not result
        assert not registry.is_loaded
        assert registry.load_error is not None

    def test_load_with_mock_data(self):
        """Test loading with mock data."""
        registry = SkillRegistry()

        # Manually add skills for testing
        skill = SkillDefinition(
            name="test-skill",
            description="Test",
            path="test-skill",
            keywords=["test"],
            category=SkillCategory.TESTING_QA
        )
        registry._skills["test-skill"] = skill
        registry._loaded = True

        assert registry.is_loaded
        assert registry.skill_count == 1
        assert registry.get_skill("test-skill") is not None

    def test_search(self):
        """Test skill search functionality."""
        registry = SkillRegistry()

        # Add test skills
        registry._skills = {
            "apollo-automation": SkillDefinition(
                name="apollo-automation",
                description="Lead generation",
                path="apollo-automation",
                keywords=["lead", "sales"],
                category=SkillCategory.LEAD_GENERATION
            ),
            "stripe-automation": SkillDefinition(
                name="stripe-automation",
                description="Payment processing",
                path="stripe-automation",
                keywords=["payment"],
                category=SkillCategory.PAYMENT_ECOMMERCE
            ),
        }
        registry._loaded = True

        results = registry.search("lead")
        assert len(results) >= 1
        assert results[0].name == "apollo-automation"

    def test_get_by_category(self):
        """Test getting skills by category."""
        registry = SkillRegistry()
        registry._skills = {
            "skill1": SkillDefinition(
                name="skill1", description="", path="",
                category=SkillCategory.TESTING_QA
            ),
            "skill2": SkillDefinition(
                name="skill2", description="", path="",
                category=SkillCategory.TESTING_QA
            ),
            "skill3": SkillDefinition(
                name="skill3", description="", path="",
                category=SkillCategory.SECURITY_COMPLIANCE
            ),
        }
        registry._loaded = True

        qa_skills = registry.get_by_category(SkillCategory.TESTING_QA)
        assert len(qa_skills) == 2


class TestDetectCategory:
    """Tests for category detection."""

    def test_detect_lead_generation(self):
        """Test detecting lead generation category."""
        cat = detect_category("apollo-automation", "Lead generation with Apollo")
        assert cat == SkillCategory.LEAD_GENERATION

    def test_detect_payment(self):
        """Test detecting payment category."""
        cat = detect_category("stripe-automation", "Payment processing")
        assert cat == SkillCategory.PAYMENT_ECOMMERCE

    def test_detect_testing(self):
        """Test detecting testing category."""
        cat = detect_category("test-engineer", "Test generation")
        assert cat == SkillCategory.TESTING_QA

    def test_detect_uncategorized(self):
        """Test uncategorized fallback."""
        cat = detect_category("random-skill", "Does something random")
        assert cat == SkillCategory.UNCATEGORIZED


# =============================================================================
# Command Registry Tests
# =============================================================================

class TestCommandDefinition:
    """Tests for CommandDefinition dataclass."""

    def test_command_creation(self):
        """Test creating a command definition."""
        cmd = CommandDefinition(
            name="security-audit",
            purpose="Run security audit",
            usage="Check for vulnerabilities",
            use_when="Before releases",
            category=CommandCategory.SECURITY
        )
        assert cmd.name == "security-audit"
        assert cmd.category == CommandCategory.SECURITY

    def test_matches_query(self):
        """Test command matching."""
        cmd = CommandDefinition(
            name="quality-code-health",
            purpose="Assess code health",
            usage="Get quality report",
            use_when="Review code"
        )
        assert cmd.matches_query("quality")
        assert cmd.matches_query("code")
        assert cmd.matches_query("health")


class TestCommandRegistry:
    """Tests for CommandRegistry class."""

    def test_registry_load(self):
        """Test loading commands."""
        registry = CommandRegistry()
        result = registry.load()
        assert result
        assert registry.is_loaded
        assert registry.command_count == len(BUILTIN_COMMANDS)

    def test_get_command(self):
        """Test getting command by name."""
        registry = CommandRegistry()
        registry.load()

        cmd = registry.get_command("gsd")
        assert cmd is not None
        assert cmd.name == "gsd"
        assert cmd.category == CommandCategory.GSD

    def test_get_by_category(self):
        """Test getting commands by category."""
        registry = CommandRegistry()
        registry.load()

        security_cmds = registry.get_by_category(CommandCategory.SECURITY)
        assert len(security_cmds) >= 3  # audit, compliance, vulnerability

    def test_approval_required(self):
        """Test getting commands requiring approval."""
        registry = CommandRegistry()
        registry.load()

        approval_cmds = registry.get_approval_required()
        assert len(approval_cmds) >= 1


# =============================================================================
# Specialized Agent Registry Tests
# =============================================================================

class TestSpecializedAgentDefinition:
    """Tests for SpecializedAgentDefinition dataclass."""

    def test_agent_creation(self):
        """Test creating an agent definition."""
        agent = SpecializedAgentDefinition(
            name="test-engineer",
            expertise="Test creation",
            tools=["Read", "Write", "Bash"],
            use_when=["Need tests", "Coverage analysis"],
            domain=AgentDomain.TESTING,
            is_proactive=True
        )
        assert agent.name == "test-engineer"
        assert agent.is_proactive
        assert len(agent.tools) == 3

    def test_relevance_score(self):
        """Test relevance scoring."""
        agent = SpecializedAgentDefinition(
            name="security-auditor",
            expertise="Vulnerability assessment, OWASP compliance",
            use_when=["Security review", "Authentication flow"]
        )

        # Should match security tasks
        assert agent.relevance_score("security review needed") > 0
        assert agent.relevance_score("vulnerability scan") > 0
        assert agent.relevance_score("cooking recipe") == 0


class TestSpecializedAgentRegistry:
    """Tests for SpecializedAgentRegistry class."""

    def test_registry_load(self):
        """Test loading agents."""
        registry = SpecializedAgentRegistry()
        result = registry.load()
        assert result
        assert registry.is_loaded
        assert registry.agent_count == len(BUILTIN_AGENTS)

    def test_get_agent(self):
        """Test getting agent by name."""
        registry = SpecializedAgentRegistry()
        registry.load()

        agent = registry.get_agent("systems-architect")
        assert agent is not None
        assert agent.domain == AgentDomain.ARCHITECTURE_DESIGN

    def test_recommend_for_task(self):
        """Test task-based recommendations."""
        registry = SpecializedAgentRegistry()
        registry.load()

        # Security task should recommend security-auditor
        recs = registry.recommend_for_task("review security vulnerabilities")
        assert len(recs) > 0
        assert any(a.name == "security-auditor" for a in recs)

    def test_get_proactive_agents(self):
        """Test getting proactive agents."""
        registry = SpecializedAgentRegistry()
        registry.load()

        proactive = registry.get_proactive_agents()
        assert len(proactive) > 0
        # All proactive agents should have is_proactive=True
        assert all(a.is_proactive for a in proactive)


# =============================================================================
# Skill Selector Tests
# =============================================================================

class TestSkillSelector:
    """Tests for SkillSelector class."""

    def test_selector_initialization(self):
        """Test selector initialization."""
        selector = SkillSelector()
        assert not selector.is_loaded

    def test_select_with_mock_registries(self):
        """Test selection with mock registries."""
        # Create mock registries
        skill_reg = SkillRegistry()
        skill_reg._skills = {
            "test-skill": SkillDefinition(
                name="test-skill",
                description="A test skill",
                path="test-skill",
                keywords=["test"],
                category=SkillCategory.TESTING_QA
            )
        }
        skill_reg._loaded = True

        cmd_reg = CommandRegistry()
        cmd_reg.load()

        agent_reg = SpecializedAgentRegistry()
        agent_reg.load()

        selector = SkillSelector(skill_reg, cmd_reg, agent_reg)
        selector._loaded = True

        result = selector.select("test something")
        assert isinstance(result, SelectionResult)

    def test_get_proactive_tools(self):
        """Test getting proactive tools."""
        skill_reg = SkillRegistry()
        skill_reg._skills = {
            "code-reviewer": SkillDefinition(
                name="code-reviewer",
                description="Code review",
                path="code-reviewer",
                keywords=["review"],
                is_proactive=True
            )
        }
        skill_reg._loaded = True

        agent_reg = SpecializedAgentRegistry()
        agent_reg.load()

        selector = SkillSelector(skill_reg, CommandRegistry(), agent_reg)
        selector._loaded = True

        proactive = selector.get_proactive_tools()
        assert len(proactive) > 0


class TestToolRecommendation:
    """Tests for ToolRecommendation dataclass."""

    def test_recommendation_creation(self):
        """Test creating a recommendation."""
        rec = ToolRecommendation(
            tool_type=ToolType.SKILL,
            name="apollo-automation",
            score=0.85,
            rationale="Lead generation skill"
        )
        assert rec.tool_type == ToolType.SKILL
        assert rec.score == 0.85


# =============================================================================
# Role Skill Mappings Tests
# =============================================================================

class TestRoleSkillMapping:
    """Tests for RoleSkillMapping dataclass."""

    def test_mapping_creation(self):
        """Test creating a role mapping."""
        mapping = RoleSkillMapping(
            role_id="test_role",
            role_name="Test Role",
            layer=AgentLayer.DEPARTMENT,
            allowed_skill_categories={SkillCategory.TESTING_QA},
            blocked_skills={"blocked-skill"}
        )
        assert mapping.role_id == "test_role"

    def test_can_use_skill(self):
        """Test skill access checking."""
        mapping = RoleSkillMapping(
            role_id="test_role",
            role_name="Test Role",
            layer=AgentLayer.DEPARTMENT,
            allowed_skill_categories={SkillCategory.TESTING_QA},
            allowed_skills={"explicit-skill"},
            blocked_skills={"blocked-skill"}
        )

        # Blocked skill
        assert not mapping.can_use_skill("blocked-skill", SkillCategory.TESTING_QA)

        # Explicit allowed
        assert mapping.can_use_skill("explicit-skill", SkillCategory.UNCATEGORIZED)

        # Category allowed
        assert mapping.can_use_skill("any-skill", SkillCategory.TESTING_QA)

        # Not allowed
        assert not mapping.can_use_skill("random", SkillCategory.PAYMENT_ECOMMERCE)


class TestRoleSkillMappingRegistry:
    """Tests for RoleSkillMappingRegistry class."""

    def test_registry_load(self):
        """Test loading mappings."""
        registry = RoleSkillMappingRegistry()
        result = registry.load()
        assert result
        assert registry.is_loaded
        assert len(registry.all_mappings()) == len(DEFAULT_ROLE_MAPPINGS)

    def test_get_mapping(self):
        """Test getting mapping by role."""
        registry = RoleSkillMappingRegistry()
        registry.load()

        mapping = registry.get_mapping("cto")
        assert mapping is not None
        assert mapping.layer == AgentLayer.C_SUITE

    def test_principal_has_all_access(self):
        """Test principal has full access."""
        registry = RoleSkillMappingRegistry()
        registry.load()

        principal = registry.get_mapping("principal_human")
        assert principal is not None
        # Principal should have all categories
        assert len(principal.allowed_skill_categories) == len(SkillCategory)


# =============================================================================
# Skill Policies Tests
# =============================================================================

class TestPolicyResult:
    """Tests for PolicyResult dataclass."""

    def test_policy_result_creation(self):
        """Test creating a policy result."""
        result = PolicyResult(
            decision=PolicyDecision.AUTO_ALLOWED,
            skill_name="test-skill",
            role_id="test_role",
            reason="Test reason"
        )
        assert result.is_allowed
        assert not result.is_blocked

    def test_blocked_result(self):
        """Test blocked policy result."""
        result = PolicyResult(
            decision=PolicyDecision.BLOCKED,
            skill_name="blocked-skill",
            role_id="test_role",
            reason="Blocked",
            block_reason=BlockReason.EXPLICIT_BLOCKLIST
        )
        assert result.is_blocked
        assert not result.is_allowed


class TestSkillPolicyEngine:
    """Tests for SkillPolicyEngine class."""

    def test_engine_load(self):
        """Test loading policy engine."""
        engine = SkillPolicyEngine()
        result = engine.load()
        assert result
        assert engine.is_loaded

    def test_evaluate_principal(self):
        """Test principal has broad access."""
        engine = SkillPolicyEngine()
        engine.load()

        result = engine.evaluate("any-skill", "principal_human")
        assert result.decision == PolicyDecision.AUTO_ALLOWED

    def test_evaluate_always_require_approval(self):
        """Test skills that always require approval."""
        engine = SkillPolicyEngine()
        engine.load()

        # Load role mappings first
        load_role_mappings()

        for skill_name in list(ALWAYS_REQUIRE_APPROVAL)[:1]:
            result = engine.evaluate(skill_name, "principal_human")
            assert result.decision == PolicyDecision.REQUIRES_APPROVAL

    def test_can_use_skill(self):
        """Test convenience method."""
        engine = SkillPolicyEngine()
        engine.load()

        # Principal should be able to use most skills
        assert engine.can_use_skill("random-skill", "principal_human")


# =============================================================================
# Skill Composer Tests
# =============================================================================

class TestCompositionStep:
    """Tests for CompositionStep dataclass."""

    def test_step_creation(self):
        """Test creating a composition step."""
        step = CompositionStep(
            step_number=1,
            tool_type=ToolType.SKILL,
            tool_name="apollo-automation",
            description="Find leads"
        )
        assert step.step_number == 1
        assert not step.requires_approval
        assert not step.is_blocked


class TestComposedWorkflow:
    """Tests for ComposedWorkflow dataclass."""

    def test_workflow_creation(self):
        """Test creating a workflow."""
        workflow = ComposedWorkflow(
            name="Test Workflow",
            description="A test workflow",
            strategy=CompositionStrategy.SEQUENTIAL,
            steps=[
                CompositionStep(1, ToolType.SKILL, "skill1", "Step 1"),
                CompositionStep(2, ToolType.SKILL, "skill2", "Step 2"),
            ]
        )
        assert workflow.step_count == 2
        assert not workflow.requires_any_approval

    def test_workflow_with_blocked_step(self):
        """Test workflow with blocked step."""
        blocked_policy = PolicyResult(
            decision=PolicyDecision.BLOCKED,
            skill_name="blocked",
            role_id="test",
            reason="Blocked"
        )

        workflow = ComposedWorkflow(
            name="Test",
            description="Test",
            strategy=CompositionStrategy.SEQUENTIAL,
            steps=[
                CompositionStep(1, ToolType.SKILL, "blocked", "Blocked",
                                policy_result=blocked_policy),
            ]
        )
        assert workflow.has_blocked_steps
        assert len(workflow.get_blocked_steps()) == 1


class TestSkillComposer:
    """Tests for SkillComposer class."""

    def test_composer_initialization(self):
        """Test composer initialization."""
        composer = SkillComposer()
        assert not composer.is_loaded

    def test_list_patterns(self):
        """Test listing workflow patterns."""
        composer = SkillComposer()
        patterns = composer.list_patterns()
        assert len(patterns) == len(WORKFLOW_PATTERNS)
        assert "feature_development" in patterns
        assert "security_audit" in patterns

    def test_get_pattern(self):
        """Test getting a pattern."""
        composer = SkillComposer()
        pattern = composer.get_pattern("bug_investigation")
        assert pattern is not None
        assert pattern["strategy"] == CompositionStrategy.SEQUENTIAL

    def test_compose_from_pattern(self):
        """Test composing from pattern."""
        composer = SkillComposer()
        composer.load()

        # Load role mappings
        load_role_mappings()

        workflow = composer.compose_from_pattern("code_quality", "principal_human")
        assert workflow is not None
        assert workflow.step_count > 0

    def test_suggest_pattern(self):
        """Test pattern suggestion."""
        composer = SkillComposer()

        assert composer.suggest_pattern("fix a bug in the code") == "bug_investigation"
        assert composer.suggest_pattern("security audit needed") == "security_audit"
        assert composer.suggest_pattern("implement new feature") == "feature_development"
        assert composer.suggest_pattern("generate leads from apollo") == "lead_generation_pipeline"


# =============================================================================
# Integration Tests
# =============================================================================

class TestSkillLayerIntegration:
    """Integration tests for the skill layer."""

    def test_end_to_end_selection(self):
        """Test end-to-end skill selection flow."""
        # Load all registries
        load_role_mappings()

        # Get selector
        selector = get_skill_selector()
        selector.load()

        # This would work if external reference exists
        # For now, just verify the flow works
        result = selector.select("test code coverage", max_recommendations=3)
        assert isinstance(result, SelectionResult)

    def test_compose_and_evaluate(self):
        """Test composing workflow with policy evaluation."""
        load_role_mappings()

        composer = get_skill_composer()
        composer.load()

        # Compose for principal (should have full access)
        workflow = compose_workflow("security audit the codebase", "principal_human")
        assert workflow is not None

    def test_role_based_filtering(self):
        """Test that roles properly filter skills."""
        load_role_mappings()

        # CFO should have payment skills requiring approval
        cfo_mapping = get_role_mapping("cfo")
        assert cfo_mapping is not None
        assert "stripe-automation" in cfo_mapping.approval_required_skills

        # CTO should have dev tools access
        cto_mapping = get_role_mapping("cto")
        assert cto_mapping is not None
        assert SkillCategory.DEVELOPMENT_TOOLS in cto_mapping.allowed_skill_categories


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
