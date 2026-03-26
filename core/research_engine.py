"""
Research Engine for project_alpha
Discovers opportunities using AI analysis
"""

import json
from typing import List, Dict
from core.ai_client import AIClient


class ResearchEngine:
    """Engine for discovering and analyzing opportunities."""

    def __init__(self):
        self.ai_client = AIClient()

    def find_opportunities(self, focus_area: str = "business automation") -> List[Dict]:
        """
        Find business opportunities using AI research.

        Args:
            focus_area: Area to focus research on

        Returns:
            List of opportunity dictionaries with idea, description, and potential
        """
        prompt = f"""Analyze the {focus_area} market and identify 3-5 high-value opportunities.

For each opportunity, provide:
1. A clear, specific idea
2. Detailed description of the opportunity
3. Potential rating (low, medium, high)

Focus on opportunities that:
- Can be automated or enhanced with AI
- Have clear market demand
- Can be built with modern technology
- Have monetization potential

Return your analysis as a JSON array with this structure:
[
  {{
    "idea": "specific opportunity name",
    "description": "detailed description of the opportunity and why it matters",
    "potential": "high|medium|low"
  }}
]

Return ONLY valid JSON, no additional text."""

        response = self.ai_client.ask_ai(
            prompt=prompt,
            system_prompt="You are a business analyst and market researcher. Provide actionable insights.",
            temperature=0.8
        )

        try:
            opportunities = json.loads(response)
            if isinstance(opportunities, list):
                return self._validate_opportunities(opportunities)
            else:
                return self._generate_fallback_opportunities(focus_area)
        except json.JSONDecodeError:
            return self._generate_fallback_opportunities(focus_area)

    def _validate_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """Validate and normalize opportunity data."""
        validated = []

        for opp in opportunities:
            if isinstance(opp, dict) and "idea" in opp and "description" in opp:
                validated.append({
                    "idea": str(opp["idea"])[:200],
                    "description": str(opp["description"])[:500],
                    "potential": opp.get("potential", "medium").lower()
                })

        return validated if validated else self._generate_fallback_opportunities("general")

    def _generate_fallback_opportunities(self, focus_area: str) -> List[Dict]:
        """Generate fallback opportunities if AI fails."""
        return [
            {
                "idea": f"AI-powered {focus_area} automation platform",
                "description": f"Comprehensive platform for automating {focus_area} tasks using AI",
                "potential": "high"
            },
            {
                "idea": f"Smart {focus_area} analytics system",
                "description": f"Real-time analytics and insights for {focus_area} operations",
                "potential": "high"
            },
            {
                "idea": f"{focus_area.title()} workflow optimizer",
                "description": f"Analyze and optimize {focus_area} workflows automatically",
                "potential": "medium"
            }
        ]

    def select_best_opportunity(self, opportunities: List[Dict]) -> Dict:
        """
        Select the best opportunity from a list.

        Args:
            opportunities: List of opportunities

        Returns:
            Best opportunity dictionary
        """
        if not opportunities:
            return self._generate_fallback_opportunities("general")[0]

        high_potential = [o for o in opportunities if o.get("potential") == "high"]

        if high_potential:
            return high_potential[0]

        return opportunities[0]

    def analyze_opportunity(self, opportunity: Dict) -> Dict:
        """
        Deep analysis of a specific opportunity.

        Args:
            opportunity: Opportunity to analyze

        Returns:
            Analysis results
        """
        prompt = f"""Analyze this business opportunity in detail:

Idea: {opportunity['idea']}
Description: {opportunity['description']}

Provide:
1. Market analysis
2. Technical feasibility
3. Resource requirements
4. Potential challenges
5. Success metrics

Return as JSON:
{{
  "market_analysis": "...",
  "technical_feasibility": "...",
  "resource_requirements": ["..."],
  "challenges": ["..."],
  "success_metrics": ["..."]
}}"""

        response = self.ai_client.ask_ai(
            prompt=prompt,
            system_prompt="You are a strategic business analyst.",
            temperature=0.7
        )

        try:
            analysis = json.loads(response)
            return analysis
        except json.JSONDecodeError:
            return {
                "market_analysis": "Promising market with growth potential",
                "technical_feasibility": "Technically feasible with modern tools",
                "resource_requirements": ["Development team", "Infrastructure", "AI capabilities"],
                "challenges": ["Market competition", "Technical complexity", "User adoption"],
                "success_metrics": ["User acquisition", "Revenue growth", "System performance"]
            }
