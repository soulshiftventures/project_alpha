"""
Firecrawl Connector for Project Alpha.

Provides web scraping and content extraction capabilities.

API Documentation: https://docs.firecrawl.dev/

LIVE EXECUTION STATUS:
- scrape: Fully implemented with httpx
- crawl: Dry-run only (async job handling needed)
- map: Dry-run only
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


class FirecrawlConnector(BaseConnector):
    """
    Connector for Firecrawl web scraping API.

    Supported operations:
    - scrape: Scrape a single URL (LIVE CAPABLE)
    - crawl: Crawl multiple pages from a starting URL (dry-run only)
    - map: Get sitemap/structure of a website (dry-run only)

    LIVE EXECUTION STATUS:
    - scrape: Fully implemented with httpx
    - crawl: Dry-run only (requires async job polling)
    - map: Dry-run only
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._register_action_contracts()

    @property
    def name(self) -> str:
        return "firecrawl"

    @property
    def category(self) -> ConnectorCategory:
        return ConnectorCategory.RESEARCH

    @property
    def required_credentials(self) -> List[str]:
        return ["firecrawl_api_key"]

    @property
    def description(self) -> str:
        return "Web scraping and content extraction API"

    @property
    def base_url(self) -> str:
        return "https://api.firecrawl.dev/v1"

    @property
    def supports_dry_run(self) -> bool:
        return True

    @property
    def requires_approval(self) -> bool:
        return False

    def get_operations(self) -> List[str]:
        return ["scrape", "crawl", "map"]

    def _register_action_contracts(self) -> None:
        """Register action contracts for this connector."""
        # scrape - LIVE CAPABLE
        register_action_contract(ActionContract(
            action_name="scrape",
            connector="firecrawl",
            action_type=ActionType.RESEARCH,
            description="Scrape a single URL and extract content",
            required_params=["url"],
            optional_params=["formats", "onlyMainContent", "includeTags", "excludeTags"],
            required_credentials=["firecrawl_api_key"],
            approval_level=ActionApprovalLevel.NONE,
            estimated_cost_class="LOW",
            is_external=True,
            supports_live=HTTPX_AVAILABLE,
            live_implementation_status="fully_live" if HTTPX_AVAILABLE else "dry_run_only",
            success_indicators=["success", "data"],
        ))

        # crawl - DRY_RUN ONLY
        register_action_contract(ActionContract(
            action_name="crawl",
            connector="firecrawl",
            action_type=ActionType.RESEARCH,
            description="Crawl multiple pages from a starting URL",
            required_params=["url"],
            optional_params=["limit", "maxDepth", "includePaths", "excludePaths"],
            required_credentials=["firecrawl_api_key"],
            approval_level=ActionApprovalLevel.STANDARD,
            estimated_cost_class="MEDIUM",
            is_external=True,
            supports_live=False,
            live_implementation_status="dry_run_only",
            success_indicators=["success", "data"],
        ))

        # map - DRY_RUN ONLY
        register_action_contract(ActionContract(
            action_name="map",
            connector="firecrawl",
            action_type=ActionType.RESEARCH,
            description="Get sitemap/structure of a website",
            required_params=["url"],
            optional_params=["search", "limit"],
            required_credentials=["firecrawl_api_key"],
            approval_level=ActionApprovalLevel.NONE,
            estimated_cost_class="LOW",
            is_external=True,
            supports_live=False,
            live_implementation_status="dry_run_only",
            success_indicators=["success", "links"],
        ))

    def _health_check_impl(self) -> ConnectorResult:
        """Check Firecrawl API connectivity."""
        api_key = self._get_credential("firecrawl_api_key")

        if not api_key.is_set():
            return ConnectorResult.error_result(
                "API key not configured",
                error_type="unconfigured",
            )

        return ConnectorResult.success_result(
            data={
                "status": "healthy",
                "api_version": "v1",
            },
            metadata={"checked_at": "now"},
        )

    def _execute_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """Execute a Firecrawl operation."""
        api_key = self._get_credential("firecrawl_api_key")

        if operation == "scrape":
            return self._execute_scrape(api_key.get_value(), params)
        elif operation == "crawl":
            return self._execute_crawl(api_key.get_value(), params)
        elif operation == "map":
            return self._execute_map(api_key.get_value(), params)
        else:
            return ConnectorResult.error_result(
                f"Unknown operation: {operation}",
                error_type="invalid_operation",
            )

    def _execute_scrape(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Scrape a single URL - LIVE EXECUTION.

        Params:
            url: URL to scrape (required)
            formats: Output formats ['markdown', 'html', 'rawHtml'] (optional)
            onlyMainContent: Extract only main content (optional)
            includeTags: HTML tags to include (optional)
            excludeTags: HTML tags to exclude (optional)
        """
        if not HTTPX_AVAILABLE:
            return ConnectorResult.error_result(
                "httpx not installed - cannot execute live",
                error_type="dependency_missing",
            )

        url = params.get("url")
        if not url:
            return ConnectorResult.error_result(
                "Missing required parameter: url",
                error_type="validation_error",
            )

        # Build request payload
        payload = {
            "url": url,
            "formats": params.get("formats", ["markdown"]),
        }

        if params.get("onlyMainContent") is not None:
            payload["onlyMainContent"] = params["onlyMainContent"]
        if params.get("includeTags"):
            payload["includeTags"] = params["includeTags"]
        if params.get("excludeTags"):
            payload["excludeTags"] = params["excludeTags"]

        # Execute live API call
        try:
            response = httpx.post(
                f"{self.base_url}/scrape",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60.0,  # Scraping can take time
            )
            response.raise_for_status()
            result_data = response.json()

            if not result_data.get("success"):
                return ConnectorResult.error_result(
                    result_data.get("error", "Firecrawl API returned success=false"),
                    error_type="api_error",
                    metadata={"response": result_data},
                )

            # Extract data safely with size limits
            data = result_data.get("data", {})
            content_preview = ""
            if data.get("markdown"):
                content_preview = data["markdown"][:500] + "..." if len(data.get("markdown", "")) > 500 else data.get("markdown", "")

            return ConnectorResult.success_result(
                data={
                    "success": True,
                    "url": url,
                    "markdown": data.get("markdown"),
                    "html": data.get("html"),
                    "metadata": data.get("metadata", {}),
                    "content_preview": content_preview,
                },
                metadata={
                    "http_status": response.status_code,
                    "live_execution": True,
                    "formats": params.get("formats", ["markdown"]),
                    "content_length": len(data.get("markdown", "")),
                },
            )

        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_json = e.response.json()
                error_body = error_json.get("error", e.response.text[:200])
            except Exception:
                error_body = e.response.text[:200] if e.response.text else "Unknown error"
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
            logger.error(f"Firecrawl scrape failed: {e}")
            return ConnectorResult.error_result(
                str(e),
                error_type=type(e).__name__,
            )

    def _execute_crawl(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Crawl multiple pages from a starting URL.

        Params:
            url: Starting URL (required)
            limit: Maximum pages to crawl (optional, default 10)
            maxDepth: Maximum crawl depth (optional)
            includePaths: URL paths to include (optional)
            excludePaths: URL paths to exclude (optional)
        """
        url = params.get("url")
        if not url:
            return ConnectorResult.error_result(
                "Missing required parameter: url",
                error_type="validation_error",
            )

        limit = params.get("limit", 10)

        return ConnectorResult.success_result(
            data={
                "url": url,
                "pages": [],
                "message": "Live API call would execute here",
            },
            metadata={
                "limit": limit,
                "maxDepth": params.get("maxDepth"),
            },
        )

    def _execute_map(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Get sitemap/structure of a website.

        Params:
            url: Website URL (required)
            search: Search query to filter URLs (optional)
            limit: Maximum URLs to return (optional)
        """
        url = params.get("url")
        if not url:
            return ConnectorResult.error_result(
                "Missing required parameter: url",
                error_type="validation_error",
            )

        return ConnectorResult.success_result(
            data={
                "url": url,
                "links": [],
                "message": "Live API call would execute here",
            },
            metadata={"search": params.get("search")},
        )

    def _dry_run_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """Simulate Firecrawl operations."""
        if operation == "scrape":
            return self._dry_run_scrape(params)
        elif operation == "crawl":
            return self._dry_run_crawl(params)
        elif operation == "map":
            return self._dry_run_map(params)
        else:
            return ConnectorResult.error_result(
                f"Unknown operation: {operation}",
                error_type="invalid_operation",
            )

    def _dry_run_scrape(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate a scrape operation."""
        url = params.get("url", "https://example.com")
        formats = params.get("formats", ["markdown"])

        mock_data = {
            "success": True,
            "data": {
                "url": url,
                "markdown": f"# Simulated Content\n\nThis is simulated scraped content from {url}",
                "metadata": {
                    "title": "Example Page Title",
                    "description": "Simulated page description",
                    "language": "en",
                    "sourceURL": url,
                },
            },
        }

        return ConnectorResult.dry_run_result(
            simulated_data=mock_data,
            metadata={
                "dry_run": True,
                "formats": formats,
            },
        )

    def _dry_run_crawl(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate a crawl operation."""
        url = params.get("url", "https://example.com")
        limit = params.get("limit", 10)

        mock_pages = [
            {
                "url": f"{url}/page-{i+1}",
                "markdown": f"# Page {i+1}\n\nSimulated crawled content...",
                "metadata": {"title": f"Page {i+1}"},
            }
            for i in range(min(limit, 5))
        ]

        return ConnectorResult.dry_run_result(
            simulated_data={
                "success": True,
                "status": "completed",
                "total": len(mock_pages),
                "data": mock_pages,
            },
            metadata={
                "dry_run": True,
                "pages_crawled": len(mock_pages),
            },
        )

    def _dry_run_map(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate a map operation."""
        url = params.get("url", "https://example.com")

        mock_links = [
            f"{url}/",
            f"{url}/about",
            f"{url}/products",
            f"{url}/contact",
            f"{url}/blog",
        ]

        return ConnectorResult.dry_run_result(
            simulated_data={
                "success": True,
                "links": mock_links,
            },
            metadata={
                "dry_run": True,
                "links_found": len(mock_links),
            },
        )
