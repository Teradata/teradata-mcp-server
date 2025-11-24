"""
Manager for QueryGrid nodes.
"""

from typing import Any, Dict

from .base import BaseClient


class NodeClient(BaseClient):
    """Manager for QueryGrid nodes."""

    BASE_ENDPOINT = "/api/nodes"

    def get_nodes(
        self,
        filter_by_system_id: str | None = None,
        filter_by_bridge_id: str | None = None,
        filter_by_fabric_id: str | None = None,
        filter_by_connector_id: str | None = None,
        extra_info: bool = False,
        fabric_version: str | None = None,
        connector_version: str | None = None,
        drivers: str | None = None,
        details: bool = False,
        filter_by_name: str | None = None,
    ) -> Dict[str, Any]:
        """Get all nodes configured in QueryGrid Manager."""
        params = {}
        if filter_by_system_id is not None and filter_by_system_id != "null":
            params["filterBySystemId"] = filter_by_system_id
        if filter_by_bridge_id is not None and filter_by_bridge_id != "null":
            params["filterByBridgeId"] = filter_by_bridge_id
        if filter_by_fabric_id is not None and filter_by_fabric_id != "null":
            params["filterByFabricId"] = filter_by_fabric_id
        if filter_by_connector_id is not None and filter_by_connector_id != "null":
            params["filterByConnectorId"] = filter_by_connector_id
        if extra_info:
            params["extraInfo"] = extra_info
        if fabric_version is not None and fabric_version != "null":
            params["fabricVersion"] = fabric_version
        if connector_version is not None and connector_version != "null":
            params["connectorVersion"] = connector_version
        if drivers is not None and drivers != "null":
            params["drivers"] = drivers
        if details:
            params["details"] = details
        if (
            filter_by_name is not None
            and filter_by_name != ""
            and filter_by_name != "null"
        ):
            params["filterByName"] = filter_by_name
        return self._request(
            "GET", self.BASE_ENDPOINT, params=params if params else None
        )

    def get_node_by_id(self, id: str) -> Dict[str, Any]:
        """Get a specific node configured in QueryGrid Manager by its ID."""
        return self._request("GET", f"{self.BASE_ENDPOINT}/{id}")

    def get_node_heartbeat_by_id(self, id: str) -> Dict[str, Any]:
        """Get the latest node heartbeat sent by a node to the QueryGrid Manager by its ID."""
        return self._request("GET", f"{self.BASE_ENDPOINT}/{id}/heartbeat")
