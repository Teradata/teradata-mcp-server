"""
Manager for QueryGrid node virtual IPs.
"""

from typing import Any, Dict

from .base import BaseClient


class NodeVirtualIPClient(BaseClient):
    """Manager for QueryGrid node virtual IPs."""

    BASE_ENDPOINT = "/api/config/node-virtual-ips"

    def get_node_virtual_ips(self) -> Dict[str, Any]:
        """
        Retrieve the list of QueryGrid node virtual IP objects from the API.

        Returns:
            Dict[str, Any]: A dictionary containing the list of node virtual IPs.
        """
        api_endpoint = self.BASE_ENDPOINT
        return self._request("GET", api_endpoint)

    def get_node_virtual_ip_by_id(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a specific node virtual IP by ID.

        Args:
            id (str): The virtual IP ID.

        Returns:
            Dict[str, Any]: The node virtual IP details.
        """
        api_endpoint = f"{self.BASE_ENDPOINT}/{id}"
        return self._request("GET", api_endpoint)
