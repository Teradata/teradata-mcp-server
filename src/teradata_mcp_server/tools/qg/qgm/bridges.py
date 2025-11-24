"""
Manager for QueryGrid bridges.
"""

from typing import Any, Dict

from .base import BaseClient


class BridgeClient(BaseClient):
    """Manager for QueryGrid bridges."""

    BASE_ENDPOINT = "/api/config/bridges"

    def get_bridges(
        self, filter_by_system_id: str | None = None, filter_by_name: str | None = None
    ) -> Dict[str, Any]:
        """
        Retrieve the list of QueryGrid bridge objects from the API.

        Args:
            filter_by_system_id (str | None): Get bridges associated with the specified system ID.
            filter_by_name (str | None): If provided, filters the bridges by name.

        Returns:
            Dict[str, Any]: A dictionary containing the list of bridges and
                   any additional metadata from the API response.
        """
        api_endpoint = self.BASE_ENDPOINT
        params = {}
        if (
            filter_by_system_id is not None
            and filter_by_system_id != ""
            and filter_by_system_id != "null"
        ):
            params["filterBySystemId"] = filter_by_system_id
        if (
            filter_by_name is not None
            and filter_by_name != ""
            and filter_by_name != "null"
        ):
            params["filterByName"] = filter_by_name
        return self._request(
            "GET", self.BASE_ENDPOINT, params=params if params else None
        )

    def get_bridge_by_id(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a specific QueryGrid bridge object by its ID.

        Args:
            id (str): The unique identifier of the bridge.

        Returns:
            Dict[str, Any]: A dictionary containing the bridge details.
        """
        api_endpoint = f"{self.BASE_ENDPOINT}/{id}"
        return self._request("GET", api_endpoint)
