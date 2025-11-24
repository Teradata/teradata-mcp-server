"""
Manager for QueryGrid issues.
"""

from typing import Any, Dict

from .base import BaseClient


class IssueClient(BaseClient):
    """Manager for QueryGrid issues."""

    BASE_ENDPOINT = "/api/issues"

    def get_issues(self) -> Dict[str, Any]:
        """
        Retrieve all active issues from the system.

        This method sends a GET request to the '/api/issues' endpoint and returns
        the response as a dictionary containing details of all currently active issues.
        If no issues are present, an empty dictionary or appropriate response may be returned.

        Returns:
            Dict[str, Any]: A dictionary representing the active issues data.

        Raises:
            Any exceptions raised by the underlying _request method, such as network errors
            or API-specific errors (e.g., authentication failures).
        """
        """Get all active issues."""
        return self._request("GET", self.BASE_ENDPOINT)

    def get_issue_by_id(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a specific active issue by its unique identifier.

        This method sends a GET request to the '/api/issues/{id}' endpoint and returns
        the response as a dictionary containing details of the specified issue.
        If the issue does not exist, the API may return an error or an empty response.

        Args:
            id (str): The unique identifier of the issue to retrieve.

        Returns:
            Dict[str, Any]: A dictionary representing the issue data.

        Raises:
            Any exceptions raised by the underlying _request method, such as network errors,
            authentication failures, or API-specific errors (e.g., issue not found).
        """
        return self._request("GET", f"{self.BASE_ENDPOINT}/{id}")
