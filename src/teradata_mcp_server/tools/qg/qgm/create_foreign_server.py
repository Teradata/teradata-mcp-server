"""
Manager for QueryGrid create foreign server operations.
"""

from typing import Any, Dict

from .base import BaseClient


class CreateForeignServerClient(BaseClient):
    """Manager for QueryGrid create foreign server operations."""

    BASE_ENDPOINT = "/api/operations"

    def get_create_foreign_server_status(self, id: str) -> Dict[str, Any]:
        """
        Get the status of the CONNECTOR_CFS diagnostic check for foreign server creation.

        Args:
            id (str): The diagnostic check ID. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

        Returns:
            Dict[str, Any]: The diagnostic check status.
        """
        api_endpoint = f"{self.BASE_ENDPOINT}/create-foreign-server/{id}"
        return self._request("GET", api_endpoint)
