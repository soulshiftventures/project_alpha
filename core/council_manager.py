"""
Council Manager for Project Alpha
Coordinates strategic advisor agents, gathers recommendations, supports debate/synthesis
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from core.agent_contracts import (
    AgentRequest, AgentResponse, RequestStatus,
    CouncilRecommendation, create_response
)
from core.agent_registry import AgentRegistry, AgentDefinition, AgentLayer


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class CouncilSession:
    """
    A council session for gathering and synthesizing advice.

    Tracks the full lifecycle of a council deliberation.
    """
    session_id: str = field(default_factory=lambda: f"council_{_utc_now().strftime('%Y%m%d%H%M%S%f')}")
    request_id: str = ""

    # Session state
    topic: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    # Participants
    advisors_invited: List[str] = field(default_factory=list)
    advisors_responded: List[str] = field(default_factory=list)

    # Recommendations collected
    recommendations: List[CouncilRecommendation] = field(default_factory=list)

    # Synthesis
    synthesis: Optional[Dict[str, Any]] = None
    agreements: List[str] = field(default_factory=list)
    disagreements: List[str] = field(default_factory=list)
    final_recommendation: str = ""
    confidence: float = 0.0

    # Timing
    started_at: str = field(default_factory=lambda: _utc_now().isoformat())
    completed_at: Optional[str] = None
    status: str = "active"  # active, completed, cancelled

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "request_id": self.request_id,
            "topic": self.topic,
            "context": self.context,
            "advisors_invited": self.advisors_invited,
            "advisors_responded": self.advisors_responded,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "synthesis": self.synthesis,
            "agreements": self.agreements,
            "disagreements": self.disagreements,
            "final_recommendation": self.final_recommendation,
            "confidence": self.confidence,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status
        }


class CouncilManager:
    """
    Manages the strategic council of advisors.

    Provides:
    - Convening advisor sessions
    - Gathering recommendations from multiple advisors
    - Synthesizing input with agreement/disagreement tracking
    - Producing council output for decision-making
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        """
        Initialize the council manager.

        Args:
            registry: Agent registry (creates new if not provided)
        """
        self._registry = registry
        self._sessions: Dict[str, CouncilSession] = {}
        self._session_history: List[CouncilSession] = []

    def set_registry(self, registry: AgentRegistry) -> None:
        """Set the agent registry."""
        self._registry = registry

    def get_advisors(self) -> List[AgentDefinition]:
        """
        Get all registered advisor agents.

        Returns:
            List of advisor agents from council layer
        """
        if not self._registry:
            return []

        # Get council layer agents that are advisors (not the manager itself)
        council_agents = self._registry.get_by_layer(AgentLayer.COUNCIL)
        return [a for a in council_agents if a.agent_id != "council_manager"]

    def convene(
        self,
        request: AgentRequest,
        topic: str,
        context: Optional[Dict[str, Any]] = None,
        advisors: Optional[List[str]] = None
    ) -> CouncilSession:
        """
        Convene a council session to gather recommendations.

        Args:
            request: The originating request
            topic: Topic for deliberation
            context: Additional context for advisors
            advisors: Specific advisor IDs (None = all advisors)

        Returns:
            CouncilSession tracking the deliberation
        """
        # Determine advisors
        if advisors is None:
            advisor_list = self.get_advisors()
            advisors = [a.agent_id for a in advisor_list]

        session = CouncilSession(
            request_id=request.request_id,
            topic=topic,
            context=context or {},
            advisors_invited=advisors
        )

        self._sessions[session.session_id] = session
        return session

    def submit_recommendation(
        self,
        session_id: str,
        advisor_id: str,
        recommendation: str,
        confidence: float,
        reasoning: str = "",
        supporting_evidence: Optional[List[str]] = None,
        concerns: Optional[List[str]] = None
    ) -> Optional[CouncilRecommendation]:
        """
        Submit a recommendation from an advisor.

        Args:
            session_id: ID of the council session
            advisor_id: ID of the advising agent
            recommendation: The recommendation text
            confidence: Confidence level 0.0-1.0
            reasoning: Explanation of the reasoning
            supporting_evidence: List of supporting points
            concerns: List of concerns or risks

        Returns:
            The submitted recommendation or None if session not found
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        # Get advisor name from registry
        advisor_name = advisor_id
        if self._registry:
            advisor_def = self._registry.get(advisor_id)
            if advisor_def:
                advisor_name = advisor_def.name

        rec = CouncilRecommendation(
            advisor_id=advisor_id,
            advisor_name=advisor_name,
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            supporting_evidence=supporting_evidence or [],
            concerns=concerns or []
        )

        session.recommendations.append(rec)
        if advisor_id not in session.advisors_responded:
            session.advisors_responded.append(advisor_id)

        return rec

    def gather_recommendations(
        self,
        session_id: str,
        business: Optional[Dict[str, Any]] = None
    ) -> List[CouncilRecommendation]:
        """
        Gather recommendations from all invited advisors.

        This is a deterministic simulation that generates
        advisor recommendations based on business context.

        Args:
            session_id: ID of the council session
            business: Optional business context

        Returns:
            List of gathered recommendations
        """
        if session_id not in self._sessions:
            return []

        session = self._sessions[session_id]
        business = business or session.context.get("business", {})

        # Generate recommendations from each advisor
        for advisor_id in session.advisors_invited:
            if advisor_id in session.advisors_responded:
                continue

            rec = self._generate_advisor_recommendation(
                advisor_id=advisor_id,
                topic=session.topic,
                business=business,
                context=session.context
            )

            if rec:
                session.recommendations.append(rec)
                session.advisors_responded.append(advisor_id)

        return session.recommendations

    def _generate_advisor_recommendation(
        self,
        advisor_id: str,
        topic: str,
        business: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[CouncilRecommendation]:
        """
        Generate a recommendation from an advisor.

        This is deterministic logic based on advisor role and context.
        """
        # Get advisor definition
        advisor_name = advisor_id
        capabilities = []
        if self._registry:
            advisor_def = self._registry.get(advisor_id)
            if advisor_def:
                advisor_name = advisor_def.name
                capabilities = advisor_def.capabilities

        # Extract business info
        stage = business.get("stage", "DISCOVERED")
        metrics = business.get("metrics", {})
        validation_score = metrics.get("validation_score", 0.0)
        performance = metrics.get("performance", 0.0)

        # Generate role-specific recommendations
        if advisor_id == "advisor_strategy":
            return self._strategy_recommendation(
                advisor_id, advisor_name, topic, stage, validation_score, performance
            )
        elif advisor_id == "advisor_risk":
            return self._risk_recommendation(
                advisor_id, advisor_name, topic, stage, metrics
            )
        elif advisor_id == "advisor_innovation":
            return self._innovation_recommendation(
                advisor_id, advisor_name, topic, stage
            )
        else:
            # Generic advisor recommendation
            return CouncilRecommendation(
                advisor_id=advisor_id,
                advisor_name=advisor_name,
                recommendation=f"Proceed with {topic} using standard approach",
                confidence=0.6,
                reasoning="Based on general assessment of the situation",
                supporting_evidence=["Standard procedures apply"],
                concerns=["Specific domain expertise may be needed"]
            )

    def _strategy_recommendation(
        self,
        advisor_id: str,
        name: str,
        topic: str,
        stage: str,
        validation_score: float,
        performance: float
    ) -> CouncilRecommendation:
        """Generate strategy advisor recommendation."""
        if stage in ["DISCOVERED", "VALIDATING"]:
            if validation_score < 0.5:
                return CouncilRecommendation(
                    advisor_id=advisor_id,
                    advisor_name=name,
                    recommendation="Focus on validation before scaling resources",
                    confidence=0.85,
                    reasoning="Low validation score suggests market fit not yet proven",
                    supporting_evidence=[
                        f"Current validation score: {validation_score:.2f}",
                        "Early-stage focus should be on learning, not scaling"
                    ],
                    concerns=[
                        "Premature scaling could waste resources",
                        "Need more customer validation data"
                    ]
                )
            else:
                return CouncilRecommendation(
                    advisor_id=advisor_id,
                    advisor_name=name,
                    recommendation="Proceed to building phase with validated approach",
                    confidence=0.8,
                    reasoning="Validation metrics support moving forward",
                    supporting_evidence=[
                        f"Validation score: {validation_score:.2f}",
                        "Market signals are positive"
                    ],
                    concerns=["Monitor competitor responses"]
                )
        elif stage in ["BUILDING", "SCALING"]:
            return CouncilRecommendation(
                advisor_id=advisor_id,
                advisor_name=name,
                recommendation="Maintain current trajectory with focus on execution",
                confidence=0.75,
                reasoning="Strategic direction is sound, execution is key",
                supporting_evidence=[
                    f"Current stage: {stage}",
                    f"Performance: {performance:.2f}"
                ],
                concerns=["Watch for market changes"]
            )
        else:
            return CouncilRecommendation(
                advisor_id=advisor_id,
                advisor_name=name,
                recommendation="Optimize for sustainability and efficiency",
                confidence=0.7,
                reasoning="Mature stage requires optimization focus",
                supporting_evidence=[f"Performance level: {performance:.2f}"],
                concerns=["Avoid complacency"]
            )

    def _risk_recommendation(
        self,
        advisor_id: str,
        name: str,
        topic: str,
        stage: str,
        metrics: Dict[str, Any]
    ) -> CouncilRecommendation:
        """Generate risk advisor recommendation."""
        failure_count = metrics.get("failure_count", 0)
        validation_score = metrics.get("validation_score", 0.0)

        concerns = []
        confidence = 0.8

        if failure_count >= 3:
            concerns.append(f"High failure count ({failure_count}) indicates systemic issues")
            confidence -= 0.15

        if validation_score < 0.3 and stage not in ["DISCOVERED"]:
            concerns.append("Low validation score is a significant risk")
            confidence -= 0.1

        if stage in ["SCALING"]:
            concerns.append("Scaling carries execution risk")

        if not concerns:
            concerns = ["Normal operating risks apply"]

        return CouncilRecommendation(
            advisor_id=advisor_id,
            advisor_name=name,
            recommendation="Proceed with risk monitoring in place" if confidence > 0.5 else "Caution advised - address risks first",
            confidence=max(0.3, confidence),
            reasoning="Risk assessment based on current metrics and stage",
            supporting_evidence=[
                f"Failure count: {failure_count}",
                f"Stage: {stage}",
                f"Validation: {validation_score:.2f}"
            ],
            concerns=concerns
        )

    def _innovation_recommendation(
        self,
        advisor_id: str,
        name: str,
        topic: str,
        stage: str
    ) -> CouncilRecommendation:
        """Generate innovation advisor recommendation."""
        if stage in ["DISCOVERED", "VALIDATING"]:
            return CouncilRecommendation(
                advisor_id=advisor_id,
                advisor_name=name,
                recommendation="Explore innovative approaches to differentiation",
                confidence=0.75,
                reasoning="Early stages are ideal for innovation exploration",
                supporting_evidence=[
                    "Lower switching costs in early stages",
                    "Opportunity to establish unique positioning"
                ],
                concerns=[
                    "Don't over-innovate at expense of core value",
                    "Validate innovations with customers"
                ]
            )
        elif stage == "BUILDING":
            return CouncilRecommendation(
                advisor_id=advisor_id,
                advisor_name=name,
                recommendation="Focus innovation on product differentiation",
                confidence=0.7,
                reasoning="Building phase benefits from focused innovation",
                supporting_evidence=["Product development is underway"],
                concerns=["Balance innovation with delivery timelines"]
            )
        else:
            return CouncilRecommendation(
                advisor_id=advisor_id,
                advisor_name=name,
                recommendation="Consider incremental innovations for optimization",
                confidence=0.65,
                reasoning="Later stages benefit from iterative improvements",
                supporting_evidence=["Established operations to improve"],
                concerns=["Major changes carry disruption risk"]
            )

    def synthesize(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Synthesize recommendations into a council output.

        Analyzes all recommendations to identify:
        - Points of agreement
        - Points of disagreement
        - Weighted final recommendation

        Args:
            session_id: ID of the council session

        Returns:
            Synthesis dictionary or None if session not found
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        if not session.recommendations:
            return None

        # Collect all concerns and evidence
        all_concerns = []
        all_evidence = []
        recommendations_text = []
        total_confidence = 0.0

        for rec in session.recommendations:
            recommendations_text.append(rec.recommendation)
            all_concerns.extend(rec.concerns)
            all_evidence.extend(rec.supporting_evidence)
            total_confidence += rec.confidence

        avg_confidence = total_confidence / len(session.recommendations)

        # Find agreements (similar recommendations)
        agreements = self._find_agreements(session.recommendations)

        # Find disagreements (conflicting recommendations)
        disagreements = self._find_disagreements(session.recommendations)

        # Generate final recommendation based on weighted input
        final_rec = self._generate_final_recommendation(
            session.recommendations, agreements, disagreements
        )

        # Build synthesis
        synthesis = {
            "advisor_count": len(session.advisors_responded),
            "recommendations_collected": len(session.recommendations),
            "average_confidence": avg_confidence,
            "agreements": agreements,
            "disagreements": disagreements,
            "key_concerns": list(set(all_concerns))[:5],
            "supporting_evidence": list(set(all_evidence))[:5],
            "final_recommendation": final_rec,
            "confidence": avg_confidence
        }

        # Update session
        session.synthesis = synthesis
        session.agreements = agreements
        session.disagreements = disagreements
        session.final_recommendation = final_rec
        session.confidence = avg_confidence
        session.completed_at = _utc_now().isoformat()
        session.status = "completed"

        # Move to history
        self._session_history.append(session)

        return synthesis

    def _find_agreements(self, recommendations: List[CouncilRecommendation]) -> List[str]:
        """Find points of agreement among recommendations."""
        agreements = []

        # Check for common themes in recommendations
        proceed_count = sum(1 for r in recommendations if "proceed" in r.recommendation.lower())
        caution_count = sum(1 for r in recommendations if "caution" in r.recommendation.lower())
        focus_count = sum(1 for r in recommendations if "focus" in r.recommendation.lower())

        total = len(recommendations)
        if total > 0:
            if proceed_count / total >= 0.5:
                agreements.append("Majority recommend proceeding")
            if caution_count / total >= 0.5:
                agreements.append("Majority advise caution")
            if focus_count / total >= 0.5:
                agreements.append("Emphasis on focus/prioritization")

        # High confidence agreement
        high_conf = [r for r in recommendations if r.confidence >= 0.7]
        if len(high_conf) == len(recommendations):
            agreements.append("All advisors have high confidence")

        return agreements if agreements else ["No strong agreement on approach"]

    def _find_disagreements(self, recommendations: List[CouncilRecommendation]) -> List[str]:
        """Find points of disagreement among recommendations."""
        disagreements = []

        # Check confidence variance
        confidences = [r.confidence for r in recommendations]
        if confidences:
            variance = max(confidences) - min(confidences)
            if variance > 0.3:
                disagreements.append(f"Confidence variance: {variance:.2f}")

        # Check for conflicting stances
        proceed = any("proceed" in r.recommendation.lower() for r in recommendations)
        caution = any("caution" in r.recommendation.lower() for r in recommendations)
        if proceed and caution:
            disagreements.append("Mixed proceed vs caution recommendations")

        # Check for different focus areas
        focuses = set()
        for rec in recommendations:
            if "innovat" in rec.recommendation.lower():
                focuses.add("innovation")
            if "risk" in rec.recommendation.lower():
                focuses.add("risk")
            if "strateg" in rec.recommendation.lower():
                focuses.add("strategy")
        if len(focuses) > 1:
            disagreements.append(f"Different focus areas: {', '.join(focuses)}")

        return disagreements if disagreements else ["No significant disagreements"]

    def _generate_final_recommendation(
        self,
        recommendations: List[CouncilRecommendation],
        agreements: List[str],
        disagreements: List[str]
    ) -> str:
        """Generate weighted final recommendation."""
        if not recommendations:
            return "Insufficient input for recommendation"

        # Weight by confidence
        weighted = sorted(recommendations, key=lambda r: r.confidence, reverse=True)
        top_rec = weighted[0]

        # Build final recommendation
        if "Majority recommend proceeding" in agreements:
            prefix = "Council recommends proceeding: "
        elif "Majority advise caution" in agreements:
            prefix = "Council advises caution: "
        else:
            prefix = "Council synthesis: "

        return f"{prefix}{top_rec.recommendation}"

    def get_session(self, session_id: str) -> Optional[CouncilSession]:
        """Get a council session by ID."""
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> List[CouncilSession]:
        """Get all active council sessions."""
        return [s for s in self._sessions.values() if s.status == "active"]

    def get_session_history(self, limit: int = 50) -> List[CouncilSession]:
        """Get recent session history."""
        return self._session_history[-limit:]

    def to_response(self, session: CouncilSession) -> AgentResponse:
        """
        Convert a completed session to an AgentResponse.

        Args:
            session: Completed council session

        Returns:
            AgentResponse with synthesis as result
        """
        if session.status != "completed":
            return create_response(
                request_id=session.request_id,
                responder="council_manager",
                status=RequestStatus.IN_PROGRESS,
                result={"session_id": session.session_id, "status": session.status}
            )

        return create_response(
            request_id=session.request_id,
            responder="council_manager",
            status=RequestStatus.COMPLETED,
            result={
                "session_id": session.session_id,
                "synthesis": session.synthesis,
                "final_recommendation": session.final_recommendation,
                "agreements": session.agreements,
                "disagreements": session.disagreements
            },
            confidence=session.confidence,
            rationale=session.final_recommendation
        )
