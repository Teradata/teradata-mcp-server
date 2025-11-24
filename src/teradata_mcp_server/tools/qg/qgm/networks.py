"""
Manager for QueryGrid networks.
"""

from typing import Any, Dict

from .base import BaseClient


class NetworkClient(BaseClient):
    """Manager for QueryGrid networks."""

    BASE_ENDPOINT = "/api/config/networks"

    def get_networks(
        self,
        flatten: bool = False,
        extra_info: bool = False,
        filter_by_name: str | None = None,
        filter_by_tag: str | None = None,
    ) -> Dict[str, Any]:
        """
        Retrieve the list of QueryGrid network objects from the API.

        Args:
            flatten (bool): Flatten versions into array elements. Defaults to False.
            extra_info (bool): Include extra details. Defaults to False.
            filter_by_name (str | None): Filter by name.
            filter_by_tag (str | None): Filter by tag (comma-separated key:value pairs).

        Returns:
            Dict[str, Any]: A dictionary containing the list of networks.
        """
        params = {}
        if flatten:
            params["flatten"] = flatten
        if extra_info:
            params["extraInfo"] = extra_info
        if (
            filter_by_name is not None
            and filter_by_name != ""
            and filter_by_name != "null"
        ):
            params["filterByName"] = filter_by_name
        if (
            filter_by_tag is not None
            and filter_by_tag != ""
            and filter_by_tag != "null"
        ):
            params["filterByTag"] = filter_by_tag
        return self._request(
            "GET", self.BASE_ENDPOINT, params=params if params else None
        )

    def get_network_by_id(self, id: str, extra_info: bool = False) -> Dict[str, Any]:
        """
        Retrieve a specific network by ID.

        Args:
            id (str): The network ID.
            extra_info (bool): Include extra details.

        Returns:
            Dict[str, Any]: The network details.
        """
        params = {}
        if extra_info:
            params["extraInfo"] = extra_info
        return self._request(
            "GET", f"{self.BASE_ENDPOINT}/{id}", params=params if params else None
        )

    def get_network_active(self, id: str) -> Dict[str, Any]:
        """Get the active version of a network."""
        api_endpoint = f"{self.BASE_ENDPOINT}/{id}/active"
        return self._request("GET", api_endpoint)

    def get_network_pending(self, id: str) -> Dict[str, Any]:
        """Get the pending version of a network."""
        api_endpoint = f"{self.BASE_ENDPOINT}/{id}/pending"
        return self._request("GET", api_endpoint)

    def get_network_previous(self, id: str) -> Dict[str, Any]:
        """Get the previous version of a network."""
        api_endpoint = f"{self.BASE_ENDPOINT}/{id}/previous"
        return self._request("GET", api_endpoint)
