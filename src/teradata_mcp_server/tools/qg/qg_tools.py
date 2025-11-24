"""
Tools for Teradata QueryGrid MCP Server

"""

import logging
from teradata_mcp_server.tools.utils import create_response
from .qgm.querygrid_manager import QueryGridManager

logger = logging.getLogger(__name__)


def handle_qg_get_api_info(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    *args,
    **kwargs,
):
    """
    Get API information including version and features.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_api_info: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.api_info_client.get_api_info()

        metadata = {"tool_name": "qg_get_api_info", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_api_info: {e}")
        error_result = f"❌ Error in QueryGrid get API info operation: {str(e)}"
        metadata = {"tool_name": "qg_get_api_info", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_managers(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    extra_info: bool = False,
    filter_by_name: str | None = None,
    *args,
    **kwargs,
):
    """
    Get details of all QueryGrid managers.

    Args:
        extra_info (bool): Include extra information. Values are boolean True/False, not string.
        filter_by_name (str | None): [Optional] Get manager associated with the specified hostname (case insensitive). Wildcard matching with '*' is supported.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_managers: args: {args}, kwargs: {kwargs}")

    try:
        # Run the synchronous operation
        result = qg_manager.manager_client.get_managers(
            extra_info=extra_info, filter_by_name=filter_by_name
        )

        metadata = {"tool_name": "qg_get_managers", "success": True}

        logger.debug(f"Tool: handle_qg_get_managers: metadata: {metadata}")
        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_managers: {e}")
        error_result = f"❌ Error in QueryGrid get managers operation: {str(e)}"
        metadata = {"tool_name": "qg_get_managers", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_manager_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid manager by ID.

    Args:
        id (str): The ID of the manager to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_manager_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.manager_client.get_manager_by_id(id)

        metadata = {"tool_name": "qg_get_manager_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_manager_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get manager by ID operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_manager_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_nodes(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
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
    *args,
    **kwargs,
):
    """
    Retrieve information about QueryGrid nodes. Use optional filter parameters to narrow results by specific criteria such as system ID, fabric ID, connector ID, or node name. Leave optional parameters unset if no filtering is required.

    Args:
        filter_by_system_id (str | None): [Optional] Filter nodes by system ID. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
        filter_by_bridge_id (str | None): [Optional] Filter nodes by bridge ID. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
        filter_by_fabric_id (str | None): [Optional] Filter nodes by fabric ID. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
        filter_by_connector_id (str | None): [Optional] Filter nodes by connector ID. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
        extra_info (bool): Include extra information. Values are boolean True/False, not string.
        fabric_version (str | None): [Optional] Filter nodes by fabric version. e.g., "03.10.00.01".
        connector_version (str | None): [Optional] Filter nodes by connector version. e.g., "03.10.00.01".
        drivers (str | None): [Optional] Works with filter_by_connector_id to make status relative to the drivers for the specified connector. Values can be True/False.
        details (bool): Include detailed information
        filter_by_name (str | None): [Optional] Filter nodes by name. The name can be any sequence of characters representing the node's name, such as 'Node1'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_nodes: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.node_client.get_nodes(
            filter_by_system_id=filter_by_system_id,
            filter_by_bridge_id=filter_by_bridge_id,
            filter_by_fabric_id=filter_by_fabric_id,
            filter_by_connector_id=filter_by_connector_id,
            extra_info=extra_info,
            fabric_version=fabric_version,
            connector_version=connector_version,
            drivers=drivers,
            details=details,
            filter_by_name=filter_by_name,
        )

        metadata = {"tool_name": "qg_get_nodes", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_nodes: {e}")
        error_result = f"❌ Error in QueryGrid get nodes operation: {str(e)}"
        metadata = {"tool_name": "qg_get_nodes", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_node_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get details of a specific QueryGrid node by ID.

    Args:
        id (str): The ID of the node to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_node_by_id: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.node_client.get_node_by_id(id)

        metadata = {"tool_name": "qg_get_node_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_node_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get node by ID operation: {str(e)}"
        metadata = {"tool_name": "qg_get_node_by_id", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_node_heartbeat_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the latest heartbeat sent by a specific QueryGrid node by ID.

    Args:
        id (str): The ID of the node to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_node_heartbeat_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.node_client.get_node_heartbeat_by_id(id)

        metadata = {"tool_name": "qg_get_node_heartbeat_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_node_heartbeat_by_id: {e}")
        error_result = (
            f"❌ Error in QueryGrid get node heartbeat by ID operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_node_heartbeat_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_systems(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    extra_info: bool = False,
    filter_by_proxy_support: str | None = None,
    filter_by_name: str | None = None,
    filter_by_tag: str | None = None,
    *args,
    **kwargs,
):
    """
    Get details of all QueryGrid systems.

    Args:
        extra_info (bool): Include extra information. Values are boolean True/False, not string.
        filter_by_proxy_support (str | None): [Optional] Filter systems based on proxy support type. Available values : NO_PROXY, LOCAL_PROXY, BRIDGE_PROXY
        filter_by_name (str | None): [Optional] Get system associated with the specified name (case insensitive). Wildcard matching with '*' is supported.
        filter_by_tag (str | None): [Optional] Get system associated with the specified tag. Provide ','(comma) separated list of key:value pairs.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_systems: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.system_client.get_systems(
            extra_info=extra_info,
            filter_by_proxy_support=filter_by_proxy_support,
            filter_by_name=filter_by_name,
            filter_by_tag=filter_by_tag,
        )

        metadata = {"tool_name": "qg_get_systems", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_systems: {e}")
        error_result = f"❌ Error in QueryGrid get systems operation: {str(e)}"
        metadata = {"tool_name": "qg_get_systems", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_system_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    extra_info: bool = False,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid system by ID.

    Args:
        id (str): The ID of the system to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
        extra_info (bool): Include extra information. Values are boolean True/False, not string.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_system_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.system_client.get_system_by_id(id, extra_info=extra_info)

        metadata = {"tool_name": "qg_get_system_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_system_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get system by ID operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_system_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_connectors(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    flatten: bool = False,
    extra_info: bool = False,
    filter_by_name: str | None = None,
    fabric_version: str | None = None,
    filter_by_tag: str | None = None,
    *args,
    **kwargs,
):
    """
    Get details of all QueryGrid connectors. Optional filters can be applied to narrow down the results.

    Args:
        flatten (bool): Flatten the response structure
        extra_info (bool): Include extra information. Values are boolean True/False, not string.
        fabric_version (str | None): [Optional] Filter connectors by fabric version
        filter_by_name (str | None): [Optional] Get connector associated with the specified name (case insensitive). Wildcard matching with '*' is supported.
        filter_by_tag (str | None): [Optional] Get connector associated with the specified tag. Provide ','(comma) separated list of key:value pairs.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_connectors: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.connector_client.get_connectors(
            flatten=flatten,
            extra_info=extra_info,
            filter_by_name=filter_by_name,
            filter_by_tag=filter_by_tag,
            fabric_version=fabric_version,
        )

        metadata = {"tool_name": "qg_get_connectors", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_connectors: {e}")
        error_result = f"❌ Error in QueryGrid get connectors operation: {str(e)}"
        metadata = {"tool_name": "qg_get_connectors", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_connector_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    extra_info: bool = False,
    *args,
    **kwargs,
):
    """
    Get details of a specific QueryGrid connector by ID.

    Args:
        id (str): The ID of the connector to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
        extra_info (bool): Include extra information. Values are boolean True/False, not string.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_connector_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.connector_client.get_connector_by_id(
            id=id, extra_info=extra_info
        )

        metadata = {"tool_name": "qg_get_connector_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_connector_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get connector by ID operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_connector_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_connector_active(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the active configuration for a QueryGrid connector.

    Args:
        id (str): The ID of the connector. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_connector_active: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.connector_client.get_connector_active(id)

        metadata = {"tool_name": "qg_get_connector_active", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_connector_active: {e}")
        error_result = f"❌ Error in QueryGrid get connector active operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_connector_active",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_connector_pending(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get details of the pending configuration for a QueryGrid connector.

    Args:
        id (str): The ID of the connector. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_connector_pending: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.connector_client.get_connector_pending(id)

        metadata = {"tool_name": "qg_get_connector_pending", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_connector_pending: {e}")
        error_result = (
            f"❌ Error in QueryGrid get connector pending operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_connector_pending",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_connector_previous(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the previous configuration for a QueryGrid connector.

    Args:
        id (str): The ID of the connector. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_connector_previous: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.connector_client.get_connector_previous(id)

        metadata = {"tool_name": "qg_get_connector_previous", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_connector_previous: {e}")
        error_result = (
            f"❌ Error in QueryGrid get connector previous operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_connector_previous",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_connector_drivers(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    version_id: str,
    *args,
    **kwargs,
):
    """
    Get details of the drivers for a QueryGrid connector.

    Args:
        id (str): The ID of the connector. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
        version_id (str): The version ID of the connector

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_connector_drivers: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.connector_client.get_connector_drivers(
            id=id, version_id=version_id
        )

        metadata = {"tool_name": "qg_get_connector_drivers", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_connector_drivers: {e}")
        error_result = (
            f"❌ Error in QueryGrid get connector drivers operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_connector_drivers",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_links(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    flatten: bool = False,
    extra_info: bool = False,
    filter_by_name: str | None = None,
    filter_by_tag: str | None = None,
    *args,
    **kwargs,
):
    """
    Get details of all QueryGrid links. Optional filters can be applied to narrow down the results.

    Args:
        flatten (bool): Flatten the response structure
        extra_info (bool): Include extra information. Values are boolean True/False, not string.
        filter_by_name (str | None): [Optional] Get link associated with the specified name (case insensitive). Wildcard matching with '*' is supported.
        filter_by_tag (str | None): [Optional] Get link associated with the specified tag. Provide ','(comma) separated list of key:value pairs.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_links: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.link_client.get_links(
            flatten=flatten,
            extra_info=extra_info,
            filter_by_name=filter_by_name,
            filter_by_tag=filter_by_tag,
        )

        metadata = {"tool_name": "qg_get_links", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_links: {e}")
        error_result = f"❌ Error in QueryGrid get links operation: {str(e)}"
        metadata = {"tool_name": "qg_get_links", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_link_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    extra_info: bool = False,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid link by ID.

    Args:
        id (str): The ID of the link to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
        extra_info (bool): Include extra information. Values are boolean True/False, not string.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_link_by_id: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.link_client.get_link_by_id(id, extra_info=extra_info)

        metadata = {"tool_name": "qg_get_link_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_link_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get link by ID operation: {str(e)}"
        metadata = {"tool_name": "qg_get_link_by_id", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_link_active(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the active configuration for a QueryGrid link.

    Args:
        id (str): The ID of the link. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_link_active: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.link_client.get_link_active(id)

        metadata = {"tool_name": "qg_get_link_active", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_link_active: {e}")
        error_result = f"❌ Error in QueryGrid get link active operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_link_active",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_link_pending(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the pending configuration for a QueryGrid link.

    Args:
        id (str): The ID of the link. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_link_pending: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.link_client.get_link_pending(id)

        metadata = {"tool_name": "qg_get_link_pending", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_link_pending: {e}")
        error_result = f"❌ Error in QueryGrid get link pending operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_link_pending",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_link_previous(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the previous configuration for a QueryGrid link.

    Args:
        id (str): The ID of the link. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_link_previous: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.link_client.get_link_previous(id)

        metadata = {"tool_name": "qg_get_link_previous", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_link_previous: {e}")
        error_result = f"❌ Error in QueryGrid get link previous operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_link_previous",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_fabrics(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    flatten: bool = False,
    extra_info: bool = False,
    filter_by_name: str | None = None,
    filter_by_tag: str | None = None,
    *args,
    **kwargs,
):
    """
    Get all QueryGrid fabrics.

    Args:
        flatten (bool): Flatten out the active, pending, and previous versions into array elements instead of nesting them.
        extra_info (bool): Include extra information. Values are boolean True/False, not string.
        filter_by_name (str | None): [Optional] Get fabric associated with the specified name (case insensitive). Wildcard matching with '*' is supported.
        filter_by_tag (str | None): [Optional] Get fabric associated with the specified tag. Provide ','(comma) separated list of key:value pairs.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_fabrics: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.fabric_client.get_fabrics(
            flatten=flatten,
            extra_info=extra_info,
            filter_by_name=filter_by_name,
            filter_by_tag=filter_by_tag,
        )

        metadata = {"tool_name": "qg_get_fabrics", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_fabrics: {e}")
        error_result = f"❌ Error in QueryGrid get fabrics operation: {str(e)}"
        metadata = {"tool_name": "qg_get_fabrics", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_fabric_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    extra_info: bool = False,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid fabric by ID.

    Args:
        id (str): The ID of the fabric to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
        extra_info (bool): Include extra information. Values are boolean True/False, not string.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_fabric_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.fabric_client.get_fabric_by_id(id, extra_info=extra_info)

        metadata = {"tool_name": "qg_get_fabric_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_fabric_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get fabric by ID operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_fabric_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_fabric_active(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the active configuration for a QueryGrid fabric.

    Args:
        id (str): The ID of the fabric. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_fabric_active: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.fabric_client.get_fabric_active(id)

        metadata = {"tool_name": "qg_get_fabric_active", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_fabric_active: {e}")
        error_result = f"❌ Error in QueryGrid get fabric active operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_fabric_active",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_fabric_pending(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the pending configuration for a QueryGrid fabric.

    Args:
        id (str): The ID of the fabric. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_fabric_pending: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.fabric_client.get_fabric_pending(id)

        metadata = {"tool_name": "qg_get_fabric_pending", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_fabric_pending: {e}")
        error_result = f"❌ Error in QueryGrid get fabric pending operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_fabric_pending",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_fabric_previous(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the previous configuration for a QueryGrid fabric.

    Args:
        id (str): The ID of the fabric. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_fabric_previous: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.fabric_client.get_fabric_previous(id)

        metadata = {"tool_name": "qg_get_fabric_previous", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_fabric_previous: {e}")
        error_result = f"❌ Error in QueryGrid get fabric previous operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_fabric_previous",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_software(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    filter_by_name: str | None = None,
    *args,
    **kwargs,
):
    """
    Get QueryGrid software information for all of the uploaded software packages.
    Args:
        filter_by_name (str | None): [Optional] Get software associated with the specified name (case insensitive). Wildcard matching with '*' is supported.
    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_software: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.software_client.get_software(filter_by_name=filter_by_name)

        metadata = {"tool_name": "qg_get_software", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_software: {e}")
        error_result = f"❌ Error in QueryGrid get software operation: {str(e)}"
        metadata = {"tool_name": "qg_get_software", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_software_jdbc_driver(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    *args,
    **kwargs,
):
    """
    Get QueryGrid software information for all of the uploaded JDBC driver software packages.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_software_jdbc_driver: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.software_client.get_software_jdbc_driver()

        metadata = {"tool_name": "qg_get_software_jdbc_driver", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_software_jdbc_driver: {e}")
        error_result = (
            f"❌ Error in QueryGrid get software JDBC driver operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_software_jdbc_driver",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_software_jdbc_driver_by_name(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    jdbc_driver_name: str,
    *args,
    **kwargs,
):
    """
    Get QueryGrid software information for the uploaded software packages related to a specific JDBC driver name.

    Args:
        jdbc_driver_name (str): The JDBC driver name to find

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_software_jdbc_driver_by_name: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.software_client.get_software_jdbc_driver_by_name(
            jdbc_driver_name
        )

        metadata = {"tool_name": "qg_get_software_jdbc_driver_by_name", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_software_jdbc_driver_by_name: {e}")
        error_result = f"❌ Error in QueryGrid get software JDBC driver by name operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_software_jdbc_driver_by_name",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_software_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid software by ID.

    Args:
        id (str): The ID of the software to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_software_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.software_client.get_software_by_id(id)

        metadata = {"tool_name": "qg_get_software_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_software_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get software by ID operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_software_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_query_summary(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    last_modified_after: str | None = None,
    completed: bool = False,
    query_text_phrase: str | None = None,
    query_ref_ids: str | None = None,
    initiator_query_id: str | None = None,
    *args,
    **kwargs,
):
    """
    Get summaries of all the queries run using QueryGrid. Query summaries can be filtered based on various criteria. Optional arguments can be ignored if not needed.

    Args:
        last_modified_after (str | None): [Optional] Return all query summary that have been modified since the time provided. Time should be provided in ISO8601 format. e.g., '2023-01-01T00:00:00Z'
        completed (bool): Include completed queries. Values are 'true' or 'false'.
        query_text_phrase (str | None): [Optional] Only return queries that contain the supplied phrase in the query text.
        query_ref_ids (str | None): [Optional] Filter by comma separated query reference IDs. IDs are in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000,223e4567-e89b-12d3-a456-426614174001'.
        initiator_query_id (str | None): [Optional] Filter by initiator query ID. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_query_summary: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.query_client.get_query_summary(
            last_modified_after=last_modified_after,
            completed=completed,
            query_text_phrase=query_text_phrase,
            query_ref_ids=query_ref_ids,
            initiator_query_id=initiator_query_id,
        )

        metadata = {"tool_name": "qg_get_query_summary", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_query_summary: {e}")
        error_result = f"❌ Error in QueryGrid get query summary operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_query_summary",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_query_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid query by ID.

    Args:
        id (str): The ID of the query to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_query_by_id: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.query_client.get_query_by_id(id)

        metadata = {"tool_name": "qg_get_query_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_query_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get query by ID operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_query_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_query_details(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get detailed information for a specific QueryGrid query.

    Args:
        id (str): The ID of the query to retrieve details for

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_query_details: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.query_client.get_query_details(id)

        metadata = {"tool_name": "qg_get_query_details", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_query_details: {e}")
        error_result = f"❌ Error in QueryGrid get query details operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_query_details",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_datacenters(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    filter_by_name: str | None = None,
    *args,
    **kwargs,
):
    """
    Get details of all QueryGrid datacenters.

    Args:
        filter_by_name (str | None): [Optional] Filter datacenters by name

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_datacenters: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.datacenter_client.get_datacenters(
            filter_by_name=filter_by_name
        )

        metadata = {"tool_name": "qg_get_datacenters", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_datacenters: {e}")
        error_result = f"❌ Error in QueryGrid get datacenters operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_datacenters",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_datacenter_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid datacenter by ID.

    Args:
        id (str): The ID of the datacenter to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_datacenter_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.datacenter_client.get_datacenter_by_id(id)

        metadata = {"tool_name": "qg_get_datacenter_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_datacenter_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get datacenter by ID operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_datacenter_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_networks(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    flatten: bool = False,
    extra_info: bool = False,
    filter_by_name: str | None = None,
    filter_by_tag: str | None = None,
    *args,
    **kwargs,
):
    """
    Get details of all QueryGrid networks.

    Args:
        flatten (bool): Flatten out the active, pending, and previous versions into array elements instead of nesting them.
        extra_info (bool): Include extra information. Values are boolean True/False, not string.
        filter_by_name (str | None): [Optional] Get network associated with the specified name (case insensitive). Wildcard matching with '*' is supported.
        filter_by_tag (str | None): [Optional] Get network associated with the specified tag. Provide ','(comma) separated list of key:value pairs.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_networks: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.network_client.get_networks(
            flatten=flatten,
            extra_info=extra_info,
            filter_by_name=filter_by_name,
            filter_by_tag=filter_by_tag,
        )

        metadata = {"tool_name": "qg_get_networks", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_networks: {e}")
        error_result = f"❌ Error in QueryGrid get networks operation: {str(e)}"
        metadata = {"tool_name": "qg_get_networks", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_network_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    extra_info: bool = False,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid network by ID.

    Args:
        id (str): The ID of the network to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
        extra_info (bool): Include extra information. Values are boolean True/False, not string.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_network_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.network_client.get_network_by_id(id, extra_info=extra_info)

        metadata = {"tool_name": "qg_get_network_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_network_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get network by ID operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_network_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_network_active(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the active configuration for a QueryGrid network.

    Args:
        id (str): The ID of the network. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_network_active: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.network_client.get_network_active(id)

        metadata = {"tool_name": "qg_get_network_active", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_network_active: {e}")
        error_result = f"❌ Error in QueryGrid get network active operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_network_active",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_network_pending(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the pending configuration for a QueryGrid network.

    Args:
        id (str): The ID of the network. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_network_pending: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.network_client.get_network_pending(id)

        metadata = {"tool_name": "qg_get_network_pending", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_network_pending: {e}")
        error_result = f"❌ Error in QueryGrid get network pending operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_network_pending",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_network_previous(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the previous configuration for a QueryGrid network.

    Args:
        id (str): The ID of the network. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_network_previous: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.network_client.get_network_previous(id)

        metadata = {"tool_name": "qg_get_network_previous", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_network_previous: {e}")
        error_result = f"❌ Error in QueryGrid get network previous operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_network_previous",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_node_virtual_ips(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    *args,
    **kwargs,
):
    """
    Get all QueryGrid node virtual IPs associated with the QueryGrid nodes.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_node_virtual_ips: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.node_virtual_ip_client.get_node_virtual_ips()

        metadata = {"tool_name": "qg_get_node_virtual_ips", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_node_virtual_ips: {e}")
        error_result = f"❌ Error in QueryGrid get node virtual IPs operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_node_virtual_ips",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_node_virtual_ip_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid node virtual IP by ID.

    Args:
        id (str): The ID of the virtual IP to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_node_virtual_ip_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.node_virtual_ip_client.get_node_virtual_ip_by_id(id)

        metadata = {"tool_name": "qg_get_node_virtual_ip_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_node_virtual_ip_by_id: {e}")
        error_result = (
            f"❌ Error in QueryGrid get node virtual IP by ID operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_node_virtual_ip_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_user_mappings(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    filter_by_name: str | None = None,
    *args,
    **kwargs,
):
    """
    Get details of all QueryGrid user mappings.

    Args:
        filter_by_name (str | None): [Optional] Filter user mappings by the specified name. Wildcard matching with '*' is supported. This parameter is optional. Do not provide it if no filtering is needed.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_user_mappings: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.user_mapping_client.get_user_mappings(
            filter_by_name=filter_by_name
        )

        metadata = {"tool_name": "qg_get_user_mappings", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_user_mappings: {e}")
        error_result = f"❌ Error in QueryGrid get user mappings operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_user_mappings",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_user_mapping_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get details of a specific QueryGrid user mapping by ID.

    Args:
        id (str): The ID of the user mapping to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_user_mapping_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.user_mapping_client.get_user_mapping_by_id(id)

        metadata = {"tool_name": "qg_get_user_mapping_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_user_mapping_by_id: {e}")
        error_result = (
            f"❌ Error in QueryGrid get user mapping by ID operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_user_mapping_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_users(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    *args,
    **kwargs,
):
    """
    Get all QueryGrid user accounts.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_users: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.user_client.get_users()

        metadata = {"tool_name": "qg_get_users", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_users: {e}")
        error_result = f"❌ Error in QueryGrid get users operation: {str(e)}"
        metadata = {"tool_name": "qg_get_users", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_user_by_username(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    username: str,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid user account by username.

    Args:
        username (str): The username of the user to retrieve

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_user_by_username: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.user_client.get_user_by_username(username)

        metadata = {"tool_name": "qg_get_user_by_username", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_user_by_username: {e}")
        error_result = f"❌ Error in QueryGrid get user by username operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_user_by_username",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_issues(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    *args,
    **kwargs,
):
    """
    Get all QueryGrid issues.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_issues: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.issue_client.get_issues()

        metadata = {"tool_name": "qg_get_issues", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_issues: {e}")
        error_result = f"❌ Error in QueryGrid get issues operation: {str(e)}"
        metadata = {"tool_name": "qg_get_issues", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_issue_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid issue by ID.

    Args:
        id (str): The ID of the issue to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_issue_by_id: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.issue_client.get_issue_by_id(id)

        metadata = {"tool_name": "qg_get_issue_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_issue_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get issue by ID operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_issue_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_diagnostic_check_status(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the status of a QueryGrid diagnostic check.

    Args:
        id (str): The ID of the diagnostic check. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_diagnostic_check_status: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.diagnostic_client.get_diagnostic_check_status(id)

        metadata = {"tool_name": "qg_get_diagnostic_check_status", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_diagnostic_check_status: {e}")
        error_result = (
            f"❌ Error in QueryGrid get diagnostic check status operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_diagnostic_check_status",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_bridges(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    filter_by_system_id: str | None = None,
    filter_by_name: str | None = None,
    *args,
    **kwargs,
):
    """
    Get all QueryGrid bridges. Optional arguments can be ignored if not needed.

    Args:
        filter_by_system_id (str | None): [Optional] Filter by system ID. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'
        filter_by_name (str | None): [Optional] Filter bridges by name

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Tool: handle_qg_get_bridges: args: {args}, kwargs: {kwargs}")

    try:
        result = qg_manager.bridge_client.get_bridges(
            filter_by_system_id=filter_by_system_id, filter_by_name=filter_by_name
        )

        metadata = {"tool_name": "qg_get_bridges", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_bridges: {e}")
        error_result = f"❌ Error in QueryGrid get bridges operation: {str(e)}"
        metadata = {"tool_name": "qg_get_bridges", "error": str(e), "success": False}
        return create_response(error_result, metadata)


def handle_qg_get_bridge_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid bridge by ID.

    Args:
        id (str): The ID of the bridge to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_bridge_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.bridge_client.get_bridge_by_id(id)

        metadata = {"tool_name": "qg_get_bridge_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_bridge_by_id: {e}")
        error_result = f"❌ Error in QueryGrid get bridge by ID operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_bridge_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_comm_policies(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    flatten: bool = False,
    extra_info: bool = False,
    filter_by_name: str | None = None,
    filter_by_tag: str | None = None,
    *args,
    **kwargs,
):
    """
    Get all QueryGrid communication policies. Optional arguments can be ignored if not needed.

    Args:
        flatten (bool): Flatten out the active, pending, and previous versions into array elements instead of nesting them.
        extra_info (bool): Include extra information. Values are boolean True/False, not string.
        filter_by_name (str | None): [Optional] Get communication policy associated with the specified name (case insensitive). Wildcard matching with '*' is supported.
        filter_by_tag (str | None): [Optional] Get communication policy associated with the specified tag. Provide ','(comma) separated list of key:value pairs.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_comm_policies: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.comm_policy_client.get_comm_policies(
            flatten=flatten,
            extra_info=extra_info,
            filter_by_name=filter_by_name,
            filter_by_tag=filter_by_tag,
        )

        metadata = {"tool_name": "qg_get_comm_policies", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_comm_policies: {e}")
        error_result = (
            f"❌ Error in QueryGrid get communication policies operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_comm_policies",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_comm_policy_by_id(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    extra_info: bool = False,
    *args,
    **kwargs,
):
    """
    Get a specific QueryGrid communication policy by ID.

    Args:
        id (str): The ID of the communication policy to retrieve. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.
        extra_info (bool): Include extra information. Values are boolean True/False, not string.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_comm_policy_by_id: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.comm_policy_client.get_comm_policy_by_id(
            id, extra_info=extra_info
        )

        metadata = {"tool_name": "qg_get_comm_policy_by_id", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_comm_policy_by_id: {e}")
        error_result = (
            f"❌ Error in QueryGrid get communication policy by ID operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_comm_policy_by_id",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_comm_policy_active(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the active configuration for a QueryGrid communication policy.

    Args:
        id (str): The ID of the communication policy. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_comm_policy_active: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.comm_policy_client.get_comm_policy_active(id)

        metadata = {"tool_name": "qg_get_comm_policy_active", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_comm_policy_active: {e}")
        error_result = (
            f"❌ Error in QueryGrid get communication policy active operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_comm_policy_active",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_comm_policy_pending(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the pending configuration for a QueryGrid communication policy.

    Args:
        id (str): The ID of the communication policy. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_comm_policy_pending: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.comm_policy_client.get_comm_policy_pending(id)

        metadata = {"tool_name": "qg_get_comm_policy_pending", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_comm_policy_pending: {e}")
        error_result = f"❌ Error in QueryGrid get communication policy pending operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_comm_policy_pending",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_comm_policy_previous(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the previous configuration for a QueryGrid communication policy.

    Args:
        id (str): The ID of the communication policy. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_comm_policy_previous: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.comm_policy_client.get_comm_policy_previous(id)

        metadata = {"tool_name": "qg_get_comm_policy_previous", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_comm_policy_previous: {e}")
        error_result = f"❌ Error in QueryGrid get communication policy previous operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_comm_policy_previous",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_nodes_auto_install_status(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the status of the automatic node installation.

    Args:
        id (str): The installation ID. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_nodes_auto_install_status: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = qg_manager.nodes_auto_install_client.get_nodes_auto_install_status(id)

        metadata = {"tool_name": "qg_get_nodes_auto_install_status", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_nodes_auto_install_status: {e}")
        error_result = (
            f"❌ Error in QueryGrid get nodes auto install status operation: {str(e)}"
        )
        metadata = {
            "tool_name": "qg_get_nodes_auto_install_status",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)


def handle_qg_get_create_foreign_server_status(
    conn: any,  # Not used for QG operations, but required by MCP framework
    qg_manager: QueryGridManager,  # Automatically injected QueryGrid manager instance
    id: str,
    *args,
    **kwargs,
):
    """
    Get the status of the CONNECTOR_CFS diagnostic check for foreign server creation.

    Args:
        id (str): The diagnostic check ID. ID is in UUID format. e.g., '123e4567-e89b-12d3-a456-426614174000'.

    Returns:
        ResponseType: formatted response with operation results + metadata
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Tool: handle_qg_get_create_foreign_server_status: args: {args}, kwargs: {kwargs}"
        )

    try:
        result = (
            qg_manager.create_foreign_server_client.get_create_foreign_server_status(id)
        )

        metadata = {"tool_name": "qg_get_create_foreign_server_status", "success": True}

        return create_response(result, metadata)

    except Exception as e:
        logger.error(f"Error in handle_qg_get_create_foreign_server_status: {e}")
        error_result = f"❌ Error in QueryGrid get create foreign server status operation: {str(e)}"
        metadata = {
            "tool_name": "qg_get_create_foreign_server_status",
            "error": str(e),
            "success": False,
        }
        return create_response(error_result, metadata)
