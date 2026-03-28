"""
Market Discovery Engine

Generates market-driven opportunity candidates based on discovery inputs.
Supports multiple discovery modes: theme scan, pain point scan, industry scan, problem exploration.
Supports optional external signal enrichment via Tavily and Firecrawl connectors.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryInput:
    """Input for market discovery scan"""
    mode: str  # theme_scan, pain_point_scan, industry_scan, problem_exploration
    market: Optional[str] = None
    industry: Optional[str] = None
    problem_area: Optional[str] = None
    customer_type: Optional[str] = None
    theme: Optional[str] = None
    trend: Optional[str] = None
    additional_context: Optional[str] = None


@dataclass
class OpportunityCandidate:
    """Market-driven opportunity candidate"""
    candidate_id: str
    title: str
    pain_point: str
    target_customer: str
    urgency: str  # low, medium, high, critical
    monetization_clarity: str  # unclear, emerging, proven
    execution_domains: List[str]
    automation_potential: str  # low, medium, high
    complexity: str  # low, medium, high
    recommended_action: str
    confidence: float  # 0.0-1.0
    discovered_via: str  # mode used
    discovered_at: str
    raw_inputs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryResult:
    """Discovery scan result with ranked candidates"""
    scan_id: str
    mode: str
    input_summary: str
    candidates: List[OpportunityCandidate]
    total_candidates: int
    scan_timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class MarketDiscoveryEngine:
    """
    Real Market Discovery Engine

    Generates market-driven opportunity candidates instead of just accepting inputs.
    Uses deterministic, testable logic for candidate generation.
    Supports optional external enrichment via Tavily/Firecrawl research connectors.
    """

    def __init__(self, enable_external_enrichment: bool = False):
        """
        Initialize the discovery engine

        Args:
            enable_external_enrichment: Enable external signal enrichment (default: False)
        """
        self.scan_history: List[DiscoveryResult] = []
        self.enable_external_enrichment = enable_external_enrichment
        self._tavily_connector = None
        self._firecrawl_connector = None

    def _init_connectors(self):
        """Initialize external research connectors if enrichment is enabled"""
        if not self.enable_external_enrichment:
            return

        # Import connectors only if enrichment is enabled
        try:
            from integrations.registry import get_connector_registry
            registry = get_connector_registry()

            # Try to get Tavily connector
            try:
                self._tavily_connector = registry.get_connector("tavily")
                logger.info("Tavily connector initialized for enrichment")
            except Exception as e:
                logger.warning(f"Could not initialize Tavily connector: {e}")

            # Try to get Firecrawl connector
            try:
                self._firecrawl_connector = registry.get_connector("firecrawl")
                logger.info("Firecrawl connector initialized for enrichment")
            except Exception as e:
                logger.warning(f"Could not initialize Firecrawl connector: {e}")

        except Exception as e:
            logger.warning(f"Could not initialize connector registry: {e}")

    def _enrich_candidate(self, candidate: OpportunityCandidate) -> Dict[str, Any]:
        """
        Enrich a candidate with external research signals via Tavily/Firecrawl

        Args:
            candidate: OpportunityCandidate to enrich

        Returns:
            Dictionary with enrichment metadata (evidence, external_signals, etc.)
        """
        if not self.enable_external_enrichment:
            return {
                "enriched": False,
                "signal_source": "internal",
                "evidence": [],
                "enrichment_status": "disabled",
            }

        # Initialize connectors if not already done
        if self._tavily_connector is None and self._firecrawl_connector is None:
            self._init_connectors()

        # If no connectors are available, return gracefully
        if self._tavily_connector is None and self._firecrawl_connector is None:
            return {
                "enriched": False,
                "signal_source": "internal",
                "evidence": [],
                "enrichment_status": "unavailable",
            }

        enrichment = {
            "enriched": False,
            "signal_source": "internal",
            "evidence": [],
            "external_references": [],
            "enrichment_status": "attempted",
        }

        # Try Tavily search for market validation
        if self._tavily_connector:
            try:
                # Build market validation query
                query = f"{candidate.title} {candidate.target_customer} market demand"

                # Check if Tavily connector is ready for live execution
                tavily_status = self._tavily_connector.get_status()
                from integrations.base import ConnectorStatus

                if tavily_status == ConnectorStatus.READY:
                    # Execute live Tavily search
                    logger.info(f"Executing live Tavily enrichment for candidate: {candidate.candidate_id}")
                    result = self._tavily_connector.execute(
                        operation="search",
                        params={
                            "query": query,
                            "max_results": 3,
                            "search_depth": "basic",
                        },
                        dry_run=False,
                    )

                    if result.success:
                        # Extract signals from search results
                        search_results = result.data.get("results", [])
                        signal_strength = min(0.8, len(search_results) * 0.25)  # Cap at 0.8
                        confidence_boost = signal_strength * 0.1  # Modest confidence boost

                        # Create safe references (URLs only, no credentials)
                        safe_references = [r.get("url") for r in search_results[:3] if r.get("url")]

                        enrichment["enriched"] = True
                        enrichment["signal_source"] = "hybrid"
                        enrichment["enrichment_status"] = "live_success"
                        enrichment["evidence"].append({
                            "source_type": "external_tavily_search",
                            "signal_strength": signal_strength,
                            "supporting_notes": f"Market validation: found {len(search_results)} relevant results for '{query}'",
                            "external_references": safe_references,
                            "confidence_adjustment": confidence_boost,
                        })
                        logger.info(f"Tavily enrichment succeeded for candidate: {candidate.candidate_id}")
                    else:
                        # Live call failed - record but don't block
                        enrichment["enrichment_status"] = "live_failed"
                        enrichment["evidence"].append({
                            "source_type": "external_tavily_search",
                            "signal_strength": 0.0,
                            "supporting_notes": f"Tavily search failed: {result.error}",
                            "external_references": [],
                            "confidence_adjustment": 0.0,
                        })
                        logger.warning(f"Tavily enrichment failed: {result.error}")
                else:
                    # Connector not ready - dry-run fallback
                    enrichment["enrichment_status"] = "credentials_missing"
                    enrichment["evidence"].append({
                        "source_type": "external_tavily_search",
                        "signal_strength": 0.0,
                        "supporting_notes": f"Tavily connector not ready (status: {tavily_status.value}). Query prepared: {query}",
                        "external_references": [],
                        "confidence_adjustment": 0.0,
                    })
                    logger.info(f"Tavily enrichment skipped (credentials missing) for candidate: {candidate.candidate_id}")

            except Exception as e:
                logger.warning(f"Tavily enrichment failed: {e}")
                enrichment["enrichment_status"] = "error"
                enrichment["evidence"].append({
                    "source_type": "external_tavily_search",
                    "signal_strength": 0.0,
                    "supporting_notes": f"Tavily enrichment error: {str(e)}",
                    "external_references": [],
                    "confidence_adjustment": 0.0,
                })

        # Try Firecrawl for problem domain validation (if Tavily didn't work)
        if self._firecrawl_connector and not enrichment["enriched"]:
            try:
                # Check if Firecrawl connector is ready
                firecrawl_status = self._firecrawl_connector.get_status()
                from integrations.base import ConnectorStatus

                if firecrawl_status == ConnectorStatus.READY:
                    # For Firecrawl, we'd need a specific URL to scrape
                    # Since we don't have one, we'll skip live execution for now
                    # but record that it was attempted
                    enrichment["enrichment_status"] = "skipped"
                    enrichment["evidence"].append({
                        "source_type": "external_firecrawl_scrape",
                        "signal_strength": 0.0,
                        "supporting_notes": f"Firecrawl enrichment skipped: no target URL for problem domain '{candidate.pain_point}'",
                        "external_references": [],
                        "confidence_adjustment": 0.0,
                    })
                    logger.info(f"Firecrawl enrichment skipped (no URL) for candidate: {candidate.candidate_id}")
                else:
                    enrichment["enrichment_status"] = "credentials_missing"
                    enrichment["evidence"].append({
                        "source_type": "external_firecrawl_scrape",
                        "signal_strength": 0.0,
                        "supporting_notes": f"Firecrawl connector not ready (status: {firecrawl_status.value})",
                        "external_references": [],
                        "confidence_adjustment": 0.0,
                    })
                    logger.info(f"Firecrawl enrichment skipped (credentials missing) for candidate: {candidate.candidate_id}")

            except Exception as e:
                logger.warning(f"Firecrawl enrichment failed: {e}")
                if enrichment["enrichment_status"] == "attempted":
                    enrichment["enrichment_status"] = "error"
                enrichment["evidence"].append({
                    "source_type": "external_firecrawl_scrape",
                    "signal_strength": 0.0,
                    "supporting_notes": f"Firecrawl enrichment error: {str(e)}",
                    "external_references": [],
                    "confidence_adjustment": 0.0,
                })

        return enrichment

    def run_discovery(self, discovery_input: DiscoveryInput, enrich: bool = False) -> DiscoveryResult:
        """
        Run market discovery scan and generate ranked candidates

        Args:
            discovery_input: Discovery parameters
            enrich: Enable external enrichment for this scan (default: False)

        Returns:
            DiscoveryResult with ranked opportunity candidates
        """
        scan_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        # Temporarily enable enrichment if requested
        original_enrichment = self.enable_external_enrichment
        if enrich:
            self.enable_external_enrichment = True

        try:
            # Generate candidates based on mode
            if discovery_input.mode == "theme_scan":
                candidates = self._theme_scan(discovery_input)
            elif discovery_input.mode == "pain_point_scan":
                candidates = self._pain_point_scan(discovery_input)
            elif discovery_input.mode == "industry_scan":
                candidates = self._industry_scan(discovery_input)
            elif discovery_input.mode == "problem_exploration":
                candidates = self._problem_exploration(discovery_input)
            else:
                raise ValueError(f"Unknown discovery mode: {discovery_input.mode}")

            # Optionally enrich candidates with external signals
            enrichment_metadata = []
            if self.enable_external_enrichment:
                for candidate in candidates:
                    enrichment = self._enrich_candidate(candidate)
                    enrichment_metadata.append({
                        "candidate_id": candidate.candidate_id,
                        "enrichment": enrichment,
                    })

            # Create result
            result = DiscoveryResult(
                scan_id=scan_id,
                mode=discovery_input.mode,
                input_summary=self._create_input_summary(discovery_input),
                candidates=candidates,
                total_candidates=len(candidates),
                scan_timestamp=timestamp,
                metadata={
                    "raw_input": discovery_input.__dict__,
                    "enriched": self.enable_external_enrichment,
                    "enrichment_metadata": enrichment_metadata if self.enable_external_enrichment else [],
                }
            )

            self.scan_history.append(result)
            return result

        finally:
            # Restore original enrichment setting
            self.enable_external_enrichment = original_enrichment

    def get_scan_result(self, scan_id: str) -> Optional[DiscoveryResult]:
        """Retrieve a previous scan result"""
        for result in self.scan_history:
            if result.scan_id == scan_id:
                return result
        return None

    def _theme_scan(self, inputs: DiscoveryInput) -> List[OpportunityCandidate]:
        """Generate candidates from theme/trend exploration"""
        candidates = []
        theme = inputs.theme or inputs.trend or "emerging technology"

        # Generate theme-based candidates
        base_candidates = [
            {
                "title": f"{theme.title()} Automation Platform",
                "pain_point": f"Manual processes in {theme} are time-consuming and error-prone",
                "target_customer": "SMBs and enterprises adopting new technology",
                "urgency": "high",
                "monetization_clarity": "emerging",
                "execution_domains": ["automation", "saas", "api"],
                "automation_potential": "high",
                "complexity": "medium",
                "recommended_action": "Research existing solutions and identify gaps",
                "confidence": 0.7,
            },
            {
                "title": f"{theme.title()} Analytics & Insights",
                "pain_point": f"Lack of actionable data in {theme} implementations",
                "target_customer": "Companies using new technology without clear ROI metrics",
                "urgency": "medium",
                "monetization_clarity": "proven",
                "execution_domains": ["analytics", "data", "visualization"],
                "automation_potential": "medium",
                "complexity": "medium",
                "recommended_action": "Validate demand with target customer interviews",
                "confidence": 0.65,
            },
            {
                "title": f"{theme.title()} Compliance & Safety",
                "pain_point": f"Regulatory uncertainty and risk management for {theme}",
                "target_customer": "Regulated industries exploring new capabilities",
                "urgency": "high",
                "monetization_clarity": "emerging",
                "execution_domains": ["compliance", "risk", "policy"],
                "automation_potential": "low",
                "complexity": "high",
                "recommended_action": "Map regulatory landscape and identify requirements",
                "confidence": 0.6,
            },
        ]

        for i, base in enumerate(base_candidates):
            candidate = OpportunityCandidate(
                candidate_id=f"theme_{i+1}",
                discovered_via="theme_scan",
                discovered_at=datetime.utcnow().isoformat(),
                raw_inputs=inputs.__dict__,
                **base
            )
            candidates.append(candidate)

        return candidates

    def _pain_point_scan(self, inputs: DiscoveryInput) -> List[OpportunityCandidate]:
        """Generate candidates from pain point analysis"""
        candidates = []
        problem = inputs.problem_area or "operational inefficiency"
        customer = inputs.customer_type or "growing businesses"

        base_candidates = [
            {
                "title": f"Automated {problem.title()} Solution",
                "pain_point": f"{customer.title()} struggle with {problem} due to lack of tooling",
                "target_customer": customer.title(),
                "urgency": "high",
                "monetization_clarity": "proven",
                "execution_domains": ["automation", "workflow", "integration"],
                "automation_potential": "high",
                "complexity": "low",
                "recommended_action": "Build MVP with core automation features",
                "confidence": 0.8,
            },
            {
                "title": f"{problem.title()} Monitoring & Alerts",
                "pain_point": f"Reactive approach to {problem} leads to lost revenue",
                "target_customer": f"{customer.title()} without dedicated ops teams",
                "urgency": "medium",
                "monetization_clarity": "proven",
                "execution_domains": ["monitoring", "alerting", "ops"],
                "automation_potential": "medium",
                "complexity": "low",
                "recommended_action": "Deploy monitoring prototype with existing customers",
                "confidence": 0.75,
            },
            {
                "title": f"{problem.title()} Best Practices Platform",
                "pain_point": f"Knowledge gaps prevent effective {problem} management",
                "target_customer": f"{customer.title()} scaling operations",
                "urgency": "low",
                "monetization_clarity": "emerging",
                "execution_domains": ["education", "content", "community"],
                "automation_potential": "low",
                "complexity": "medium",
                "recommended_action": "Create content library and validate engagement",
                "confidence": 0.55,
            },
        ]

        for i, base in enumerate(base_candidates):
            candidate = OpportunityCandidate(
                candidate_id=f"pain_{i+1}",
                discovered_via="pain_point_scan",
                discovered_at=datetime.utcnow().isoformat(),
                raw_inputs=inputs.__dict__,
                **base
            )
            candidates.append(candidate)

        return candidates

    def _industry_scan(self, inputs: DiscoveryInput) -> List[OpportunityCandidate]:
        """Generate candidates from industry/market analysis"""
        candidates = []
        industry = inputs.industry or inputs.market or "software"

        base_candidates = [
            {
                "title": f"{industry.title()} Workflow Automation",
                "pain_point": f"Industry-specific processes lack specialized automation",
                "target_customer": f"{industry.title()} companies with manual workflows",
                "urgency": "high",
                "monetization_clarity": "proven",
                "execution_domains": ["automation", "vertical-saas", "integration"],
                "automation_potential": "high",
                "complexity": "medium",
                "recommended_action": "Interview 10 companies to map common workflows",
                "confidence": 0.7,
            },
            {
                "title": f"{industry.title()} Data Intelligence",
                "pain_point": f"Fragmented data sources prevent actionable insights",
                "target_customer": f"{industry.title()} decision-makers seeking competitive advantage",
                "urgency": "medium",
                "monetization_clarity": "proven",
                "execution_domains": ["data", "analytics", "business-intelligence"],
                "automation_potential": "medium",
                "complexity": "high",
                "recommended_action": "Build data connector for top 3 industry platforms",
                "confidence": 0.65,
            },
            {
                "title": f"{industry.title()} Compliance Automation",
                "pain_point": f"Regulatory burden consumes resources without adding value",
                "target_customer": f"Regulated {industry.title()} firms",
                "urgency": "high",
                "monetization_clarity": "emerging",
                "execution_domains": ["compliance", "automation", "reporting"],
                "automation_potential": "medium",
                "complexity": "high",
                "recommended_action": "Map compliance requirements and identify automation opportunities",
                "confidence": 0.6,
            },
        ]

        for i, base in enumerate(base_candidates):
            candidate = OpportunityCandidate(
                candidate_id=f"industry_{i+1}",
                discovered_via="industry_scan",
                discovered_at=datetime.utcnow().isoformat(),
                raw_inputs=inputs.__dict__,
                **base
            )
            candidates.append(candidate)

        return candidates

    def _problem_exploration(self, inputs: DiscoveryInput) -> List[OpportunityCandidate]:
        """Generate candidates from problem domain exploration"""
        candidates = []
        problem = inputs.problem_area or "customer acquisition"

        base_candidates = [
            {
                "title": f"{problem.title()} Automation Platform",
                "pain_point": f"Manual {problem} processes don't scale effectively",
                "target_customer": "Growth-stage companies hitting scaling limits",
                "urgency": "high",
                "monetization_clarity": "proven",
                "execution_domains": ["automation", "growth", "saas"],
                "automation_potential": "high",
                "complexity": "medium",
                "recommended_action": "Build automation for top 3 time-consuming tasks",
                "confidence": 0.75,
            },
            {
                "title": f"{problem.title()} Analytics & Attribution",
                "pain_point": f"Can't measure ROI or optimize {problem} spend",
                "target_customer": "Marketing and growth teams with limited visibility",
                "urgency": "medium",
                "monetization_clarity": "proven",
                "execution_domains": ["analytics", "attribution", "optimization"],
                "automation_potential": "medium",
                "complexity": "high",
                "recommended_action": "Create attribution model for 2-3 channels",
                "confidence": 0.7,
            },
            {
                "title": f"{problem.title()} Enablement & Training",
                "pain_point": f"Team lacks skills/knowledge for effective {problem}",
                "target_customer": "Companies investing in capability building",
                "urgency": "low",
                "monetization_clarity": "emerging",
                "execution_domains": ["education", "training", "enablement"],
                "automation_potential": "low",
                "complexity": "low",
                "recommended_action": "Develop training curriculum and test with pilot group",
                "confidence": 0.5,
            },
        ]

        for i, base in enumerate(base_candidates):
            candidate = OpportunityCandidate(
                candidate_id=f"problem_{i+1}",
                discovered_via="problem_exploration",
                discovered_at=datetime.utcnow().isoformat(),
                raw_inputs=inputs.__dict__,
                **base
            )
            candidates.append(candidate)

        return candidates

    def _create_input_summary(self, inputs: DiscoveryInput) -> str:
        """Create human-readable summary of discovery inputs"""
        parts = []

        if inputs.mode:
            mode_labels = {
                "theme_scan": "Theme Scan",
                "pain_point_scan": "Pain Point Scan",
                "industry_scan": "Industry Scan",
                "problem_exploration": "Problem Exploration"
            }
            parts.append(f"Mode: {mode_labels.get(inputs.mode, inputs.mode)}")

        if inputs.theme or inputs.trend:
            parts.append(f"Theme: {inputs.theme or inputs.trend}")
        if inputs.market or inputs.industry:
            parts.append(f"Industry: {inputs.market or inputs.industry}")
        if inputs.problem_area:
            parts.append(f"Problem: {inputs.problem_area}")
        if inputs.customer_type:
            parts.append(f"Customer: {inputs.customer_type}")
        if inputs.additional_context:
            parts.append(f"Context: {inputs.additional_context}")

        return " | ".join(parts) if parts else "General Market Scan"


# Global instance
_discovery_engine = None


def get_discovery_engine() -> MarketDiscoveryEngine:
    """Get global discovery engine instance"""
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = MarketDiscoveryEngine()
    return _discovery_engine
