"""
Idea Intake for Project Alpha Discovery Layer.

Handles conversion of rough, unstructured input into structured opportunity
hypotheses. Supports ambiguous input and normalizes into actionable opportunities.

ARCHITECTURE:
- intake_raw_input: Convert raw text into RawInput
- normalize_to_hypotheses: Generate opportunity hypotheses from raw input
- Deterministic, testable logic

NO AI PRETENSE:
- Uses keyword matching and heuristics
- No fake deep intelligence
- Clear, testable rules
"""

import uuid
import re
from typing import List, Optional, Dict, Any
from datetime import datetime

from .discovery_models import (
    RawInput,
    OpportunityHypothesis,
    InputType,
    MonetizationPath,
)


def intake_raw_input(
    raw_text: str,
    submitted_by: str = "principal",
    tags: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> RawInput:
    """
    Create a RawInput record from unstructured text.

    Args:
        raw_text: Rough idea/problem/opportunity text
        submitted_by: Who submitted this
        tags: Optional tags
        context: Optional context dict

    Returns:
        RawInput record
    """
    input_id = f"input-{uuid.uuid4().hex[:12]}"
    input_type = _classify_input_type(raw_text)

    return RawInput(
        input_id=input_id,
        input_type=input_type,
        raw_text=raw_text,
        submitted_by=submitted_by,
        tags=tags or [],
        context=context or {},
    )


def normalize_to_hypotheses(
    raw_input: RawInput,
    max_hypotheses: int = 3,
) -> List[OpportunityHypothesis]:
    """
    Generate opportunity hypotheses from raw input.

    Uses heuristics to extract opportunity elements and create
    structured hypotheses.

    Args:
        raw_input: Raw input to normalize
        max_hypotheses: Maximum hypotheses to generate

    Returns:
        List of opportunity hypotheses
    """
    text = raw_input.raw_text.strip()

    if not text:
        return []

    # Generate primary hypothesis
    hypothesis = _generate_primary_hypothesis(raw_input)

    # For now, return single hypothesis
    # Future: could generate variants or multiple interpretations
    return [hypothesis]


def _classify_input_type(text: str) -> InputType:
    """
    Classify input type based on keywords.

    Args:
        text: Input text

    Returns:
        InputType classification
    """
    text_lower = text.lower()

    # Problem indicators
    problem_keywords = [
        "problem", "pain", "frustrat", "difficult", "challenge",
        "struggle", "issue", "hate", "annoying", "broken"
    ]
    problem_score = sum(1 for kw in problem_keywords if kw in text_lower)

    # Opportunity indicators
    opportunity_keywords = [
        "opportunity", "market", "space", "niche", "trend",
        "growing", "demand", "need for", "gap"
    ]
    opportunity_score = sum(1 for kw in opportunity_keywords if kw in text_lower)

    # Idea indicators
    idea_keywords = [
        "idea", "build", "create", "make", "develop",
        "platform", "tool", "service", "product", "app"
    ]
    idea_score = sum(1 for kw in idea_keywords if kw in text_lower)

    # Curiosity indicators
    curiosity_keywords = [
        "curious", "interest", "explore", "learn about",
        "what if", "wonder", "looking into"
    ]
    curiosity_score = sum(1 for kw in curiosity_keywords if kw in text_lower)

    # Determine type
    scores = {
        InputType.PROBLEM: problem_score,
        InputType.OPPORTUNITY: opportunity_score,
        InputType.IDEA: idea_score,
        InputType.CURIOSITY: curiosity_score,
    }

    max_score = max(scores.values())
    if max_score == 0:
        return InputType.HYBRID

    # Check if multiple high scores (hybrid)
    high_scorers = [k for k, v in scores.items() if v == max_score]
    if len(high_scorers) > 1:
        return InputType.HYBRID

    return max(scores.items(), key=lambda x: x[1])[0]


def _generate_primary_hypothesis(raw_input: RawInput) -> OpportunityHypothesis:
    """
    Generate primary opportunity hypothesis from raw input.

    Args:
        raw_input: Raw input

    Returns:
        OpportunityHypothesis
    """
    text = raw_input.raw_text.strip()

    # Extract elements using heuristics
    title = _extract_title(text)
    description = _extract_description(text)
    target_audience = _extract_target_audience(text)
    problem = _extract_problem(text, raw_input.input_type)
    solution = _extract_solution(text, raw_input.input_type)
    monetization = _infer_monetization(text)
    domains = _infer_domains(text)
    market_size = _estimate_market_size(text)
    competition = _estimate_competition(text)

    hypothesis_id = f"hyp-{uuid.uuid4().hex[:12]}"

    return OpportunityHypothesis(
        hypothesis_id=hypothesis_id,
        title=title,
        description=description,
        target_audience=target_audience,
        problem_addressed=problem,
        proposed_solution=solution,
        monetization_path=monetization,
        likely_domains=domains,
        market_size_estimate=market_size,
        competition_level=competition,
        source_input_id=raw_input.input_id,
    )


def _extract_title(text: str) -> str:
    """Generate title from text."""
    # Use first sentence or first 80 chars
    sentences = text.split(".")
    if sentences:
        title = sentences[0].strip()
        if len(title) > 80:
            title = title[:77] + "..."
        return title
    return text[:80]


def _extract_description(text: str) -> str:
    """Extract description."""
    # Full text for now, could be summarized
    return text


def _extract_target_audience(text: str) -> str:
    """Extract or infer target audience."""
    text_lower = text.lower()

    # Common audience patterns
    audience_patterns = {
        "small business": ["small business", "smb", "small companies"],
        "startups": ["startup", "founders", "entrepreneurs"],
        "freelancers": ["freelancer", "independent", "solopreneur"],
        "agencies": ["agency", "agencies", "consultants"],
        "enterprises": ["enterprise", "large companies", "corporations"],
        "creators": ["creator", "influencer", "content creator"],
        "developers": ["developer", "programmer", "engineer"],
        "marketers": ["marketer", "marketing team"],
        "sales teams": ["sales", "sales team", "sales rep"],
    }

    for audience, patterns in audience_patterns.items():
        if any(p in text_lower for p in patterns):
            return audience

    return "General market (not specified)"


def _extract_problem(text: str, input_type: InputType) -> str:
    """Extract problem being addressed."""
    text_lower = text.lower()

    # If input is problem-type, entire text is the problem
    if input_type == InputType.PROBLEM:
        return text

    # Look for problem indicators
    problem_markers = [
        "problem is", "issue is", "pain point",
        "struggle with", "difficult to", "hard to"
    ]

    for marker in problem_markers:
        if marker in text_lower:
            idx = text_lower.index(marker)
            # Extract sentence containing marker
            before = text[:idx]
            after = text[idx:]
            sentence_end = after.find(".")
            if sentence_end > 0:
                return (before + after[:sentence_end]).strip()

    return "Problem not explicitly stated"


def _extract_solution(text: str, input_type: InputType) -> str:
    """Extract proposed solution."""
    text_lower = text.lower()

    # If input is idea-type, it likely describes the solution
    if input_type == InputType.IDEA:
        return text

    # Look for solution indicators
    solution_markers = [
        "solution", "solve", "tool that", "platform that",
        "service that", "would help", "could help"
    ]

    for marker in solution_markers:
        if marker in text_lower:
            idx = text_lower.index(marker)
            after = text[idx:]
            sentence_end = after.find(".")
            if sentence_end > 0:
                return after[:sentence_end].strip()

    return "Solution to be determined"


def _infer_monetization(text: str) -> MonetizationPath:
    """Infer monetization path from text."""
    text_lower = text.lower()

    monetization_signals = {
        MonetizationPath.SUBSCRIPTION: [
            "subscription", "monthly", "recurring", "saas"
        ],
        MonetizationPath.ONE_TIME_SALE: [
            "sell", "purchase", "buy once", "one-time"
        ],
        MonetizationPath.TRANSACTION_FEE: [
            "fee per", "commission", "transaction fee", "percentage"
        ],
        MonetizationPath.ADVERTISING: [
            "ads", "advertising", "sponsor"
        ],
        MonetizationPath.AFFILIATE: [
            "affiliate", "referral", "commission"
        ],
        MonetizationPath.SERVICE: [
            "service", "consulting", "done for you"
        ],
    }

    for path, signals in monetization_signals.items():
        if any(s in text_lower for s in signals):
            return path

    return MonetizationPath.UNCLEAR


def _infer_domains(text: str) -> List[str]:
    """Infer likely execution domains."""
    text_lower = text.lower()

    domain_keywords = {
        "growth": ["lead", "sales", "marketing", "outreach", "acquisition"],
        "product": ["product", "feature", "build", "develop"],
        "research": ["research", "analyze", "study", "data"],
        "automation": ["automate", "workflow", "integrate"],
        "content": ["content", "blog", "article", "publish"],
        "customer_support": ["support", "customer service", "help"],
        "finance": ["finance", "payment", "invoice", "revenue"],
    }

    domains = []
    for domain, keywords in domain_keywords.items():
        if any(kw in text_lower for kw in keywords):
            domains.append(domain)

    return domains if domains else ["unknown"]


def _estimate_market_size(text: str) -> str:
    """Estimate market size from text."""
    text_lower = text.lower()

    large_indicators = ["large market", "huge opportunity", "massive", "billion"]
    small_indicators = ["niche", "small market", "specific audience"]

    if any(ind in text_lower for ind in large_indicators):
        return "large"
    elif any(ind in text_lower for ind in small_indicators):
        return "small"
    else:
        return "medium"


def _estimate_competition(text: str) -> str:
    """Estimate competition level from text."""
    text_lower = text.lower()

    high_competition = ["crowded", "lots of competitors", "saturated"]
    low_competition = ["no competitors", "no one doing", "untapped", "gap"]

    if any(ind in text_lower for ind in high_competition):
        return "high"
    elif any(ind in text_lower for ind in low_competition):
        return "low"
    else:
        return "medium"
