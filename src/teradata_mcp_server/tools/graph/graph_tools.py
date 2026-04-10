"""
graph_tools.py — Registration aggregator for graph analysis tools.

──────────────────────────────────────────────────────────────────────
WHY THIS FILE EXISTS AND WHY IT IS STRUCTURED THIS WAY
──────────────────────────────────────────────────────────────────────

This file is intentionally a THIN HUB. It contains no handler logic,
no SQL, and no business rules. Its only job is to import handlers and
descriptors from the individual tool modules in the graph/ sub-package
and expose them as a single GRAPH_TOOLS list for MCP server registration.

This structure was adopted for the following reasons:

1. VERSION CONTROL
   Each tool lives in its own file. A git diff for a bug fix or feature
   change touches exactly one tool file — not a 2,000+ line monolith.
   PR reviews are scoped. Blame history is meaningful. Bisecting a
   regression is straightforward.

2. INDEPENDENT DEPLOYMENT
   A hotfix to graph_bfsLevels can be deployed by copying one file.
   There is no risk of inadvertently shipping changes to other tools
   alongside an unrelated fix.

3. PARALLEL DEVELOPMENT
   Multiple engineers can work on different tools simultaneously without
   merge conflicts. Separate files eliminate the constant collision source
   that a shared monolith creates.

4. TESTABILITY
   Each tool file can be unit-tested in isolation. A test for
   graph_bfsLevels only needs to import that one module and mock the
   connection — it does not pull in other tools, their imports, or their
   dependencies.

5. SEPARATION OF CONCERNS
   Tool logic, shared utilities, and server registration are three
   distinct concerns. They now live in three distinct places:
     graph/<tool>.py        — handler logic + descriptor
     graph/_graph_utils.py  — shared BFS helpers (internal, not a tool)
     graph_tools.py         — this file: registration only

──────────────────────────────────────────────────────────────────────
PACKAGE STRUCTURE
──────────────────────────────────────────────────────────────────────

  teradata_mcp_server/tools/
  ├── graph_tools.py                      ← YOU ARE HERE (hub only)
  ├── graph/
  │   ├── __init__.py
  │   ├── _graph_utils.py                 ← shared helpers (bfs_safe_int,
  │   │                                      create_bfs_summary,
  │   │                                      extract_cycle_candidates)
  │   ├── graph_traceLineage.py           ← hybrid: Python CTEs, server-side traversal
  │   ├── graph_findRootObjects.py        ← SQL-only root object discovery
  │   ├── graph_detectCycles.py           ← Python: Union-Find + iterative DFS
  │   ├── graph_connectedComponents.py    ← Python: Union-Find WCC analysis
  │   └── graph_bfsLevels.py             ← Python BFS (no SP dependency)
  └── utils.py                            ← shared MCP utilities (create_response etc.)

──────────────────────────────────────────────────────────────────────
ADDING A NEW TOOL
──────────────────────────────────────────────────────────────────────

  1. Create graph/graph_<toolName>.py following the existing module
     pattern (module docstring, imports, handler, descriptor constant).
  2. Import the handler and descriptor here (two lines below).
  3. Add the descriptor to GRAPH_TOOLS (one line below).
  4. Create tests/tools/graph/test_graph_<toolName>.py.

Nothing else changes — the MCP server consumes GRAPH_TOOLS unchanged.

──────────────────────────────────────────────────────────────────────
SP-FREE ARCHITECTURE — ALL TOOLS
──────────────────────────────────────────────────────────────────────

All graph tools in this package are free of stored procedure (SP)
dependencies.  No Teradata DDL objects are required beyond read access
to the edge repository view/table.  The implementation strategies are:

  graph_findRootObjects
    Pure SQL SELECT — NOT EXISTS subquery identifies objects with no
    upstream dependencies.  No Python algorithm required.

  graph_bfsLevels
    Pure Python — one bulk edge SELECT, then standard queue-based BFS
    (O(V+E)) in the MCP server process.  Replaced an SP-based
    Bellman-Ford SQL relaxation loop.

  graph_detectCycles
    Pure Python — one scoped edge SELECT, then Union-Find WCC
    partitioning followed by iterative DFS (grey/black colouring).
    Iterative DFS avoids Python's recursion limit on deep graphs.

  graph_connectedComponents
    Pure Python — one scoped edge SELECT, then path-compressed
    Union-Find assigns every node to a component in O(α·N) time.

  graph_traceLineage
    Hybrid — Python constructs Teradata recursive CTEs and executes
    them as plain SELECT statements.  The recursive traversal runs
    entirely in Teradata spool (server-side), returning only the
    reachable subgraph across the network.  Python owns orchestration,
    deduplication, and response assembly.  This approach avoids
    transferring the full edge table when only a small subgraph is
    needed — critical at scale (100 000+ edges).

The only Teradata privilege required across all tools is SELECT on
the edge_repository view/table.

──────────────────────────────────────────────────────────────────────
"""

import logging

# ── Individual tool imports ────────────────────────────────────────────────
#
# Each import pair brings in:
#   handle_*  — the callable handler passed to the MCP framework
#   *_TOOL    — the descriptor dict (name, handler ref, description, parameters)
#
# Import order matches logical workflow:
#   findRootObjects → bfsLevels → traceLineage → detectCycles → connectedComponents → analyseDatabase

from teradata_mcp_server.tools.graph.graph_findRootObjects import (
    handle_graph_findRootObjects,
    GRAPH_FIND_ROOT_OBJECTS_TOOL,
)

from teradata_mcp_server.tools.graph.graph_bfsLevels import (
    handle_graph_bfsLevels,
    GRAPH_BFS_LEVELS_TOOL,
)

from teradata_mcp_server.tools.graph.graph_traceLineage import (
    handle_graph_traceLineage,
    GRAPH_TRACE_LINEAGE_TOOL,
)

from teradata_mcp_server.tools.graph.graph_detectCycles import (
    handle_graph_detectCycles,
    GRAPH_DETECT_CYCLES_TOOL,
)

from teradata_mcp_server.tools.graph.graph_connectedComponents import (
    handle_graph_connectedComponents,
    GRAPH_CONNECTED_COMPONENTS_TOOL,
)

from teradata_mcp_server.tools.graph.graph_analyseDatabase import (
    handle_graph_analyseDatabase,
    GRAPH_ANALYSE_DATABASE_TOOL,
)

from teradata_mcp_server.tools.graph.graph_edge_contract import (
    handle_graph_edgeContractDDL,
    GRAPH_EDGE_CONTRACT_DDL_TOOL,
)

logger = logging.getLogger("teradata_mcp_server")

# ── Tool registry ──────────────────────────────────────────────────────────
#
# GRAPH_TOOLS is the single list consumed by the MCP server at startup.
# The server iterates this list and registers each tool's name, handler,
# and parameter schema with the MCP protocol layer.
#
# Order here controls the order tools appear in MCP tool listings.
# Workflow order (roots → BFS → dependencies → cycles → components)
# makes the listing intuitive for both humans and AI agents.
#
# To disable a tool temporarily: comment out its entry here.
# To add a new tool: append its descriptor (see ADDING A NEW TOOL above).

GRAPH_TOOLS = [
    GRAPH_EDGE_CONTRACT_DDL_TOOL,     # Step 0 — generate edge repository DDL
    GRAPH_FIND_ROOT_OBJECTS_TOOL,     # Step 1 — discover seed objects
    GRAPH_BFS_LEVELS_TOOL,            # Step 2 — wave planning + blast radius
    GRAPH_TRACE_LINEAGE_TOOL,         # Step 3 — full lineage + impact paths
    GRAPH_DETECT_CYCLES_TOOL,         # Step 4 — cycle validation
    GRAPH_CONNECTED_COMPONENTS_TOOL,  # Step 5 — graph partitioning
    GRAPH_ANALYSE_DATABASE_TOOL,      # Step 6 — composite single-fetch analysis
]

logger.debug(
    "graph_tools: registered %d tools: %s",
    len(GRAPH_TOOLS),
    [t['name'] for t in GRAPH_TOOLS]
)
