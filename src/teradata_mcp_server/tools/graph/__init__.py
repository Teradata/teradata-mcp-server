# graph/__init__.py
"""
Graph analysis tools package for dependency graph analysis.

This __init__.py re-exports all handle_* functions from the individual
tool modules so that the MCP server's ModuleLoader can discover them
via inspect.getmembers() when it loads this package.

The ModuleLoader (module_loader.py) maps the 'graph' prefix to
'teradata_mcp_server.tools.graph' and then calls:

    module = importlib.import_module('teradata_mcp_server.tools.graph')
    for name, func in inspect.getmembers(module, inspect.isfunction):
        all_functions[name] = func

If the handle_* functions are not importable at the package level,
the ModuleLoader finds nothing and no graph tools are registered.

Import order follows the logical workflow:
  findRootObjects → bfsLevels → traceLineage
  → detectCycles → connectedComponents → analyseDatabase (composite)

Author:  Paul Dancer — Teradata Consulting Services
"""

# ── Step 1: Root object discovery (SQL-only) ──────────────────────
# ── Step 6: Composite analysis (single call, shared edge fetch) ──
from .graph_analyse_database import handle_graph_analyseDatabase

# ── Step 2: BFS wave planning (pure Python) ───────────────────────
from .graph_bfs_levels import handle_graph_bfsLevels

# ── Step 5: Connected components (Python Union-Find WCC) ─────────
from .graph_connected_components import handle_graph_connectedComponents

# ── Step 4: Cycle detection (Python Union-Find + iterative DFS) ──
from .graph_detect_cycles import handle_graph_detectCycles

# ── Step 7: Edge contract DDL generator (no DB connection needed) ─
from .graph_edge_contract import handle_graph_edgeContractDDL
from .graph_find_root_objects import handle_graph_findRootObjects

# ── Step 3: Full lineage / impact analysis (hybrid CTE) ──────────
from .graph_trace_lineage import handle_graph_traceLineage
