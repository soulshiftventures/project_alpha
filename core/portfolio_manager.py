"""
Portfolio Manager for project_alpha
Manages multiple businesses portfolio-wide
"""

import json
import os
from typing import Dict, List
from core.lifecycle_manager import LifecycleManager


class PortfolioManager:
    """Manages portfolio of multiple businesses."""

    def __init__(self, max_active: int = 5):
        """
        Initialize portfolio manager.

        Args:
            max_active: Maximum number of concurrent active businesses
        """
        self.max_active = max_active
        self.lifecycle_manager = LifecycleManager()

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

    def can_add_business(self) -> bool:
        """
        Check if we can add more businesses.

        Returns:
            True if under max_active limit, False otherwise
        """
        active = self.get_active_businesses()
        return len(active) < self.max_active

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
        Get portfolio statistics.

        Returns:
            Dictionary with portfolio stats
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

        return {
            "total_businesses": len(all_businesses),
            "by_stage": by_stage,
            "active_count": len(active),
            "terminated_count": by_stage.get("TERMINATED", 0),
            "avg_validation_score": round(avg_validation, 2),
            "avg_performance": round(avg_performance, 2),
            "top_performer": top_performer_id
        }

    def load_portfolio(self) -> List[Dict]:
        """Load portfolio from storage."""
        return self.lifecycle_manager.load_businesses()

    def save_portfolio(self, businesses: List[Dict]):
        """Save portfolio to storage."""
        self.lifecycle_manager.save_businesses(businesses)
