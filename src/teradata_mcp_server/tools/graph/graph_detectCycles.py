"""
graph_detectCycles.py — Cycle detection tool.

Provides handle_graph_detectCycles and GRAPH_DETECT_CYCLES_TOOL.

Pure-Python implementation — no stored procedure required.

Algorithm overview:
  1. Fetch all edges within the container scope in a single SQL SELECT.
  2. Perform Union-Find (WCC partitioning) to identify connected components.
  3. Run iterative DFS (grey/black colouring) independently within each
     component. Iterative DFS avoids Python's recursion limit on deep graphs.
  4. Collect and deduplicate all directed cycles found.
  5. Assemble the same three-structure response the SP returned:
       cycle_details   — one row per node per cycle
       cycle_summaries — one row per cycle with human-readable path
       summary_stats   — single aggregate row

Edge direction convention (matches Edge Repository / graph_bfsLevels):
  Src_Object_Name is REFERENCED BY Tgt_Object_Name.
    => Src is the DEPENDENCY (upstream of Tgt).
    => Tgt is the DEPENDENT  (downstream of Src).
  The directed edge for cycle detection runs Src → Tgt:
    a view (Tgt) DEPENDS ON a table (Src), so the edge Src→Tgt represents
    "Src must exist before Tgt".  A cycle in this direction is a genuine
    circular dependency.

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
    Build a NOT (...) exclusion fragment for Src_Container_Name LIKE patterns.

    A pattern containing a dot is treated as a fully-qualified DB.Object pattern;
    a plain pattern is matched against the container name only.

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
# Union-Find for WCC partitioning
# ---------------------------------------------------------------------------

class _UnionFind:
    """
    Simple Union-Find with path compression.

    Used to partition the edge set into Weakly Connected Components before
    running per-component DFS.  Partitioning dramatically reduces the work
    per DFS call on graphs with many isolated sub-graphs.
    """

    def __init__(self):
        self._parent: dict = {}

    def find(self, x) -> str:
        """Return canonical representative of x's component (with path compression)."""
        self._parent.setdefault(x, x)
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])   # path compression
        return self._parent[x]

    def union(self, a, b) -> None:
        """Merge the components containing a and b."""
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb

    def component_map(self) -> dict[str, str]:
        """Return {node: component_root} for all known nodes."""
        return {n: self.find(n) for n in self._parent}


# ---------------------------------------------------------------------------
# Iterative DFS cycle detection
# ---------------------------------------------------------------------------

def _detect_cycles_in_subgraph(
    nodes: set,
    adj: dict[str, list[str]]
) -> list[list[str]]:
    """
    Find all simple directed cycles reachable in an adjacency sub-graph.

    Uses an iterative DFS with grey/black node colouring.  The iterative
    approach is mandatory — Python's default recursion limit (1 000) is
    easily exceeded on deep dependency chains.

    A node is GREY while it is on the current DFS stack (being explored).
    A node is BLACK once all its descendants have been fully explored.
    A back-edge into a GREY node signals a cycle.

    The cycle path is reconstructed from the DFS stack at the moment the
    back-edge is detected.

    Arguments:
      nodes - Set of node FQ names in this component
      adj   - Adjacency list {src: [tgt, ...]} for the full graph
              (caller is responsible for scoping to this component)

    Returns:
      List of cycles; each cycle is a list of FQ node names (start == end).
    """
    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[str, int] = {}
    cycles: list[list[str]] = []

    for start in nodes:
        if colour.get(start) == BLACK:
            continue

        # Stack entries: (node, iterator-over-neighbours, path-so-far)
        stack: list[tuple[str, object, list[str]]] = [
            (start, iter(adj.get(start, [])), [start])
        ]
        colour[start] = GREY

        while stack:
            node, neighbours, path = stack[-1]
            try:
                nxt = next(neighbours)

                if colour.get(nxt) == GREY:
                    # Back-edge found — reconstruct the cycle portion
                    cycle_start_idx = path.index(nxt)
                    cycle = path[cycle_start_idx:] + [nxt]
                    cycles.append(cycle)

                elif colour.get(nxt) != BLACK:
                    colour[nxt] = GREY
                    stack.append(
                        (nxt, iter(adj.get(nxt, [])), path + [nxt])
                    )

            except StopIteration:
                colour[node] = BLACK
                stack.pop()

    return cycles


# ---------------------------------------------------------------------------
# Response assembly helpers
# ---------------------------------------------------------------------------

def _build_cycle_details(
    cycles: list[list[str]],
    component_id_map: dict[str, int]
) -> list[dict]:
    """
    Build the cycle_details result set — one row per node per cycle.

    Arguments:
      cycles          - List of cycle paths (each a list of FQ names, start==end)
      component_id_map - {node_fq: component_id} lookup

    Returns:
      List of dicts matching the SP's cur_NodeDetails schema
    """
    rows = []
    for cycle_id, cycle in enumerate(cycles, start=1):
        # The last element is a repeat of the first — omit it for position count
        members = cycle[:-1]
        for pos, node_fq in enumerate(members, start=1):
            rows.append({
                "Cycle_Id":        cycle_id,
                "Cycle_Pos":       pos,
                "Node_FQ":         node_fq,
                "Cycle_Length":    len(members),
                "Component_Id":    component_id_map.get(node_fq, -1),
                "Strategy":        "DFS",
            })
    return rows


def _build_cycle_summaries(
    cycles: list[list[str]],
    component_id_map: dict[str, int]
) -> list[dict]:
    """
    Build the cycle_summaries result set — one row per cycle.

    Arguments:
      cycles           - List of cycle paths
      component_id_map - {node_fq: component_id} lookup

    Returns:
      List of dicts matching the SP's cur_CompSummaries schema
    """
    rows = []
    for cycle_id, cycle in enumerate(cycles, start=1):
        members = cycle[:-1]
        path_str = ' -> '.join(cycle)       # start → ... → start
        rows.append({
            "Cycle_Id":        cycle_id,
            "Cycle_Length":    len(members),
            "Component_Id":    component_id_map.get(members[0], -1),
            "Strategy":        "DFS",
            "Cycle_Path":      path_str,
        })
    return rows


def _build_summary_stats(
    cycles: list[list[str]],
    edge_count: int,
    component_count: int
) -> list[dict]:
    """
    Build the summary_stats result set — single aggregate row.

    Arguments:
      cycles          - List of detected cycles
      edge_count      - Total edges loaded from the repository
      component_count - Number of WCC components identified

    Returns:
      Single-element list matching the SP's cur_SummaryStats schema
    """
    total_nodes_in_cycles = sum(len(c) - 1 for c in cycles)   # exclude repeated end
    components_with_cycles = len({c[0] for c in cycles})       # rough proxy

    if len(cycles) == 0:
        message = "No cycles detected — graph is a DAG."
    elif len(cycles) == 1:
        message = "1 cycle detected."
    else:
        message = f"{len(cycles)} cycles detected."

    return [{
        "Cycle_Count":              len(cycles),
        "Total_Nodes_In_Cycles":    total_nodes_in_cycles,
        "Components_With_Cycles":   components_with_cycles,
        "Edge_Count":               edge_count,
        "Components_Scanned":       component_count,
        "Strategy_Used":            "DFS",
        "Summary_Message":          message,
    }]


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------

def handle_graph_detectCycles(
    conn: TeradataConnection,
    container_pattern: str,
    exclude_objects: str = '',
    edge_repository: str = '',
    tool_name: str | None = None,
    *args,
    **kwargs
):
    """
    Detect circular dependencies (cycles) in the dependency graph.

    Pure-Python implementation — no stored procedure required.  Issues a single
    SQL SELECT to fetch the scoped edge set, then performs WCC partitioning
    followed by iterative DFS cycle detection entirely in the MCP server process.

    Use this tool for:
      - Validating graph integrity (DAG property)
      - Finding objects that form circular references
      - Identifying stub-then-replace code patterns
      - Debugging topological sort hangs
      - Pre-deployment cycle checks

    Arguments:
      container_pattern - str: CSV LIKE patterns for container scope.
                          Supports wildcards (%) and CSV format.
                          Examples:
                            'DFJ%'              — single database family
                            '%WBC%,%StGeo%'     — multiple families
                            'DEV01_%,DEV02_%'   — multiple prefixes

      exclude_objects   - str: CSV LIKE patterns to exclude from the scan.
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
      ResponseType: formatted response with cycle detection results.

      Response structure:
        {
          "cycle_details":   [...],  // One row per node per cycle
          "cycle_summaries": [...],  // One row per cycle with path string
          "summary_stats":   [...]   // Single aggregate row
        }

      cycle_details row fields:
        Cycle_Id, Cycle_Pos, Node_FQ, Cycle_Length, Component_Id

      cycle_summaries row fields:
        Cycle_Id, Cycle_Length, Component_Id, Cycle_Path

      summary_stats row fields:
        Cycle_Count, Total_Nodes_In_Cycles, Components_With_Cycles,
        Edge_Count, Components_Scanned, Summary_Message
    """
    logger.debug(
        "Tool: handle_graph_detectCycles: Args: "
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
                "tool_name": tool_name or "graph_detectCycles",
                "container_pattern": container_pattern,
                "status": "error",
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
                "tool_name": tool_name or "graph_detectCycles",
                "container_pattern": container_pattern,
                "status": "error",
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
FROM  {edge_repository}
WHERE {container_where}
  {excl_where}
"""
            logger.debug(
                "Tool: handle_graph_detectCycles: Fetching edges:\n%s", edge_sql
            )

            cur.execute(edge_sql)
            raw_edges = cur.fetchall()

        # -------------------------------------------------------------------
        # Step 2 — Build adjacency list and WCC components
        # -------------------------------------------------------------------
        # adj[src] = [tgt, ...] — directed: src → tgt means tgt DEPENDS ON src
        adj: dict[str, list[str]] = defaultdict(list)
        uf = _UnionFind()

        for src_fq, tgt_fq in raw_edges:
            adj[src_fq].append(tgt_fq)
            uf.union(src_fq, tgt_fq)

        edge_count = len(raw_edges)
        logger.debug(
            "Tool: handle_graph_detectCycles: Loaded %d edges", edge_count
        )

        if edge_count == 0:
            # No edges in scope — no cycles possible
            return create_response(
                {
                    "cycle_details":   [],
                    "cycle_summaries": [],
                    "summary_stats":   _build_summary_stats([], 0, 0),
                },
                {
                    "tool_name":         tool_name or "graph_detectCycles",
                    "container_pattern": container_pattern,
                    "exclude_objects":   exclude_objects,
                    "edge_repository":   edge_repository,
                    "result_set_counts": {
                        "cycle_details":   0,
                        "cycle_summaries": 0,
                        "summary_stats":   1,
                    },
                    "status":  "success",
                    "message": "No edges found in scope — no cycles possible.",
                }
            )

        # Assign integer component IDs from the Union-Find roots
        comp_map = uf.component_map()
        unique_roots = list({v for v in comp_map.values()})
        root_to_id = {r: i + 1 for i, r in enumerate(unique_roots)}
        component_id_map: dict[str, int] = {
            n: root_to_id[r] for n, r in comp_map.items()
        }

        # Group nodes by component
        components: dict[str, set[str]] = defaultdict(set)
        for node, comp_root in comp_map.items():
            components[comp_root].add(node)

        component_count = len(components)
        logger.debug(
            "Tool: handle_graph_detectCycles: %d components identified",
            component_count
        )

        # -------------------------------------------------------------------
        # Step 3 — Run iterative DFS within each component
        # -------------------------------------------------------------------
        all_cycles: list[list[str]] = []

        for comp_root, comp_nodes in components.items():
            cycles_in_comp = _detect_cycles_in_subgraph(comp_nodes, adj)
            all_cycles.extend(cycles_in_comp)

        logger.debug(
            "Tool: handle_graph_detectCycles: %d cycle(s) detected",
            len(all_cycles)
        )

        # -------------------------------------------------------------------
        # Step 4 — Assemble response structures
        # -------------------------------------------------------------------
        cycle_details   = _build_cycle_details(all_cycles, component_id_map)
        cycle_summaries = _build_cycle_summaries(all_cycles, component_id_map)
        summary_stats   = _build_summary_stats(
            all_cycles, edge_count, component_count
        )

        response_data = {
            "cycle_details":   cycle_details,
            "cycle_summaries": cycle_summaries,
            "summary_stats":   summary_stats,
        }

        metadata = {
            "tool_name":         tool_name or "graph_detectCycles",
            "container_pattern": container_pattern,
            "exclude_objects":   exclude_objects,
            "edge_repository":   edge_repository,
            "result_set_counts": {
                "cycle_details":   len(cycle_details),
                "cycle_summaries": len(cycle_summaries),
                "summary_stats":   len(summary_stats),
            },
            "status":  "success",
            "message": summary_stats[0]["Summary_Message"],
        }

        logger.debug(
            "Tool: handle_graph_detectCycles: metadata: %s", metadata
        )
        return create_response(response_data, metadata)

    except Exception as e:
        logger.error(
            "Tool: handle_graph_detectCycles: Error: %s", e, exc_info=True
        )
        return create_response(
            {"error": str(e)},
            {
                "tool_name":         tool_name or "graph_detectCycles",
                "container_pattern": container_pattern,
                "status":            "error",
            }
        )


# ---------------------------------------------------------------------------
# Tool registration descriptor
# ---------------------------------------------------------------------------
GRAPH_DETECT_CYCLES_TOOL = {
    "name": "graph_detectCycles",
    "handler": handle_graph_detectCycles,
    "description": (
        "Detect circular references (cycles) in the dependency graph. "
        "Pure-Python implementation — no stored procedure required. "
        "Fetches the scoped edge set in one SQL SELECT, partitions into Weakly "
        "Connected Components via Union-Find, then runs iterative DFS cycle "
        "detection within each component. "
        "Returns each cycle as an ordered list of nodes with a human-readable "
        "path string. Use to validate graph integrity, find stub-then-replace "
        "patterns, or identify objects that will cause topological sort to hang. "
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
}
