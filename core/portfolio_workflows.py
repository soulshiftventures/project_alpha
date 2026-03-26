"""
Portfolio Workflows for Project Alpha Phase 5
Manages up to 5 concurrent businesses with intelligent task prioritization,
load balancing, and portfolio-level health monitoring.
"""

import heapq
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class PortfolioWorkflows:
    """
    Portfolio-level workflow management for multiple concurrent businesses.

    Features:
    - Manage up to 5 concurrent businesses
    - Rank and prioritize tasks across portfolio
    - Schedule stage transitions automatically
    - Portfolio-level task generation and execution
    - Load balancing across businesses
    - Portfolio health monitoring with early warnings
    """

    def __init__(self, max_concurrent_businesses: int = 5):
        """
        Initialize portfolio workflows.

        Args:
            max_concurrent_businesses: Maximum number of businesses to manage (default: 5)
        """
        self.max_concurrent_businesses = max_concurrent_businesses
        self.portfolio = {}  # business_id -> business_dict
        self.task_queue = []  # Priority queue: (priority_score, timestamp, task)
        self.execution_history = []
        self.load_balancer = LoadBalancer()
        self.health_monitor = PortfolioHealthMonitor()

    def add_business(self, business: Dict) -> Dict:
        """
        Add a business to the portfolio.

        Args:
            business: Business dictionary

        Returns:
            Result dictionary with status
        """
        if len(self.portfolio) >= self.max_concurrent_businesses:
            return {
                "status": "rejected",
                "reason": "portfolio_full",
                "current_count": len(self.portfolio),
                "max_allowed": self.max_concurrent_businesses,
                "suggestion": "Wait for a business to complete or terminate one"
            }

        business_id = business["id"]

        if business_id in self.portfolio:
            return {
                "status": "rejected",
                "reason": "already_exists",
                "business_id": business_id
            }

        # Initialize portfolio-specific metadata
        business["portfolio_metadata"] = {
            "added_at": datetime.utcnow().isoformat(),
            "priority_score": self._calculate_priority_score(business),
            "resource_allocation": 1.0 / (len(self.portfolio) + 1),  # Equal allocation initially
            "last_update": datetime.utcnow().isoformat()
        }

        self.portfolio[business_id] = business

        # Rebalance resources across portfolio
        self._rebalance_resources()

        return {
            "status": "added",
            "business_id": business_id,
            "portfolio_size": len(self.portfolio),
            "priority_score": business["portfolio_metadata"]["priority_score"],
            "resource_allocation": business["portfolio_metadata"]["resource_allocation"]
        }

    def remove_business(self, business_id: str) -> Dict:
        """
        Remove a business from the portfolio.

        Args:
            business_id: Business ID to remove

        Returns:
            Result dictionary
        """
        if business_id not in self.portfolio:
            return {
                "status": "not_found",
                "business_id": business_id
            }

        business = self.portfolio.pop(business_id)

        # Rebalance resources
        self._rebalance_resources()

        return {
            "status": "removed",
            "business_id": business_id,
            "business_stage": business["stage"],
            "portfolio_size": len(self.portfolio)
        }

    def manage_portfolio(
        self,
        businesses: List[Dict],
        orchestrator: Any
    ) -> Dict:
        """
        Main portfolio management function.
        Coordinates task prioritization, execution, and health monitoring across all businesses.

        Args:
            businesses: List of all businesses in portfolio
            orchestrator: WorkflowOrchestrator instance

        Returns:
            Portfolio management result
        """
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "portfolio_size": len(businesses),
            "businesses_processed": 0,
            "total_tasks_executed": 0,
            "stage_transitions": [],
            "health_status": {},
            "load_balance_report": {},
            "execution_details": []
        }

        # Update portfolio with current businesses
        for business in businesses:
            if business["id"] not in self.portfolio:
                self.add_business(business)

        # Generate and prioritize all tasks across portfolio
        all_tasks = self._generate_portfolio_tasks(businesses)
        prioritized_tasks = self._prioritize_tasks(all_tasks)

        # Load balance task execution
        balanced_execution_plan = self.load_balancer.balance_workload(
            businesses=businesses,
            tasks=prioritized_tasks
        )

        result["load_balance_report"] = balanced_execution_plan["report"]

        # Execute tasks according to balanced plan
        for business_id, task_batch in balanced_execution_plan["execution_schedule"].items():
            business = next(b for b in businesses if b["id"] == business_id)

            execution_result = self._execute_business_tasks(
                business=business,
                tasks=task_batch,
                orchestrator=orchestrator
            )

            result["execution_details"].append(execution_result)
            result["total_tasks_executed"] += execution_result["tasks_completed"]
            result["businesses_processed"] += 1

            # Check for stage transitions
            transition = self._check_stage_transition(business, execution_result)
            if transition["should_transition"]:
                result["stage_transitions"].append(transition)

        # Monitor portfolio health
        health_status = self.health_monitor.assess_portfolio_health(
            portfolio=self.portfolio,
            execution_results=result["execution_details"]
        )

        result["health_status"] = health_status

        # Store execution history
        self.execution_history.append(result)

        return result

    def _generate_portfolio_tasks(self, businesses: List[Dict]) -> List[Dict]:
        """
        Generate all tasks for all businesses in portfolio.

        Args:
            businesses: List of businesses

        Returns:
            List of all tasks with business context
        """
        all_tasks = []

        for business in businesses:
            # Import stage_workflows to get tasks
            from . import stage_workflows

            stage_workflows_instance = stage_workflows.StageWorkflows()
            business_tasks = stage_workflows_instance.get_tasks_for_stage(
                stage=business["stage"],
                business=business
            )

            # Enrich tasks with portfolio metadata
            for task in business_tasks:
                task["business_id"] = business["id"]
                task["business_stage"] = business["stage"]
                task["business_priority"] = business.get("portfolio_metadata", {}).get("priority_score", 0.5)
                all_tasks.append(task)

        return all_tasks

    def _prioritize_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """
        Prioritize tasks across entire portfolio using multi-factor scoring.

        Priority factors:
        1. Business priority score (0-1)
        2. Task priority (high=1.0, medium=0.6, low=0.3)
        3. Stage urgency (BUILDING/SCALING=1.0, others=0.7)
        4. Time sensitivity (overdue tasks get higher priority)

        Args:
            tasks: List of tasks from all businesses

        Returns:
            Sorted list of tasks (highest priority first)
        """
        scored_tasks = []

        for task in tasks:
            # Factor 1: Business priority
            business_priority = task.get("business_priority", 0.5)

            # Factor 2: Task priority
            task_priority_map = {"high": 1.0, "medium": 0.6, "low": 0.3}
            task_priority = task_priority_map.get(task.get("priority", "medium"), 0.6)

            # Factor 3: Stage urgency
            urgent_stages = ["BUILDING", "SCALING", "VALIDATING"]
            stage_urgency = 1.0 if task.get("business_stage") in urgent_stages else 0.7

            # Factor 4: Time sensitivity (simplified - would check deadlines in production)
            time_sensitivity = 1.0

            # Composite score
            composite_score = (
                business_priority * 0.35 +
                task_priority * 0.30 +
                stage_urgency * 0.25 +
                time_sensitivity * 0.10
            )

            scored_tasks.append((composite_score, task))

        # Sort by composite score (descending)
        scored_tasks.sort(key=lambda x: x[0], reverse=True)

        return [task for score, task in scored_tasks]

    def _execute_business_tasks(
        self,
        business: Dict,
        tasks: List[Dict],
        orchestrator: Any
    ) -> Dict:
        """
        Execute tasks for a single business.

        Args:
            business: Business dictionary
            tasks: Tasks to execute
            orchestrator: WorkflowOrchestrator instance

        Returns:
            Execution result
        """
        result = {
            "business_id": business["id"],
            "business_stage": business["stage"],
            "started_at": datetime.utcnow().isoformat(),
            "tasks_total": len(tasks),
            "tasks_completed": 0,
            "tasks_failed": 0,
            "task_results": []
        }

        for task in tasks:
            task_result = orchestrator._execute_task_with_tools(
                task=task,
                business=business,
                stage=business["stage"],
                stage_workflows_module=None  # Will use fallback or direct execution
            )

            result["task_results"].append(task_result)

            if task_result.get("status") == "completed":
                result["tasks_completed"] += 1
            else:
                result["tasks_failed"] += 1

        result["completed_at"] = datetime.utcnow().isoformat()
        result["success_rate"] = result["tasks_completed"] / max(result["tasks_total"], 1)

        return result

    def _check_stage_transition(self, business: Dict, execution_result: Dict) -> Dict:
        """
        Check if business should transition to next stage based on execution results.

        Args:
            business: Business dictionary
            execution_result: Task execution result

        Returns:
            Transition decision dictionary
        """
        current_stage = business["stage"]

        # Stage transition criteria
        transitions = {
            "DISCOVERED": {
                "next": "VALIDATING",
                "criteria": {
                    "min_success_rate": 0.75,
                    "min_tasks_completed": 3
                }
            },
            "VALIDATING": {
                "next": "BUILDING",
                "criteria": {
                    "min_success_rate": 0.70,
                    "min_tasks_completed": 5,
                    "validation_score": 0.65
                }
            },
            "BUILDING": {
                "next": "SCALING",
                "criteria": {
                    "min_success_rate": 0.80,
                    "min_tasks_completed": 6
                }
            },
            "SCALING": {
                "next": "OPERATING",
                "criteria": {
                    "min_success_rate": 0.75,
                    "min_tasks_completed": 5,
                    "performance": 0.80
                }
            },
            "OPERATING": {
                "next": "OPTIMIZING",
                "criteria": {
                    "min_success_rate": 0.70,
                    "performance": 0.60  # If performance drops, optimize
                }
            },
            "OPTIMIZING": {
                "next": "OPERATING",
                "criteria": {
                    "min_success_rate": 0.75,
                    "performance": 0.75  # Return to operations when optimized
                }
            }
        }

        transition_config = transitions.get(current_stage)

        if not transition_config:
            return {
                "should_transition": False,
                "current_stage": current_stage,
                "reason": "No transition defined for this stage"
            }

        criteria = transition_config["criteria"]
        success_rate = execution_result.get("success_rate", 0)
        tasks_completed = execution_result.get("tasks_completed", 0)

        # Check criteria
        meets_success_rate = success_rate >= criteria.get("min_success_rate", 0.75)
        meets_task_count = tasks_completed >= criteria.get("min_tasks_completed", 0)

        # Additional criteria checks
        additional_checks = True

        if "validation_score" in criteria:
            validation_score = business.get("metrics", {}).get("validation_score", 0)
            additional_checks = additional_checks and (validation_score >= criteria["validation_score"])

        if "performance" in criteria:
            performance = business.get("metrics", {}).get("performance", 0)
            additional_checks = additional_checks and (performance >= criteria["performance"])

        should_transition = meets_success_rate and meets_task_count and additional_checks

        return {
            "should_transition": should_transition,
            "business_id": business["id"],
            "current_stage": current_stage,
            "next_stage": transition_config["next"] if should_transition else current_stage,
            "success_rate": success_rate,
            "tasks_completed": tasks_completed,
            "criteria_met": {
                "success_rate": meets_success_rate,
                "task_count": meets_task_count,
                "additional": additional_checks
            }
        }

    def _calculate_priority_score(self, business: Dict) -> float:
        """
        Calculate priority score for a business (0.0 to 1.0).

        Factors:
        - Stage (BUILDING/SCALING are higher priority)
        - Opportunity score
        - Current performance
        - Time in current stage

        Args:
            business: Business dictionary

        Returns:
            Priority score (0.0 to 1.0)
        """
        stage = business.get("stage", "DISCOVERED")
        opportunity_score = business.get("opportunity", {}).get("score", 0.5)
        performance = business.get("metrics", {}).get("performance", 0.5)

        # Stage weight
        stage_weights = {
            "DISCOVERED": 0.5,
            "VALIDATING": 0.7,
            "BUILDING": 1.0,
            "SCALING": 0.9,
            "OPERATING": 0.6,
            "OPTIMIZING": 0.7,
            "TERMINATED": 0.0
        }
        stage_weight = stage_weights.get(stage, 0.5)

        # Composite priority score
        priority_score = (
            stage_weight * 0.40 +
            opportunity_score * 0.35 +
            performance * 0.25
        )

        return round(min(max(priority_score, 0.0), 1.0), 2)

    def _rebalance_resources(self):
        """
        Rebalance resource allocation across portfolio businesses.

        Higher priority businesses get more resources.
        """
        if not self.portfolio:
            return

        # Calculate total priority
        total_priority = sum(
            b.get("portfolio_metadata", {}).get("priority_score", 0.5)
            for b in self.portfolio.values()
        )

        # Allocate resources proportionally
        for business in self.portfolio.values():
            priority_score = business.get("portfolio_metadata", {}).get("priority_score", 0.5)
            business["portfolio_metadata"]["resource_allocation"] = priority_score / max(total_priority, 0.01)
            business["portfolio_metadata"]["last_update"] = datetime.utcnow().isoformat()

    def get_portfolio_status(self) -> Dict:
        """
        Get current portfolio status.

        Returns:
            Portfolio status dictionary
        """
        stage_distribution = defaultdict(int)
        total_priority = 0.0

        for business in self.portfolio.values():
            stage_distribution[business["stage"]] += 1
            total_priority += business.get("portfolio_metadata", {}).get("priority_score", 0.5)

        avg_priority = total_priority / max(len(self.portfolio), 1)

        return {
            "portfolio_size": len(self.portfolio),
            "max_capacity": self.max_concurrent_businesses,
            "utilization": len(self.portfolio) / self.max_concurrent_businesses,
            "stage_distribution": dict(stage_distribution),
            "average_priority": round(avg_priority, 2),
            "businesses": [
                {
                    "id": b["id"],
                    "stage": b["stage"],
                    "priority": b.get("portfolio_metadata", {}).get("priority_score", 0.5),
                    "resource_allocation": b.get("portfolio_metadata", {}).get("resource_allocation", 0.0)
                }
                for b in self.portfolio.values()
            ]
        }


class LoadBalancer:
    """
    Load balancer for distributing tasks across businesses.
    """

    def balance_workload(
        self,
        businesses: List[Dict],
        tasks: List[Dict]
    ) -> Dict:
        """
        Balance task workload across businesses.

        Args:
            businesses: List of businesses
            tasks: List of prioritized tasks

        Returns:
            Balanced execution schedule
        """
        # Group tasks by business
        tasks_by_business = defaultdict(list)

        for task in tasks:
            business_id = task.get("business_id")
            tasks_by_business[business_id].append(task)

        # Calculate load per business
        load_report = {}

        for business in businesses:
            business_id = business["id"]
            business_tasks = tasks_by_business.get(business_id, [])

            load_report[business_id] = {
                "task_count": len(business_tasks),
                "high_priority_count": sum(1 for t in business_tasks if t.get("priority") == "high"),
                "stage": business["stage"],
                "estimated_time": len(business_tasks) * 0.5  # Mock: 0.5 units per task
            }

        return {
            "execution_schedule": dict(tasks_by_business),
            "report": load_report,
            "total_tasks": len(tasks),
            "businesses_count": len(businesses)
        }


class PortfolioHealthMonitor:
    """
    Monitor portfolio health and provide early warnings.
    """

    def assess_portfolio_health(
        self,
        portfolio: Dict,
        execution_results: List[Dict]
    ) -> Dict:
        """
        Assess overall portfolio health.

        Args:
            portfolio: Portfolio dictionary (business_id -> business)
            execution_results: Recent execution results

        Returns:
            Health assessment
        """
        if not portfolio:
            return {
                "overall_health": "empty",
                "score": 0.0,
                "warnings": ["Portfolio is empty"],
                "recommendations": ["Add businesses to portfolio"]
            }

        # Calculate metrics
        avg_success_rate = sum(
            r.get("success_rate", 0)
            for r in execution_results
        ) / max(len(execution_results), 1)

        # Count businesses by stage
        stage_counts = defaultdict(int)
        for business in portfolio.values():
            stage_counts[business["stage"]] += 1

        # Health score calculation
        health_score = avg_success_rate

        # Penalties
        if stage_counts.get("TERMINATED", 0) > len(portfolio) * 0.3:
            health_score -= 0.2  # Too many terminated businesses

        if stage_counts.get("DISCOVERED", 0) == len(portfolio):
            health_score -= 0.1  # No progression

        # Warnings
        warnings = []
        if avg_success_rate < 0.70:
            warnings.append("Low average success rate across portfolio")

        if len(portfolio) < 3:
            warnings.append("Portfolio under-diversified (less than 3 businesses)")

        if stage_counts.get("TERMINATED", 0) > 2:
            warnings.append(f"High termination count: {stage_counts['TERMINATED']} businesses")

        # Recommendations
        recommendations = []
        if len(portfolio) < 5:
            recommendations.append("Consider adding more businesses to portfolio")

        if stage_counts.get("BUILDING", 0) == 0 and stage_counts.get("SCALING", 0) == 0:
            recommendations.append("No businesses in active development stages")

        if avg_success_rate < 0.75:
            recommendations.append("Review task execution processes to improve success rate")

        # Overall health status
        if health_score >= 0.80:
            overall_health = "excellent"
        elif health_score >= 0.65:
            overall_health = "good"
        elif health_score >= 0.50:
            overall_health = "fair"
        else:
            overall_health = "poor"

        return {
            "overall_health": overall_health,
            "score": round(health_score, 2),
            "metrics": {
                "portfolio_size": len(portfolio),
                "avg_success_rate": round(avg_success_rate, 2),
                "stage_distribution": dict(stage_counts)
            },
            "warnings": warnings,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }
