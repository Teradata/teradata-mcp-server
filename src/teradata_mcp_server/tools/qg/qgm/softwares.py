"""
Manager for QueryGrid software.
"""

from typing import Any, Dict
from unicodedata import name

from .base import BaseClient


class SoftwareClient(BaseClient):
    """Manager for QueryGrid software."""

    BASE_ENDPOINT = "/api/software"

    def __init__(self, session, base_url: str):
        super().__init__(session, base_url)
        self.resource_path = self.BASE_ENDPOINT

    def get_software(self, filter_by_name: str | None = None) -> Dict[str, Any]:
        """Get all software packages."""
        params = {}
        if (
            filter_by_name is not None
            and filter_by_name != ""
            and filter_by_name != "null"
        ):
            params["filterByName"] = filter_by_name
        return self._request(
            "GET", self.resource_path, params=params
        )  # No extraInfo for software

    def get_software_jdbc_driver(self) -> Dict[str, Any]:
        """Find all JDBC driver related software."""
        api_endpoint = f"{self.resource_path}/jdbc-driver"
        return self._request("GET", api_endpoint)  # No extraInfo for software

    def get_software_jdbc_driver_by_name(self, jdbc_driver_name: str) -> Dict[str, Any]:
        """Find JDBC driver software by name."""
        api_endpoint = f"{self.resource_path}/jdbc-driver/{jdbc_driver_name}"
        return self._request("GET", api_endpoint)

    def get_software_by_id(self, id: str) -> Dict[str, Any]:
        """Get software by ID."""
        api_endpoint = f"{self.resource_path}/{id}"
        return self._request("GET", api_endpoint)

    def get_software_package(self, id: str) -> Dict[str, Any]:
        """Download software package by ID."""
        api_endpoint = f"{self.resource_path}/{id}/package"
        return self._request("GET", api_endpoint)

    def get_software_resource_bundle(
        self, id: str, locale: str | None = None
    ) -> Dict[str, Any]:
        """Download software resource bundle by ID."""
        api_endpoint = f"{self.resource_path}/{id}/resource-bundle"
        params = {}
        if locale is not None and locale != "" and locale != "null":
            params["locale"] = locale
        return self._request("GET", api_endpoint, params=params)
