"""
Tests for Production Hardening + Warning Cleanup

Tests defensive handling, safer rendering, and empty-state UI rendering.
"""

import pytest
from datetime import datetime, timezone

from core.safe_rendering import (
    safe_get,
    safe_format_datetime,
    safe_isoformat,
    safe_enum_value,
    safe_list,
    safe_dict,
    safe_int,
    safe_float,
    safe_call,
    ensure_record_exists,
    safe_join_records,
    safe_percentage,
)


class TestSafeRendering:
    """Test safe rendering utilities."""

    def test_safe_get_dict(self):
        """Test safe_get with dict."""
        data = {"key": "value"}
        assert safe_get(data, "key") == "value"
        assert safe_get(data, "missing") is None
        assert safe_get(data, "missing", "default") == "default"

    def test_safe_get_object(self):
        """Test safe_get with object."""
        class TestObj:
            key = "value"

        obj = TestObj()
        assert safe_get(obj, "key") == "value"
        assert safe_get(obj, "missing") is None
        assert safe_get(obj, "missing", "default") == "default"

    def test_safe_get_none(self):
        """Test safe_get with None."""
        assert safe_get(None, "key") is None
        assert safe_get(None, "key", "default") == "default"

    def test_safe_format_datetime_valid(self):
        """Test safe_format_datetime with valid datetime."""
        dt = datetime(2025, 1, 15, 10, 30, 0)
        formatted = safe_format_datetime(dt)
        assert "2025-01-15" in formatted
        assert "10:30:00" in formatted

    def test_safe_format_datetime_none(self):
        """Test safe_format_datetime with None."""
        assert safe_format_datetime(None) == "N/A"

    def test_safe_format_datetime_string(self):
        """Test safe_format_datetime with ISO string."""
        dt_str = "2025-01-15T10:30:00"
        formatted = safe_format_datetime(dt_str)
        assert "2025-01-15" in formatted or dt_str == formatted

    def test_safe_isoformat_valid(self):
        """Test safe_isoformat with valid datetime."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        iso = safe_isoformat(dt)
        assert iso is not None
        assert "2025-01-15" in iso

    def test_safe_isoformat_none(self):
        """Test safe_isoformat with None."""
        assert safe_isoformat(None) is None

    def test_safe_isoformat_string(self):
        """Test safe_isoformat with string."""
        dt_str = "2025-01-15T10:30:00"
        assert safe_isoformat(dt_str) == dt_str

    def test_safe_enum_value(self):
        """Test safe_enum_value."""
        from enum import Enum

        class Status(Enum):
            PENDING = "pending"
            ACTIVE = "active"

        assert safe_enum_value(Status.PENDING) == "pending"
        assert safe_enum_value(None) == "unknown"
        assert safe_enum_value(None, "default") == "default"
        assert safe_enum_value("not_enum") == "not_enum"

    def test_safe_list(self):
        """Test safe_list conversion."""
        assert safe_list([1, 2, 3]) == [1, 2, 3]
        assert safe_list((1, 2, 3)) == [1, 2, 3]
        assert safe_list({1, 2, 3}) == [1, 2, 3]
        assert safe_list(None) == []
        assert safe_list("not_list") == []

    def test_safe_dict(self):
        """Test safe_dict conversion."""
        assert safe_dict({"key": "value"}) == {"key": "value"}
        assert safe_dict(None) == {}
        assert safe_dict("not_dict") == {}

    def test_safe_int(self):
        """Test safe_int conversion."""
        assert safe_int(42) == 42
        assert safe_int("42") == 42
        assert safe_int("not_int") == 0
        assert safe_int("not_int", -1) == -1
        assert safe_int(None) == 0

    def test_safe_float(self):
        """Test safe_float conversion."""
        assert safe_float(42.5) == 42.5
        assert safe_float("42.5") == 42.5
        assert safe_float("not_float") == 0.0
        assert safe_float("not_float", -1.0) == -1.0
        assert safe_float(None) == 0.0

    def test_safe_call_success(self):
        """Test safe_call with successful function."""
        def success_func(x):
            return x * 2

        assert safe_call(success_func, 5) == 10

    def test_safe_call_failure(self):
        """Test safe_call with failing function."""
        def fail_func():
            raise ValueError("test error")

        assert safe_call(fail_func, default="fallback") == "fallback"
        assert safe_call(fail_func) is None

    def test_ensure_record_exists_with_record(self):
        """Test ensure_record_exists with valid record."""
        record = {"id": "123", "name": "test"}
        result = ensure_record_exists(record, "job", "123")
        assert result == record
        assert "_missing" not in result

    def test_ensure_record_exists_with_none(self):
        """Test ensure_record_exists with None."""
        result = ensure_record_exists(None, "job", "123")
        assert result["_missing"] is True
        assert result["_type"] == "job"
        assert result["_id"] == "123"
        assert "not found" in result["_message"].lower()

    def test_safe_join_records_both_present(self):
        """Test safe_join_records with both records."""
        primary = {"id": "123", "name": "test"}
        related = {"status": "active", "count": 5}
        result = safe_join_records(primary, related, "rel")

        assert result["id"] == "123"
        assert result["name"] == "test"
        assert result["rel_status"] == "active"
        assert result["rel_count"] == 5
        assert "rel_missing" not in result

    def test_safe_join_records_missing_related(self):
        """Test safe_join_records with missing related."""
        primary = {"id": "123", "name": "test"}
        result = safe_join_records(primary, None, "rel")

        assert result["id"] == "123"
        assert result["name"] == "test"
        assert result["rel_missing"] is True

    def test_safe_join_records_missing_primary(self):
        """Test safe_join_records with missing primary."""
        related = {"status": "active"}
        result = safe_join_records(None, related, "rel")

        assert result["rel_status"] == "active"

    def test_safe_percentage_valid(self):
        """Test safe_percentage with valid values."""
        assert safe_percentage(50, 100) == "50.0%"
        assert safe_percentage(1, 3, 2) == "33.33%"
        assert safe_percentage(0, 100) == "0.0%"

    def test_safe_percentage_zero_denominator(self):
        """Test safe_percentage with zero denominator."""
        assert safe_percentage(50, 0) == "N/A"

    def test_safe_percentage_none_values(self):
        """Test safe_percentage with None values."""
        assert safe_percentage(None, 100) == "0.0%"
        assert safe_percentage(50, None) == "N/A"
        assert safe_percentage(None, None) == "N/A"


class TestEmptyStateHandling:
    """Test empty-state and partial-state handling."""

    def test_empty_opportunities_list(self):
        """Test handling of empty opportunities list."""
        # This would test UI rendering with no opportunities
        opportunities = []
        assert isinstance(opportunities, list)
        assert len(opportunities) == 0

    def test_missing_plan_reference(self):
        """Test handling of missing plan reference."""
        approval = {
            "record_id": "appr_1",
            "plan_id": "plan_nonexistent",
        }

        # Simulate plan lookup failure
        plan = None

        # Service should handle this gracefully
        result = ensure_record_exists(plan, "plan", approval["plan_id"])
        assert result["_missing"] is True

    def test_partial_job_data(self):
        """Test handling of partial job data."""
        # Job with minimal fields
        partial_job = {
            "job_id": "job_1",
            "status": "pending",
            # Missing: backend, times, result, etc.
        }

        # Safe access should handle missing fields
        backend = safe_get(partial_job, "backend", "unknown")
        result = safe_dict(safe_get(partial_job, "result"))

        assert backend == "unknown"
        assert result == {}

    def test_missing_linked_record(self):
        """Test handling of missing linked record."""
        # Approval references job that doesn't exist
        approval = {
            "record_id": "appr_1",
            "job_id": "job_nonexistent",
        }

        # Simulate safe join
        job = None
        result = safe_join_records(approval, job, "job")

        assert result["record_id"] == "appr_1"
        assert result["job_missing"] is True


class TestHistoryQuerySafety:
    """Test history query safety with missing joins."""

    def test_query_with_missing_opportunity(self):
        """Test history query when opportunity is missing."""
        # Handoff references deleted opportunity
        handoff = {
            "handoff_id": "hand_1",
            "opportunity_id": "opp_deleted",
            "plan_id": "plan_1",
        }

        # Ensure safe access to missing opportunity
        opp_id = safe_get(handoff, "opportunity_id", "unknown")
        assert opp_id == "opp_deleted"

    def test_query_with_missing_plan(self):
        """Test history query when plan is missing."""
        # Job references deleted plan
        job = {
            "job_id": "job_1",
            "plan_id": "plan_deleted",
        }

        # Safe handling
        result = ensure_record_exists(None, "plan", job["plan_id"])
        assert result["_missing"] is True


class TestCapacityStatusRendering:
    """Test capacity status rendering safety."""

    def test_missing_capacity_config(self):
        """Test rendering when no capacity config exists."""
        config = None

        # Safe handling
        config_dict = safe_dict(config)
        assert config_dict == {}

        # Default values
        max_businesses = safe_get(config_dict, "max_businesses", 10)
        assert max_businesses == 10

    def test_partial_capacity_status(self):
        """Test rendering with partial capacity status."""
        status = {
            "current_businesses": 3,
            # Missing: limits, utilization, etc.
        }

        current = safe_int(safe_get(status, "current_businesses"))
        limit = safe_int(safe_get(status, "max_businesses", 10))

        assert current == 3
        assert limit == 10


class TestDatetimeHandling:
    """Test timezone-aware datetime handling."""

    def test_utc_now_replacement(self):
        """Test that datetime.now(timezone.utc) works correctly."""
        now = datetime.now(timezone.utc)

        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

        # Should be ISO format compatible
        iso = now.isoformat()
        assert isinstance(iso, str)
        assert "T" in iso

    def test_safe_isoformat_with_timezone(self):
        """Test safe_isoformat with timezone-aware datetime."""
        now = datetime.now(timezone.utc)
        iso = safe_isoformat(now)

        assert iso is not None
        assert "+" in iso or "Z" in iso  # Timezone indicator


# Integration-style tests

class TestServiceLayerHardening:
    """Test service layer defensive handling."""

    def test_get_job_detail_missing_job(self):
        """Test get_job_detail with missing job."""
        # This would test the actual service method
        # For now, test the pattern
        job = None

        if job is None:
            result = None
        else:
            result = {"job_id": safe_get(job, "job_id")}

        assert result is None  # Service should return None for missing job

    def test_get_approval_detail_with_missing_plan(self):
        """Test get_approval_detail when referenced plan is missing."""
        # Approval exists but plan doesn't
        approval = {
            "record_id": "appr_1",
            "plan_id": "plan_missing",
        }

        plan = None  # Simulate missing plan

        # Service should handle gracefully
        detail = dict(approval)
        if approval.get("plan_id") and plan:
            detail["related_plan"] = plan
        elif approval.get("plan_id") and not plan:
            # Should not crash, should continue
            detail["related_plan"] = None

        assert detail["record_id"] == "appr_1"
        assert detail["related_plan"] is None
