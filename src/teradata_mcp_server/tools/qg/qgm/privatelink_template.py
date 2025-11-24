"""
Manager for QueryGrid privatelink template operations.
"""

from .base import BaseClient


class PrivatelinkTemplateClient(BaseClient):
    """Manager for QueryGrid privatelink template operations."""

    BASE_ENDPOINT = "/api/operations"

    def get_privatelink_template(self, cloud_platform: str) -> bytes:
        """
        Generate private link template file for a given cloud platform.

        Args:
            cloud_platform (str): Name of the cloud platform. E.g. aws, azure, gc

        Returns:
            bytes: The template file content.
        """
        params = {"cloud_platform": cloud_platform}
        api_endpoint = f"{self.BASE_ENDPOINT}/privatelink-template"
        response = self.session.get(f"{self.base_url}{api_endpoint}", params=params)
        response.raise_for_status()
        return response.content
