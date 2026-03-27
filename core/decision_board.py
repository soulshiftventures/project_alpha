"""
Decision Board for Project Alpha
Receives options/recommendations, resolves conflicts, selects direction with rationale
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from core.agent_contracts import (
    AgentRequest, AgentResponse, RequestStatus,
    DecisionRecord, BoardVote, create_response
)
from core.agent_registry import AgentRegistry, AgentDefinition, AgentLayer


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class DecisionOption:
    """An option to be evaluated by the board."""
    option_id: str
    title: str
    description: str

    # Scores and metrics
    scores: Dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0

    # Source
    proposed_by: str = ""  # Agent that proposed this option
    from_council: bool = False  # Whether it came from council synthesis

    # Metadata
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "option_id": self.option_id,
            "title": self.title,
            "description": self.description,
            "scores": self.scores,
            "overall_score": self.overall_score,
            "proposed_by": self.proposed_by,
            "from_council": self.from_council,
            "pros": self.pros,
            "cons": self.cons,
            "risks": self.risks,
            "requirements": self.requirements
        }


@dataclass
class DecisionSession:
    """
    A decision-making session for the board.

    Tracks options, votes, and final decision.
    """
    session_id: str = field(default_factory=lambda: f"board_{_utc_now().strftime('%Y%m%d%H%M%S%f')}")
    request_id: str = ""

    # Topic
    topic: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    # Options
    options: List[DecisionOption] = field(default_factory=list)

    # Voting
    voters: List[str] = field(default_factory=list)
    votes: List[BoardVote] = field(default_factory=list)

    # Decision
    selected_option_id: Optional[str] = None
    selected_option: Optional[DecisionOption] = None
    decision_rationale: str = ""
    next_actions: List[str] = field(default_factory=list)
    confidence: float = 0.0

    # Timing
    started_at: str = field(default_factory=lambda: _utc_now().isoformat())
    completed_at: Optional[str] = None
    status: str = "active"  # active, voting, decided, cancelled

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "request_id": self.request_id,
            "topic": self.topic,
            "context": self.context,
            "options": [o.to_dict() for o in self.options],
            "voters": self.voters,
            "votes": [v.to_dict() for v in self.votes],
            "selected_option_id": self.selected_option_id,
            "selected_option": self.selected_option.to_dict() if self.selected_option else None,
            "decision_rationale": self.decision_rationale,
            "next_actions": self.next_actions,
            "confidence": self.confidence,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status
        }


class DecisionBoard:
    """
    The decision-making board for the hierarchy.

    Provides:
    - Option evaluation and scoring
    - Conflict resolution
    - Direction selection with rationale
    - Vote-based decision making
    """

    # Scoring criteria and weights
    DEFAULT_CRITERIA = {
        "strategic_alignment": 0.25,
        "risk_level": 0.20,
        "resource_efficiency": 0.20,
        "feasibility": 0.20,
        "potential_impact": 0.15
    }

    def __init__(self, registry: Optional[AgentRegistry] = None):
        """
        Initialize the decision board.

        Args:
            registry: Agent registry for voter lookup
        """
        self._registry = registry
        self._sessions: Dict[str, DecisionSession] = {}
        self._decision_history: List[DecisionRecord] = []
        self._criteria = self.DEFAULT_CRITERIA.copy()

    def set_registry(self, registry: AgentRegistry) -> None:
        """Set the agent registry."""
        self._registry = registry

    def set_criteria(self, criteria: Dict[str, float]) -> None:
        """
        Set custom scoring criteria.

        Args:
            criteria: Dictionary of criterion name to weight
        """
        self._criteria = criteria

    def get_board_members(self) -> List[AgentDefinition]:
        """
        Get all board member agents.

        Returns:
            List of C-suite agents who participate in board decisions
        """
        if not self._registry:
            return []
        return self._registry.get_by_layer(AgentLayer.C_SUITE)

    def create_session(
        self,
        request: AgentRequest,
        topic: str,
        context: Optional[Dict[str, Any]] = None
    ) -> DecisionSession:
        """
        Create a new decision session.

        Args:
            request: Originating request
            topic: Decision topic
            context: Additional context

        Returns:
            New DecisionSession
        """
        # Get board members as voters
        voters = [m.agent_id for m in self.get_board_members()]

        session = DecisionSession(
            request_id=request.request_id,
            topic=topic,
            context=context or {},
            voters=voters
        )

        self._sessions[session.session_id] = session
        return session

    def add_option(
        self,
        session_id: str,
        title: str,
        description: str,
        proposed_by: str = "",
        from_council: bool = False,
        pros: Optional[List[str]] = None,
        cons: Optional[List[str]] = None,
        risks: Optional[List[str]] = None
    ) -> Optional[DecisionOption]:
        """
        Add an option to a decision session.

        Args:
            session_id: Session ID
            title: Option title
            description: Option description
            proposed_by: Agent that proposed this
            from_council: Whether from council synthesis
            pros: List of advantages
            cons: List of disadvantages
            risks: List of risks

        Returns:
            Created DecisionOption or None if session not found
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        option = DecisionOption(
            option_id=f"opt_{len(session.options) + 1}",
            title=title,
            description=description,
            proposed_by=proposed_by,
            from_council=from_council,
            pros=pros or [],
            cons=cons or [],
            risks=risks or []
        )

        session.options.append(option)
        return option

    def add_options_from_council(
        self,
        session_id: str,
        council_synthesis: Dict[str, Any]
    ) -> List[DecisionOption]:
        """
        Add options derived from council synthesis.

        Args:
            session_id: Session ID
            council_synthesis: Output from council manager

        Returns:
            List of created options
        """
        if session_id not in self._sessions:
            return []

        options = []

        # Create main recommendation as an option
        final_rec = council_synthesis.get("final_recommendation", "")
        if final_rec:
            option = self.add_option(
                session_id=session_id,
                title="Council Recommendation",
                description=final_rec,
                proposed_by="council_manager",
                from_council=True,
                pros=council_synthesis.get("agreements", []),
                cons=council_synthesis.get("disagreements", []),
                risks=council_synthesis.get("key_concerns", [])
            )
            if option:
                options.append(option)

        return options

    def score_options(self, session_id: str, business: Optional[Dict[str, Any]] = None) -> bool:
        """
        Score all options in a session.

        Uses weighted criteria to produce scores.

        Args:
            session_id: Session ID
            business: Business context for scoring

        Returns:
            True if scoring completed, False if session not found
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        business = business or session.context.get("business", {})

        for option in session.options:
            scores = self._evaluate_option(option, business, session.context)
            option.scores = scores

            # Calculate weighted overall score
            total_weight = sum(self._criteria.values())
            overall = sum(
                scores.get(criterion, 0.5) * weight
                for criterion, weight in self._criteria.items()
            ) / total_weight if total_weight > 0 else 0.5

            option.overall_score = overall

        return True

    def _evaluate_option(
        self,
        option: DecisionOption,
        business: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Evaluate an option against criteria.

        This is deterministic scoring logic.
        """
        scores = {}
        stage = business.get("stage", "DISCOVERED")
        metrics = business.get("metrics", {})

        # Strategic alignment (based on stage appropriateness)
        stage_alignment = {
            "DISCOVERED": 0.7,
            "VALIDATING": 0.75,
            "BUILDING": 0.8,
            "SCALING": 0.85,
            "OPERATING": 0.8,
            "OPTIMIZING": 0.7,
            "TERMINATED": 0.5
        }
        scores["strategic_alignment"] = stage_alignment.get(stage, 0.6)

        # Risk level (inverse - higher is better/lower risk)
        failure_count = metrics.get("failure_count", 0)
        risk_base = 0.8
        risk_base -= failure_count * 0.1
        risk_base -= len(option.risks) * 0.05
        scores["risk_level"] = max(0.2, min(1.0, risk_base))

        # Resource efficiency (based on requirements)
        req_count = len(option.requirements)
        efficiency = 0.9 - (req_count * 0.1)
        scores["resource_efficiency"] = max(0.3, efficiency)

        # Feasibility (based on current metrics and stage)
        validation_score = metrics.get("validation_score", 0.5)
        build_progress = metrics.get("build_progress", 0.5)

        if stage in ["DISCOVERED", "VALIDATING"]:
            feasibility = 0.7 + (validation_score * 0.2)
        elif stage in ["BUILDING"]:
            feasibility = 0.6 + (build_progress * 0.3)
        else:
            feasibility = 0.75

        scores["feasibility"] = min(1.0, feasibility)

        # Potential impact (based on pros/cons ratio and source)
        pros_cons_ratio = len(option.pros) / max(len(option.cons), 1)
        impact = 0.5 + min(0.4, pros_cons_ratio * 0.1)
        if option.from_council:
            impact += 0.1  # Council-backed options get slight boost
        scores["potential_impact"] = min(1.0, impact)

        return scores

    def cast_vote(
        self,
        session_id: str,
        voter_id: str,
        vote: str,
        rationale: str = "",
        conditions: Optional[List[str]] = None
    ) -> Optional[BoardVote]:
        """
        Cast a vote in a decision session.

        Args:
            session_id: Session ID
            voter_id: Voting agent ID
            vote: "approve", "reject", or "abstain"
            rationale: Reason for vote
            conditions: Conditions for approval

        Returns:
            BoardVote or None if session not found
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        # Get voter name from registry
        voter_name = voter_id
        weight = 1.0
        if self._registry:
            voter_def = self._registry.get(voter_id)
            if voter_def:
                voter_name = voter_def.name
                # CEO gets higher weight
                if voter_id == "ceo":
                    weight = 1.5

        board_vote = BoardVote(
            voter_id=voter_id,
            voter_name=voter_name,
            vote=vote,
            weight=weight,
            rationale=rationale,
            conditions=conditions or []
        )

        session.votes.append(board_vote)
        session.status = "voting"

        return board_vote

    def auto_vote(self, session_id: str) -> List[BoardVote]:
        """
        Generate automatic votes from all board members.

        This is deterministic voting based on option scores.

        Args:
            session_id: Session ID

        Returns:
            List of generated votes
        """
        if session_id not in self._sessions:
            return []

        session = self._sessions[session_id]

        # Get best option by score
        if not session.options:
            return []

        best_option = max(session.options, key=lambda o: o.overall_score)
        votes = []

        for voter_id in session.voters:
            # Determine vote based on option quality
            score = best_option.overall_score

            if score >= 0.7:
                vote = "approve"
                rationale = f"Strong option with score {score:.2f}"
            elif score >= 0.5:
                vote = "approve"
                rationale = f"Acceptable option with score {score:.2f}"
            else:
                vote = "abstain"
                rationale = f"Uncertain about option with score {score:.2f}"

            # Some voters might have specific concerns
            conditions = []
            if best_option.risks:
                conditions.append(f"Monitor risk: {best_option.risks[0]}")

            board_vote = self.cast_vote(
                session_id=session_id,
                voter_id=voter_id,
                vote=vote,
                rationale=rationale,
                conditions=conditions
            )
            if board_vote:
                votes.append(board_vote)

        return votes

    def decide(self, session_id: str) -> Optional[DecisionRecord]:
        """
        Make a final decision based on votes and scores.

        Args:
            session_id: Session ID

        Returns:
            DecisionRecord or None if session not found
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        if not session.options:
            return None

        # Calculate vote tallies
        approve_weight = sum(v.weight for v in session.votes if v.vote == "approve")
        reject_weight = sum(v.weight for v in session.votes if v.vote == "reject")
        total_weight = sum(v.weight for v in session.votes)

        # Determine if approved
        approved = approve_weight > reject_weight if total_weight > 0 else True

        if approved:
            # Select best option by score
            selected = max(session.options, key=lambda o: o.overall_score)
            session.selected_option_id = selected.option_id
            session.selected_option = selected

            # Build rationale
            rationale_parts = [
                f"Selected: {selected.title}",
                f"Score: {selected.overall_score:.2f}",
                f"Votes: {approve_weight:.1f} approve, {reject_weight:.1f} reject"
            ]
            if selected.pros:
                rationale_parts.append(f"Key advantage: {selected.pros[0]}")

            session.decision_rationale = ". ".join(rationale_parts)

            # Determine next actions
            session.next_actions = self._determine_next_actions(selected, session.context)

            # Confidence based on vote margin and score
            vote_confidence = approve_weight / total_weight if total_weight > 0 else 0.5
            session.confidence = (vote_confidence + selected.overall_score) / 2
        else:
            # Decision rejected - no option selected
            session.decision_rationale = "Options rejected by board vote"
            session.confidence = 0.0

        # Finalize session
        session.completed_at = _utc_now().isoformat()
        session.status = "decided"

        # Create decision record
        record = DecisionRecord(
            request_id=session.request_id,
            decision_type="board_decision",
            decision=session.selected_option.title if session.selected_option else "Rejected",
            rationale=session.decision_rationale,
            options_considered=[o.to_dict() for o in session.options],
            selected_option_index=session.options.index(session.selected_option) if session.selected_option else -1,
            confidence=session.confidence,
            scores={o.option_id: o.overall_score for o in session.options},
            decided_by="decision_board"
        )

        self._decision_history.append(record)
        return record

    def _determine_next_actions(
        self,
        option: DecisionOption,
        context: Dict[str, Any]
    ) -> List[str]:
        """Determine next actions based on selected option."""
        actions = []

        stage = context.get("business", {}).get("stage", "DISCOVERED")

        # Stage-appropriate actions
        if stage == "DISCOVERED":
            actions.append("Proceed with validation tasks")
        elif stage == "VALIDATING":
            actions.append("Continue validation with selected approach")
        elif stage == "BUILDING":
            actions.append("Execute build tasks per decision")
        elif stage == "SCALING":
            actions.append("Scale operations according to decision")
        elif stage == "OPERATING":
            actions.append("Adjust operations as decided")
        elif stage == "OPTIMIZING":
            actions.append("Implement optimization measures")

        # Risk-based actions
        if option.risks:
            actions.append(f"Monitor risk: {option.risks[0]}")

        # Requirements-based actions
        if option.requirements:
            actions.append(f"Fulfill requirement: {option.requirements[0]}")

        return actions

    def evaluate_single(
        self,
        request: AgentRequest,
        recommendation: str,
        business: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[DecisionRecord, List[str]]:
        """
        Convenience method to evaluate a single recommendation.

        Creates a session, adds the option, scores, votes, and decides.

        Args:
            request: Originating request
            recommendation: The recommendation to evaluate
            business: Business context
            context: Additional context

        Returns:
            Tuple of (DecisionRecord, next_actions)
        """
        context = context or {}
        context["business"] = business

        # Create session
        session = self.create_session(
            request=request,
            topic=request.objective,
            context=context
        )

        # Add option
        self.add_option(
            session_id=session.session_id,
            title="Recommended Action",
            description=recommendation,
            proposed_by=request.requester
        )

        # Score
        self.score_options(session.session_id, business)

        # Auto-vote
        self.auto_vote(session.session_id)

        # Decide
        record = self.decide(session.session_id)

        return record, session.next_actions

    def get_session(self, session_id: str) -> Optional[DecisionSession]:
        """Get a decision session by ID."""
        return self._sessions.get(session_id)

    def get_decision_history(self, limit: int = 50) -> List[DecisionRecord]:
        """Get recent decision history."""
        return self._decision_history[-limit:]

    def to_response(self, session: DecisionSession) -> AgentResponse:
        """
        Convert a completed session to an AgentResponse.

        Args:
            session: Completed decision session

        Returns:
            AgentResponse with decision as result
        """
        if session.status != "decided":
            return create_response(
                request_id=session.request_id,
                responder="decision_board",
                status=RequestStatus.IN_PROGRESS,
                result={"session_id": session.session_id, "status": session.status}
            )

        return create_response(
            request_id=session.request_id,
            responder="decision_board",
            status=RequestStatus.COMPLETED,
            result={
                "session_id": session.session_id,
                "decision": session.selected_option.title if session.selected_option else "Rejected",
                "selected_option": session.selected_option.to_dict() if session.selected_option else None,
                "rationale": session.decision_rationale,
                "next_actions": session.next_actions,
                "votes_summary": {
                    "approve": sum(1 for v in session.votes if v.vote == "approve"),
                    "reject": sum(1 for v in session.votes if v.vote == "reject"),
                    "abstain": sum(1 for v in session.votes if v.vote == "abstain")
                }
            },
            confidence=session.confidence,
            rationale=session.decision_rationale
        )
