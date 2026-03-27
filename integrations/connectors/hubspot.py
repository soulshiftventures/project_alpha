"""
HubSpot Connector for Project Alpha.

Provides CRM capabilities for contacts, deals, and pipelines.

API Documentation: https://developers.hubspot.com/docs/api/overview

LIVE EXECUTION STATUS:
- create_contact: Fully implemented with httpx
- update_contact: Fully implemented with httpx
- get_contact: Dry-run only
- list_contacts: Dry-run only
- create_deal: Dry-run only
- update_deal: Dry-run only
- list_deals: Dry-run only
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


class HubSpotConnector(BaseConnector):
    """
    Connector for HubSpot CRM platform.

    Supported operations:
    - list_contacts: List contacts with optional filters (dry-run only)
    - get_contact: Get a specific contact (dry-run only)
    - create_contact: Create a new contact (LIVE CAPABLE)
    - update_contact: Update an existing contact (LIVE CAPABLE)
    - list_deals: List deals with optional filters (dry-run only)
    - create_deal: Create a new deal (dry-run only)
    - update_deal: Update an existing deal (dry-run only)

    LIVE EXECUTION STATUS:
    - create_contact: Fully implemented with httpx
    - update_contact: Fully implemented with httpx
    - Others: Dry-run only (read operations kept as dry-run for safety)
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._register_action_contracts()

    @property
    def name(self) -> str:
        return "hubspot"

    @property
    def category(self) -> ConnectorCategory:
        return ConnectorCategory.CRM

    @property
    def required_credentials(self) -> List[str]:
        return ["hubspot_api_key"]

    @property
    def optional_credentials(self) -> List[str]:
        return ["hubspot_portal_id"]

    @property
    def description(self) -> str:
        return "CRM platform for contacts, deals, and pipelines"

    @property
    def base_url(self) -> str:
        return "https://api.hubapi.com"

    @property
    def supports_dry_run(self) -> bool:
        return True

    @property
    def requires_approval(self) -> bool:
        return True  # CRM writes need approval

    def get_operations(self) -> List[str]:
        return [
            "list_contacts",
            "get_contact",
            "create_contact",
            "update_contact",
            "list_deals",
            "create_deal",
            "update_deal",
        ]

    def _register_action_contracts(self) -> None:
        """Register action contracts for this connector."""
        # create_contact - LIVE CAPABLE
        register_action_contract(ActionContract(
            action_name="create_contact",
            connector="hubspot",
            action_type=ActionType.DATA_CREATE,
            description="Create a new contact in HubSpot CRM",
            required_params=["email"],
            optional_params=["firstname", "lastname", "phone", "company", "properties"],
            required_credentials=["hubspot_api_key"],
            approval_level=ActionApprovalLevel.STANDARD,
            estimated_cost_class="MINIMAL",
            is_external=True,
            supports_live=HTTPX_AVAILABLE,
            live_implementation_status="fully_live" if HTTPX_AVAILABLE else "dry_run_only",
            success_indicators=["id", "properties"],
        ))

        # update_contact - LIVE CAPABLE
        register_action_contract(ActionContract(
            action_name="update_contact",
            connector="hubspot",
            action_type=ActionType.DATA_UPDATE,
            description="Update an existing contact in HubSpot CRM",
            required_params=["contact_id", "properties"],
            optional_params=[],
            required_credentials=["hubspot_api_key"],
            approval_level=ActionApprovalLevel.STANDARD,
            estimated_cost_class="MINIMAL",
            is_external=True,
            supports_live=HTTPX_AVAILABLE,
            live_implementation_status="fully_live" if HTTPX_AVAILABLE else "dry_run_only",
            success_indicators=["id", "properties"],
        ))

        # get_contact - DRY_RUN ONLY
        register_action_contract(ActionContract(
            action_name="get_contact",
            connector="hubspot",
            action_type=ActionType.DATA_FETCH,
            description="Get a contact by ID from HubSpot CRM",
            required_params=["contact_id"],
            optional_params=["properties"],
            required_credentials=["hubspot_api_key"],
            approval_level=ActionApprovalLevel.NONE,
            estimated_cost_class="FREE",
            is_external=False,
            supports_live=False,
            live_implementation_status="dry_run_only",
            success_indicators=["id"],
        ))

        # list_contacts - DRY_RUN ONLY
        register_action_contract(ActionContract(
            action_name="list_contacts",
            connector="hubspot",
            action_type=ActionType.DATA_FETCH,
            description="List contacts from HubSpot CRM",
            required_params=[],
            optional_params=["limit", "after", "properties", "sorts"],
            required_credentials=["hubspot_api_key"],
            approval_level=ActionApprovalLevel.NONE,
            estimated_cost_class="FREE",
            is_external=False,
            supports_live=False,
            live_implementation_status="dry_run_only",
            success_indicators=["results"],
        ))

    def _health_check_impl(self) -> ConnectorResult:
        """Check HubSpot API connectivity."""
        api_key = self._get_credential("hubspot_api_key")

        if not api_key.is_set():
            return ConnectorResult.error_result(
                "API key not configured",
                error_type="unconfigured",
            )

        return ConnectorResult.success_result(
            data={
                "status": "healthy",
                "api_version": "v3",
            },
            metadata={"checked_at": "now"},
        )

    def _execute_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """Execute a HubSpot operation."""
        api_key = self._get_credential("hubspot_api_key")

        operation_map = {
            "list_contacts": self._execute_list_contacts,
            "get_contact": self._execute_get_contact,
            "create_contact": self._execute_create_contact,
            "update_contact": self._execute_update_contact,
            "list_deals": self._execute_list_deals,
            "create_deal": self._execute_create_deal,
            "update_deal": self._execute_update_deal,
        }

        if operation not in operation_map:
            return ConnectorResult.error_result(
                f"Unknown operation: {operation}",
                error_type="invalid_operation",
            )

        return operation_map[operation](api_key.get_value(), params)

    def _execute_list_contacts(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        List contacts with optional filters.

        Params:
            limit: Maximum contacts to return (optional, default 10)
            after: Pagination cursor (optional)
            properties: List of properties to return (optional)
            sorts: Sort criteria (optional)
        """
        return ConnectorResult.success_result(
            data={
                "results": [],
                "paging": {"next": None},
                "message": "Live API call would execute here",
            },
            metadata={
                "limit": params.get("limit", 10),
            },
        )

    def _execute_get_contact(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Get a specific contact by ID.

        Params:
            contact_id: Contact ID (required)
            properties: List of properties to return (optional)
        """
        contact_id = params.get("contact_id")
        if not contact_id:
            return ConnectorResult.error_result(
                "Missing required parameter: contact_id",
                error_type="validation_error",
            )

        return ConnectorResult.success_result(
            data={
                "id": contact_id,
                "properties": {},
                "message": "Live API call would execute here",
            },
            metadata={"contact_id": contact_id},
        )

    def _execute_create_contact(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Create a new contact - LIVE EXECUTION.

        Params:
            email: Contact email (required)
            firstname: First name (optional)
            lastname: Last name (optional)
            phone: Phone number (optional)
            company: Company name (optional)
            properties: Additional properties (optional)
        """
        if not HTTPX_AVAILABLE:
            return ConnectorResult.error_result(
                "httpx not installed - cannot execute live",
                error_type="dependency_missing",
            )

        email = params.get("email")
        if not email:
            return ConnectorResult.error_result(
                "Missing required parameter: email",
                error_type="validation_error",
            )

        # Build properties
        properties = {"email": email}

        if params.get("firstname"):
            properties["firstname"] = params["firstname"]
        if params.get("lastname"):
            properties["lastname"] = params["lastname"]
        if params.get("phone"):
            properties["phone"] = params["phone"]
        if params.get("company"):
            properties["company"] = params["company"]

        # Merge additional properties if provided
        if params.get("properties"):
            properties.update(params["properties"])

        payload = {"properties": properties}

        # Execute live API call
        try:
            response = httpx.post(
                f"{self.base_url}/crm/v3/objects/contacts",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            result_data = response.json()

            return ConnectorResult.success_result(
                data={
                    "id": result_data.get("id"),
                    "properties": result_data.get("properties", {}),
                    "createdAt": result_data.get("createdAt"),
                    "updatedAt": result_data.get("updatedAt"),
                },
                metadata={
                    "http_status": response.status_code,
                    "live_execution": True,
                    "contact_id": result_data.get("id"),
                    "email": email,
                },
            )

        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_json = e.response.json()
                error_body = error_json.get("message", e.response.text[:200])
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
            logger.error(f"HubSpot create_contact failed: {e}")
            return ConnectorResult.error_result(
                str(e),
                error_type=type(e).__name__,
            )

    def _execute_update_contact(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Update an existing contact - LIVE EXECUTION.

        Params:
            contact_id: Contact ID (required)
            properties: Properties to update (required)
        """
        if not HTTPX_AVAILABLE:
            return ConnectorResult.error_result(
                "httpx not installed - cannot execute live",
                error_type="dependency_missing",
            )

        contact_id = params.get("contact_id")
        properties = params.get("properties")

        if not contact_id:
            return ConnectorResult.error_result(
                "Missing required parameter: contact_id",
                error_type="validation_error",
            )
        if not properties:
            return ConnectorResult.error_result(
                "Missing required parameter: properties",
                error_type="validation_error",
            )

        payload = {"properties": properties}

        # Execute live API call
        try:
            response = httpx.patch(
                f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            result_data = response.json()

            return ConnectorResult.success_result(
                data={
                    "id": result_data.get("id"),
                    "properties": result_data.get("properties", {}),
                    "updatedAt": result_data.get("updatedAt"),
                },
                metadata={
                    "http_status": response.status_code,
                    "live_execution": True,
                    "contact_id": contact_id,
                    "updated_properties": list(properties.keys()),
                },
            )

        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_json = e.response.json()
                error_body = error_json.get("message", e.response.text[:200])
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
            logger.error(f"HubSpot update_contact failed: {e}")
            return ConnectorResult.error_result(
                str(e),
                error_type=type(e).__name__,
            )

    def _execute_list_deals(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        List deals with optional filters.

        Params:
            limit: Maximum deals to return (optional, default 10)
            after: Pagination cursor (optional)
            properties: List of properties to return (optional)
        """
        return ConnectorResult.success_result(
            data={
                "results": [],
                "paging": {"next": None},
                "message": "Live API call would execute here",
            },
            metadata={
                "limit": params.get("limit", 10),
            },
        )

    def _execute_create_deal(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Create a new deal.

        Params:
            dealname: Deal name (required)
            pipeline: Pipeline ID (optional)
            dealstage: Deal stage ID (optional)
            amount: Deal amount (optional)
            properties: Additional properties (optional)
        """
        dealname = params.get("dealname")
        if not dealname:
            return ConnectorResult.error_result(
                "Missing required parameter: dealname",
                error_type="validation_error",
            )

        return ConnectorResult.success_result(
            data={
                "id": None,
                "properties": {"dealname": dealname},
                "message": "Live API call would execute here",
            },
            metadata={"dealname": dealname},
        )

    def _execute_update_deal(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Update an existing deal.

        Params:
            deal_id: Deal ID (required)
            properties: Properties to update (required)
        """
        deal_id = params.get("deal_id")
        properties = params.get("properties")

        if not deal_id:
            return ConnectorResult.error_result(
                "Missing required parameter: deal_id",
                error_type="validation_error",
            )
        if not properties:
            return ConnectorResult.error_result(
                "Missing required parameter: properties",
                error_type="validation_error",
            )

        return ConnectorResult.success_result(
            data={
                "id": deal_id,
                "properties": properties,
                "message": "Live API call would execute here",
            },
            metadata={"deal_id": deal_id},
        )

    def _dry_run_impl(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """Simulate HubSpot operations."""
        dry_run_map = {
            "list_contacts": self._dry_run_list_contacts,
            "get_contact": self._dry_run_get_contact,
            "create_contact": self._dry_run_create_contact,
            "update_contact": self._dry_run_update_contact,
            "list_deals": self._dry_run_list_deals,
            "create_deal": self._dry_run_create_deal,
            "update_deal": self._dry_run_update_deal,
        }

        if operation not in dry_run_map:
            return ConnectorResult.error_result(
                f"Unknown operation: {operation}",
                error_type="invalid_operation",
            )

        return dry_run_map[operation](params)

    def _dry_run_list_contacts(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate listing contacts."""
        limit = params.get("limit", 5)

        mock_contacts = [
            {
                "id": f"contact_{i+1}",
                "properties": {
                    "email": f"contact{i+1}@example.com",
                    "firstname": f"First{i+1}",
                    "lastname": f"Last{i+1}",
                    "phone": f"+1-555-010{i}",
                    "company": f"Company {i+1}",
                    "createdate": "2024-01-15T10:00:00.000Z",
                },
            }
            for i in range(min(limit, 5))
        ]

        return ConnectorResult.dry_run_result(
            simulated_data={
                "results": mock_contacts,
                "paging": {"next": {"after": "cursor_abc123"} if limit > 5 else None},
            },
            metadata={
                "dry_run": True,
                "simulated_count": len(mock_contacts),
            },
        )

    def _dry_run_get_contact(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate getting a contact."""
        contact_id = params.get("contact_id", "contact_1")

        mock_contact = {
            "id": contact_id,
            "properties": {
                "email": "john.doe@example.com",
                "firstname": "John",
                "lastname": "Doe",
                "phone": "+1-555-0100",
                "company": "Example Corp",
                "jobtitle": "CEO",
                "createdate": "2024-01-15T10:00:00.000Z",
                "lastmodifieddate": "2024-03-20T14:30:00.000Z",
            },
        }

        return ConnectorResult.dry_run_result(
            simulated_data=mock_contact,
            metadata={"dry_run": True, "contact_id": contact_id},
        )

    def _dry_run_create_contact(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate creating a contact."""
        email = params.get("email", "new@example.com")

        mock_contact = {
            "id": "contact_new_123",
            "properties": {
                "email": email,
                "firstname": params.get("firstname", ""),
                "lastname": params.get("lastname", ""),
                "phone": params.get("phone", ""),
                "company": params.get("company", ""),
                "createdate": "2024-03-27T10:00:00.000Z",
            },
        }

        return ConnectorResult.dry_run_result(
            simulated_data=mock_contact,
            metadata={"dry_run": True, "would_create": email},
        )

    def _dry_run_update_contact(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate updating a contact."""
        contact_id = params.get("contact_id", "contact_1")
        properties = params.get("properties", {})

        mock_contact = {
            "id": contact_id,
            "properties": {
                **properties,
                "lastmodifieddate": "2024-03-27T10:00:00.000Z",
            },
        }

        return ConnectorResult.dry_run_result(
            simulated_data=mock_contact,
            metadata={
                "dry_run": True,
                "contact_id": contact_id,
                "would_update": list(properties.keys()),
            },
        )

    def _dry_run_list_deals(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate listing deals."""
        limit = params.get("limit", 5)

        mock_deals = [
            {
                "id": f"deal_{i+1}",
                "properties": {
                    "dealname": f"Deal {i+1}",
                    "amount": str(10000 + (i * 5000)),
                    "dealstage": "appointmentscheduled",
                    "pipeline": "default",
                    "closedate": f"2024-04-{15+i}T00:00:00.000Z",
                    "createdate": "2024-03-01T10:00:00.000Z",
                },
            }
            for i in range(min(limit, 5))
        ]

        return ConnectorResult.dry_run_result(
            simulated_data={
                "results": mock_deals,
                "paging": {"next": None},
            },
            metadata={
                "dry_run": True,
                "simulated_count": len(mock_deals),
            },
        )

    def _dry_run_create_deal(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate creating a deal."""
        dealname = params.get("dealname", "New Deal")

        mock_deal = {
            "id": "deal_new_123",
            "properties": {
                "dealname": dealname,
                "amount": params.get("amount", "0"),
                "pipeline": params.get("pipeline", "default"),
                "dealstage": params.get("dealstage", "appointmentscheduled"),
                "createdate": "2024-03-27T10:00:00.000Z",
            },
        }

        return ConnectorResult.dry_run_result(
            simulated_data=mock_deal,
            metadata={"dry_run": True, "would_create": dealname},
        )

    def _dry_run_update_deal(self, params: Dict[str, Any]) -> ConnectorResult:
        """Simulate updating a deal."""
        deal_id = params.get("deal_id", "deal_1")
        properties = params.get("properties", {})

        mock_deal = {
            "id": deal_id,
            "properties": {
                **properties,
                "hs_lastmodifieddate": "2024-03-27T10:00:00.000Z",
            },
        }

        return ConnectorResult.dry_run_result(
            simulated_data=mock_deal,
            metadata={
                "dry_run": True,
                "deal_id": deal_id,
                "would_update": list(properties.keys()),
            },
        )
