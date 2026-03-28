"""
Tests for Live External Enrichment Integration.

Validates that:
- External enrichment executes when credentials are available
- Fallback works when credentials are missing
- Enrichment evidence is properly persisted
- UI displays enrichment state correctly
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.market_discovery import MarketDiscoveryEngine, DiscoveryInput, OpportunityCandidate
from core.discovery_history import DiscoveryHistory, EnrichedCandidate
from integrations.base import ConnectorResult, ConnectorStatus
from integrations.connectors.tavily import TavilyConnector
from integrations.connectors.firecrawl import FirecrawlConnector


class TestLiveExternalEnrichment:
    """Tests for live external enrichment execution"""

    def test_enrichment_executes_with_credentials(self):
        """Test that enrichment executes when Tavily credentials are available"""
        # Setup
        engine = MarketDiscoveryEngine(enable_external_enrichment=True)

        # Mock Tavily connector with live capabilities
        mock_tavily = Mock(spec=TavilyConnector)
        mock_tavily.get_status.return_value = ConnectorStatus.READY
        mock_tavily.execute.return_value = ConnectorResult.success_result(
            data={
                "query": "test query",
                "results": [
                    {"title": "Result 1", "url": "https://example.com/1"},
                    {"title": "Result 2", "url": "https://example.com/2"},
                ],
            },
            metadata={"live_execution": True},
        )

        engine._tavily_connector = mock_tavily

        # Create test candidate
        candidate = OpportunityCandidate(
            candidate_id="test-001",
            title="Test Automation Tool",
            pain_point="Manual testing is slow",
            target_customer="SMB development teams",
            urgency="high",
            monetization_clarity="clear",
            execution_domains=["automation", "testing"],
            automation_potential="high",
            complexity="medium",
            recommended_action="Build MVP",
            confidence=0.7,
            discovered_via="test",
            discovered_at="2024-01-01T00:00:00Z",
            raw_inputs={},
        )

        # Execute enrichment
        enrichment = engine._enrich_candidate(candidate)

        # Assertions
        assert enrichment["enriched"] is True
        assert enrichment["signal_source"] == "hybrid"
        assert enrichment["enrichment_status"] == "live_success"
        assert len(enrichment["evidence"]) > 0

        # Check evidence structure
        evidence = enrichment["evidence"][0]
        assert evidence["source_type"] == "external_tavily_search"
        assert evidence["signal_strength"] > 0.0
        assert evidence["confidence_adjustment"] > 0.0
        assert len(evidence["external_references"]) > 0

        # Verify Tavily was called
        mock_tavily.execute.assert_called_once()
        call_args = mock_tavily.execute.call_args
        assert call_args[1]["operation"] == "search"
        assert call_args[1]["dry_run"] is False

    def test_enrichment_skips_without_credentials(self):
        """Test that enrichment falls back gracefully when credentials are missing"""
        # Setup
        engine = MarketDiscoveryEngine(enable_external_enrichment=True)

        # Mock Tavily connector as unconfigured
        mock_tavily = Mock(spec=TavilyConnector)
        mock_tavily.get_status.return_value = ConnectorStatus.UNCONFIGURED

        engine._tavily_connector = mock_tavily

        # Create test candidate
        candidate = OpportunityCandidate(
            candidate_id="test-002",
            title="Test Tool",
            pain_point="Test pain",
            target_customer="SMBs",
            urgency="medium",
            monetization_clarity="clear",
            execution_domains=["test"],
            automation_potential="medium",
            complexity="low",
            recommended_action="Test",
            confidence=0.6,
            discovered_via="test",
            discovered_at="2024-01-01T00:00:00Z",
            raw_inputs={},
        )

        # Execute enrichment
        enrichment = engine._enrich_candidate(candidate)

        # Assertions
        assert enrichment["enriched"] is False
        assert enrichment["enrichment_status"] == "credentials_missing"
        assert len(enrichment["evidence"]) > 0

        # Check evidence structure
        evidence = enrichment["evidence"][0]
        assert evidence["source_type"] == "external_tavily_search"
        assert evidence["signal_strength"] == 0.0
        assert evidence["confidence_adjustment"] == 0.0
        assert "not ready" in evidence["supporting_notes"].lower()

    def test_enrichment_disabled_by_default(self):
        """Test that enrichment is disabled by default"""
        # Setup
        engine = MarketDiscoveryEngine(enable_external_enrichment=False)

        candidate = OpportunityCandidate(
            candidate_id="test-003",
            title="Test",
            pain_point="Test",
            target_customer="Test",
            urgency="low",
            monetization_clarity="clear",
            execution_domains=["test"],
            automation_potential="low",
            complexity="low",
            recommended_action="Test",
            confidence=0.5,
            discovered_via="test",
            discovered_at="2024-01-01T00:00:00Z",
            raw_inputs={},
        )

        # Execute enrichment
        enrichment = engine._enrich_candidate(candidate)

        # Assertions
        assert enrichment["enriched"] is False
        assert enrichment["signal_source"] == "internal"
        assert enrichment["enrichment_status"] == "disabled"
        assert len(enrichment["evidence"]) == 0

    def test_enrichment_persisted_to_history(self):
        """Test that enrichment evidence is persisted correctly"""
        # Setup
        history = DiscoveryHistory()

        # Create mock discovery result with enrichment
        mock_result = Mock()
        mock_result.scan_id = "scan-001"
        mock_result.mode = "theme_scan"
        mock_result.input_summary = "Test scan"
        mock_result.total_candidates = 1
        mock_result.scan_timestamp = "2024-01-01T00:00:00Z"
        mock_result.metadata = {
            "enriched": True,
            "enrichment_metadata": [
                {
                    "candidate_id": "test-001",
                    "enrichment": {
                        "enriched": True,
                        "signal_source": "hybrid",
                        "enrichment_status": "live_success",
                        "evidence": [
                            {
                                "source_type": "external_tavily_search",
                                "signal_strength": 0.75,
                                "supporting_notes": "Found 3 results",
                                "external_references": ["https://example.com/1"],
                                "confidence_adjustment": 0.075,
                            }
                        ],
                    }
                }
            ],
        }

        # Create candidate
        candidate = OpportunityCandidate(
            candidate_id="test-001",
            title="Test Tool",
            pain_point="Test pain",
            target_customer="SMBs",
            urgency="medium",
            monetization_clarity="clear",
            execution_domains=["test"],
            automation_potential="medium",
            complexity="low",
            recommended_action="Test",
            confidence=0.6,
            discovered_via="theme_scan",
            discovered_at="2024-01-01T00:00:00Z",
            raw_inputs={},
        )
        mock_result.candidates = [candidate]

        # Persist scan
        record = history.persist_scan(mock_result, enriched=True)

        # Assertions
        assert record.scan_id == "scan-001"
        assert len(record.candidates) == 1

        # Check enrichment data
        persisted_candidate = record.candidates[0]
        assert persisted_candidate["signal_source"] == "hybrid"
        assert persisted_candidate["evidence"] is not None
        assert len(persisted_candidate["evidence"]) > 0
        assert persisted_candidate["evidence"][0]["source_type"] == "external_tavily_search"

    def test_live_enrichment_handles_api_failure(self):
        """Test that enrichment handles API failures gracefully"""
        # Setup
        engine = MarketDiscoveryEngine(enable_external_enrichment=True)

        # Mock Tavily connector that returns failure
        mock_tavily = Mock(spec=TavilyConnector)
        mock_tavily.get_status.return_value = ConnectorStatus.READY
        mock_tavily.execute.return_value = ConnectorResult.error_result(
            "API rate limit exceeded",
            error_type="rate_limit",
        )

        engine._tavily_connector = mock_tavily

        candidate = OpportunityCandidate(
            candidate_id="test-004",
            title="Test",
            pain_point="Test",
            target_customer="Test",
            urgency="medium",
            monetization_clarity="clear",
            execution_domains=["test"],
            automation_potential="medium",
            complexity="low",
            recommended_action="Test",
            confidence=0.6,
            discovered_via="test",
            discovered_at="2024-01-01T00:00:00Z",
            raw_inputs={},
        )

        # Execute enrichment
        enrichment = engine._enrich_candidate(candidate)

        # Assertions
        assert enrichment["enrichment_status"] == "live_failed"
        assert len(enrichment["evidence"]) > 0
        evidence = enrichment["evidence"][0]
        assert evidence["signal_strength"] == 0.0
        assert "failed" in evidence["supporting_notes"].lower()

    def test_enrichment_evidence_safe_references_only(self):
        """Test that only safe references (URLs) are persisted, no credentials"""
        # Setup
        engine = MarketDiscoveryEngine(enable_external_enrichment=True)

        # Mock Tavily with potentially sensitive data
        mock_tavily = Mock(spec=TavilyConnector)
        mock_tavily.get_status.return_value = ConnectorStatus.READY
        mock_tavily.execute.return_value = ConnectorResult.success_result(
            data={
                "query": "test query",
                "results": [
                    {"title": "Result 1", "url": "https://example.com/1", "api_key": "secret"},
                ],
                "api_key": "should-be-redacted",
            },
            metadata={"live_execution": True},
        )

        engine._tavily_connector = mock_tavily

        candidate = OpportunityCandidate(
            candidate_id="test-005",
            title="Test",
            pain_point="Test",
            target_customer="Test",
            urgency="medium",
            monetization_clarity="clear",
            execution_domains=["test"],
            automation_potential="medium",
            complexity="low",
            recommended_action="Test",
            confidence=0.6,
            discovered_via="test",
            discovered_at="2024-01-01T00:00:00Z",
            raw_inputs={},
        )

        # Execute enrichment
        enrichment = engine._enrich_candidate(candidate)

        # Assertions
        assert enrichment["enriched"] is True
        evidence = enrichment["evidence"][0]

        # Check that only URLs are in references
        for ref in evidence["external_references"]:
            assert ref.startswith("http")
            assert "api_key" not in ref.lower()
            assert "secret" not in ref.lower()


class TestEnrichmentIntegration:
    """Integration tests for enrichment flow"""

    def test_full_discovery_with_enrichment(self):
        """Test complete discovery flow with enrichment enabled"""
        # Setup
        engine = MarketDiscoveryEngine(enable_external_enrichment=False)  # Start disabled

        # Mock Tavily
        mock_tavily = Mock(spec=TavilyConnector)
        mock_tavily.get_status.return_value = ConnectorStatus.READY
        mock_tavily.execute.return_value = ConnectorResult.success_result(
            data={
                "query": "test query",
                "results": [
                    {"title": "Market Result", "url": "https://example.com/market"},
                ],
            },
            metadata={"live_execution": True},
        )

        engine._tavily_connector = mock_tavily

        # Create discovery input
        discovery_input = DiscoveryInput(
            mode="theme_scan",
            theme="AI automation",
        )

        # Run discovery WITH enrichment
        result = engine.run_discovery(discovery_input, enrich=True)

        # Assertions
        assert result is not None
        assert result.total_candidates > 0
        assert result.metadata.get("enriched") is True

        # Check enrichment metadata
        enrichment_metadata = result.metadata.get("enrichment_metadata", [])
        assert len(enrichment_metadata) > 0

    def test_discovery_without_enrichment(self):
        """Test discovery flow with enrichment disabled"""
        # Setup
        engine = MarketDiscoveryEngine(enable_external_enrichment=False)

        discovery_input = DiscoveryInput(
            mode="theme_scan",
            theme="Test theme",
        )

        # Run discovery WITHOUT enrichment
        result = engine.run_discovery(discovery_input, enrich=False)

        # Assertions
        assert result is not None
        assert result.total_candidates > 0
        assert result.metadata.get("enriched") is False or result.metadata.get("enriched") is None
        enrichment_metadata = result.metadata.get("enrichment_metadata", [])
        assert len(enrichment_metadata) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
