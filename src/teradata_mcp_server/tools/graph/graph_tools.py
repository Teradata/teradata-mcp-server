"""
Graph dependency analysis tools for Teradata MCP Server.

This module provides tools for analysing object dependencies using the
QueryDependenciesAgent stored procedure from the ODEX framework.
"""

import logging
from teradatasql import TeradataConnection
from teradata_mcp_server.tools.utils import create_response, rows_to_json

logger = logging.getLogger("teradata_mcp_server")


# ------------------ Tool: Query Dependencies Agent ------------------#
def handle_graph_queryDependenciesAgent(
    conn: TeradataConnection,
    object_name: str,
    max_depth_up: int = 3,
    max_depth_down: int = 3,
    exclude_objects: str = '',
    include_containers: str = '',
    edge_repository: str = 'DEV_01_ODEX_STD_0_V.ODEXRepository',
    return_format: str = 'detailed',
    tool_name: str | None = None,
    *args,
    **kwargs
):
    """
    Analyse object dependencies in Teradata. SUPPORTS WILDCARDS (%) and CSV patterns.

    Examples: 'DB.Table' (single), '%WBC%.%' (wildcard), 'DB.T1,DB.T2' (CSV)

    Finds upstream dependencies (what the object depends on) and downstream dependencies 
    (what depends on the object). Returns nodes and edges representing the dependency graph.

    Use this for:
    - Impact analysis: "What breaks if I change/drop this object?"
    - Lineage tracing: "Where does this data come from?"
    - Dependency discovery: "What does this object use?"
    - Documentation: Understanding object relationships
    - Pre-deployment validation: Checking impacts before making changes

    Arguments:
      object_name       - str: Object name pattern(s). **SUPPORTS WILDCARDS (%) and CSV**.

                          IMPORTANT: This is a STRING parameter (type: str), not an array.
                          Pass multiple patterns as a single comma-separated string.

                          SINGLE OBJECT:
                          'DEV01_StGeo_STD_T.mortgage_account' - Specific table

                          WILDCARDS (%):
                          '%WBC%.%' - All objects in databases containing WBC
                          'DEV01_StGeo_STD_T.%' - All objects in specific database
                          '%.mortgage_%' - All objects starting with 'mortgage_' across all databases

                          MULTIPLE OBJECTS (CSV format):
                          '%WBC%.%,%StGeo%.%' - All objects in WBC and StGeo databases
                          'DEV01_%.%,DEV02_%.%' - All objects in DEV01 and DEV02
                          'DB1.Table1,DB2.Table2,DB3.Table3' - Multiple specific objects

                          WHITESPACE HANDLING:
                          The stored procedure automatically trims whitespace from each pattern,
                          so these are EQUIVALENT:
                          ✅ '%WBC%.%,%StGeo%.%' (no spaces)
                          ✅ '%WBC%.%, %StGeo%.%' (spaces after commas - will be trimmed)
                          ✅ ' %WBC%.% , %StGeo%.% ' (extra spaces - will be trimmed)

                          However, for consistency and clarity, use NO spaces after commas.

                          HOW TO PASS IN CODE:
                          Python: object_name="%WBC%.%,%StGeo%.%"
                          JSON: {"object_name": "%WBC%.%,%StGeo%.%"}

                          CRITICAL: This is a STRING type parameter.
                          ✅ CORRECT: Pass as string: object_name="%WBC%.%,%StGeo%.%"
                          ❌ WRONG: Pass as array: object_name=["%WBC%.%", "%StGeo%.%"]

      max_depth_up      - int: Maximum levels to traverse upstream (0-10). Default: 3
                          0 = No upstream analysis (downstream only)
                          1 = Direct dependencies only
                          3 = Standard depth (good balance)
                          10 = Maximum depth (complete lineage trace)

      max_depth_down    - int: Maximum levels to traverse downstream (0-10). Default: 3
                          0 = No downstream analysis (upstream only)
                          1 = Direct dependents only
                          3 = Standard depth (typical blast radius)
                          10 = Maximum depth (complete impact analysis)

      exclude_objects   - str: Comma-separated list of patterns to exclude (SERVER-SIDE filter).
                          Also supports CSV format with automatic whitespace trimming.
                          Matches against DatabaseName.ObjectName format.

                          Database-Level Exclusions:
                          'PRD_%' - Excludes ALL objects in databases starting with PRD_
                          'PRD_%,TST_%,DFJ%' - Exclude multiple database families

                          Object-Level Exclusions:
                          '%.temp_%' - Excludes objects with 'temp_' in the name
                          'PROD_DB.%' - Excludes all objects in PROD_DB

                          Performance: Proper exclusions reduce results by 20-50%
                          Default: '' (empty string = no exclusions)

      include_containers - str: Comma-separated list of schemas/databases to include (whitelist).
                          Also supports CSV format with automatic whitespace trimming.
                          Empty = all containers (subject to exclude_objects)
                          Specified = ONLY listed containers analysed
                          Default: '' (all containers)

      edge_repository   - str: ODEX repository table containing dependency data.
                          Default: 'DEV_01_ODEX_STD_0_V.ODEXRepository'

      return_format     - str: Output format: 'detailed', 'summary', or 'edges_only'
                          'detailed' (default): Full nodes, edges, summary, metadata
                          'summary': High-level statistics only
                          'edges_only': Raw edge data for graph construction
                          Default: 'detailed'

    Returns:
      ResponseType: formatted response with dependency analysis results + metadata

    Example queries that trigger this tool:
      - "Show me dependencies for DEV02_WBC_STD_P.SP_POPULATE_WITH_COUNTS"
      - "Analyse dependencies for all WBC and StGeo objects"
      - "What breaks if I drop vw_borrower_risk_assessment?"
      - "Find upstream dependencies for MyTable, 5 levels deep"
      - "Impact analysis for all objects in DEV01 and DEV02 databases"

    Example calls with single and multiple patterns:
      # Single object
      handle_graph_queryDependenciesAgent(
          conn=connection,
          object_name="DEV01_StGeo_STD_T.mortgage_account"
      )

      # Wildcard pattern
      handle_graph_queryDependenciesAgent(
          conn=connection,
          object_name="%WBC%.%"  # All objects in WBC databases
      )

      # Multiple databases (CSV)
      handle_graph_queryDependenciesAgent(
          conn=connection,
          object_name="%WBC%.%,%StGeo%.%"  # String, not array!
      )

      # Multiple specific objects
      handle_graph_queryDependenciesAgent(
          conn=connection,
          object_name="DEV01_WBC_STD_T.Table1,DEV02_StGeo_STD_V.View1"
      )

      # With whitespace (will be trimmed by procedure)
      handle_graph_queryDependenciesAgent(
          conn=connection,
          object_name="%WBC%.%, %StGeo%.%"  # Spaces OK, will be trimmed
      )

    Technical Implementation Notes:
      - object_name is passed AS-IS to the stored procedure
      - The procedure uses STRTOK_SPLIT_TO_TABLE to parse CSV
      - Each pattern is automatically TRIM()'ed of whitespace by the procedure
      - CSV patterns like '%WBC%.%,%StGeo%.%' are handled server-side
      - The tool does NOT modify, validate, or parse the object_name parameter
      - All CSV parsing and whitespace handling is done by the stored procedure
    """
    logger.debug(
        f"Tool: handle_graph_queryDependenciesAgent: Args: object_name={object_name}, "
        f"max_depth_up={max_depth_up}, max_depth_down={max_depth_down}, "
        f"exclude_objects={exclude_objects}, include_containers={include_containers}, "
        f"edge_repository={edge_repository}, return_format={return_format}"
    )

    # Validate depth parameters (clamp to safe range)
    max_depth_up = max(0, min(10, max_depth_up))
    max_depth_down = max(0, min(10, max_depth_down))
    batch_size = 0

    try:
        with conn.cursor() as cur:
            # Call the QueryDependenciesAgent stored procedure
            #
            # CRITICAL: object_name parameter is passed AS-IS without modification
            #
            # The stored procedure handles CSV parsing internally using:
            #   STRTOK_SPLIT_TO_TABLE(1, TRIM(i_ObjectPatternList), ',')
            #
            # Each pattern is then trimmed: SELECT TRIM(o_token) AS fq_pattern
            #
            # This means the procedure accepts:
            #   - Single patterns: 'DEV01_StGeo_STD_T.mortgage_account'
            #   - CSV patterns: '%WBC%.%,%StGeo%.%'
            #   - CSV with spaces: '%WBC%.%, %StGeo%.%' (spaces are trimmed)
            call_sql = """
                CALL DEV_01_ODEX_RPT_0_P.QueryDependenciesAgentBatch(
                    ?,  -- 1. i_ObjectPatternList (CSV string)
                    ?,  -- 2. i_MaxDepthUp
                    ?,  -- 3. i_MaxDepthDown
                    ?,  -- 4. i_ExclFQObjectNames (CSV)
                    ?,  -- 5. i_InclContainers (CSV)
                    ?,  -- 6. i_ObjectDependencyTable
                    'N', -- 7. i_Output_ResultSet (we'll query volatile tables ourselves)
                    ?,  -- 8. i_BatchSize (0 = auto)
                    ?,  -- 9. o_EdgesUpTableName (output)
                    ?,  -- 10. o_EdgesDownTableName (output)
                    ?,  -- 11. o_SQLCode (output)
                    ?,  -- 12. o_SQLSTATE (output)
                    ?,  -- 13. o_RtnCode (output)
                    ?   -- 14. o_RtnMsg (output)
                )
            """

            # Parameters passed directly without modification
            # object_name is passed as a string, even if it contains commas (CSV format)
            # Parameters passed directly without modification
            # object_name is passed as a string, even if it contains commas (CSV format)
            params = [
                object_name,           # 1. Passed AS-IS - procedure handles CSV parsing
                max_depth_up,          # 2.
                max_depth_down,        # 3.
                exclude_objects,       # 4. Also supports CSV format
                include_containers,    # 5. Also supports CSV format
                edge_repository,       # 6.
                # 7. i_BatchSize (0 = auto) ← **YOU NEED TO ADD THIS**
                0,
                None,                  # 8. o_EdgesUpTableName (was 7, now 9)
                # 9. o_EdgesDownTableName (was 8, now 10)
                None,
                None,                  # 10. o_SQLCode (was 9, now 11)
                None,                  # 11. o_SQLSTATE (was 10, now 12)
                None,                  # 12. o_RtnCode (was 11, now 13)
                None                   # 13. o_RtnMsg (was 12, now 14)
            ]

            logger.debug(
                f"Tool: handle_graph_queryDependenciesAgent: "
                f"Calling procedure with object_name='{object_name}' "
                f"(CSV parsing handled by procedure)"
            )

            # Execute the stored procedure
            result = cur.execute(call_sql, params)

            # Fetch output parameters
            output_row = cur.fetchone()
            if not output_row:
                raise Exception(
                    "No output returned from QueryDependenciesAgent procedure")

            edges_up_table = output_row[0]
            edges_down_table = output_row[1]
            sql_code = output_row[2]
            sql_state = output_row[3]
            rtn_code = output_row[4]
            rtn_msg = output_row[5]

            logger.debug(
                f"Tool: handle_graph_queryDependenciesAgent: Procedure returned: "
                f"rtn_code={rtn_code}, edges_up={edges_up_table}, edges_down={edges_down_table}"
            )

            # Check for errors from the procedure
            if rtn_code != 0:
                error_msg = f"QueryDependenciesAgent failed: {rtn_msg} (Code: {rtn_code}, SQLCode: {sql_code}, SQLState: {sql_state})"
                logger.error(
                    f"Tool: handle_graph_queryDependenciesAgent: {error_msg}")
                return create_response(
                    {"error": error_msg},
                    {
                        "tool_name": tool_name if tool_name else "graph_queryDependenciesAgent",
                        "object_name": object_name,
                        "status": "error",
                        "rtn_code": rtn_code
                    }
                )

            # Query the volatile tables created by the procedure
            # Upstream edges
            edges_up_data = []
            if edges_up_table:
                cur.execute(
                    f"SELECT * FROM {edges_up_table} ORDER BY Depth, FQDependentObjectName")
                edges_up_data = rows_to_json(cur.description, cur.fetchall())

            # Downstream edges
            edges_down_data = []
            if edges_down_table:
                cur.execute(
                    f"SELECT * FROM {edges_down_table} ORDER BY Depth, FQDependentObjectName")
                edges_down_data = rows_to_json(cur.description, cur.fetchall())

            # Derive unique nodes from edges (matching procedure's logic)
            nodes_data = _derive_nodes_from_edges(
                edges_up_data, edges_down_data)

            # Format response based on requested format
            if return_format == 'summary':
                formatted_data = _format_summary(
                    nodes_data, edges_up_data, edges_down_data, object_name)
            elif return_format == 'edges_only':
                formatted_data = {
                    "upstream_edges": edges_up_data,
                    "downstream_edges": edges_down_data
                }
            else:  # detailed
                formatted_data = {
                    "nodes": nodes_data,
                    "upstream_edges": edges_up_data,
                    "downstream_edges": edges_down_data,
                    "summary": _create_summary_stats(nodes_data, edges_up_data, edges_down_data)
                }

            # Build metadata
            metadata = {
                "tool_name": tool_name if tool_name else "graph_queryDependenciesAgent",
                "object_name": object_name,
                "max_depth_up": max_depth_up,
                "max_depth_down": max_depth_down,
                "edge_repository": edge_repository,
                "return_format": return_format,
                "volatile_tables": {
                    "edges_up": edges_up_table,
                    "edges_down": edges_down_table
                },
                "counts": {
                    "nodes": len(nodes_data),
                    "upstream_edges": len(edges_up_data),
                    "downstream_edges": len(edges_down_data)
                },
                "status": "success",
                "rtn_code": rtn_code,
                "message": rtn_msg
            }

            logger.debug(
                f"Tool: handle_graph_queryDependenciesAgent: metadata: {metadata}")
            return create_response(formatted_data, metadata)

    except Exception as e:
        logger.error(
            f"Tool: handle_graph_queryDependenciesAgent: Error: {e}", exc_info=True)
        return create_response(
            {"error": str(e)},
            {
                "tool_name": tool_name if tool_name else "graph_queryDependenciesAgent",
                "object_name": object_name,
                "status": "error"
            }
        )


def _derive_nodes_from_edges(edges_up: list, edges_down: list) -> list:
    """
    Derive unique nodes from edge lists.

    Matches the procedure's logic: nodes are DISTINCT objects from edges.

    Arguments:
      edges_up   - List of upstream edge dictionaries
      edges_down - List of downstream edge dictionaries

    Returns:
      List of unique node dictionaries
    """
    # Helper function to safely convert Depth to integer
    def safe_depth_int(value):
        """Convert Depth field to integer, handling string/numeric types."""
        try:
            return int(value) if value is not None else 0
        except (ValueError, TypeError):
            return 0

    nodes = {}  # Use dict to deduplicate by FQDependentObjectName

    # Extract nodes from upstream edges
    for edge in edges_up:
        fq_name = edge.get('FQDependentObjectName')
        if fq_name and fq_name not in nodes:
            nodes[fq_name] = {
                'FQDependentObjectName': fq_name,
                'DependentObjectDBName': edge.get('DependentObjectDBName'),
                'DependentObjectName': edge.get('DependentObjectName'),
                'Direction': 'Upstream',
                'Depth': safe_depth_int(edge.get('Depth', 0)),
                'ObjectType': edge.get('Src_Kind') or edge.get('Tgt_Kind')
            }

    # Extract nodes from downstream edges
    for edge in edges_down:
        fq_name = edge.get('FQDependentObjectName')
        if fq_name and fq_name not in nodes:
            nodes[fq_name] = {
                'FQDependentObjectName': fq_name,
                'DependentObjectDBName': edge.get('DependentObjectDBName'),
                'DependentObjectName': edge.get('DependentObjectName'),
                'Direction': 'Downstream',
                'Depth': safe_depth_int(edge.get('Depth', 0)),
                'ObjectType': edge.get('Src_Kind') or edge.get('Tgt_Kind')
            }

    return list(nodes.values())


def _create_summary_stats(nodes: list, edges_up: list, edges_down: list) -> dict:
    """
    Create summary statistics from dependency data.

    Arguments:
      nodes      - List of node dictionaries
      edges_up   - List of upstream edges
      edges_down - List of downstream edges

    Returns:
      Dictionary with summary statistics
    """
    upstream_nodes = [n for n in nodes if n.get('Direction') == 'Upstream']
    downstream_nodes = [n for n in nodes if n.get('Direction') == 'Downstream']

    # Count by object type
    type_counts = {}
    for node in nodes:
        obj_type = node.get('ObjectType', 'Unknown')
        type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

    # Convert Depth values to integers before processing (Teradata byteint comes as string)
    def safe_depth(node):
        """Safely convert Depth field to integer, handling both string and numeric types."""
        depth = node.get('Depth', 0)
        try:
            return int(depth) if depth is not None else 0
        except (ValueError, TypeError):
            return 0

    return {
        "total_nodes": len(nodes),
        "upstream_nodes": len(upstream_nodes),
        "downstream_nodes": len(downstream_nodes),
        "total_edges": len(edges_up) + len(edges_down),
        "upstream_edges": len(edges_up),
        "downstream_edges": len(edges_down),
        "max_depth_upstream": max([abs(safe_depth(n)) for n in upstream_nodes], default=0),
        "max_depth_downstream": max([safe_depth(n) for n in downstream_nodes], default=0),
        "object_type_counts": type_counts
    }


def _format_summary(nodes: list, edges_up: list, edges_down: list, object_name: str) -> dict:
    """
    Format a concise summary of dependency analysis.

    Arguments:
      nodes       - List of node dictionaries
      edges_up    - List of upstream edges
      edges_down  - List of downstream edges
      object_name - Object name pattern(s) analysed (may be CSV)

    Returns:
      Dictionary with formatted summary
    """
    stats = _create_summary_stats(nodes, edges_up, edges_down)

    upstream_nodes = [n for n in nodes if n.get('Direction') == 'Upstream']
    downstream_nodes = [n for n in nodes if n.get('Direction') == 'Downstream']

    summary_text = f"""
DEPENDENCY ANALYSIS SUMMARY
{'=' * 60}

Object Pattern(s): {object_name}

OVERVIEW
  Total Nodes:               {stats['total_nodes']}
  Total Edges:               {stats['total_edges']}

UPSTREAM (What These Objects Depend On)
  Dependencies Found:        {stats['upstream_nodes']}
  Edges:                     {stats['upstream_edges']}
  Max Depth Reached:         {stats['max_depth_upstream']}

DOWNSTREAM (What Depends On These Objects)
  Dependents Found:          {stats['downstream_nodes']}
  Edges:                     {stats['downstream_edges']}
  Max Depth Reached:         {stats['max_depth_downstream']}
"""

    if stats['object_type_counts']:
        summary_text += "\nBY OBJECT TYPE\n"
        for obj_type, count in sorted(stats['object_type_counts'].items(), key=lambda x: x[1], reverse=True):
            summary_text += f"  {obj_type:20s} {count:3d}\n"

    return {
        "summary_text": summary_text,
        "statistics": stats,
        "upstream_objects": [n['FQDependentObjectName'] for n in upstream_nodes],
        "downstream_objects": [n['FQDependentObjectName'] for n in downstream_nodes]
    }


# ------------------ Tool: Find Root Objects ------------------#
def handle_graph_findRootObjects(
    conn: TeradataConnection,
    container_pattern: str,
    exclude_objects: str = '',
    edge_repository: str = 'DEV_01_ODEX_STD_0_V.ODEXRepository',
    object_types: str = '',
    return_format: str = 'detailed',
    tool_name: str | None = None,
    *args,
    **kwargs
):
    """
    Find root objects (objects with no upstream dependencies) in specified containers.

    Root objects are ideal starting points for downstream impact analysis as they
    represent the foundational data sources that nothing else depends upon.

    Use this for:
    - Finding starting points for downstream impact analysis
    - Identifying source tables and base objects in data pipelines
    - Discovering independent objects that can be safely analysed in isolation
    - Understanding data flow origins in a schema or database
    - Planning migration or refactoring by identifying foundation objects

    Arguments:
      container_pattern - str: Database/schema pattern(s) to search. SUPPORTS WILDCARDS (%) and CSV.

                          IMPORTANT: This is a STRING parameter (type: str), not an array.
                          Pass multiple patterns as a single comma-separated string.

                          SINGLE CONTAINER:
                          'DEV01_StGeo_STD_T' - Specific database

                          WILDCARDS (%):
                          '%WBC%' - All databases containing WBC
                          'DEV01_%' - All databases starting with DEV01_
                          '%_STD_T' - All databases ending with _STD_T

                          MULTIPLE CONTAINERS (CSV format):
                          '%WBC%,%StGeo%' - All WBC and StGeo databases
                          'DEV01_StGeo_STD_T,DEV02_WBC_STD_T' - Specific databases
                          'DEV01_%,DEV02_%' - All DEV01 and DEV02 databases

                          WHITESPACE HANDLING:
                          Whitespace is automatically trimmed, so these are equivalent:
                          ✅ '%WBC%,%StGeo%' (no spaces)
                          ✅ '%WBC%, %StGeo%' (spaces after commas - OK)

                          HOW TO PASS IN CODE:
                          Python: container_pattern="%WBC%,%StGeo%"
                          JSON: {"container_pattern": "%WBC%,%StGeo%"}

                          CRITICAL: This is a STRING type parameter.
                          ✅ CORRECT: Pass as string: container_pattern="%WBC%,%StGeo%"
                          ❌ WRONG: Pass as array: container_pattern=["%WBC%", "%StGeo%"]

      exclude_objects   - str: Comma-separated list of patterns to exclude (SERVER-SIDE filter).
                          Matches against DatabaseName.ObjectName format.

                          Common exclusion patterns:
                          'PRD_%,PROD_%' - Exclude production databases
                          '%.temp_%,%.bak_%' - Exclude temporary and backup objects
                          'DFJ%,C_D02%' - Exclude personal/sandbox schemas

                          Performance: Reduces result set and improves query time
                          Default: '' (empty string = no exclusions)

      edge_repository   - str: ODEX repository table containing dependency data.
                          Default: 'DEV_01_ODEX_STD_0_V.ODEXRepository'

      object_types      - str: Comma-separated list of object types to include (optional filter).
                          Examples: 'T' (tables), 'V' (views), 'P' (procedures), 'M' (macros)
                          Multiple: 'T,V' (tables and views only)
                          Empty = all object types included
                          Default: '' (all types)

      return_format     - str: Output format: 'detailed' or 'summary'
                          'detailed' (default): Full object list with metadata
                          'summary': High-level statistics and counts only
                          Default: 'detailed'

    Returns:
      ResponseType: formatted response with root objects + metadata

    Example queries that trigger this tool:
      - "Which objects in WBC and StGeo databases have no dependencies?"
      - "Find root objects in DEV01 databases"
      - "What are the starting points for impact analysis in StGeo?"
      - "Show me base tables with no upstream dependencies"
      - "Which objects should I start analysing for downstream impact?"

    Example calls:
      # Find root objects in WBC and StGeo databases
      handle_graph_findRootObjects(
          conn=connection,
          container_pattern="%WBC%,%StGeo%"
      )

      # Find only root tables (no views/procedures)
      handle_graph_findRootObjects(
          conn=connection,
          container_pattern="DEV01_%",
          object_types="T"
      )

      # Find root objects excluding production and temporary objects
      handle_graph_findRootObjects(
          conn=connection,
          container_pattern="%WBC%,%StGeo%",
          exclude_objects="PRD_%,%.temp_%,%.bak_%"
      )

      # Quick summary of root objects
      handle_graph_findRootObjects(
          conn=connection,
          container_pattern="DEV01_StGeo_STD_T",
          return_format="summary"
      )

    Technical Implementation:
      - Queries ODEX repository to find all objects in specified containers
      - Identifies objects that appear as sources but never as targets
      - These are "root" objects - they have no upstream dependencies
      - Results are filtered by exclude_objects and object_types parameters
      - Returns list of root objects suitable for downstream impact analysis
    """
    logger.debug(
        f"Tool: handle_graph_findRootObjects: Args: container_pattern={container_pattern}, "
        f"exclude_objects={exclude_objects}, edge_repository={edge_repository}, "
        f"object_types={object_types}, return_format={return_format}"
    )

    try:
        with conn.cursor() as cur:
            # Build the SQL query to find root objects using NOT EXISTS
            # Root objects are those that appear as sources but never as targets
            # (i.e., they have no upstream dependencies)

            # Parse container patterns (CSV support)
            container_patterns = [
                p.strip() for p in container_pattern.split(',') if p.strip()]

            # Build LIKE clauses for container patterns - used in main WHERE and NOT EXISTS
            container_conditions = []
            for pattern in container_patterns:
                container_conditions.append(
                    f"Src_Container_Name LIKE '{pattern}'")

            container_where = " OR ".join(container_conditions)

            # Build exclusion conditions if provided
            exclusion_where = ""
            if exclude_objects:
                exclude_patterns = [p.strip()
                                    for p in exclude_objects.split(',') if p.strip()]
                exclusion_conditions = []
                for pattern in exclude_patterns:
                    # Check if pattern contains a dot (fully qualified) or just database pattern
                    if '.' in pattern:
                        # Fully qualified pattern like 'DB.Object'
                        db_part, obj_part = pattern.split('.', 1)
                        exclusion_conditions.append(
                            f"(o1.Src_Container_Name LIKE '{db_part}' AND o1.Src_Object_Name LIKE '{obj_part}')"
                        )
                    else:
                        # Database-only pattern like 'PRD_%'
                        exclusion_conditions.append(
                            f"o1.Src_Container_Name LIKE '{pattern}'")

                if exclusion_conditions:
                    exclusion_where = " AND NOT (" + \
                        " OR ".join(exclusion_conditions) + ")"

            # Build object type filter if provided
            type_where = ""
            if object_types:
                type_list = [
                    f"'{t.strip()}'" for t in object_types.split(',') if t.strip()]
                if type_list:
                    type_where = f" AND o1.Src_Kind IN ({','.join(type_list)})"

            import time
            start_time = time.time()
            # Main query to find root objects using NOT EXISTS
            # This is more efficient than NOT IN for large datasets
            # The query finds objects that exist as sources but never as targets
            sql = f"""
LOCKING ROW FOR ACCESS 
SELECT DISTINCT
    o1.Src_Container_Name AS DatabaseName,
    o1.Src_Object_Name AS ObjectName,
    TRIM(o1.Src_Container_Name) || '.' || TRIM(o1.Src_Object_Name) AS FullyQualifiedName,
    o1.Src_Kind AS ObjectType,
    COUNT(DISTINCT o1.Tgt_Container_Name || '.' || o1.Tgt_Object_Name) AS DownstreamDependentCount
FROM {edge_repository} o1
WHERE ({container_where})
  {exclusion_where}
  {type_where}
  AND NOT EXISTS (
      SELECT 1
      FROM {edge_repository} o2
      WHERE o2.Tgt_Container_Name = o1.Src_Container_Name
        AND o2.Tgt_Object_Name = o1.Src_Object_Name
        AND ({container_where.replace('Src_Container_Name', 'o2.Src_Container_Name')})
  )
GROUP BY 
    o1.Src_Container_Name,
    o1.Src_Object_Name,
    o1.Src_Kind
ORDER BY 
    DownstreamDependentCount DESC,
    o1.Src_Container_Name,
    o1.Src_Object_Name
            """

            logger.debug(
                f"Tool: handle_graph_findRootObjects: Executing SQL:\n{sql}")

            # Execute query
            cur.execute(sql)

            query_time = time.time() - start_time
            print(f"Query execution took {query_time:.2f} seconds")

            # Fetch all results and convert to list of dictionaries
            # NOTE: rows_to_json takes (description, rows) - description FIRST!
            root_objects = rows_to_json(cur.description, cur.fetchall())

            logger.debug(
                f"Tool: handle_graph_findRootObjects: Found {len(root_objects)} root objects")
            if root_objects and len(root_objects) > 0:
                logger.debug(
                    f"Tool: handle_graph_findRootObjects: First object: {root_objects[0]}")

            # Safety check: ensure root_objects is a list of dicts, not a string
            if not isinstance(root_objects, list):
                logger.error(
                    f"Tool: handle_graph_findRootObjects: root_objects is not a list! Type: {type(root_objects)}")
                root_objects = []

            # Format results based on return_format
            if return_format == 'summary':
                formatted_data = _format_root_summary(
                    root_objects, container_pattern)
            else:  # detailed
                formatted_data = {
                    "root_objects": root_objects,
                    "summary": _create_root_summary_stats(root_objects, container_pattern)
                }

            # Build metadata
            metadata = {
                "tool_name": tool_name if tool_name else "graph_findRootObjects",
                "container_pattern": container_pattern,
                "exclude_objects": exclude_objects,
                "object_types": object_types,
                "edge_repository": edge_repository,
                "return_format": return_format,
                "sql": sql,
                "columns": [
                    {"name": desc[0], "type": "str"} for desc in cur.description
                ],
                "row_count": len(root_objects),
                "status": "success"
            }

            logger.debug(
                f"Tool: handle_graph_findRootObjects: metadata: {metadata}")
            return create_response(formatted_data, metadata)

    except Exception as e:
        logger.error(
            f"Tool: handle_graph_findRootObjects: Error: {e}", exc_info=True)
        return create_response(
            {"error": str(e)},
            {
                "tool_name": tool_name if tool_name else "graph_findRootObjects",
                "container_pattern": container_pattern,
                "status": "error"
            }
        )


def _create_root_summary_stats(root_objects: list, container_pattern: str) -> dict:
    """
    Create summary statistics for root objects analysis.

    Arguments:
      root_objects      - List of root object dictionaries
      container_pattern - Container pattern(s) searched

    Returns:
      Dictionary with summary statistics
    """
    # Count by object type
    type_counts = {}
    for obj in root_objects:
        obj_type = obj.get('ObjectType', 'Unknown')
        type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

    # Count by database
    db_counts = {}
    for obj in root_objects:
        db_name = obj.get('DatabaseName', 'Unknown')
        db_counts[db_name] = db_counts.get(db_name, 0) + 1

    # Calculate total downstream dependencies
    total_downstream = sum(
        int(obj.get('DownstreamDependentCount', 0)) if isinstance(obj.get('DownstreamDependentCount'), str)
        else obj.get('DownstreamDependentCount', 0)
        for obj in root_objects
    )

    # Find objects with most downstream dependencies
    top_objects = sorted(
        root_objects,
        key=lambda x: int(x.get('DownstreamDependentCount', 0)) if isinstance(x.get(
            'DownstreamDependentCount'), str) else x.get('DownstreamDependentCount', 0),
        reverse=True
    )[:10]

    return {
        "total_root_objects": len(root_objects),
        "container_pattern": container_pattern,
        "object_type_counts": type_counts,
        "database_counts": db_counts,
        "total_downstream_dependencies": total_downstream,
        "average_downstream_per_root": round(total_downstream / len(root_objects), 2) if root_objects else 0,
        "top_impact_objects": [
            {
                "name": obj.get('FullyQualifiedName'),
                "type": obj.get('ObjectType'),
                "downstream_count": obj.get('DownstreamDependentCount')
            }
            for obj in top_objects
        ]
    }


def _format_root_summary(root_objects: list, container_pattern: str) -> dict:
    """
    Format a concise summary of root objects analysis.

    Arguments:
      root_objects      - List of root object dictionaries
      container_pattern - Container pattern(s) searched

    Returns:
      Dictionary with formatted summary
    """
    stats = _create_root_summary_stats(root_objects, container_pattern)

    summary_text = f"""
ROOT OBJECTS ANALYSIS SUMMARY
{'=' * 60}

Container Pattern(s): {container_pattern}

OVERVIEW
  Total Root Objects Found:  {stats['total_root_objects']}
  Total Downstream Impact:   {stats['total_downstream_dependencies']} objects
  Avg Downstream per Root:   {stats['average_downstream_per_root']}

DEFINITION
  Root objects are objects with NO upstream dependencies.
  They represent foundational data sources and are ideal 
  starting points for downstream impact analysis.
"""

    if stats['object_type_counts']:
        summary_text += "\nBY OBJECT TYPE\n"
        for obj_type, count in sorted(stats['object_type_counts'].items(), key=lambda x: x[1], reverse=True):
            summary_text += f"  {obj_type:20s} {count:3d}\n"

    if stats['database_counts']:
        summary_text += "\nBY DATABASE\n"
        for db_name, count in sorted(stats['database_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
            summary_text += f"  {db_name:40s} {count:3d}\n"

        if len(stats['database_counts']) > 10:
            summary_text += f"  ... and {len(stats['database_counts']) - 10} more databases\n"

    if stats['top_impact_objects']:
        summary_text += "\nTOP 10 ROOT OBJECTS BY DOWNSTREAM IMPACT\n"
        for i, obj in enumerate(stats['top_impact_objects'], 1):
            summary_text += f"  {i:2d}. {obj['name']:50s} ({obj['type']}) → {obj['downstream_count']} dependents\n"

    summary_text += """
RECOMMENDATION
  Start your downstream impact analysis with the objects listed above,
  particularly those with higher downstream dependent counts, as they
  represent foundational objects with broader impact scope.
"""

    return {
        "summary_text": summary_text,
        "statistics": stats,
        "root_object_names": [obj.get('FullyQualifiedName') for obj in root_objects]
    }


# ------------------ Tool: graph_detectCycles ------------------#
def handle_graph_detectCycles(
    conn: TeradataConnection,
    container_pattern: str,
    excl_patterns: str = '',
    object_dependency_table: str = 'DEV_01_ODEX_STD_0_V.ODEXRepository',
    strategy: str = 'AUTO',
    max_edges_for_cte: int = 0,
    tool_name: str | None = None,
    *args,
    **kwargs
):
    """
    Detect circular dependencies (cycles) in the ODEX lineage graph.

    Analyses the dependency graph for the specified container pattern and returns
    all directed cycles found. Uses sophisticated algorithms (WCC partitioning +
    recursive CTE or iterative DFS) to efficiently detect cycles even in large graphs.

    Use this tool for:
      - Validating graph integrity (DAG property)
      - Finding objects that form circular references
      - Identifying "stub-then-replace" code patterns
      - Debugging topological sort hangs
      - Pre-deployment cycle checks

    Arguments:
      container_pattern       - str: CSV LIKE patterns for container scope.
                                SUPPORTS WILDCARDS (%) and CSV format.
                                Examples:
                                  'DFJ%'                  - Single database family
                                  '%WBC%,%StGeo%'         - Multiple database families
                                  'DEV01_%,DEV02_%,TST_%' - Multiple prefixes

      excl_patterns           - str: CSV LIKE patterns to exclude from scan.
                                Also supports CSV with automatic whitespace trimming.
                                Matches against DatabaseName.ObjectName format.
                                Examples:
                                  'DFJ%,C_D02%'         - Exclude specific databases
                                  '%.temp_%'            - Exclude temporary objects
                                  'PROD_%,TST_%'        - Exclude by prefix
                                Default: '' (no exclusions)

      object_dependency_table - str: ODEX repository view/table containing edges.
                                Default: 'DEV_01_ODEX_STD_0_V.ODEXRepository'

      strategy                - str: Cycle detection strategy:
                                'AUTO' (default) - WCC-partitioned single-pass CTE
                                                   Best for all workloads
                                'CTE'            - Full-graph unpartitioned CTE
                                                   Suitable for small graphs only
                                'DFS'            - Iterative DFS
                                                   Debugging/validation only
                                Default: 'AUTO'

      max_edges_for_cte       - int: Strategy selection hint (0 = use SP defaults)
                                When strategy='AUTO', the SP may override to DFS
                                if edge count exceeds this threshold.
                                0 = Let SP decide based on internal heuristics
                                Default: 0

    Returns:
      ResponseType: formatted response with cycle detection results

      Response structure:
        {
          "cycle_details": [       // Result Set 1: One row per node per cycle
            {
              "Cycle_Id": 1,
              "Cycle_Pos": 1,
              "Node_FQ": "DB.Object",
              "Cycle_Length": 3,
              "Component_Id": 5,
              "Strategy": "AUTO"
            },
            ...
          ],
          "cycle_summaries": [     // Result Set 2: One row per cycle (XmlAgg path)
            {
              "Cycle_Id": 1,
              "Cycle_Length": 3,
              "Component_Id": 5,
              "Strategy": "AUTO",
              "Cycle_Path": "A -> B -> C -> A"
            },
            ...
          ],
          "summary_stats": [       // Result Set 3: Single row with overall metrics
            {
              "Cycle_Count": 1,
              "Total_Nodes_In_Cycles": 3,
              "Components_With_Cycles": 1,
              "Edge_Count": 1250,
              "Components_Scanned": 15,
              "Strategy_Used": "AUTO",
              "Summary_Message": "1 cycle detected"
            }
          ]
        }

      Metadata:
        - tool_name, container_pattern, strategy_requested
        - result_set_counts (rows in each result set)
        - status, message

    Example queries that trigger this tool:
      - "Check for circular dependencies in WBC databases"
      - "Are there any cycles in the StGeo lineage?"
      - "Detect circular references in DFJ% databases"
      - "Find dependency loops in DEV01 and DEV02"

    Example calls:
      # Single database family
      handle_graph_detectCycles(
          conn=connection,
          container_pattern="DFJ%"
      )

      # Multiple families
      handle_graph_detectCycles(
          conn=connection,
          container_pattern="%WBC%,%StGeo%",
          excl_patterns="DFJ%,C_D02%"
      )

      # Force specific strategy
      handle_graph_detectCycles(
          conn=connection,
          container_pattern="DEV01_%",
          strategy="CTE"  # Use CTE regardless of graph size
      )

    Technical Implementation Notes:
      - The SP uses DYNAMIC RESULT SETS 3 to return three cursors
      - container_pattern and excl_patterns are passed AS-IS to the SP
      - The SP uses STRTOK_SPLIT_TO_TABLE to parse CSV patterns
      - Each pattern is automatically TRIM()'ed by the SP
      - All CSV parsing and whitespace handling is done server-side
      - The tool uses cursor.nextset() to fetch all three result sets
      - strategy is normalised to uppercase before passing to SP
      - max_edges_for_cte=0 means "let SP decide"
    """
    logger.debug(
        f"Tool: handle_graph_detectCycles: Args: container_pattern={container_pattern}, "
        f"excl_patterns={excl_patterns}, object_dependency_table={object_dependency_table}, "
        f"strategy={strategy}, max_edges_for_cte={max_edges_for_cte}"
    )

    # Normalise strategy to uppercase
    strategy_norm = strategy.upper() if strategy else 'AUTO'

    # Validate strategy (must be AUTO, CTE, or DFS)
    if strategy_norm not in ('AUTO', 'CTE', 'DFS'):
        logger.warning(
            f"Tool: handle_graph_detectCycles: Invalid strategy '{strategy}', using 'AUTO'"
        )
        strategy_norm = 'AUTO'

    try:
        with conn.cursor() as cur:
            # ------------------------------------------------------------------
            # Call the graph_detectCycles stored procedure
            #
            # CRITICAL: container_pattern and excl_patterns are passed AS-IS
            #
            # Signature:
            #   IN  i_ContainerPattern      VARCHAR(2000)
            #   IN  i_ExclPatterns          VARCHAR(2000)
            #   IN  i_ObjectDependencyTable VARCHAR(257)
            #   IN  i_Strategy              CHAR(4)
            #   IN  i_MaxEdgesForCTE        INTEGER
            #   OUT o_CycleCount            INTEGER
            #   OUT o_RtnCode               SMALLINT
            #   OUT o_RtnMsg                VARCHAR(10000)
            #
            # DYNAMIC RESULT SETS 3:
            #   The SP declares three cursors WITH RETURN:
            #     cur_CycleDetails, cur_CycleSummaries, cur_SummaryStats
            #   Each cursor is PREPARE'd from dynamic SQL, then OPEN'd
            #   The open cursors become result sets 1, 2, 3
            #
            # We use cursor.nextset() to fetch all three result sets
            # ------------------------------------------------------------------
            logger.debug(
                f"Tool: handle_graph_detectCycles: Calling DEV_01_ODEX_RPT_0_P.graph_detectCycles"
            )

            # Prepare OUT parameter placeholders (3 OUT parameters)
            cur.execute(
                """
                CALL DEV_01_ODEX_RPT_0_P.graph_detectCycles(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    # IN parameters
                    container_pattern,
                    excl_patterns,
                    object_dependency_table,
                    strategy_norm,
                    max_edges_for_cte,
                    # OUT parameter placeholders (3 OUT params)
                    0,      # o_CycleCount
                    0,      # o_RtnCode
                    ''      # o_RtnMsg
                )
            )

            # ------------------------------------------------------------------
            # Fetch Result Set 1: Cycle Details (one row per node per cycle)
            # ------------------------------------------------------------------
            cycle_details_desc = cur.description
            cycle_details_raw = cur.fetchall()
            logger.debug(
                f"Tool: handle_graph_detectCycles: Fetched result set 1 (Cycle Details): "
                f"{len(cycle_details_raw)} rows"
            )

            # ------------------------------------------------------------------
            # Move to Result Set 2: Cycle Summaries (one row per cycle)
            # ------------------------------------------------------------------
            if not cur.nextset():
                logger.warning(
                    "Tool: handle_graph_detectCycles: No second result set available"
                )
                cycle_summaries_raw = []
                cycle_summaries_desc = None
            else:
                cycle_summaries_desc = cur.description
                cycle_summaries_raw = cur.fetchall()
                logger.debug(
                    f"Tool: handle_graph_detectCycles: Fetched result set 2 (Cycle Summaries): "
                    f"{len(cycle_summaries_raw)} rows"
                )

            # ------------------------------------------------------------------
            # Move to Result Set 3: Summary Statistics (single row)
            # ------------------------------------------------------------------
            if not cur.nextset():
                logger.warning(
                    "Tool: handle_graph_detectCycles: No third result set available"
                )
                summary_stats_raw = []
                summary_stats_desc = None
            else:
                summary_stats_desc = cur.description
                summary_stats_raw = cur.fetchall()
                logger.debug(
                    f"Tool: handle_graph_detectCycles: Fetched result set 3 (Summary Stats): "
                    f"{len(summary_stats_raw)} rows"
                )

            # ------------------------------------------------------------------
            # Convert raw result sets to JSON-serialisable structures
            # ------------------------------------------------------------------
            cycle_details_json = rows_to_json(
                cycle_details_desc, cycle_details_raw)
            cycle_summaries_json = rows_to_json(
                cycle_summaries_desc, cycle_summaries_raw) if cycle_summaries_desc else []
            summary_stats_json = rows_to_json(
                summary_stats_desc, summary_stats_raw) if summary_stats_desc else []

            logger.debug(
                f"Tool: handle_graph_detectCycles: Converted result sets to JSON: "
                f"cycle_details={len(cycle_details_json)}, "
                f"cycle_summaries={len(cycle_summaries_json)}, "
                f"summary_stats={len(summary_stats_json)}"
            )

            # ------------------------------------------------------------------
            # Assemble response
            #
            # Return all three result sets in the response data
            # ------------------------------------------------------------------
            response_data = {
                "cycle_details":   cycle_details_json,
                "cycle_summaries": cycle_summaries_json,
                "summary_stats":   summary_stats_json
            }

            metadata = {
                "tool_name":              tool_name if tool_name else "graph_detectCycles",
                "container_pattern":      container_pattern,
                "excl_patterns":          excl_patterns,
                "object_dependency_table": object_dependency_table,
                "strategy_requested":     strategy_norm,
                "result_set_counts": {
                    "cycle_details":      len(cycle_details_json),
                    "cycle_summaries":    len(cycle_summaries_json),
                    "summary_stats":      len(summary_stats_json)
                },
                "status":                 "success",
                "message":                "Cycle detection completed successfully"
            }

            logger.debug(
                f"Tool: handle_graph_detectCycles: metadata: {metadata}")
            return create_response(response_data, metadata)

    except Exception as e:
        logger.error(
            f"Tool: handle_graph_detectCycles: Error: {e}", exc_info=True)
        return create_response(
            {"error": str(e)},
            {
                "tool_name": tool_name if tool_name else "graph_detectCycles",
                "container_pattern": container_pattern,
                "status": "error"
            }
        )


# ------------------------------------------------------------------
# Tool registration descriptor
#
# Add this entry to the GRAPH_TOOLS list in graph_tools.py (or the
# tools registry in your MCP server configuration) so the tool is
# exposed via the MCP protocol.
#
# Example registration dict (matches pattern in graph_tools.py):
# ------------------------------------------------------------------
GRAPH_DETECT_CYCLES_TOOL = {
    "name": "graph_detectCycles",
    "handler": handle_graph_detectCycles,
    "description": (
        "Detect circular references (cycles) in the ODEX lineage graph. "
        "Calls the graph_detectCycles stored procedure which uses WCC partitioning "
        "and a single-pass WITH RECURSIVE CTE to find all directed cycles in the "
        "dependency graph for the specified container scope. "
        "Returns each cycle as an ordered list of nodes with a human-readable path string. "
        "Use this to validate graph integrity, find stub-then-replace patterns, "
        "or identify objects that will cause topological sort to hang."
    ),
    "parameters": {
        "container_pattern": {
            "type": "string",
            "description": (
                "CSV LIKE patterns for containers (databases/schemas) to scan. "
                "Supports wildcards: 'DFJ%' or '%WBC%,%StGeo%' for multiple."
            ),
            "required": True
        },
        "excl_patterns": {
            "type": "string",
            "description": (
                "CSV LIKE patterns to exclude from the scan. "
                "Matches against FQ object names (Database.ObjectName). "
                "Example: 'DFJ%,C_D02%'. Default: '' (no exclusions)."
            ),
            "default": ""
        },
        "object_dependency_table": {
            "type": "string",
            "description": (
                "ODEX repository view/table containing dependency edges. "
                "Default: 'DEV_01_ODEX_STD_0_V.ODEXRepository'."
            ),
            "default": "DEV_01_ODEX_STD_0_V.ODEXRepository"
        },
        "strategy": {
            "type": "string",
            "description": (
                "Cycle detection strategy: "
                "'AUTO' (default) = WCC-partitioned single-pass CTE, best for all workloads; "
                "'CTE' = full-graph unpartitioned CTE, small graphs only; "
                "'DFS' = iterative DFS, debugging only."
            ),
            "default": "AUTO"
        },
        "max_edges_for_cte": {
            "type": "integer",
            "description": "Strategy selection hint (0 = use SP defaults). Default: 0.",
            "default": 0
        }
    }
}

"""
Connected Components analysis tool for Teradata MCP Server.

This module provides the graph_connectedComponents tool which identifies all
Weakly Connected Components (WCC) in the ODEX lineage graph. A connected
component is a maximal set of nodes reachable from one another when edge
direction is ignored.

The tool calls the DEV_01_ODEX_RPT_0_P.graph_connectedComponents stored
procedure (which delegates to graph_buildWCC helper) and returns three
result sets: node details, component summaries, and overall statistics.
"""


logger = logging.getLogger("teradata_mcp_server")


# ------------------ Tool: Connected Components ------------------#
def handle_graph_connectedComponents(
    conn: TeradataConnection,
    container_pattern: str,
    excl_patterns: str = '',
    object_dependency_table: str = 'DEV_01_ODEX_STD_0_V.ODEXRepository',
    tool_name: str | None = None,
    *args,
    **kwargs
):
    """
    Identify all Weakly Connected Components (WCC) in the ODEX lineage graph.

    A connected component is a maximal set of nodes where every node can reach
    every other node when edge direction is ignored. This partitions the graph
    into isolated sub-graphs.

    Use this tool for:
      - Understanding graph structure and partitioning
      - Identifying isolated sub-graphs
      - Scoping downstream impact analysis to a single component
      - Pre-filtering before cycle detection (cycles exist only within a component)
      - Identifying "islands" of related objects for migration or refactoring
      - Estimating blast radius

    Arguments:
      container_pattern       - str: CSV LIKE patterns for container scope.
                                SUPPORTS WILDCARDS (%) and CSV format.
                                Examples: '%WBC%', '%WBC%,%StGeo%', 'DEV01_%,DEV02_%'

                                CRITICAL: STRING type, not array.
                                CORRECT: container_pattern="%WBC%,%StGeo%"
                                WRONG:   container_pattern=["%WBC%", "%StGeo%"]

      excl_patterns           - str: CSV LIKE patterns to exclude.
                                Matches against DatabaseName.ObjectName.
                                Default: '' (no exclusions)

      object_dependency_table - str: ODEX repository view/table.
                                Default: 'DEV_01_ODEX_STD_0_V.ODEXRepository'

    Returns:
      ResponseType: formatted response with connected component results

      Response structure:
        {
          "node_details":        [...],  // One row per node with Component_Id
          "component_summaries": [...],  // One row per component with counts, node list
          "summary_stats":       [...]   // Single row with overall metrics
        }
    """
    logger.debug(
        f"Tool: handle_graph_connectedComponents: Args: "
        f"container_pattern={container_pattern}, "
        f"excl_patterns={excl_patterns}, "
        f"object_dependency_table={object_dependency_table}"
    )

    try:
        with conn.cursor() as cur:
            # ------------------------------------------------------------------
            # Call graph_connectedComponents (delegates to graph_buildWCC)
            #
            # Signature:
            #   IN  i_ContainerPattern, i_ExclPatterns, i_ObjectDependencyTable
            #   OUT o_ComponentCount, o_NodeCount, o_EdgeCount, o_RtnCode, o_RtnMsg
            #
            # DYNAMIC RESULT SETS 3:
            #   cur_NodeDetails, cur_CompSummaries, cur_SummaryStats
            # ------------------------------------------------------------------
            call_sql = """
                CALL DEV_01_ODEX_RPT_0_P.graph_connectedComponents(
                    ?,  -- 1. i_ContainerPattern (CSV string)
                    ?,  -- 2. i_ExclPatterns (CSV string)
                    ?,  -- 3. i_ObjectDependencyTable
                    ?,  -- 4. o_ComponentCount (output)
                    ?,  -- 5. o_NodeCount (output)
                    ?,  -- 6. o_EdgeCount (output)
                    ?,  -- 7. o_RtnCode (output)
                    ?   -- 8. o_RtnMsg (output)
                )
            """

            # IN params passed AS-IS; OUT params as placeholders
            params = [
                container_pattern,          # 1. Passed AS-IS
                excl_patterns,              # 2. Passed AS-IS
                object_dependency_table,    # 3. Repository table
                0,                          # 4. o_ComponentCount
                0,                          # 5. o_NodeCount
                0,                          # 6. o_EdgeCount
                0,                          # 7. o_RtnCode
                ''                          # 8. o_RtnMsg
            ]

            logger.debug(
                f"Tool: handle_graph_connectedComponents: "
                f"Calling procedure with container_pattern='{container_pattern}'"
            )

            # Execute the stored procedure
            cur.execute(call_sql, params)

            # ------------------------------------------------------------------
            # Fetch Result Set 1: Node Details
            # ------------------------------------------------------------------
            node_details_desc = cur.description
            node_details_raw = cur.fetchall()
            logger.debug(
                f"Tool: handle_graph_connectedComponents: "
                f"Result set 1 (Node Details): {len(node_details_raw)} rows"
            )

            # ------------------------------------------------------------------
            # Result Set 2: Component Summaries
            # ------------------------------------------------------------------
            if not cur.nextset():
                logger.warning(
                    "Tool: handle_graph_connectedComponents: "
                    "No second result set available"
                )
                comp_summaries_raw = []
                comp_summaries_desc = None
            else:
                comp_summaries_desc = cur.description
                comp_summaries_raw = cur.fetchall()
                logger.debug(
                    f"Tool: handle_graph_connectedComponents: "
                    f"Result set 2 (Component Summaries): "
                    f"{len(comp_summaries_raw)} rows"
                )

            # ------------------------------------------------------------------
            # Result Set 3: Summary Statistics
            # ------------------------------------------------------------------
            if not cur.nextset():
                logger.warning(
                    "Tool: handle_graph_connectedComponents: "
                    "No third result set available"
                )
                summary_stats_raw = []
                summary_stats_desc = None
            else:
                summary_stats_desc = cur.description
                summary_stats_raw = cur.fetchall()
                logger.debug(
                    f"Tool: handle_graph_connectedComponents: "
                    f"Result set 3 (Summary Stats): "
                    f"{len(summary_stats_raw)} rows"
                )

            # ------------------------------------------------------------------
            # Convert to JSON-serialisable structures
            # ------------------------------------------------------------------
            node_details_json = rows_to_json(
                node_details_desc, node_details_raw
            )
            comp_summaries_json = rows_to_json(
                comp_summaries_desc, comp_summaries_raw
            ) if comp_summaries_desc else []
            summary_stats_json = rows_to_json(
                summary_stats_desc, summary_stats_raw
            ) if summary_stats_desc else []

            # ------------------------------------------------------------------
            # Assemble response
            # ------------------------------------------------------------------
            response_data = {
                "node_details":        node_details_json,
                "component_summaries": comp_summaries_json,
                "summary_stats":       summary_stats_json
            }

            metadata = {
                "tool_name": (
                    tool_name if tool_name
                    else "graph_connectedComponents"
                ),
                "container_pattern":       container_pattern,
                "excl_patterns":           excl_patterns,
                "object_dependency_table": object_dependency_table,
                "result_set_counts": {
                    "node_details":        len(node_details_json),
                    "component_summaries": len(comp_summaries_json),
                    "summary_stats":       len(summary_stats_json)
                },
                "status":  "success",
                "message": "Connected components analysis completed successfully"
            }

            logger.debug(
                f"Tool: handle_graph_connectedComponents: metadata: {metadata}"
            )
            return create_response(response_data, metadata)

    except Exception as e:
        logger.error(
            f"Tool: handle_graph_connectedComponents: Error: {e}",
            exc_info=True
        )
        return create_response(
            {"error": str(e)},
            {
                "tool_name": (
                    tool_name if tool_name
                    else "graph_connectedComponents"
                ),
                "container_pattern": container_pattern,
                "status": "error"
            }
        )


# ------------------------------------------------------------------
# Tool registration descriptor
# ------------------------------------------------------------------
GRAPH_CONNECTED_COMPONENTS_TOOL = {
    "name": "graph_connectedComponents",
    "handler": handle_graph_connectedComponents,
    "description": (
        "Identify all Weakly Connected Components (WCC) in the ODEX lineage graph. "
        "A connected component is a maximal set of nodes reachable from one another "
        "when edge direction is ignored. Calls graph_connectedComponents which "
        "delegates to the shared graph_buildWCC helper for edge loading and WCC "
        "propagation. Returns node-to-component mapping, per-component summaries "
        "(with cycle candidate flags), and overall statistics. "
        "Use to understand graph structure, identify isolated sub-graphs, "
        "scope impact analysis, or pre-filter before cycle detection."
    ),
    "parameters": {
        "container_pattern": {
            "type": "string",
            "description": (
                "CSV LIKE patterns for containers (databases/schemas) to scan. "
                "Supports wildcards: 'DFJ%' or '%WBC%,%StGeo%' for multiple."
            ),
            "required": True
        },
        "excl_patterns": {
            "type": "string",
            "description": (
                "CSV LIKE patterns to exclude from the scan. "
                "Matches against FQ object names (Database.ObjectName). "
                "Example: 'DFJ%,C_D02%'. Default: '' (no exclusions)."
            ),
            "default": ""
        },
        "object_dependency_table": {
            "type": "string",
            "description": (
                "ODEX repository view/table containing dependency edges. "
                "Default: 'DEV_01_ODEX_STD_0_V.ODEXRepository'."
            ),
            "default": "DEV_01_ODEX_STD_0_V.ODEXRepository"
        }
    }
}


"""
BFS hop-distance analysis tool for Teradata MCP Server.

This module provides the graph_bfsLevels tool which computes Breadth-First
Search shortest-path hop distances from one or more root nodes in the ODEX
dependency graph.

Unlike graph_queryDependenciesAgent (which returns edges and full lineage
paths), this tool returns one row per reachable node with signed hop
distances and a direction flag — purpose-built for migration wave planning,
blast-radius sizing, and cycle member depth analysis.

The tool calls DEV_01_ODEX_RPT_0_P.graph_bfsLevels which performs two
independent multi-source BFS passes (upstream: Tgt→Src, downstream: Src→Tgt)
using volatile working tables, seeding all root nodes simultaneously so each
non-root node settles at the distance to its nearest root.
"""

# ------------------ Tool: graph_bfsLevels ------------------#
def handle_graph_bfsLevels(
    conn: TeradataConnection,
    root_node_list: str,
    max_depth_up: int = 10,
    max_depth_down: int = 10,
    exclude_objects: str = '',
    include_containers: str = '',
    edge_repository: str = 'DEV_01_ODEX_STD_0_V.ODEXRepository',
    tool_name: str | None = None,
    *args,
    **kwargs
):
    """
    Compute BFS shortest-path hop distances from one or more root nodes.

    WHEN TO USE THIS TOOL vs graph_queryDependenciesAgent:
    -------------------------------------------------------
    Use graph_bfsLevels when asked to:
      - Sequence objects for deployment or migration (ORDER BY upstream_level
        gives correct topological deployment order)
      - Group objects by migration wave (nearest_root identifies which of the
        input root tables each object belongs to)
      - Find which migration root table each object is closest to across a
        multi-root migration scope
      - Identify cycle members by depth (direction='BOTH' nodes with unequal
        absolute upstream/downstream levels are cycle candidates)
      - Count objects within N hops of a change (blast-radius sizing)
      - Answer "how far is object X from the migration root tables?"

    Do NOT use graph_bfsLevels for general lineage tracing, impact path
    analysis, or questions about which objects depend on which. Use
    graph_queryDependenciesAgent for those — it returns the full edge set
    with relationship detail. graph_bfsLevels returns distances, not paths.

    KEY DISTINCTION — root_node_list accepts EXACT FQ names only (no
    wildcards). Use graph_findRootObjects first to identify the seed
    objects, then pass their exact FQ names here.

    Arguments:
      root_node_list    - str: CSV of exact fully-qualified root node names.
                          No wildcards — exact names only.

                          SINGLE ROOT:
                          'DEV01_StGeo_STD_T.mortgage_account'

                          MULTIPLE ROOTS (CSV):
                          'DEV01_StGeo_STD_T.mortgage_account,
                           DEV01_StGeo_STD_T.mortgage_borrower,
                           DEV01_StGeo_STD_T.mortgage_property'

                          CRITICAL: Exact FQ names, no wildcards.
                          Use graph_findRootObjects or
                          graph_queryDependenciesAgent first to discover names.

      max_depth_up      - int: Maximum upstream hops to traverse.
                          0 = skip upstream analysis entirely.
                          Default: 10

      max_depth_down    - int: Maximum downstream hops to traverse.
                          0 = skip downstream analysis entirely.
                          Default: 10

      exclude_objects   - str: CSV of FQ object name LIKE patterns to exclude.
                          Matches Src and Tgt sides of every edge traversed.
                          Example: 'DFJ%,C_D02%,%.temp_%'
                          Default: '' (no exclusions)

      include_containers - str: CSV of container name LIKE patterns to include.
                           Only edges where both Src and Tgt containers match
                           at least one pattern are traversed.
                           Empty = all containers.
                           Example: 'DEV01_StGeo%,MF_STGEO%,TABLEAU%'
                           Default: '' (all containers)

      edge_repository   - str: ODEX lineage view containing dependency edges.
                          Default: 'DEV_01_ODEX_STD_0_V.ODEXRepository'

    Returns:
      ResponseType: formatted response with BFS node results + metadata

      Response structure:
        {
          "nodes": [
            {
              "node":             "DEV01_StGeo_STD_T.mortgage_account",
              "container_name":   "DEV01_StGeo_STD_T",
              "object_name":      "mortgage_account",
              "object_kind":      "Table",
              "upstream_level":   0,       // NULL if not traversed upstream
              "downstream_level": 0,       // NULL if not traversed downstream
              "nearest_root":     "DEV01_StGeo_STD_T.mortgage_account",
              "direction":        "ROOT",  // ROOT / U / D / BOTH
              "is_root":          "Y"
            },
            ...
          ],
          "cycle_candidates": [...],  // direction='BOTH' nodes with unequal
                                      // absolute upstream/downstream levels
          "summary": {
            "total_nodes":      46,
            "root_nodes":       3,
            "upstream_only":    12,
            "downstream_only":  28,
            "both_directions":  3,
            "cycle_candidates": 1
          }
        }

      direction values:
        ROOT  - One of the input root nodes (upstream_level=0, downstream_level=0)
        U     - Reachable upstream only (negative upstream_level)
        D     - Reachable downstream only (positive downstream_level)
        BOTH  - Reachable in both directions — possible cycle member.
                Unequal absolute levels (e.g. upstream_level=-1,
                downstream_level=+4) strongly indicate a cycle back-edge.
                Equal absolute levels indicate a shared dependency pattern.

      nearest_root:
        When multiple root nodes are supplied, nearest_root identifies which
        of the roots this object is closest to. Use this to group objects
        into migration waves — one wave per root table.

    Example queries that trigger this tool:
      - "Sequence the StGeo objects for deployment"
      - "Group all StGeo objects by their nearest migration root table"
      - "Which migration root is mortgage_borrower closest to?"
      - "How many objects are within 3 hops of mortgage_account?"
      - "Show me the migration wave plan for the three StGeo source tables"
      - "Are there any cycle members in the StGeo graph and how deep are they?"
      - "Give me the blast radius of changing mortgage_account"
      - "What order should I deploy the StGeo objects in?"

    Example calls:
      # Single root, both directions, 10 hops
      handle_graph_bfsLevels(
          conn=connection,
          root_node_list="DEV01_StGeo_STD_T.mortgage_account"
      )

      # Multi-root migration wave planning
      handle_graph_bfsLevels(
          conn=connection,
          root_node_list=(
              "DEV01_StGeo_STD_T.mortgage_account,"
              "DEV01_StGeo_STD_T.mortgage_borrower,"
              "DEV01_StGeo_STD_T.mortgage_property"
          ),
          include_containers="DEV01_StGeo%,MF_STGEO%,TABLEAU%,POWERBI%"
      )

      # Upstream ancestry only, 5 hops
      handle_graph_bfsLevels(
          conn=connection,
          root_node_list="DEV01_StGeo_STD_T.mortgage_account",
          max_depth_up=5,
          max_depth_down=0
      )

      # With exclusions
      handle_graph_bfsLevels(
          conn=connection,
          root_node_list="DEV01_StGeo_STD_T.mortgage_account",
          exclude_objects="DEV01_StGeo_STD_M.geographic_risk_analysis",
          include_containers="DEV01_StGeo%,MF_STGEO%"
      )

    Technical Implementation Notes:
      - Calls DEV_01_ODEX_RPT_0_P.graph_bfsLevels (DYNAMIC RESULT SETS 1)
      - The SP performs two independent multi-source BFS passes using volatile
        working tables seeded with ALL root nodes simultaneously
      - Upstream pass follows Tgt→Src edges; downstream follows Src→Tgt edges
      - Each non-root node settles at the distance to its nearest root
      - Depth cap enforced in both BFS loop iteration count and result set filter
      - root_node_list is passed AS-IS; SP uses STRTOK_SPLIT_TO_TABLE to parse CSV
      - SP signature:
          IN  i_RootNodeList       VARCHAR(1000)
          IN  i_MaxDepthUp         BYTEINT
          IN  i_MaxDepthDown       BYTEINT
          IN  i_ExclFQObjectNames  VARCHAR(1000)
          IN  i_InclContainers     VARCHAR(500)
          IN  i_ObjectLineageView  VARCHAR(257)
          OUT o_SQLCode            INTEGER
          OUT o_SQLSTATE           CHAR(5)
          OUT o_RtnCode            SMALLINT
          OUT o_RtnMsg             VARCHAR(10000)
    """
    logger.debug(
        f"Tool: handle_graph_bfsLevels: Args: root_node_list={root_node_list}, "
        f"max_depth_up={max_depth_up}, max_depth_down={max_depth_down}, "
        f"exclude_objects={exclude_objects}, include_containers={include_containers}, "
        f"edge_repository={edge_repository}"
    )

    # Clamp depth parameters to safe range
    max_depth_up = max(0, min(10, int(max_depth_up)))
    max_depth_down = max(0, min(10, int(max_depth_down)))

    try:
        with conn.cursor() as cur:
            # ------------------------------------------------------------------
            # Call DEV_01_ODEX_RPT_0_P.graph_bfsLevels
            #
            # Signature (10 parameters):
            #   IN  i_RootNodeList       VARCHAR(1000)  -- CSV exact FQ names
            #   IN  i_MaxDepthUp         BYTEINT
            #   IN  i_MaxDepthDown       BYTEINT
            #   IN  i_ExclFQObjectNames  VARCHAR(1000)
            #   IN  i_InclContainers     VARCHAR(500)
            #   IN  i_ObjectLineageView  VARCHAR(257)
            #   OUT o_SQLCode            INTEGER
            #   OUT o_SQLSTATE           CHAR(5)
            #   OUT o_RtnCode            SMALLINT
            #   OUT o_RtnMsg             VARCHAR(10000)
            #
            # DYNAMIC RESULT SETS 1:
            #   cur_Result: one row per reachable node
            #   Columns: node, container_name, object_name, object_kind,
            #            upstream_level, downstream_level, nearest_root,
            #            direction, is_root
            #
            # OUT parameters returned as first fetchone() row
            # Result set follows via cur.nextset()
            # ------------------------------------------------------------------
            call_sql = """
                CALL DEV_01_ODEX_RPT_0_P.graph_bfsLevels(
                    ?,   -- 1. i_RootNodeList       (CSV exact FQ names)
                    ?,   -- 2. i_MaxDepthUp
                    ?,   -- 3. i_MaxDepthDown
                    ?,   -- 4. i_ExclFQObjectNames  (CSV LIKE patterns)
                    ?,   -- 5. i_InclContainers     (CSV LIKE patterns)
                    ?,   -- 6. i_ObjectLineageView
                    ?,   -- 7. o_SQLCode            (output)
                    ?,   -- 8. o_SQLSTATE           (output)
                    ?,   -- 9. o_RtnCode            (output)
                    ?    -- 10. o_RtnMsg            (output)
                )
            """

            params = [
                root_node_list,             # 1. Passed AS-IS — SP handles CSV parsing
                max_depth_up,               # 2.
                max_depth_down,             # 3.
                exclude_objects or '',      # 4. Empty string if not supplied
                include_containers or '',   # 5. Empty string if not supplied
                edge_repository,            # 6.
                0,                          # 7. o_SQLCode  placeholder
                '',                         # 8. o_SQLSTATE placeholder
                0,                          # 9. o_RtnCode  placeholder
                ''                          # 10. o_RtnMsg  placeholder
            ]

            logger.debug(
                f"Tool: handle_graph_bfsLevels: "
                f"Calling DEV_01_ODEX_RPT_0_P.graph_bfsLevels"
            )

            cur.execute(call_sql, params)

            # ------------------------------------------------------------------
            # Fetch OUT parameters from first row
            # ------------------------------------------------------------------
            output_row = cur.fetchone()
            if not output_row:
                raise Exception(
                    "No output returned from graph_bfsLevels procedure"
                )

            sql_code = output_row[0]
            sql_state = output_row[1]
            rtn_code = output_row[2]
            rtn_msg = output_row[3]

            logger.debug(
                f"Tool: handle_graph_bfsLevels: Procedure returned: "
                f"rtn_code={rtn_code}, sql_code={sql_code}, rtn_msg={rtn_msg}"
            )

            # Check for SP-level errors
            if rtn_code != 0:
                error_msg = (
                    f"graph_bfsLevels failed: {rtn_msg} "
                    f"(RtnCode: {rtn_code}, SQLCode: {sql_code}, "
                    f"SQLState: {sql_state})"
                )
                logger.error(f"Tool: handle_graph_bfsLevels: {error_msg}")
                return create_response(
                    {"error": error_msg},
                    {
                        "tool_name":       tool_name if tool_name else "graph_bfsLevels",
                        "root_node_list":  root_node_list,
                        "status":          "error",
                        "rtn_code":        rtn_code,
                        "sql_code":        sql_code,
                        "sql_state":       sql_state
                    }
                )

            # ------------------------------------------------------------------
            # Fetch Result Set 1: BFS node results
            # One row per reachable node (plus root nodes themselves)
            # ------------------------------------------------------------------
            if not cur.nextset():
                logger.warning(
                    "Tool: handle_graph_bfsLevels: "
                    "No result set returned from graph_bfsLevels"
                )
                nodes_json = []
            else:
                nodes_desc = cur.description
                nodes_raw = cur.fetchall()
                nodes_json = rows_to_json(nodes_desc, nodes_raw)

                logger.debug(
                    f"Tool: handle_graph_bfsLevels: "
                    f"Result set: {len(nodes_json)} nodes returned"
                )

            # ------------------------------------------------------------------
            # Derive summary statistics and surface cycle candidates
            # _extract_cycle_candidates is called once here and the result
            # is passed into _create_bfs_summary so the node list is only
            # iterated once for cycle detection rather than twice.
            # ------------------------------------------------------------------
            cycle_cands = _extract_cycle_candidates(nodes_json)
            summary     = _create_bfs_summary(nodes_json, cycle_cands)

            logger.debug(
                f"Tool: handle_graph_bfsLevels: "
                f"Summary: {summary}, cycle_candidates={len(cycle_cands)}"
            )

            # ------------------------------------------------------------------
            # Assemble response
            # ------------------------------------------------------------------
            response_data = {
                "nodes":            nodes_json,
                "cycle_candidates": cycle_cands,
                "summary":          summary
            }

            metadata = {
                "tool_name":          tool_name if tool_name else "graph_bfsLevels",
                "root_node_list":     root_node_list,
                "max_depth_up":       max_depth_up,
                "max_depth_down":     max_depth_down,
                "exclude_objects":    exclude_objects,
                "include_containers": include_containers,
                "edge_repository":    edge_repository,
                "counts":             summary,
                "status":             "success",
                "rtn_code":           rtn_code,
                "message":            rtn_msg
            }

            logger.debug(
                f"Tool: handle_graph_bfsLevels: metadata: {metadata}"
            )
            return create_response(response_data, metadata)

    except Exception as e:
        logger.error(
            f"Tool: handle_graph_bfsLevels: Error: {e}", exc_info=True
        )
        return create_response(
            {"error": str(e)},
            {
                "tool_name":      tool_name if tool_name else "graph_bfsLevels",
                "root_node_list": root_node_list,
                "status":         "error"
            }
        )


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _bfs_safe_int(value) -> int | None:
    """
    Safely convert a value to int, returning None if conversion fails
    or value is None. Used for level columns which may be NULL from
    Teradata when a node is unreachable in one direction.

    Arguments:
      value - Any value from a Teradata result row

    Returns:
      int or None
    """
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _create_bfs_summary(nodes: list, cycle_candidates: list) -> dict:
    """
    Create summary statistics from the BFS node result set.

    cycle_candidates is passed in from the caller rather than being
    computed internally — _extract_cycle_candidates is called once in
    the handler and the result is shared here and in response_data,
    avoiding a redundant second pass over the node list.

    Arguments:
      nodes            - List of node dictionaries from rows_to_json
      cycle_candidates - Pre-computed list from _extract_cycle_candidates

    Returns:
      Dictionary with counts by direction and depth extremes
    """
    root_nodes      = [n for n in nodes if n.get('is_root')    == 'Y']
    upstream_nodes  = [n for n in nodes if n.get('direction')  == 'U']
    downstream_nodes = [n for n in nodes if n.get('direction') == 'D']
    both_nodes      = [n for n in nodes if n.get('direction')  == 'BOTH']
    cycle_cands     = cycle_candidates

    # Deepest upstream level (most negative — largest absolute value)
    up_levels = [
        abs(_bfs_safe_int(n.get('upstream_level')) or 0)
        for n in nodes
        if _bfs_safe_int(n.get('upstream_level')) is not None
    ]

    # Deepest downstream level (most positive)
    down_levels = [
        _bfs_safe_int(n.get('downstream_level')) or 0
        for n in nodes
        if _bfs_safe_int(n.get('downstream_level')) is not None
    ]

    # Nearest root grouping — how many nodes per root
    root_groups: dict[str, int] = {}
    for n in nodes:
        nearest = n.get('nearest_root')
        if nearest:
            root_groups[nearest] = root_groups.get(nearest, 0) + 1

    # Object kind breakdown
    kind_counts: dict[str, int] = {}
    for n in nodes:
        kind = n.get('object_kind') or 'Unknown'
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    return {
        "total_nodes":           len(nodes),
        "root_nodes":            len(root_nodes),
        "upstream_only":         len(upstream_nodes),
        "downstream_only":       len(downstream_nodes),
        "both_directions":       len(both_nodes),
        "cycle_candidates":      len(cycle_cands),
        "max_upstream_depth":    max(up_levels,   default=0),
        "max_downstream_depth":  max(down_levels, default=0),
        "nodes_per_nearest_root": root_groups,
        "object_kind_counts":    kind_counts
    }


def _extract_cycle_candidates(nodes: list) -> list:
    """
    Extract nodes that are reachable in both directions with unequal
    absolute upstream and downstream levels.

    A node with direction='BOTH' and abs(upstream_level) != downstream_level
    is a cycle candidate — the asymmetry indicates a back-edge in the graph,
    which is the hallmark of a circular reference when traversing the ODEX
    dependency graph.

    Nodes with direction='BOTH' and equal absolute levels are shared
    dependencies (reachable in both directions at the same hop count)
    and are included in the list with a cycle_likely flag of False
    for completeness.

    Arguments:
      nodes - List of node dictionaries from rows_to_json

    Returns:
      List of cycle candidate node dictionaries enriched with:
        cycle_likely     - True if abs(upstream_level) != downstream_level
        upstream_abs     - Absolute value of upstream_level for easy comparison
    """
    candidates = []

    for n in nodes:
        if n.get('direction') != 'BOTH':
            continue

        up_level = _bfs_safe_int(n.get('upstream_level'))
        down_level = _bfs_safe_int(n.get('downstream_level'))

        if up_level is None or down_level is None:
            continue

        up_abs = abs(up_level)
        cycle_likely = up_abs != down_level

        candidates.append({
            **n,
            "upstream_abs":  up_abs,
            "cycle_likely":  cycle_likely
        })

    # Sort: most likely cycles first (asymmetric), then by node name
    candidates.sort(
        key=lambda x: (not x['cycle_likely'], x.get('node', ''))
    )

    return candidates


# ------------------------------------------------------------------
# Tool registration descriptor
#
# Register this in your MCP server tools list alongside the other
# GRAPH_*_TOOL descriptors in graph_tools.py.
# ------------------------------------------------------------------
GRAPH_BFS_LEVELS_TOOL = {
    "name": "graph_bfsLevels",
    "handler": handle_graph_bfsLevels,
    "description": (
        "Compute BFS shortest-path hop distances from one or more root nodes "
        "in the ODEX dependency graph. Returns one row per reachable node with "
        "signed upstream_level (negative integer), downstream_level (positive "
        "integer), nearest_root (which of the input root nodes this object is "
        "closest to), direction (ROOT/U/D/BOTH), and is_root flag. "
        ""
        "USE THIS TOOL — not graph_queryDependenciesAgent — when asked to: "
        "sequence objects for deployment or migration (ORDER BY upstream_level "
        "gives correct deployment order); group objects into migration waves "
        "(nearest_root groups each object under its closest root table); find "
        "which migration root table each object belongs to across a multi-root "
        "scope; count objects within N hops of a change for blast-radius sizing; "
        "identify cycle members by depth (direction=BOTH nodes with unequal "
        "absolute upstream/downstream levels are cycle candidates, complementing "
        "graph_detectCycles); or answer how far any object is from the migration "
        "root tables. "
        ""
        "Do NOT use this tool for general lineage tracing, impact path analysis, "
        "or questions about which specific objects depend on which — use "
        "graph_queryDependenciesAgent for those. graph_bfsLevels returns "
        "distances and wave groupings, not dependency paths or edge detail. "
        ""
        "IMPORTANT: root_node_list accepts exact fully-qualified names only "
        "(no wildcards). Use graph_findRootObjects or graph_queryDependenciesAgent "
        "first to identify seed object names if needed."
    ),
    "parameters": {
        "root_node_list": {
            "type": "string",
            "description": (
                "CSV of exact fully-qualified root node names. No wildcards. "
                "Single: 'MyDB.MyTable'. "
                "Multiple: 'MyDB.TableA,MyDB.TableB,MyDB.TableC'."
            ),
            "required": True
        },
        "max_depth_up": {
            "type": "integer",
            "description": (
                "Maximum upstream hops to traverse. "
                "0 = skip upstream entirely. Default: 10."
            ),
            "default": 10
        },
        "max_depth_down": {
            "type": "integer",
            "description": (
                "Maximum downstream hops to traverse. "
                "0 = skip downstream entirely. Default: 10."
            ),
            "default": 10
        },
        "exclude_objects": {
            "type": "string",
            "description": (
                "CSV of FQ object name LIKE patterns to exclude from traversal. "
                "Matched against both Src and Tgt sides of every edge. "
                "Example: 'DFJ%,C_D02%,%.temp_%'. Default: '' (no exclusions)."
            ),
            "default": ""
        },
        "include_containers": {
            "type": "string",
            "description": (
                "CSV of container name LIKE patterns to include. "
                "When supplied, only edges where both Src and Tgt containers "
                "match at least one pattern are traversed. "
                "Example: 'DEV01_StGeo%,MF_STGEO%,TABLEAU%,POWERBI%'. "
                "Default: '' (all containers)."
            ),
            "default": ""
        },
        "edge_repository": {
            "type": "string",
            "description": (
                "ODEX repository view containing dependency edges. "
                "Default: 'DEV_01_ODEX_STD_0_V.ODEXRepository'."
            ),
            "default": "DEV_01_ODEX_STD_0_V.ODEXRepository"
        }
    }
}
