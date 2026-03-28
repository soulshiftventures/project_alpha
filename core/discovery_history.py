"""
Discovery History Management

Provides persistence and query support for discovery scans, candidates, and conversion tracking.
Supports filtering by scan mode, theme, date, converted status, and more.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class CandidateStatus(Enum):
    """Status of an opportunity candidate"""
    UNCONVERTED = "unconverted"
    CONVERTED = "converted"
    ARCHIVED = "archived"
    IGNORED = "ignored"


class SignalSource(Enum):
    """Source of discovery signal"""
    INTERNAL = "internal"  # Generated from internal heuristics
    EXTERNAL_TAVILY = "external_tavily"  # Enriched via Tavily research
    EXTERNAL_FIRECRAWL = "external_firecrawl"  # Enriched via Firecrawl scraping
    HYBRID = "hybrid"  # Combination of internal and external


@dataclass
class CandidateEvidence:
    """Evidence supporting an opportunity candidate"""
    source_type: str  # internal_heuristic, external_research, etc.
    signal_strength: float  # 0.0-1.0
    supporting_notes: str
    external_references: List[str]  # URLs or citations (redacted/safe)
    confidence_adjustment: float  # How much this evidence adjusts confidence


@dataclass
class EnrichedCandidate:
    """Opportunity candidate with enrichment metadata"""
    candidate_id: str
    title: str
    pain_point: str
    target_customer: str
    urgency: str
    monetization_clarity: str
    execution_domains: List[str]
    automation_potential: str
    complexity: str
    recommended_action: str
    confidence: float
    discovered_via: str
    discovered_at: str
    raw_inputs: Dict[str, Any]

    # Enrichment fields
    signal_source: str = "internal"  # internal, external_tavily, external_firecrawl, hybrid
    evidence: List[Dict[str, Any]] = None  # List of CandidateEvidence dicts
    enrichment_timestamp: Optional[str] = None

    # Conversion tracking
    status: str = "unconverted"  # unconverted, converted, archived, ignored
    converted_opportunity_id: Optional[str] = None
    converted_at: Optional[str] = None
    archived_at: Optional[str] = None
    archived_reason: Optional[str] = None

    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class DiscoveryScanRecord:
    """Persistent record of a discovery scan"""
    scan_id: str
    mode: str
    input_summary: str
    candidates: List[Dict[str, Any]]  # List of EnrichedCandidate dicts
    total_candidates: int
    scan_timestamp: str
    metadata: Dict[str, Any]

    # Conversion tracking
    converted_count: int = 0
    archived_count: int = 0
    ignored_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class DiscoveryHistory:
    """
    Manages discovery scan persistence and history queries.

    Supports:
    - Persist discovery scans and candidates
    - Retrieve past scans
    - Filter by mode, theme, industry, date, status
    - Track candidate conversion
    - Compare scan results
    """

    def __init__(self, state_store=None):
        """Initialize discovery history manager"""
        self._state_store = state_store
        self._scans: Dict[str, DiscoveryScanRecord] = {}
        self._candidates: Dict[str, EnrichedCandidate] = {}

    def persist_scan(self, scan_result: Any, enriched: bool = False) -> DiscoveryScanRecord:
        """
        Persist a discovery scan result

        Args:
            scan_result: DiscoveryResult from MarketDiscoveryEngine
            enriched: Whether candidates have been externally enriched

        Returns:
            DiscoveryScanRecord
        """
        # Get enrichment metadata from scan result
        enrichment_metadata = scan_result.metadata.get("enrichment_metadata", [])

        # Convert candidates to enriched format
        enriched_candidates = []
        for candidate in scan_result.candidates:
            # Find enrichment data for this candidate
            candidate_enrichment = None
            for meta in enrichment_metadata:
                if meta.get("candidate_id") == candidate.candidate_id:
                    candidate_enrichment = meta.get("enrichment", {})
                    break

            # Determine signal source from enrichment data
            signal_source = "internal"
            evidence_list = []
            if candidate_enrichment:
                signal_source = candidate_enrichment.get("signal_source", "internal")
                evidence_list = candidate_enrichment.get("evidence", [])

            enriched_candidate = EnrichedCandidate(
                candidate_id=candidate.candidate_id,
                title=candidate.title,
                pain_point=candidate.pain_point,
                target_customer=candidate.target_customer,
                urgency=candidate.urgency,
                monetization_clarity=candidate.monetization_clarity,
                execution_domains=candidate.execution_domains,
                automation_potential=candidate.automation_potential,
                complexity=candidate.complexity,
                recommended_action=candidate.recommended_action,
                confidence=candidate.confidence,
                discovered_via=candidate.discovered_via,
                discovered_at=candidate.discovered_at,
                raw_inputs=candidate.raw_inputs,
                signal_source=signal_source,
                evidence=evidence_list,
                enrichment_timestamp=_utc_now().isoformat() if enriched else None,
                status=CandidateStatus.UNCONVERTED.value,
            )
            enriched_candidates.append(enriched_candidate)
            self._candidates[enriched_candidate.candidate_id] = enriched_candidate

        # Create scan record
        record = DiscoveryScanRecord(
            scan_id=scan_result.scan_id,
            mode=scan_result.mode,
            input_summary=scan_result.input_summary,
            candidates=[c.to_dict() for c in enriched_candidates],
            total_candidates=scan_result.total_candidates,
            scan_timestamp=scan_result.scan_timestamp,
            metadata=scan_result.metadata,
        )

        self._scans[record.scan_id] = record

        # Persist to state store if available
        if self._state_store:
            try:
                # Add enriched flag to metadata for state store
                store_data = record.to_dict()
                store_data["enriched"] = 1 if enriched else 0
                self._state_store.save_discovery_scan(store_data)
                logger.info(f"Persisted scan {record.scan_id} (enriched={enriched}) to state store")
            except Exception as e:
                logger.warning(f"Failed to persist scan to state store: {e}")

        return record

    def get_scan(self, scan_id: str) -> Optional[DiscoveryScanRecord]:
        """Retrieve a scan by ID"""
        return self._scans.get(scan_id)

    def list_scans(
        self,
        mode: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DiscoveryScanRecord]:
        """
        List discovery scans with optional filtering

        Args:
            mode: Filter by discovery mode (theme_scan, pain_point_scan, etc.)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of DiscoveryScanRecords
        """
        scans = list(self._scans.values())

        # Filter by mode
        if mode:
            scans = [s for s in scans if s.mode == mode]

        # Sort by timestamp (newest first)
        scans.sort(key=lambda s: s.scan_timestamp, reverse=True)

        # Apply pagination
        return scans[offset:offset + limit]

    def filter_scans(
        self,
        mode: Optional[str] = None,
        theme: Optional[str] = None,
        industry: Optional[str] = None,
        problem: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        has_conversions: Optional[bool] = None,
        limit: int = 50,
    ) -> List[DiscoveryScanRecord]:
        """
        Advanced filtering for discovery scans

        Args:
            mode: Discovery mode filter
            theme: Theme/trend keyword search
            industry: Industry/market keyword search
            problem: Problem area keyword search
            date_from: ISO timestamp filter (inclusive)
            date_to: ISO timestamp filter (inclusive)
            has_conversions: Filter scans with/without conversions
            limit: Maximum results

        Returns:
            Filtered list of DiscoveryScanRecords
        """
        scans = list(self._scans.values())

        # Apply filters
        if mode:
            scans = [s for s in scans if s.mode == mode]

        if theme:
            theme_lower = theme.lower()
            scans = [s for s in scans if theme_lower in s.input_summary.lower()]

        if industry:
            industry_lower = industry.lower()
            scans = [s for s in scans if industry_lower in s.input_summary.lower()]

        if problem:
            problem_lower = problem.lower()
            scans = [s for s in scans if problem_lower in s.input_summary.lower()]

        if date_from:
            scans = [s for s in scans if s.scan_timestamp >= date_from]

        if date_to:
            scans = [s for s in scans if s.scan_timestamp <= date_to]

        if has_conversions is not None:
            if has_conversions:
                scans = [s for s in scans if s.converted_count > 0]
            else:
                scans = [s for s in scans if s.converted_count == 0]

        # Sort by timestamp (newest first)
        scans.sort(key=lambda s: s.scan_timestamp, reverse=True)

        return scans[:limit]

    def get_candidate(self, candidate_id: str) -> Optional[EnrichedCandidate]:
        """Get a specific candidate by ID"""
        return self._candidates.get(candidate_id)

    def filter_candidates(
        self,
        status: Optional[str] = None,
        signal_source: Optional[str] = None,
        discovered_via: Optional[str] = None,
        limit: int = 100,
    ) -> List[EnrichedCandidate]:
        """
        Filter candidates by status, source, or discovery mode

        Args:
            status: Filter by conversion status
            signal_source: Filter by signal source (internal, external, hybrid)
            discovered_via: Filter by discovery mode
            limit: Maximum results

        Returns:
            Filtered list of EnrichedCandidates
        """
        candidates = list(self._candidates.values())

        if status:
            candidates = [c for c in candidates if c.status == status]

        if signal_source:
            candidates = [c for c in candidates if c.signal_source == signal_source]

        if discovered_via:
            candidates = [c for c in candidates if c.discovered_via == discovered_via]

        # Sort by discovered_at (newest first)
        candidates.sort(key=lambda c: c.discovered_at, reverse=True)

        return candidates[:limit]

    def mark_converted(
        self,
        candidate_id: str,
        opportunity_id: str,
    ) -> bool:
        """
        Mark a candidate as converted to an opportunity

        Args:
            candidate_id: ID of the candidate
            opportunity_id: ID of the created opportunity

        Returns:
            True if successful
        """
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False

        candidate.status = CandidateStatus.CONVERTED.value
        candidate.converted_opportunity_id = opportunity_id
        candidate.converted_at = _utc_now().isoformat()

        # Update scan record conversion count
        for scan in self._scans.values():
            for c in scan.candidates:
                if c["candidate_id"] == candidate_id:
                    c["status"] = CandidateStatus.CONVERTED.value
                    c["converted_opportunity_id"] = opportunity_id
                    c["converted_at"] = candidate.converted_at
                    scan.converted_count += 1
                    break

        return True

    def mark_archived(
        self,
        candidate_id: str,
        reason: str,
    ) -> bool:
        """
        Mark a candidate as archived

        Args:
            candidate_id: ID of the candidate
            reason: Reason for archiving

        Returns:
            True if successful
        """
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False

        candidate.status = CandidateStatus.ARCHIVED.value
        candidate.archived_at = _utc_now().isoformat()
        candidate.archived_reason = reason

        # Update scan record
        for scan in self._scans.values():
            for c in scan.candidates:
                if c["candidate_id"] == candidate_id:
                    c["status"] = CandidateStatus.ARCHIVED.value
                    c["archived_at"] = candidate.archived_at
                    c["archived_reason"] = reason
                    scan.archived_count += 1
                    break

        return True

    def mark_ignored(self, candidate_id: str) -> bool:
        """Mark a candidate as ignored"""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False

        candidate.status = CandidateStatus.IGNORED.value

        # Update scan record
        for scan in self._scans.values():
            for c in scan.candidates:
                if c["candidate_id"] == candidate_id:
                    c["status"] = CandidateStatus.IGNORED.value
                    scan.ignored_count += 1
                    break

        return True

    def get_conversion_stats(self) -> Dict[str, Any]:
        """
        Get conversion statistics across all scans

        Returns:
            Dictionary with conversion metrics
        """
        total_candidates = len(self._candidates)
        converted = sum(1 for c in self._candidates.values() if c.status == CandidateStatus.CONVERTED.value)
        archived = sum(1 for c in self._candidates.values() if c.status == CandidateStatus.ARCHIVED.value)
        ignored = sum(1 for c in self._candidates.values() if c.status == CandidateStatus.IGNORED.value)
        unconverted = sum(1 for c in self._candidates.values() if c.status == CandidateStatus.UNCONVERTED.value)

        # Stats by discovery mode
        mode_stats = {}
        for candidate in self._candidates.values():
            mode = candidate.discovered_via
            if mode not in mode_stats:
                mode_stats[mode] = {"total": 0, "converted": 0, "conversion_rate": 0.0}
            mode_stats[mode]["total"] += 1
            if candidate.status == CandidateStatus.CONVERTED.value:
                mode_stats[mode]["converted"] += 1

        # Calculate conversion rates
        for mode in mode_stats:
            if mode_stats[mode]["total"] > 0:
                mode_stats[mode]["conversion_rate"] = mode_stats[mode]["converted"] / mode_stats[mode]["total"]

        # Stats by signal source
        source_stats = {}
        for candidate in self._candidates.values():
            source = candidate.signal_source
            if source not in source_stats:
                source_stats[source] = {"total": 0, "converted": 0, "conversion_rate": 0.0}
            source_stats[source]["total"] += 1
            if candidate.status == CandidateStatus.CONVERTED.value:
                source_stats[source]["converted"] += 1

        # Calculate conversion rates
        for source in source_stats:
            if source_stats[source]["total"] > 0:
                source_stats[source]["conversion_rate"] = source_stats[source]["converted"] / source_stats[source]["total"]

        return {
            "total_candidates": total_candidates,
            "converted": converted,
            "archived": archived,
            "ignored": ignored,
            "unconverted": unconverted,
            "conversion_rate": converted / total_candidates if total_candidates > 0 else 0.0,
            "by_mode": mode_stats,
            "by_source": source_stats,
        }


# Global instance
_discovery_history = None


def get_discovery_history(state_store=None) -> DiscoveryHistory:
    """Get global discovery history instance"""
    global _discovery_history
    if _discovery_history is None:
        _discovery_history = DiscoveryHistory(state_store=state_store)
    return _discovery_history
