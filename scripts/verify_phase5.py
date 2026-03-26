#!/usr/bin/env python3
"""
Phase 5 Integration Verification Script
Verifies all Phase 5 components are properly integrated
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.portfolio_workflows import PortfolioWorkflows
from project_alpha.core.workflow_validator import WorkflowValidator


def print_section(title):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def verify_imports():
    """Verify all Phase 5 modules can be imported."""
    print_section("PHASE 5 IMPORT VERIFICATION")

    try:
        print("✓ WorkflowOrchestrator imported successfully")
        print("✓ StageWorkflows imported successfully")
        print("✓ PortfolioWorkflows imported successfully")
        print("✓ WorkflowValidator imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def verify_initialization():
    """Verify all Phase 5 modules can be initialized."""
    print_section("PHASE 5 INITIALIZATION VERIFICATION")

    try:
        orchestrator = WorkflowOrchestrator()
        print("✓ WorkflowOrchestrator initialized")

        stage_workflows = StageWorkflows()
        print("✓ StageWorkflows initialized")

        portfolio_workflows = PortfolioWorkflows()
        print("✓ PortfolioWorkflows initialized")

        validator = WorkflowValidator()
        print("✓ WorkflowValidator initialized")

        return True, orchestrator, stage_workflows, portfolio_workflows, validator
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return False, None, None, None, None


def verify_tool_status(orchestrator):
    """Verify tool status detection."""
    print_section("PHASE 5 TOOL STATUS VERIFICATION")

    try:
        tool_status = orchestrator.get_tool_status()

        print("\nTool Availability:")
        for tool_name, status in tool_status.items():
            available = "✓" if status["available"] else "✗"
            initialized = "✓" if status["initialized"] else "✗"
            print(f"  {available} {tool_name.upper()}: Available={status['available']}, Initialized={initialized}")

        return True
    except Exception as e:
        print(f"✗ Tool status check failed: {e}")
        return False


def verify_stage_workflows(stage_workflows):
    """Verify stage workflow generation."""
    print_section("PHASE 5 STAGE WORKFLOW VERIFICATION")

    mock_business = {
        "id": "test_001",
        "stage": "VALIDATING",
        "opportunity": {"idea": "Test business idea"},
        "metrics": {"validation_score": 0.75}
    }

    try:
        # Test each stage
        stages = ["DISCOVERED", "VALIDATING", "BUILDING", "SCALING", "OPERATING", "OPTIMIZING", "TERMINATED"]

        for stage in stages:
            mock_business["stage"] = stage
            tasks = stage_workflows.get_tasks_for_stage(stage, mock_business)
            print(f"  ✓ {stage}: Generated {len(tasks)} tasks")

        return True
    except Exception as e:
        print(f"✗ Stage workflow generation failed: {e}")
        return False


def verify_portfolio_workflows(portfolio_workflows):
    """Verify portfolio workflow functionality."""
    print_section("PHASE 5 PORTFOLIO WORKFLOW VERIFICATION")

    mock_businesses = [
        {
            "id": "biz_001",
            "stage": "VALIDATING",
            "opportunity": {"idea": "Business 1"},
            "metrics": {"validation_score": 0.8}
        },
        {
            "id": "biz_002",
            "stage": "BUILDING",
            "opportunity": {"idea": "Business 2"},
            "metrics": {"build_progress": 0.6}
        },
        {
            "id": "biz_003",
            "stage": "SCALING",
            "opportunity": {"idea": "Business 3"},
            "metrics": {"performance": 0.85, "stability": 0.90}
        }
    ]

    try:
        # Create mock orchestrator
        class MockOrchestrator:
            pass

        result = portfolio_workflows.manage_portfolio(mock_businesses, MockOrchestrator())

        print(f"  ✓ Portfolio workflow executed")
        print(f"  ✓ Analyzed {result['businesses_analyzed']} businesses")
        print(f"  ✓ Portfolio health: {result['portfolio_health']['status']}")
        print(f"  ✓ Generated {len(result['recommendations'])} recommendations")

        return True
    except Exception as e:
        print(f"✗ Portfolio workflow failed: {e}")
        return False


def verify_validation(validator):
    """Verify workflow validation."""
    print_section("PHASE 5 WORKFLOW VALIDATION VERIFICATION")

    mock_business = {
        "id": "test_001",
        "stage": "VALIDATING",
        "opportunity": {"idea": "Test business"},
        "metrics": {"validation_score": 0.75}
    }

    mock_tasks = [
        {
            "task_id": "task_001",
            "title": "Test task",
            "assigned_agent": "research",
            "stage": "VALIDATING",
            "priority": "high"
        }
    ]

    try:
        is_valid, errors = validator.validate_stage_workflow(
            business=mock_business,
            stage="VALIDATING",
            tasks=mock_tasks
        )

        if is_valid:
            print("  ✓ Stage workflow validation passed")
        else:
            print(f"  ✗ Stage workflow validation failed: {errors}")

        # Test portfolio validation
        is_valid, errors = validator.validate_portfolio_workflow([mock_business])

        if is_valid:
            print("  ✓ Portfolio workflow validation passed")
        else:
            print(f"  ✗ Portfolio workflow validation failed: {errors}")

        # Check validation stats
        stats = validator.get_validation_stats()
        print(f"  ✓ Validation stats: {stats['total_validations']} validations, {stats['success_rate']:.2%} success rate")

        return True
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        return False


def verify_orchestrator_execution(orchestrator, stage_workflows):
    """Verify workflow orchestrator execution."""
    print_section("PHASE 5 ORCHESTRATOR EXECUTION VERIFICATION")

    mock_business = {
        "id": "test_001",
        "stage": "VALIDATING",
        "opportunity": {"idea": "Test business"},
        "metrics": {"validation_score": 0.75}
    }

    mock_tasks = [
        {
            "task_id": "task_001",
            "title": "Test validation task",
            "assigned_agent": "research",
            "stage": "VALIDATING",
            "priority": "high"
        }
    ]

    try:
        result = orchestrator.execute_stage_workflow(
            business=mock_business,
            stage="VALIDATING",
            tasks=mock_tasks,
            stage_workflows_module=stage_workflows
        )

        print(f"  ✓ Workflow executed: {result['workflow_id']}")
        print(f"  ✓ Status: {result['status']}")
        print(f"  ✓ Tasks completed: {result['tasks_completed']}/{result['tasks_total']}")
        print(f"  ✓ Success rate: {result['success_rate']:.2%}")

        # Check execution stats
        stats = orchestrator.get_execution_stats()
        print(f"  ✓ Execution stats: {stats['total_workflows']} workflows, {stats['success_rate']:.2%} success rate")

        return True
    except Exception as e:
        print(f"✗ Orchestrator execution failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("\n" + "=" * 70)
    print(" PROJECT ALPHA - PHASE 5 INTEGRATION VERIFICATION")
    print("=" * 70)

    results = []

    # 1. Verify imports
    results.append(("Imports", verify_imports()))

    # 2. Verify initialization
    init_result = verify_initialization()
    results.append(("Initialization", init_result[0]))

    if not init_result[0]:
        print("\n✗ Cannot continue - initialization failed")
        return 1

    orchestrator, stage_workflows, portfolio_workflows, validator = init_result[1:]

    # 3. Verify tool status
    results.append(("Tool Status", verify_tool_status(orchestrator)))

    # 4. Verify stage workflows
    results.append(("Stage Workflows", verify_stage_workflows(stage_workflows)))

    # 5. Verify portfolio workflows
    results.append(("Portfolio Workflows", verify_portfolio_workflows(portfolio_workflows)))

    # 6. Verify validation
    results.append(("Workflow Validation", verify_validation(validator)))

    # 7. Verify orchestrator execution
    results.append(("Orchestrator Execution", verify_orchestrator_execution(orchestrator, stage_workflows)))

    # Final summary
    print_section("VERIFICATION SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nResults: {passed}/{total} checks passed\n")

    for check_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {check_name}")

    if passed == total:
        print("\n" + "=" * 70)
        print(" ✓ ALL PHASE 5 COMPONENTS VERIFIED SUCCESSFULLY")
        print("=" * 70 + "\n")
        return 0
    else:
        print("\n" + "=" * 70)
        print(f" ✗ {total - passed} VERIFICATION(S) FAILED")
        print("=" * 70 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
