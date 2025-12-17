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

    def __init__(self, tdconn, registry_db: str, last_load_ts: Optional[str] = None):
        """
        Initialize the registry loader.

        Args:
            tdconn: Teradata connection object with an engine attribute
            registry_db: Name of the database containing registry views
            last_load_ts: Last load timestamp (ISO format) to filter tools registered since then
        """
        self.tdconn = tdconn
        self.registry_db = registry_db
        self.engine = tdconn.engine if hasattr(tdconn, 'engine') else None
        self.last_load_ts = last_load_ts

    def load_tools(self) -> tuple[Dict[str, Dict[str, Any]], Optional[str]]:
        """
        Load tool definitions from the database registry, optionally filtering by timestamp.

        Returns:
            Tuple of (tool_definitions, current_timestamp):
            - tool_definitions: Dictionary mapping tool names to their definitions
            - current_timestamp: Database current timestamp to use as watermark for next refresh

            Tool definition structure:
            {
                'tool_name': {
                    'description': 'Tool description',
                    'database_name': 'db_name',
                    'table_name': 'table_name',
                    'db_object': 'db_name.table_name',
                    'object_type': 'UDF' or 'MACRO',
                    'tags': 'comma,separated,tags',
                    'registered_ts': 'timestamp when tool was registered',
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
            return {}, None

        try:
            logger.info(f"RegistryLoader: Starting tool load from '{self.registry_db}' (filter timestamp: {self.last_load_ts or 'None - initial load'})")

            with self.engine.connect() as conn:
                # Load tool metadata (including current timestamp)
                tools_data, current_ts = self._query_tools(conn)

                logger.info(f"RegistryLoader: Query returned {len(tools_data)} tools, current_ts={current_ts}")

                if not tools_data:
                    if self.last_load_ts:
                        logger.info(f"No new tools found in registry database '{self.registry_db}' since {self.last_load_ts}")
                    else:
                        logger.warning(f"No tools found in registry database '{self.registry_db}'")
                    return {}, current_ts

                # Load parameter metadata
                params_data = self._query_params(conn)
                logger.info(f"RegistryLoader: Loaded {len(params_data)} parameter definitions")

                # Build tool definitions
                tool_defs = self._build_tool_definitions(tools_data, params_data)

                if self.last_load_ts:
                    logger.info(f"Loaded {len(tool_defs)} new/updated tools from registry database '{self.registry_db}' since {self.last_load_ts}")
                else:
                    logger.info(f"Loaded {len(tool_defs)} tools from registry database '{self.registry_db}'")
                return tool_defs, current_ts

        except Exception as e:
            logger.error(f"Failed to load tools from registry: {e}", exc_info=True)
            return {}, None

    def _query_tools(self, conn: Connection) -> tuple[list, Optional[str]]:
        """
        Query the mcp_list_tools view for tool metadata, optionally filtering by timestamp.

        Expected columns:
        - ToolName: Name of the tool
        - DataBaseName: Database where the object resides
        - TableName: Name of the database object (UDF/Macro name)
        - ToolType: Type of object ('F'=UDF, 'M'=Macro, 'T'=Table, 'V'=View)
        - registered_ts: Timestamp when tool was registered/updated
        - docstring: Tool description/documentation
        - Tags: Comma-separated tags (optional)

        Returns:
            Tuple of (tools_list, current_timestamp)
        """
        # Build WHERE clause for incremental loading
        where_clause = ""
        if self.last_load_ts:
            where_clause = f"WHERE registered_ts > TIMESTAMP '{self.last_load_ts}'"

        query_sql = f"""
            SELECT
                ToolName,
                DataBaseName,
                TableName,
                ToolType,
                registered_ts,
                docstring,
                Tags,
                current_timestamp
            FROM {self.registry_db}.mcp_list_tools
            {where_clause}
            ORDER BY ToolName
        """

        logger.info(f"RegistryLoader: Executing query on {self.registry_db}.mcp_list_tools with filter: {where_clause or 'NONE'}")

        query = text(query_sql)
        result = conn.execute(query)
        tools = []
        current_ts = None

        for row in result:
            tools.append({
                'ToolName': row[0],
                'DataBaseName': row[1],
                'TableName': row[2],
                'ToolType': row[3] if len(row) > 3 else 'F',  # Default to Function/UDF
                'registered_ts': row[4] if len(row) > 4 else None,
                'docstring': row[5] if len(row) > 5 else '',
                'Tags': row[6] if len(row) > 6 else '',
            })
            # Capture current_timestamp from the first row (all rows have same value)
            if current_ts is None and len(row) > 7:
                current_ts = str(row[7]) if row[7] else None

        logger.info(f"RegistryLoader: Found {len(tools)} tools in registry (filtered: {self.last_load_ts is not None})")
        return tools, current_ts

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
                'registered_ts': tool.get('registered_ts'),
                'parameters': self._build_params(tool_params)
            }

            logger.debug(f"Built definition for tool '{tool_name}' ({tool['ToolType']}, registered: {tool.get('registered_ts')})")

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