"""
Tests for template registry functionality.

Tests the template registration, listing, searching, and launching.
"""

import pytest
from core.template_registry import (
    TemplateRegistry,
    WorkflowTemplate,
    TemplateInput,
    TemplateStep,
    TemplateCategory,
    TemplateMode,
    TemplateComplexity,
    get_template_registry,
    list_templates,
    get_template,
    launch_template,
)


class TestTemplateRegistry:
    """Test the TemplateRegistry class."""

    def test_registry_initialization(self):
        """Test that registry initializes with default templates."""
        registry = TemplateRegistry()
        templates = registry.list_templates()

        assert len(templates) > 0
        assert any(t.template_id == "discovery_intake" for t in templates)
        assert any(t.template_id == "connector_health" for t in templates)

    def test_get_template_exists(self):
        """Test getting an existing template."""
        registry = TemplateRegistry()
        template = registry.get_template("discovery_intake")

        assert template is not None
        assert template.template_id == "discovery_intake"
        assert template.name == "Discovery Intake"
        assert template.category == TemplateCategory.DISCOVERY

    def test_get_template_not_exists(self):
        """Test getting a non-existent template."""
        registry = TemplateRegistry()
        template = registry.get_template("nonexistent_template")

        assert template is None

    def test_list_templates_all(self):
        """Test listing all templates."""
        registry = TemplateRegistry()
        templates = registry.list_templates()

        assert len(templates) >= 6  # We have 6 default templates
        # Should be sorted by name
        names = [t.name for t in templates]
        assert names == sorted(names)

    def test_list_templates_by_category(self):
        """Test filtering templates by category."""
        registry = TemplateRegistry()

        discovery = registry.list_templates(category=TemplateCategory.DISCOVERY)
        assert len(discovery) >= 1
        assert all(t.category == TemplateCategory.DISCOVERY for t in discovery)

        research = registry.list_templates(category=TemplateCategory.RESEARCH)
        assert len(research) >= 1
        assert all(t.category == TemplateCategory.RESEARCH for t in research)

    def test_list_templates_by_mode(self):
        """Test filtering templates by mode."""
        registry = TemplateRegistry()

        dry_run_only = registry.list_templates(mode=TemplateMode.DRY_RUN_ONLY)
        assert len(dry_run_only) >= 1
        assert all(t.mode == TemplateMode.DRY_RUN_ONLY for t in dry_run_only)

        live_capable = registry.list_templates(mode=TemplateMode.LIVE_CAPABLE)
        assert len(live_capable) >= 1
        assert all(t.mode == TemplateMode.LIVE_CAPABLE for t in live_capable)

    def test_list_templates_combined_filters(self):
        """Test filtering with multiple criteria."""
        registry = TemplateRegistry()

        templates = registry.list_templates(
            category=TemplateCategory.RESEARCH,
            mode=TemplateMode.LIVE_CAPABLE,
        )

        for t in templates:
            assert t.category == TemplateCategory.RESEARCH
            assert t.mode == TemplateMode.LIVE_CAPABLE

    def test_search_templates_by_name(self):
        """Test searching templates by name."""
        registry = TemplateRegistry()

        results = registry.search_templates("discovery")
        assert len(results) >= 1
        assert any("discovery" in t.name.lower() for t in results)

    def test_search_templates_by_description(self):
        """Test searching templates by description."""
        registry = TemplateRegistry()

        results = registry.search_templates("notification")
        assert len(results) >= 1
        assert any("notification" in t.description.lower() for t in results)

    def test_search_templates_by_tag(self):
        """Test searching templates by tag."""
        registry = TemplateRegistry()

        results = registry.search_templates("first-run")
        assert len(results) >= 1
        assert any("first-run" in t.tags for t in results)

    def test_search_templates_no_results(self):
        """Test searching with no matching results."""
        registry = TemplateRegistry()

        results = registry.search_templates("nonexistent_xyz_123")
        assert len(results) == 0

    def test_get_template_summary(self):
        """Test getting template summary statistics."""
        registry = TemplateRegistry()
        summary = registry.get_template_summary()

        assert "total" in summary
        assert summary["total"] >= 6
        assert "by_category" in summary
        assert "by_mode" in summary
        assert "by_complexity" in summary
        assert "live_capable" in summary
        assert summary["live_capable"] >= 1

    def test_launch_template_success(self):
        """Test launching a template successfully."""
        registry = TemplateRegistry()

        launch = registry.launch_template(
            template_id="discovery_intake",
            inputs={"idea": "Test business idea"},
            dry_run=True,
            launched_by="test",
        )

        assert launch is not None
        assert launch.template_id == "discovery_intake"
        assert launch.dry_run is True
        assert launch.launched_by == "test"
        assert launch.status == "pending"
        assert "idea" in launch.inputs

    def test_launch_template_with_defaults(self):
        """Test launching template uses default values."""
        registry = TemplateRegistry()

        launch = registry.launch_template(
            template_id="discovery_intake",
            inputs={"idea": "Test idea"},
            dry_run=True,
        )

        assert launch is not None
        # Priority should have default value "medium"
        assert launch.inputs.get("priority") == "medium"

    def test_launch_template_missing_required(self):
        """Test launching template fails without required inputs."""
        registry = TemplateRegistry()

        # discovery_intake requires "idea"
        launch = registry.launch_template(
            template_id="discovery_intake",
            inputs={},  # Missing required "idea"
            dry_run=True,
        )

        assert launch is None

    def test_launch_template_nonexistent(self):
        """Test launching non-existent template fails."""
        registry = TemplateRegistry()

        launch = registry.launch_template(
            template_id="nonexistent_template",
            inputs={},
            dry_run=True,
        )

        assert launch is None

    def test_get_launch(self):
        """Test retrieving a launch record."""
        registry = TemplateRegistry()

        launch = registry.launch_template(
            template_id="connector_health",
            inputs={},
            dry_run=True,
        )

        retrieved = registry.get_launch(launch.launch_id)
        assert retrieved is not None
        assert retrieved.launch_id == launch.launch_id

    def test_update_launch_status(self):
        """Test updating launch status."""
        registry = TemplateRegistry()

        launch = registry.launch_template(
            template_id="connector_health",
            inputs={},
            dry_run=True,
        )

        updated = registry.update_launch_status(
            launch.launch_id,
            status="completed",
            result={"message": "Success"},
        )

        assert updated is not None
        assert updated.status == "completed"
        assert updated.result == {"message": "Success"}

    def test_list_launches(self):
        """Test listing launches."""
        registry = TemplateRegistry()

        # Create some launches
        registry.launch_template("connector_health", {}, True)
        registry.launch_template("connector_health", {}, True)

        launches = registry.list_launches()
        assert len(launches) >= 2

    def test_list_launches_filtered(self):
        """Test listing launches with filters."""
        registry = TemplateRegistry()

        # Create launches
        registry.launch_template("connector_health", {}, True)
        registry.launch_template("discovery_intake", {"idea": "Test"}, True)

        filtered = registry.list_launches(template_id="connector_health")
        assert all(l.template_id == "connector_health" for l in filtered)


class TestTemplateDataStructures:
    """Test template data structure classes."""

    def test_template_input_to_dict(self):
        """Test TemplateInput serialization."""
        input_def = TemplateInput(
            name="test_input",
            label="Test Input",
            input_type="text",
            required=True,
            default_value="default",
            help_text="Help text",
        )

        d = input_def.to_dict()
        assert d["name"] == "test_input"
        assert d["label"] == "Test Input"
        assert d["required"] is True

    def test_template_step_to_dict(self):
        """Test TemplateStep serialization."""
        step = TemplateStep(
            step_id="s1",
            name="Test Step",
            description="Step description",
            action_type="connector",
            connector="test",
            operation="test_op",
        )

        d = step.to_dict()
        assert d["step_id"] == "s1"
        assert d["name"] == "Test Step"
        assert d["connector"] == "test"

    def test_workflow_template_to_dict(self):
        """Test WorkflowTemplate serialization."""
        template = WorkflowTemplate(
            template_id="test_template",
            name="Test Template",
            description="Test description",
            category=TemplateCategory.MAINTENANCE,
            mode=TemplateMode.READ_ONLY,
            complexity=TemplateComplexity.SIMPLE,
        )

        d = template.to_dict()
        assert d["template_id"] == "test_template"
        assert d["category"] == "maintenance"
        assert d["mode"] == "read_only"
        assert d["complexity"] == "simple"


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_get_template_registry_singleton(self):
        """Test that get_template_registry returns singleton."""
        registry1 = get_template_registry()
        registry2 = get_template_registry()

        # Both should reference the same instance
        assert registry1 is registry2

    def test_list_templates_function(self):
        """Test the list_templates convenience function."""
        templates = list_templates()

        assert isinstance(templates, list)
        assert len(templates) >= 6
        assert all(isinstance(t, dict) for t in templates)

    def test_list_templates_with_category(self):
        """Test list_templates with category filter."""
        templates = list_templates(category="discovery")

        assert len(templates) >= 1
        assert all(t["category"] == "discovery" for t in templates)

    def test_get_template_function(self):
        """Test the get_template convenience function."""
        template = get_template("discovery_intake")

        assert template is not None
        assert isinstance(template, dict)
        assert template["template_id"] == "discovery_intake"

    def test_launch_template_function(self):
        """Test the launch_template convenience function."""
        result = launch_template(
            template_id="connector_health",
            inputs={},
            dry_run=True,
        )

        assert result is not None
        assert isinstance(result, dict)
        assert result["template_id"] == "connector_health"


class TestDefaultTemplates:
    """Test the default first-run templates."""

    def test_discovery_intake_template(self):
        """Test discovery intake template structure."""
        template = get_template("discovery_intake")

        assert template["name"] == "Discovery Intake"
        assert template["category"] == "discovery"
        assert template["mode"] == "dry_run_only"

        # Check inputs
        input_names = [i["name"] for i in template["inputs"]]
        assert "idea" in input_names

        # Check steps
        assert len(template["steps"]) >= 1

    def test_validation_first_template(self):
        """Test validation-first template structure."""
        template = get_template("validation_first")

        assert template["name"] == "Validation-First Opportunity"
        assert template["category"] == "research"
        assert template["mode"] == "live_capable"
        assert template["requires_live_credentials"] is True

    def test_research_scenario_template(self):
        """Test research scenario template structure."""
        template = get_template("research_scenario")

        assert template["name"] == "Research Scenario"
        assert template["category"] == "research"

        input_names = [i["name"] for i in template["inputs"]]
        assert "query" in input_names

    def test_notification_test_template(self):
        """Test notification test template structure."""
        template = get_template("notification_test")

        assert template["name"] == "Notification Test"
        assert template["category"] == "notification"
        assert template["mode"] == "live_capable"

        input_names = [i["name"] for i in template["inputs"]]
        assert "channel" in input_names
        assert "message" in input_names

    def test_crm_update_template(self):
        """Test CRM update template structure."""
        template = get_template("crm_update")

        assert template["name"] == "CRM Update"
        assert template["category"] == "crm"

        input_names = [i["name"] for i in template["inputs"]]
        assert "email" in input_names

    def test_connector_health_template(self):
        """Test connector health template structure."""
        template = get_template("connector_health")

        assert template["name"] == "Connector Health Check"
        assert template["category"] == "maintenance"
        assert template["mode"] == "read_only"
        assert template["requires_live_credentials"] is False
