"""
Manager for QueryGrid systems.
"""

from typing import Any, Dict

from .base import BaseClient


class SystemClient(BaseClient):
    """Manager for QueryGrid systems."""

    BASE_ENDPOINT = "/api/config/systems"

    def __init__(self, session, base_url: str):
        super().__init__(session, base_url)
        self.resource_path = self.BASE_ENDPOINT

    def get_systems(
        self,
        extra_info: bool = False,
        filter_by_proxy_support: str | None = None,
        filter_by_name: str | None = None,
        filter_by_tag: str | None = None,
    ) -> Dict[str, Any]:
        """Get all systems."""
        params = {}
        if extra_info:
            params["extraInfo"] = extra_info
        if (
            filter_by_proxy_support is not None
            and filter_by_proxy_support != ""
            and filter_by_proxy_support != "null"
        ):
            params["filterByProxySupport"] = filter_by_proxy_support
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

    def get_system_by_id(self, id: str, extra_info: bool = False) -> Dict[str, Any]:
        """Get a system by ID."""
        params = {}
        if extra_info:
            params["extraInfo"] = extra_info
        return self._request("GET", f"{self.resource_path}/{id}", params=params)
