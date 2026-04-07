"""
graph_findRootObjects.py — Root object discovery tool.

Provides handle_graph_findRootObjects and GRAPH_FIND_ROOT_OBJECTS_TOOL.
Queries the edge repository directly (no SP) to find objects with no upstream
dependencies — the ideal seed points for downstream impact analysis.

Author:  Paul Dancer — Teradata Global Field Tech
"""

import logging
import time
from teradatasql import TeradataConnection
from teradata_mcp_server.tools.utils import create_response, rows_to_json

logger = logging.getLogger("teradata_mcp_server")


def handle_graph_findRootObjects(
    conn: TeradataConnection,
    container_pattern: str,
    exclude_objects: str = '',
    edge_repository: str = '',
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

      edge_repository   - str: Edge repository table/view conforming to the
                          Required parameter — no default.

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
      - Queries the edge repository to find all objects in specified containers
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


# ------------------------------------------------------------------
# Tool registration descriptor
# ------------------------------------------------------------------
GRAPH_FIND_ROOT_OBJECTS_TOOL = {
    "name": "graph_findRootObjects",
    "handler": handle_graph_findRootObjects,
    "description": (
        "Find root objects — objects with no upstream dependencies — in the "
        "specified containers. Root objects are foundational data sources and "
        "ideal starting points for downstream impact analysis or migration wave "
        "planning. Results are ordered by downstream dependent count descending. "
        "Use graph_bfsLevels after this tool to compute hop distances from the "
        "identified root objects. "
        "Requires an edge repository conforming to the Graph Edge Contract. "
        "If you don't have one yet, call graph_edgeContractDDL first to "
        "generate the CREATE TABLE or CREATE VIEW DDL."
    ),
    "parameters": {
        "container_pattern": {
            "type": "string",
            "description": (
                "CSV LIKE patterns for databases/schemas to search. "
                "Supports wildcards: \'%WBC%\' or \'%WBC%,%StGeo%\'."
            ),
            "required": True
        },
        "exclude_objects": {
            "type": "string",
            "description": (
                "CSV of FQ object name LIKE patterns to exclude. "
                "Example: \'PRD_%,%.temp_%\'. Default: \'\'."
            ),
            "default": ""
        },
        "edge_repository": {
            "type": "string",
            "description": (
                "Edge repository table or view conforming to the Graph Edge Contract. "
                "Call graph_edgeContractDDL to generate one if needed. "
                "Required parameter — no default."
            ),
            "required": True
        },
        "object_types": {
            "type": "string",
            "description": (
                "CSV of object type codes to include. "
                "Example: \'Table\' or \'Table,View\'. Default: \'\'  (all types)."
            ),
            "default": ""
        },
        "return_format": {
            "type": "string",
            "description": "Output format: \'detailed\' (default) or \'summary\'.",
            "default": "detailed"
        }
    }
}
