"""
Manager for QueryGrid nodes auto install operations.
"""

from typing import Any, Dict

from .base import BaseClient


class NodesAutoInstallClient(BaseClient):
    """Manager for QueryGrid nodes auto install operations."""

    BASE_ENDPOINT = "/api/operations"

    def get_nodes_auto_install_status(self, id: str) -> Dict[str, Any]:
        """
        Get the status of the automatic node installation.

        Args:
            id (str): The installation ID. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

        Returns:
            Dict[str, Any]: The installation status.
        """
        api_endpoint = f"{self.BASE_ENDPOINT}/nodes-auto-install/{id}"
        return self._request("GET", api_endpoint)
