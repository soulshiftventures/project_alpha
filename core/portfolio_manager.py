"""
Portfolio Manager for project_alpha
Manages multiple businesses portfolio-wide with configurable capacity management.
"""

import json
import os
from typing import Dict, List, Optional
from core.lifecycle_manager import LifecycleManager
from core.capacity_manager import (
    CapacityManager,
    CapacityCheckContext,
    CapacityDimension,
    CapacityDecision
)


class PortfolioManager:
    """Manages portfolio of multiple businesses with configurable capacity."""

    def __init__(
        self,
        max_active: Optional[int] = None,
        capacity_manager: Optional[CapacityManager] = None
    ):
        """
        Initialize portfolio manager.

        Args:
            max_active: Deprecated. Use capacity_manager instead.
                       If provided, sets soft limit on businesses dimension.
            capacity_manager: CapacityManager instance for capacity enforcement
        """
        self.lifecycle_manager = LifecycleManager()

        # Initialize or use provided capacity manager
        if capacity_manager:
            self.capacity_manager = capacity_manager
        else:
            from core.capacity_policies import CapacityPolicies
            policies = CapacityPolicies()
            self.capacity_manager = CapacityManager(capacity_policies=policies)

        # Handle legacy max_active parameter
        if max_active is not None:
            # Set as soft limit for backwards compatibility
            self.capacity_manager.set_limit(
                dimension=CapacityDimension.BUSINESSES,
                soft_limit=max_active,
                hard_limit=None,  # No hard limit by default
                description=f"Legacy max_active limit: {max_active}"
            )

    def add_business(self, business: Dict):
        """
        Add business to portfolio.

        Args:
            business: Business dictionary to add
        """
        # Business is already added via lifecycle_manager.create_business()
        # This method is here for API consistency
        pass

    def get_all_businesses(self) -> List[Dict]:
        """Get all businesses in portfolio."""
        return self.lifecycle_manager.load_businesses()

    def get_active_businesses(self) -> List[Dict]:
        """Get all non-TERMINATED businesses."""
        return self.lifecycle_manager.get_active_businesses()

    def can_add_business(self, business: Optional[Dict] = None) -> Dict:
        """
        Check if we can add more businesses using capacity manager.

        Args:
            business: Optional business dict for context (cost, domain, etc.)

        Returns:
            Dictionary with 'allowed' (bool), 'decision', 'reason', and 'details'
        """
        active = self.get_active_businesses()

        # Build capacity check context
        context = CapacityCheckContext(
            dimension=CapacityDimension.BUSINESSES,
            current_count=len(active),
            requested_increment=1
        )

        # Add business-specific context if provided
        if business:
            context.business_id = business.get("id")
            # Add cost estimate if available
            if "projected_capital" in business.get("opportunity", {}):
                context.estimated_cost = business["opportunity"]["projected_capital"]

        # Check capacity
        result = self.capacity_manager.check_capacity(context)

        return {
            "allowed": result.decision in [CapacityDecision.ALLOWED, CapacityDecision.WARNING],
            "decision": result.decision.value,
            "reason": result.reason,
            "warnings": result.warnings,
            "recommendations": result.recommendations,
            "details": {
                "current_count": result.current_count,
                "projected_count": result.projected_count,
                "soft_limit": result.soft_limit,
                "hard_limit": result.hard_limit
            }
        }

    def get_top_performers(self, limit: int = 3) -> List[Dict]:
        """
        Get top performing businesses.

        Args:
            limit: Maximum number of businesses to return

        Returns:
            List of top performing businesses sorted by performance
        """
        active = self.get_active_businesses()

        # Sort by composite score (performance + stability + build_progress)
        def calculate_score(business: Dict) -> float:
            metrics = business["metrics"]
            performance = metrics.get("performance", 0.0)
            stability = metrics.get("stability", 0.0)
            build_progress = metrics.get("build_progress", 0.0)
            validation_score = metrics.get("validation_score", 0.0)

            # Weighted composite score
            stage = business["stage"]
            if stage == "VALIDATING":
                return validation_score
            elif stage == "BUILDING":
                return build_progress * 0.8 + validation_score * 0.2
            elif stage in ["SCALING", "OPERATING", "OPTIMIZING"]:
                return performance * 0.6 + stability * 0.4
            else:
                return 0.0

        sorted_businesses = sorted(
            active,
            key=calculate_score,
            reverse=True
        )

        return sorted_businesses[:limit]

    def get_portfolio_stats(self) -> Dict:
        """
        Get portfolio statistics including capacity status.

        Returns:
            Dictionary with portfolio stats and capacity information
        """
        all_businesses = self.get_all_businesses()
        active = self.get_active_businesses()

        # Count by stage
        by_stage = {}
        for stage in LifecycleManager.STAGES:
            by_stage[stage] = len([b for b in all_businesses if b["stage"] == stage])

        # Calculate averages
        validation_scores = [
            b["metrics"].get("validation_score", 0.0)
            for b in active
            if b["stage"] in ["VALIDATING", "BUILDING", "SCALING", "OPERATING", "OPTIMIZING"]
        ]
        avg_validation = sum(validation_scores) / len(validation_scores) if validation_scores else 0.0

        performances = [
            b["metrics"].get("performance", 0.0)
            for b in active
            if b["stage"] in ["SCALING", "OPERATING", "OPTIMIZING"]
        ]
        avg_performance = sum(performances) / len(performances) if performances else 0.0

        # Find top performer
        top_performers = self.get_top_performers(1)
        top_performer_id = top_performers[0]["id"] if top_performers else None

        # Get capacity status
        capacity_status = self.capacity_manager.get_capacity_status()
        business_capacity = capacity_status["dimensions"].get("businesses", {})

        return {
            "total_businesses": len(all_businesses),
            "by_stage": by_stage,
            "active_count": len(active),
            "terminated_count": by_stage.get("TERMINATED", 0),
            "avg_validation_score": round(avg_validation, 2),
            "avg_performance": round(avg_performance, 2),
            "top_performer": top_performer_id,
            "capacity": {
                "current_count": business_capacity.get("current_count", len(active)),
                "soft_limit": business_capacity.get("soft_limit"),
                "hard_limit": business_capacity.get("hard_limit"),
                "utilization": business_capacity.get("utilization", 0.0),
                "mode": business_capacity.get("mode", "unlimited")
            }
        }

    def load_portfolio(self) -> List[Dict]:
        """Load portfolio from storage."""
        return self.lifecycle_manager.load_businesses()

    def save_portfolio(self, businesses: List[Dict]):
        """Save portfolio to storage."""
        self.lifecycle_manager.save_businesses(businesses)
