"""
Tests for Operator Interface Layer.

Tests UI routes, service layer, and backend integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


# =============================================================================
# Test Service Layer
# =============================================================================

class TestServiceLayer:
    """Tests for ui/services.py."""

    def test_system_status_dataclass(self):
        """Test SystemStatus dataclass creation."""
        from ui.services import SystemStatus

        status = SystemStatus(
            healthy=True,
            runtime_initialized=True,
            active_jobs=3,
            pending_approvals=2,
            available_backends=["INLINE_LOCAL", "QUEUE_LOCAL"],
            total_events=100,
            recent_errors=5
        )

        assert status.healthy is True
        assert status.runtime_initialized is True
        assert status.active_jobs == 3
        assert status.pending_approvals == 2
        assert len(status.available_backends) == 2

    def test_system_status_to_dict(self):
        """Test SystemStatus serialization."""
        from ui.services import SystemStatus

        status = SystemStatus(
            healthy=True,
            runtime_initialized=False,
            active_jobs=0,
            pending_approvals=0,
            available_backends=[],
            total_events=50,
            recent_errors=0
        )

        data = status.to_dict()
        assert isinstance(data, dict)
        assert data["healthy"] is True
        assert data["active_jobs"] == 0

    def test_business_summary_dataclass(self):
        """Test BusinessSummary dataclass."""
        from ui.services import BusinessSummary

        business = BusinessSummary(
            business_id="biz-001",
            name="Test Business",
            stage="ideation",
            status="active",
            created_at="2024-01-01T00:00:00Z"
        )

        assert business.business_id == "biz-001"
        assert business.name == "Test Business"
        assert business.stage == "ideation"

    def test_business_summary_to_dict(self):
        """Test BusinessSummary serialization."""
        from ui.services import BusinessSummary

        business = BusinessSummary(
            business_id="biz-002",
            name="Another Business",
            stage="validation"
        )

        data = business.to_dict()
        assert data["business_id"] == "biz-002"
        assert data["name"] == "Another Business"

    def test_goal_submission_dataclass(self):
        """Test GoalSubmission dataclass."""
        from ui.services import GoalSubmission

        submission = GoalSubmission(
            objective="Build a feature",
            business_id="biz-001",
            stage="development",
            priority="high",
            notes="Important feature",
            requester="principal"
        )

        assert submission.objective == "Build a feature"
        assert submission.priority == "high"
        assert submission.requester == "principal"

    def test_goal_submission_defaults(self):
        """Test GoalSubmission default values."""
        from ui.services import GoalSubmission

        submission = GoalSubmission(
            objective="Simple goal",
            requester="operator"
        )

        assert submission.business_id is None
        assert submission.stage is None
        assert submission.priority == "medium"
        assert submission.notes is None


class TestOperatorService:
    """Tests for OperatorService class."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator."""
        mock = Mock()
        mock.orchestrate.return_value = Mock(
            request_id="req-001",
            status="completed",
            execution_plan=Mock(
                steps=[],
                to_dict=lambda: {"steps": []}
            ),
            to_dict=lambda: {"request_id": "req-001", "status": "completed"}
        )
        mock.approval = Mock()
        mock.logger = Mock()
        return mock

    @pytest.fixture
    def mock_runtime_manager(self):
        """Create mock runtime manager."""
        mock = Mock()
        mock.is_initialized = True
        mock.get_stats.return_value = {
            "total_backends": 2,
            "active_backends": 1
        }
        mock.list_available_backends.return_value = [
            {"type": "INLINE_LOCAL", "enabled": True}
        ]
        return mock

    @pytest.fixture
    def mock_approval_manager(self):
        """Create mock approval manager."""
        mock = Mock()
        mock.get_pending.return_value = []
        mock.get_history.return_value = []
        mock.approve.return_value = True
        mock.deny.return_value = True
        return mock

    @pytest.fixture
    def mock_event_logger(self):
        """Create mock event logger."""
        mock = Mock()
        mock._events = []
        mock.get_events.return_value = []
        mock.count_by_type.return_value = {"total": 0}
        mock.get_errors.return_value = []
        mock.get_decisions.return_value = []
        return mock

    @pytest.fixture
    def mock_job_dispatcher(self):
        """Create mock job dispatcher."""
        mock = Mock()
        mock.list_jobs.return_value = []
        mock.get_job.return_value = None
        mock.get_stats.return_value = {"pending": 0, "running": 0}
        mock.cancel_job.return_value = True
        return mock

    @pytest.fixture
    def service(self, mock_orchestrator, mock_runtime_manager,
                mock_approval_manager, mock_event_logger, mock_job_dispatcher):
        """Create OperatorService with mocked dependencies."""
        from ui.services import OperatorService

        svc = OperatorService(
            orchestrator=mock_orchestrator,
            runtime_manager=mock_runtime_manager,
            approval_manager=mock_approval_manager,
            event_logger=mock_event_logger,
            job_dispatcher=mock_job_dispatcher
        )
        svc._initialized = True  # Mark as initialized
        return svc

    def test_get_system_status(self, service, mock_approval_manager,
                               mock_job_dispatcher, mock_event_logger):
        """Test getting system status."""
        mock_approval_manager.get_pending.return_value = [1, 2]
        mock_job_dispatcher.list_jobs.return_value = [{"status": "running"}]
        mock_event_logger._events = [1, 2, 3]
        mock_event_logger.get_errors.return_value = []

        status = service.get_system_status()

        assert status.healthy is True
        assert status.pending_approvals == 2

    def test_get_portfolio(self, service):
        """Test getting portfolio."""
        portfolio = service.get_portfolio()

        assert isinstance(portfolio, list)

    def test_submit_goal(self, service, mock_orchestrator):
        """Test submitting a goal."""
        from ui.services import GoalSubmission

        submission = GoalSubmission(
            objective="Test objective",
            requester="principal"
        )

        result = service.submit_goal(submission)

        mock_orchestrator.orchestrate.assert_called_once()
        assert result.request_id == "req-001"

    def test_get_pending_approvals(self, service, mock_approval_manager):
        """Test getting pending approvals."""
        mock_record = Mock()
        mock_record.record_id = "apr-001"
        mock_record.request_id = "req-001"
        mock_record.action = "test_action"
        mock_record.requester = "principal"
        mock_record.classification = Mock(value="requires_approval")
        mock_record.reason = "Test reason"
        mock_record.created_at = "2024-01-01"
        mock_record.context = {}

        mock_approval_manager.get_pending.return_value = [mock_record]

        pending = service.get_pending_approvals()

        assert len(pending) == 1
        assert pending[0]["record_id"] == "apr-001"

    def test_approve_request(self, service, mock_approval_manager):
        """Test approving a request."""
        # Set up mock to return an approval record
        mock_record = Mock()
        mock_record.request_id = "req-001"
        mock_record.connector_name = None
        mock_record.operation = None
        mock_approval_manager.approve.return_value = mock_record

        result = service.approve_request("apr-001", approver="principal")

        mock_approval_manager.approve.assert_called_once()
        # approve_request now returns a dict with success key
        assert result["success"] is True

    def test_deny_request(self, service, mock_approval_manager):
        """Test denying a request."""
        # Set up mock to return an approval record
        mock_record = Mock()
        mock_record.request_id = "req-001"
        mock_approval_manager.deny.return_value = mock_record

        result = service.deny_request("apr-001", "Not approved", denier="principal")

        mock_approval_manager.deny.assert_called_once()
        # deny_request now returns a dict with success key
        assert result["success"] is True

    def test_get_jobs(self, service, mock_job_dispatcher):
        """Test getting jobs."""
        mock_job = Mock()
        mock_job.job_id = "job-001"
        mock_job.plan_id = "plan-001"
        mock_job.backend_type = Mock(value="INLINE_LOCAL")
        mock_job.status = Mock(value="running")
        mock_job.options = None
        mock_job.dispatched_at = None
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.worker_instance_id = None
        mock_job.retry_count = 0
        mock_job.error = None
        mock_job.is_complete = False

        mock_job_dispatcher.list_jobs.return_value = [mock_job]

        jobs = service.get_jobs(status="running", limit=10)

        assert len(jobs) == 1
        assert jobs[0]["job_id"] == "job-001"

    def test_cancel_job(self, service, mock_job_dispatcher):
        """Test canceling a job."""
        # Set up mock job that can be cancelled
        mock_job = Mock()
        mock_job.plan_id = "plan-001"
        mock_job.is_complete = False
        mock_job_dispatcher.get_job.return_value = mock_job
        mock_job_dispatcher.cancel_job.return_value = True

        result = service.cancel_job("job-001")

        mock_job_dispatcher.cancel_job.assert_called_once_with("job-001")
        # cancel_job now returns a dict with success key
        assert result["success"] is True

    def test_get_events(self, service, mock_event_logger):
        """Test getting events."""
        mock_event = Mock()
        mock_event.to_dict.return_value = {"event_type": "test", "message": "Test event"}

        mock_event_logger.get_events.return_value = [mock_event]

        events = service.get_events(limit=10)

        assert len(events) == 1
        assert events[0]["event_type"] == "test"

    def test_get_backends(self, service, mock_runtime_manager):
        """Test getting backends."""
        mock_runtime_manager.list_available_backends.return_value = [
            {"name": "local", "type": "INLINE_LOCAL", "enabled": True}
        ]

        backends = service.get_backends()

        assert len(backends) == 1


# =============================================================================
# Test Flask Routes
# =============================================================================

class TestFlaskRoutes:
    """Tests for Flask application routes."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from ui.app import app
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def mock_service(self):
        """Create mock operator service."""
        from ui.services import SystemStatus, BusinessSummary

        mock = Mock()
        mock.get_system_status.return_value = SystemStatus(
            healthy=True,
            runtime_initialized=True,
            active_jobs=2,
            pending_approvals=0,
            available_backends=["INLINE_LOCAL"],
            total_events=50,
            recent_errors=0
        )
        mock.get_events.return_value = []
        mock.get_recent_decisions.return_value = []
        mock.get_portfolio.return_value = []
        mock.get_business.return_value = None
        mock.get_orchestration_history.return_value = []
        mock.get_recent_plans.return_value = []
        mock.get_execution_plan.return_value = None
        mock.get_pending_approvals.return_value = []
        mock.get_approval_history.return_value = []
        mock.get_jobs.return_value = []
        mock.get_job.return_value = None
        mock.get_job_detail.return_value = None
        mock.get_job_stats.return_value = {"pending": 0, "running": 0}
        mock.get_event_counts.return_value = {"total": 0}
        mock.get_backends.return_value = []
        mock.get_runtime_stats.return_value = {}
        mock.get_plan_detail.return_value = None
        mock.get_approval_detail.return_value = None
        mock.approve_request.return_value = {"success": True}
        mock.deny_request.return_value = {"success": True}
        mock.cancel_job.return_value = {"success": True}
        mock.retry_job.return_value = {"success": True}

        # Daily operator activation methods
        mock.get_paused_scenarios.return_value = []
        mock.get_failed_jobs.return_value = []
        mock.get_active_blockers.return_value = []
        mock.get_capacity_status.return_value = {"warnings": []}
        mock.get_credentials_summary.return_value = {"expiring_soon": 0}
        mock.list_scenario_runs.return_value = []
        mock.get_connector_actions.return_value = ([], {"failed": 0})
        mock.get_capacity_decisions.return_value = []
        mock.get_combined_status.return_value = {
            "healthy": True,
            "ready": True,
            "dry_run_ready": True,
            "live_ready": False,
        }
        mock.get_operator_action_history.return_value = []

        return mock

    def test_home_route(self, client, mock_service):
        """Test home route returns 200."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/')
            assert response.status_code == 200

    def test_api_status_route(self, client, mock_service):
        """Test API status route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/api/status')
            assert response.status_code == 200
            data = response.get_json()
            assert 'healthy' in data

    def test_portfolio_route(self, client, mock_service):
        """Test portfolio route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/portfolio')
            assert response.status_code == 200

    def test_api_portfolio_route(self, client, mock_service):
        """Test API portfolio route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/api/portfolio')
            assert response.status_code == 200

    def test_portfolio_detail_not_found(self, client, mock_service):
        """Test portfolio detail 404."""
        mock_service.get_business.return_value = None
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/portfolio/nonexistent')
            assert response.status_code == 404

    def test_goals_route(self, client, mock_service):
        """Test goals route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/goals')
            assert response.status_code == 200

    def test_submit_goal_empty(self, client, mock_service):
        """Test goal submission with empty objective."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.post('/goals/submit', data={'objective': ''})
            assert response.status_code == 200
            assert b'required' in response.data.lower()

    def test_api_submit_goal_empty(self, client, mock_service):
        """Test API goal submission with empty objective."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.post('/api/goals',
                                   json={'objective': ''},
                                   content_type='application/json')
            assert response.status_code == 400

    def test_plans_route(self, client, mock_service):
        """Test plans route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/plans')
            assert response.status_code == 200

    def test_plan_detail_not_found(self, client, mock_service):
        """Test plan detail 404."""
        mock_service.get_plan_detail.return_value = None
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/plans/nonexistent')
            assert response.status_code == 404

    def test_approvals_route(self, client, mock_service):
        """Test approvals route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/approvals')
            assert response.status_code == 200

    def test_api_approvals_route(self, client, mock_service):
        """Test API approvals route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/api/approvals')
            assert response.status_code == 200

    def test_approve_route(self, client, mock_service):
        """Test approve action."""
        mock_service.approve_request.return_value = True
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.post('/approvals/apr-001/approve')
            assert response.status_code == 302  # Redirect

    def test_deny_route(self, client, mock_service):
        """Test deny action."""
        mock_service.deny_request.return_value = True
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.post('/approvals/apr-001/deny',
                                   data={'reason': 'Test denial'})
            assert response.status_code == 302  # Redirect

    def test_jobs_route(self, client, mock_service):
        """Test jobs route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/jobs')
            assert response.status_code == 200

    def test_jobs_filter_route(self, client, mock_service):
        """Test jobs route with filter."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/jobs?status=running')
            assert response.status_code == 200

    def test_job_detail_not_found(self, client, mock_service):
        """Test job detail 404."""
        mock_service.get_job_detail.return_value = None
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/jobs/nonexistent')
            assert response.status_code == 404

    def test_cancel_job_route(self, client, mock_service):
        """Test cancel job action."""
        mock_service.cancel_job.return_value = True
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.post('/jobs/job-001/cancel')
            assert response.status_code == 302  # Redirect

    def test_events_route(self, client, mock_service):
        """Test events route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/events')
            assert response.status_code == 200

    def test_events_filter_route(self, client, mock_service):
        """Test events route with filter."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/events?severity=error')
            assert response.status_code == 200

    def test_api_events_route(self, client, mock_service):
        """Test API events route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/api/events')
            assert response.status_code == 200

    def test_backends_route(self, client, mock_service):
        """Test backends route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/backends')
            assert response.status_code == 200

    def test_api_backends_route(self, client, mock_service):
        """Test API backends route."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/api/backends')
            assert response.status_code == 200

    def test_404_handler_api(self, client):
        """Test 404 handler returns JSON for API."""
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data


# =============================================================================
# Test Integration
# =============================================================================

class TestServiceIntegration:
    """Integration tests for service with real dependencies."""

    def test_get_operator_service_singleton(self):
        """Test operator service is singleton."""
        import ui.services
        # Reset singleton for test
        ui.services._operator_service = None

        service1 = ui.services.get_operator_service()
        service2 = ui.services.get_operator_service()

        assert service1 is service2

        # Clean up
        ui.services._operator_service = None

    def test_service_creation_with_defaults(self):
        """Test service initializes with defaults."""
        from ui.services import OperatorService

        service = OperatorService()

        # Before initialization, components are None
        assert service._initialized is False


# =============================================================================
# Test Smoke Routes - Critical Operator Pages
# =============================================================================

class TestSmokeRoutes:
    """Smoke tests for critical operator routes to catch template/context bugs."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from ui.app import app
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def mock_service(self):
        """Create comprehensive mock operator service for smoke tests."""
        from ui.services import SystemStatus

        mock = Mock()

        # System status
        mock.get_system_status.return_value = SystemStatus(
            healthy=True,
            runtime_initialized=True,
            active_jobs=0,
            pending_approvals=0,
            available_backends=["INLINE_LOCAL"],
            total_events=10,
            recent_errors=0
        )

        # Dashboard data
        mock.get_paused_scenarios.return_value = []
        mock.get_failed_jobs.return_value = []
        mock.get_active_blockers.return_value = []
        mock.get_capacity_status.return_value = {"warnings": []}
        mock.get_credentials_summary.return_value = {"expiring_soon": 0, "missing": 0}
        mock.list_scenario_runs.return_value = []
        mock.get_connector_actions.return_value = ([], {"total": 0, "failed": 0})
        mock.get_capacity_decisions.return_value = []
        mock.get_combined_status.return_value = {
            "healthy": True,
            "ready": True,
            "dry_run_ready": True,
            "live_ready": False,
            "live_connectors": [],
        }
        mock.get_operator_action_history.return_value = []
        mock.get_events.return_value = []
        mock.get_recent_decisions.return_value = []

        # Work queue
        mock.get_pending_approvals.return_value = []
        mock.get_approval_history.return_value = []

        # Scenarios
        mock.list_scenarios.return_value = []
        mock.get_scenario_run_stats.return_value = {"total": 0, "running": 0, "completed": 0}

        # Playbook/Templates
        mock.get_templates.return_value = []
        mock.get_template_summary.return_value = {"total": 0}
        mock.list_template_launches.return_value = []

        # Health & Readiness
        mock.get_health_report.return_value = {
            "status": "healthy",
            "subsystems": {},
            "timestamp": "2024-01-01T00:00:00Z"
        }
        mock.get_readiness_report.return_value = {
            "overall_status": "ready",
            "dry_run_ready": True,
            "live_ready": False,
            "components": [],
            "connectors": [],
            "missing_required": [],
            "warnings": [],
            "recommendations": [],
            "timestamp": "2024-01-01T00:00:00Z"
        }
        mock.get_setup_checklist.return_value = {
            "status": "complete",
            "items": [
                {"label": "Test item", "completed": True, "action": None}
            ],
            "completed_count": 1,
            "total_count": 1,
            "next_step": None,
            "instructions": []
        }

        # Discovery
        mock.list_discovery_scans.return_value = []
        mock.get_discovery_scan_result.return_value = None
        mock.run_discovery_scan.return_value = {
            "scan_id": "test-scan",
            "mode": "theme_scan",
            "input_summary": "Test",
            "total_candidates": 0,
            "candidates": [],
            "scan_timestamp": "2024-01-01T00:00:00",
            "metadata": {},
        }

        return mock

    def test_smoke_home(self, client, mock_service):
        """Smoke test: / (home) page renders without errors."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/')
            assert response.status_code == 200
            # Updated for productization reset - home page now says "Welcome to Project Alpha"
            assert b'Project Alpha' in response.data or b'Welcome' in response.data

    def test_smoke_work_queue(self, client, mock_service):
        """Smoke test: /work-queue page renders without errors."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/work-queue')
            assert response.status_code == 200

    def test_smoke_approvals(self, client, mock_service):
        """Smoke test: /approvals page renders without errors."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/approvals')
            assert response.status_code == 200

    def test_smoke_scenarios(self, client, mock_service):
        """Smoke test: /scenarios page renders without errors."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/scenarios')
            assert response.status_code == 200

    def test_smoke_playbook(self, client, mock_service):
        """Smoke test: /playbook page renders without errors."""
        with patch('ui.services.get_playbook_content', return_value={"title": "Test", "sections": []}):
            with patch('ui.app.get_service', return_value=mock_service):
                response = client.get('/playbook')
                assert response.status_code == 200

    def test_smoke_templates(self, client, mock_service):
        """Smoke test: /templates page renders without errors."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/templates')
            assert response.status_code == 200

    def test_smoke_health(self, client, mock_service):
        """Smoke test: /health page renders without errors."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/health')
            assert response.status_code == 200

    def test_smoke_readiness(self, client, mock_service):
        """Smoke test: /readiness page renders without errors and checklist iterates correctly."""
        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/readiness')
            assert response.status_code == 200
            # Verify checklist items are rendered (not dict.items())
            assert b'Test item' in response.data

    def test_readiness_checklist_data_structure(self, client, mock_service):
        """Test /readiness checklist data is passed correctly to template."""
        # This test specifically validates the bug fix for checklist.items vs checklist['items']
        mock_service.get_setup_checklist.return_value = {
            "status": "incomplete",
            "items": [
                {"label": "Setup credentials", "completed": False, "action": "export API_KEY=xxx"},
                {"label": "Initialize runtime", "completed": True, "action": None}
            ],
            "completed_count": 1,
            "total_count": 2,
            "next_step": "Setup credentials",
            "instructions": ["Follow the setup guide"]
        }

        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/readiness')
            assert response.status_code == 200
            # Verify both items are rendered
            assert b'Setup credentials' in response.data
            assert b'Initialize runtime' in response.data
            assert b'export API_KEY=xxx' in response.data

    def test_discover_page_loads(self, client, mock_service):
        """Test /discover page loads with discovery scans."""
        mock_service.list_discovery_scans.return_value = [
            {
                "scan_id": "scan-123",
                "mode": "theme_scan",
                "input_summary": "Theme Scan: AI automation",
                "total_candidates": 3,
                "scan_timestamp": "2024-01-01T00:00:00",
            }
        ]

        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/discover')
            assert response.status_code == 200
            assert b'Discover Opportunities' in response.data
            assert b'Market Pain-Point Scan' in response.data
            assert b'Problem Exploration' in response.data
            assert b'Industry Scan' in response.data

    def test_discover_scan_market(self, client, mock_service):
        """Test /discover/scan-market runs market scan."""
        mock_service.run_discovery_scan.return_value = {
            "scan_id": "scan-123",
            "mode": "pain_point_scan",
            "input_summary": "Market: SaaS",
            "total_candidates": 3,
            "candidates": [],
            "scan_timestamp": "2024-01-01T00:00:00",
            "metadata": {},
        }

        with patch('ui.app.get_service', return_value=mock_service):
            response = client.post('/discover/scan-market', data={
                'market_theme': 'SaaS'
            }, follow_redirects=False)
            assert response.status_code == 302
            assert '/discover/result/scan-123' in response.location

    def test_discover_scan_industry(self, client, mock_service):
        """Test /discover/scan-industry runs industry scan."""
        mock_service.run_discovery_scan.return_value = {
            "scan_id": "scan-456",
            "mode": "industry_scan",
            "input_summary": "Industry: Healthcare",
            "total_candidates": 3,
            "candidates": [],
            "scan_timestamp": "2024-01-01T00:00:00",
            "metadata": {},
        }

        with patch('ui.app.get_service', return_value=mock_service):
            response = client.post('/discover/scan-industry', data={
                'industry': 'Healthcare'
            }, follow_redirects=False)
            assert response.status_code == 302
            assert '/discover/result/scan-456' in response.location

    def test_discover_from_theme(self, client, mock_service):
        """Test /discover/from-theme runs theme scan."""
        mock_service.run_discovery_scan.return_value = {
            "scan_id": "scan-789",
            "mode": "theme_scan",
            "input_summary": "Theme: Automation",
            "total_candidates": 3,
            "candidates": [],
            "scan_timestamp": "2024-01-01T00:00:00",
            "metadata": {},
        }

        with patch('ui.app.get_service', return_value=mock_service):
            response = client.post('/discover/from-theme', data={
                'theme': 'Automation'
            }, follow_redirects=False)
            assert response.status_code == 302
            assert '/discover/result/scan-789' in response.location

    def test_discover_result(self, client, mock_service):
        """Test /discover/result/<scan_id> shows results."""
        mock_service.get_discovery_scan_result.return_value = {
            "scan_id": "scan-123",
            "mode": "theme_scan",
            "input_summary": "Theme: AI automation",
            "total_candidates": 2,
            "scan_timestamp": "2024-01-01T00:00:00",
            "candidates": [
                {
                    "candidate_id": "cand-1",
                    "title": "AI Automation Platform",
                    "pain_point": "Manual AI processes are time-consuming",
                    "target_customer": "Growing businesses",
                    "urgency": "high",
                    "monetization_clarity": "emerging",
                    "execution_domains": ["automation", "ai"],
                    "automation_potential": "high",
                    "complexity": "medium",
                    "recommended_action": "Build MVP",
                    "confidence": 0.7,
                    "discovered_via": "theme_scan",
                    "discovered_at": "2024-01-01T00:00:00",
                }
            ],
            "metadata": {},
        }

        with patch('ui.app.get_service', return_value=mock_service):
            response = client.get('/discover/result/scan-123')
            assert response.status_code == 200
            assert b'Discovery Scan Results' in response.data
            assert b'AI Automation Platform' in response.data
            assert b'Manual AI processes are time-consuming' in response.data
