"""
Lifecycle Manager for project_alpha
Manages business lifecycle states and transitions
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class LifecycleManager:
    """Manages business lifecycle states and transitions."""

    STAGES = ["DISCOVERED", "VALIDATING", "BUILDING", "SCALING", "OPERATING", "OPTIMIZING", "TERMINATED"]

    def __init__(self, businesses_file: str = None):
        # Allow env override for testing isolation
        if businesses_file is None:
            businesses_file = os.environ.get(
                "PROJECT_ALPHA_BUSINESSES_FILE",
                "project_alpha/businesses/businesses.json"
            )
        self.businesses_file = businesses_file
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Ensure businesses file exists."""
        if not os.path.exists(self.businesses_file):
            os.makedirs(os.path.dirname(self.businesses_file), exist_ok=True)
            with open(self.businesses_file, 'w') as f:
                json.dump([], f)

    def load_businesses(self) -> List[Dict]:
        """Load all businesses from storage."""
        try:
            with open(self.businesses_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_businesses(self, businesses: List[Dict]):
        """Save all businesses to storage."""
        with open(self.businesses_file, 'w') as f:
            json.dump(businesses, f, indent=2)

    def create_business(self, opportunity: Dict) -> Dict:
        """
        Create a new business from an opportunity.

        Args:
            opportunity: Opportunity dictionary with idea, description, potential

        Returns:
            Business dictionary in DISCOVERED stage
        """
        timestamp = _utc_now().isoformat()

        business = {
            "id": str(uuid.uuid4()),
            "opportunity": {
                "idea": opportunity.get("idea", "Unknown opportunity"),
                "description": opportunity.get("description", ""),
                "potential": opportunity.get("potential", "medium")
            },
            "stage": "DISCOVERED",
            "metrics": {
                "validation_score": 0.0,
                "build_progress": 0.0,
                "revenue": 0.0,
                "performance": 0.0,
                "stability": 0.0,
                "failure_count": 0,
                "validation_attempts": 0,
                "optimization_attempts": 0,
                "performance_history": []
            },
            "tasks": [],
            "history": [
                {
                    "timestamp": timestamp,
                    "stage": "DISCOVERED",
                    "event": "Business created",
                    "details": {"opportunity": opportunity.get("idea", "Unknown")}
                }
            ],
            "created_at": timestamp,
            "updated_at": timestamp
        }

        businesses = self.load_businesses()
        businesses.append(business)
        self.save_businesses(businesses)

        return business

    def get_business(self, business_id: str) -> Optional[Dict]:
        """Get a specific business by ID."""
        businesses = self.load_businesses()
        for business in businesses:
            if business["id"] == business_id:
                return business
        return None

    def update_business(self, business_id: str, updates: Dict):
        """Update a business."""
        businesses = self.load_businesses()
        for business in businesses:
            if business["id"] == business_id:
                business.update(updates)
                business["updated_at"] = _utc_now().isoformat()
                self.save_businesses(businesses)
                return
        raise ValueError(f"Business {business_id} not found")

    def update_stage(self, business_id: str, new_stage: str, reason: str):
        """
        Transition business to new stage.

        Args:
            business_id: ID of business to update
            new_stage: New stage name
            reason: Reason for transition
        """
        if new_stage not in self.STAGES:
            raise ValueError(f"Invalid stage: {new_stage}")

        businesses = self.load_businesses()
        for business in businesses:
            if business["id"] == business_id:
                old_stage = business["stage"]
                business["stage"] = new_stage
                business["updated_at"] = _utc_now().isoformat()

                # Add history entry
                business["history"].append({
                    "timestamp": _utc_now().isoformat(),
                    "stage": new_stage,
                    "event": f"Transitioned from {old_stage} to {new_stage}",
                    "details": {"reason": reason}
                })

                self.save_businesses(businesses)
                return

        raise ValueError(f"Business {business_id} not found")

    def update_metrics(self, business_id: str, metrics: Dict):
        """
        Update business metrics.

        Args:
            business_id: ID of business to update
            metrics: Dictionary of metrics to update
        """
        businesses = self.load_businesses()
        for business in businesses:
            if business["id"] == business_id:
                # Update metrics
                for key, value in metrics.items():
                    business["metrics"][key] = value

                # Track performance history
                if "performance" in metrics:
                    business["metrics"]["performance_history"].append({
                        "timestamp": _utc_now().isoformat(),
                        "value": metrics["performance"]
                    })
                    # Keep only last 10 measurements
                    if len(business["metrics"]["performance_history"]) > 10:
                        business["metrics"]["performance_history"] = \
                            business["metrics"]["performance_history"][-10:]

                business["updated_at"] = _utc_now().isoformat()
                self.save_businesses(businesses)
                return

        raise ValueError(f"Business {business_id} not found")

    def add_task_to_business(self, business_id: str, task_id: str):
        """Link a task to a business."""
        businesses = self.load_businesses()
        for business in businesses:
            if business["id"] == business_id:
                if task_id not in business["tasks"]:
                    business["tasks"].append(task_id)
                    business["updated_at"] = _utc_now().isoformat()
                    self.save_businesses(businesses)
                return

        raise ValueError(f"Business {business_id} not found")

    def record_history(self, business_id: str, event: str, details: Dict):
        """Record an event in business history."""
        businesses = self.load_businesses()
        for business in businesses:
            if business["id"] == business_id:
                business["history"].append({
                    "timestamp": _utc_now().isoformat(),
                    "stage": business["stage"],
                    "event": event,
                    "details": details
                })
                business["updated_at"] = _utc_now().isoformat()
                self.save_businesses(businesses)
                return

        raise ValueError(f"Business {business_id} not found")

    def get_active_businesses(self) -> List[Dict]:
        """Get all non-TERMINATED businesses."""
        businesses = self.load_businesses()
        return [b for b in businesses if b["stage"] != "TERMINATED"]

    def get_businesses_by_stage(self, stage: str) -> List[Dict]:
        """Get all businesses in a specific stage."""
        businesses = self.load_businesses()
        return [b for b in businesses if b["stage"] == stage]

    def evaluate_transition(self, business: Dict) -> Optional[str]:
        """
        Evaluate if business should transition to new stage.

        Args:
            business: Business dictionary

        Returns:
            New stage name if transition needed, None otherwise
        """
        current_stage = business["stage"]
        metrics = business["metrics"]

        if current_stage == "DISCOVERED":
            return "VALIDATING"  # Always move to validation

        elif current_stage == "VALIDATING":
            validation_attempts = metrics.get("validation_attempts", 0)

            if self._should_terminate_validation(business):
                return "TERMINATED"
            elif self._should_build(business):
                return "BUILDING"
            # Stay in VALIDATING if more attempts needed
            return None

        elif current_stage == "BUILDING":
            if self._should_terminate_building(business):
                return "TERMINATED"
            elif self._should_scale(business):
                return "SCALING"
            return None

        elif current_stage == "SCALING":
            if self._should_operate(business):
                return "OPERATING"
            return None

        elif current_stage == "OPERATING":
            if self._should_optimize(business):
                return "OPTIMIZING"
            return None

        elif current_stage == "OPTIMIZING":
            if self._should_terminate_optimization(business):
                return "TERMINATED"
            elif self._should_return_to_operating(business):
                return "OPERATING"
            return None

        elif current_stage == "TERMINATED":
            return None  # No transitions from TERMINATED

        return None

    def _should_build(self, business: Dict) -> bool:
        """Check if business should transition to BUILDING."""
        metrics = business["metrics"]
        validation_score = metrics.get("validation_score", 0.0)
        return validation_score > 0.7

    def _should_scale(self, business: Dict) -> bool:
        """Check if business should transition to SCALING."""
        metrics = business["metrics"]
        build_progress = metrics.get("build_progress", 0.0)
        failure_count = metrics.get("failure_count", 0)
        return build_progress > 0.9 and failure_count < 3

    def _should_operate(self, business: Dict) -> bool:
        """Check if business should transition to OPERATING."""
        metrics = business["metrics"]
        performance = metrics.get("performance", 0.0)
        stability = metrics.get("stability", 0.0)
        return performance > 0.8 and stability > 0.8

    def _should_optimize(self, business: Dict) -> bool:
        """Check if business should transition to OPTIMIZING."""
        metrics = business["metrics"]
        performance_history = metrics.get("performance_history", [])

        # Need at least 2 measurements
        if len(performance_history) < 2:
            return False

        # Check if performance is declining (last 2 measurements below 0.6)
        recent = performance_history[-2:]
        return all(p["value"] < 0.6 for p in recent)

    def _should_return_to_operating(self, business: Dict) -> bool:
        """Check if business should return to OPERATING from OPTIMIZING."""
        metrics = business["metrics"]
        performance = metrics.get("performance", 0.0)
        return performance > 0.7

    def _should_terminate_validation(self, business: Dict) -> bool:
        """Check if business should be terminated during validation."""
        metrics = business["metrics"]
        validation_score = metrics.get("validation_score", 0.0)
        validation_attempts = metrics.get("validation_attempts", 0)

        # Terminate if score is low after 3 attempts
        return validation_score < 0.3 and validation_attempts >= 3

    def _should_terminate_building(self, business: Dict) -> bool:
        """Check if business should be terminated during building."""
        metrics = business["metrics"]
        failure_count = metrics.get("failure_count", 0)
        return failure_count >= 5

    def _should_terminate_optimization(self, business: Dict) -> bool:
        """Check if business should be terminated during optimization."""
        metrics = business["metrics"]
        performance = metrics.get("performance", 0.0)
        optimization_attempts = metrics.get("optimization_attempts", 0)

        # Terminate if performance still low after 3 optimization attempts
        return performance < 0.4 and optimization_attempts >= 3
