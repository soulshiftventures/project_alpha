"""
Tests for Discovery Persistence + External Signal Enrichment Sprint

Covers:
- Discovery scan persistence
- Candidate persistence
- History and filtering
- External enrichment fallback behavior
- Conversion tracking
- State store integration
"""

import pytest
from datetime import datetime
from core.market_discovery import (
    MarketDiscoveryEngine,
    DiscoveryInput,
    OpportunityCandidate,
)
from core.discovery_history import (
    get_discovery_history,
    DiscoveryHistory,
    CandidateStatus,
    SignalSource,
    EnrichedCandidate,
    DiscoveryScanRecord,
)
from core.state_store import StateStore, StateStoreConfig
from ui.services import (
    run_discovery_scan,
    get_discovery_scan_result,
    list_discovery_scans,
    filter_discovery_scans,
    convert_candidate_to_opportunity,
    archive_candidate,
    get_discovery_conversion_stats,
)


class TestDiscoveryHistory:
    """Test discovery history persistence and querying"""

    def test_history_initialization(self):
        """Test history manager initializes correctly"""
        history = DiscoveryHistory()
        assert history._scans == {}
        assert history._candidates == {}

    def test_persist_scan(self):
        """Test persisting a discovery scan"""
        engine = MarketDiscoveryEngine()
        discovery_input = DiscoveryInput(
            mode="theme_scan",
            theme="AI automation",
        )
        result = engine.run_discovery(discovery_input)

        history = DiscoveryHistory()
        record = history.persist_scan(result, enriched=False)

        assert record.scan_id == result.scan_id
        assert record.mode == "theme_scan"
        assert record.total_candidates == 3
        assert len(record.candidates) == 3
        assert record.scan_id in history._scans

    def test_persist_scan_with_enrichment(self):
        """Test persisting enriched scan"""
        engine = MarketDiscoveryEngine(enable_external_enrichment=True)
        discovery_input = DiscoveryInput(
            mode="pain_point_scan",
            problem_area="customer onboarding",
        )
        # Run with enrich=True but without credentials
        result = engine.run_discovery(discovery_input, enrich=True)

        history = DiscoveryHistory()
        record = history.persist_scan(result, enriched=True)

        # Check enrichment flags - enriched=True was passed
        # signal_source will be "internal" because enrichment was attempted but no credentials
        for candidate_dict in record.candidates:
            # Signal source should be "internal" when enrichment fails/unavailable
            assert candidate_dict["signal_source"] in ["internal", "hybrid"]
            assert candidate_dict["status"] == CandidateStatus.UNCONVERTED.value

    def test_get_scan(self):
        """Test retrieving a scan by ID"""
        engine = MarketDiscoveryEngine()
        discovery_input = DiscoveryInput(mode="theme_scan", theme="automation")
        result = engine.run_discovery(discovery_input)

        history = DiscoveryHistory()
        history.persist_scan(result)

        retrieved = history.get_scan(result.scan_id)
        assert retrieved is not None
        assert retrieved.scan_id == result.scan_id
        assert retrieved.mode == "theme_scan"

    def test_list_scans(self):
        """Test listing scans with pagination"""
        engine = MarketDiscoveryEngine()
        history = DiscoveryHistory()

        # Create multiple scans
        for i in range(5):
            discovery_input = DiscoveryInput(
                mode="theme_scan",
                theme=f"theme_{i}",
            )
            result = engine.run_discovery(discovery_input)
            history.persist_scan(result)

        # List with limit
        scans = history.list_scans(limit=3)
        assert len(scans) == 3

        # List all
        all_scans = history.list_scans(limit=50)
        assert len(all_scans) == 5

    def test_filter_scans_by_mode(self):
        """Test filtering scans by mode"""
        engine = MarketDiscoveryEngine()
        history = DiscoveryHistory()

        # Create scans with different modes
        modes = ["theme_scan", "pain_point_scan", "industry_scan"]
        for mode in modes:
            discovery_input = DiscoveryInput(mode=mode, theme="test")
            result = engine.run_discovery(discovery_input)
            history.persist_scan(result)

        # Filter by theme_scan
        theme_scans = history.filter_scans(mode="theme_scan")
        assert len(theme_scans) == 1
        assert theme_scans[0].mode == "theme_scan"

        # Filter by pain_point_scan
        pain_scans = history.filter_scans(mode="pain_point_scan")
        assert len(pain_scans) == 1
        assert pain_scans[0].mode == "pain_point_scan"

    def test_filter_scans_by_theme(self):
        """Test filtering scans by theme keyword"""
        engine = MarketDiscoveryEngine()
        history = DiscoveryHistory()

        # Create scans with different themes
        themes = ["AI automation", "cost reduction", "developer tools"]
        for theme in themes:
            discovery_input = DiscoveryInput(mode="theme_scan", theme=theme)
            result = engine.run_discovery(discovery_input)
            history.persist_scan(result)

        # Filter by AI keyword
        ai_scans = history.filter_scans(theme="AI")
        assert len(ai_scans) == 1
        assert "AI" in ai_scans[0].input_summary

    def test_filter_scans_by_conversions(self):
        """Test filtering scans by conversion status"""
        engine = MarketDiscoveryEngine()
        history = DiscoveryHistory()

        # Create scans
        discovery_input = DiscoveryInput(mode="theme_scan", theme="test")
        result = engine.run_discovery(discovery_input)
        record = history.persist_scan(result)

        # Mark one candidate as converted
        candidate_id = record.candidates[0]["candidate_id"]
        history.mark_converted(candidate_id, "opp_123")

        # Filter with conversions
        with_conversions = history.filter_scans(has_conversions=True)
        assert len(with_conversions) == 1

        # Filter without conversions (should be 0 since we converted one)
        without_conversions = history.filter_scans(has_conversions=False)
        assert len(without_conversions) == 0


class TestCandidateConversion:
    """Test candidate conversion tracking"""

    def test_mark_converted(self):
        """Test marking a candidate as converted"""
        engine = MarketDiscoveryEngine()
        discovery_input = DiscoveryInput(mode="theme_scan", theme="automation")
        result = engine.run_discovery(discovery_input)

        history = DiscoveryHistory()
        record = history.persist_scan(result)
        candidate_id = record.candidates[0]["candidate_id"]

        # Convert candidate
        success = history.mark_converted(candidate_id, "opportunity_123")
        assert success is True

        # Verify status
        candidate = history.get_candidate(candidate_id)
        assert candidate.status == CandidateStatus.CONVERTED.value
        assert candidate.converted_opportunity_id == "opportunity_123"
        assert candidate.converted_at is not None

        # Verify scan counts updated
        scan = history.get_scan(record.scan_id)
        assert scan.converted_count == 1

    def test_mark_archived(self):
        """Test marking a candidate as archived"""
        engine = MarketDiscoveryEngine()
        discovery_input = DiscoveryInput(mode="theme_scan", theme="test")
        result = engine.run_discovery(discovery_input)

        history = DiscoveryHistory()
        record = history.persist_scan(result)
        candidate_id = record.candidates[0]["candidate_id"]

        # Archive candidate
        success = history.mark_archived(candidate_id, "Not a good fit")
        assert success is True

        # Verify status
        candidate = history.get_candidate(candidate_id)
        assert candidate.status == CandidateStatus.ARCHIVED.value
        assert candidate.archived_reason == "Not a good fit"
        assert candidate.archived_at is not None

        # Verify scan counts
        scan = history.get_scan(record.scan_id)
        assert scan.archived_count == 1

    def test_mark_ignored(self):
        """Test marking a candidate as ignored"""
        engine = MarketDiscoveryEngine()
        discovery_input = DiscoveryInput(mode="theme_scan", theme="test")
        result = engine.run_discovery(discovery_input)

        history = DiscoveryHistory()
        record = history.persist_scan(result)
        candidate_id = record.candidates[0]["candidate_id"]

        # Ignore candidate
        success = history.mark_ignored(candidate_id)
        assert success is True

        # Verify status
        candidate = history.get_candidate(candidate_id)
        assert candidate.status == CandidateStatus.IGNORED.value

        # Verify scan counts
        scan = history.get_scan(record.scan_id)
        assert scan.ignored_count == 1

    def test_filter_candidates_by_status(self):
        """Test filtering candidates by conversion status"""
        engine = MarketDiscoveryEngine()
        discovery_input = DiscoveryInput(mode="theme_scan", theme="test")
        result = engine.run_discovery(discovery_input)

        history = DiscoveryHistory()
        record = history.persist_scan(result)

        # Convert, archive, and ignore different candidates
        history.mark_converted(record.candidates[0]["candidate_id"], "opp_1")
        history.mark_archived(record.candidates[1]["candidate_id"], "Not viable")
        # Leave third as unconverted

        # Filter by status
        converted = history.filter_candidates(status=CandidateStatus.CONVERTED.value)
        assert len(converted) == 1

        archived = history.filter_candidates(status=CandidateStatus.ARCHIVED.value)
        assert len(archived) == 1

        unconverted = history.filter_candidates(status=CandidateStatus.UNCONVERTED.value)
        assert len(unconverted) == 1

    def test_conversion_stats(self):
        """Test conversion statistics"""
        engine = MarketDiscoveryEngine()
        history = DiscoveryHistory()

        # Create multiple scans with different modes
        for mode in ["theme_scan", "pain_point_scan", "industry_scan"]:
            discovery_input = DiscoveryInput(mode=mode, theme="test")
            result = engine.run_discovery(discovery_input)
            record = history.persist_scan(result)

            # Convert first candidate from each scan
            history.mark_converted(record.candidates[0]["candidate_id"], f"opp_{mode}")

        stats = history.get_conversion_stats()

        assert stats["total_candidates"] == 9  # 3 scans * 3 candidates
        assert stats["converted"] == 3
        assert stats["unconverted"] == 6
        assert stats["conversion_rate"] == 3 / 9

        # Check by-mode stats
        assert "theme_scan" in stats["by_mode"]
        assert stats["by_mode"]["theme_scan"]["converted"] == 1
        assert stats["by_mode"]["theme_scan"]["total"] == 3


class TestExternalEnrichment:
    """Test external signal enrichment behavior"""

    def test_enrichment_disabled_by_default(self):
        """Test enrichment is disabled by default"""
        engine = MarketDiscoveryEngine()
        assert engine.enable_external_enrichment is False

    def test_enrichment_flag_in_result(self):
        """Test enrichment flag in discovery result"""
        engine = MarketDiscoveryEngine(enable_external_enrichment=False)
        discovery_input = DiscoveryInput(mode="theme_scan", theme="AI")
        result = engine.run_discovery(discovery_input)

        assert result.metadata.get("enriched") is False

        # Try with enrichment enabled
        engine_enriched = MarketDiscoveryEngine(enable_external_enrichment=True)
        result_enriched = engine_enriched.run_discovery(discovery_input, enrich=True)

        # Note: Enrichment may not actually happen without live connectors
        # but the flag should be set
        assert "enriched" in result_enriched.metadata

    def test_enrichment_fallback_without_connectors(self):
        """Test enrichment gracefully falls back without connectors"""
        engine = MarketDiscoveryEngine(enable_external_enrichment=True)
        discovery_input = DiscoveryInput(mode="theme_scan", theme="automation")

        # Should not raise even without connectors
        result = engine.run_discovery(discovery_input)
        assert result is not None
        assert len(result.candidates) == 3

    def test_internal_signal_source_without_enrichment(self):
        """Test candidates have internal signal source by default"""
        engine = MarketDiscoveryEngine()
        discovery_input = DiscoveryInput(mode="theme_scan", theme="test")
        result = engine.run_discovery(discovery_input)

        history = DiscoveryHistory()
        record = history.persist_scan(result, enriched=False)

        for candidate_dict in record.candidates:
            assert candidate_dict["signal_source"] == "internal"


class TestServiceLayerIntegration:
    """Test service layer discovery functions"""

    def test_run_discovery_scan_service(self):
        """Test run_discovery_scan service function"""
        result = run_discovery_scan(
            mode="theme_scan",
            theme="AI automation",
        )

        assert "scan_id" in result
        assert result["mode"] == "theme_scan"
        assert result["total_candidates"] == 3
        assert len(result["candidates"]) == 3

    def test_run_discovery_scan_with_enrichment(self):
        """Test run_discovery_scan with enrichment flag"""
        result = run_discovery_scan(
            mode="pain_point_scan",
            problem_area="customer retention",
            enrich=True,
        )

        assert "scan_id" in result
        # Enrichment metadata should be present
        assert "metadata" in result

    def test_list_discovery_scans_service(self):
        """Test list_discovery_scans service function"""
        # Create a few scans
        for i in range(3):
            run_discovery_scan(mode="theme_scan", theme=f"theme_{i}")

        scans = list_discovery_scans(limit=10)
        assert len(scans) >= 3

        # Check structure
        for scan in scans:
            assert "scan_id" in scan
            assert "mode" in scan
            assert "total_candidates" in scan
            assert "scan_timestamp" in scan

    def test_get_discovery_scan_result_service(self):
        """Test get_discovery_scan_result service function"""
        # Create a scan
        result = run_discovery_scan(mode="theme_scan", theme="test")
        scan_id = result["scan_id"]

        # Retrieve it
        retrieved = get_discovery_scan_result(scan_id)
        assert retrieved is not None
        assert retrieved["scan_id"] == scan_id
        assert retrieved["mode"] == "theme_scan"

    def test_convert_candidate_service(self):
        """Test convert_candidate_to_opportunity service function"""
        # Create scan
        result = run_discovery_scan(mode="theme_scan", theme="test")
        candidate_id = result["candidates"][0]["candidate_id"]

        # Convert
        success = convert_candidate_to_opportunity(candidate_id, "opp_test")
        assert success is True

    def test_archive_candidate_service(self):
        """Test archive_candidate service function"""
        # Create scan
        result = run_discovery_scan(mode="theme_scan", theme="test")
        candidate_id = result["candidates"][0]["candidate_id"]

        # Archive
        success = archive_candidate(candidate_id, "Not viable")
        assert success is True

    def test_conversion_stats_service(self):
        """Test get_discovery_conversion_stats service function"""
        # Create and convert some candidates
        result = run_discovery_scan(mode="theme_scan", theme="test")
        candidate_id = result["candidates"][0]["candidate_id"]
        convert_candidate_to_opportunity(candidate_id, "opp_test")

        stats = get_discovery_conversion_stats()
        assert "total_candidates" in stats
        assert "converted" in stats
        assert "conversion_rate" in stats
        assert stats["converted"] >= 1


class TestStateStoreIntegration:
    """Test state store integration for discovery scans"""

    def test_state_store_has_discovery_table(self, tmp_path):
        """Test state store includes discovery_scans table"""
        db_path = tmp_path / "test_state.db"
        config = StateStoreConfig(db_path=str(db_path))
        store = StateStore(config)
        store.initialize()

        # Check table exists
        cursor = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='discovery_scans'"
        )
        result = cursor.fetchone()
        assert result is not None

    def test_save_discovery_scan_to_store(self, tmp_path):
        """Test saving discovery scan to state store"""
        db_path = tmp_path / "test_state.db"
        config = StateStoreConfig(db_path=str(db_path))
        store = StateStore(config)
        store.initialize()

        scan_data = {
            "scan_id": "test_scan_1",
            "mode": "theme_scan",
            "input_summary": "Test scan",
            "candidates": [{"candidate_id": "c1", "title": "Test"}],
            "total_candidates": 1,
            "scan_timestamp": datetime.utcnow().isoformat(),
            "metadata": {},
        }

        success = store.save_discovery_scan(scan_data)
        assert success is True

        # Retrieve
        retrieved = store.get_discovery_scan("test_scan_1")
        assert retrieved is not None
        assert retrieved["scan_id"] == "test_scan_1"

    def test_list_discovery_scans_from_store(self, tmp_path):
        """Test listing discovery scans from state store"""
        db_path = tmp_path / "test_state.db"
        config = StateStoreConfig(db_path=str(db_path))
        store = StateStore(config)
        store.initialize()

        # Save multiple scans
        for i in range(3):
            scan_data = {
                "scan_id": f"scan_{i}",
                "mode": "theme_scan",
                "input_summary": f"Scan {i}",
                "candidates": [],
                "total_candidates": 0,
                "scan_timestamp": datetime.utcnow().isoformat(),
                "metadata": {},
            }
            store.save_discovery_scan(scan_data)

        scans = store.list_discovery_scans()
        assert len(scans) == 3

    def test_update_discovery_scan_counts(self, tmp_path):
        """Test updating discovery scan conversion counts"""
        db_path = tmp_path / "test_state.db"
        config = StateStoreConfig(db_path=str(db_path))
        store = StateStore(config)
        store.initialize()

        # Save scan
        scan_data = {
            "scan_id": "test_scan",
            "mode": "theme_scan",
            "input_summary": "Test",
            "candidates": [],
            "total_candidates": 3,
            "scan_timestamp": datetime.utcnow().isoformat(),
            "metadata": {},
        }
        store.save_discovery_scan(scan_data)

        # Update counts
        success = store.update_discovery_scan_counts(
            "test_scan",
            converted_count=2,
            archived_count=1,
        )
        assert success is True

        # Verify
        retrieved = store.get_discovery_scan("test_scan")
        assert retrieved["converted_count"] == 2
        assert retrieved["archived_count"] == 1
