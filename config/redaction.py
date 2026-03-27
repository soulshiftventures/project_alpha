"""
Secret Redaction Utilities.

Provides functions for safely redacting sensitive values in logs,
debug output, error messages, and UI displays.

SECURITY:
- Always use redaction before logging or displaying config values
- Never expose full secret values in any output
"""

import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse, urlunparse


# Marker used in place of redacted values
REDACTION_MARKER = "[REDACTED]"

# Patterns that indicate a key contains sensitive data
SENSITIVE_KEY_PATTERNS = [
    r".*key.*",
    r".*secret.*",
    r".*password.*",
    r".*token.*",
    r".*credential.*",
    r".*api[-_]?key.*",
    r".*auth.*",
    r".*bearer.*",
    r".*private.*",
    r".*cert.*",
    r".*passphrase.*",
    r".*connection[-_]?string.*",
]

# Compiled patterns for efficiency
_SENSITIVE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_KEY_PATTERNS]


class RedactedString:
    """
    A string wrapper that prevents accidental exposure of secrets.

    When printed or converted to string, shows redaction marker.
    The actual value is accessible only via explicit method call.
    """

    def __init__(self, value: str, hint: str = ""):
        self._value = value
        self._hint = hint

    def __str__(self) -> str:
        """Return redacted representation."""
        if self._hint:
            return f"{REDACTION_MARKER} ({self._hint})"
        return REDACTION_MARKER

    def __repr__(self) -> str:
        """Return redacted representation."""
        return f"RedactedString({REDACTION_MARKER})"

    def __bool__(self) -> bool:
        """Return True if the underlying value is truthy."""
        return bool(self._value)

    def __len__(self) -> int:
        """Return length of underlying value."""
        return len(self._value) if self._value else 0

    def get_value(self) -> str:
        """
        Get the actual secret value.

        WARNING: Only use this when actually needed for API calls.
        Never log or display this value.
        """
        return self._value

    def is_set(self) -> bool:
        """Check if the value is set and non-empty."""
        return bool(self._value)

    def preview(self, chars: int = 4) -> str:
        """
        Get a safe preview showing only first few characters.

        Useful for debugging connection issues.
        """
        if not self._value:
            return "(empty)"
        if len(self._value) <= chars:
            return REDACTION_MARKER
        return f"{self._value[:chars]}...{REDACTION_MARKER}"


def is_sensitive_key(key: str) -> bool:
    """
    Check if a key name indicates sensitive data.

    Args:
        key: The key/variable name to check

    Returns:
        True if the key appears to contain sensitive data
    """
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.match(key):
            return True
    return False


def redact_value(value: Any, key: str = "") -> Any:
    """
    Redact a value if it appears to be sensitive.

    Args:
        value: The value to potentially redact
        key: Optional key name to help determine sensitivity

    Returns:
        Redacted marker if sensitive, otherwise the original value
    """
    if value is None:
        return None

    # Check if the key indicates sensitivity
    if key and is_sensitive_key(key):
        return REDACTION_MARKER

    # Check if the value looks like a secret
    if isinstance(value, str):
        # Long alphanumeric strings without spaces are suspicious
        if len(value) > 20 and not " " in value and re.match(r"^[A-Za-z0-9_\-]+$", value):
            return REDACTION_MARKER
        # API key patterns
        if re.match(r"^(sk|pk|api|key|token)[_\-]", value, re.IGNORECASE):
            return REDACTION_MARKER

    if isinstance(value, RedactedString):
        return REDACTION_MARKER

    return value


def redact_dict(
    data: Dict[str, Any],
    sensitive_keys: Optional[Set[str]] = None,
    deep: bool = True
) -> Dict[str, Any]:
    """
    Redact sensitive values in a dictionary.

    Args:
        data: Dictionary to redact
        sensitive_keys: Additional keys to treat as sensitive
        deep: Whether to recursively redact nested dicts

    Returns:
        New dictionary with sensitive values redacted
    """
    if not isinstance(data, dict):
        return data

    result = {}
    sensitive = sensitive_keys or set()

    for key, value in data.items():
        # Check if this key should be redacted
        should_redact = key in sensitive or is_sensitive_key(key)

        if should_redact:
            result[key] = REDACTION_MARKER
        elif deep and isinstance(value, dict):
            result[key] = redact_dict(value, sensitive_keys, deep)
        elif deep and isinstance(value, list):
            result[key] = [
                redact_dict(item, sensitive_keys, deep) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, RedactedString):
            result[key] = REDACTION_MARKER
        else:
            result[key] = value

    return result


def redact_url(url: str) -> str:
    """
    Redact sensitive parts of a URL (password, tokens in query).

    Args:
        url: The URL to redact

    Returns:
        URL with sensitive parts redacted
    """
    if not url:
        return url

    try:
        parsed = urlparse(url)

        # Redact password in netloc
        if parsed.password:
            # Replace password but keep username
            netloc = parsed.netloc.replace(f":{parsed.password}@", f":{REDACTION_MARKER}@")
        else:
            netloc = parsed.netloc

        # Redact sensitive query parameters
        if parsed.query:
            query_parts = []
            for part in parsed.query.split("&"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    if is_sensitive_key(key):
                        query_parts.append(f"{key}={REDACTION_MARKER}")
                    else:
                        query_parts.append(part)
                else:
                    query_parts.append(part)
            query = "&".join(query_parts)
        else:
            query = ""

        return urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            query,
            parsed.fragment
        ))
    except Exception:
        # If parsing fails, return a safe version
        return "[URL REDACTED]"


def redact_exception(exc: Exception) -> str:
    """
    Create a safe string representation of an exception.

    Removes any potentially sensitive values from error messages.

    Args:
        exc: The exception to redact

    Returns:
        Safe string representation
    """
    message = str(exc)

    # Redact anything that looks like an API key or token
    message = re.sub(
        r"(sk|pk|api|key|token)[_\-][A-Za-z0-9_\-]{10,}",
        REDACTION_MARKER,
        message,
        flags=re.IGNORECASE
    )

    # Redact URLs with credentials
    message = re.sub(
        r"://[^:]+:[^@]+@",
        f"://{REDACTION_MARKER}:{REDACTION_MARKER}@",
        message
    )

    return message


def safe_log_dict(data: Dict[str, Any]) -> str:
    """
    Create a safe string representation of a dict for logging.

    Args:
        data: Dictionary to convert

    Returns:
        String representation with sensitive values redacted
    """
    redacted = redact_dict(data)
    return str(redacted)
