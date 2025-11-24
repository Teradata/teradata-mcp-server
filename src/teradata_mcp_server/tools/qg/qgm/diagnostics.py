"""
Manager for QueryGrid diagnostic operations.
"""

from typing import Any, Dict

from .base import BaseClient


class DiagnosticClient(BaseClient):
    """Manager for QueryGrid diagnostic operations."""

    BASE_ENDPOINT = "/api/operations/diagnostic-check"

    def get_diagnostic_check_status(self, id: str) -> Dict[str, Any]:
        """Get the status of a diagnostic check operation."""
        return self._request("GET", f"{self.BASE_ENDPOINT}/{id}")
