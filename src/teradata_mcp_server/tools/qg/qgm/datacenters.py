"""
Manager for QueryGrid data centers.
"""

from typing import Any, Dict

from .base import BaseClient


class DataCenterClient(BaseClient):
    """Manager for QueryGrid data centers."""

    BASE_ENDPOINT = "/api/config/datacenters"

    def get_datacenters(self, filter_by_name: str | None = None) -> Dict[str, Any]:
        """
        Retrieve the list of QueryGrid data center objects from the API.

        Args:
            filter_by_name (str | None): If provided, filters the data centers by name.
                          Defaults to None.

        Returns:
            Dict[str, Any]: A dictionary containing the list of data centers and
                   any additional metadata from the API response.
        """
        params = {}
        if (
            filter_by_name is not None
            and filter_by_name != ""
            and filter_by_name != "null"
        ):
            params["filterByName"] = filter_by_name
        return self._request("GET", self.BASE_ENDPOINT, params=params)

    def get_datacenter_by_id(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a specific QueryGrid data center object by its ID.

        Args:
            id (str): The unique identifier of the data center. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

        Returns:
            Dict[str, Any]: A dictionary containing the data center details.
        """
        api_endpoint = f"{self.BASE_ENDPOINT}/{id}"
        return self._request("GET", api_endpoint)
