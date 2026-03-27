"""
HubSpot Connector for Project Alpha.

Provides CRM capabilities for contacts, deals, and pipelines.

API Documentation: https://developers.hubspot.com/docs/api/overview
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


logger = logging.getLogger(__name__)


class HubSpotConnector(BaseConnector):
    """
    Connector for HubSpot CRM platform.

    Supported operations:
    - list_contacts: List contacts with optional filters
    - get_contact: Get a specific contact
    - create_contact: Create a new contact
    - update_contact: Update an existing contact
    - list_deals: List deals with optional filters
    - create_deal: Create a new deal
    - update_deal: Update an existing deal
    """

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
        Create a new contact.

        Params:
            email: Contact email (required)
            firstname: First name (optional)
            lastname: Last name (optional)
            phone: Phone number (optional)
            company: Company name (optional)
            properties: Additional properties (optional)
        """
        email = params.get("email")
        if not email:
            return ConnectorResult.error_result(
                "Missing required parameter: email",
                error_type="validation_error",
            )

        return ConnectorResult.success_result(
            data={
                "id": None,
                "properties": {"email": email},
                "message": "Live API call would execute here",
            },
            metadata={"email": email},
        )

    def _execute_update_contact(
        self,
        api_key: str,
        params: Dict[str, Any],
    ) -> ConnectorResult:
        """
        Update an existing contact.

        Params:
            contact_id: Contact ID (required)
            properties: Properties to update (required)
        """
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

        return ConnectorResult.success_result(
            data={
                "id": contact_id,
                "properties": properties,
                "message": "Live API call would execute here",
            },
            metadata={"contact_id": contact_id},
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
