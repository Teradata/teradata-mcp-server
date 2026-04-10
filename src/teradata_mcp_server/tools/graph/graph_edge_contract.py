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
#    The graph analysis tools (findRootObjects, traceLineage,           #
#    connectedComponents, detectCycles, bfsLevels, analyseDatabase) all           #
#    require an edge repository — a table or view conforming to this contract.    #
#    Users supply its fully-qualified name via the edge_repository parameter.     #
#                                                                                 #
#    Column names are deliberately platform-agnostic:                             #
#      Src_Container_Name / Tgt_Container_Name  (not DatabaseName)                #
#      Src_Object_Name    / Tgt_Object_Name     (not ObjectName)                  #
#      Src_Kind           / Tgt_Kind            (not Object_Kind)                 #
#                                                                                 #
#    Optional enrichment columns (present in lineage_graph; ignored by tools      #
#    that don't use them — safe to omit from custom edge repositories):           #
#      Edge_Relationship   — nature of the edge (e.g. ETL_INPUT, ETL_OUTPUT)     #
#      Transformation_Type — process type (e.g. ETL, FEATURE_ENG, AGGREGATION)   #
#                                                                                 #
#    "Container" generalises across platforms: a Teradata database, a script      #
#    directory, an Informatica workflow folder, a dbt project, etc.               #
#                                                                                 #
#    AI-Native Data Product shortcut:                                             #
#    {ProductName}_Semantic.lineage_graph (Observability Module v1.5) already     #
#    conforms to this contract and can be used directly as edge_repository.       #
#                                                                                 #
#    Contract Version: 1.1                                                        #
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

Version:  1.1
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
  Column Name          Type            Nullable   Description
  ──────────────────   ──────────────  ────────   ──────────────────────────────────
  Src_Container_Name   VARCHAR(128)    No         Container of the source (upstream)
                                                  object. Platform-agnostic: a
                                                  Teradata database, a script
                                                  directory, an ETL workflow folder,
                                                  a dbt project, etc.

  Src_Object_Name      VARCHAR(128)    No         Name of the source object.

  Src_Kind             VARCHAR(30)     No         Object type of the source.
                                                  Recommended: T=Table, V=View,
                                                  P=Procedure, M=Macro, J=JoinIndex,
                                                  H=HashIndex, G=Trigger,
                                                  A=AggregateUDF, F=UDF, S=Script,
                                                  E=ETL Mapping.
                                                  Custom values permitted.

  Tgt_Container_Name   VARCHAR(128)    No         Container of the target
                                                  (downstream) object. Same
                                                  semantics as Src_Container_Name.

  Tgt_Object_Name      VARCHAR(128)    No         Name of the target object.

  Tgt_Kind             VARCHAR(30)     No         Object type of the target.
                                                  Same value domain as Src_Kind.


EDGE SEMANTICS
--------------
Each row represents one directed dependency edge:

    Source (Src)  ──is referenced by──▶  Target (Tgt)

The TARGET object depends on the SOURCE object.
  - SOURCE is upstream: a prerequisite, a referenced table or script.
  - TARGET is downstream: a consumer, a dependent view or mapping.

Example:
  Src_Container_Name='PROD_STD_T'  Src_Object_Name='CUSTOMER'    Src_Kind='Table'
  Tgt_Container_Name='PROD_STD_V'  Tgt_Object_Name='CUST_ACTIVE' Tgt_Kind='View'
  Edge_Relationship='DIRECT'        Transformation_Type='ETL'

  Meaning: View PROD_STD_V.CUST_ACTIVE depends on table PROD_STD_T.CUSTOMER
           via an ETL transformation.


OPTIONAL COLUMNS
----------------
The following columns are recognised by the contract but not required by the
graph analysis tools. They are ignored by tools that do not use them, so
omitting them from a custom edge repository does not break conformance.

  Column Name           Type           Nullable   Description
  ─────────────────────  ─────────────  ────────   ──────────────────────────────────
  Edge_Relationship      VARCHAR(50)    Yes        Nature of the dependency edge.
                                                   Recommended values:
                                                     DIRECT       — object-to-object
                                                                    dependency
                                                     ETL_INPUT    — source table to
                                                                    ETL job
                                                     ETL_OUTPUT   — ETL job to target
                                                                    table
                                                     JOIN         — join dependency
                                                     TRANSFORM    — general
                                                                    transformation
                                                   Custom values permitted.
                                                   Produced by lineage_graph view.

  Transformation_Type    VARCHAR(50)    Yes        Process or transformation category.
                                                   Recommended values:
                                                     ETL            FEATURE_ENG
                                                     AGGREGATION    JOIN
                                                     EMBEDDING_GEN  FILTER
                                                     PIVOT
                                                   Custom values permitted.
                                                   Sourced from data_lineage table.

These columns are present in the {ProductName}_Semantic.lineage_graph view
(Observability Module v1.5) and can be used by graph visualisation tools for
edge labelling and filtering. The graph_* analysis tools (findRootObjects,
bfsLevels, traceLineage, detectCycles, connectedComponents, analyseDatabase)
do not read these columns — they operate on node identity only.


NODE IDENTITY
-------------
Nodes are identified by fully-qualified name: Container.Object

The graph tools construct this internally as:
  Src_Container_Name || '.' || Src_Object_Name   (source node)
  Tgt_Container_Name || '.' || Tgt_Object_Name   (target node)


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
The edge repository may contain additional columns beyond the required and
optional columns defined in this contract. They will be ignored by the graph
tools.


CONTAINER SCOPING
-----------------
All graph tools accept container_pattern or include_containers parameters
that filter edges using SQL LIKE against Src_Container_Name and Tgt_Container_Name.
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

    Required columns in the generated schema (6):
      Src_Container_Name, Src_Object_Name, Src_Kind,
      Tgt_Container_Name, Tgt_Object_Name, Tgt_Kind

    Optional enrichment columns (2):
      Edge_Relationship   — nature of the edge (ETL_INPUT, ETL_OUTPUT, DIRECT…)
      Transformation_Type — process category (ETL, FEATURE_ENG, AGGREGATION…)
      These are ignored by graph analysis tools but useful for visualisation.

    AI-Native Data Product shortcut:
      If you are working within an AI-Native Data Product, the view
      {ProductName}_Semantic.lineage_graph (Observability Module v1.5)
      already conforms to this contract. You do not need to generate DDL
      — pass that view's fully-qualified name directly as edge_repository
      on any graph_* tool. Example:
        edge_repository='StGeoMortgage_Semantic.lineage_graph'

    Arguments:
      conn:            TeradataConnection (unused — accepted for
                       ModuleLoader compatibility).
      target_database: Database in which to create the edge repository.
                       For AI-Native Data Products this is typically
                       {ProductName}_Semantic.
                       Example: 'StGeoMortgage_Semantic'
      object_name:     Name for the edge table/view.
                       Default: 'EdgeRepository'
      output_type:     'TABLE' or 'VIEW'.
                       TABLE: generates CREATE TABLE DDL + separate sample DML.
                              Includes all 6 required + 2 optional columns.
                       VIEW:  generates a CREATE VIEW template for mapping an
                              existing lineage source to all 8 contract columns.
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
        "Tool: handle_graph_edgeContractDDL: "
        "Args: target_database=%s, object_name=%s, output_type=%s",
        target_database, object_name, output_type
    )

    # ── Validate output_type ──────────────────────────────────────────────────
    output_type = output_type.upper().strip()
    if output_type not in ("TABLE", "VIEW"):
        logger.warning(
            "Tool: handle_graph_edgeContractDDL: Invalid output_type '%s'",
            output_type
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
        "Tool: handle_graph_edgeContractDDL: Generated %s DDL for %s.%s",
        output_type, target_database, object_name
    )

    result = {
        "ddl": ddl,
        "output_type": output_type,
        "contract_version": "1.1",
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
-- Contract Version: 1.1
-- ================================================================

CREATE SET TABLE {db}.{name}
    ,NO FALLBACK
    ,NO BEFORE JOURNAL
    ,NO AFTER JOURNAL
    ,CHECKSUM = DEFAULT
    ,DEFAULT MERGEBLOCKRATIO
(
    -- ── Required columns (6) ─────────────────────────────────────
    Src_Container_Name  VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
    ,Src_Object_Name    VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
    ,Src_Kind           VARCHAR(30)  CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
                        COMPRESS ('T','V','P','M','J','H','G','A','F','S','E','R',
                                  'Table','View','Procedure','Macro','Job','Script')
    ,Tgt_Container_Name VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
    ,Tgt_Object_Name    VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
    ,Tgt_Kind           VARCHAR(30)  CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
                        COMPRESS ('T','V','P','M','J','H','G','A','F','S','E','R',
                                  'Table','View','Procedure','Macro','Job','Script')
    -- ── Optional enrichment columns (2) ──────────────────────────
    -- Ignored by graph analysis tools; used by visualisation clients.
    ,Edge_Relationship  VARCHAR(50)  CHARACTER SET UNICODE NOT CASESPECIFIC
                        COMPRESS ('DIRECT','ETL_INPUT','ETL_OUTPUT',
                                  'JOIN','TRANSFORM','FILTER')
    ,Transformation_Type VARCHAR(50) CHARACTER SET UNICODE NOT CASESPECIFIC
                        COMPRESS ('ETL','FEATURE_ENG','AGGREGATION','JOIN',
                                  'EMBEDDING_GEN','FILTER','PIVOT')
)
UNIQUE PRIMARY INDEX (Src_Container_Name, Src_Object_Name, Tgt_Container_Name, Tgt_Object_Name)
;

-- ================================================================
-- NOTE: Multi-Value Compression (MVC) on kind and optional columns
-- ================================================================
-- Src_Kind / Tgt_Kind COMPRESS lists cover both single-letter codes
-- (legacy: T, V, P…) and full-word values (Table, View, Procedure…)
-- used by the lineage_graph view. Remove unused values for optimal
-- compression. Non-listed values store correctly but uncompressed.
--
-- Edge_Relationship and Transformation_Type COMPRESS lists cover the
-- standard values from the Observability Module. Extend as needed for
-- custom edge types in your edge repository.
-- ================================================================

COMMENT ON TABLE {db}.{name}
    AS 'Graph Edge Contract v1.1 - edge repository for Teradata MCP Server graph tools. Each row is a directed dependency: Target depends on Source. Required: 6 columns. Optional enrichment: Edge_Relationship, Transformation_Type.'
;

COMMENT ON COLUMN {db}.{name}.Src_Container_Name
    AS 'Source (upstream) container. Platform-agnostic: Teradata database, script directory, ETL workflow folder, etc.'
;

COMMENT ON COLUMN {db}.{name}.Src_Object_Name
    AS 'Source (upstream) object name.'
;

COMMENT ON COLUMN {db}.{name}.Src_Kind
    AS 'Source object type. Single-letter codes (T=Table, V=View, P=Procedure, M=Macro, J=JoinIndex, H=HashIndex, G=Trigger, S=Script, E=ETL Mapping) or full words (Table, View, Job). Custom values permitted.'
;

COMMENT ON COLUMN {db}.{name}.Tgt_Container_Name
    AS 'Target (downstream) container. Same semantics as Src_Container_Name.'
;

COMMENT ON COLUMN {db}.{name}.Tgt_Object_Name
    AS 'Target (downstream) object name.'
;

COMMENT ON COLUMN {db}.{name}.Tgt_Kind
    AS 'Target object type. Same value domain as Src_Kind.'
;

COMMENT ON COLUMN {db}.{name}.Edge_Relationship
    AS 'Optional. Nature of the dependency edge. Standard values: DIRECT (object dependency), ETL_INPUT (source to job), ETL_OUTPUT (job to target), JOIN, TRANSFORM, FILTER. Custom values permitted. Ignored by graph analysis tools.'
;

COMMENT ON COLUMN {db}.{name}.Transformation_Type
    AS 'Optional. Process or transformation category. Standard values: ETL, FEATURE_ENG, AGGREGATION, JOIN, EMBEDDING_GEN, FILTER, PIVOT. Sourced from data_lineage.transformation_type. Ignored by graph analysis tools.'
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
-- Optional columns omitted — they are not required for conformance.
-- ================================================================

INSERT INTO {db}.{name}
( Src_Container_Name, Src_Object_Name, Src_Kind
 ,Tgt_Container_Name, Tgt_Object_Name, Tgt_Kind)
VALUES
( 'MY_DB_STD_T', 'CUSTOMER',        'Table'
 ,'MY_DB_STD_V', 'CUSTOMER_ACTIVE', 'View')
;

INSERT INTO {db}.{name}
( Src_Container_Name, Src_Object_Name, Src_Kind
 ,Tgt_Container_Name, Tgt_Object_Name, Tgt_Kind)
VALUES
( 'MY_DB_STD_V', 'CUSTOMER_ACTIVE', 'View'
 ,'MY_DB_STD_V', 'CUSTOMER_REPORT', 'View')
;

-- ================================================================
-- Cross-platform example with optional enrichment columns populated.
-- An ETL job is surfaced as a first-class node (matching lineage_graph):
--   CUSTOMER (table) -> ETL_LOAD (job) -> CUSTOMER_FEATURES (table)
-- ================================================================

INSERT INTO {db}.{name}
( Src_Container_Name, Src_Object_Name, Src_Kind
 ,Tgt_Container_Name, Tgt_Object_Name, Tgt_Kind
 ,Edge_Relationship,  Transformation_Type)
VALUES
( 'MY_DB_STD_T', 'CUSTOMER',         'Table'
 ,'',             'ETL_LOAD',         'Job'
 ,'ETL_INPUT',    'ETL')
;

INSERT INTO {db}.{name}
( Src_Container_Name, Src_Object_Name, Src_Kind
 ,Tgt_Container_Name, Tgt_Object_Name, Tgt_Kind
 ,Edge_Relationship,  Transformation_Type)
VALUES
( '',                  'ETL_LOAD',          'Job'
 ,'MY_PRED_STD_T',    'CUSTOMER_FEATURES', 'Table'
 ,'ETL_OUTPUT',       'FEATURE_ENG')
;

-- ================================================================
-- Validation — confirm the edge repository meets the contract.
-- Only the six required columns must be NOT NULL.
-- Expected result: 0 violations.
-- ================================================================

SELECT 'NULL_CHECK' AS Validation
    ,COUNT(*) AS Violations
FROM {db}.{name}
WHERE Src_Container_Name IS NULL
   OR Src_Object_Name    IS NULL
   OR Src_Kind           IS NULL
   OR Tgt_Container_Name IS NULL
   OR Tgt_Object_Name    IS NULL
   OR Tgt_Kind           IS NULL
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
-- Contract Version: 1.1
--
-- Customise the SELECT below to map your lineage source to the
-- six required columns. The two optional enrichment columns
-- (Edge_Relationship, Transformation_Type) are included as
-- placeholders — map them or return NULL if not available.
-- ================================================================

REPLACE VIEW {db}.{name}
(
     Src_Container_Name
    ,Src_Object_Name
    ,Src_Kind
    ,Tgt_Container_Name
    ,Tgt_Object_Name
    ,Tgt_Kind
    -- Optional enrichment columns (NULL if not available in your source)
    ,Edge_Relationship
    ,Transformation_Type
)
AS
LOCKING ROW FOR ACCESS
SELECT
     src.ContainerName      AS Src_Container_Name
    ,src.ObjectName         AS Src_Object_Name
    ,src.ObjectKind         AS Src_Kind
    ,tgt.ContainerName      AS Tgt_Container_Name
    ,tgt.ObjectName         AS Tgt_Object_Name
    ,tgt.ObjectKind         AS Tgt_Kind
    -- ============================================================
    -- Map these to your actual columns, or use NULL if not available.
    -- Examples:
    --   src.RelationshipType  AS Edge_Relationship
    --   src.ProcessCategory   AS Transformation_Type
    -- ============================================================
    ,CAST(NULL AS VARCHAR(50))  AS Edge_Relationship
    ,CAST(NULL AS VARCHAR(50))  AS Transformation_Type
FROM
    -- ============================================================
    -- Replace this with your actual lineage source.
    -- Examples:
    --   Your_DB.Your_Lineage_Table
    --   A join across metadata tables
    --   A UNION ALL of multiple lineage sources
    --   {'{ProductName}'}_Observability.data_lineage (AI-Native Data Product)
    -- ============================================================
    YOUR_DATABASE.YOUR_LINEAGE_TABLE AS src
    -- Map your source columns to the contract column aliases above.
;

COMMENT ON VIEW {db}.{name}
    AS 'Graph Edge Contract v1.1 - edge repository view for Teradata MCP Server graph tools. 6 required columns + 2 optional enrichment columns (Edge_Relationship, Transformation_Type). Customise the source query to map your lineage data.'
;"""


# ──────────────────────────────────────────────────────────────────────────────── #
#  Tool registration descriptor                                                   #
# ──────────────────────────────────────────────────────────────────────────────── #

GRAPH_EDGE_CONTRACT_DDL_TOOL = {
    "name": "graph_edgeContractDDL",
    "handler": handle_graph_edgeContractDDL,
    "description": (
        "Generate Teradata DDL for a Graph Edge Contract-conforming edge "
        "repository table or view. Call this FIRST if you don't yet have an "
        "edge repository — all other graph_* tools require one. "
        "No database connection is used; DDL is returned as text ready to run. "
        "TABLE output includes separate sample DML. "
        "VIEW output generates a customisable template covering all 8 contract "
        "columns: 6 required (Src_Container_Name, Src_Object_Name, Src_Kind, "
        "Tgt_Container_Name, Tgt_Object_Name, Tgt_Kind) and 2 optional "
        "enrichment columns (Edge_Relationship, Transformation_Type) for use "
        "by graph visualisation tools. "
        "AI-Native Data Product shortcut: if you have an Observability Module "
        "(v1.5+), pass {ProductName}_Semantic.lineage_graph directly as "
        "edge_repository — it already conforms to this contract. "
        "Contract Version: 1.1."
    ),
    "parameters": {
        "target_database": {
            "type": "string",
            "description": (
                "Database in which to create the edge repository. "
                "For AI-Native Data Products this is typically "
                "{ProductName}_Semantic. "
                "Example: 'StGeoMortgage_Semantic'."
            ),
            "required": True,
        },
        "object_name": {
            "type": "string",
            "description": (
                "Name for the edge table or view. Default: 'EdgeRepository'."
            ),
            "default": "EdgeRepository",
        },
        "output_type": {
            "type": "string",
            "description": (
                "'TABLE' (default): CREATE TABLE DDL + separate sample DML. "
                "'VIEW': CREATE VIEW template for mapping an existing lineage source."
            ),
            "default": "TABLE",
        },
    },
}
