"""
graph_bfsLevels.py — Pure-Python BFS implementation for graph dependency analysis.

This module provides handle_graph_bfsLevels, a pure-Python BFS
implementation that executes entirely in the MCP server process.

Key design points:
  - One SQL round-trip to Teradata (edge fetch), then all BFS runs in Python.
  - Standard queue-based BFS (O(V+E)) rather than iterative SQL relaxation.
  - No stored procedure dependency — no volatile tables, no Teradata DDL objects.
  - All include_containers, exclude_objects, and depth-cap filtering applied
    in Python before BFS starts.
  - Output schema: node fields, direction values, nearest_root,
    cycle_candidates, summary — fully compatible with the MCP tool
    descriptor, tool registration, and all callers.

Edge direction convention (critical — matches the corrected SP):
  Edge Repository edge:  Src "referenced by" Tgt
    => Src is the DEPENDENCY   (upstream   of Tgt)
    => Tgt is the DEPENDENT    (downstream of Src)

  Upstream   BFS (finds what a node DEPENDS ON):
    Traverse edges in the Src→Tgt direction.
    Starting from settled Tgt-side nodes, discover Src-side ancestors.
    node_i = Src_Object_Name_FQ  (upstream candidate being discovered)
    node_j = Tgt_Object_Name_FQ  (already-settled downstream neighbour)

  Downstream BFS (finds what DEPENDS ON a node):
    Traverse edges in the Tgt→Src direction.
    Starting from settled Src-side nodes, discover Tgt-side consumers.
    node_i = Tgt_Object_Name_FQ  (downstream candidate being discovered)
    node_j = Src_Object_Name_FQ  (already-settled upstream neighbour)

Author:  Paul Dancer — Teradata Global Field Tech
"""

import logging
import fnmatch
from collections import defaultdict, deque

from teradatasql import TeradataConnection
from teradata_mcp_server.tools.utils import create_response, rows_to_json
from teradata_mcp_server.tools.graph._graph_utils import (
    bfs_safe_int,
    create_bfs_summary,
    extract_cycle_candidates,
    parse_csv_patterns,
)

logger = logging.getLogger("teradata_mcp_server")


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------

def handle_graph_bfsLevels(
    conn: TeradataConnection,
    root_node_list: str,
    max_depth_up: int = 10,
    max_depth_down: int = 10,
    exclude_objects: str = '',
    include_containers: str = '',
    edge_repository: str = '',
    tool_name: str | None = None,
    *args,
    **kwargs
):
    """
    Compute BFS shortest-path hop distances from one or more root nodes.

    Pure-Python implementation — no stored procedure required.

    WHEN TO USE THIS TOOL vs graph_traceLineage:
    -------------------------------------------------------
    Use graph_bfsLevels when asked to:
      - Sequence objects for deployment or migration (ORDER BY downstream_level
        gives correct topological deployment order for root objects)
      - Group objects into migration waves (nearest_root identifies which of
        the input root tables each object belongs to)
      - Find which migration root table each object is closest to across a
        multi-root migration scope
      - Identify cycle members by depth (direction='BOTH' nodes with unequal
        absolute upstream/downstream levels are cycle candidates)
      - Count objects within N hops of a change (blast-radius sizing)
      - Answer "how far is object X from the migration root tables?"

    Do NOT use graph_bfsLevels for general lineage tracing, impact path
    analysis, or questions about which specific objects depend on which.
    Use graph_traceLineage for those — it returns the full edge
    set with relationship detail. graph_bfsLevels returns distances and
    wave groupings, not dependency paths or edge detail.

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
                          graph_traceLineage first to discover names.

      max_depth_up      - int: Maximum upstream hops to traverse.
                          0 = skip upstream analysis entirely.
                          Default: 10

                          Upstream means "what this object DEPENDS ON" —
                          its sources, prerequisites, and ancestors.
                          For root objects with in-degree zero, upstream_level
                          will be NULL for all non-root nodes (correct).

      max_depth_down    - int: Maximum downstream hops to traverse.
                          0 = skip downstream analysis entirely.
                          Default: 10

                          Downstream means "what DEPENDS ON this object" —
                          its consumers, dependents, and impact radius.
                          For root objects with in-degree zero, downstream_level
                          will show positive values for all consumers (correct).

      exclude_objects   - str: CSV of FQ object name LIKE patterns to exclude.
                          Matched against both Src and Tgt sides of every edge.
                          Python fnmatch is used for pattern matching (% → *).
                          Example: 'DFJ%,C_D02%,%.temp_%'
                          Default: '' (no exclusions)

      include_containers - str: CSV of container name LIKE patterns to include.
                           Only edges where BOTH Src and Tgt containers match
                           at least one pattern are traversed.
                           Python fnmatch used for matching (% → *).
                           Empty = all containers included.
                           Example: 'DEV01_StGeo%,MF_STGEO%,TABLEAU%,POWERBI%'
                           Default: '' (all containers)

      edge_repository   - str: Edge repository view/table conforming to the
                          Required parameter — no default.

    Returns:
      ResponseType: formatted response with BFS node results + metadata.
      Schema is identical to handle_graph_bfsLevels (SP-based tool).

      Response structure:
        {
          "nodes": [
            {
              "node":             "DEV01_StGeo_STD_T.mortgage_account",
              "container_name":   "DEV01_StGeo_STD_T",
              "object_name":      "mortgage_account",
              "object_kind":      "Table",
              "upstream_level":   None,    // None (NULL) if unreachable or skipped
              "downstream_level": 0,       // 0 for root, positive for consumers
              "nearest_root":     "DEV01_StGeo_STD_T.mortgage_account",
              "direction":        "ROOT",  // ROOT / U / D / BOTH
              "is_root":          "Y"
            },
            ...
          ],
          "cycle_candidates": [...],  // direction='BOTH' nodes with unequal
                                      // absolute upstream/downstream levels
          "summary": {
            "total_nodes":          46,
            "root_nodes":           3,
            "upstream_only":        12,
            "downstream_only":      28,
            "both_directions":      3,
            "cycle_candidates":     1,
            "max_upstream_depth":   4,
            "max_downstream_depth": 5,
            "nodes_per_nearest_root": {"DB.Root1": 20, "DB.Root2": 26},
            "object_kind_counts":   {"Table": 10, "View": 22, "Macro": 8, ...}
          }
        }

      direction values:
        ROOT  - One of the input root nodes
        U     - Reachable upstream only (negative upstream_level)
        D     - Reachable downstream only (positive downstream_level)
        BOTH  - Reachable in both directions — possible cycle member.
                Unequal absolute levels indicate a back-edge (cycle).
                Equal absolute levels indicate a shared dependency.

    Technical Implementation Notes:
      - One SQL round-trip to fetch all edges matching the container/exclusion
        filters. All BFS computation is then done in Python memory.
      - Standard queue-based BFS (O(V+E)) — optimal for unweighted graphs.
        This is more correct than the original Bellman-Ford style SQL
        relaxation loop that the SP inherited from the notebook.
      - Multi-source BFS: all root nodes are seeded simultaneously at level 0.
        Each non-root node settles at the distance to its nearest root, with
        ties broken deterministically by lexicographic root name order.
      - Upstream BFS follows Src→Tgt edges to discover Src-side ancestors.
      - Downstream BFS follows Tgt→Src edges to discover Tgt-side consumers.
      - This direction convention matches the corrected SP (Option B fix):
          upstream_level = NULL for root objects with in-degree zero (correct)
          downstream_level = positive for all consumers (correct)
      - Filter application order:
          1. SQL WHERE clause: fetch only edges matching include_containers
             (both Src and Tgt containers must match at least one pattern)
          2. Python post-filter: exclude edges where either endpoint matches
             an exclude_objects pattern (applied before building adjacency)
          3. BFS depth cap: enforced during queue processing
      - Node metadata (container_name, object_name, object_kind) is derived
        from the edge set and stored in a node registry during the fetch phase.
    """
    logger.debug(
        "Tool: handle_graph_bfsLevels: Args: root_node_list=%s, "
        "max_depth_up=%s, max_depth_down=%s, exclude_objects=%s, "
        "include_containers=%s, edge_repository=%s",
        root_node_list, max_depth_up, max_depth_down,
        exclude_objects, include_containers, edge_repository
    )

    if not edge_repository:
        return create_response(
            {"error": "edge_repository is required. Call graph_edgeContractDDL to generate one."},
            {
                "tool_name": tool_name or "graph_bfsLevels",
                "status": "error",
            }
        )

    # Clamp depth parameters to safe range
    max_depth_up   = max(0, min(10, int(max_depth_up)))
    max_depth_down = max(0, min(10, int(max_depth_down)))

    _tn = tool_name if tool_name else "graph_bfsLevels"

    try:
        # ------------------------------------------------------------------
        # Step 1 — Parse root node list
        # ------------------------------------------------------------------
        roots: list[str] = parse_csv_patterns(root_node_list)

        if not roots:
            raise ValueError(
                f"root_node_list is empty or could not be parsed: "
                f"'{root_node_list}'"
            )

        logger.debug(
            f"Tool: handle_graph_bfsLevels: "
            f"Parsed {len(roots)} root node(s): {roots}"
        )

        # ------------------------------------------------------------------
        # Step 2 — Parse filter patterns for Python-side matching
        # ------------------------------------------------------------------
        excl_patterns = parse_csv_patterns(exclude_objects)   # may be empty
        incl_patterns = parse_csv_patterns(include_containers)  # may be empty

        # ------------------------------------------------------------------
        # Step 3 — Fetch edge set from Teradata (one round-trip)
        #
        # include_containers filter is applied in SQL (WHERE clause) for
        # efficiency — avoids fetching edges that will be discarded.
        # exclude_objects filter is applied in Python (more flexible LIKE
        # patterns that are awkward to push into a single SQL predicate).
        #
        # Column selection:
        #   Src_Object_Name_FQ — fully-qualified source (dependency/upstream)
        #   Tgt_Object_Name_FQ — fully-qualified target (dependent/downstream)
        #   Src_Container_Name — database of source  (for node registry)
        #   Src_Object_Name    — short name of source (for node registry)
        #   Src_Kind           — object type of source
        #   Tgt_Container_Name — database of target
        #   Tgt_Object_Name    — short name of target
        #   Tgt_Kind           — object type of target
        # ------------------------------------------------------------------
        fetch_sql = _build_fetch_sql(
            edge_repository  = edge_repository,
            incl_patterns    = incl_patterns,
        )

        logger.debug(
            f"Tool: handle_graph_bfsLevels: Fetching edges: {fetch_sql}"
        )

        with conn.cursor() as cur:
            cur.execute(fetch_sql)
            raw_rows = cur.fetchall()
            col_names = [d[0].lower() for d in cur.description]

        logger.debug(
            f"Tool: handle_graph_bfsLevels: "
            f"Fetched {len(raw_rows)} raw edge rows"
        )

        # ------------------------------------------------------------------
        # Step 4 — Build in-memory graph structures
        #
        # node_registry: node_fq → {container_name, object_name, object_kind}
        # fwd_adj: Src → {Tgt}  (Src referenced by Tgt; Src is the dependency)
        # rev_adj: Tgt → {Src}  (reverse: Tgt depends on Src)
        #
        # fwd_adj is used by the UPSTREAM BFS to discover Src-side ancestors
        # starting from settled Tgt-side neighbours.
        #
        # rev_adj is used by the DOWNSTREAM BFS to discover Tgt-side consumers
        # starting from settled Src-side neighbours.
        #
        # Exclude-objects filtering is applied here: any edge where either
        # endpoint FQ name matches a pattern in excl_patterns is dropped.
        # ------------------------------------------------------------------
        node_registry: dict[str, dict] = {}
        fwd_adj: dict[str, set[str]] = defaultdict(set)  # Src → {Tgt}
        rev_adj: dict[str, set[str]] = defaultdict(set)  # Tgt → {Src}

        col_idx = {name: i for i, name in enumerate(col_names)}

        edges_total    = 0
        edges_excluded = 0

        for row in raw_rows:
            src_fq  = _val(row, col_idx, 'src_object_name_fq')
            tgt_fq  = _val(row, col_idx, 'tgt_object_name_fq')
            src_db  = _val(row, col_idx, 'src_container_name')
            src_nm  = _val(row, col_idx, 'src_object_name')
            src_knd = _val(row, col_idx, 'src_kind')
            tgt_db  = _val(row, col_idx, 'tgt_container_name')
            tgt_nm  = _val(row, col_idx, 'tgt_object_name')
            tgt_knd = _val(row, col_idx, 'tgt_kind')

            if not src_fq or not tgt_fq:
                continue

            edges_total += 1

            # Apply exclude_objects filter — both endpoints checked
            if excl_patterns and (
                _matches_any(src_fq, excl_patterns) or
                _matches_any(tgt_fq, excl_patterns)
            ):
                edges_excluded += 1
                continue

            # Register both nodes in the registry
            if src_fq not in node_registry:
                node_registry[src_fq] = {
                    'container_name': src_db or '',
                    'object_name':    src_nm or src_fq.split('.')[-1],
                    'object_kind':    src_knd or '',
                }
            if tgt_fq not in node_registry:
                node_registry[tgt_fq] = {
                    'container_name': tgt_db or '',
                    'object_name':    tgt_nm or tgt_fq.split('.')[-1],
                    'object_kind':    tgt_knd or '',
                }

            # Build forward and reverse adjacency
            fwd_adj[src_fq].add(tgt_fq)   # Src → Tgt
            rev_adj[tgt_fq].add(src_fq)   # Tgt → Src

        logger.debug(
            f"Tool: handle_graph_bfsLevels: "
            f"Graph built — {len(node_registry)} unique nodes, "
            f"{edges_total} raw edges, {edges_excluded} excluded. "
            f"|fwd_adj|={len(fwd_adj)}, |rev_adj|={len(rev_adj)}"
        )

        # Ensure root nodes are registered even if they have no edges
        # (isolated roots are valid — they appear only as ROOT in output)
        for r in roots:
            if r not in node_registry:
                parts = r.split('.', 1)
                node_registry[r] = {
                    'container_name': parts[0] if len(parts) > 1 else '',
                    'object_name':    parts[1] if len(parts) > 1 else r,
                    'object_kind':    '',
                }

        # ------------------------------------------------------------------
        # Step 5 — Multi-source BFS: UPSTREAM pass
        #
        # "Upstream" = what a node DEPENDS ON (its sources, ancestors).
        #
        # Edge Repository: Src "referenced by" Tgt  ⟹  Src is the dependency.
        #
        # Algorithm:
        #   Seed all root nodes at level 0.
        #   For each settled Tgt-side node (neighbour), look up its Src-side
        #   nodes via rev_adj (Tgt → {Src}).
        #   Each reachable Src node is upstream of the root.
        #
        # Why rev_adj?
        #   rev_adj[tgt] = {all Src nodes that Tgt depends on}
        #   Walking rev_adj from a settled node discovers its dependencies —
        #   which is exactly "upstream" in data lineage terms.
        #
        # For root objects with in-degree zero (no rev_adj entry), no Src
        # nodes exist, so upstream_level remains None for all non-root nodes.
        # This is correct behaviour.
        # ------------------------------------------------------------------
        up_level:    dict[str, int]      = {}  # node_fq → hop count (0..N)
        up_root:     dict[str, str]      = {}  # node_fq → nearest root

        if max_depth_up > 0:
            up_level, up_root = _bfs_multisource(
                roots        = roots,
                adj          = rev_adj,     # Tgt → {Src}: walk upstream
                max_depth    = max_depth_up,
                label        = "upstream",
            )
            logger.debug(
                f"Tool: handle_graph_bfsLevels: "
                f"Upstream BFS settled {len(up_level)} nodes "
                f"(max_depth={max_depth_up})"
            )
        else:
            logger.debug(
                "Tool: handle_graph_bfsLevels: "
                "Upstream BFS skipped (max_depth_up=0)"
            )

        # ------------------------------------------------------------------
        # Step 6 — Multi-source BFS: DOWNSTREAM pass
        #
        # "Downstream" = what DEPENDS ON a node (its consumers, dependents).
        #
        # Edge Repository: Src "referenced by" Tgt  ⟹  Tgt is the dependent.
        #
        # Algorithm:
        #   Seed all root nodes at level 0.
        #   For each settled Src-side node (neighbour), look up its Tgt-side
        #   nodes via fwd_adj (Src → {Tgt}).
        #   Each reachable Tgt node is downstream of the root.
        #
        # Why fwd_adj?
        #   fwd_adj[src] = {all Tgt nodes that reference Src}
        #   Walking fwd_adj from a settled node discovers its consumers —
        #   which is exactly "downstream" in data lineage terms.
        #
        # For root objects with in-degree zero, all their Tgt-side consumers
        # are reachable via fwd_adj, so downstream_level correctly shows
        # positive values for views, macros, reports, etc.
        # ------------------------------------------------------------------
        dn_level:    dict[str, int]      = {}
        dn_root:     dict[str, str]      = {}

        if max_depth_down > 0:
            dn_level, dn_root = _bfs_multisource(
                roots        = roots,
                adj          = fwd_adj,     # Src → {Tgt}: walk downstream
                max_depth    = max_depth_down,
                label        = "downstream",
            )
            logger.debug(
                f"Tool: handle_graph_bfsLevels: "
                f"Downstream BFS settled {len(dn_level)} nodes "
                f"(max_depth={max_depth_down})"
            )
        else:
            logger.debug(
                "Tool: handle_graph_bfsLevels: "
                "Downstream BFS skipped (max_depth_down=0)"
            )

        # ------------------------------------------------------------------
        # Step 7 — Assemble result rows
        #
        # One row per reachable node (including roots themselves).
        # Schema matches SP output exactly so callers need no changes.
        #
        # Rules:
        #   upstream_level   : negative integer (-(hop_count)), None if unreachable
        #   downstream_level : positive integer  (+hop_count),  None if unreachable
        #   Root node        : upstream_level=0, downstream_level=0 always
        #   direction        : ROOT / U / D / BOTH
        #   nearest_root     : upstream root takes precedence over downstream root
        #   is_root          : 'Y' if node is in the root set, 'N' otherwise
        # ------------------------------------------------------------------
        root_set = set(roots)

        # Union of all settled nodes (roots + BFS-reachable)
        all_nodes: set[str] = root_set.copy()
        all_nodes.update(up_level.keys())
        all_nodes.update(dn_level.keys())

        result_nodes: list[dict] = []

        for node_fq in sorted(all_nodes):
            meta = node_registry.get(node_fq, {})
            is_root_node = node_fq in root_set

            if is_root_node:
                upstream_level   = 0
                downstream_level = 0
                nearest_root_val = node_fq
                direction        = 'ROOT'
            else:
                raw_up = up_level.get(node_fq)
                raw_dn = dn_level.get(node_fq)

                # upstream_level: negative (opposite sign to hop count)
                upstream_level   = (-(raw_up)) if raw_up is not None else None
                # downstream_level: positive (same sign as hop count)
                downstream_level = raw_dn if raw_dn is not None else None

                # nearest_root: upstream wins on tie (matches SP behaviour)
                nearest_root_val = (
                    up_root.get(node_fq) or dn_root.get(node_fq)
                )

                if raw_up is not None and raw_dn is not None:
                    direction = 'BOTH'
                elif raw_up is not None:
                    direction = 'U'
                elif raw_dn is not None:
                    direction = 'D'
                else:
                    direction = None  # Should not occur — node is in all_nodes

            result_nodes.append({
                'node':             node_fq,
                'container_name':   meta.get('container_name', ''),
                'object_name':      meta.get('object_name', ''),
                'object_kind':      meta.get('object_kind', ''),
                'upstream_level':   upstream_level,
                'downstream_level': downstream_level,
                'nearest_root':     nearest_root_val,
                'direction':        direction,
                'is_root':          'Y' if is_root_node else 'N',
            })

        logger.debug(
            f"Tool: handle_graph_bfsLevels: "
            f"Assembled {len(result_nodes)} result nodes"
        )

        # ------------------------------------------------------------------
        # Step 8 — Build summary and extract cycle candidates
        # (re-uses existing private helpers from the SP-based tool)
        # ------------------------------------------------------------------
        cycle_cands = extract_cycle_candidates(result_nodes)
        summary     = create_bfs_summary(result_nodes, cycle_cands)

        # ------------------------------------------------------------------
        # Step 9 — Assemble response (identical schema to SP-based tool)
        # ------------------------------------------------------------------
        response_data = {
            "nodes":            result_nodes,
            "cycle_candidates": cycle_cands,
            "summary":          summary,
        }

        metadata = {
            "tool_name":          _tn,
            "root_node_list":     root_node_list,
            "max_depth_up":       max_depth_up,
            "max_depth_down":     max_depth_down,
            "exclude_objects":    exclude_objects,
            "include_containers": include_containers,
            "edge_repository":    edge_repository,
            "implementation":     "python_bfs",  # distinguishes from SP-based tool
            "graph_stats": {
                "unique_nodes_in_graph": len(node_registry),
                "raw_edges_fetched":     edges_total,
                "edges_excluded":        edges_excluded,
                "edges_traversed":       edges_total - edges_excluded,
            },
            "counts":             summary,
            "status":             "success",
            "rtn_code":           0,
            "message": (
                f"Module=graph_bfsLevels;"
                f"RootCount={len(roots)};"
                f"TotalNodes={len(result_nodes)};"
                f"Success;"
            ),
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
                "tool_name":      _tn,
                "root_node_list": root_node_list,
                "status":         "error",
            }
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------
# parse_csv_patterns is imported from _graph_utils.


def _matches_any(fq_name: str, patterns: list[str]) -> bool:
    """
    Return True if fq_name matches any pattern in patterns.

    Converts SQL LIKE wildcards (%) to fnmatch wildcards (*) before matching.
    Case-insensitive to match Teradata NOT CASESPECIFIC behaviour.

    Arguments:
      fq_name  - Fully-qualified object name (e.g. 'MyDB.MyTable')
      patterns - List of LIKE-style patterns (e.g. ['DFJ%', '%.temp_%'])

    Returns:
      True if any pattern matches, False otherwise
    """
    name_lower = fq_name.lower()
    for pat in patterns:
        # Convert SQL LIKE % to fnmatch *
        fn_pat = pat.replace('%', '*').lower()
        if fnmatch.fnmatch(name_lower, fn_pat):
            return True
    return False


def _matches_container_any(container: str, patterns: list[str]) -> bool:
    """
    Return True if the container name matches any of the given patterns.

    Used to validate include_containers filter against container names.
    Converts SQL LIKE % to fnmatch * for matching.

    Arguments:
      container - Database/container name (e.g. 'DEV01_StGeo_STD_T')
      patterns  - List of LIKE-style container patterns

    Returns:
      True if any pattern matches, False otherwise
    """
    if not patterns:
        return True  # No whitelist = all containers included
    name_lower = container.lower()
    for pat in patterns:
        fn_pat = pat.replace('%', '*').lower()
        if fnmatch.fnmatch(name_lower, fn_pat):
            return True
    return False


def _build_fetch_sql(
    edge_repository: str,
    incl_patterns:   list[str],
) -> str:
    """
    Build the SQL query to fetch edges from the edge repository.

    include_containers is pushed into the WHERE clause for efficiency.
    exclude_objects is applied in Python after fetching.

    Edge repository column usage:
      Src_Object_Name_FQ — fully-qualified dependency (upstream)
      Tgt_Object_Name_FQ — fully-qualified dependent  (downstream)

    Arguments:
      edge_repository - Fully-qualified view/table name
      incl_patterns   - Parsed list of container LIKE patterns (may be empty)

    Returns:
      SQL string ready for cursor.execute()
    """
    base_sql = f"""
LOCKING ROW FOR ACCESS
SELECT
     TRIM(r.Src_Object_Name_FQ) AS Src_Object_Name_FQ
    ,TRIM(r.Tgt_Object_Name_FQ) AS Tgt_Object_Name_FQ
    ,TRIM(r.Src_Container_Name) AS Src_Container_Name
    ,TRIM(r.Src_Object_Name)    AS Src_Object_Name
    ,TRIM(r.Src_Kind)           AS Src_Kind
    ,TRIM(r.Tgt_Container_Name) AS Tgt_Container_Name
    ,TRIM(r.Tgt_Object_Name)    AS Tgt_Object_Name
    ,TRIM(r.Tgt_Kind)           AS Tgt_Kind
FROM {edge_repository} r
WHERE r.Src_Object_Name_FQ IS NOT NULL
AND   TRIM(r.Src_Object_Name_FQ) <> ''
AND   r.Tgt_Object_Name_FQ IS NOT NULL
AND   TRIM(r.Tgt_Object_Name_FQ) <> ''"""

    if incl_patterns:
        # Build OR-expanded WHERE clause for container inclusion.
        # Applies to BOTH Src and Tgt containers — an edge is included only
        # if both endpoints are within the whitelisted container set.
        src_clauses = " OR ".join(
            f"TRIM(r.Src_Container_Name) LIKE '{p}'"
            for p in incl_patterns
        )
        tgt_clauses = " OR ".join(
            f"TRIM(r.Tgt_Container_Name) LIKE '{p}'"
            for p in incl_patterns
        )
        base_sql += f"\nAND   ({src_clauses})"
        base_sql += f"\nAND   ({tgt_clauses})"

    return base_sql + ";"


def _val(row, col_idx: dict, col_name: str) -> str | None:
    """
    Safely extract a value from a result row by column name.

    Arguments:
      row      - Tuple of row values from cursor.fetchall()
      col_idx  - Dict mapping lowercase column name → position index
      col_name - Column name to look up (lowercase)

    Returns:
      Stripped string value, or None if missing/null
    """
    idx = col_idx.get(col_name)
    if idx is None:
        return None
    val = row[idx]
    if val is None:
        return None
    return str(val).strip()


def _bfs_multisource(
    roots:     list[str],
    adj:       dict[str, set[str]],
    max_depth: int,
    label:     str,
) -> tuple[dict[str, int], dict[str, str]]:
    """
    Standard queue-based multi-source BFS from a set of root nodes.

    All roots are seeded simultaneously at level 0 (multi-source BFS).
    Each reachable node settles at the hop count to its nearest root.
    Ties are broken deterministically: the lexicographically smallest
    root name wins (consistent with MIN(nearest_root) in the SP).

    Importantly, root nodes themselves are NOT added to the level/root
    dicts returned — they are handled separately in the caller as
    direction='ROOT'. This prevents roots from appearing twice in output.

    Arguments:
      roots     - List of exact root node FQ names
      adj       - Adjacency dict: node → {reachable neighbours}
                  For upstream BFS: rev_adj (Tgt → {Src})
                  For downstream BFS: fwd_adj (Src → {Tgt})
      max_depth - Maximum hops to traverse from any root
      label     - 'upstream' or 'downstream' (used for logging only)

    Returns:
      Tuple of:
        level_map - Dict: node_fq → hop_count (1..max_depth)
                    Root nodes are NOT included (handled separately).
        root_map  - Dict: node_fq → nearest_root FQ name
    """
    level_map: dict[str, int] = {}
    root_map:  dict[str, str] = {}

    # Seed: all root nodes at level 0.
    # Visited set initialised with roots so they are never re-settled
    # by BFS propagation from other roots.
    visited: set[str] = set(roots)

    # Queue entries: (node_fq, nearest_root_fq, current_depth)
    queue: deque[tuple[str, str, int]] = deque()

    for r in sorted(roots):   # sorted → lexicographic tie-breaking
        queue.append((r, r, 0))

    while queue:
        node, nearest_root, depth = queue.popleft()

        if depth >= max_depth:
            # At depth cap — do not propagate further from this node
            continue

        # Traverse neighbours from the adjacency dict
        for neighbour in sorted(adj.get(node, [])):   # sorted → determinism
            if neighbour in visited:
                continue

            visited.add(neighbour)
            new_depth = depth + 1
            level_map[neighbour] = new_depth
            root_map[neighbour]  = nearest_root
            queue.append((neighbour, nearest_root, new_depth))

    logger.debug(
        f"_bfs_multisource [{label}]: "
        f"settled {len(level_map)} non-root nodes"
    )
    return level_map, root_map


# bfs_safe_int — imported from _graph_utils


# create_bfs_summary — imported from _graph_utils



# extract_cycle_candidates — imported from _graph_utils



# ---------------------------------------------------------------------------
# Tool registration descriptor
#
# Register alongside the other GRAPH_*_TOOL descriptors in graph_tools.py.
# ---------------------------------------------------------------------------
GRAPH_BFS_LEVELS_TOOL = {
    # Tool name matches the MCP protocol
    # interface and all existing agent prompts.
    "name":    "graph_bfsLevels",
    "handler": handle_graph_bfsLevels,
    "description": (
        "Compute BFS shortest-path hop distances from one or more root nodes "
        "in the dependency graph. Pure-Python implementation — no stored "
        "procedure required. One SQL round-trip to fetch edges, then all BFS "
        "computation runs in the MCP server process. "
        ""
        "Returns one row per reachable node with: upstream_level (None for root "
        "objects with in-degree zero, negative for upstream ancestors), "
        "downstream_level (0 for roots, positive for consumers), nearest_root "
        "(which of the input root nodes this object is closest to), direction "
        "(ROOT/U/D/BOTH), and is_root flag. Output schema is identical to the "
        "SP-based graph_bfsLevels tool. "
        ""
        "USE THIS TOOL — not graph_traceLineage — when asked to: "
        "sequence objects for deployment or migration (ORDER BY downstream_level "
        "gives correct topological deployment order for objects downstream of "
        "root tables); group objects into migration waves (nearest_root groups "
        "each object under its closest root table); find which migration root "
        "table each object belongs to across a multi-root migration scope; count "
        "objects within N hops of a change for blast-radius sizing; identify "
        "cycle members by depth (direction=BOTH nodes with unequal absolute "
        "upstream/downstream levels are cycle candidates); or answer how far any "
        "object is from the migration root tables. "
        ""
        "Do NOT use this tool for general lineage tracing, impact path analysis, "
        "or questions about which specific objects depend on which — use "
        "graph_traceLineage for those. graph_bfsLevels returns "
        "distances and wave groupings, not dependency paths or edge detail. "
        ""
        "Requires an edge repository conforming to the Graph Edge Contract. "
        "If you don't have one yet, call graph_edgeContractDDL first to "
        "generate the CREATE TABLE or CREATE VIEW DDL. "
        ""
        "IMPORTANT: root_node_list accepts exact fully-qualified names only "
        "(no wildcards). Use graph_findRootObjects first if needed."
    ),
    "parameters": {
        "root_node_list": {
            "type": "string",
            "description": (
                "CSV of exact fully-qualified root node names. No wildcards. "
                "Single: 'MyDB.MyTable'. "
                "Multiple: 'MyDB.TableA,MyDB.TableB,MyDB.TableC'."
            ),
            "required": True,
        },
        "max_depth_up": {
            "type": "integer",
            "description": (
                "Maximum upstream hops to traverse. Upstream = what the node "
                "depends on (its sources and ancestors). "
                "0 = skip upstream entirely. Default: 10."
            ),
            "default": 10,
        },
        "max_depth_down": {
            "type": "integer",
            "description": (
                "Maximum downstream hops to traverse. Downstream = what depends "
                "on the node (its consumers and impact radius). "
                "0 = skip downstream entirely. Default: 10."
            ),
            "default": 10,
        },
        "exclude_objects": {
            "type": "string",
            "description": (
                "CSV of FQ object name LIKE patterns to exclude from traversal. "
                "Matched against both Src and Tgt sides of every edge. "
                "SQL LIKE wildcards (%) supported. "
                "Example: 'DFJ%,C_D02%,%.temp_%'. Default: '' (no exclusions)."
            ),
            "default": "",
        },
        "include_containers": {
            "type": "string",
            "description": (
                "CSV of container name LIKE patterns to include. "
                "Only edges where BOTH Src and Tgt containers match at least "
                "one pattern are fetched and traversed. "
                "SQL LIKE wildcards (%) supported. "
                "Example: 'DEV01_StGeo%,MF_STGEO%,TABLEAU%,POWERBI%'. "
                "Default: '' (all containers)."
            ),
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
    },
}
