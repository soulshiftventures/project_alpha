"""
Tests for playbook UI pages and quick-start flows.

Tests the playbook content, quickstart flows, and template UI routes.
"""

import pytest
from ui.services import get_playbook_content, get_quickstart_flows


class TestPlaybookContent:
    """Test the playbook content generation."""

    def test_playbook_content_structure(self):
        """Test that playbook content has required structure."""
        content = get_playbook_content()

        assert "title" in content
        assert content["title"] == "Operator Playbook"
        assert "version" in content
        assert "sections" in content
        assert "quick_reference" in content

    def test_playbook_sections_present(self):
        """Test that all expected sections are present."""
        content = get_playbook_content()
        sections = content["sections"]

        assert len(sections) >= 5  # At least 5 main sections

        section_ids = [s["id"] for s in sections]
        assert "getting-started" in section_ids
        assert "daily-workflow" in section_ids
        assert "common-workflows" in section_ids
        assert "modes" in section_ids
        assert "recovery" in section_ids

    def test_playbook_section_structure(self):
        """Test that each section has required fields."""
        content = get_playbook_content()

        for section in content["sections"]:
            assert "id" in section
            assert "title" in section
            assert "summary" in section
            assert "topics" in section
            assert isinstance(section["topics"], list)

    def test_playbook_topics_structure(self):
        """Test that topics have required fields."""
        content = get_playbook_content()

        for section in content["sections"]:
            for topic in section["topics"]:
                assert "name" in topic
                # Topics may have route or just description
                assert "description" in topic or "route" in topic

    def test_playbook_quick_reference(self):
        """Test quick reference links."""
        content = get_playbook_content()
        quick_ref = content["quick_reference"]

        assert "status_check" in quick_ref
        assert "work_queue" in quick_ref
        assert "approvals" in quick_ref
        assert "templates" in quick_ref

        # Each quick ref should have route and label
        for key, item in quick_ref.items():
            assert "route" in item
            assert "label" in item

    def test_playbook_getting_started_topics(self):
        """Test getting started section has key topics."""
        content = get_playbook_content()
        getting_started = next(s for s in content["sections"] if s["id"] == "getting-started")

        topic_names = [t["name"] for t in getting_started["topics"]]
        assert "Verify Readiness" in topic_names
        assert "Setup Checklist" in topic_names
        assert "Health Check" in topic_names

    def test_playbook_daily_workflow_topics(self):
        """Test daily workflow section has key topics."""
        content = get_playbook_content()
        daily = next(s for s in content["sections"] if s["id"] == "daily-workflow")

        topic_names = [t["name"] for t in daily["topics"]]
        assert "Dashboard" in topic_names
        assert "Work Queue" in topic_names
        assert "Approvals" in topic_names


class TestQuickstartFlows:
    """Test quickstart flow definitions."""

    def test_quickstart_flows_structure(self):
        """Test that quickstart flows have required structure."""
        flows = get_quickstart_flows()

        assert isinstance(flows, list)
        assert len(flows) >= 5  # At least 5 quickstart flows

    def test_quickstart_flow_fields(self):
        """Test that each flow has required fields."""
        flows = get_quickstart_flows()

        for flow in flows:
            assert "id" in flow
            assert "name" in flow
            assert "description" in flow
            assert "steps" in flow
            assert "estimated_time" in flow

    def test_quickstart_flow_steps_structure(self):
        """Test that flow steps have required fields."""
        flows = get_quickstart_flows()

        for flow in flows:
            assert isinstance(flow["steps"], list)
            assert len(flow["steps"]) >= 2  # At least 2 steps

            for step in flow["steps"]:
                assert "name" in step
                assert "action" in step

    def test_quickstart_discovery_flow(self):
        """Test the discovery quickstart flow."""
        flows = get_quickstart_flows()
        discovery = next((f for f in flows if f["id"] == "first-discovery"), None)

        assert discovery is not None
        assert discovery["name"] == "Start Discovery"
        assert discovery["template_id"] == "discovery_intake"
        assert any("/discovery" in str(s.get("route", "")) for s in discovery["steps"])

    def test_quickstart_research_flow(self):
        """Test the research quickstart flow."""
        flows = get_quickstart_flows()
        research = next((f for f in flows if f["id"] == "run-research"), None)

        assert research is not None
        assert research["name"] == "Run Research Scenario"
        assert research["template_id"] == "research_scenario"

    def test_quickstart_notification_flow(self):
        """Test the notification quickstart flow."""
        flows = get_quickstart_flows()
        notification = next((f for f in flows if f["id"] == "test-notification"), None)

        assert notification is not None
        assert notification["name"] == "Send Test Notification"
        assert notification.get("requires_credentials") is True

    def test_quickstart_approvals_flow(self):
        """Test the approvals quickstart flow."""
        flows = get_quickstart_flows()
        approvals = next((f for f in flows if f["id"] == "review-approvals"), None)

        assert approvals is not None
        assert approvals["name"] == "Review Approvals"
        assert any("/approvals" in str(s.get("route", "")) for s in approvals["steps"])

    def test_quickstart_health_flow(self):
        """Test the health check quickstart flow."""
        flows = get_quickstart_flows()
        health = next((f for f in flows if f["id"] == "check-health"), None)

        assert health is not None
        assert health["name"] == "Inspect Connector Health"
        assert health["template_id"] == "connector_health"

    def test_quickstart_resume_flow(self):
        """Test the resume work quickstart flow."""
        flows = get_quickstart_flows()
        resume = next((f for f in flows if f["id"] == "resume-work"), None)

        assert resume is not None
        assert resume["name"] == "Resume Paused Work"
        assert any("/recovery" in str(s.get("route", "")) for s in resume["steps"])


class TestPlaybookUIIntegration:
    """Integration tests for playbook UI with Flask app."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from ui.app import app
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_playbook_route(self, client):
        """Test playbook page loads."""
        response = client.get("/playbook")
        assert response.status_code == 200
        assert b"Operator Playbook" in response.data

    def test_quickstart_route(self, client):
        """Test quickstart page loads."""
        response = client.get("/quickstart")
        assert response.status_code == 200
        assert b"Quick-Start" in response.data

    def test_templates_route(self, client):
        """Test templates browse page loads."""
        response = client.get("/templates")
        assert response.status_code == 200
        assert b"Workflow Templates" in response.data

    def test_template_detail_route(self, client):
        """Test template detail page loads."""
        response = client.get("/templates/discovery_intake")
        assert response.status_code == 200
        assert b"Discovery Intake" in response.data

    def test_template_detail_not_found(self, client):
        """Test template detail 404 for missing template."""
        response = client.get("/templates/nonexistent_template")
        assert response.status_code == 404

    def test_api_playbook(self, client):
        """Test API playbook endpoint."""
        response = client.get("/api/playbook")
        assert response.status_code == 200

        data = response.get_json()
        assert "title" in data
        assert "sections" in data

    def test_api_quickstart(self, client):
        """Test API quickstart endpoint."""
        response = client.get("/api/quickstart")
        assert response.status_code == 200

        data = response.get_json()
        assert "flows" in data
        assert len(data["flows"]) >= 5

    def test_api_templates(self, client):
        """Test API templates list endpoint."""
        response = client.get("/api/templates")
        assert response.status_code == 200

        data = response.get_json()
        assert "templates" in data
        assert "count" in data
        assert data["count"] >= 6

    def test_api_templates_filter_category(self, client):
        """Test API templates with category filter."""
        response = client.get("/api/templates?category=discovery")
        assert response.status_code == 200

        data = response.get_json()
        assert all(t["category"] == "discovery" for t in data["templates"])

    def test_api_templates_filter_mode(self, client):
        """Test API templates with mode filter."""
        response = client.get("/api/templates?mode=live_capable")
        assert response.status_code == 200

        data = response.get_json()
        assert all(t["mode"] == "live_capable" for t in data["templates"])

    def test_api_template_summary(self, client):
        """Test API template summary endpoint."""
        response = client.get("/api/templates/summary")
        assert response.status_code == 200

        data = response.get_json()
        assert "total" in data
        assert "by_category" in data
        assert "live_capable" in data

    def test_api_template_detail(self, client):
        """Test API template detail endpoint."""
        response = client.get("/api/templates/discovery_intake")
        assert response.status_code == 200

        data = response.get_json()
        assert data["template_id"] == "discovery_intake"
        assert "inputs" in data
        assert "steps" in data

    def test_api_template_detail_not_found(self, client):
        """Test API template detail 404."""
        response = client.get("/api/templates/nonexistent")
        assert response.status_code == 404

    def test_api_template_launch_success(self, client):
        """Test API template launch."""
        response = client.post(
            "/api/templates/connector_health/launch",
            json={"inputs": {}, "dry_run": True},
            content_type="application/json",
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["template_id"] == "connector_health"
        assert data["dry_run"] is True

    def test_api_template_launches_list(self, client):
        """Test API template launches list."""
        # First launch a template
        client.post(
            "/api/templates/connector_health/launch",
            json={"inputs": {}, "dry_run": True},
            content_type="application/json",
        )

        response = client.get("/api/templates/launches")
        assert response.status_code == 200

        data = response.get_json()
        assert "launches" in data

    def test_templates_filter_form(self, client):
        """Test templates page with filter parameters."""
        response = client.get("/templates?category=research")
        assert response.status_code == 200
        # Should show filtered results
        assert b"research" in response.data.lower()

    def test_template_launch_form_get(self, client):
        """Test template launch page (GET)."""
        response = client.get("/templates/discovery_intake/launch")
        assert response.status_code == 200
        assert b"Launch Template" in response.data

    def test_template_launch_form_post(self, client):
        """Test template launch (POST)."""
        response = client.post(
            "/templates/connector_health/launch",
            data={"dry_run": "true"},
            follow_redirects=True,
        )
        assert response.status_code == 200


class TestPlaybookNavigation:
    """Test navigation between playbook pages."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from ui.app import app
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_nav_includes_playbook(self, client):
        """Test that playbook is accessible (now under Admin)."""
        # Productization reset: Playbook moved to Admin section
        response = client.get("/admin")
        assert response.status_code == 200
        assert b"Playbook" in response.data or b"Help" in response.data

    def test_nav_includes_templates(self, client):
        """Test that templates are accessible (now under Admin)."""
        # Productization reset: Templates moved to Admin section
        response = client.get("/admin")
        assert response.status_code == 200
        assert b"Templates" in response.data or b"Help" in response.data

    def test_nav_includes_quickstart(self, client):
        """Test that quick-start is accessible (now under Admin)."""
        # Productization reset: Quick-Start moved to Admin section
        response = client.get("/admin")
        assert response.status_code == 200
        assert b"Quick-Start" in response.data or b"Help" in response.data

    def test_playbook_links_to_templates(self, client):
        """Test playbook page links to templates."""
        response = client.get("/playbook")
        assert response.status_code == 200
        assert b"/templates" in response.data

    def test_quickstart_links_to_templates(self, client):
        """Test quickstart page links to templates."""
        response = client.get("/quickstart")
        assert response.status_code == 200
        assert b"/templates" in response.data
