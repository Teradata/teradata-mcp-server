"""
_graph_utils.py — Shared utility functions for ODEX graph analysis tools.

This module is INTERNAL to the graph tool package — it is not registered
as an MCP tool and is not imported by the server directly. It exists to
avoid duplicating the BFS helper logic across individual tool files.

Naming convention: the leading underscore signals internal use only.

Contents:
  bfs_safe_int            — Safe int conversion for nullable level columns
  create_bfs_summary      — Summary statistics from a BFS node result list
  extract_cycle_candidates — Extract direction='BOTH' nodes as cycle candidates

These helpers were originally private functions (_bfs_safe_int,
_create_bfs_summary, _extract_cycle_candidates) embedded in the monolithic
graph_tools.py. They are lifted here unchanged so each tool file can import
them rather than carrying local copies.

Author:  Paul Dancer — Teradata Global Field Tech
"""


def bfs_safe_int(value) -> int | None:
    """
    Safely convert a value to int, returning None if conversion fails.

    Used for upstream_level and downstream_level columns which may be None
    (NULL from Teradata) when a node is unreachable in one direction.

    Arguments:
      value - Any value from a node dict or Teradata result row

    Returns:
      int or None
    """
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def create_bfs_summary(nodes: list, cycle_candidates: list) -> dict:
    """
    Create summary statistics from a BFS node result list.

    cycle_candidates is passed in from the caller rather than being
    computed internally — extract_cycle_candidates is called once in
    the handler and the result is shared here and in response_data,
    avoiding a redundant second pass over the node list.

    Arguments:
      nodes            - List of node dicts (one per reachable node)
      cycle_candidates - Pre-computed list from extract_cycle_candidates

    Returns:
      Dictionary with counts by direction and depth extremes:
        total_nodes, root_nodes, upstream_only, downstream_only,
        both_directions, cycle_candidates, max_upstream_depth,
        max_downstream_depth, nodes_per_nearest_root, object_kind_counts
    """
    root_nodes       = [n for n in nodes if n.get('is_root')   == 'Y']
    upstream_nodes   = [n for n in nodes if n.get('direction') == 'U']
    downstream_nodes = [n for n in nodes if n.get('direction') == 'D']
    both_nodes       = [n for n in nodes if n.get('direction') == 'BOTH']
    cycle_cands      = cycle_candidates

    # Deepest upstream level (most negative → largest absolute value)
    up_levels = [
        abs(bfs_safe_int(n.get('upstream_level')) or 0)
        for n in nodes
        if bfs_safe_int(n.get('upstream_level')) is not None
    ]

    # Deepest downstream level (most positive)
    down_levels = [
        bfs_safe_int(n.get('downstream_level')) or 0
        for n in nodes
        if bfs_safe_int(n.get('downstream_level')) is not None
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
        "total_nodes":            len(nodes),
        "root_nodes":             len(root_nodes),
        "upstream_only":          len(upstream_nodes),
        "downstream_only":        len(downstream_nodes),
        "both_directions":        len(both_nodes),
        "cycle_candidates":       len(cycle_cands),
        "max_upstream_depth":     max(up_levels,   default=0),
        "max_downstream_depth":   max(down_levels, default=0),
        "nodes_per_nearest_root": root_groups,
        "object_kind_counts":     kind_counts,
    }


def extract_cycle_candidates(nodes: list) -> list:
    """
    Extract nodes that are reachable in both directions with unequal
    absolute upstream and downstream levels.

    A node with direction='BOTH' and abs(upstream_level) != downstream_level
    is a cycle candidate — the asymmetry indicates a back-edge in the graph,
    which is the hallmark of a circular reference when traversing the ODEX
    dependency graph.

    Nodes with direction='BOTH' and equal absolute levels are shared
    dependencies (reachable in both directions at the same hop count)
    and are included with cycle_likely=False for completeness.

    Arguments:
      nodes - List of node dicts

    Returns:
      List of cycle candidate dicts enriched with:
        cycle_likely - True if abs(upstream_level) != downstream_level
        upstream_abs - Absolute value of upstream_level for easy comparison
    """
    candidates = []

    for n in nodes:
        if n.get('direction') != 'BOTH':
            continue

        up_level   = bfs_safe_int(n.get('upstream_level'))
        down_level = bfs_safe_int(n.get('downstream_level'))

        if up_level is None or down_level is None:
            continue

        up_abs       = abs(up_level)
        cycle_likely = up_abs != down_level

        candidates.append({
            **n,
            "upstream_abs": up_abs,
            "cycle_likely": cycle_likely,
        })

    # Sort: most likely cycles first (asymmetric), then by node name
    candidates.sort(
        key=lambda x: (not x['cycle_likely'], x.get('node', ''))
    )

    return candidates
