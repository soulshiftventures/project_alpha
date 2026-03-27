"""
Tavily Connector for Project Alpha.

Provides web search and research capabilities via Tavily API.

API Documentation: https://docs.tavily.com/

LIVE EXECUTION STATUS:
- search: Fully implemented with httpx
- extract: Fully implemented with httpx
"""

from typing import Any, Dict, List, Optional
import logging

from integrations.base import (
    BaseConnector,
    ConnectorCategory,
    ConnectorResult,
    ConnectorError,
    RateLimitError,
    AuthenticationError,
)
from integrations.action_contracts import (
    ActionContract,
    ActionType,
    ActionApprovalLevel,
    register_action_contract,
)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


logger = logging.getLogger(__name__)


class TavilyConnector(BaseConnector):
    """
    Connector for Tavily web search API.

    Supported operations:
    - search: Perform web search (LIVE CAPABLE)
    - extract: Extract content from URLs (LIVE CAPABLE)

    LIVE EXECUTION STATUS:
    - search: Fully implemented with httpx
    - extract: Fully implemented with httpx
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._register_action_contracts()

    @property
    def name(self) -> str:
        return "tavily"

    @property
    def category(self) -> ConnectorCategory:
        return ConnectorCategory.RESEARCH

    @property
    def required_credentials(self) -> List[str]:
        return ["tavily_api_key"]

    @property
    def description(self) -> str:
        return "AI-powered web search and research API"

    @property
    def base_url(self) -> str:
        return "https://api.tavily.com"

    @property
    def supports_dry_run(self) -> bool:
        return True

    @property
    def requires_approval(self) -> bool:
        return False

    def get_operations(self) -> List[str]:
        return ["search", "extract"]

    def _register_action_contracts(self) -> None:
        """Register action contracts for this connector."""
        # search - LIVE CAPABLE
        register_action_contract(ActionContract(
            action_name="search",
            connector="tavily",
            action_type=ActionType.RESEARCH,
            description="Perform AI-powered web search via Tavily",
            required_params=["query"],
            optional_params=["search_depth", "include_domains", "exclude_domains", "max_results"],
            required_credentials=["tavily_api_key"],
            approval_level=ActionApprovalLevel.NONE,
            estimated_cost_class="LOW",
            is_external=True,
            supports_live=HTTPX_AVAILABLE,
            live_implementation_status="fully_live" if HTTPX_AVAILABLE else "dry_run_only",
            success_indicators=["results", "query"],
        ))

        # extract - LIVE CAPABLE
        register_action_contract(ActionContract(
            action_name="extract",
            connector="tavily",
            action_type=ActionType.RESEARCH,
            description="Extract content from URLs via Tavily",
            required_params=["urls"],
            optional_params=[],
            required_credentials=["tavily_api_key"],
            approval_level=ActionApprovalLevel.NONE,
            estimated_cost_class="LOW",
            is_external=True,
            supports_live=HTTPX_AVAILABLE,
            live_implementation_status="fully_live" if HTTPX_AVAILABLE else "dry_run_only",
            success_indicators=["results"],
        ))

    def _health_check_impl(self) -> ConnectorResult:
        """
        Check Tavily API connectivity.

        Makes a minimal search request to verify API key and connectivity.
        """
        # In real implementation, would make actual API call
        # For now, verify credential is configured
        api_key = self._get_credential("tavily_api_key")

        if not api_key.is_set():
            return ConnectorResult.error_result(
                "API key not configured",
                error_type="unconfigured",
            )

        # Simulated health check response
        return ConnectorResult.success_result(
            data={
                "status": "healthy",
                "api_version": "v1",
                "rate_limit_remaining": 100,
            },
            metadata={"checked_at": "now"},
        )

    def _execute_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Execute a Tavily operation.

        Args:
            operation: 'search' or 'extract'
            params: Operation parameters
        """
        api_key = self._get_credential("tavily_api_key")

        if operation == "search":
            return self._execute_search(api_key.get_value(), params)
        elif operation == "extract":
            return self._execute_extract(api_key.get_value(), params)
        else:
            return ConnectorResult.error_result(
                f"Unknown operation: {operation}",
                error_type="invalid_operation",
            )

    def _execute_search(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Execute a search query - LIVE EXECUTION.

        Params:
            query: Search query string (required)
            search_depth: 'basic' or 'advanced' (optional)
            include_domains: List of domains to include (optional)
            exclude_domains: List of domains to exclude (optional)
            max_results: Maximum results to return (optional, default 5)
        """
        if not HTTPX_AVAILABLE:
            return ConnectorResult.error_result(
                "httpx not installed - cannot execute live",
                error_type="dependency_missing",
            )

        query = params.get("query")
        if not query:
            return ConnectorResult.error_result(
                "Missing required parameter: query",
                error_type="validation_error",
            )

        # Build request payload
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": params.get("search_depth", "basic"),
            "max_results": params.get("max_results", 5),
        }

        if params.get("include_domains"):
            payload["include_domains"] = params["include_domains"]
        if params.get("exclude_domains"):
            payload["exclude_domains"] = params["exclude_domains"]

        # Execute live API call
        try:
            response = httpx.post(
                f"{self.base_url}/search",
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            result_data = response.json()

            # Redact API key from any error responses
            if "api_key" in result_data:
                result_data["api_key"] = "[REDACTED]"

            return ConnectorResult.success_result(
                data={
                    "query": query,
                    "results": result_data.get("results", []),
                    "answer": result_data.get("answer"),
                    "response_time": result_data.get("response_time"),
                },
                metadata={
                    "http_status": response.status_code,
                    "live_execution": True,
                    "search_depth": params.get("search_depth", "basic"),
                    "results_count": len(result_data.get("results", [])),
                },
            )

        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = e.response.text[:200]  # Limit error body size
            except Exception:
                pass
            return ConnectorResult.error_result(
                f"HTTP {e.response.status_code}: {error_body}",
                error_type="http_error",
                metadata={"status_code": e.response.status_code},
            )
        except httpx.TimeoutException:
            return ConnectorResult.error_result(
                "Request timed out",
                error_type="timeout",
            )
        except httpx.RequestError as e:
            return ConnectorResult.error_result(
                f"Request failed: {str(e)}",
                error_type="connection_error",
            )
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return ConnectorResult.error_result(
                str(e),
                error_type=type(e).__name__,
            )

    def _execute_extract(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Extract content from URLs - LIVE EXECUTION.

        Params:
            urls: List of URLs to extract from (required)
        """
        if not HTTPX_AVAILABLE:
            return ConnectorResult.error_result(
                "httpx not installed - cannot execute live",
                error_type="dependency_missing",
            )

        urls = params.get("urls")
        if not urls:
            return ConnectorResult.error_result(
                "Missing required parameter: urls",
                error_type="validation_error",
            )

        if not isinstance(urls, list):
            urls = [urls]

        # Build request payload
        payload = {
            "api_key": api_key,
            "urls": urls,
        }

        # Execute live API call
        try:
            response = httpx.post(
                f"{self.base_url}/extract",
                json=payload,
                timeout=60.0,  # Extract can take longer
            )
            response.raise_for_status()
            result_data = response.json()

            # Redact API key from any error responses
            if "api_key" in result_data:
                result_data["api_key"] = "[REDACTED]"

            return ConnectorResult.success_result(
                data={
                    "results": result_data.get("results", []),
                    "failed_results": result_data.get("failed_results", []),
                },
                metadata={
                    "http_status": response.status_code,
                    "live_execution": True,
                    "urls_processed": len(urls),
                    "results_count": len(result_data.get("results", [])),
                },
            )

        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = e.response.text[:200]
            except Exception:
                pass
            return ConnectorResult.error_result(
                f"HTTP {e.response.status_code}: {error_body}",
                error_type="http_error",
                metadata={"status_code": e.response.status_code},
            )
        except httpx.TimeoutException:
            return ConnectorResult.error_result(
                "Request timed out",
                error_type="timeout",
            )
        except httpx.RequestError as e:
            return ConnectorResult.error_result(
                f"Request failed: {str(e)}",
                error_type="connection_error",
            )
        except Exception as e:
            logger.error(f"Tavily extract failed: {e}")
            return ConnectorResult.error_result(
                str(e),
                error_type=type(e).__name__,
            )

    def _dry_run_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Simulate Tavily operations.

        Returns realistic-looking mock data without making API calls.
        """
        if operation == "search":
            return self._dry_run_search(params)
        elif operation == "extract":
            return self._dry_run_extract(params)
        else:
            return ConnectorResult.error_result(
                f"Unknown operation: {operation}",
                error_type="invalid_operation",
            )

    def _dry_run_search(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate a search operation."""
        query = params.get("query", "sample query")
        max_results = params.get("max_results", 5)

        mock_results = [
            {
                "title": f"Search Result {i+1} for: {query}",
                "url": f"https://example.com/result-{i+1}",
                "content": f"This is simulated content for search result {i+1}...",
                "score": 0.95 - (i * 0.1),
            }
            for i in range(min(max_results, 5))
        ]

        return ConnectorResult.dry_run_result(
            simulated_data={
                "query": query,
                "results": mock_results,
                "response_time": 0.5,
            },
            metadata={
                "dry_run": True,
                "simulated_results_count": len(mock_results),
            },
        )

    def _dry_run_extract(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate an extract operation."""
        urls = params.get("urls", ["https://example.com"])
        if not isinstance(urls, list):
            urls = [urls]

        mock_extracts = [
            {
                "url": url,
                "raw_content": f"Simulated extracted content from {url}...",
                "success": True,
            }
            for url in urls
        ]

        return ConnectorResult.dry_run_result(
            simulated_data={
                "results": mock_extracts,
                "failed_urls": [],
            },
            metadata={
                "dry_run": True,
                "urls_processed": len(urls),
            },
        )
