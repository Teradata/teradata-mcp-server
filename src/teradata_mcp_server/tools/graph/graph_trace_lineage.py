"""
graph_traceLineage.py — Dependency lineage analysis tool.

Provides handle_graph_traceLineage and GRAPH_TRACE_LINEAGE_TOOL.

Hybrid implementation — no stored procedure required.

Design:
  Python constructs and executes parameterised Teradata recursive CTEs as plain
  SELECT statements.  The recursive traversal runs entirely in Teradata spool
  (server-side), so only the reachable subgraph crosses the network — not the
  full edge table.  Python owns all orchestration, filtering, response assembly,
  and format selection.

  This approach satisfies two competing constraints simultaneously:
    1. No stored procedure — no Teradata DDL, no REPLACE PROCEDURE privilege,
       no server-side objects to deploy or version.
    2. No full-table transfer at scale — a graph with 100 000 edges is queried
       with only the reachable subgraph returned per invocation.

Recursive CTE direction convention (matches Edge Repository / graph_bfsLevels):
  Edge Repository row:  Src is REFERENCED BY Tgt.
    => Src is the DEPENDENCY   (upstream   of Tgt).
    => Tgt is the DEPENDENT    (downstream of Src).

  Upstream CTE   — "what does my seed depend on?":
    Anchor on seed as Tgt; recurse by following Src side outward.

  Downstream CTE — "what depends on my seed?":
    Anchor on seed as Src; recurse by following Tgt side outward.

Author:  Paul Dancer — Teradata Global Field Tech
"""

import logging

from teradatasql import TeradataConnection

from teradata_mcp_server.tools.graph._graph_utils import parse_csv_patterns
from teradata_mcp_server.tools.utils import create_response, rows_to_json

logger = logging.getLogger("teradata_mcp_server")


# ---------------------------------------------------------------------------
# Internal helpers — pattern parsing
# ---------------------------------------------------------------------------
# parse_csv_patterns is imported from _graph_utils.
# _build_or_like is kept local — it covers both Src and Tgt columns
# simultaneously, which is a different pattern from build_like_or.


def _build_or_like(patterns: list[str], src_col: str, tgt_col: str) -> str:
    """
    Build an OR-joined pair of LIKE clauses covering both Src and Tgt columns.

    Used to scope the recursive CTE anchor and recursion steps so that only
    edges touching the requested containers participate.

    Arguments:
      patterns - List of LIKE pattern strings for container names
      src_col  - SQL column name for the source container
      tgt_col  - SQL column name for the target container

    Returns:
      SQL fragment, e.g.
        "({src_col} LIKE 'A%' OR {tgt_col} LIKE 'A%'
          OR {src_col} LIKE 'B%' OR {tgt_col} LIKE 'B%')"
      Returns empty string if patterns is empty (no filtering).
    """
    if not patterns:
        return ""
    clauses = []
    for p in patterns:
        clauses.append(f"{src_col} LIKE '{p}'")
        clauses.append(f"{tgt_col} LIKE '{p}'")
    return "AND (" + " OR ".join(clauses) + ")"


def _build_excl_fragment(patterns: list[str], db_col: str, obj_col: str) -> str:
    """
    Build a NOT (...) exclusion fragment for object-level filtering.

    A pattern containing a dot is treated as a fully-qualified DB.Object
    pattern; a plain pattern is matched against the container/DB column only.

    Arguments:
      patterns - List of exclusion LIKE patterns
      db_col   - SQL column holding the database/schema name
      obj_col  - SQL column holding the object name

    Returns:
      SQL fragment beginning with "AND NOT (...)" or empty string
    """
    if not patterns:
        return ""

    conditions = []
    for p in patterns:
        if "." in p:
            db_part, obj_part = p.split(".", 1)
            conditions.append(f"({db_col} LIKE '{db_part}' AND {obj_col} LIKE '{obj_part}')")
        else:
            conditions.append(f"{db_col} LIKE '{p}'")

    return "AND NOT (" + " OR ".join(conditions) + ")"


# ---------------------------------------------------------------------------
# CTE builders
# ---------------------------------------------------------------------------


def _build_upstream_cte(
    seed_pattern: str,
    max_depth: int,
    edge_table: str,
    incl_fragment: str,
    excl_fragment: str,
) -> str:
    """
    Build a Teradata recursive CTE that traverses upstream from a seed pattern.

    "Upstream" means: what does my seed DEPEND ON?  In Edge Repository terms,
    when a row has Tgt matching the seed, Src is the upstream dependency.
    The anchor selects rows where Tgt matches the seed; recursion follows
    the Src side outward (each discovered Src becomes the next Tgt to search).

    Arguments:
      seed_pattern  - LIKE pattern for the seed object (DB.Object format)
      max_depth     - Maximum hop count to traverse
      edge_table    - Fully-qualified edge repository view/table name
      incl_fragment - SQL fragment for container inclusion ("AND (...)") or ''
      excl_fragment - SQL fragment for object exclusion ("AND NOT (...)") or ''

    Returns:
      Complete WITH RECURSIVE ... SELECT statement as a string
    """
    return f"""
WITH RECURSIVE UpstreamBFS
    (
     Src_DB
    ,Src_Obj
    ,Src_Kind
    ,Tgt_DB
    ,Tgt_Obj
    ,Tgt_Kind
    ,Depth
    ,Path_Str
    ) AS
(
    -- ----------------------------------------------------------------
    -- Anchor: edges where the target matches the seed pattern
    -- ----------------------------------------------------------------
    SELECT
         TRIM(e.Src_Container_Name)
        ,TRIM(e.Src_Object_Name)
        ,COALESCE(TRIM(e.Src_Kind), 'Unknown')
        ,TRIM(e.Tgt_Container_Name)
        ,TRIM(e.Tgt_Object_Name)
        ,COALESCE(TRIM(e.Tgt_Kind), 'Unknown')
        ,CAST(1 AS INTEGER)
        ,CAST(
             TRIM(e.Src_Container_Name) || '.' || TRIM(e.Src_Object_Name)
             || ' <- '
             || TRIM(e.Tgt_Container_Name) || '.' || TRIM(e.Tgt_Object_Name)
         AS VARCHAR(8000)
         )
    FROM  {edge_table} e
    WHERE (TRIM(e.Tgt_Container_Name) || '.' || TRIM(e.Tgt_Object_Name))
              LIKE '{seed_pattern}'
      {incl_fragment}
      {excl_fragment}

    UNION ALL

    -- ----------------------------------------------------------------
    -- Recursion: follow the Src side of each already-discovered edge
    -- ----------------------------------------------------------------
    SELECT
         TRIM(e.Src_Container_Name)
        ,TRIM(e.Src_Object_Name)
        ,COALESCE(TRIM(e.Src_Kind), 'Unknown')
        ,TRIM(e.Tgt_Container_Name)
        ,TRIM(e.Tgt_Object_Name)
        ,COALESCE(TRIM(e.Tgt_Kind), 'Unknown')
        ,b.Depth + 1
        ,CAST(
             TRIM(e.Src_Container_Name) || '.' || TRIM(e.Src_Object_Name)
             || ' <- '
             || b.Path_Str
         AS VARCHAR(8000)
         )
    FROM  {edge_table} e
    INNER JOIN UpstreamBFS b
           ON  TRIM(e.Tgt_Container_Name) = b.Src_DB
           AND TRIM(e.Tgt_Object_Name)    = b.Src_Obj
    WHERE b.Depth < {max_depth}
      {incl_fragment}
      {excl_fragment}
)
SELECT
     Src_DB                                     AS DependentObjectDBName
    ,Src_Obj                                    AS DependentObjectName
    ,Src_DB || '.' || Src_Obj                   AS FQDependentObjectName
    ,Tgt_DB                                     AS ReferencedObjectDBName
    ,Tgt_Obj                                    AS ReferencedObjectName
    ,Tgt_DB || '.' || Tgt_Obj                   AS FQReferencedObjectName
    ,Src_Kind                                   AS Src_Kind
    ,Tgt_Kind                                   AS Tgt_Kind
    ,CAST(Depth * -1 AS INTEGER)                AS Depth
    ,Path_Str                                   AS DependencyPath
FROM  UpstreamBFS
ORDER BY Depth ASC, FQDependentObjectName
"""


def _build_downstream_cte(
    seed_pattern: str,
    max_depth: int,
    edge_table: str,
    incl_fragment: str,
    excl_fragment: str,
) -> str:
    """
    Build a Teradata recursive CTE that traverses downstream from a seed pattern.

    "Downstream" means: what DEPENDS ON my seed?  In Edge Repository terms,
    when a row has Src matching the seed, Tgt is the downstream dependent.
    The anchor selects rows where Src matches the seed; recursion follows
    the Tgt side outward (each discovered Tgt becomes the next Src to search).

    Arguments:
      seed_pattern  - LIKE pattern for the seed object (DB.Object format)
      max_depth     - Maximum hop count to traverse
      edge_table    - Fully-qualified edge repository view/table name
      incl_fragment - SQL fragment for container inclusion ("AND (...)") or ''
      excl_fragment - SQL fragment for object exclusion ("AND NOT (...)") or ''

    Returns:
      Complete WITH RECURSIVE ... SELECT statement as a string
    """
    return f"""
WITH RECURSIVE DownstreamBFS
    (
     Src_DB
    ,Src_Obj
    ,Src_Kind
    ,Tgt_DB
    ,Tgt_Obj
    ,Tgt_Kind
    ,Depth
    ,Path_Str
    ) AS
(
    -- ----------------------------------------------------------------
    -- Anchor: edges where the source matches the seed pattern
    -- ----------------------------------------------------------------
    SELECT
         TRIM(e.Src_Container_Name)
        ,TRIM(e.Src_Object_Name)
        ,COALESCE(TRIM(e.Src_Kind), 'Unknown')
        ,TRIM(e.Tgt_Container_Name)
        ,TRIM(e.Tgt_Object_Name)
        ,COALESCE(TRIM(e.Tgt_Kind), 'Unknown')
        ,CAST(1 AS INTEGER)
        ,CAST(
             TRIM(e.Src_Container_Name) || '.' || TRIM(e.Src_Object_Name)
             || ' -> '
             || TRIM(e.Tgt_Container_Name) || '.' || TRIM(e.Tgt_Object_Name)
         AS VARCHAR(8000)
         )
    FROM  {edge_table} e
    WHERE (TRIM(e.Src_Container_Name) || '.' || TRIM(e.Src_Object_Name))
              LIKE '{seed_pattern}'
      {incl_fragment}
      {excl_fragment}

    UNION ALL

    -- ----------------------------------------------------------------
    -- Recursion: follow the Tgt side of each already-discovered edge
    -- ----------------------------------------------------------------
    SELECT
         TRIM(e.Src_Container_Name)
        ,TRIM(e.Src_Object_Name)
        ,COALESCE(TRIM(e.Src_Kind), 'Unknown')
        ,TRIM(e.Tgt_Container_Name)
        ,TRIM(e.Tgt_Object_Name)
        ,COALESCE(TRIM(e.Tgt_Kind), 'Unknown')
        ,b.Depth + 1
        ,CAST(
             b.Path_Str
             || ' -> '
             || TRIM(e.Tgt_Container_Name) || '.' || TRIM(e.Tgt_Object_Name)
         AS VARCHAR(8000)
         )
    FROM  {edge_table} e
    INNER JOIN DownstreamBFS b
           ON  TRIM(e.Src_Container_Name) = b.Tgt_DB
           AND TRIM(e.Src_Object_Name)    = b.Tgt_Obj
    WHERE b.Depth < {max_depth}
      {incl_fragment}
      {excl_fragment}
)
SELECT
     Tgt_DB                                     AS DependentObjectDBName
    ,Tgt_Obj                                    AS DependentObjectName
    ,Tgt_DB || '.' || Tgt_Obj                   AS FQDependentObjectName
    ,Src_DB                                     AS ReferencedObjectDBName
    ,Src_Obj                                    AS ReferencedObjectName
    ,Src_DB || '.' || Src_Obj                   AS FQReferencedObjectName
    ,Src_Kind                                   AS Src_Kind
    ,Tgt_Kind                                   AS Tgt_Kind
    ,CAST(Depth AS INTEGER)                     AS Depth
    ,Path_Str                                   AS DependencyPath
FROM  DownstreamBFS
ORDER BY Depth ASC, FQDependentObjectName
"""


# ---------------------------------------------------------------------------
# Node / summary helpers — identical contract to the SP-based version
# ---------------------------------------------------------------------------


def _safe_int(value) -> int:
    """
    Safely convert a value to int, returning 0 on failure.

    Arguments:
      value - Any value (may be Teradata BYTEINT returned as string)

    Returns:
      int
    """
    try:
        return int(value) if value is not None else 0
    except (ValueError, TypeError):
        return 0


def _derive_nodes_from_edges(
    edges_up: list[dict],
    edges_down: list[dict],
) -> list[dict]:
    """
    Derive unique nodes from edge lists.

    Deduplicates by FQDependentObjectName, preferring the upstream record when
    a node appears in both directions.

    Arguments:
      edges_up   - List of upstream edge dicts
      edges_down - List of downstream edge dicts

    Returns:
      List of unique node dicts
    """
    nodes: dict[str, dict] = {}

    for edge in edges_up:
        fq = edge.get("FQDependentObjectName")
        if fq and fq not in nodes:
            nodes[fq] = {
                "FQDependentObjectName": fq,
                "DependentObjectDBName": edge.get("DependentObjectDBName"),
                "DependentObjectName": edge.get("DependentObjectName"),
                "Direction": "Upstream",
                "Depth": _safe_int(edge.get("Depth", 0)),
                "ObjectType": edge.get("Src_Kind") or edge.get("Tgt_Kind"),
            }

    for edge in edges_down:
        fq = edge.get("FQDependentObjectName")
        if fq and fq not in nodes:
            nodes[fq] = {
                "FQDependentObjectName": fq,
                "DependentObjectDBName": edge.get("DependentObjectDBName"),
                "DependentObjectName": edge.get("DependentObjectName"),
                "Direction": "Downstream",
                "Depth": _safe_int(edge.get("Depth", 0)),
                "ObjectType": edge.get("Src_Kind") or edge.get("Tgt_Kind"),
            }

    return list(nodes.values())


def _create_summary_stats(
    nodes: list[dict],
    edges_up: list[dict],
    edges_down: list[dict],
) -> dict:
    """
    Create summary statistics from dependency data.

    Arguments:
      nodes      - List of node dicts
      edges_up   - List of upstream edge dicts
      edges_down - List of downstream edge dicts

    Returns:
      Dictionary of summary statistics
    """
    upstream_nodes = [n for n in nodes if n.get("Direction") == "Upstream"]
    downstream_nodes = [n for n in nodes if n.get("Direction") == "Downstream"]

    type_counts: dict[str, int] = {}
    for node in nodes:
        kind = node.get("ObjectType", "Unknown") or "Unknown"
        type_counts[kind] = type_counts.get(kind, 0) + 1

    return {
        "total_nodes": len(nodes),
        "upstream_nodes": len(upstream_nodes),
        "downstream_nodes": len(downstream_nodes),
        "total_edges": len(edges_up) + len(edges_down),
        "upstream_edges": len(edges_up),
        "downstream_edges": len(edges_down),
        "max_depth_upstream": max((abs(_safe_int(n.get("Depth", 0))) for n in upstream_nodes), default=0),
        "max_depth_downstream": max((_safe_int(n.get("Depth", 0)) for n in downstream_nodes), default=0),
        "object_type_counts": type_counts,
    }


def _format_summary(
    nodes: list[dict],
    edges_up: list[dict],
    edges_down: list[dict],
    object_name: str,
) -> dict:
    """
    Format a concise summary of dependency analysis.

    Arguments:
      nodes       - List of node dicts
      edges_up    - List of upstream edge dicts
      edges_down  - List of downstream edge dicts
      object_name - Object name pattern(s) analysed (may be CSV)

    Returns:
      Dictionary with summary_text, statistics, upstream_objects, downstream_objects
    """
    stats = _create_summary_stats(nodes, edges_up, edges_down)
    upstream_nodes = [n for n in nodes if n.get("Direction") == "Upstream"]
    downstream_nodes = [n for n in nodes if n.get("Direction") == "Downstream"]

    summary_text = f"""
DEPENDENCY ANALYSIS SUMMARY
{"=" * 60}

Object Pattern(s): {object_name}

OVERVIEW
  Total Nodes:               {stats["total_nodes"]}
  Total Edges:               {stats["total_edges"]}

UPSTREAM (What These Objects Depend On)
  Dependencies Found:        {stats["upstream_nodes"]}
  Edges:                     {stats["upstream_edges"]}
  Max Depth Reached:         {stats["max_depth_upstream"]}

DOWNSTREAM (What Depends On These Objects)
  Dependents Found:          {stats["downstream_nodes"]}
  Edges:                     {stats["downstream_edges"]}
  Max Depth Reached:         {stats["max_depth_downstream"]}
"""

    if stats["object_type_counts"]:
        summary_text += "\nBY OBJECT TYPE\n"
        for obj_type, count in sorted(stats["object_type_counts"].items(), key=lambda x: x[1], reverse=True):
            summary_text += f"  {obj_type:20s} {count:3d}\n"

    return {
        "summary_text": summary_text,
        "statistics": stats,
        "upstream_objects": [n["FQDependentObjectName"] for n in upstream_nodes],
        "downstream_objects": [n["FQDependentObjectName"] for n in downstream_nodes],
    }


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------


def handle_graph_traceLineage(
    conn: TeradataConnection,
    object_name: str,
    max_depth_up: int = 3,
    max_depth_down: int = 3,
    exclude_objects: str = "",
    include_containers: str = "",
    edge_repository: str = "",
    return_format: str = "detailed",
    tool_name: str | None = None,
    *args,
    **kwargs,
):
    """
    Analyse object dependencies in Teradata. Supports wildcards (%) and CSV patterns.

    Hybrid implementation — no stored procedure required.  Python constructs
    Teradata recursive CTEs that execute entirely server-side.  Only the
    reachable subgraph crosses the network — not the full edge table.

    Examples: 'DB.Table' (single), '%WBC%.%' (wildcard), 'DB.T1,DB.T2' (CSV)

    Finds upstream dependencies (what the object depends on) and downstream
    dependents (what depends on the object).  Returns nodes and edges
    representing the dependency subgraph.

    When multiple patterns are provided via CSV, one upstream CTE and one
    downstream CTE is executed per pattern.  Results are merged and
    deduplicated by Python before assembly.

    Use this for:
      - Impact analysis: "What breaks if I change or drop this object?"
      - Lineage tracing: "Where does this data come from?"
      - Dependency discovery: "What does this object use?"
      - Pre-deployment validation: checking impacts before making changes

    Arguments:
      object_name        - str: Object name pattern(s).
                           Supports wildcards (%) and CSV format.
                           STRING type — not an array.

                           Single:   'DEV01_StGeo_STD_T.mortgage_account'
                           Wildcard: '%WBC%.%'
                           Multiple: '%WBC%.%,%StGeo%.%'

      max_depth_up       - int: Maximum levels to traverse upstream (0-10).
                           0 = no upstream analysis.  Default: 3

      max_depth_down     - int: Maximum levels to traverse downstream (0-10).
                           0 = no downstream analysis.  Default: 3

      exclude_objects    - str: CSV LIKE patterns to exclude.
                           Matches against DB.Object format.
                           Example: 'PRD_%,%.temp_%'
                           Default: '' (no exclusions)

      include_containers - str: CSV of container LIKE patterns to include
                           (whitelist).  Empty = all containers.
                           Default: '' (all containers)

      edge_repository    - str: Edge repository view/table conforming to the
                           Required parameter — no default.

      return_format      - str: 'detailed' (default), 'summary', or 'edges_only'

    Returns:
      ResponseType: formatted response with dependency analysis results.

      detailed response structure:
        {
          "nodes":           [...],  // Unique nodes (deduplicated)
          "upstream_edges":  [...],  // One row per upstream edge
          "downstream_edges":[...],  // One row per downstream edge
          "summary":         {...}   // Aggregate statistics
        }

      Edge row fields:
        DependentObjectDBName, DependentObjectName, FQDependentObjectName,
        ReferencedObjectDBName, ReferencedObjectName, FQReferencedObjectName,
        Src_Kind, Tgt_Kind, Depth, DependencyPath
    """
    logger.debug(
        "Tool: handle_graph_traceLineage: Args: "
        "object_name=%s, max_depth_up=%s, max_depth_down=%s, "
        "exclude_objects=%s, include_containers=%s, "
        "edge_repository=%s, return_format=%s",
        object_name,
        max_depth_up,
        max_depth_down,
        exclude_objects,
        include_containers,
        edge_repository,
        return_format,
    )

    # -----------------------------------------------------------------------
    # Validate and clamp depth parameters
    # -----------------------------------------------------------------------
    max_depth_up = max(0, min(10, int(max_depth_up)))
    max_depth_down = max(0, min(10, int(max_depth_down)))

    # -----------------------------------------------------------------------
    # Parse pattern inputs
    # -----------------------------------------------------------------------
    seed_patterns = parse_csv_patterns(object_name)
    excl_patterns = parse_csv_patterns(exclude_objects)
    incl_containers = parse_csv_patterns(include_containers)

    if not seed_patterns:
        return create_response(
            {"error": "object_name must not be empty"},
            {
                "tool_name": tool_name or "graph_traceLineage",
                "object_name": object_name,
                "status": "error",
            },
        )

    if not edge_repository:
        return create_response(
            {"error": "edge_repository is required. Call graph_edgeContractDDL to generate one."},
            {
                "tool_name": tool_name or "graph_traceLineage",
                "object_name": object_name,
                "status": "error",
            },
        )

    try:
        # -----------------------------------------------------------------------
        # Build shared SQL fragments (same for every seed pattern)
        # -----------------------------------------------------------------------
        incl_fragment = _build_or_like(incl_containers, "e.Src_Container_Name", "e.Tgt_Container_Name")
        excl_fragment = _build_excl_fragment(excl_patterns, "e.Src_Container_Name", "e.Src_Object_Name")

        all_edges_up: list[dict] = []
        all_edges_down: list[dict] = []

        with conn.cursor() as cur:
            for pattern in seed_patterns:
                # ---------------------------------------------------------------
                # Upstream traversal (skip if max_depth_up == 0)
                # ---------------------------------------------------------------
                if max_depth_up > 0:
                    up_sql = _build_upstream_cte(
                        seed_pattern=pattern,
                        max_depth=max_depth_up,
                        edge_table=edge_repository,
                        incl_fragment=incl_fragment,
                        excl_fragment=excl_fragment,
                    )
                    logger.debug("Tool: handle_graph_traceLineage: Upstream CTE for pattern '%s':\n%s", pattern, up_sql)
                    cur.execute(up_sql)
                    batch = rows_to_json(cur.description, cur.fetchall())
                    all_edges_up.extend(batch)
                    logger.debug(
                        "Tool: handle_graph_traceLineage: Pattern '%s' upstream: %d edges", pattern, len(batch)
                    )

                # ---------------------------------------------------------------
                # Downstream traversal (skip if max_depth_down == 0)
                # ---------------------------------------------------------------
                if max_depth_down > 0:
                    down_sql = _build_downstream_cte(
                        seed_pattern=pattern,
                        max_depth=max_depth_down,
                        edge_table=edge_repository,
                        incl_fragment=incl_fragment,
                        excl_fragment=excl_fragment,
                    )
                    logger.debug(
                        "Tool: handle_graph_traceLineage: Downstream CTE for pattern '%s':\n%s", pattern, down_sql
                    )
                    cur.execute(down_sql)
                    batch = rows_to_json(cur.description, cur.fetchall())
                    all_edges_down.extend(batch)
                    logger.debug(
                        "Tool: handle_graph_traceLineage: Pattern '%s' downstream: %d edges", pattern, len(batch)
                    )

        # -----------------------------------------------------------------------
        # Deduplicate edges by (FQDependentObjectName, FQReferencedObjectName)
        # -----------------------------------------------------------------------
        def _dedup(edges: list[dict]) -> list[dict]:
            """Remove duplicate edges, keeping the first occurrence."""
            seen: set[tuple] = set()
            out: list[dict] = []
            for e in edges:
                key = (
                    e.get("FQDependentObjectName"),
                    e.get("FQReferencedObjectName"),
                )
                if key not in seen:
                    seen.add(key)
                    out.append(e)
            return out

        edges_up = _dedup(all_edges_up)
        edges_down = _dedup(all_edges_down)

        # -----------------------------------------------------------------------
        # Derive nodes and assemble response
        # -----------------------------------------------------------------------
        nodes_data = _derive_nodes_from_edges(edges_up, edges_down)

        if return_format == "summary":
            formatted_data = _format_summary(nodes_data, edges_up, edges_down, object_name)
        elif return_format == "edges_only":
            formatted_data = {
                "upstream_edges": edges_up,
                "downstream_edges": edges_down,
            }
        else:  # detailed (default)
            formatted_data = {
                "nodes": nodes_data,
                "upstream_edges": edges_up,
                "downstream_edges": edges_down,
                "summary": _create_summary_stats(nodes_data, edges_up, edges_down),
            }

        metadata = {
            "tool_name": tool_name or "graph_traceLineage",
            "object_name": object_name,
            "max_depth_up": max_depth_up,
            "max_depth_down": max_depth_down,
            "edge_repository": edge_repository,
            "return_format": return_format,
            "counts": {
                "nodes": len(nodes_data),
                "upstream_edges": len(edges_up),
                "downstream_edges": len(edges_down),
            },
            "status": "success",
            "message": (
                f"Dependency analysis complete: "
                f"{len(nodes_data)} node(s), "
                f"{len(edges_up)} upstream edge(s), "
                f"{len(edges_down)} downstream edge(s)."
            ),
        }

        logger.debug("Tool: handle_graph_traceLineage: metadata: %s", metadata)
        return create_response(formatted_data, metadata)

    except Exception as e:
        logger.error("Tool: handle_graph_traceLineage: Error: %s", e, exc_info=True)
        return create_response(
            {"error": str(e)},
            {
                "tool_name": tool_name or "graph_traceLineage",
                "object_name": object_name,
                "status": "error",
            },
        )


# ---------------------------------------------------------------------------
# Tool registration descriptor
# ---------------------------------------------------------------------------
GRAPH_TRACE_LINEAGE_TOOL = {
    "name": "graph_traceLineage",
    "handler": handle_graph_traceLineage,
    "description": (
        "Analyse object dependencies in Teradata — finds upstream dependencies "
        "(what the object depends on) and downstream dependents (what depends "
        "on the object). Hybrid implementation: Python constructs Teradata "
        "recursive CTEs that execute entirely server-side, so only the reachable "
        "subgraph crosses the network. No stored procedure required. "
        "Supports wildcards (%) and CSV patterns for object_name. "
        "Use for impact analysis, lineage tracing, and pre-deployment validation. "
        "Do NOT use for migration wave sequencing — use graph_bfsLevels for that. "
        "Requires an edge repository conforming to the Graph Edge Contract. "
        "If you don't have one yet, call graph_edgeContractDDL first to "
        "generate the CREATE TABLE or CREATE VIEW DDL."
    ),
    "parameters": {
        "object_name": {
            "type": "string",
            "description": (
                "Object name pattern(s). Supports wildcards (%) and CSV. "
                "Single: 'DB.Table'. Wildcard: '%WBC%.%'. "
                "Multiple: '%WBC%.%,%StGeo%.%'."
            ),
            "required": True,
        },
        "max_depth_up": {
            "type": "integer",
            "description": "Maximum upstream levels to traverse (0-10). Default: 3.",
            "default": 3,
        },
        "max_depth_down": {
            "type": "integer",
            "description": "Maximum downstream levels to traverse (0-10). Default: 3.",
            "default": 3,
        },
        "exclude_objects": {
            "type": "string",
            "description": ("CSV of FQ object name LIKE patterns to exclude. Example: 'PRD_%,%.temp_%'. Default: ''."),
            "default": "",
        },
        "include_containers": {
            "type": "string",
            "description": ("CSV of container LIKE patterns to include (whitelist). Default: '' (all containers)."),
            "default": "",
        },
        "edge_repository": {
            "type": "string",
            "description": (
                "Edge repository table or view conforming to the Graph Edge Contract. "
                "Call graph_edgeContractDDL to generate one if needed. "
                "Required parameter — no default."
            ),
            "required": True,
        },
        "return_format": {
            "type": "string",
            "description": ("Output format: 'detailed' (default), 'summary', or 'edges_only'."),
            "default": "detailed",
        },
    },
}
