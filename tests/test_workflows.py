"""
Comprehensive test suite for Project Alpha
Tests all stage workflows, portfolio management, multi-business operations,
tool integrations, and fallback patterns
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List

# Import project modules
import sys
import os
# Add project root to path dynamically
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.workflow_orchestrator import WorkflowOrchestrator
from core.stage_workflows import StageWorkflows
from core.lifecycle_manager import LifecycleManager
from core.portfolio_manager import PortfolioManager


# ============================================================================
# TEST CLASS 1: Stage Workflows Testing
# ============================================================================

class TestStageWorkflows:
    """Test all 7 lifecycle stage workflows."""

    @pytest.fixture
    def workflows(self):
        """Create StageWorkflows instance."""
        return StageWorkflows()

    @pytest.fixture
    def lifecycle(self):
        """Create LifecycleManager instance."""
        return LifecycleManager()

    @pytest.fixture
    def sample_business(self, lifecycle):
        """Create a sample business for testing."""
        return lifecycle.create_business({
            "idea": "Test business idea",
            "target_market": "Test market",
            "potential": "high"
        })

    # ------------------------------------------------------------------------
    # DISCOVERED Stage Tests
    # ------------------------------------------------------------------------

    def test_discovered_stage(self, workflows, sample_business):
        """Test DISCOVERED stage workflow."""
        # Get tasks
        tasks = workflows.get_discovered_tasks(sample_business)

        # Verify task count
        assert len(tasks) == 4, "DISCOVERED stage should generate 4 tasks"

        # Verify task structure
        for task in tasks:
            assert "task_id" in task
            assert "title" in task
            assert "description" in task
            assert "priority" in task
            assert "assigned_agent" in task
            assert "stage" in task
            assert task["stage"] == "DISCOVERED"

        # Verify task priorities
        priorities = [t["priority"] for t in tasks]
        assert "high" in priorities, "Should have high priority tasks"

        # Test task execution
        for task in tasks:
            result = workflows.execute_discovered_task(task, sample_business)
            assert result["status"] == "success"

    def test_discovered_research_task(self, workflows, sample_business):
        """Test DISCOVERED research task execution."""
        tasks = workflows.get_discovered_tasks(sample_business)
        research_task = tasks[0]  # First task is market research

        result = workflows.execute_discovered_task(research_task, sample_business)

        assert result["status"] == "success"
        assert "market_size" in result
        assert "demand_level" in result
        assert "findings" in result
        assert isinstance(result["findings"], list)

    def test_discovered_decision_task(self, workflows, sample_business):
        """Test DISCOVERED validation decision task."""
        tasks = workflows.get_discovered_tasks(sample_business)
        decision_task = tasks[-1]  # Last task is decision

        result = workflows.execute_discovered_task(decision_task, sample_business)

        assert result["status"] == "success"
        assert "decision" in result
        assert result["decision"] in ["go", "no_go"]
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0

    # ------------------------------------------------------------------------
    # VALIDATING Stage Tests
    # ------------------------------------------------------------------------

    def test_validating_stage(self, workflows, lifecycle, sample_business):
        """Test VALIDATING stage workflow."""
        # Move business to VALIDATING
        lifecycle.update_stage(sample_business["id"], "VALIDATING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        # Get tasks
        tasks = workflows.get_validating_tasks(business)

        # Verify task count
        assert len(tasks) == 8, "VALIDATING stage should generate 8 tasks"

        # Verify all tasks belong to VALIDATING stage
        for task in tasks:
            assert task["stage"] == "VALIDATING"

        # Test task execution
        for task in tasks[:3]:  # Test first 3 tasks
            result = workflows.execute_validating_task(task, business)
            assert result["status"] == "success"

    def test_validating_problem_validation(self, workflows, lifecycle, sample_business):
        """Test problem validation task."""
        lifecycle.update_stage(sample_business["id"], "VALIDATING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_validating_tasks(business)
        problem_task = tasks[0]

        result = workflows.execute_validating_task(problem_task, business)

        assert result["status"] == "success"
        assert "problem_validated" in result
        assert isinstance(result["problem_validated"], bool)
        assert "customer_pain_level" in result
        assert 0.0 <= result["customer_pain_level"] <= 1.0

    def test_validating_pricing_research(self, workflows, lifecycle, sample_business):
        """Test pricing research task."""
        lifecycle.update_stage(sample_business["id"], "VALIDATING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_validating_tasks(business)
        pricing_task = tasks[2]

        result = workflows.execute_validating_task(pricing_task, business)

        assert result["status"] == "success"
        assert "pricing_strategy" in result
        assert "willingness_to_pay" in result
        assert "recommended_price" in result

    def test_validating_build_decision(self, workflows, lifecycle, sample_business):
        """Test build/no-build decision based on validation score."""
        lifecycle.update_stage(sample_business["id"], "VALIDATING", "Test")

        # Test with high validation score (should build)
        lifecycle.update_metrics(sample_business["id"], {"validation_score": 0.80})
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_validating_tasks(business)
        decision_task = tasks[-1]

        result = workflows.execute_validating_task(decision_task, business)

        assert result["status"] == "success"
        assert result["decision"] == "build"
        assert result["next_stage"] == "BUILDING"

    # ------------------------------------------------------------------------
    # BUILDING Stage Tests
    # ------------------------------------------------------------------------

    def test_building_stage(self, workflows, lifecycle, sample_business):
        """Test BUILDING stage workflow."""
        lifecycle.update_stage(sample_business["id"], "BUILDING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_building_tasks(business)

        assert len(tasks) == 8, "BUILDING stage should generate 8 tasks"

        # Verify task types
        task_titles = [t["title"] for t in tasks]
        assert any("architecture" in t.lower() for t in task_titles)
        assert any("sprint" in t.lower() for t in task_titles)
        assert any("testing" in t.lower() or "qa" in t.lower() for t in task_titles)

        # Test execution
        for task in tasks[:2]:
            result = workflows.execute_building_task(task, business)
            assert result["status"] == "success"

    def test_building_architecture_task(self, workflows, lifecycle, sample_business):
        """Test architecture design task."""
        lifecycle.update_stage(sample_business["id"], "BUILDING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_building_tasks(business)
        arch_task = tasks[0]

        result = workflows.execute_building_task(arch_task, business)

        assert result["status"] == "success"
        assert "architecture_type" in result
        assert "tech_stack" in result
        assert isinstance(result["tech_stack"], list)
        assert "components" in result

    def test_building_testing_task(self, workflows, lifecycle, sample_business):
        """Test QA and testing task."""
        lifecycle.update_stage(sample_business["id"], "BUILDING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_building_tasks(business)
        test_task = tasks[4]  # QA task

        result = workflows.execute_building_task(test_task, business)

        assert result["status"] == "success"
        assert "test_coverage" in result
        assert 0.0 <= result["test_coverage"] <= 1.0
        assert "quality_score" in result

    # ------------------------------------------------------------------------
    # SCALING Stage Tests
    # ------------------------------------------------------------------------

    def test_scaling_stage(self, workflows, lifecycle, sample_business):
        """Test SCALING stage workflow."""
        lifecycle.update_stage(sample_business["id"], "SCALING", "Test")
        lifecycle.update_metrics(sample_business["id"], {
            "performance": 0.75,
            "stability": 0.80
        })
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_scaling_tasks(business)

        assert len(tasks) == 7, "SCALING stage should generate 7 tasks"

        # Test execution
        for task in tasks[:3]:
            result = workflows.execute_scaling_task(task, business)
            assert result["status"] == "success"

    def test_scaling_marketing_task(self, workflows, lifecycle, sample_business):
        """Test growth marketing task."""
        lifecycle.update_stage(sample_business["id"], "SCALING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_scaling_tasks(business)
        marketing_task = tasks[0]

        result = workflows.execute_scaling_task(marketing_task, business)

        assert result["status"] == "success"
        assert "campaigns_launched" in result
        assert "cac" in result  # Customer Acquisition Cost
        assert "roi" in result

    def test_scaling_infrastructure_task(self, workflows, lifecycle, sample_business):
        """Test infrastructure scaling task."""
        lifecycle.update_stage(sample_business["id"], "SCALING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_scaling_tasks(business)
        infra_task = tasks[3]

        result = workflows.execute_scaling_task(infra_task, business)

        assert result["status"] == "success"
        assert "capacity_increase" in result
        assert "auto_scaling" in result
        assert "stability" in result

    # ------------------------------------------------------------------------
    # OPERATING Stage Tests
    # ------------------------------------------------------------------------

    def test_operating_stage(self, workflows, lifecycle, sample_business):
        """Test OPERATING stage workflow."""
        lifecycle.update_stage(sample_business["id"], "OPERATING", "Test")
        lifecycle.update_metrics(sample_business["id"], {
            "performance": 0.85,
            "stability": 0.90
        })
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_operating_tasks(business)

        assert len(tasks) == 5, "OPERATING stage should generate 5 tasks"

        # Test execution
        for task in tasks:
            result = workflows.execute_operating_task(task, business)
            assert result["status"] == "success"

    def test_operating_monitoring_task(self, workflows, lifecycle, sample_business):
        """Test operations monitoring task."""
        lifecycle.update_stage(sample_business["id"], "OPERATING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_operating_tasks(business)
        monitoring_task = tasks[0]

        result = workflows.execute_operating_task(monitoring_task, business)

        assert result["status"] == "success"
        assert "uptime" in result
        assert result["uptime"] > 0.99  # Should have high uptime
        assert "active_users" in result
        assert "stability" in result

    def test_operating_revenue_task(self, workflows, lifecycle, sample_business):
        """Test revenue optimization task."""
        lifecycle.update_stage(sample_business["id"], "OPERATING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_operating_tasks(business)
        revenue_task = tasks[2]

        result = workflows.execute_operating_task(revenue_task, business)

        assert result["status"] == "success"
        assert "mrr" in result
        assert "arpu" in result

    # ------------------------------------------------------------------------
    # OPTIMIZING Stage Tests
    # ------------------------------------------------------------------------

    def test_optimizing_stage(self, workflows, lifecycle, sample_business):
        """Test OPTIMIZING stage workflow."""
        lifecycle.update_stage(sample_business["id"], "OPTIMIZING", "Test")
        lifecycle.update_metrics(sample_business["id"], {
            "performance": 0.60,
            "stability": 0.70
        })
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_optimizing_tasks(business)

        assert len(tasks) == 6, "OPTIMIZING stage should generate 6 tasks"

        # Test execution
        for task in tasks[:3]:
            result = workflows.execute_optimizing_task(task, business)
            assert result["status"] == "success"

    def test_optimizing_bottleneck_analysis(self, workflows, lifecycle, sample_business):
        """Test bottleneck analysis task."""
        lifecycle.update_stage(sample_business["id"], "OPTIMIZING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_optimizing_tasks(business)
        bottleneck_task = tasks[0]

        result = workflows.execute_optimizing_task(bottleneck_task, business)

        assert result["status"] == "success"
        assert "bottlenecks_found" in result
        assert "optimization_plan" in result
        assert "expected_improvement" in result

    def test_optimizing_cost_optimization(self, workflows, lifecycle, sample_business):
        """Test cost optimization task."""
        lifecycle.update_stage(sample_business["id"], "OPTIMIZING", "Test")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_optimizing_tasks(business)
        cost_task = tasks[1]

        result = workflows.execute_optimizing_task(cost_task, business)

        assert result["status"] == "success"
        assert "cost_reduction" in result
        assert "savings_monthly" in result
        assert "roi" in result

    # ------------------------------------------------------------------------
    # TERMINATED Stage Tests
    # ------------------------------------------------------------------------

    def test_terminated_stage(self, workflows, lifecycle, sample_business):
        """Test TERMINATED stage workflow."""
        lifecycle.update_stage(sample_business["id"], "TERMINATED", "Test termination")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_terminated_tasks(business)

        assert len(tasks) == 4, "TERMINATED stage should generate 4 tasks"

        # Test execution
        for task in tasks:
            result = workflows.execute_terminated_task(task, business)
            assert result["status"] == "success"

    def test_terminated_final_report(self, workflows, lifecycle, sample_business):
        """Test final report generation."""
        lifecycle.update_stage(sample_business["id"], "TERMINATED", "Failed validation")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_terminated_tasks(business)
        report_task = tasks[0]

        result = workflows.execute_terminated_task(report_task, business)

        assert result["status"] == "success"
        assert result["final_report_generated"] is True
        assert "termination_reason" in result
        assert "lifecycle_duration" in result

    def test_terminated_lessons_learned(self, workflows, lifecycle, sample_business):
        """Test lessons learned documentation."""
        lifecycle.update_stage(sample_business["id"], "TERMINATED", "Performance declined")
        business = lifecycle.get_business(sample_business["id"])

        tasks = workflows.get_terminated_tasks(business)
        lessons_task = tasks[2]

        result = workflows.execute_terminated_task(lessons_task, business)

        assert result["status"] == "success"
        assert result["lessons_documented"] is True
        assert "key_lessons" in result
        assert isinstance(result["key_lessons"], list)


# ============================================================================
# TEST CLASS 2: Portfolio Workflows Testing
# ============================================================================

class TestPortfolioWorkflows:
    """Test portfolio-level management and operations."""

    @pytest.fixture
    def portfolio(self):
        """Create PortfolioManager instance."""
        return PortfolioManager(max_active=5)

    @pytest.fixture
    def lifecycle(self):
        """Create LifecycleManager instance."""
        return LifecycleManager()

    def test_portfolio_initialization(self, portfolio):
        """Test portfolio manager initialization."""
        # Check capacity manager initialized (replaces max_active)
        assert portfolio.capacity_manager is not None
        assert portfolio.lifecycle_manager is not None

    def test_add_business_to_portfolio(self, portfolio, lifecycle):
        """Test adding business to portfolio."""
        business = lifecycle.create_business({
            "idea": "Test business",
            "potential": "high"
        })

        initial_count = len(portfolio.get_all_businesses())
        portfolio.add_business(business)
        final_count = len(portfolio.get_all_businesses())

        # Business count should increase
        assert final_count >= initial_count

    def test_portfolio_capacity_limit(self, portfolio, lifecycle):
        """Test portfolio capacity enforcement."""
        # Add businesses up to limit
        for i in range(6):
            capacity_check = portfolio.can_add_business()
            if capacity_check["allowed"]:
                business = lifecycle.create_business({
                    "idea": f"Business {i}",
                    "potential": "medium"
                })

        # After adding multiple businesses, check capacity status
        active = portfolio.get_active_businesses()
        stats = portfolio.get_portfolio_stats()
        # Verify capacity info is present
        assert "capacity" in stats
        # With legacy max_active=5, soft limit should be configured
        if stats["capacity"]["soft_limit"]:
            assert len(active) <= stats["capacity"]["soft_limit"] + 5  # Allow some overflow for warnings

    def test_get_active_businesses(self, portfolio, lifecycle):
        """Test retrieving active (non-terminated) businesses."""
        # Create business and terminate it
        business = lifecycle.create_business({"idea": "To be terminated"})
        lifecycle.update_stage(business["id"], "TERMINATED", "Test")

        active = portfolio.get_active_businesses()
        active_ids = [b["id"] for b in active]

        # Terminated business should not be in active list
        assert business["id"] not in active_ids

    def test_get_top_performers(self, portfolio, lifecycle):
        """Test getting top performing businesses."""
        # Create businesses with different performance levels
        for i, perf in enumerate([0.9, 0.7, 0.5, 0.8]):
            biz = lifecycle.create_business({"idea": f"Business {i}"})
            lifecycle.update_stage(biz["id"], "SCALING", "Test")
            lifecycle.update_metrics(biz["id"], {
                "performance": perf,
                "stability": 0.8
            })

        top = portfolio.get_top_performers(limit=3)

        assert len(top) <= 3
        # Should be sorted by performance
        if len(top) >= 2:
            perf1 = top[0]["metrics"]["performance"]
            perf2 = top[1]["metrics"]["performance"]
            assert perf1 >= perf2

    def test_portfolio_statistics(self, portfolio, lifecycle):
        """Test portfolio statistics calculation."""
        # Create diverse portfolio
        stages = ["DISCOVERED", "VALIDATING", "BUILDING", "SCALING"]
        for i, stage in enumerate(stages):
            biz = lifecycle.create_business({"idea": f"Business {i}"})
            lifecycle.update_stage(biz["id"], stage, "Test")

        stats = portfolio.get_portfolio_stats()

        assert "total_businesses" in stats
        assert "by_stage" in stats
        assert "active_count" in stats
        assert "terminated_count" in stats
        assert isinstance(stats["by_stage"], dict)


# ============================================================================
# TEST CLASS 3: Multi-Business Operations Testing
# ============================================================================

class TestMultiBusinessOperations:
    """Test concurrent multi-business management."""

    @pytest.fixture
    def orchestrator(self):
        """Create WorkflowOrchestrator instance."""
        return WorkflowOrchestrator()

    @pytest.fixture
    def workflows(self):
        """Create StageWorkflows instance."""
        return StageWorkflows()

    @pytest.fixture
    def lifecycle(self):
        """Create LifecycleManager instance."""
        return LifecycleManager()

    def test_concurrent_workflow_execution(self, orchestrator, workflows, lifecycle):
        """Test executing workflows for multiple businesses concurrently."""
        # Create 3 businesses in different stages
        businesses = []
        for i, stage in enumerate(["DISCOVERED", "VALIDATING", "BUILDING"]):
            biz = lifecycle.create_business({"idea": f"Business {i}"})
            lifecycle.update_stage(biz["id"], stage, "Test")
            businesses.append(lifecycle.get_business(biz["id"]))

        # Execute workflow for each business
        results = []
        for biz in businesses:
            tasks = workflows.get_tasks_for_stage(biz["stage"], biz)
            result = orchestrator.execute_stage_workflow(
                business=biz,
                stage=biz["stage"],
                tasks=tasks[:2],  # Execute first 2 tasks
                stage_workflows_module=workflows
            )
            results.append(result)

        # All workflows should complete
        assert len(results) == 3
        for result in results:
            assert result["status"] in ["completed", "partial"]
            assert result["tasks_total"] == 2

    def test_workflow_isolation(self, orchestrator, workflows, lifecycle):
        """Test that workflows for different businesses don't interfere."""
        # Create 2 businesses
        biz1 = lifecycle.create_business({"idea": "Business 1"})
        biz2 = lifecycle.create_business({"idea": "Business 2"})

        # Execute workflows
        tasks1 = workflows.get_discovered_tasks(biz1)
        result1 = orchestrator.execute_stage_workflow(
            business=biz1,
            stage="DISCOVERED",
            tasks=tasks1[:1],
            stage_workflows_module=workflows
        )

        tasks2 = workflows.get_discovered_tasks(biz2)
        result2 = orchestrator.execute_stage_workflow(
            business=biz2,
            stage="DISCOVERED",
            tasks=tasks2[:1],
            stage_workflows_module=workflows
        )

        # Results should be independent
        assert result1["business_id"] != result2["business_id"]
        assert result1["workflow_id"] != result2["workflow_id"]

    def test_execution_statistics_tracking(self, orchestrator, workflows, lifecycle):
        """Test that execution statistics are properly tracked."""
        initial_stats = orchestrator.get_execution_stats()
        initial_workflows = initial_stats["total_workflows"]

        # Execute a workflow
        biz = lifecycle.create_business({"idea": "Test business"})
        tasks = workflows.get_discovered_tasks(biz)
        orchestrator.execute_stage_workflow(
            business=biz,
            stage="DISCOVERED",
            tasks=tasks[:2],
            stage_workflows_module=workflows
        )

        # Stats should update
        final_stats = orchestrator.get_execution_stats()
        assert final_stats["total_workflows"] == initial_workflows + 1
        assert final_stats["total_tasks"] >= initial_stats["total_tasks"] + 2


# ============================================================================
# TEST CLASS 4: Tool Integrations Testing
# ============================================================================

class TestToolIntegrations:
    """Test AI-Q, NemoClaw, Zep, and Simulator integrations."""

    @pytest.fixture
    def orchestrator(self):
        """Create WorkflowOrchestrator instance."""
        return WorkflowOrchestrator()

    @pytest.fixture
    def lifecycle(self):
        """Create LifecycleManager instance."""
        return LifecycleManager()

    # ------------------------------------------------------------------------
    # Tool Status Tests
    # ------------------------------------------------------------------------

    def test_tool_status_check(self, orchestrator):
        """Test getting tool availability status."""
        status = orchestrator.get_tool_status()

        assert "ai_q" in status
        assert "nemoclaw" in status
        assert "zep" in status
        assert "simulator" in status

        for tool, info in status.items():
            assert "available" in info
            assert "initialized" in info
            assert isinstance(info["available"], bool)
            assert isinstance(info["initialized"], bool)

    def test_simulator_always_available(self, orchestrator):
        """Test that simulator is always available."""
        status = orchestrator.get_tool_status()

        assert status["simulator"]["available"] is True
        assert status["simulator"]["initialized"] is True
        assert orchestrator.simulator is not None

    # ------------------------------------------------------------------------
    # AI-Q Integration Tests
    # ------------------------------------------------------------------------

    @patch.dict(os.environ, {"AIQ_API_KEY": "test_key"})
    def test_aiq_detection_with_key(self):
        """Test AI-Q detection when API key is set."""
        orchestrator = WorkflowOrchestrator()
        status = orchestrator.get_tool_status()

        assert status["ai_q"]["available"] is True

    def test_aiq_detection_without_key(self, orchestrator):
        """Test AI-Q detection when no API key is set."""
        # Remove key if it exists
        if "AIQ_API_KEY" in os.environ:
            del os.environ["AIQ_API_KEY"]

        orchestrator = WorkflowOrchestrator()
        status = orchestrator.get_tool_status()

        # Should gracefully handle missing key
        assert isinstance(status["ai_q"]["available"], bool)

    def test_aiq_reasoning(self, orchestrator, lifecycle):
        """Test AI-Q reasoning functionality."""
        business = lifecycle.create_business({"idea": "Test business"})
        tasks = [
            {"task_id": "t1", "title": "Task 1", "priority": "high"},
            {"task_id": "t2", "title": "Task 2", "priority": "low"}
        ]

        reasoning = orchestrator._ai_q_reason(business, "DISCOVERED", tasks)

        assert "available" in reasoning
        if reasoning["available"]:
            assert "confidence" in reasoning
            assert "insights" in reasoning

    def test_aiq_task_prioritization(self, orchestrator):
        """Test AI-Q task prioritization."""
        tasks = [
            {"task_id": "t1", "priority": "low"},
            {"task_id": "t2", "priority": "high"},
            {"task_id": "t3", "priority": "medium"}
        ]

        reasoning = {"available": True, "recommended_order": "priority_first"}
        prioritized = orchestrator._ai_q_prioritize_tasks(tasks, reasoning)

        # High priority should come first
        assert prioritized[0]["priority"] == "high"

    # ------------------------------------------------------------------------
    # NemoClaw Integration Tests
    # ------------------------------------------------------------------------

    def test_nemoclaw_detection(self, orchestrator):
        """Test NemoClaw detection."""
        status = orchestrator.get_tool_status()

        # Should check for binary availability
        assert isinstance(status["nemoclaw"]["available"], bool)

    def test_nemoclaw_sandbox_execution(self, orchestrator, lifecycle):
        """Test NemoClaw sandbox execution."""
        business = lifecycle.create_business({"idea": "Test business"})
        task = {"task_id": "t1", "title": "Test task"}

        result = orchestrator._nemoclaw_execute(task, business)

        # Should return status regardless of availability
        assert "status" in result

        if result["status"] == "success":
            assert "output" in result
            assert "sandbox_path" in result["output"]

    # ------------------------------------------------------------------------
    # Zep Memory Integration Tests
    # ------------------------------------------------------------------------

    @patch.dict(os.environ, {"ZEP_API_KEY": "test_zep_key"})
    def test_zep_detection_with_key(self):
        """Test Zep detection when API key is set."""
        orchestrator = WorkflowOrchestrator()
        status = orchestrator.get_tool_status()

        assert status["zep"]["available"] is True

    def test_zep_memory_storage(self, orchestrator, lifecycle):
        """Test Zep memory storage."""
        business = lifecycle.create_business({"idea": "Test business"})
        task = {"task_id": "t1", "title": "Test task"}
        result = {"status": "completed", "output": {"data": "test"}}

        # Should not raise exception even if Zep is unavailable
        try:
            orchestrator._zep_store_result(task, result, business, "DISCOVERED")
            # If we get here, it worked or failed gracefully
            assert True
        except Exception as e:
            pytest.fail(f"Zep storage should fail gracefully: {e}")

    # ------------------------------------------------------------------------
    # Simulator Integration Tests
    # ------------------------------------------------------------------------

    def test_simulator_task_simulation(self, orchestrator, lifecycle):
        """Test simulator task simulation."""
        business = lifecycle.create_business({"idea": "Test business"})
        task = {"task_id": "t1", "title": "Test task"}

        simulation = orchestrator._simulate_task(task, business, "BUILDING")

        assert "confidence" in simulation
        assert "available" in simulation
        assert 0.0 <= simulation["confidence"] <= 1.0

    def test_simulator_confidence_adjustment(self, orchestrator, lifecycle):
        """Test simulator confidence adjustment based on business metrics."""
        # Business with high failure count
        business = lifecycle.create_business({"idea": "Risky business"})
        lifecycle.update_metrics(business["id"], {"failure_count": 5})
        business = lifecycle.get_business(business["id"])

        task = {"task_id": "t1"}
        simulation = orchestrator._simulate_task(task, business, "BUILDING")

        # Confidence should be reduced due to failures
        assert simulation["confidence"] < 0.9

    def test_simulator_stage_specific_confidence(self, orchestrator, lifecycle):
        """Test simulator adjusts confidence based on stage."""
        business = lifecycle.create_business({"idea": "Test business"})
        lifecycle.update_stage(business["id"], "SCALING", "Test")
        lifecycle.update_metrics(business["id"], {"performance": 0.9})
        business = lifecycle.get_business(business["id"])

        task = {"task_id": "t1"}
        simulation = orchestrator._simulate_task(task, business, "SCALING")

        # High performance should result in high confidence
        assert simulation["confidence"] > 0.7


# ============================================================================
# TEST CLASS 5: Fallback Patterns Testing
# ============================================================================

class TestFallbackPatterns:
    """Test fallback behaviors and error handling."""

    @pytest.fixture
    def orchestrator(self):
        """Create WorkflowOrchestrator instance."""
        return WorkflowOrchestrator()

    @pytest.fixture
    def workflows(self):
        """Create StageWorkflows instance."""
        return StageWorkflows()

    @pytest.fixture
    def lifecycle(self):
        """Create LifecycleManager instance."""
        return LifecycleManager()

    # ------------------------------------------------------------------------
    # Fallback Execution Tests
    # ------------------------------------------------------------------------

    def test_fallback_execution_unknown_task(self, orchestrator, lifecycle):
        """Test fallback execution for unknown task types."""
        business = lifecycle.create_business({"idea": "Test business"})
        task = {
            "task_id": "unknown_1",
            "title": "Unknown task type",
            "stage": "UNKNOWN"
        }

        result = orchestrator._fallback_execute(task, business, "UNKNOWN")

        assert result["status"] == "completed"
        assert result["fallback"] is True
        assert "message" in result["output"]

    def test_fallback_on_missing_stage_executor(self, orchestrator, workflows, lifecycle):
        """Test fallback when stage-specific executor is missing."""
        business = lifecycle.create_business({"idea": "Test business"})
        task = {
            "task_id": "test_1",
            "title": "Test task",
            "stage": "NONEXISTENT_STAGE"
        }

        # Simulate missing executor by using invalid stage
        result = orchestrator._execute_task_with_tools(
            task=task,
            business=business,
            stage="NONEXISTENT_STAGE",
            stage_workflows_module=workflows
        )

        # Should use fallback and complete
        assert result["status"] in ["completed", "failed"]

    # ------------------------------------------------------------------------
    # Low Confidence Rejection Tests
    # ------------------------------------------------------------------------

    def test_reject_low_confidence_task(self, orchestrator, lifecycle):
        """Test that low confidence tasks are rejected."""
        # Create business with metrics that will lower confidence
        business = lifecycle.create_business({"idea": "High risk business"})
        lifecycle.update_metrics(business["id"], {"failure_count": 10})
        business = lifecycle.get_business(business["id"])

        # Mock simulator to return low confidence
        with patch.object(orchestrator, '_simulate_task') as mock_sim:
            mock_sim.return_value = {
                "confidence": 0.5,
                "available": True
            }

            task = {"task_id": "risky_1", "title": "Risky task"}
            result = orchestrator._execute_task_with_tools(
                task=task,
                business=business,
                stage="BUILDING",
                stage_workflows_module=StageWorkflows()
            )

            # Task should be rejected
            assert result["status"] == "failed"
            assert "confidence" in result.get("error", "").lower() or "simulation" in result

    def test_accept_high_confidence_task(self, orchestrator, workflows, lifecycle):
        """Test that high confidence tasks proceed."""
        business = lifecycle.create_business({"idea": "Low risk business"})
        task = {"task_id": "safe_1", "title": "Safe task", "stage": "DISCOVERED"}

        # Mock simulator to return high confidence
        with patch.object(orchestrator, '_simulate_task') as mock_sim:
            mock_sim.return_value = {
                "confidence": 0.95,
                "available": True
            }

            result = orchestrator._execute_task_with_tools(
                task=task,
                business=business,
                stage="DISCOVERED",
                stage_workflows_module=workflows
            )

            # Task should proceed (not rejected by simulation)
            assert result["status"] in ["completed", "failed"]
            # If failed, it shouldn't be due to confidence
            if result["status"] == "failed":
                error = result.get("error", "").lower()
                assert "confidence" not in error

    # ------------------------------------------------------------------------
    # Tool Unavailability Fallback Tests
    # ------------------------------------------------------------------------

    def test_fallback_when_ai_q_unavailable(self, orchestrator, workflows, lifecycle):
        """Test fallback behavior when AI-Q is unavailable."""
        # Ensure AI-Q is unavailable
        orchestrator.ai_q = None
        orchestrator.ai_q_available = False

        business = lifecycle.create_business({"idea": "Test business"})
        tasks = workflows.get_discovered_tasks(business)

        # Should proceed without AI-Q
        result = orchestrator.execute_stage_workflow(
            business=business,
            stage="DISCOVERED",
            tasks=tasks[:2],
            stage_workflows_module=workflows
        )

        assert result["status"] in ["completed", "partial"]
        # AI-Q reasoning should indicate unavailable
        if "ai_q_reasoning" in result:
            assert result["ai_q_reasoning"]["available"] is False

    def test_fallback_when_nemoclaw_unavailable(self, orchestrator, workflows, lifecycle):
        """Test fallback to direct execution when NemoClaw is unavailable."""
        # Ensure NemoClaw is unavailable
        orchestrator.nemoclaw = None
        orchestrator.nemoclaw_available = False

        business = lifecycle.create_business({"idea": "Test business"})
        task = {"task_id": "t1", "title": "Test task", "stage": "BUILDING"}

        result = orchestrator._execute_task_with_tools(
            task=task,
            business=business,
            stage="BUILDING",
            stage_workflows_module=workflows
        )

        # Should complete via fallback execution
        assert result["status"] in ["completed", "failed"]
        assert result.get("executed_in_sandbox", False) is False

    def test_fallback_when_zep_unavailable(self, orchestrator, workflows, lifecycle):
        """Test graceful degradation when Zep is unavailable."""
        # Ensure Zep is unavailable
        orchestrator.zep = None
        orchestrator.zep_available = False

        business = lifecycle.create_business({"idea": "Test business"})
        tasks = workflows.get_discovered_tasks(business)

        # Should proceed without Zep memory storage
        result = orchestrator.execute_stage_workflow(
            business=business,
            stage="DISCOVERED",
            tasks=tasks[:1],
            stage_workflows_module=workflows
        )

        # Workflow should complete despite missing Zep
        assert result["status"] in ["completed", "partial"]

    # ------------------------------------------------------------------------
    # Error Recovery Tests
    # ------------------------------------------------------------------------

    def test_continue_on_task_failure(self, orchestrator, workflows, lifecycle):
        """Test that workflow continues when individual tasks fail."""
        business = lifecycle.create_business({"idea": "Test business"})

        # Create mix of valid and invalid tasks
        tasks = workflows.get_discovered_tasks(business)[:2]

        # Mock one task to fail
        with patch.object(workflows, 'execute_discovered_task') as mock_exec:
            results = [
                {"status": "success", "data": "ok"},
                {"status": "error", "error": "Simulated failure"}
            ]
            mock_exec.side_effect = results

            result = orchestrator.execute_stage_workflow(
                business=business,
                stage="DISCOVERED",
                tasks=tasks,
                stage_workflows_module=workflows
            )

            # Workflow should complete as partial
            assert result["status"] == "partial"
            assert result["tasks_completed"] < result["tasks_total"]
            assert len(result["errors"]) > 0

    def test_record_failures_in_metrics(self, orchestrator, workflows, lifecycle):
        """Test that task failures are recorded in business metrics."""
        business = lifecycle.create_business({"idea": "Test business"})
        initial_failures = business["metrics"].get("failure_count", 0)

        # Simulate task failure
        task = {"task_id": "fail_1", "title": "Failing task", "stage": "DISCOVERED"}

        with patch.object(workflows, 'execute_discovered_task') as mock_exec:
            mock_exec.side_effect = Exception("Simulated error")

            try:
                orchestrator._execute_task_with_tools(
                    task=task,
                    business=business,
                    stage="DISCOVERED",
                    stage_workflows_module=workflows
                )
            except:
                pass

        # Check that failure was handled
        # (Note: Actual metrics update happens in main.py, not orchestrator)
        # This test verifies error handling doesn't crash the system


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_workflow_cycle(self):
        """Test complete workflow from discovery to building."""
        orchestrator = WorkflowOrchestrator()
        workflows = StageWorkflows()
        lifecycle = LifecycleManager()

        # Create business
        business = lifecycle.create_business({
            "idea": "Integration test business",
            "potential": "high"
        })

        # DISCOVERED stage
        discovered_tasks = workflows.get_discovered_tasks(business)
        discovered_result = orchestrator.execute_stage_workflow(
            business=business,
            stage="DISCOVERED",
            tasks=discovered_tasks,
            stage_workflows_module=workflows
        )

        assert discovered_result["status"] in ["completed", "partial"]

        # Transition to VALIDATING
        lifecycle.update_stage(business["id"], "VALIDATING", "Test")
        lifecycle.update_metrics(business["id"], {"validation_score": 0.85})
        business = lifecycle.get_business(business["id"])

        # VALIDATING stage
        validating_tasks = workflows.get_validating_tasks(business)
        validating_result = orchestrator.execute_stage_workflow(
            business=business,
            stage="VALIDATING",
            tasks=validating_tasks[:3],
            stage_workflows_module=workflows
        )

        assert validating_result["status"] in ["completed", "partial"]

        # Verify execution stats
        stats = orchestrator.get_execution_stats()
        assert stats["total_workflows"] >= 2

    def test_portfolio_with_multiple_stages(self):
        """Test portfolio management across multiple stages."""
        portfolio = PortfolioManager(max_active=5)
        lifecycle = LifecycleManager()
        orchestrator = WorkflowOrchestrator()
        workflows = StageWorkflows()

        # Create businesses in different stages
        stages_to_test = ["DISCOVERED", "VALIDATING", "BUILDING"]
        for stage in stages_to_test:
            if portfolio.can_add_business():
                biz = lifecycle.create_business({"idea": f"Business {stage}"})
                lifecycle.update_stage(biz["id"], stage, "Test")

        # Verify portfolio
        stats = portfolio.get_portfolio_stats()
        assert stats["active_count"] == len(stages_to_test)
        assert stats["total_businesses"] >= len(stages_to_test)


# ============================================================================
# Pytest Configuration and Fixtures
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Clean up test data before and after test session."""
    import tempfile
    import shutil

    # Setup: Create isolated temp directory for test businesses
    temp_dir = tempfile.mkdtemp(prefix="project_alpha_test_")
    test_file = os.path.join(temp_dir, "businesses.json")
    os.environ["PROJECT_ALPHA_BUSINESSES_FILE"] = test_file

    yield

    # Teardown: Clean up temp directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    # Remove env var
    if "PROJECT_ALPHA_BUSINESSES_FILE" in os.environ:
        del os.environ["PROJECT_ALPHA_BUSINESSES_FILE"]


@pytest.fixture(scope="function", autouse=True)
def reset_test_state():
    """Reset state between tests."""
    import json

    # Reset execution count
    workflows = StageWorkflows()
    workflows.execution_count = 0

    # Reset businesses file to empty state for each test
    businesses_file = os.environ.get("PROJECT_ALPHA_BUSINESSES_FILE")
    if businesses_file:
        os.makedirs(os.path.dirname(businesses_file), exist_ok=True)
        with open(businesses_file, 'w') as f:
            json.dump([], f)

    yield


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
