# ------------------------------------------------------------------------------- #
#  File: graph_edge_contract.py                                                   #
#                                                                                 #
#  Description:                                                                   #
#    Graph Edge Contract — schema abstraction for the graph analysis tools.       #
#                                                                                 #
#    Provides:                                                                    #
#      1. GRAPH_EDGE_CONTRACT constant — canonical contract text, served as an    #
#         MCP Resource via app.py registration.                                   #
#      2. handle_graph_edgeContractDDL() — MCP Tool that generates ready-to-run   #
#         Teradata DDL for a contract-conforming edge table or view.              #
#                                                                                 #
#    The graph analysis tools (findRootObjects, queryDependenciesAgent,           #
#    connectedComponents, detectCycles, bfsLevels, analyseDatabase) all           #
#    require an edge repository — a table or view conforming to this contract.    #
#    Users supply its fully-qualified name via the edge_repository parameter.     #
#                                                                                 #
#    Column names are deliberately platform-agnostic:                             #
#      SrcContainer / TgtContainer  (not DatabaseName)                            #
#      SrcObject    / TgtObject     (not ObjectName)                              #
#      SrcKind      / TgtKind       (not Object_Kind)                             #
#                                                                                 #
#    "Container" generalises across platforms: a Teradata database, a script      #
#    directory, an Informatica workflow folder, a dbt project, etc.               #
#                                                                                 #
#    Contract Version: 1.0                                                        #
# ------------------------------------------------------------------------------- #

import logging
from typing import Any

logger = logging.getLogger("teradata_mcp_server")


# ──────────────────────────────────────────────────────────────────────────────── #
#  GRAPH EDGE CONTRACT — Canonical Text                                           #
#                                                                                 #
#  Registered as an MCP Resource in app.py (URI: graph://edge-contract).          #
#  AI agents retrieve this to understand the edge_repository schema required      #
#  by all graph_* tools.                                                          #
# ──────────────────────────────────────────────────────────────────────────────── #

GRAPH_EDGE_CONTRACT = """
Graph Edge Contract — Teradata MCP Server (Community Edition)
=============================================================

Version:  1.0
Status:   Stable
Applies:  All graph_* tools in the Teradata MCP Server


PURPOSE
-------
The graph analysis tools operate on a directed dependency graph stored as an
edge list. The edge repository is any Teradata table or view that conforms to
this contract. Users supply its fully-qualified name via the edge_repository
parameter on each graph tool.


REQUIRED COLUMNS
----------------
  Column Name    Type            Nullable   Description
  ────────────   ──────────────  ────────   ──────────────────────────────────
  SrcContainer   VARCHAR(128)    No         Container of the source (upstream)
                                            object. Platform-agnostic: a
                                            Teradata database, a script
                                            directory, an ETL workflow folder,
                                            a dbt project, etc.

  SrcObject      VARCHAR(128)    No         Name of the source object.

  SrcKind        VARCHAR(30)     No         Object type of the source.
                                            Recommended: T=Table, V=View,
                                            P=Procedure, M=Macro, J=JoinIndex,
                                            H=HashIndex, G=Trigger,
                                            A=AggregateUDF, F=UDF, S=Script,
                                            E=ETL Mapping.
                                            Custom values permitted.

  TgtContainer   VARCHAR(128)    No         Container of the target
                                            (downstream) object. Same
                                            semantics as SrcContainer.

  TgtObject      VARCHAR(128)    No         Name of the target object.

  TgtKind        VARCHAR(30)     No         Object type of the target.
                                            Same value domain as SrcKind.


EDGE SEMANTICS
--------------
Each row represents one directed dependency edge:

    Source (Src)  ──is referenced by──▶  Target (Tgt)

The TARGET object depends on the SOURCE object.
  - SOURCE is upstream: a prerequisite, a referenced table or script.
  - TARGET is downstream: a consumer, a dependent view or mapping.

Example:
  SrcContainer='PROD_STD_T'  SrcObject='CUSTOMER'    SrcKind='T'
  TgtContainer='PROD_STD_V'  TgtObject='CUST_ACTIVE' TgtKind='V'

  Meaning: View PROD_STD_V.CUST_ACTIVE depends on table PROD_STD_T.CUSTOMER.


NODE IDENTITY
-------------
Nodes are identified by fully-qualified name: Container.Object

The graph tools construct this internally as:
  SrcContainer || '.' || SrcObject   (source node)
  TgtContainer || '.' || TgtObject   (target node)


WHY "CONTAINER" NOT "DATABASE"
------------------------------
The column names are deliberately platform-agnostic. "Container" generalises
across platforms and technologies:

  Platform          Container means
  ────────────────  ────────────────────────────────────────
  Teradata          Database name
  Oracle            Schema name
  SQL Server        Database.Schema
  Informatica       Workflow or folder path
  Shell scripts     Directory path
  dbt               Project or schema
  Tableau/Power BI  Workbook or workspace

This allows a single edge repository to hold cross-platform lineage —
e.g., a Teradata table consumed by an Informatica mapping that feeds a
Tableau dashboard — all in one graph.


ADDITIONAL COLUMNS
------------------
The edge repository may contain additional columns beyond the six required
columns. They will be ignored by the graph tools.


CONTAINER SCOPING
-----------------
All graph tools accept container_pattern or include_containers parameters
that filter edges using SQL LIKE against SrcContainer and TgtContainer.
The edge repository should contain edges across ALL relevant containers —
cross-container dependencies are the primary use case for graph analysis.


DUPLICATE EDGES
---------------
The graph tools tolerate duplicate edges (same Src->Tgt pair appearing more
than once). Duplicates are deduplicated in memory during adjacency list
construction. For performance, it is recommended that the edge repository
contains no duplicates.


DDL GENERATION
--------------
Use the graph_edgeContractDDL tool to generate a ready-to-run CREATE TABLE
or CREATE VIEW statement for a conforming edge repository.
""".strip()


# ──────────────────────────────────────────────────────────────────────────────── #
#  DDL GENERATOR — Tool Handler                                                   #
#                                                                                 #
#  Generates Teradata DDL for a contract-conforming edge table or view.           #
#  No database connection required — pure template generation.                    #
# ──────────────────────────────────────────────────────────────────────────────── #

def handle_graph_edgeContractDDL(
    conn: Any,
    target_database: str,
    object_name: str = "EdgeRepository",
    output_type: str = "TABLE",
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """
    Generate DDL for a Graph Edge Contract-conforming table or view.

    This tool does NOT require a database connection — it generates DDL
    text from templates. No SQL is executed. The conn parameter is
    accepted for ModuleLoader calling convention compatibility but is
    not used.

    Args:
        conn:            TeradataConnection (unused — accepted for
                         ModuleLoader compatibility).
        target_database: Database in which to create the edge repository.
                         Example: 'MY_PROJECT_STD_0_V'
        object_name:     Name for the edge table/view.
                         Default: 'EdgeRepository'
        output_type:     'TABLE' or 'VIEW'.
                         TABLE: generates CREATE TABLE DDL + separate sample DML.
                         VIEW:  generates a CREATE VIEW template.
                         Default: 'TABLE'

    Returns:
        list[dict]: Response payload containing:
            - ddl:              DDL script (CREATE TABLE/VIEW + COMMENTs)
            - sample_dml:       Sample INSERT statements + validation query
                                (TABLE only; absent for VIEW)
            - output_type:      'TABLE' or 'VIEW'
            - contract_version: Contract version string
    """
    logger.debug(
        f"Tool: handle_graph_edgeContractDDL: "
        f"Args: target_database={target_database}, "
        f"object_name={object_name}, output_type={output_type}"
    )

    # ── Validate output_type ──────────────────────────────────────────────────
    output_type = output_type.upper().strip()
    if output_type not in ("TABLE", "VIEW"):
        logger.warning(
            f"Tool: handle_graph_edgeContractDDL: "
            f"Invalid output_type '{output_type}'"
        )
        return [{"error": f"Invalid output_type '{output_type}'. Must be 'TABLE' or 'VIEW'."}]

    # ── Generate DDL (and sample DML for TABLE variant) ─────────────────────
    if output_type == "TABLE":
        ddl = _generate_table_ddl(target_database, object_name)
        sample_dml = _generate_sample_dml(target_database, object_name)
    else:
        ddl = _generate_view_ddl(target_database, object_name)
        sample_dml = None

    logger.info(
        f"Tool: handle_graph_edgeContractDDL: "
        f"Generated {output_type} DDL for {target_database}.{object_name}"
    )

    result = {
        "ddl": ddl,
        "output_type": output_type,
        "contract_version": "1.0",
    }
    if sample_dml is not None:
        result["sample_dml"] = sample_dml

    return [result]


# ──────────────────────────────────────────────────────────────────────────────── #
#  Internal DDL Templates                                                         #
# ──────────────────────────────────────────────────────────────────────────────── #

def _generate_table_ddl(db: str, name: str) -> str:
    """
    Generate CREATE TABLE DDL with column comments (DDL only — no DML).

    Follows the Teradata Engineering Discipline: DDL files contain only
    structural statements (CREATE, COMMENT, GRANT).  Sample DML is
    returned separately by _generate_sample_dml().

    Args:
        db:   Target database name.
        name: Target table name.

    Returns:
        str: Teradata DDL script (CREATE TABLE + COMMENTs).
    """
    return f"""-- ================================================================
-- Graph Edge Contract — Edge Repository
-- Generated by: Teradata MCP Server (Community Edition)
-- Contract Version: 1.0
-- ================================================================

CREATE SET TABLE {db}.{name}
    ,NO FALLBACK
    ,NO BEFORE JOURNAL
    ,NO AFTER JOURNAL
    ,CHECKSUM = DEFAULT
    ,DEFAULT MERGEBLOCKRATIO
(
    SrcContainer    VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
    ,SrcObject      VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
    ,SrcKind        VARCHAR(30)  CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL COMPRESS ('T','V','P','M','J','H','G','A','F','S','E','R')
    ,TgtContainer   VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
    ,TgtObject      VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
    ,TgtKind        VARCHAR(30)  CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL COMPRESS ('T','V','P','M','J','H','G','A','F','S','E','R')
)
UNIQUE PRIMARY INDEX (SrcContainer, SrcObject, TgtContainer, TgtObject)
;

-- ================================================================
-- NOTE: Multi-Value Compression (MVC) on SrcKind / TgtKind
-- ================================================================
-- The COMPRESS lists above use the standard single-letter kind codes
-- (T, V, P, M, J, H, G, A, F, S, E, R). If you store full names
-- instead (e.g. 'Table', 'View', 'Procedure'), amend the COMPRESS
-- lists to match your actual values, otherwise those rows will not
-- benefit from compression. Non-compressed values still store
-- correctly — they just consume full column storage per row.
-- ================================================================

COMMENT ON TABLE {db}.{name}
    AS 'Graph Edge Contract v1.0 - edge repository for Teradata MCP Server graph tools. Each row is a directed dependency: Target depends on Source.'
;

COMMENT ON COLUMN {db}.{name}.SrcContainer
    AS 'Source (upstream) container. Platform-agnostic: Teradata database, script directory, ETL workflow folder, etc.'
;

COMMENT ON COLUMN {db}.{name}.SrcObject
    AS 'Source (upstream) object name.'
;

COMMENT ON COLUMN {db}.{name}.SrcKind
    AS 'Source object type. Standard values: T=Table, V=View, P=Procedure, M=Macro, J=JoinIndex, H=HashIndex, G=Trigger, S=Script, E=ETL Mapping. Custom values permitted.'
;

COMMENT ON COLUMN {db}.{name}.TgtContainer
    AS 'Target (downstream) container. Same semantics as SrcContainer.'
;

COMMENT ON COLUMN {db}.{name}.TgtObject
    AS 'Target (downstream) object name.'
;

COMMENT ON COLUMN {db}.{name}.TgtKind
    AS 'Target object type. Same value domain as SrcKind.'
;"""


def _generate_sample_dml(db: str, name: str) -> str:
    """
    Generate sample INSERT statements and a validation query for a
    Graph Edge Contract table.

    Separated from the DDL to follow the Teradata Engineering Discipline:
    DDL files (.tbl) must never contain INSERT/SELECT statements.

    Args:
        db:   Target database name.
        name: Target table name.

    Returns:
        str: Sample DML script (INSERTs + validation SELECT).
    """
    return f"""-- ================================================================
-- Sample data — two edges forming a simple dependency chain:
--   CUSTOMER (table) <- CUSTOMER_ACTIVE (view) <- CUSTOMER_REPORT (view)
-- ================================================================

INSERT INTO {db}.{name}
(SrcContainer, SrcObject, SrcKind, TgtContainer, TgtObject, TgtKind)
VALUES ('MY_DB_STD_T', 'CUSTOMER', 'T', 'MY_DB_STD_V', 'CUSTOMER_ACTIVE', 'V')
;

INSERT INTO {db}.{name}
(SrcContainer, SrcObject, SrcKind, TgtContainer, TgtObject, TgtKind)
VALUES ('MY_DB_STD_V', 'CUSTOMER_ACTIVE', 'V', 'MY_DB_STD_V', 'CUSTOMER_REPORT', 'V')
;

-- ================================================================
-- Cross-platform example — Teradata table consumed by an
-- Informatica mapping that feeds a Tableau workbook.
-- ================================================================

INSERT INTO {db}.{name}
(SrcContainer, SrcObject, SrcKind, TgtContainer, TgtObject, TgtKind)
VALUES ('MY_DB_STD_T', 'CUSTOMER', 'T', 'INF_PROD/Workflows', 'wf_Customer_Load', 'E')
;

INSERT INTO {db}.{name}
(SrcContainer, SrcObject, SrcKind, TgtContainer, TgtObject, TgtKind)
VALUES ('INF_PROD/Workflows', 'wf_Customer_Load', 'E', 'Tableau/Sales', 'Customer_Dashboard', 'R')
;

-- ================================================================
-- Validation — confirm the edge repository meets the contract.
-- All six columns must be NOT NULL. Expected result: 0 violations.
-- ================================================================

SELECT 'NULL_CHECK' AS Validation
    ,COUNT(*) AS Violations
FROM {db}.{name}
WHERE SrcContainer IS NULL
   OR SrcObject    IS NULL
   OR SrcKind      IS NULL
   OR TgtContainer IS NULL
   OR TgtObject    IS NULL
   OR TgtKind      IS NULL
;"""


def _generate_view_ddl(db: str, name: str) -> str:
    """
    Generate CREATE VIEW DDL template for user customisation.

    The view body contains placeholder references that the user must
    replace with their actual lineage source table/view.

    Args:
        db:   Target database name.
        name: Target view name.

    Returns:
        str: Teradata SQL script with placeholder source references.
    """
    return f"""-- ================================================================
-- Graph Edge Contract — Edge Repository (VIEW)
-- Generated by: Teradata MCP Server (Community Edition)
-- Contract Version: 1.0
--
-- Customise the SELECT below to map your lineage source to the
-- six required contract columns.
-- ================================================================

REPLACE VIEW {db}.{name}
( 
    SrcContainer
    ,SrcObject
    ,SrcKind
    ,TgtContainer
    ,TgtObject
    ,TgtKind
)
AS
LOCKING ROW FOR ACCESS
SELECT
    src.ContainerName   AS SrcContainer
    ,src.ObjectName     AS SrcObject
    ,src.ObjectKind     AS SrcKind
    ,tgt.ContainerName  AS TgtContainer
    ,tgt.ObjectName     AS TgtObject
    ,tgt.ObjectKind     AS TgtKind
FROM
    -- ============================================================
    -- Replace this with your actual lineage source.
    -- Examples:
    --   Your_DB.Your_Lineage_Table
    --   A join across metadata tables
    --   A UNION ALL of multiple lineage sources
    -- ============================================================
    YOUR_DATABASE.YOUR_LINEAGE_TABLE AS src
    -- Map your source columns to the contract column aliases above.
;

COMMENT ON VIEW {db}.{name}
    AS 'Graph Edge Contract v1.0 - edge repository view for Teradata MCP Server graph tools. Customise the source query to map your lineage data.'
;"""
