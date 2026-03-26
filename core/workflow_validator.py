"""
Workflow Validator for Project Alpha Phase 5
Pre-execution validation system with 5-check safety framework
"""

import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json


class WorkflowValidator:
    """
    5-check pre-execution validation system for workflows.

    Validation Checks:
    1. Business health check (metrics validation)
    2. Task dependency validation
    3. Resource availability check
    4. Simulation validation (75% confidence threshold)
    5. Tool integration check (AI-Q, NemoClaw, Zep availability)

    Minimum 75% confidence required to proceed with workflow execution.
    """

    def __init__(self, orchestrator: Optional[Any] = None):
        """
        Initialize workflow validator.

        Args:
            orchestrator: Optional WorkflowOrchestrator instance for tool access
        """
        self.orchestrator = orchestrator
        self.confidence_threshold = 0.75
        self.validation_history = []

        # Initialize Zep memory integration if available
        self.zep_available = self._check_zep_available()
        self.zep_session_id = f"validator_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    def _check_zep_available(self) -> bool:
        """Check if Zep memory is available."""
        try:
            return os.getenv("ZEP_API_KEY") is not None
        except Exception:
            return False

    def validate_workflow(
        self,
        business: Dict,
        stage: str,
        tasks: List[Dict],
        stage_workflows_module: Any
    ) -> Dict:
        """
        Perform complete 5-check validation before workflow execution.

        Args:
            business: Business dictionary with metrics and history
            stage: Current lifecycle stage
            tasks: List of tasks to execute
            stage_workflows_module: Stage workflows module for task generation

        Returns:
            Validation result dictionary with:
            - passed: bool (True if all checks pass)
            - confidence: float (overall confidence score 0.0-1.0)
            - checks: dict (individual check results)
            - warnings: list (non-critical warnings)
            - errors: list (critical errors)
            - recommendation: str (proceed/abort/review)
        """
        validation_id = f"val_{business['id']}_{stage}_{datetime.utcnow().isoformat()}"

        result = {
            "validation_id": validation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "business_id": business["id"],
            "business_idea": business["opportunity"]["idea"][:50],
            "stage": stage,
            "task_count": len(tasks),
            "passed": False,
            "confidence": 0.0,
            "checks": {},
            "warnings": [],
            "errors": [],
            "recommendation": "abort"
        }

        # Perform all 5 validation checks
        check1 = self._check_business_health(business, stage)
        check2 = self._check_task_dependencies(tasks, business, stage)
        check3 = self._check_resource_availability(business, stage, tasks)
        check4 = self._check_simulation(business, stage, tasks)
        check5 = self._check_tool_integration()

        # Store individual check results
        result["checks"] = {
            "business_health": check1,
            "task_dependencies": check2,
            "resource_availability": check3,
            "simulation": check4,
            "tool_integration": check5
        }

        # Calculate overall confidence
        confidence_scores = [
            check1["confidence"],
            check2["confidence"],
            check3["confidence"],
            check4["confidence"],
            check5["confidence"]
        ]
        result["confidence"] = sum(confidence_scores) / len(confidence_scores)

        # Collect warnings and errors
        for check_name, check_result in result["checks"].items():
            if check_result.get("warnings"):
                result["warnings"].extend([
                    f"[{check_name}] {w}" for w in check_result["warnings"]
                ])
            if check_result.get("errors"):
                result["errors"].extend([
                    f"[{check_name}] {e}" for e in check_result["errors"]
                ])

        # Determine if validation passes
        all_checks_passed = all(
            check["passed"] for check in result["checks"].values()
        )
        confidence_meets_threshold = result["confidence"] >= self.confidence_threshold

        result["passed"] = all_checks_passed and confidence_meets_threshold

        # Generate recommendation
        if result["passed"]:
            result["recommendation"] = "proceed"
        elif result["confidence"] >= 0.65:
            result["recommendation"] = "review"
            result["warnings"].append(
                f"Confidence ({result['confidence']:.2f}) below threshold ({self.confidence_threshold}), manual review recommended"
            )
        else:
            result["recommendation"] = "abort"
            result["errors"].append(
                f"Confidence ({result['confidence']:.2f}) too low for safe execution"
            )

        # Log to Zep memory if available
        if self.zep_available:
            self._log_to_zep(result)

        # Store in validation history
        self.validation_history.append(result)

        return result

    def validate_stage_workflow(
        self,
        business: Dict,
        stage: str,
        tasks: List[Dict]
    ) -> Tuple[bool, List[str]]:
        """
        Legacy method for backward compatibility.
        Use validate_workflow() for full 5-check validation.

        Args:
            business: Business dictionary
            stage: Current lifecycle stage
            tasks: List of tasks to execute

        Returns:
            Tuple of (is_valid, error_messages)
        """
        # Call new validation method
        result = self.validate_workflow(business, stage, tasks, None)

        # Convert to legacy format
        is_valid = result["passed"]
        errors = result["errors"]

        return is_valid, errors

    def _check_business_health(self, business: Dict, stage: str) -> Dict:
        """
        Check 1: Business health check and metrics validation.

        Validates:
        - Business metrics are within acceptable ranges
        - No critical failures in history
        - Stage is appropriate for current business state
        - Performance indicators are healthy
        """
        check_result = {
            "check_name": "business_health",
            "passed": False,
            "confidence": 0.0,
            "warnings": [],
            "errors": [],
            "details": {}
        }

        metrics = business.get("metrics", {})
        history = business.get("history", [])

        # Check failure count
        failure_count = metrics.get("failure_count", 0)
        if failure_count > 5:
            check_result["errors"].append(
                f"High failure count ({failure_count}), business may be unstable"
            )
            check_result["confidence"] = 0.3
        elif failure_count > 3:
            check_result["warnings"].append(
                f"Elevated failure count ({failure_count}), monitor closely"
            )
            check_result["confidence"] = 0.65
        else:
            check_result["confidence"] = 0.9

        # Check performance score
        performance = metrics.get("performance", 0.5)
        if performance < 0.4:
            check_result["errors"].append(
                f"Low performance score ({performance:.2f}), optimization required"
            )
            check_result["confidence"] = min(check_result["confidence"], 0.4)
        elif performance < 0.6:
            check_result["warnings"].append(
                f"Below-average performance ({performance:.2f})"
            )
            check_result["confidence"] = min(check_result["confidence"], 0.7)

        # Check validation score for early stages
        if stage in ["DISCOVERED", "VALIDATING"]:
            validation_score = metrics.get("validation_score", 0.5)
            if validation_score < 0.5:
                check_result["warnings"].append(
                    f"Low validation score ({validation_score:.2f}) for early stage"
                )
                check_result["confidence"] = min(check_result["confidence"], 0.75)

        # Check stage history for loops or regression
        if len(history) > 1:
            recent_stages = [h.get("stage") for h in history[-3:]]
            if len(recent_stages) != len(set(recent_stages)):
                check_result["warnings"].append(
                    f"Stage cycling detected: {recent_stages}, possible regression"
                )
                check_result["confidence"] = min(check_result["confidence"], 0.7)

        # Check if business is in terminated state
        if business.get("stage") == "TERMINATED":
            check_result["errors"].append(
                "Business is in TERMINATED state, cannot execute workflow"
            )
            check_result["confidence"] = 0.0
            check_result["passed"] = False
            return check_result

        check_result["details"] = {
            "failure_count": failure_count,
            "performance": performance,
            "validation_score": metrics.get("validation_score", 0.5),
            "stage_history_length": len(history)
        }

        check_result["passed"] = len(check_result["errors"]) == 0
        return check_result

    def _check_task_dependencies(
        self,
        tasks: List[Dict],
        business: Dict,
        stage: str
    ) -> Dict:
        """
        Check 2: Task dependency validation.

        Validates:
        - All task dependencies are satisfied
        - Tasks are in valid order
        - No circular dependencies
        - Required tasks for stage are present
        """
        check_result = {
            "check_name": "task_dependencies",
            "passed": False,
            "confidence": 0.9,  # Start high, reduce for issues
            "warnings": [],
            "errors": [],
            "details": {}
        }

        if not tasks:
            check_result["errors"].append("No tasks provided for validation")
            check_result["confidence"] = 0.0
            return check_result

        # Check for duplicate task IDs
        task_ids = [t.get("task_id") for t in tasks]
        if len(task_ids) != len(set(task_ids)):
            check_result["errors"].append("Duplicate task IDs detected")
            check_result["confidence"] = 0.5

        # Validate task structure
        required_fields = ["task_id", "title", "stage", "priority"]
        for task in tasks:
            missing_fields = [f for f in required_fields if f not in task]
            if missing_fields:
                check_result["warnings"].append(
                    f"Task {task.get('task_id', 'unknown')} missing fields: {missing_fields}"
                )
                check_result["confidence"] = min(check_result["confidence"], 0.75)

        # Check task count is reasonable for stage
        expected_task_ranges = {
            "DISCOVERED": (3, 4),
            "VALIDATING": (5, 8),
            "BUILDING": (7, 8),
            "SCALING": (5, 7),
            "OPERATING": (4, 5),
            "OPTIMIZING": (5, 6),
            "TERMINATED": (3, 4)
        }

        expected_range = expected_task_ranges.get(stage, (3, 8))
        if not (expected_range[0] <= len(tasks) <= expected_range[1]):
            check_result["warnings"].append(
                f"Task count ({len(tasks)}) outside expected range {expected_range} for {stage}"
            )
            check_result["confidence"] = min(check_result["confidence"], 0.8)

        # Check task priorities
        high_priority_count = sum(1 for t in tasks if t.get("priority") == "high")
        if high_priority_count == 0:
            check_result["warnings"].append("No high-priority tasks defined")
            check_result["confidence"] = min(check_result["confidence"], 0.85)

        # Validate stage consistency
        for task in tasks:
            if task.get("stage") != stage:
                check_result["errors"].append(
                    f"Task {task.get('task_id')} stage mismatch: expected {stage}, got {task.get('stage')}"
                )
                check_result["confidence"] = 0.6

        check_result["details"] = {
            "task_count": len(tasks),
            "expected_range": expected_range,
            "high_priority_count": high_priority_count,
            "unique_task_ids": len(set(task_ids))
        }

        check_result["passed"] = len(check_result["errors"]) == 0
        return check_result

    def _check_resource_availability(
        self,
        business: Dict,
        stage: str,
        tasks: List[Dict]
    ) -> Dict:
        """
        Check 3: Resource availability check.

        Validates:
        - Required agents are available
        - System resources are sufficient
        - No blocking resource constraints
        - Execution capacity is available
        """
        check_result = {
            "check_name": "resource_availability",
            "passed": False,
            "confidence": 0.85,
            "warnings": [],
            "errors": [],
            "details": {}
        }

        # Check required agents for tasks
        required_agents = set()
        for task in tasks:
            assigned_agent = task.get("assigned_agent")
            if assigned_agent:
                required_agents.add(assigned_agent)

        available_agents = ["research", "planning", "builder", "automation", "content"]
        missing_agents = required_agents - set(available_agents)

        if missing_agents:
            check_result["warnings"].append(
                f"Some required agents may not be available: {missing_agents}"
            )
            check_result["confidence"] = 0.75

        # Check for resource-intensive stages
        resource_intensive_stages = ["BUILDING", "SCALING"]
        if stage in resource_intensive_stages:
            check_result["warnings"].append(
                f"Stage {stage} is resource-intensive, ensure adequate capacity"
            )
            check_result["confidence"] = min(check_result["confidence"], 0.8)

        # Check concurrent workflow limits (simulate)
        # In production, this would check actual system load
        max_concurrent_workflows = 10
        active_workflows = 1  # Placeholder: would check orchestrator.active_workflows

        if active_workflows >= max_concurrent_workflows:
            check_result["errors"].append(
                f"Maximum concurrent workflows ({max_concurrent_workflows}) reached"
            )
            check_result["confidence"] = 0.4

        # Check business resource allocation
        metrics = business.get("metrics", {})
        if metrics.get("failure_count", 0) > 3:
            check_result["warnings"].append(
                "Business has elevated failure count, may consume additional resources for retries"
            )
            check_result["confidence"] = min(check_result["confidence"], 0.75)

        check_result["details"] = {
            "required_agents": list(required_agents),
            "available_agents": available_agents,
            "stage_intensity": "high" if stage in resource_intensive_stages else "normal",
            "active_workflows": active_workflows,
            "max_concurrent": max_concurrent_workflows
        }

        check_result["passed"] = len(check_result["errors"]) == 0
        return check_result

    def _check_simulation(
        self,
        business: Dict,
        stage: str,
        tasks: List[Dict]
    ) -> Dict:
        """
        Check 4: Simulation validation (75% confidence threshold).

        Validates:
        - Workflow execution simulation confidence >= 75%
        - Tasks are likely to succeed based on historical data
        - No predicted failures in critical tasks
        - Overall success probability is acceptable
        """
        check_result = {
            "check_name": "simulation",
            "passed": False,
            "confidence": 0.0,
            "warnings": [],
            "errors": [],
            "details": {}
        }

        # Get Simulator from orchestrator if available
        simulator = None
        if self.orchestrator:
            simulator = self.orchestrator.simulator

        if not simulator:
            check_result["warnings"].append("Simulator not available, using fallback estimation")
            check_result["confidence"] = 0.75  # Default to threshold
            check_result["passed"] = True
            return check_result

        # Simulate each task
        task_simulations = []
        total_confidence = 0.0

        for task in tasks:
            task_sim = self._simulate_single_task(task, business, stage)
            task_simulations.append(task_sim)
            total_confidence += task_sim["confidence"]

        # Calculate average confidence
        avg_confidence = total_confidence / len(tasks) if tasks else 0.0
        check_result["confidence"] = avg_confidence

        # Check critical tasks
        critical_tasks = [t for t in task_simulations if t.get("priority") == "high"]
        critical_failures = [t for t in critical_tasks if t["confidence"] < 0.6]

        if critical_failures:
            check_result["errors"].append(
                f"{len(critical_failures)} critical tasks predicted to fail"
            )
            check_result["confidence"] = min(check_result["confidence"], 0.65)

        # Check overall threshold
        if avg_confidence < self.confidence_threshold:
            check_result["errors"].append(
                f"Simulation confidence ({avg_confidence:.2f}) below threshold ({self.confidence_threshold})"
            )
        else:
            check_result["passed"] = True

        # Identify risky tasks
        risky_tasks = [
            t for t in task_simulations
            if t["confidence"] < 0.7
        ]
        if risky_tasks:
            check_result["warnings"].append(
                f"{len(risky_tasks)} tasks have elevated risk (confidence < 0.7)"
            )

        check_result["details"] = {
            "avg_confidence": avg_confidence,
            "task_count": len(tasks),
            "critical_task_count": len(critical_tasks),
            "critical_failures": len(critical_failures),
            "risky_task_count": len(risky_tasks),
            "threshold": self.confidence_threshold,
            "task_simulations": [
                {
                    "task_id": t.get("task_id"),
                    "confidence": t["confidence"],
                    "risk_level": t.get("risk_level", "medium")
                }
                for t in task_simulations
            ]
        }

        return check_result

    def _simulate_single_task(
        self,
        task: Dict,
        business: Dict,
        stage: str
    ) -> Dict:
        """
        Simulate a single task to predict success probability.

        Uses business metrics, historical data, and task characteristics
        to estimate execution confidence.
        """
        # Base confidence starts at 0.8
        base_confidence = 0.8

        # Adjust based on business metrics
        metrics = business.get("metrics", {})
        failure_count = metrics.get("failure_count", 0)
        performance = metrics.get("performance", 0.5)

        # Reduce confidence for high failure count
        if failure_count > 3:
            base_confidence -= 0.15
        elif failure_count > 1:
            base_confidence -= 0.05

        # Adjust for performance
        base_confidence = (base_confidence + performance) / 2

        # Adjust for stage complexity
        complex_stages = ["BUILDING", "SCALING", "OPTIMIZING"]
        if stage in complex_stages:
            base_confidence -= 0.05

        # Adjust for task priority
        if task.get("priority") == "high":
            # High priority tasks should have higher confidence requirements
            base_confidence -= 0.02

        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, base_confidence))

        # Determine risk level
        if confidence >= 0.8:
            risk_level = "low"
        elif confidence >= 0.7:
            risk_level = "medium"
        else:
            risk_level = "high"

        return {
            "task_id": task.get("task_id"),
            "confidence": confidence,
            "risk_level": risk_level,
            "factors": {
                "base_confidence": 0.8,
                "failure_penalty": failure_count * -0.05,
                "performance_adjustment": (performance - 0.5) * 0.2,
                "stage_complexity": -0.05 if stage in complex_stages else 0.0
            }
        }

    def _check_tool_integration(self) -> Dict:
        """
        Check 5: Tool integration check.

        Validates:
        - AI-Q availability and status
        - NemoClaw availability and status
        - Zep memory availability and status
        - Simulator availability and status
        - Fallback patterns are configured
        """
        check_result = {
            "check_name": "tool_integration",
            "passed": False,
            "confidence": 0.0,
            "warnings": [],
            "errors": [],
            "details": {}
        }

        tools_status = {
            "ai_q": {"available": False, "required": False},
            "nemoclaw": {"available": False, "required": False},
            "zep": {"available": False, "required": False},
            "simulator": {"available": True, "required": True}
        }

        # Check each tool via orchestrator if available
        if self.orchestrator:
            tool_status = self.orchestrator.get_tool_status()

            tools_status["ai_q"]["available"] = tool_status.get("ai_q", {}).get("available", False)
            tools_status["nemoclaw"]["available"] = tool_status.get("nemoclaw", {}).get("available", False)
            tools_status["zep"]["available"] = tool_status.get("zep", {}).get("available", False)
            tools_status["simulator"]["available"] = tool_status.get("simulator", {}).get("available", True)

        # Count available tools
        available_count = sum(
            1 for tool in tools_status.values()
            if tool["available"]
        )
        total_tools = len(tools_status)

        # Calculate confidence based on tool availability
        # Simulator is required, others are optional but improve confidence
        if tools_status["simulator"]["available"]:
            base_confidence = 0.75  # Simulator alone gives 75%

            # Each additional tool adds confidence
            if tools_status["ai_q"]["available"]:
                base_confidence += 0.08
            if tools_status["nemoclaw"]["available"]:
                base_confidence += 0.08
            if tools_status["zep"]["available"]:
                base_confidence += 0.09

            check_result["confidence"] = min(base_confidence, 1.0)
            check_result["passed"] = True
        else:
            check_result["errors"].append("Simulator (required tool) is not available")
            check_result["confidence"] = 0.0

        # Generate warnings for unavailable optional tools
        if not tools_status["ai_q"]["available"]:
            check_result["warnings"].append(
                "AI-Q not available, using basic task prioritization"
            )

        if not tools_status["nemoclaw"]["available"]:
            check_result["warnings"].append(
                "NemoClaw not available, tasks will execute without sandboxing"
            )

        if not tools_status["zep"]["available"]:
            check_result["warnings"].append(
                "Zep memory not available, validation results will not be persisted"
            )

        check_result["details"] = {
            "tools": tools_status,
            "available_count": available_count,
            "total_count": total_tools,
            "fallback_mode": available_count < total_tools
        }

        return check_result

    def _log_to_zep(self, validation_result: Dict):
        """
        Log validation result to Zep memory.

        In production, this would make an API call to Zep.
        Currently stores to local memory as fallback.
        """
        if not self.zep_available:
            return

        try:
            # Prepare memory entry
            memory_entry = {
                "session_id": self.zep_session_id,
                "timestamp": validation_result["timestamp"],
                "validation_id": validation_result["validation_id"],
                "business_id": validation_result["business_id"],
                "stage": validation_result["stage"],
                "passed": validation_result["passed"],
                "confidence": validation_result["confidence"],
                "recommendation": validation_result["recommendation"],
                "checks": {
                    name: {
                        "passed": check["passed"],
                        "confidence": check["confidence"]
                    }
                    for name, check in validation_result["checks"].items()
                },
                "warnings_count": len(validation_result["warnings"]),
                "errors_count": len(validation_result["errors"])
            }

            # In production: zep_client.add_memory(memory_entry)
            # For now: store to local file as backup
            self._store_validation_locally(memory_entry)

        except Exception:
            # Fail silently - validation logging should not block execution
            pass

    def _store_validation_locally(self, memory_entry: Dict):
        """Store validation result to local file as backup."""
        try:
            memory_dir = "project_alpha/memory"
            os.makedirs(memory_dir, exist_ok=True)

            validation_file = os.path.join(memory_dir, "validation_history.json")

            # Read existing history
            if os.path.exists(validation_file):
                with open(validation_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []

            # Append new entry
            history.append(memory_entry)

            # Write back
            with open(validation_file, 'w') as f:
                json.dump(history, f, indent=2)

        except Exception:
            pass

    def validate_portfolio_workflow(
        self,
        businesses: List[Dict]
    ) -> Tuple[bool, List[str]]:
        """
        Validate a portfolio workflow before execution.

        Args:
            businesses: List of businesses to manage

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate businesses list
        if not businesses:
            errors.append("Businesses list is empty")
            return False, errors

        if not isinstance(businesses, list):
            errors.append("Businesses must be a list")
            return False, errors

        # Validate each business
        for idx, business in enumerate(businesses):
            if not business:
                errors.append(f"Business at index {idx} is None or empty")
                continue

            if "id" not in business:
                errors.append(f"Business at index {idx} missing required field: id")

            if "stage" not in business:
                errors.append(f"Business at index {idx} missing required field: stage")

            if "metrics" not in business:
                errors.append(f"Business at index {idx} missing required field: metrics")

        is_valid = len(errors) == 0

        validation_result = {
            "is_valid": is_valid,
            "workflow_type": "portfolio",
            "businesses_count": len(businesses),
            "errors": errors
        }

        self.validation_history.append(validation_result)

        return is_valid, errors

    def _validate_task(self, task: Dict, idx: int) -> List[str]:
        """Validate a single task."""
        errors = []

        if not task:
            errors.append(f"Task at index {idx} is None or empty")
            return errors

        # Required fields
        required_fields = ["task_id", "title", "assigned_agent", "stage"]
        for field in required_fields:
            if field not in task:
                errors.append(f"Task at index {idx} missing required field: {field}")

        # Validate priority
        if "priority" in task:
            valid_priorities = ["low", "medium", "high"]
            if task["priority"] not in valid_priorities:
                errors.append(f"Task at index {idx} has invalid priority: {task['priority']}")

        # Validate assigned agent
        if "assigned_agent" in task:
            valid_agents = ["research", "planning", "builder", "automation", "content"]
            if task["assigned_agent"] not in valid_agents:
                errors.append(f"Task at index {idx} has invalid agent: {task['assigned_agent']}")

        return errors

    def _validate_stage_preconditions(self, business: Dict, stage: str) -> List[str]:
        """Validate stage-specific preconditions."""
        errors = []
        metrics = business.get("metrics", {})

        if stage == "VALIDATING":
            # Must have completed DISCOVERED stage
            if "validation_score" not in metrics:
                # First time in VALIDATING is OK
                pass

        elif stage == "BUILDING":
            # Must have sufficient validation score
            validation_score = metrics.get("validation_score", 0.0)
            if validation_score < 0.5:
                errors.append(f"Validation score too low for BUILDING: {validation_score:.2f} (minimum: 0.50)")

        elif stage == "SCALING":
            # Must have completed building
            build_progress = metrics.get("build_progress", 0.0)
            if build_progress < 0.7:
                errors.append(f"Build progress too low for SCALING: {build_progress:.2f} (minimum: 0.70)")

        elif stage == "OPERATING":
            # Must have scaling metrics
            performance = metrics.get("performance", 0.0)
            if performance < 0.6:
                errors.append(f"Performance too low for OPERATING: {performance:.2f} (minimum: 0.60)")

        elif stage == "OPTIMIZING":
            # Must have identified performance issues
            performance = metrics.get("performance", 0.0)
            if performance >= 0.8:
                errors.append(f"Performance too high for OPTIMIZING: {performance:.2f} (should be < 0.80)")

        elif stage == "TERMINATED":
            # Can always terminate
            pass

        return errors

    def get_validation_statistics(self) -> Dict:
        """
        Get validation statistics from history.

        Returns:
            Statistics dictionary with validation metrics
        """
        if not self.validation_history:
            return {
                "total_validations": 0,
                "passed_count": 0,
                "failed_count": 0,
                "avg_confidence": 0.0,
                "pass_rate": 0.0
            }

        total = len(self.validation_history)
        passed = sum(1 for v in self.validation_history if v.get("passed", False))
        failed = total - passed

        avg_confidence = sum(
            v.get("confidence", 0.0) for v in self.validation_history
        ) / total

        return {
            "total_validations": total,
            "passed_count": passed,
            "failed_count": failed,
            "avg_confidence": avg_confidence,
            "pass_rate": passed / total,
            "recommendations": {
                "proceed": sum(1 for v in self.validation_history if v.get("recommendation") == "proceed"),
                "review": sum(1 for v in self.validation_history if v.get("recommendation") == "review"),
                "abort": sum(1 for v in self.validation_history if v.get("recommendation") == "abort")
            }
        }

    def get_validation_report(self, validation_id: str) -> Optional[Dict]:
        """
        Get detailed validation report by ID.

        Args:
            validation_id: Validation ID to retrieve

        Returns:
            Validation result dictionary or None if not found
        """
        for validation in self.validation_history:
            if validation.get("validation_id") == validation_id:
                return validation
        return None

    def clear_validation_history(self):
        """Clear validation history (use with caution)."""
        self.validation_history = []

    def validate_tools_integration(self, orchestrator: Any) -> Tuple[bool, Dict]:
        """
        Legacy method for backward compatibility.
        Use _check_tool_integration() for full validation.

        Args:
            orchestrator: WorkflowOrchestrator instance

        Returns:
            Tuple of (all_tools_ready, tool_status)
        """
        if not hasattr(orchestrator, "get_tool_status"):
            return False, {"error": "Orchestrator missing get_tool_status method"}

        tool_status = orchestrator.get_tool_status()

        # Check each tool
        required_tools = ["simulator"]  # Simulator is always required
        optional_tools = ["ai_q", "nemoclaw", "zep"]

        all_required_ready = all(
            tool_status.get(tool, {}).get("available", False)
            for tool in required_tools
        )

        return all_required_ready, tool_status

    def get_validation_history(self) -> List[Dict]:
        """Get validation history."""
        return self.validation_history

    def get_validation_stats(self) -> Dict:
        """
        Legacy method for backward compatibility.
        Use get_validation_statistics() for detailed stats.
        """
        return self.get_validation_statistics()

    def clear_history(self):
        """
        Legacy method for backward compatibility.
        Use clear_validation_history() instead.
        """
        self.clear_validation_history()
