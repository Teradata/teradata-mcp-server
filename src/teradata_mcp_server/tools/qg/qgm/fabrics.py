"""
Manager for QueryGrid fabrics.
"""

from typing import Any, Dict

from .base import BaseClient


class FabricClient(BaseClient):
    """Manager for QueryGrid fabrics."""

    BASE_ENDPOINT = "/api/config/fabrics"

    def __init__(self, session, base_url: str):
        super().__init__(session, base_url)
        self.resource_path = self.BASE_ENDPOINT

    def get_fabrics(
        self,
        flatten: bool = False,
        extra_info: bool = False,
        filter_by_name: str | None = None,
        filter_by_tag: str | None = None,
    ) -> Dict[str, Any]:
        """Get all fabrics."""
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
        return self._request("GET", self.resource_path, params=params)

    def get_fabric_by_id(self, id: str, extra_info: bool = False) -> Dict[str, Any]:
        """Get a fabric by ID."""
        params = {}
        if extra_info:
            params["extraInfo"] = extra_info
        return self._request("GET", f"{self.resource_path}/{id}", params=params)

    def get_fabric_active(self, id: str) -> Dict[str, Any]:
        """Get the active version of a fabric."""
        return self._request("GET", f"{self.resource_path}/{id}/active")

    def get_fabric_pending(self, id: str) -> Dict[str, Any]:
        """Get the pending version of a fabric."""
        return self._request("GET", f"{self.resource_path}/{id}/pending")

    def get_fabric_previous(self, id: str) -> Dict[str, Any]:
        """Get the previous version of a fabric."""
        return self._request("GET", f"{self.resource_path}/{id}/previous")
