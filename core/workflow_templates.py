"""
Workflow Templates for Project Alpha
8 pre-built templates with full tool integration (AI-Q, NemoClaw, Zep, Simulator)
Ready for copy-paste production use.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class WorkflowTemplates:
    """
    Pre-built workflow templates for all business lifecycle scenarios.

    Templates:
    1. Rapid Validation Template - Fast market validation (2-3 weeks)
    2. MVP Build Template - Structured MVP development (4-8 weeks)
    3. Growth Scaling Template - Systematic growth scaling (8-12 weeks)
    4. Operational Maintenance Template - Steady-state operations
    5. Optimization Template - Performance/cost optimization cycles
    6. Shutdown Template - Graceful business termination
    7. AI-Driven Planning Template - AI-Q powered strategic planning
    8. Fallback Patterns Template - Resilient execution with fallbacks
    """

    def __init__(self):
        """Initialize workflow templates."""
        self.templates = {
            "rapid_validation": self.rapid_validation_template,
            "mvp_build": self.mvp_build_template,
            "growth_scaling": self.growth_scaling_template,
            "operational_maintenance": self.operational_maintenance_template,
            "optimization": self.optimization_template,
            "shutdown": self.shutdown_template,
            "ai_driven_planning": self.ai_driven_planning_template,
            "fallback_patterns": self.fallback_patterns_template
        }

    # ========================================================================
    # TEMPLATE 1: RAPID VALIDATION
    # ========================================================================

    def rapid_validation_template(self, business: Dict) -> Dict:
        """
        Rapid Validation Template (2-3 weeks)

        Aggressive market validation with AI-Q reasoning and Simulator predictions.
        Optimized for speed - validate or kill fast.

        Tools used:
        - AI-Q: Market opportunity reasoning
        - Simulator: Success probability predictions
        - Zep: Store validation insights for future reference

        Args:
            business: Business dictionary

        Returns:
            Workflow configuration
        """
        idea = business["opportunity"]["idea"]

        return {
            "template_name": "rapid_validation",
            "duration_estimate": "2-3 weeks",
            "stages": ["DISCOVERED", "VALIDATING"],
            "description": "Fast-track validation to determine market viability",
            "phases": [
                {
                    "phase_id": "discovery_sprint",
                    "duration": "3-5 days",
                    "tasks": [
                        {
                            "task_id": "rapid_1",
                            "title": f"AI-Q Market Opportunity Analysis: {idea[:35]}",
                            "description": "Use AI-Q to analyze market opportunity and size",
                            "tools": ["ai_q"],
                            "priority": "high",
                            "expected_duration": "1 day",
                            "success_criteria": {
                                "opportunity_score": ">0.65",
                                "market_size": "defined",
                                "ai_q_confidence": ">0.75"
                            },
                            "execution_config": {
                                "use_ai_q": True,
                                "ai_q_mode": "market_analysis",
                                "store_in_zep": True
                            }
                        },
                        {
                            "task_id": "rapid_2",
                            "title": f"Competitive Intelligence Scan: {idea[:35]}",
                            "description": "Rapid competitive landscape analysis",
                            "tools": ["research", "simulator"],
                            "priority": "high",
                            "expected_duration": "1 day",
                            "success_criteria": {
                                "competitors_identified": ">=3",
                                "differentiation_found": True
                            },
                            "execution_config": {
                                "use_simulator": True,
                                "simulate_competitive_response": True
                            }
                        },
                        {
                            "task_id": "rapid_3",
                            "title": f"Problem-Solution Fit Quick Test: {idea[:35]}",
                            "description": "Validate problem severity and solution fit",
                            "tools": ["research", "zep"],
                            "priority": "high",
                            "expected_duration": "2 days",
                            "success_criteria": {
                                "problem_validated": True,
                                "solution_fit_score": ">0.70"
                            },
                            "execution_config": {
                                "interview_count": "8-10",
                                "store_in_zep": True,
                                "zep_namespace": "validation_insights"
                            }
                        }
                    ]
                },
                {
                    "phase_id": "validation_sprint",
                    "duration": "5-7 days",
                    "tasks": [
                        {
                            "task_id": "rapid_4",
                            "title": f"Customer Willingness-to-Pay Research: {idea[:35]}",
                            "description": "Rapid pricing validation with target customers",
                            "tools": ["research"],
                            "priority": "high",
                            "expected_duration": "2 days",
                            "success_criteria": {
                                "pricing_validated": True,
                                "willingness_to_pay": "defined"
                            }
                        },
                        {
                            "task_id": "rapid_5",
                            "title": f"MVP Scope Definition: {idea[:35]}",
                            "description": "Define minimum viable product scope",
                            "tools": ["planning", "ai_q"],
                            "priority": "high",
                            "expected_duration": "1 day",
                            "success_criteria": {
                                "mvp_features_defined": True,
                                "build_estimate": "defined"
                            },
                            "execution_config": {
                                "use_ai_q": True,
                                "ai_q_mode": "feature_prioritization"
                            }
                        },
                        {
                            "task_id": "rapid_6",
                            "title": f"Build/No-Build Decision: {idea[:35]}",
                            "description": "Make final go/no-go decision based on validation",
                            "tools": ["ai_q", "simulator"],
                            "priority": "high",
                            "expected_duration": "1 day",
                            "success_criteria": {
                                "decision_made": True,
                                "confidence": ">0.75"
                            },
                            "execution_config": {
                                "use_ai_q": True,
                                "ai_q_mode": "decision_analysis",
                                "use_simulator": True,
                                "simulate_outcomes": True,
                                "store_decision_in_zep": True
                            }
                        }
                    ]
                }
            ],
            "success_criteria": {
                "validation_score": ">0.65",
                "decision_confidence": ">0.75",
                "time_to_decision": "<3 weeks"
            },
            "next_template": {
                "if_go": "mvp_build",
                "if_no_go": "shutdown"
            }
        }

    # ========================================================================
    # TEMPLATE 2: MVP BUILD
    # ========================================================================

    def mvp_build_template(self, business: Dict) -> Dict:
        """
        MVP Build Template (4-8 weeks)

        Structured MVP development with NemoClaw sandboxing and continuous testing.

        Tools used:
        - NemoClaw: Sandboxed development environment
        - Simulator: Feature impact predictions
        - Zep: Store development patterns and learnings
        - AI-Q: Technical decision guidance

        Args:
            business: Business dictionary

        Returns:
            Workflow configuration
        """
        idea = business["opportunity"]["idea"]

        return {
            "template_name": "mvp_build",
            "duration_estimate": "4-8 weeks",
            "stages": ["BUILDING"],
            "description": "Structured MVP development with quality gates",
            "phases": [
                {
                    "phase_id": "architecture_phase",
                    "duration": "3-5 days",
                    "tasks": [
                        {
                            "task_id": "mvp_1",
                            "title": f"Technical Architecture Design: {idea[:35]}",
                            "description": "Design system architecture with AI-Q guidance",
                            "tools": ["builder", "ai_q"],
                            "priority": "high",
                            "expected_duration": "2 days",
                            "success_criteria": {
                                "architecture_documented": True,
                                "tech_stack_defined": True,
                                "scalability_plan": "defined"
                            },
                            "execution_config": {
                                "use_ai_q": True,
                                "ai_q_mode": "architecture_review",
                                "store_in_zep": True,
                                "zep_namespace": "architecture_patterns"
                            }
                        },
                        {
                            "task_id": "mvp_2",
                            "title": f"NemoClaw Sandbox Setup: {idea[:35]}",
                            "description": "Initialize NemoClaw development sandbox",
                            "tools": ["nemoclaw"],
                            "priority": "high",
                            "expected_duration": "1 day",
                            "success_criteria": {
                                "sandbox_initialized": True,
                                "ci_cd_setup": True
                            },
                            "execution_config": {
                                "use_nemoclaw": True,
                                "sandbox_config": {
                                    "isolation_level": "full",
                                    "resource_limits": "standard"
                                }
                            }
                        }
                    ]
                },
                {
                    "phase_id": "development_sprint_1",
                    "duration": "1-2 weeks",
                    "tasks": [
                        {
                            "task_id": "mvp_3",
                            "title": f"Core Features Development Sprint 1: {idea[:35]}",
                            "description": "Develop authentication and core infrastructure",
                            "tools": ["builder", "nemoclaw"],
                            "priority": "high",
                            "expected_duration": "1 week",
                            "success_criteria": {
                                "features_completed": ">=80%",
                                "tests_passing": True,
                                "code_quality": ">0.75"
                            },
                            "execution_config": {
                                "use_nemoclaw": True,
                                "run_in_sandbox": True,
                                "continuous_testing": True
                            }
                        },
                        {
                            "task_id": "mvp_4",
                            "title": f"Feature Impact Simulation: {idea[:35]}",
                            "description": "Simulate feature impact before deployment",
                            "tools": ["simulator"],
                            "priority": "medium",
                            "expected_duration": "1 day",
                            "success_criteria": {
                                "simulation_confidence": ">0.75"
                            },
                            "execution_config": {
                                "use_simulator": True,
                                "simulate_user_behavior": True,
                                "simulate_load": True
                            }
                        }
                    ]
                },
                {
                    "phase_id": "development_sprint_2",
                    "duration": "1-2 weeks",
                    "tasks": [
                        {
                            "task_id": "mvp_5",
                            "title": f"Core Features Development Sprint 2: {idea[:35]}",
                            "description": "Complete core MVP features",
                            "tools": ["builder", "nemoclaw"],
                            "priority": "high",
                            "expected_duration": "1 week",
                            "success_criteria": {
                                "mvp_complete": True,
                                "all_tests_passing": True
                            },
                            "execution_config": {
                                "use_nemoclaw": True,
                                "run_in_sandbox": True
                            }
                        },
                        {
                            "task_id": "mvp_6",
                            "title": f"QA and Testing: {idea[:35]}",
                            "description": "Comprehensive testing in NemoClaw sandbox",
                            "tools": ["nemoclaw", "simulator"],
                            "priority": "high",
                            "expected_duration": "3 days",
                            "success_criteria": {
                                "test_coverage": ">80%",
                                "critical_bugs": "0",
                                "performance": "acceptable"
                            },
                            "execution_config": {
                                "use_nemoclaw": True,
                                "use_simulator": True,
                                "simulate_edge_cases": True
                            }
                        }
                    ]
                },
                {
                    "phase_id": "beta_phase",
                    "duration": "1-2 weeks",
                    "tasks": [
                        {
                            "task_id": "mvp_7",
                            "title": f"Beta User Onboarding: {idea[:35]}",
                            "description": "Onboard beta users and collect feedback",
                            "tools": ["automation", "zep"],
                            "priority": "medium",
                            "expected_duration": "1 week",
                            "success_criteria": {
                                "beta_users": ">=15",
                                "feedback_collected": True
                            },
                            "execution_config": {
                                "store_feedback_in_zep": True,
                                "zep_namespace": "beta_feedback"
                            }
                        },
                        {
                            "task_id": "mvp_8",
                            "title": f"Production Readiness Review: {idea[:35]}",
                            "description": "Final readiness check with AI-Q",
                            "tools": ["ai_q", "simulator"],
                            "priority": "high",
                            "expected_duration": "2 days",
                            "success_criteria": {
                                "readiness_score": ">0.85",
                                "deployment_plan": "approved"
                            },
                            "execution_config": {
                                "use_ai_q": True,
                                "ai_q_mode": "readiness_assessment",
                                "use_simulator": True,
                                "simulate_production_load": True
                            }
                        }
                    ]
                }
            ],
            "success_criteria": {
                "mvp_completed": True,
                "quality_score": ">0.80",
                "beta_feedback_positive": ">70%",
                "ready_for_production": True
            },
            "next_template": "growth_scaling"
        }

    # ========================================================================
    # TEMPLATE 3: GROWTH SCALING
    # ========================================================================

    def growth_scaling_template(self, business: Dict) -> Dict:
        """
        Growth Scaling Template (8-12 weeks)

        Systematic growth with AI-Q marketing optimization and performance monitoring.

        Tools used:
        - AI-Q: Growth strategy optimization
        - Simulator: Campaign performance predictions
        - Zep: Store growth patterns and successful tactics

        Args:
            business: Business dictionary

        Returns:
            Workflow configuration
        """
        idea = business["opportunity"]["idea"]

        return {
            "template_name": "growth_scaling",
            "duration_estimate": "8-12 weeks",
            "stages": ["SCALING"],
            "description": "Systematic growth scaling with performance optimization",
            "phases": [
                {
                    "phase_id": "growth_foundation",
                    "duration": "2 weeks",
                    "tasks": [
                        {
                            "task_id": "growth_1",
                            "title": f"AI-Q Growth Strategy: {idea[:35]}",
                            "description": "Develop AI-optimized growth strategy",
                            "tools": ["ai_q", "content"],
                            "priority": "high",
                            "expected_duration": "3 days",
                            "success_criteria": {
                                "strategy_defined": True,
                                "channels_identified": ">=3",
                                "cac_target": "defined"
                            },
                            "execution_config": {
                                "use_ai_q": True,
                                "ai_q_mode": "growth_optimization",
                                "analyze_market_dynamics": True,
                                "store_in_zep": True
                            }
                        },
                        {
                            "task_id": "growth_2",
                            "title": f"Performance Baseline Establishment: {idea[:35]}",
                            "description": "Establish performance baselines and KPIs",
                            "tools": ["automation"],
                            "priority": "high",
                            "expected_duration": "2 days",
                            "success_criteria": {
                                "kpis_defined": True,
                                "monitoring_setup": True
                            }
                        },
                        {
                            "task_id": "growth_3",
                            "title": f"Infrastructure Scaling Prep: {idea[:35]}",
                            "description": "Prepare infrastructure for increased load",
                            "tools": ["builder", "simulator"],
                            "priority": "high",
                            "expected_duration": "3 days",
                            "success_criteria": {
                                "auto_scaling_enabled": True,
                                "load_tested": True
                            },
                            "execution_config": {
                                "use_simulator": True,
                                "simulate_10x_load": True
                            }
                        }
                    ]
                },
                {
                    "phase_id": "growth_execution",
                    "duration": "4-6 weeks",
                    "tasks": [
                        {
                            "task_id": "growth_4",
                            "title": f"Campaign Launch Wave 1: {idea[:35]}",
                            "description": "Launch initial growth campaigns",
                            "tools": ["content", "automation"],
                            "priority": "high",
                            "expected_duration": "2 weeks",
                            "success_criteria": {
                                "campaigns_live": ">=3",
                                "cac": "<target",
                                "conversion_rate": "defined"
                            }
                        },
                        {
                            "task_id": "growth_5",
                            "title": f"Performance Optimization Loop: {idea[:35]}",
                            "description": "Continuous performance monitoring and optimization",
                            "tools": ["automation", "ai_q"],
                            "priority": "high",
                            "expected_duration": "ongoing",
                            "success_criteria": {
                                "uptime": ">99.5%",
                                "response_time": "<500ms",
                                "error_rate": "<1%"
                            },
                            "execution_config": {
                                "use_ai_q": True,
                                "ai_q_mode": "performance_optimization",
                                "continuous_monitoring": True
                            }
                        },
                        {
                            "task_id": "growth_6",
                            "title": f"User Acquisition Scaling: {idea[:35]}",
                            "description": "Scale successful acquisition channels",
                            "tools": ["automation", "simulator"],
                            "priority": "high",
                            "expected_duration": "4 weeks",
                            "success_criteria": {
                                "user_growth": ">20% weekly",
                                "cac_payback": "<6 months"
                            },
                            "execution_config": {
                                "use_simulator": True,
                                "simulate_scaling_scenarios": True,
                                "store_learnings_in_zep": True
                            }
                        }
                    ]
                },
                {
                    "phase_id": "growth_optimization",
                    "duration": "2 weeks",
                    "tasks": [
                        {
                            "task_id": "growth_7",
                            "title": f"Retention Program Launch: {idea[:35]}",
                            "description": "Implement customer retention initiatives",
                            "tools": ["content", "automation"],
                            "priority": "medium",
                            "expected_duration": "1 week",
                            "success_criteria": {
                                "retention_program_live": True,
                                "churn_rate": "decreasing"
                            }
                        },
                        {
                            "task_id": "growth_8",
                            "title": f"Scaling Readiness Assessment: {idea[:35]}",
                            "description": "Assess readiness for operations stage",
                            "tools": ["ai_q", "planning"],
                            "priority": "high",
                            "expected_duration": "2 days",
                            "success_criteria": {
                                "scaling_success": True,
                                "ready_for_operations": True
                            },
                            "execution_config": {
                                "use_ai_q": True,
                                "ai_q_mode": "stage_transition_analysis"
                            }
                        }
                    ]
                }
            ],
            "success_criteria": {
                "user_growth": ">200%",
                "performance_stable": True,
                "cac_payback": "<6 months",
                "ready_for_operations": True
            },
            "next_template": "operational_maintenance"
        }

    # ========================================================================
    # TEMPLATE 4: OPERATIONAL MAINTENANCE
    # ========================================================================

    def operational_maintenance_template(self, business: Dict) -> Dict:
        """
        Operational Maintenance Template (Ongoing)

        Steady-state operations with automated monitoring and periodic optimization.

        Tools used:
        - Automation: Continuous monitoring and alerting
        - Zep: Store operational patterns and incident learnings
        - Simulator: Predict potential issues

        Args:
            business: Business dictionary

        Returns:
            Workflow configuration
        """
        idea = business["opportunity"]["idea"]

        return {
            "template_name": "operational_maintenance",
            "duration_estimate": "ongoing",
            "stages": ["OPERATING"],
            "description": "Steady-state operations with proactive maintenance",
            "task_frequency": "weekly",
            "tasks": [
                {
                    "task_id": "ops_1",
                    "title": f"Operations Health Check: {idea[:35]}",
                    "description": "Weekly operations health monitoring",
                    "tools": ["automation"],
                    "priority": "high",
                    "frequency": "weekly",
                    "success_criteria": {
                        "uptime": ">99.9%",
                        "active_incidents": "0",
                        "performance": "stable"
                    },
                    "execution_config": {
                        "automated_monitoring": True,
                        "alert_on_anomalies": True
                    }
                },
                {
                    "task_id": "ops_2",
                    "title": f"Revenue Optimization Review: {idea[:35]}",
                    "description": "Weekly revenue and pricing optimization",
                    "tools": ["planning", "automation"],
                    "priority": "high",
                    "frequency": "weekly",
                    "success_criteria": {
                        "mrr_growth": ">=0%",
                        "churn_rate": "<5%"
                    }
                },
                {
                    "task_id": "ops_3",
                    "title": f"Customer Support Quality: {idea[:35]}",
                    "description": "Monitor and optimize customer support",
                    "tools": ["content", "automation"],
                    "priority": "medium",
                    "frequency": "weekly",
                    "success_criteria": {
                        "response_time": "<8 hours",
                        "satisfaction_score": ">4.0"
                    }
                },
                {
                    "task_id": "ops_4",
                    "title": f"System Maintenance: {idea[:35]}",
                    "description": "Regular system maintenance and updates",
                    "tools": ["builder", "automation"],
                    "priority": "medium",
                    "frequency": "bi-weekly",
                    "success_criteria": {
                        "security_patches_applied": True,
                        "system_health": ">0.90"
                    },
                    "execution_config": {
                        "store_maintenance_log_in_zep": True
                    }
                },
                {
                    "task_id": "ops_5",
                    "title": f"Predictive Issue Detection: {idea[:35]}",
                    "description": "Use Simulator to predict potential issues",
                    "tools": ["simulator"],
                    "priority": "medium",
                    "frequency": "weekly",
                    "success_criteria": {
                        "predictions_generated": True,
                        "preventive_actions_taken": "as_needed"
                    },
                    "execution_config": {
                        "use_simulator": True,
                        "predict_failure_modes": True,
                        "simulate_load_patterns": True
                    }
                }
            ],
            "success_criteria": {
                "uptime": ">99.9%",
                "customer_satisfaction": ">4.0",
                "mrr_stable_or_growing": True
            },
            "escalation_triggers": {
                "performance_drop": {
                    "threshold": "<0.65",
                    "action": "transition_to_optimization"
                },
                "incident_rate": {
                    "threshold": ">5 per week",
                    "action": "deep_dive_analysis"
                }
            },
            "next_template": {
                "if_performance_drops": "optimization",
                "if_stable": "continue"
            }
        }

    # ========================================================================
    # TEMPLATE 5: OPTIMIZATION
    # ========================================================================

    def optimization_template(self, business: Dict) -> Dict:
        """
        Optimization Template (2-4 weeks)

        Focused optimization cycles for performance, cost, or user experience improvements.

        Tools used:
        - AI-Q: Optimization strategy
        - Simulator: Impact predictions
        - NemoClaw: Safe testing environment
        - Zep: Store optimization learnings

        Args:
            business: Business dictionary

        Returns:
            Workflow configuration
        """
        idea = business["opportunity"]["idea"]

        return {
            "template_name": "optimization",
            "duration_estimate": "2-4 weeks",
            "stages": ["OPTIMIZING"],
            "description": "Focused optimization for performance, cost, or UX",
            "phases": [
                {
                    "phase_id": "analysis",
                    "duration": "3-5 days",
                    "tasks": [
                        {
                            "task_id": "opt_1",
                            "title": f"AI-Q Optimization Analysis: {idea[:35]}",
                            "description": "Use AI-Q to identify optimization opportunities",
                            "tools": ["ai_q"],
                            "priority": "high",
                            "expected_duration": "2 days",
                            "success_criteria": {
                                "opportunities_identified": ">=3",
                                "impact_quantified": True
                            },
                            "execution_config": {
                                "use_ai_q": True,
                                "ai_q_mode": "bottleneck_analysis",
                                "analyze_cost": True,
                                "analyze_performance": True,
                                "analyze_ux": True
                            }
                        },
                        {
                            "task_id": "opt_2",
                            "title": f"Optimization Impact Simulation: {idea[:35]}",
                            "description": "Simulate impact of proposed optimizations",
                            "tools": ["simulator"],
                            "priority": "high",
                            "expected_duration": "1 day",
                            "success_criteria": {
                                "simulation_confidence": ">0.75",
                                "roi_estimated": True
                            },
                            "execution_config": {
                                "use_simulator": True,
                                "simulate_before_after": True
                            }
                        }
                    ]
                },
                {
                    "phase_id": "implementation",
                    "duration": "1-2 weeks",
                    "tasks": [
                        {
                            "task_id": "opt_3",
                            "title": f"Performance Optimizations: {idea[:35]}",
                            "description": "Implement performance improvements",
                            "tools": ["builder", "nemoclaw"],
                            "priority": "high",
                            "expected_duration": "1 week",
                            "success_criteria": {
                                "performance_improvement": ">20%",
                                "no_regressions": True
                            },
                            "execution_config": {
                                "use_nemoclaw": True,
                                "test_in_sandbox": True,
                                "before_after_metrics": True
                            }
                        },
                        {
                            "task_id": "opt_4",
                            "title": f"Cost Optimizations: {idea[:35]}",
                            "description": "Optimize infrastructure and operational costs",
                            "tools": ["automation", "builder"],
                            "priority": "medium",
                            "expected_duration": "3 days",
                            "success_criteria": {
                                "cost_reduction": ">15%",
                                "performance_maintained": True
                            }
                        },
                        {
                            "task_id": "opt_5",
                            "title": f"UX Improvements: {idea[:35]}",
                            "description": "Implement user experience improvements",
                            "tools": ["content", "simulator"],
                            "priority": "medium",
                            "expected_duration": "3 days",
                            "success_criteria": {
                                "user_satisfaction_increase": ">10%",
                                "task_completion_rate_increase": ">15%"
                            },
                            "execution_config": {
                                "use_simulator": True,
                                "simulate_user_flows": True
                            }
                        }
                    ]
                },
                {
                    "phase_id": "validation",
                    "duration": "3-5 days",
                    "tasks": [
                        {
                            "task_id": "opt_6",
                            "title": f"Optimization Results Validation: {idea[:35]}",
                            "description": "Validate optimization improvements",
                            "tools": ["automation", "ai_q"],
                            "priority": "high",
                            "expected_duration": "3 days",
                            "success_criteria": {
                                "improvements_verified": True,
                                "no_negative_impacts": True
                            },
                            "execution_config": {
                                "use_ai_q": True,
                                "ai_q_mode": "results_validation",
                                "store_learnings_in_zep": True,
                                "zep_namespace": "optimization_patterns"
                            }
                        }
                    ]
                }
            ],
            "success_criteria": {
                "performance_improved": ">15%",
                "cost_reduced": ">10%",
                "user_satisfaction_improved": ">10%",
                "ready_to_resume_operations": True
            },
            "next_template": "operational_maintenance"
        }

    # ========================================================================
    # TEMPLATE 6: SHUTDOWN
    # ========================================================================

    def shutdown_template(self, business: Dict) -> Dict:
        """
        Shutdown Template (1-2 weeks)

        Graceful business termination with knowledge preservation.

        Tools used:
        - Zep: Comprehensive lessons learned storage
        - Automation: Resource cleanup

        Args:
            business: Business dictionary

        Returns:
            Workflow configuration
        """
        idea = business["opportunity"]["idea"]
        termination_reason = business.get("termination_reason", "Unknown")

        return {
            "template_name": "shutdown",
            "duration_estimate": "1-2 weeks",
            "stages": ["TERMINATED"],
            "description": "Graceful shutdown with knowledge preservation",
            "termination_reason": termination_reason,
            "tasks": [
                {
                    "task_id": "shutdown_1",
                    "title": f"Comprehensive Final Report: {idea[:35]}",
                    "description": "Generate detailed final business report",
                    "tools": ["planning"],
                    "priority": "high",
                    "expected_duration": "2 days",
                    "success_criteria": {
                        "report_completed": True,
                        "all_metrics_documented": True
                    }
                },
                {
                    "task_id": "shutdown_2",
                    "title": f"Lessons Learned Deep Dive: {idea[:35]}",
                    "description": "Document comprehensive lessons learned",
                    "tools": ["planning", "zep"],
                    "priority": "high",
                    "expected_duration": "2 days",
                    "success_criteria": {
                        "lessons_documented": True,
                        "root_cause_identified": True
                    },
                    "execution_config": {
                        "store_in_zep": True,
                        "zep_namespace": "lessons_learned",
                        "include_what_worked": True,
                        "include_what_failed": True,
                        "include_recommendations": True
                    }
                },
                {
                    "task_id": "shutdown_3",
                    "title": f"Data and Asset Archival: {idea[:35]}",
                    "description": "Archive all data and assets for future reference",
                    "tools": ["automation"],
                    "priority": "medium",
                    "expected_duration": "3 days",
                    "success_criteria": {
                        "data_archived": True,
                        "retention_period_set": True
                    }
                },
                {
                    "task_id": "shutdown_4",
                    "title": f"Resource Deallocation: {idea[:35]}",
                    "description": "Deallocate all resources and cleanup systems",
                    "tools": ["automation"],
                    "priority": "high",
                    "expected_duration": "2 days",
                    "success_criteria": {
                        "resources_deallocated": True,
                        "cost_eliminated": True,
                        "cleanup_verified": True
                    }
                },
                {
                    "task_id": "shutdown_5",
                    "title": f"Knowledge Transfer to Zep: {idea[:35]}",
                    "description": "Transfer all valuable knowledge to Zep for future businesses",
                    "tools": ["zep"],
                    "priority": "high",
                    "expected_duration": "1 day",
                    "success_criteria": {
                        "knowledge_transferred": True,
                        "searchable_in_zep": True
                    },
                    "execution_config": {
                        "store_in_zep": True,
                        "zep_namespaces": [
                            "lessons_learned",
                            "what_worked",
                            "failure_patterns",
                            "market_insights"
                        ],
                        "enable_future_retrieval": True
                    }
                }
            ],
            "success_criteria": {
                "all_tasks_completed": True,
                "knowledge_preserved": True,
                "resources_deallocated": True,
                "cost_eliminated": True
            },
            "post_shutdown_actions": {
                "zep_retrieval_ready": True,
                "lessons_available_for_new_businesses": True
            }
        }

    # ========================================================================
    # TEMPLATE 7: AI-DRIVEN PLANNING
    # ========================================================================

    def ai_driven_planning_template(self, business: Dict) -> Dict:
        """
        AI-Driven Planning Template (1 week)

        Use AI-Q for strategic planning and decision-making.
        Can be applied at any stage for strategic guidance.

        Tools used:
        - AI-Q: Strategic reasoning and planning
        - Simulator: Scenario planning
        - Zep: Store strategic insights

        Args:
            business: Business dictionary

        Returns:
            Workflow configuration
        """
        idea = business["opportunity"]["idea"]
        current_stage = business.get("stage", "UNKNOWN")

        return {
            "template_name": "ai_driven_planning",
            "duration_estimate": "1 week",
            "stages": ["ANY"],
            "description": "AI-Q powered strategic planning and decision-making",
            "applicable_stages": "all",
            "tasks": [
                {
                    "task_id": "ai_plan_1",
                    "title": f"AI-Q Strategic Analysis: {idea[:35]}",
                    "description": f"Deep strategic analysis for {current_stage} stage",
                    "tools": ["ai_q"],
                    "priority": "high",
                    "expected_duration": "1 day",
                    "success_criteria": {
                        "strategic_options_identified": ">=3",
                        "confidence_score": ">0.75"
                    },
                    "execution_config": {
                        "use_ai_q": True,
                        "ai_q_mode": "strategic_planning",
                        "current_stage": current_stage,
                        "analyze_opportunities": True,
                        "analyze_threats": True,
                        "analyze_competitive_position": True
                    }
                },
                {
                    "task_id": "ai_plan_2",
                    "title": f"Scenario Simulation: {idea[:35]}",
                    "description": "Simulate multiple strategic scenarios",
                    "tools": ["simulator", "ai_q"],
                    "priority": "high",
                    "expected_duration": "2 days",
                    "success_criteria": {
                        "scenarios_simulated": ">=3",
                        "best_path_identified": True
                    },
                    "execution_config": {
                        "use_simulator": True,
                        "use_ai_q": True,
                        "simulate_optimistic_scenario": True,
                        "simulate_realistic_scenario": True,
                        "simulate_pessimistic_scenario": True,
                        "compare_outcomes": True
                    }
                },
                {
                    "task_id": "ai_plan_3",
                    "title": f"Decision Recommendation: {idea[:35]}",
                    "description": "AI-Q generated decision recommendation",
                    "tools": ["ai_q"],
                    "priority": "high",
                    "expected_duration": "1 day",
                    "success_criteria": {
                        "recommendation_generated": True,
                        "reasoning_clear": True,
                        "confidence": ">0.80"
                    },
                    "execution_config": {
                        "use_ai_q": True,
                        "ai_q_mode": "decision_recommendation",
                        "include_risks": True,
                        "include_opportunities": True,
                        "include_action_plan": True
                    }
                },
                {
                    "task_id": "ai_plan_4",
                    "title": f"Strategic Knowledge Storage: {idea[:35]}",
                    "description": "Store strategic insights in Zep for future reference",
                    "tools": ["zep"],
                    "priority": "medium",
                    "expected_duration": "0.5 days",
                    "success_criteria": {
                        "insights_stored": True,
                        "retrievable": True
                    },
                    "execution_config": {
                        "store_in_zep": True,
                        "zep_namespace": "strategic_insights",
                        "include_decision_rationale": True
                    }
                }
            ],
            "success_criteria": {
                "strategic_direction_clear": True,
                "decision_confidence": ">0.80",
                "action_plan_defined": True
            },
            "use_cases": [
                "Before major stage transitions",
                "When facing strategic uncertainty",
                "For quarterly planning",
                "When performance metrics decline"
            ]
        }

    # ========================================================================
    # TEMPLATE 8: FALLBACK PATTERNS
    # ========================================================================

    def fallback_patterns_template(self, business: Dict) -> Dict:
        """
        Fallback Patterns Template

        Resilient execution patterns with graceful degradation.
        Used when tools are unavailable or tasks fail.

        Tools used:
        - All tools with fallback strategies
        - Simulator: Always available (built-in)

        Args:
            business: Business dictionary

        Returns:
            Workflow configuration with fallback strategies
        """
        return {
            "template_name": "fallback_patterns",
            "description": "Resilient execution with graceful degradation",
            "applicable_stages": "all",
            "fallback_strategies": {
                "ai_q_unavailable": {
                    "fallback": "Use Simulator for basic reasoning",
                    "degradation": "Lower confidence in strategic decisions",
                    "action": "Proceed with caution, implement more validation steps"
                },
                "nemoclaw_unavailable": {
                    "fallback": "Execute in standard environment with extra testing",
                    "degradation": "Reduced isolation, higher risk",
                    "action": "Implement comprehensive testing and staged rollout"
                },
                "zep_unavailable": {
                    "fallback": "Store insights locally in execution history",
                    "degradation": "No cross-session memory",
                    "action": "Document learnings in local files for manual review"
                },
                "simulator_unavailable": {
                    "fallback": "Simulator is always available (built-in)",
                    "degradation": "N/A",
                    "action": "N/A"
                }
            },
            "execution_patterns": {
                "optimistic_execution": {
                    "description": "Assume tools are available, fail fast if not",
                    "use_case": "Development/testing environments",
                    "error_handling": "Immediate failure with clear error message"
                },
                "pessimistic_execution": {
                    "description": "Check all tool availability before execution",
                    "use_case": "Production environments",
                    "error_handling": "Graceful degradation to fallback"
                },
                "adaptive_execution": {
                    "description": "Try primary tool, fallback on failure",
                    "use_case": "Most common pattern",
                    "error_handling": "Automatic fallback with logging"
                }
            },
            "retry_strategies": {
                "exponential_backoff": {
                    "initial_delay": "1 second",
                    "max_delay": "60 seconds",
                    "max_retries": 3,
                    "use_for": ["API calls", "External services"]
                },
                "immediate_retry": {
                    "max_retries": 2,
                    "use_for": ["Transient failures", "Network blips"]
                },
                "no_retry": {
                    "use_for": ["Validation errors", "Business logic errors"]
                }
            },
            "circuit_breaker": {
                "enabled": True,
                "failure_threshold": 5,
                "timeout": "30 seconds",
                "reset_after": "60 seconds",
                "description": "Prevent cascading failures by stopping calls to failing services"
            },
            "monitoring_and_alerting": {
                "log_all_fallbacks": True,
                "alert_on_repeated_fallbacks": True,
                "fallback_threshold": 3,
                "alert_channels": ["logs", "monitoring_dashboard"]
            }
        }

    # ========================================================================
    # Template Utilities
    # ========================================================================

    def get_template(self, template_name: str, business: Dict) -> Optional[Dict]:
        """
        Get a workflow template by name.

        Args:
            template_name: Template name
            business: Business dictionary

        Returns:
            Template configuration or None
        """
        template_func = self.templates.get(template_name)

        if template_func:
            return template_func(business)
        else:
            return None

    def list_templates(self) -> List[Dict]:
        """
        List all available templates.

        Returns:
            List of template metadata
        """
        return [
            {
                "name": "rapid_validation",
                "description": "Fast market validation (2-3 weeks)",
                "stages": ["DISCOVERED", "VALIDATING"],
                "tools": ["ai_q", "simulator", "zep"]
            },
            {
                "name": "mvp_build",
                "description": "Structured MVP development (4-8 weeks)",
                "stages": ["BUILDING"],
                "tools": ["nemoclaw", "simulator", "zep", "ai_q"]
            },
            {
                "name": "growth_scaling",
                "description": "Systematic growth scaling (8-12 weeks)",
                "stages": ["SCALING"],
                "tools": ["ai_q", "simulator", "zep"]
            },
            {
                "name": "operational_maintenance",
                "description": "Steady-state operations (ongoing)",
                "stages": ["OPERATING"],
                "tools": ["automation", "zep", "simulator"]
            },
            {
                "name": "optimization",
                "description": "Performance/cost optimization (2-4 weeks)",
                "stages": ["OPTIMIZING"],
                "tools": ["ai_q", "simulator", "nemoclaw", "zep"]
            },
            {
                "name": "shutdown",
                "description": "Graceful termination (1-2 weeks)",
                "stages": ["TERMINATED"],
                "tools": ["zep", "automation"]
            },
            {
                "name": "ai_driven_planning",
                "description": "Strategic planning (1 week)",
                "stages": ["ANY"],
                "tools": ["ai_q", "simulator", "zep"]
            },
            {
                "name": "fallback_patterns",
                "description": "Resilient execution patterns",
                "stages": ["ANY"],
                "tools": ["all_with_fallbacks"]
            }
        ]

    def recommend_template(self, business: Dict) -> Dict:
        """
        Recommend the best template for a business based on its current state.

        Args:
            business: Business dictionary

        Returns:
            Recommendation dictionary with template name and reasoning
        """
        stage = business.get("stage", "UNKNOWN")
        performance = business.get("metrics", {}).get("performance", 0.5)

        # Stage-based recommendations
        stage_templates = {
            "DISCOVERED": "rapid_validation",
            "VALIDATING": "rapid_validation",
            "BUILDING": "mvp_build",
            "SCALING": "growth_scaling",
            "OPERATING": "operational_maintenance",
            "OPTIMIZING": "optimization",
            "TERMINATED": "shutdown"
        }

        recommended_template = stage_templates.get(stage, "ai_driven_planning")

        # Performance-based overrides
        if stage == "OPERATING" and performance < 0.65:
            recommended_template = "optimization"

        # Get template details
        template = self.get_template(recommended_template, business)

        return {
            "recommended_template": recommended_template,
            "reasoning": f"Business is in {stage} stage with performance {performance:.2f}",
            "template_details": template,
            "alternatives": self._get_alternative_templates(stage, performance)
        }

    def _get_alternative_templates(self, stage: str, performance: float) -> List[str]:
        """Get alternative templates that might be applicable."""
        alternatives = ["ai_driven_planning", "fallback_patterns"]

        if stage == "OPERATING" and performance > 0.80:
            alternatives.append("growth_scaling")

        return alternatives
