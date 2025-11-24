"""
Manager for QueryGrid users.
"""

from typing import Any, Dict

from .base import BaseClient


class UserClient(BaseClient):
    """Manager for QueryGrid users."""

    BASE_ENDPOINT = "/api/users"

    def get_users(self) -> Dict[str, Any]:
        """
        Retrieve the list of QueryGrid user objects from the API.

        Returns:
            Dict[str, Any]: A dictionary containing the list of users.
        """
        api_endpoint = self.BASE_ENDPOINT
        return self._request("GET", api_endpoint)

    def get_user_by_username(self, username: str) -> Dict[str, Any]:
        """
        Retrieve a specific user by username.

        Args:
            username (str): The username.

        Returns:
            Dict[str, Any]: The user details.
        """
        api_endpoint = f"{self.BASE_ENDPOINT}/{username}"
        return self._request("GET", api_endpoint)
