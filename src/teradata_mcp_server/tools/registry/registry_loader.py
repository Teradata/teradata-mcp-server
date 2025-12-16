"""
Tool registry loader for dynamically loading tool definitions from database.

Queries the database registry views to discover and load tool definitions:
- mcp_list_tools: Tool metadata (name, database, table, description, tags)
- mcp_list_toolParams: Tool parameters (name, type, position, required, description)

The schema for the database registry must be set to the `registry` key in the profile.yml configuration file.
"""

import logging
from typing import Any, Dict, Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection

logger = logging.getLogger("teradata_mcp_server.registry_loader")


class RegistryLoader:
    """
    Loads tool definitions from database registry views.

    The registry views should be in a dedicated database (e.g., 'mcp') and contain:
    - mcp_list_tools: Tool metadata
    - mcp_list_toolParams: Parameter definitions for each tool
    """

    # Map Teradata data types to Python types
    TYPE_MAP = {
        # Character types
        'CV': str,           # VARCHAR
        'CF': str,           # CHAR
        'BV': str,           # VARBYTE
        'BF': str,           # BYTE
        'CO': str,           # CLOB
        'BO': str,           # BLOB
        
        # Integer types
        'I': int,            # INTEGER
        'I1': int,           # BYTEINT
        'I2': int,           # SMALLINT
        'I8': int,           # BIGINT
        
        # Floating point types
        'F': float,          # FLOAT/DOUBLE PRECISION
        
        # Decimal/Numeric types
        'D': float,          # DECIMAL
        'N': float,          # NUMERIC
        'PD': float,         # DECIMAL (packed)
        'PZ': float,         # DECIMAL (zoned)
        
        # Date/Time types
        'DA': str,           # DATE (ISO format: YYYY-MM-DD)
        'AT': str,           # TIME
        'TS': str,           # TIMESTAMP
        'TZ': str,           # TIME WITH TIME ZONE
        'SZ': str,           # TIMESTAMP WITH TIME ZONE
        'DT': str,           # DATETIME (legacy)
        
        # Interval types
        'YM': str,           # INTERVAL YEAR TO MONTH
        'DM': str,           # INTERVAL DAY TO MONTH (legacy)
        'DS': str,           # INTERVAL DAY TO SECOND
        'HS': str,           # INTERVAL HOUR TO SECOND
        'PM': str,           # PERIOD(DATE)
        'PS': str,           # PERIOD(TIMESTAMP)
        'PT': str,           # PERIOD(TIME)
        
        # Special types
        'JN': str,           # JSON
        'XM': str,           # XML
        'VA': str,           # VARRAY
        'UT': str,           # UDT (User Defined Type)
        '++': str,           # TD_ANYTYPE
    }

    def __init__(self, tdconn, registry_db: str):
        """
        Initialize the registry loader.

        Args:
            tdconn: Teradata connection object with an engine attribute
            registry_db: Name of the database containing registry views
        """
        self.tdconn = tdconn
        self.registry_db = registry_db
        self.engine = tdconn.engine if hasattr(tdconn, 'engine') else None

    def load_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all tool definitions from the database registry.

        Returns:
            Dictionary mapping tool names to their definitions:
            {
                'tool_name': {
                    'description': 'Tool description',
                    'database_name': 'db_name',
                    'table_name': 'table_name',
                    'db_object': 'db_name.table_name',
                    'object_type': 'UDF' or 'MACRO',
                    'tags': 'comma,separated,tags',
                    'parameters': {
                        'param_name': {
                            'type_hint': type,
                            'description': 'param description',
                            'required': True/False,
                            'position': 1,
                        }
                    }
                }
            }
        """
        if not self.engine:
            logger.warning("No database engine available - cannot load registry tools")
            return {}

        try:
            with self.engine.connect() as conn:
                # Load tool metadata
                tools_data = self._query_tools(conn)

                if not tools_data:
                    logger.warning(f"No tools found in registry database '{self.registry_db}'")
                    return {}

                # Load parameter metadata
                params_data = self._query_params(conn)

                # Build tool definitions
                tool_defs = self._build_tool_definitions(tools_data, params_data)

                logger.info(f"Loaded {len(tool_defs)} tools from registry database '{self.registry_db}'")
                return tool_defs

        except Exception as e:
            logger.error(f"Failed to load tools from registry: {e}", exc_info=True)
            return {}

    def _query_tools(self, conn: Connection) -> list:
        """
        Query the mcp_list_tools view for tool metadata.

        Expected columns:
        - ToolName: Name of the tool
        - DataBaseName: Database where the object resides
        - TableName: Name of the database object (UDF/Macro name)
        - ToolType: Type of object ('F'=UDF, 'M'=Macro, 'T'=Table, 'V'=View)
        - docstring: Tool description/documentation
        - Tags: Comma-separated tags (optional)
        """
        query = text(f"""
            SELECT
                ToolName,
                DataBaseName,
                TableName,
                ToolType,
                docstring,
                Tags
            FROM {self.registry_db}.mcp_list_tools
            ORDER BY ToolName
        """)

        result = conn.execute(query)
        tools = []

        for row in result:
            tools.append({
                'ToolName': row[0],
                'DataBaseName': row[1],
                'TableName': row[2],
                'ToolType': row[3] if len(row) > 3 else 'F',  # Default to Function/UDF
                'docstring': row[4] if len(row) > 4 else '',
                'Tags': row[5] if len(row) > 5 else '',
            })

        logger.debug(f"Found {len(tools)} tools in registry")
        return tools

    def _query_params(self, conn: Connection) -> list:
        """
        Query the mcp_list_toolParams view for parameter metadata.

        Expected columns:
        - ToolName: Name of the tool
        - ParamName: Name of the parameter
        - ParamType: Teradata data type (CV, I, F, etc.)
        - ParamLength: Length/precision (optional, for display)
        - ParamPosition: Position in parameter list (1-based)
        - ParamRequired: 'Y' or 'N'
        - ParamComment: Parameter description
        """
        query = text(f"""
            SELECT
                ToolName,
                ParamName,
                ParamType,
                ParamLength,
                ParamPosition,
                ParamRequired,
                ParamComment
            FROM {self.registry_db}.mcp_list_toolParams
            ORDER BY ToolName, ParamPosition
        """)

        result = conn.execute(query)
        params = []

        for row in result:
            params.append({
                'ToolName': row[0],
                'ParamName': row[1],
                'ParamType': row[2],
                'ParamLength': row[3] if len(row) > 3 else None,
                'ParamPosition': row[4] if len(row) > 4 else 1,
                'ParamRequired': row[5] if len(row) > 5 else 'Y',
                'ParamComment': row[6] if len(row) > 6 else '',
            })

        logger.debug(f"Found {len(params)} parameters across all tools")
        return params

    def _build_tool_definitions(self, tools_data: list, params_data: list) -> Dict[str, Dict[str, Any]]:
        """
        Build tool definition dictionaries from query results.

        Args:
            tools_data: List of tool metadata dictionaries
            params_data: List of parameter metadata dictionaries

        Returns:
            Dictionary mapping tool names to their complete definitions
        """
        tool_defs = {}

        # Create a lookup map for parameters by tool name
        params_by_tool = {}
        for param in params_data:
            tool_name = param['ToolName']
            if tool_name not in params_by_tool:
                params_by_tool[tool_name] = []
            params_by_tool[tool_name].append(param)

        # Build tool definitions
        for tool in tools_data:
            tool_name = tool['ToolName']
            tool_params = params_by_tool.get(tool_name, [])

            tool_defs[tool_name] = {
                'description': tool['docstring'] or f"Execute {tool['DataBaseName']}.{tool['TableName']}",
                'database_name': tool['DataBaseName'],
                'table_name': tool['TableName'],
                'db_object': f"{tool['DataBaseName']}.{tool['TableName']}",
                'object_type': tool['ToolType'],
                'tags': tool.get('Tags', ''),
                'parameters': self._build_params(tool_params)
            }

            logger.info(f"Built definition for tool '{tool_name}' ({tool['ToolType']})")

        return tool_defs

    def _build_params(self, params_data: list) -> Dict[str, Dict[str, Any]]:
        """
        Build parameter definitions from query results.

        Args:
            params_data: List of parameter metadata dictionaries for a single tool

        Returns:
            Dictionary mapping parameter names to their definitions
        """
        params = {}

        # Sort by position to maintain correct parameter order
        sorted_params = sorted(params_data, key=lambda p: p['ParamPosition'])

        for param in sorted_params:
            param_name = param['ParamName']
            param_type_str = param['ParamType'].upper()

            # Map Teradata type to Python type
            python_type = self.TYPE_MAP.get(param_type_str, str)

            # Build description with type info
            description = param.get('ParamComment', '')
            if param.get('ParamLength'):
                description += f" (type: {param_type_str}({param['ParamLength']}))"
            else:
                description += f" (type: {param_type_str})"

            params[param_name] = {
                'type_hint': python_type,
                'description': description.strip(),
                'required': param.get('ParamRequired', 'Y').upper() == 'Y',
                'position': param['ParamPosition'],
            }

        return params