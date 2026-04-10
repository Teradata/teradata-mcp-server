"""
graph_connectedComponents.py — Connected components analysis tool.

Provides handle_graph_connectedComponents and GRAPH_CONNECTED_COMPONENTS_TOOL.

Pure-Python implementation — no stored procedure required.

Algorithm overview:
  1. Fetch all edges within the container scope in a single SQL SELECT.
  2. Run Union-Find (path-compressed) to assign every node to a component.
  3. Compute per-component summaries and overall statistics in Python.
  4. Assemble the same three-structure response the SP returned:
       node_details        — one row per node with Component_Id
       component_summaries — one row per component with node count and list
       summary_stats       — single aggregate row

Edge direction convention (matches Edge Repository / graph_bfsLevels):
  Src_Object_Name is REFERENCED BY Tgt_Object_Name.
  For WCC purposes edge direction is ignored — two nodes are in the same
  component if there is any path (directed or undirected) between them.

Author:  Paul Dancer — Teradata Global Field Tech
"""

import logging
from collections import defaultdict
from teradatasql import TeradataConnection
from teradata_mcp_server.tools.utils import create_response
from teradata_mcp_server.tools.graph._graph_utils import (
    build_like_or,
    parse_csv_patterns,
)

logger = logging.getLogger("teradata_mcp_server")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
# parse_csv_patterns and build_like_or are imported from _graph_utils.


def _build_excl_clauses(patterns: list[str]) -> str:
    """
    Build a NOT (...) exclusion fragment for container/object patterns.

    A pattern containing a dot is treated as a fully-qualified DB.Object
    pattern; a plain pattern is matched against the container name only.

    Arguments:
      patterns - List of exclusion LIKE patterns

    Returns:
      SQL fragment beginning with "AND NOT (...)" or empty string
    """
    if not patterns:
        return ''

    conditions = []
    for p in patterns:
        if '.' in p:
            db_part, obj_part = p.split('.', 1)
            conditions.append(
                f"(Src_Container_Name LIKE '{db_part}'"
                f" AND Src_Object_Name LIKE '{obj_part}')"
            )
        else:
            conditions.append(f"Src_Container_Name LIKE '{p}'")

    return 'AND NOT (' + ' OR '.join(conditions) + ')'


# ---------------------------------------------------------------------------
# Union-Find
# ---------------------------------------------------------------------------

class _UnionFind:
    """
    Union-Find with path compression.

    Assigns every node to a canonical component representative.
    union() merges two components; find() returns the representative.
    """

    def __init__(self):
        self._parent: dict = {}

    def find(self, x) -> str:
        """Return canonical representative for x (with path compression)."""
        self._parent.setdefault(x, x)
        # -- Walk to root --
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        # -- Path compression (flatten all nodes to root) --
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a, b) -> None:
        """Merge the components containing a and b."""
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb

    def all_nodes(self) -> set:
        """Return the set of all nodes known to this Union-Find."""
        return set(self._parent.keys())

    def component_map(self) -> dict[str, str]:
        """Return {node: component_root} for all known nodes."""
        return {n: self.find(n) for n in self._parent}


# ---------------------------------------------------------------------------
# Response assembly helpers
# ---------------------------------------------------------------------------

def _build_node_details(
    component_map: dict[str, str],
    root_to_id: dict[str, int],
    node_kind: dict[str, str],
) -> list[dict]:
    """
    Build node_details — one row per node with its Component_Id.

    Arguments:
      component_map - {node_fq: component_root} from Union-Find
      root_to_id    - {component_root: integer_id} mapping
      node_kind     - {node_fq: object_kind} from the edge fetch

    Returns:
      List of node detail dicts
    """
    rows = []
    for node_fq, comp_root in sorted(component_map.items()):
        parts = node_fq.split('.', 1)
        db_name  = parts[0] if len(parts) > 1 else ''
        obj_name = parts[1] if len(parts) > 1 else parts[0]
        rows.append({
            "Node_FQ":        node_fq,
            "DatabaseName":   db_name,
            "ObjectName":     obj_name,
            "Component_Id":   root_to_id[comp_root],
            "Object_Kind":    node_kind.get(node_fq, 'Unknown'),
        })
    return rows


def _build_component_summaries(
    component_map: dict[str, str],
    root_to_id: dict[str, int],
) -> list[dict]:
    """
    Build component_summaries — one row per component.

    Arguments:
      component_map - {node_fq: component_root}
      root_to_id    - {component_root: integer_id}

    Returns:
      List of component summary dicts ordered by Component_Id
    """
    # Group nodes by component root
    comp_nodes: dict[str, list[str]] = defaultdict(list)
    for node_fq, comp_root in component_map.items():
        comp_nodes[comp_root].append(node_fq)

    rows = []
    for comp_root, nodes in comp_nodes.items():
        nodes_sorted = sorted(nodes)
        rows.append({
            "Component_Id":  root_to_id[comp_root],
            "Node_Count":    len(nodes_sorted),
            "Node_List":     ', '.join(nodes_sorted),
        })

    rows.sort(key=lambda r: r["Component_Id"])
    return rows


def _build_summary_stats(
    component_summaries: list[dict],
    edge_count: int,
) -> list[dict]:
    """
    Build summary_stats — single aggregate row.

    Arguments:
      component_summaries - List of component summary dicts
      edge_count          - Total edges loaded from the repository

    Returns:
      Single-element list
    """
    node_count = sum(c["Node_Count"] for c in component_summaries)
    comp_count = len(component_summaries)

    sizes = [c["Node_Count"] for c in component_summaries]
    largest  = max(sizes, default=0)
    smallest = min(sizes, default=0)

    singleton_count = sum(1 for s in sizes if s == 1)

    return [{
        "Component_Count":   comp_count,
        "Node_Count":        node_count,
        "Edge_Count":        edge_count,
        "Largest_Component": largest,
        "Smallest_Component": smallest,
        "Singleton_Count":   singleton_count,
        "Summary_Message": (
            f"{comp_count} connected component(s) identified "
            f"across {node_count} node(s) and {edge_count} edge(s)."
        ),
    }]


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------

def handle_graph_connectedComponents(
    conn: TeradataConnection,
    container_pattern: str,
    exclude_objects: str = '',
    edge_repository: str = '',
    tool_name: str | None = None,
    *args,
    **kwargs
):
    """
    Identify all Weakly Connected Components (WCC) in the dependency graph.

    Pure-Python implementation — no stored procedure required.  Issues a single
    SQL SELECT to fetch the scoped edge set, then performs Union-Find WCC
    partitioning entirely in the MCP server process.

    A connected component is a maximal set of nodes where every node can reach
    every other node when edge direction is ignored.  This partitions the graph
    into isolated sub-graphs.

    Use this tool for:
      - Understanding graph structure and partitioning
      - Identifying isolated sub-graphs
      - Scoping downstream impact analysis to a single component
      - Pre-filtering before cycle detection (cycles exist only within a component)
      - Identifying "islands" of related objects for migration or refactoring
      - Estimating blast radius

    Arguments:
      container_pattern - str: CSV LIKE patterns for container scope.
                          Supports wildcards (%) and CSV format.
                          Examples: '%WBC%', '%WBC%,%StGeo%', 'DEV01_%,DEV02_%'

                          CRITICAL: STRING type, not array.
                          CORRECT: container_pattern="%WBC%,%StGeo%"
                          WRONG:   container_pattern=["%WBC%", "%StGeo%"]

      exclude_objects   - str: CSV LIKE patterns to exclude.
                          Matches against container name (or DB.Object if
                          the pattern contains a dot).
                          Default: '' (no exclusions)

      edge_repository   - str: Edge repository view/table conforming to the
                          Graph Edge Contract (Src_Container_Name,
                          Src_Object_Name, Src_Kind, Tgt_Container_Name,
                          Tgt_Object_Name, Tgt_Kind columns).
                          For AI-Native Data Products use:
                            '{ProductName}_Semantic.lineage_graph'
                          Call graph_edgeContractDDL to generate a new one.
                          Required — no default.

    Returns:
      ResponseType: formatted response with connected component results.

      Response structure:
        {
          "node_details":        [...],  // One row per node with Component_Id
          "component_summaries": [...],  // One row per component
          "summary_stats":       [...]   // Single aggregate row
        }

      node_details row fields:
        Node_FQ, DatabaseName, ObjectName, Component_Id, Object_Kind

      component_summaries row fields:
        Component_Id, Node_Count, Node_List

      summary_stats row fields:
        Component_Count, Node_Count, Edge_Count,
        Largest_Component, Smallest_Component, Singleton_Count, Summary_Message
    """
    logger.debug(
        "Tool: handle_graph_connectedComponents: Args: "
        "container_pattern=%s, exclude_objects=%s, edge_repository=%s",
        container_pattern, exclude_objects, edge_repository
    )

    # -----------------------------------------------------------------------
    # Parse and validate inputs
    # -----------------------------------------------------------------------
    container_patterns = parse_csv_patterns(container_pattern)
    if not container_patterns:
        return create_response(
            {"error": "container_pattern must not be empty"},
            {
                "tool_name":         tool_name or "graph_connectedComponents",
                "container_pattern": container_pattern,
                "status":            "error",
            }
        )

    if not edge_repository:
        return create_response(
            {"error": (
                "edge_repository is required. "
                "For AI-Native Data Products use '{ProductName}_Semantic.lineage_graph'. "
                "Call graph_edgeContractDDL to generate a new edge repository."
            )},
            {
                "tool_name":         tool_name or "graph_connectedComponents",
                "container_pattern": container_pattern,
                "status":            "error",
            }
        )

    excl_pattern_list = parse_csv_patterns(exclude_objects)

    try:
        with conn.cursor() as cur:
            # -------------------------------------------------------------------
            # Step 1 — Fetch all scoped edges in one SQL SELECT
            # -------------------------------------------------------------------
            container_where = build_like_or(
                container_patterns, 'Src_Container_Name'
            )
            excl_where = _build_excl_clauses(excl_pattern_list)

            edge_sql = f"""
LOCKING ROW FOR ACCESS
SELECT
     TRIM(Src_Container_Name) || '.' || TRIM(Src_Object_Name) AS Src_FQ
    ,TRIM(Tgt_Container_Name) || '.' || TRIM(Tgt_Object_Name) AS Tgt_FQ
    ,COALESCE(TRIM(Src_Kind), 'Unknown')                       AS Src_Kind
FROM  {edge_repository}
WHERE {container_where}
  {excl_where}
"""
            logger.debug(
                "Tool: handle_graph_connectedComponents: Fetching edges:\n%s",
                edge_sql
            )

            cur.execute(edge_sql)
            raw_edges = cur.fetchall()

        # -------------------------------------------------------------------
        # Step 2 — Build Union-Find and collect node kinds
        # -------------------------------------------------------------------
        uf = _UnionFind()
        node_kind: dict[str, str] = {}      # {node_fq: object_kind}

        for src_fq, tgt_fq, src_kind in raw_edges:
            uf.union(src_fq, tgt_fq)
            # Record source kind; target kind not available without a second lookup
            if src_fq not in node_kind:
                node_kind[src_fq] = src_kind or 'Unknown'

        edge_count = len(raw_edges)
        logger.debug(
            "Tool: handle_graph_connectedComponents: Loaded %d edges", edge_count
        )

        # -------------------------------------------------------------------
        # Step 3 — Assign integer component IDs
        # -------------------------------------------------------------------
        comp_map = uf.component_map()
        unique_roots = sorted({v for v in comp_map.values()})
        root_to_id   = {r: i + 1 for i, r in enumerate(unique_roots)}

        component_count = len(unique_roots)
        logger.debug(
            "Tool: handle_graph_connectedComponents: %d component(s) identified",
            component_count
        )

        # -------------------------------------------------------------------
        # Step 4 — Build response structures
        # -------------------------------------------------------------------
        node_details        = _build_node_details(comp_map, root_to_id, node_kind)
        component_summaries = _build_component_summaries(comp_map, root_to_id)
        summary_stats       = _build_summary_stats(component_summaries, edge_count)

        response_data = {
            "node_details":        node_details,
            "component_summaries": component_summaries,
            "summary_stats":       summary_stats,
        }

        metadata = {
            "tool_name":         tool_name or "graph_connectedComponents",
            "container_pattern": container_pattern,
            "exclude_objects":   exclude_objects,
            "edge_repository":   edge_repository,
            "result_set_counts": {
                "node_details":        len(node_details),
                "component_summaries": len(component_summaries),
                "summary_stats":       len(summary_stats),
            },
            "status":  "success",
            "message": summary_stats[0]["Summary_Message"],
        }

        logger.debug(
            "Tool: handle_graph_connectedComponents: metadata: %s", metadata
        )
        return create_response(response_data, metadata)

    except Exception as e:
        logger.error(
            "Tool: handle_graph_connectedComponents: Error: %s", e, exc_info=True
        )
        return create_response(
            {"error": str(e)},
            {
                "tool_name":         tool_name or "graph_connectedComponents",
                "container_pattern": container_pattern,
                "status":            "error",
            }
        )


# ---------------------------------------------------------------------------
# Tool registration descriptor
# ---------------------------------------------------------------------------
GRAPH_CONNECTED_COMPONENTS_TOOL = {
    "name": "graph_connectedComponents",
    "handler": handle_graph_connectedComponents,
    "description": (
        "Identify all Weakly Connected Components (WCC) in the dependency graph. "
        "Pure-Python implementation — no stored procedure required. "
        "A connected component is a maximal set of nodes reachable from one another "
        "when edge direction is ignored. Fetches the scoped edge set in one SQL SELECT, "
        "then performs Union-Find WCC partitioning in the MCP server process. "
        "Returns node-to-component mapping, per-component summaries, and overall "
        "statistics. Use to understand graph structure, identify isolated sub-graphs, "
        "scope impact analysis, or pre-filter before cycle detection. "
        "Requires an edge repository conforming to the Graph Edge Contract. "
        "For AI-Native Data Products use '{ProductName}_Semantic.lineage_graph'. "
        "Call graph_edgeContractDDL to generate a new edge repository."
    ),
    "parameters": {
        "container_pattern": {
            "type": "string",
            "description": (
                "CSV LIKE patterns for containers (databases/schemas) to scan. "
                "Supports wildcards: 'DFJ%' or '%WBC%,%StGeo%' for multiple."
            ),
            "required": True,
        },
        "exclude_objects": {
            "type": "string",
            "description": (
                "CSV LIKE patterns to exclude from the scan. "
                "Matches against container name (or DB.Object if pattern contains a dot). "
                "Example: 'DFJ%,C_D02%'. Default: '' (no exclusions)."
            ),
            "default": "",
        },
        "edge_repository": {
            "type": "string",
            "description": (
                "Edge repository table or view conforming to the Graph Edge Contract. "
                "For AI-Native Data Products use '{ProductName}_Semantic.lineage_graph'. "
                "Call graph_edgeContractDDL to generate one if needed. "
                "Required — no default."
            ),
            "required": True,
        },
        },
    },
}
