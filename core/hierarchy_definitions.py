"""
Hierarchy Definitions for Project Alpha
Defines the default hierarchy layers and built-in agents
"""

from typing import Dict, List
from core.agent_contracts import AgentLayer
from core.agent_registry import AgentRegistry, AgentDefinition, AgentStatus


# All lifecycle stages
ALL_STAGES = [
    "DISCOVERED", "VALIDATING", "BUILDING",
    "SCALING", "OPERATING", "OPTIMIZING", "TERMINATED"
]


def create_default_hierarchy() -> AgentRegistry:
    """
    Create and populate the default agent hierarchy.

    Hierarchy structure:
    1. Principal (human operator)
    2. Executive (chief_orchestrator)
    3. Council (strategic advisors)
    4. Board (decision makers)
    5. C-Suite (executive agents)
    6. Department (functional agents)
    7. Execution (existing workflow engine)

    Returns:
        Populated AgentRegistry
    """
    registry = AgentRegistry()

    # Register all agents
    for agent in get_all_agents():
        registry.register(agent)

    return registry


def get_all_agents() -> List[AgentDefinition]:
    """Get list of all agent definitions."""
    agents = []

    # Principal layer
    agents.extend(get_principal_agents())

    # Executive layer
    agents.extend(get_executive_agents())

    # Council layer
    agents.extend(get_council_agents())

    # Board layer
    agents.extend(get_board_agents())

    # C-Suite layer
    agents.extend(get_csuite_agents())

    # Department layer
    agents.extend(get_department_agents())

    return agents


def get_principal_agents() -> List[AgentDefinition]:
    """Get principal layer agents (human operator)."""
    return [
        AgentDefinition(
            agent_id="principal",
            name="Principal",
            layer=AgentLayer.PRINCIPAL,
            role="Human operator with final authority",
            capabilities=["approve", "override", "configure", "terminate"],
            allowed_stages=ALL_STAGES,
            reports_to=None,
            direct_reports=["chief_orchestrator"]
        )
    ]


def get_executive_agents() -> List[AgentDefinition]:
    """Get executive layer agents."""
    return [
        AgentDefinition(
            agent_id="chief_orchestrator",
            name="Chief Orchestrator",
            layer=AgentLayer.EXECUTIVE,
            role="Central coordinator under principal authority",
            capabilities=[
                "route_requests",
                "coordinate_hierarchy",
                "escalate_decisions",
                "delegate_work",
                "monitor_execution"
            ],
            allowed_stages=ALL_STAGES,
            handler_path="core.chief_orchestrator.ChiefOrchestrator",
            reports_to="principal",
            direct_reports=["council_manager", "decision_board", "ceo"]
        )
    ]


def get_council_agents() -> List[AgentDefinition]:
    """Get council layer agents (strategic advisors)."""
    return [
        AgentDefinition(
            agent_id="council_manager",
            name="Council Manager",
            layer=AgentLayer.COUNCIL,
            role="Coordinates strategic advisor agents",
            capabilities=[
                "gather_recommendations",
                "synthesize_advice",
                "facilitate_debate",
                "present_options"
            ],
            allowed_stages=ALL_STAGES,
            handler_path="core.council_manager.CouncilManager",
            reports_to="chief_orchestrator",
            direct_reports=[
                "advisor_strategy",
                "advisor_risk",
                "advisor_innovation"
            ]
        ),
        AgentDefinition(
            agent_id="advisor_strategy",
            name="Strategy Advisor",
            layer=AgentLayer.COUNCIL,
            role="Strategic planning and direction advice",
            capabilities=["strategic_analysis", "market_assessment", "competitive_analysis"],
            allowed_stages=ALL_STAGES,
            reports_to="council_manager"
        ),
        AgentDefinition(
            agent_id="advisor_risk",
            name="Risk Advisor",
            layer=AgentLayer.COUNCIL,
            role="Risk assessment and mitigation advice",
            capabilities=["risk_analysis", "threat_assessment", "mitigation_planning"],
            allowed_stages=ALL_STAGES,
            reports_to="council_manager"
        ),
        AgentDefinition(
            agent_id="advisor_innovation",
            name="Innovation Advisor",
            layer=AgentLayer.COUNCIL,
            role="Innovation opportunities and technology trends",
            capabilities=["technology_trends", "innovation_opportunities", "disruption_analysis"],
            allowed_stages=ALL_STAGES,
            reports_to="council_manager"
        )
    ]


def get_board_agents() -> List[AgentDefinition]:
    """Get board layer agents (decision makers)."""
    return [
        AgentDefinition(
            agent_id="decision_board",
            name="Decision Board",
            layer=AgentLayer.BOARD,
            role="Receives options/recommendations, resolves conflicts, selects direction",
            capabilities=[
                "evaluate_options",
                "resolve_conflicts",
                "select_direction",
                "provide_rationale",
                "vote_on_decisions"
            ],
            allowed_stages=ALL_STAGES,
            handler_path="core.decision_board.DecisionBoard",
            reports_to="chief_orchestrator",
            direct_reports=["ceo", "coo", "cfo", "cto", "cmo"]
        )
    ]


def get_csuite_agents() -> List[AgentDefinition]:
    """Get C-Suite layer agents (executive agents)."""
    return [
        AgentDefinition(
            agent_id="ceo",
            name="CEO Agent",
            layer=AgentLayer.C_SUITE,
            role="Overall business strategy and vision",
            capabilities=[
                "strategic_direction",
                "priority_setting",
                "resource_allocation",
                "stakeholder_management"
            ],
            allowed_stages=ALL_STAGES,
            reports_to="decision_board",
            direct_reports=["dept_research", "dept_planning"]
        ),
        AgentDefinition(
            agent_id="coo",
            name="COO Agent",
            layer=AgentLayer.C_SUITE,
            role="Operations and execution oversight",
            capabilities=[
                "operational_planning",
                "process_optimization",
                "execution_monitoring",
                "resource_management"
            ],
            allowed_stages=["BUILDING", "SCALING", "OPERATING", "OPTIMIZING"],
            reports_to="decision_board",
            direct_reports=["dept_operations", "dept_automation"]
        ),
        AgentDefinition(
            agent_id="cfo",
            name="CFO Agent",
            layer=AgentLayer.C_SUITE,
            role="Financial strategy and resource management",
            capabilities=[
                "financial_planning",
                "budget_management",
                "roi_analysis",
                "cost_optimization"
            ],
            allowed_stages=ALL_STAGES,
            reports_to="decision_board"
        ),
        AgentDefinition(
            agent_id="cto",
            name="CTO Agent",
            layer=AgentLayer.C_SUITE,
            role="Technology strategy and architecture",
            capabilities=[
                "technology_strategy",
                "architecture_decisions",
                "technical_assessment",
                "innovation_planning"
            ],
            allowed_stages=["VALIDATING", "BUILDING", "SCALING", "OPERATING", "OPTIMIZING"],
            reports_to="decision_board",
            direct_reports=["dept_product", "dept_validation"]
        ),
        AgentDefinition(
            agent_id="cmo",
            name="CMO Agent",
            layer=AgentLayer.C_SUITE,
            role="Marketing strategy and growth",
            capabilities=[
                "market_strategy",
                "brand_management",
                "customer_acquisition",
                "growth_planning"
            ],
            allowed_stages=["VALIDATING", "BUILDING", "SCALING", "OPERATING"],
            reports_to="decision_board",
            direct_reports=["dept_growth", "dept_content"]
        )
    ]


def get_department_agents() -> List[AgentDefinition]:
    """Get department layer agents (functional execution)."""
    return [
        AgentDefinition(
            agent_id="dept_research",
            name="Research Department",
            layer=AgentLayer.DEPARTMENT,
            role="Market research and opportunity discovery",
            capabilities=[
                "market_research",
                "opportunity_discovery",
                "competitor_analysis",
                "trend_identification"
            ],
            allowed_stages=["DISCOVERED", "VALIDATING"],
            handler_path="core.research_engine.ResearchEngine",
            reports_to="ceo"
        ),
        AgentDefinition(
            agent_id="dept_planning",
            name="Planning Department",
            layer=AgentLayer.DEPARTMENT,
            role="Strategic and operational planning",
            capabilities=[
                "strategic_planning",
                "task_planning",
                "resource_planning",
                "timeline_management"
            ],
            allowed_stages=ALL_STAGES,
            handler_path="core.planning_engine.PlanningEngine",
            reports_to="ceo"
        ),
        AgentDefinition(
            agent_id="dept_product",
            name="Product/Build Department",
            layer=AgentLayer.DEPARTMENT,
            role="Product development and building",
            capabilities=[
                "product_development",
                "feature_building",
                "mvp_creation",
                "iteration_management"
            ],
            allowed_stages=["BUILDING", "SCALING", "OPTIMIZING"],
            handler_path="core.stage_workflows.StageWorkflows",
            reports_to="cto"
        ),
        AgentDefinition(
            agent_id="dept_operations",
            name="Operations Department",
            layer=AgentLayer.DEPARTMENT,
            role="Day-to-day operations and process management",
            capabilities=[
                "process_management",
                "quality_control",
                "delivery_management",
                "operational_support"
            ],
            allowed_stages=["OPERATING", "OPTIMIZING"],
            handler_path="core.execution_engine.ExecutionEngine",
            reports_to="coo"
        ),
        AgentDefinition(
            agent_id="dept_growth",
            name="Growth/Marketing Department",
            layer=AgentLayer.DEPARTMENT,
            role="Customer acquisition and growth",
            capabilities=[
                "customer_acquisition",
                "marketing_campaigns",
                "conversion_optimization",
                "retention_strategies"
            ],
            allowed_stages=["SCALING", "OPERATING"],
            reports_to="cmo"
        ),
        AgentDefinition(
            agent_id="dept_content",
            name="Content Department",
            layer=AgentLayer.DEPARTMENT,
            role="Content creation and management",
            capabilities=[
                "content_creation",
                "messaging",
                "documentation",
                "communication"
            ],
            allowed_stages=["VALIDATING", "BUILDING", "SCALING", "OPERATING"],
            reports_to="cmo"
        ),
        AgentDefinition(
            agent_id="dept_automation",
            name="Automation Department",
            layer=AgentLayer.DEPARTMENT,
            role="Process automation and efficiency",
            capabilities=[
                "process_automation",
                "workflow_optimization",
                "tool_integration",
                "efficiency_improvement"
            ],
            allowed_stages=["BUILDING", "SCALING", "OPERATING", "OPTIMIZING"],
            reports_to="coo"
        ),
        AgentDefinition(
            agent_id="dept_validation",
            name="Validation Department",
            layer=AgentLayer.DEPARTMENT,
            role="Testing, validation, and quality assurance",
            capabilities=[
                "validation_testing",
                "quality_assurance",
                "hypothesis_testing",
                "metric_validation"
            ],
            allowed_stages=["VALIDATING", "BUILDING", "OPTIMIZING"],
            handler_path="core.workflow_validator.WorkflowValidator",
            reports_to="cto"
        )
    ]


# Layer hierarchy order (top to bottom)
LAYER_ORDER = [
    AgentLayer.PRINCIPAL,
    AgentLayer.EXECUTIVE,
    AgentLayer.COUNCIL,
    AgentLayer.BOARD,
    AgentLayer.C_SUITE,
    AgentLayer.DEPARTMENT,
    AgentLayer.EXECUTION
]


def get_layer_index(layer: AgentLayer) -> int:
    """Get the index of a layer in the hierarchy (0 = top)."""
    try:
        return LAYER_ORDER.index(layer)
    except ValueError:
        return len(LAYER_ORDER)


def is_superior_layer(layer_a: AgentLayer, layer_b: AgentLayer) -> bool:
    """Check if layer_a is above layer_b in the hierarchy."""
    return get_layer_index(layer_a) < get_layer_index(layer_b)


def get_escalation_path(from_layer: AgentLayer) -> List[AgentLayer]:
    """Get the layers above a given layer for escalation."""
    idx = get_layer_index(from_layer)
    return LAYER_ORDER[:idx]


# Capability to agent mapping for routing
CAPABILITY_ROUTING: Dict[str, List[str]] = {
    # Research capabilities
    "market_research": ["dept_research"],
    "opportunity_discovery": ["dept_research"],
    "competitor_analysis": ["dept_research"],

    # Planning capabilities
    "strategic_planning": ["dept_planning", "ceo"],
    "task_planning": ["dept_planning"],
    "resource_planning": ["dept_planning", "coo"],

    # Product capabilities
    "product_development": ["dept_product"],
    "feature_building": ["dept_product"],
    "mvp_creation": ["dept_product"],

    # Operations capabilities
    "process_management": ["dept_operations", "coo"],
    "quality_control": ["dept_operations", "dept_validation"],

    # Growth capabilities
    "customer_acquisition": ["dept_growth", "cmo"],
    "marketing_campaigns": ["dept_growth"],

    # Technology capabilities
    "technology_strategy": ["cto"],
    "architecture_decisions": ["cto", "dept_product"],

    # Validation capabilities
    "validation_testing": ["dept_validation"],
    "hypothesis_testing": ["dept_validation"],

    # Strategic capabilities
    "strategic_direction": ["ceo", "decision_board"],
    "priority_setting": ["ceo"],

    # Decision capabilities
    "evaluate_options": ["decision_board"],
    "resolve_conflicts": ["decision_board", "chief_orchestrator"],
}


def get_agents_for_capability(capability: str) -> List[str]:
    """Get agent IDs that can handle a specific capability."""
    return CAPABILITY_ROUTING.get(capability, [])
