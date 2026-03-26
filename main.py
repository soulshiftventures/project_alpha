#!/usr/bin/env python3
"""
Project Alpha - AI-Powered Business Lifecycle Engine
Manages multiple businesses through their complete lifecycle
"""

import sys
import time
from project_alpha.core.research_engine import ResearchEngine
from project_alpha.core.planning_engine import PlanningEngine
from project_alpha.core.state_manager import StateManager
from project_alpha.core.execution_engine import ExecutionEngine
from project_alpha.core.result_collector import ResultCollector
from project_alpha.core.evaluation_engine import EvaluationEngine
from project_alpha.core.memory import Memory
from project_alpha.core.ai_client import AIClient
from project_alpha.core.lifecycle_manager import LifecycleManager
from project_alpha.core.portfolio_manager import PortfolioManager

# Phase 5 imports
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.portfolio_workflows import PortfolioWorkflows
from project_alpha.core.workflow_validator import WorkflowValidator


def print_banner():
    """Print system banner."""
    print("\n" + "=" * 70)
    print(" PROJECT ALPHA - BUSINESS LIFECYCLE ENGINE")
    print(" Continuous Portfolio Management System - Phase 5")
    print(" Integrated Workflow Orchestration")
    print("=" * 70 + "\n")


def extract_metrics_from_result(output: dict, stage: str) -> dict:
    """Extract metrics from task output based on stage."""
    metrics = {}

    if stage == "VALIDATING":
        metrics["validation_score"] = calculate_validation_score(output)
    elif stage == "BUILDING":
        metrics["build_progress"] = calculate_build_progress(output)
    elif stage == "SCALING":
        metrics["performance"] = calculate_performance(output)
        metrics["stability"] = calculate_stability(output)
    elif stage == "OPERATING":
        metrics["stability"] = calculate_stability(output)
    elif stage == "OPTIMIZING":
        metrics["performance"] = calculate_performance(output)

    return metrics


def calculate_validation_score(output: dict) -> float:
    """Calculate validation score from task output."""
    indicators = ["demand", "feasible", "viable", "validated", "positive", "promising"]
    negative = ["unfeasible", "no demand", "invalid", "negative", "unpromising"]

    score = 0.5  # Start neutral
    text = str(output).lower()

    for indicator in indicators:
        if indicator in text:
            score += 0.12

    for neg in negative:
        if neg in text:
            score -= 0.2

    return max(0.0, min(1.0, score))


def calculate_build_progress(output: dict) -> float:
    """Calculate build progress from task output."""
    if "components" in output:
        components = output.get("components", [])
        if components:
            total = len(components)
            completed = len([c for c in components if "complete" in str(c).lower()])
            return completed / max(total, 1)

    if "implementation_steps" in output:
        steps = output.get("implementation_steps", [])
        if steps:
            return 0.5 + (len(steps) * 0.1)

    # Default progress based on task completion
    return 0.3


def calculate_performance(output: dict) -> float:
    """Calculate performance metric from task output."""
    if "performance" in output:
        perf = output.get("performance")
        if isinstance(perf, (int, float)):
            return float(perf)

    if "success_rate" in output:
        return float(output.get("success_rate", 0.5))

    # Analyze output for performance indicators
    text = str(output).lower()
    indicators = ["optimized", "fast", "efficient", "success"]
    score = 0.5

    for indicator in indicators:
        if indicator in text:
            score += 0.1

    return min(1.0, score)


def calculate_stability(output: dict) -> float:
    """Calculate stability metric from task output."""
    if "stability" in output:
        stab = output.get("stability")
        if isinstance(stab, (int, float)):
            return float(stab)

    # Analyze for stability indicators
    text = str(output).lower()
    indicators = ["stable", "reliable", "consistent", "robust"]
    score = 0.5

    for indicator in indicators:
        if indicator in text:
            score += 0.12

    return min(1.0, score)


def main():
    """Main business lifecycle engine loop."""
    print_banner()

    # Get focus area
    focus_area = "business automation"
    if len(sys.argv) > 1:
        focus_area = " ".join(sys.argv[1:])

    # Initialize all engines
    ai_client = AIClient()
    print(f"AI Provider: {ai_client.get_provider()}")
    if not ai_client.is_available():
        print("⚠ No AI API key found. Using fallback mode.")
        print("  Set ANTHROPIC_API_KEY or OPENAI_API_KEY for full AI capabilities.\n")

    print(f"Focus Area: {focus_area}")
    print(f"Max Active Businesses: 5\n")
    print("-" * 70)

    research_engine = ResearchEngine()
    planning_engine = PlanningEngine()
    state_manager = StateManager()
    execution_engine = ExecutionEngine()
    result_collector = ResultCollector()
    evaluation_engine = EvaluationEngine(max_retries=3)
    memory = Memory()
    lifecycle_manager = LifecycleManager()
    portfolio_manager = PortfolioManager(max_active=5)

    # Phase 5: Initialize workflow system
    workflow_orchestrator = WorkflowOrchestrator()
    stage_workflows = StageWorkflows()
    portfolio_workflows = PortfolioWorkflows()
    workflow_validator = WorkflowValidator()

    # Display tool status
    tool_status = workflow_orchestrator.get_tool_status()
    print("\n[PHASE 5] Workflow Tool Status:")
    print(f"  AI-Q:      {'✓ Available' if tool_status['ai_q']['available'] else '✗ Not Available'}")
    print(f"  NemoClaw:  {'✓ Available' if tool_status['nemoclaw']['available'] else '✗ Not Available'}")
    print(f"  Zep:       {'✓ Available' if tool_status['zep']['available'] else '✗ Not Available'}")
    print(f"  Simulator: {'✓ Available' if tool_status['simulator']['available'] else '✗ Not Available'}")

    print("\n🚀 BUSINESS LIFECYCLE ENGINE - Starting Continuous Operation (Phase 5)\n")

    iteration = 0
    max_iterations = 50  # Limit iterations for testing (use 1000 for production)

    while iteration < max_iterations:
        iteration += 1
        print(f"\n{'='*70}")
        print(f"CYCLE {iteration}")
        print(f"{'='*70}\n")

        # PHASE 1: DISCOVERY
        if portfolio_manager.can_add_business():
            print("[DISCOVERY] Searching for new opportunities...")
            opportunities = research_engine.find_opportunities(focus_area)

            if opportunities:
                selected = research_engine.select_best_opportunity(opportunities)
                print(f"  → Found: {selected['idea']}")

                # Create new business
                business = lifecycle_manager.create_business(selected)
                portfolio_manager.add_business(business)

                memory.save_decision(
                    decision=f"Created business: {selected['idea']}",
                    context=f"Stage: DISCOVERED, Potential: {selected.get('potential', 'unknown')}",
                    outcome="pending"
                )
        else:
            print("[DISCOVERY] Portfolio at capacity (max 5 active businesses)")

        # PHASE 2: PORTFOLIO MANAGEMENT
        active_businesses = portfolio_manager.get_active_businesses()
        print(f"\n[PORTFOLIO] Managing {len(active_businesses)} active businesses\n")

        for business in active_businesses:
            business_id = business["id"]
            current_stage = business["stage"]

            print(f"  Business: {business['opportunity']['idea'][:55]}")
            print(f"  Stage: {current_stage}")

            # Show key metrics
            metrics = business["metrics"]
            if current_stage == "VALIDATING":
                print(f"  Validation: {metrics.get('validation_score', 0.0):.2f}")
            elif current_stage == "BUILDING":
                print(f"  Progress: {metrics.get('build_progress', 0.0):.2f}")
            elif current_stage in ["SCALING", "OPERATING", "OPTIMIZING"]:
                print(f"  Performance: {metrics.get('performance', 0.0):.2f}, "
                      f"Stability: {metrics.get('stability', 0.0):.2f}")

            # Check if stage transition needed
            next_stage = lifecycle_manager.evaluate_transition(business)

            if next_stage and next_stage != current_stage:
                print(f"  → Transitioning: {current_stage} → {next_stage}")
                lifecycle_manager.update_stage(business_id, next_stage, "Metrics threshold met")
                current_stage = next_stage

                # Reload business after stage change
                business = lifecycle_manager.get_business(business_id)

            # Generate stage-appropriate tasks if needed
            if current_stage != "TERMINATED":
                business_tasks = [
                    state_manager.get_task(tid)
                    for tid in business.get("tasks", [])
                    if state_manager.get_task(tid) is not None
                ]
                pending_tasks = [t for t in business_tasks if t["status"] == "pending"]

                if len(pending_tasks) == 0:
                    print(f"  → Generating {current_stage} tasks...")

                    # Phase 5: Use stage workflows for task generation
                    new_tasks = stage_workflows.get_tasks_for_stage(current_stage, business)

                    # Fallback to Phase 4 if no tasks generated
                    if not new_tasks:
                        new_tasks = planning_engine.create_stage_tasks(business, current_stage)

                    for task in new_tasks:
                        task["business_id"] = business_id
                        task["business_stage"] = current_stage
                        state_manager.add_task(task)
                        lifecycle_manager.add_task_to_business(business_id, task["task_id"])

                    print(f"    Generated {len(new_tasks)} tasks")

                    # Track validation/optimization attempts
                    if current_stage == "VALIDATING":
                        attempts = metrics.get("validation_attempts", 0) + 1
                        lifecycle_manager.update_metrics(business_id, {"validation_attempts": attempts})
                    elif current_stage == "OPTIMIZING":
                        attempts = metrics.get("optimization_attempts", 0) + 1
                        lifecycle_manager.update_metrics(business_id, {"optimization_attempts": attempts})

        # PHASE 3: EXECUTION
        all_pending = state_manager.get_pending_tasks()

        if all_pending:
            # Filter tasks that belong to active businesses
            active_tasks = [
                task for task in all_pending
                if task.get("business_id") and
                   lifecycle_manager.get_business(task["business_id"]) and
                   lifecycle_manager.get_business(task["business_id"])["stage"] != "TERMINATED"
            ]

            if active_tasks:
                print(f"\n[EXECUTION] Processing {len(active_tasks)} pending tasks\n")

                for task in active_tasks[:10]:  # Process max 10 per cycle
                    business_id = task.get("business_id")
                    business = lifecycle_manager.get_business(business_id)

                    if not business or business["stage"] == "TERMINATED":
                        continue

                    print(f"  ◆ {task['title'][:60]}")
                    print(f"    Business: {business['opportunity']['idea'][:45]}")
                    print(f"    Agent: {task['assigned_agent']}")

                    # Phase 5: Validate task before execution
                    is_valid, validation_errors = workflow_validator.validate_stage_workflow(
                        business=business,
                        stage=business["stage"],
                        tasks=[task]
                    )

                    if not is_valid:
                        print(f"    ✗ Validation failed: {validation_errors[0]}")
                        state_manager.update_task(task["task_id"], {
                            "status": "failed",
                            "error": f"Validation failed: {'; '.join(validation_errors)}"
                        })
                        continue

                    # Execute
                    state_manager.update_task(task["task_id"], {"status": "in_progress"})

                    # Phase 5: Use workflow orchestrator for execution with tool integration
                    workflow_result = workflow_orchestrator.execute_stage_workflow(
                        business=business,
                        stage=business["stage"],
                        tasks=[task],
                        stage_workflows_module=stage_workflows
                    )

                    # Extract task result from workflow result
                    if workflow_result["outputs"]:
                        task_output = workflow_result["outputs"][0]
                        collected = {
                            "status": task_output.get("status", "completed"),
                            "output": task_output.get("output", {}),
                            "error": task_output.get("error")
                        }
                    else:
                        # Fallback to Phase 4 execution
                        result = execution_engine.execute_business_task(task, business)
                        collected = result_collector.collect_result(task, result)

                    state_manager.update_task(task["task_id"], collected)

                    # Update business metrics based on outcome
                    if collected["status"] == "completed":
                        print(f"    ✓ Completed")

                        # Extract and update metrics
                        metrics_update = extract_metrics_from_result(
                            collected["output"],
                            business["stage"]
                        )

                        if metrics_update:
                            lifecycle_manager.update_metrics(business_id, metrics_update)

                        memory.save_result(task["task_id"], task["title"], collected)
                    else:
                        print(f"    ✗ Failed: {collected.get('error', 'Unknown error')[:50]}")

                        # Increment failure count
                        failure_count = business["metrics"].get("failure_count", 0) + 1
                        lifecycle_manager.update_metrics(business_id, {"failure_count": failure_count})

                    time.sleep(0.05)

        # PHASE 4: REPORTING (Enhanced with Phase 5)
        if iteration % 5 == 0:  # Every 5 cycles - Portfolio review
            print(f"\n{'='*70}")
            print("PORTFOLIO REVIEW (PHASE 5)")
            print(f"{'='*70}")

            # Phase 5: Portfolio workflow validation and execution
            active_businesses = portfolio_manager.get_active_businesses()

            if active_businesses:
                # Validate portfolio workflow
                is_valid, validation_errors = workflow_validator.validate_portfolio_workflow(
                    businesses=active_businesses
                )

                if is_valid:
                    # Execute portfolio workflow
                    portfolio_result = workflow_orchestrator.execute_portfolio_workflow(
                        businesses=active_businesses,
                        portfolio_workflows_module=portfolio_workflows
                    )

                    print(f"\n  Businesses Analyzed: {portfolio_result['businesses_analyzed']}")

                    if "portfolio_health" in portfolio_result:
                        health = portfolio_result["portfolio_health"]
                        print(f"  Portfolio Health: {health['status']}")
                        print(f"  Diversification: {health['diversification_score']:.2f}")

                    if portfolio_result.get("recommendations"):
                        print(f"\n  Recommendations:")
                        for rec in portfolio_result["recommendations"]:
                            print(f"    • {rec}")

                    # Log portfolio result to Zep memory (via orchestrator)
                    if workflow_orchestrator.zep:
                        print("  ✓ Portfolio metrics logged to Zep memory")
                else:
                    print(f"\n  ✗ Portfolio validation failed: {validation_errors[0]}")

        # PHASE 4: Standard reporting (every 10 cycles)
        if iteration % 10 == 0:
            print(f"\n{'='*70}")
            print("PORTFOLIO STATUS")
            print(f"{'='*70}")

            stats = portfolio_manager.get_portfolio_stats()
            print(f"\nTotal Businesses: {stats['total_businesses']}")
            print(f"Active: {stats['active_count']}")
            print(f"Terminated: {stats['terminated_count']}")

            print(f"\nBy Stage:")
            for stage, count in stats['by_stage'].items():
                if count > 0:
                    print(f"  {stage}: {count}")

            top_performers = portfolio_manager.get_top_performers(3)
            if top_performers:
                print(f"\nTop Performers:")
                for idx, biz in enumerate(top_performers, 1):
                    perf = biz["metrics"].get("performance", 0.0)
                    val_score = biz["metrics"].get("validation_score", 0.0)
                    print(f"  {idx}. {biz['opportunity']['idea'][:50]}")
                    print(f"     Stage: {biz['stage']}, Score: {max(perf, val_score):.2f}")

        # Check termination condition
        active = portfolio_manager.get_active_businesses()
        if len(active) == 0 and iteration > 10:
            print("\n\nAll businesses terminated or completed.")
            break

        # Brief sleep to prevent tight loop
        time.sleep(0.1)

    # FINAL REPORT (Phase 5 Enhanced)
    print(f"\n{'='*70}")
    print("FINAL REPORT - PHASE 5")
    print(f"{'='*70}\n")

    stats = portfolio_manager.get_portfolio_stats()
    memory_stats = memory.get_statistics()

    print(f"Cycles Completed: {iteration}")
    print(f"Total Businesses Created: {stats['total_businesses']}")
    print(f"Active: {stats['active_count']}")
    print(f"Terminated: {stats['terminated_count']}")

    print(f"\nMemory Statistics:")
    print(f"  Decisions: {memory_stats['total_decisions']}")
    print(f"  Results: {memory_stats['total_results']}")
    print(f"  Successful Tasks: {memory_stats['successful_tasks']}")
    print(f"  Failed Tasks: {memory_stats['failed_tasks']}")

    # Phase 5: Workflow execution statistics
    print(f"\n[PHASE 5] Workflow Execution Summary:")
    workflow_stats = workflow_orchestrator.get_execution_stats()
    print(f"  Total Workflows: {workflow_stats['total_workflows']}")
    print(f"  Total Tasks: {workflow_stats['total_tasks']}")
    print(f"  Completed Tasks: {workflow_stats['completed_tasks']}")
    print(f"  Success Rate: {workflow_stats['success_rate']:.2%}")

    # Phase 5: Validation statistics
    validation_stats = workflow_validator.get_validation_statistics()
    print(f"\n[PHASE 5] Workflow Validation Summary:")
    print(f"  Total Validations: {validation_stats['total_validations']}")
    print(f"  Passed: {validation_stats['passed_count']}")
    print(f"  Failed: {validation_stats['failed_count']}")
    print(f"  Pass Rate: {validation_stats['pass_rate']:.2%}")
    print(f"  Avg Confidence: {validation_stats['avg_confidence']:.2%}")

    # Phase 5: Portfolio management summary
    print(f"\n[PHASE 5] Portfolio Management Summary:")
    print(f"  Portfolio Reviews: {portfolio_workflows.get_review_count()}")
    print(f"  Rebalancing Actions: {len(portfolio_workflows.get_rebalancing_history())}")

    # Phase 5: Tool integration summary
    tool_status = workflow_orchestrator.get_tool_status()
    print(f"\n[PHASE 5] Tool Integration Status:")
    for tool_name, status in tool_status.items():
        available = "✓" if status["available"] else "✗"
        print(f"  {available} {tool_name.upper()}: {status['initialized']}")

    if stats['active_count'] > 0:
        memory.save_learning(
            category="portfolio",
            insight=f"Managed {stats['total_businesses']} businesses with {stats['active_count']} still active",
            confidence=0.9
        )

    print("\n" + "=" * 70)
    print("\n🎉 BUSINESS_LIFECYCLE_ENGINE_READY (Phase 5 Integration Complete)\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
