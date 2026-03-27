"""
Safe Rendering Utilities for Project Alpha

Provides defensive handling for missing or partial data in UI rendering,
ensuring pages don't break when records are missing or state is incomplete.
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone


def safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """
    Safely get a value from an object/dict, returning default if not found.

    Args:
        obj: Object or dictionary to get value from
        key: Key to retrieve
        default: Default value if key not found

    Returns:
        Value or default
    """
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


def safe_format_datetime(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Safely format a datetime object, returning 'N/A' if None.

    Args:
        dt: Datetime to format
        format_str: Format string

    Returns:
        Formatted datetime or 'N/A'
    """
    if dt is None:
        return "N/A"

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except (ValueError, AttributeError):
            return dt

    try:
        return dt.strftime(format_str)
    except (AttributeError, ValueError):
        return "N/A"


def safe_isoformat(dt: Optional[datetime]) -> Optional[str]:
    """
    Safely convert datetime to ISO format string.

    Args:
        dt: Datetime to convert

    Returns:
        ISO format string or None
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        return dt

    try:
        return dt.isoformat()
    except AttributeError:
        return None


def safe_enum_value(enum_obj: Any, default: str = "unknown") -> str:
    """
    Safely get the value from an enum, returning default if not an enum.

    Args:
        enum_obj: Enum object
        default: Default value if not an enum

    Returns:
        Enum value or default
    """
    if enum_obj is None:
        return default

    try:
        return enum_obj.value
    except AttributeError:
        return str(enum_obj) if enum_obj else default


def safe_list(value: Any) -> List:
    """
    Safely convert value to a list, returning empty list if None or not iterable.

    Args:
        value: Value to convert

    Returns:
        List or empty list
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, (tuple, set)):
        return list(value)

    return []


def safe_dict(value: Any) -> Dict:
    """
    Safely convert value to a dict, returning empty dict if None or not dict-like.

    Args:
        value: Value to convert

    Returns:
        Dict or empty dict
    """
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    return {}


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to int, returning default if conversion fails.

    Args:
        value: Value to convert
        default: Default value

    Returns:
        Integer or default
    """
    if value is None:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float, returning default if conversion fails.

    Args:
        value: Value to convert
        default: Default value

    Returns:
        Float or default
    """
    if value is None:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_call(func: Callable, *args, default: Any = None, **kwargs) -> Any:
    """
    Safely call a function, returning default if it raises an exception.

    Args:
        func: Function to call
        *args: Positional arguments
        default: Default value on error
        **kwargs: Keyword arguments

    Returns:
        Function result or default
    """
    try:
        return func(*args, **kwargs)
    except Exception:
        return default


def ensure_record_exists(
    record: Optional[Any],
    record_type: str = "record",
    record_id: str = "unknown"
) -> Dict[str, Any]:
    """
    Ensure a record exists, returning a placeholder dict if None.

    Args:
        record: Record to check
        record_type: Type of record (for error message)
        record_id: ID of record (for error message)

    Returns:
        Record data or placeholder
    """
    if record is None:
        return {
            "_missing": True,
            "_type": record_type,
            "_id": record_id,
            "_message": f"{record_type.capitalize()} not found",
        }

    if isinstance(record, dict):
        return record

    # Try to convert object to dict
    try:
        if hasattr(record, '__dict__'):
            return record.__dict__
        if hasattr(record, 'asdict'):
            return record.asdict()
    except Exception:
        pass

    return {"_value": record}


def safe_join_records(
    primary: Optional[Dict[str, Any]],
    related: Optional[Dict[str, Any]],
    key_prefix: str = "related"
) -> Dict[str, Any]:
    """
    Safely join two records, handling missing related records gracefully.

    Args:
        primary: Primary record
        related: Related record to join
        key_prefix: Prefix for related record keys

    Returns:
        Combined record with graceful handling of missing data
    """
    if primary is None:
        primary = {}

    result = dict(primary)

    if related is None:
        result[f"{key_prefix}_missing"] = True
        return result

    for key, value in related.items():
        result[f"{key_prefix}_{key}"] = value

    return result


def render_status_badge(status: str, status_colors: Optional[Dict[str, str]] = None) -> str:
    """
    Render a status badge with appropriate color.

    Args:
        status: Status string
        status_colors: Optional dict of status to color mappings

    Returns:
        HTML badge string
    """
    if status_colors is None:
        status_colors = {
            "success": "green",
            "completed": "green",
            "running": "blue",
            "pending": "yellow",
            "failed": "red",
            "error": "red",
            "blocked": "red",
            "warning": "orange",
            "approved": "green",
            "denied": "red",
        }

    color = status_colors.get(status.lower(), "gray")
    return f'<span class="badge badge-{color}">{status}</span>'


def safe_percentage(numerator: Any, denominator: Any, decimal_places: int = 1) -> str:
    """
    Safely calculate and format a percentage.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        decimal_places: Number of decimal places

    Returns:
        Formatted percentage string or 'N/A'
    """
    try:
        num = float(numerator) if numerator is not None else 0
        denom = float(denominator) if denominator is not None else 0

        if denom == 0:
            return "N/A"

        percentage = (num / denom) * 100
        return f"{percentage:.{decimal_places}f}%"
    except (ValueError, TypeError):
        return "N/A"


# =========================================================================
# Connector Action Redaction
# =========================================================================


def redact_sensitive_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive fields from connector request/response data.

    Args:
        data: Data dictionary to redact

    Returns:
        Redacted copy of data
    """
    if not data:
        return {}

    # Fields that should never be exposed
    sensitive_keys = {
        "token", "api_key", "secret", "password", "credential",
        "authorization", "auth", "bearer", "api_token",
        "access_token", "refresh_token", "private_key",
    }

    redacted = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Check if key contains sensitive terms
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            # Recursively redact nested dicts
            redacted[key] = redact_sensitive_fields(value)
        elif isinstance(value, list):
            # Redact lists of dicts
            redacted[key] = [
                redact_sensitive_fields(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value

    return redacted


def safe_connector_request_summary(params: Dict[str, Any], max_length: int = 200) -> str:
    """
    Generate safe summary of connector request parameters.

    Args:
        params: Request parameters
        max_length: Maximum summary length

    Returns:
        Safe summary string
    """
    if not params:
        return "No parameters"

    # Redact sensitive fields
    redacted_params = redact_sensitive_fields(params)

    # Build summary
    summary_parts = []
    for key, value in redacted_params.items():
        if isinstance(value, (dict, list)):
            summary_parts.append(f"{key}=[complex]")
        elif isinstance(value, str) and len(value) > 50:
            summary_parts.append(f"{key}={value[:47]}...")
        else:
            summary_parts.append(f"{key}={value}")

    summary = ", ".join(summary_parts)

    if len(summary) > max_length:
        summary = summary[:max_length - 3] + "..."

    return summary


def safe_connector_response_summary(
    response: Dict[str, Any],
    success: bool,
    max_length: int = 300,
) -> str:
    """
    Generate safe summary of connector response data.

    Args:
        response: Response data
        success: Whether response was successful
        max_length: Maximum summary length

    Returns:
        Safe summary string
    """
    if not response:
        return "No response data" if success else "Error occurred"

    # Redact sensitive fields
    redacted_response = redact_sensitive_fields(response)

    # Extract key information
    summary_parts = []

    # Status indicator
    if success:
        summary_parts.append("\u2713 Success")
    else:
        summary_parts.append("\u2717 Failed")

    # Extract meaningful fields (not sensitive)
    display_fields = ["message_id", "id", "status", "count", "result_count", "ok"]

    for field in display_fields:
        if field in redacted_response:
            value = redacted_response[field]
            if value is not None:
                summary_parts.append(f"{field}={value}")

    # Add data count if present
    if "data" in redacted_response:
        data = redacted_response["data"]
        if isinstance(data, list):
            summary_parts.append(f"items={len(data)}")
        elif isinstance(data, dict):
            summary_parts.append(f"data_keys={len(data)}")

    summary = ", ".join(summary_parts)

    if len(summary) > max_length:
        summary = summary[:max_length - 3] + "..."

    return summary


def safe_connector_error_summary(error: Optional[str], max_length: int = 200) -> str:
    """
    Generate safe summary of connector error.

    Args:
        error: Error message
        max_length: Maximum summary length

    Returns:
        Safe error summary
    """
    if not error:
        return "No error"

    # Remove any potential credential leaks from error messages
    error_clean = error

    # Common patterns that might contain credentials
    sensitive_patterns = [
        "token=", "api_key=", "secret=", "password=",
        "authorization:", "bearer ", "api-key:",
    ]

    for pattern in sensitive_patterns:
        if pattern.lower() in error_clean.lower():
            error_clean = "Error message contains sensitive information (redacted)"
            break

    if len(error_clean) > max_length:
        error_clean = error_clean[:max_length - 3] + "..."

    return error_clean
