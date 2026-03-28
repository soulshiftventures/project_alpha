"""
Pain Point Scanner

Identifies and scores pain points for market opportunities.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PainPoint:
    """Identified pain point"""
    description: str
    severity: str  # low, medium, high, critical
    frequency: str  # rare, occasional, frequent, constant
    impact_areas: List[str]
    affected_personas: List[str]
    current_solutions: List[str]
    solution_gaps: List[str]
    monetization_potential: str  # low, medium, high


class PainPointScanner:
    """
    Scans for pain points based on market/industry/problem inputs

    Uses deterministic scoring logic for testability.
    """

    def __init__(self):
        self.pain_point_database = self._initialize_database()

    def scan_pain_points(
        self,
        industry: Optional[str] = None,
        problem_area: Optional[str] = None,
        customer_type: Optional[str] = None,
    ) -> List[PainPoint]:
        """
        Scan for pain points matching the given criteria

        Args:
            industry: Industry/market filter
            problem_area: Problem domain filter
            customer_type: Customer segment filter

        Returns:
            List of matching pain points, ranked by severity
        """
        matching_points = []

        # Match pain points from database
        for pain_point in self.pain_point_database:
            if self._matches_criteria(pain_point, industry, problem_area, customer_type):
                matching_points.append(pain_point)

        # Rank by severity then frequency
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        frequency_order = {"constant": 4, "frequent": 3, "occasional": 2, "rare": 1}

        matching_points.sort(
            key=lambda p: (
                severity_order.get(p.severity, 0),
                frequency_order.get(p.frequency, 0)
            ),
            reverse=True
        )

        return matching_points

    def score_pain_point(self, pain_point: PainPoint) -> float:
        """
        Calculate overall pain point score (0.0-1.0)

        Score based on severity, frequency, and monetization potential
        """
        severity_scores = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
        frequency_scores = {"constant": 1.0, "frequent": 0.75, "occasional": 0.5, "rare": 0.25}
        monetization_scores = {"high": 1.0, "medium": 0.6, "low": 0.3}

        severity_score = severity_scores.get(pain_point.severity, 0.5)
        frequency_score = frequency_scores.get(pain_point.frequency, 0.5)
        monetization_score = monetization_scores.get(pain_point.monetization_potential, 0.5)

        # Weighted average: severity 40%, frequency 30%, monetization 30%
        overall_score = (
            severity_score * 0.4 +
            frequency_score * 0.3 +
            monetization_score * 0.3
        )

        return round(overall_score, 2)

    def _matches_criteria(
        self,
        pain_point: PainPoint,
        industry: Optional[str],
        problem_area: Optional[str],
        customer_type: Optional[str],
    ) -> bool:
        """Check if pain point matches search criteria"""
        # If no criteria, return all
        if not industry and not problem_area and not customer_type:
            return True

        # Check industry match
        if industry:
            industry_lower = industry.lower()
            if not any(industry_lower in area.lower() for area in pain_point.impact_areas):
                return False

        # Check problem area match
        if problem_area:
            problem_lower = problem_area.lower()
            if problem_lower not in pain_point.description.lower():
                return False

        # Check customer type match
        if customer_type:
            customer_lower = customer_type.lower()
            if not any(customer_lower in persona.lower() for persona in pain_point.affected_personas):
                return False

        return True

    def _initialize_database(self) -> List[PainPoint]:
        """Initialize pain point database with common patterns"""
        return [
            PainPoint(
                description="Manual data entry and sync across systems",
                severity="high",
                frequency="constant",
                impact_areas=["operations", "data-management", "productivity"],
                affected_personas=["operations-managers", "data-teams", "admins"],
                current_solutions=["spreadsheets", "manual-processes", "basic-scripts"],
                solution_gaps=["lack-of-automation", "error-prone", "time-consuming"],
                monetization_potential="high",
            ),
            PainPoint(
                description="Lack of real-time visibility into operations",
                severity="high",
                frequency="frequent",
                impact_areas=["operations", "monitoring", "decision-making"],
                affected_personas=["executives", "operations-managers", "analysts"],
                current_solutions=["periodic-reports", "dashboards", "manual-checking"],
                solution_gaps=["delayed-insights", "reactive-approach", "no-alerts"],
                monetization_potential="high",
            ),
            PainPoint(
                description="Fragmented tools and workflows without integration",
                severity="medium",
                frequency="frequent",
                impact_areas=["productivity", "operations", "collaboration"],
                affected_personas=["teams", "managers", "end-users"],
                current_solutions=["multiple-tools", "manual-bridging", "workarounds"],
                solution_gaps=["no-integration", "context-switching", "inefficiency"],
                monetization_potential="high",
            ),
            PainPoint(
                description="Compliance and audit preparation overhead",
                severity="high",
                frequency="occasional",
                impact_areas=["compliance", "risk", "finance", "legal"],
                affected_personas=["compliance-officers", "auditors", "legal-teams"],
                current_solutions=["manual-collection", "spreadsheets", "documentation"],
                solution_gaps=["time-intensive", "error-prone", "hard-to-validate"],
                monetization_potential="medium",
            ),
            PainPoint(
                description="Customer onboarding friction and manual setup",
                severity="medium",
                frequency="frequent",
                impact_areas=["customer-success", "sales", "onboarding"],
                affected_personas=["customer-success", "sales-teams", "new-customers"],
                current_solutions=["manual-setup", "email-guides", "support-calls"],
                solution_gaps=["slow-time-to-value", "high-touch", "inconsistent"],
                monetization_potential="high",
            ),
            PainPoint(
                description="Inability to measure ROI and attribution",
                severity="medium",
                frequency="frequent",
                impact_areas=["marketing", "sales", "analytics"],
                affected_personas=["marketing-teams", "executives", "growth-leaders"],
                current_solutions=["last-touch-attribution", "spreadsheets", "gut-feel"],
                solution_gaps=["incomplete-data", "attribution-gaps", "no-multi-touch"],
                monetization_potential="high",
            ),
            PainPoint(
                description="Scaling bottlenecks due to manual processes",
                severity="high",
                frequency="occasional",
                impact_areas=["operations", "growth", "productivity"],
                affected_personas=["executives", "operations-managers", "growing-teams"],
                current_solutions=["hire-more-people", "overtime", "delayed-features"],
                solution_gaps=["not-sustainable", "expensive", "quality-issues"],
                monetization_potential="high",
            ),
            PainPoint(
                description="Security and access control complexity",
                severity="high",
                frequency="constant",
                impact_areas=["security", "compliance", "it"],
                affected_personas=["security-teams", "it-admins", "compliance-officers"],
                current_solutions=["manual-provisioning", "basic-rbac", "spreadsheets"],
                solution_gaps=["over-provisioning", "stale-access", "audit-gaps"],
                monetization_potential="medium",
            ),
            PainPoint(
                description="Poor data quality and inconsistent records",
                severity="medium",
                frequency="frequent",
                impact_areas=["data-management", "analytics", "operations"],
                affected_personas=["data-teams", "analysts", "operations"],
                current_solutions=["manual-cleanup", "data-validation-rules", "spot-checks"],
                solution_gaps=["reactive", "incomplete", "ongoing-effort"],
                monetization_potential="medium",
            ),
            PainPoint(
                description="Knowledge silos and tribal knowledge",
                severity="medium",
                frequency="occasional",
                impact_areas=["knowledge-management", "operations", "training"],
                affected_personas=["teams", "managers", "new-hires"],
                current_solutions=["documentation", "wiki", "ask-colleagues"],
                solution_gaps=["outdated-docs", "hard-to-find", "context-missing"],
                monetization_potential="low",
            ),
        ]


# Global instance
_pain_point_scanner = None


def get_pain_point_scanner() -> PainPointScanner:
    """Get global pain point scanner instance"""
    global _pain_point_scanner
    if _pain_point_scanner is None:
        _pain_point_scanner = PainPointScanner()
    return _pain_point_scanner
