"""
graph_analyseDatabase.py — Composite graph analysis tool.

Provides handle_graph_analyseDatabase and GRAPH_ANALYSE_DATABASE_TOOL.

Runs all four core graph analyses in a single MCP tool call:
  1. Root object discovery      (findRootObjects logic)
  2. Connected component analysis (connectedComponents logic)
  3. Cycle detection             (detectCycles logic)
  4. BFS deployment waves        (bfsLevels logic)

CRITICAL SCALABILITY ADVANTAGE:
  The four individual tools each independently fetch the edge set from
  Teradata via SQL — that is 4 round-trips fetching the same rows.
  This composite tool fetches the edge set ONCE and shares it across
  all four analyses in memory.  On a graph with 100 000 edges, this
  eliminates ~3 redundant network transfers and ~3 redundant SQL scans.

  Additionally, the composite tool returns ONE MCP response instead of
  four, eliminating 3 stdio/JSON serialisation round-trips through the
  Claude Desktop MCP transport layer — the primary source of latency
  observed at small scale.

SP-free: all computation runs in the MCP server process.  The only
Teradata privilege required is SELECT on the edge repository view.

If you don't have an edge repository yet, call graph_edgeContractDDL first to generate the CREATE TABLE or CREATE VIEW DDL for one.

Author:  Paul Dancer — Teradata Global Field Tech
"""

import logging
import time
from collections import defaultdict, deque
from collections.abc import Iterator

from teradatasql import TeradataConnection

from teradata_mcp_server.tools.graph._graph_utils import (
    bfs_safe_int,
    build_like_or,
    create_bfs_summary,
    extract_cycle_candidates,
    parse_csv_patterns,
)
from teradata_mcp_server.tools.utils import create_response

logger = logging.getLogger("teradata_mcp_server")


# ═══════════════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════════════
# parse_csv_patterns and build_like_or are imported from _graph_utils.


def _build_excl_where(excl_patterns: list[str]) -> str:
    """
    Build exclusion predicates for SQL WHERE clause.

    Supports both database-only patterns ('SANDBOX%') and fully-qualified
    patterns ('DB.Object%') containing a dot separator.

    Arguments:
      excl_patterns - List of exclusion LIKE patterns

    Returns:
      SQL fragment starting with ' AND NOT (...)', or '' if no patterns
    """
    if not excl_patterns:
        return ''
    clauses = []
    for p in excl_patterns:
        if '.' in p:
            db_part, obj_part = p.split('.', 1)
            clauses.append(
                f"(Src_Container_Name LIKE '{db_part}' "
                f"AND Src_Object_Name LIKE '{obj_part}')"
            )
        else:
            clauses.append(f"Src_Container_Name LIKE '{p}'")
    return ' AND NOT (' + ' OR '.join(clauses) + ')'


# ═══════════════════════════════════════════════════════════════════
# Union-Find (path-compressed, union-by-rank)
# ═══════════════════════════════════════════════════════════════════

class _UnionFind:
    """
    Path-compressed Union-Find for connected component detection.

    Provides near-constant-time union and find operations (O(α·N)
    amortised via path compression and union-by-rank).
    """

    def __init__(self):
        """Initialise empty Union-Find structure."""
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def find(self, x: str) -> str:
        """
        Find the root representative of x with path compression.

        Arguments:
          x - Node identifier

        Returns:
          Root representative of x's component
        """
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        """
        Merge the components containing a and b (union-by-rank).

        Arguments:
          a - First node identifier
          b - Second node identifier
        """
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1

    def components(self) -> dict[str, list[str]]:
        """
        Return all components as {root: [members]} dict.

        Returns:
          Dictionary mapping component root to sorted member list
        """
        comps: dict[str, list[str]] = defaultdict(list)
        for node in self._parent:
            comps[self.find(node)].append(node)
        return {k: sorted(v) for k, v in comps.items()}


# ═══════════════════════════════════════════════════════════════════
# Iterative DFS cycle detection
# ═══════════════════════════════════════════════════════════════════

def _find_cycles_dfs(
    nodes: set,
    adj: dict[str, list[str]]
) -> list[list[str]]:
    """
    Find all simple directed cycles via iterative DFS (grey/black colouring).

    Iterative approach avoids Python's recursion limit on deep graphs.

    Arguments:
      nodes - Set of node FQ names in this component
      adj   - Adjacency list {src: [tgt, ...]}

    Returns:
      List of cycles; each cycle is a list of FQ names (start == end)
    """
    white, grey, black = 0, 1, 2
    colour: dict[str, int] = {}
    cycles: list[list[str]] = []

    for start in nodes:
        if colour.get(start) == black:
            continue
        stack: list[tuple[str, Iterator[str], list[str]]] = [
            (start, iter(adj.get(start, [])), [start])
        ]
        colour[start] = grey

        while stack:
            node, neighbours, path = stack[-1]
            try:
                nxt = next(neighbours)
                if colour.get(nxt) == grey:
                    idx = path.index(nxt)
                    cycles.append(path[idx:] + [nxt])
                elif colour.get(nxt) != black:
                    colour[nxt] = grey
                    stack.append((nxt, iter(adj.get(nxt, [])), path + [nxt]))
            except StopIteration:
                colour[node] = black
                stack.pop()

    return cycles


# ═══════════════════════════════════════════════════════════════════
# BFS engine
# ═══════════════════════════════════════════════════════════════════

def _run_bfs(
    root_fqs: list[str],
    fwd_adj: dict[str, list[str]],
    rev_adj: dict[str, list[str]],
    node_meta: dict[str, dict],
    max_depth_down: int,
    max_depth_up: int
) -> dict:
    """
    Run multi-source BFS from the given roots on the in-memory edge set.

    Arguments:
      root_fqs       - List of root node fully-qualified names
      fwd_adj        - Forward adjacency {src: [tgt, ...]} (for downstream)
      rev_adj        - Reverse adjacency {tgt: [src, ...]} (for upstream)
      node_meta      - {fq: {container, object, kind}} metadata lookup
      max_depth_down - Maximum downstream hops
      max_depth_up   - Maximum upstream hops

    Returns:
      Dict with 'nodes', 'cycle_candidates', 'summary' keys
    """
    down_level: dict[str, int] = {}
    up_level: dict[str, int] = {}
    nearest_root: dict[str, str] = {}

    # ── Seed roots at level 0 ──
    for r in root_fqs:
        down_level[r] = 0
        up_level[r] = 0
        nearest_root[r] = r

    # ── Downstream BFS (forward: src → tgt) ──
    if max_depth_down > 0:
        queue: deque[tuple[str, int, str]] = deque()
        for r in root_fqs:
            queue.append((r, 0, r))
        while queue:
            node, depth, root = queue.popleft()
            for tgt in fwd_adj.get(node, []):
                if tgt not in down_level:
                    new_depth = depth + 1
                    if new_depth <= max_depth_down:
                        down_level[tgt] = new_depth
                        nearest_root[tgt] = root
                        queue.append((tgt, new_depth, root))

    # ── Upstream BFS (reverse: tgt → src) ──
    if max_depth_up > 0:
        queue = deque()
        for r in root_fqs:
            queue.append((r, 0, r))
        while queue:
            node, depth, root = queue.popleft()
            for src in rev_adj.get(node, []):
                if src not in up_level:
                    new_depth = depth + 1
                    if new_depth <= max_depth_up:
                        up_level[src] = -(new_depth)
                        if src not in nearest_root:
                            nearest_root[src] = root
                        queue.append((src, new_depth, root))

    # ── Assemble node list ──
    root_set = set(root_fqs)
    all_reached = set(down_level.keys()) | set(up_level.keys())
    nodes = []
    for fq in sorted(all_reached):
        is_root = fq in root_set
        d_val = down_level.get(fq)
        u_val = up_level.get(fq)

        if is_root:
            direction = 'ROOT'
        elif d_val is not None and u_val is not None:
            direction = 'BOTH'
        elif u_val is not None:
            direction = 'U'
        else:
            direction = 'D'

        meta = node_meta.get(fq, {})
        nodes.append({
            'node': fq,
            'container_name': meta.get('container', fq.split('.')[0] if '.' in fq else ''),
            'object_name': meta.get('object', fq.split('.')[1] if '.' in fq else fq),
            'object_kind': meta.get('kind', 'Unknown'),
            'upstream_level': u_val if not is_root else 0,
            'downstream_level': d_val if d_val is not None else (0 if is_root else None),
            'nearest_root': nearest_root.get(fq, ''),
            'direction': direction,
            'is_root': 'Y' if is_root else 'N',
        })

    cycle_cands = extract_cycle_candidates(nodes)
    summary = create_bfs_summary(nodes, cycle_cands)

    return {
        'nodes': nodes,
        'cycle_candidates': cycle_cands,
        'summary': summary,
    }


# ═══════════════════════════════════════════════════════════════════
# Public handler
# ═══════════════════════════════════════════════════════════════════

def handle_graph_analyseDatabase(
    conn: TeradataConnection,
    container_pattern: str,
    exclude_objects: str = '',
    top_n_roots: int = 4,
    max_depth_down: int = 10,
    max_depth_up: int = 0,
    edge_repository: str = '',
    tool_name: str | None = None,
    *args,
    **kwargs
):
    """
    Composite graph analysis — runs findRootObjects, connectedComponents,
    detectCycles, and bfsLevels in a single MCP call with ONE shared
    edge fetch.

    This tool eliminates the scalability bottleneck of serial MCP round-
    trips by combining four graph analyses that would otherwise require
    four separate tool calls, each independently fetching the same edge
    set from Teradata.

    Performance vs individual tools:
      - 1 SQL round-trip instead of 4 (shared edge fetch)
      - 1 MCP response instead of 4 (eliminates stdio serialisation overhead)
      - Same algorithmic complexity (O(V+E) BFS, O(α·N) Union-Find, O(V+E) DFS)
      - In-memory edge sharing: all analyses operate on the same Python list

    Use this for:
      - Full database migration readiness assessment
      - Pre-migration cycle + root + wave analysis in one call
      - Dashboard data population (all four analyses needed simultaneously)
      - Any workflow that would otherwise call 3+ individual graph tools

    Arguments:
      container_pattern - str: CSV LIKE patterns for container scope.
                          Supports wildcards (%) and CSV format.
                          Examples: '%SALES%', '%SALES%,%FINANCE%', 'PROD_%'

                          CRITICAL: STRING type, not array.
                          CORRECT: container_pattern="%SALES%,%FINANCE%"
                          WRONG:   container_pattern=["%SALES%", "%FINANCE%"]

      exclude_objects    - str: CSV LIKE patterns to exclude.
                           Default: '' (no exclusions)

      top_n_roots        - int: Number of top root objects (by downstream
                           dependent count) to include in BFS wave analysis.
                           Default: 4

      max_depth_down     - int: Maximum downstream BFS hops from roots.
                           Default: 10

      max_depth_up       - int: Maximum upstream BFS hops from roots.
                           0 = skip upstream analysis.
                           Default: 0

      edge_repository    - str: Edge repository view/table conforming to the
                           Graph Edge Contract (Src_Container_Name,
                           Src_Object_Name, Src_Kind, Tgt_Container_Name,
                           Tgt_Object_Name, Tgt_Kind columns).
                           Call graph_edgeContractDDL to generate one.
                           Required parameter — no default.

    Returns:
      ResponseType: single response containing all four analyses:

      {
        "root_objects":   { "objects": [...], "summary": {...} },
        "components":     { "node_details": [...], "summaries": [...], "stats": [...] },
        "cycles":         { "details": [...], "summaries": [...], "stats": [...] },
        "bfs_waves":      { "nodes": [...], "cycle_candidates": [...], "summary": {...} },
        "edge_stats":     { "total_edges": N, "fetch_time_ms": N }
      }

    Example calls:
      # Full analysis of Sales and Finance databases
      handle_graph_analyseDatabase(
          conn=connection,
          container_pattern="%SALES%,%FINANCE%",
          edge_repository="MY_LINEAGE_DB.EdgeRepository"
      )

      # Single database family with top 8 roots
      handle_graph_analyseDatabase(
          conn=connection,
          container_pattern="%FINANCE%",
          top_n_roots=8,
          edge_repository="MY_LINEAGE_DB.EdgeRepository"
      )

      # Exclude sandbox schemas
      handle_graph_analyseDatabase(
          conn=connection,
          container_pattern="PROD_%,STAGE_%",
          exclude_objects="SANDBOX%,%.temp_%",
          edge_repository="MY_LINEAGE_DB.EdgeRepository"
      )
    """
    logger.debug(
        "Tool: handle_graph_analyseDatabase: Args: "
        "container_pattern=%s, exclude_objects=%s, top_n_roots=%d, "
        "max_depth_down=%d, max_depth_up=%d, edge_repository=%s",
        container_pattern, exclude_objects, top_n_roots,
        max_depth_down, max_depth_up, edge_repository
    )

    t_start = time.time()
    container_patterns = parse_csv_patterns(container_pattern)
    excl_patterns = parse_csv_patterns(exclude_objects)

    if not container_patterns:
        return create_response(
            {"error": "container_pattern must not be empty"},
            {"tool_name": tool_name or "graph_analyseDatabase",
             "status": "error"}
        )

    if not edge_repository:
        return create_response(
            {"error": "edge_repository is required. Call graph_edgeContractDDL to generate one."},
            {"tool_name": tool_name or "graph_analyseDatabase",
             "status": "error"}
        )

    try:
        # ═══════════════════════════════════════════════════════════
        # STEP 0 — Single shared edge fetch (ONE SQL round-trip)
        # ═══════════════════════════════════════════════════════════
        container_where = build_like_or(container_patterns, 'Src_Container_Name')
        excl_where = _build_excl_where(excl_patterns)

        edge_sql = f"""
LOCKING ROW FOR ACCESS
SELECT
     TRIM(Src_Container_Name) AS SrcDB
    ,TRIM(Src_Object_Name)    AS SrcObj
    ,Src_Kind                 AS SrcKind
    ,TRIM(Tgt_Container_Name) AS TgtDB
    ,TRIM(Tgt_Object_Name)    AS TgtObj
    ,Tgt_Kind                 AS TgtKind
FROM  {edge_repository}
WHERE {container_where}
  {excl_where}
"""
        logger.debug(
            "Tool: handle_graph_analyseDatabase: Edge SQL:\n%s", edge_sql
        )

        with conn.cursor() as cur:
            cur.execute(edge_sql)
            raw_edges = cur.fetchall()

        t_fetch = time.time()
        fetch_ms = round((t_fetch - t_start) * 1000)
        edge_count = len(raw_edges)

        logger.info(
            "Tool: handle_graph_analyseDatabase: Fetched %d edges in %dms",
            edge_count, fetch_ms
        )

        # ── Build in-memory structures shared by all analyses ──
        # Forward adjacency: src → [tgt, ...] (directed: dependency → dependent)
        fwd_adj: dict[str, list[str]] = defaultdict(list)
        # Reverse adjacency: tgt → [src, ...] (for upstream BFS)
        rev_adj: dict[str, list[str]] = defaultdict(list)
        # Node metadata registry
        node_meta: dict[str, dict] = {}
        # Union-Find for connected components
        uf = _UnionFind()
        # Track downstream dependent counts for root discovery
        src_nodes: dict[str, int] = defaultdict(int)
        tgt_nodes: set[str] = set()

        for src_db, src_obj, src_kind, tgt_db, tgt_obj, tgt_kind in raw_edges:
            if not src_obj or not tgt_obj:
                continue  # Skip null edges

            src_fq = f"{src_db}.{src_obj}"
            tgt_fq = f"{tgt_db}.{tgt_obj}"

            fwd_adj[src_fq].append(tgt_fq)
            rev_adj[tgt_fq].append(src_fq)
            uf.union(src_fq, tgt_fq)

            # Count downstream dependents per source
            src_nodes[src_fq] += 1
            tgt_nodes.add(tgt_fq)

            # Store node metadata
            if src_fq not in node_meta:
                node_meta[src_fq] = {
                    'container': src_db,
                    'object': src_obj,
                    'kind': src_kind or 'Unknown',
                }
            if tgt_fq not in node_meta:
                node_meta[tgt_fq] = {
                    'container': tgt_db,
                    'object': tgt_obj,
                    'kind': tgt_kind or 'Unknown',
                }

        # ═══════════════════════════════════════════════════════════
        # STEP 1 — Root objects (objects never appearing as targets)
        # ═══════════════════════════════════════════════════════════
        root_objects = []
        for fq, downstream_count in src_nodes.items():
            if fq not in tgt_nodes:
                meta = node_meta.get(fq, {})
                root_objects.append({
                    'DatabaseName': meta.get('container', ''),
                    'ObjectName': meta.get('object', ''),
                    'FullyQualifiedName': fq,
                    'ObjectType': meta.get('kind', 'Unknown'),
                    'DownstreamDependentCount': downstream_count,
                })

        # Sort by downstream impact descending
        root_objects.sort(
            key=lambda x: (-x['DownstreamDependentCount'], x['FullyQualifiedName'])
        )

        # Summary statistics
        type_counts: dict[str, int] = {}
        db_counts: dict[str, int] = {}
        for obj in root_objects:
            t = obj['ObjectType']
            type_counts[t] = type_counts.get(t, 0) + 1
            d = obj['DatabaseName']
            db_counts[d] = db_counts.get(d, 0) + 1

        root_summary = {
            'total_root_objects': len(root_objects),
            'object_type_counts': type_counts,
            'database_counts': db_counts,
            'total_downstream_dependencies': sum(
                o['DownstreamDependentCount'] for o in root_objects
            ),
        }

        t_roots = time.time()
        logger.info(
            "Tool: handle_graph_analyseDatabase: Found %d root objects in %dms",
            len(root_objects), round((t_roots - t_fetch) * 1000)
        )

        # ═══════════════════════════════════════════════════════════
        # STEP 2 — Connected components (reuse Union-Find from step 0)
        # ═══════════════════════════════════════════════════════════
        raw_comps = uf.components()

        # Assign sequential integer IDs sorted by descending size
        sorted_roots = sorted(raw_comps.keys(), key=lambda r: -len(raw_comps[r]))
        root_to_id = {r: i + 1 for i, r in enumerate(sorted_roots)}

        comp_node_details = []
        comp_id_map: dict[str, int] = {}
        for root, members in raw_comps.items():
            cid = root_to_id[root]
            for fq in members:
                comp_id_map[fq] = cid
                meta = node_meta.get(fq, {})
                comp_node_details.append({
                    'Node_FQ': fq,
                    'DatabaseName': meta.get('container', ''),
                    'ObjectName': meta.get('object', ''),
                    'Component_Id': cid,
                    'Object_Kind': meta.get('kind', 'Unknown'),
                })

        comp_summaries = []
        for root in sorted_roots:
            cid = root_to_id[root]
            members = raw_comps[root]
            comp_summaries.append({
                'Component_Id': cid,
                'Node_Count': len(members),
                'Node_List': ', '.join(members),
            })

        comp_stats = [{
            'Component_Count': len(raw_comps),
            'Node_Count': len(comp_id_map),
            'Edge_Count': edge_count,
            'Largest_Component': max(len(m) for m in raw_comps.values()) if raw_comps else 0,
            'Smallest_Component': min(len(m) for m in raw_comps.values()) if raw_comps else 0,
            'Singleton_Count': sum(1 for m in raw_comps.values() if len(m) == 1),
            'Summary_Message': (
                f"{len(raw_comps)} connected component(s) identified "
                f"across {len(comp_id_map)} node(s) and {edge_count} edge(s)."
            ),
        }]

        t_comps = time.time()
        logger.info(
            "Tool: handle_graph_analyseDatabase: %d components in %dms",
            len(raw_comps), round((t_comps - t_roots) * 1000)
        )

        # ═══════════════════════════════════════════════════════════
        # STEP 3 — Cycle detection (reuse adj + UF from step 0)
        # ═══════════════════════════════════════════════════════════
        all_cycles: list[list[str]] = []
        components_scanned = 0

        for root in sorted_roots:
            cycle_members = set(raw_comps[root])
            if len(cycle_members) < 2:
                continue
            components_scanned += 1
            cycles = _find_cycles_dfs(cycle_members, fwd_adj)
            all_cycles.extend(cycles)

        # Deduplicate by canonical form (min rotation)
        seen_canonical: set[tuple[str, ...]] = set()
        unique_cycles: list[list[str]] = []
        for cycle in all_cycles:
            inner = cycle[:-1]
            if not inner:
                continue
            min_idx = inner.index(min(inner))
            canonical = tuple(inner[min_idx:] + inner[:min_idx])
            if canonical not in seen_canonical:
                seen_canonical.add(canonical)
                unique_cycles.append(cycle)

        # Build cycle details and summaries
        cycle_details = []
        cycle_summaries = []
        cycle_node_set: set[str] = set()

        for cycle_id, cycle in enumerate(unique_cycles, 1):
            cycle_len = len(cycle) - 1
            for pos, fq in enumerate(cycle[:-1], 1):
                cycle_node_set.add(fq)
                cycle_details.append({
                    'Cycle_Id': cycle_id,
                    'Cycle_Pos': pos,
                    'Node_FQ': fq,
                    'Cycle_Length': cycle_len,
                    'Component_Id': comp_id_map.get(fq, 0),
                    'Strategy': 'DFS',
                })
            cycle_summaries.append({
                'Cycle_Id': cycle_id,
                'Cycle_Length': cycle_len,
                'Component_Id': comp_id_map.get(cycle[0], 0),
                'Strategy': 'DFS',
                'Cycle_Path': ' -> '.join(cycle),
            })

        comps_with_cycles = len({
            cd['Component_Id'] for cd in cycle_details
        })

        cycle_stats = [{
            'Cycle_Count': len(unique_cycles),
            'Total_Nodes_In_Cycles': len(cycle_details),
            'Unique_Nodes_In_Cycles': len(cycle_node_set),
            'Components_With_Cycles': comps_with_cycles,
            'Edge_Count': edge_count,
            'Components_Scanned': components_scanned,
            'Strategy_Used': 'DFS',
            'Summary_Message': (
                f"{len(unique_cycles)} cycle(s) detected."
                if unique_cycles else
                "No cycles detected — graph is a DAG."
            ),
        }]

        t_cycles = time.time()
        logger.info(
            "Tool: handle_graph_analyseDatabase: %d cycles in %dms",
            len(unique_cycles), round((t_cycles - t_comps) * 1000)
        )

        # ═══════════════════════════════════════════════════════════
        # STEP 4 — BFS waves from top N root objects
        # ═══════════════════════════════════════════════════════════
        top_roots = root_objects[:top_n_roots]
        top_root_fqs = [r['FullyQualifiedName'] for r in top_roots]

        if top_root_fqs:
            bfs_result = _run_bfs(
                root_fqs=top_root_fqs,
                fwd_adj=fwd_adj,
                rev_adj=rev_adj,
                node_meta=node_meta,
                max_depth_down=max_depth_down,
                max_depth_up=max_depth_up,
            )
        else:
            bfs_result = {
                'nodes': [],
                'cycle_candidates': [],
                'summary': {
                    'total_nodes': 0, 'root_nodes': 0,
                    'upstream_only': 0, 'downstream_only': 0,
                    'both_directions': 0, 'cycle_candidates': 0,
                    'max_upstream_depth': 0, 'max_downstream_depth': 0,
                    'nodes_per_nearest_root': {},
                    'object_kind_counts': {},
                },
            }

        t_bfs = time.time()
        logger.info(
            "Tool: handle_graph_analyseDatabase: BFS %d nodes in %dms",
            len(bfs_result['nodes']), round((t_bfs - t_cycles) * 1000)
        )

        # ═══════════════════════════════════════════════════════════
        # Assemble composite response
        # ═══════════════════════════════════════════════════════════
        t_total = round((time.time() - t_start) * 1000)

        response_data = {
            'root_objects': {
                'objects': root_objects,
                'summary': root_summary,
            },
            'components': {
                'node_details': comp_node_details,
                'summaries': comp_summaries,
                'stats': comp_stats,
            },
            'cycles': {
                'details': cycle_details,
                'summaries': cycle_summaries,
                'stats': cycle_stats,
            },
            'bfs_waves': bfs_result,
            'edge_stats': {
                'total_edges': edge_count,
                'fetch_time_ms': fetch_ms,
                'total_time_ms': t_total,
            },
        }

        metadata = {
            'tool_name': tool_name or 'graph_analyseDatabase',
            'container_pattern': container_pattern,
            'exclude_objects': exclude_objects,
            'top_n_roots': top_n_roots,
            'max_depth_down': max_depth_down,
            'max_depth_up': max_depth_up,
            'edge_repository': edge_repository,
            'timing': {
                'edge_fetch_ms': fetch_ms,
                'root_objects_ms': round((t_roots - t_fetch) * 1000),
                'components_ms': round((t_comps - t_roots) * 1000),
                'cycles_ms': round((t_cycles - t_comps) * 1000),
                'bfs_ms': round((t_bfs - t_cycles) * 1000),
                'total_ms': t_total,
            },
            'counts': {
                'edges': edge_count,
                'root_objects': len(root_objects),
                'components': len(raw_comps),
                'cycles': len(unique_cycles),
                'bfs_nodes': len(bfs_result['nodes']),
            },
            'status': 'success',
            'message': (
                f"Composite analysis complete: {len(root_objects)} roots, "
                f"{len(raw_comps)} components, {len(unique_cycles)} cycles, "
                f"{len(bfs_result['nodes'])} BFS nodes. "
                f"Total: {t_total}ms (1 SQL fetch: {fetch_ms}ms)."
            ),
        }

        logger.info(
            "Tool: handle_graph_analyseDatabase: Complete in %dms — "
            "%d roots, %d components, %d cycles, %d BFS nodes",
            t_total, len(root_objects), len(raw_comps),
            len(unique_cycles), len(bfs_result['nodes'])
        )

        return create_response(response_data, metadata)

    except Exception as e:
        logger.error(
            "Tool: handle_graph_analyseDatabase: Error: %s",
            e, exc_info=True
        )
        return create_response(
            {"error": str(e)},
            {
                "tool_name": tool_name or "graph_analyseDatabase",
                "container_pattern": container_pattern,
                "status": "error",
            }
        )


# ═══════════════════════════════════════════════════════════════════
# Tool registration descriptor
# ═══════════════════════════════════════════════════════════════════

GRAPH_ANALYSE_DATABASE_TOOL = {
    "name": "graph_analyseDatabase",
    "handler": handle_graph_analyseDatabase,
    "description": (
        "Composite graph analysis — runs root object discovery, connected "
        "component analysis, cycle detection, and BFS deployment wave "
        "planning in a SINGLE MCP call with one shared edge fetch. "
        "Use this instead of calling graph_findRootObjects, "
        "graph_connectedComponents, graph_detectCycles, and "
        "graph_bfsLevels individually when you need two or more of "
        "these analyses. Returns all four result sets in one response. "
        "Dramatically faster than sequential calls due to shared edge "
        "fetch (1 SQL round-trip instead of 4) and single MCP response. "
        "Requires an edge repository conforming to the Graph Edge Contract. "
        "If you don't have one yet, call graph_edgeContractDDL first to "
        "generate the CREATE TABLE or CREATE VIEW DDL."
    ),
    "parameters": {
        "container_pattern": {
            "type": "string",
            "description": (
                "CSV LIKE patterns for databases/schemas to analyse. "
                "Supports wildcards: '%SALES%' or '%SALES%,%FINANCE%'."
            ),
            "required": True,
        },
        "exclude_objects": {
            "type": "string",
            "description": (
                "CSV LIKE patterns to exclude. "
                "Example: 'SANDBOX%,%.temp_%'. Default: ''."
            ),
            "default": "",
        },
        "top_n_roots": {
            "type": "integer",
            "description": (
                "Number of top root objects (by downstream impact) "
                "to include in BFS wave analysis. Default: 4."
            ),
            "default": 4,
        },
        "max_depth_down": {
            "type": "integer",
            "description": (
                "Maximum downstream BFS hops from roots. Default: 10."
            ),
            "default": 10,
        },
        "max_depth_up": {
            "type": "integer",
            "description": (
                "Maximum upstream BFS hops. 0 = skip upstream. Default: 0."
            ),
            "default": 0,
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
