"""
API Info client for QueryGrid Manager API.
"""

from .base import BaseClient


class ApiInfoClient(BaseClient):
    """Client for API info operations."""

    BASE_ENDPOINT = "/api/"

    def get_api_info(self) -> dict:
        """Get information about the API version and features."""
        api_endpoint = self.BASE_ENDPOINT
        return self._request("GET", api_endpoint)
