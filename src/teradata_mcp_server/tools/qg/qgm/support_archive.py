"""
Manager for QueryGrid support archives.
"""

from typing import Any, Dict

from .base import BaseClient


class SupportArchiveClient(BaseClient):
    """Manager for QueryGrid support archives."""

    BASE_ENDPOINT = "/api/support-archive"

    def get_support_archive_manager(
        self,
        start_time: str | None = None,
        end_time: str | None = None,
        days: str | None = None,
        hours: str | None = None,
    ) -> Dict[str, Any]:
        """
        Generate and download manager support archive.

        Args:
            start_time (str | None): [Optional] The start of the time range to collect logs in ISO8601 format.
            end_time (str | None): [Optional] The end of the time range to collect logs in ISO8601 format.
            days (str | None): [Optional] The number of days back to include log files, defaults to 7.
            hours (str | None): [Optional] The number of hours back to include log files.
        Returns:
            Dict[str, Any]: The support archive data.
        """
        params = {}
        if start_time is not None and start_time != "" and start_time != "null":
            params["start-time"] = start_time
        if end_time is not None and end_time != "" and end_time != "null":
            params["end-time"] = end_time
        if days is not None and days != "" and days != "null":
            params["days"] = days
        if hours is not None and hours != "" and hours != "null":
            params["hours"] = hours
        return self._request("GET", f"{self.BASE_ENDPOINT}/manager", params=params)

    def get_support_archive_query(
        self, queryId: str, all: bool = True
    ) -> Dict[str, Any]:
        """
        Generate and download query support archive.

        Args:
            queryId (str): The query ID.
            all (bool): Collect support information for all operations associated with the specified query Id.

        Returns:
            Dict[str, Any]: The support archive data.
        """
        params = {"query": queryId}
        if all:
            params["all"] = all
        return self._request("GET", f"{self.BASE_ENDPOINT}/query", params=params)

    def get_support_archive_config(self) -> Dict[str, Any]:
        """Generate config support archive."""
        return self._request("GET", f"{self.BASE_ENDPOINT}/config")

    def get_support_archive_node(
        self,
        start_time: str | None = None,
        end_time: str | None = None,
        days: str | None = None,
        hours: str | None = None,
        node: str | None = None,
        system_name: str | None = None,
        threads: int | None = None,
        sender: str | None = None,
    ) -> Dict[str, Any]:
        """
        Generate and download node support archive.

        Args:
            start_time (str | None): The start of the time range to collect logs in ISO8601 format.
            end_time (str | None): The end of the time range to collect logs in ISO8601 format.
            days (str | None): The number of days back to include log files, defaults to 7.
            hours (str | None): The number of hours back to include log files.
            node (str | None): Id or the hostname of a specific node.
            system_name (str | None): Generate node-logs support archive for a specific system name.
            threads (int | None): The number of threads to use for collecting node logs, defaults to 10.
            sender (str | None): Generate node-logs support archive for a specific sender. Examples - [node, fabric, connector]

        Returns:
            Dict[str, Any]: The support archive data.
        """
        params = {}
        if start_time is not None and start_time != "" and start_time != "null":
            params["start-time"] = start_time
        if end_time is not None and end_time != "" and end_time != "null":
            params["end-time"] = end_time
        if days is not None and days != "" and days != "null":
            params["days"] = days
        if hours is not None and hours != "" and hours != "null":
            params["hours"] = hours
        if node is not None and node != "" and node != "null":
            params["node"] = node
        if system_name is not None and system_name != "" and system_name != "null":
            params["system-name"] = system_name
        if threads:
            params["threads"] = threads
        if sender is not None and sender != "" and sender != "null":
            params["sender"] = sender
        return self._request("GET", f"{self.BASE_ENDPOINT}/node", params=params)

    def get_support_archive_diagnostic_check(
        self, diagnosticCheckId: str
    ) -> Dict[str, Any]:
        """
        Generate and download diagnostic check support archive.

        Args:
            diagnosticCheckId (str): The diagnostic check ID. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

        Returns:
            Dict[str, Any]: The support archive data.
        """
        params = {"id": diagnosticCheckId}
        return self._request(
            "GET", f"{self.BASE_ENDPOINT}/diagnostic-check", params=params
        )
