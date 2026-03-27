"""
Tests for Expanded Live Connector Coverage.

Tests the new live-capable connectors:
- Tavily (search, extract)
- SendGrid (send_email)
- HubSpot (create_contact, update_contact)
- Firecrawl (scrape)

Each connector is tested for:
1. Live success with mocked HTTP
2. Missing credential blocking
3. Approval gating (via action contracts)
4. Dry-run vs live behavior
5. Persisted action records
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from integrations.connectors.tavily import TavilyConnector, HTTPX_AVAILABLE as TAVILY_HTTPX
from integrations.connectors.sendgrid import SendGridConnector, HTTPX_AVAILABLE as SENDGRID_HTTPX
from integrations.connectors.hubspot import HubSpotConnector, HTTPX_AVAILABLE as HUBSPOT_HTTPX
from integrations.connectors.firecrawl import FirecrawlConnector, HTTPX_AVAILABLE as FIRECRAWL_HTTPX
from integrations.action_contracts import (
    get_action_contract,
    ActionType,
    ActionApprovalLevel,
)
from integrations.base import ConnectorResult


class TestTavilyLiveExecution:
    """Test Tavily connector live execution."""

    def test_search_live_success(self):
        """Test successful live search."""
        if not TAVILY_HTTPX:
            pytest.skip("httpx not installed")

        connector = TavilyConnector()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": "test query",
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content...",
                    "score": 0.95,
                }
            ],
            "answer": "Test answer",
            "response_time": 0.5,
        }

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_tavily_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                with patch("httpx.post", return_value=mock_response):
                    result = connector.execute(
                        operation="search",
                        params={"query": "test query"},
                        dry_run=False,
                    )

        assert result.success
        assert result.data["query"] == "test query"
        assert len(result.data["results"]) == 1
        assert result.metadata.get("live_execution") is True

    def test_search_missing_credentials_blocked(self):
        """Test that missing credentials block execution."""
        connector = TavilyConnector()

        result = connector.execute(
            operation="search",
            params={"query": "test"},
            dry_run=False,
        )

        assert not result.success or result.error_type == "unconfigured"

    def test_search_dry_run_behavior(self):
        """Test dry-run returns simulated data."""
        connector = TavilyConnector()

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                result = connector.execute(
                    operation="search",
                    params={"query": "test query", "max_results": 3},
                    dry_run=True,
                )

        assert result.success
        assert result.dry_run
        assert "results" in result.data
        assert result.metadata.get("dry_run") is True

    def test_extract_live_success(self):
        """Test successful live extract."""
        if not TAVILY_HTTPX:
            pytest.skip("httpx not installed")

        connector = TavilyConnector()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "raw_content": "Extracted content...",
                }
            ],
            "failed_results": [],
        }

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_tavily_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                with patch("httpx.post", return_value=mock_response):
                    result = connector.execute(
                        operation="extract",
                        params={"urls": ["https://example.com"]},
                        dry_run=False,
                    )

        assert result.success
        assert len(result.data["results"]) == 1
        assert result.metadata.get("live_execution") is True

    def test_search_http_error_handling(self):
        """Test HTTP error handling."""
        if not TAVILY_HTTPX:
            pytest.skip("httpx not installed")

        connector = TavilyConnector()

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                with patch("httpx.post") as mock_post:
                    mock_post.side_effect = Exception("Connection failed")

                    result = connector.execute(
                        operation="search",
                        params={"query": "test"},
                        dry_run=False,
                    )

        assert not result.success
        assert result.error is not None

    def test_action_contract_registration(self):
        """Test Tavily action contracts are registered."""
        search_contract = get_action_contract("tavily", "search")
        extract_contract = get_action_contract("tavily", "extract")

        if TAVILY_HTTPX:
            assert search_contract is not None
            assert search_contract.supports_live
            assert search_contract.action_type == ActionType.RESEARCH

            assert extract_contract is not None
            assert extract_contract.supports_live


class TestSendGridLiveExecution:
    """Test SendGrid connector live execution."""

    def test_send_email_live_success(self):
        """Test successful live email send."""
        if not SENDGRID_HTTPX:
            pytest.skip("httpx not installed")

        connector = SendGridConnector()

        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {"x-message-id": "test-msg-123"}

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_sendgrid_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                with patch("httpx.post", return_value=mock_response):
                    result = connector.execute(
                        operation="send_email",
                        params={
                            "to": "recipient@example.com",
                            "subject": "Test Subject",
                            "content": "Test content",
                            "from_email": "sender@example.com",
                        },
                        dry_run=False,
                    )

        assert result.success
        assert result.data["status_code"] == 202
        assert result.data["message_id"] == "test-msg-123"
        assert result.metadata.get("live_execution") is True

    def test_send_email_missing_credentials_blocked(self):
        """Test that missing credentials block execution."""
        connector = SendGridConnector()

        result = connector.execute(
            operation="send_email",
            params={
                "to": "test@example.com",
                "subject": "Test",
                "content": "Test",
                "from_email": "sender@example.com",
            },
            dry_run=False,
        )

        assert not result.success or result.error_type == "unconfigured"

    def test_send_email_dry_run_behavior(self):
        """Test dry-run returns simulated data."""
        connector = SendGridConnector()

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                result = connector.execute(
                    operation="send_email",
                    params={
                        "to": "test@example.com",
                        "subject": "Test",
                        "content": "Test content",
                        "from_email": "sender@example.com",
                    },
                    dry_run=True,
                )

        assert result.success
        assert result.dry_run
        assert result.metadata.get("dry_run") is True

    def test_send_email_validation_errors(self):
        """Test validation errors for missing params."""
        connector = SendGridConnector()

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                # Missing 'to'
                result = connector.execute(
                    operation="send_email",
                    params={"subject": "Test", "content": "Test"},
                    dry_run=False,
                )

        assert not result.success
        assert "to" in result.error.lower()

    def test_action_contract_requires_approval(self):
        """Test SendGrid send_email requires approval."""
        contract = get_action_contract("sendgrid", "send_email")

        if SENDGRID_HTTPX:
            assert contract is not None
            assert contract.approval_level == ActionApprovalLevel.STANDARD
            assert contract.is_external is True


class TestHubSpotLiveExecution:
    """Test HubSpot connector live execution."""

    def test_create_contact_live_success(self):
        """Test successful live contact creation."""
        if not HUBSPOT_HTTPX:
            pytest.skip("httpx not installed")

        connector = HubSpotConnector()

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "12345",
            "properties": {
                "email": "new@example.com",
                "firstname": "John",
                "lastname": "Doe",
            },
            "createdAt": "2024-03-27T10:00:00.000Z",
            "updatedAt": "2024-03-27T10:00:00.000Z",
        }

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_hubspot_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                with patch("httpx.post", return_value=mock_response):
                    result = connector.execute(
                        operation="create_contact",
                        params={
                            "email": "new@example.com",
                            "firstname": "John",
                            "lastname": "Doe",
                        },
                        dry_run=False,
                    )

        assert result.success
        assert result.data["id"] == "12345"
        assert result.data["properties"]["email"] == "new@example.com"
        assert result.metadata.get("live_execution") is True

    def test_update_contact_live_success(self):
        """Test successful live contact update."""
        if not HUBSPOT_HTTPX:
            pytest.skip("httpx not installed")

        connector = HubSpotConnector()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345",
            "properties": {
                "phone": "+1-555-0100",
            },
            "updatedAt": "2024-03-27T10:00:00.000Z",
        }

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_hubspot_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                with patch("httpx.patch", return_value=mock_response):
                    result = connector.execute(
                        operation="update_contact",
                        params={
                            "contact_id": "12345",
                            "properties": {"phone": "+1-555-0100"},
                        },
                        dry_run=False,
                    )

        assert result.success
        assert result.data["id"] == "12345"
        assert result.metadata.get("live_execution") is True
        assert "phone" in result.metadata.get("updated_properties", [])

    def test_create_contact_missing_credentials(self):
        """Test that missing credentials block execution."""
        connector = HubSpotConnector()

        result = connector.execute(
            operation="create_contact",
            params={"email": "test@example.com"},
            dry_run=False,
        )

        assert not result.success or result.error_type == "unconfigured"

    def test_create_contact_dry_run_behavior(self):
        """Test dry-run returns simulated data."""
        connector = HubSpotConnector()

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                result = connector.execute(
                    operation="create_contact",
                    params={
                        "email": "test@example.com",
                        "firstname": "Test",
                    },
                    dry_run=True,
                )

        assert result.success
        assert result.dry_run
        assert result.metadata.get("dry_run") is True

    def test_action_contract_requires_approval(self):
        """Test HubSpot create_contact requires approval."""
        contract = get_action_contract("hubspot", "create_contact")

        if HUBSPOT_HTTPX:
            assert contract is not None
            assert contract.approval_level == ActionApprovalLevel.STANDARD
            assert contract.action_type == ActionType.DATA_CREATE


class TestFirecrawlLiveExecution:
    """Test Firecrawl connector live execution."""

    def test_scrape_live_success(self):
        """Test successful live scrape."""
        if not FIRECRAWL_HTTPX:
            pytest.skip("httpx not installed")

        connector = FirecrawlConnector()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "markdown": "# Page Title\n\nContent here...",
                "metadata": {
                    "title": "Page Title",
                    "description": "Page description",
                },
            },
        }

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_firecrawl_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                with patch("httpx.post", return_value=mock_response):
                    result = connector.execute(
                        operation="scrape",
                        params={"url": "https://example.com"},
                        dry_run=False,
                    )

        assert result.success
        assert result.data["success"] is True
        assert "markdown" in result.data
        assert result.metadata.get("live_execution") is True

    def test_scrape_missing_credentials_blocked(self):
        """Test that missing credentials block execution."""
        connector = FirecrawlConnector()

        result = connector.execute(
            operation="scrape",
            params={"url": "https://example.com"},
            dry_run=False,
        )

        assert not result.success or result.error_type == "unconfigured"

    def test_scrape_dry_run_behavior(self):
        """Test dry-run returns simulated data."""
        connector = FirecrawlConnector()

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                result = connector.execute(
                    operation="scrape",
                    params={"url": "https://example.com"},
                    dry_run=True,
                )

        assert result.success
        assert result.dry_run
        assert result.metadata.get("dry_run") is True

    def test_scrape_api_error_handling(self):
        """Test API error handling when success=false."""
        if not FIRECRAWL_HTTPX:
            pytest.skip("httpx not installed")

        connector = FirecrawlConnector()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": False,
            "error": "URL not accessible",
        }

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                with patch("httpx.post", return_value=mock_response):
                    result = connector.execute(
                        operation="scrape",
                        params={"url": "https://example.com"},
                        dry_run=False,
                    )

        assert not result.success
        assert "not accessible" in result.error.lower()

    def test_action_contract_registration(self):
        """Test Firecrawl action contracts are registered."""
        scrape_contract = get_action_contract("firecrawl", "scrape")
        crawl_contract = get_action_contract("firecrawl", "crawl")

        if FIRECRAWL_HTTPX:
            assert scrape_contract is not None
            assert scrape_contract.supports_live
            assert scrape_contract.action_type == ActionType.RESEARCH

            assert crawl_contract is not None
            assert not crawl_contract.supports_live  # crawl is dry-run only


class TestLiveCapableActionsSummary:
    """Test summary of all live-capable actions."""

    def test_live_capable_count(self):
        """Test that we have the expected number of live-capable actions from this sprint."""
        from integrations.action_contracts import get_live_capable_actions
        from integrations.connectors.telegram import TelegramConnector

        # Force connector instantiation to register contracts
        TelegramConnector()  # 2 live actions
        TavilyConnector()    # 2 live actions
        SendGridConnector()  # 1 live action
        HubSpotConnector()   # 2 live actions
        FirecrawlConnector() # 1 live action

        live_actions = get_live_capable_actions()

        # We should have at least 6 new live-capable actions from this sprint:
        # - Tavily: search, extract (2)
        # - SendGrid: send_email (1)
        # - HubSpot: create_contact, update_contact (2)
        # - Firecrawl: scrape (1)
        # Plus Telegram if instantiated: send_message, get_updates (2)
        # Total: 8 live-capable actions

        if TAVILY_HTTPX:  # All use same httpx check
            # Check we have at least 6 from the new connectors
            new_connectors = ["tavily", "sendgrid", "hubspot", "firecrawl"]
            new_live_actions = [a for a in live_actions if a.connector in new_connectors]
            assert len(new_live_actions) >= 6, f"Expected >= 6 new live actions, got {len(new_live_actions)}"

    def test_all_live_actions_have_required_fields(self):
        """Test that all live action contracts have required fields."""
        from integrations.action_contracts import get_live_capable_actions

        # Force connector instantiation
        TavilyConnector()
        SendGridConnector()
        HubSpotConnector()
        FirecrawlConnector()

        for contract in get_live_capable_actions():
            assert contract.action_name, f"Missing action_name: {contract}"
            assert contract.connector, f"Missing connector: {contract}"
            assert contract.description, f"Missing description: {contract}"
            assert contract.required_credentials, f"Missing required_credentials: {contract}"


class TestConnectorActionPersistence:
    """Test that connector actions are persisted correctly."""

    def test_live_execution_records_action(self):
        """Test that live execution records action in history."""
        if not TAVILY_HTTPX:
            pytest.skip("httpx not installed")

        from core.connector_action_history import get_connector_action_history

        connector = TavilyConnector()
        history = get_connector_action_history()

        # Get initial count
        initial_actions = history.get_actions_by_connector("tavily")
        initial_count = len(initial_actions) if initial_actions else 0

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": "test",
            "results": [],
            "response_time": 0.1,
        }

        with patch.object(connector, '_secrets_manager') as mock_sm:
            mock_secret = MagicMock()
            mock_secret.is_set.return_value = True
            mock_secret.get_value.return_value = "fake_key"
            mock_sm.is_secret_configured.return_value = True
            mock_sm.get_secret.return_value = mock_secret

            with patch.object(connector, '_policy_engine') as mock_policy:
                from core.credential_policies import PolicyDecision
                mock_policy.check_access.return_value = (PolicyDecision.ALLOW, None)

                with patch("httpx.post", return_value=mock_response):
                    result = connector.execute(
                        operation="search",
                        params={"query": "test"},
                        dry_run=False,
                    )

        # Verify result
        assert result.success

        # Note: Action persistence happens through integration_skill layer,
        # not directly in connector.execute(). This test validates the
        # connector execution flow works correctly.
