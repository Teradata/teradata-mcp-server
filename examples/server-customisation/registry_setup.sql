
-- ============================================================================
-- Setup the tool registry tables and views
-- ============================================================================
create database mcp as perm=10e6;

database mcp;

CREATE TABLE mcp_tool(
    ToolName VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL,
    DataBaseName VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL,
    TableName VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NULL,
    description VARCHAR(10000) CHARACTER SET UNICODE --The tool description can be infered from the object comment string, but we may want to override it
) UNIQUE PRIMARY INDEX(ToolName);

CREATE TABLE mcp_tool_type(
    toolType CHAR(5) NOT NULL,
    description VARCHAR(10000) NOT NULL) 
    UNIQUE PRIMARY INDEX(toolType);

ins mcp_tool_type('t', 'Tabular dataset defined as table in this system');
ins mcp_tool_type('v', 'Tabular dataset defined as view in this system');
ins mcp_tool_type('m', 'Macro defined in this system');
ins mcp_tool_type('f', 'Scalar function (UDF) defined in this system');

replace view mcp_toolV as
sel
r.ToolName,
r.DataBaseName,
r.TableName,
coalesce(r.description, t.CommentString) description,
t.TableKind toolType
from mcp_tool r
join dbc.TablesV t
    on r.DataBaseName=t.DataBaseName
    and r.TableName=t.TableName
where t.TableKind in ('M', 'V', 'T', 'F')

-- Get tool parameters with details
replace view mcp_toolParamsV as
SELECT 
    r.ToolName,
    c.ColumnName AS ParamName,
    c.ColumnType AS ParamType,
    c.ColumnLength AS ParamLength,
    c.ColumnId - 1024 AS ParamPosition,
    c.Nullable ParamRequired,
    c.CommentString AS ParamComment
from mcp_tool r
join dbc.TablesV t
    on r.DataBaseName=t.DataBaseName
    and r.TableName=t.TableName
join dbc.ColumnsV c 
    ON c.DatabaseName = t.DatabaseName 
    AND c.TableName = t.TableName
where t.TableKind <> 'F' or c.SPParameterType='I'    

-- Get tool docstrings
replace view mcp_toolDocV as 
SELECT 
    t.toolName,
    COALESCE(t.description, 'No description') || CHR(10) ||
    CHR(10) ||
    'Arguments:' || CHR(10) ||'   '||
    COALESCE(
        (SELECT TRIM(BOTH FROM 
            XMLAGG(
                '  ' || TRIM(p.ParamName) || ' - ' || 
                COALESCE(p.ParamComment, 'no description') || CHR(10)
                ORDER BY p.ParamPosition
            ) (VARCHAR(10000))
        )
         FROM mcp_toolParamsV p
         WHERE p.ToolName = t.ToolName),
        '  (no parameters)'
    ) AS docstring
FROM mcp_toolV t;

create table mcp_tool_user_access
(
    ToolName VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL,
    UserName VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
) Primary index (toolName);

create table mcp_tool_tag
(
    ToolName VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL,
    TagName VARCHAR(128) CHARACTER SET UNICODE NOT CASESPECIFIC NOT NULL
) Primary index (toolName);

replace view mcp_list_tools as
sel
t.ToolName,
r.databasename,
r.tablename,
trim(r.toolType) toolType,
d.docstring,
XMLAGG(tt.TagName||' ') Tags
from mcp_toolV r
join mcp_tool_user_access t
    on t.ToolName=r.ToolName    
left join mcp_tool_tag tt
    on t.ToolName=tt.ToolName
left join mcp_toolDocV d
    on t.ToolName=d.ToolName    
where t.username=user
group by 1, 2, 3, 4, 5;

replace view mcp_list_toolParams as
sel
r.*
from mcp_toolParamsV r
join mcp_tool_user_access t
    on t.ToolName=r.ToolName    
where t.username=user;

-- ============================================================================
-- Create the custom tool functions and macros
-- ============================================================================

database demo_user;

-- FUNCTION: weekday
REPLACE FUNCTION weekday (dt varchar(100))
RETURNS VARCHAR(100)
LANGUAGE SQL
CONTAINS SQL
DETERMINISTIC
SQL SECURITY DEFINER
COLLATION INVOKER
INLINE TYPE 1
RETURN TO_CHAR(CAST(dt AS DATE FORMAT 'YYYY-MM-DD'), 'Day');

-- Include parameter documentation in the function comment
COMMENT ON FUNCTION weekday AS 
'Extracts the weekday name from a date string.';

-- Attempt to comment on function parameter
COMMENT ON COLUMN weekday.dt AS 'Date string in YYYY-MM-DD format';

-- Attempt to comment on function parameter
COMMENT ON COLUMN weekday.RETURN0 AS 'Weekday name (e.g., Monday, Tuesday)';

sel weekday('2023-12-19')

-- MACRO: dba_tableSpace
REPLACE MACRO dba_tableSpace(
    database_name VARCHAR(128),
    table_name VARCHAR(128)
) AS (
    SELECT 
        DatabaseName, 
        TableName, 
        SUM(CurrentPerm) AS CurrentPerm, 
        SUM(PeakPerm) AS PeakPerm,
        CAST((100-(AVG(CURRENTPERM)/MAX(NULLIFZERO(CURRENTPERM))*100)) AS DECIMAL(5,2)) AS SkewPct
    FROM DBC.AllSpaceV
    WHERE 
        (COALESCE(:database_name, '') = '' OR DatabaseName = :database_name)
        AND (COALESCE(:table_name, '') = '' OR TableName = :table_name)
    GROUP BY DatabaseName, TableName
    ORDER BY 3 DESC;
);

COMMENT ON MACRO dba_tableSpace AS 
'Get table space usage information with optional filtering by database and/or table.
Returns current permanent space, peak permanent space, and skew percentage.
Parameters:
 - Database name
 - Table name
 Use empty string or NULL for all databases/tables'
;

COMMENT ON COLUMN dba_tableSpace.database_name AS 'Database name to filter by. Use empty string for all databases.';

COMMENT ON COLUMN dba_tableSpace.table_name AS 'Table name to filter by. Use empty string for all tables.';

-- MACRO: dba_databaseSpace
REPLACE MACRO dba_databaseSpace(
    database_name VARCHAR(128)
) AS (
    SELECT
        DatabaseName,
        CAST(SUM(MaxPerm)/1024/1024/1024 AS DECIMAL(10,2)) AS SpaceAllocated_GB,
        CAST(SUM(CurrentPerm)/1024/1024/1024 AS DECIMAL(10,2)) AS SpaceUsed_GB,
        CAST((SUM(MaxPerm) - SUM(CurrentPerm))/1024/1024/1024 AS DECIMAL(10,2)) AS FreeSpace_GB,
        CAST((SUM(CurrentPerm) * 100.0 / NULLIF(SUM(MaxPerm),0)) AS DECIMAL(10,2)) AS PercentUsed
    FROM DBC.DiskSpaceV
    WHERE MaxPerm > 0
        AND (COALESCE(:database_name, '') = '' OR DatabaseName = :database_name)
    GROUP BY 1
    ORDER BY PercentUsed DESC;
);

COMMENT ON MACRO dba_databaseSpace AS 
'Get database space allocation and usage information.
Returns space allocated, used, free, and percentage used in gigabytes.';

COMMENT ON COLUMN dba_databaseSpace.database_name AS 'Database name to filter by. Use empty string for all databases.';

EXEC dba_tableSpace(database,'');
EXEC dba_databaseSpace(database)

-- ============================================================================
-- Register the custom tools
-- ============================================================================
ins mcp_tool('get_weekday', 'demo_user', 'weekday', null);
ins mcp_tool('dba_tableSpace', 'demo_user', 'dba_tableSpace', null);
ins mcp_tool('dba_databaseSpace', 'demo_user', 'dba_databaseSpace', null);


ins mcp_tool_user_access
sel ToolName, user from mcp_toolV;

ins mcp_tool_tag
sel ToolName, case when substr(toolname,1,3)='dba' then 'dba' else 'general' end 
from mcp_toolV;


-- ============================================================================
--Check if all that worked
-- ============================================================================
sel * from mcp.mcp_list_tools;
sel * from mcp.mcp_list_toolParams;
