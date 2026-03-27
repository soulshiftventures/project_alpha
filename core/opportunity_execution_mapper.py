"""
Opportunity Execution Mapper for Project Alpha.

Maps opportunity handoffs to execution plans with appropriate prepopulation.

ARCHITECTURE:
- map_to_execution_plan: Main mapping function
- prepopulate_pursue_plan: Pursue-now path planning
- prepopulate_validate_plan: Validate-first path planning
- Domain and cost continuity preservation
"""

import logging
from typing import Dict, List, Optional, Any

from .opportunity_handoff import HandoffRecord, HandoffMode, HandoffContext
from .execution_plan import (
    ExecutionPlan, ExecutionStep,
    ExecutionDomain, ExecutionStatus, SkillBundle
)
from .discovery_models import OpportunityRecord, OperatorConstraints

logger = logging.getLogger(__name__)


def map_to_execution_plan(
    handoff: HandoffRecord,
    business_id: Optional[str] = None,
) -> ExecutionPlan:
    """
    Map opportunity handoff to execution plan.

    Creates appropriate execution plan based on handoff mode:
    - PURSUE_NOW → full execution plan
    - VALIDATE_FIRST → validation-oriented plan

    Args:
        handoff: Handoff record with opportunity context
        business_id: Optional business ID

    Returns:
        Prepopulated ExecutionPlan
    """
    context = handoff.handoff_context

    # Determine business ID
    if business_id is None:
        business_id = f"opp_{context.opportunity_id[:8]}"

    # Map domain
    primary_domain = _map_domain(context.recommended_primary_domain)

    if handoff.mode == HandoffMode.PURSUE_NOW:
        plan = _prepopulate_pursue_plan(handoff, business_id, primary_domain)
    elif handoff.mode == HandoffMode.VALIDATE_FIRST:
        plan = _prepopulate_validate_plan(handoff, business_id, primary_domain)
    else:
        raise ValueError(f"Cannot create execution plan for handoff mode: {handoff.mode.value}")

    logger.info(
        f"Mapped handoff {handoff.handoff_id} to execution plan {plan.plan_id} "
        f"(mode: {handoff.mode.value}, domain: {primary_domain.value})"
    )

    return plan


def _prepopulate_pursue_plan(
    handoff: HandoffRecord,
    business_id: str,
    primary_domain: ExecutionDomain,
) -> ExecutionPlan:
    """
    Create execution-oriented plan for pursue-now handoff.

    Emphasizes implementation and launch readiness.

    Args:
        handoff: Handoff record
        business_id: Business ID
        primary_domain: Primary execution domain

    Returns:
        ExecutionPlan for pursue-now
    """
    context = handoff.handoff_context

    # Build objective from opportunity
    objective = f"Execute: {context.opportunity_title}"

    # Create empty skill bundle
    skill_bundle = SkillBundle(
        skills=[],
        commands=[],
        specialized_agents=[],
        requires_approval=False,
    )

    # Create plan
    plan = ExecutionPlan(
        objective=objective,
        role_id="principal_human",
        business_id=business_id,
        stage="BUILDING",  # Pursue-now starts in building
        primary_domain=primary_domain,
        skill_bundle=skill_bundle,
        requires_approval=False,
    )

    # Store context in outputs for reference (ExecutionPlan doesn't have metadata attribute)
    plan.outputs.append({
        "type": "opportunity_context",
        "opportunity_id": context.opportunity_id,
        "handoff_id": handoff.handoff_id,
        "handoff_mode": handoff.mode.value,
        "target_audience": context.target_audience,
        "problem_addressed": context.problem_addressed,
        "proposed_solution": context.proposed_solution,
        "monetization_path": context.monetization_path,
        "overall_score": context.overall_score,
        "risk_level": context.risk_level,
        "warnings": context.warnings,
    })

    # Prepopulate steps from next_steps
    for idx, next_step in enumerate(context.next_steps[:5], 1):  # Max 5 initial steps
        step = ExecutionStep(
            step_id=f"step_{idx}_pursue",
            description=next_step,
            domain=primary_domain,
            skills=[],
            commands=[],
            handler_module="stage_workflows",
            handler_method="execute_building_task",
            status=ExecutionStatus.PENDING,
        )
        plan.steps.append(step)

    # Add domain-specific steps if none provided
    if not plan.steps:
        plan.steps.append(
            ExecutionStep(
                step_id="step_1_initial",
                description=f"Begin execution: {context.proposed_solution}",
                domain=primary_domain,
                skills=[],
                commands=[],
                handler_module="stage_workflows",
                handler_method="execute_building_task",
                status=ExecutionStatus.PENDING,
            )
        )

    # Note: ExecutionPlan doesn't have complexity_score/risk_score/projected_capital attributes
    # Context is preserved in plan.outputs for reference

    return plan


def _prepopulate_validate_plan(
    handoff: HandoffRecord,
    business_id: str,
    primary_domain: ExecutionDomain,
) -> ExecutionPlan:
    """
    Create validation-oriented plan for validate-first handoff.

    Emphasizes lightweight testing and evidence gathering.

    Args:
        handoff: Handoff record
        business_id: Business ID
        primary_domain: Primary execution domain

    Returns:
        ExecutionPlan for validate-first
    """
    context = handoff.handoff_context

    # Build validation objective
    objective = f"Validate: {context.opportunity_title}"

    # Create empty skill bundle
    skill_bundle = SkillBundle(
        skills=[],
        commands=[],
        specialized_agents=[],
        requires_approval=False,
    )

    # Create plan in VALIDATING stage
    plan = ExecutionPlan(
        objective=objective,
        role_id="principal_human",
        business_id=business_id,
        stage="VALIDATING",
        primary_domain=primary_domain,
        skill_bundle=skill_bundle,
        requires_approval=False,
    )

    # Store context in outputs for reference
    plan.outputs.append({
        "type": "opportunity_context",
        "opportunity_id": context.opportunity_id,
        "handoff_id": handoff.handoff_id,
        "handoff_mode": handoff.mode.value,
        "validation_focus": "lightweight_testing",
        "target_audience": context.target_audience,
        "problem_addressed": context.problem_addressed,
        "overall_score": context.overall_score,
        "warnings": context.warnings,
    })

    # Create validation-specific steps
    validation_steps = [
        f"Research: Validate market demand for {context.target_audience}",
        f"Test: {context.problem_addressed} - confirm pain point exists",
        f"Prototype: Minimal version of {context.proposed_solution}",
        f"Gather evidence: Test with {context.target_audience}",
        f"Evaluate: Determine if validation criteria met",
    ]

    # Use next_steps if provided, otherwise use validation template
    steps_to_use = context.next_steps[:5] if context.next_steps else validation_steps

    for idx, step_desc in enumerate(steps_to_use, 1):
        step = ExecutionStep(
            step_id=f"step_{idx}_validate",
            description=step_desc,
            domain=ExecutionDomain.VALIDATION if "test" in step_desc.lower() or "validate" in step_desc.lower() else primary_domain,
            skills=[],
            commands=[],
            handler_module="stage_workflows",
            handler_method="execute_validating_task",
            status=ExecutionStatus.PENDING,
        )
        plan.steps.append(step)

    # Note: ExecutionPlan doesn't have complexity_score/risk_score/projected_capital attributes
    # Validation context (simpler, lower risk, 10% capital) is documented in outputs

    return plan


def _map_domain(domain_str: str) -> ExecutionDomain:
    """Map domain string to ExecutionDomain enum."""
    domain_mapping = {
        "research": ExecutionDomain.RESEARCH,
        "strategy": ExecutionDomain.STRATEGY,
        "planning": ExecutionDomain.PLANNING,
        "product": ExecutionDomain.PRODUCT,
        "engineering": ExecutionDomain.ENGINEERING,
        "validation": ExecutionDomain.VALIDATION,
        "operations": ExecutionDomain.OPERATIONS,
        "automation": ExecutionDomain.AUTOMATION,
        "internal_admin": ExecutionDomain.INTERNAL_ADMIN,
        "finance": ExecutionDomain.FINANCE,
        "compliance": ExecutionDomain.COMPLIANCE,
        "growth": ExecutionDomain.GROWTH,
        "customer_support": ExecutionDomain.CUSTOMER_SUPPORT,
        "content": ExecutionDomain.CONTENT,
        "unknown": ExecutionDomain.UNKNOWN,
    }
    return domain_mapping.get(domain_str, ExecutionDomain.UNKNOWN)


def enrich_plan_with_opportunity_context(
    plan: ExecutionPlan,
    opportunity: OpportunityRecord,
) -> ExecutionPlan:
    """
    Enrich existing execution plan with opportunity context.

    Useful when plan already exists but needs opportunity metadata.

    Args:
        plan: Existing execution plan
        opportunity: Opportunity record

    Returns:
        Enriched plan
    """
    # Add opportunity metadata to outputs (ExecutionPlan doesn't have metadata attribute)
    context_output = {
        "type": "opportunity_context",
        "opportunity_id": opportunity.opportunity_id,
        "opportunity_title": opportunity.hypothesis.title,
        "opportunity_score": opportunity.score.overall_score,
        "opportunity_recommendation": opportunity.recommendation.action.value,
    }

    # Add capital info if available
    if opportunity.operator_constraints_snapshot:
        constraints_dict = opportunity.operator_constraints_snapshot
        max_capital = constraints_dict.get("max_initial_capital", 10000)
        context_output["projected_capital"] = max_capital * opportunity.score.capital_intensity

    plan.outputs.append(context_output)

    return plan
