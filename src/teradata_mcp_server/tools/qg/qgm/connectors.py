"""
Manager for QueryGrid connectors.
"""

from typing import Any, Dict

from .base import BaseClient


class ConnectorClient(BaseClient):
    """Manager for QueryGrid connectors."""

    BASE_ENDPOINT = "/api/config/connectors"

    def __init__(self, session, base_url: str):
        super().__init__(session, base_url)
        self.resource_path = self.BASE_ENDPOINT

    def get_connectors(
        self,
        flatten: bool = False,
        extra_info: bool = False,
        fabric_version: str | None = None,
        filter_by_name: str | None = None,
        filter_by_tag: str | None = None,
    ) -> Dict[str, Any]:
        """Get all connectors."""
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
        if (
            fabric_version is not None
            and fabric_version != ""
            and fabric_version != "null"
        ):
            params["fabricVersion"] = fabric_version
        return self._request("GET", self.resource_path, params=params)

    def get_connector_by_id(self, id: str, extra_info: bool = False) -> Dict[str, Any]:
        """Get a connector by ID."""
        params = {}
        if extra_info:
            params["extraInfo"] = extra_info
        return self._request("GET", f"{self.resource_path}/{id}", params=params)

    def get_connector_active(self, id: str) -> Dict[str, Any]:
        """Get the active version of a connector."""
        return self._request("GET", f"{self.resource_path}/{id}/active")

    def get_connector_pending(self, id: str) -> Dict[str, Any]:
        """Get the pending version of a connector."""
        return self._request("GET", f"{self.resource_path}/{id}/pending")

    def get_connector_previous(self, id: str) -> Dict[str, Any]:
        """Get the previous version of a connector."""
        return self._request("GET", f"{self.resource_path}/{id}/previous")

    def get_connector_drivers(self, id: str, version_id: str) -> Dict[str, Any]:
        """Get drivers for a connector version."""
        return self._request(
            "GET", f"{self.resource_path}/{id}/versions/{version_id}/drivers"
        )
