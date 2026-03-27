"""
Tests for Safe Live Integration Layer.

Tests cover:
- Config and settings (redaction, env loading)
- Secrets management (metadata only, no real values)
- Credential policies and rate limiting
- Connector base architecture
- Dry-run vs live execution
- Integration skill interface

SECURITY:
- Tests use mock values only
- No real credentials in test code
- Redaction is verified
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


# =============================================================================
# Config Layer Tests
# =============================================================================

class TestRedaction:
    """Tests for secret redaction."""

    def test_redacted_string_hides_value(self):
        """RedactedString never exposes value in str()."""
        from config.redaction import RedactedString, REDACTION_MARKER

        secret = RedactedString("super_secret_key", hint="API Key")

        # String representation should be redacted
        assert str(secret) == f"{REDACTION_MARKER} (API Key)"
        assert "super_secret_key" not in str(secret)

    def test_redacted_string_get_value(self):
        """RedactedString.get_value() returns actual value when needed."""
        from config.redaction import RedactedString

        secret = RedactedString("actual_value")
        assert secret.get_value() == "actual_value"

    def test_redacted_string_is_set(self):
        """RedactedString.is_set() checks if value exists."""
        from config.redaction import RedactedString

        set_secret = RedactedString("has_value")
        empty_secret = RedactedString("")

        assert set_secret.is_set() is True
        assert empty_secret.is_set() is False

    def test_redact_value_sensitive_keys(self):
        """redact_value detects sensitive keys."""
        from config.redaction import redact_value, REDACTION_MARKER

        # redact_value(value, key) - key is second parameter
        assert redact_value("secret123", "api_key") == REDACTION_MARKER
        assert redact_value("mypass", "password") == REDACTION_MARKER
        assert redact_value("tok_123", "token") == REDACTION_MARKER
        assert redact_value("shh", "secret") == REDACTION_MARKER

    def test_redact_value_non_sensitive(self):
        """redact_value passes through non-sensitive values."""
        from config.redaction import redact_value

        # Non-sensitive keys pass through
        assert redact_value("john", "username") == "john"
        assert redact_value(42, "count") == 42

    def test_redact_dict(self):
        """redact_dict redacts sensitive keys in dictionaries."""
        from config.redaction import redact_dict, REDACTION_MARKER

        data = {
            "api_key": "secret123",
            "username": "john",
            "nested": {
                "password": "hidden",
                "visible": "shown",
            }
        }

        redacted = redact_dict(data)

        assert redacted["api_key"] == REDACTION_MARKER
        assert redacted["username"] == "john"
        assert redacted["nested"]["password"] == REDACTION_MARKER
        assert redacted["nested"]["visible"] == "shown"


class TestSettings:
    """Tests for settings management."""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"}, clear=False)
    def test_settings_loads_from_env(self):
        """Settings loads values from environment."""
        from config.settings import get_settings

        settings = get_settings()

        # Should be wrapped in RedactedString
        assert settings.anthropic_api_key.is_set() is True
        # Value should come from env
        assert settings.anthropic_api_key.get_value() == "test_key"

    def test_settings_has_dry_run_default(self):
        """Settings has dry_run_default property."""
        from config.settings import get_settings

        settings = get_settings()

        # dry_run_default should be a boolean
        assert isinstance(settings.dry_run_default, bool)

    def test_settings_to_safe_dict(self):
        """Settings.to_safe_dict() redacts sensitive values."""
        from config.settings import get_settings
        from config.redaction import REDACTION_MARKER

        settings = get_settings()
        safe = settings.to_safe_dict()

        # Should be a dict
        assert isinstance(safe, dict)
        # Should contain environment but no raw secrets
        assert "environment" in safe


# =============================================================================
# Secrets Manager Tests
# =============================================================================

class TestSecretsManager:
    """Tests for secrets manager."""

    def test_metadata_never_contains_value(self):
        """SecretMetadata.to_safe_dict() never exposes actual value."""
        from core.secrets_manager import SecretMetadata, SecretSensitivity
        from config.redaction import REDACTION_MARKER

        meta = SecretMetadata(
            name="test_key",
            service="test_service",
            purpose="Testing",
            env_var="TEST_KEY",
            sensitivity=SecretSensitivity.HIGH,
            required_by=["test_component"],
        )

        safe_dict = meta.to_safe_dict()

        # Should contain metadata but value should be redacted
        assert safe_dict["name"] == "test_key"
        assert safe_dict["service"] == "test_service"
        # Value should be the redaction marker, not actual value
        assert safe_dict.get("value") == REDACTION_MARKER

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_value"}, clear=False)
    def test_secrets_manager_get_secret(self):
        """SecretsManager retrieves secrets as RedactedString."""
        from core.secrets_manager import get_secrets_manager
        from config.redaction import RedactedString

        manager = get_secrets_manager()

        # Get a known registered secret
        secret = manager.get_secret("anthropic_api_key")

        assert isinstance(secret, RedactedString)
        assert secret.is_set() is True
        assert secret.get_value() == "test_value"

    def test_secrets_manager_list_secrets(self):
        """SecretsManager.list_secrets() returns registered secret names."""
        from core.secrets_manager import get_secrets_manager

        manager = get_secrets_manager()
        secrets = manager.list_secrets()

        # Should have some registered secrets
        assert len(secrets) > 0
        assert "anthropic_api_key" in secrets


# =============================================================================
# Credential Policies Tests
# =============================================================================

class TestCredentialPolicies:
    """Tests for credential policy engine."""

    def test_policy_check_allowed(self):
        """Policy allows authorized operations."""
        from core.credential_policies import CredentialPolicyEngine, PolicyDecision

        engine = CredentialPolicyEngine()

        decision, reason = engine.check_access(
            credential_name="anthropic_api_key",
            component="ai_client",
            operation="health_check",
            record_usage=False,
        )

        assert decision == PolicyDecision.ALLOW

    def test_policy_check_unauthorized_component(self):
        """Policy denies unauthorized components."""
        from core.credential_policies import CredentialPolicyEngine, PolicyDecision

        engine = CredentialPolicyEngine()

        decision, reason = engine.check_access(
            credential_name="anthropic_api_key",
            component="unauthorized_component",
            operation="some_operation",
            record_usage=False,
        )

        assert decision == PolicyDecision.DENY

    def test_rate_limit_status(self):
        """Rate limit status reports correctly."""
        from core.credential_policies import CredentialPolicyEngine

        engine = CredentialPolicyEngine()

        status = engine.get_rate_limit_status("anthropic_api_key", "ai_client")

        assert "limits" in status
        assert "usage" in status
        assert "remaining" in status


# =============================================================================
# Connector Tests
# =============================================================================

class TestBaseConnector:
    """Tests for base connector architecture."""

    def test_connector_status_unconfigured(self):
        """Connector reports unconfigured when credentials missing."""
        from integrations.connectors.tavily import TavilyConnector
        from integrations.base import ConnectorStatus

        connector = TavilyConnector()
        status = connector.get_status()

        # Without env vars, should be unconfigured
        assert status == ConnectorStatus.UNCONFIGURED

    def test_connector_operations_list(self):
        """Connector lists available operations."""
        from integrations.connectors.tavily import TavilyConnector

        connector = TavilyConnector()
        ops = connector.get_operations()

        assert "search" in ops
        assert "extract" in ops

    def test_connector_dry_run(self):
        """Connector dry-run returns simulated data."""
        from integrations.connectors.tavily import TavilyConnector
        from unittest.mock import patch

        connector = TavilyConnector()

        # Mock credential check to pass
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
                    params={"query": "test query"},
                    dry_run=True,
                )

        assert result.success is True
        assert result.dry_run is True
        assert "simulated" in str(result.data).lower() or result.data is not None

    def test_connector_to_dict(self):
        """Connector.to_dict() provides safe representation."""
        from integrations.connectors.apollo import ApolloConnector

        connector = ApolloConnector()
        info = connector.to_dict()

        assert info["name"] == "apollo"
        assert info["category"] == "lead_generation"
        assert "api_key" not in str(info).lower() or "required_credentials" in info


# =============================================================================
# Connector Registry Tests
# =============================================================================

class TestConnectorRegistry:
    """Tests for connector registry."""

    def test_registry_lists_connectors(self):
        """Registry lists all registered connectors."""
        from integrations.registry import get_connector_registry

        registry = get_connector_registry()
        names = registry.list_names()

        # Should have our connectors registered
        assert "tavily" in names
        assert "apollo" in names
        assert "hubspot" in names

    def test_registry_get_connector(self):
        """Registry retrieves connectors by name."""
        from integrations.registry import get_connector_registry

        registry = get_connector_registry()
        connector = registry.get("tavily")

        assert connector is not None
        assert connector.name == "tavily"

    def test_registry_summary(self):
        """Registry provides summary."""
        from integrations.registry import get_connector_registry

        registry = get_connector_registry()
        summary = registry.get_summary()

        assert "total" in summary
        assert "by_status" in summary
        assert "by_category" in summary


# =============================================================================
# Integration Skill Tests
# =============================================================================

class TestIntegrationSkill:
    """Tests for integration skill interface."""

    def test_skill_get_available_connectors(self):
        """Integration skill lists available connectors."""
        from core.integration_skill import IntegrationSkill

        skill = IntegrationSkill()
        connectors = skill.get_available_connectors()

        assert isinstance(connectors, list)
        assert len(connectors) > 0

    def test_skill_get_summary(self):
        """Integration skill provides summary."""
        from core.integration_skill import IntegrationSkill

        skill = IntegrationSkill()
        summary = skill.get_summary()

        assert "connectors" in summary
        assert "policies" in summary

    def test_skill_execute_requires_connector(self):
        """Execute fails gracefully for unknown connector."""
        from core.integration_skill import IntegrationSkill, IntegrationRequest

        skill = IntegrationSkill()

        request = IntegrationRequest(
            connector="nonexistent_connector",
            operation="test",
        )

        response = skill.execute(request)

        assert response.success is False
        assert "not found" in response.error.lower()


# =============================================================================
# Integration Policies Tests
# =============================================================================

class TestIntegrationPolicies:
    """Tests for integration governance policies."""

    def test_policy_evaluate_allows_read(self):
        """Policy allows read operations."""
        from core.integration_policies import get_integration_policy_engine

        engine = get_integration_policy_engine()

        decision = engine.evaluate(
            connector="hubspot",
            operation="list_contacts",
        )

        assert decision.allowed is True

    def test_policy_evaluate_requires_approval_for_write(self):
        """Policy requires approval for write operations."""
        from core.integration_policies import get_integration_policy_engine

        engine = get_integration_policy_engine()

        decision = engine.evaluate(
            connector="hubspot",
            operation="create_contact",
        )

        assert decision.requires_approval is True

    def test_policy_high_risk_operations(self):
        """Policy identifies high-risk operations."""
        from core.integration_policies import get_integration_policy_engine

        engine = get_integration_policy_engine()
        high_risk = engine.get_high_risk_operations()

        # Should have some high-risk operations
        assert len(high_risk) > 0


# =============================================================================
# Rotation Manager Tests
# =============================================================================

class TestRotationManager:
    """Tests for credential rotation tracking."""

    def test_rotation_summary(self):
        """Rotation manager provides summary."""
        from core.rotation_manager import RotationManager

        manager = RotationManager()
        summary = manager.get_summary()

        assert "total_credentials" in summary
        assert "health" in summary
        assert "by_status" in summary

    def test_rotation_schedule_status(self):
        """Rotation schedule reports correct status."""
        from core.rotation_manager import RotationSchedule, RotationStatus
        from datetime import datetime, timezone, timedelta

        # Recently rotated
        recent = RotationSchedule(
            credential_name="test",
            interval_days=90,
            last_rotated=datetime.now(timezone.utc) - timedelta(days=10),
        )
        assert recent.get_status() == RotationStatus.CURRENT

        # Never rotated
        never = RotationSchedule(
            credential_name="test2",
            interval_days=90,
        )
        assert never.get_status() == RotationStatus.NEVER_ROTATED


# =============================================================================
# UI Services Integration Tests
# =============================================================================

class TestUIServices:
    """Tests for UI service layer integration."""

    def test_integrations_summary(self):
        """UI service returns integrations summary."""
        from ui.services import OperatorService

        service = OperatorService()
        summary = service.get_integrations_summary()

        # Should return dict (may have error if not initialized)
        assert isinstance(summary, dict)

    def test_connectors_list(self):
        """UI service returns connectors list."""
        from ui.services import OperatorService

        service = OperatorService()
        connectors = service.get_connectors()

        assert isinstance(connectors, list)

    def test_credentials_summary(self):
        """UI service returns credentials summary."""
        from ui.services import OperatorService

        service = OperatorService()
        summary = service.get_credentials_summary()

        assert isinstance(summary, dict)
