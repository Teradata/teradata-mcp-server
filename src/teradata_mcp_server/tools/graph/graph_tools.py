"""
Graph dependency analysis tools for Teradata MCP Server.

This module provides tools for analysing object dependencies using the
QueryDependenciesAgent stored procedure from the ODEX framework.
"""

import logging
from teradatasql import TeradataConnection
from teradata_mcp_server.tools.utils import create_response, rows_to_json

logger = logging.getLogger("teradata_mcp_server")


#------------------ Tool: Query Dependencies Agent ------------------#
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
                CALL DEV_01_ODEX_RPT_0_P.QueryDependenciesAgent(
                    ?,  -- i_ObjectPatternList (CSV string: 'pattern1,pattern2,pattern3')
                    ?,  -- i_MaxDepthUp
                    ?,  -- i_MaxDepthDown
                    ?,  -- i_ExclFQObjectNames (also CSV)
                    ?,  -- i_InclContainers (also CSV)
                    ?,  -- i_ObjectDependencyTable
                    'N', -- i_Output_ResultSet (we'll query volatile tables ourselves)
                    ?,  -- o_EdgesUpTableName (output)
                    ?,  -- o_EdgesDownTableName (output)
                    ?,  -- o_SQLCode (output)
                    ?,  -- o_SQLSTATE (output)
                    ?,  -- o_RtnCode (output)
                    ?   -- o_RtnMsg (output)
                )
            """
            
            # Parameters passed directly without modification
            # object_name is passed as a string, even if it contains commas (CSV format)
            params = [
                object_name,      # Passed AS-IS - procedure handles CSV parsing
                max_depth_up,
                max_depth_down,
                exclude_objects,  # Also supports CSV format
                include_containers,  # Also supports CSV format
                edge_repository,
                None,  # o_EdgesUpTableName
                None,  # o_EdgesDownTableName
                None,  # o_SQLCode
                None,  # o_SQLSTATE
                None,  # o_RtnCode
                None   # o_RtnMsg
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
                raise Exception("No output returned from QueryDependenciesAgent procedure")
            
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
                logger.error(f"Tool: handle_graph_queryDependenciesAgent: {error_msg}")
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
                cur.execute(f"SELECT * FROM {edges_up_table} ORDER BY Depth, FQDependentObjectName")
                edges_up_data = rows_to_json(cur.description, cur.fetchall())
            
            # Downstream edges
            edges_down_data = []
            if edges_down_table:
                cur.execute(f"SELECT * FROM {edges_down_table} ORDER BY Depth, FQDependentObjectName")
                edges_down_data = rows_to_json(cur.description, cur.fetchall())
            
            # Derive unique nodes from edges (matching procedure's logic)
            nodes_data = _derive_nodes_from_edges(edges_up_data, edges_down_data)
            
            # Format response based on requested format
            if return_format == 'summary':
                formatted_data = _format_summary(nodes_data, edges_up_data, edges_down_data, object_name)
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
            
            logger.debug(f"Tool: handle_graph_queryDependenciesAgent: metadata: {metadata}")
            return create_response(formatted_data, metadata)
            
    except Exception as e:
        logger.error(f"Tool: handle_graph_queryDependenciesAgent: Error: {e}", exc_info=True)
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
