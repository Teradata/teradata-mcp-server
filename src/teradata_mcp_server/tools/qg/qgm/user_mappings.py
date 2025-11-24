"""
Manager for QueryGrid user/role mappings.
"""

from typing import Any, Dict

from .base import BaseClient


class UserMappingClient(BaseClient):
    """Manager for QueryGrid user/role mappings."""

    BASE_ENDPOINT = "/api/config/user-mappings"

    def get_user_mappings(self, filter_by_name: str | None = None) -> Dict[str, Any]:
        """
        Retrieve the list of QueryGrid user mapping objects from the API.

        Args:
            filter_by_name (str | None): If provided, filters the user mappings by name.

        Returns:
            Dict[str, Any]: A dictionary containing the list of user mappings.
        """
        params = {}
        if (
            filter_by_name is not None
            and filter_by_name != ""
            and filter_by_name != "null"
        ):
            params["filterByName"] = filter_by_name
        return self._request(
            "GET", self.BASE_ENDPOINT, params=params if params else None
        )

    def get_user_mapping_by_id(self, mapping_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific user mapping by ID.

        Args:
            mapping_id (str): The mapping ID.

        Returns:
            Dict[str, Any]: The user mapping details.
        """
        api_endpoint = f"{self.BASE_ENDPOINT}/{mapping_id}"
        return self._request("GET", api_endpoint)
