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
from .graph_findRootObjects import handle_graph_findRootObjects

# ── Step 2: BFS wave planning (pure Python) ───────────────────────
from .graph_bfsLevels import handle_graph_bfsLevels

# ── Step 3: Full lineage / impact analysis (hybrid CTE) ──────────
from .graph_traceLineage import handle_graph_traceLineage

# ── Step 4: Cycle detection (Python Union-Find + iterative DFS) ──
from .graph_detectCycles import handle_graph_detectCycles

# ── Step 5: Connected components (Python Union-Find WCC) ─────────
from .graph_connectedComponents import handle_graph_connectedComponents

# ── Step 6: Composite analysis (single call, shared edge fetch) ──
from .graph_analyseDatabase import handle_graph_analyseDatabase

# ── Step 7: Edge contract DDL generator (no DB connection needed) ─
from .graph_edge_contract import handle_graph_edgeContractDDL
