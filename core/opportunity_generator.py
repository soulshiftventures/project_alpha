"""
Opportunity Generator

Generates opportunity candidates from pain points and market inputs.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from core.pain_point_scanner import PainPoint, get_pain_point_scanner
from core.market_discovery import OpportunityCandidate


@dataclass
class GenerationContext:
    """Context for opportunity generation"""
    market: Optional[str] = None
    industry: Optional[str] = None
    customer_type: Optional[str] = None
    theme: Optional[str] = None
    problem_area: Optional[str] = None
    additional_context: Optional[str] = None


class OpportunityGenerator:
    """
    Generates opportunity candidates from pain points

    Converts pain points into actionable business opportunities.
    """

    def __init__(self):
        self.pain_point_scanner = get_pain_point_scanner()

    def generate_from_pain_points(
        self,
        context: GenerationContext,
        max_candidates: int = 5
    ) -> List[OpportunityCandidate]:
        """
        Generate opportunity candidates from pain points

        Args:
            context: Generation context with market/industry/customer filters
            max_candidates: Maximum number of candidates to generate

        Returns:
            List of opportunity candidates
        """
        # Scan for relevant pain points
        pain_points = self.pain_point_scanner.scan_pain_points(
            industry=context.industry or context.market,
            problem_area=context.problem_area,
            customer_type=context.customer_type,
        )

        # Generate candidates from top pain points
        candidates = []
        for i, pain_point in enumerate(pain_points[:max_candidates]):
            candidate = self._pain_point_to_candidate(
                pain_point=pain_point,
                context=context,
                index=i,
            )
            candidates.append(candidate)

        return candidates

    def generate_from_theme(
        self,
        theme: str,
        context: GenerationContext,
        max_candidates: int = 3
    ) -> List[OpportunityCandidate]:
        """
        Generate opportunity candidates from a theme/trend

        Args:
            theme: Theme or trend to explore
            context: Additional generation context
            max_candidates: Maximum number of candidates

        Returns:
            List of opportunity candidates
        """
        candidates = []

        # Generate theme-based opportunities
        templates = [
            {
                "suffix": "Automation Platform",
                "pain_point": f"Manual {theme} processes lack specialized tooling",
                "execution_domains": ["automation", "saas", "api"],
                "automation_potential": "high",
                "complexity": "medium",
                "recommended_action": "Build automation for top 3 manual tasks",
            },
            {
                "suffix": "Analytics & Intelligence",
                "pain_point": f"Limited visibility into {theme} performance and ROI",
                "execution_domains": ["analytics", "data", "business-intelligence"],
                "automation_potential": "medium",
                "complexity": "medium",
                "recommended_action": "Create dashboard for key metrics",
            },
            {
                "suffix": "Integration Hub",
                "pain_point": f"Fragmented {theme} tools require manual bridging",
                "execution_domains": ["integration", "api", "workflow"],
                "automation_potential": "high",
                "complexity": "low",
                "recommended_action": "Build connectors for top 5 platforms",
            },
        ]

        for i, template in enumerate(templates[:max_candidates]):
            candidate = OpportunityCandidate(
                candidate_id=f"theme_{uuid.uuid4().hex[:8]}",
                title=f"{theme.title()} {template['suffix']}",
                pain_point=template["pain_point"],
                target_customer=context.customer_type or "Growing businesses adopting new technology",
                urgency="medium",
                monetization_clarity="emerging",
                execution_domains=template["execution_domains"],
                automation_potential=template["automation_potential"],
                complexity=template["complexity"],
                recommended_action=template["recommended_action"],
                confidence=0.6 + (i * 0.05),  # Slight variation
                discovered_via="theme_generation",
                discovered_at=datetime.utcnow().isoformat(),
                raw_inputs=asdict(context),
            )
            candidates.append(candidate)

        return candidates

    def _pain_point_to_candidate(
        self,
        pain_point: PainPoint,
        context: GenerationContext,
        index: int,
    ) -> OpportunityCandidate:
        """Convert a pain point into an opportunity candidate"""
        # Determine title from pain point
        title = self._generate_title(pain_point, context)

        # Map severity to urgency
        urgency_mapping = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
        }
        urgency = urgency_mapping.get(pain_point.severity, "medium")

        # Map monetization potential to clarity
        clarity_mapping = {
            "high": "proven",
            "medium": "emerging",
            "low": "unclear",
        }
        monetization_clarity = clarity_mapping.get(pain_point.monetization_potential, "emerging")

        # Determine target customer
        target_customer = self._determine_target_customer(pain_point, context)

        # Determine complexity based on solution gaps
        complexity = self._assess_complexity(pain_point)

        # Score pain point for confidence
        confidence = self.pain_point_scanner.score_pain_point(pain_point)

        # Generate recommended action
        recommended_action = self._generate_recommended_action(pain_point, context)

        return OpportunityCandidate(
            candidate_id=f"pain_{uuid.uuid4().hex[:8]}",
            title=title,
            pain_point=pain_point.description,
            target_customer=target_customer,
            urgency=urgency,
            monetization_clarity=monetization_clarity,
            execution_domains=pain_point.impact_areas[:3],  # Top 3 areas
            automation_potential=self._assess_automation_potential(pain_point),
            complexity=complexity,
            recommended_action=recommended_action,
            confidence=confidence,
            discovered_via="pain_point_analysis",
            discovered_at=datetime.utcnow().isoformat(),
            raw_inputs=asdict(context),
        )

    def _generate_title(self, pain_point: PainPoint, context: GenerationContext) -> str:
        """Generate opportunity title from pain point"""
        # Extract key terms from pain point description
        description_lower = pain_point.description.lower()

        if "manual" in description_lower and "data" in description_lower:
            return "Automated Data Sync Platform"
        elif "visibility" in description_lower or "monitoring" in description_lower:
            return "Real-Time Operations Dashboard"
        elif "integration" in description_lower or "fragmented" in description_lower:
            return "Unified Workflow Integration Hub"
        elif "compliance" in description_lower or "audit" in description_lower:
            return "Automated Compliance Management"
        elif "onboarding" in description_lower or "customer" in description_lower:
            return "Self-Service Onboarding Platform"
        elif "roi" in description_lower or "attribution" in description_lower:
            return "Multi-Touch Attribution Analytics"
        elif "scaling" in description_lower or "bottleneck" in description_lower:
            return "Process Automation for Scale"
        elif "security" in description_lower or "access" in description_lower:
            return "Automated Access Management"
        elif "data quality" in description_lower:
            return "Data Quality Automation"
        elif "knowledge" in description_lower:
            return "Knowledge Management Platform"
        else:
            # Fallback: use first impact area
            area = pain_point.impact_areas[0] if pain_point.impact_areas else "business"
            return f"{area.replace('-', ' ').title()} Automation Solution"

    def _determine_target_customer(self, pain_point: PainPoint, context: GenerationContext) -> str:
        """Determine target customer from pain point and context"""
        if context.customer_type:
            return context.customer_type

        # Use affected personas
        if pain_point.affected_personas:
            persona = pain_point.affected_personas[0]
            return persona.replace("-", " ").title()

        return "Growing businesses"

    def _assess_complexity(self, pain_point: PainPoint) -> str:
        """Assess implementation complexity"""
        gap_count = len(pain_point.solution_gaps)
        impact_area_count = len(pain_point.impact_areas)

        # More gaps and impact areas = higher complexity
        if gap_count >= 3 or impact_area_count >= 4:
            return "high"
        elif gap_count >= 2 or impact_area_count >= 3:
            return "medium"
        else:
            return "low"

    def _assess_automation_potential(self, pain_point: PainPoint) -> str:
        """Assess automation potential"""
        description_lower = pain_point.description.lower()

        # High automation potential keywords
        high_keywords = ["manual", "data entry", "sync", "repetitive", "routine"]
        medium_keywords = ["visibility", "monitoring", "tracking", "reporting"]
        low_keywords = ["knowledge", "training", "decision", "strategic"]

        if any(keyword in description_lower for keyword in high_keywords):
            return "high"
        elif any(keyword in description_lower for keyword in medium_keywords):
            return "medium"
        elif any(keyword in description_lower for keyword in low_keywords):
            return "low"
        else:
            return "medium"  # Default

    def _generate_recommended_action(self, pain_point: PainPoint, context: GenerationContext) -> str:
        """Generate recommended next action"""
        if pain_point.monetization_potential == "high":
            return "Build MVP and validate with 5 target customers"
        elif pain_point.severity in ["high", "critical"]:
            return "Interview 10 affected users to validate pain point severity"
        elif pain_point.frequency in ["frequent", "constant"]:
            return "Map current workflow and identify automation opportunities"
        else:
            return "Research existing solutions and identify differentiation"


# Global instance
_opportunity_generator = None


def get_opportunity_generator() -> OpportunityGenerator:
    """Get global opportunity generator instance"""
    global _opportunity_generator
    if _opportunity_generator is None:
        _opportunity_generator = OpportunityGenerator()
    return _opportunity_generator
